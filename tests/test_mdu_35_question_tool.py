"""Regression contracts for MDU-35 (question-tool failure mitigation).

MDU-35 adds one bounded, ordered, loggable clause to all three orchestrator
mirrors: ask early, never leave a question pending, batch approvals into one
call, check for a dead question after a long pause, and treat an aborted
question as a dropped approval gate rather than consent.

The clause lands as a standalone ``- **QUESTION TOOL`` section placed
immediately before the ``- **Repository Ownership:**`` bullet in
``prompts/orchestrator.md``, ``grok/agents/orchestrator.md`` and the private
overlay's ``grok/agents/grokestrator.md``. It must be byte-identical across the
three sources, and two new ``ROLE_KEYWORDS["orchestrator"]`` clauses must bind
to both base mirrors so that dropping the block fails the parity fuse.

House style follows ``test_mdu_31_repo_ownership.py``: path constants, raw-text
spans for byte identity, lowercase pins for phrase presence, and a conditional
``skipif`` for the overlay sibling.

Design doc: ``docs/design/mdu-35-question-tool.md`` (test plan T1-T7).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import validate

REPO_ROOT = Path(__file__).resolve().parents[1]

ORCHESTRATOR_PROMPT = REPO_ROOT / "prompts" / "orchestrator.md"
ORCHESTRATOR_GROK = REPO_ROOT / "grok" / "agents" / "orchestrator.md"

# Private overlay sibling. Absent in a standalone clone of the public base, so
# every check against it is conditional.
OVERLAY_ROOT = REPO_ROOT.parent / "opencode_agents"
OVERLAY_GROKESTRATOR = OVERLAY_ROOT / "grok" / "agents" / "grokestrator.md"

BASE_MIRRORS = [ORCHESTRATOR_PROMPT, ORCHESTRATOR_GROK]

# The block span is delimited by its heading and the ownership bullet that
# immediately follows it in every mirror.
QUESTION_TOOL_ANCHOR = "- **QUESTION TOOL"
QUESTION_TOOL_HEADING = (
    "- **QUESTION TOOL — ASK EARLY, NEVER LEAVE ONE PENDING, "
    "NEVER TRUST A DEAD ONE:**"
)
OWNERSHIP_ANCHOR = "- **Repository Ownership:**"

# Required verbatim phrases (design doc "Pin vocabulary"). Files are lowercased
# before matching, so these are lowercase, backtick-free substrings.
PIN_PHRASES = [
    "never leave a question pending",
    "a single answer window covers them all",
    "if it died unanswered",
    "dropped approval gate, never user consent",
    "restate the outstanding questions as plain text",
    "answer by number",
    "do not silently continue",
    "left pending about 60 minutes",
]

# The same phrases in rule order (design doc T4 / review Trace C): rule 1 to
# rule 4 must appear ascending, and the hard rule is last.
ORDERED_PINS = [
    "never leave a question pending",
    "a single answer window covers them all",
    "if it died unanswered",
    "dropped approval gate, never user consent",
]

# New validator fuse clauses (design doc "validate.py additions"). Lowercase on
# purpose: ``validate_parity`` lowercases file text before matching.
MDU_35_CLAUSES = [("dead question",), ("dropped approval gate",)]


def _lower(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def _assert_pins(path: Path, label: str = "MDU-35") -> None:
    text = _lower(path)
    for phrase in PIN_PHRASES:
        assert phrase in text, f"{path.name} missing {label} phrase {phrase!r}"


def _block_span(path: Path) -> str:
    """Return the raw QUESTION TOOL section, anchor up to the ownership bullet."""
    text = path.read_text(encoding="utf-8")
    start = text.find(QUESTION_TOOL_ANCHOR)
    assert start != -1, f"{path.name} has no {QUESTION_TOOL_ANCHOR!r} section"
    assert start == 0 or text[start - 1] == "\n", (
        f"{path.name}: QUESTION TOOL anchor is not at a line start"
    )
    end = text.find(OWNERSHIP_ANCHOR, start)
    assert end != -1, (
        f"{path.name}: no {OWNERSHIP_ANCHOR!r} bullet after the QUESTION TOOL section"
    )
    return text[start:end]


def test_pin_and_clause_lists_are_the_agreed_contract() -> None:
    # Guard the guard: a shrunken pin list would silently weaken every check
    # below, and the ordering pins must be a subset of the presence pins.
    assert len(PIN_PHRASES) == 8, "MDU-35 pins exactly 8 phrases"
    assert len(ORDERED_PINS) == 4, "MDU-35 orders exactly 4 rules"
    assert all(phrase == phrase.lower() for phrase in PIN_PHRASES)
    assert all(phrase in PIN_PHRASES for phrase in ORDERED_PINS)
    assert all("`" not in phrase for phrase in PIN_PHRASES), (
        "pins must avoid inline-code spans (MDU-34 risk 6 backtick trap)"
    )
    assert MDU_35_CLAUSES == [("dead question",), ("dropped approval gate",)]
    assert all(alt == alt.lower() for clause in MDU_35_CLAUSES for alt in clause), (
        "validator clauses must be lowercase: validate_parity lowercases file text"
    )


# T1 - anchor + placement in the two base mirrors.
def test_question_tool_block_precedes_ownership_in_base_mirrors() -> None:
    for path in BASE_MIRRORS:
        assert path.exists(), f"missing {path}"
        text = path.read_text(encoding="utf-8")
        assert text.count(QUESTION_TOOL_ANCHOR) == 1, (
            f"{path.name}: expected exactly one QUESTION TOOL section"
        )
        anchor = text.find(QUESTION_TOOL_ANCHOR)
        ownership = text.find(OWNERSHIP_ANCHOR)
        assert anchor != -1, f"{path.name}: missing the QUESTION TOOL section"
        assert ownership != -1, f"{path.name}: missing the ownership bullet"
        assert anchor < ownership, (
            f"{path.name}: QUESTION TOOL section ({anchor}) must precede the "
            f"Repository Ownership bullet ({ownership})"
        )
        # Placement: heading verbatim, and only a blank line before the
        # ownership bullet (the section is a sibling block, not a sub-bullet).
        assert text[anchor:].startswith(QUESTION_TOOL_HEADING), (
            f"{path.name}: QUESTION TOOL heading is not verbatim"
        )
        assert _block_span(path).endswith("\n\n"), (
            f"{path.name}: QUESTION TOOL section is not followed by a blank line"
        )


@pytest.mark.skipif(
    not OVERLAY_GROKESTRATOR.exists(),
    reason="overlay sibling opencode_agents/ not present",
)
def test_question_tool_block_precedes_ownership_in_grokestrator() -> None:
    # The third orchestrator. Its ownership anchor is the one-line bullet, so
    # only the anchor ordering is shared with the base mirrors.
    text = OVERLAY_GROKESTRATOR.read_text(encoding="utf-8")
    assert text.count(QUESTION_TOOL_ANCHOR) == 1
    anchor = text.find(QUESTION_TOOL_ANCHOR)
    ownership = text.find(OWNERSHIP_ANCHOR)
    assert anchor != -1, f"{OVERLAY_GROKESTRATOR.name}: missing the QUESTION TOOL section"
    assert ownership != -1, f"{OVERLAY_GROKESTRATOR.name}: missing the ownership bullet"
    assert anchor < ownership
    assert text[anchor:].startswith(QUESTION_TOOL_HEADING)
    assert _block_span(OVERLAY_GROKESTRATOR).endswith("\n\n")


# T2 - pins in every source mirror.
def test_all_pins_present_in_every_source_mirror() -> None:
    for path in BASE_MIRRORS:
        _assert_pins(path)

    if not OVERLAY_GROKESTRATOR.exists():
        return
    _assert_pins(OVERLAY_GROKESTRATOR)


def test_block_carries_preamble_and_four_numbered_rules() -> None:
    # Structure pin: preamble line plus exactly four numbered rules, in the
    # order the design doc drafts them.
    sources = list(BASE_MIRRORS)
    if OVERLAY_GROKESTRATOR.exists():
        sources.append(OVERLAY_GROKESTRATOR)
    for path in sources:
        span = _block_span(path)
        for marker in ("  1. Ask early.", "  2. Batch.", "  3. After resuming", "  4. HARD RULE"):
            assert marker in span, f"{path.name}: missing rule marker {marker!r}"


# T3 - span byte identity.
def test_block_span_byte_identical_across_base_mirrors() -> None:
    spans = {path: _block_span(path) for path in BASE_MIRRORS}
    reference_path = BASE_MIRRORS[0]
    reference = spans[reference_path]
    assert reference.startswith(QUESTION_TOOL_HEADING)
    for path in BASE_MIRRORS[1:]:
        assert spans[path] == reference, (
            f"QUESTION TOOL block in {path} differs from {reference_path} "
            f"({len(spans[path])} vs {len(reference)} chars)"
        )


@pytest.mark.skipif(
    not OVERLAY_GROKESTRATOR.exists(),
    reason="overlay sibling opencode_agents/ not present",
)
def test_block_span_byte_identical_across_all_three_mirrors() -> None:
    reference = _block_span(ORCHESTRATOR_PROMPT)
    assert len(reference) > 0, "QUESTION TOOL block span is empty"
    overlaid = _block_span(OVERLAY_GROKESTRATOR)
    assert overlaid == reference, (
        f"grokestrator QUESTION TOOL block differs from the base "
        f"({len(overlaid)} vs {len(reference)} chars)"
    )


# T4 - rule ordering per mirror.
def test_rules_appear_in_ascending_order_per_mirror() -> None:
    sources = list(BASE_MIRRORS)
    if OVERLAY_GROKESTRATOR.exists():
        sources.append(OVERLAY_GROKESTRATOR)
    for path in sources:
        span = _block_span(path).lower()
        positions = [span.find(phrase) for phrase in ORDERED_PINS]
        assert all(pos != -1 for pos in positions), (
            f"{path.name}: rule pin missing inside the block; positions {positions}"
        )
        assert positions == sorted(positions), (
            f"{path.name}: rules are out of order; positions {positions} "
            f"for {ORDERED_PINS}"
        )


# T5 - validator fuse: clauses present and bound to both base mirrors.
def test_validator_fuse_clauses_present_and_bound() -> None:
    clauses = validate.ROLE_KEYWORDS["orchestrator"]
    for clause in MDU_35_CLAUSES:
        assert clause in clauses, (
            f"validate.ROLE_KEYWORDS['orchestrator'] missing MDU-35 clause {clause!r}"
        )

    # Stronger than a literal pin: at least one alternative must occur
    # (case-insensitively) in BOTH base mirrors. A clause that survives only in
    # the canonical prompt would fail this once the mirror loses the block.
    mirror_texts = [_lower(path) for path in BASE_MIRRORS]
    for clause in MDU_35_CLAUSES:
        bound = [
            alt for alt in clause if all(alt.lower() in text for text in mirror_texts)
        ]
        assert bound, (
            f"validator clause {clause!r} binds to no alternative present in both "
            f"orchestrator mirrors; it would not track the MDU-35 rule"
        )


def _parity_errors(workspace: Path, prompt_text: str, mirror_text: str) -> list[str]:
    """Run ``validate.validate_parity`` over a synthetic two-file build tree."""
    (workspace / "prompts").mkdir(parents=True, exist_ok=True)
    (workspace / "grok" / "agents").mkdir(parents=True, exist_ok=True)
    (workspace / "prompts" / "orchestrator.md").write_text(prompt_text, encoding="utf-8")
    (workspace / "grok" / "agents" / "orchestrator.md").write_text(
        mirror_text, encoding="utf-8"
    )
    return validate.validate_parity(workspace)


def _strip_question_block(text: str) -> str:
    start = text.find(QUESTION_TOOL_ANCHOR)
    end = text.find(OWNERSHIP_ANCHOR, start)
    assert start != -1 and end != -1, "cannot strip a block that is not present"
    return text[:start] + text[end:]


def test_intact_tree_passes_the_parity_fuse(tmp_path: Path) -> None:
    errors = _parity_errors(
        tmp_path,
        ORCHESTRATOR_PROMPT.read_text(encoding="utf-8"),
        ORCHESTRATOR_GROK.read_text(encoding="utf-8"),
    )
    mdu_35 = [
        error
        for error in errors
        if "dead question" in error or "dropped approval gate" in error
    ]
    assert mdu_35 == [], f"intact tree already fails the MDU-35 parity fuse: {mdu_35}"


def test_mirror_losing_the_block_fails_parity(tmp_path: Path) -> None:
    # The behavioural pin: deleting the block from the grok mirror must be
    # caught by the fuse clauses, not silently tolerated.
    errors = _parity_errors(
        tmp_path,
        ORCHESTRATOR_PROMPT.read_text(encoding="utf-8"),
        _strip_question_block(ORCHESTRATOR_GROK.read_text(encoding="utf-8")),
    )
    for clause in MDU_35_CLAUSES:
        label = "/".join(clause)
        assert any(label in error for error in errors), (
            f"parity fuse did not fire for clause {clause!r} after the grok mirror "
            f"lost the QUESTION TOOL block; errors: {errors}"
        )


def test_canonical_losing_the_block_fails_parity(tmp_path: Path) -> None:
    # Reverse direction: the fuse is symmetric, so a canonical-only deletion is
    # caught as well.
    errors = _parity_errors(
        tmp_path,
        _strip_question_block(ORCHESTRATOR_PROMPT.read_text(encoding="utf-8")),
        ORCHESTRATOR_GROK.read_text(encoding="utf-8"),
    )
    assert any("dead question" in error for error in errors), (
        f"parity fuse did not fire after the canonical prompt lost the block; "
        f"errors: {errors}"
    )


# T6 - deployed build copies (transient base build, tracked overlay build).
def _assert_build_copy(build_file: Path, source: Path) -> None:
    if not build_file.exists():
        pytest.skip(f"{build_file} not built")
    if build_file.stat().st_mtime < source.stat().st_mtime:
        pytest.skip(f"{build_file} predates {source.name} (stale build)")
    text = build_file.read_text(encoding="utf-8")
    assert QUESTION_TOOL_ANCHOR in text, f"{build_file} dropped the QUESTION TOOL block"
    lower = text.lower()
    for phrase in PIN_PHRASES:
        assert phrase in lower, f"{build_file} missing pin {phrase!r}"
    anchor = text.find(QUESTION_TOOL_ANCHOR)
    ownership = text.find(OWNERSHIP_ANCHOR)
    assert -1 < anchor < ownership, (
        f"{build_file}: QUESTION TOOL block must precede the ownership bullet"
    )


@pytest.mark.parametrize(
    "build_file",
    [
        REPO_ROOT / "build" / "grok" / "agents" / "orchestrator.md",
        REPO_ROOT / "build" / "claude" / "agents" / "orchestrator.md",
    ],
    ids=["grok", "claude"],
)
def test_base_build_copies_carry_the_block(build_file: Path) -> None:
    _assert_build_copy(build_file, ORCHESTRATOR_PROMPT)


@pytest.mark.parametrize(
    "build_file",
    [
        OVERLAY_ROOT / "build" / "grok" / "agents" / "grokestrator.md",
        OVERLAY_ROOT / "build" / "claude" / "agents" / "grokestrator.md",
    ],
    ids=["grok", "claude"],
)
def test_overlay_build_copies_carry_the_block(build_file: Path) -> None:
    _assert_build_copy(build_file, OVERLAY_GROKESTRATOR)
