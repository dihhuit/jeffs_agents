#!/usr/bin/env python3
"""Live model-health probe and deploy gate for the paid model set (MDU-40).

``opencode models`` lists a model as ``active`` long after upstream has killed
it (mdu-37: 12 agents on a dead ``opencode/nemotron-3-ultra-free``). This script
runs one real inference per model and records the result, so a deploy can be
gated on proof of life rather than on a listing.

The canonical ``opencode.json`` is the single source of truth: every distinct
model it declares is a hard probe target, grouped by provider
(``opencode-go/*`` and ``xai/*``).

Usage:
    probe_models.py --refresh | --gate | --refresh --gate

    --refresh                 probe every model in the config and rewrite the report
    --gate                    evaluate the report; exit 1 when red
    --config <file>           opencode.json under test
                              (default: <repo>/build/opencode.json)
    --report <file>           report (default: <repo>/config/model-probe-report.json)
    --include-xai             accepted no-op; xai/* probing is always on
    --timeout 90              per-attempt timeout in seconds
    --attempts 2              total attempts per model (permanent errors: 1)
    --max-workers 2           models probed in parallel
    --max-age-days 7          gate freshness window (0 disables the age rule only)
    --max-runtime-s 300       whole-refresh budget; remainder is ``skipped``
    --cli opencode            CLI binary used for ``run -m <model> "..."``

Exit codes (same 0/1/2 convention as ``resume_block.py``):

    0  refresh: report written (even if models failed) · gate: green
    1  gate: red — report missing/stale/mismatched or a target is not ok
    2  usage/environment error: no CLI, bad config, unwritable report, bad args
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "build" / "opencode.json"
DEFAULT_REPORT = REPO_ROOT / "config" / "model-probe-report.json"

SCHEMA_VERSION = 1
PROMPT = "Reply with exactly: OK"
BOOTSTRAP = (
    "python3 scripts/lib/probe_models.py --refresh --gate "
    "--config build/opencode.json"
)
RETRY_SLEEP_S = 1.0
ERROR_MAX_CHARS = 200

#: CSI/OSC ANSI escape sequences emitted by the CLI's colour output. Captured
#: stderr like ``"\x1b[0m"`` is pure formatting and must never become the
#: ``error`` recorded in the report.
ANSI_RE = re.compile(r"\x1b(?:\[[0-9;?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[@-Z\\-_])")

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
# config + report helpers
# ---------------------------------------------------------------------------

def load_config(path: Path) -> dict:
    """Load the OpenCode config under test; raise ``ProbeError`` when unusable."""
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProbeError(f"opencode config not found: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ProbeError(f"opencode config unreadable: {path} ({exc})") from exc
    if not isinstance(config, dict):
        raise ProbeError(f"opencode config is not a JSON object: {path}")
    agents = config.get("agents")
    if not isinstance(agents, dict):
        raise ProbeError(f"opencode config has no agents object: {path}")
    return config


def collect_models(config_path: Path) -> dict[str, list[str]]:
    """Group the config's agent models by provider prefix, deduped and sorted.

    A paid config yields ``{"opencode-go": [...], "xai": [...]}``. The config
    is the single source of truth (MDU-40): every distinct model is a hard
    probe target, so any remap or agent add/remove re-reds a stale report.
    """
    groups: dict[str, set[str]] = {}
    for definition in (load_config(config_path).get("agents") or {}).values():
        if not isinstance(definition, dict):
            continue
        model = definition.get("model")
        if not isinstance(model, str) or "/" not in model:
            continue
        provider = model.split("/", 1)[0]
        groups.setdefault(provider, set()).add(model)
    return {provider: sorted(models) for provider, models in sorted(groups.items())}


def config_sha256(config_path: Path) -> str:
    """Hash the config's meaning, not its bytes: sorted ``agent=model`` lines.

    Re-indenting or re-ordering the config hashes identically; adding,
    removing, or remapping an agent changes the hash and re-reds the gate.
    """
    agents = load_config(config_path).get("agents") or {}
    pairs = sorted(
        f"{name}={definition.get('model')}"
        for name, definition in agents.items()
        if isinstance(definition, dict) and isinstance(definition.get("model"), str)
    )
    return hashlib.sha256("\n".join(pairs).encode("utf-8")).hexdigest()


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

def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences so report errors carry readable text only."""
    return ANSI_RE.sub("", text or "")


