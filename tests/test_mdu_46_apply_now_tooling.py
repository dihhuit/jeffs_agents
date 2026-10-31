"""Tests for MDU-46 apply-now tooling.

Three groups:

* the OPTIONAL top-level ``model`` field in ``scripts/lib/run_ledger.py``
  (validation, summarize/format_summary surfacing, CLI) plus the parity pin
  that keeps the field out of ``REQUIRED_FIELDS``;
* the apply-now clause pins in ``docs/brief-checklist.md``;
* the local upstream draft in ``docs/upstream-drafts/`` (filing gate, masked
  evidence pointer, no submission mechanics).

Hermetic: ``tmp_path`` for anything written, repo-doc reads for the pins, no
network and no git state.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import run_ledger as ledger


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = REPO_ROOT / "docs" / "brief-checklist.md"
DRAFT = REPO_ROOT / "docs" / "upstream-drafts" / "opencode-question-60min-kill.md"

VALID_MODEL = "opencode-go/glm-5.3-flash"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _valid_manifest() -> dict:
    """A complete manifest carrying no ``model`` key at all."""
    return {
        "mdu_id": "mdu-99",
        "title": "MDU-99 widget",
        "status": "completed",
        "harness": "opencode",
        "started_at": "2026-09-15T08:00:00Z",
        "completed_at": "2026-09-15T12:00:00Z",
        "phases": [
            {
                "phase": "design",
                "agent": "architect",
                "model_tier": "budget",
                "outcome": "pass",
                "notes": "Kept it minimal.",
            }
        ],
        "fix_iterations": 0,
        "autonomy_level": 2,
        "verification": {
            "build": True,
            "tests_passed": 1,
            "tests_total": 1,
            "qa_grade": "PASS",
            "ci_green": True,
        },
        "artifacts": ["docs/widget.md"],
        "summary": "Closed the loop on widgets.",
    }


# ---------------------------------------------------------------------------
# (a) ledger model field
# ---------------------------------------------------------------------------

def test_model_absent_is_valid():
    manifest = _valid_manifest()
    assert "model" not in manifest
    assert ledger.validate_manifest(manifest) == []


def test_model_valid_string_is_valid():
    manifest = _valid_manifest()
    manifest["model"] = VALID_MODEL
    assert ledger.validate_manifest(manifest) == []


def test_model_whitespace_only_passes():
    """Non-empty is the whole rule; no trimming logic."""
    manifest = _valid_manifest()
    manifest["model"] = " "
    assert ledger.validate_manifest(manifest) == []


def test_model_empty_string_fails():
    manifest = _valid_manifest()
    manifest["model"] = ""
    errors = ledger.validate_manifest(manifest)
    assert errors == ["'model' must be a non-empty string"]


@pytest.mark.parametrize("value", [7, ["a"], {"id": "x"}, None, True])
def test_model_non_string_fails(value):
    manifest = _valid_manifest()
    manifest["model"] = value
    errors = ledger.validate_manifest(manifest)
    assert errors == ["'model' must be a non-empty string"]


def test_model_stays_out_of_required_fields():
    """Parity protection: the inline prompt example carries no model key."""
    assert "model" not in ledger.REQUIRED_FIELDS
    assert "model" not in ledger.REQUIRED_VERIFICATION_FIELDS


def _manifest_with_model(model: str | None) -> dict:
    manifest = _valid_manifest()
    if model is not None:
        manifest["model"] = model
    return manifest


def test_summarize_counts_by_model():
    stats = ledger.summarize(
        [
            _manifest_with_model(VALID_MODEL),
            _manifest_with_model(None),
        ]
    )
    assert stats["by_model"] == {VALID_MODEL: 1}
    # No pre-seeded keys for models that never occur.
    assert stats["manifests"] == 2


def test_summarize_by_model_is_empty_without_models():
    stats = ledger.summarize([_manifest_with_model(None)])
    assert stats["by_model"] == {}


def test_format_summary_prints_by_model_block():
    stats = ledger.summarize([_manifest_with_model(VALID_MODEL)])
    text = ledger.format_summary(stats)
    assert "by model:" in text
    assert VALID_MODEL in text
    # the block sits after the harness block, before the phase counters
    assert text.index("by harness:") < text.index("by model:")
    assert text.index("by model:") < text.index("phases recorded:")


def test_format_summary_prints_none_without_models():
    stats = ledger.summarize([_manifest_with_model(None)])
    text = ledger.format_summary(stats)
    block = text.split("by model:", 1)[1]
    assert block.splitlines()[1] == "  (none)"


def test_cli_validate_accepts_manifest_with_model(tmp_path, capsys):
    manifest = _manifest_with_model(VALID_MODEL)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    assert ledger.main(["validate", str(path)]) == 0
    assert "is a valid run manifest" in capsys.readouterr().out


def test_cli_validate_rejects_empty_model(tmp_path, capsys):
    manifest = _manifest_with_model("")
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    assert ledger.main(["validate", str(path)]) == 1
    assert "'model' must be a non-empty string" in capsys.readouterr().out


def test_cli_summarize_json_exposes_by_model(tmp_path, capsys):
    runs = tmp_path / "runs"
    (runs / "mdu-99").mkdir(parents=True)
    (runs / "mdu-99" / "manifest.json").write_text(
        json.dumps(_manifest_with_model(VALID_MODEL)), encoding="utf-8"
    )

    assert ledger.main(["summarize", str(runs), "--json"]) == 0
    stats = json.loads(capsys.readouterr().out)
    assert stats["by_model"] == {VALID_MODEL: 1}


# ---------------------------------------------------------------------------
# (b) docs/brief-checklist.md pins
# ---------------------------------------------------------------------------

# (id, fragment) pairs from the MDU-46 design; the id and the fragment must
# land on the same line so the clause cannot be listed without its citation.
CHECKLIST_PINS = [
    ("20261014-1", "what-done-looks-like"),
    ("20261014-2", "20-line excerpt"),
    ("20261021-12", "evidence producer"),
    ("20261030-2", "denied by design"),
    ("20261027-3", "before dispatching qa"),
    ("20261014-5", "final manifest path"),
    ("20261026-2", "model field"),
    ("20261024-1", "surveyed-file list"),
    ("20261029-1", "second response"),
]


@pytest.fixture(scope="module")
def checklist_lines() -> list[str]:
    assert CHECKLIST.is_file(), f"missing checklist doc: {CHECKLIST.name}"
    return [
        line.lower()
        for line in CHECKLIST.read_text(encoding="utf-8").splitlines()
    ]


@pytest.mark.parametrize("clause_id, fragment", CHECKLIST_PINS)
def test_checklist_clause_on_one_line_with_id(clause_id, fragment, checklist_lines):
    assert any(
        clause_id.lower() in line and fragment.lower() in line
        for line in checklist_lines
    ), f"{clause_id} ({fragment!r}) is not on a single checklist line"


def test_checklist_states_it_is_a_doc_not_a_definition():
    text = CHECKLIST.read_text(encoding="utf-8").lower()
    assert "doc, not a prompt" in text
    assert "prompts/" in text
    assert "grok/agents/" in text


@pytest.mark.parametrize(
    "role_heading",
    [
        "## architect",
        "## just-code / fix child",
        "## code-reviewer",
        "## test-agent",
        "## devops",
        "## qa",
        "## introspector",
    ],
)
def test_checklist_names_every_role_template(role_heading):
    text = CHECKLIST.read_text(encoding="utf-8")
    assert role_heading in text


# ---------------------------------------------------------------------------
# (c) local upstream draft pins
# ---------------------------------------------------------------------------

FORBIDDEN_SUBMISSION_MECHANICS = [
    "gh issue",
    "gh pr",
    "git remote",
    "git push",
    "git clone",
    "file this issue",
    "file it now",
]


def test_upstream_draft_exists():
    assert DRAFT.is_file(), f"missing upstream draft: {DRAFT.name}"


def test_upstream_draft_banner_is_at_the_top():
    head = DRAFT.read_text(encoding="utf-8").splitlines()[:10]
    assert any("FILING GATED" in line for line in head)


@pytest.mark.parametrize("forbidden", FORBIDDEN_SUBMISSION_MECHANICS)
def test_upstream_draft_has_no_submission_mechanics(forbidden):
    text = DRAFT.read_text(encoding="utf-8").lower()
    assert forbidden not in text


def test_upstream_draft_cites_masked_evidence_pointer():
    text = DRAFT.read_text(encoding="utf-8")
    assert "runs/mdu-35-question-tool/evidence.md" in text
