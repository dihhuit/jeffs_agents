"""Tests for the run ledger (scripts/lib/run_ledger.py).

Covers ``validate_manifest`` (schema + enum checks), ``validate_file``,
``load_manifests``, ``summarize`` aggregation, and the ``validate`` /
``summarize`` CLI paths of ``main``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import run_ledger as ledger


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _valid_manifest() -> dict:
    """A complete manifest that passes every schema check."""
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
            },
            {
                "phase": "test",
                "agent": "test-agent",
                "model_tier": "mid",
                "outcome": "fail",
                "notes": "Found a flake.",
            },
        ],
        "fix_iterations": 2,
        "autonomy_level": 2,
        "verification": {
            "build": True,
            "tests_passed": 10,
            "tests_total": 12,
            "qa_grade": "PASS",
            "ci_green": True,
        },
        "artifacts": ["src/widget.py"],
        "summary": "Closed the loop on widgets.",
    }


def _as_manifest(mdu_id: str) -> dict:
    """A valid manifest with a distinct id, status and test numbers."""
    data = _valid_manifest()
    data["mdu_id"] = mdu_id
    return data


def _write_manifest(runs_dir: Path, mdu_id: str, **overrides) -> Path:
    """Write manifest.json for a subdir of runs_dir; return the file path."""
    data = _as_manifest(mdu_id)
    data.update(overrides)
    manifest_dir = runs_dir / mdu_id
    manifest_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_dir / "manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# validate_manifest
# ---------------------------------------------------------------------------

def test_validate_manifest_valid_complete_manifest() -> None:
    assert ledger.validate_manifest(_valid_manifest()) == []


def test_validate_manifest_missing_required_field() -> None:
    data = _valid_manifest()
    del data["title"]
    errors = ledger.validate_manifest(data)
    assert any(err == "missing required field: 'title'" for err in errors)


def test_validate_manifest_bad_status_enum() -> None:
    data = _valid_manifest()
    data["status"] = "bogus"
    errors = ledger.validate_manifest(data)
    assert any("invalid status 'bogus'" in err for err in errors)
    assert any("expected one of" in err for err in errors)


@pytest.mark.parametrize("harness", ["opencode", "grok", "claude"])
def test_validate_manifest_valid_harness_values(harness: str) -> None:
    data = _valid_manifest()
    data["harness"] = harness
    assert ledger.validate_manifest(data) == []


def test_validate_manifest_missing_harness_field() -> None:
    data = _valid_manifest()
    del data["harness"]
    errors = ledger.validate_manifest(data)
    assert any(err == "missing required field: 'harness'" for err in errors)


def test_validate_manifest_invalid_harness() -> None:
    data = _valid_manifest()
    data["harness"] = "powershell"
    errors = ledger.validate_manifest(data)
    assert any(
        err
        == "harness must be one of opencode|grok|claude (got 'powershell')"
        for err in errors
    )


def test_validate_manifest_bad_model_tier_enum() -> None:
    data = _valid_manifest()
    data["phases"][0]["model_tier"] = "ultra"
    errors = ledger.validate_manifest(data)
    assert any(
        "phases[0] invalid model_tier 'ultra'" in err for err in errors
    )


def test_validate_manifest_bad_phase_enum() -> None:
    data = _valid_manifest()
    data["phases"][0]["phase"] = "build"
    errors = ledger.validate_manifest(data)
    assert any(
        "phases[0] invalid phase 'build'" in err for err in errors
    )


def test_validate_manifest_bad_outcome_enum() -> None:
    data = _valid_manifest()
    data["phases"][1]["outcome"] = "maybe"
    errors = ledger.validate_manifest(data)
    assert any(
        "phases[1] invalid outcome 'maybe'" in err for err in errors
    )


def test_validate_manifest_missing_phase_model_tier() -> None:
    data = _valid_manifest()
    del data["phases"][0]["model_tier"]
    errors = ledger.validate_manifest(data)
    assert any(
        err == "phases[0] missing required field: 'model_tier'"
        for err in errors
    )


@pytest.mark.parametrize("level", [7, -1, "2"])
def test_validate_manifest_bad_autonomy_level(level: object) -> None:
    data = _valid_manifest()
    data["autonomy_level"] = level
    errors = ledger.validate_manifest(data)
    assert any(
        "'autonomy_level' must be an integer in 0..4" in err
        for err in errors
    )


def test_validate_manifest_autonomy_level_boundaries_ok() -> None:
    for level in (0, 4):
        data = _valid_manifest()
        data["autonomy_level"] = level
        assert ledger.validate_manifest(data) == []


def test_validate_manifest_timestamp_wrong_type() -> None:
    data = _valid_manifest()
    data["started_at"] = 1234567890
    errors = ledger.validate_manifest(data)
    assert any(
        "'started_at' must be an ISO-8601 string" in err for err in errors
    )


def test_validate_manifest_phases_element_not_object() -> None:
    data = _valid_manifest()
    data["phases"] = ["design", dict(data["phases"][1])]
    errors = ledger.validate_manifest(data)
    assert any("phases[0] must be an object" in err for err in errors)


def test_validate_manifest_phases_not_array() -> None:
    data = _valid_manifest()
    data["phases"] = "design"
    errors = ledger.validate_manifest(data)
    assert any("'phases' must be an array" in err for err in errors)


def test_validate_manifest_verification_missing_subfield() -> None:
    data = _valid_manifest()
    del data["verification"]["ci_green"]
    errors = ledger.validate_manifest(data)
    assert any(
        err == "missing required field: 'verification.ci_green'"
        for err in errors
    )


def test_validate_manifest_verification_wrong_type() -> None:
    data = _valid_manifest()
    data["verification"]["tests_passed"] = "10"
    errors = ledger.validate_manifest(data)
    assert any(
        "'verification.tests_passed' must be an integer" in err
        for err in errors
    )


def test_validate_manifest_verification_not_object() -> None:
    data = _valid_manifest()
    data["verification"] = ["build", True]
    errors = ledger.validate_manifest(data)
    assert any("'verification' must be an object" in err for err in errors)


def test_validate_manifest_not_a_dict() -> None:
    assert ledger.validate_manifest(["not", "a", "dict"]) == [
        "manifest must be a JSON object"
    ]


# ---------------------------------------------------------------------------
# validate_file
# ---------------------------------------------------------------------------

def test_validate_file_valid_json_passes(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(_valid_manifest()), encoding="utf-8")
    ok, errors = ledger.validate_file(path)
    assert ok is True
    assert errors == []


def test_validate_file_invalid_json_syntax(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text("{ not json", encoding="utf-8")
    ok, errors = ledger.validate_file(path)
    assert ok is False
    assert len(errors) == 1
    assert "invalid JSON" in errors[0]
    assert "manifest.json" in errors[0]


def test_validate_file_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text("", encoding="utf-8")
    ok, errors = ledger.validate_file(path)
    assert ok is False
    assert len(errors) == 1
    assert "invalid JSON" in errors[0]


def test_validate_file_missing_file(tmp_path: Path) -> None:
    ok, errors = ledger.validate_file(tmp_path / "nope.json")
    assert ok is False
    assert errors[0].startswith("manifest not found: ")


# ---------------------------------------------------------------------------
# load_manifests
# ---------------------------------------------------------------------------

def test_load_manifests_reads_all_valid(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    _write_manifest(runs, "mdu-01")
    _write_manifest(runs, "mdu-02")
    manifests = ledger.load_manifests(runs)
    assert len(manifests) == 2
    ids = [data["mdu_id"] for _, data in manifests]
    assert ids == ["mdu-01", "mdu-02"]


def test_load_manifests_skips_corrupt_json(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    _write_manifest(runs, "mdu-01")
    bad = runs / "mdu-02" / "manifest.json"
    bad.parent.mkdir()
    bad.write_text("{ corrupt", encoding="utf-8")
    manifests = ledger.load_manifests(runs)
    assert len(manifests) == 1
    assert manifests[0][1]["mdu_id"] == "mdu-01"


def test_load_manifests_missing_dir_returns_empty(tmp_path: Path) -> None:
    assert ledger.load_manifests(tmp_path / "no-such-dir") == []


def test_load_manifests_skips_subdir_without_manifest(tmp_path: Path) -> None:
    (tmp_path / "runs" / "empty-run").mkdir(parents=True)
    assert ledger.load_manifests(tmp_path / "runs") == []


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------

def test_summarize_aggregates_across_manifests() -> None:
    first = _as_manifest("mdu-01")
    second = _as_manifest("mdu-02")
    second["status"] = "in_progress"
    second["phases"] = [
        {
            "phase": "implement",
            "agent": "just-code",
            "model_tier": "budget",
            "outcome": "pass",
            "notes": "ok",
        },
        {
            "phase": "deploy",
            "agent": "devops",
            "model_tier": "mid",
            "outcome": "pass",
            "notes": "ok",
        },
        {
            "phase": "validate",
            "agent": "qa",
            "model_tier": "premium",
            "outcome": "pass",
            "notes": "ok",
        },
    ]
    second["fix_iterations"] = 0
    second["verification"]["qa_grade"] = "FAIL"
    second["verification"]["tests_passed"] = 5
    second["verification"]["tests_total"] = 20

    stats = ledger.summarize([first, second])

    assert stats["manifests"] == 2
    assert stats["by_status"]["completed"] == 1
    assert stats["by_status"]["in_progress"] == 1
    assert stats["by_status"]["failed"] == 0
    assert stats["by_harness"] == {"claude": 0, "grok": 0, "opencode": 2}
    assert stats["phases_total"] == 5
    assert stats["phases_by_phase"]["design"] == 1
    assert stats["phases_by_phase"]["implement"] == 1
    assert stats["phases_by_phase"]["test"] == 1
    assert stats["phases_by_phase"]["deploy"] == 1
    assert stats["phases_by_phase"]["validate"] == 1
    assert stats["phases_by_tier"]["budget"] == 2
    assert stats["phases_by_tier"]["mid"] == 2
    assert stats["phases_by_tier"]["premium"] == 1
    assert stats["fix_iterations_total"] == 2
    assert stats["qa"] == {"PASS": 1, "FAIL": 1}
    assert stats["tests_total"] == 32
    assert stats["tests_passed"] == 15


def test_summarize_empty_manifest_list_is_zeroed() -> None:
    stats = ledger.summarize([])
    assert stats["manifests"] == 0
    assert all(count == 0 for count in stats["by_status"].values())
    assert stats["by_harness"] == {"claude": 0, "grok": 0, "opencode": 0}
    assert stats["phases_total"] == 0
    assert all(count == 0 for count in stats["phases_by_phase"].values())
    assert all(count == 0 for count in stats["phases_by_tier"].values())
    assert stats["fix_iterations_total"] == 0
    assert stats["qa"] == {"PASS": 0, "FAIL": 0}
    assert stats["tests_total"] == 0
    assert stats["tests_passed"] == 0


def test_summarize_by_harness_counts_mixed_set() -> None:
    opencode_docs = [
        _as_manifest("mdu-01"),
        _as_manifest("mdu-02"),
    ]
    grok_doc = _as_manifest("mdu-03")
    grok_doc["harness"] = "grok"
    unknown_doc = _as_manifest("mdu-04")
    unknown_doc["harness"] = "powershell"  # not a valid harness

    stats = ledger.summarize([*opencode_docs, grok_doc, unknown_doc])

    # Unknown harnesses still count as manifests but are not tallied.
    assert stats["manifests"] == 4
    assert stats["by_harness"] == {"claude": 0, "grok": 1, "opencode": 2}


def test_summarize_ignores_garbage_entries_without_crashing() -> None:
    stats = ledger.summarize(
        [
            {"status": "completed"},  # no verification, phases, fix_iterations
            {"phases": ["string-phase"], "verification": "nope"},
        ]
    )
    assert stats["manifests"] == 2
    assert stats["by_status"]["completed"] == 1
    assert stats["phases_total"] == 0


def test_summarize_skips_non_dict_manifest_entries() -> None:
    stats = ledger.summarize(
        [
            {"status": "completed", "harness": "opencode"},
            ["not", "an", "object"],
            "just-a-string",
        ]
    )
    assert stats["manifests"] == 1
    assert stats["by_status"]["completed"] == 1
    assert stats["by_harness"] == {"claude": 0, "grok": 0, "opencode": 1}


# ---------------------------------------------------------------------------
# format_summary
# ---------------------------------------------------------------------------

def test_format_summary_by_harness_mixed_set() -> None:
    manifests = [
        _as_manifest("mdu-01"),
        _as_manifest("mdu-02"),
    ]
    grok_doc = _as_manifest("mdu-03")
    grok_doc["harness"] = "grok"
    text = ledger.format_summary(ledger.summarize([*manifests, grok_doc]))

    assert "by harness:" in text
    assert "  grok         1" in text
    assert "  opencode     2" in text
    # Zero-count harnesses are suppressed, not printed as "claude 0".
    assert "claude" not in text


def test_format_summary_by_harness_all_zero_shows_none() -> None:
    text = ledger.format_summary(ledger.summarize([]))
    assert "by harness:" in text
    assert "  (none)" in text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_validate_valid_manifest_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    path = _write_manifest(tmp_path / "runs", "mdu-01")
    code = ledger.main(["validate", str(path)])
    out = capsys.readouterr().out
    assert code == 0
    assert "[ok]" in out
    assert "is a valid run manifest" in out


def test_cli_validate_invalid_manifest_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"mdu_id": "mdu-01"}), encoding="utf-8")
    code = ledger.main(["validate", str(path)])
    out = capsys.readouterr().out
    assert code == 1
    assert "[fail]" in out
    assert "missing required field: 'title'" in out


def test_cli_validate_missing_manifest_exits_one(
    capsys: pytest.CaptureFixture,
) -> None:
    code = ledger.main(["validate", "no/such/manifest.json"])
    out = capsys.readouterr().out
    assert code == 1
    assert "manifest not found" in out


def test_cli_summarize_prints_text_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    runs = tmp_path / "runs"
    _write_manifest(runs, "mdu-01")
    code = ledger.main(["summarize", str(runs)])
    out = capsys.readouterr().out
    assert code == 0
    assert "Run ledger summary" in out
    assert "manifests:" in out
    assert "by status:" in out
    assert "by harness:" in out
    assert "completed" in out
    assert "phases recorded:" in out


def test_cli_summarize_json_is_parseable(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    runs = tmp_path / "runs"
    _write_manifest(runs, "mdu-01")
    code = ledger.main(["summarize", str(runs), "--json"])
    out = capsys.readouterr().out
    assert code == 0
    stats = json.loads(out)
    assert stats["manifests"] == 1
    assert stats["by_status"]["completed"] == 1
    assert "by_harness" in stats
    assert stats["by_harness"] == {"claude": 0, "grok": 0, "opencode": 1}


def test_cli_summarize_empty_dir_reports_info(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    empty = tmp_path / "empty-runs"
    empty.mkdir()
    code = ledger.main(["summarize", str(empty)])
    captured = capsys.readouterr()
    assert code == 0
    assert "(none)" in captured.out
    assert "no manifests found" in captured.err