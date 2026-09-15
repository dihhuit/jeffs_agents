"""Tests for scripts/lib/model_registry.py.

Covers registry snapshot loading, model reference extraction from
opencode.json, stale-model checking, and the ``--check`` / ``--snapshot`` /
``--live`` CLI surface.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import model_registry
from model_registry import check_models, find_model_refs, load_registry


# ---------------------------------------------------------------------------
# load_registry
# ---------------------------------------------------------------------------

def test_load_registry_parses_snapshot_lines(tmp_path: Path) -> None:
    path = tmp_path / "models.txt"
    path.write_text("model-a\nmodel-b\nopencode/go/thing\n", encoding="utf-8")
    assert load_registry(path) == {"model-a", "model-b", "opencode/go/thing"}


def test_load_registry_tolerates_blank_lines_and_comments(tmp_path: Path) -> None:
    path = tmp_path / "models.txt"
    path.write_text(
        "model-a\n\n   \n# a comment\nmodel-b\n# another comment\n\n",
        encoding="utf-8",
    )
    assert load_registry(path) == {"model-a", "model-b"}


def test_load_registry_strips_whitespace(tmp_path: Path) -> None:
    path = tmp_path / "models.txt"
    path.write_text("  model-a  \n\tmodel-b\n", encoding="utf-8")
    assert load_registry(path) == {"model-a", "model-b"}


def test_load_registry_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_registry(tmp_path / "does-not-exist.txt")


# ---------------------------------------------------------------------------
# find_model_refs
# ---------------------------------------------------------------------------

def _write_opencode(tmp_path: Path, *, agents: dict | None = None, raw: str | None = None) -> Path:
    path = tmp_path / "opencode.json"
    if raw is not None:
        path.write_text(raw, encoding="utf-8")
    else:
        path.write_text(json.dumps({"agent": agents or {}}), encoding="utf-8")
    return path


def test_find_model_refs_returns_agent_model_pairs(tmp_path: Path) -> None:
    path = _write_opencode(
        tmp_path,
        agents={
            "agent-a": {"model": "model-1"},
            "agent-b": {"model": "model-2"},
        },
    )
    assert find_model_refs(path) == [("agent-a", "model-1"), ("agent-b", "model-2")]


def test_find_model_refs_skips_dict_valued_model(tmp_path: Path) -> None:
    path = _write_opencode(
        tmp_path,
        agents={
            "agent-a": {"model": {"provider": "opencode-go", "id": "thing"}},
            "agent-b": {"model": "model-1"},
        },
    )
    assert find_model_refs(path) == [("agent-b", "model-1")]


def test_find_model_refs_skips_agents_without_model(tmp_path: Path) -> None:
    path = _write_opencode(
        tmp_path,
        agents={
            "agent-a": {"description": "no model here"},
            "agent-b": {"model": "model-1"},
        },
    )
    assert find_model_refs(path) == [("agent-b", "model-1")]


def test_find_model_refs_skips_non_dict_agent_definitions(tmp_path: Path) -> None:
    path = _write_opencode(
        tmp_path,
        agents={
            "agent-a": "just a string",
            "agent-b": ["a", "list"],
            "agent-c": {"model": "model-1"},
        },
    )
    assert find_model_refs(path) == [("agent-c", "model-1")]


def test_find_model_refs_no_agent_key_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "opencode.json"
    path.write_text(json.dumps({"skills": []}), encoding="utf-8")
    assert find_model_refs(path) == []


def test_find_model_refs_invalid_json_raises(tmp_path: Path) -> None:
    path = _write_opencode(tmp_path, raw="{ definitely not json")
    with pytest.raises(json.JSONDecodeError):
        find_model_refs(path)


# ---------------------------------------------------------------------------
# check_models
# ---------------------------------------------------------------------------

def test_check_models_all_present_returns_empty() -> None:
    registry = {"model-1", "model-2", "model-3"}
    refs = [("agent-a", "model-1"), ("agent-b", "model-2"), ("agent-c", "model-3")]
    assert check_models(registry, refs) == []


def test_check_models_missing_refs_returns_errors_naming_ref() -> None:
    registry = {"model-1"}
    refs = [("agent-a", "model-1"), ("agent-b", "model-ghost")]
    errors = check_models(registry, refs)
    assert len(errors) == 1
    assert "agent-b" in errors[0]
    assert "model-ghost" in errors[0]


def test_check_models_multiple_missing_refs() -> None:
    errors = check_models({"model-1"}, [("a", "x"), ("b", "model-1"), ("c", "y")])
    assert len(errors) == 2
    assert any("'x'" in e and "'a'" in e for e in errors)
    assert any("'y'" in e and "'c'" in e for e in errors)


def test_check_models_empty_refs_returns_empty() -> None:
    assert check_models({"model-1"}, []) == []


# ---------------------------------------------------------------------------
# check_live
# ---------------------------------------------------------------------------

def test_check_live_cli_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(model_registry.shutil, "which", lambda name: None)
    result = model_registry.check_live(Path("/nonexistent/snapshot.txt"))
    assert result == {"removed": [], "added": [], "cli_found": False}


def test_check_live_diffs_snapshot_against_live(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    snapshot = tmp_path / "models.txt"
    snapshot.write_text("model-a\nmodel-b\n", encoding="utf-8")

    monkeypatch.setattr(model_registry.shutil, "which", lambda name: "/usr/local/bin/opencode")

    class FakeResult:
        returncode = 0
        stdout = "model-a\nmodel-c\n# comment line\n\n"

    monkeypatch.setattr(model_registry.subprocess, "run", lambda *a, **kw: FakeResult())
    result = model_registry.check_live(snapshot)
    assert result["cli_found"] is True
    assert result["removed"] == ["model-b"]
    assert result["added"] == ["model-c"]


# ---------------------------------------------------------------------------
# CLI: main()
# ---------------------------------------------------------------------------

def _snapshot(tmp_path: Path, *models: str) -> Path:
    path = tmp_path / "snapshot.txt"
    path.write_text("\n".join(models) + "\n", encoding="utf-8")
    return path


def test_cli_check_all_valid_exit_0(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    snapshot = _snapshot(tmp_path, "model-a", "model-b")
    config = _write_opencode(
        tmp_path,
        agents={"agent-a": {"model": "model-a"}, "agent-b": {"model": "model-b"}},
    )
    code = model_registry.main(["--check", str(config), "--snapshot", str(snapshot)])
    out = capsys.readouterr().out
    assert code == 0
    assert "[ok]" in out
    assert "2 model reference(s)" in out
    assert "all present in registry" in out


def test_cli_check_stale_ref_exit_1(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    snapshot = _snapshot(tmp_path, "model-a")
    config = _write_opencode(
        tmp_path,
        agents={"agent-a": {"model": "model-a"}, "agent-b": {"model": "stale-model"}},
    )
    code = model_registry.main(["--check", str(config), "--snapshot", str(snapshot)])
    out = capsys.readouterr().out
    assert code == 1
    assert "[fail]" in out
    assert "stale-model" in out


def test_cli_custom_snapshot_respected(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    # The default snapshot does not contain model-custom, so a pass proves the
    # --snapshot override was honored.
    snapshot = _snapshot(tmp_path, "model-custom")
    config = _write_opencode(tmp_path, agents={"agent-a": {"model": "model-custom"}})
    code = model_registry.main(["--check", str(config), "--snapshot", str(snapshot)])
    out = capsys.readouterr().out
    assert code == 0
    assert "1 model reference(s)" in out
    # success line names the custom snapshot path, proving the override won
    assert str(snapshot) in out


def test_cli_live_when_cli_unavailable_exit_0(
    tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot = _snapshot(tmp_path, "model-a")
    monkeypatch.setattr(model_registry.shutil, "which", lambda name: None)
    code = model_registry.main(["--live", "--snapshot", str(snapshot)])
    out = capsys.readouterr().out
    assert code == 0
    assert "not on PATH" in out


def test_cli_live_with_cli_on_path_prints_drift_exit_0(
    tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot = _snapshot(tmp_path, "model-a", "model-b")
    monkeypatch.setattr(model_registry.shutil, "which", lambda name: "/usr/local/bin/opencode")

    class FakeResult:
        returncode = 0
        stdout = "model-a\nmodel-c\n"

    monkeypatch.setattr(model_registry.subprocess, "run", lambda *a, **kw: FakeResult())
    code = model_registry.main(["--live", "--snapshot", str(snapshot)])
    out = capsys.readouterr().out
    assert code == 0
    assert "1 removed, 1 added" in out
    assert "model-b" in out
    assert "model-c" in out


def test_cli_live_with_no_drift_exit_0(
    tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot = _snapshot(tmp_path, "model-a")
    monkeypatch.setattr(model_registry.shutil, "which", lambda name: "/usr/local/bin/opencode")

    class FakeResult:
        returncode = 0
        stdout = "model-a\n"

    monkeypatch.setattr(model_registry.subprocess, "run", lambda *a, **kw: FakeResult())
    code = model_registry.main(["--live", "--snapshot", str(snapshot)])
    out = capsys.readouterr().out
    assert code == 0
    assert "0 removed, 0 added" in out


def test_cli_missing_snapshot_exit_1(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    config = _write_opencode(tmp_path, agents={"agent-a": {"model": "model-a"}})
    code = model_registry.main(
        ["--check", str(config), "--snapshot", str(tmp_path / "missing.txt")]
    )
    err = capsys.readouterr().err
    assert code == 1
    assert "snapshot not found" in err


def test_cli_missing_check_json_exit_1(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    snapshot = _snapshot(tmp_path, "model-a")
    code = model_registry.main(
        ["--check", str(tmp_path / "missing.json"), "--snapshot", str(snapshot)]
    )
    err = capsys.readouterr().err
    assert code == 1
    assert "opencode.json not found" in err


def test_cli_check_and_live_combined(tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = _snapshot(tmp_path, "model-a")
    config = _write_opencode(tmp_path, agents={"agent-a": {"model": "model-a"}})
    monkeypatch.setattr(model_registry.shutil, "which", lambda name: None)
    code = model_registry.main(["--check", str(config), "--live", "--snapshot", str(snapshot)])
    out = capsys.readouterr().out
    assert code == 0
    assert "[ok]" in out
    assert "not on PATH" in out