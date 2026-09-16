#!/usr/bin/env python3
"""Run evals: list, execute, and summarize golden eval tasks.

Evals exercise the agent DEFINITIONS themselves — the repo's own gates and,
in the future, agent-driven golden tasks — so prompt changes cannot silently
regress the team. Each task lives in ``evals/tasks/<name>/`` with a
``task.md`` (YAML frontmatter + markdown body) and an optional ``driver.sh``.

This module provides:

* ``list`` — enumerate ``evals/tasks/*/task.md`` with their frontmatter.
* ``run`` — execute a task's ``driver.sh`` (cwd = task dir, timeout enforced
  via ``timeout <minutes>m bash driver.sh``), interpret exit 0 = pass,
  non-zero = fail, timeout = fail, and write a result manifest to
  ``evals/results/<task>-<ts>.json``.
* ``summary`` — aggregate every ``evals/results/*.json`` into a compact
  table (task, result, duration).

Result manifests mirror the ``run_ledger.py`` conventions (``status``,
``started_at``, ``completed_at``, ``phases``, ``verification``) so the same
summarize logic can aggregate them.

The helper functions (``parse_task``, ``run_task``, ``summarize_results``)
are pure and importable by tests. No third-party dependencies: the YAML
frontmatter is parsed with a small built-in subset parser.

Usage:
    run_evals.py list [tasks_dir]
    run_evals.py run <task_dir> [--results-dir DIR]
    run_evals.py summary [results_dir]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# --- Module constants ---------------------------------------------------------

DEFAULT_TASKS_DIR = "evals/tasks"
DEFAULT_RESULTS_DIR = "evals/results"
TIMEOUT_RETURNCODE = 124  # GNU coreutils `timeout` exit code
OUTPUT_TAIL_CHARS = 2000

# --- Task parsing -------------------------------------------------------------

def _coerce(value: str):
    """Coerce a frontmatter scalar: strip quotes, map bools/ints."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    if value in ("true", "True"):
        return True
    if value in ("false", "False"):
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and body from a task.md file.

    Frontmatter is delimited by a leading ``---`` line and the next ``---``
    line. Only a small YAML subset is supported: ``key: value`` scalars and
    ``key:`` followed by indented ``- item`` list entries (e.g. ``expect``).
    Returns ``(frontmatter, body)``; if no frontmatter is present, returns
    ``({}, text)``.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text

    frontmatter: dict = {}
    current_list_key: str | None = None
    for line in lines[1:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if current_list_key is not None:
                frontmatter.setdefault(current_list_key, []).append(
                    _coerce(stripped[2:])
                )
            continue
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            if value:
                frontmatter[key] = _coerce(value)
                current_list_key = None
            else:
                current_list_key = key
                frontmatter[key] = []

    body = "\n".join(lines[end + 1:]).strip()
    return frontmatter, body


def parse_task(task_dir: Path) -> dict:
    """Parse a task directory into a dict.

    Reads ``task.md`` and returns ``{"task_dir", "name", "description",
    "trigger", "timeout_minutes", "expect", "body"}``. ``name`` falls back to
    the directory name and ``timeout_minutes`` defaults to 10 when the
    frontmatter omits them. Raises ``FileNotFoundError`` if ``task.md`` is
    missing. Pure function: no I/O beyond reading the task file.
    """
    task_md = task_dir / "task.md"
    text = task_md.read_text(encoding="utf-8")
    frontmatter, body = _parse_frontmatter(text)
    return {
        "task_dir": str(task_dir),
        "name": frontmatter.get("name", task_dir.name),
        "description": frontmatter.get("description", ""),
        "trigger": frontmatter.get("trigger", "manual"),
        "timeout_minutes": frontmatter.get("timeout_minutes", 10),
        "expect": frontmatter.get("expect", []),
        "body": body,
    }


# --- Running ------------------------------------------------------------------

def _now_iso() -> str:
    """Current UTC time as an ISO-8601 string (run_ledger-compatible)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_test_counts(output: str) -> tuple[int, int]:
    """Extract ``N passed`` / ``N failed`` counts from pytest output.

    Returns ``(tests_passed, tests_total)``; both default to 0 when the
    output has no pytest summary line.
    """
    passed = 0
    failed = 0
    for match in re.finditer(r"(\d+)\s+passed", output):
        passed = int(match.group(1))
    for match in re.finditer(r"(\d+)\s+failed", output):
        failed = int(match.group(1))
    return passed, passed + failed


def run_task(task: dict, results_dir: Path) -> dict:
    """Execute a task's driver and write a result manifest.

    Runs ``timeout <minutes>m bash driver.sh`` with cwd = task dir using
    ``subprocess.run(..., capture_output=True)`` (no shell). Exit 0 → pass;
    non-zero → fail; the ``timeout`` returncode (124) → fail with a
    "timed out" note. Writes ``results_dir/<task>-<ts>.json`` and returns
    the manifest dict. A task without a ``driver.sh`` yields a fail manifest
    without running anything.
    """
    task_dir = Path(task["task_dir"])
    driver = task_dir / "driver.sh"
    timeout_minutes = int(task.get("timeout_minutes", 10))
    started_at = _now_iso()
    started_monotonic = time.monotonic()

    if not driver.is_file():
        manifest = _build_manifest(
            task, "fail", "no driver.sh in task directory",
            started_at, _now_iso(), 0.0, "", "", 0, 0,
        )
        _write_manifest(manifest, results_dir)
        return manifest

    try:
        proc = subprocess.run(
            ["timeout", f"{timeout_minutes}m", "bash", "driver.sh"],
            cwd=task_dir,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        manifest = _build_manifest(
            task, "fail", f"could not launch driver: {exc}",
            started_at, _now_iso(), 0.0, "", "", 0, 0,
        )
        _write_manifest(manifest, results_dir)
        return manifest

    completed_at = _now_iso()
    duration = time.monotonic() - started_monotonic
    output = (proc.stdout or "") + (proc.stderr or "")

    if proc.returncode == TIMEOUT_RETURNCODE:
        outcome, notes = "fail", f"timed out after {timeout_minutes} minute(s)"
    elif proc.returncode == 0:
        outcome, notes = "pass", "driver exited 0"
    else:
        outcome, notes = "fail", f"driver exited {proc.returncode}"

    tests_passed, tests_total = _parse_test_counts(output)
    manifest = _build_manifest(
        task, outcome, notes, started_at, completed_at, duration,
        output, proc.stdout or "", tests_passed, tests_total,
    )
    _write_manifest(manifest, results_dir)
    return manifest


def _build_manifest(
    task: dict,
    outcome: str,
    notes: str,
    started_at: str,
    completed_at: str,
    duration: float,
    output: str,
    stdout: str,
    tests_passed: int,
    tests_total: int,
) -> dict:
    """Assemble a result manifest mirroring run_ledger conventions."""
    return {
        "task": task["name"],
        "title": task["name"],
        "status": outcome,
        "started_at": started_at,
        "completed_at": completed_at,
        "phases": [
            {
                "phase": "eval",
                "agent": "driver.sh",
                "model_tier": "n/a",
                "outcome": outcome,
                "notes": notes,
            }
        ],
        "verification": {
            "build": outcome == "pass",
            "tests_passed": tests_passed,
            "tests_total": tests_total,
            "qa_grade": "PASS" if outcome == "pass" else "FAIL",
            "ci_green": outcome == "pass",
        },
        "duration_seconds": round(duration, 2),
        "expect": task.get("expect", []),
        "summary": f"{task['name']}: {outcome} ({notes})",
        "output_tail": output[-OUTPUT_TAIL_CHARS:],
        "stdout": stdout,
    }


def _write_manifest(manifest: dict, results_dir: Path) -> Path:
    """Write a manifest to ``results_dir/<task>-<ts>.json``."""
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    path = results_dir / f"{manifest['task']}-{timestamp}.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path


# --- Summarize ----------------------------------------------------------------

def summarize_results(results_dir: Path) -> list[dict]:
    """Load every ``*.json`` result manifest under results_dir.

    Returns a list of manifest dicts, sorted by filename. Unreadable or
    malformed files are skipped so one bad result can't crash the summary.
    Pure function: no side effects.
    """
    results: list[dict] = []
    if not results_dir.is_dir():
        return results
    for path in sorted(results_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            results.append(data)
    return results


def format_summary_table(results: list[dict]) -> str:
    """Render results as a compact table: task, result, duration."""
    if not results:
        return "no eval results found"
    header = f"{'task':<24} {'result':<8} {'duration':>10}"
    lines = [header, "-" * len(header)]
    for data in results:
        task = data.get("task", "?")
        status = data.get("status", "?")
        duration = data.get("duration_seconds")
        duration_str = f"{duration:.1f}s" if isinstance(duration, (int, float)) else "-"
        lines.append(f"{task:<24} {status:<8} {duration_str:>10}")
    return "\n".join(lines)


# --- CLI ----------------------------------------------------------------------

def _gate_lines(output: str) -> list[str]:
    """Lines of driver output that carry a PASS/FAIL verdict."""
    return [line for line in output.splitlines()
            if re.match(r"^\s*(PASS|FAIL)\b", line)]


def _cmd_list(tasks_dir: Path) -> int:
    if not tasks_dir.is_dir():
        print(f"  [error]  tasks dir not found: {tasks_dir}", file=sys.stderr)
        return 1
    task_dirs = sorted(d for d in tasks_dir.iterdir()
                       if d.is_dir() and (d / "task.md").is_file())
    if not task_dirs:
        print(f"  [info]  no tasks found under {tasks_dir} "
              f"(expected evals/tasks/*/task.md)", file=sys.stderr)
        return 0
    for task_dir in task_dirs:
        task = parse_task(task_dir)
        print(f"{task['name']}")
        print(f"  description: {task['description']}")
        print(f"  trigger: {task['trigger']}")
        print(f"  timeout_minutes: {task['timeout_minutes']}")
        if task["expect"]:
            print("  expect:")
            for item in task["expect"]:
                print(f"    - {item}")
        print()
    return 0


def _cmd_run(task_dir: Path, results_dir: Path) -> int:
    try:
        task = parse_task(task_dir)
    except FileNotFoundError:
        print(f"  [error]  no task.md in {task_dir}", file=sys.stderr)
        return 1
    manifest = run_task(task, results_dir)
    outcome = manifest["status"]
    duration = manifest.get("duration_seconds", 0.0)
    notes = manifest["phases"][0]["notes"]
    print(f"  [{outcome:<4}]  {manifest['task']} ({duration:.1f}s) — {notes}")
    for line in _gate_lines(manifest.get("stdout", "")):
        print(f"          {line}")
    print(f"  [info]  manifest written to {results_dir}/"
          f"{manifest['task']}-<ts>.json")
    return 0 if outcome == "pass" else 1


def _cmd_summary(results_dir: Path) -> int:
    results = summarize_results(results_dir)
    print(format_summary_table(results))
    if not results:
        print(f"  [info]  no results found under {results_dir} "
              f"(expected evals/results/*.json)", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_evals.py",
        description="List, execute, and summarize golden eval tasks.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser(
        "list", help="enumerate evals/tasks/*/task.md with their frontmatter"
    )
    list_parser.add_argument(
        "tasks_dir",
        nargs="?",
        default=DEFAULT_TASKS_DIR,
        help=f"directory containing eval tasks (default: {DEFAULT_TASKS_DIR})",
    )

    run_parser = subparsers.add_parser(
        "run", help="execute a task's driver.sh and write a result manifest"
    )
    run_parser.add_argument("task_dir", metavar="task_dir")
    run_parser.add_argument(
        "--results-dir",
        default=DEFAULT_RESULTS_DIR,
        help=f"directory for result manifests (default: {DEFAULT_RESULTS_DIR})",
    )

    summary_parser = subparsers.add_parser(
        "summary", help="aggregate all evals/results/*.json under a directory"
    )
    summary_parser.add_argument(
        "results_dir",
        nargs="?",
        default=DEFAULT_RESULTS_DIR,
        help=f"directory containing result manifests (default: {DEFAULT_RESULTS_DIR})",
    )

    args = parser.parse_args(argv)

    if args.command == "list":
        return _cmd_list(Path(args.tasks_dir))
    if args.command == "run":
        return _cmd_run(Path(args.task_dir), Path(args.results_dir))
    if args.command == "summary":
        return _cmd_summary(Path(args.results_dir))

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())