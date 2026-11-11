"""MDU-57 form-denial retry discipline: two clause families + two checklist lines.

Hermetic: repo + sibling-overlay reads only, no network, no git state, no writes.
The constants below are the byte-identity authority (mdu-49 convention): they hold
the §2 (Clause A), §3 (Clause B) and §4 (Clause C) blockquotes of
docs/design/mdu-57-form-denial-retry-discipline.md minus the emitted bullet lead.

Clause-file pins resolve their root through `MDU57_TEST_ROOT`, so the mutation
matrix (design §6 / AC-6) can point the suite at a /tmp copy with exactly one
clause stripped. Checklist and doc-consistency pins always read the real repo.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
OVERLAY_ROOT = REPO_ROOT.parent / "opencode_agents"
HAS_OVERLAY = OVERLAY_ROOT.is_dir()

# In a standalone base clone the overlay sibling is absent: skip only the pins
# that read overlay files (mdu-47 convention).
needs_overlay = pytest.mark.skipif(
    not HAS_OVERLAY, reason="overlay sibling opencode_agents/ not present"
)

# Clause-file root: overridable for the mutation matrix (design §6).
CLAUSE_ROOT = Path(os.environ.get("MDU57_TEST_ROOT", str(REPO_ROOT))).resolve()

DESIGN_DOC = (
    REPO_ROOT / "docs" / "design" / "mdu-57-form-denial-retry-discipline.md"
)
BRIEF_CHECKLIST = REPO_ROOT / "docs" / "brief-checklist.md"
OVERLAY_QA = OVERLAY_ROOT / "overlays" / "prompts" / "qa.md"
# Overlay-root Grok profiles are root-ADDED sources (no base same-name file; the
# build's step-4 add-if-absent promotes them), so they are live QA carriers that
# the base suite must pin from the sibling (mdu-54 rule: root, not build copy).
OVERLAY_GROK_QA = OVERLAY_ROOT / "grok" / "agents" / "grok-qa.md"
OVERLAY_GROK_QA_PRO = OVERLAY_ROOT / "grok" / "agents" / "grok-qa-pro.md"

# ---------------------------------------------------------------------------
# Constants — verbatim from the design doc (§2, §3, §4 blockquotes).
# ---------------------------------------------------------------------------

D1_20261110_1 = (
    "Shell denials under the deny-first wall are command-form-specific: before "
    "recording 'shell denied / signals UNKNOWN', retry ONCE in the plain "
    "allowlisted form (`timeout N python3 <script>`; no compounds, pipes, or "
    "redirects) — bare `echo`/`pwd` and compound forms are denied BY DESIGN and "
    "are not evidence of a lockout."
)
EMITTED_D1 = "  - " + D1_20261110_1

D2_20261110_1 = (
    "**Denied probes:** the brief names the expected probe commands and the "
    "file-tool fallback (read/grep/sed); run them as named, in the plain "
    "allowlisted form. Report a shell denial in the verdict as a form/permission "
    "event with the checks re-routed to attached or file-tool evidence — never "
    "improvise in-place rewrites of repo files as a probe."
)
EMITTED_D2 = "- " + D2_20261110_1

C_QA_LINE = (
    "- Pre-state the exact probe commands (plain allowlisted form) and the "
    "file-tool fallback (read/grep/sed) in every command-bearing QA brief; a "
    "denial QA reports is a form/permission event, not missing coverage. "
    "[20261110-1]"
)
C_INTROSPECTOR_LINE = (
    "- Add the plain-form retry line to the introspector brief: run the signal "
    "script as `timeout N python3 <script>`, no compounds, pipes, or redirects; "
    "bare `echo`/`pwd` and compound denials are by design. [20261110-1]"
)

# ---------------------------------------------------------------------------
# Pre-existing anchors (position / unchanged pins; not the clause's own words).
# ---------------------------------------------------------------------------

D1D_20261021_8 = (
    "- **Denied shell:** If `shell` is permission-denied, make exactly ONE retry "
    "with the simple single-command wrapper form `timeout <n> <command>` — no "
    "pipes, no redirects, no command substitution (e.g. `timeout 120 python3 -m "
    "pytest -q`). If that is also denied, do not conclude that shell is "
    "unavailable and do not report BLOCKED for it: fall back immediately to file "
    'tools plus orchestrator-attached outputs, labelling the affected checks '
    '"verified via orchestrator-attached output".'
)

RUN_PARENT = (
    "- Run the `session_signals.py` script to extract signals from the current "
    "OpenCode, Grok, or Claude session."
)
PASS_LINE = (
    "  Pass `--cwd`, `--session-id`, and `--harness` if the orchestrator supplied "
    "them; pass `--manifest runs/<mdu-id>/manifest.json` when an MDU id is given."
)
READ_PARENT = "- Read `agent-improvements.md` at the project root if it exists."

INTROSPECTOR_MIRRORS = [
    ("opencode", CLAUSE_ROOT / "prompts" / "introspector.md"),
    ("grok", CLAUSE_ROOT / "grok" / "agents" / "introspector.md"),
]

QA_DENIAL_20261021_8 = (
    "- Denied shell → one simple `timeout <n> <command>` attempt, then fast "
    "fallback with 'verified via orchestrator-attached output' labels. "
    "[20261021-8]"
)
QA_TRACE_20261021_11 = (
    "- Prompt-text acceptance criteria are traced, not presence-ticked. "
    "[20261021-11]"
)

# (label, path, the carrier's own anchor that must follow Clause B).
# The anchor text differs per carrier, so it cannot be one shared fragment.
QA_BASE_CARRIERS = [
    (
        "opencode-qa",
        CLAUSE_ROOT / "prompts" / "qa.md",
        "If the `webapp-verification` skill is available, load it.",
    ),
    (
        "grok-qa",
        CLAUSE_ROOT / "grok" / "agents" / "qa.md",
        "Be thorough but focused on the current deliverable's claimed functionality.",
    ),
    (
        "grok-qa-pro",
        CLAUSE_ROOT / "grok" / "agents" / "qa-pro.md",
        "- Provide PASS or FAIL grade with detailed, severity-ranked bug reports.",
    ),
]

OVERLAY_BEFORE_ANCHOR = (
    "When writing bug or issue reports to return with a FAIL grade,"
)

# Overlay QA carriers: the full-file prompt override plus the two root-added Grok
# profiles (build step 4). Each has its own following anchor.
OVERLAY_QA_CARRIERS = [
    ("overlay-fullfile-qa", OVERLAY_QA, OVERLAY_BEFORE_ANCHOR),
    (
        "overlay-grok-qa",
        OVERLAY_GROK_QA,
        "When an acceptance criterion covers prompt TEXT",
    ),
    (
        "overlay-grok-qa-pro",
        OVERLAY_GROK_QA_PRO,
        "- Provide PASS or FAIL with detailed bug reports.",
    ),
]


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


def _lines_matching(text: str, needle: str) -> list[str]:
    return [line for line in text.splitlines() if needle in line]


def _position(text: str, needle: str, path: Path) -> int:
    pos = text.find(needle)
    assert pos != -1, f"{path}: anchor missing ({needle[:60]!r})"
    return pos


def _assert_order(path: Path, first: str, second: str, label: str) -> None:
    text = _text(path)
    first_pos = _position(text, first, path)
    second_pos = _position(text, second, path)
    assert first_pos < second_pos, (
        f"{path}: expected {label} order {first[:40]!r} < {second[:40]!r}"
    )


# ---------------------------------------------------------------------------
# 1. Clause A: present exactly once per mirror
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label, path", INTROSPECTOR_MIRRORS)
def test_d1_present_exactly_once_per_mirror(label, path):
    text = _text(path)
    assert text.count(EMITTED_D1) == 1, (
        f"{label} ({path}): Clause A (20261110-1) sub-bullet must appear "
        f"exactly once with the `  - ` lead"
    )


# ---------------------------------------------------------------------------
# 2. Clause A: cross-mirror byte identity
# ---------------------------------------------------------------------------

def test_d1_byte_identical_across_mirrors():
    lines = {
        _line_containing(_text(path), D1_20261110_1)
        for _label, path in INTROSPECTOR_MIRRORS
    }
    assert len(lines) == 1, (
        "Clause A line differs across the introspector mirrors:\n"
        + "\n".join(sorted(lines))
    )
    assert lines == {EMITTED_D1}, "Clause A emitted bytes drifted from the constant"


# ---------------------------------------------------------------------------
# 3. Clause A: inside the script bullet (run parent < pass line < A < read parent)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label, path", INTROSPECTOR_MIRRORS)
def test_d1_inside_script_bullet(label, path):
    _assert_order(path, RUN_PARENT, PASS_LINE, f"{label} run-parent < pass-line")
    _assert_order(path, PASS_LINE, EMITTED_D1, f"{label} pass-line < Clause A")
    _assert_order(path, EMITTED_D1, READ_PARENT, f"{label} Clause A < read-parent")


# ---------------------------------------------------------------------------
# 4. Clause A: pass line and read parent byte-unchanged
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label, path", INTROSPECTOR_MIRRORS)
def test_pass_line_and_read_parent_unchanged(label, path):
    text = _text(path)
    pass_lines = _lines_matching(text, "  Pass `--cwd`, `--session-id`")
    assert pass_lines == [PASS_LINE], (
        f"{label} ({path}): pass line changed or duplicated: {pass_lines!r}"
    )
    read_lines = _lines_matching(text, "Read `agent-improvements.md` at the project root")
    assert read_lines == [READ_PARENT], (
        f"{label} ({path}): read-parent bullet changed or duplicated: {read_lines!r}"
    )


# ---------------------------------------------------------------------------
# 5. Clause B: present exactly once per base carrier
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label, path, _anchor", QA_BASE_CARRIERS)
def test_d2_present_exactly_once_per_base_carrier(label, path, _anchor):
    text = _text(path)
    assert text.count(EMITTED_D2) == 1, (
        f"{label} ({path}): Clause B (20261110-1) bullet must appear exactly "
        f"once with the `- ` lead"
    )


# ---------------------------------------------------------------------------
# 6. Clause B: byte identity across the base carriers
# ---------------------------------------------------------------------------

def test_d2_byte_identical_across_base_carriers():
    lines = {
        _line_containing(_text(path), D2_20261110_1)
        for _label, path, _anchor in QA_BASE_CARRIERS
    }
    assert len(lines) == 1, (
        "Clause B line differs across the QA carriers:\n" + "\n".join(sorted(lines))
    )
    assert lines == {EMITTED_D2}, "Clause B emitted bytes drifted from the constant"


# ---------------------------------------------------------------------------
# 7. Clause B: immediately after D1d, before the carrier's following anchor
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label, path, anchor", QA_BASE_CARRIERS)
def test_d2_after_d1d_before_following_anchor(label, path, anchor):
    _assert_order(path, D1D_20261021_8, EMITTED_D2, f"{label} D1d < Clause B")
    _assert_order(path, EMITTED_D2, anchor, f"{label} Clause B < following anchor")

    lines = _text(path).splitlines()
    d1d_idx = next(
        (
            i
            for i, entry in enumerate(lines)
            if D1D_20261021_8 in entry
        ),
        None,
    )
    d2_idx = next(
        (i for i, entry in enumerate(lines) if EMITTED_D2 in entry), None
    )
    assert d1d_idx is not None, f"{label} ({path}): D1d bullet missing"
    assert d2_idx is not None, f"{label} ({path}): Clause B bullet missing"
    between = lines[d1d_idx + 1 : d2_idx]
    assert all(line.strip() == "" for line in between), (
        f"{label} ({path}): Clause B is not immediately after D1d; "
        f"intervening content: {between!r}"
    )


# ---------------------------------------------------------------------------
# 8. Clause B: the D1d bullet is byte-unchanged in every base carrier
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label, path, _anchor", QA_BASE_CARRIERS)
def test_d1d_bullet_unchanged(label, path, _anchor):
    d1d_lines = _lines_matching(_text(path), D1D_20261021_8)
    assert d1d_lines == [D1D_20261021_8], (
        f"{label} ({path}): D1d denied-shell bullet changed or duplicated: "
        f"{d1d_lines!r}"
    )


# ---------------------------------------------------------------------------
# 9. Clause B: overlay carriers (full-file override + root-added Grok profiles).
#    mdu-47 @needs_overlay gate; overlay SOURCE only (build copies regenerate).
# ---------------------------------------------------------------------------

@needs_overlay
@pytest.mark.parametrize("label, path, before_anchor", OVERLAY_QA_CARRIERS)
def test_overlay_qa_carries_d2(label, path, before_anchor):
    text = _text(path)
    assert text.count(EMITTED_D2) == 1, (
        f"{label} ({path}): Clause B must appear exactly once in this overlay QA "
        "carrier (snippets are never re-applied to full-file overrides, and "
        "root-added Grok profiles are promoted as-is)"
    )
    assert _line_containing(text, D2_20261110_1) == EMITTED_D2, (
        f"{label} ({path}): Clause B bytes differ from the base carriers"
    )
    d1d_lines = _lines_matching(text, D1D_20261021_8)
    assert d1d_lines == [D1D_20261021_8], (
        f"{label} ({path}): overlay D1d denied-shell bullet changed or duplicated"
    )
    _assert_order(path, D1D_20261021_8, EMITTED_D2, f"{label} D1d < Clause B")
    _assert_order(
        path, EMITTED_D2, before_anchor, f"{label} Clause B < following anchor"
    )


# ---------------------------------------------------------------------------
# 10. Doc consistency — constants are verbatim in the design doc
# ---------------------------------------------------------------------------

DOC_CONSTANTS = [
    ("D1_20261110_1", D1_20261110_1),
    ("D2_20261110_1", D2_20261110_1),
    ("C_QA_LINE", C_QA_LINE),
    ("C_INTROSPECTOR_LINE", C_INTROSPECTOR_LINE),
]


@pytest.mark.parametrize("const_name, const", DOC_CONSTANTS)
def test_constants_match_design_doc(const_name, const):
    doc = _text(DESIGN_DOC)
    assert const in doc, (
        f"{const_name} constant drifted from {DESIGN_DOC}: {const[:60]!r}"
    )


# ---------------------------------------------------------------------------
# 11. Clause C: checklist lines present exactly once, in their sections/order
# ---------------------------------------------------------------------------

def _section(doc: str, heading: str) -> str:
    start = doc.find(heading)
    assert start != -1, f"section heading missing from brief checklist: {heading!r}"
    rest = doc[start + len(heading) :]
    nxt = rest.find("\n## ")
    return heading + (rest if nxt == -1 else rest[:nxt])


@pytest.mark.parametrize(
    "side, line",
    [("qa", C_QA_LINE), ("introspector", C_INTROSPECTOR_LINE)],
)
def test_checklist_lines_present_and_placed(side, line):
    doc = _text(BRIEF_CHECKLIST)

    assert doc.count(line) == 1, (
        f"{BRIEF_CHECKLIST}: the {side}-side brief-checklist line must appear "
        "exactly once"
    )

    if side == "qa":
        qa_section = _section(doc, "## qa")
        assert "## introspector" not in qa_section, "`## qa` section slice overran"
        assert C_QA_LINE in qa_section, (
            "QA-side checklist line is not inside the `## qa` section"
        )
        d1d_idx = qa_section.find(QA_DENIAL_20261021_8)
        c_qa_idx = qa_section.find(C_QA_LINE)
        trace_idx = qa_section.find(QA_TRACE_20261021_11)
        assert d1d_idx != -1, "`[20261021-8]` denial line missing from `## qa`"
        assert trace_idx != -1, "`[20261021-11]` trace line missing from `## qa`"
        assert d1d_idx < c_qa_idx < trace_idx, (
            "QA-side checklist line must sit after the [20261021-8] denial line and "
            "before the [20261021-11] trace line"
        )
        return

    intro_section = _section(doc, "## introspector")
    assert C_INTROSPECTOR_LINE in intro_section, (
        "introspector-side checklist line is not inside the `## introspector` section"
    )
    tail = [entry for entry in intro_section.splitlines() if entry.strip()]
    assert tail[-1] == C_INTROSPECTOR_LINE, (
        "introspector-side checklist line must be the last line of "
        f"`## introspector`; found {tail[-1]!r}"
    )
