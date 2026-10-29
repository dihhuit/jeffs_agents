#!/usr/bin/env python3
"""Generate the Zen-tier OpenCode config from the canonical ``opencode.json``.

The Zen tier is a whole-file transform of the Go-tier config: every agent
``model`` that is a paid ``opencode-go/*`` reference is replaced by a free Zen
model from ``config/zen-model-map.json``; already-free ``opencode/*`` agents
pass through unchanged, as do ``xai/*`` agents (MDU-42: xAI account models
run on the user's xAI subscription in the Zen tier too, never a downgrade).
Everything else (permissions, prompt refs, mode, colors, temperatures,
top-level keys) is copied structurally identical, so the two tiers cannot
drift by construction.

The transform is fail-closed: an agent with no ``model``, an agent model with
no mapping that is neither already free nor ``xai/*``, an ``opencode/*``
model outside the free Zen allowlist, a mapping target outside that
allowlist, or an override naming an unknown agent all exit non-zero instead
of leaking a paid (or unroutable) model into the Zen file. A stale mapping
source (a row no agent uses) only warns.

Usage:
    gen_zen_config.py --input <opencode.json> --output <opencode.zen.json>
                      [--map <config/zen-model-map.json>]
                      [--snapshot <config/model-registry.txt>]
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

from model_registry import DEFAULT_SNAPSHOT, free_zen_models, load_registry

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAP = REPO_ROOT / "config" / "zen-model-map.json"


class GenError(Exception):
    """Raised when the generator cannot produce a trustworthy Zen config."""


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GenError(f"invalid JSON in {path}: {exc}") from exc


def transform(
    config: dict, mapping: dict, free_models: set[str]
) -> tuple[dict, list[str], list[str]]:
    """Return ``(zen_config, errors, warnings)`` for one config + mapping pair.

    Pure function (no I/O) so tests and callers can reuse it. ``errors`` being
    non-empty means the output must not be written.
    """
    errors: list[str] = []
    warnings: list[str] = []

    agents = config.get("agents")
    if not isinstance(agents, dict) or not agents:
        return config, ["input config has no 'agents' object"], warnings

    model_map = mapping.get("models")
    if not isinstance(model_map, dict):
        errors.append("map file is missing an 'models' object")
        model_map = {}
    overrides = mapping.get("overrides", {})
    if not isinstance(overrides, dict):
        errors.append("map file 'overrides' must be an object")
        overrides = {}

    used_sources: set[str] = set()
    zen_agents: dict = {}
    for name, definition in agents.items():
        if not isinstance(definition, dict):
            errors.append(f"agent '{name}' is not an object")
            continue
        zen_definition = copy.deepcopy(definition)
        source_model = definition.get("model")
        if source_model is None:
            errors.append(
                f"agent '{name}' has no 'model'; cannot map it to a Zen model"
            )
        elif not isinstance(source_model, str):
            errors.append(
                f"agent '{name}' has a non-string model; cannot map it to a Zen model"
            )
        elif source_model.startswith("xai/"):
            # MDU-42: xai/* models are identity-exempt from every zen remap.
            pass
        elif source_model in model_map:
            used_sources.add(source_model)
            zen_definition["model"] = model_map[source_model]
        elif source_model.startswith("opencode/"):
            if source_model not in free_models:
                errors.append(
                    f"agent '{name}' model '{source_model}' looks free but is not in "
                    "the free Zen allowlist (refusing to emit an unroutable model)"
                )
        else:
            errors.append(
                f"agent '{name}' model '{source_model}' has no Zen mapping and is "
                "not an 'opencode/*' free model (refusing to leak it into the Zen config)"
            )
        zen_agents[name] = zen_definition

    for agent_name, target in overrides.items():
        if agent_name not in zen_agents:
            errors.append(f"override names unknown agent '{agent_name}'")
            continue
        zen_agents[agent_name]["model"] = target

    raw_targets = list(model_map.values()) + list(overrides.values())
    for target in raw_targets:
        if not isinstance(target, str) or not target:
            errors.append(f"mapping target is not a model string: {target!r}")
    for target in sorted({t for t in raw_targets if isinstance(t, str)}):
        if target not in free_models:
            errors.append(
                f"mapping target '{target}' is not in the free Zen allowlist "
                f"({len(free_models)} models from the registry snapshot)"
            )

    for stale_source in sorted(set(model_map) - used_sources):
        warnings.append(
            f"map source '{stale_source}' matches no agent (stale row; safe to remove)"
        )

    substitutions = mapping.get("description_substitutions", [])
    if not isinstance(substitutions, list):
        errors.append("map file 'description_substitutions' must be a list")
        substitutions = []
    for row in substitutions:
        if (
            not isinstance(row, list)
            or len(row) != 2
            or not all(isinstance(part, str) for part in row)
        ):
            errors.append(
                f"description_substitutions row is not a [from, to] string pair: {row!r}"
            )
            continue
        source, replacement = row
        for definition in zen_agents.values():
            description = definition.get("description")
            if isinstance(description, str):
                definition["description"] = description.replace(source, replacement)

    zen_config = copy.deepcopy(config)
    zen_config["agents"] = zen_agents
    return zen_config, errors, warnings


def render(config: dict) -> str:
    """Serialize deterministically: stable key order, 2-space indent, newline."""
    return json.dumps(config, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gen_zen_config.py",
        description="Generate the free-Zen OpenCode config variant.",
    )
    parser.add_argument(
        "--input",
        required=True,
        metavar="opencode.json",
        help="canonical (Go-tier) opencode.json to transform",
    )
    parser.add_argument(
        "--output",
        required=True,
        metavar="opencode.zen.json",
        help="path to write the Zen-tier config",
    )
    parser.add_argument(
        "--map",
        metavar="file",
        default=str(DEFAULT_MAP),
        help=f"model mapping table (default: {DEFAULT_MAP})",
    )
    parser.add_argument(
        "--snapshot",
        metavar="file",
        default=str(DEFAULT_SNAPSHOT),
        help=f"model registry snapshot (default: {DEFAULT_SNAPSHOT})",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    map_path = Path(args.map)
    output_path = Path(args.output)
    snapshot_path = Path(args.snapshot)

    for label, path in (
        ("input config", input_path),
        ("mapping table", map_path),
        ("registry snapshot", snapshot_path),
    ):
        if not path.is_file():
            print(f"  [error] {label} not found: {path}", file=sys.stderr)
            return 1

    try:
        config = load_json(input_path)
        mapping = load_json(map_path)
    except GenError as exc:
        print(f"  [error] {exc}", file=sys.stderr)
        return 1

    free_models = free_zen_models(load_registry(snapshot_path))
    zen_config, errors, warnings = transform(config, mapping, free_models)

    for warning in warnings:
        print(f"  [warn]  {warning}", file=sys.stderr)
    if errors:
        print(
            f"  [fail]  {len(errors)} error(s) generating {output_path.name}:",
            file=sys.stderr,
        )
        for error in errors:
            print(f"          - {error}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render(zen_config), encoding="utf-8")
    agent_count = len(zen_config.get("agents", {}))
    print(
        f"  [ok]    {output_path.name}: {agent_count} agents on free Zen models "
        f"({map_path.name})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
