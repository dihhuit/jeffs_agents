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

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "schemas" / "opencode.schema.json"

PROMPT_REF = re.compile(r"\{file:\./prompts/([^}]+)\}")
FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# Models allowed in grok/agents frontmatter. Update when a new model ships.
GROK_MODEL_ALLOWLIST = {"grok-4.6", "grok-4.5"}

# Stems in prompts/ whose grok mirrors include tier variants. Every listed
# mirror must stay behaviorally in sync with the canonical prompt.
GROK_MIRRORS: dict[str, list[str]] = {
    "architect": ["architect.md", "architect-premium.md"],
    "just-code": ["just-code.md", "just-code-mid.md", "just-code-pro.md"],
    "test-agent": ["test-agent.md", "test-agent-pro.md"],
    "code-reviewer": ["code-reviewer.md", "code-reviewer-pro.md"],
    "devops": ["devops.md", "devops-pro.md"],
    "qa": ["qa.md", "qa-pro.md"],
    "ui-ux-designer": ["ui-ux-designer.md", "ui-ux-designer-pro.md"],
    "research": ["research.md"],
    "orchestrator": ["orchestrator.md"],
}

# Role-specific contract keywords per stem. Each clause is a tuple of
# alternative substrings; the clause is satisfied when any alternative is
# present. Grok mirrors are shorter and phrase things differently, so the
# check is keyword-presence based rather than sentence matching.
ROLE_KEYWORDS: dict[str, list[tuple[str, ...]]] = {
    "just-code": [("never edit test",)],
    "test-agent": [("never modify source", "never modify production")],
    "code-reviewer": [("read-only",), ("security",)],
    "devops": [("roll back",), ("immutable infrastructure", "infrastructure-as-code")],
    "qa": [("pass grade", "pass or fail grade"), ("fail grade", "pass or fail grade")],
    "architect": [("never write production code",)],
    "research": [("never write or edit files",)],
    "orchestrator": [("mdu",), ("delegat",)],
    "ui-ux-designer": [("design",)],
}


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


def validate_skills(build_dir: Path) -> list[str]:
    """Validate Agent Skills frontmatter in build_dir/skills/*/SKILL.md.

    Each skill directory must contain a SKILL.md with YAML frontmatter that
    declares a kebab-case ``name`` and a ``description``. Missing or broken
    files are flagged as errors.
    """
    errors: list[str] = []
    skills_dir = build_dir / "skills"
    if not skills_dir.is_dir():
        return []

    skill_dirs = sorted(d for d in skills_dir.iterdir() if d.is_dir())
    if not skill_dirs:
        return []

    for skill_dir in skill_dirs:
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"skill directory missing SKILL.md: {skill_dir.name}")
            continue
        text = skill_file.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        if not meta:
            errors.append(f"skill missing YAML frontmatter: {skill_dir.name}")
            continue
        name = meta.get("name", "")
        if not name:
            errors.append(f"skill missing 'name' in frontmatter: {skill_dir.name}")
        elif not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            errors.append(
                f"skill name '{name}' is not kebab-case: {skill_dir.name}"
            )
        if "description" not in meta:
            errors.append(
                f"skill missing 'description' in frontmatter: {skill_dir.name}"
            )

    return errors


def validate_parity(build_dir: Path) -> list[str]:
    """Check that grok/agents mirrors stay behaviorally in sync with prompts.

    For each ``build_dir/prompts/<stem>.md``, every grok mirror listed in
    ``GROK_MIRRORS`` must contain the same key behavioral clauses: the
    structural markers ("Hard constraints", safety/step-limit wording) and the
    role-specific contract keywords from ``ROLE_KEYWORDS``. Checks are
    case-insensitive substring matches so shorter grok phrasing is tolerated.
    Returns a list of error strings; empty when every pair is consistent.
    """
    errors: list[str] = []
    prompts_dir = build_dir / "prompts"
    grok_dir = build_dir / "grok" / "agents"
    if not prompts_dir.is_dir() or not grok_dir.is_dir():
        return []

    for prompt_file in sorted(prompts_dir.glob("*.md")):
        stem = prompt_file.stem
        mirrors = GROK_MIRRORS.get(stem)
        if mirrors is None:
            continue
        canonical = prompt_file.read_text(encoding="utf-8").lower()
        for mirror_name in mirrors:
            mirror_path = grok_dir / mirror_name
            if not mirror_path.is_file():
                errors.append(
                    f"grok mirror grok/agents/{mirror_name} missing "
                    f"(expected for prompts/{prompt_file.name})"
                )
                continue
            mirror = mirror_path.read_text(encoding="utf-8").lower()
            errors.extend(
                _parity_clause_errors(
                    stem, canonical, mirror, mirror_name, prompt_file.name
                )
            )
    return errors


