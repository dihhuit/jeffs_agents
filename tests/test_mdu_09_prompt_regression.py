"""Tests for MDU-09 — the prompt regression gate.

The gate is ``scripts/lib/prompt_regression.py``. A golden case is one target
file plus an *ordered* list of exact markers; matching is
``text.find(marker, pos)``, so presence without order is not enough. A case may
also carry ``forbidden`` markers.

Everything here drives the CLI as a subprocess (``sys.executable``) because
that is how CI, the orchestrator pre-commit clause and eval task 04 use it.
Scratch repos are built under ``tmp_path`` and addressed with ``--root``, so the
real tree is never mutated.

Exit-code contract under test: 0 clean, 1 findings/regression, 2 operational
(fail closed). Offline only: no network, no npm/npx, no promptfoo execution.

"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "lib" / "prompt_regression.py"
CASES_FILE = REPO_ROOT / "evals" / "golden" / "cases.json"
BASELINE_FILE = REPO_ROOT / "evals" / "golden" / "baseline.json"
CONFIG = REPO_ROOT / "evals" / "promptfoo.yaml"
DRIVER = REPO_ROOT / "evals" / "promptfoo_driver.sh"

HEX12 = re.compile(r"^[0-9a-f]{12}$")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _run(*args: str, cwd: Path | None = None, env: dict | None = None):
    """Run the gate CLI, returning the completed process."""
    full_env = dict(os.environ)
    if env is not None:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, str(GATE), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd or REPO_ROOT),
        env=full_env,
        timeout=120,
    )


def _run_json(*args: str, **kwargs):
    """Run the gate with ``--json`` and return ``(exit_code, parsed_payload)``."""
    proc = _run(*args, "--json", **kwargs)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:  # pragma: no cover - registers as a failure
        pytest.fail(f"gate did not emit JSON (exit {proc.returncode}): "
                    f"{proc.stdout[:200]!r} {proc.stderr[:200]!r}")
    return proc.returncode, payload


CASE = {
    "id": "c1",
    "target": "prompts/x.md",
    "description": "ordered markers in the target prompt",
    "trace": ["ALPHA first", "BETA second"],
}


def _tree(tmp_path: Path, *, target_text: str = "ALPHA first\nBETA second\n",
          cases: list | None = None, baseline: dict | str | None = None,
          cases_raw: str | None = None) -> Path:
    """Build a scratch repo root with golden cases, a target file and a baseline."""
    root = tmp_path / "root"
    (root / "evals" / "golden").mkdir(parents=True)
    (root / "prompts").mkdir()
    (root / "prompts" / "x.md").write_text(target_text, encoding="utf-8")

    if cases_raw is not None:
        (root / "evals" / "golden" / "cases.json").write_text(cases_raw, encoding="utf-8")
    else:
        payload = {"version": 1, "cases": cases if cases is not None else [dict(CASE)]}
        (root / "evals" / "golden" / "cases.json").write_text(
            json.dumps(payload), encoding="utf-8")

    if baseline is not None:
        text = baseline if isinstance(baseline, str) else json.dumps(baseline)
        (root / "evals" / "golden" / "baseline.json").write_text(text, encoding="utf-8")
    return root


def _empty_bin(tmp_path: Path) -> Path:
    """A PATH entry with no executables in it (deterministic 'nothing installed')."""
    path = tmp_path / "empty-bin"
    path.mkdir(exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# 1. order sensitivity — the core semantic
# ---------------------------------------------------------------------------

def test_in_order_trace_passes(tmp_path):
    root = _tree(tmp_path, baseline={"version": 1, "case_results": {"c1": "pass"}})
    code, payload = _run_json("gate", "--root", str(root))
    assert code == 0
    assert payload["case_results"] == {"c1": "pass"}
    assert payload["regressions"] == []


def test_out_of_order_trace_fails_the_gate(tmp_path):
    """Both markers present, wrong order -> regression, not a pass."""
    root = _tree(
        tmp_path,
        target_text="BETA second\nALPHA first\n",
        baseline={"version": 1, "case_results": {"c1": "pass"}},
    )
    code, payload = _run_json("gate", "--root", str(root))
    assert code == 1
    assert payload["case_results"] == {"c1": "fail"}


def test_ordering_is_strictly_after_the_previous_match(tmp_path):
    """A repeated marker cannot satisfy two consecutive trace positions."""
    case = {
        "id": "dup",
        "target": "prompts/x.md",
        "description": "same marker twice",
        "trace": ["SAME marker", "SAME marker"],
    }
    root = _tree(
        tmp_path,
        target_text="SAME marker\n",
        cases=[case],
        baseline={"version": 1, "case_results": {"dup": "pass"}},
    )
    code, payload = _run_json("gate", "--root", str(root))
    assert code == 1, "one occurrence must not satisfy a two-marker trace"
    assert payload["case_results"] == {"dup": "fail"}


def test_forbidden_marker_fails_an_otherwise_ordered_trace(tmp_path):
    case = dict(CASE, forbidden=["LEGACY phrasing"])
    root = _tree(
        tmp_path,
        target_text="ALPHA first\nBETA second\nLEGACY phrasing\n",
        cases=[case],
        baseline={"version": 1, "case_results": {"c1": "pass"}},
    )
    code, payload = _run_json("gate", "--root", str(root))
    assert code == 1
    assert payload["case_results"] == {"c1": "fail"}


# ---------------------------------------------------------------------------
# 2. case deletion is a regression
# ---------------------------------------------------------------------------

def test_deleting_a_baselined_case_is_detected(tmp_path):
    root = _tree(tmp_path, baseline={
        "version": 1,
        "case_results": {"c1": "pass", "removed-case": "pass"},
    })
    code, payload = _run_json("gate", "--root", str(root))
    assert code == 1
    assert payload["regressions"] == ["removed-case"]
    # the surviving case still passes: deletion, not a broken target
    assert payload["case_results"] == {"c1": "pass"}


def test_adding_a_case_without_baselining_is_only_a_note(tmp_path):
    extra = {"id": "c2", "target": "prompts/x.md", "description": "d",
             "trace": ["ALPHA first", "BETA second"]}
    root = _tree(tmp_path, cases=[dict(CASE), extra],
                 baseline={"version": 1, "case_results": {"c1": "pass"}})
    code, payload = _run_json("gate", "--root", str(root))
    assert code == 0, "new cases must not fail the gate, only be noted"
    assert any("c2" in note for note in payload["notes"])


# ---------------------------------------------------------------------------
# 3. gutted / structurally invalid baseline is operational (exit 2)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "baseline",
    [
        pytest.param({"version": 1, "case_results": {}}, id="empty-case-results"),
        pytest.param({"version": 1, "case_results": []}, id="case-results-is-list"),
        pytest.param({"version": 1, "cases": []}, id="cases-list-replaces-results"),
        pytest.param({"version": 1}, id="missing-case-results"),
        pytest.param({}, id="empty-object"),
        pytest.param("[]", id="json-list"),
        pytest.param("{ not json", id="malformed-json"),
    ],
)
def test_gutted_baseline_is_operational_not_silent(tmp_path, baseline):
    root = _tree(tmp_path, baseline=baseline)
    code, payload = _run_json("gate", "--root", str(root))
    assert code == 2, f"a {baseline!r} baseline must fail closed with exit 2"
    assert payload["case_results"] == {}
    assert payload.get("error")


def test_missing_baseline_is_operational(tmp_path):
    root = _tree(tmp_path)  # no baseline written
    code, payload = _run_json("gate", "--root", str(root))
    assert code == 2
    assert "baseline" in payload["error"]


# ---------------------------------------------------------------------------
# 4. trace with fewer than two markers is an invalid case definition
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("trace", [pytest.param([], id="empty"),
                                   pytest.param(["ALPHA first"], id="one-marker")])
@pytest.mark.parametrize("command", ["cases", "snapshot", "gate"])
def test_short_trace_is_rejected_operationally(tmp_path, trace, command):
    """Shipped contract: <2 markers is an invalid definition -> exit 2, not 1."""
    case = dict(CASE, trace=trace)
    root = _tree(tmp_path, cases=[case], baseline={
        "version": 1, "case_results": {"c1": "pass"}})
    args = [command, "--root", str(root)]
    if command == "snapshot":
        args += ["--out", str(tmp_path / "snap.json")]
    code, payload = _run_json(*args)
    assert code == 2
    assert "at least 2 markers" in payload["error"]


# ---------------------------------------------------------------------------
# 4b. an empty case list is an operational error, not a silent pass
# ---------------------------------------------------------------------------

def test_empty_case_list_is_operational_not_a_pass(tmp_path):
    """Zero cases must fail closed with exit 2, never pass or report findings."""
    root = _tree(tmp_path, cases=[], baseline={
        "version": 1, "case_results": {"c1": "pass"}})
    proc = _run("gate", "--root", str(root))
    assert proc.returncode == 2, (
        "an empty 'cases' list must be an operational error: "
        f"{proc.stdout[:120]!r} {proc.stderr[:120]!r}"
    )
    assert "cases" in (proc.stdout + proc.stderr).lower()


# ---------------------------------------------------------------------------
# 5. path traversal in the case target
# ---------------------------------------------------------------------------

def test_relative_traversal_target_is_refused_and_not_leaked(tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("ALPHA first\nBETA second\n", encoding="utf-8")
    case = dict(CASE, target="../../outside.txt")
    root = _tree(tmp_path, cases=[case], baseline={
        "version": 1, "case_results": {"c1": "pass"}})

    code, payload = _run_json("gate", "--root", str(root))
    assert code != 0, "a target escaping the root must never pass"
    assert code == 2
    assert ".." in payload["error"]
    assert payload["case_results"] == {}
    out = json.dumps(payload)
    assert "ALPHA first" not in out, "out-of-root file content must not be echoed"


# ---------------------------------------------------------------------------
# 6. constrained YAML subset: unsupported shapes -> exit 2
# ---------------------------------------------------------------------------

BAD_YAML = {
    "flow-list": (
        'prompts:\n  - "{{task}}"\nproviders:\n'
        '  - ["exec: bash promptfoo_driver.sh"]\ntests:\n  - description: "d"\n'
    ),
    "flow-map-item": (
        'prompts:\n  - "{{task}}"\nproviders:\n  - "exec: bash promptfoo_driver.sh"\n'
        'tests:\n  - description: "d"\n    vars: {task: evals/tasks/04-prompt-golden-cases}\n'
    ),
    "anchor": (
        "defaults: &shared\n  timeout: 300\nprompts:\n  - \"{{task}}\"\n"
    ),
    "alias": (
        'shared: prompts\nprompts:\n  - *shared\n'
    ),
    "block-scalar-literal": (
        'prompts:\n  - "{{task}}"\nproviders:\n  - "exec: bash promptfoo_driver.sh"\n'
        'tests:\n  - description: |\n      multi line\n'
    ),
    "block-scalar-folded": (
        'prompts:\n  - "{{task}}"\nproviders:\n  -\n    > folded\n'
    ),
    "tag": (
        "prompts: !!str {{task}}\n"
    ),
}


@pytest.mark.parametrize("name", sorted(BAD_YAML))
def test_check_config_rejects_unsupported_yaml_shapes(tmp_path, name):
    cfg = tmp_path / f"{name}.yaml"
    cfg.write_text(BAD_YAML[name], encoding="utf-8")
    proc = _run("check-config", "--config", str(cfg))
    assert proc.returncode == 2, (
        f"{name} must be an operational error, not a validation finding: "
        f"{proc.stdout[:120]!r} {proc.stderr[:120]!r}"
    )
    assert "unsupported shape" in (proc.stdout + proc.stderr)
    assert re.search(r"line \d+", proc.stdout + proc.stderr), "rejection names a line"


def test_check_config_missing_config_is_operational(tmp_path):
    proc = _run("check-config", "--config", str(tmp_path / "nope.yaml"))
    assert proc.returncode == 2


def test_check_config_structural_findings_exit_1_not_2(tmp_path):
    """A parseable config with too few tests is a finding (1), distinct from a shape error (2)."""
    cfg = tmp_path / "thin.yaml"
    cfg.write_text(
        'prompts:\n  - "{{task}}"\nproviders:\n  - "exec: bash promptfoo_driver.sh"\n'
        'tests:\n  - description: "only one"\n    vars:\n'
        "      task: evals/tasks/04-prompt-golden-cases\n"
        "    assert:\n      - type: contains\n        value: PASS\n",
        encoding="utf-8",
    )
    proc = _run("check-config", "--config", str(cfg))
    assert proc.returncode == 1
    assert "need >= 3" in proc.stdout


# ---------------------------------------------------------------------------
# 7. offline check-config on the shipped config
# ---------------------------------------------------------------------------

def test_check_config_offline_on_shipped_config(tmp_path):
    """Exit 0 on the shipped config; no promptfoo/npx is ever launched."""
    sentinel = tmp_path / "invoked.marker"
    shim_dir = tmp_path / "shim-bin"
    shim_dir.mkdir()
    for name in ("promptfoo", "npx", "node", "npm"):
        shim = shim_dir / name
        shim.write_text(f"#!/bin/sh\necho {name} >> {sentinel}\nexit 0\n", encoding="utf-8")
        shim.chmod(0o755)

    proc = _run("check-config", env={"PATH": str(shim_dir)})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS check-config" in proc.stdout
    assert "promptfoo-live" not in proc.stdout, "offline mode must not probe the CLI"
    assert not sentinel.exists(), "offline mode must not execute promptfoo/npx/node"


# ---------------------------------------------------------------------------
# 8. --live SKIP path when promptfoo is genuinely unavailable
# ---------------------------------------------------------------------------

def test_live_check_reports_skip_without_promptfoo(tmp_path):
    proc = _run("check-config", "--live", env={"PATH": str(_empty_bin(tmp_path))})
    assert proc.returncode == 0, "absence of promptfoo must not fail the gate"
    assert "SKIP promptfoo-live" in proc.stdout
    assert "PASS promptfoo-live" not in proc.stdout
    assert "FAIL promptfoo-live" not in proc.stdout
    assert "promptfoo CLI not on PATH" in proc.stdout


# ---------------------------------------------------------------------------
# 9. promptfoo config binding (static, offline)
# ---------------------------------------------------------------------------

def test_promptfoo_config_binds_tasks_to_exec_provider():
    text = CONFIG.read_text(encoding="utf-8")
    import prompt_regression  # conftest puts scripts/lib on sys.path

    config = prompt_regression.parse_promptfoo_config(text)

    assert config["prompts"] == ["{{task}}"]

    providers = config["providers"]
    assert providers, "at least one provider"
    for provider in providers:
        assert isinstance(provider, str) and provider.startswith("exec:")
        assert "promptfoo_driver.sh" in provider

    tests = config["tests"]
    assert len(tests) >= 3
    for i, test in enumerate(tests):
        task = test["vars"]["task"]
        assert re.match(r"^evals/tasks/[A-Za-z0-9._-]+$", task), task
        driver = REPO_ROOT / task / "driver.sh"
        assert driver.is_file(), f"tests[{i}] points at a missing driver: {driver}"
        assert os.access(driver, os.X_OK), f"{driver} is not executable"
        assert test["assert"], f"tests[{i}] has no assertions"
        assert test["assert"][0]["type"] in prompt_regression.ASSERT_TYPES


def test_promptfoo_driver_maps_argument_to_task_driver():
    text = DRIVER.read_text(encoding="utf-8")
    assert "tasks/${task##*/}/driver.sh" in text
    assert os.access(DRIVER, os.X_OK), "the exec provider invokes this script directly"


def test_promptfoo_driver_runs_a_task_offline():
    """The dispatcher really reaches tasks/<name>/driver.sh (no promptfoo involved)."""
    proc = subprocess.run(
        ["bash", str(DRIVER), "evals/tasks/04-prompt-golden-cases"],
        capture_output=True, text=True, cwd=str(REPO_ROOT / "evals"), timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS prompt-golden-cases" in proc.stdout


def test_promptfoo_driver_rejects_unknown_task():
    proc = subprocess.run(
        ["bash", str(DRIVER), "evals/tasks/does-not-exist"],
        capture_output=True, text=True, cwd=str(REPO_ROOT / "evals"), timeout=60,
    )
    assert proc.returncode == 1
    assert "no driver" in proc.stdout


# ---------------------------------------------------------------------------
# 10. committed golden cases are verbatim, unique and in-root
# ---------------------------------------------------------------------------

def test_committed_golden_cases_are_verbatim_and_non_vacuous():
    data = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    assert data["version"] == 1
    cases = data["cases"]
    assert cases, "the case set must not be empty"

    root = REPO_ROOT.resolve()
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids)), "duplicate case ids"

    for case in cases:
        case_id = case["id"]
        target = case["target"]
        assert ".." not in Path(target).parts, f"{case_id}: target escapes the root"
        assert not Path(target).is_absolute(), f"{case_id}: absolute target"
        target_path = (REPO_ROOT / target).resolve()
        assert target_path.is_relative_to(root), f"{case_id}: target outside the repo"
        assert target_path.is_file(), f"{case_id}: missing target {target}"

        text = target_path.read_text(encoding="utf-8")
        trace = case["trace"]
        assert len(trace) >= 2, f"{case_id}: a one-marker trace is vacuous"
        for marker in trace:
            assert marker, f"{case_id}: empty marker"
            occurrences = text.count(marker)
            assert occurrences == 1, (
                f"{case_id}: marker occurs {occurrences}x, expected exactly 1: "
                f"{marker!r} — uniqueness is what makes the ordered trace meaningful"
            )


def test_committed_golden_cases_match_their_targets_by_running_gate():
    proc = _run("gate", "--json")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["case_results"]
    assert all(result == "pass" for result in payload["case_results"].values())
    assert payload["regressions"] == []


# ---------------------------------------------------------------------------
# 11. baseline provenance
# ---------------------------------------------------------------------------

def test_baseline_provenance_and_shape():
    baseline = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    assert baseline["version"] == 1
    assert isinstance(baseline["case_results"], dict) and baseline["case_results"]
    assert all(result == "pass" for result in baseline["case_results"].values())
    assert HEX12.match(baseline["source_commit"]), (
        f"source_commit must be a 12-char short SHA: {baseline['source_commit']!r}"
    )
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", baseline["generated_at"])

    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))["cases"]
    case_ids = {case["id"] for case in cases}
    missing = case_ids - set(baseline["case_results"])
    assert not missing, f"cases not covered by the baseline: {sorted(missing)}"


# ---------------------------------------------------------------------------
# 12. exit-code contract, table driven
# ---------------------------------------------------------------------------

def test_exit_code_contract(tmp_path):
    clean = _tree(tmp_path / "clean", baseline={
        "version": 1, "case_results": {"c1": "pass"}})
    regressed = _tree(tmp_path / "regressed", target_text="nothing here\n",
                      baseline={"version": 1, "case_results": {"c1": "pass"}})
    deleted = _tree(tmp_path / "deleted", baseline={
        "version": 1, "case_results": {"c1": "pass", "gone": "pass"}})
    unreachable = tmp_path / "unreachable"
    malformed = _tree(tmp_path / "malformed", cases_raw="{ not json",
                       baseline={"version": 1, "case_results": {"c1": "pass"}})

    table = [
        ("clean", ["gate", "--root", str(clean)], 0),
        ("regressed", ["gate", "--root", str(regressed)], 1),
        ("deleted-case", ["gate", "--root", str(deleted)], 1),
        ("missing-root", ["gate", "--root", str(unreachable)], 2),
        ("malformed-cases", ["gate", "--root", str(malformed)], 2),
        ("cases-missing-root", ["cases", "--root", str(unreachable)], 2),
    ]
    for name, args, expected in table:
        code, _payload = _run_json(*args)
        assert code == expected, f"{name}: expected exit {expected}, got {code}"


# ---------------------------------------------------------------------------
# snapshot / diff round trip (used by the "prompt change protocol")
# ---------------------------------------------------------------------------

def test_diff_flags_a_pass_to_fail_regression(tmp_path):
    root = _tree(tmp_path, baseline={"version": 1, "case_results": {"c1": "pass"}})
    before, after = tmp_path / "before.json", tmp_path / "after.json"

    code, _ = _run_json("snapshot", "--root", str(root), "--out", str(before))
    assert code == 0

    (root / "prompts" / "x.md").write_text("BETA second\nALPHA first\n", encoding="utf-8")
    code, _ = _run_json("snapshot", "--root", str(root), "--out", str(after))
    assert code == 1, "the snapshot for a failing case reports the failure"

    code, payload = _run_json("diff", "--before", str(before), "--after", str(after))
    assert code == 1
    assert payload["regressions"] == ["c1"]


def test_diff_is_clean_when_nothing_changed(tmp_path):
    root = _tree(tmp_path, baseline={"version": 1, "case_results": {"c1": "pass"}})
    snap = tmp_path / "snap.json"
    assert _run_json("snapshot", "--root", str(root), "--out", str(snap))[0] == 0
    code, payload = _run_json("diff", "--before", str(snap), "--after", str(snap))
    assert code == 0
    assert payload["regressions"] == []


# ---------------------------------------------------------------------------
# Contract tests for gaps that used to be recorded as xfail. The underlying
# defects are fixed, so these are ordinary passing tests (do not weaken: they
# assert the contract the MDU requires).
# ---------------------------------------------------------------------------

def test_absolute_target_outside_root_is_refused(tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("ALPHA first\nBETA second\n", encoding="utf-8")
    case = dict(CASE, target=str(outside))
    root = _tree(tmp_path, cases=[case], baseline={
        "version": 1, "case_results": {"c1": "pass"}})

    code, payload = _run_json("gate", "--root", str(root))
    assert code == 2, f"absolute target must be refused, got exit {code}"
    assert "ALPHA first" not in json.dumps(payload)


def test_check_config_rejects_tab_indentation(tmp_path):
    item = (
        '\t- description: "d{n}"\n\t  vars:\n'
        "\t    task: evals/tasks/04-prompt-golden-cases\n"
        "\t  assert:\n\t    - type: contains\n\t      value: PASS\n"
    )
    cfg = tmp_path / "tabs.yaml"
    cfg.write_text(
        'prompts:\n\t- "{{task}}"\nproviders:\n\t- "exec: bash promptfoo_driver.sh"\n'
        "tests:\n" + "".join(item.format(n=i) for i in (1, 2, 3)),
        encoding="utf-8",
    )
    proc = _run("check-config", "--config", str(cfg))
    assert proc.returncode == 2, (
        "tab indentation is invalid YAML; a green offline check is a false green"
    )
