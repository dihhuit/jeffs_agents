#!/usr/bin/env python3
"""Live model-health probe and deploy gate for the free Zen models (MDU-38).

``opencode models`` lists a model as ``active`` long after upstream has killed
it (mdu-37: 12 agents on a dead ``opencode/nemotron-3-ultra-free``). This script
runs one real inference per model and records the result, so a deploy can be
gated on proof of life rather than on a listing.

Usage:
    probe_models.py --refresh | --gate | --refresh --gate

    --refresh                 probe every target/alternate and rewrite the report
    --gate                    evaluate the report; exit 1 when red
    --map <file>              model map (default: <repo>/config/zen-model-map.json)
    --report <file>           report (default: <repo>/config/model-probe-report.json)
    --config <file>           optional opencode.json; free refs absent from the
                              report warn only (never fails)
    --timeout 90              per-attempt timeout in seconds
    --attempts 2              total attempts per model (permanent errors: 1)
    --max-workers 2           models probed in parallel
    --max-age-days 7          gate freshness window (0 disables the age rule only)
    --max-runtime-s 300       whole-refresh budget; remainder is ``skipped``
    --cli opencode            CLI binary used for ``run -m <model> "..."``

Exit codes (same 0/1/2 convention as ``resume_block.py``):

    0  refresh: report written (even if models failed) · gate: green
    1  gate: red — report missing/stale/mismatched or a target is not ok
    2  usage/environment error: no CLI, bad map, unwritable report, bad args
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAP = REPO_ROOT / "config" / "zen-model-map.json"
DEFAULT_REPORT = REPO_ROOT / "config" / "model-probe-report.json"

SCHEMA_VERSION = 1
PROMPT = "Reply with exactly: OK"
BOOTSTRAP = "python3 scripts/lib/probe_models.py --refresh --gate"
RETRY_SLEEP_S = 1.0
ERROR_MAX_CHARS = 200

#: Failure text that will not change on a retry: one attempt, then report.
PERMANENT_SIGNALS = (
    "model is unavailable",
    "model not found",
    "not found",
    "404",
    "invalid model",
)


class ProbeError(Exception):
    """Raised when the probe or gate cannot be evaluated at all (exit 2)."""


# ---------------------------------------------------------------------------
# map + report helpers
# ---------------------------------------------------------------------------

def load_map(path: Path) -> dict:
    """Load the Zen model map; raise ``ProbeError`` for a missing/invalid map."""
    try:
        mapping = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProbeError(f"model map not found: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ProbeError(f"model map unreadable: {path} ({exc})") from exc
    if not isinstance(mapping, dict):
        raise ProbeError(f"model map is not a JSON object: {path}")
    for key in ("models", "overrides"):
        if key in mapping and not isinstance(mapping[key], dict):
            raise ProbeError(f"model map '{key}' must be an object: {path}")
    if "alternates" in mapping and not isinstance(mapping["alternates"], list):
        raise ProbeError(f"model map 'alternates' must be a list: {path}")
    return mapping


def canonical_map_sha256(mapping: dict) -> str:
    """Hash the map's meaning, not its bytes.

    Canonicalisation is ``sort_keys`` plus compact separators, so the overlay's
    re-serialized ``build/zen-model-map.json`` (different indentation) hashes
    identically to the base map; otherwise every build would re-red the gate.
    """
    payload = json.dumps(mapping, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def probe_set(mapping: dict) -> tuple[list[str], list[str]]:
    """Return ``(targets, alternates)``, deduped and sorted.

    Targets are ``models.values() | overrides.values()`` — the hot paths that
    ``gen_zen_config.py`` emits. A model listed in both sets is a target.
    """
    targets: set[str] = set()
    for key in ("models", "overrides"):
        targets.update(
            model
            for model in (mapping.get(key) or {}).values()
            if isinstance(model, str) and model
        )
    alternates = {
        model
        for model in (mapping.get("alternates") or [])
        if isinstance(model, str) and model
    }
    return sorted(targets), sorted(alternates - targets)


def _portable_path(path: Path) -> str:
    """Render a path relative to the repo or cwd when possible, else absolute."""
    resolved = path.resolve()
    for root in (REPO_ROOT, Path.cwd()):
        try:
            return str(resolved.relative_to(root))
        except ValueError:
            continue
    return str(resolved)


def parse_probed_at(value: object) -> datetime | None:
    """Parse a report ``probed_at`` into an aware UTC datetime."""
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    try:
        if text.endswith("Z"):
            return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def write_report(path: Path, report: dict) -> None:
    """Write the report atomically (``tmp`` + ``os.replace``)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    try:
        tmp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# probing
