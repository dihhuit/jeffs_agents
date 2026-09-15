"""Integration tests for the model-registry hooks in scripts/lib/validate.py.

Covers ``validate_model_refs``, ``print_live_drift``, and the ``--live-models``
flag path of ``validate.main`` using a minimal synthetic build directory.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import model_registry
import validate


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_snapshot(tmp_path: Path, *models: str) -> Path:
    path = tmp_path / "model-registry.txt"
    path.write_text("\n".join(models) + "\n", encoding="utf-8")
    return path


def _minimal_build(
    tmp_path: Path,
    *,
    agent_model: str = "model-a",
    prompt: str = "You are a test agent.",
) -> Path:
    """Create a build dir that passes all validate.py checks."""
    build = tmp_path / "build"
    (build / "grok" / "agents").mkdir(parents=True)
    (build / "claude" / "agents").mkdir(parents=True)
    (build / "prompts").mkdir(parents=True)

    (build / "opencode.json").write_text(
        json.dumps({"agent": {"test-agent": {"model": agent_model, "prompt": prompt}}}),
        encoding="utf-8",
    )
    (build / "grok" / "agents" / "test.md").write_text(
        "---\nname: test-agent\nmodel: grok-4.6\ndescription: \"test\"\n---\n",
        encoding="utf-8",
    )
    (build / "claude" / "agents" / "test.md").write_text(
        "---\nname: test-agent\ndescription: \"test\"\n---\n",
        encoding="utf-8",
    )
    return build


# ---------------------------------------------------------------------------
# validate_model_refs
# ---------------------------------------------------------------------------

def test_validate_model_refs_all_valid(tmp_path: Path) -> None:
    build = _minimal_build(tmp_path, agent_model="model-a")
    snapshot = _write_snapshot(tmp_path, "model-a")
    assert validate.validate_model_refs(build, snapshot) == []


def test_validate_model_refs_stale_model(tmp_path: Path) -> None:
    build = _minimal_build(tmp_path, agent_model="model-ghost")
    snapshot = _write_snapshot(tmp_path, "model-a")
    errors = validate.validate_model_refs(build, snapshot)
    assert len(errors) == 1
    assert "model-ghost" in errors[0]
    assert "test-agent" in errors[0]


def test_validate_model_refs_missing_opencode_json(tmp_path: Path) -> None:
    build = tmp_path / "empty-build"
    build.mkdir()
    snapshot = _write_snapshot(tmp_path, "model-a")
    errors = validate.validate_model_refs(build, snapshot)
    assert errors == ["missing opencode.json for model registry check"]


def test_validate_model_refs_missing_snapshot(tmp_path: Path) -> None:
    build = _minimal_build(tmp_path, agent_model="model-a")
    errors = validate.validate_model_refs(build, tmp_path / "missing-registry.txt")
    assert len(errors) == 1
    assert "model registry snapshot not found" in errors[0]


# ---------------------------------------------------------------------------
# print_live_drift
# ---------------------------------------------------------------------------

def test_print_live_drift_cli_unavailable(tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = _write_snapshot(tmp_path, "model-a")
    monkeypatch.setattr(model_registry.shutil, "which", lambda name: None)
    validate.print_live_drift(snapshot)
    out = capsys.readouterr().out
    assert "not on PATH" in out


def test_print_live_drift_prints_drift(tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = _write_snapshot(tmp_path, "model-a", "model-b")
    monkeypatch.setattr(model_registry.shutil, "which", lambda name: "/usr/local/bin/opencode")

    class FakeResult:
        returncode = 0
        stdout = "model-a\nmodel-c\n"

    monkeypatch.setattr(model_registry.subprocess, "run", lambda *a, **kw: FakeResult())
    validate.print_live_drift(snapshot)
    out = capsys.readouterr().out
    assert "1 removed, 1 added" in out
    assert "model-b" in out
    assert "model-c" in out


# ---------------------------------------------------------------------------
# validate.main integration
# ---------------------------------------------------------------------------

def test_validate_main_live_models_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    build = _minimal_build(tmp_path, agent_model="model-a")
    snapshot = _write_snapshot(tmp_path, "model-a")
    monkeypatch.setattr(validate, "DEFAULT_SNAPSHOT", snapshot)
    monkeypatch.setattr(model_registry.shutil, "which", lambda name: None)

    code = validate.main(["--live-models", str(build)])
    out = capsys.readouterr().out
    assert code == 0
    assert "model refs:" in out
    assert "not on PATH" in out


def test_validate_main_fails_on_stale_model(
    tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    build = _minimal_build(tmp_path, agent_model="model-ghost")
    snapshot = _write_snapshot(tmp_path, "model-a")
    monkeypatch.setattr(validate, "DEFAULT_SNAPSHOT", snapshot)

    code = validate.main([str(build)])
    out = capsys.readouterr().out
    assert code == 1
    assert "model-ghost" in out