def _first_error_line(returncode: int, stdout: str, stderr: str) -> str:
    """Return the most useful single-line error for a failed attempt."""
    for text in (stderr, stdout):
        for line in strip_ansi(text).splitlines():
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
            stdout = strip_ansi(proc.stdout or "")
            stderr = strip_ansi(proc.stderr or "")
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


def _run_plan(
    plan: list[tuple[str, str]],
    *,
    cli: str,
    timeout: int,
    attempts: int,
    max_workers: int,
    max_runtime_s: int,
    runner=subprocess.run,
) -> list[dict]:
    """Probe a ``(model, role)`` plan honouring the refresh budget, stable order."""
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
    return results


def build_results(
    models: list[str],
    *,
    cli: str,
    timeout: int,
    attempts: int,
    max_workers: int,
    max_runtime_s: int,
    runner=subprocess.run,
) -> list[dict]:
    """Probe every ``opencode-go/*`` target; return results in stable order."""
    return _run_plan(
        [(model, "target") for model in models],
        cli=cli,
        timeout=timeout,
        attempts=attempts,
        max_workers=max_workers,
        max_runtime_s=max_runtime_s,
        runner=runner,
    )


def build_xai_results(
    xai_models: list[str],
    *,
    cli: str,
    timeout: int,
    attempts: int,
    max_workers: int,
    max_runtime_s: int,
    runner=subprocess.run,
) -> list[dict]:
    """Probe the ``xai/*`` targets (MDU-42).

    Same exact-match OK rule as the Go targets; entries carry ``role: "xai"``
    and land in the report's distinct ``xai_results`` section.
    """
    return _run_plan(
        [(model, "xai") for model in xai_models],
        cli=cli,
        timeout=timeout,
        attempts=attempts,
        max_workers=max_workers,
        max_runtime_s=max_runtime_s,
        runner=runner,
    )


def _print_results(results: list[dict]) -> None:
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


def _counts(results: list[dict]) -> str:
    tally = {"ok": 0, "fail": 0, "skipped": 0}
    for result in results:
        tally[result["status"]] = tally.get(result["status"], 0) + 1
    return (
        f"{tally['ok']} ok, {tally['fail']} fail, "
        f"{tally['skipped']} skipped"
    )


def refresh_report(
    config_path: Path,
    report_path: Path,
    *,
    cli: str,
    timeout: int,
    attempts: int,
    max_workers: int,
    max_runtime_s: int,
    runner=subprocess.run,
) -> int:
    """Probe every model in the config and rewrite the report.

    Returns 0 when the report was written, 2 when it could not be.
    """
    groups = collect_models(config_path)
    results = build_results(
        groups.get("opencode-go", []),
        cli=cli,
        timeout=timeout,
        attempts=attempts,
        max_workers=max_workers,
        max_runtime_s=max_runtime_s,
        runner=runner,
    )
    xai_results = build_xai_results(
        groups.get("xai", []),
        cli=cli,
        timeout=timeout,
        attempts=attempts,
        max_workers=max_workers,
        max_runtime_s=max_runtime_s,
        runner=runner,
    )
    report: dict = {
        "schema_version": SCHEMA_VERSION,
        "probed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "refresh",
        "cli": cli,
        "timeout_s": timeout,
        "config_path": _portable_path(config_path),
        "config_sha256": config_sha256(config_path),
        "results": results,
        "xai_results": xai_results,
    }
    try:
        write_report(report_path, report)
    except OSError as exc:
        print(f"  [error] cannot write report {report_path}: {exc}", file=sys.stderr)
        return 2

    _print_results(results)
    _print_results(xai_results)
    print(
        f"  [info]  opencode-go: {len(results)} probed ({_counts(results)}); "
        f"xai: {len(xai_results)} probed ({_counts(xai_results)})"
    )
    print(f"  [info]  report → {report_path}")
    return 0


# ---------------------------------------------------------------------------
# gate
# ---------------------------------------------------------------------------

def _target_offence(model: str, entries: list[dict], label: str) -> str | None:
    """Grade one hard target: exactly one ``ok`` entry, else name the failure."""
    if not entries:
        return f"{label} '{model}' missing from the report"
    ok_entries = [entry for entry in entries if entry.get("status") == "ok"]
    if len(ok_entries) == 1:
        return None
    if len(entries) > 1:
        return f"{label} '{model}' has {len(entries)} results, need exactly one ok"
    status = entries[0].get("status")
    error = entries[0].get("error")
    detail = f" ({error})" if error else ""
    return f"{label} '{model}' is {status}{detail}"


