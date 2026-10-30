#!/usr/bin/env python3
"""MDU-38 tests: live model-health probe, report semantics, and gate wiring.

Rebaselined for MDU-40: the config is the single source of truth (no map, no
alternates), every model in ``opencode.json`` is a hard target, and the report
carries ``config_sha256`` over the sorted ``agent=model`` pairs.

Inference is stubbed through the injected ``runner`` (no subprocesses, no
network), and the deploy wiring is asserted by reading the shell scripts — the
same convention as ``test_mdu_30``.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import probe_models

REPO = Path(__file__).resolve().parent.parent
OVERLAY = REPO.parent / "opencode_agents"
DOC = REPO / "docs" / "model-registry.md"
README = REPO / "README.md"
CI = REPO / ".github" / "workflows" / "ci.yml"

#: Small config so refresh tests probe a handful of models (not the real set).
CONFIG = {
    "default_agent": "orchestrator",
    "agents": {
        "orchestrator": {"model": "opencode-go/mimo-v2.5"},
        "research": {"model": "opencode-go/deep-research"},
        "grok": {"model": "xai/grok-4.7"},
    },
}
TARGET = "opencode-go/mimo-v2.5"
SECOND = "opencode-go/deep-research"
XAI = "xai/grok-4.7"


@pytest.fixture(autouse=True)
def _opencode_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gate tests must not depend on a real CLI being installed."""
    monkeypatch.setattr(probe_models.shutil, "which", lambda _cli: "/usr/bin/opencode")
    monkeypatch.setattr(probe_models, "RETRY_SLEEP_S", 0.0)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_config(
    tmp_path: Path, config: dict | None = None, *, indent: int = 2
) -> Path:
    path = tmp_path / "opencode.json"
    path.write_text(json.dumps(config or CONFIG, indent=indent), encoding="utf-8")
    return path


def _stamp(*, days: float = 0.0, hours: float = 0.0) -> str:
    when = datetime.now(timezone.utc) + timedelta(days=days, hours=hours)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def _entry(model: str, role: str, status: str, error: str | None = None) -> dict:
    return {
        "model": model,
        "role": role,
        "status": status,
        "attempts": 1,
        "latency_s": 0.1,
        "error": error,
    }


def _entries(config_path: Path, statuses: dict | None = None) -> list[dict]:
    statuses = statuses or {}
    models = probe_models.collect_models(config_path).get("opencode-go", [])
    return [
        _entry(model, "target", statuses.get(model, "ok")) for model in models
    ]


def _xai_entries(config_path: Path, statuses: dict | None = None) -> list[dict]:
    statuses = statuses or {}
    models = probe_models.collect_models(config_path).get("xai", [])
    return [_entry(model, "xai", statuses.get(model, "ok")) for model in models]


def _report(
    config_path: Path,
    *,
    results: list[dict] | None = None,
    xai_results: list[dict] | None = None,
    probed_at: str | None = None,
    config_sha: str | None = None,
    schema_version: int = probe_models.SCHEMA_VERSION,
) -> dict:
    return {
        "schema_version": schema_version,
        "probed_at": probed_at or _stamp(),
        "mode": "refresh",
        "cli": "opencode",
        "timeout_s": 90,
        "config_path": probe_models._portable_path(config_path),
        "config_sha256": (
            config_sha
            if config_sha is not None
            else probe_models.config_sha256(config_path)
        ),
        "results": results if results is not None else _entries(config_path),
        "xai_results": (
            xai_results if xai_results is not None else _xai_entries(config_path)
        ),
    }


def _runner(
    *, failing: set[str] | None = None, error: str = "Model is unavailable", calls=None
):
    """Stub ``subprocess.run``: models in ``failing`` exit 1, the rest answer OK."""
    failing = failing or set()

    def run(cmd, **kwargs):
        model = cmd[3]
        if calls is not None:
            calls.append(list(cmd))
        if model in failing:
            return SimpleNamespace(returncode=1, stdout="", stderr=error)
        return SimpleNamespace(returncode=0, stdout="OK\n", stderr="")

    return run


def _gate(
    tmp_path: Path,
    config_path: Path | None = None,
    *,
    report: dict | str | None = None,
    max_age_days: int = 7,
) -> int:
    config_path = config_path or _write_config(tmp_path)
    report_path = tmp_path / "model-probe-report.json"
    if report is not None:
        text = report if isinstance(report, str) else json.dumps(report)
        report_path.write_text(text, encoding="utf-8")
    argv = [
        "--gate",
        "--config",
        str(config_path),
        "--report",
        str(report_path),
    ]
    if max_age_days != 7:
        argv += ["--max-age-days", str(max_age_days)]
    return probe_models.main(argv)


