"""Regression contracts for MDU-31 (Repository ownership rule for write actions).

MDU-31 pins a hard rule into both base orchestrator mirrors: commit / push /
open PRs / file issues ONLY on repositories the user owns; any third-party or
open-source repository needs explicit, per-action human approval; unclear
ownership means STOP and ask; and filing anything upstream is never a default
step of an MDU.

The rule lands as a ``- **Repository Ownership:**`` block that is a SIBLING of
the ``Human Approval Gates`` bullet list (not folded into it), placed
immediately after the last gate bullet and before ``Your responsibilities:``.
The block must be byte-identical in ``prompts/orchestrator.md`` and
``grok/agents/orchestrator.md``, and the public base must carry no personal
remote names.

``MDU_31_PHRASES`` and ``PERSONAL_NAMES`` are imported by the overlay test
module (``opencode_agents/tests/test_mdu_31_overlay_repo_ownership.py``) - one
contract, no second copy to drift.

Cheap, dependency-free checks following ``test_mdu_28_resume_detect.py``:
read the file, lowercase for phrase matching, slice raw text for the
byte-identity check.

Design doc: ``docs/design/mdu-31-repo-ownership.md`` (section 8.1).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import validate

REPO_ROOT = Path(__file__).resolve().parents[1]

ORCHESTRATOR_PROMPT = REPO_ROOT / "prompts" / "orchestrator.md"
ORCHESTRATOR_GROK = REPO_ROOT / "grok" / "agents" / "orchestrator.md"

# Private overlay sibling. Absent in a standalone clone of the public base, so
# every check against it is conditional (design doc 8.1, test 7).
OVERLAY_GROKESTRATOR = (
    REPO_ROOT.parent / "opencode_agents" / "grok" / "agents" / "grokestrator.md"
)

BASE_ORCHESTRATOR_FILES = [
    ORCHESTRATOR_PROMPT,
    ORCHESTRATOR_GROK,
]

# The ownership block span, identified by its first line and the line after it.
OWNERSHIP_ANCHOR = "- **Repository Ownership:**"
OWNERSHIP_END = "\nYour responsibilities:"

# Last Human Approval Gates bullet: the block must sit immediately after it.
LAST_GATE_BULLET = (
    "  - Require human approval before exceeding 3 fix-retries on the same issue."
)

# Required verbatim MDU-31 phrases (design doc 2.1). Files are lowercased
# before matching, so these are lowercase with straight punctuation.
MDU_31_PHRASES = [  # lowercase; file contents are lowercased before matching
    "repository ownership",
    "only on repositories the user owns",
    "per-action human approval",
    "stop and ask",
    "default step of an mdu",
    "explicit user instruction",
    "upstream",
]

# Personal remote identifiers. These must never reach the public base's
# deployed agent bodies; they belong to the private overlay only.
PERSONAL_NAMES = ["dihhuit", "jeffs_agents", "opencode_agents"]

# Orchestrator validator clauses that must still hold (MDU-23/28 era).
PRE_EXISTING_ORCHESTRATOR_CLAUSES = [
    ("mdu",),
    ("delegat",),
    ("140000",),
    ("continue this session across mdus",),
    ("cache miss",),
    ("compact and continue",),
]

# New MDU-31 validator clauses (design doc 7). Each clause is a tuple of
# alternatives; the validator passes when any alternative occurs in the body.
MDU_31_ORCHESTRATOR_CLAUSES = [
    ("repositories the user owns",),
    ("per-action human approval",),
    ("never file upstream",),
]


def _lower(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def _assert_phrases(path: Path, phrases: list[str], label: str = "MDU-31") -> None:
    text = _lower(path)
    for phrase in phrases:
        assert phrase in text, f"{path.name} missing {label} phrase {phrase!r}"


def _ownership_span(path: Path) -> str:
    """Return the raw text from the ownership anchor up to ``Your responsibilities:``."""
    text = path.read_text(encoding="utf-8")
    start = text.find(OWNERSHIP_ANCHOR)
    assert start != -1, f"{path.name} has no {OWNERSHIP_ANCHOR!r} line"
    assert start == 0 or text[start - 1] == "\n", (
        f"{path.name}: ownership anchor is not at a line start"
    )
    end = text.find(OWNERSHIP_END, start)
    assert end != -1, f"{path.name} ownership block has no 'Your responsibilities:' line after it"
    return text[start:end]


def _gate_lines(text: str) -> list[str]:
    """All "Require human approval..." gate bullets in an orchestrator prompt."""
    return [
        line.strip()
        for line in text.splitlines()
        if "Require human approval" in line
    ]


def test_phrase_and_name_lists_are_the_agreed_contract() -> None:
    # Guard the guard: dropping a phrase would silently shrink every check
    # below, and both test modules import this list.
    assert len(MDU_31_PHRASES) == 7, "MDU-31 requires exactly 7 locked phrases"
    assert len(PERSONAL_NAMES) == 3, "MDU-31 requires exactly 3 personal identifiers"
    assert all(phrase == phrase.lower() for phrase in MDU_31_PHRASES)
    assert all(name == name.lower() for name in PERSONAL_NAMES)


def test_ownership_block_present_in_both_mirrors() -> None:
    for path in BASE_ORCHESTRATOR_FILES:
        assert path.exists(), f"missing {path}"
        _assert_phrases(path, MDU_31_PHRASES)
        # The block must also carry its bold label, not just the prose.
        assert OWNERSHIP_ANCHOR.lower() in _lower(path), (
            f"{path.name} missing the {OWNERSHIP_ANCHOR!r} label"
        )


def test_ownership_block_byte_identical_across_mirrors() -> None:
    spans = {path: _ownership_span(path) for path in BASE_ORCHESTRATOR_FILES}
    reference_path = BASE_ORCHESTRATOR_FILES[0]
    reference = spans[reference_path]
    assert len(reference) > 0, "ownership block span is empty"
    for path in BASE_ORCHESTRATOR_FILES[1:]:
        assert spans[path] == reference, (
            f"ownership block in {path} differs from {reference_path} "
            f"({len(spans[path])} vs {len(reference)} chars)"
        )


def test_ownership_block_sits_after_gates_before_responsibilities() -> None:
    for path in BASE_ORCHESTRATOR_FILES:
        text = path.read_text(encoding="utf-8")
        last_gate = text.find(LAST_GATE_BULLET)
        anchor = text.find(OWNERSHIP_ANCHOR)
        responsibilities = text.find("\nYour responsibilities:")
        assert last_gate != -1, f"{path.name}: missing the last Human Approval Gates bullet"
        assert anchor != -1, f"{path.name}: missing the ownership block"
        assert responsibilities != -1, f"{path.name}: missing the responsibilities heading"
        assert last_gate < anchor < responsibilities, (
            f"{path.name}: ownership block must sit after the gates "
            f"({last_gate}) and before 'Your responsibilities:' ({responsibilities}), "
            f"found at {anchor}"
        )
        # Immediate adjacency: only a blank line may separate the last gate
        # bullet from the block (design doc 3: sibling block, one blank line).
        between = text[last_gate + len(LAST_GATE_BULLET) : anchor]
        assert between == "\n\n", (
            f"{path.name}: expected exactly one blank line between the last gate "
            f"bullet and the ownership block, got {between!r}"
        )


def test_gates_list_untouched_by_mdu_31() -> None:
    # The MDU-12 contract still holds locally (redundant with
    # test_mdu_12_06_contracts.py by design - cheap, and localizes breakage),
    # and the new block is NOT part of the four-gate list.
    canonical = ORCHESTRATOR_PROMPT.read_text(encoding="utf-8")
    mirror = ORCHESTRATOR_GROK.read_text(encoding="utf-8")

    canonical_gates = _gate_lines(canonical)
    mirror_gates = _gate_lines(mirror)
    assert len(canonical_gates) == 4, (
        f"expected exactly 4 Human Approval Gates, found {len(canonical_gates)}"
    )
    assert canonical_gates == mirror_gates
    assert "pushing to protected branches" in canonical_gates[0]
    assert "exceeding 3 fix-retries" in canonical_gates[3]

    for path in BASE_ORCHESTRATOR_FILES:
        span = _ownership_span(path)
        assert "Require human approval" not in span, (
            f"{path.name}: ownership block contains a Human Approval Gates bullet - "
            f"the rule was folded into the gates list instead of added as a sibling"
        )
        # The four sub-bullets of the block, one per required behaviour.
        sub_bullets = [
            line for line in span.splitlines() if line.startswith("  - ")
        ]
        assert len(sub_bullets) == 4, (
            f"{path.name}: expected 4 ownership sub-bullets, found {len(sub_bullets)}"
        )


def test_public_agent_bodies_leak_no_personal_names() -> None:
    # Scope: deployed agent bodies only. README.md and docs/ legitimately name
    # the base's own remote and are out of scope (design doc 8.1, test 5).
    bodies = sorted(REPO_ROOT.glob("prompts/*.md")) + sorted(
        REPO_ROOT.glob("grok/agents/*.md")
    )
    assert bodies, "no deployed agent bodies found - globs are wrong"

    for path in bodies:
        text = _lower(path)
        for name in PERSONAL_NAMES:
            assert name not in text, (
                f"{path.relative_to(REPO_ROOT)} leaks personal identifier {name!r}; "
                f"personal remotes belong in the private overlay only"
            )


def test_role_keywords_orchestrator_locks_ownership_clauses() -> None:
    clauses = validate.ROLE_KEYWORDS["orchestrator"]

    # The six pre-existing clauses stay pinned as exact tuples: membership of
    # the literal tuple is the pin (the validator accepts any clause tuple, so
    # a loosened or retyped variant would not match).
    assert len(PRE_EXISTING_ORCHESTRATOR_CLAUSES) == 6
    for clause in PRE_EXISTING_ORCHESTRATOR_CLAUSES:
        assert clause in clauses, (
            f"validate.ROLE_KEYWORDS['orchestrator'] lost pre-existing clause {clause!r}"
        )
    # The new clauses are additions, not replacements.
    for clause in MDU_31_ORCHESTRATOR_CLAUSES:
        assert clause in clauses, (
            f"validate.ROLE_KEYWORDS['orchestrator'] missing MDU-31 clause {clause!r}"
        )

    # Stronger than a literal pin: each ownership clause must have at least one
    # alternative that the validator would actually find, i.e. it occurs
    # (case-insensitively) in BOTH orchestrator mirrors. A clause matching a
    # stray word rather than the rule sentence fails here once the rule is
    # deleted, which is exactly the hole this closes.
    mirror_texts = [_lower(path) for path in BASE_ORCHESTRATOR_FILES]
    for clause in MDU_31_ORCHESTRATOR_CLAUSES:
        bound = [
            alt
            for alt in clause
            if all(alt.lower() in text for text in mirror_texts)
        ]
        assert bound, (
            f"validator clause {clause!r} binds to no alternative present in both "
            f"orchestrator mirrors; it would not track the MDU-31 rule"
        )

    # The upstream clause must exist somewhere in the orchestrator keyword set.
    assert any(
        "upstream" in alt for clause in clauses for alt in clause
    ), "no orchestrator validator clause mentions 'upstream'"


@pytest.mark.skipif(
    not OVERLAY_GROKESTRATOR.exists(),
    reason="overlay sibling opencode_agents/ not present",
)
def test_overlay_grokestrator_source_carries_generic_rule_only() -> None:
    # grokestrator is the third orchestrator and has no validator parity pair.
    # Its SOURCE carries the rule in generic form only; the personal remotes
    # arrive through the overlay global snippet at build time, so an inline
    # personal copy here would duplicate them in the built artifact.
    _assert_phrases(OVERLAY_GROKESTRATOR, MDU_31_PHRASES)
    text = _lower(OVERLAY_GROKESTRATOR)
    for name in PERSONAL_NAMES:
        count = text.count(name)
        assert count == 0, (
            f"grokestrator source contains personal identifier {name!r} "
            f"{count} time(s); it must carry the generic rule only"
        )