def gate_offences(
    report_path: Path,
    config_path: Path,
    *,
    max_age_days: int,
    now: datetime | None = None,
) -> tuple[list[str], list[str]]:
    """Evaluate the report against the config; return ``(offences, warnings)``.

    Offences are red (exit 1); warnings never fail the gate. Rule 1 returns
    immediately because no later rule can be trusted against an absent or
    malformed report.
    """
    offences: list[str] = []
    warnings: list[str] = []
    groups = collect_models(config_path)

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

    # 2. the config the report describes is still the config in this tree.
    expected_hash = config_sha256(config_path)
    reported_hash = report.get("config_sha256")
    if not reported_hash:
        offences.append(
            "report cache predates MDU-40 schema; run "
            f"--refresh --gate --config {config_path}"
        )
    elif reported_hash != expected_hash:
        offences.append(
            "config changed since last probe "
            f"(report {str(reported_hash)[:12]}…, "
            f"current {expected_hash[:12]}…)"
        )

    # 3. freshness (--max-age-days 0 disables only this rule).
    age = now - probed_at
    if max_age_days and max_age_days > 0 and age > timedelta(days=max_age_days):
        offences.append(
            f"report is stale: {age.total_seconds() / 86400:.1f} day(s) old, "
            f"max {max_age_days} day(s)"
        )

    # 4. every opencode-go target needs exactly one ok result.
    by_model: dict[str, list[dict]] = {}
    for entry in report.get("results") or []:
        if isinstance(entry, dict) and isinstance(entry.get("model"), str):
            by_model.setdefault(entry["model"], []).append(entry)
    for model in groups.get("opencode-go", []):
        offence = _target_offence(model, by_model.get(model, []), "target")
        if offence:
            offences.append(offence)

    # 5. every xai target needs exactly one ok result too (MDU-42).
    xai_models = groups.get("xai", [])
    if xai_models:
        xai_results = report.get("xai_results")
        if not isinstance(xai_results, list):
            offences.append(
                "report has no xai_results section "
                "(re-run probe_models.py --refresh --config <opencode.json>)"
            )
            xai_results = []
        xai_by_model: dict[str, list[dict]] = {}
        for entry in xai_results:
            if isinstance(entry, dict) and isinstance(entry.get("model"), str):
                xai_by_model.setdefault(entry["model"], []).append(entry)
        for model in xai_models:
            offence = _target_offence(
                model, xai_by_model.get(model, []), "xai target"
            )
            if offence:
                offences.append(offence)

    # 6. models outside the paid provider set warn only (the validator fails
    # closed on them; the probe gate reports what it did not measure).
    for provider, models in groups.items():
        if provider in ("opencode-go", "xai"):
            continue
        for model in models:
            warnings.append(
                f"config ref '{model}' is outside the paid probe set "
                "(not probed; validator rejects it)"
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
            "Probe the paid model set of the canonical opencode.json with a live "
            "inference and gate deploys on the resulting report."
        ),
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="probe every model in the config and rewrite the report (exit 0 when written)",
    )
    parser.add_argument(
        "--gate",
        action="store_true",
        help="evaluate the report against the config; exit 1 when red",
    )
    parser.add_argument(
        "--config",
        metavar="file",
        default=str(DEFAULT_CONFIG),
        help=f"opencode.json under test (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--report",
        metavar="file",
        default=str(DEFAULT_REPORT),
        help=f"probe report (default: {DEFAULT_REPORT})",
    )
    parser.add_argument(
        "--include-xai",
        action="store_true",
        help=(
            "deprecated no-op (MDU-40): xai/* targets are always probed and "
            "graded; kept so existing scripts keep working"
        ),
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
    config_path = Path(args.config)

    if shutil.which(args.cli) is None:
        print(
            f"  [error] '{args.cli}' CLI not on PATH; model-health probe cannot run "
            "(exit 2, no report written)",
            file=sys.stderr,
        )
        return 2

    try:
        collect_models(config_path)
    except ProbeError as exc:
        print(f"  [error] {exc}", file=sys.stderr)
        return 2

    if args.refresh:
        exit_code = refresh_report(
            config_path,
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
            config_path,
            max_age_days=args.max_age_days,
        )
    except ProbeError as exc:
        print(f"  [error] {exc}", file=sys.stderr)
        return 2
    return _print_gate_verdict(offences, warnings)


if __name__ == "__main__":
    raise SystemExit(main())
