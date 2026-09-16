#!/usr/bin/env python3
"""Run ledger: validate and summarize per-MDU run manifests.

The orchestrator writes one manifest per MDU at ``runs/<mdu-id>/manifest.json``
recording which agents ran, which model tiers were used, and the outcome of
each phase. This module provides:

* ``validate`` — check a manifest against the schema (required fields + enums),
  exiting 1 on any violation.
* ``summarize`` — aggregate every ``runs/*/manifest.json`` under a directory
  into counts by status, harness, phases done, fix iterations, per-model-tier
  phase usage, and QA results. Prints a text summary, or ``--json`` for machine
  use.

The schema constants are module-level so tests and other tooling can import
them without re-declaring the enum sets.

Usage:
    run_ledger.py validate <manifest.json>
    run_ledger.py summarize [runs_dir] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# --- Schema constants (shared by validate and summarize) ---------------------

STATUSES = {"in_progress", "completed", "failed", "escalated"}
PHASES = {"design", "implement", "review", "test", "deploy", "validate", "commit"}
MODEL_TIERS = {"free", "budget", "mid", "premium", "top-tier"}
OUTCOMES = {"pass", "fail", "pending"}
QA_GRADES = {"PASS", "FAIL", None}
HARNESSES = {"opencode", "grok", "claude"}

REQUIRED_FIELDS = (
    "mdu_id",
    "title",
    "status",
    "harness",
    "started_at",
    "completed_at",
    "phases",
    "fix_iterations",
    "autonomy_level",
    "verification",
    "artifacts",
    "summary",
)

REQUIRED_VERIFICATION_FIELDS = (
    "build",
    "tests_passed",
    "tests_total",
    "qa_grade",
    "ci_green",
)

DEFAULT_RUNS_DIR = "runs"


# --- Validation --------------------------------------------------------------

def validate_manifest(data: dict) -> list[str]:
    """Return a list of schema violation strings for ``data`` (empty if valid).

    Checks required fields, enum membership, and the nested ``phases`` /
    ``verification`` structures. Pure function: no I/O, no side effects.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["manifest must be a JSON object"]

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"missing required field: '{field}'")

    if "status" in data and data["status"] not in STATUSES:
        errors.append(
            f"invalid status '{data['status']}' (expected one of "
            f"{sorted(STATUSES)})"
        )

    if "harness" in data and data["harness"] not in HARNESSES:
        errors.append(
            f"harness must be one of opencode|grok|claude (got '{data['harness']}')"
        )

    for field in ("started_at", "completed_at"):
        if field not in data:
            continue
        value = data[field]
        if not isinstance(value, str):
            errors.append(f"'{field}' must be an ISO-8601 string")
            continue
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            errors.append(
                f"'{field}' must be an ISO-8601 timestamp (got {value!r})"
            )

    if "fix_iterations" in data and not isinstance(data["fix_iterations"], int):
        errors.append("'fix_iterations' must be an integer")

    if "autonomy_level" in data:
        level = data["autonomy_level"]
        if not isinstance(level, int) or not 0 <= level <= 4:
            errors.append("'autonomy_level' must be an integer in 0..4")

    if "phases" in data:
        if not isinstance(data["phases"], list):
            errors.append("'phases' must be an array")
        else:
            for i, phase in enumerate(data["phases"]):
                errors.extend(_validate_phase(phase, i))

    if "verification" in data:
        verification = data["verification"]
        if not isinstance(verification, dict):
            errors.append("'verification' must be an object")
        else:
            for field in REQUIRED_VERIFICATION_FIELDS:
                if field not in verification:
                    errors.append(f"missing required field: 'verification.{field}'")
            if "build" in verification and not isinstance(verification["build"], bool):
                errors.append("'verification.build' must be a boolean")
            for field in ("tests_passed", "tests_total"):
                if field in verification and not isinstance(
                    verification[field], int
                ):
                    errors.append(f"'verification.{field}' must be an integer")
            if "qa_grade" in verification and verification["qa_grade"] not in QA_GRADES:
                errors.append(
                    f"invalid verification.qa_grade '{verification['qa_grade']}' "
                    f"(expected 'PASS', 'FAIL', or null)"
                )
            if "ci_green" in verification and not isinstance(
                verification["ci_green"], (bool, type(None))
            ):
                errors.append("'verification.ci_green' must be a boolean or null")

    if "artifacts" in data and not isinstance(data["artifacts"], list):
        errors.append("'artifacts' must be an array of relative paths")

    if "summary" in data and not isinstance(data["summary"], str):
        errors.append("'summary' must be a string")

    return errors


