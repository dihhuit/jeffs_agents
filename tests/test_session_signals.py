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