# ---------------------------------------------------------------------------

def _first_error_line(returncode: int, stdout: str, stderr: str) -> str:
    """Return the most useful single-line error for a failed attempt."""
    for text in (stderr, stdout):
        for line in (text or "").splitlines():
            line = line.strip()
            if line:
                return line[:ERROR_MAX_CHARS]
    return f"exit code {returncode}"


def is_permanent_failure(output: str) -> bool:
    """True when the failure text means a retry cannot succeed."""
    lowered = (output or "").lower()
    return any(signal in lowered for signal in PERMANENT_SIGNALS)


def probe_one(
    model: str,
    *,
    cli: str = "opencode",
    timeout: int = 90,
    attempts: int = 2,
    runner=subprocess.run,
) -> dict:
    """Probe one model; return ``{status, attempts, latency_s, error}``.

    ``runner`` is injected (same discipline as ``check_live``) so tests can
    stub inference without subprocesses. Success is deliberately strict:
    ``returncode == 0`` **and** stdout stripped equals exactly ``OK`` — a
    truncated run, or output merely containing ``OK`` (e.g. ``NOT OK``), is not
    proof a model answered.
    """
    total_attempts = max(1, attempts)
    started = time.monotonic()
    last_error = "no attempt made"
    used = 0
    for attempt in range(1, total_attempts + 1):
        used = attempt
        try:
            proc = runner(
                [cli, "run", "-m", model, PROMPT],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            last_error = f"timeout after {timeout}s"
        except OSError as exc:  # binary vanished or cannot be executed
            last_error = f"runner error: {exc}"
        else:
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            if proc.returncode == 0 and stdout.strip() == "OK":
                return {
                    "status": "ok",
                    "attempts": attempt,
                    "latency_s": round(time.monotonic() - started, 2),
                    "error": None,
                }
            if proc.returncode == 0:
                last_error = f"no OK in output: {_first_error_line(0, stdout, stderr)}"
            else:
                last_error = _first_error_line(proc.returncode, stdout, stderr)
            if is_permanent_failure(f"{stdout}\n{stderr}"):
                break
        if attempt < total_attempts:
            time.sleep(RETRY_SLEEP_S)
    return {
        "status": "fail",
        "attempts": used,
        "latency_s": round(time.monotonic() - started, 2),
        "error": last_error,
    }


def _probe_model(
    model: str,
    role: str,
    *,
    cli: str,
    timeout: int,
    attempts: int,
    runner,
    deadline: float | None,
) -> dict:
    """Probe one model in a worker thread, honouring the refresh budget."""
    if deadline is not None and time.monotonic() >= deadline:
        return {
            "model": model,
            "role": role,
            "status": "skipped",
            "attempts": 0,
            "latency_s": 0.0,
            "error": "--max-runtime-s exhausted before this model was probed",
        }
    outcome = probe_one(
        model, cli=cli, timeout=timeout, attempts=attempts, runner=runner
    )
    return {"model": model, "role": role, **outcome}


def build_results(
    mapping: dict,
    *,
    cli: str,
    timeout: int,
    attempts: int,
    max_workers: int,
    max_runtime_s: int,
    runner=subprocess.run,
) -> list[dict]:
    """Probe every target and alternate; return results in stable order."""
    targets, alternates = probe_set(mapping)
    plan = [(model, "target") for model in targets] + [
        (model, "alternate") for model in alternates
    ]
    deadline = (
        time.monotonic() + max_runtime_s
        if max_runtime_s and max_runtime_s > 0
        else None
    )
    workers = max(1, min(max_workers, len(plan) or 1))

    def job(item: tuple[str, str]) -> dict:
        return _probe_model(
            item[0],
            item[1],
            cli=cli,
            timeout=timeout,
            attempts=attempts,
            runner=runner,
            deadline=deadline,
        )

    if workers == 1:
        results = [job(item) for item in plan]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(job, plan))

    role_order = {"target": 0, "alternate": 1}
    return sorted(results, key=lambda r: (role_order.get(r["role"], 2), r["model"]))


