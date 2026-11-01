"""MDU-49 definition batch 3: six queued clauses across nine source bodies.

Hermetic: repo reads only, no network, no git state, no writes outside the test
process. The seven full-clause constants below are the byte-identity authority:
they hold the §2-§7 blockquotes of docs/design/mdu-49-definition-batch-3.md
verbatim (design doc §11.1). Doc-consistency pins keep doc == test.

Clause-file pins resolve their root through `MDU49_TEST_ROOT`, so the mutation
matrix (design §11, AC-6) can point the suite at a /tmp copy with exactly one
clause stripped. Checklist and doc-consistency pins always read the real repo.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
OVERLAY_ROOT = REPO_ROOT.parent / "opencode_agents"
HAS_OVERLAY = OVERLAY_ROOT.is_dir()

# In a standalone base clone the overlay sibling is absent: skip only the pins
# that read overlay files (mdu-35 convention).
needs_overlay = pytest.mark.skipif(
    not HAS_OVERLAY, reason="overlay sibling opencode_agents/ not present"
)

# Clause-file root: overridable for the mutation matrix (design §11.6).
CLAUSE_ROOT = Path(os.environ.get("MDU49_TEST_ROOT", str(REPO_ROOT))).resolve()

DESIGN_DOC = REPO_ROOT / "docs" / "design" / "mdu-49-definition-batch-3.md"
CHECKLIST = REPO_ROOT / "docs" / "brief-checklist.md"

# ---------------------------------------------------------------------------
# The seven clause constants — verbatim §2-§7 blockquotes (generated from the doc).
# ---------------------------------------------------------------------------

D1_20261027_3 = (
    "Before dispatching QA, ensure runs/<mdu-id>/manifest.json has all completed "
    "phases, the verification block, a summary and completed_at; run "
    "scripts/lib/run_ledger.py validate and require exit 0; pass the exact "
    "manifest path to QA and require QA to validate it. After QA, only flip "
    "qa_grade (and re-run the validator)."
)

D2_20261030_3 = (
    "For any wording/term sweep, do not hand-list target files: grep the old term "
    "across BOTH repos (source and built/installed trees), attach the full "
    "file:line hit list to the implement brief, and require the pin test to fail "
    "on any remaining live hit rather than pinning a file count. Name "
    "dead/ignored copies explicitly as excluded, with the reason."
)

D3_20261021_9 = (
    "Before delegating a phase, check the target agent's shell allowlist in "
    "opencode.json against the commands that phase requires. A phase that must "
    "execute an arbitrary script or an unrestricted command routes to devops or "
    "runs in the orchestrator session; QA and other inspection agents receive the "
    "produced artifacts to grade. Do not assign a phase to an agent whose "
    "allowlist cannot run its commands — verify the permission profile at design "
    "time, not mid-run."
)

D4_20261031_1 = (
    "Design may be conducted in-conversation by the orchestrator INSTEAD of "
    "dispatching the architect only when (a) the orchestrator has already "
    "gathered the design inputs live in this session (evidence, probes, config "
    "reads), (b) the MDU is diagnosis/recommendation rather than "
    "new-code-shaping, and (c) the deviation is recorded in the manifest design "
    "note with its justification. Any other in-conversation design is a "
    "delegation-loop violation (20261014-1 class)."
)

D5_CODER_20261031_2 = (
    "An edit/write tool result that looks corrupted or unexpected (oldString "
    "mismatch, phantom content in the echoed result, truncated output) is "
    "UNTRUSTED until verified: grep or read the target file on disk and confirm "
    "the actual state before quoting the result anywhere — manifests, briefs, "
    "verdicts. Never propagate edit-result display text as truth."
)

D5_ORCH_20261031_2 = (
    "An edit/write tool result that looks corrupted or unexpected (oldString "
    "mismatch, phantom content in the echoed result, truncated output) is "
    "UNTRUSTED until verified: grep or read the target file on disk and confirm "
    "the actual state before quoting the result anywhere — manifests, briefs, "
    "verdicts. Never propagate edit-result display text as truth. The run-ledger "
    "validation discipline covers the manifest side; this covers the general "
    "case."
)

D6_20261101_1 = (
    "Before recording that a definition change is unapplied (or letting that "
    "claim drive a closure decision), grep the target file(s) for the clause text "
    "— file tools on the working tree are the floor; when shell is available, "
    "check HEAD and cite the commit hash that added or last changed it (a "
    "`timeout`-wrapped `git log`, e.g. `timeout 30 git log --oneline -- <file>`, "
    "works); if shell is denied, record the on-disk grep and the denial instead "
    "of skipping the check. A stale claim is corrected with evidence, not "
    "repeated; if the clause is present, close or re-scope the suggestion instead "
    "of noting 'still unapplied'."
)

# ---------------------------------------------------------------------------
# Targets: 9 source files (design §0/§8). Base paths honor MDU49_TEST_ROOT;
# the overlay grokestrator is a live personal agent outside every build, so it
# always reads the real sibling repo.
# ---------------------------------------------------------------------------

BASE_ORCH_FILES = [
    ("prompts/orchestrator.md", CLAUSE_ROOT / "prompts" / "orchestrator.md"),
    ("grok/agents/orchestrator.md", CLAUSE_ROOT / "grok" / "agents" / "orchestrator.md"),
]
GROKESTRATOR = ("grok/agents/grokestrator.md", OVERLAY_ROOT / "grok" / "agents" / "grokestrator.md")
CODER_FILES = [
    ("prompts/just-code.md", CLAUSE_ROOT / "prompts" / "just-code.md"),
    ("grok/agents/just-code.md", CLAUSE_ROOT / "grok" / "agents" / "just-code.md"),
    ("grok/agents/just-code-mid.md", CLAUSE_ROOT / "grok" / "agents" / "just-code-mid.md"),
    ("grok/agents/just-code-pro.md", CLAUSE_ROOT / "grok" / "agents" / "just-code-pro.md"),
]
INTROSPECTOR_FILES = [
    ("prompts/introspector.md", CLAUSE_ROOT / "prompts" / "introspector.md"),
    ("grok/agents/introspector.md", CLAUSE_ROOT / "grok" / "agents" / "introspector.md"),
]

# Per-mirror anchors differ where the body is condensed (grokestrator), so each
# mirror carries its own anchor tuple: (label, path, model header, guardrail
# anchor the D5 bullet precedes).
_BASE_MIRRORS = [
    (
        "prompts/orchestrator.md",
        CLAUSE_ROOT / "prompts" / "orchestrator.md",
        "**MODEL SELECTION",
        "**Human Approval Gates:**",
    ),
    (
        "grok/agents/orchestrator.md",
        CLAUSE_ROOT / "grok" / "agents" / "orchestrator.md",
        "**MODEL SELECTION",
        "**Human Approval Gates:**",
    ),
]
_OVERLAY_MIRROR = (
    "grok/agents/grokestrator.md",
    OVERLAY_ROOT / "grok" / "agents" / "grokestrator.md",
    "- **MODEL SELECTION",
    "**QUESTION TOOL",
)
ORCH_MIRRORS = _BASE_MIRRORS + ([_OVERLAY_MIRROR] if HAS_OVERLAY else [])

FINALIZE_ANCHOR = "  - Finalize order: set final `status`"
CODER_HANDOFF_ANCHOR = "- **CODER HANDOFF:**"
VERIFY_ANCHOR = "- Always verify your work: build, lint, test."
SECRETS_ANCHOR = "- **NEVER commit secrets**"
INTROSPECT_UPDATE_ANCHOR = "- Update `agent-improvements.md`"
INTROSPECT_WRITE_ANCHOR = "- Also write `runs/<mdu-id>/introspection.md`"

# Full emitted bullet (lead included) per clause — the byte-identity authority.
BASE_PRESENCE_PINS = [
    ("20261027-3", "D1", "  - " + D1_20261027_3, BASE_ORCH_FILES),
    ("20261030-3", "D2", "- **Wording/term sweeps:** " + D2_20261030_3, BASE_ORCH_FILES),
    ("20261021-9", "D3", "- **Phase-routing pre-check:** " + D3_20261021_9, BASE_ORCH_FILES),
    ("20261031-1", "D4", "- **Design-phase delegation:** " + D4_20261031_1, BASE_ORCH_FILES),
    ("20261031-2", "D5-orch", "- **DISPLAY INTEGRITY:** " + D5_ORCH_20261031_2, BASE_ORCH_FILES),
    ("20261031-2", "D5-coder", "- " + D5_CODER_20261031_2, CODER_FILES),
    ("20261101-1", "D6", "- " + D6_20261101_1, INTROSPECTOR_FILES),
]

OVERLAY_PRESENCE_PINS = [
    ("20261027-3", "D1", "  - " + D1_20261027_3),
    ("20261030-3", "D2", "- **Wording/term sweeps:** " + D2_20261030_3),
    ("20261021-9", "D3", "- **Phase-routing pre-check:** " + D3_20261021_9),
    ("20261031-1", "D4", "- **Design-phase delegation:** " + D4_20261031_1),
    ("20261031-2", "D5-orch", "- **DISPLAY INTEGRITY:** " + D5_ORCH_20261031_2),
]

ALL_CONSTANTS = [
    ("20261027-3", "D1", D1_20261027_3),
    ("20261030-3", "D2", D2_20261030_3),
    ("20261021-9", "D3", D3_20261021_9),
    ("20261031-1", "D4", D4_20261031_1),
    ("20261031-2", "D5-coder", D5_CODER_20261031_2),
    ("20261031-2", "D5-orch", D5_ORCH_20261031_2),
    ("20261101-1", "D6", D6_20261101_1),
]


def _text(path: Path) -> str:
    assert path.is_file(), f"missing clause target: {path}"
    return path.read_text(encoding="utf-8")


def _line_containing(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle in line:
            return line
    raise AssertionError(f"needle not found in any line: {needle[:60]!r}")


def _assert_order(path: Path, first: str, second: str, label: str) -> None:
    text = _text(path)
    first_pos = text.find(first)
    second_pos = text.find(second)
    assert first_pos != -1, f"{path}: {label} clause missing (searched {first[:50]!r})"
    assert second_pos != -1, f"{path}: ordering anchor missing ({second[:50]!r})"
    assert first_pos < second_pos, f"{path}: {label} must precede {second[:50]!r}"


# ---------------------------------------------------------------------------
# 1. Full-clause presence — 16 base file assertions + 5 overlay-gated ones = 21
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("clause_id, clause_name, emitted, files", BASE_PRESENCE_PINS)
def test_clause_present_in_each_file(clause_id, clause_name, emitted, files):
    for label, path in files:
        text = _text(path)
        assert emitted in text, (
            f"{clause_id} {clause_name} clause is not byte-identical in {label}\n"
            f"expected: {emitted!r}"
        )


@needs_overlay
@pytest.mark.parametrize("clause_id, clause_name, emitted", OVERLAY_PRESENCE_PINS)
def test_clause_present_in_grokestrator(clause_id, clause_name, emitted):
    label, path = GROKESTRATOR
    text = _text(path)
    assert emitted in text, (
        f"{clause_id} {clause_name} clause is not byte-identical in {label}\n"
        f"expected: {emitted!r}"
    )


# ---------------------------------------------------------------------------
# 2. Doc consistency — the test constants are the doc's blockquotes (always the
#    real repo doc, never the mutation copy)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("clause_id, clause_name, clause", ALL_CONSTANTS)
def test_constant_matches_design_doc_blockquote(clause_id, clause_name, clause):
    doc = _text(DESIGN_DOC)
    assert clause in doc, (
        f"{clause_id} {clause_name} constant drifted from the design doc blockquote"
    )


# ---------------------------------------------------------------------------
# 3. Mirror parity
# ---------------------------------------------------------------------------

def test_d5_coder_is_substring_of_d5_orch():
    assert D5_CODER_20261031_2 in D5_ORCH_20261031_2, (
        "D5 coder shape must be a strict substring of the orchestrator shape"
    )
    assert D5_ORCH_20261031_2 != D5_CODER_20261031_2


@pytest.mark.parametrize("label, path", [(label, path) for label, path in CODER_FILES])
def test_d5_coder_sentences_in_every_coder_body(label, path):
    assert D5_CODER_20261031_2 in _text(path)


def test_d5_coder_sentences_in_every_orchestrator_body():
    for label, path, _model, _gate in ORCH_MIRRORS:
        text = _text(path)
        assert D5_CODER_20261031_2 in text, f"{label}: D5 sentences 1-2 missing"
        assert D5_ORCH_20261031_2 in text, f"{label}: D5 sentence 3 missing"


@pytest.mark.parametrize("label, path", [(label, path) for label, path in CODER_FILES])
def test_d5_sentence3_absent_from_coder_bodies(label, path):
    # Sentence 3 is orchestrator-only (design §6 scope ruling).
    assert D5_ORCH_20261031_2 not in _text(path), (
        f"{label}: the coder shape must not carry D5 sentence 3"
    )


MIRROR_LINE_PINS = [
    ("20261027-3", "D1", D1_20261027_3),
    ("20261030-3", "D2", D2_20261030_3),
    ("20261021-9", "D3", D3_20261021_9),
    ("20261031-1", "D4", D4_20261031_1),
    ("20261031-2", "D5-orch", D5_ORCH_20261031_2),
]


@pytest.mark.parametrize("clause_id, clause_name, clause", MIRROR_LINE_PINS)
def test_clause_line_byte_identical_across_mirrors(clause_id, clause_name, clause):
    lines = {_line_containing(_text(path), clause) for _label, path, _m, _g in ORCH_MIRRORS}
    assert len(lines) == 1, (
        f"{clause_id} {clause_name} line differs across mirrors:\n" + "\n".join(sorted(lines))
    )


# ---------------------------------------------------------------------------
# 4. Ordering / adjacency pins
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label, path, model_anchor, gate_anchor", ORCH_MIRRORS)
def test_d1_precedes_finalize_order(label, path, model_anchor, gate_anchor):
    _assert_order(path, "  - " + D1_20261027_3, FINALIZE_ANCHOR, "D1")


@pytest.mark.parametrize("label, path, model_anchor, gate_anchor", ORCH_MIRRORS)
def test_d4_d3_d2_cluster_order_before_model_selection(label, path, model_anchor, gate_anchor):
    text = _text(path)
    d4 = text.find("- **Design-phase delegation:** " + D4_20261031_1)
    d3 = text.find("- **Phase-routing pre-check:** " + D3_20261021_9)
    d2 = text.find("- **Wording/term sweeps:** " + D2_20261030_3)
    model = text.find(model_anchor)
    assert d4 != -1, f"{label}: D4 missing"
    assert d3 != -1, f"{label}: D3 missing"
    assert d2 != -1, f"{label}: D2 missing"
    assert model != -1, f"{label}: model-selection header missing"
    assert d4 < d3 < d2 < model, (
        f"{label}: cluster must read D4 < D3 < D2 < MODEL SELECTION "
        f"(got {d4}, {d3}, {d2}, {model})"
    )


@pytest.mark.parametrize("label, path, model_anchor, gate_anchor", ORCH_MIRRORS)
def test_d5_sits_between_coder_handoff_and_next_guardrail(label, path, model_anchor, gate_anchor):
    _assert_order(path, "- **DISPLAY INTEGRITY:** " + D5_ORCH_20261031_2, gate_anchor, "D5")
    _assert_order(path, CODER_HANDOFF_ANCHOR, "- **DISPLAY INTEGRITY:**", "CODER HANDOFF before D5")


@pytest.mark.parametrize("label, path", [(label, path) for label, path in CODER_FILES])
def test_d5_coder_between_verify_and_secret_gates(label, path):
    _assert_order(path, VERIFY_ANCHOR, "- " + D5_CODER_20261031_2, "D5 coder")
    _assert_order(path, "- " + D5_CODER_20261031_2, SECRETS_ANCHOR, "D5 coder")


@pytest.mark.parametrize("label, path", [(label, path) for label, path in INTROSPECTOR_FILES])
def test_d6_follows_update_and_precedes_write(label, path):
    _assert_order(path, INTROSPECT_UPDATE_ANCHOR, "- " + D6_20261101_1, "D6")
    _assert_order(path, "- " + D6_20261101_1, INTROSPECT_WRITE_ANCHOR, "D6")


# ---------------------------------------------------------------------------
# 5. Checklist pins (design §14) — dispatch-time fallback rows
# ---------------------------------------------------------------------------

NEW_CHECKLIST_PINS = [
    ("20261030-3", "grep the old term across BOTH repos"),
    ("20261031-2", "verify the file on disk"),
    ("20261101-1", "cite the commit hash when git is available"),
]


@pytest.fixture(scope="module")
def checklist_lines() -> list[str]:
    return _text(CHECKLIST).splitlines()


@pytest.mark.parametrize("clause_id, fragment", NEW_CHECKLIST_PINS)
def test_new_checklist_clause_on_one_line_with_id(clause_id, fragment, checklist_lines):
    matching = [line for line in checklist_lines if clause_id in line and fragment in line]
    assert matching, f"[{clause_id}] row with {fragment!r} not found on a single line"
    assert matching[0].lstrip().startswith("- "), (
        f"[{clause_id}] row is not a single bullet: {matching[0]!r}"
    )