def _validate_phase(phase: object, index: int) -> list[str]:
    """Validate a single ``phases`` entry; errors are prefixed with its index."""
    errors: list[str] = []
    prefix = f"phases[{index}]"
    if not isinstance(phase, dict):
        return [f"{prefix} must be an object"]

    if "phase" not in phase:
        errors.append(f"{prefix} missing required field: 'phase'")
    elif phase["phase"] not in PHASES:
        errors.append(
            f"{prefix} invalid phase '{phase['phase']}' (expected one of "
            f"{sorted(PHASES)})"
        )

    if "agent" not in phase:
        errors.append(f"{prefix} missing required field: 'agent'")
    elif not isinstance(phase["agent"], str):
        errors.append(f"{prefix} 'agent' must be a string")

    if "model_tier" not in phase:
        errors.append(f"{prefix} missing required field: 'model_tier'")
    elif phase["model_tier"] not in MODEL_TIERS:
        errors.append(
            f"{prefix} invalid model_tier '{phase['model_tier']}' (expected one "
            f"of {sorted(MODEL_TIERS)})"
        )

    if "outcome" not in phase:
        errors.append(f"{prefix} missing required field: 'outcome'")
    elif phase["outcome"] not in OUTCOMES:
        errors.append(
            f"{prefix} invalid outcome '{phase['outcome']}' (expected one of "
            f"{sorted(OUTCOMES)})"
        )

    if "notes" not in phase:
        errors.append(f"{prefix} missing required field: 'notes'")
    elif not isinstance(phase["notes"], str):
        errors.append(f"{prefix} 'notes' must be a string")

    return errors


