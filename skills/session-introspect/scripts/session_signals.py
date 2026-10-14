#!/usr/bin/env python3
"""Extract improvement signals from OpenCode, Grok, or Claude session logs.

Pure-stdlib CLI and importable functions.  Designed to be invoked by the
``introspector`` agent after an MDU (or any task) to turn recent session
evidence into agent-definition suggestions without ever editing definitions
or source code.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from pathlib import Path
from urllib.parse import quote

__all__ = ["collect_signals", "signals_from_manifest", "main"]

# ---------------------------------------------------------------------------
# Signal detection constants
# ---------------------------------------------------------------------------

REJECTION_PHRASES = [
    "request changes",
    "changes requested",
    "do not approve",
    "not approved",
]

APPROVAL_PHRASES = ["approve", "lgtm", "sign-off"]
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


def _contains_any(text: str, phrases: list[str]) -> bool:
    low = text.lower()
    return any(phrase in low for phrase in phrases)


def _is_rejection(text: str) -> bool:
    return _contains_any(_strip_think(text), REJECTION_PHRASES)


def _is_approval(text: str) -> bool:
    low = _strip_think(text).lower()
    return any(phrase in low for phrase in APPROVAL_PHRASES) and not _is_rejection(
        text
    )


def _is_reviewer(agent: str) -> bool:
    return any(sub in agent.lower() for sub in REVIEWER_SUBSTRINGS)


def _is_qa(agent: str) -> bool:
    return any(sub in agent.lower() for sub in QA_SUBSTRINGS)


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

    # 1. Review rejection streak
    streak_agent: str | None = None
    streak_texts: list[str] = []
    prior_coder: str | None = None
    for evt in sorted_events:
        agent = str(evt.get("agent") or "")
        text = str(evt.get("text") or "")
        if not _is_reviewer(agent):
            if _is_coder(agent):
                prior_coder = agent
            continue
        if _is_rejection(text):
            streak_agent = agent
            streak_texts.append(text)
        elif _is_approval(text):
            if len(streak_texts) >= 2 and streak_agent:
                complaint = streak_texts[-1]
                signals.append(
                    _signal(
                        kind="review_reject_streak",
                        severity="high",
                        agent=streak_agent,
                        evidence=f"{len(streak_texts)} consecutive rejections from {streak_agent}; "
                        f"last complaint: {complaint[:200]}",
                        suggestion="Add the reviewer's repeated complaint to the coding agent prompt "
                        "as a pre-flight checklist item.",
                        apply_now=f"Put the reviewer's repeated complaint verbatim into the next "
                        f"just-code brief: {complaint[:400]}",
                    )
                )
                if prior_coder:
                    signals[-1]["evidence"] += f" | prior coder: {prior_coder}"
            streak_texts = []
    # End-of-session streak (no approval after it).
    if len(streak_texts) >= 2 and streak_agent:
        complaint = streak_texts[-1]
        sig = _signal(
            kind="review_reject_streak",
            severity="high",
            agent=streak_agent,
            evidence=f"{len(streak_texts)} consecutive rejections from {streak_agent}; "
            f"last complaint: {complaint[:200]}",
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

    # 4. Repeated tool errors
    error_counts: dict[tuple[str, str | None], int] = {}
    for evt in sorted_events:
        agent = str(evt.get("agent") or "")
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

    # 6. Context reread
    read_counts: dict[tuple[str, str | None], int] = {}
    for evt in sorted_events:
        agent = str(evt.get("agent") or "")
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

    # 7. QA fail repeat
    qa_fails: dict[str, int] = {}
    for evt in sorted_events:
        agent = str(evt.get("agent") or "")
        text = str(evt.get("text") or "")
        if _is_qa(agent) and "FAIL" in text:
            qa_fails[agent] = qa_fails.get(agent, 0) + 1
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

    return signals


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
) -> dict:
    return {
        "agent": agent,
        "role": role,
        "text": text,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "t": t,
        "tool": tool,
        "tool_path": tool_path,
        "tool_error": tool_error,
        "permission_requested": permission_requested,
    }


def _collect_opencode(cwd: str, session_id: str | None = None) -> tuple[list[dict], dict, list[str]]:
    """Read OpenCode sqlite logs from ~/.local/share/opencode/opencode.db."""
    events: list[dict] = []
    notes: list[str] = []
    info: dict = {"harness": "opencode", "session_id": "", "cwd": cwd}
    db_path = Path.home() / ".local" / "share" / "opencode" / "opencode.db"
    if not db_path.is_file():
        notes.append(f"OpenCode db not found: {db_path}")
        return events, info, notes

    # Simpler: re-open and fetch parts per message.
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if session_id:
            cur.execute(
                "SELECT id FROM session WHERE id = ? AND directory = ? LIMIT 1",
                (session_id, cwd),
            )
        else:
            cur.execute(
                "SELECT id FROM session WHERE directory = ? OR ? LIKE directory || '%' "
                "ORDER BY time_updated DESC LIMIT 1",
                (cwd, cwd),
            )
        row = cur.fetchone()
        if not row:
            notes.append("No matching OpenCode session for cwd")
            return events, info, notes
        root_id = row["id"]
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
                    tool=tool,
                    tool_path=tool_path,
                    tool_error=tool_error,
                    permission_requested=permission_requested,
                )
            )
        conn.close()
    except Exception as exc:
        notes.append(f"OpenCode collector error: {exc}")

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
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
