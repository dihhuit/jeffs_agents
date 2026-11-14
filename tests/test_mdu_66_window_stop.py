"""MDU-66 stop pin: no live agent definition may carry a context_window key.

Fails when a scanned definition gains a ``context_window:`` line, or when
the design-doc / backlog stop record disappears. Does not pin a file count.
Reads files as text only — no network, no shell.
"""

from __future__ import annotations

import re
from pathlib import Path

_HERE = Path(__file__).resolve()
REPO = _HERE.parents[1]
# parents[0] is tests/, parents[1] is this repo, parents[2] is the agents workspace.
OVERLAY = _HERE.parents[2] / "opencode_agents" / "grok" / "agents" / "grokestrator.md"

CONTEXT_WINDOW = re.compile(r"^\s*context_window\s*:")

DESIGN = REPO / "docs" / "design" / "mdu-66-grokestrator-context-window.md"
BACKLOG = REPO / "FEATURE_BACKLOG.md"
ORCHESTRATOR = REPO / "grok" / "agents" / "orchestrator.md"

PIN_LINES = (
    "Frontmatter context_window is ignored.",
    "Probe contextWindowTokens stayed 256000.",
    "The model id stayed grok-4.7.",
    "The model-wide user-config table was not applied.",
    "No agent definition was edited.",
)

MODEL_LINE = "model: grok-4.7"
STATUS_FRAGMENTS = (
    "Done — 2026-11-14",
    "was not applied",
    "No agent file edit",
)


def _live_agent_files() -> list[Path]:
    """Top-level agent markdown only. Count is not asserted."""
    files: list[Path] = []
    for root in (REPO / "grok" / "agents", REPO / "prompts"):
        if root.is_dir():
            files.extend(sorted(path for path in root.glob("*.md") if path.is_file()))
    return files


def _context_window_hits(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    hits: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if CONTEXT_WINDOW.match(line):
            hits.append(f"{path}:{lineno}:{line}")
    return hits


def test_no_live_context_window_key() -> None:
    assert OVERLAY.is_file(), f"overlay missing: {OVERLAY}"
    hits: list[str] = []
    for path in (*_live_agent_files(), OVERLAY):
        hits.extend(_context_window_hits(path))
    assert not hits, "context_window key on a live agent definition:\n" + "\n".join(hits)


def _first_lines(path: Path, count: int = 6) -> list[str]:
    assert path.is_file(), f"missing: {path}"
    return path.read_text(encoding="utf-8").splitlines()[:count]


def test_model_id_stays_grok_4_7() -> None:
    for path in (ORCHESTRATOR, OVERLAY):
        head = _first_lines(path)
        assert MODEL_LINE in head, (
            f"{path} first 6 lines lack a line exactly {MODEL_LINE!r}: {head!r}"
        )


def test_design_stop_record() -> None:
    assert DESIGN.is_file(), f"stop record missing: {DESIGN}"
    lines = DESIGN.read_text(encoding="utf-8").splitlines()
    missing = [line for line in PIN_LINES if line not in lines]
    assert not missing, "design doc dropped stop-record lines:\n" + "\n".join(missing)


def _mdu66_section(text: str) -> tuple[str, list[str]]:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("### MDU-66")), None)
    assert start is not None, "FEATURE_BACKLOG.md has no heading starting with '### MDU-66'"
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("### "):
            break
        body.append(line)
    return lines[start], body


def test_backlog_stop_record() -> None:
    assert BACKLOG.is_file(), f"stop record missing: {BACKLOG}"
    heading, body = _mdu66_section(BACKLOG.read_text(encoding="utf-8"))
    assert "queue head" not in heading, f"MDU-66 heading still says queue head: {heading!r}"
    status = [line for line in body if line.lstrip().startswith("- **Status:**")]
    assert status, "MDU-66 section has no status bullet"
    blob = "\n".join(status)
    missing = [fragment for fragment in STATUS_FRAGMENTS if fragment not in blob]
    assert not missing, f"status bullet missing {missing!r}: {blob!r}"
