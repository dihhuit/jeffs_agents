"""MDU-47 definition-guards batch + orchestrator repoint.

Hermetic: repo reads only, no network, no git state, tmp_path for any writes.
Covers clause presence, mirror parity, ordering, dirty-tree verify pins,
orchestrator model repoint, and brief-checklist pins.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
OVERLAY_ROOT = REPO_ROOT.parent / "opencode_agents"
HAS_OVERLAY = OVERLAY_ROOT.is_dir()

# In a standalone base clone the overlay sibling is absent: skip only the pins
# that read overlay files (mdu-35 convention) instead of raising FileNotFoundError.
needs_overlay = pytest.mark.skipif(
    not HAS_OVERLAY, reason="overlay sibling opencode_agents/ not present"
)

# ---------------------------------------------------------------------------
# D1 clause fragments and the files that must carry each one.
# (id, fragment, files) triples; the id lives in the test, not in prompts.
# ---------------------------------------------------------------------------

D1B_FRAGMENT = "trace it as a procedure, not a presence tick"
D1B_FILES = (
    REPO_ROOT / "prompts" / "code-reviewer.md",
    REPO_ROOT / "grok" / "agents" / "code-reviewer.md",
    REPO_ROOT / "grok" / "agents" / "code-reviewer-pro.md",
    REPO_ROOT / "prompts" / "grok-review.md",
    REPO_ROOT / "grok" / "agents" / "grok-review.md",
)

# Per-file sign-off anchors the D1b bullet must precede. The anchor text differs
# per mirror (mdu-41 D6 pattern), so it cannot be one shared fragment: pinning the
# bullet's own words here would only re-assert the D1b clause against itself.
D1B_SIGN_OFF_ANCHORS = [
    (
        "20261021-11",
        "If the code is correct",
        (
            REPO_ROOT / "prompts" / "code-reviewer.md",
            REPO_ROOT / "grok" / "agents" / "code-reviewer.md",
        ),
    ),
    (
        "20261021-11",
        "Only sign off when",
        (
            REPO_ROOT / "prompts" / "grok-review.md",
            REPO_ROOT / "grok" / "agents" / "grok-review.md",
        ),
    ),
    (
        "20261021-11",
        "Reserve this level",
        (REPO_ROOT / "grok" / "agents" / "code-reviewer-pro.md",),
    ),
]

D1C_FRAGMENT = "fails the criterion even when every element is present"
D1C_BASE_FILES = (
    REPO_ROOT / "prompts" / "qa.md",
    REPO_ROOT / "grok" / "agents" / "qa.md",
    REPO_ROOT / "grok" / "agents" / "qa-pro.md",
)

D1D_FRAGMENT = "no pipes, no redirects, no command substitution"
D1D_FALLBACK_FRAGMENT = "verified via orchestrator-attached output"
D1D_BASE_FILES = (
    REPO_ROOT / "prompts" / "qa.md",
    REPO_ROOT / "grok" / "agents" / "qa.md",
    REPO_ROOT / "grok" / "agents" / "qa-pro.md",
)

# The overlay qa full-file override must carry both QA sentences too (D2).
OVERLAY_QA = OVERLAY_ROOT / "overlays" / "prompts" / "qa.md"

D1E_FRAGMENT = "write file paths repo-relative"
D1E_FILES = (
    REPO_ROOT / "prompts" / "architect.md",
    REPO_ROOT / "grok" / "agents" / "architect.md",
    REPO_ROOT / "grok" / "agents" / "architect-premium.md",
)

# One pinned fragment per clause => 5 + 3 + 3 + 3 = 14 base prompt-file assertions,
# plus 2 overlay qa assertions in the overlay-gated test below.
CLAUSE_FILE_ASSERTIONS = [
    ("20261021-11", D1B_FRAGMENT, D1B_FILES),
    ("20261021-11", D1C_FRAGMENT, D1C_BASE_FILES),
    ("20261021-8", D1D_FRAGMENT, D1D_BASE_FILES),
    ("20261030-5", D1E_FRAGMENT, D1E_FILES),
]

OVERLAY_CLAUSE_FILE_ASSERTIONS = [
    ("20261021-11", D1C_FRAGMENT, (OVERLAY_QA,)),
    ("20261021-8", D1D_FRAGMENT, (OVERLAY_QA,)),
]


# ---------------------------------------------------------------------------
# 1. Per-clause presence (14 base + 2 overlay prompt-file assertions)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("clause_id, fragment, files", CLAUSE_FILE_ASSERTIONS)
def test_clause_fragment_present(clause_id, fragment, files):
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert fragment in text, f"{clause_id} fragment missing in {path}: {fragment!r}"


@needs_overlay
@pytest.mark.parametrize("clause_id, fragment, files", OVERLAY_CLAUSE_FILE_ASSERTIONS)
def test_overlay_clause_fragment_present(clause_id, fragment, files):
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert fragment in text, f"{clause_id} fragment missing in {path}: {fragment!r}"


# ---------------------------------------------------------------------------
# 2. Mirror parity
# ---------------------------------------------------------------------------

def test_d1b_trace_in_all_reviewer_files():
    for path in D1B_FILES:
        assert D1B_FRAGMENT in path.read_text(encoding="utf-8")


def test_d1c_trace_in_all_base_qa_bodies():
    for path in D1C_BASE_FILES:
        assert D1C_FRAGMENT in path.read_text(encoding="utf-8")


@needs_overlay
def test_d1c_trace_in_overlay_qa():
    assert D1C_FRAGMENT in OVERLAY_QA.read_text(encoding="utf-8")


def test_d1d_timeout_and_fallback_in_all_base_qa_bodies():
    for path in D1D_BASE_FILES:
        text = path.read_text(encoding="utf-8")
        assert D1D_FRAGMENT in text
        assert D1D_FALLBACK_FRAGMENT in text


@needs_overlay
def test_d1d_timeout_and_fallback_in_overlay_qa():
    text = OVERLAY_QA.read_text(encoding="utf-8")
    assert D1D_FRAGMENT in text
    assert D1D_FALLBACK_FRAGMENT in text


def test_d1e_workspace_in_all_architect_files():
    for path in D1E_FILES:
        assert D1E_FRAGMENT in path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 3. Ordering pins
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("clause_id, anchor, files", D1B_SIGN_OFF_ANCHORS)
def test_d1b_trace_precedes_sign_off(clause_id, anchor, files):
    for path in files:
        text = path.read_text(encoding="utf-8")
        trace_pos = text.find(D1B_FRAGMENT)
        sign_off_pos = text.find(anchor)
        assert trace_pos != -1, f"{clause_id} trace missing in {path}"
        assert sign_off_pos != -1, f"{path}: sign-off anchor missing: {anchor!r}"
        assert trace_pos < sign_off_pos, (
            f"{path}: D1b {clause_id} trace must precede sign-off anchor {anchor!r}"
        )


@pytest.mark.parametrize("path", D1D_BASE_FILES)
def test_d1d_timeout_precedes_d1c_trace(path):
    text = path.read_text(encoding="utf-8")
    timeout_pos = text.find(D1D_FRAGMENT)
    trace_pos = text.find(D1C_FRAGMENT)
    assert timeout_pos != -1
    assert trace_pos != -1
    assert timeout_pos < trace_pos, f"{path}: D1d timeout must precede D1c trace"


@needs_overlay
def test_d1d_timeout_precedes_d1c_trace_in_overlay_qa():
    text = OVERLAY_QA.read_text(encoding="utf-8")
    timeout_pos = text.find(D1D_FRAGMENT)
    trace_pos = text.find(D1C_FRAGMENT)
    assert timeout_pos != -1
    assert trace_pos != -1
    assert timeout_pos < trace_pos, f"{OVERLAY_QA}: D1d timeout must precede D1c trace"


# ---------------------------------------------------------------------------
# 4. Dirty-tree verify pins (20261017-1 already shipped by MDU-24)
# ---------------------------------------------------------------------------

DIRTY_TREE_FILES = (
    REPO_ROOT / "prompts" / "test-agent.md",
    REPO_ROOT / "grok" / "agents" / "test-agent.md",
    REPO_ROOT / "grok" / "agents" / "test-agent-pro.md",
)
DIRTY_TREE_OVERLAY_FILES = (
    OVERLAY_ROOT / "grok" / "agents" / "grok-test-agent.md",
    OVERLAY_ROOT / "grok" / "agents" / "grok-test-agent-pro.md",
)


@pytest.mark.parametrize("path", DIRTY_TREE_FILES)
def test_dirty_tree_bullet_present(path):
    text = path.read_text(encoding="utf-8")
    assert "**Dirty tree:**" in text, f"{path} missing Dirty tree bullet"
    assert "git stash clear" in text, f"{path} missing git stash clear"


@needs_overlay
@pytest.mark.parametrize("path", DIRTY_TREE_OVERLAY_FILES)
def test_dirty_tree_bullet_present_in_overlay_mirrors(path):
    text = path.read_text(encoding="utf-8")
    assert "**Dirty tree:**" in text, f"{path} missing Dirty tree bullet"
    assert "git stash clear" in text, f"{path} missing git stash clear"


# ---------------------------------------------------------------------------
# 5. Repoint pin
# ---------------------------------------------------------------------------

OPENCODE_JSON = REPO_ROOT / "opencode.json"


def test_orchestrator_model_repointed():
    config = json.loads(OPENCODE_JSON.read_text(encoding="utf-8"))
    orch = config["agents"]["orchestrator"]
    assert orch["model"] == "opencode-go/glm-5.3-flash"
    assert "(Go mid, glm-5.3-flash)" in orch["description"]


def test_other_mimo_rows_untouched():
    config = json.loads(OPENCODE_JSON.read_text(encoding="utf-8"))
    mimo_rows = [
        (name, agent["model"])
        for name, agent in config["agents"].items()
        if agent.get("model") == "opencode-go/mimo-v2.6-flash"
    ]
    assert len(mimo_rows) == 7, f"expected 7 mimo-v2.6-flash rows, found {len(mimo_rows)}: {mimo_rows}"
    assert "orchestrator" not in {name for name, _ in mimo_rows}


# ---------------------------------------------------------------------------
# 6. Checklist pins
# ---------------------------------------------------------------------------

CHECKLIST = REPO_ROOT / "docs" / "brief-checklist.md"

NEW_CHECKLIST_PINS = [
    ("20261030-5", "write paths repo-relative"),
    ("20261021-11", "traced as procedures"),
    ("20261021-11", "not presence-ticked"),
    ("20261021-11", "Prompt-text acceptance criteria"),
    ("20261017-1", "never run destructive git state commands"),
    ("20261021-8", "one simple `timeout <n> <command>` attempt"),
    ("20261021-8", "verified via orchestrator-attached output"),
]


@pytest.fixture(scope="module")
def checklist_lines() -> list[str]:
    return CHECKLIST.read_text(encoding="utf-8").splitlines()


@pytest.mark.parametrize("clause_id, fragment", NEW_CHECKLIST_PINS)
def test_new_checklist_clause_on_one_line_with_id(clause_id, fragment, checklist_lines):
    assert any(
        clause_id in line and fragment in line for line in checklist_lines
    ), f"{clause_id} ({fragment!r}) not on a single checklist line"
