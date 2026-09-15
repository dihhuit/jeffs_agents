#!/usr/bin/env python3
"""Validate agent definition build output for OpenCode, Grok Build, and Claude Code."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from model_registry import (
    DEFAULT_SNAPSHOT,
    check_live,
    check_models,
    find_model_refs,
    load_registry,
)

PROMPT_REF = re.compile(r"\{file:\./prompts/([^}]+)\}")
FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# Models allowed in grok/agents frontmatter. Update when a new model ships.
GROK_MODEL_ALLOWLIST = {"grok-4.6", "grok-4.5"}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER.match(text)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def validate_opencode(build_dir: Path) -> list[str]:
    errors: list[str] = []
    config_path = build_dir / "opencode.json"
    prompts_dir = build_dir / "prompts"

    if not config_path.is_file():
        return ["missing opencode.json"]

    try:
        config = load_json(config_path)
    except json.JSONDecodeError as exc:
        return [f"invalid JSON in opencode.json: {exc}"]

    agents = config.get("agent")
    if not isinstance(agents, dict) or not agents:
        errors.append("opencode.json has no agents")

    for name, definition in (agents or {}).items():
        if not isinstance(definition, dict):
            errors.append(f"agent '{name}' is not an object")
            continue
        prompt = definition.get("prompt", "")
        if not isinstance(prompt, str):
            continue
        match = PROMPT_REF.search(prompt)
        if not match:
            continue
        prompt_file = prompts_dir / match.group(1)
        if not prompt_file.is_file():
            errors.append(
                f"agent '{name}' references missing prompt: prompts/{match.group(1)}"
            )

    return errors


def validate_grok_agents(build_dir: Path) -> list[str]:
    errors: list[str] = []
    agents_dir = build_dir / "grok" / "agents"
    if not agents_dir.is_dir():
        return ["missing grok/agents/"]

    profiles = sorted(agents_dir.glob("*.md"))
    if not profiles:
        return ["no grok agent profiles in grok/agents/"]

    for profile in profiles:
        text = profile.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        if not meta:
            errors.append(f"grok profile missing YAML frontmatter: {profile.name}")
            continue
        if "name" not in meta:
            errors.append(f"grok profile missing 'name' in frontmatter: {profile.name}")
        if "model" not in meta:
            errors.append(f"grok profile missing 'model' in frontmatter: {profile.name}")
            continue
        if meta["model"] not in GROK_MODEL_ALLOWLIST:
            errors.append(
                f"grok profile uses model '{meta['model']}' outside allowlist "
                f"{sorted(GROK_MODEL_ALLOWLIST)}: {profile.name}"
            )

    return errors


def validate_claude_agents(build_dir: Path) -> list[str]:
    errors: list[str] = []
    agents_dir = build_dir / "claude" / "agents"
    if not agents_dir.is_dir():
        return ["missing claude/agents/"]

    agent_files = sorted(agents_dir.glob("*.md"))
    if not agent_files:
        return ["no Claude agent definitions in claude/agents/"]

    for agent_file in agent_files:
        text = agent_file.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        if not meta:
            errors.append(f"claude agent missing YAML frontmatter: {agent_file.name}")
            continue
        if "name" not in meta:
            errors.append(f"claude agent missing 'name' in frontmatter: {agent_file.name}")
        if "description" not in meta:
            errors.append(
                f"claude agent missing 'description' in frontmatter: {agent_file.name}"
            )

    return errors


def validate_model_refs(build_dir: Path, snapshot_path: Path) -> list[str]:
    """Validate every agent model reference in build_dir/opencode.json."""
    config_path = build_dir / "opencode.json"
    if not config_path.is_file():
        return ["missing opencode.json for model registry check"]
    if not snapshot_path.is_file():
        return [f"model registry snapshot not found: {snapshot_path}"]
    registry = load_registry(snapshot_path)
    refs = find_model_refs(config_path)
    return check_models(registry, refs)


def print_live_drift(snapshot_path: Path) -> None:
    """Print snapshot-vs-live drift for `opencode models` (informational only)."""
    drift = check_live(snapshot_path)
    if not drift["cli_found"]:
        print("  [info]  `opencode` CLI not on PATH; skipping live model drift check")
        return
    print(
        f"  [info]  live model drift vs snapshot ({snapshot_path}): "
        f"{len(drift['removed'])} removed, {len(drift['added'])} added"
    )
    for model in drift["removed"]:
        print(f"          - removed from live: {model}")
    for model in drift["added"]:
        print(f"          - added in live: {model}")
    if drift["removed"] or drift["added"]:
        print(
            "  [info]  snapshot is stale. Refresh it with: "
            "`opencode models > config/model-registry.txt`"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate.py",
        description="Validate agent definition build output.",
    )
    parser.add_argument(
        "build_dir",
        nargs="?",
        default="build",
        help="build output directory (default: build)",
    )
    parser.add_argument(
        "--live-models",
        action="store_true",
        help="print live model drift vs the registry snapshot (informational)",
    )
    args = parser.parse_args(argv)

    build_dir = Path(args.build_dir).resolve()
    print(f"==> Validating build output: {build_dir}")

    errors: list[str] = []
    errors.extend(validate_opencode(build_dir))
    errors.extend(validate_grok_agents(build_dir))
    errors.extend(validate_claude_agents(build_dir))
    errors.extend(validate_model_refs(build_dir, DEFAULT_SNAPSHOT))

    if errors:
        print("  [fail]  validation errors:")
        for err in errors:
            print(f"          - {err}")
        return 1

    agent_count = len(load_json(build_dir / "opencode.json").get("agent", {}))
    grok_count = len(list((build_dir / "grok" / "agents").glob("*.md")))
    claude_count = len(list((build_dir / "claude" / "agents").glob("*.md")))
    print(f"  [ok]    opencode.json: {agent_count} agents, all prompt refs resolved")
    print(f"  [ok]    grok/agents: {grok_count} profiles with valid frontmatter")
    print(f"  [ok]    claude/agents: {claude_count} subagents with valid frontmatter")
    print(
        f"  [ok]    model refs: all agent models present in registry "
        f"({DEFAULT_SNAPSHOT})"
    )

    if args.live_models:
        print_live_drift(DEFAULT_SNAPSHOT)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())