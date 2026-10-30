#!/usr/bin/env python3
"""MDU-40 tests: the paid-only default tier.

The Zen/free tier is retired. There is one canonical ``opencode.json``, every
agent model is paid (``opencode-go/*`` or ``xai/*``), and the probe gate grades
the config itself (no map, no alternates, no ``--variant``).
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

import probe_models
import validate

REPO = Path(__file__).resolve().parent.parent
OPENCODE_JSON = REPO / "opencode.json"
DEPLOY = REPO / "scripts" / "deploy.sh"
OVERLAY = REPO.parent / "opencode_agents"

PAID_PREFIXES = ("opencode-go/", "xai/")
CANONICAL_SENTENCE = (
    "All loop phases run on paid models; free-tier variants are retired (MDU-40)."
)
DELETED_AGENTS = {
    "just-code-free",
    "test-agent-free",
    "code-reviewer-free",
    "devops-free",
    "qa-free",
    "research",
    "deepseek-research",
    "nemotron-research",
}
#: Base prompt mirrors of the orchestrator loop (the overlay copy is the
#: overlay MDU's responsibility — see the MDU-40 handoff).
MIRRORS = (
    REPO / "prompts" / "orchestrator.md",
    REPO / "grok" / "agents" / "orchestrator.md",
)

#: The single sanctioned "free model" context: the MDU-41 ladder's *negative*
#: prohibition ("never substitute a free model — free variants no longer
#: exist"). Free-model *usage/assignment* wording stays forbidden; only this
#: explicit never-substitute guard may name one.
SANCTIONED_FREE_PREFIX = "never substitute a "


def _unsanctioned_free_model_spans(text: str) -> list[str]:
    """Return every "free model" occurrence not preceded by the guard phrase."""
    lowered = text.lower()
    spans = []
    index = lowered.find("free model")
    while index != -1:
        prefix = lowered[max(0, index - len(SANCTIONED_FREE_PREFIX)):index]
        if prefix != SANCTIONED_FREE_PREFIX:
            spans.append(lowered[max(0, index - 60):index + len("free model")])
        index = lowered.find("free model", index + 1)
    return spans


def _config() -> dict:
    return json.loads(OPENCODE_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1-3. canonical config census
# ---------------------------------------------------------------------------

def test_canonical_config_is_paid_only() -> None:
    config = _config()
    agents = config["agents"]
    assert len(agents) == 20
    for name, definition in agents.items():
        assert not name.endswith("-free"), name
        assert definition["model"].startswith(PAID_PREFIXES), (name, definition)
    text = OPENCODE_JSON.read_text(encoding="utf-8")
    assert "big-pickle" not in text
    assert re.search(r"\b[\w.]*-free\b", text) is None

    default_agent = config.get("default_agent")
    assert default_agent in agents
    assert agents[default_agent]["model"].startswith(PAID_PREFIXES)


#: Models that upstream killed or that the paid census retired; the canonical
#: config must never name them again (mimo-v2.5 was deprecated upstream and a
#: probe confirmed its death).
RETIRED_MODEL_IDS = ("opencode-go/mimo-v2.5",)


def test_canonical_config_has_no_retired_models() -> None:
    text = OPENCODE_JSON.read_text(encoding="utf-8")
    for needle in RETIRED_MODEL_IDS:
        assert needle not in text, needle


def test_removed_free_agents_are_absent() -> None:
    agents = _config()["agents"]
    assert DELETED_AGENTS.isdisjoint(agents), DELETED_AGENTS & set(agents)
    # deep-research survives and absorbed the research delegation.
    assert "deep-research" in agents


def test_research_permission_allows_are_repointed() -> None:
    text = OPENCODE_JSON.read_text(encoding="utf-8")
    assert '"resource": "research"' not in text
    assert text.count('"resource": "deep-research"') >= 14


# ---------------------------------------------------------------------------
# 4. mirror parity
# ---------------------------------------------------------------------------

def test_orchestrator_mirrors_carry_the_paid_sentence() -> None:
    for path in MIRRORS:
        text = path.read_text(encoding="utf-8")
        assert CANONICAL_SENTENCE in text, path
        assert "big-pickle" not in text, path
        assert re.search(r"\b[\w.]*-free\b", text) is None, path
        # Only the MDU-41 "never substitute a free model" guard may name one.
        assert not _unsanctioned_free_model_spans(text), (
            path,
            _unsanctioned_free_model_spans(text),
        )


# ---------------------------------------------------------------------------
# 5. validator census
# ---------------------------------------------------------------------------

def _write_config_build(tmp_path: Path, config: dict) -> Path:
    build = tmp_path / "build"
    build.mkdir()
    (build / "opencode.json").write_text(json.dumps(config), encoding="utf-8")
    return build


def test_validate_paid_census_rejects_a_free_agent(tmp_path: Path) -> None:
    build = _write_config_build(
        tmp_path,
        {
            "default_agent": "paid",
            "agents": {
                "paid": {"model": "opencode-go/glm-5.2"},
                "legacy": {"model": "opencode/big-pickle"},
            },
        },
    )
    errors = validate.validate_paid_census(build)
    assert any("'opencode/big-pickle'" in err for err in errors), errors
    assert any("big-pickle" in err for err in errors), errors


def test_validate_paid_census_accepts_the_shipped_config(tmp_path: Path) -> None:
    build = tmp_path / "build"
    build.mkdir()
    (build / "opencode.json").write_text(
        OPENCODE_JSON.read_text(encoding="utf-8"), encoding="utf-8"
    )
    assert validate.validate_paid_census(build) == []


# ---------------------------------------------------------------------------
# 6. probe gates the config itself
# ---------------------------------------------------------------------------

def _write_probe_config(tmp_path: Path, models: dict[str, str]) -> Path:
    path = tmp_path / "opencode.json"
    path.write_text(
        json.dumps({"agents": {name: {"model": m} for name, m in models.items()}}),
        encoding="utf-8",
    )
    return path


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_collect_models_and_hash_track_the_config(tmp_path: Path) -> None:
    config = _write_probe_config(
        tmp_path,
        {
            "a": "opencode-go/glm-5.2",
            "b": "opencode-go/glm-5.2",
            "c": "xai/grok-4.7",
        },
    )
    assert probe_models.collect_models(config) == {
        "opencode-go": ["opencode-go/glm-5.2"],
        "xai": ["xai/grok-4.7"],
    }
    before = probe_models.config_sha256(config)
    config.write_text(
        json.dumps(
            {"agents": {"a": {"model": "opencode-go/mimo-v2.5"}}}
        ),
        encoding="utf-8",
    )
    assert probe_models.config_sha256(config) != before


def test_gate_reds_on_missing_target_and_stale_hash(tmp_path: Path) -> None:
    config = _write_probe_config(tmp_path, {"a": "opencode-go/glm-5.2"})
    report_path = tmp_path / "report.json"
    report = {
        "schema_version": probe_models.SCHEMA_VERSION,
        "probed_at": _stamp(),
        "mode": "refresh",
        "cli": "opencode",
        "timeout_s": 90,
        "config_path": str(config),
        "config_sha256": probe_models.config_sha256(config),
        "results": [],
        "xai_results": [],
    }
    report_path.write_text(json.dumps(report), encoding="utf-8")
    offences, _warnings = probe_models.gate_offences(
        report_path, config, max_age_days=7
    )
    assert any(
        "target 'opencode-go/glm-5.2' missing from the report" in o
        for o in offences
    ), offences

    report["config_sha256"] = "0" * 64
    report_path.write_text(json.dumps(report), encoding="utf-8")
    offences, _warnings = probe_models.gate_offences(
        report_path, config, max_age_days=7
    )
    assert any("config changed since last probe" in o for o in offences), offences


# ---------------------------------------------------------------------------
# 7. deploy tier semantics
# ---------------------------------------------------------------------------

def _deploy(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(DEPLOY), *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def test_deploy_tier_is_paid() -> None:
    text = DEPLOY.read_text(encoding="utf-8")
    assert 'TIER="paid"' in text
    assert "opencode.zen.json" not in text
    assert "zen-model-map.json" not in text
    assert "TWO_TIER" not in text
    # build.sh retires the stale generated artifact instead of producing it.
    build_text = (REPO / "scripts" / "build.sh").read_text(encoding="utf-8")
    assert 'rm -f "${BUILD_DIR}/opencode.zen.json"' in build_text


def test_deploy_rejects_the_retired_zen_tier() -> None:
    proc = _deploy("--tier=zen")
    assert proc.returncode == 2
    assert "zen tier retired in MDU-40" in proc.stderr + proc.stdout


@pytest.mark.parametrize("flag", ["--tier=paid", "--tier=go", ""])
def test_deploy_paid_dry_run_has_one_target(flag: str) -> None:
    proc = _deploy(flag) if flag else _deploy()
    output = proc.stdout + proc.stderr
    assert proc.returncode == 0, output
    assert "Tier: paid" in output
    assert "single config: opencode.json" in output
    assert "opencode.zen.json" not in output
    assert "parked" not in output.lower()