def _refresh(
    tmp_path: Path, runner, config_path: Path | None = None, **kwargs
) -> tuple[int, Path]:
    config_path = config_path or _write_config(tmp_path)
    report_path = tmp_path / "model-probe-report.json"
    argv = ["--refresh", "--config", str(config_path), "--report", str(report_path)]
    return probe_models.main(argv, runner=runner), report_path


# ---------------------------------------------------------------------------
# 1. probe_one: success, strictness, retry classification
# ---------------------------------------------------------------------------

def test_probe_one_ok_needs_exit_zero_and_ok_in_stdout() -> None:
    calls: list[list[str]] = []
    result = probe_models.probe_one(TARGET, runner=_runner(calls=calls))
    assert result["status"] == "ok"
    assert result["attempts"] == 1
    assert result["error"] is None
    assert calls == [
        ["opencode", "run", "-m", TARGET, "Reply with exactly: OK"]
    ]


def test_probe_one_zero_exit_without_ok_is_a_failure() -> None:
    def run(cmd, **kwargs):
        return SimpleNamespace(returncode=0, stdout="partial answer\n", stderr="")

    result = probe_models.probe_one(TARGET, runner=run)
    assert result["status"] == "fail"
    assert "no OK in output" in result["error"]
    # An unknown failure is retried once.
    assert result["attempts"] == 2


@pytest.mark.parametrize("stdout", ["NOT OK\n", "OKChrome"])
def test_probe_one_rejects_ok_substring_and_ok_prefix(stdout: str) -> None:
    """F1 regression pins: exact match only, not "contains OK" / "starts with OK"."""

    def run(cmd, **kwargs):
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    result = probe_models.probe_one(TARGET, runner=run)
    assert result["status"] == "fail"
    assert "no OK in output" in result["error"]
    # Neither string is a permanent signal, so the normal retry budget applies.
    assert result["attempts"] == 2


@pytest.mark.parametrize(
    "stderr", ["429 Too Many Requests", "500 Internal Server Error"]
)
def test_probe_one_transient_signal_is_retried(stderr: str) -> None:
    calls: list[list[str]] = []

    def run(cmd, **kwargs):
        calls.append(list(cmd))
        return SimpleNamespace(returncode=1, stdout="", stderr=stderr)

    result = probe_models.probe_one(TARGET, attempts=2, runner=run)
    assert result["status"] == "fail"
    assert result["attempts"] == 2
    assert result["error"] == stderr
    assert len(calls) == 2


def test_probe_one_permanent_signal_is_not_retried() -> None:
    calls: list[list[str]] = []
    result = probe_models.probe_one(
        TARGET, runner=_runner(failing={TARGET}, calls=calls)
    )
    assert result["status"] == "fail"
    assert result["attempts"] == 1
    assert result["error"] == "Model is unavailable"
    assert len(calls) == 1


def test_probe_one_timeout_then_ok_retries() -> None:
    calls: list[list[str]] = []

    def run(cmd, **kwargs):
        calls.append(list(cmd))
        if len(calls) == 1:
            raise subprocess.TimeoutExpired(cmd, 90)
        return SimpleNamespace(returncode=0, stdout="OK\n", stderr="")

    result = probe_models.probe_one(TARGET, timeout=90, runner=run)
    assert result["status"] == "ok"
    assert result["attempts"] == 2


def test_probe_one_timeout_twice_fails_after_two_attempts() -> None:
    def run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, 90)

    result = probe_models.probe_one(TARGET, timeout=90, attempts=2, runner=run)
    assert result["status"] == "fail"
    assert result["attempts"] == 2
    assert "timeout after 90s" in result["error"]


# ---------------------------------------------------------------------------
# 2. --refresh: report shape, exit-code contract, no-CLI behaviour
# ---------------------------------------------------------------------------

def test_refresh_writes_the_documented_report_shape(tmp_path: Path) -> None:
    exit_code, report_path = _refresh(tmp_path, _runner())
    assert exit_code == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert set(report) == {
        "schema_version",
        "probed_at",
        "mode",
        "cli",
        "timeout_s",
        "config_path",
        "config_sha256",
        "results",
        "xai_results",
    }
    assert report["schema_version"] == probe_models.SCHEMA_VERSION
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", report["probed_at"])
    assert report["config_sha256"] == probe_models.config_sha256(
        tmp_path / "opencode.json"
    )
    # collect_models sorts: deep-research < mimo-v2.5.
    assert [r["model"] for r in report["results"]] == [SECOND, TARGET]
    assert [r["model"] for r in report["xai_results"]] == [XAI]
    assert set(report["results"][0]) == {
        "model",
        "role",
        "status",
        "attempts",
        "latency_s",
        "error",
    }


