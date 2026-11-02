#!/usr/bin/env python3
"""Extract improvement signals from OpenCode, Grok, or Claude session logs.

Pure-stdlib CLI and importable functions.  Designed to be invoked by the
``introspector`` agent after an MDU (or any task) to turn recent session
evidence into agent-definition suggestions without ever editing definitions
or source code.

OpenCode v2 stores (``session_v2``/``session_message``) are read by extracting
the ``content`` array: ``text`` parts become the message text (``reasoning``
parts are deliberately excluded) and finalized ``tool`` parts become synthetic
``role="tool"`` events.  Permission events are not extractable on v2 (the
``permission`` table is project-scoped), so ``permission_thrash`` reads zero by
construction there.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

__all__ = ["collect_signals", "signals_from_manifest", "main"]

# ---------------------------------------------------------------------------
# Signal detection constants
# ---------------------------------------------------------------------------

# Verdict matchers are word-boundary anchored (mdu-52).  Plain substring
# matching scored a reviewer NIT that merely named the signal kind
# ("review_reject_streak") as a rejection round; ``\b`` alone is not enough
# either, because prose/hyphen spellings and quoted phrase-list entries keep
# their boundaries, so VERDICT_MENTION_RE strips those mentions first.
REJECTION_RE = re.compile(
    r"\b(?:request changes|changes requested|do not approve|not approved"
    r"|reject(?:ed|s|ing|ion|ions)?)\b",
    re.IGNORECASE,
)
APPROVAL_RE = re.compile(
    r"\b(?:approv(?:e|es|ed)|lgtm|sign-offs?)\b",
    re.IGNORECASE,
)
# Stripped (replaced by a single space) before verdict matching: the signal
# kind in any spelling, an adjacent negated plural, and a quoted standalone
# phrase are mentions, not verdicts.  A genuine verdict never carries these
# forms, so removing them can only narrow the match.
VERDICT_MENTION_RE = re.compile(
    r"(?i)\b(?:review[\s_-]+)?reject[\s_-]+streak\b"  # the signal kind, any spelling
    r"|\b(?:no|zero)\s+rejections?\b"  # adjacent negated plural
    r"|[`'\"]\s*(?:request changes|changes requested|do not approve"
    r"|not approved|reject(?:ed|s|ing|ion|ions)?)\s*[`'\"]"  # quoted standalone phrase
    # Quantified-metric mention (mdu-52 cycle 2, live AC-report FP): the reject
    # counter's name and the shapes its evidence/report templates put around it
    # are measurements, not verdicts.  Every branch keeps the "reject" stem, so
    # stripping can only remove matches, never create one; a bare "rejections"
    # with no quantifier/template context still reads as a verdict.
    r"|\breview_rejections?\b"  # metric name: review_rejection(s)
    # ``consecutive`` is mandatory: only the counter's own template uses it.
    # Without it, a bare "<count> rejections" span ("2 rejections remain
    # unaddressed") was stripped and flipped genuine verdicts false; it also
    # broke idempotence, since "two review_rejections rejections" lost the
    # metric name on pass 1 and the count span on pass 2.  Requiring the word
    # leaves both passes agreeing with the first.
    r"|\b(?:\d+|zero|no|none|one|two|three)\s+consecutive\s+rejections?\b"
    r"|\brejections?\s*(?:[=!<>]=?|≥|≤)\s*\d+"  # counter comparison
    r"|\brejections?\s+from\b"  # evidence template tail
)

# A QA phase must end with a standalone verdict line ("QA GRADE: FAIL").
# Line-anchored so a message that quotes the instruction mid-line
# ("... QA GRADE: PASS or QA GRADE: FAIL.") does not count.
QA_FAIL_VERDICT = re.compile(r"(?im)^qa grade:\s*fail\b")

# Rotated model tiers share one role; pool their counts under the base name.
TIER_SUFFIXES = ("-pro", "-mid", "-premium", "-free")

REVIEWER_SUBSTRINGS = ["code-reviewer", "grok-review"]
CODER_SUBSTRINGS = [
    "just-code",
    "grok-just-code",
    "grok-mdu-code",
    "implement",
    "coder",
]
QA_SUBSTRINGS = ["qa", "grok-qa"]

LONG_CYCLE_WARN_S = 480
LONG_CYCLE_HIGH_S = 900
STALL_HIGH_S = 600
IDLE_GAP_THRESHOLD_S = 600
TOKEN_HOTSPOT_ABSOLUTE = 80_000
TOKEN_HOTSPOT_SHARE = 0.40
TOKEN_HOTSPOT_MIN = 20_000
REPEATED_ERROR_THRESHOLD = 3
PERMISSION_THRESHOLD = 5
CONTEXT_REREAD_THRESHOLD = 4
QA_FAIL_THRESHOLD = 2
EPS_MS = 300_000
CACHE_MISS_READ_MAX = 1152
CACHE_MISS_INPUT_MIN = 80_000
LONG_CONTEXT_TOKENS = 140_000
LONG_CONTEXT_HIGH_TOKENS = 200_000

# Opaqueness notes for OpenCode v2 trees.  A structural zero (no text, no
# permission surface) must never read as a clean run.  Both wordings are
# greppable and deliberately avoid the substrings ``v1`` and ``store selected``
# so they cannot collide with the v1/store-selection notes.
V2_PERMISSION_NOTE = (
    "v2 permission extraction: none (permission table is project-scoped, not "
    "session-scoped); permission_thrash reads zero — treat as UNKNOWN"
)
V2_TEXT_MISSING_NOTE = (
    "v2 text extraction: none of {count} assistant message(s) carried "
    "extractable text; text-based signals read zero — treat as UNKNOWN"
)

FLAGSHIP_MODELS = ("grok-4.7", "glm-5.2", "kimi-k3")
BULK_AGENTS = {
    "just-code",
    "test-agent",
    "code-reviewer",
    "qa",
    "devops",
    "research",
    "ui-ux-designer",
    "grok-just-code",
    "grok-test-agent",
    "grok-code-reviewer",
    "grok-qa",
    "grok-devops",
    "grok-research",
    "grok-ui-ux-designer",
    "grok-mdu-code",
}


# ---------------------------------------------------------------------------
# Secret redaction
# ---------------------------------------------------------------------------

_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"(?i)(api[_-]?key|apikey|token|secret|password|passwd|auth)[\s]*[:=][\s]*"
            r'["\']?[a-z0-9_\-/+=]{8,}["\']?'
        ),
        r"\1=***",
    ),
    (re.compile(r"(?i)(bearer\s+)[a-z0-9_\-/+=]{20,}"), r"\1***"),
    (
        re.compile(
            r"\b(?:sk|pk|ghp|gho|ghu|ghs|ghr|glpat|hf_|hf-)[a-z0-9_\-/+=]{16,}\b"
        ),
        "***",
    ),
]


def redact(text: str) -> str:
    """Remove strings that look like API keys/tokens from free-form text."""
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def _strip_think(text: str) -> str:
    """Remove chain-of-thought blocks so they cannot count as verdicts.

    Strips closed ``<think>...</think>`` blocks and an unclosed ``<think>``
    to end of string (case-insensitive).
    """
    text = re.sub(r"(?is)<think>.*?</think>", "", text)
    text = re.sub(r"(?is)<think>.*", "", text)
    return text


def _verdict_text(text: str) -> str:
    """Think-stripped text with mention/negation guards neutralized.

    Each guard match is replaced by a single space (never the empty string)
    so stripping cannot join two fragments into a verdict phrase.
    """
    return VERDICT_MENTION_RE.sub(" ", _strip_think(text))


def _rejects(vt: str) -> bool:
    """Match a rejection phrase against already-guard-neutralized text."""
    return REJECTION_RE.search(vt) is not None


def _is_rejection(text: str) -> bool:
    return _rejects(_verdict_text(text))


def _is_approval(text: str) -> bool:
    vt = _verdict_text(text)
    return APPROVAL_RE.search(vt) is not None and not _rejects(vt)


def _is_reviewer(agent: str) -> bool:
    return any(sub in agent.lower() for sub in REVIEWER_SUBSTRINGS)


def _is_qa(agent: str) -> bool:
    return any(sub in agent.lower() for sub in QA_SUBSTRINGS)


def _family(agent: str) -> str:
    """Return the role family: the name with one trailing tier suffix stripped.

    ``code-reviewer-pro`` and ``code-reviewer-free`` both become
    ``code-reviewer``.  No cross-harness unification happens (``grok-qa`` stays
    ``grok-qa``): one store per session makes name collisions impossible.
    """
    name = agent.lower()
    for suffix in TIER_SUFFIXES:
        if name.endswith(suffix) and len(name) > len(suffix):
            return name[: -len(suffix)]
    return name


def _is_coder(agent: str) -> bool:
    return any(sub in agent.lower() for sub in CODER_SUBSTRINGS)


def _coerce_float(value: float | int | str | None) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _coerce_int(value: float | int | str | None) -> int:
    if value is None:
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _extract_text(payload: dict) -> str:
    """Best-effort text extraction from a normalized message/part payload."""
    if isinstance(payload, str):
        return payload
    pieces: list[str] = []
    for key in ("text", "content", "message", "result", "output", "error"):
        val = payload.get(key)
        if val is None:
            continue
        if isinstance(val, str):
            pieces.append(val)
        elif isinstance(val, dict):
            pieces.append(_extract_text(val))
        elif isinstance(val, list):
            for item in val:
                pieces.append(_extract_text(item) if isinstance(item, dict) else str(item))
    return " ".join(pieces)


# ---------------------------------------------------------------------------
# Signal objects
# ---------------------------------------------------------------------------


def _signal(
    kind: str,
    severity: str,
    agent: str,
    evidence: str,
    suggestion: str,
    apply_now: str,
) -> dict:
    return {
        "kind": kind,
        "severity": severity,
        "agent": agent,
        "evidence": redact(evidence),
        "suggestion": redact(suggestion),
        "apply_now": redact(apply_now),
    }


# ---------------------------------------------------------------------------
# Pure signal detection over normalized events
# ---------------------------------------------------------------------------


def collect_signals(events: list[dict]) -> list[dict]:
    """Return a list of signal dicts from normalized event dicts.

    The input events must each contain at least these keys:

    * agent (str)
    * role (str)
    * text (str)
    * tokens_in (int)
    * tokens_out (int)
    * t (float seconds)
    * tool (str|None)
    * tool_path (str|None)
    * tool_error (bool)
    * permission_requested (bool)
    """
    signals: list[dict] = []
    if not events:
        return signals

    # Sort by time for all span/streak logic.
    sorted_events = sorted(events, key=lambda e: _coerce_float(e.get("t")))

    # 1. Review rejection streak (pooled across rotated tier variants)
    streak_agent: str | None = None
    streak_texts: list[str] = []
    streak_variants: list[str] = []
    prior_coder: str | None = None
    for evt in sorted_events:
        agent = str(evt.get("agent") or "")
        text = str(evt.get("text") or "")
        if not _is_reviewer(agent):
            if _is_coder(agent):
                prior_coder = agent
            continue
        if _is_rejection(text):
            streak_agent = _family(agent)
            streak_texts.append(text)
            if agent not in streak_variants:
                streak_variants.append(agent)
        elif _is_approval(text):
            if len(streak_texts) >= 2 and streak_agent:
                complaint = streak_texts[-1]
                evidence = (
                    f"{len(streak_texts)} consecutive rejections from {streak_agent}; "
                    f"last complaint: {complaint[:200]}"
                )
                if len(streak_variants) > 1:
                    evidence += f"; variants: {', '.join(streak_variants)}"
                signals.append(
                    _signal(
                        kind="review_reject_streak",
                        severity="high",
                        agent=streak_agent,
                        evidence=evidence,
                        suggestion="Add the reviewer's repeated complaint to the coding agent prompt "
                        "as a pre-flight checklist item.",
                        apply_now=f"Put the reviewer's repeated complaint verbatim into the next "
                        f"just-code brief: {complaint[:400]}",
                    )
                )
                if prior_coder:
                    signals[-1]["evidence"] += f" | prior coder: {prior_coder}"
            streak_texts = []
            streak_variants = []
    # End-of-session streak (no approval after it).
    if len(streak_texts) >= 2 and streak_agent:
        complaint = streak_texts[-1]
        evidence = (
            f"{len(streak_texts)} consecutive rejections from {streak_agent}; "
            f"last complaint: {complaint[:200]}"
        )
        if len(streak_variants) > 1:
            evidence += f"; variants: {', '.join(streak_variants)}"
        sig = _signal(
            kind="review_reject_streak",
            severity="high",
            agent=streak_agent,
            evidence=evidence,
            suggestion="Add the reviewer's repeated complaint to the coding agent prompt "
            "as a pre-flight checklist item.",
            apply_now=f"Put the reviewer's repeated complaint verbatim into the next "
            f"just-code brief: {complaint[:400]}",
        )
        if prior_coder:
            sig["evidence"] += f" | prior coder: {prior_coder}"
        signals.append(sig)

    # 2. Long cycles per agent (active time, not wall clock)
    by_agent: dict[str, list[float]] = {}
    for evt in sorted_events:
        # Synthetic v2 tool events share their message timestamp; counting them
        # would only inflate the "across N events" evidence.
        if str(evt.get("role") or "") == "tool":
            continue
        agent = str(evt.get("agent") or "")
        t = _coerce_float(evt.get("t"))
        if agent and t >= 0:
            by_agent.setdefault(agent, []).append(t)
    for agent, times in by_agent.items():
        if len(times) < 2:
            continue
        times.sort()
        wall_clock = max(times) - min(times)
        active_time = sum(
            gap for gap in (t2 - t1 for t1, t2 in zip(times, times[1:]))
            if gap < IDLE_GAP_THRESHOLD_S
        )
        if active_time >= LONG_CYCLE_HIGH_S:
            severity = "high"
        elif active_time >= LONG_CYCLE_WARN_S:
            severity = "warn"
        else:
            continue
        signals.append(
            _signal(
                kind="long_cycle",
                severity=severity,
                agent=agent,
                evidence=f"{agent} active {active_time:.0f}s, wall {wall_clock:.0f}s "
                f"across {len(times)} events",
                suggestion="The prompt/task was too broad; split the MDU and add an explicit output contract.",
                apply_now=f"Narrow {agent}'s brief for the next delegation and require a concrete "
                "deliverable before it proceeds.",
            )
        )

    # 3. Token hotspots
    agent_tokens: dict[str, int] = {}
    total_tokens = 0
    for evt in sorted_events:
        agent = str(evt.get("agent") or "")
        if not agent:
            continue
        tk = _coerce_int(evt.get("tokens_in")) + _coerce_int(evt.get("tokens_out"))
        agent_tokens[agent] = agent_tokens.get(agent, 0) + tk
        total_tokens += tk
    if total_tokens == 0:
        # Note is added by the caller so it shows up in the JSON report.
        pass
    else:
        for agent, tk in agent_tokens.items():
            share = tk / total_tokens if total_tokens else 0.0
            if tk >= TOKEN_HOTSPOT_ABSOLUTE or (
                tk >= TOKEN_HOTSPOT_MIN and share >= TOKEN_HOTSPOT_SHARE
            ):
                signals.append(
                    _signal(
                        kind="token_hotspot",
                        severity="warn",
                        agent=agent,
                        evidence=f"{agent} used {tk:,} tokens ({share:.0%} of session)",
                        suggestion="Use a cheaper variant, a narrower brief, don't paste whole files, "
                        "and prefer grep/read snippets.",
                        apply_now=f"Give {agent} a narrower brief next time and pass relevant excerpts "
                        "instead of whole files.",
                    )
                )

    # 4. Repeated tool errors (family-pooled across tier variants)
    error_counts: dict[tuple[str, str | None], int] = {}
    for evt in sorted_events:
        agent = _family(str(evt.get("agent") or ""))
        tool = evt.get("tool")
        tool = str(tool) if tool else None
        if evt.get("tool_error") and tool:
            error_counts[(agent, tool)] = error_counts.get((agent, tool), 0) + 1
    for (agent, tool), count in error_counts.items():
        if count >= REPEATED_ERROR_THRESHOLD:
            signals.append(
                _signal(
                    kind="repeated_tool_error",
                    severity="warn",
                    agent=agent,
                    evidence=f"{agent} hit {count} errors on tool {tool}",
                    suggestion="The prompt should include the working command/path or a fallback.",
                    apply_now=f"Pre-flight the {tool} command/path for {agent} in the next brief "
                    "and include a fallback.",
                )
            )

    # 5. Permission thrash
    permission_count = sum(
        1 for evt in sorted_events if evt.get("permission_requested")
    )
    if permission_count >= PERMISSION_THRESHOLD:
        signals.append(
            _signal(
                kind="permission_thrash",
                severity="warn",
                agent="session",
                evidence=f"{permission_count} permission requests in the session",
                suggestion="Add a permission allow for the repeated path/tool in the agent definition "
                "(suggest, don't edit).",
                apply_now="Review the most frequent permission target and add an explicit allow "
                "to the agent definition after user confirmation.",
            )
        )

    # 6. Context reread (family-pooled across tier variants)
    read_counts: dict[tuple[str, str | None], int] = {}
    for evt in sorted_events:
        agent = _family(str(evt.get("agent") or ""))
        tool = evt.get("tool")
        tool = str(tool) if tool else ""
        path = evt.get("tool_path")
        path = str(path) if path else ""
        if "read" in tool.lower() or "grep" in tool.lower():
            key = (agent, path or tool)
            read_counts[key] = read_counts.get(key, 0) + 1
    for (agent, target), count in read_counts.items():
        if count >= CONTEXT_REREAD_THRESHOLD and target:
            signals.append(
                _signal(
                    kind="context_reread",
                    severity="warn",
                    agent=agent,
                    evidence=f"{agent} read/grepped {target} {count} times",
                    suggestion="Tell the agent to read once and keep notes; pass the relevant excerpt "
                    "in the brief.",
                    apply_now=f"Pass the relevant excerpt for {target} in {agent}'s next brief "
                    "and ask it to take notes before acting.",
                )
            )

    # 7. QA fail repeat (family-pooled across tier variants)
    qa_fails: dict[str, int] = {}
    for evt in sorted_events:
        agent = str(evt.get("agent") or "")
        text = str(evt.get("text") or "")
        if _is_qa(agent) and QA_FAIL_VERDICT.search(text):
            family = _family(agent)
            qa_fails[family] = qa_fails.get(family, 0) + 1
    for agent, count in qa_fails.items():
        if count >= QA_FAIL_THRESHOLD:
            signals.append(
                _signal(
                    kind="qa_fail_repeat",
                    severity="high",
                    agent=agent,
                    evidence=f"{agent} reported FAIL {count} times",
                    suggestion="Add the failing assertion to the test-agent brief before re-deploy.",
                    apply_now="Route the latest FAIL details to test-agent in the next loop so the "
                    "regression is asserted before code changes.",
                )
            )

    # 8. Stalled subagent
    prev_t: float | None = None
    for evt in sorted_events:
        t = _coerce_float(evt.get("t"))
        if prev_t is not None and t - prev_t >= STALL_HIGH_S:
            agent = str(evt.get("agent") or "")
            signals.append(
                _signal(
                    kind="stalled_subagent",
                    severity="warn",
                    agent=agent,
                    evidence=f"{t - prev_t:.0f}s gap before event from {agent}",
                    suggestion="Decompose; the watchdog should have fired earlier.",
                    apply_now="Mention the stall in the next orchestrator loop and shorten the "
                    "subagent leash (earlier check-in or smaller scope).",
                )
            )
        prev_t = t

    signals.extend(_cost_signals(sorted_events))
    return signals


def _is_bulk_agent(agent: str) -> bool:
    name = agent.lower()
    # Tier rotation: -mid/-pro/-premium are deliberately expensive; -free is a
    # cheap rotation tier and still counts as a bulk role.
    if name.endswith(("-mid", "-pro", "-premium")):
        return False
    return _family(name) in BULK_AGENTS


def _cost_signals(events: list[dict]) -> list[dict]:
    """Cache misses, fat prompts, and flagship models on bulk roles."""
    found: list[dict] = []
    misses: dict[str, int] = {}
    long_counts: dict[str, int] = {}
    long_high: dict[str, int] = {}
    expensive: dict[str, str] = {}
    for evt in events:
        raw_agent = str(evt.get("agent") or "") or "session"
        agent = _family(raw_agent)
        tokens_in = _coerce_int(evt.get("tokens_in"))
        cache_read = _coerce_int(evt.get("cache_read"))
        prompt = tokens_in + cache_read
        model = str(evt.get("model") or "")
        if cache_read <= CACHE_MISS_READ_MAX and tokens_in >= CACHE_MISS_INPUT_MIN:
            misses[agent] = misses.get(agent, 0) + 1
        if prompt >= LONG_CONTEXT_TOKENS:
            long_counts[agent] = long_counts.get(agent, 0) + 1
        if prompt >= LONG_CONTEXT_HIGH_TOKENS:
            long_high[agent] = long_high.get(agent, 0) + 1
        # Raw name, not the pooled family: _is_bulk_agent excludes the
        # -mid/-pro/-premium tiers itself, and _family() would strip the
        # suffix before that check could see it.
        if _is_bulk_agent(raw_agent) and any(flag in model for flag in FLAGSHIP_MODELS):
            expensive[raw_agent] = model
    for agent, count in misses.items():
        found.append(
            _signal(
                kind="cache_miss",
                severity="high" if count >= 3 else "warn",
                agent=agent,
                evidence=f"{agent} had {count} cache miss(es): cache.read <= {CACHE_MISS_READ_MAX} "
                f"and input >= {CACHE_MISS_INPUT_MIN}",
                suggestion="A cache miss rebills the transcript. Compact or start a new session "
                "before the next delegate.",
                apply_now=f"Do not delegate from {agent} after a cache miss. Compact, or start a "
                "new session from the resume block.",
            )
        )
    for agent, count in long_counts.items():
        high = long_high.get(agent, 0)
        found.append(
            _signal(
                kind="long_context",
                severity="high" if high else "warn",
                agent=agent,
                evidence=f"{agent} had {count} turn(s) with prompt >= {LONG_CONTEXT_TOKENS}"
                + (f", {high} of them >= {LONG_CONTEXT_HIGH_TOKENS}" if high else ""),
                suggestion="Compact at 140000 after durable artifacts exist. Prompts >= 200000 "
                "on grok-4.7 are billed at 2x.",
                apply_now=f"Cap {agent} before 140000 prompt tokens. Do not continue a child "
                "that is already over the cliff.",
            )
        )
    for agent, model in expensive.items():
        found.append(
            _signal(
                kind="expensive_model",
                severity="warn",
                agent=agent,
                evidence=f"{agent} ran on {model}, a flagship model, for a bulk role",
                suggestion="Use grok-build-0.1 or the Go default for bulk coding, test, review, "
                "QA, devops, research, and UI. Keep grok-4.7 for the orchestrator, architecture, "
                "and mid/pro roles.",
                apply_now=f"Next brief for this work names the cheaper agent, not {agent} on {model}.",
            )
        )
    return found


def signals_from_manifest(manifest: dict) -> list[dict]:
    """Return signals derived from a run manifest dict.

    Detects:
    * ``fix_iterations >= 2`` -> ``fix_loop``
    * same phase name with outcome ``fail`` >= 2 -> ``phase_fail_streak``
    """
    signals: list[dict] = []
    fix_iterations = _coerce_int(manifest.get("fix_iterations"))
    if fix_iterations >= 2:
        notes = ""
        for phase in manifest.get("phases", []):
            if isinstance(phase, dict) and phase.get("outcome") == "fail":
                note = phase.get("notes") or ""
                if note:
                    notes += f" {note}"
        signals.append(
            _signal(
                kind="fix_loop",
                severity="high",
                agent="session",
                evidence=f"manifest fix_iterations={fix_iterations}",
                suggestion="Tighten the coding prompt with the failure notes.",
                apply_now=f"Fold these failure notes into the next just-code brief: {notes.strip()[:400]}"
                if notes.strip()
                else "Tighten the coding brief before the next delegation.",
            )
        )

    phase_fail_counts: dict[str, int] = {}
    for phase in manifest.get("phases", []):
        if not isinstance(phase, dict):
            continue
        if phase.get("outcome") == "fail":
            name = str(phase.get("phase") or "")
            if name:
                phase_fail_counts[name] = phase_fail_counts.get(name, 0) + 1
    for phase, count in phase_fail_counts.items():
        if count >= 2:
            signals.append(
                _signal(
                    kind="phase_fail_streak",
                    severity="high",
                    agent=phase,
                    evidence=f"phase '{phase}' failed {count} times",
                    suggestion="This phase has a recurring failure pattern; add a pre-flight checklist "
                    "or decompose it.",
                    apply_now=f"Add a phase-specific checklist for '{phase}' to the next brief and "
                    "verify prerequisites before delegating.",
                )
            )

    return signals


# ---------------------------------------------------------------------------
# Live log collectors (best-effort)
# ---------------------------------------------------------------------------


def _normalize_event(
    agent: str,
    role: str,
    text: str,
    t: float,
    tokens_in: int = 0,
    tokens_out: int = 0,
    tool: str | None = None,
    tool_path: str | None = None,
    tool_error: bool = False,
    permission_requested: bool = False,
    cache_read: int = 0,
    model: str = "",
) -> dict:
    return {
        "agent": agent,
        "role": role,
        "text": text,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cache_read": cache_read,
        "model": model,
        "t": t,
        "tool": tool,
        "tool_path": tool_path,
        "tool_error": tool_error,
        "permission_requested": permission_requested,
    }


def _opencode_db_path() -> Path:
    """Default OpenCode sqlite store path (overridable for tests)."""
    return Path.home() / ".local" / "share" / "opencode" / "opencode.db"


def _to_epoch_ms(value: object) -> float:
    """Coerce an epoch-seconds, epoch-ms, or ISO-8601 timestamp to epoch ms."""
    if value is None or isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        num = float(value)
    else:
        text = str(value).strip()
        if not text:
            return 0.0
        if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", text):
            num = float(text)
        else:
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                return 0.0
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp() * 1000.0
    if num <= 0:
        return 0.0
    return num * 1000.0 if num < 1e11 else num


def _ms_to_iso(ms: float | None) -> str | None:
    if not ms or ms <= 0:
        return None
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _time_range(events: list[dict]) -> dict:
    """Min/max positive event time as UTC ISO-8601 (nulls when absent)."""
    times = [t for t in (_coerce_float(e.get("t")) for e in events) if t > 0]
    if not times:
        return {"oldest": None, "newest": None}
    return {
        "oldest": _ms_to_iso(min(times) * 1000.0),
        "newest": _ms_to_iso(max(times) * 1000.0),
    }


def _newest_row(rows: list[sqlite3.Row]) -> dict | None:
    """Pick the freshest row in Python; no SQL ORDER BY on an untyped column."""
    newest: dict | None = None
    for row in rows:
        ms = _to_epoch_ms(row["time_updated"])
        if newest is None or ms > newest["newest_ms"]:
            newest = {"id": row["id"], "newest_ms": ms}
    return newest


def _store_freshness(cur: sqlite3.Cursor, cwd: str) -> dict[str, dict | None]:
    """Freshest session per store: v1 ``session``, v2 ``session_v2``."""
    freshness: dict[str, dict | None] = {}
    for store, table in (("v1", "session"), ("v2", "session_v2")):
        try:
            cur.execute(
                f"SELECT id, time_updated FROM {table} "
                "WHERE directory = ? OR ? LIKE directory || '%'",
                (cwd, cwd),
            )
            freshness[store] = _newest_row(cur.fetchall())
        except sqlite3.Error:
            freshness[store] = None
    return freshness


def _select_store(freshness: dict[str, dict | None]) -> str:
    """v2 is the live schema; v1 wins only when clearly fresher (> EPS_MS)."""
    v1, v2 = freshness["v1"], freshness["v2"]
    if v1 is None and v2 is None:
        return ""
    if v1 is None:
        return "v2"
    if v2 is None:
        return "v1"
    if v1["newest_ms"] > v2["newest_ms"] + EPS_MS:
        return "v1"
    return "v2"


def _session_row(
    cur: sqlite3.Cursor, table: str, session_id: str, cwd: str
) -> sqlite3.Row | None:
    """Look an id up with the cwd prefix predicate so ancestor dirs match."""
    try:
        cur.execute(
            f"SELECT id, directory, parent_id, time_updated FROM {table} "
            "WHERE id = ? AND (directory = ? OR ? LIKE directory || '%') LIMIT 1",
            (session_id, cwd, cwd),
        )
        return cur.fetchone()
    except sqlite3.Error:
        return None


def _wrong_directory_notes(
    cur: sqlite3.Cursor, session_id: str, cwd: str
) -> list[str]:
    """Explain why a supplied session id matched neither store, with recovery."""
    notes: list[str] = []
    table = ""
    found: sqlite3.Row | None = None
    for candidate in ("session", "session_v2"):
        try:
            cur.execute(
                f"SELECT id, directory, parent_id FROM {candidate} WHERE id = ? LIMIT 1",
                (session_id,),
            )
            found = cur.fetchone()
        except sqlite3.Error:
            found = None
        if found is not None:
            table = candidate
            break
    if found is None:
        return [f"session id {session_id} not found in OpenCode stores"]

    directory = found["directory"] or ""
    notes.append(f"session id {session_id} belongs to {directory}, not {cwd}")

    parent_id = found["parent_id"]
    if parent_id and _session_row(cur, table, parent_id, cwd) is not None:
        notes.append(f"propose parent as root: rerun with --session-id {parent_id}")

    child_count = 0
    try:
        cur.execute(
            f"SELECT COUNT(*) FROM {table} WHERE parent_id = ? "
            "AND (directory = ? OR ? LIKE directory || '%')",
            (session_id, cwd, cwd),
        )
        count_row = cur.fetchone()
        child_count = int(count_row[0]) if count_row else 0
    except sqlite3.Error:
        child_count = 0
    if child_count:
        notes.append(
            f"supplied id has {child_count} child session(s) under {cwd}; "
            "rerun without --session-id (freshest-store selection) "
            f"or with --cwd {directory}"
        )
    return notes


def _collect_opencode(
    cwd: str,
    session_id: str | None = None,
    db_path: Path | None = None,
) -> tuple[list[dict], dict, list[str]]:
    """Read OpenCode sqlite logs from ~/.local/share/opencode/opencode.db."""
    events: list[dict] = []
    notes: list[str] = []
    info: dict = {
        "harness": "opencode",
        "session_id": "",
        "cwd": cwd,
        "store": "",
        "time_range": {"oldest": None, "newest": None},
    }

    def _done() -> tuple[list[dict], dict, list[str]]:
        info["time_range"] = _time_range(events)
        return events, info, notes

    resolved_db = Path(db_path) if db_path is not None else _opencode_db_path()
    if not resolved_db.is_file():
        notes.append(f"OpenCode db not found: {resolved_db}")
        return _done()
    db_path = resolved_db

    # Simpler: re-open and fetch parts per message.
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        store = ""
        if session_id:
            # The id pins the tree; no cross-store freshness comparison runs.
            if _session_row(cur, "session", session_id, cwd) is not None:
                store = "v1"
            elif _session_row(cur, "session_v2", session_id, cwd) is not None:
                store = "v2"
            if not store:
                notes.extend(_wrong_directory_notes(cur, session_id, cwd))
                conn.close()
                return _done()
            root_id = session_id
        else:
            freshness = _store_freshness(cur, cwd)
            info["store_candidates"] = [
                {
                    "store": name,
                    "id": freshness[name]["id"] if freshness[name] else None,
                    "newest": (
                        _ms_to_iso(freshness[name]["newest_ms"])
                        if freshness[name]
                        else None
                    ),
                }
                for name in ("v1", "v2")
            ]
            store = _select_store(freshness)
            if not store:
                notes.append("No matching OpenCode session for cwd")
                conn.close()
                return _done()
            if freshness["v1"] is not None and freshness["v2"] is not None:
                other = "v1" if store == "v2" else "v2"
                notes.append(
                    f"store selected: {store} "
                    f"(newest {_ms_to_iso(freshness[store]['newest_ms']) or 'unknown'}; "
                    f"{other} newest "
                    f"{_ms_to_iso(freshness[other]['newest_ms']) or 'unknown'})"
                )
            root_id = freshness[store]["id"]

        if store == "v2":
            v2_events, v2_info, v2_notes = _collect_opencode_v2(conn, cwd, session_id)
            notes.extend(v2_notes)
            info.update(v2_info)
            info["store"] = "v2"
            events = v2_events
            conn.close()
            return _done()

        info["store"] = "v1"
        # If this session has parent_id, use parent.
        cur.execute("SELECT parent_id FROM session WHERE id = ?", (root_id,))
        prow = cur.fetchone()
        if prow and prow["parent_id"]:
            root_id = prow["parent_id"]
        info["session_id"] = root_id
        cur.execute(
            "SELECT id, agent FROM session WHERE id = ? OR parent_id = ?",
            (root_id, root_id),
        )
        session_agents = {r["id"]: (r["agent"] or "") for r in cur.fetchall()}

        cur.execute(
            "SELECT id, session_id, data FROM message WHERE session_id IN "
            f"({','.join('?' * len(session_agents))}) ORDER BY id",
            tuple(session_agents.keys()),
        )
        messages = [dict(r) for r in cur.fetchall()]
        for msg_row in messages:
            try:
                msg = json.loads(msg_row["data"] or "{}")
            except json.JSONDecodeError:
                continue
            mid = msg_row["id"]
            agent_name = msg.get("agent") or session_agents.get(msg_row["session_id"], "")
            role = msg.get("role") or ""
            tokens = msg.get("tokens") or {}
            tokens_in = _coerce_int(tokens.get("input"))
            tokens_out = _coerce_int(tokens.get("output"))
            cache = tokens.get("cache") or {}
            cache_read = _coerce_int(cache.get("read") if isinstance(cache, dict) else 0)
            model_field = msg.get("model") or {}
            model = ""
            if isinstance(model_field, dict):
                model = str(model_field.get("id") or "")
            elif model_field:
                model = str(model_field)
            created_ms = msg.get("time", {}).get("created") if isinstance(
                msg.get("time"), dict
            ) else None
            t = _coerce_float(created_ms) / 1000.0 if created_ms else 0.0

            cur.execute("SELECT data FROM part WHERE message_id = ? ORDER BY id", (mid,))
            parts = []
            for (pdata,) in cur.fetchall():
                try:
                    parts.append(json.loads(pdata or "{}"))
                except json.JSONDecodeError:
                    parts.append({})
            text = " ".join(_extract_text(p) for p in parts)
            tool = None
            tool_path = None
            tool_error = False
            permission_requested = False
            for part in parts:
                ptype = part.get("type") or ""
                name = part.get("name") or ""
                state = part.get("state") or ""
                if ptype == "tool":
                    tool = name
                    args = part.get("arguments") or part.get("input") or {}
                    if isinstance(args, dict):
                        for path_key in ("path", "filePath", "file", "command"):
                            val = args.get(path_key)
                            if val:
                                tool_path = str(val)
                                break
                    if state in ("error", "failed"):
                        tool_error = True
                    if "permission" in name.lower() or state == "permission_requested":
                        permission_requested = True
                elif state == "permission_requested":
                    permission_requested = True
            events.append(
                _normalize_event(
                    agent=agent_name,
                    role=role,
                    text=text,
                    t=t,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cache_read=cache_read,
                    model=model,
                    tool=tool,
                    tool_path=tool_path,
                    tool_error=tool_error,
                    permission_requested=permission_requested,
                )
            )
        if not any(
            _coerce_int(evt.get("tokens_in")) or _coerce_int(evt.get("cache_read"))
            for evt in events
        ):
            v2_events, v2_info, v2_notes = _collect_opencode_v2(conn, cwd, session_id)
            notes.extend(v2_notes)
            if v2_events:
                events = v2_events
                info.update(v2_info)
                info["store"] = "v2"
                notes.append("store selected: v2 (v1 tree had no token data)")
        conn.close()
    except Exception as exc:
        notes.append(f"OpenCode collector error: {exc}")

    return _done()


def _v2_tool_target(name: str, tool_input: object) -> str | None:
    """Pick the detector-relevant target of a v2 tool part's ``state.input``.

    ``tool_path`` has exactly one consumer, ``context_reread`` (detector 6), and
    grep inputs carry a ``pattern`` instead of a ``path``.  Preferring the
    pattern keeps N distinct greps from pooling under one ``(agent, "grep")``
    key and false-firing at threshold 4.
    """
    if not isinstance(tool_input, dict):
        return None
    if "grep" in name.lower():
        keys = ("pattern", "path", "filePath", "file", "command")
    else:
        keys = ("path", "filePath", "file", "command")
    for key in keys:
        val = tool_input.get(key)
        if val:
            return str(val)
    return None


def _v2_extract_message(msg: dict) -> tuple[str, list[dict]]:
    """Split a v2 ``session_message.data`` row into text and tool parts.

    Returns ``(text, finalized_tool_parts)``.  Only ``text`` parts contribute
    text: ``reasoning`` parts are chain-of-thought and must never count as
    verdicts (v2 separates CoT structurally, so the exclusion happens here
    instead of via ``_strip_think`` after the fact).  Tool parts that are still
    ``running``/``streaming`` and parts without a non-empty ``name`` are
    dropped: an un-finalized call has no outcome worth counting.
    """
    content = msg.get("content")
    if not isinstance(content, list):
        return "", []
    pieces: list[str] = []
    tool_parts: list[dict] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        ptype = part.get("type")
        if ptype == "text":
            text = part.get("text")
            if isinstance(text, str):
                pieces.append(text)
        elif ptype == "tool":
            name = part.get("name")
            if not isinstance(name, str) or not name:
                continue
            state = part.get("state")
            status = state.get("status") if isinstance(state, dict) else None
            if status in ("running", "streaming"):
                continue
            tool_parts.append(part)
    return " ".join(pieces), tool_parts


def _v2_tool_event(agent: str, t: float, part: dict) -> dict | None:
    """Build one synthetic ``role="tool"`` event from a finalized tool part.

    Returns ``None`` when the part is not countable (in-flight status, no
    name).  Tokens stay on the message event so cost signals are not double
    billed; ``permission_requested`` is always False on v2 (D-5).
    """
    if not isinstance(part, dict):
        return None
    name = part.get("name")
    if not isinstance(name, str) or not name:
        return None
    state = part.get("state")
    state = state if isinstance(state, dict) else {}
    status = state.get("status")
    if status in ("running", "streaming"):
        return None
    return _normalize_event(
        agent=agent,
        role="tool",
        text="",
        t=t,
        tool=name,
        tool_path=_v2_tool_target(name, state.get("input")),
        tool_error=status in ("error", "failed"),
        permission_requested=False,
    )


def _collect_opencode_v2(
    conn: sqlite3.Connection, cwd: str, session_id: str | None
) -> tuple[list[dict], dict, list[str]]:
    """Read assistant turns from session_v2 / session_message when present."""
    events: list[dict] = []
    notes: list[str] = []
    info: dict = {"harness": "opencode", "session_id": session_id or "", "cwd": cwd}
    # Capability constants: text and tool extraction are on for v2, permission
    # extraction is not (the permission table is project-scoped).  The counts
    # are filled in as rows are interpreted.
    extraction = {
        "messages": 0,
        "text_events": 0,
        "tool_events": 0,
        "text": True,
        "tools": True,
        "permission": False,
    }
    info["v2_extraction"] = extraction
    try:
        cur = conn.cursor()
        if session_id:
            cur.execute(
                "SELECT id FROM session_v2 WHERE id = ? "
                "AND (directory = ? OR ? LIKE directory || '%') LIMIT 1",
                (session_id, cwd, cwd),
            )
            row = cur.fetchone()
            root_id = row["id"] if row else ""
        else:
            cur.execute(
                "SELECT id, time_updated FROM session_v2 "
                "WHERE directory = ? OR ? LIKE directory || '%'",
                (cwd, cwd),
            )
            newest = _newest_row(cur.fetchall())
            root_id = newest["id"] if newest else ""
        if not root_id:
            return events, info, notes
        cur.execute("SELECT parent_id FROM session_v2 WHERE id = ?", (root_id,))
        prow = cur.fetchone()
        if prow and prow["parent_id"]:
            root_id = prow["parent_id"]
        info["session_id"] = root_id
        cur.execute(
            "SELECT id, agent FROM session_v2 WHERE id = ? OR parent_id = ?",
            (root_id, root_id),
        )
        session_agents = {r["id"]: (r["agent"] or "") for r in cur.fetchall()}
        cur.execute(
            "SELECT session_id, data, time_created FROM session_message "
            "WHERE session_id IN "
            f"({','.join('?' * len(session_agents))}) AND type = 'assistant' "
            "ORDER BY time_created",
            tuple(session_agents.keys()),
        )
        for srow in cur.fetchall():
            try:
                msg = json.loads(srow["data"] or "{}")
            except json.JSONDecodeError:
                continue
            if not isinstance(msg, dict):
                continue
            tokens = msg.get("tokens") or {}
            if not isinstance(tokens, dict):
                tokens = {}
            cache = tokens.get("cache") or {}
            model_field = msg.get("model") or {}
            model = ""
            if isinstance(model_field, dict):
                model = str(model_field.get("id") or "")
            elif model_field:
                model = str(model_field)
            created = srow["time_created"]
            t = _coerce_float(created) / 1000.0 if created else 0.0
            agent = str(
                msg.get("agent") or session_agents.get(srow["session_id"], "")
            )
            text, tool_parts = _v2_extract_message(msg)
            extraction["messages"] += 1
            if text.strip():
                extraction["text_events"] += 1
            events.append(
                _normalize_event(
                    agent=agent,
                    role="assistant",
                    text=text,
                    t=t,
                    tokens_in=_coerce_int(tokens.get("input")),
                    tokens_out=_coerce_int(tokens.get("output")),
                    cache_read=_coerce_int(cache.get("read") if isinstance(cache, dict) else 0),
                    model=model,
                )
            )
            # One synthetic event per finalized tool part, in content order;
            # same-t ordering is stable in collect_signals.
            for part in tool_parts:
                tool_event = _v2_tool_event(agent, t, part)
                if tool_event is None:
                    continue
                events.append(tool_event)
                extraction["tool_events"] += 1
        if events:
            notes.append(V2_PERMISSION_NOTE)
            if extraction["messages"] > 0 and extraction["text_events"] == 0:
                notes.append(
                    V2_TEXT_MISSING_NOTE.format(count=extraction["messages"])
                )
    except sqlite3.Error as exc:
        notes.append(f"OpenCode v2 messages unavailable: {exc}")
    return events, info, notes


def _collect_grok(cwd: str, session_id: str | None = None) -> tuple[list[dict], dict, list[str]]:
    """Read Grok Build session logs from ~/.grok/sessions/<urlencoded-cwd>/."""
    events: list[dict] = []
    notes: list[str] = []
    info: dict = {"harness": "grok", "session_id": "", "cwd": cwd}
    base = Path.home() / ".grok" / "sessions" / quote(cwd, safe="")
    if not base.is_dir():
        notes.append(f"Grok sessions dir not found: {base}")
        return events, info, notes

    try:
        summaries = sorted(
            [p for p in base.glob("*/summary.json") if p.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not summaries:
            notes.append("No Grok session summaries found")
            return events, info, notes
        if session_id:
            chosen = next((s for s in summaries if s.parent.name == session_id), None)
            if not chosen:
                notes.append(f"Grok session {session_id} not found")
                return events, info, notes
        else:
            chosen = summaries[0]
        sess_dir = chosen.parent
        info["session_id"] = sess_dir.name
        summary = json.loads(chosen.read_text(encoding="utf-8"))
        agent_name = summary.get("agent_name") or "agent"

        events_path = sess_dir / "events.jsonl"
        if events_path.is_file():
            for line in events_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                etype = event.get("type") or ""
                ts = _coerce_float(event.get("ts"))
                tool = None
                tool_path = None
                tool_error = False
                permission_requested = False
                text = ""
                if etype == "tool_started":
                    tool = event.get("tool_name") or event.get("tool") or ""
                    args = event.get("arguments") or event.get("input") or {}
                    if isinstance(args, dict):
                        for key in ("path", "filePath", "file", "command"):
                            val = args.get(key)
                            if val:
                                tool_path = str(val)
                                break
                    text = f"tool_started {tool}"
                elif etype == "tool_completed":
                    tool = event.get("tool_name") or event.get("tool") or ""
                    if event.get("error") or event.get("outcome") in ("error", "failed"):
                        tool_error = True
                    text = f"tool_completed {tool}"
                elif etype in ("permission_requested", "permission_asked"):
                    permission_requested = True
                    text = "permission_requested"
                elif etype in ("turn_started", "turn_ended"):
                    text = etype
                elif etype == "phase_changed":
                    text = f"phase_changed {event.get('phase', '')}"
                else:
                    text = etype
                events.append(
                    _normalize_event(
                        agent=agent_name,
                        role="assistant" if etype else "",
                        text=text,
                        t=ts,
                        tool=tool,
                        tool_path=tool_path,
                        tool_error=tool_error,
                        permission_requested=permission_requested,
                    )
                )
    except Exception as exc:
        notes.append(f"Grok collector error: {exc}")

    return events, info, notes


def _collect_claude(cwd: str, session_id: str | None = None) -> tuple[list[dict], dict, list[str]]:
    """Read Claude Code logs from ~/.claude/projects/<cwd-with-dashes>/."""
    events: list[dict] = []
    notes: list[str] = []
    info: dict = {"harness": "claude", "session_id": "", "cwd": cwd}
    encoded = cwd.lstrip("/").replace("/", "-")
    if cwd.startswith("/"):
        encoded = "-" + encoded
    base = Path.home() / ".claude" / "projects" / encoded
    if not base.is_dir():
        notes.append(f"Claude projects dir not found: {base}")
        return events, info, notes

    try:
        files = sorted(base.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            notes.append("No Claude session files found")
            return events, info, notes
        if session_id:
            chosen = next((f for f in files if f.stem == session_id), None)
            if not chosen:
                notes.append(f"Claude session {session_id} not found")
                return events, info, notes
        else:
            chosen = files[0]
        info["session_id"] = chosen.stem
        for line in chosen.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            rtype = record.get("type") or ""
            agent = "claude" if rtype == "assistant" else "user"
            text = _extract_text(record)
            ts = _coerce_float(record.get("timestamp"))
            usage = record.get("message", {}).get("usage") or {}
            tokens_in = _coerce_int(usage.get("input_tokens"))
            tokens_out = _coerce_int(usage.get("output_tokens"))
            model = record.get("message", {}).get("model") or ""
            events.append(
                _normalize_event(
                    agent=agent,
                    role=rtype,
                    text=text,
                    t=ts,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    tool=model,
                    tool_path=None,
                    tool_error=False,
                    permission_requested=False,
                )
            )
    except Exception as exc:
        notes.append(f"Claude collector error: {exc}")

    return events, info, notes


def _compute_metrics(events: list[dict]) -> dict:
    agents: dict[str, dict] = {}
    review_rejections = 0
    for evt in events:
        # Synthetic v2 tool events are per-call bookkeeping for tool detectors,
        # not assistant messages: keep per-agent counts, token sums and
        # durations tied to real message events.
        if str(evt.get("role") or "") == "tool":
            continue
        agent = str(evt.get("agent") or "")
        if not agent:
            continue
        if agent not in agents:
            agents[agent] = {
                "name": agent,
                "messages": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "duration_s": 0,
                "times": [],
            }
        agents[agent]["messages"] += 1
        agents[agent]["tokens_in"] += _coerce_int(evt.get("tokens_in"))
        agents[agent]["tokens_out"] += _coerce_int(evt.get("tokens_out"))
        t = _coerce_float(evt.get("t"))
        if t > 0:
            agents[agent]["times"].append(t)
        if _is_reviewer(agent) and _is_rejection(str(evt.get("text") or "")):
            review_rejections += 1

    agent_list = []
    for data in agents.values():
        times = data.pop("times")
        data["duration_s"] = int(max(times) - min(times)) if len(times) >= 2 else 0
        agent_list.append(data)
    return {"agents": agent_list, "review_rejections": review_rejections}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _find_script() -> Path | None:
    """Return the first available session_signals.py path for the prompt."""
    candidates = [
        Path(__file__).resolve(),
        Path.home() / ".config" / "opencode" / "skills" / "session-introspect" / "scripts" / "session_signals.py",
        Path.home() / ".grok" / "skills" / "session-introspect" / "scripts" / "session_signals.py",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _select_harness(
    results: list[tuple[str, list[dict], dict, list[str]]],
) -> tuple[str, list[dict], dict, list[str]]:
    """Pick the first harness that produced events or a session id.

    Each result is (name, events, info, notes). When no harness matches, the
    returned notes contain the accumulated per-harness misses plus a summary
    line.
    """
    misses: list[str] = []
    for name, ev, inf, nt in results:
        if ev or inf.get("session_id"):
            return name, ev, inf, list(nt)
        misses.extend(nt)
    misses.append("No log source matched (tried opencode, grok, claude)")
    return "", [], {"harness": "", "session_id": ""}, misses


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract improvement signals from the current session logs."
    )
    parser.add_argument("--cwd", default=os.getcwd(), help="working directory")
    parser.add_argument("--session-id", help="specific session id")
    parser.add_argument(
        "--harness",
        choices=["auto", "opencode", "grok", "claude"],
        default="auto",
        help="which CLI logs to read",
    )
    parser.add_argument("--manifest", help="optional run manifest JSON file")
    args = parser.parse_args(argv)

    cwd = os.path.abspath(args.cwd)
    notes: list[str] = []
    events: list[dict] = []
    info: dict = {"harness": "", "session_id": "", "cwd": cwd}

    # Manifest-derived signals first (independent of logs).
    manifest_signals: list[dict] = []
    if args.manifest:
        try:
            manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
            manifest_signals.extend(signals_from_manifest(manifest))
        except Exception as exc:
            notes.append(f"manifest error: {exc}")

    # Live log collection.
    harness = args.harness
    if harness == "auto":
        results = [
            (name, *collector(cwd, args.session_id))
            for name, collector in [
                ("opencode", _collect_opencode),
                ("grok", _collect_grok),
                ("claude", _collect_claude),
            ]
        ]
        selected, events, sel_info, notes = _select_harness(results)
        harness = selected
        if selected:
            info = sel_info
    else:
        collector = {
            "opencode": _collect_opencode,
            "grok": _collect_grok,
            "claude": _collect_claude,
        }[harness]
        events, info, notes = collector(cwd, args.session_id)

    info["harness"] = harness

    signals = collect_signals(events)
    signals.extend(manifest_signals)

    metrics = _compute_metrics(events)
    if metrics["agents"] and all(
        a["tokens_in"] == 0 and a["tokens_out"] == 0 for a in metrics["agents"]
    ):
        notes.append("token fields were empty in collected logs")

    result = {
        "harness": info.get("harness", ""),
        "session_id": info.get("session_id", ""),
        "cwd": info.get("cwd", cwd),
        "signals": signals,
        "metrics": metrics,
        "notes": notes,
        "info": info,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