def refresh_report(
    mapping: dict,
    map_path: Path,
    report_path: Path,
    *,
    cli: str,
    timeout: int,
    attempts: int,
    max_workers: int,
    max_runtime_s: int,
    runner=subprocess.run,
) -> int:
    """Probe and rewrite the report; return 0 when it was written, 2 when not."""
    results = build_results(
        mapping,
        cli=cli,
        timeout=timeout,
        attempts=attempts,
        max_workers=max_workers,
        max_runtime_s=max_runtime_s,
        runner=runner,
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "probed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "refresh",
        "cli": cli,
        "timeout_s": timeout,
        "map_path": _portable_path(map_path),
        "map_sha256": canonical_map_sha256(mapping),
        "results": results,
    }
    try:
        write_report(report_path, report)
    except OSError as exc:
        print(f"  [error] cannot write report {report_path}: {exc}", file=sys.stderr)
        return 2

    for result in results:
        line = (
            f"{result['model']} ({result['role']}) "
            f"{result['attempts']} attempt(s), {result['latency_s']}s"
        )
        if result["status"] == "ok":
            print(f"  [ok]    {line}")
        elif result["status"] == "skipped":
            print(f"  [warn]  {line} — skipped")
        else:
            print(f"  [fail]  {line} — {result['error']}", file=sys.stderr)

    counts = {"ok": 0, "fail": 0, "skipped": 0}
    for result in results:
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    summary = (
        f"{len(results)} model(s) probed: {counts['ok']} ok, "
        f"{counts['fail']} fail, {counts['skipped']} skipped"
    )
    print(f"  [info]  {summary} → {report_path}")
    return 0


# ---------------------------------------------------------------------------
# gate
# ---------------------------------------------------------------------------

def gate_offences(
    report_path: Path,
    mapping: dict,
    *,
    max_age_days: int,
    config_path: Path | None = None,
    now: datetime | None = None,
) -> tuple[list[str], list[str]]:
    """Evaluate the report against the map; return ``(offences, warnings)``.

    Offences are red (exit 1); warnings never fail the gate. Rule 1 returns
    immediately because no later rule can be trusted against an absent or
    malformed report.
    """
    offences: list[str] = []
    warnings: list[str] = []
    targets, alternates = probe_set(mapping)

    # 1. report present, readable, right schema, sane probed_at.
    if not report_path.is_file():
        return [f"report missing: {report_path}"], warnings
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"report unreadable: {report_path} ({exc})"], warnings
    if not isinstance(report, dict):
        return [f"report is not a JSON object: {report_path}"], warnings
    if report.get("schema_version") != SCHEMA_VERSION:
        return [
            f"report schema_version is {report.get('schema_version')!r}, "
            f"expected {SCHEMA_VERSION}"
        ], warnings
    probed_at = parse_probed_at(report.get("probed_at"))
    if probed_at is None:
        return [
            f"report probed_at is missing or unparsable: {report.get('probed_at')!r}"
        ], warnings
    now = now or datetime.now(timezone.utc)
    if probed_at - now > timedelta(hours=1):
        return [f"report probed_at is in the future: {report['probed_at']}"], warnings

    # 2. the map the report describes is still the map in this tree.
    expected_hash = canonical_map_sha256(mapping)
    if report.get("map_sha256") != expected_hash:
        offences.append(
            "map changed since last probe "
            f"(report {str(report.get('map_sha256'))[:12]}…, "
            f"current {expected_hash[:12]}…)"
        )

    # 3. freshness (--max-age-days 0 disables only this rule).
    age = now - probed_at
    if max_age_days and max_age_days > 0 and age > timedelta(days=max_age_days):
        offences.append(
            f"report is stale: {age.total_seconds() / 86400:.1f} day(s) old, "
            f"max {max_age_days} day(s)"
        )

    # 4./5. targets must be ok; alternates only warn.
    by_model: dict[str, list[dict]] = {}
    results = report.get("results")
    if isinstance(results, list):
        for entry in results:
            if isinstance(entry, dict) and isinstance(entry.get("model"), str):
                by_model.setdefault(entry["model"], []).append(entry)

    for model in targets:
        entries = by_model.get(model, [])
        if not entries:
            offences.append(f"target '{model}' missing from the report")
            continue
        ok_entries = [entry for entry in entries if entry.get("status") == "ok"]
        if len(ok_entries) == 1:
            continue
        if len(entries) > 1 and len(ok_entries) != 1:
            offences.append(
                f"target '{model}' has {len(entries)} results, need exactly one ok"
            )
            continue
        status = entries[0].get("status")
        error = entries[0].get("error")
        detail = f" ({error})" if error else ""
        offences.append(f"target '{model}' is {status}{detail}")

    for model in alternates:
        entries = by_model.get(model, [])
        if any(entry.get("status") == "ok" for entry in entries):
            continue
        status = entries[0].get("status") if entries else "missing from the report"
        warnings.append(f"alternate '{model}' is {status}")

    # 6. free config refs beyond the reported set warn only.
    if config_path is not None:
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProbeError(f"opencode config unreadable: {config_path} ({exc})") from exc
        refs: set[str] = set()
        for definition in (config.get("agents") or {}).values():
            if isinstance(definition, dict):
                model = definition.get("model")
                if isinstance(model, str) and model.startswith("opencode/"):
                    refs.add(model)
        for model in sorted(refs - set(by_model)):
            warnings.append(
                f"config ref '{model}' is absent from the probe report (probing not extended)"
            )

    return offences, warnings


