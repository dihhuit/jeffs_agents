"""Regression contracts for MDU-15 (inline run-manifest schema in the orchestrator).

MDU-15 moves the run-ledger contract out of ``docs/observability.md`` and into a
single contiguous block at the end of the responsibilities list in BOTH base
orchestrator mirrors, so a headless CLI in a bare scratch workspace can conform
with zero external lookup. ``scripts/lib/run_ledger.py`` stays the single source
of truth: this module cross-checks the prompt's field lists, enum values, and
compact example against its module constants, so changing one without the other
turns red.

House style follows ``test_mdu_31_repo_ownership.py``: path constants, lowercase
phrase matching, raw-text span slicing for byte-identity, literal clause-tuple
membership plus a binding check.

``MDU_15_PHRASES`` is imported by the overlay test module
(``opencode_agents/tests/test_mdu_15_overlay_run_ledger_inline.py``) - one
contract, no second copy to drift.

Design doc: ``docs/design/mdu-15-run-ledger-schema-inline.md`` (section 6.1).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import run_ledger
import validate

REPO_ROOT = Path(__file__).resolve().parents[1]

ORCHESTRATOR_PROMPT = REPO_ROOT / "prompts" / "orchestrator.md"
ORCHESTRATOR_GROK = REPO_ROOT / "grok" / "agents" / "orchestrator.md"

BASE_ORCHESTRATOR_FILES = [
    ORCHESTRATOR_PROMPT,
    ORCHESTRATOR_GROK,
]

OBSERVABILITY_DOC = REPO_ROOT / "docs" / "observability.md"

# The ledger block span: from its headline line up to (exclusive) the next
# "Hard constraints:" heading. The block is the last responsibilities item.
BLOCK_ANCHOR = "- **Maintain a run ledger per MDU"
BLOCK_END = "\nHard constraints:"

# The seven pre-MDU-15 bullets that the inline block replaced.
OLD_DOC_POINTER = "for the full schema"
OLD_PHASE_BULLET = (
    "Append a phase entry (`phase`, `agent`, `model_tier`, `outcome`, `notes`) "
    "to `phases` as each phase completes."
)

# Required verbatim MDU-15 phrases (design doc 2.1). Files are lowercased
# before matching, so these are lowercase with straight punctuation.
MDU_15_PHRASES = [  # lowercase; file contents are lowercased before matching
    "maintain a run ledger per mdu",
    "no external doc is needed",
    "the final status is `completed`, never `complete`",
    "never free text like `manual-smoke-pass`",
    'never `"n/a"`',
    "never `0` when phase notes describe a fix cycle",
    "the cli you are running in",
    "must exit 0",
    "copy the shape, not the values",
    "in_progress|completed|failed|escalated",
    "run_ledger.py validate",
    "finalize every remaining field",
]

# Orchestrator validator clauses that must still hold (MDU-23/28/31 era).
PRE_EXISTING_ORCHESTRATOR_CLAUSES = [
    ("mdu",),
    ("delegat",),
    ("140000",),
    ("continue this session across mdus",),
    ("cache miss",),
    ("compact and continue",),
    ("repositories the user owns",),
    ("per-action human approval",),
    ("never file upstream",),
]

# New MDU-15 validator clauses (design doc 5). Each clause is a tuple of
# alternatives; the validator passes when any alternative occurs in the body.
MDU_15_ORCHESTRATOR_CLAUSES = [
    ("run ledger",),
    ("run_ledger.py validate",),
    ("qa_grade",),
    ("model_tier",),
    ("fix_iterations",),
    ("in_progress",),
]

# ``_validate_phase`` hardcodes the entry keys instead of exporting a constant;
# the example test below cross-checks them transitively against the validator.
PHASE_ENTRY_FIELDS = {"phase", "agent", "model_tier", "outcome", "notes"}

ENUM_KEYS = {
    "status": run_ledger.STATUSES,
    "harness": run_ledger.HARNESSES,
    "phases[].phase": run_ledger.PHASES,
    "phases[].model_tier": run_ledger.MODEL_TIERS,
    "phases[].outcome": run_ledger.OUTCOMES,
}

BACKTICK_TOKEN = re.compile(r"`([^`]+)`")
ENUM_PAIR = re.compile(r"`([a-z_.\[\]]+)`: `([^`]+)`")
JSON_FENCE = re.compile(r"```json\s*\n(.*?)\n\s*```", re.DOTALL)


def _lower(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def _assert_phrases(path: Path, phrases: list[str]) -> None:
    text = _lower(path)
    missing = [phrase for phrase in phrases if phrase not in text]
    assert not missing, f"{path.name} missing MDU-15 phrases {missing}"


def _block_span(path: Path) -> str:
    """Return the raw text from the ledger anchor up to ``Hard constraints:``."""
    text = path.read_text(encoding="utf-8")
    start = text.find(BLOCK_ANCHOR)
    assert start != -1, f"{path.name} has no {BLOCK_ANCHOR!r} line"
    assert start == 0 or text[start - 1] == "\n", (
        f"{path.name}: ledger anchor is not at a line start"
    )
    end = text.find(BLOCK_END, start)
    assert end != -1, (
        f"{path.name}: ledger block has no 'Hard constraints:' line after it"
    )
    return text[start:end]


def _block_line(path: Path, label: str) -> str:
    """The single line of the ledger block carrying ``label``."""
    lines = [line for line in _block_span(path).splitlines() if label in line]
    assert len(lines) == 1, (
        f"{path.name}: expected exactly one ledger line containing {label!r}, "
        f"found {len(lines)}"
    )
    return lines[0]


def _values_after_label(line: str, label: str) -> set[str]:
    _, _, tail = line.partition(label)
    return set(BACKTICK_TOKEN.findall(tail))


def _enum_values(path: Path) -> dict[str, set[str]]:
    line = _block_line(path, "Allowed values:")
    pairs = ENUM_PAIR.findall(line)
    assert pairs, f"{path.name}: Allowed values line has no `key`: `value` pairs"
    return {key: set(value.split("|")) for key, value in pairs}


def test_phrase_list_is_the_agreed_contract() -> None:
    # Guard the guard: dropping a phrase would silently shrink every check
    # below, and the overlay test module imports this list.
    assert len(MDU_15_PHRASES) == 12, "MDU-15 requires exactly 12 locked phrases"
    assert all(phrase == phrase.lower() for phrase in MDU_15_PHRASES)
    assert len(PRE_EXISTING_ORCHESTRATOR_CLAUSES) == 9
    assert len(MDU_15_ORCHESTRATOR_CLAUSES) == 6


def test_ledger_block_present_in_both_mirrors() -> None:
    for path in BASE_ORCHESTRATOR_FILES:
        assert path.exists(), f"missing {path}"
        assert BLOCK_ANCHOR.lower() in _lower(path), (
            f"{path.name} missing the {BLOCK_ANCHOR!r} headline"
        )
        _assert_phrases(path, MDU_15_PHRASES)


def test_ledger_block_byte_identical_across_mirrors() -> None:
    spans = {path: _block_span(path) for path in BASE_ORCHESTRATOR_FILES}
    for path in BASE_ORCHESTRATOR_FILES:
        text = path.read_text(encoding="utf-8")
        count = text.count(BLOCK_ANCHOR)
        assert count == 1, (
            f"{path.name}: ledger anchor appears {count}x, expected exactly 1"
        )
        assert spans[path], f"{path.name}: ledger block span is empty"

    reference_path = BASE_ORCHESTRATOR_FILES[0]
    reference = spans[reference_path]
    for path in BASE_ORCHESTRATOR_FILES[1:]:
        assert spans[path] == reference, (
            f"ledger block in {path} differs from {reference_path} "
            f"({len(spans[path])} vs {len(reference)} chars)"
        )


def test_old_bullets_and_doc_pointer_removed() -> None:
    for path in BASE_ORCHESTRATOR_FILES:
        text = path.read_text(encoding="utf-8")
        for stale in (OLD_DOC_POINTER, OLD_PHASE_BULLET, "observability.md"):
            assert stale not in text, (
                f"{path.name} still contains {stale!r}; the inline contract must "
                f"replace the removed bullets and need no external lookup"
            )


def test_inline_required_fields_line_matches_run_ledger() -> None:
    expected = set(run_ledger.REQUIRED_FIELDS)
    for path in BASE_ORCHESTRATOR_FILES:
        line = _block_line(path, "Required fields:")
        found = set(BACKTICK_TOKEN.findall(line))
        assert found == expected, (
            f"{path.name}: inline Required fields {sorted(found)} != "
            f"run_ledger.REQUIRED_FIELDS {sorted(expected)}"
        )


def test_inline_verification_fields_line_matches_run_ledger() -> None:
    expected = set(run_ledger.REQUIRED_VERIFICATION_FIELDS)
    for path in BASE_ORCHESTRATOR_FILES:
        line = _block_line(path, "`verification` fields:")
        found = _values_after_label(line, "fields:")
        assert found == expected, (
            f"{path.name}: inline verification fields {sorted(found)} != "
            f"run_ledger.REQUIRED_VERIFICATION_FIELDS {sorted(expected)}"
        )


def test_inline_phases_entry_fields_pinned() -> None:
    for path in BASE_ORCHESTRATOR_FILES:
        line = _block_line(path, "`phases[]` entry fields:")
        found = _values_after_label(line, "fields:")
        assert found == PHASE_ENTRY_FIELDS, (
            f"{path.name}: inline phases[] entry fields {sorted(found)} != "
            f"{sorted(PHASE_ENTRY_FIELDS)}"
        )


def test_inline_enums_match_run_ledger_constants() -> None:
    # The no-drift fuse: change a code enum without the prompt -> red.
    expected_keys = set(ENUM_KEYS) | {"verification.qa_grade"}
    for path in BASE_ORCHESTRATOR_FILES:
        values = _enum_values(path)
        assert set(values) == expected_keys, (
            f"{path.name}: inline enum keys {sorted(values)} != {sorted(expected_keys)}"
        )
        for key, constant in ENUM_KEYS.items():
            assert values[key] == set(constant), (
                f"{path.name}: inline {key} values {sorted(values[key])} != "
                f"run_ledger constant {sorted(constant)}"
            )
        grade = values["verification.qa_grade"]
        # ``null`` in the prompt is the pre-QA state for the code's None.
        assert "null" in grade, (
            f"{path.name}: verification.qa_grade must offer the null alternative"
        )
        assert grade - {"null"} == {v for v in run_ledger.QA_GRADES if v is not None}, (
            f"{path.name}: qa_grade values {sorted(grade)} do not match "
            f"run_ledger.QA_GRADES (plus null)"
        )


def test_inline_example_is_valid_manifest() -> None:
    for path in BASE_ORCHESTRATOR_FILES:
        match = JSON_FENCE.search(_block_span(path))
        assert match is not None, f"{path.name}: no ```json example in the ledger block"
        example = json.loads(match.group(1))

        missing = [field for field in run_ledger.REQUIRED_FIELDS if field not in example]
        assert not missing, (
            f"{path.name}: inline example is missing required fields {missing}"
        )
        assert run_ledger.validate_manifest(example) == [], (
            f"{path.name}: inline example fails run_ledger.validate_manifest: "
            f"{run_ledger.validate_manifest(example)}"
        )


def test_role_keywords_orchestrator_locks_ledger_clauses() -> None:
    clauses = validate.ROLE_KEYWORDS["orchestrator"]

    # The nine pre-existing clauses stay pinned as exact tuples: membership of
    # the literal tuple is the pin (the validator accepts any clause tuple, so
    # a loosened or retyped variant would not match).
    for clause in PRE_EXISTING_ORCHESTRATOR_CLAUSES:
        assert clause in clauses, (
            f"validate.ROLE_KEYWORDS['orchestrator'] lost pre-existing clause {clause!r}"
        )
    # The new clauses are additions, not replacements.
    for clause in MDU_15_ORCHESTRATOR_CLAUSES:
        assert clause in clauses, (
            f"validate.ROLE_KEYWORDS['orchestrator'] missing MDU-15 clause {clause!r}"
        )

    # Stronger than a literal pin: each ledger clause must have at least one
    # alternative that the validator would actually find, i.e. it occurs
    # (case-insensitively) in BOTH orchestrator mirrors.
    mirror_texts = [_lower(path) for path in BASE_ORCHESTRATOR_FILES]
    for clause in MDU_15_ORCHESTRATOR_CLAUSES:
        bound = [
            alt
            for alt in clause
            if all(alt.lower() in text for text in mirror_texts)
        ]
        assert bound, (
            f"validator clause {clause!r} binds to no alternative present in both "
            f"orchestrator mirrors; it would not track the MDU-15 contract"
        )


def test_docs_observability_names_the_inline_location() -> None:
    assert OBSERVABILITY_DOC.is_file(), f"missing {OBSERVABILITY_DOC}"
    text = OBSERVABILITY_DOC.read_text(encoding="utf-8")
    assert "prompts/orchestrator.md" in text, (
        "docs/observability.md must name the inline location (prompts/orchestrator.md)"
    )
    assert "run_ledger.py" in text, (
        "docs/observability.md must still name run_ledger.py as the source of truth"
    )
