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


def find_model_refs(opencode_json_path: Path) -> list[tuple[str, str]]:
    """Return ``(agent_name, model_ref)`` pairs for every agent in opencode.json.

    String-valued ``model`` fields are collected as references. Dict-valued
    ``model`` fields (structured model configs) are skipped since they do not
    name a single registry model.
    """
    config = json.loads(opencode_json_path.read_text(encoding="utf-8"))
    agents = config.get("agent") or {}
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
    args = parser.parse_args(argv)

    snapshot_path = Path(args.snapshot)
    if not snapshot_path.is_file():
        print(f"  [error] registry snapshot not found: {snapshot_path}", file=sys.stderr)
        return 1

    exit_code = 0

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

    if not args.check and not args.live:
        parser.print_usage(sys.stderr)
        return 2

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())