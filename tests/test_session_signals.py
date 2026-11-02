"""Tests for the session-introspect skill script.

Imports the skill script via importlib so the tests do not depend on the
script living on ``sys.path`` under ``scripts/lib``.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPO_ROOT
    / "skills"
    / "session-introspect"
    / "scripts"
    / "session_signals.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("session_signals", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


session_signals = _load_module()


def _event(
    agent: str,
    text: str,
    t: float,
    *,
    role: str = "assistant",
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


# ---------------------------------------------------------------------------
# Review rejection streaks
# ---------------------------------------------------------------------------


def test_review_reject_streak_of_two_emits_signal_and_names_prior_coder() -> None:
    events = [
        _event("just-code", "implemented feature", t=1.0),
        _event("code-reviewer", "I request changes because tests are missing", t=2.0),
        _event("code-reviewer", "I still request changes; docs missing", t=3.0),
    ]
    signals = session_signals.collect_signals(events)
    kinds = [s["kind"] for s in signals]
    assert "review_reject_streak" in kinds
    sig = next(s for s in signals if s["kind"] == "review_reject_streak")
    assert sig["agent"] == "code-reviewer"
    assert "just-code" in sig["evidence"]


def test_single_rejection_does_not_emit_streak() -> None:
    events = [
        _event("just-code", "implemented feature", t=1.0),
        _event("code-reviewer", "I request changes", t=2.0),
    ]
    signals = session_signals.collect_signals(events)
    assert not any(s["kind"] == "review_reject_streak" for s in signals)


def test_approval_resets_rejection_streak() -> None:
    events = [
        _event("code-reviewer", "I request changes", t=1.0),
        _event("code-reviewer", "LGTM, approving", t=2.0),
        _event("code-reviewer", "I request changes again", t=3.0),
    ]
    signals = session_signals.collect_signals(events)
    assert not any(s["kind"] == "review_reject_streak" for s in signals)


def test_blocking_inside_think_does_not_count_as_rejection() -> None:
    events = [
        _event("code-reviewer", "<think>this is blocking</think>", t=1.0),
        _event("code-reviewer", "<think>still blocking</think>", t=2.0),
    ]
    signals = session_signals.collect_signals(events)
    assert not any(s["kind"] == "review_reject_streak" for s in signals)


def test_request_changes_outside_think_counts_as_rejection() -> None:
    events = [
        _event(
            "code-reviewer",
            "<think>maybe</think> I REQUEST CHANGES because tests are missing",
            t=1.0,
        ),
        _event(
            "code-reviewer",
            "<think>maybe</think> I REQUEST CHANGES; docs still missing",
            t=2.0,
        ),
    ]
    signals = session_signals.collect_signals(events)
    assert any(s["kind"] == "review_reject_streak" for s in signals)


# ---------------------------------------------------------------------------
# Long cycles
# ---------------------------------------------------------------------------


def test_long_cycle_warns_at_500s() -> None:
    events = [
        _event("just-code", "start", t=0.0),
        _event("just-code", "finish", t=500.0),
    ]
    signals = session_signals.collect_signals(events)
    sig = next((s for s in signals if s["kind"] == "long_cycle"), None)
    assert sig is not None
    assert sig["severity"] == "warn"


def test_no_long_cycle_for_single_idle_gap() -> None:
    """A resumed session with one idle gap must not emit long_cycle."""
    events = [
        _event("just-code", "start", t=0.0),
        _event("just-code", "finish", t=86400.0),
    ]
    signals = session_signals.collect_signals(events)
    assert not any(s["kind"] == "long_cycle" for s in signals)


def test_long_cycle_warns_on_sub_600s_gaps_spanning_500s() -> None:
    """Several sub-600s gaps adding to 500s active time must emit warn."""
    events = [
        _event("just-code", f"step {i}", t=float(i * 100))
        for i in range(6)
    ]
    signals = session_signals.collect_signals(events)
    sig = next((s for s in signals if s["kind"] == "long_cycle"), None)
    assert sig is not None
    assert sig["severity"] == "warn"
    assert "active" in sig["evidence"]


def test_no_long_cycle_at_100s() -> None:
    events = [
        _event("just-code", "start", t=0.0),
        _event("just-code", "finish", t=100.0),
    ]
    signals = session_signals.collect_signals(events)
    assert not any(s["kind"] == "long_cycle" for s in signals)


# ---------------------------------------------------------------------------
# Token hotspots
# ---------------------------------------------------------------------------


def test_token_hotspot_at_90000_tokens() -> None:
    events = [
        _event("just-code", "big edit", t=1.0, tokens_in=50_000, tokens_out=40_000),
    ]
    signals = session_signals.collect_signals(events)
    assert any(s["kind"] == "token_hotspot" for s in signals)


def test_cache_miss_and_long_context_and_expensive_model() -> None:
    events = [
        _event("grokestrator", "delegate", t=1.0, tokens_in=90_000),
        _event("grok-just-code", "edit", t=2.0, tokens_in=10_000),
    ]
    events[0]["cache_read"] = 512
    events[1]["cache_read"] = 200_000
    events[1]["model"] = "grok-4.7"
    signals = session_signals.collect_signals(events)
    kinds = {s["kind"] for s in signals}
    assert "cache_miss" in kinds
    assert "long_context" in kinds
    assert "expensive_model" in kinds
    assert not any(s["kind"] == "expensive_model" and s["agent"] == "grokestrator" for s in signals)


def test_no_token_hotspot_when_all_tokens_zero() -> None:
    events = [
        _event("just-code", "edit", t=1.0, tokens_in=0, tokens_out=0),
    ]
    signals = session_signals.collect_signals(events)
    assert not any(s["kind"] == "token_hotspot" for s in signals)


# ---------------------------------------------------------------------------
# Repeated tool errors
# ---------------------------------------------------------------------------


def test_repeated_tool_error_at_three() -> None:
    events = [
        _event("just-code", "tool error", t=float(i), tool="bash", tool_error=True)
        for i in range(3)
    ]
    signals = session_signals.collect_signals(events)
    assert any(s["kind"] == "repeated_tool_error" for s in signals)


# ---------------------------------------------------------------------------
# Context reread
# ---------------------------------------------------------------------------


def test_context_reread_at_four() -> None:
    events = [
        _event(
            "just-code",
            "reading file",
            t=float(i),
            tool="read",
            tool_path="/foo/bar.py",
        )
        for i in range(4)
    ]
    signals = session_signals.collect_signals(events)
    assert any(s["kind"] == "context_reread" for s in signals)


# ---------------------------------------------------------------------------
# Manifest-derived signals
# ---------------------------------------------------------------------------


def test_signals_from_manifest_fix_iterations_two_emits_fix_loop() -> None:
    manifest = {
        "fix_iterations": 2,
        "phases": [
            {"phase": "test", "outcome": "fail", "notes": "flaky assertion"},
        ],
    }
    signals = session_signals.signals_from_manifest(manifest)
    assert any(s["kind"] == "fix_loop" for s in signals)


def test_signals_from_manifest_fix_iterations_zero_does_not_emit() -> None:
    manifest = {"fix_iterations": 0, "phases": []}
    signals = session_signals.signals_from_manifest(manifest)
    assert not any(s["kind"] == "fix_loop" for s in signals)


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_no_logs_exits_zero_with_note(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--cwd", str(tmp_path), "--harness", "opencode"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["harness"] == "opencode"
    assert data["cwd"] == str(tmp_path)
    assert data["notes"]
    assert any(
        "OpenCode db not found" in note or "No matching OpenCode session" in note
        for note in data["notes"]
    )


# ---------------------------------------------------------------------------
# Auto harness dispatch
# ---------------------------------------------------------------------------


def test_select_harness_skips_opencode_without_events_or_session() -> None:
    """Auto mode must fall through to grok when opencode only has a miss note."""
    opencode = (
        "opencode",
        [],
        {"harness": "opencode", "session_id": ""},
        ["No matching OpenCode session for cwd"],
    )
    grok = (
        "grok",
        [_event("just-code", "did work", t=1.0)],
        {"harness": "grok", "session_id": "grok-session-1"},
        [],
    )
    claude = (
        "claude",
        [],
        {"harness": "claude", "session_id": ""},
        ["Claude logs not found"],
    )
    name, events, info, notes = session_signals._select_harness(
        [opencode, grok, claude]
    )
    assert name == "grok"
    assert events == grok[1]
    assert info["session_id"] == "grok-session-1"
    assert "No matching OpenCode session for cwd" not in notes


def test_select_harness_no_match_reports_all_misses() -> None:
    results = [
        ("opencode", [], {"session_id": ""}, ["No matching OpenCode session for cwd"]),
        ("grok", [], {"session_id": ""}, ["Grok logs not found"]),
        ("claude", [], {"session_id": ""}, ["Claude logs not found"]),
    ]
    name, events, _info, notes = session_signals._select_harness(results)
    assert name == ""
    assert events == []
    assert "No log source matched (tried opencode, grok, claude)" in notes
    assert any("No matching OpenCode session for cwd" in n for n in notes)
    assert any("Grok logs not found" in n for n in notes)


# ---------------------------------------------------------------------------
# Tier-family grouping (MDU-50 defect 3)
# ---------------------------------------------------------------------------


def test_family_strips_one_trailing_tier_suffix() -> None:
    assert session_signals._family("code-reviewer-pro") == "code-reviewer"
    assert session_signals._family("code-reviewer-mid") == "code-reviewer"
    assert session_signals._family("code-reviewer-premium") == "code-reviewer"
    assert session_signals._family("code-reviewer-free") == "code-reviewer"
    assert session_signals._family("code-reviewer") == "code-reviewer"
    assert session_signals._family("grok-qa-mid") == "grok-qa"
    assert session_signals._family("orchestrator") == "orchestrator"
    assert session_signals._family("pro") == "pro"


def test_review_reject_streak_pools_tier_variants() -> None:
    events = [
        _event("code-reviewer-pro", "REQUEST CHANGES: tests missing", t=1.0),
        _event("code-reviewer-mid", "I REJECT this: docs missing", t=2.0),
        _event("code-reviewer-free", "LGTM", t=3.0),
    ]
    signals = session_signals.collect_signals(events)
    sig = next(s for s in signals if s["kind"] == "review_reject_streak")
    assert sig["agent"] == "code-reviewer"
    assert "2 consecutive rejections from code-reviewer" in sig["evidence"]
    assert "variants:" in sig["evidence"]
    assert "code-reviewer-pro" in sig["evidence"]
    assert "code-reviewer-mid" in sig["evidence"]


def test_bare_reject_verdict_counts_as_rejection() -> None:
    events = [
        _event("code-reviewer", "REJECT", t=1.0),
        _event("code-reviewer", "REJECT", t=2.0),
    ]
    signals = session_signals.collect_signals(events)
    sig = next(s for s in signals if s["kind"] == "review_reject_streak")
    assert sig["agent"] == "code-reviewer"
    assert "2 consecutive rejections" in sig["evidence"]


def test_qa_fail_repeat_pools_tier_variants() -> None:
    events = [
        _event("qa-mid", "QA GRADE: FAIL", t=1.0),
        _event("qa", "QA GRADE: FAIL", t=2.0),
    ]
    signals = session_signals.collect_signals(events)
    sig = next(s for s in signals if s["kind"] == "qa_fail_repeat")
    assert sig["agent"] == "qa"
    assert "reported FAIL 2 times" in sig["evidence"]


def test_repeated_tool_error_pools_tier_variants() -> None:
    events = [
        _event("just-code-pro", "tool error", t=1.0, tool="bash", tool_error=True),
        _event("just-code-mid", "tool error", t=2.0, tool="bash", tool_error=True),
        _event("just-code", "tool error", t=3.0, tool="bash", tool_error=True),
    ]
    signals = session_signals.collect_signals(events)
    sig = next(s for s in signals if s["kind"] == "repeated_tool_error")
    assert sig["agent"] == "just-code"
    assert "hit 3 errors" in sig["evidence"]


def test_free_tier_is_a_bulk_role_for_expensive_model() -> None:
    assert session_signals._is_bulk_agent("code-reviewer-free") is True
    assert session_signals._is_bulk_agent("code-reviewer") is True
    assert session_signals._is_bulk_agent("code-reviewer-pro") is False
    events = [
        _event("code-reviewer-free", "reviewed", t=1.0),
    ]
    events[0]["model"] = "grok-4.7"
    signals = session_signals.collect_signals(events)
    sig = next(s for s in signals if s["kind"] == "expensive_model")
    assert sig["agent"] == "code-reviewer-free"


def test_pro_tier_on_flagship_model_is_not_expensive() -> None:
    """Regression: the bulk check must see the raw tier suffix, not the family."""
    events = [
        _event("code-reviewer-pro", "reviewed", t=1.0),
    ]
    events[0]["model"] = "grok-4.7"
    signals = session_signals.collect_signals(events)
    assert not any(s["kind"] == "expensive_model" for s in signals)


def test_mid_tier_on_flagship_model_is_not_expensive() -> None:
    events = [
        _event("just-code-mid", "edited", t=1.0),
    ]
    events[0]["model"] = "grok-4.7"
    signals = session_signals.collect_signals(events)
    assert not any(s["kind"] == "expensive_model" for s in signals)


def test_context_reread_pools_tier_variants_to_reach_threshold() -> None:
    """Two re-reads per tier variant only cross the threshold when family-pooled."""
    events = [
        _event("just-code-pro", "read", t=1.0, tool="read", tool_path="a.py"),
        _event("just-code-pro", "read", t=2.0, tool="read", tool_path="a.py"),
        _event("just-code-mid", "read", t=3.0, tool="read", tool_path="a.py"),
        _event("just-code-mid", "read", t=4.0, tool="read", tool_path="a.py"),
    ]
    signals = session_signals.collect_signals(events)
    sig = next(s for s in signals if s["kind"] == "context_reread")
    assert sig["agent"] == "just-code"


def test_pro_tier_cache_miss_still_groups_under_family() -> None:
    """Cost pooling stays family-keyed; only the bulk-tier test uses the raw name."""
    events = [
        _event("code-reviewer-pro", "reviewed", t=1.0, tokens_in=90_000),
    ]
    events[0]["cache_read"] = 512
    events[0]["model"] = "grok-4.7"
    signals = session_signals.collect_signals(events)
    sig = next(s for s in signals if s["kind"] == "cache_miss")
    assert sig["agent"] == "code-reviewer"


# ---------------------------------------------------------------------------
# QA verdict line (MDU-50 defect 4)
# ---------------------------------------------------------------------------


def test_quoted_qa_verdict_instruction_is_not_a_fail() -> None:
    instruction = "End with exactly: QA GRADE: PASS or QA GRADE: FAIL"
    events = [
        _event("qa", instruction, t=1.0),
        _event("qa", instruction, t=2.0),
    ]
    signals = session_signals.collect_signals(events)
    assert not any(s["kind"] == "qa_fail_repeat" for s in signals)


def test_standalone_qa_verdict_line_counts_once_per_message() -> None:
    events = [
        _event("qa", "findings: x\nQA GRADE: FAIL\nQA GRADE: FAIL", t=1.0),
        _event("qa", "QA GRADE: FAIL", t=2.0),
    ]
    signals = session_signals.collect_signals(events)
    sig = next(s for s in signals if s["kind"] == "qa_fail_repeat")
    assert "reported FAIL 2 times" in sig["evidence"]


def test_lowercase_qa_verdict_line_counts() -> None:
    events = [
        _event("qa", "qa grade: fail", t=1.0),
        _event("qa", "qa grade: fail", t=2.0),
    ]
    signals = session_signals.collect_signals(events)
    assert any(s["kind"] == "qa_fail_repeat" for s in signals)


def test_qa_grade_failed_word_does_not_count() -> None:
    events = [
        _event("qa", "QA GRADE: FAILED", t=1.0),
        _event("qa", "QA GRADE: FAILED", t=2.0),
    ]
    signals = session_signals.collect_signals(events)
    assert not any(s["kind"] == "qa_fail_repeat" for s in signals)


# ---------------------------------------------------------------------------
# Synthetic v2 tool events must not inflate metrics or cycle evidence (MDU-51)
# ---------------------------------------------------------------------------


def test_tool_role_events_are_excluded_from_agent_metrics() -> None:
    """A message plus its synthetic tool events counts as one message."""
    events = [
        _event("just-code", "edited", t=10.0, tokens_in=1000, tokens_out=100),
        _event("just-code", "", t=10.0, role="tool", tool="read", tool_path="a.py"),
        _event("just-code", "", t=10.0, role="tool", tool="edit", tool_path="a.py"),
    ]
    metrics = session_signals._compute_metrics(events)
    row = next(a for a in metrics["agents"] if a["name"] == "just-code")
    assert row["messages"] == 1
    assert row["tokens_in"] == 1000
    assert row["tokens_out"] == 100
    assert row["duration_s"] == 0


def test_long_cycle_evidence_count_excludes_tool_role_events() -> None:
    """Same-t tool events cannot change active/wall time or the evidence count."""
    events = [
        _event("just-code", "first", t=0.0),
        _event("just-code", "second", t=500.0),
        _event("just-code", "third", t=1000.0),
        _event("just-code", "", t=1000.0, role="tool", tool="read", tool_path="a.py"),
        _event("just-code", "", t=1000.0, role="tool", tool="grep", tool_path="b"),
    ]
    signals = session_signals.collect_signals(events)
    sig = next(s for s in signals if s["kind"] == "long_cycle")
    assert "active 1000s" in sig["evidence"]
    assert "across 3 events" in sig["evidence"]

