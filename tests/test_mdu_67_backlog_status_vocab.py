"""MDU-67 backlog status vocabulary: one clause line in the four base carriers.

Constants are the design-doc fences (docs/design/mdu-67-backlog-status-vocab.md
§2 and §3). `MDU67_TEST_ROOT` redirects only those four carrier reads, so a
/tmp mutant fails presence or adjacency and not the doc, backlog, or
suggestion pins. Census walks the real repo's prompts/ and grok/agents/ and
checks where the line appears — it does not count files.

Hermetic: file reads only — no network, no git calls, no writes, no secrets.
Paths resolve from Path(__file__) so the suite is cwd-independent.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(os.environ.get("MDU67_TEST_ROOT", str(REPO_ROOT))).resolve()

DESIGN_DOC = Path("docs") / "design" / "mdu-67-backlog-status-vocab.md"
BACKLOG = Path("FEATURE_BACKLOG.md")
IMPROVEMENTS = Path("agent-improvements.md")

# §2 fence. Leading "- " is part of the line.
CLAUSE_LINE = (
    "- When you write a FEATURE_BACKLOG `- **Status:**` line, the resolving word is `Done` or `Superseded` only. `Stopped`, `Stop`, and `Closed` fail `test_backlog_no_entry_remains_unresolved`. A deliberate stop is still `Done`, with the stop reason in the same bullet."
)

# §3 status line. The dash before the date is U+2014.
STATUS_LINE = (
    "- **Status:** Done — 2026-11-14 (CLI-independent prompt clause so a deliberate non-ship is still Done.)"
)

REBUILD_LINE = (
    "- A fix is incomplete until the generated copies are fresh: after editing any source file that has build/generated copies (skills, prompts, grok builds, pi goldens, build/ trees), run the build/gate that regenerates them in the SAME cycle and re-diff the copies against the source before reporting done — a source fix with stale copies will be returned by review."
)

TOKEN_LONG = (
    "- **Token budget**: If the task is large, break it into multiple smaller subtasks and implement incrementally. Do not generate excessive code in a single response."
)
TOKEN_SHORT = "- **Token budget**: If the task is large, break it into multiple smaller subtasks."

CHECKED_LINE = (
    "- [x] id: 20261114-1 | severity: low | target: just-code | kind: backlog_status_vocab | **RESOLVED 2026-11-14 (mdu-67)**"
)
UNCHECKED_LINE = (
    "- [ ] id: 20261114-1 | severity: low | target: just-code | kind: backlog_status_vocab"
)
NOTE_LINE = (
    "  - note (2026-11-14, mdu-67): **RESOLVED** — clause shipped byte-identical to the suggestion in prompts/just-code.md, grok/agents/just-code.md, grok/agents/just-code-mid.md, grok/agents/just-code-pro.md, and overlay grok/agents/grok-just-code.md, grok/agents/grok-just-code-mid.md, grok/agents/grok-just-code-pro.md."
)

# (repo-relative carrier, successor kind from design §1 rows 1–4)
BASE_CARRIERS = (
    (Path("prompts") / "just-code.md", "token-long"),
    (Path("grok") / "agents" / "just-code.md", "token-short"),
    (Path("grok") / "agents" / "just-code-mid.md", "behavior"),
    (Path("grok") / "agents" / "just-code-pro.md", "behavior"),
)


def _label(rel: Path) -> str:
    return rel.as_posix()


def _read(path: Path, root: Path) -> str:
    """Read a file, refusing any path that escapes its declared root."""
    resolved = path.resolve()
    assert resolved.is_relative_to(root.resolve()), (
        f"path escaped its root {root}: {resolved}"
    )
    assert resolved.is_file(), f"missing target: {resolved}"
    return resolved.read_text(encoding="utf-8")


def _repo_text(rel: Path) -> str:
    """Design doc, backlog, and the suggestion log always use the real repo."""
    return _read(REPO_ROOT / rel, REPO_ROOT)


def _specimen_text(rel: Path) -> str:
    """Four base carriers. `MDU67_TEST_ROOT` may point these at a /tmp copy."""
    assert not rel.is_absolute(), f"specimen labels must be repo-relative: {rel}"
    return _read(TEST_ROOT / rel, TEST_ROOT)


def _full_line_count(text: str, line: str) -> int:
    """`grep -F -x` equivalent: exact full-line matches only."""
    return sum(1 for candidate in text.splitlines() if candidate == line)


def _section(text: str, start_prefix: str, end_prefix: str) -> str:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith(start_prefix)), None)
    assert start is not None, f"missing heading {start_prefix!r}"
    end = next(
        (i for i, line in enumerate(lines) if i > start and line.startswith(end_prefix)),
        None,
    )
    assert end is not None, f"missing heading {end_prefix!r} after {start_prefix!r}"
    return "\n".join(lines[start:end])


# ---------------------------------------------------------------------------
# 1. Doc consistency — §2 fence line and §3 status line are full lines
# ---------------------------------------------------------------------------

def test_design_doc_clause_and_status_are_full_lines():
    doc = _repo_text(DESIGN_DOC)
    section_2 = _section(doc, "## 2.", "## 3.")
    section_3 = _section(doc, "## 3.", "## 4.")
    assert _full_line_count(section_2, CLAUSE_LINE) == 1, (
        "design doc §2 fence is missing or not a single full line"
    )
    assert _full_line_count(section_3, STATUS_LINE) == 1, (
        "design doc §3 status line is missing or not a single full line"
    )


# ---------------------------------------------------------------------------
# 2. Presence — each base carrier has the §2 line once
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "rel, _kind",
    BASE_CARRIERS,
    ids=[_label(rel) for rel, _kind in BASE_CARRIERS],
)
def test_base_carrier_contains_clause_once(rel, _kind):
    count = _full_line_count(_specimen_text(rel), CLAUSE_LINE)
    assert count == 1, (
        f"{_label(rel)}: the §2 line must appear as an exact full line exactly "
        f"once; found {count}"
    )


# ---------------------------------------------------------------------------
# 3. Adjacency — immediate next line after the rebuild anchor; successor stays
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "rel, kind",
    BASE_CARRIERS,
    ids=[_label(rel) for rel, _kind in BASE_CARRIERS],
)
def test_clause_follows_rebuild_anchor(rel, kind):
    label = _label(rel)
    lines = _specimen_text(rel).splitlines()
    assert _full_line_count("\n".join(lines), CLAUSE_LINE) == 1, (
        f"{label}: adjacency requires the §2 line once, immediately after the rebuild anchor"
    )
    idx = lines.index(CLAUSE_LINE)
    assert idx > 0 and lines[idx - 1] == REBUILD_LINE, (
        f"{label}: the §2 line must be the immediate next line after the rebuild anchor "
        "(no blank between)"
    )
    if kind == "token-long":
        assert idx + 1 < len(lines) and lines[idx + 1] == TOKEN_LONG, (
            f"{label}: successor must stay the long token-budget line"
        )
    elif kind == "token-short":
        assert idx + 1 < len(lines) and lines[idx + 1] == TOKEN_SHORT, (
            f"{label}: successor must stay the short token-budget line"
        )
    else:
        assert lines[idx + 1 : idx + 3] == ["", "Behavior:"], (
            f"{label}: successor must stay a blank line then `Behavior:`"
        )


# ---------------------------------------------------------------------------
# 4. Backlog — one MDU-67 heading, one status line equal to §3
# ---------------------------------------------------------------------------

def test_backlog_mdu67_heading_and_status_line():
    text = _repo_text(BACKLOG)
    lines = text.splitlines()
    headings = [line for line in lines if line.startswith("### MDU-67")]
    assert len(headings) == 1, (
        f"FEATURE_BACKLOG.md must have one heading starting with '### MDU-67'; "
        f"found {len(headings)}"
    )
    heading = headings[0]
    assert "queue head" not in heading, f"MDU-67 heading contains 'queue head': {heading!r}"
    start = lines.index(heading)
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("### "):
            break
        body.append(line)
    status = [line for line in body if line.startswith("- **Status:**")]
    assert status == [STATUS_LINE], (
        f"MDU-67 section must contain exactly the §3 status line; found {status!r}"
    )
    assert _full_line_count(text, STATUS_LINE) == 1, (
        "the §3 status line must appear once in FEATURE_BACKLOG.md"
    )


# ---------------------------------------------------------------------------
# 5. Suggestion — checked id present, unchecked id absent, §4 note present
# ---------------------------------------------------------------------------

def test_suggestion_20261114_1_checked_and_noted():
    text = _repo_text(IMPROVEMENTS)
    assert _full_line_count(text, CHECKED_LINE) == 1, (
        "agent-improvements.md is missing the §4 checked id line"
    )
    assert _full_line_count(text, UNCHECKED_LINE) == 0, (
        "agent-improvements.md still has the unchecked 20261114-1 id line"
    )
    assert _full_line_count(text, NOTE_LINE) == 1, (
        "agent-improvements.md is missing the §4 mdu-67 note"
    )


# ---------------------------------------------------------------------------
# 6. Census — the §2 line's homes under prompts/ and grok/agents/, not a count
# ---------------------------------------------------------------------------

def _definition_markdown(root: Path) -> list[Path]:
    found: list[Path] = []
    for rel_dir in (Path("prompts"), Path("grok") / "agents"):
        directory = root / rel_dir
        if directory.is_dir():
            found.extend(path for path in directory.rglob("*.md") if path.is_file())
    return found


def test_census_clause_only_in_four_base_carriers():
    allowed = {(REPO_ROOT / rel).resolve() for rel, _kind in BASE_CARRIERS}
    scanned = _definition_markdown(REPO_ROOT)
    assert scanned, "census found no markdown under prompts/ or grok/agents/"
    offenders = [
        path.resolve().relative_to(REPO_ROOT).as_posix()
        for path in scanned
        if path.resolve() not in allowed
        and _full_line_count(path.read_text(encoding="utf-8"), CLAUSE_LINE) > 0
    ]
    assert offenders == [], (
        f"the §2 line leaked outside the four base carriers: {offenders}"
    )
