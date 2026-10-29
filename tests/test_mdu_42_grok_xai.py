#!/usr/bin/env python3
"""MDU-42 tests: grok-named agents must run on xAI account models.

Covers the validator clause in both variants (go and zen), the
``--grok-xai-check`` CLI, probe ``--include-xai`` (inference stubbed through
the injected ``runner`` — no subprocesses, no network), and the deploy
wiring asserted by reading the shell scripts — the same convention as
``test_mdu_33`` / ``test_mdu_38``.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import model_registry
import probe_models
import validate

REPO = Path(__file__).resolve().parent.parent
DEPLOY = REPO / "scripts" / "deploy.sh"
XAI_MODEL = "xai/grok-4.7"
FREE_MODEL = "opencode/big-pickle"


# ---------------------------------------------------------------------------
# validator clause (D2) — both variants
# ---------------------------------------------------------------------------

def _agent(model: str, *, description: str = "test agent", **extra) -> dict:
    definition = {
        "mode": "subagent",
        "description": description,
        "model": model,
        "system": "You are a test agent.",
    }
    definition.update(extra)
    return definition


def _permissions() -> list[dict]:
    return [
        {"action": "external_directory", "resource": "/tmp/**", "effect": "allow"},
        {"action": "external_directory", "resource": "/proc/**", "effect": "allow"},
    ]


def _build(tmp_path: Path, agents: dict) -> Path:
    """A build dir whose opencode.json / opencode.zen.json carry ``agents``."""
    prompts = tmp_path / "build" / "prompts"
    prompts.mkdir(parents=True)
    (tmp_path / "build" / "grok" / "agents").mkdir(parents=True)
    (tmp_path / "build" / "claude" / "agents").mkdir(parents=True)
    (prompts / "plain.md").write_text("hello\n", encoding="utf-8")
    config = {"agents": agents, "permissions": _permissions()}
    (tmp_path / "build" / "opencode.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )
    (tmp_path / "build" / "opencode.zen.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )
    return tmp_path / "build"


@pytest.mark.parametrize(
    "model,violates",
    [
        (FREE_MODEL, True),
        ("opencode-go/glm-5.2", True),
        (XAI_MODEL, False),
    ],
)
def test_grok_named_must_be_xai_go_variant(tmp_path: Path, model: str, violates: bool) -> None:
    build = _build(tmp_path, {"grok-plan": _agent(model)})
    errors = validate.validate_opencode(build)
    if violates:
        assert any(
            "grok-named agent 'grok-plan'" in err
            and f"'{model}'" in err
            and "does not start with 'xai/'" in err
            for err in errors
        ), errors
    else:
        assert not any("grok-named" in err for err in errors), errors


@pytest.mark.parametrize(
    "model,violates",
    [
        (FREE_MODEL, True),
        (XAI_MODEL, False),
    ],
)
def test_grok_named_must_be_xai_zen_variant(tmp_path: Path, model: str, violates: bool) -> None:
    """MDU-42: the clause also runs under --variant zen (xai kept by design)."""
    build = _build(tmp_path, {"grokestrator": _agent(model)})
    errors = validate.validate_zen(build)
    if violates:
        assert any(
            "opencode.zen.json grok-named agent 'grokestrator'" in err
            and f"'{model}'" in err
            for err in errors
        ), errors
    else:
        # The xai pass-through must not be tripped by the free-allowlist check.
        assert not any("grok-named" in err for err in errors), errors


def test_grok_named_missing_model_is_a_violation(tmp_path: Path) -> None:
    build = _build(tmp_path, {"grok-qa": {"mode": "subagent", "description": "x"}})
    errors = validate.validate_opencode(build)
    assert any(
        "grok-named agent 'grok-qa' has no model field" in err for err in errors
    ), errors


def test_grok_named_bare_xai_prefix_is_a_violation(tmp_path: Path) -> None:
    """'xai/' (empty provider suffix) is not a usable xai/* model (2026-10 review)."""
    build = _build(tmp_path, {"grok-qa": _agent("xai/")})
    errors = validate.validate_opencode(build)
    assert any(
        "grok-named agent 'grok-qa'" in err and "empty xai/ provider suffix" in err
        for err in errors
    ), errors
    # The grok-xai-check CLI (deploy gate primitive) rejects it too.
    cfg = tmp_path / "opencode.json"
    cfg.write_text(json.dumps({"agents": {"grok-qa": _agent("xai/")}}), encoding="utf-8")
    assert model_registry.main(["--grok-xai-check", str(cfg)]) == 1


def test_non_grok_agents_are_not_subject(tmp_path: Path) -> None:
    build = _build(tmp_path, {"orchestrator": _agent(FREE_MODEL)})
    errors = validate.validate_opencode(build)
    assert not any("grok-named" in err for err in errors), errors


def test_grok_name_prefix_is_respected(tmp_path: Path) -> None:
    build = _build(tmp_path, {"grok-plan": _agent(XAI_MODEL)})
    assert validate.validate_opencode(build) == [] or not any(
        "grok-named" in err for err in validate.validate_opencode(build)
    )


def test_validate_variant_zen_flags_grok_downgrade_end_to_end(tmp_path: Path) -> None:
    """The check is wired into validate.main via validate_zen (zen mode)."""
    build = _build(tmp_path, {"grok-plan": _agent(FREE_MODEL)})
    rc = validate.main(["--variant", "zen", str(build)])
    assert rc == 1


# ---------------------------------------------------------------------------
# --grok-xai-check CLI (deploy gate primitive)
# ---------------------------------------------------------------------------

def test_grok_xai_check_cli(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    cfg = tmp_path / "opencode.json"
    cfg.write_text(
        json.dumps(
            {"agents": {"grok-plan": _agent(FREE_MODEL), "just-code": _agent(FREE_MODEL)}}
        ),
        encoding="utf-8",
    )
    rc = model_registry.main(["--grok-xai-check", str(cfg)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "grok-named agent 'grok-plan'" in out
    assert "just-code" not in out

    cfg.write_text(
        json.dumps({"agents": {"grok-plan": _agent(XAI_MODEL)}}), encoding="utf-8"
    )
    rc = model_registry.main(["--grok-xai-check", str(cfg)])
    assert rc == 0
    assert "holds" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# probe --include-xai (D4) — stubbed inference
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _opencode_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe_models.shutil, "which", lambda _cli: "/usr/bin/opencode")
    monkeypatch.setattr(probe_models, "RETRY_SLEEP_S", 0.0)


MAP = {
    "version": 1,
    "models": {"opencode-go/deepseek-v4.1-flash": FREE_MODEL},
    "overrides": {},
    "alternates": [],
}

XAI_CONFIG = {
    "agents": {
        "grok-plan": _agent(XAI_MODEL),
        "just-code": _agent(FREE_MODEL),
    }
}


def _write_map(tmp_path: Path) -> Path:
    path = tmp_path / "zen-model-map.json"
    path.write_text(json.dumps(MAP, indent=2), encoding="utf-8")
    return path


def _write_config(tmp_path: Path, config: dict | None = None) -> Path:
    path = tmp_path / "opencode.json"
    path.write_text(json.dumps(config or XAI_CONFIG), encoding="utf-8")
    return path


def _runner(*, failing: set[str] | None = None, calls=None):
    failing = failing or set()

    def run(cmd, **kwargs):
        model = cmd[3]
        if calls is not None:
            calls.append(list(cmd))
        if model in failing:
            return SimpleNamespace(returncode=1, stdout="", stderr="model not found")
        return SimpleNamespace(returncode=0, stdout="OK\n", stderr="")

    return run


def _stamp_now() -> str:
    import datetime as dt

    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_collect_xai_models_only_grok_named_xai(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    assert probe_models.collect_xai_models(config_path) == [XAI_MODEL]
    assert probe_models.collect_xai_models(_write_config(tmp_path, {"agents": {}})) == []
    assert probe_models.collect_xai_models(None) == []


def test_refresh_writes_xai_section(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    rc = probe_models.refresh_report(
        MAP,
        _write_map(tmp_path),
        report_path,
        cli="opencode",
        timeout=90,
        attempts=1,
        max_workers=1,
        max_runtime_s=0,
        runner=_runner(),
        xai_models=[XAI_MODEL],
        include_xai=True,
    )
    assert rc == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["xai_enabled"] is True
    assert [entry["model"] for entry in report["xai_results"]] == [XAI_MODEL]
    assert report["xai_results"][0]["role"] == "xai"
    assert report["xai_results"][0]["status"] == "ok"
    # The zen results section and hash contract are untouched.
    assert report["map_sha256"] == probe_models.canonical_map_sha256(MAP)
    assert {e["model"] for e in report["results"]} == {FREE_MODEL}


def test_refresh_skips_xai_section_when_disabled(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    probe_models.refresh_report(
        MAP,
        _write_map(tmp_path),
        report_path,
        cli="opencode",
        timeout=90,
        attempts=1,
        max_workers=1,
        max_runtime_s=0,
        runner=_runner(),
        xai_models=[],
        include_xai=False,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert "xai_results" not in report and "xai_enabled" not in report


def test_refresh_probes_xai_with_same_match_rule(tmp_path: Path) -> None:
    """xai probing uses the strict exact-match OK gate (probe_one)."""
    calls: list[list[str]] = []
    rc = probe_models.refresh_report(
        MAP,
        _write_map(tmp_path),
        tmp_path / "report.json",
        cli="opencode",
        timeout=90,
        attempts=1,
        max_workers=1,
        max_runtime_s=0,
        runner=_runner(failing={XAI_MODEL}, calls=calls),
        xai_models=[XAI_MODEL],
        include_xai=True,
    )
    assert rc == 0
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    entry = report["xai_results"][0]
    assert entry["status"] == "fail"
    assert "model not found" in entry["error"]
    assert calls == [
        ["opencode", "run", "-m", FREE_MODEL, probe_models.PROMPT],
        ["opencode", "run", "-m", XAI_MODEL, probe_models.PROMPT],
    ]


def test_gate_green_green_xai(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    probe_models.refresh_report(
        MAP,
        _write_map(tmp_path),
        report_path,
        cli="opencode",
        timeout=90,
        attempts=1,
        max_workers=1,
        max_runtime_s=0,
        runner=_runner(),
        xai_models=[XAI_MODEL],
        include_xai=True,
    )
    offences, _warnings = probe_models.gate_offences(
        report_path, MAP, max_age_days=7, config_path=_write_config(tmp_path)
    )
    assert not any("xai" in o for o in offences), offences


def test_gate_red_when_xai_probe_fails(tmp_path: Path, now=None) -> None:
    import datetime as dt

    now = dt.datetime.now(dt.timezone.utc)
    mapping_hash = probe_models.canonical_map_sha256(MAP)
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "schema_version": probe_models.SCHEMA_VERSION,
                "probed_at": _stamp_now(),
                "mode": "refresh",
                "cli": "opencode",
                "timeout_s": 90,
                "map_path": "config/zen-model-map.json",
                "map_sha256": mapping_hash,
                "results": [
                    {"model": FREE_MODEL, "role": "target", "status": "ok",
                     "attempts": 1, "latency_s": 0.1, "error": None}
                ],
                "xai_enabled": True,
                "xai_results": [
                    {"model": XAI_MODEL, "role": "xai", "status": "fail",
                     "attempts": 1, "latency_s": 0.1, "error": "model not found"}
                ],
            }
        ),
        encoding="utf-8",
    )
    offences, _warnings = probe_models.gate_offences(
        report_path, MAP, max_age_days=7, config_path=_write_config(tmp_path), now=now
    )
    assert any(
        f"xai target '{XAI_MODEL}' is fail" in o and "model not found" in o
        for o in offences
    ), offences


def test_gate_red_when_xai_entry_missing_from_report(tmp_path: Path) -> None:
    import datetime as dt

    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "schema_version": probe_models.SCHEMA_VERSION,
                "probed_at": _stamp_now(),
                "mode": "refresh",
                "cli": "opencode",
                "timeout_s": 90,
                "map_path": "config/zen-model-map.json",
                "map_sha256": probe_models.canonical_map_sha256(MAP),
                "results": [
                    {"model": FREE_MODEL, "role": "target", "status": "ok",
                     "attempts": 1, "latency_s": 0.1, "error": None}
                ],
            }
        ),
        encoding="utf-8",
    )
    offences, _warnings = probe_models.gate_offences(
        report_path, MAP, max_age_days=7, config_path=_write_config(tmp_path)
    )
    assert any(
        f"xai target '{XAI_MODEL}' missing from the xai_results" in o for o in offences
    ), offences


def test_gate_include_xai_requires_report_section(tmp_path: Path) -> None:
    import datetime as dt

    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "schema_version": probe_models.SCHEMA_VERSION,
                "probed_at": _stamp_now(),
                "mode": "refresh",
                "cli": "opencode",
                "timeout_s": 90,
                "map_path": "config/zen-model-map.json",
                "map_sha256": probe_models.canonical_map_sha256(MAP),
                "results": [],
            }
        ),
        encoding="utf-8",
    )
    config_path = _write_config(tmp_path, {"agents": {}})
    offences, _warnings = probe_models.gate_offences(
        report_path, MAP, max_age_days=7, config_path=config_path, include_xai=True
    )
    assert any("report has no xai_results section" in o for o in offences), offences
    offences, _warnings = probe_models.gate_offences(
        report_path, MAP, max_age_days=7, config_path=config_path
    )
    assert not any("xai" in o for o in offences), offences


def _raw_report(
    tmp_path: Path,
    target_status: str = "ok",
    xai_results: list[dict] | None = None,
) -> Path:
    """A minimal schema-valid report for gate_offences unit checks."""
    report_path = tmp_path / "report.json"
    body: dict = {
        "schema_version": probe_models.SCHEMA_VERSION,
        "probed_at": _stamp_now(),
        "mode": "refresh",
        "cli": "opencode",
        "timeout_s": 90,
        "map_path": "config/zen-model-map.json",
        "map_sha256": probe_models.canonical_map_sha256(MAP),
        "results": [
            {"model": FREE_MODEL, "role": "target", "status": target_status,
             "attempts": 1, "latency_s": 0.1, "error": None}
        ],
    }
    if xai_results is not None:
        body["xai_enabled"] = True
        body["xai_results"] = xai_results
    report_path.write_text(json.dumps(body), encoding="utf-8")
    return report_path


def test_gate_tolerates_duplicate_xai_entries_with_one_ok(tmp_path: Path) -> None:
    """ok==1 among duplicate xai entries is green — mirrors the target rule.

    The earlier fall-through reported entries[0]'s own status here, which
    could produce the nonsense offence "xai target '…' is ok".
    """
    report_path = _raw_report(
        tmp_path,
        xai_results=[
            {"model": XAI_MODEL, "role": "xai", "status": "fail",
             "attempts": 1, "latency_s": 0.1, "error": "transient"},
            {"model": XAI_MODEL, "role": "xai", "status": "ok",
             "attempts": 1, "latency_s": 0.1, "error": None},
        ],
    )
    offences, _warnings = probe_models.gate_offences(
        report_path, MAP, max_age_days=7, config_path=_write_config(tmp_path)
    )
    assert not any("xai" in o for o in offences), offences


def test_gate_duplicate_xai_entries_zero_ok_names_duplicates(tmp_path: Path) -> None:
    report_path = _raw_report(
        tmp_path,
        xai_results=[
            {"model": XAI_MODEL, "role": "xai", "status": "fail",
             "attempts": 1, "latency_s": 0.1, "error": "model not found"},
            {"model": XAI_MODEL, "role": "xai", "status": "fail",
             "attempts": 1, "latency_s": 0.1, "error": "model not found"},
        ],
    )
    offences, _warnings = probe_models.gate_offences(
        report_path, MAP, max_age_days=7, config_path=_write_config(tmp_path)
    )
    assert any(
        f"xai target '{XAI_MODEL}' has 2 results, need exactly one ok" in o
        for o in offences
    ), offences
    # No offence may quote an entry's own ok-looking status.
    assert not any("is ok" in o for o in offences), offences


def test_cli_include_xai_end_to_end(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    calls: list[list[str]] = []
    rc = probe_models.main(
        [
            "--refresh", "--gate",
            "--map", str(_write_map(tmp_path)),
            "--report", str(tmp_path / "report.json"),
            "--config", str(_write_config(tmp_path)),
            "--include-xai",
            "--timeout", "90", "--attempts", "1",
            "--max-workers", "1", "--max-runtime-s", "0",
        ],
        runner=_runner(failing={XAI_MODEL}, calls=calls),
    )
    assert rc == 1
    out = capsys.readouterr().err
    assert "xai target 'xai/grok-4.7' is fail" in out


def test_cli_gate_rule_3_exit_2_on_bad_args(tmp_path: Path) -> None:
    # Sanity: the main() contract still distinguishes usage errors from red.
    rc = probe_models.main([], runner=_runner())
    assert rc == 2


# ---------------------------------------------------------------------------
# deploy wiring (D3)
# ---------------------------------------------------------------------------

def test_deploy_gate_wiring() -> None:
    text = DEPLOY.read_text(encoding="utf-8")
    assert "--grok-xai-check" in text
    # The gate runs inside deploy_opencode_json, i.e. before any copy, and
    # both installed tier files are checked.
    assert "grok_xai_gate" in text
    assert text.index("grok_xai_gate") < text.index("deploy_opencode_json") or (
        "grok_xai_gate \"$parked\"" in text and "grok_xai_gate \"$active\"" in text
    )
    # MDU-42 review fix: the probe gate receives the active tier config too,
    # so the xai rule is evaluable (not blind to xai/* targets), and the
    # printed hints tell the user how to produce an xai_results section.
    assert '--include-xai --config "$active"' in text
    assert "--refresh --gate --include-xai" in text


def test_grok_xai_check_free_model_fails(tmp_path: Path, tmp_path_factory) -> None:
    """Exercise model_registry --grok-xai-check directly (the deploy gate primitive).

    Earlier known as ``test_deploy_gate_aborts_before_install``; that name
    overstated what the test does — it never runs deploy.sh, only the checker
    the deploy invokes.
    """
    repo = tmp_path_factory.mktemp("deploy") / "repo"
    import shutil

    shutil.copytree(REPO / "scripts", repo / "scripts")
    build = repo / "build"
    build.mkdir()
    config = {"agents": {"grok-plan": _agent(FREE_MODEL)}}
    (build / "opencode.json").write_text(json.dumps(config), encoding="utf-8")
    proc = probe_models.subprocess.run(
        [
            "python3", str(repo / "scripts" / "lib" / "model_registry.py"),
            "--grok-xai-check", str(build / "opencode.json"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "grok-named agent 'grok-plan'" in proc.stdout