def test_refresh_exits_zero_when_a_model_fails(tmp_path: Path) -> None:
    """The report is data; only --gate grades it (AC-1)."""
    exit_code, report_path = _refresh(tmp_path, _runner(failing={TARGET}))
    assert exit_code == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    target = next(r for r in report["results"] if r["model"] == TARGET)
    assert target["status"] == "fail"


def test_refresh_without_cli_exits_two_and_writes_no_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(probe_models.shutil, "which", lambda _cli: None)
    exit_code, report_path = _refresh(tmp_path, _runner())
    assert exit_code == 2
    assert not report_path.exists()


def test_config_hash_is_indentation_and_key_order_insensitive(tmp_path: Path) -> None:
    first = _write_config(tmp_path, indent=2)
    reordered = {
        "agents": {
            "grok": {"model": "xai/grok-4.7"},
            "research": {"model": "opencode-go/deep-research"},
            "orchestrator": {"model": "opencode-go/mimo-v2.5"},
        },
        "default_agent": "orchestrator",
    }
    second = tmp_path / "reindented.json"
    second.write_text(json.dumps(reordered, indent=8), encoding="utf-8")
    assert probe_models.config_sha256(first) == probe_models.config_sha256(second)


def test_config_hash_changes_when_a_model_is_remapped(tmp_path: Path) -> None:
    first = _write_config(tmp_path)
    remapped = json.loads(json.dumps(CONFIG))
    remapped["agents"]["orchestrator"]["model"] = "opencode-go/glm-5.2"
    second = tmp_path / "remapped.json"
    second.write_text(json.dumps(remapped), encoding="utf-8")
    assert probe_models.config_sha256(first) != probe_models.config_sha256(second)


def test_collect_models_groups_by_provider_and_dedupes(tmp_path: Path) -> None:
    config = {
        "agents": {
            "a": {"model": "opencode-go/mimo-v2.5"},
            "b": {"model": "opencode-go/mimo-v2.5"},
            "c": {"model": "xai/grok-4.7"},
            "d": {"model": "no-slash"},
        }
    }
    path = tmp_path / "opencode.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    assert probe_models.collect_models(path) == {
        "opencode-go": ["opencode-go/mimo-v2.5"],
        "xai": ["xai/grok-4.7"],
    }


def test_max_runtime_exhaustion_marks_the_remainder_skipped() -> None:
    def boom(cmd, **kwargs):  # pragma: no cover - must never be called
        raise AssertionError("runner called past the runtime budget")

    result = probe_models._probe_model(
        TARGET,
        "target",
        cli="opencode",
        timeout=1,
        attempts=1,
        runner=boom,
        deadline=time.monotonic() - 1,
    )
    assert result["status"] == "skipped"
    assert result["attempts"] == 0


# ---------------------------------------------------------------------------
# 3. --gate: green path, hard rules, warn-only rules, exit codes
# ---------------------------------------------------------------------------

