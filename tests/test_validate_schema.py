"""Unit tests for the ``validate_schema`` JSON Schema check in scripts/lib/validate.py.

Covers the valid/invalid config paths, the missing-schema-file and missing-config
graceful handles, the skip-when-``jsonschema``-unavailable path, and the
schema-error reporting format (violation message + offending field path).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import validate


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

VALID_AGENT = {
    "mode": "subagent",
    "description": "test",
    "model": "model-a",
    "prompt": "You are a test agent.",
}


def _write_config(tmp_path: Path, agents: dict) -> Path:
    """Write build/opencode.json with the given ``agent`` mapping."""
    build = tmp_path / "build"
    build.mkdir(parents=True, exist_ok=True)
    (build / "opencode.json").write_text(
        json.dumps({"agent": agents}), encoding="utf-8"
    )
    return build


# ---------------------------------------------------------------------------
# valid config
# ---------------------------------------------------------------------------

def test_validate_schema_valid_config_passes(tmp_path: Path) -> None:
    build = _write_config(tmp_path, {"test-agent": dict(VALID_AGENT)})
    errors, ran = validate.validate_schema(build)
    assert ran is True
    assert errors == []


# ---------------------------------------------------------------------------
# schema violations
# ---------------------------------------------------------------------------

def test_validate_schema_invalid_mode_reports_field(tmp_path: Path) -> None:
    agent = dict(VALID_AGENT, mode="bogus")
    build = _write_config(tmp_path, {"test-agent": agent})
    errors, ran = validate.validate_schema(build)
    assert ran is True
    assert len(errors) == 1
    assert "opencode.json schema violation" in errors[0]
    assert "'bogus'" in errors[0]
    assert "mode" in errors[0]


def test_validate_schema_missing_required_fields_reported(tmp_path: Path) -> None:
    # Regression: the pre-MDU-03 fixture shape (only model + prompt) is invalid.
    build = _write_config(
        tmp_path, {"test-agent": {"model": "model-a", "prompt": "You are a test agent."}}
    )
    errors, ran = validate.validate_schema(build)
    assert ran is True
    assert len(errors) == 2
    assert any("'mode' is a required property" in err for err in errors)
    assert any("'description' is a required property" in err for err in errors)


# ---------------------------------------------------------------------------
# graceful handles
# ---------------------------------------------------------------------------

def test_validate_schema_jsonschema_unavailable_skips(
    tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    build = _write_config(tmp_path, {"test-agent": dict(VALID_AGENT)})
    # import jsonschema inside validate_schema raises ImportError, same as
    # an environment without the package installed.
    monkeypatch.setitem(sys.modules, "jsonschema", None)
    errors, ran = validate.validate_schema(build)
    out = capsys.readouterr().out
    assert ran is False
    assert errors == []
    assert "jsonschema not installed" in out


def test_validate_schema_missing_schema_file(tmp_path: Path) -> None:
    build = _write_config(tmp_path, {"test-agent": dict(VALID_AGENT)})
    missing = tmp_path / "no-such-schema.json"
    errors, ran = validate.validate_schema(build, missing)
    assert ran is True
    assert errors == [f"opencode schema not found: {missing}"]


def test_validate_schema_missing_opencode_json(tmp_path: Path) -> None:
    build = tmp_path / "empty-build"
    build.mkdir()
    errors, ran = validate.validate_schema(build)
    assert ran is True
    assert errors == ["missing opencode.json for schema check"]


def test_validate_schema_invalid_schema_json(tmp_path: Path) -> None:
    build = _write_config(tmp_path, {"test-agent": dict(VALID_AGENT)})
    bad_schema = tmp_path / "bad-schema.json"
    bad_schema.write_text("{ not json", encoding="utf-8")
    errors, ran = validate.validate_schema(build, bad_schema)
    assert ran is True
    assert len(errors) == 1
    assert "invalid JSON in schema" in errors[0]
    assert "bad-schema.json" in errors[0]