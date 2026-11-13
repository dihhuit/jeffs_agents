"""MDU-62 two-tier PR/push policy: clause, census, and no-PR-mandate pins.

The policy rule is: on repositories the user owns, no PR is required — push the
branch or push directly to ``main``; on any other remote, explicit per-action
human approval comes BEFORE a PR or a branch push. The carrier set is ONE source
file (``skills/git-autonomy/SKILL.md``); the orchestrator mirrors are deliberately
un-edited, so they are pinned in the negative (no PR mandate) rather than the
positive.

Constants below are the byte-identity authority (mdu-49/mdu-60 convention): they
hold the design doc's §2a clause lines and §2b guard verbatim. Specimen pins
(``skills/`` and the design doc) resolve through ``MDU62_TEST_ROOT``, so the
mutation matrix (design §5) can point the suite at a /tmp copy with exactly one
piece of the clause stripped. Repo-state pins (orchestrator mirrors, overlay
sibling census) always read the real repository, because the mutation copies
never contain them.

Hermetic: file reads only — no network, no git calls, no writes, no secrets.
Paths resolve from ``Path(__file__)`` so the suite is cwd-independent, exactly
like ``test_mdu_59_dispatch_truth.py`` and ``test_mdu_60_qa_write_access.py``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
OVERLAY_ROOT = REPO_ROOT.parent / "opencode_agents"
HAS_OVERLAY = OVERLAY_ROOT.is_dir()

# Specimen root: overridable for the mutation matrix (design §5). Defaults to the
# real repo, so the shipped suite and the mutant runs share one code path.
TEST_ROOT = Path(os.environ.get("MDU62_TEST_ROOT", str(REPO_ROOT))).resolve()

# ---------------------------------------------------------------------------
# Constants — verbatim from the design doc (§2a fence, §2b guard).
# ---------------------------------------------------------------------------

CLAUSE_LINES = (
    "- **Two-tier push policy:** On repositories the user owns, no PR is required — "
    "push the branch or push directly to `main` (the sanctioned default-green path); "
    "the existing secret and prompt gates still apply, and if `main` is branch-protected "
    "the protected-branch approval rule still applies.",
    "- On any other remote (OSS, third-party, or unclear ownership), obtain explicit "
    "per-action human approval BEFORE opening a PR or pushing any branch; one approval "
    "never covers the next action.",
)
TIER1_LINE, TIER2_LINE = CLAUSE_LINES
TIER1_MARKER = "- **Two-tier push policy:**"
TIER2_MARKER = "- On any other remote"

GUARD_LINE = (
    "Only when a PR is actually required under Push safety (any remote you do not own, "
    "or an explicit user request). Include:"
)

# Lowercased fragment of the retired :39 sentence — the PR-by-default directive.
OLD_DIRECTIVE = "push the feature branch and open the pr"
OLD_SENTENCE = (
    "- Push the feature branch and open the PR; do not push directly to `main` unless "
    "the project explicitly allows it."
)

# Distinctive marker of the shipped two-tier clause (census signal).
CLAUSE_MARKER = "two-tier push policy"

# §2c state pin: the load-trigger description line must not change.
DESCRIPTION_LINE = (
    "description: Branch, commit, and PR hygiene for autonomous runs — feature branch "
    "per MDU, conventional commit subjects with the MDU id, sign-off discipline, PR "
    "description contents, and push safety rules. Load when committing or opening a PR "
    "for completed work."
)

PUSH_SAFETY = "## Push safety"
CHECKLIST = "## Checklist before commit"
PR_SECTION = "## PR description"
OWNERSHIP_MARKER = "**Repository Ownership:**"

# Phrases that would re-mandate a PR from the ownership block (design §4). The
# mirrors may say "open PRs" as part of "commit, push, open PRs ONLY on owned
# repos" — that is an ownership boundary, not a PR mandate.
PR_MANDATE_FRAGMENTS = ("open a pull request", "open a pr")

SKILL = TEST_ROOT / "skills" / "git-autonomy" / "SKILL.md"
DESIGN_DOC = TEST_ROOT / "docs" / "design" / "mdu-62-pr-policy.md"

# Repo-state pins: real repo only (the /tmp mutants do not carry these files).
# Third carrier is the overlay sibling; absent in a standalone clone of the base.
GROKESTRATOR = OVERLAY_ROOT / "grok" / "agents" / "grokestrator.md"
MIRRORS = [
    pytest.param(REPO_ROOT / "prompts" / "orchestrator.md", id="opencode"),
    pytest.param(REPO_ROOT / "grok" / "agents" / "orchestrator.md", id="grok"),
    pytest.param(
        GROKESTRATOR,
        id="grokestrator",
        marks=pytest.mark.skipif(
            not GROKESTRATOR.is_file(), reason="overlay sibling not present"
        ),
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text(path: Path, root: Path | tuple[Path, ...] = TEST_ROOT) -> str:
    """Read a specimen file, refusing any path that escapes its declared root(s)."""
    roots = root if isinstance(root, tuple) else (root,)
    resolved = path.resolve()
    assert any(resolved.is_relative_to(r.resolve()) for r in roots), (
        f"specimen path escaped its root(s) {roots}: {resolved}"
    )
    assert resolved.is_file(), f"missing specimen target: {resolved}"
    return resolved.read_text(encoding="utf-8")


def _between(text: str, start: str, end: str) -> str:
    start_idx = text.find(start)
    assert start_idx != -1, f"section heading missing: {start!r}"
    end_idx = text.find(end, start_idx + len(start))
    assert end_idx != -1, f"section heading missing: {end!r}"
    return text[start_idx:end_idx]


def _skill_files(root: Path) -> list[Path]:
    """Every live SKILL.md under ``<root>/skills``; built copies are regenerated."""
    files = sorted((root / "skills").rglob("SKILL.md"))
    assert files, f"no SKILL.md found under {root / 'skills'} — vacuous census"
    return files


def _ownership_span(path: Path) -> str:
    """The Repository Ownership block of an orchestrator mirror."""
    text = _text(path, root=(REPO_ROOT, OVERLAY_ROOT))
    start = text.find(OWNERSHIP_MARKER)
    assert start != -1, f"{path}: Repository Ownership block missing"
    rest = text[start:]
    end = len(rest)
    for stop in ("\nYour responsibilities", "\n\n## ", "\n\n- **", "\n\n*"):
        idx = rest.find(stop, len(OWNERSHIP_MARKER))
        if idx != -1:
            end = min(end, idx)
    span = rest[:end]
    assert "per-action human approval" in span.lower(), (
        f"{path}: extracted span is not the ownership block: {span[:120]!r}"
    )
    return span


# ---------------------------------------------------------------------------
# 1. Doc consistency — the constants are verbatim in the design doc §2a fence
# ---------------------------------------------------------------------------

def test_clause_constant_matches_design_doc():
    section_2a = _between(_text(DESIGN_DOC), "**2a.", "**2b.")
    for line in CLAUSE_LINES:
        assert line in section_2a, (
            f"CLAUSE_LINES drifted from the design doc §2a fence: {line[:70]!r}"
        )


# ---------------------------------------------------------------------------
# 2. Clause present exactly once, inside Push safety (non-vacuous: asserts TEXT)
# ---------------------------------------------------------------------------

def _bullets(text: str, prefix: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith(prefix)]


def test_two_tier_clause_present_once_in_push_safety():
    """Both tier bullets appear exactly once, inside ``## Push safety``.

    Located by bullet marker, not by full bytes: the fragment-level scenario
    pins (cases 4/5) own the wording, so a stripped phrase reds exactly the pin
    that names it (design §5 M3).
    """
    text = _text(SKILL)
    push_block = _between(text, PUSH_SAFETY, CHECKLIST)
    for marker in (TIER1_MARKER, TIER2_MARKER):
        found = _bullets(text, marker)
        assert len(found) == 1, (
            f"{SKILL}: expected exactly one {marker!r} bullet, found {len(found)}"
        )
        assert found[0] in push_block, (
            f"{SKILL}: {marker!r} bullet must sit inside `## Push safety`"
        )
    tier1 = _bullets(text, TIER1_MARKER)[0]
    assert tier1.rstrip().endswith("protected-branch approval rule still applies."), (
        f"{SKILL}: tier-1 tail reworded: {tier1[-80:]!r}"
    )
    assert OLD_DIRECTIVE not in text.lower(), (
        f"{SKILL}: the retired PR-by-default directive is still present"
    )
    assert OLD_SENTENCE not in text, (
        f"{SKILL}: the retired :39 sentence is still present verbatim"
    )


# ---------------------------------------------------------------------------
# 3. Census: no skill body re-mandates a PR by default (design §3)
# ---------------------------------------------------------------------------

def test_census_no_pr_by_default_directive_in_any_skill():
    offenders = [
        str(path.relative_to(TEST_ROOT))
        for path in _skill_files(TEST_ROOT)
        if OLD_DIRECTIVE in path.read_text(encoding="utf-8").lower()
    ]
    assert offenders == [], (
        "PR-by-default directive leaked back into a live skill body: " + repr(offenders)
    )
    assert CLAUSE_MARKER in _text(SKILL).lower(), (
        f"{SKILL}: the two-tier clause marker is missing"
    )


# ---------------------------------------------------------------------------
# 4. Scenario: owned repositories → no PR, direct push (census req 3a)
# ---------------------------------------------------------------------------

def test_scenario_owned_repo_no_pr_direct_push():
    """In the user's deployment ``dihhuit/*`` are the owned remotes (mdu-31 plus

    the overlay snippet), so this pin is the dihhuit → no-PR scenario: the tier
    is keyed to ownership, and the deployment maps ownership onto dihhuit.
    """
    text = _text(SKILL)
    assert TIER1_LINE in text, f"{SKILL}: tier-1 (owned-repo) line missing"
    for fragment in (
        "repositories the user owns",
        "no PR is required",
        "push directly to `main`",
        "default-green path",
        "secret and prompt gates",
        "branch-protected",
    ):
        assert fragment in TIER1_LINE, (
            f"owned-repo tier lost fragment {fragment!r}: {TIER1_LINE[:90]!r}"
        )


# ---------------------------------------------------------------------------
# 5. Scenario: any other remote → approval first (census req 3b)
# ---------------------------------------------------------------------------

def test_scenario_any_other_remote_approval_first():
    text = _text(SKILL)
    assert TIER2_LINE in text, f"{SKILL}: tier-2 (third-party) line missing"
    for fragment in (
        "any other remote",
        "explicit per-action human approval",
        "BEFORE opening a PR or pushing any branch",
        "one approval never covers the next action",
    ):
        assert fragment in TIER2_LINE, (
            f"third-party tier lost fragment {fragment!r}: {TIER2_LINE[:90]!r}"
        )


# ---------------------------------------------------------------------------
# 6. PR description section is conditional (design §2b)
# ---------------------------------------------------------------------------

def test_pr_description_section_is_conditional():
    """The guard must replace the bare ``Include:`` intro of the PR-description
    list, before ``## Push safety``.

    Note: the shipped body keeps the ``## PR description`` heading, so the
    position check enforces heading-before-guard (the guard introduces the
    ``Design ref``/``Test results`` list and precedes Push safety); the
    ``!= -1`` branch is defensive only.
    """
    text = _text(SKILL)
    assert text.count(GUARD_LINE) == 1, (
        f"{SKILL}: the conditional PR-description guard must appear exactly once"
    )
    guard_idx = text.find(GUARD_LINE)
    push_idx = text.find(PUSH_SAFETY)
    design_ref_idx = text.find("- **Design ref**")
    assert guard_idx < design_ref_idx < push_idx, (
        f"{SKILL}: the guard must introduce the PR-description list and precede "
        "`## Push safety`"
    )
    assert "\nInclude:" not in text, (
        f"{SKILL}: the bare `Include:` intro survived — the guard did not replace it"
    )
    heading_idx = text.find(PR_SECTION)
    if heading_idx != -1:
        assert heading_idx < guard_idx, (
            f"{SKILL}: the guard must follow the `## PR description` heading"
        )


# ---------------------------------------------------------------------------
# 7. State pin: the frontmatter description (load trigger) is unchanged (§2c)
# ---------------------------------------------------------------------------

def test_skill_description_frontmatter_unchanged():
    lines = _text(SKILL).splitlines()
    assert DESCRIPTION_LINE in lines, (
        f"{SKILL}: the `description:` load-trigger line changed; §2c leaves it as-is"
    )
    assert "Load when committing or opening a PR for completed work." in DESCRIPTION_LINE


# ---------------------------------------------------------------------------
# 8. Orchestrator mirrors: no PR mandate, no old directive (design §4)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", MIRRORS)
def test_mirrors_still_carry_no_pr_mandate(path):
    span = _ownership_span(path).lower()
    text = _text(path, root=(REPO_ROOT, OVERLAY_ROOT))
    label = path.parent.parent.name or str(path)
    for fragment in PR_MANDATE_FRAGMENTS:
        assert fragment not in span, (
            f"{label} ({path}): the ownership block re-mandates a PR ({fragment!r}); "
            "the mirrors must stay no-PR-mandate (design §4)"
        )
    assert OLD_DIRECTIVE not in text.lower(), (
        f"{label} ({path}): the retired PR-by-default directive leaked into a mirror"
    )


# ---------------------------------------------------------------------------
# 9. Overlay census: no live overlay skill re-mandates a PR by default
# ---------------------------------------------------------------------------

needs_overlay = pytest.mark.skipif(
    not HAS_OVERLAY, reason="overlay sibling opencode_agents/ not present"
)


@needs_overlay
def test_overlay_skill_census():
    offenders = [
        str(path.relative_to(OVERLAY_ROOT))
        for path in _skill_files(OVERLAY_ROOT)
        if OLD_DIRECTIVE in path.read_text(encoding="utf-8").lower()
    ]
    assert offenders == [], (
        "PR-by-default directive present in an overlay skill body: " + repr(offenders)
    )
