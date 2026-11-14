"""MDU-63 definition-guards batch: three guard clauses across 15 carriers.

The batch ships three introspector suggestions as definition text:

* **20261024-1** (architect, token_hotspot) — read the brief's named files,
  survey with grep/glob, publish the surveyed-file list. 5 carriers.
* **20261113-1** (just-code, rebuild_after_source_edit) — a fix is incomplete
  until the generated copies are rebuilt and re-diffed in the same cycle.
  7 carriers (4 base + 3 overlay).
* **20261110-2** (orchestrator, cache_miss) — do not spawn the next phase from
  a session that an external probe reports as a cache miss. 3 mirrors.

Constants below are the byte-identity authority (mdu-49/60/62 convention): the
clause bodies are copied from `agent-improvements.md` (the log is the only
pre-insertion home of the text) and re-pinned against the design doc fences in
`docs/design/mdu-63-definition-guards-batch.md` §2.

Specimen pins resolve through `MDU63_TEST_ROOT` so the mutation matrix
(design §7c) can point the suite at a `/tmp/opencode` copy with exactly one
piece of a clause stripped. The overlay `grokestrator.md` mirror is the
third-mirror repo-state pin: it always reads the real overlay repository and
skips when that sibling is absent.

Hermetic: file reads only — no network, no git calls, no writes, no secrets.
Paths resolve from `Path(__file__)` so the suite is cwd-independent.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
OVERLAY_ROOT = REPO_ROOT.parent / "opencode_agents"
HAS_OVERLAY = OVERLAY_ROOT.is_dir()

# Specimen root: overridable for the mutation matrix (design §7c). Defaults to
# the real repo, so the shipped suite and the mutant runs share one code path.
TEST_ROOT = Path(os.environ.get("MDU63_TEST_ROOT", str(REPO_ROOT))).resolve()

DESIGN_DOC_REL = Path("docs") / "design" / "mdu-63-definition-guards-batch.md"

# ---------------------------------------------------------------------------
# Constants — verbatim clause bodies (design §2 fences / agent-improvements.md)
# ---------------------------------------------------------------------------

ARCH_CLAUSE = (
    "The design brief names the files and sections relevant to this MDU. Read those first and treat them as the authoritative state; survey the rest of the repository with grep/glob, not full reads. List every file you surveyed at the top of the design doc so the read surface is auditable."
)

REBUILD_CLAUSE = (
    "A fix is incomplete until the generated copies are fresh: after editing any source file that has build/generated copies (skills, prompts, grok builds, pi goldens, build/ trees), run the build/gate that regenerates them in the SAME cycle and re-diff the copies against the source before reporting done — a source fix with stale copies will be returned by review."
)

CACHE_CLAUSE = (
    "If a store probe or signal run reports a cache miss on this session (cache.read ≤1152 with input ≥80k), do not spawn the next phase from this session — start fresh from the resume block (or compact) first; a miss on a ≥200k-token orchestrator prompt re-bills every subsequent child brief."
)

# Emitted forms (design D-3): bullets for the architect and just-code families,
# a two-space-indented paragraph for the orchestrator mirrors.
ARCH_LINE = "- " + ARCH_CLAUSE
REBUILD_LINE = "- " + REBUILD_CLAUSE
CACHE_LINE = "  " + CACHE_CLAUSE

ARCH_MARKER = "- **Be token efficient**"
CONSTRAINTS_HEADING = "Hard constraints:"
BEFORE_REPORTING_WORK_DONE = "- Before reporting work done, scan the files you changed"
BEFORE_REPORTING_DONE = "- Before reporting done, run `timeout 60 python3 scripts/lib/secret_scan.py"

GATE_START = "- **CACHE MISS GATE:**"
GATE_STEP_3 = '  3. "keep going" is not an override.'
CODER_HANDOFF = "- **CODER HANDOFF:**"

# Fragment (scenario) markers: short, distinctive substrings of each clause.
ARCH_FRAGMENTS = (
    "authoritative state",
    "grep/glob, not full reads",
    "read surface is auditable",
)
REBUILD_FRAGMENTS = (
    "generated copies are fresh",
    "in the SAME cycle",
    "re-diff the copies against the source",
)
CACHE_FRAGMENTS = (
    "store probe or signal run",
    "do not spawn the next phase from this session",
    "re-bills every subsequent child brief",
)

# ---------------------------------------------------------------------------
# Carrier census (design §1: 15 files; these 9 are the base specimen rows)
# ---------------------------------------------------------------------------

ARCH_CARRIERS = (
    Path("prompts") / "architect.md",
    Path("grok") / "agents" / "architect.md",
    Path("grok") / "agents" / "architect-premium.md",
)

JUST_CODE_CARRIERS = (
    Path("prompts") / "just-code.md",
    Path("grok") / "agents" / "just-code.md",
    Path("grok") / "agents" / "just-code-mid.md",
    Path("grok") / "agents" / "just-code-pro.md",
)

ORCH_CARRIERS = (
    Path("prompts") / "orchestrator.md",
    Path("grok") / "agents" / "orchestrator.md",
)

# (clause id, marker line, fragment tuple, carriers) — one row per clause family.
CLAUSE_CASES = (
    ("20261024-1", ARCH_LINE, ARCH_FRAGMENTS, ARCH_CARRIERS),
    ("20261113-1", REBUILD_LINE, REBUILD_FRAGMENTS, JUST_CODE_CARRIERS),
    ("20261110-2", CACHE_LINE, CACHE_FRAGMENTS, ORCH_CARRIERS),
)

BASE_CARRIERS = ARCH_CARRIERS + JUST_CODE_CARRIERS + ORCH_CARRIERS

# Repo-state pin: the overlay third mirror (the overlay suite owns the rest).
GROKESTRATOR = OVERLAY_ROOT / "grok" / "agents" / "grokestrator.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _label(rel: Path) -> str:
    return rel.as_posix()


def _specimen(rel: Path) -> Path:
    """Repo-relative specimen path under the (possibly mutant) test root."""
    assert not rel.is_absolute(), f"specimen labels must be repo-relative: {rel}"
    return TEST_ROOT / rel


def _text(path: Path, root: Path = TEST_ROOT) -> str:
    """Read a specimen file, refusing any path that escapes its declared root."""
    resolved = path.resolve()
    assert resolved.is_relative_to(root.resolve()), (
        f"specimen path escaped its root {root}: {resolved}"
    )
    assert resolved.is_file(), f"missing specimen target: {resolved}"
    return resolved.read_text(encoding="utf-8")


def _full_line_count(text: str, line: str) -> int:
    """`grep -F -x` equivalent: exact full-line matches only."""
    return sum(1 for candidate in text.splitlines() if candidate == line)


def _index(text: str, needle: str, where: str) -> int:
    idx = text.find(needle)
    assert idx != -1, f"{where}: anchor missing: {needle[:70]!r}"
    return idx


# ---------------------------------------------------------------------------
# 1. Doc consistency — the constants are verbatim in the design doc §2 fences
# ---------------------------------------------------------------------------

def test_constants_match_design_doc():
    doc = _text(_specimen(DESIGN_DOC_REL))
    bounds = (doc.find("**2a."), doc.find("**2b."), doc.find("**2c."), doc.find("## 3."))
    assert all(idx != -1 for idx in bounds), f"design doc §2 section markers missing: {bounds}"
    section_2a, section_2b, section_2c = (
        doc[bounds[0]:bounds[1]],
        doc[bounds[1]:bounds[2]],
        doc[bounds[2]:bounds[3]],
    )
    for label, clause, section in (
        ("20261024-1", ARCH_CLAUSE, section_2a),
        ("20261113-1", REBUILD_CLAUSE, section_2b),
        ("20261110-2", CACHE_CLAUSE, section_2c),
    ):
        assert clause in section, (
            f"{label} constant drifted from the design doc §2 fence: {clause[:70]!r}"
        )
        assert clause in section.splitlines(), (
            f"{label} constant is not a full fence line in the design doc §2"
        )


# ---------------------------------------------------------------------------
# 2. Presence + bytes — the emitted line is a FULL line exactly once (9 base)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "clause_id, line, rel",
    [
        pytest.param(cid, line, rel, id=f"{cid}-{_label(rel)}")
        for cid, line, _fragments, carriers in CLAUSE_CASES
        for rel in carriers
    ],
)
def test_clause_present_once_as_full_line(clause_id, line, rel):
    text = _text(_specimen(rel))
    count = _full_line_count(text, line)
    assert count == 1, (
        f"{_label(rel)}: {clause_id} clause must appear as an exact full line "
        f"exactly once (design D-3 emitted form); found {count}"
    )
    if line.startswith("  "):
        assert _full_line_count(text, line.lstrip()) == 0, (
            f"{_label(rel)}: the cache clause must not also appear unindented"
        )


# ---------------------------------------------------------------------------
# 3. Adjacency — each clause keeps its designed relative position (design D-2)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rel", ARCH_CARRIERS, ids=_label)
def test_architect_clause_follows_token_efficiency(rel):
    text = _text(_specimen(rel))
    token_idx = _index(text, ARCH_MARKER, _label(rel))
    clause_idx = _index(text, ARCH_LINE, _label(rel))
    hard_idx = _index(text, CONSTRAINTS_HEADING, _label(rel))
    assert token_idx < clause_idx < hard_idx, (
        f"{_label(rel)}: the survey clause must follow the token-efficiency bullet "
        "and stay inside the responsibilities span (before `Hard constraints:`)"
    )


@pytest.mark.parametrize(
    "rel, anchor",
    (
        (Path("prompts") / "just-code.md", BEFORE_REPORTING_WORK_DONE),
        (Path("grok") / "agents" / "just-code.md", BEFORE_REPORTING_DONE),
        (Path("grok") / "agents" / "just-code-mid.md", BEFORE_REPORTING_DONE),
        (Path("grok") / "agents" / "just-code-pro.md", BEFORE_REPORTING_DONE),
    ),
    ids=("prompts-just-code", "grok-just-code", "grok-just-code-mid", "grok-just-code-pro"),
)
def test_just_code_clause_follows_before_reporting_done(rel, anchor):
    text = _text(_specimen(rel))
    hard_idx = _index(text, CONSTRAINTS_HEADING, _label(rel))
    anchor_idx = text.find(anchor, hard_idx)
    assert anchor_idx != -1, (
        f"{_label(rel)}: before-reporting-done anchor missing after `Hard constraints:`"
    )
    clause_idx = _index(text, REBUILD_LINE, _label(rel))
    assert anchor_idx < clause_idx, (
        f"{_label(rel)}: the rebuild-freshness bullet must follow the "
        "before-reporting-done secret bullet (it is itself a before-done check)"
    )
    body_start = hard_idx + len(CONSTRAINTS_HEADING)
    next_section = text.find("\n\nBehavior:", body_start)
    if next_section == -1:
        next_section = len(text)
    assert body_start < clause_idx < next_section, (
        f"{_label(rel)}: the rebuild bullet must stay inside the Hard-constraints list"
    )


@pytest.mark.parametrize("rel", ORCH_CARRIERS, ids=_label)
def test_orchestrator_clause_inside_cache_miss_gate(rel):
    text = _text(_specimen(rel))
    gate_idx = _index(text, GATE_START, _label(rel))
    step3_idx = _index(text, GATE_STEP_3, _label(rel))
    clause_idx = _index(text, CACHE_LINE, _label(rel))
    handoff_idx = _index(text, CODER_HANDOFF, _label(rel))
    assert gate_idx < step3_idx < clause_idx < handoff_idx, (
        f"{_label(rel)}: order must be CACHE MISS GATE < step 3 < cache clause < "
        "CODER HANDOFF (design §3c: one cache-miss authority per mirror)"
    )


# ---------------------------------------------------------------------------
# 4. Fragments — scenario pins, one per shipped phrase (mdu-62 style)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "clause_id, line, fragment, rel",
    [
        pytest.param(cid, line, fragment, rel, id=f"{cid}-{fragment.split()[0]}-{_label(rel)}")
        for cid, line, fragments, carriers in CLAUSE_CASES
        for fragment in fragments
        for rel in carriers
    ],
)
def test_clause_fragments(clause_id, line, fragment, rel):
    text = _text(_specimen(rel))
    assert fragment in text, (
        f"{_label(rel)}: {clause_id} lost fragment {fragment!r}"
    )
    assert _full_line_count(text, line) == 1, (
        f"{_label(rel)}: fragment {fragment!r} must live in the single clause line"
    )


# ---------------------------------------------------------------------------
# 5. Census negatives — no second home, no near-duplicate (design §1 ruling 3)
# ---------------------------------------------------------------------------

def _live_definition_files(root: Path) -> list[Path]:
    """Live definition surfaces: prompts/, grok/agents/, skills/ (build trees out)."""
    prompts = sorted((root / "prompts").glob("*.md"))
    grok_agents = sorted((root / "grok" / "agents").glob("*.md"))
    assert prompts, f"no prompts/*.md found under {root} — vacuous census"
    assert grok_agents, f"no grok/agents/*.md found under {root} — vacuous census"
    files = prompts + grok_agents
    skills_root = root / "skills"
    if skills_root.is_dir():
        files.extend(sorted(skills_root.rglob("*.md")))
    return files


@pytest.mark.parametrize(
    "clause_id, marker",
    (
        ("20261024-1", ARCH_FRAGMENTS[0]),
        ("20261113-1", REBUILD_FRAGMENTS[0]),
        ("20261110-2", CACHE_FRAGMENTS[0]),
    ),
)
def test_census_no_unplanned_carrier(clause_id, marker):
    carriers = {_specimen(rel).resolve() for rel in BASE_CARRIERS}
    offenders = [
        path.relative_to(TEST_ROOT).as_posix()
        for path in _live_definition_files(TEST_ROOT)
        if path.resolve() not in carriers
        and marker in path.read_text(encoding="utf-8")
    ]
    assert offenders == [], (
        f"{clause_id} clause marker {marker!r} leaked into a live definition file "
        f"outside the declared carrier set: {offenders}"
    )


@pytest.mark.parametrize(
    "rel, marker",
    [
        pytest.param(rel, fragments[0], id=f"{_label(rel)}")
        for _cid, _line, fragments, carriers in CLAUSE_CASES
        for rel in carriers
    ],
)
def test_carrier_has_no_duplicate_clause(rel, marker):
    count = _text(_specimen(rel)).count(marker)
    assert count == 1, (
        f"{_label(rel)}: clause marker {marker!r} appears {count} times — no carrier "
        "may hold a second near-duplicate copy"
    )


# ---------------------------------------------------------------------------
# 6. Third mirror — the overlay grokestrator (repo-state pin, skipif)
# ---------------------------------------------------------------------------

needs_overlay = pytest.mark.skipif(
    not GROKESTRATOR.is_file(), reason="overlay sibling opencode_agents/ not present"
)


@needs_overlay
def test_grokestrator_carries_cache_clause_once():
    text = _text(GROKESTRATOR, root=OVERLAY_ROOT)
    count = _full_line_count(text, CACHE_LINE)
    assert count == 1, (
        f"grokestrator.md: the cache-miss paragraph must appear as an exact full "
        f"line exactly once; found {count}"
    )


@needs_overlay
def test_grokestrator_clause_inside_cache_miss_gate():
    text = _text(GROKESTRATOR, root=OVERLAY_ROOT)
    gate_idx = _index(text, GATE_START, "grokestrator.md")
    step3_idx = _index(text, GATE_STEP_3, "grokestrator.md")
    clause_idx = _index(text, CACHE_LINE, "grokestrator.md")
    handoff_idx = _index(text, CODER_HANDOFF, "grokestrator.md")
    assert gate_idx < step3_idx < clause_idx < handoff_idx, (
        "grokestrator.md: order must be CACHE MISS GATE < step 3 < cache clause < "
        "CODER HANDOFF"
    )