def _print_gate_verdict(offences: list[str], warnings: list[str]) -> int:
    for warning in warnings:
        print(f"  [warn]  {warning}", file=sys.stderr)
    if offences:
        print(
            f"  [fail]  model-health gate red ({len(offences)} offence(s)):",
            file=sys.stderr,
        )
        for offence in offences:
            print(f"          - {offence}", file=sys.stderr)
        print(f"  [info]  refresh with: {BOOTSTRAP}", file=sys.stderr)
        return 1
    print(f"  [ok]    model-health gate green ({len(warnings)} warning(s))")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None, *, runner=subprocess.run) -> int:
    parser = argparse.ArgumentParser(
        prog="probe_models.py",
        description=(
            "Probe free Zen models with a live inference and gate deploys on the "
            "resulting report."
        ),
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="probe every target/alternate and rewrite the report (exit 0 when written)",
    )
    parser.add_argument(
        "--gate",
        action="store_true",
        help="evaluate the report against the map; exit 1 when red",
    )
    parser.add_argument(
        "--map",
        metavar="file",
        default=str(DEFAULT_MAP),
        help=f"model map (default: {DEFAULT_MAP})",
    )
    parser.add_argument(
        "--report",
        metavar="file",
        default=str(DEFAULT_REPORT),
        help=f"probe report (default: {DEFAULT_REPORT})",
    )
    parser.add_argument(
        "--config",
        metavar="file",
        default=None,
        help="optional opencode.json; free refs absent from the report warn only",
    )
    parser.add_argument(
        "--timeout", type=int, default=90, metavar="s", help="per-attempt timeout (default: 90)"
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=2,
        metavar="n",
        help="total attempts per model; permanent errors stop after one (default: 2)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=2,
        metavar="n",
        help="models probed in parallel (default: 2)",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=7,
        metavar="n",
        help="gate freshness window in days; 0 disables the age rule (default: 7)",
    )
    parser.add_argument(
        "--max-runtime-s",
        type=int,
        default=300,
        metavar="s",
        help="whole-refresh budget; remainder is skipped (default: 300)",
    )
    parser.add_argument(
        "--cli", default="opencode", metavar="bin", help="CLI binary (default: opencode)"
    )
    args = parser.parse_args(argv)

    if not args.refresh and not args.gate:
        parser.print_usage(sys.stderr)
        print(
            "  [error] one of --refresh, --gate or --refresh --gate is required",
            file=sys.stderr,
        )
        return 2
    if args.timeout < 1 or args.attempts < 1 or args.max_workers < 1:
        print(
            "  [error] --timeout, --attempts and --max-workers must be >= 1",
            file=sys.stderr,
        )
        return 2

    report_path = Path(args.report)
    map_path = Path(args.map)

    if shutil.which(args.cli) is None:
        print(
            f"  [error] '{args.cli}' CLI not on PATH; model-health probe cannot run "
            "(exit 2, no report written)",
            file=sys.stderr,
        )
        return 2

    try:
        mapping = load_map(map_path)
    except ProbeError as exc:
        print(f"  [error] {exc}", file=sys.stderr)
        return 2

    if args.refresh:
        exit_code = refresh_report(
            mapping,
            map_path,
            report_path,
            cli=args.cli,
            timeout=args.timeout,
            attempts=args.attempts,
            max_workers=args.max_workers,
            max_runtime_s=args.max_runtime_s,
            runner=runner,
        )
        if exit_code != 0:
            return exit_code
        if not args.gate:
            return 0

    try:
        offences, warnings = gate_offences(
            report_path,
            mapping,
            max_age_days=args.max_age_days,
            config_path=Path(args.config) if args.config else None,
        )
    except ProbeError as exc:
        print(f"  [error] {exc}", file=sys.stderr)
        return 2
    return _print_gate_verdict(offences, warnings)


if __name__ == "__main__":
    raise SystemExit(main())
