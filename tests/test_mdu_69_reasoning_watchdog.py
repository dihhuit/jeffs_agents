"""MDU-69 reasoning-watchdog pin, base side.

The clause is the design-doc fence under Exact clause. The mutation copies
grok/agents/orchestrator.md under /tmp, deletes that line, and expects the
presence check to find zero matches. It does not write the worktree.

Hermetic apart from that /tmp copy: no network, no git calls.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

GROK_ORCHESTRATOR = Path("grok") / "agents" / "orchestrator.md"
PROMPTS_ORCHESTRATOR = Path("prompts") / "orchestrator.md"
BACKLOG = Path("FEATURE_BACKLOG.md")

# Exact clause. Leading "- " is part of the line.
CLAUSE_LINE = (
    "- On Grok, a child in `streaming_reasoning` with a growing thought is "
    "working, even when `toolCallCount` is 0 and the assigned file does not "
    "exist yet. Do not cancel it at the five-minute check. Cancel when phase "
    "events go idle, or when it is calling tools and still has not written "
    "the assigned file."
)

# The dash before the date is U+2014.
STATUS_LINE = (
    "- **Status:** Done \u2014 2026-11-15 (streaming_reasoning with a growing "
    "thought is progress. The five-minute cancel applies to an idle stream "
    "or a tool loop with no write.)"
)

PREV_PREFIX = "- **Subagent Watchdog:**"
NEXT_PREFIX = "- **Session Checkpoint:**"


def _read(path: Path) -> str:
    resolved = path.resolve()
    assert resolved.is_relative_to(REPO_ROOT.resolve()), f"path escaped the repo: {resolved}"
    assert resolved.is_file(), f"missing target: {resolved}"
    return resolved.read_text(encoding="utf-8")


def _repo_text(rel: Path) -> str:
    assert not rel.is_absolute()
    return _read(REPO_ROOT / rel)


def _full_line_count(text: str, line: str) -> int:
    """`grep -F -x` equivalent: exact full-line matches only."""
    return sum(1 for candidate in text.splitlines() if candidate == line)


def _assert_clause_between_anchors(text: str, where: str) -> None:
    lines = text.splitlines()
    count = _full_line_count(text, CLAUSE_LINE)
    assert count == 1, f"{where}: clause full-line count is {count}, expected 1"
    idx = lines.index(CLAUSE_LINE)
    assert idx > 0, f"{where}: the clause line has no previous line"
    assert lines[idx - 1].startswith(PREV_PREFIX), (
        f"{where}: previous line does not start with the watchdog anchor"
    )
    assert idx + 1 < len(lines), f"{where}: the clause line has no successor"
    assert lines[idx + 1].startswith(NEXT_PREFIX), (
        f"{where}: successor does not start with the session-checkpoint anchor"
    )


def _under_tmp(path: Path) -> None:
    resolved = path.resolve()
    tmp = Path("/tmp").resolve()
    assert resolved == tmp or resolved.is_relative_to(tmp), (
        f"mutation path is not under /tmp: {resolved}"
    )
    assert not resolved.is_relative_to(REPO_ROOT.resolve()), (
        f"mutation path is inside the base worktree: {resolved}"
    )
    overlay = REPO_ROOT.parent / "opencode_agents"
    if overlay.exists():
        assert not resolved.is_relative_to(overlay.resolve()), (
            f"mutation path is inside the overlay worktree: {resolved}"
        )


def test_grok_orchestrator_clause_once_between_anchors() -> None:
    _assert_clause_between_anchors(
        _repo_text(GROK_ORCHESTRATOR), GROK_ORCHESTRATOR.as_posix()
    )


def test_prompts_orchestrator_has_no_streaming_reasoning() -> None:
    text = _repo_text(PROMPTS_ORCHESTRATOR)
    assert "streaming_reasoning" not in text


def test_feature_backlog_status_line() -> None:
    assert "\u2014" in STATUS_LINE
    assert "Done - " not in STATUS_LINE
    text = _repo_text(BACKLOG)
    assert _full_line_count(text, STATUS_LINE) == 1


def test_mutation_deleted_clause_has_zero_matches() -> None:
    src = REPO_ROOT / GROK_ORCHESTRATOR
    original = src.read_bytes()
    mutant_root = Path(tempfile.mkdtemp(prefix="mdu69-reasoning-watchdog-", dir="/tmp"))
    try:
        _under_tmp(mutant_root)
        dest = mutant_root / "grok" / "agents" / "orchestrator.md"
        _under_tmp(dest)
        dest.parent.mkdir(parents=True)
        shutil.copyfile(src, dest)
        text = dest.read_text(encoding="utf-8")
        assert _full_line_count(text, CLAUSE_LINE) == 1, (
            "refusing to mutate a copy that does not carry the clause once"
        )
        stripped = [line for line in text.splitlines() if line != CLAUSE_LINE]
        payload = "\n".join(stripped)
        if text.endswith("\n"):
            payload += "\n"
        dest.write_text(payload, encoding="utf-8")
        copied = dest.read_text(encoding="utf-8")
        assert _full_line_count(copied, CLAUSE_LINE) == 0
        assert src.read_bytes() == original
    finally:
        shutil.rmtree(mutant_root, ignore_errors=True)
        assert src.read_bytes() == original
