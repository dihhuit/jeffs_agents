#!/usr/bin/env python3
"""Prompt regression gate: ordered golden traces over prompt files.

Deterministic, offline, stdlib-only. A golden case is one target file plus an
ordered list of exact substrings (the trace) that must appear in that file in
sequence, plus an optional list of forbidden substrings that must not appear.

This module provides:

* ``cases`` — list the committed golden-case set.
* ``snapshot`` — evaluate every case under a root and write a stable JSON
  snapshot (used for before/after comparisons).
* ``diff`` — compare two snapshots and report regressions (pass→fail or
  pass→absent).
* ``gate`` — evaluate every case and cross-check against the committed
  baseline. Used by CI, the orchestrator pre-commit clause, and eval task 04.
* ``baseline`` — generate ``evals/golden/baseline.json`` from a fully passing
  tree. Refuses to write when any case fails; requires ``--update`` to overwrite
  an existing baseline.
* ``check-config`` — offline validator for the constrained promptfoo config
  grammar (``evals/promptfoo.yaml``). With ``--live`` it also runs promptfoo
  when the CLI is available, but it never fails closed when promptfoo is absent.

Accepted YAML grammar for ``check-config`` (strict subset):

* Top-level is a map: ``key: value`` or ``key:`` to start a nested collection.
* Top-level values may be lists of scalars (``- item``) or lists of flat maps.
* A list item that contains ``:`` is parsed as a map item; additional map keys
  at deeper indentation belong to the same item.
* Nested maps are allowed; a key with no value may be followed by a nested map
  or a nested list at deeper indentation.
* All other shapes (aliases, anchors, tags, multi-line flow objects, block
  scalars with ``>``/``|``, unquoted oddities) are rejected with an explicit
  line number.

Usage:
    prompt_regression.py cases [--root DIR]
    prompt_regression.py snapshot [--root DIR] [--out PATH] [--json]
    prompt_regression.py diff --before P --after P [--json]
    prompt_regression.py gate [--root DIR] [--json]
    prompt_regression.py baseline [--root DIR] [--update]
    prompt_regression.py check-config [--config P] [--live]

Exit codes (mirror ``secret_scan.py``):
    0  clean / no regression
    1  findings / regression / refused
    2  operational failure (fail closed)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- Module constants ---------------------------------------------------------

CASES_FILE = "evals/golden/cases.json"
BASELINE_FILE = "evals/golden/baseline.json"
RESULTS_DIR = "evals/results"
SNAPSHOT_PREFIX = "prompt-regression-"
ASSERT_TYPES = {"contains", "equals", "icontains"}
# A promptfoo test task must name a task directory under evals/tasks/; "." and
# ".." are rejected so a task value cannot escape evals/tasks/.
TASK_DIR_RE = re.compile(r"^evals/tasks/(?!\.{1,2}$)([A-Za-z0-9._-]+)$")


# --- Case loading -------------------------------------------------------------

def _fail(message: str, as_json: bool, *, case_results: dict | None = None,
          regressions: list | None = None, notes: list | None = None,
          label: str = "prompt-regression-gate") -> int:
    """Print a failure/operational message and return exit code 2."""
    if as_json:
        print(json.dumps({
            "exit_code": 2,
            "case_results": case_results or {},
            "regressions": regressions or [],
            "notes": notes or [],
            "error": message,
        }, indent=2, sort_keys=True))
    else:
        print(f"FAIL {label} ({message})", file=sys.stderr)
    return 2


def load_cases(root: Path) -> tuple[list[dict], list[str]]:
    """Load and validate ``evals/golden/cases.json`` under ``root``.

    Returns ``(cases, errors)``. ``errors`` is empty on success. Operational
    errors (missing file, malformed JSON, bad shape) are reported as strings
    so the caller can decide the exit code.
    """
    path = root / CASES_FILE
    errors: list[str] = []
    if not path.is_file():
        return [], [f"missing cases file: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], [f"malformed JSON in {path}: {exc}"]
    except UnicodeDecodeError as exc:
        return [], [f"cannot read {path}: {exc}"]
    except OSError as exc:
        return [], [f"cannot read {path}: {exc}"]

    if not isinstance(data, dict):
        return [], [f"{path} must be a JSON object"]
    if data.get("version") != 1:
        errors.append(f"{path} has unsupported version {data.get('version')!r}")
    cases = data.get("cases", [])
    if not isinstance(cases, list):
        errors.append(f"{path} 'cases' must be a list")
        return [], errors
    if not cases:
        errors.append(f"{path} 'cases' must contain at least one case")
        return [], errors

    seen_ids: set[str] = set()
    for i, case in enumerate(cases):
        prefix = f"cases[{i}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for required in ("id", "target", "description", "trace"):
            if required not in case:
                errors.append(f"{prefix} missing required field '{required}'")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{prefix} 'id' must be a non-empty string")
        elif case_id in seen_ids:
            errors.append(f"duplicate case id: {case_id}")
        else:
            seen_ids.add(case_id)
        for field in ("target", "description"):
            if field in case and (not isinstance(case[field], str) or not case[field]):
                errors.append(f"{prefix} '{field}' must be a non-empty string")
        target = case.get("target", "")
        if isinstance(target, str) and target:
            if Path(target).is_absolute():
                errors.append(f"{prefix} 'target' must be repo-relative: {target}")
            elif ".." in target.split("/"):
                errors.append(f"{prefix} 'target' contains '..' path segment: {target}")
        trace = case.get("trace", [])
        if not isinstance(trace, list) or not all(isinstance(m, str) for m in trace):
            errors.append(f"{prefix} 'trace' must be a list of strings")
        elif isinstance(trace, list) and len(trace) < 2:
            errors.append(f"{prefix} (id={case_id}) 'trace' must contain at least 2 markers")
        elif isinstance(trace, list) and any(m == "" for m in trace):
            errors.append(f"{prefix} (id={case_id}) 'trace' markers must be non-empty strings")
        forbidden = case.get("forbidden", [])
        if not isinstance(forbidden, list) or not all(isinstance(m, str) for m in forbidden):
            errors.append(f"{prefix} 'forbidden' must be a list of strings")
        elif isinstance(forbidden, list) and any(m == "" for m in forbidden):
            errors.append(f"{prefix} (id={case_id}) 'forbidden' markers must be non-empty strings")

    return cases, errors


# --- Case evaluation ----------------------------------------------------------

class TargetError(Exception):
    """Raised when a target file exists but cannot be read (operational)."""


def evaluate_case(root: Path, case: dict) -> tuple[str, str]:
    """Evaluate a single golden case.

    Returns ``(result, reason)`` where ``result`` is ``"pass"`` or ``"fail"``
    and ``reason`` is a short human-readable explanation. The trace is checked
    as an ordered subsequence; forbidden markers cause failure if present.

    Raises ``TargetError`` when the target file exists but is unreadable;
    missing targets are reported as a normal case failure.
    """
    case_id = case["id"]
    target = case["target"]
    trace = list(case.get("trace", []))
    forbidden = list(case.get("forbidden", []))

    target_path = (root / target).resolve()
    root_resolved = root.resolve()
    try:
        target_path.relative_to(root_resolved)
    except ValueError:
        raise TargetError(f"target escapes the repo root: {target}") from None
    try:
        text = target_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "fail", "missing target"
    except UnicodeDecodeError as exc:
        raise TargetError(f"cannot read target {target}: {exc}") from exc
    except OSError as exc:
        raise TargetError(f"cannot read target {target}: {exc}") from exc

    pos = 0
    for marker in trace:
        idx = text.find(marker, pos)
        if idx == -1:
            return "fail", f"out of order or missing: {marker}"
        pos = idx + len(marker)

    for marker in forbidden:
        if marker in text:
            return "fail", f"forbidden present: {marker}"

    marker_count = len(trace)
    return "pass", f"{marker_count}/{marker_count} markers in order"


def evaluate_all(cases: list[dict], root: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Evaluate every case under ``root``.

    Returns ``(case_results, reasons)`` dicts keyed by case id.
    """
    case_results: dict[str, str] = {}
    reasons: dict[str, str] = {}
    for case in cases:
        case_id = case["id"]
        result, reason = evaluate_case(root, case)
        case_results[case_id] = result
        reasons[case_id] = reason
    return case_results, reasons


