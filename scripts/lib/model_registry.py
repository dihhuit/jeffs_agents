#!/usr/bin/env python3
"""Offline and live validation of model references against the model registry.

The registry is a committed snapshot of ``opencode models`` output
(``config/model-registry.txt``) so agent definitions can be validated without
network access or a running CLI. ``--live`` additionally diffs the snapshot
against the current ``opencode models`` output when the CLI is available.

Usage:
    model_registry.py --check <opencode.json> [--snapshot <file>] [--live]

    --check <opencode.json>   validate every agent ``model`` reference
    --snapshot <file>         registry snapshot (default: <repo>/config/model-registry.txt)
    --live                    also diff the snapshot against `opencode models`
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SNAPSHOT = REPO_ROOT / "config" / "model-registry.txt"


def load_registry(path: Path) -> set[str]:
    """Load a registry snapshot file into a set of model IDs (one per line)."""
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


# ---------------------------------------------------------------------------
# MDU-42: grok-named agents must run on xAI account models
# ---------------------------------------------------------------------------

#: Exact names treated as grok-named beyond the ``grok-`` prefix.
GROK_NAMED_EXACT = {"grokestrator", "grok-plan"}


def is_grok_named(agent_name: str) -> bool:
    """True when an agent name identifies a Grok-harness agent (MDU-42).

    Grok-named = the name starts with ``grok-`` or is exactly ``grokestrator``
    or ``grok-plan``. These agents must always run on the user's xAI account
    models (``xai/*``) — never a free or Go-substituted opencode model.
    """
    return agent_name.startswith("grok-") or agent_name in GROK_NAMED_EXACT


def grok_xai_errors(agents: dict, *, label: str) -> list[str]:
    """Return named errors for grok-named agents whose model is not ``xai/*``.

    ``label`` names the config under test (e.g. ``"opencode.json"``). Agents
    without a usable string ``model`` field are also flagged: they would
    resolve to an unknown default rather than the xAI account.
    """
    errors: list[str] = []
    for name, definition in agents.items():
        if not isinstance(definition, dict) or not is_grok_named(name):
            continue
        model = definition.get("model")
        if not isinstance(model, str) or not model:
            errors.append(
                f"{label} grok-named agent '{name}' has no model field "
                "(grok-named agents must resolve to an xai/* model)"
            )
        elif not model.startswith("xai/"):
            errors.append(
                f"{label} grok-named agent '{name}' uses model '{model}', "
                "which does not start with 'xai/'"
            )
        elif len(model) <= len("xai/"):
            errors.append(
                f"{label} grok-named agent '{name}' uses model '{model}', "
                "which has an empty xai/ provider suffix"
            )
    return errors


def find_model_refs(opencode_json_path: Path) -> list[tuple[str, str]]:
    """Return ``(agent_name, model_ref)`` pairs for every agent in opencode.json.

    String-valued ``model`` fields are collected as references. Dict-valued
    ``model`` fields (structured model configs) are skipped since they do not
    name a single registry model.
    """
    config = json.loads(opencode_json_path.read_text(encoding="utf-8"))
    agents = config.get("agents") or {}
    refs: list[tuple[str, str]] = []
    for name, definition in agents.items():
        if not isinstance(definition, dict):
            continue
        model = definition.get("model")
        if isinstance(model, str):
            refs.append((name, model))
    return refs


def check_models(registry: set[str], refs: list[tuple[str, str]]) -> list[str]:
    """Return error strings for any model reference not present in the registry."""
    errors: list[str] = []
    for agent, model in refs:
        if model not in registry:
            errors.append(f"agent '{agent}' references unknown model '{model}'")
    return errors


def check_live(snapshot_path: Path, cli: str = "opencode") -> dict:
    """Diff the registry snapshot against live ``opencode models`` output.

    Only runs the CLI if it is on PATH (``shutil.which``). Returns
    ``{"removed": [...], "added": [...], "cli_found": bool}`` where ``removed``
    are snapshot models no longer available live and ``added`` are new live
    models missing from the snapshot.
    """
    if shutil.which(cli) is None:
        return {"removed": [], "added": [], "cli_found": False}

    snapshot = load_registry(snapshot_path)
    proc = subprocess.run(
        [cli, "models"], capture_output=True, text=True, check=False
    )
    live = {
        line.strip()
        for line in proc.stdout.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    return {
        "removed": sorted(snapshot - live),
        "added": sorted(live - snapshot),
        "cli_found": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="model_registry.py",
        description="Validate model references against the model registry snapshot.",
    )
    parser.add_argument(
        "--check",
        metavar="opencode.json",
        help="validate every agent model reference in this opencode.json",
    )
    parser.add_argument(
        "--snapshot",
        metavar="file",
        default=str(DEFAULT_SNAPSHOT),
        help=f"registry snapshot (default: {DEFAULT_SNAPSHOT})",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="also diff the snapshot against `opencode models` (never fails)",
    )
    parser.add_argument(
        "--grok-xai-check",
        metavar="opencode.json",
        help=(
            "verify every grok-named agent resolves to an xai/* model (MDU-42); "
            "exit 1 with named errors otherwise"
        ),
    )
    args = parser.parse_args(argv)

    snapshot_path = Path(args.snapshot)
    if args.check and not snapshot_path.is_file():
        print(f"  [error] registry snapshot not found: {snapshot_path}", file=sys.stderr)
        return 1

    exit_code = 0

    if args.grok_xai_check:
        check_path = Path(args.grok_xai_check)
        if not check_path.is_file():
            print(
                f"  [error] opencode config not found: {check_path}",
                file=sys.stderr,
            )
            return 1
        try:
            agents = json.loads(check_path.read_text(encoding="utf-8")).get(
                "agents"
            ) or {}
        except json.JSONDecodeError as exc:
            print(
                f"  [error] invalid JSON in {check_path}: {exc}", file=sys.stderr
            )
            return 1
        errors = grok_xai_errors(agents, label=str(check_path))
        if errors:
            print(
                f"  [fail]  grok-xai hard rule violated in {check_path} "
                f"({len(errors)} offence(s)):"
            )
            for err in errors:
                print(f"          - {err}")
            exit_code = 1
        else:
            print(f"  [ok]    grok-xai hard rule holds in {check_path}")

    if args.check:
        check_path = Path(args.check)
        if not check_path.is_file():
            print(f"  [error] opencode.json not found: {check_path}", file=sys.stderr)
            return 1
        registry = load_registry(snapshot_path)
        refs = find_model_refs(check_path)
        errors = check_models(registry, refs)
        if errors:
            print(f"  [fail]  {len(errors)} stale model reference(s) in {check_path}:")
            for err in errors:
                print(f"          - {err}")
            exit_code = 1
        else:
            print(
                f"  [ok]    {len(refs)} model reference(s) in {check_path} "
                f"all present in registry ({snapshot_path})"
            )

    if args.live:
        drift = check_live(snapshot_path)
        if not drift["cli_found"]:
            print("  [info]  `opencode` CLI not on PATH; skipping live drift check")
        else:
            print(
                f"  [info]  live drift vs snapshot ({snapshot_path}): "
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

    if not args.check and not args.live and not args.grok_xai_check:
        parser.print_usage(sys.stderr)
        return 2

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())