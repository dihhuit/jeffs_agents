"""MDU-61 MCP harness-vs-reality: the app-backed MCP gating clause, 6 base carriers.

Hermetic: repo + sibling-overlay reads only, no network, no git state, no writes
outside ``/tmp/opencode`` (mutation matrix copies). The constants below are the
byte-identity authority (mdu-49/60 convention): they hold the design doc §D3
blockquote (minus the emitted ``- `` lead) and the §D5 checklist line verbatim.

Clause-file pins resolve their root through ``MDU61_TEST_ROOT``, so the mutation
matrix (design §D6) can point the suite at a /tmp copy with exactly one carrier
stripped. Checklist, docs, golden and design-doc pins always read the real repo.
File-count-free by construction: every pin is a substring/count/position/digest
check on clause text, never on a file's line count.

Overlay carriers (5, the 20261112-3 env-gated pin class): the gate is derived
from LIVE sibling content, not from an operator action (mdu-60 §9):

* overlay sibling absent -> skip (standalone base clone);
* sibling present, clause absent -> skip with a reason naming the pending
  overlay commit; the strict pins flip on automatically the moment it lands;
* sibling present, clause present -> strict pins run unconditionally (exactly
  once per overlay carrier + sha256 equality across all 11 carriers).

``MDU61_OVERLAY_SHIPPED=1`` is only an optional force flag: when set it demands
the live clause, so a stale flag cannot fake green. ``MDU61_TEST_ROOT`` moves
the clause-file root only; the overlay pins always read the real sibling.

Design D6 branch 2 (deferral variant) is NOT active: the user pre-approved the
clause in-MDU, so the base presence/adjacency pins are strict and there is no
live-content gate on them.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
OVERLAY_ROOT = REPO_ROOT.parent / "opencode_agents"
HAS_OVERLAY = OVERLAY_ROOT.is_dir()

# Clause-file root: overridable for the mutation matrix (design §D6).
CLAUSE_ROOT = Path(os.environ.get("MDU61_TEST_ROOT", str(REPO_ROOT))).resolve()

DESIGN_DOC = REPO_ROOT / "docs" / "design" / "mdu-61-mcp-fixes.md"
BRIEF_CHECKLIST = REPO_ROOT / "docs" / "brief-checklist.md"
MCP_DOC = REPO_ROOT / "docs" / "mcp.md"
GOLDEN_DIR = REPO_ROOT / "tests" / "fixtures" / "pi_golden" / "prompts"

# ---------------------------------------------------------------------------
# Constants — verbatim from the design doc (§D3 blockquote minus the `- ` lead;
# §D5 checklist line whole). The emitted sha256 of the block starts with
# 0d2766e6 (the tests recompute the full digest at runtime and compare it
# against the live carriers, so only the prefix is recorded here).
# ---------------------------------------------------------------------------

CLAUSE_LINES = (
    "**App-backed MCP gating (Blender):** Before any blender-dependent step (tool",
    "  call, verification item, deploy check), probe the application first:",
    "  `pgrep -x blender` must show the Blender app running with the",
    "  `mcp-for-blender` addon enabled. A running `mcp-for-blender` server process",
    '  alone is launcher-level only and is NOT sufficient — a harness "connected"',
    "  status reports the launcher, not the application. If the app is absent,",
    "  immediately report a BLOCKED status (distinct from PASS/FAIL) naming the",
    "  probe, what failed, and that Blender must be running with the addon",
    "  enabled — mirroring the Playwright-or-BLOCKED discipline; never report",
    '  blender as "connected" from launcher status alone. The same app-vs-launcher',
    "  rule applies to any MCP server that fronts a running application.",
)
CLAUSE_20261112_4 = "\n".join(CLAUSE_LINES)
EMITTED_CLAUSE = "- " + CLAUSE_20261112_4
CLAUSE_FIRST_LINE = CLAUSE_LINES[0]
EMITTED_FIRST_LINE = EMITTED_CLAUSE.splitlines()[0]

CHECKLIST_LINE = (
    "- Pre-state the app probe before any blender-dependent step (`pgrep -x blender`; "
    "a running mcp-for-blender server process is launcher-level only); absent app → "
    'the child reports BLOCKED, never "connected". [20261112-4]'
)

# The two pre-existing qa anchor bullets (design §D3 placement table). The base
# carriers carry the LONG variant; overlay grok-qa is the SHORT variant, so the
# adjacency pin accepts both.
QA_ANCHOR_LONG = (
    "- Still run non-browser checks you can (HTTP/API, CLI, logs) and list what "
    "browser coverage was blocked."
)
QA_ANCHOR_SHORT = (
    "- Still run non-browser checks you can and list what browser coverage was blocked."
)
QA_ANCHORS = (QA_ANCHOR_LONG, QA_ANCHOR_SHORT)

# The devops anchor: the clause is the LAST bullet of this block.
HARD_CONSTRAINTS_HEADING = "Hard constraints:"

# The qa checklist insertion anchor (design §D5).
QA_PRESTATE_LINE_ID = "[20261110-1]"

# Docs distinctive terms (design §D4).
DOC_CHROME_ERROR = "Chromium distribution 'chrome' is not found"
DOC_APP_PROBE = "pgrep -x blender"
DOC_LAUNCHER_COUNT = "pgrep -fc mcp-for-blender"
DOC_BROWSER_FLAG = "--browser chromium"

# Census term: the clause's distinctive heading text.
DISTINCTIVE_TERM = "App-backed MCP gating"

# ---------------------------------------------------------------------------
# Carriers. Base = clause-rooted (the mutation matrix strips one at a time).
# ---------------------------------------------------------------------------

QA_CARRIERS = [
    ("prompts/qa.md", CLAUSE_ROOT / "prompts" / "qa.md"),
    ("grok/agents/qa.md", CLAUSE_ROOT / "grok" / "agents" / "qa.md"),
    ("grok/agents/qa-pro.md", CLAUSE_ROOT / "grok" / "agents" / "qa-pro.md"),
]
DEVOPS_CARRIERS = [
    ("prompts/devops.md", CLAUSE_ROOT / "prompts" / "devops.md"),
    ("grok/agents/devops.md", CLAUSE_ROOT / "grok" / "agents" / "devops.md"),
    ("grok/agents/devops-pro.md", CLAUSE_ROOT / "grok" / "agents" / "devops-pro.md"),
]
BASE_CARRIERS = QA_CARRIERS + DEVOPS_CARRIERS
FAMILY_BY_LABEL = {label: "qa" for label, _p in QA_CARRIERS}
FAMILY_BY_LABEL.update({label: "devops" for label, _p in DEVOPS_CARRIERS})

# Overlay carriers (5, personal — always the real sibling, never the mutant root).
OVERLAY_CARRIERS = [
    ("grok/agents/grok-qa.md", OVERLAY_ROOT / "grok" / "agents" / "grok-qa.md"),
    ("grok/agents/grok-qa-pro.md", OVERLAY_ROOT / "grok" / "agents" / "grok-qa-pro.md"),
    ("grok/agents/grok-devops.md", OVERLAY_ROOT / "grok" / "agents" / "grok-devops.md"),
    ("grok/agents/grok-devops-pro.md", OVERLAY_ROOT / "grok" / "agents" / "grok-devops-pro.md"),
    ("overlays/prompts/qa.md", OVERLAY_ROOT / "overlays" / "prompts" / "qa.md"),
]

GOLDEN_CARRIERS = ["qa", "qa-pro", "devops", "devops-pro"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text(path: Path) -> str:
    assert path.is_file(), f"missing pin target: {path}"
    return path.read_text(encoding="utf-8")


def _clause_block(path: Path) -> str:
    """Return the emitted clause block (all clause lines) found in ``path``."""
    lines = _text(path).splitlines()
    for index, line in enumerate(lines):
        if line.startswith(EMITTED_FIRST_LINE):
            return "\n".join(lines[index : index + len(CLAUSE_LINES)])
    raise AssertionError(f"{path}: app-backed MCP gating clause bullet not found")


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _section(doc: str, heading: str) -> str:
    start = doc.find(heading)
    assert start != -1, f"section heading missing from brief checklist: {heading!r}"
    rest = doc[start + len(heading) :]
    nxt = rest.find("\n## ")
    return heading + (rest if nxt == -1 else rest[:nxt])


def _clause_start(path: Path) -> tuple[list[str], int]:
    lines = _text(path).splitlines()
    for index, line in enumerate(lines):
        if line == EMITTED_FIRST_LINE:
            return lines, index
    raise AssertionError(f"{path}: app-backed MCP gating clause bullet not found")


# ---------------------------------------------------------------------------
# 1. Presence exactly once per base carrier + block byte-match
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label, path", BASE_CARRIERS)
def test_clause_present_exactly_once_per_carrier(label, path):
    text = _text(path)
    assert text.count(EMITTED_CLAUSE) == 1, (
        f"{label} ({path}): the app-backed MCP gating clause must appear exactly "
        "once, byte-identical, with the `- ` lead"
    )
    assert _clause_block(path) == EMITTED_CLAUSE, (
        f"{label} ({path}): clause block bytes drifted from CLAUSE_20261112_4"
    )


# ---------------------------------------------------------------------------
# 2. Cross-carrier sha256 equality across all 6 base carriers
# ---------------------------------------------------------------------------

def test_clause_sha256_equal_across_base_carriers():
    digests = {label: _digest(_clause_block(path)) for label, path in BASE_CARRIERS}
    assert len(set(digests.values())) == 1, (
        "the app-backed MCP gating clause differs across the base carriers: "
        + json.dumps(digests, indent=2)
    )
    assert set(digests.values()) == {_digest(EMITTED_CLAUSE)}, (
        "clause digest drifted from the constant"
    )


# ---------------------------------------------------------------------------
# 3. Adjacency — qa family: one blank line + one of the two anchor bullets.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label, path", QA_CARRIERS)
def test_qa_clause_follows_anchor_bullet(label, path):
    lines, start = _clause_start(path)
    assert start >= 2, f"{label} ({path}): no room before the clause for an anchor"
    assert lines[start - 1] == "", (
        f"{label} ({path}): the clause must be blank-line separated from its "
        f"anchor bullet, found {lines[start - 1]!r}"
    )
    assert lines[start - 2] in QA_ANCHORS, (
        f"{label} ({path}): the clause must be preceded (one blank line) by the "
        "Playwright-or-BLOCKED anchor bullet; "
        f"found {lines[start - 2]!r}"
    )


# ---------------------------------------------------------------------------
# 4. Adjacency — devops family: LAST bullet of the `Hard constraints:` block.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label, path", DEVOPS_CARRIERS)
def test_devops_clause_is_last_hard_constraint_bullet(label, path):
    lines, start = _clause_start(path)
    heading_idx = next(
        (i for i, line in enumerate(lines[:start]) if line == HARD_CONSTRAINTS_HEADING),
        None,
    )
    assert heading_idx is not None, (
        f"{label} ({path}): `{HARD_CONSTRAINTS_HEADING}` heading missing before "
        "the clause"
    )
    between = [line for line in lines[heading_idx + 1 : start] if line.strip()]
    assert all(line.startswith("- ") for line in between), (
        f"{label} ({path}): the clause must sit inside the "
        f"`{HARD_CONSTRAINTS_HEADING}` bullet block; found non-bullet lines: "
        f"{[line for line in between if not line.startswith('- ')]!r}"
    )
    after_idx = start + len(CLAUSE_LINES)
    assert after_idx < len(lines), f"{label} ({path}): clause runs to EOF"
    assert not lines[after_idx].startswith("- "), (
        f"{label} ({path}): the clause must be the LAST bullet of the "
        f"`{HARD_CONSTRAINTS_HEADING}` block, found another bullet after it: "
        f"{lines[after_idx]!r}"
    )


# ---------------------------------------------------------------------------
# 5. Doc consistency — the constants are the design doc's own blockquotes
# ---------------------------------------------------------------------------

def test_clause_constant_matches_design_doc():
    doc = _text(DESIGN_DOC)
    assert CLAUSE_20261112_4 in doc, "CLAUSE_20261112_4 drifted from the design §D3 block"
    assert EMITTED_CLAUSE in doc, "EMITTED_CLAUSE drifted from the design §D3 block"


def test_checklist_constant_matches_design_doc():
    assert CHECKLIST_LINE in _text(DESIGN_DOC), (
        "CHECKLIST_LINE drifted from the design §D5 blockquote"
    )


# ---------------------------------------------------------------------------
# 6. Brief checklist: once in `## devops`, once in `## qa` after [20261110-1]
# ---------------------------------------------------------------------------

def test_checklist_line_once_per_section():
    doc = _text(BRIEF_CHECKLIST)
    assert doc.count(CHECKLIST_LINE) == 2, (
        f"{BRIEF_CHECKLIST}: the [20261112-4] checklist line must appear exactly "
        "twice (one per section)"
    )
    for heading in ("## devops", "## qa"):
        section = _section(doc, heading)
        assert "## " not in section[len(heading) :], f"`{heading}` slice overran"
        assert section.count(CHECKLIST_LINE) == 1, (
            f"the [20261112-4] checklist line must appear exactly once in `{heading}`"
        )


def test_qa_checklist_line_sits_immediately_after_prestate_line():
    lines = _section(_text(BRIEF_CHECKLIST), "## qa").splitlines()
    prestate = [i for i, line in enumerate(lines) if QA_PRESTATE_LINE_ID in line]
    assert prestate, f"`{QA_PRESTATE_LINE_ID}` pre-state line missing from `## qa`"
    idx = prestate[0]
    assert idx + 1 < len(lines), "`## qa` slice ends at the pre-state line"
    assert lines[idx + 1] == CHECKLIST_LINE, (
        "the [20261112-4] line must sit immediately after the [20261110-1] "
        f"pre-state line, found {lines[idx + 1]!r}"
    )


def test_devops_checklist_line_is_last_section_line():
    lines = _section(_text(BRIEF_CHECKLIST), "## devops").splitlines()
    body = [line for line in lines[1:] if line.strip()]
    assert body, "`## devops` section is empty"
    assert body[-1] == CHECKLIST_LINE, (
        "the [20261112-4] line must be the last line of `## devops`, found "
        f"{body[-1]!r}"
    )


# ---------------------------------------------------------------------------
# 7. Docs pins (3) — docs/mcp.md carries the env-gap documentation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "label, needle",
    [
        ("chrome-missing-error", DOC_CHROME_ERROR),
        ("app-probe", DOC_APP_PROBE),
        ("launcher-count", DOC_LAUNCHER_COUNT),
    ],
)
def test_mcp_doc_documents_the_env_gap(label, needle):
    assert needle in _text(MCP_DOC), (
        f"docs/mcp.md: the {label} term must be documented ({needle!r})"
    )


def test_mcp_doc_names_the_browser_flag_repeatedly():
    count = _text(MCP_DOC).count(DOC_BROWSER_FLAG)
    assert count >= 2, (
        "docs/mcp.md: `--browser chromium` must appear at least twice (details "
        f"bullet + harness-default sentence), found {count}"
    )


# ---------------------------------------------------------------------------
# 8. Golden pins (4) — the regenerated pi templates carry the emitted clause
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", GOLDEN_CARRIERS)
def test_golden_template_carries_emitted_clause(name):
    path = GOLDEN_DIR / f"{name}.md"
    assert _text(path).count(EMITTED_CLAUSE) == 1, (
        f"{path}: the regenerated golden template must carry the emitted clause "
        "exactly once (mdu-56 gates B/C enforce byte fidelity)"
    )


# ---------------------------------------------------------------------------
# 9. Census: the distinctive term matches ONLY the 6 base carriers
# ---------------------------------------------------------------------------

def test_distinctive_term_only_in_the_clause_carriers():
    carriers = [path for _label, path in BASE_CARRIERS]
    for path in carriers:
        assert DISTINCTIVE_TERM in _text(path)
    allowed = set(carriers)
    strays = sorted(
        str(path.relative_to(CLAUSE_ROOT))
        for path in list((CLAUSE_ROOT / "prompts").glob("*.md"))
        + list((CLAUSE_ROOT / "grok" / "agents").glob("*.md"))
        if DISTINCTIVE_TERM in _text(path) and path not in allowed
    )
    assert strays == [], (
        f"`{DISTINCTIVE_TERM}` leaked into non-carrier role bodies: " + repr(strays)
    )


# ---------------------------------------------------------------------------
# 10. Mutation matrix (design §D6): MDU61_TEST_ROOT -> /tmp copy, one carrier
#     stripped at a time -> presence/sha/adjacency pins fail as designed.
#
# In-process and hermetic: the module is re-imported with the env var pointing
# at the mutant tree, then the pin functions are called directly. No subprocess,
# no git state, and the working tree is never touched — only the copies under
# /tmp/opencode.
# ---------------------------------------------------------------------------

TEST_FILE = Path(__file__).resolve()
MUTANT_BASE = Path("/tmp/opencode")
MUTANT_LABEL = "_mdu61_mutant_module"


@pytest.fixture
def mutant_root():
    MUTANT_BASE.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="mdu61-mut-", dir=str(MUTANT_BASE)))
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _build_mutant_tree(root: Path) -> None:
    """Copy the real carrier trees (never the mutant env value) under ``root``."""
    shutil.copytree(REPO_ROOT / "prompts", root / "prompts")
    shutil.copytree(REPO_ROOT / "grok" / "agents", root / "grok" / "agents")


def _strip_clause(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    assert EMITTED_FIRST_LINE in lines, f"{path}: nothing to strip"
    start = lines.index(EMITTED_FIRST_LINE)
    del lines[start : start + len(CLAUSE_LINES)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _load_mutant_module(monkeypatch, root: Path):
    monkeypatch.setenv("MDU61_TEST_ROOT", str(root))
    spec = importlib.util.spec_from_file_location(MUTANT_LABEL, TEST_FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.CLAUSE_ROOT == root.resolve(), (
        "MDU61_TEST_ROOT did not move the clause-file root"
    )
    return module


@pytest.mark.parametrize("label", [label for label, _path in BASE_CARRIERS])
def test_mutation_stripping_one_carrier_reds_the_pins(label, mutant_root, monkeypatch):
    # `label` is the repo-relative carrier path; the mutant path is re-rooted on
    # the /tmp copy and the guards below make a repo write structurally
    # impossible (a carrier's absolute path must never reach a write).
    mutant_path = mutant_root / label
    assert mutant_path.is_relative_to(mutant_root)
    assert mutant_root.resolve().is_relative_to(MUTANT_BASE.resolve())
    _build_mutant_tree(mutant_root)
    _strip_clause(mutant_path)
    mutant = _load_mutant_module(monkeypatch, mutant_root)

    with pytest.raises(AssertionError):
        mutant.test_clause_present_exactly_once_per_carrier(label, mutant_path)

    with pytest.raises(AssertionError):
        mutant.test_clause_sha256_equal_across_base_carriers()

    adjacency = (
        mutant.test_qa_clause_follows_anchor_bullet
        if FAMILY_BY_LABEL[label] == "qa"
        else mutant.test_devops_clause_is_last_hard_constraint_bullet
    )
    with pytest.raises(AssertionError):
        adjacency(label, mutant_path)


# ---------------------------------------------------------------------------
# 11. Overlay carriers (5) — the 20261112-3 env-gated pin class.
#
# Fail-closed, no operator step: the strict pins run the moment the overlay
# commit lands. Pre-overlay-ship (today) the clause is absent from the sibling
# and the pins skip, naming the pending overlay commit. The gate opens on ANY
# landed carrier, so a partial overlay ship reds the suite instead of hiding
# behind the skip (the 5-carrier edit is one atomic commit).
# ---------------------------------------------------------------------------

OVERLAY_CLAUSE_PRESENT = HAS_OVERLAY and any(
    path.is_file() and EMITTED_CLAUSE in _text(path) for _l, path in OVERLAY_CARRIERS
)


def _overlay_clause_skip_reason() -> str:
    if not HAS_OVERLAY:
        return "overlay sibling opencode_agents/ not present"
    return (
        "pending overlay commit: opencode_agents/ does not yet carry the "
        "20261112-4 app-backed MCP gating clause in grok/agents/grok-qa{,-pro}.md, "
        "grok/agents/grok-devops{,-pro}.md and overlays/prompts/qa.md; these "
        "strict pins flip on automatically once that overlay commit lands"
    )


needs_overlay_clause = pytest.mark.skipif(
    not OVERLAY_CLAUSE_PRESENT, reason=_overlay_clause_skip_reason()
)


def test_force_flag_cannot_fake_the_overlay_clause():
    """`MDU61_OVERLAY_SHIPPED=1` only asserts; it never substitutes for content."""
    if os.environ.get("MDU61_OVERLAY_SHIPPED") != "1":
        return
    assert OVERLAY_CLAUSE_PRESENT, (
        "MDU61_OVERLAY_SHIPPED=1 is set but the overlay carriers do not carry the "
        "app-backed MCP gating clause; the force flag must not fake green"
    )


@needs_overlay_clause
@pytest.mark.parametrize("label, path", OVERLAY_CARRIERS)
def test_overlay_carrier_carries_clause_exactly_once(label, path):
    text = _text(path)
    assert text.count(EMITTED_CLAUSE) == 1, (
        f"overlay {label}: the app-backed MCP gating clause must appear exactly "
        "once, byte-identical to the base carriers"
    )
    assert _clause_block(path) == EMITTED_CLAUSE, (
        f"overlay {label}: clause block bytes drifted from CLAUSE_20261112_4"
    )


@needs_overlay_clause
def test_overlay_clause_sha256_matches_all_base_carriers():
    digests = {label: _digest(_clause_block(path)) for label, path in BASE_CARRIERS}
    digests.update(
        {f"overlay:{label}": _digest(_clause_block(path)) for label, path in OVERLAY_CARRIERS}
    )
    assert len(digests) == 11, "expected 6 base + 5 overlay carriers"
    assert len(set(digests.values())) == 1, (
        "the clause differs across the 11 carriers: " + json.dumps(digests, indent=2)
    )