# --- Snapshot I/O -------------------------------------------------------------

def _now_iso() -> str:
    """Current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_snapshot_shape(data: dict, path: Path) -> list[str]:
    """Validate the common snapshot/baseline shape. Returns list of error strings."""
    errors: list[str] = []
    if data.get("version") != 1:
        errors.append(f"{path} has unsupported version {data.get('version')!r}")
    case_results = data.get("case_results")
    if not isinstance(case_results, dict):
        errors.append(f"{path} 'case_results' must be a dict")
    elif not case_results:
        errors.append(f"{path} 'case_results' is empty")
    return errors


def _validate_baseline(baseline: dict, path: Path) -> list[str]:
    """Validate baseline.json shape. Returns list of error strings."""
    if not isinstance(baseline, dict):
        return [f"{path} must be a JSON object"]
    errors = _validate_snapshot_shape(baseline, path)
    case_results = baseline.get("case_results")
    if isinstance(case_results, dict):
        for case_id, result in case_results.items():
            if result != "pass":
                errors.append(f"{path} 'case_results'[{case_id!r}] must be 'pass'")
    return errors


def load_snapshot(path: Path) -> tuple[dict | None, list[str]]:
    """Load a snapshot file, returning ``(data, errors)``."""
    errors: list[str] = []
    if not path.is_file():
        return None, [f"missing snapshot file: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"malformed JSON in {path}: {exc}"]
    except UnicodeDecodeError as exc:
        return None, [f"cannot read {path}: {exc}"]
    except OSError as exc:
        return None, [f"cannot read {path}: {exc}"]
    if not isinstance(data, dict):
        return None, [f"{path} must be a JSON object"]
    errors = _validate_snapshot_shape(data, path)
    return data, errors


def write_snapshot(path: Path, root: Path, case_results: dict[str, str],
                   reasons: dict[str, str]) -> None:
    """Write a stable snapshot JSON to ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "version": 1,
        "generated_at": _now_iso(),
        "root": str(root),
        "case_results": case_results,
        "reasons": reasons,
    }
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