def test_gate_is_green_with_every_target_ok(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    config_path = _write_config(tmp_path)
    assert _gate(tmp_path, config_path, report=_report(config_path)) == 0
    assert "gate green" in capsys.readouterr().out


def test_gate_red_on_failed_target_and_names_it(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    config_path = _write_config(tmp_path)
    report = _report(
        config_path, results=_entries(config_path, statuses={TARGET: "fail"})
    )
    assert _gate(tmp_path, config_path, report=report) == 1
    assert TARGET in capsys.readouterr().err


@pytest.mark.parametrize("status", ["skipped", "missing"])
def test_gate_red_when_a_target_is_not_ok(
    tmp_path: Path, status: str, capsys: pytest.CaptureFixture
) -> None:
    config_path = _write_config(tmp_path)
    if status == "missing":
        results = [e for e in _entries(config_path) if e["model"] != TARGET]
    else:
        results = _entries(config_path, statuses={TARGET: "skipped"})
    report = _report(config_path, results=results)
    assert _gate(tmp_path, config_path, report=report) == 1
    assert TARGET in capsys.readouterr().err


def test_gate_red_when_an_xai_target_fails_or_is_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    config_path = _write_config(tmp_path)
    failed = _report(
        config_path, xai_results=_xai_entries(config_path, statuses={XAI: "fail"})
    )
    assert _gate(tmp_path, config_path, report=failed) == 1
    assert XAI in capsys.readouterr().err

    missing = _report(config_path, xai_results=[])
    assert _gate(tmp_path, config_path, report=missing) == 1
    assert XAI in capsys.readouterr().err


def test_gate_red_when_the_report_has_no_xai_results_section(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    config_path = _write_config(tmp_path)
    report = _report(config_path)
    report.pop("xai_results")
    assert _gate(tmp_path, config_path, report=report) == 1
    assert "no xai_results section" in capsys.readouterr().err


def test_gate_missing_report_is_red_with_the_bootstrap_hint(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    config_path = _write_config(tmp_path)
    assert _gate(tmp_path, config_path, report=None) == 1
    err = capsys.readouterr().err
    assert "report missing" in err
    assert "--refresh --gate" in err


def test_gate_stale_report_is_red_unless_age_rule_disabled(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    config_path = _write_config(tmp_path)
    report = _report(config_path, probed_at=_stamp(days=-8))
    assert _gate(tmp_path, config_path, report=report) == 1
    assert "stale" in capsys.readouterr().err
    assert _gate(tmp_path, config_path, report=report, max_age_days=0) == 0


def test_gate_red_when_the_config_changed_since_the_probe(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    config_path = _write_config(tmp_path)
    report = _report(config_path, config_sha="0" * 64)
    assert _gate(tmp_path, config_path, report=report) == 1
    assert "config changed since last probe" in capsys.readouterr().err


def test_max_runtime_budget_lands_in_the_report_as_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """The budget must reach the written report, not just ``_probe_model``."""
    clock = [0.0]
    monkeypatch.setattr(probe_models.time, "monotonic", lambda: clock[0])

    def slow(cmd, **kwargs):
        clock[0] += 100.0  # burn more than the whole budget on the first model
        return SimpleNamespace(returncode=0, stdout="OK\n", stderr="")

    config_path = _write_config(tmp_path)
    report_path = tmp_path / "model-probe-report.json"
    argv = [
        "--refresh",
        "--gate",
        "--max-runtime-s",
        "5",
        "--max-workers",
        "1",
        "--config",
        str(config_path),
        "--report",
        str(report_path),
    ]
    exit_code = probe_models.main(argv, runner=slow)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    by_model = {r["model"]: r for r in report["results"]}
    assert by_model[SECOND]["status"] == "ok"
    assert by_model[TARGET]["status"] == "skipped"
    assert by_model[TARGET]["attempts"] == 0
    # A skipped target is a hard offence: the refresh+gate goes red.
    assert exit_code == 1
    assert "skipped" in capsys.readouterr().err


def test_gate_red_on_malformed_report(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    config_path = _write_config(tmp_path)
    assert _gate(tmp_path, config_path, report="{not json") == 1
    assert "report unreadable" in capsys.readouterr().err


def test_gate_red_on_schema_version_mismatch(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    config_path = _write_config(tmp_path)
    report = _report(
        config_path, schema_version=probe_models.SCHEMA_VERSION + 1
    )
    assert _gate(tmp_path, config_path, report=report) == 1
    assert "schema_version" in capsys.readouterr().err


def test_gate_red_when_a_target_has_duplicate_non_ok_results(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    config_path = _write_config(tmp_path)
    results = [
        _entry(TARGET, "target", "fail", error="timeout after 90s"),
        _entry(TARGET, "target", "fail", error="Model is unavailable"),
        _entry(SECOND, "target", "ok"),
    ]
    assert _gate(tmp_path, config_path, report=_report(config_path, results=results)) == 1
    err = capsys.readouterr().err
    assert "need exactly one ok" in err
    assert TARGET in err


def test_gate_red_on_future_probed_at(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    config_path = _write_config(tmp_path)
    report = _report(config_path, probed_at=_stamp(hours=2))
    assert _gate(tmp_path, config_path, report=report) == 1
    assert "future" in capsys.readouterr().err


def test_gate_exits_two_without_a_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    config_path = _write_config(tmp_path)
    monkeypatch.setattr(probe_models.shutil, "which", lambda _cli: None)
    assert _gate(tmp_path, config_path, report=_report(config_path)) == 2
    assert "CLI not on PATH" in capsys.readouterr().err


def test_gate_config_refs_outside_the_paid_set_warn_only(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    config = {
        "agents": {
            "research": {"model": "opencode/flint-40b-free"},
            "paid": {"model": "opencode-go/glm-5.2"},
        }
    }
    config_path = _write_config(tmp_path, config)
    report = _report(config_path, xai_results=[])
    assert _gate(tmp_path, config_path, report=report) == 0
    err = capsys.readouterr().err
    assert "opencode/flint-40b-free" in err
    assert "opencode-go/glm-5.2" not in err


# ---------------------------------------------------------------------------
# 4. --refresh --gate end-to-end
# ---------------------------------------------------------------------------

def test_refresh_then_gate_fails_closed_on_a_dead_target(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    report_path = tmp_path / "model-probe-report.json"
    exit_code = probe_models.main(
        [
            "--refresh",
            "--gate",
            "--config",
            str(config_path),
            "--report",
            str(report_path),
        ],
        runner=_runner(failing={TARGET}),
    )
    assert exit_code == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    target = next(r for r in report["results"] if r["model"] == TARGET)
    assert target["status"] == "fail"


# ---------------------------------------------------------------------------
# 4b. MDU-40 fix-cycle regression pins
# ---------------------------------------------------------------------------

def test_main_rejects_the_retired_map_argument(capsys: pytest.CaptureFixture) -> None:
    """The zen map is retired: --map is an unknown argument and exits 2."""
    with pytest.raises(SystemExit) as exc:
        probe_models.main(["--map", "x", "--refresh"])
    assert exc.value.code == 2
    assert "--map" in capsys.readouterr().err


def test_include_xai_is_an_accepted_no_op(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """--include-xai survives for older callers, but xai is always probed."""
    config_path = _write_config(tmp_path)
    report_path = tmp_path / "model-probe-report.json"
    report_path.write_text(json.dumps(_report(config_path)), encoding="utf-8")
    exit_code = probe_models.main(
        [
            "--gate",
            "--include-xai",
            "--config",
            str(config_path),
            "--report",
            str(report_path),
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "gate green" in captured.out
    assert "--include-xai" not in captured.err


def test_xai_seeding_populates_results_and_is_graded(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """A config with an xai/* row refreshes xai_results and the gate grades it."""
    config_path = _write_config(tmp_path)
    report_path = tmp_path / "model-probe-report.json"
    exit_code = probe_models.main(
        [
            "--refresh",
            "--gate",
            "--config",
            str(config_path),
            "--report",
            str(report_path),
        ],
        runner=_runner(failing={XAI}),
    )
    assert exit_code == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert [entry["model"] for entry in report["xai_results"]] == [XAI]
    assert report["xai_results"][0]["role"] == "xai"
    assert report["xai_results"][0]["status"] == "fail"
    assert XAI in capsys.readouterr().err


# ---------------------------------------------------------------------------
# 5. wiring + docs
# ---------------------------------------------------------------------------

def test_overlay_deploy_orders_probe_then_grok_xai_gate_before_any_copy() -> None:
    deploy = OVERLAY / "scripts" / "deploy.sh"
    if not deploy.is_file():
        pytest.skip("overlay checkout not present (base-only CI)")
    text = deploy.read_text(encoding="utf-8")
    assert "probe_models.py" in text
    assert "--gate" in text
    assert "--skip-probe" in text
    assert "config/model-probe-report.json" in text
    # Hard gate, escaping only through --skip-probe; dry runs warn.
    assert "refusing to install" in text
    assert "dry run continues" in text
    assert "run_probe_gate\n  run_grok_xai_gate\n  deploy_opencode_json" in text


def test_base_deploy_gate_is_advisory() -> None:
    text = (REPO / "scripts" / "deploy.sh").read_text(encoding="utf-8")
    assert "probe_models.py" in text
    assert "--gate" in text
    assert "advisory" in text
    assert "probe_gate_advisory\n  deploy_opencode_json" in text
    assert "refusing to install" not in text


def test_model_registry_doc_documents_probe_and_paid_config() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "## Live model-health probe (MDU-38)" in text
    for needle in (
        "--refresh",
        "--gate",
        "--max-age-days",
        "--skip-probe",
        "config/model-probe-report.json",
        "config_sha256",
        "build/opencode.json",
    ):
        assert needle in text, needle
    # Every shipped model is named, because every one is a hard target.
    config = json.loads((REPO / "opencode.json").read_text(encoding="utf-8"))
    for definition in config["agents"].values():
        assert definition["model"] in text, definition["model"]
    # The Zen map is retired; no stale map reference survives.
    assert "zen-model-map.json" not in text


def test_readme_mentions_the_probe_gate() -> None:
    text = " ".join(README.read_text(encoding="utf-8").split())
    assert "probe_models.py" in text
    assert "--skip-probe" in text
    assert "local-only and never" in text
    assert "runs in CI" in text


def test_ci_has_no_live_probe_invocation() -> None:
    lines = [
        line
        for line in CI.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    ]
    assert not any("probe_models" in line for line in lines)
