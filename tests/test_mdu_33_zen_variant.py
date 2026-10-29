#!/usr/bin/env python3
"""MDU-33 tests: Zen-tier config variant generation and validation.

Covers the design's test-plan sketch: generator determinism, fail-closed
behaviour, free Zen allowlist derivation, agent parity, ``validate_zen`` and
the ``--variant`` flag, description substitutions, plus the README/docs
acceptance-criteria strings.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import gen_zen_config
import model_registry
import validate
from model_registry import free_zen_models, load_registry

REPO = Path(__file__).resolve().parent.parent
OPENCODE = REPO / "opencode.json"
ZEN_MAP = REPO / "config" / "zen-model-map.json"
SNAPSHOT = REPO / "config" / "model-registry.txt"
README = REPO / "README.md"
MODEL_DOC = REPO / "docs" / "model-registry.md"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _free_models() -> set[str]:
    return free_zen_models(load_registry(SNAPSHOT))


def _mapping() -> dict:
    return json.loads(ZEN_MAP.read_text(encoding="utf-8"))


def _real_transform() -> tuple[dict, dict, list[str], list[str]]:
    config = json.loads(OPENCODE.read_text(encoding="utf-8"))
    zen, errors, warnings = gen_zen_config.transform(config, _mapping(), _free_models())
    return config, zen, errors, warnings


def _agent(model: str, *, description: str = "test agent", **extra) -> dict:
    definition = {
        "mode": "subagent",
        "description": description,
        "model": model,
        "system": "You are a test agent.",
    }
    definition.update(extra)
    return definition


def _write_map(tmp_path: Path, mapping: dict) -> Path:
    path = tmp_path / "zen-map.json"
    path.write_text(json.dumps(mapping), encoding="utf-8")
    return path


def _minimal_build(tmp_path: Path, *, model: str = "opencode/big-pickle") -> Path:
    """A build dir that passes every validate.py check."""
    build = tmp_path / "build"
    (build / "grok" / "agents").mkdir(parents=True)
    (build / "claude" / "agents").mkdir(parents=True)
    (build / "prompts").mkdir(parents=True)

    config = {
        "agents": {"test-agent": _agent(model)},
        "permissions": [
            {"action": "external_directory", "resource": "/tmp/**", "effect": "allow"},
            {"action": "external_directory", "resource": "/proc/**", "effect": "allow"},
        ],
    }
    (build / "opencode.json").write_text(json.dumps(config), encoding="utf-8")
    (build / "opencode.zen.json").write_text(json.dumps(config), encoding="utf-8")
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
# 1. transform on the real config
# ---------------------------------------------------------------------------

def test_real_transform_keeps_every_agent_name() -> None:
    config, zen, errors, _ = _real_transform()
    assert errors == []
    assert set(zen["agents"]) == set(config["agents"])
    assert len(zen["agents"]) == 28


def test_real_transform_uses_only_free_models() -> None:
    _, zen, errors, _ = _real_transform()
    assert errors == []
    free = _free_models()
    for name, definition in zen["agents"].items():
        assert definition["model"] in free, name


def test_real_transform_has_no_go_references_anywhere() -> None:
    _, zen, _, _ = _real_transform()
    assert "opencode-go/" not in gen_zen_config.render(zen)


def test_real_transform_expected_targets() -> None:
    _, zen, _, _ = _real_transform()
    expected = {
        "just-code": "opencode/big-pickle",
        "test-agent": "opencode/big-pickle",
        "inception": "opencode/big-pickle",
        "just-code-mid": "opencode/big-pickle",
        "test-agent-pro": "opencode/big-pickle",
        "just-code-pro": "opencode/big-pickle",
        "architect-premium": "opencode/big-pickle",
        "devops-pro": "opencode/big-pickle",
        "ui-ux-designer": "opencode/nemotron-3.5-lightning-free",
        "introspector": "opencode/nemotron-3.5-lightning-free",
        "orchestrator": "opencode/big-pickle",
        "research": "opencode/mimo-v2.6-flash-free",
        "deepseek-research": "opencode/nemotron-3.5-lightning-free",
        "nemotron-research": "opencode/nemotron-3.5-lightning-free",
    }
    for agent, model in expected.items():
        assert zen["agents"][agent]["model"] == model, agent


# ---------------------------------------------------------------------------
# 2. per-agent parity
# ---------------------------------------------------------------------------

def test_real_transform_is_structurally_identical_apart_from_model_and_description() -> None:
    config, zen, _, _ = _real_transform()
    for name, base in config["agents"].items():
        base_cmp = {k: v for k, v in base.items() if k not in ("model", "description")}
        zen_cmp = {
            k: v for k, v in zen["agents"][name].items() if k not in ("model", "description")
        }
        assert zen_cmp == base_cmp, name


def test_real_transform_preserves_top_level_config() -> None:
    config, zen, _, _ = _real_transform()
    assert zen["$schema"] == config["$schema"]
    assert zen["default_agent"] == config["default_agent"]
    assert zen["permissions"] == config["permissions"]


# ---------------------------------------------------------------------------
# 3. fail-closed generator behaviour
# ---------------------------------------------------------------------------

def test_generator_cli_writes_output(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    output = tmp_path / "out" / "opencode.zen.json"
    exit_code = gen_zen_config.main(
        [
            "--input", str(OPENCODE),
            "--map", str(ZEN_MAP),
            "--output", str(output),
        ]
    )
    assert exit_code == 0
    assert output.is_file()
    assert "28 agents" in capsys.readouterr().out


def test_generator_output_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    argv = [
        "--input", str(OPENCODE),
        "--map", str(ZEN_MAP),
    ]
    assert gen_zen_config.main(argv + ["--output", str(first)]) == 0
    assert gen_zen_config.main(argv + ["--output", str(second)]) == 0
    assert first.read_bytes() == second.read_bytes()


def test_generator_fails_closed_on_unmapped_model(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    config = {"agents": {"new-agent": _agent("opencode-go/brand-new-model")}}
    input_path = tmp_path / "opencode.json"
    input_path.write_text(json.dumps(config), encoding="utf-8")
    output = tmp_path / "zen.json"
    exit_code = gen_zen_config.main(
        [
            "--input", str(input_path),
            "--map", str(ZEN_MAP),
            "--output", str(output),
        ]
    )
    assert exit_code != 0
    assert not output.exists()
    assert "no Zen mapping" in capsys.readouterr().err


def test_generator_fails_closed_on_non_free_target(tmp_path: Path) -> None:
    mapping = _mapping()
    mapping["models"]["opencode-go/deepseek-v4.1-flash"] = "opencode-go/glm-5.2"
    map_path = _write_map(tmp_path, mapping)
    output = tmp_path / "zen.json"
    exit_code = gen_zen_config.main(
        [
            "--input", str(OPENCODE),
            "--map", str(map_path),
            "--output", str(output),
        ]
    )
    assert exit_code != 0
    assert not output.exists()


def test_generator_fails_closed_on_unknown_override_agent(tmp_path: Path) -> None:
    mapping = _mapping()
    mapping["overrides"] = {"ghost-agent": "opencode/big-pickle"}
    map_path = _write_map(tmp_path, mapping)
    exit_code = gen_zen_config.main(
        [
            "--input", str(OPENCODE),
            "--map", str(map_path),
            "--output", str(tmp_path / "zen.json"),
        ]
    )
    assert exit_code != 0


def test_generator_warns_but_passes_on_stale_map_source(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    mapping = _mapping()
    mapping["models"]["opencode-go/retired-model"] = "opencode/big-pickle"
    map_path = _write_map(tmp_path, mapping)
    exit_code = gen_zen_config.main(
        [
            "--input", str(OPENCODE),
            "--map", str(map_path),
            "--output", str(tmp_path / "zen.json"),
        ]
    )
    assert exit_code == 0
    assert "stale" in capsys.readouterr().err


def test_generator_applies_overrides_last(tmp_path: Path) -> None:
    mapping = _mapping()
    mapping["overrides"] = {"just-code": "opencode/mimo-v2.6-flash-free"}
    map_path = _write_map(tmp_path, mapping)
    output = tmp_path / "zen.json"
    assert (
        gen_zen_config.main(
            [
                "--input", str(OPENCODE),
                "--map", str(map_path),
                "--output", str(output),
            ]
        )
        == 0
    )
    zen = json.loads(output.read_text(encoding="utf-8"))
    assert zen["agents"]["just-code"]["model"] == "opencode/mimo-v2.6-flash-free"


def test_generator_allows_already_free_models_through(tmp_path: Path) -> None:
    config = {"agents": {"free-agent": _agent("opencode/space-bunny-free")}}
    input_path = tmp_path / "opencode.json"
    input_path.write_text(json.dumps(config), encoding="utf-8")
    output = tmp_path / "zen.json"
    exit_code = gen_zen_config.main(
        [
            "--input", str(input_path),
            "--map", str(ZEN_MAP),
            "--output", str(output),
        ]
    )
    assert exit_code == 0
    zen = json.loads(output.read_text(encoding="utf-8"))
    assert zen["agents"]["free-agent"]["model"] == "opencode/space-bunny-free"


def test_generator_passes_xai_models_through_identity(tmp_path: Path) -> None:
    """MDU-42: xai/* models are identity-exempt from every zen remap."""
    config = {"agents": {"grok-x-y": _agent("xai/grok-4.7")}}
    input_path = tmp_path / "opencode.json"
    input_path.write_text(json.dumps(config), encoding="utf-8")
    output = tmp_path / "zen.json"
    exit_code = gen_zen_config.main(
        [
            "--input", str(input_path),
            "--map", str(ZEN_MAP),
            "--output", str(output),
        ]
    )
    assert exit_code == 0
    zen = json.loads(output.read_text(encoding="utf-8"))
    assert zen["agents"]["grok-x-y"]["model"] == "xai/grok-4.7"


def test_generator_passes_xai_through_for_any_agent_name(tmp_path: Path) -> None:
    """The xai/* exemption is a model-family rule, not an agent-name rule."""
    config = {"agents": {"brand-new-agent": _agent("xai/some-account-model")}}
    input_path = tmp_path / "opencode.json"
    input_path.write_text(json.dumps(config), encoding="utf-8")
    output = tmp_path / "zen.json"
    exit_code = gen_zen_config.main(
        [
            "--input", str(input_path),
            "--map", str(ZEN_MAP),
            "--output", str(output),
        ]
    )
    assert exit_code == 0
    zen = json.loads(output.read_text(encoding="utf-8"))
    assert zen["agents"]["brand-new-agent"]["model"] == "xai/some-account-model"


def test_generator_never_downgrades_xai_via_map_row(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """A stale xai/* map row cannot downgrade; identity wins and the row warns."""
    config = {"agents": {"grok-x-y": _agent("xai/grok-4.7")}}
    input_path = tmp_path / "opencode.json"
    input_path.write_text(json.dumps(config), encoding="utf-8")
    mapping = _mapping()
    mapping["models"]["xai/grok-4.7"] = "opencode/big-pickle"
    map_path = _write_map(tmp_path, mapping)
    output = tmp_path / "zen.json"
    exit_code = gen_zen_config.main(
        [
            "--input", str(input_path),
            "--map", str(map_path),
            "--output", str(output),
        ]
    )
    assert exit_code == 0
    zen = json.loads(output.read_text(encoding="utf-8"))
    assert zen["agents"]["grok-x-y"]["model"] == "xai/grok-4.7"
    stderr = capsys.readouterr().err
    assert "stale row" in stderr and "'xai/grok-4.7'" in stderr


def test_generator_fails_closed_on_free_prefix_outside_allowlist(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    config = {"agents": {"typo-agent": _agent("opencode/space-bunny-fre")}}
    input_path = tmp_path / "opencode.json"
    input_path.write_text(json.dumps(config), encoding="utf-8")
    output = tmp_path / "zen.json"
    exit_code = gen_zen_config.main(
        [
            "--input", str(input_path),
            "--map", str(ZEN_MAP),
            "--output", str(output),
        ]
    )
    assert exit_code != 0
    assert not output.exists()
    assert "not in the free Zen allowlist" in capsys.readouterr().err


def test_generator_fails_closed_on_absent_model(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    agent = _agent("opencode/big-pickle")
    del agent["model"]
    config = {"agents": {"inheriting-agent": agent}}
    input_path = tmp_path / "opencode.json"
    input_path.write_text(json.dumps(config), encoding="utf-8")
    output = tmp_path / "zen.json"
    exit_code = gen_zen_config.main(
        [
            "--input", str(input_path),
            "--map", str(ZEN_MAP),
            "--output", str(output),
        ]
    )
    assert exit_code != 0
    assert not output.exists()
    assert "has no 'model'" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# 4. free_zen_models derivation
# ---------------------------------------------------------------------------

def test_free_zen_models_uses_provider_prefix(tmp_path: Path) -> None:
    path = tmp_path / "registry.txt"
    path.write_text(
        "\n".join(
            [
                "opencode/big-pickle",
                "opencode/nemotron-3-ultra-free",
                "opencode-go/glm-5.2",
                "opencode-zen/big-pickle",
                "xai/grok-4.7",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    assert free_zen_models(load_registry(path)) == {
        "opencode/big-pickle",
        "opencode/nemotron-3-ultra-free",
    }


def test_free_zen_models_real_snapshot() -> None:
    free = _free_models()
    assert "opencode/big-pickle" in free
    assert "opencode/nemotron-3.5-lightning-free" in free
    assert not any(model.startswith("opencode-go/") for model in free)
    assert not any(model.startswith("opencode-zen/") for model in free)
    assert not any(model.startswith("xai/") for model in free)


# ---------------------------------------------------------------------------
# 5. validate_zen
# ---------------------------------------------------------------------------

def test_validate_zen_passes_on_matching_fixture(tmp_path: Path) -> None:
    build = _minimal_build(tmp_path)
    assert validate.validate_zen(build) == []


def test_validate_zen_skips_when_file_absent(tmp_path: Path) -> None:
    build = _minimal_build(tmp_path)
    (build / "opencode.zen.json").unlink()
    assert validate.validate_zen(build) == []


def test_validate_zen_flags_paid_go_model(tmp_path: Path) -> None:
    build = _minimal_build(tmp_path)
    zen = json.loads((build / "opencode.zen.json").read_text(encoding="utf-8"))
    zen["agents"]["test-agent"]["model"] = "opencode-go/glm-5.2"
    (build / "opencode.zen.json").write_text(json.dumps(zen), encoding="utf-8")
    errors = validate.validate_zen(build)
    assert any("paid Go model" in err for err in errors)
    assert any("'opencode-go/'" in err for err in errors)


def test_validate_zen_flags_non_free_opencode_model(tmp_path: Path) -> None:
    build = _minimal_build(tmp_path)
    zen = json.loads((build / "opencode.zen.json").read_text(encoding="utf-8"))
    zen["agents"]["test-agent"]["model"] = "opencode/not-in-snapshot"
    (build / "opencode.zen.json").write_text(json.dumps(zen), encoding="utf-8")
    errors = validate.validate_zen(build)
    assert any("non-free model" in err for err in errors)


def test_validate_zen_flags_per_agent_drift(tmp_path: Path) -> None:
    build = _minimal_build(tmp_path)
    zen = json.loads((build / "opencode.zen.json").read_text(encoding="utf-8"))
    zen["agents"]["test-agent"]["request"] = {"body": {"temperature": 0.9}}
    (build / "opencode.zen.json").write_text(json.dumps(zen), encoding="utf-8")
    errors = validate.validate_zen(build)
    assert any("beyond model/description" in err for err in errors)


def test_validate_zen_flags_missing_agent(tmp_path: Path) -> None:
    build = _minimal_build(tmp_path)
    zen = json.loads((build / "opencode.zen.json").read_text(encoding="utf-8"))
    del zen["agents"]["test-agent"]
    (build / "opencode.zen.json").write_text(json.dumps(zen), encoding="utf-8")
    errors = validate.validate_zen(build)
    assert any("missing agent" in err for err in errors)


def test_validate_zen_flags_extra_agent(tmp_path: Path) -> None:
    build = _minimal_build(tmp_path)
    zen = json.loads((build / "opencode.zen.json").read_text(encoding="utf-8"))
    zen["agents"]["extra"] = _agent("opencode/big-pickle")
    (build / "opencode.zen.json").write_text(json.dumps(zen), encoding="utf-8")
    errors = validate.validate_zen(build)
    assert any("absent from opencode.json" in err for err in errors)


def test_validate_zen_flags_top_level_key_drift(tmp_path: Path) -> None:
    build = _minimal_build(tmp_path)
    zen = json.loads((build / "opencode.zen.json").read_text(encoding="utf-8"))
    zen["permissions"] = []
    (build / "opencode.zen.json").write_text(json.dumps(zen), encoding="utf-8")
    errors = validate.validate_zen(build)
    assert any("top-level key 'permissions'" in err for err in errors)


def test_validate_schema_checks_zen_variant(tmp_path: Path) -> None:
    build = _minimal_build(tmp_path)
    zen = json.loads((build / "opencode.zen.json").read_text(encoding="utf-8"))
    zen["agents"] = {}
    (build / "opencode.zen.json").write_text(json.dumps(zen), encoding="utf-8")
    errors, ran = validate.validate_schema(build, config_name="opencode.zen.json")
    if not ran:  # jsonschema not installed
        pytest.skip("jsonschema not installed")
    assert any("opencode.zen.json schema violation" in err for err in errors)


# ---------------------------------------------------------------------------
# 6. --variant flag
# ---------------------------------------------------------------------------

def test_main_variant_zen_passes(tmp_path: Path) -> None:
    build = _minimal_build(tmp_path)
    assert validate.main([str(build), "--variant", "zen"]) == 0


def test_main_variant_go_ignores_invalid_zen(tmp_path: Path) -> None:
    build = _minimal_build(tmp_path)
    zen = json.loads((build / "opencode.zen.json").read_text(encoding="utf-8"))
    zen["agents"]["test-agent"]["model"] = "opencode-go/glm-5.2"
    (build / "opencode.zen.json").write_text(json.dumps(zen), encoding="utf-8")
    assert validate.main([str(build), "--variant", "go"]) == 0


def test_main_variant_both_catches_invalid_zen(tmp_path: Path) -> None:
    build = _minimal_build(tmp_path)
    zen = json.loads((build / "opencode.zen.json").read_text(encoding="utf-8"))
    zen["agents"]["test-agent"]["model"] = "opencode-go/glm-5.2"
    (build / "opencode.zen.json").write_text(json.dumps(zen), encoding="utf-8")
    assert validate.main([str(build), "--variant", "both"]) == 1


def test_main_variant_zen_absent_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    build = _minimal_build(tmp_path)
    (build / "opencode.zen.json").unlink()
    assert validate.main([str(build), "--variant", "zen"]) == 1
    assert "absent but --variant zen was requested" in capsys.readouterr().out


def test_main_variant_both_absent_is_info_only(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    build = _minimal_build(tmp_path)
    (build / "opencode.zen.json").unlink()
    assert validate.main([str(build), "--variant", "both"]) == 0
    assert "skipping Zen variant checks" in capsys.readouterr().out


def test_main_default_variant_absent_is_info_only(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    build = _minimal_build(tmp_path)
    (build / "opencode.zen.json").unlink()
    assert validate.main([str(build)]) == 0
    assert "skipping Zen variant checks" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# 7. description substitutions
# ---------------------------------------------------------------------------

def test_real_transform_removes_go_tier_description_phrases() -> None:
    _, zen, _, _ = _real_transform()
    assert "opencode-go/" not in gen_zen_config.render(zen)
    phrases = [
        "Go budget model",
        "mid-tier Go model",
        "premium Go model",
        "top-tier reasoning model",
        "mid-tier coding-optimized model",
        "premium model",
    ]
    for name, definition in zen["agents"].items():
        description = definition["description"]
        for phrase in phrases:
            assert phrase not in description, (name, phrase)


def test_real_transform_description_uses_zen_wording() -> None:
    _, zen, _, _ = _real_transform()
    assert zen["agents"]["just-code"]["description"].startswith(
        "Writes production code using Zen free model."
    )
    assert zen["agents"]["architect-premium"]["description"].startswith(
        "Produces architecture using Zen free model."
    )


# ---------------------------------------------------------------------------
# 8. integration + README/docs acceptance strings
# ---------------------------------------------------------------------------

def test_build_emits_and_validates_zen_config() -> None:
    build = subprocess.run(
        ["bash", "build.sh"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert build.returncode == 0, build.stderr
    zen_path = REPO / "build" / "opencode.zen.json"
    assert zen_path.is_file()
    assert "opencode-go/" not in zen_path.read_text(encoding="utf-8")

    check = subprocess.run(
        ["python3", "scripts/lib/validate.py", "build", "--variant", "zen"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert check.returncode == 0, check.stdout + check.stderr


def test_readme_documents_two_tier_switch() -> None:
    text = README.read_text(encoding="utf-8")
    assert "Model Tiers — Zen (default) / Go (switch-up)" in text
    assert "Install the default (Zen) tier" in text
    assert "./deploy.sh --force --tier=go" in text
    assert "./deploy.sh --force --tier=zen" in text
    assert "opencode.zen.json" in text
    assert "opencode.go.json" in text
    assert "start a new session" in text
    assert "docs/model-registry.md#zen-variant-mapping-mdu-33" in text


def test_readme_blocks_are_valid_local_links() -> None:
    text = README.read_text(encoding="utf-8")
    match = re.search(
        r"\[docs/model-registry\.md\]\(([^)]+)\)", text
    )
    assert match, "README must link docs/model-registry.md"
    target = match.group(1).split("#", 1)[0]
    assert (REPO / target).is_file()


def test_model_registry_doc_has_zen_section() -> None:
    text = MODEL_DOC.read_text(encoding="utf-8")
    assert "## Zen variant mapping (MDU-33)" in text
    assert "overrides" in text
    # Every mapped source and target is documented.
    for source, target in _mapping()["models"].items():
        assert source in text
        assert target in text


# ---------------------------------------------------------------------------
# 9. gap coverage: cross-process determinism, remaining fail-closed branches
# ---------------------------------------------------------------------------

def _run_generator(tmp_path: Path, argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", "scripts/lib/gen_zen_config.py", *argv],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_generator_is_byte_identical_across_separate_processes(tmp_path: Path) -> None:
    """Determinism must hold across runs, not just within one interpreter."""
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    common = ["--input", str(OPENCODE), "--map", str(ZEN_MAP)]
    for output in (first, second):
        result = _run_generator(tmp_path, common + ["--output", str(output)])
        assert result.returncode == 0, result.stderr
    assert first.read_bytes() == second.read_bytes()
    # Deterministic serialization: stable key order, trailing newline.
    text = first.read_text(encoding="utf-8")
    assert text.endswith("\n") and not text.endswith("\n\n")
    assert text == json.dumps(json.loads(text), indent=2, ensure_ascii=False) + "\n"


def test_generator_fails_closed_when_map_file_is_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    output = tmp_path / "zen.json"
    exit_code = gen_zen_config.main(
        [
            "--input", str(OPENCODE),
            "--map", str(tmp_path / "no-such-map.json"),
            "--output", str(output),
        ]
    )
    assert exit_code != 0
    assert not output.exists()
    assert "mapping table not found" in capsys.readouterr().err


def test_generator_fails_closed_on_non_string_map_target(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    mapping = _mapping()
    mapping["models"]["opencode-go/deepseek-v4.1-flash"] = 42
    map_path = _write_map(tmp_path, mapping)
    output = tmp_path / "zen.json"
    exit_code = gen_zen_config.main(
        [
            "--input", str(OPENCODE),
            "--map", str(map_path),
            "--output", str(output),
        ]
    )
    assert exit_code != 0
    assert not output.exists()
    assert "not a model string" in capsys.readouterr().err


def test_generator_fails_closed_on_malformed_substitution_row(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    mapping = _mapping()
    mapping["description_substitutions"] = [["Go budget model"], ["a", "b", "c"]]
    map_path = _write_map(tmp_path, mapping)
    output = tmp_path / "zen.json"
    exit_code = gen_zen_config.main(
        [
            "--input", str(OPENCODE),
            "--map", str(map_path),
            "--output", str(output),
        ]
    )
    assert exit_code != 0
    assert not output.exists()
    assert "not a [from, to] string pair" in capsys.readouterr().err


def test_generator_applies_substitution_rows_from_the_map(tmp_path: Path) -> None:
    """Substitutions are data: a custom row rewrites every agent description."""
    config = {
        "agents": {
            "first": _agent(
                "opencode-go/deepseek-v4.1-flash", description="Go budget model."
            ),
            "second": _agent(
                "opencode-go/deepseek-v4.1-flash", description="premium Go model."
            ),
        }
    }
    input_path = tmp_path / "opencode.json"
    input_path.write_text(json.dumps(config), encoding="utf-8")
    mapping = {
        "models": {"opencode-go/deepseek-v4.1-flash": "opencode/big-pickle"},
        "description_substitutions": [
            ["Go budget model", "Zen free model"],
            ["premium Go model", "premium Zen model"],
        ],
    }
    map_path = _write_map(tmp_path, mapping)
    output = tmp_path / "zen.json"
    assert (
        gen_zen_config.main(
            ["--input", str(input_path), "--map", str(map_path), "--output", str(output)]
        )
        == 0
    )
    zen = json.loads(output.read_text(encoding="utf-8"))
    assert zen["agents"]["first"]["description"] == "Zen free model."
    assert zen["agents"]["second"]["description"] == "premium Zen model."


# ---------------------------------------------------------------------------
# 10. gap coverage: validator catches drift beyond the first agent
# ---------------------------------------------------------------------------

def _build_with_agents(tmp_path: Path, agents: dict) -> Path:
    build = _minimal_build(tmp_path)
    for name in ("opencode.json", "opencode.zen.json"):
        config = json.loads((build / name).read_text(encoding="utf-8"))
        config["agents"] = agents
        (build / name).write_text(json.dumps(config), encoding="utf-8")
    return build


def test_validate_zen_flags_go_model_in_later_agent(tmp_path: Path) -> None:
    """A paid model on any agent is caught, not only the first one seen."""
    build = _build_with_agents(
        tmp_path,
        {
            "first": _agent("opencode/big-pickle"),
            "second": _agent("opencode/big-pickle"),
            "third": _agent("opencode-go/glm-5.2"),
        },
    )
    errors = validate.validate_zen(build)
    model_errors = [err for err in errors if "paid Go model" in err]
    assert len(model_errors) == 1
    assert "'third'" in model_errors[0]


def test_validate_zen_flags_go_text_in_later_agent_description(tmp_path: Path) -> None:
    """Raw-text scan catches a Go reference left in a non-first description."""
    build = _build_with_agents(
        tmp_path,
        {
            "first": _agent("opencode/big-pickle"),
            "second": _agent(
                "opencode/big-pickle",
                description="Runs on opencode-go/glm-5.2 when the tier is Go.",
            ),
        },
    )
    errors = validate.validate_zen(build)
    assert any("still contains 'opencode-go/'" in err for err in errors)
    # The model-ref check alone would pass; the text scan is what fires.
    assert not any("paid Go model" in err for err in errors)


def test_main_variant_zen_ignores_paid_models_in_base_config(tmp_path: Path) -> None:
    """Zen-only validation must not fail on the (expected) paid Go tier file."""
    build = _minimal_build(tmp_path)
    for name in ("opencode.json", "opencode.zen.json"):
        config = json.loads((build / name).read_text(encoding="utf-8"))
        config["agents"]["test-agent"]["model"] = (
            "opencode-go/deepseek-v4.1-flash"
            if name == "opencode.json"
            else "opencode/big-pickle"
        )
        (build / name).write_text(json.dumps(config), encoding="utf-8")
    assert validate.main([str(build), "--variant", "zen"]) == 0


# ---------------------------------------------------------------------------
# 11. gap coverage: deploy.sh --tier parsing and two-tier install
# ---------------------------------------------------------------------------

def _deploy_repo(tmp_path: Path, *, with_build: bool = True) -> Path:
    """A throwaway repo root holding scripts/ (and optionally a build/ tree)."""
    repo = tmp_path / "deploy-repo"
    shutil.copytree(REPO / "scripts", repo / "scripts")
    if with_build:
        build = repo / "build"
        (build / "prompts").mkdir(parents=True)
        (build / "grok" / "agents").mkdir(parents=True)
        (build / "claude" / "agents").mkdir(parents=True)
        go_config = {"agents": {"go-agent": _agent("opencode-go/glm-5.2")}}
        zen_config = {"agents": {"go-agent": _agent("opencode/big-pickle")}}
        (build / "opencode.json").write_text(json.dumps(go_config), encoding="utf-8")
        (build / "opencode.zen.json").write_text(
            json.dumps(zen_config), encoding="utf-8"
        )
        (build / "prompts" / "shared.md").write_text("prompt\n", encoding="utf-8")
        # Real build trees always carry at least one grok/claude profile; an
        # empty dir makes deploy.sh's find-based count gate fail (pre-existing).
        (build / "grok" / "agents" / "go-agent.md").write_text(
            "---\nname: go-agent\nmodel: grok-4.6\ndescription: \"go\"\n---\n",
            encoding="utf-8",
        )
        (build / "claude" / "agents" / "go-agent.md").write_text(
            "---\nname: go-agent\ndescription: \"go\"\n---\n", encoding="utf-8"
        )
    return repo


def _deploy_env(tmp_path: Path) -> tuple[Path, dict]:
    """Isolated HOME plus a fake `opencode` so detection is deterministic."""
    home = tmp_path / "deploy-home"
    home.mkdir()
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    stub = fake_bin / "opencode"
    stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    stub.chmod(0o755)
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    return home, env


def _run_deploy(repo: Path, env: dict, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(repo / "scripts" / "deploy.sh"), *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_deploy_rejects_invalid_tier_values() -> None:
    env = os.environ.copy()
    for argv in (["--tier=bogus"], ["--tier="], ["--tier"]):
        result = subprocess.run(
            ["bash", "scripts/deploy.sh", *argv],
            cwd=REPO,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert result.returncode == 2, (argv, result.stdout, result.stderr)
        assert "--tier must be 'zen' or 'go'" in result.stderr, argv


def test_deploy_warns_on_unknown_argument(tmp_path: Path) -> None:
    repo = _deploy_repo(tmp_path)
    home, env = _deploy_env(tmp_path)
    result = _run_deploy(repo, env, "--bogus-flag")
    assert result.returncode == 0, result.stderr
    assert "ignoring unknown argument: --bogus-flag" in result.stderr
    assert "Tier: zen" in result.stdout
    # A dry run must not create the active config.
    assert not (home / ".config" / "opencode" / "opencode.json").exists()


def test_deploy_dry_run_with_build_reports_both_tier_files(tmp_path: Path) -> None:
    repo = _deploy_repo(tmp_path)
    home, env = _deploy_env(tmp_path)
    result = _run_deploy(repo, env)
    assert result.returncode == 0, result.stderr
    assert "deploying from build/" in result.stdout
    assert "[dry-run] opencode.json (zen tier)" in result.stdout
    assert "[dry-run] opencode.go.json (inactive tier)" in result.stdout
    assert "Dry run complete" in result.stdout
    assert not (home / ".config" / "opencode").exists()


def test_deploy_dry_run_without_build_warns_and_uses_repo_root(tmp_path: Path) -> None:
    repo = _deploy_repo(tmp_path, with_build=False)
    _, env = _deploy_env(tmp_path)
    result = _run_deploy(repo, env)
    assert result.returncode == 0, result.stderr
    assert "build/ not found; dry-run will use repo root" in result.stderr
    assert "opencode.zen.json missing; run ./build.sh" in result.stderr
    assert "Tier: zen" in result.stdout


def test_deploy_force_installs_active_and_parked_tiers(tmp_path: Path) -> None:
    repo = _deploy_repo(tmp_path)
    home, env = _deploy_env(tmp_path)
    result = _run_deploy(repo, env, "--force", "--tier=go")
    assert result.returncode == 0, result.stdout + result.stderr
    config_dir = home / ".config" / "opencode"
    active = json.loads((config_dir / "opencode.json").read_text(encoding="utf-8"))
    parked = json.loads(
        (config_dir / "opencode.zen.json").read_text(encoding="utf-8")
    )
    assert active["agents"]["go-agent"]["model"] == "opencode-go/glm-5.2"
    assert parked["agents"]["go-agent"]["model"] == "opencode/big-pickle"
    assert (config_dir / "prompts" / "shared.md").is_file()
    assert "opencode.json (go tier)" in result.stdout
    assert "opencode.zen.json (inactive tier)" in result.stdout


# ---------------------------------------------------------------------------
# 12. gap coverage: README AC-3 default install + manual switch
# ---------------------------------------------------------------------------

def test_readme_ac3_default_tier_and_manual_switch() -> None:
    text = README.read_text(encoding="utf-8")
    # Zen is the default: the bare --force install is documented as zen.
    assert "./deploy.sh --force                # same as --tier=zen" in text
    # Manual switch-up without the repo is documented concretely.
    assert (
        "cp ~/.config/opencode/opencode.zen.json "
        "~/.config/opencode/opencode.json"
    ) in text
    # Parked-file names match what deploy.sh actually writes.
    assert "opencode.go.json" in text