# --- Comparison ---------------------------------------------------------------

def compare_snapshots(before: dict, after: dict) -> tuple[list[str], list[str], list[str]]:
    """Compare two snapshots and classify changes.

    Returns ``(regressions, improvements, notes)``. A regression is a case that
    was ``pass`` in ``before`` and ``fail`` or absent in ``after``. Improvements
    are ``fail``→``pass``. New cases are noted, never failures.
    """
    before_results = before.get("case_results", {})
    after_results = after.get("case_results", {})
    regressions: list[str] = []
    improvements: list[str] = []
    notes: list[str] = []

    for case_id, result in before_results.items():
        if result != "pass":
            continue
        after_result = after_results.get(case_id)
        if after_result == "pass":
            continue
        regressions.append(case_id)

    for case_id, result in after_results.items():
        if result == "pass" and before_results.get(case_id) != "pass":
            if case_id not in before_results:
                notes.append(f"new case: {case_id}")
            else:
                improvements.append(case_id)

    return regressions, improvements, notes


# --- Output formatting --------------------------------------------------------

def _format_table(case_results: dict[str, str], reasons: dict[str, str]) -> str:
    """Format per-case results as a compact text table."""
    if not case_results:
        return "no cases defined"
    width = max(len(case_id) for case_id in case_results)
    width = max(width, len("case"))
    lines = [f"{'case':<{width}}  {'result':<6}  reason", "-" * width + "  " + "-" * 6 + "  " + "-" * 20]
    for case_id in sorted(case_results):
        result = case_results[case_id]
        reason = reasons.get(case_id, "")
        lines.append(f"{case_id:<{width}}  {result:<6}  {reason}")
    return "\n".join(lines)


def _json_output(exit_code: int, case_results: dict[str, str],
                 regressions: list[str], notes: list[str]) -> None:
    print(json.dumps({
        "exit_code": exit_code,
        "case_results": case_results,
        "regressions": regressions,
        "notes": notes,
    }, indent=2, sort_keys=True))