def validate_file(path: Path) -> tuple[bool, list[str]]:
    """Load and validate a manifest file.

    Returns ``(ok, errors)`` where ``ok`` is False for unreadable files,
    malformed JSON, or any schema violation.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return False, [f"manifest not found: {path}"]
    except OSError as exc:
        return False, [f"cannot read manifest {path}: {exc}"]
    except json.JSONDecodeError as exc:
        return False, [f"invalid JSON in {path}: {exc}"]
    errors = validate_manifest(data)
    return (not errors, errors)


# --- Summarize ---------------------------------------------------------------

def load_manifests(runs_dir: Path) -> list[tuple[Path, dict]]:
    """Return ``(path, data)`` pairs for every ``*/manifest.json`` under runs_dir.

    Directories without a manifest are skipped; unreadable or malformed files
    are skipped too (summarize should not die on one bad ledger).
    """
    manifests: list[tuple[Path, dict]] = []
    if not runs_dir.is_dir():
        return manifests
    for manifest_path in sorted(runs_dir.glob("*/manifest.json")):
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        manifests.append((manifest_path, data))
    return manifests


def summarize(manifests: list[dict]) -> dict:
    """Aggregate manifests into a summary dict.

    Non-dict entries (e.g. a valid-JSON top-level array or string) are
    skipped so one malformed ledger can't crash the summary.

    Returns counts by status, per-harness counts, total phases done, per-phase
    counts, total fix iterations, per-model-tier phase counts, and QA PASS/FAIL
    counts.
    """
    manifests = [data for data in manifests if isinstance(data, dict)]
    stats = {
        "manifests": len(manifests),
        "by_status": {status: 0 for status in sorted(STATUSES)},
        "by_harness": {harness: 0 for harness in sorted(HARNESSES)},
        "phases_total": 0,
        "phases_by_phase": {phase: 0 for phase in sorted(PHASES)},
        "phases_by_tier": {tier: 0 for tier in sorted(MODEL_TIERS)},
        "fix_iterations_total": 0,
        "qa": {"PASS": 0, "FAIL": 0},
        "tests_total": 0,
        "tests_passed": 0,
    }

    for data in manifests:
        status = data.get("status")
        if status in stats["by_status"]:
            stats["by_status"][status] += 1

        harness = data.get("harness")
        if harness in stats["by_harness"]:
            stats["by_harness"][harness] += 1

        fix_iterations = data.get("fix_iterations")
        if isinstance(fix_iterations, int):
            stats["fix_iterations_total"] += fix_iterations

        verification = data.get("verification")
        if isinstance(verification, dict):
            qa_grade = verification.get("qa_grade")
            if qa_grade in stats["qa"]:
                stats["qa"][qa_grade] += 1
            tests_total = verification.get("tests_total")
            tests_passed = verification.get("tests_passed")
            if isinstance(tests_total, int):
                stats["tests_total"] += tests_total
            if isinstance(tests_passed, int):
                stats["tests_passed"] += tests_passed

        phases = data.get("phases")
        if isinstance(phases, list):
            for phase in phases:
                if not isinstance(phase, dict):
                    continue
                stats["phases_total"] += 1
                if phase.get("phase") in stats["phases_by_phase"]:
                    stats["phases_by_phase"][phase["phase"]] += 1
                if phase.get("model_tier") in stats["phases_by_tier"]:
                    stats["phases_by_tier"][phase["model_tier"]] += 1

    return stats


def format_summary(stats: dict) -> str:
    """Render the aggregate stats as a human-readable text block."""
    lines = [
        "Run ledger summary",
        "==================",
        f"manifests:            {stats['manifests']}",
        "",
        "by status:",
    ]
    for status, count in stats["by_status"].items():
        if count:
            lines.append(f"  {status:<12} {count}")
    if not any(stats["by_status"].values()):
        lines.append("  (none)")

    lines.append("")
    lines.append("by harness:")
    for harness, count in stats["by_harness"].items():
        if count:
            lines.append(f"  {harness:<12} {count}")
    if not any(stats["by_harness"].values()):
        lines.append("  (none)")

    lines.append("")
    lines.append(f"phases recorded:      {stats['phases_total']}")
    lines.append("phases by phase:")
    for phase, count in stats["phases_by_phase"].items():
        if count:
            lines.append(f"  {phase:<10} {count}")
    lines.append("phases by model tier:")
    for tier, count in stats["phases_by_tier"].items():
        if count:
            lines.append(f"  {tier:<8} {count}")

    lines.append("")
    lines.append(f"fix iterations total: {stats['fix_iterations_total']}")
    lines.append(f"QA:                   PASS {stats['qa']['PASS']}, "
                 f"FAIL {stats['qa']['FAIL']}")
    if stats["tests_total"]:
        lines.append(
            f"tests:                {stats['tests_passed']}/{stats['tests_total']} "
            f"passed"
        )
    return "\n".join(lines)


# --- CLI ---------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_ledger.py",
        description="Validate and summarize per-MDU run manifests.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate", help="check a manifest against the schema"
    )
    validate_parser.add_argument("manifest", metavar="manifest.json")

    summarize_parser = subparsers.add_parser(
        "summarize", help="aggregate all runs/*/manifest.json under a directory"
    )
    summarize_parser.add_argument(
        "runs_dir",
        nargs="?",
        default=DEFAULT_RUNS_DIR,
        help=f"directory containing run manifests (default: {DEFAULT_RUNS_DIR})",
    )
    summarize_parser.add_argument(
        "--json",
        action="store_true",
        help="emit the summary as JSON instead of text",
    )

    args = parser.parse_args(argv)

    if args.command == "validate":
        ok, errors = validate_file(Path(args.manifest))
        if ok:
            print(f"  [ok]    {args.manifest} is a valid run manifest")
            return 0
        print(f"  [fail]  {args.manifest}:")
        for error in errors:
            print(f"          - {error}")
        return 1

    if args.command == "summarize":
        runs_dir = Path(args.runs_dir)
        manifests = load_manifests(runs_dir)
        stats = summarize([data for _, data in manifests])
        if args.json:
            print(json.dumps(stats, indent=2, sort_keys=True))
        else:
            print(format_summary(stats))
            if not manifests:
                print(
                    f"  [info]  no manifests found under {runs_dir} "
                    f"(expected runs/*/manifest.json)",
                    file=sys.stderr,
                )
        return 0

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())