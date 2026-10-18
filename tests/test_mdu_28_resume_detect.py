"""Regression contracts for MDU-28 (Resume-block recognition on the first turn).

MDU-28 replaces the SESSION BOUNDARY gate section in all three orchestrator
prompts with a deterministic first-turn rule:

1. the gate may fire only if THIS session ran an MDU loop to commit/park;
2. a resume block is recognized by purpose, not header (prose, markdown, or
   JSON with >= 2 structured keys) - only the override stays exact-phrase;
3. a commit/"done" inside a resume block is the PREVIOUS session's ending,
   proof the gate is OFF, not proof it is reached;
4. an all-blocked ``next:`` ends the turn as a normal blocked-work turn end,
   never with gate language.

The section body is required to be byte-identical in the two base orchestrator
files and in the overlay ``grokestrator`` (cross-repo sibling), because no
validator parity pair covers grokestrator (it has no ``prompts/`` stem).

Design doc: ``docs/design/mdu-28-resume-detect.md``.

Cheap, dependency-free checks, following ``test_mdu_23_session_hygiene.py``:
read the file, lowercase it, assert required substrings are present (and, for
the section span, that the three copies are byte-identical).
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

ORCHESTRATOR_PROMPT = REPO_ROOT / "prompts" / "orchestrator.md"
ORCHESTRATOR_GROK = REPO_ROOT / "grok" / "agents" / "orchestrator.md"

# Private overlay sibling. Absent in a standalone clone of the public base, so
# every check against it is conditional (design doc "Tests", cross-repo note).
OVERLAY_GROKESTRATOR = REPO_ROOT.parent / "opencode_agents" / "grok" / "agents" / "grokestrator.md"

BASE_ORCHESTRATOR_FILES = [
    ORCHESTRATOR_PROMPT,
    ORCHESTRATOR_GROK,
]

# The gate SECTION span, identified by its first and last lines. Sliced from
# raw text (not re-joined lines) so the byte-identity check is exact.
GATE_ANCHOR = "- **SESSION BOUNDARY \u2014 ONE MDU PER SESSION:**"
GATE_END = "Do not ask again this session."

# Required verbatim MDU-28 phrases (design doc "Required test phrases").
# Files are lowercased before matching, so these are lowercase with straight
# apostrophes.
MDU_28_PHRASES = [
    "own transcript and work",  # rule 1 - evidence source
    "the gate is off by construction",  # rule 1 - first-turn determinism
    "do not read pasted history as this session's history",  # rule 1 - pasted-history ban
    "recognize a resume block by purpose, not by header",  # rule 2 - purpose-based recognition
    "two or more of these keys",  # rule 2 - JSON >= 2 key threshold
    "proof the gate is off here, not proof it is reached",  # rule 3 - anti-conflation direction
    "this session's mandate is the block's",  # rule 3 - next: minus blocked_on:
    "a normal blocked-work turn end",  # rule 4 - all-blocked turn end is not a gate stop
]

# The gate must not be weakened: the hard stop, the exact-phrase-only override,
# and the explicit statement that a resume block is NOT that override.
STOP_LINE = "STOP AT THE END OF THIS MDU. DO NOT START THE NEXT MDU IN THIS SESSION."
OVERRIDE_PHRASE = "continue this session across mdus"
NOT_THE_OVERRIDE_PHRASE = "a resume block is not that phrase"

# MDU-23 phrases that must survive the MDU-28 replacement (rule 1's bold line +
# the untouched compaction/STOP contract).
MDU_23_LOCKED_PHRASES = [
    "stop at the end of this mdu",
    "must compact at 140000 once durable artifacts exist",
    "a pasted resume block in a new session is the start of work",
]

# The full resume-block key enumeration (rule 2's >= 2 structured-key
# recognition reads this set). Files are lowercased before matching.
RESUME_BLOCK_KEYS = [
    "mdu_id",
    "branch",
    "commit_sha",
    "done",
    "next",
    "blocked_on",
    "design",
    "backlog",
    "artifacts",
    "harness",
    "status",
]

# The banned gate-language example trio as actually quoted in the blocked-next
# paragraph (straight ASCII double quotes, comma-separated, closing paren).
# Anchored on the whole contiguous trio because a standalone "end of this mdu"
# also matches the required STOP line inside the same span.
BANNED_EXAMPLE_TRIO = '("stop as required", "boundary reached", "end of this mdu")'


def _lower(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def _assert_phrases(path: Path, phrases: list[str]) -> None:
    text = _lower(path)
    for phrase in phrases:
        assert phrase in text, f"{path.name} missing MDU-28 phrase {phrase!r}"


def _gate_span(path: Path) -> str:
    """Return the raw text of the SESSION BOUNDARY section, anchor to end line."""
    text = path.read_text(encoding="utf-8")
    start = text.find(GATE_ANCHOR)
    assert start != -1, f"{path.name} has no SESSION BOUNDARY anchor line"
    assert start == 0 or text[start - 1] == "\n", f"{path.name}: anchor is not at a line start"
    end = text.find(GATE_END, start)
    assert end != -1, f"{path.name} gate section has no {GATE_END!r} line"
    return text[start : end + len(GATE_END)]


def test_mdu_28_phrase_list_is_the_required_eight() -> None:
    # Guard the guard: dropping a rule from the list would silently shrink the
    # regression contract below (one phrase per required behavior).
    assert len(MDU_28_PHRASES) == 8, "MDU-28 requires exactly 8 locked phrases"


def test_base_orchestrator_files_carry_resume_detection() -> None:
    for path in BASE_ORCHESTRATOR_FILES:
        assert path.exists(), f"missing {path}"
        _assert_phrases(path, MDU_28_PHRASES)


def test_resume_detection_rules_precede_the_stop_line() -> None:
    # The first-turn/resume rules must hit the reader BEFORE the bold STOP line,
    # otherwise a first-turn resume block is read as a boundary crossing.
    for path in BASE_ORCHESTRATOR_FILES:
        text = _lower(path)
        assert text.index("recognize a resume block by purpose") < text.index(
            "stop at the end of this mdu"
        ), f"{path.name}: resume recognition must precede the STOP line"


def test_gate_still_hard_stops_and_requires_exact_override() -> None:
    files = list(BASE_ORCHESTRATOR_FILES)
    if OVERLAY_GROKESTRATOR.exists():
        files.append(OVERLAY_GROKESTRATOR)
    for path in files:
        raw = path.read_text(encoding="utf-8")
        text = raw.lower()
        assert STOP_LINE in raw, f"{path.name} missing the verbatim STOP line"
        assert OVERRIDE_PHRASE in text, f"{path.name} missing the exact override phrase"
        assert NOT_THE_OVERRIDE_PHRASE in text, (
            f"{path.name} must state a resume block is not the override phrase"
        )


@pytest.mark.skipif(
    not OVERLAY_GROKESTRATOR.exists(),
    reason="overlay sibling opencode_agents/ not present",
)
def test_overlay_grokestrator_carries_resume_detection() -> None:
    # grokestrator is the third orchestrator and has no validator parity pair,
    # so this conditional cross-repo check is the only gate on the third file.
    _assert_phrases(OVERLAY_GROKESTRATOR, MDU_28_PHRASES)


def test_gate_section_spans_are_byte_identical() -> None:
    # The replacement text is one span pasted verbatim into all three files.
    # In a standalone clone the overlay is absent and the two base files are
    # still compared; in the workspace all three must match exactly.
    files = list(BASE_ORCHESTRATOR_FILES)
    if OVERLAY_GROKESTRATOR.exists():
        files.append(OVERLAY_GROKESTRATOR)
    assert len(files) >= 2, "need at least the two base orchestrator files"

    spans = {path: _gate_span(path) for path in files}
    reference_path = files[0]
    reference = spans[reference_path]
    assert len(reference) > 0, "gate section span is empty"
    for path in files[1:]:
        assert spans[path] == reference, (
            f"gate section in {path} differs from {reference_path} "
            f"({len(spans[path])} vs {len(reference)} chars)"
        )


def test_mdu_23_locked_phrases_survive_mdu_28() -> None:
    # Cross-section interaction: MDU-28 replaced the section body, so the
    # MDU-23 contract inside it must still hold (redundant with
    # test_mdu_23_session_hygiene.py by design - cheap, and localizes breakage).
    for path in BASE_ORCHESTRATOR_FILES:
        _assert_phrases(path, MDU_23_LOCKED_PHRASES)


def test_gate_span_names_all_11_resume_keys_and_banned_example_trio() -> None:
    # Rule 2 recognition depends on the complete key enumeration, and rule 4
    # depends on the banned gate-language example trio staying in the
    # blocked-next paragraph - both checked strictly INSIDE the gate span, so
    # text elsewhere in the file cannot satisfy them.
    assert len(RESUME_BLOCK_KEYS) == 11, "resume block requires exactly 11 keys"

    files = list(BASE_ORCHESTRATOR_FILES)
    if OVERLAY_GROKESTRATOR.exists():
        files.append(OVERLAY_GROKESTRATOR)

    enumeration = ", ".join(f"`{key}`" for key in RESUME_BLOCK_KEYS)
    for path in files:
        span = _gate_span(path).lower()
        for key in RESUME_BLOCK_KEYS:
            assert f"`{key}`" in span, (
                f"{path.name} gate section missing resume-block key {key!r}"
            )
        # Presence per key is not enough: common keys (next, done, branch...)
        # appear elsewhere in the span, so a dropped key from the enumeration
        # line must still fail. The 11 keys must be one contiguous list.
        assert enumeration in span, (
            f"{path.name} gate section does not enumerate the 11 resume keys "
            f"as one contiguous list"
        )
        assert BANNED_EXAMPLE_TRIO in span, (
            f"{path.name} gate section missing the banned gate-language "
            f"example trio {BANNED_EXAMPLE_TRIO!r}"
        )


def test_session_boundary_header_appears_exactly_once_per_file() -> None:
    # _gate_span() slices from the FIRST anchor, so a duplicate header would
    # silently leave a second copy of the section untested.
    files = list(BASE_ORCHESTRATOR_FILES)
    if OVERLAY_GROKESTRATOR.exists():
        files.append(OVERLAY_GROKESTRATOR)

    anchor = GATE_ANCHOR.lower()
    for path in files:
        count = _lower(path).count(anchor)
        assert count == 1, (
            f"{path.name} has {count} SESSION BOUNDARY headers, expected exactly 1"
        )