# --- YAML subset parser for check-config --------------------------------------

def _yaml_coerce(value: str) -> object:
    """Coerce a YAML scalar: strip quotes, map bools/ints."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    if value in ("true", "True"):
        return True
    if value in ("false", "False"):
        return False
    if value in ("null", "Null", "NULL", "~"):
        return None
    if value.lstrip("-").isdigit():
        return int(value)
    return value


_BARE_KEY_RE = __import__("re").compile(r"^[A-Za-z0-9_-]+$")
_UNSUPPORTED_SCALAR_PREFIXES = frozenset("[ { & * ! | > <".split())


def _check_scalar(value: str, line_no: int) -> None:
    """Reject flow-style/anchor/alias/tag/block scalar values."""
    stripped = value.strip()
    if stripped and stripped[0] in _UNSUPPORTED_SCALAR_PREFIXES:
        raise ValueError(
            f"unsupported shape at line {line_no}: scalar starting with '{stripped[0]}'"
        )


def _is_bare_key(value: str) -> bool:
    """True when ``value`` looks like an unquoted YAML map key."""
    return bool(_BARE_KEY_RE.match(value.strip()))


def _looks_like_map_item(content: str) -> bool:
    """True when a list-item string starts with ``bare_key:`` (possibly no value)."""
    if ":" not in content:
        return False
    key, _, _rest = content.partition(":")
    return _is_bare_key(key)


def _tokenize_yaml(text: str) -> list[tuple[int, int, str]]:
    """Return ``(line_no, indent, content)`` for non-empty, non-comment lines."""
    tokens: list[tuple[int, int, str]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        leading = line[:len(line) - len(line.lstrip())]
        if "\t" in leading:
            raise ValueError(
                f"unsupported shape at line {i}: tab indentation is not valid YAML"
            )
        indent = len(leading)
        tokens.append((i, indent, line.lstrip()))
    return tokens


def _parse_yaml_map(tokens: list[tuple[int, int, str]], idx: int,
                    base_indent: int) -> tuple[dict, int]:
    """Parse a map at ``base_indent``. Returns ``(map, next_idx)``."""
    result: dict = {}
    while idx < len(tokens):
        line_no, indent, content = tokens[idx]
        if indent < base_indent:
            break
        if indent > base_indent:
            raise ValueError(f"unsupported shape at line {line_no}: unexpected indent in map")
        if content.startswith("- "):
            break
        if ":" not in content:
            raise ValueError(f"unsupported shape at line {line_no}: expected key: value")
        key, _, value = content.partition(":")
        key = key.strip()
        value = value.strip()
        idx += 1
        if value:
            _check_scalar(value, line_no)
            result[key] = _yaml_coerce(value)
        else:
            if idx >= len(tokens):
                result[key] = None
                continue
            next_line_no, next_indent, next_content = tokens[idx]
            if next_indent <= base_indent:
                result[key] = None
                continue
            if next_content.startswith("- "):
                nested, idx = _parse_yaml_list(tokens, idx, next_indent)
                result[key] = nested
            else:
                nested, idx = _parse_yaml_map(tokens, idx, next_indent)
                result[key] = nested
    return result, idx


def _parse_yaml_list(tokens: list[tuple[int, int, str]], idx: int,
                     base_indent: int) -> tuple[list, int]:
    """Parse a list at ``base_indent``. Returns ``(list, next_idx)``."""
    items: list = []
    while idx < len(tokens):
        line_no, indent, content = tokens[idx]
        if indent < base_indent:
            break
        if indent > base_indent:
            raise ValueError(f"unsupported shape at line {line_no}: unexpected indent in list")
        if not content.startswith("- "):
            raise ValueError(f"unsupported shape at line {line_no}: expected list item")
        item_content = content[2:]
        idx += 1
        key, _, value = item_content.partition(":")
        key = key.strip()
        value = value.strip()
        if _looks_like_map_item(item_content):
            # Map item: inline key + optional value, plus deeper keys.
            item: dict = {}
            if value:
                _check_scalar(value, line_no)
                item[key] = _yaml_coerce(value)
            else:
                item[key] = None
            while idx < len(tokens):
                ln2, ind2, cont2 = tokens[idx]
                if ind2 <= base_indent:
                    break
                if cont2.startswith("- "):
                    # Nested list belonging to the most recent key with no value.
                    last_key = None
                    for k, v in item.items():
                        if v is None:
                            last_key = k
                    if last_key is None:
                        raise ValueError(f"unsupported shape at line {ln2}: nested list without key")
                    nested, idx = _parse_yaml_list(tokens, idx, ind2)
                    item[last_key] = nested
                else:
                    nested, idx = _parse_yaml_map(tokens, idx, ind2)
                    item.update(nested)
            items.append(item)
        else:
            _check_scalar(item_content, line_no)
            items.append(_yaml_coerce(item_content))
    return items, idx


def parse_promptfoo_config(text: str) -> dict:
    """Parse the constrained promptfoo YAML grammar.

    Raises ``ValueError`` with a line number for any unsupported shape.
    """
    tokens = _tokenize_yaml(text)
    if not tokens:
        return {}
    if tokens[0][2].startswith("- "):
        raise ValueError("unsupported shape at line 1: top-level list")
    result, idx = _parse_yaml_map(tokens, 0, 0)
    if idx != len(tokens):
        raise ValueError(
            f"unsupported shape at line {tokens[idx][0]}: unexpected content after top-level map"
        )
    return result


# --- check-config validation --------------------------------------------------

def _task_dir_exists(root: Path, task: str) -> bool:
    """True when ``root/evals/tasks/<task>/driver.sh`` exists."""
    return (root / "evals" / "tasks" / task / "driver.sh").is_file()


def validate_promptfoo_config(config: dict, root: Path) -> list[str]:
    """Validate parsed config structure; return list of findings (empty = clean)."""
    findings: list[str] = []

    for key in ("prompts", "providers", "tests"):
        if key not in config:
            findings.append(f"missing top-level key: {key}")
        elif not config[key]:
            findings.append(f"top-level key is empty: {key}")

    if "tests" in config:
        tests = config["tests"]
        if not isinstance(tests, list):
            findings.append("'tests' must be a list")
        elif len(tests) < 3:
            findings.append(f"'tests' has {len(tests)} entries (need >= 3)")
        else:
            for i, test in enumerate(tests):
                prefix = f"tests[{i}]"
                if not isinstance(test, dict):
                    findings.append(f"{prefix} must be a map")
                    continue
                if not test.get("description"):
                    findings.append(f"{prefix} missing non-empty 'description'")
                vars_block = test.get("vars")
                if not isinstance(vars_block, dict):
                    findings.append(f"{prefix} missing 'vars' map")
                else:
                    task = vars_block.get("task")
                    if not isinstance(task, str) or not task:
                        findings.append(f"{prefix} 'vars.task' must be a non-empty string")
                    else:
                        match = TASK_DIR_RE.match(task)
                        if not match:
                            findings.append(
                                f"{prefix} 'vars.task' must be 'evals/tasks/<name>': {task!r}"
                            )
                        elif not _task_dir_exists(root, match.group(1)):
                            findings.append(
                                f"{prefix} task dir missing or has no driver.sh: {task}"
                            )
                asserts = test.get("assert")
                if not isinstance(asserts, list) or not asserts:
                    findings.append(f"{prefix} 'assert' must be a non-empty list")
                else:
                    for j, assertion in enumerate(asserts):
                        if not isinstance(assertion, dict):
                            findings.append(f"{prefix}.assert[{j}] must be a map")
                            continue
                        if "type" not in assertion or "value" not in assertion:
                            findings.append(f"{prefix}.assert[{j}] missing 'type' or 'value'")
                            continue
                        if assertion.get("type") not in ASSERT_TYPES:
                            findings.append(
                                f"{prefix}.assert[{j}] invalid type {assertion.get('type')!r}"
                            )
    return findings


# --- Subcommand implementations -----------------------------------------------

def _cmd_cases(root: Path, as_json: bool) -> int:
    cases, errors = load_cases(root)
    if errors:
        return _fail("; ".join(errors), as_json, label="prompt-regression-cases")
    if as_json:
        print(json.dumps({"cases": cases}, indent=2, sort_keys=True))
    else:
        for case in cases:
            print(f"{case['id']}: {case['description']}")
    return 0


def _cmd_snapshot(root: Path, out: Path | None, as_json: bool) -> int:
    cases, errors = load_cases(root)
    if errors:
        return _fail("; ".join(errors), as_json, label="prompt-regression-snapshot")

    try:
        case_results, reasons = evaluate_all(cases, root)
    except TargetError as exc:
        return _fail(str(exc), as_json, label="prompt-regression-snapshot")
    snapshot_path = out or (root / RESULTS_DIR /
                            f"{SNAPSHOT_PREFIX}{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.json")
    try:
        write_snapshot(snapshot_path, root, case_results, reasons)
    except OSError as exc:
        return _fail(f"cannot write snapshot {snapshot_path}: {exc}", as_json,
                     case_results=case_results, label="prompt-regression-snapshot")

    passed = sum(1 for r in case_results.values() if r == "pass")
    total = len(case_results)
    all_pass = passed == total

    if as_json:
        _json_output(0 if all_pass else 1, case_results, [], [])
    else:
        print(_format_table(case_results, reasons))
        print()
        if all_pass:
            print(f"PASS prompt-regression-snapshot ({passed}/{total} cases)")
        else:
            failed = total - passed
            print(f"FAIL prompt-regression-snapshot ({failed}/{total} cases failed)")
        print(f"  [info]  snapshot written to {snapshot_path}")
    return 0 if all_pass else 1


def _cmd_diff(before_path: Path, after_path: Path, as_json: bool) -> int:
    before, errors1 = load_snapshot(before_path)
    after, errors2 = load_snapshot(after_path)
    errors = errors1 + errors2
    if errors:
        return _fail("; ".join(errors), as_json, label="prompt-regression-diff")
    regressions, improvements, notes = compare_snapshots(before, after)  # type: ignore[arg-type]

    if as_json:
        _json_output(0 if not regressions else 1,
                     after.get("case_results", {}), regressions, notes)
    else:
        for case_id in sorted(regressions):
            print(f"FAIL {case_id} — regression (pass→fail or missing)")
        for case_id in sorted(improvements):
            print(f"PASS {case_id} — improvement (fail→pass)")
        for note in notes:
            print(f"[info] {note}")
        if regressions:
            print(f"FAIL prompt-regression-diff ({len(regressions)} regression(s))")
        else:
            print("PASS prompt-regression-diff (no regressions)")
    return 0 if not regressions else 1


def _cmd_gate(root: Path, as_json: bool) -> int:
    cases, errors = load_cases(root)
    if errors:
        return _fail("; ".join(errors), as_json, label="prompt-regression-gate")

    baseline_path = root / BASELINE_FILE
    baseline, baseline_errors = load_snapshot(baseline_path)
    if baseline_errors:
        return _fail("; ".join(baseline_errors), as_json, label="prompt-regression-gate")
    baseline_errors = _validate_baseline(baseline, baseline_path)  # type: ignore[arg-type]
    if baseline_errors:
        return _fail("; ".join(baseline_errors), as_json, label="prompt-regression-gate")

    try:
        case_results, reasons = evaluate_all(cases, root)
    except TargetError as exc:
        return _fail(str(exc), as_json, label="prompt-regression-gate")
    baseline_results = baseline.get("case_results", {})  # type: ignore[union-attr]
    case_ids = {case["id"] for case in cases}

    regressions: list[str] = []
    notes: list[str] = []
    for case_id, result in baseline_results.items():
        if case_id not in case_ids:
            regressions.append(case_id)
    for case_id in case_results:
        if case_results[case_id] == "pass" and case_id not in baseline_results:
            notes.append(f"new case not yet baselined: {case_id}")

    passed = sum(1 for r in case_results.values() if r == "pass")
    total = len(case_results)
    all_pass = passed == total
    baseline_intact = not regressions

    exit_code = 0 if (all_pass and baseline_intact) else 1

    if as_json:
        _json_output(exit_code, case_results, regressions, notes)
    else:
        print(_format_table(case_results, reasons))
        print()
        for note in notes:
            print(f"[info] {note}")
        for case_id in sorted(regressions):
            print(f"FAIL {case_id} — baselined case missing from cases.json")
        if all_pass and baseline_intact:
            print(f"PASS prompt-regression-gate ({passed}/{total} cases, baseline intact)")
        else:
            failed = total - passed
            parts = []
            if failed:
                parts.append(f"{failed}/{total} cases failed")
            if regressions:
                parts.append(f"{len(regressions)} baselined case(s) missing")
            print(f"FAIL prompt-regression-gate ({', '.join(parts)})")
    return exit_code


def _cmd_baseline(root: Path, update: bool) -> int:
    cases, errors = load_cases(root)
    if errors:
        print(f"FAIL baseline (operational: {'; '.join(errors)})", file=sys.stderr)
        return 2

    baseline_path = root / BASELINE_FILE
    if baseline_path.exists() and not update:
        print("FAIL baseline (refused: existing baseline; use --update to overwrite)",
              file=sys.stderr)
        return 1

    try:
        case_results, _reasons = evaluate_all(cases, root)
    except TargetError as exc:
        print(f"FAIL baseline (operational: {exc})", file=sys.stderr)
        return 2
    failed = [case_id for case_id, result in case_results.items() if result == "fail"]
    if failed:
        print(f"FAIL baseline (refused: {len(failed)} case(s) failing — baseline not refreshed)",
              file=sys.stderr)
        return 1

    try:
        commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short=12", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError as exc:
        print(f"FAIL baseline (operational: git rev-parse failed: {exc})", file=sys.stderr)
        return 2
    except FileNotFoundError:
        print("FAIL baseline (operational: git not found on PATH)", file=sys.stderr)
        return 2

    baseline = {
        "version": 1,
        "generated_at": _now_iso(),
        "source_commit": commit,
        "case_results": {case_id: "pass" for case_id in case_results},
    }
    try:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n",
                                 encoding="utf-8")
    except OSError as exc:
        print(f"FAIL baseline (operational: cannot write {baseline_path}: {exc})",
              file=sys.stderr)
        return 2

    print(f"PASS baseline written to {baseline_path} ({len(case_results)} cases, commit {commit})")
    return 0


def _cmd_check_config(config_path: Path, live: bool, root: Path) -> int:
    if not config_path.is_file():
        print(f"FAIL check-config (missing config: {config_path})", file=sys.stderr)
        return 2
    try:
        text = config_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        print(f"FAIL check-config (cannot read {config_path}: {exc})", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"FAIL check-config (cannot read {config_path}: {exc})", file=sys.stderr)
        return 2

    try:
        config = parse_promptfoo_config(text)
    except ValueError as exc:
        print(f"FAIL check-config ({exc})", file=sys.stderr)
        return 2

    findings = validate_promptfoo_config(config, root)
    for finding in findings:
        print(f"FAIL check-config ({finding})")

    if live:
        if shutil.which("promptfoo"):
            try:
                proc = subprocess.run(
                    ["timeout", "300", "promptfoo", "eval", "-c", str(config_path)],
                    capture_output=True, text=True,
                )
                if proc.returncode == 0:
                    print("PASS promptfoo-live")
                else:
                    print(f"FAIL promptfoo-live (exit {proc.returncode})")
                    findings.append(f"promptfoo-live exit {proc.returncode}")
            except FileNotFoundError:
                print("SKIP promptfoo-live (reason: promptfoo binary on PATH but could not be launched; offline validation only)")
            except OSError as exc:
                print(f"SKIP promptfoo-live (reason: could not launch promptfoo: {exc}; offline validation only)")
        elif shutil.which("npx"):
            try:
                probe = subprocess.run(
                    ["timeout", "60", "npx", "-y", "promptfoo@latest", "--version"],
                    capture_output=True, text=True,
                )
            except FileNotFoundError:
                print("SKIP promptfoo-live (reason: npx on PATH but promptfoo not acquirable; offline validation only)")
                probe = None
            except OSError as exc:
                print(f"SKIP promptfoo-live (reason: could not launch npx probe: {exc}; offline validation only)")
                probe = None
            if probe is None:
                pass
            elif probe.returncode != 0:
                print("SKIP promptfoo-live (reason: promptfoo not acquirable via npx; offline validation only)")
            else:
                try:
                    proc = subprocess.run(
                        ["timeout", "300", "npx", "-y", "promptfoo@latest", "eval", "-c", str(config_path)],
                        capture_output=True, text=True,
                    )
                    if proc.returncode == 0:
                        print("PASS promptfoo-live")
                    else:
                        print(f"FAIL promptfoo-live (exit {proc.returncode})")
                        findings.append(f"promptfoo-live exit {proc.returncode}")
                except FileNotFoundError:
                    print("SKIP promptfoo-live (reason: promptfoo not acquirable via npx; offline validation only)")
                except OSError as exc:
                    print(f"SKIP promptfoo-live (reason: could not launch promptfoo via npx: {exc}; offline validation only)")
        else:
            print("SKIP promptfoo-live (reason: promptfoo CLI not on PATH; offline validation only)")

    if not findings:
        print("PASS check-config (offline validation clean)")
        return 0
    return 1


# --- CLI ----------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="prompt_regression.py",
        description="Prompt regression gate: ordered golden traces over prompt files.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    root_kwargs = {
        "default": str(Path(__file__).resolve().parents[2]),
        "help": "repo root (default: this script's repo root)",
    }

    cases_parser = subparsers.add_parser("cases", help="list the committed golden cases")
    cases_parser.add_argument("--root", **root_kwargs)
    cases_parser.add_argument("--json", action="store_true", help="machine-readable output")

    snapshot_parser = subparsers.add_parser(
        "snapshot", help="evaluate cases and write a snapshot"
    )
    snapshot_parser.add_argument("--root", **root_kwargs)
    snapshot_parser.add_argument("--out", help="snapshot output path")
    snapshot_parser.add_argument("--json", action="store_true", help="machine-readable output")

    diff_parser = subparsers.add_parser(
        "diff", help="compare two snapshots and report regressions"
    )
    diff_parser.add_argument("--before", required=True, help="before snapshot path")
    diff_parser.add_argument("--after", required=True, help="after snapshot path")
    diff_parser.add_argument("--json", action="store_true", help="machine-readable output")

    gate_parser = subparsers.add_parser(
        "gate", help="evaluate cases against the committed baseline"
    )
    gate_parser.add_argument("--root", **root_kwargs)
    gate_parser.add_argument("--json", action="store_true", help="machine-readable output")

    baseline_parser = subparsers.add_parser(
        "baseline", help="write the committed baseline from a passing tree"
    )
    baseline_parser.add_argument("--root", **root_kwargs)
    baseline_parser.add_argument(
        "--update", action="store_true",
        help="overwrite an existing baseline.json",
    )

    check_parser = subparsers.add_parser(
        "check-config", help="offline-validate the promptfoo config"
    )
    check_parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parents[2] / "evals" / "promptfoo.yaml"),
        help="path to promptfoo.yaml (default: <root>/evals/promptfoo.yaml)",
    )
    check_parser.add_argument(
        "--live", action="store_true",
        help="also run promptfoo if the CLI is available",
    )

    args = parser.parse_args(argv)

    if args.command == "cases":
        return _cmd_cases(Path(args.root), args.json)
    if args.command == "snapshot":
        out = Path(args.out) if args.out else None
        return _cmd_snapshot(Path(args.root), out, args.json)
    if args.command == "diff":
        return _cmd_diff(Path(args.before), Path(args.after), args.json)
    if args.command == "gate":
        return _cmd_gate(Path(args.root), args.json)
    if args.command == "baseline":
        return _cmd_baseline(Path(args.root), args.update)
    if args.command == "check-config":
        return _cmd_check_config(Path(args.config), args.live,
                                 Path(__file__).resolve().parents[2])

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
