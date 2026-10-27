#!/usr/bin/env python3
"""Resume block: validate a canonical resume-block emission.

The orchestrator ends a session by handing the user a resume block. That block
is the next session's starting state, so its shape is fixed here: one fenced
``json`` object with eleven required keys plus optional free-text ``notes``.

This module provides the single documented shape's validator:

* ``validate`` — check a fixture against the canonical shape, exiting 1 on any
  violation and 0 when it is canonical. Extra keys warn but never fail.

Canonical is an *emission* contract only. The session-boundary gate still
accepts prose, markdown blocks, ``key: value`` lists, and JSON with two or more
of the keys — this tool never judges gate input (see ``docs/resume-block.md``).

The schema constants are module-level so tests and docs tooling can import them
without re-declaring the key sets.

Usage:
    resume_block.py validate <fixture>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Sibling import: scripts/lib is on sys.path both under pytest (tests/conftest.py)
# and when this file is run directly, but make it explicit for any other caller.
SCRIPT_LIB = Path(__file__).resolve().parent
if str(SCRIPT_LIB) not in sys.path:
    sys.path.insert(0, str(SCRIPT_LIB))

from run_ledger import HARNESSES  # noqa: E402  (single harness vocabulary)

# --- Schema constants (shared by validate and docs) --------------------------

REQUIRED_KEYS = (
    "mdu_id",
    "branch",
    "commit_sha",
    "harness",
    "status",
    "done",
    "next",
    "blocked_on",
    "design",
    "backlog",
    "artifacts",
)

OPTIONAL_KEYS = ("notes",)

ARRAY_KEYS = ("done", "next", "blocked_on", "artifacts")

# Both keys must be present; at least one must be non-empty. Preserves the
# legacy "the design or backlog path" semantics.
EITHER_OR_KEYS = ("design", "backlog")

EITHER_OR_ERROR = (
    "missing required field: 'design' or 'backlog' (one must be non-empty)"
)

# Fixed second line on non-JSON input: the tool checks output, never input.
READ_PERMISSIVE_NOTE = (
    "this tool checks canonical emission only; prose and key: value blocks "
    "remain valid gate input (docs/resume-block.md)"
)

SCALAR_KEYS = ("mdu_id", "branch", "commit_sha", "harness", "status")


# --- Validation --------------------------------------------------------------

def validate_block(data: object) -> list[str]:
    """Return a list of canonical-shape violations for ``data`` (empty if none).

    Checks required-key presence, types, the harness enum, and the
    design-or-backlog either-or rule. Extra keys are not a violation. Pure
    function: no I/O, no side effects.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["resume block must be a JSON object"]

    for key in REQUIRED_KEYS:
        if key not in data:
            errors.append(f"missing required key: '{key}'")

    for key in SCALAR_KEYS:
        if key not in data:
            continue
        value = data[key]
        if not isinstance(value, str) or not value.strip():
            errors.append(f"'{key}' must be a non-empty string")

    for key in ARRAY_KEYS:
        if key not in data:
            continue
        value = data[key]
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            errors.append(f"'{key}' must be an array of strings")

    if (
        isinstance(data.get("harness"), str)
        and data.get("harness") not in HARNESSES
    ):
        errors.append(
            f"harness must be one of opencode|grok|claude (got '{data['harness']}')"
        )

    if all(key in data for key in EITHER_OR_KEYS):
        values = [data[key] for key in EITHER_OR_KEYS]
        for key, value in zip(EITHER_OR_KEYS, values):
            if not isinstance(value, str):
                errors.append(f"'{key}' must be a string")
        if all(isinstance(value, str) for value in values) and not any(
            value.strip() for value in values
        ):
            errors.append(EITHER_OR_ERROR)

    return errors


def validate_file(path: Path) -> tuple[bool, list[str]]:
    """Load and validate a resume block fixture.

    Returns ``(ok, errors)`` where ``ok`` is False for unreadable files,
    malformed JSON, or any shape violation.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False, [f"resume block not found: {path}"]
    except OSError as exc:
        return False, [f"cannot read resume block {path}: {exc}"]
    except UnicodeDecodeError:
        return False, [f"resume block is not valid utf-8: {path}"]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return False, ["not valid JSON", READ_PERMISSIVE_NOTE]
    errors = validate_block(data)
    return (not errors, errors)


def extra_keys(data: object) -> list[str]:
    """Return keys outside the canonical shape, sorted (warnings, not failures)."""
    if not isinstance(data, dict):
        return []
    known = set(REQUIRED_KEYS) | set(OPTIONAL_KEYS)
    return sorted(key for key in data if key not in known)


# --- CLI ---------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="resume_block.py",
        description="Validate a canonical resume-block emission.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate", help="check a fixture against the canonical shape"
    )
    validate_parser.add_argument("fixture", metavar="fixture")

    args = parser.parse_args(argv)

    if args.command == "validate":
        path = Path(args.fixture)
        ok, errors = validate_file(path)
        if ok:
            print(f"  [ok]    {args.fixture} is a canonical resume block")
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):  # pragma: no cover - raced read
                return 0
            for key in extra_keys(data):
                print(
                    f"  [warn]  extra key '{key}' is not part of the canonical shape"
                )
            return 0
        print(f"  [fail]  {args.fixture}:")
        for error in errors:
            print(f"          - {error}")
        return 1

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
