"""Tests for parity validation between prompts/ canons and grok/agents mirrors.

Covers ``validate.validate_parity``: the clause-presence table (Hard
constraints section, Step Limit statement, role-specific contract keywords),
tier-variant coverage, missing-mirror detection, alternative-phrase leniency
(e.g. "pass or fail grade"), graceful degradation on missing directories, and
the ``validate.main`` integration path that turns a parity violation into a
non-zero exit.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import validate

REPO_ROOT = Path(__file__).resolve().parents[1]

# Canonical prompts/ prompt that satisfies every just-code parity clause:
# "Hard constraints" + "never edit test" + Step Limit wording.
_CANONICAL_JUST_CODE = """\
You are Just Code.

Hard constraints:
- NEVER edit test files. Test files are the sole responsibility of the test-agent.

Safety constraints:
- **Step Limit:** Maximum of 50 loop steps per invocation.
"""

# Grok mirror that satisfies every just-code parity clause ("loop steps"
# phrasing instead of "Step Limit", per the mirror leniency rule).
_MIRROR_JUST_CODE = """\
---
name: just-code
model: grok-4.6
---
You are Just Code (grok mirror).

Hard constraints:
- Never edit test files.

Safety constraints:
- Maximum of 50 loop steps per invocation.
"""


def _write(build: Path, rel: str, text: str) -> Path:
    """Write a file into the synthetic build dir, creating parents."""
    path = build / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _mirror(name: str) -> str:
    """An otherwise-consistent grok just-code mirror with the given frontmatter name."""
    return _MIRROR_JUST_CODE.replace("name: just-code", f"name: {name}")


def _just_code_build(tmp_path: Path) -> Path:
    """Build dir with a consistent canonical + all three just-code tier mirrors."""
    build = tmp_path / "build"
    _write(build, "prompts/just-code.md", _CANONICAL_JUST_CODE)
    for mirror in ("just-code", "just-code-mid", "just-code-pro"):
        _write(build, f"grok/agents/{mirror}.md", _mirror(mirror))
    return build


# ---------------------------------------------------------------------------
# consistent pair
# ---------------------------------------------------------------------------

def test_consistent_pair_has_no_errors(tmp_path: Path) -> None:
    build = _just_code_build(tmp_path)
    assert validate.validate_parity(build) == []


# ---------------------------------------------------------------------------
# grok mirror missing a required clause
# ---------------------------------------------------------------------------

def test_grok_mirror_missing_clause_error_format(tmp_path: Path) -> None:
    build = _just_code_build(tmp_path)
    # Mirror drops the "never edit test" contract.
    _write(
        build,
        "grok/agents/just-code.md",
        _mirror("just-code").replace(
            "Never edit test files.", "You do not author tests yourself."
        ),
    )
    errors = validate.validate_parity(build)
    assert errors == [
        "grok mirror grok/agents/just-code.md missing never edit test "
        "present in prompts/just-code.md"
    ]


def test_canonical_missing_clause_flags_canonical_side(tmp_path: Path) -> None:
    build = _just_code_build(tmp_path)
    # Canonical loses its "Hard constraints" section while the mirror keeps it.
    _write(
        build,
        "prompts/just-code.md",
        "You are Just Code.\n\n"
        "Hardline rules:\n"
        "- NEVER edit test files.\n\n"
        "Safety constraints:\n"
        "- **Step Limit:** Maximum of 50 loop steps per invocation.\n",
    )
    errors = validate.validate_parity(build)
    # The canonical-clause gap is flagged once per checked mirror pair.
    assert len(errors) == 3
    assert all(err.startswith("prompts/just-code.md missing Hard constraints section") for err in errors)
    assert (
        "prompts/just-code.md missing Hard constraints section "
        "present in grok/agents/just-code.md" in errors[0]
    )


# ---------------------------------------------------------------------------
# Step Limit / loop steps leniency
# ---------------------------------------------------------------------------

def test_missing_step_limit_statement_flagged(tmp_path: Path) -> None:
    build = _just_code_build(tmp_path)
    # Mirror keeps "Hard constraints" but loses both "safety constraints" and
    # the "loop steps" phrasing, so the Step Limit statement is one-sided.
    _write(
        build,
        "grok/agents/just-code.md",
        _mirror("just-code").replace("Safety constraints:", "Constraints:")
        .replace(
            "Maximum of 50 loop steps per invocation.",
            "You must wrap up by step 50.",
        ),
    )
    errors = validate.validate_parity(build)
    assert errors == [
        "grok mirror grok/agents/just-code.md missing Step Limit statement "
        "present in prompts/just-code.md"
    ]


def test_loop_steps_phrasing_acceptable_in_both_sides(tmp_path: Path) -> None:
    # Canonical says "loop steps", mirror says "safety constraints + loop
    # steps": the lenient check must accept either phrasing on either side.
    build = _just_code_build(tmp_path)
    _write(
        build,
        "prompts/just-code.md",
        "Hard constraints:\n- NEVER edit test files.\n\n"
        "Safety constraints:\n- Maximum of 50 loop steps per invocation.\n",
    )
    _write(
        build,
        "grok/agents/just-code.md",
        "Hard constraints:\n- Never edit test files.\n\n"
        "Safety constraints:\n- **Step Limit:** Maximum of 50 loop steps.\n",
    )
    assert validate.validate_parity(build) == []


# ---------------------------------------------------------------------------
# missing mirror file
# ---------------------------------------------------------------------------

def test_missing_grok_mirror_file_flagged(tmp_path: Path) -> None:
    build = tmp_path / "build"
    (build / "grok" / "agents").mkdir(parents=True)
    _write(
        build,
        "prompts/research.md",
        "Research agent.\n\nHard constraints:\n- Never write or edit files.\n\n"
        "Safety constraints:\n- **Step Limit:** Maximum of 50 loop steps.\n",
    )
    errors = validate.validate_parity(build)
    assert errors == [
        "grok mirror grok/agents/research.md missing "
        "(expected for prompts/research.md)"
    ]


# ---------------------------------------------------------------------------
# tier variants checked individually
# ---------------------------------------------------------------------------

def test_tier_variant_parity_flagged_individually(tmp_path: Path) -> None:
    build = tmp_path / "build"
    _write(build, "prompts/just-code.md", _CANONICAL_JUST_CODE)
    _write(build, "grok/agents/just-code.md", _MIRROR_JUST_CODE)
    # Only the mid variant drifts: it loses the "never edit test" contract.
    _write(
        build,
        "grok/agents/just-code-mid.md",
        _mirror("just-code-mid").replace(
            "Never edit test files.", "You do not author tests yourself."
        ),
    )
    _write(build, "grok/agents/just-code-pro.md", _mirror("just-code-pro"))
    errors = validate.validate_parity(build)
    assert len(errors) == 1
    assert "grok/agents/just-code-mid.md" in errors[0]
    assert "missing never edit test" in errors[0]


# ---------------------------------------------------------------------------
# alternative-phrase leniency for qa clauses
# ---------------------------------------------------------------------------

def test_qa_alternative_phrase_pass_or_fail_grade_satisfies_clauses(
    tmp_path: Path,
) -> None:
    # (a) The real qa.md / qa-pro.md wording ("PASS grade, or a FAIL grade")
    # satisfies the qa parity clauses verbatim.
    real = tmp_path / "real"
    _write(real, "prompts/qa.md", (REPO_ROOT / "prompts/qa.md").read_text(encoding="utf-8"))
    _write(real, "grok/agents/qa.md", (REPO_ROOT / "grok/agents/qa.md").read_text(encoding="utf-8"))
    _write(real, "grok/agents/qa-pro.md", (REPO_ROOT / "grok/agents/qa-pro.md").read_text(encoding="utf-8"))
    assert validate.validate_parity(real) == []

    # (b) The "pass or fail grade" alternative phrase satisfies the same
    # clauses even when the two sides use different alternatives.
    alt = tmp_path / "alt"
    _write(
        alt,
        "prompts/qa.md",
        "You provide a PASS grade, or a FAIL grade for the deliverable.\n\n"
        "Hard constraints:\n- Bug reports must include reproduction steps.\n\n"
        "Safety constraints:\n- **Step Limit:** Maximum of 50 loop steps.\n",
    )
    _write(
        alt,
        "grok/agents/qa.md",
        "You provide a pass or fail grade for the deliverable.\n\n"
        "Hard constraints:\n- Bug reports must include reproduction steps.\n\n"
        "Safety constraints:\n- Maximum of 50 loop steps.\n",
    )
    _write(
        alt,
        "grok/agents/qa-pro.md",
        "You provide a pass or fail grade for the deliverable.\n\n"
        "Hard constraints:\n- Bug reports must include reproduction steps.\n\n"
        "Safety constraints:\n- Maximum of 50 loop steps.\n",
    )
    assert validate.validate_parity(alt) == []


# ---------------------------------------------------------------------------
# real orchestrator pair (CI-gate drift guard)
# ---------------------------------------------------------------------------

def test_real_orchestrator_pair_consistent(tmp_path: Path) -> None:
    """The real prompts/orchestrator.md + grok/agents/orchestrator.md pair must
    keep passing validate_parity; a regression here means the CI gate itself
    drifted from the prompts."""
    build = tmp_path / "build"
    _write(
        build,
        "prompts/orchestrator.md",
        (REPO_ROOT / "prompts/orchestrator.md").read_text(encoding="utf-8"),
    )
    _write(
        build,
        "grok/agents/orchestrator.md",
        (REPO_ROOT / "grok/agents/orchestrator.md").read_text(encoding="utf-8"),
    )
    assert validate.validate_parity(build) == []


# ---------------------------------------------------------------------------
# graceful degradation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "paths",
    [
        (),
        ("prompts",),
        ("grok/agents",),
        ("prompts", "grok/agents"),
    ],
)
def test_validate_parity_graceful_when_dirs_missing(
    tmp_path: Path, paths: tuple[str, ...]
) -> None:
    build = tmp_path / "build"
    build.mkdir()
    for rel in paths:
        (build / rel).mkdir(parents=True)
    assert validate.validate_parity(build) == []


# ---------------------------------------------------------------------------
# validate.main integration
# ---------------------------------------------------------------------------

def test_validate_main_exits_one_on_parity_violation(
    tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    build = tmp_path / "build"
    _write(build, "prompts/just-code.md", _CANONICAL_JUST_CODE)
    _write(
        build,
        "grok/agents/just-code.md",
        _MIRROR_JUST_CODE.replace(
            "Never edit test files.", "You do not author tests yourself."
        ),
    )
    _write(
        build,
        "claude/agents/test.md",
        "---\nname: test-agent\ndescription: \"test agent\"\n---\n",
    )
    (build / "opencode.json").write_text(
        json.dumps(
            {
                "agent": {
                    "test-agent": {
                        "mode": "subagent",
                        "description": "test agent",
                        "model": "model-a",
                        "prompt": "{file:./prompts/just-code.md}",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    snapshot = tmp_path / "model-registry.txt"
    snapshot.write_text("model-a\n", encoding="utf-8")
    monkeypatch.setattr(validate, "DEFAULT_SNAPSHOT", snapshot)

    code = validate.main([str(build)])
    out = capsys.readouterr().out
    assert code == 1
    assert "[fail]" in out
    assert (
        "grok mirror grok/agents/just-code.md missing never edit test "
        "present in prompts/just-code.md" in out
    )