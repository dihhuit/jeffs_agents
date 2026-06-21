#!/usr/bin/env python3
"""Generate Claude Code subagent definitions from opencode.json + prompts/.

Reads a build (or source) directory containing ``opencode.json`` and
``prompts/`` and writes Claude Code user-level subagent files to
``<out>/claude/agents/*.md``.

Each agent becomes a Markdown file with YAML frontmatter:

    ---
    name: <agent key>
    description: "<description>"
    ---

    <system prompt body>

The ``model`` is intentionally omitted so each agent inherits the user's
configured Claude Code model. Behavioral tool restrictions are expressed in
the prompt body itself (mirroring how Grok profiles are deployed), so no
``tools`` allowlist is emitted.

Usage:
    gen_claude_agents.py <src_dir> [<out_dir>]

    src_dir   directory containing opencode.json and prompts/
    out_dir   output directory (default: <src_dir>/claude/agents)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROMPT_REF = re.compile(r"\{file:\./prompts/([^}]+)\}")


def yaml_quote(value: str) -> str:
    """Return a safe double-quoted YAML scalar."""
    return json.dumps(value, ensure_ascii=False)


def resolve_body(definition: dict, prompts_dir: Path) -> str | None:
    """Resolve an agent's system-prompt body from its opencode definition."""
    prompt = definition.get("prompt", "")
    if not isinstance(prompt, str):
        return None
    match = PROMPT_REF.search(prompt)
    if match:
        prompt_file = prompts_dir / match.group(1)
        if prompt_file.is_file():
            return prompt_file.read_text(encoding="utf-8").rstrip() + "\n"
        return None
    if prompt.strip():
        return prompt.rstrip() + "\n"
    return None


def main() -> int:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "build").resolve()
    out_dir = (
        Path(sys.argv[2]).resolve()
        if len(sys.argv) > 2
        else src / "claude" / "agents"
    )

    config_path = src / "opencode.json"
    prompts_dir = src / "prompts"

    if not config_path.is_file():
        print(f"  [error] missing opencode.json at {config_path}", file=sys.stderr)
        return 1

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"  [error] invalid JSON in {config_path}: {exc}", file=sys.stderr)
        return 1

    agents = config.get("agent") or {}
    out_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped: list[str] = []
    for name, definition in agents.items():
        if not isinstance(definition, dict):
            continue
        body = resolve_body(definition, prompts_dir)
        if body is None:
            skipped.append(name)
            continue
        description = str(definition.get("description", "")).strip() or f"{name} agent"
        frontmatter = (
            "---\n"
            f"name: {name}\n"
            f"description: {yaml_quote(description)}\n"
            "---\n\n"
        )
        (out_dir / f"{name}.md").write_text(frontmatter + body, encoding="utf-8")
        written += 1

    print(f"  [ok]    generated {written} Claude agent(s) -> {out_dir}")
    if skipped:
        print(
            f"  [warn]  skipped (no resolvable prompt): {', '.join(skipped)}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
