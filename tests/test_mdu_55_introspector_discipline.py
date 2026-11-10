"""MDU-55 introspector self-cost discipline: one loop-mode sub-bullet, one SKILL note.

Hermetic: repo reads only, no network, no git state, no writes. The constants
below are the byte-identity authority: they hold the §2 blockquote and the §4
note (heading + 5-line body) of
docs/design/mdu-55-introspector-self-cost-discipline.md verbatim.

Clause-file pins resolve their root through `MDU55_TEST_ROOT`, so the mutation
matrix (design §5) can point the suite at a /tmp copy with exactly one clause
stripped. Doc-consistency pins always read the real repo doc.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Clause-file root: overridable for the mutation matrix (design §5).
CLAUSE_ROOT = Path(os.environ.get("MDU55_TEST_ROOT", str(REPO_ROOT))).resolve()

DESIGN_DOC = (
    REPO_ROOT / "docs" / "design" / "mdu-55-introspector-self-cost-discipline.md"
)
SKILL_MD = CLAUSE_ROOT / "skills" / "session-introspect" / "SKILL.md"

MIRRORS = [
    ("opencode", CLAUSE_ROOT / "prompts" / "introspector.md"),
    ("grok", CLAUSE_ROOT / "grok" / "agents" / "introspector.md"),
]

# ---------------------------------------------------------------------------
# Constants — verbatim from the design doc (§2 blockquote, §4 note).
# ---------------------------------------------------------------------------

D1_20261102_2 = (
    "Read `agent-improvements.md` once at the start — grep for the open `[ ]` "
    "suggestion ids and read only those sections, not the whole file — and update "
    "it by targeted section edits; never re-read the full file after the first "
    "pass. Run the signal script once at the start; if your own prompt context "
    "approaches 140,000 tokens, stop gathering evidence and write the report from "
    "the notes you already have."
)

EMITTED_LINE = "  - " + D1_20261102_2

SKILL_NOTE_HEADING = "### Run timing and the pass's own signals"

SKILL_NOTE_BODY = (
    "The script runs at pass start, so the introspector's own token, long_context, and\n"
    "stall signals are captured mid-pass and structurally under-report — a closing\n"
    "re-run (or an orchestrator-side run after the pass) is needed to see them. A pass\n"
    "record that claims no long_context is describing only the pre-script window;\n"
    "check a closing run before treating the pass's own cost as clean."
)

# Pre-existing anchors (position pins; not the clause's own words).
READ_PARENT = "- Read `agent-improvements.md` at the project root if it exists."
MANIFEST_BULLET = (
    "- Read `runs/<mdu-id>/manifest.json` if the orchestrator passed an MDU id."
)
HOWTO_HEADING = "## How to run the helper"
SIGNAL_KINDS_HEADING = "## Signal kinds"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _line_containing(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle in line:
            return line
    raise AssertionError(f"needle not found in any line: {needle[:60]!r}")


def _assert_order(path: Path, first: str, second: str, label: str) -> None:
    text = _text(path)
    first_pos = text.find(first)
    second_pos = text.find(second)
    assert first_pos != -1, f"{path}: {label} anchor missing ({first[:50]!r})"
    assert second_pos != -1, f"{path}: {label} anchor missing ({second[:50]!r})"
    assert first_pos < second_pos, f"{path}: expected {label} order {first[:40]!r} < {second[:40]!r}"


# ---------------------------------------------------------------------------
# 1. Presence, exactly once, per mirror
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label, path", MIRRORS)
def test_subbullet_present_exactly_once_in_each_mirror(label, path):
    text = _text(path)
    assert text.count(EMITTED_LINE) == 1, (
        f"{label}: D1 20261102-2 sub-bullet must appear exactly once"
    )


# ---------------------------------------------------------------------------
# 2. Cross-mirror byte identity
# ---------------------------------------------------------------------------

def test_subbullet_line_byte_identical_across_mirrors():
    lines = {_line_containing(_text(path), D1_20261102_2) for _label, path in MIRRORS}
    assert len(lines) == 1, (
        "D1 20261102-2 line differs across mirrors:\n" + "\n".join(sorted(lines))
    )
    assert lines == {EMITTED_LINE}


# ---------------------------------------------------------------------------
# 3. Doc consistency — constants are verbatim in the design doc
# ---------------------------------------------------------------------------

DOC_CONSTANTS = [
    ("D1", D1_20261102_2),
    ("skill_note_body", SKILL_NOTE_BODY),
    ("skill_note_heading", SKILL_NOTE_HEADING),
]


@pytest.mark.parametrize("const_name, const", DOC_CONSTANTS)
def test_constant_matches_design_doc(const_name, const):
    doc = _text(DESIGN_DOC)
    assert const in doc, f"{const_name} constant drifted from the design doc"


# ---------------------------------------------------------------------------
# 4. Ordering: read parent < sub-bullet < manifest bullet
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label, path", MIRRORS)
def test_subbullet_between_read_parent_and_manifest_bullet(label, path):
    _assert_order(path, READ_PARENT, EMITTED_LINE, f"{label} read-parent < sub-bullet")
    _assert_order(path, EMITTED_LINE, MANIFEST_BULLET, f"{label} sub-bullet < manifest")


# ---------------------------------------------------------------------------
# 5. Parent bullet byte-unchanged
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label, path", MIRRORS)
def test_read_parent_bullet_unchanged(label, path):
    text = _text(path)
    parent_lines = [
        line for line in text.splitlines() if READ_PARENT in line
    ]
    assert parent_lines == [READ_PARENT], (
        f"{label}: read-parent bullet changed or duplicated: {parent_lines!r}"
    )


# ---------------------------------------------------------------------------
# 6. SKILL.md note: heading once + body present
# ---------------------------------------------------------------------------

def test_skill_note_heading_once_and_body_present():
    text = _text(SKILL_MD)
    assert text.count(SKILL_NOTE_HEADING) == 1, "SKILL note heading must appear once"
    assert SKILL_NOTE_BODY in text, "SKILL note body drifted"


# ---------------------------------------------------------------------------
# 7. SKILL.md note position: after `## How to run the helper`, before `## Signal kinds`
# ---------------------------------------------------------------------------

def test_skill_note_between_howto_and_signal_kinds():
    _assert_order(
        SKILL_MD, HOWTO_HEADING, SKILL_NOTE_HEADING, "how-to < note heading"
    )
    _assert_order(
        SKILL_MD, SKILL_NOTE_HEADING, SIGNAL_KINDS_HEADING, "note heading < signal kinds"
    )