def _parity_clause_errors(
    stem: str,
    canonical: str,
    mirror: str,
    mirror_name: str,
    prompt_name: str,
) -> list[str]:
    """Compare one canonical prompt against one grok mirror, clause by clause."""
    errors: list[str] = []

    # Structural marker: "Hard constraints" section.
    _check_clause(
        errors,
        canonical,
        mirror,
        ("hard constraints",),
        "Hard constraints section",
        mirror_name,
        prompt_name,
    )

    # Structural marker: safety constraints / step-limit statement. The
    # canonical says "Step Limit"; grok mirrors say "Maximum of 50 loop steps".
    canonical_safety = (
        "safety constraints" in canonical
        or "step limit" in canonical
        or "loop steps" in canonical
    )
    mirror_safety = "safety constraints" in mirror or "loop steps" in mirror
    if canonical_safety and not mirror_safety:
        errors.append(
            f"grok mirror grok/agents/{mirror_name} missing "
            f"Step Limit statement present in prompts/{prompt_name}"
        )
    elif mirror_safety and not canonical_safety:
        errors.append(
            f"prompts/{prompt_name} missing "
            f"Step Limit statement present in grok/agents/{mirror_name}"
        )

    # Role-specific contract keywords.
    for clause in ROLE_KEYWORDS.get(stem, ()):
        _check_clause(
            errors,
            canonical,
            mirror,
            clause,
            "/".join(clause),
            mirror_name,
            prompt_name,
        )
    return errors


def _check_clause(
    errors: list[str],
    canonical: str,
    mirror: str,
    alternatives: tuple[str, ...],
    label: str,
    mirror_name: str,
    prompt_name: str,
) -> None:
    """Append a parity error when a clause is present in only one of the files."""
    in_canonical = any(alt in canonical for alt in alternatives)
    in_mirror = any(alt in mirror for alt in alternatives)
    if in_canonical and not in_mirror:
        errors.append(
            f"grok mirror grok/agents/{mirror_name} missing "
            f"{label} present in prompts/{prompt_name}"
        )
    elif in_mirror and not in_canonical:
        errors.append(
            f"prompts/{prompt_name} missing "
            f"{label} present in grok/agents/{mirror_name}"
        )


def validate_schema(
    build_dir: Path, schema_path: Path = SCHEMA_PATH
) -> tuple[list[str], bool]:
    """Validate build_dir/opencode.json against schemas/opencode.schema.json.

    Returns ``(errors, ran)``. When ``jsonschema`` is not installed the check
    is skipped with a warning (``ran=False``) so environments without the
    package still complete; CI installs jsonschema so the check always runs
    there. Schema violations are appended to ``errors`` like the other checks.
    """
    config_path = build_dir / "opencode.json"
    if not config_path.is_file():
        return ["missing opencode.json for schema check"], True
    if not schema_path.is_file():
        return [f"opencode schema not found: {schema_path}"], True
    try:
        import jsonschema
    except ImportError:
        print(
            "  [warn]  jsonschema not installed; "
            "skipping opencode.json schema check"
        )
        return [], False
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid JSON in schema {schema_path}: {exc}"], True
    errors: list[str] = []
    validator_cls = jsonschema.validators.validator_for(schema)
    for exc in validator_cls(schema).iter_errors(load_json(config_path)):
        where = f" at {list(exc.absolute_path)}" if exc.absolute_path else ""
        errors.append(f"opencode.json schema violation: {exc.message}{where}")
    return errors, True


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
    errors.extend(validate_skills(build_dir))
    errors.extend(validate_parity(build_dir))
    errors.extend(validate_model_refs(build_dir, DEFAULT_SNAPSHOT))
    schema_errors, schema_ran = validate_schema(build_dir)
    errors.extend(schema_errors)

    if errors:
        print("  [fail]  validation errors:")
        for err in errors:
            print(f"          - {err}")
        return 1

    agent_count = len(load_json(build_dir / "opencode.json").get("agent", {}))
    grok_count = len(list((build_dir / "grok" / "agents").glob("*.md")))
    claude_count = len(list((build_dir / "claude" / "agents").glob("*.md")))
    print(f"  [ok]    opencode.json: {agent_count} agents, all prompt refs resolved")
    if schema_ran:
        print("  [ok]    opencode.json: conforms to schemas/opencode.schema.json")
    print(f"  [ok]    grok/agents: {grok_count} profiles with valid frontmatter")
    print(f"  [ok]    claude/agents: {claude_count} subagents with valid frontmatter")
    parity_pairs = sum(
        len(GROK_MIRRORS[stem])
        for stem in GROK_MIRRORS
        if (build_dir / "prompts" / f"{stem}.md").is_file()
    )
    print(f"  [ok]    parity: {parity_pairs} prompt↔grok pairs consistent")
    skills_dir = build_dir / "skills"
    skill_count = len(list(skills_dir.glob("*/SKILL.md"))) if skills_dir.is_dir() else 0
    print(f"  [ok]    skills: {skill_count} valid skill(s)")
    print(
        f"  [ok]    model refs: all agent models present in registry "
        f"({DEFAULT_SNAPSHOT})"
    )

    if args.live_models:
        print_live_drift(DEFAULT_SNAPSHOT)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())