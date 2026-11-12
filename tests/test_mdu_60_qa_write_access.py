"""MDU-60 QA write-access: consume-and-persist clause + two brief-checklist lines.

Hermetic: repo + sibling-overlay reads only, no network, no git state, no writes.
The constants below are the byte-identity authority (mdu-49 convention): they hold
the design doc's §2a blockquote (minus the emitted ``- `` lead) and the §2b
checklist lines verbatim.

Clause-file pins resolve their root through ``MDU60_TEST_ROOT``, so the mutation
matrix (design §2d) can point the suite at a /tmp copy with exactly one clause
stripped. Checklist, doc-consistency and AC-2 state pins always read the real
repo. File-count-free by construction: every pin is a substring/count/position/
digest check on clause text, never on a file's line count.

Third-mirror protocol (overlay ``grok/agents/grokestrator.md``): the gate is
derived from LIVE overlay content, not from an operator action (mdu-49/mdu-57
convention, fail-closed on availability + content):

* overlay sibling absent  -> skip (standalone base clone);
* sibling present, clause absent -> skip with a reason naming the pending
  overlay step; the strict pins flip on automatically the moment the clause
  lands, with no human step;
* sibling present, clause present -> strict pins run unconditionally
  (clause exactly once + byte/sha256 equality with the base mirrors).

``MDU60_OVERLAY_SHIPPED=1`` is only an optional force flag: when set it demands
the live clause, so a stale flag cannot fake green. ``MDU60_TEST_ROOT`` moves
the clause-file root only; the overlay pins always read the real sibling.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
OVERLAY_ROOT = REPO_ROOT.parent / "opencode_agents"
HAS_OVERLAY = OVERLAY_ROOT.is_dir()

# The third-mirror gate lives in section 9: it is derived from live overlay
# content (not an env var), so no marker is needed here. `MDU60_TEST_ROOT` only
# moves the clause-file root (mutation matrix); overlay pins read the real
# sibling and must not be redirected.

# Clause-file root: overridable for the mutation matrix (design §2d).
CLAUSE_ROOT = Path(os.environ.get("MDU60_TEST_ROOT", str(REPO_ROOT))).resolve()

DESIGN_DOC = REPO_ROOT / "docs" / "design" / "mdu-60-qa-write-access.md"
BRIEF_CHECKLIST = REPO_ROOT / "docs" / "brief-checklist.md"
OPENCODE_JSON = REPO_ROOT / "opencode.json"

# ---------------------------------------------------------------------------
# Constants — verbatim from the design doc (§2a blockquote minus the `- ` lead;
# §2b checklist lines whole).
# ---------------------------------------------------------------------------

CLAUSE_LINES = (
    "**Durable QA output (consume-and-persist):** When QA or any read-only grading",
    "  agent must produce a durable artifact (answers_qa JSON, findings, reports,",
    "  screenshots), the orchestrator consumes the QA reply — the reply IS the",
    "  deliverable — and dispatches a write-capable agent (just-code/devops) to",
    "  persist it, or writes the coordination artifact itself. The QA brief",
    '  pre-states verbatim: "your reply is the deliverable; a write-capable agent',
    '  persists artifacts; do not attempt writes." Do not grant QA write permission',
    "  to work around this; the read-only sandbox is the grade's independence",
    "  guarantee.",
)
CLAUSE_20261112_2 = "\n".join(CLAUSE_LINES)
EMITTED_CLAUSE = "- " + CLAUSE_20261112_2

CHECKLIST_LINE_WRITER = (
    "- Name the durable-artifact writer (just-code/devops) in every QA brief whose "
    "verdict must persist as a file; QA does not write artifacts. [20261112-2]"
)
CHECKLIST_LINE_REPLY = (
    "- The QA reply is the deliverable; a write-capable agent persists durable "
    'artifacts; QA briefs pre-state "do not attempt writes." [20261112-2]'
)

# Pre-existing anchors (position pins; not the clause's own words).
PHASE_ROUTING_ANCHOR = (
    "- **Phase-routing pre-check:** Before delegating a phase, check the target "
    "agent's shell allowlist in opencode.json against the commands that phase "
    "requires. A phase that must execute an arbitrary script or an unrestricted "
    "command routes to devops or runs in the orchestrator session; QA and other "
    "inspection agents receive the produced artifacts to grade. Do not assign a "
    "phase to an agent whose allowlist cannot run its commands — verify the "
    "permission profile at design time, not mid-run."
)
WORDING_SWEEP_FOLLOW = "- **Wording/term sweeps:**"
QA_PRESTATE_LINE = (
    "- Pre-state the exact probe commands (plain allowlisted form) and the "
    "file-tool fallback (read/grep/sed) in every command-bearing QA brief; a "
    "denial QA reports is a form/permission event, not missing coverage. "
    "[20261110-1]"
)
QA_TRACE_LINE = (
    "- Prompt-text acceptance criteria are traced, not presence-ticked. "
    "[20261021-11]"
)

# Base mirrors (clause-rooted: the mutation matrix strips one at a time).
BASE_MIRRORS = [
    ("opencode", CLAUSE_ROOT / "prompts" / "orchestrator.md"),
    ("grok", CLAUSE_ROOT / "grok" / "agents" / "orchestrator.md"),
]
# Third live mirror: overlay root-added Grok profile (design §2a/§3).
GROKESTRATOR = OVERLAY_ROOT / "grok" / "agents" / "grokestrator.md"

# AC-2 (design §2c): the UNCHANGED read-only state of both grading agents.
GRADING_AGENTS = ["qa", "qa-pro"]

# Read-only role bodies the clause must never leak into: the pattern keeps the
# orchestrator as the addressee and explicitly does not touch qa prompt bodies
# (design §2a "Editing `qa` prompt bodies is out of scope").
READ_ONLY_ROLE_BODIES = [
    REPO_ROOT / "prompts" / "qa.md",
    REPO_ROOT / "grok" / "agents" / "qa.md",
    REPO_ROOT / "grok" / "agents" / "qa-pro.md",
]
GOLDEN_QA_TEMPLATE = REPO_ROOT / "tests" / "fixtures" / "pi_golden" / "prompts" / "qa.md"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text(path: Path) -> str:
    assert path.is_file(), f"missing clause target: {path}"
    return path.read_text(encoding="utf-8")


def _clause_block(path: Path) -> str:
    """Return the emitted clause block (all clause lines) found in ``path``."""
    lines = _text(path).splitlines()
    for index, line in enumerate(lines):
        if line.startswith("- **Durable QA output"):
            block = "\n".join(lines[index : index + len(CLAUSE_LINES)])
            return block
    raise AssertionError(f"{path}: durable-QA clause bullet not found")


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _section(doc: str, heading: str) -> str:
    start = doc.find(heading)
    assert start != -1, f"section heading missing from brief checklist: {heading!r}"
    rest = doc[start + len(heading) :]
    nxt = rest.find("\n## ")
    return heading + (rest if nxt == -1 else rest[:nxt])


def _permissions(agent: str) -> list[dict]:
    config = json.loads(_text(OPENCODE_JSON))
    agents = config.get("agents")
    assert isinstance(agents, dict), "opencode.json missing 'agents' object"
    assert agent in agents, f"opencode.json missing agent {agent!r}"
    perms = agents[agent].get("permissions")
    assert isinstance(perms, list), (
        f"opencode.json agent {agent!r} must carry a permissions list"
    )
    return perms


# ---------------------------------------------------------------------------
# 1. Clause present exactly once per base mirror (non-vacuous: asserts TEXT)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label, path", BASE_MIRRORS)
def test_clause_present_exactly_once_per_mirror(label, path):
    text = _text(path)
    assert text.count(EMITTED_CLAUSE) == 1, (
        f"{label} ({path}): the durable-QA clause must appear exactly once, "
        "byte-identical, with the `- ` lead"
    )
    assert _clause_block(path) == EMITTED_CLAUSE, (
        f"{label} ({path}): clause block bytes drifted from CLAUSE_20261112_2"
    )


# ---------------------------------------------------------------------------
# 2. Cross-mirror sha256 equality
# ---------------------------------------------------------------------------

def test_clause_sha256_equal_across_base_mirrors():
    digests = {label: _digest(_clause_block(path)) for label, path in BASE_MIRRORS}
    assert len(set(digests.values())) == 1, (
        "durable-QA clause differs across the base mirrors: "
        + json.dumps(digests, indent=2)
    )
    assert set(digests.values()) == {_digest(EMITTED_CLAUSE)}, (
        "clause digest drifted from the constant"
    )


# ---------------------------------------------------------------------------
# 3. Adjacency: immediately AFTER the phase-routing pre-check, before the
#    wording/term-sweeps bullet (design §3 anchor note).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label, path", BASE_MIRRORS)
def test_clause_follows_phase_routing_precheck(label, path):
    lines = _text(path).splitlines()
    anchor_idx = next(
        (i for i, line in enumerate(lines) if line == PHASE_ROUTING_ANCHOR), None
    )
    assert anchor_idx is not None, (
        f"{label} ({path}): phase-routing pre-check bullet missing or reworded"
    )
    assert lines[anchor_idx + 1] == "- " + CLAUSE_LINES[0], (
        f"{label} ({path}): clause must start on the line immediately after the "
        "phase-routing pre-check"
    )
    after_idx = anchor_idx + 1 + len(CLAUSE_LINES)
    assert lines[after_idx].startswith(WORDING_SWEEP_FOLLOW), (
        f"{label} ({path}): expected the wording/term-sweeps bullet right after "
        f"the clause, found {lines[after_idx]!r}"
    )


@pytest.mark.parametrize("label, path", BASE_MIRRORS)
def test_phase_routing_anchor_bullet_unchanged(label, path):
    matches = [line for line in _text(path).splitlines() if PHASE_ROUTING_ANCHOR in line]
    assert matches == [PHASE_ROUTING_ANCHOR], (
        f"{label} ({path}): phase-routing pre-check bullet changed or duplicated"
    )


# ---------------------------------------------------------------------------
# 4. Brief-checklist lines: present exactly once, placed in `## qa`
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "label, line",
    [("writer", CHECKLIST_LINE_WRITER), ("reply", CHECKLIST_LINE_REPLY)],
)
def test_checklist_line_present_exactly_once(label, line):
    doc = _text(BRIEF_CHECKLIST)
    assert doc.count(line) == 1, (
        f"{BRIEF_CHECKLIST}: the {label} checklist line must appear exactly once"
    )


def test_checklist_lines_inside_qa_after_prestate():
    doc = _text(BRIEF_CHECKLIST)
    qa_section = _section(doc, "## qa")
    assert "## introspector" not in qa_section, "`## qa` section slice overran"
    for line in (CHECKLIST_LINE_WRITER, CHECKLIST_LINE_REPLY):
        assert line in qa_section, f"checklist line not inside `## qa`: {line[:60]!r}"
    prestate_idx = qa_section.find(QA_PRESTATE_LINE)
    writer_idx = qa_section.find(CHECKLIST_LINE_WRITER)
    reply_idx = qa_section.find(CHECKLIST_LINE_REPLY)
    trace_idx = qa_section.find(QA_TRACE_LINE)
    assert prestate_idx != -1, "`[20261110-1]` pre-state line missing from `## qa`"
    assert trace_idx != -1, "`[20261021-11]` trace line missing from `## qa`"
    assert prestate_idx < writer_idx < reply_idx < trace_idx, (
        "the two [20261112-2] lines must sit after the [20261110-1] pre-state "
        "line and before the [20261021-11] trace line"
    )


# ---------------------------------------------------------------------------
# 5. Doc consistency — constants are verbatim in the design doc (real repo only)
# ---------------------------------------------------------------------------

def test_clause_constant_matches_design_doc():
    assert CLAUSE_20261112_2 in _text(DESIGN_DOC), (
        "CLAUSE_20261112_2 drifted from the design doc §2a blockquote"
    )


@pytest.mark.parametrize(
    "label, line",
    [("writer", CHECKLIST_LINE_WRITER), ("reply", CHECKLIST_LINE_REPLY)],
)
def test_checklist_constants_match_design_doc(label, line):
    assert line in _text(DESIGN_DOC), (
        f"{label} checklist constant drifted from the design doc §2b blockquote"
    )


# ---------------------------------------------------------------------------
# 6. AC-2 state pin: qa + qa-pro stay read-only (no permission edit ships)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("agent", GRADING_AGENTS)
def test_grading_agent_permissions_stay_read_only(agent):
    perms = _permissions(agent)
    triples = {(p.get("action"), p.get("resource"), p.get("effect")) for p in perms}
    assert ("edit", "*", "deny") in triples, (
        f"opencode.json/{agent}: the edit/* deny wall is missing"
    )
    write_allows = [
        p
        for p in perms
        if p.get("action") in {"edit", "write"} and p.get("effect") == "allow"
    ]
    assert write_allows == [], (
        f"opencode.json/{agent}: write/edit allow rules must not be granted "
        f"(AC-2 pins the UNCHANGED read-only state): {write_allows!r}"
    )
    assert not [p for p in perms if p.get("action") == "write"], (
        f"opencode.json/{agent}: no `write` action may be added; the deny-first "
        "`edit` wall is the shipped shape"
    )


# ---------------------------------------------------------------------------
# 7. Negative boundary: the clause never leaks into read-only role bodies or
#    the frozen golden QA template (design §2d negative boundary).
# ---------------------------------------------------------------------------

def test_clause_absent_from_read_only_role_bodies():
    targets = READ_ONLY_ROLE_BODIES + [GOLDEN_QA_TEMPLATE]
    for path in targets:
        if not path.is_file():
            continue
        assert EMITTED_CLAUSE not in _text(path), (
            f"{path}: the orchestrator-side durable-QA clause must not leak into "
            "a read-only role body or its frozen golden template"
        )


# ---------------------------------------------------------------------------
# 8. Net-new census: the clause's distinctive term ships in exactly the base
#    mirrors (no stale second copy hides elsewhere in prompts/)
# ---------------------------------------------------------------------------

def test_distinctive_term_only_in_the_clause_carriers():
    carriers = [path for _label, path in BASE_MIRRORS]
    for path in carriers:
        assert "consume-and-persist" in _text(path)
    allowed = set(carriers)
    if HAS_OVERLAY and GROKESTRATOR.is_file():
        allowed.add(GROKESTRATOR)
    strays = sorted(
        str(path.relative_to(CLAUSE_ROOT))
        for path in list((CLAUSE_ROOT / "prompts").glob("*.md"))
        + list((CLAUSE_ROOT / "grok" / "agents").glob("*.md"))
        if "consume-and-persist" in _text(path) and path not in allowed
    )
    assert strays == [], (
        "`consume-and-persist` leaked into non-carrier role bodies: " + repr(strays)
    )


# ---------------------------------------------------------------------------
# 9. Third mirror (overlay grokestrator) — cross-repo carrier whose gate is
#    derived from LIVE file content (design §2a/§5).
#
# Fail-closed, no operator step: the strict pins run the moment the overlay
# edit lands. Pre-overlay-ship (today) the clause is absent from the sibling
# file and the pins skip, naming the pending overlay step.
# ---------------------------------------------------------------------------

OVERLAY_CLAUSE_PRESENT = (
    HAS_OVERLAY and GROKESTRATOR.is_file() and EMITTED_CLAUSE in _text(GROKESTRATOR)
)


def _overlay_clause_skip_reason() -> str:
    if not HAS_OVERLAY:
        return "overlay sibling opencode_agents/ not present"
    return (
        "pending overlay step: opencode_agents/grok/agents/grokestrator.md does "
        "not yet carry the durable-QA clause; these strict pins flip on "
        "automatically once the clause lands in the overlay file"
    )


needs_overlay_clause = pytest.mark.skipif(
    not OVERLAY_CLAUSE_PRESENT, reason=_overlay_clause_skip_reason()
)


def test_force_flag_cannot_fake_the_overlay_clause():
    """`MDU60_OVERLAY_SHIPPED=1` only asserts; it never substitutes for content."""
    if os.environ.get("MDU60_OVERLAY_SHIPPED") != "1":
        return
    assert OVERLAY_CLAUSE_PRESENT, (
        "MDU60_OVERLAY_SHIPPED=1 is set but the overlay grokestrator file does "
        "not carry the durable-QA clause; the force flag must not fake green"
    )


@needs_overlay_clause
def test_third_mirror_carries_clause():
    text = _text(GROKESTRATOR)
    assert text.count(EMITTED_CLAUSE) == 1, (
        "overlay grok/agents/grokestrator.md: the durable-QA clause must appear "
        "exactly once, byte-identical to the base mirrors"
    )


@needs_overlay_clause
def test_third_mirror_clause_sha256_matches_base_mirrors():
    digests = {label: _digest(_clause_block(path)) for label, path in BASE_MIRRORS}
    digests["grokestrator"] = _digest(_clause_block(GROKESTRATOR))
    assert len(set(digests.values())) == 1, (
        "the clause differs across all three orchestrator mirrors: "
        + json.dumps(digests, indent=2)
    )
