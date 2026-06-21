#!/usr/bin/env python3
"""Validate agent definition build output for OpenCode, Grok Build, and Claude Code."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROMPT_REF = re.compile(r"\{file:\./prompts/([^}]+)\}")
FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


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


def main() -> int:
    build_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "build").resolve()
    print(f"==> Validating build output: {build_dir}")

    errors: list[str] = []
    errors.extend(validate_opencode(build_dir))
    errors.extend(validate_grok_agents(build_dir))
    errors.extend(validate_claude_agents(build_dir))

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())