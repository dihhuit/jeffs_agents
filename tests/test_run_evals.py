"""Tests for scripts/lib/run_evals.py.

Covers ``parse_task`` (frontmatter parsing + defaults + missing-file error),
``run_task`` (exit-code interpretation, timeout, missing driver, result
manifest with the run_ledger-compatible fields), ``_parse_test_counts``,
``summarize_results`` / ``format_summary_table``, and the list/run/summary
CLI paths of ``main``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import run_evals

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _task_dir(
    tmp_path: Path,
    name: str = "demo",
    driver: str | None = "exit 0",
    frontmatter: dict | None = None,
) -> Path:
    """Create a task dir with task.md and (optionally) driver.sh."""
    task_dir = tmp_path / name
    task_dir.mkdir(parents=True)
    fm = frontmatter if frontmatter is not None else {
        "name": name,
        "description": "demo task",
        "trigger": "ci",
        "timeout_minutes": 5,
        "expect": ["gate A", "gate B"],
    }
    lines = ["---"]
    for key, value in fm.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  - {item}" for item in value)
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {name}")
    (task_dir / "task.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if driver is not None:
        (task_dir / "driver.sh").write_text(driver + "\n", encoding="utf-8")
    return task_dir


def _write_result(results_dir: Path, name: str, **overrides) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "task": name,
        "status": "pass",
        "duration_seconds": 1.0,
        "phases": [],
        "verification": {"build": True},
    }
    data.update(overrides)
    path = results_dir / f"{name}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# parse_task
# ---------------------------------------------------------------------------

def test_parse_task_full_frontmatter(tmp_path: Path) -> None:
    task_dir = _task_dir(tmp_path, name="demo")
    task = run_evals.parse_task(task_dir)
    assert task["task_dir"] == str(task_dir)
    assert task["name"] == "demo"
    assert task["description"] == "demo task"
    assert task["trigger"] == "ci"
    assert task["timeout_minutes"] == 5
    assert task["expect"] == ["gate A", "gate B"]
    assert "# demo" in task["body"]


def test_parse_task_missing_frontmatter_uses_defaults(tmp_path: Path) -> None:
    task_dir = tmp_path / "plain"
    task_dir.mkdir()
    (task_dir / "task.md").write_text("# plain\n\nbody text here\n", encoding="utf-8")
    task = run_evals.parse_task(task_dir)
    assert task["name"] == "plain"
    assert task["description"] == ""
    assert task["trigger"] == "manual"
    assert task["timeout_minutes"] == 10
    assert task["expect"] == []
    assert "# plain" in task["body"]
    assert "body text here" in task["body"]


def test_parse_task_missing_task_md_raises(tmp_path: Path) -> None:
    task_dir = tmp_path / "empty"
    task_dir.mkdir()
    with pytest.raises(FileNotFoundError):
        run_evals.parse_task(task_dir)


def test_parse_task_coerces_scalars(tmp_path: Path) -> None:
    task_dir = _task_dir(
        tmp_path,
        name="coerced",
        frontmatter={
            "name": "coerced",
            "timeout_minutes": "15",
            "trigger": "on_pr",
            "expect": ["x"],
        },
    )
    task = run_evals.parse_task(task_dir)
    assert task["timeout_minutes"] == 15
    assert task["trigger"] == "on_pr"


# ---------------------------------------------------------------------------
# run_task
# ---------------------------------------------------------------------------

def test_run_task_driver_exit_zero_pass(tmp_path: Path) -> None:
    task_dir = _task_dir(tmp_path, driver="exit 0")
    manifest = run_evals.run_task(run_evals.parse_task(task_dir), tmp_path / "results")
    assert manifest["status"] == "pass"
    assert manifest["phases"][0]["notes"] == "driver exited 0"
    assert manifest["verification"]["build"] is True
    assert manifest["verification"]["qa_grade"] == "PASS"
    assert manifest["verification"]["ci_green"] is True


def test_run_task_driver_exit_three_fail(tmp_path: Path) -> None:
    task_dir = _task_dir(tmp_path, driver="exit 3")
    manifest = run_evals.run_task(run_evals.parse_task(task_dir), tmp_path / "results")
    assert manifest["status"] == "fail"
    assert manifest["phases"][0]["notes"] == "driver exited 3"
    assert manifest["verification"]["build"] is False
    assert manifest["verification"]["qa_grade"] == "FAIL"


def test_run_task_timeout_is_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Minutes-only timeout granularity makes real timeouts slow; simulate the
    # GNU coreutils `timeout` returncode (124) instead.
    task_dir = _task_dir(
        tmp_path, name="slow", frontmatter={"name": "slow", "timeout_minutes": 1}
    )

    class FakeProc:
        returncode = run_evals.TIMEOUT_RETURNCODE
        stdout = ""
        stderr = ""

    monkeypatch.setattr(run_evals.subprocess, "run", lambda *a, **kw: FakeProc())
    manifest = run_evals.run_task(run_evals.parse_task(task_dir), tmp_path / "results")
    assert manifest["status"] == "fail"
    assert "timed out after" in manifest["phases"][0]["notes"]


def test_run_task_oserror_launch_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_dir = _task_dir(tmp_path)

    def boom(*args, **kwargs):
        raise OSError("timeout binary unavailable")

    monkeypatch.setattr(run_evals.subprocess, "run", boom)
    manifest = run_evals.run_task(run_evals.parse_task(task_dir), tmp_path / "results")
    assert manifest["status"] == "fail"
    assert "could not launch driver" in manifest["phases"][0]["notes"]


def test_run_task_missing_driver_fail(tmp_path: Path) -> None:
    task_dir = _task_dir(tmp_path, driver=None)
    manifest = run_evals.run_task(run_evals.parse_task(task_dir), tmp_path / "results")
    assert manifest["status"] == "fail"
    assert manifest["phases"][0]["notes"] == "no driver.sh in task directory"
    assert manifest["duration_seconds"] == 0.0


def test_run_task_writes_manifest_with_required_fields(tmp_path: Path) -> None:
    task_dir = _task_dir(tmp_path, driver="echo PASS demo; exit 0")
    results_dir = tmp_path / "results"
    run_evals.run_task(run_evals.parse_task(task_dir), results_dir)
    manifests = list(results_dir.glob("*.json"))
    assert len(manifests) == 1
    data = json.loads(manifests[0].read_text(encoding="utf-8"))
    for field in (
        "status",
        "started_at",
        "completed_at",
        "phases",
        "verification",
        "duration_seconds",
    ):
        assert field in data, f"manifest missing '{field}'"
    assert data["status"] == "pass"
    assert isinstance(data["duration_seconds"], (int, float))
    assert data["started_at"].endswith("Z")
    assert isinstance(data["phases"], list) and data["phases"]
    assert data["verification"]["tests_passed"] == 0


# ---------------------------------------------------------------------------
# _parse_test_counts
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "output, expected",
    [
        ("87 passed in 0.26s", (87, 87)),
        ("1 failed, 86 passed in 1.02s", (86, 87)),
        ("12 passed, 1 failed, 1 error in 2.5s", (12, 13)),
        ("no pytest summary here", (0, 0)),
        ("", (0, 0)),
    ],
)
def test_parse_test_counts(output: str, expected: tuple[int, int]) -> None:
    assert run_evals._parse_test_counts(output) == expected


# ---------------------------------------------------------------------------
# summarize_results
# ---------------------------------------------------------------------------

def test_summarize_results_counts_pass_and_fail(tmp_path: Path) -> None:
    results_dir = tmp_path / "results"
    _write_result(results_dir, "a", status="pass", duration_seconds=1.2)
    _write_result(results_dir, "b", status="pass", duration_seconds=0.8)
    _write_result(results_dir, "c", status="fail", duration_seconds=2.0)
    results = run_evals.summarize_results(results_dir)
    assert len(results) == 3
    statuses = [data["status"] for data in results]
    assert statuses.count("pass") == 2
    assert statuses.count("fail") == 1


def test_summarize_results_empty_and_missing_dirs_no_crash(tmp_path: Path) -> None:
    assert run_evals.summarize_results(tmp_path / "missing") == []
    empty = tmp_path / "empty"
    empty.mkdir()
    assert run_evals.summarize_results(empty) == []
    assert run_evals.format_summary_table([]) == "no eval results found"


def test_summarize_results_skips_corrupt_json(tmp_path: Path) -> None:
    results_dir = tmp_path / "results"
    _write_result(results_dir, "ok", status="pass")
    (results_dir / "broken.json").write_text("{ not json", encoding="utf-8")
    results = run_evals.summarize_results(results_dir)
    assert len(results) == 1
    assert results[0]["task"] == "ok"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_list_shows_repo_health(capsys: pytest.CaptureFixture) -> None:
    code = run_evals.main(["list", str(REPO_ROOT / "evals" / "tasks")])
    out = capsys.readouterr().out
    assert code == 0
    assert "repo-health" in out
    assert "description:" in out
    assert "timeout_minutes: 5" in out


def test_cli_run_passing_task_exit_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    task_dir = _task_dir(tmp_path, name="demo", driver="exit 0")
    code = run_evals.main(
        ["run", str(task_dir), "--results-dir", str(tmp_path / "results")]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "[pass]" in out


def test_cli_run_failing_task_exit_one(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    task_dir = _task_dir(tmp_path, name="demo", driver="exit 1")
    code = run_evals.main(
        ["run", str(task_dir), "--results-dir", str(tmp_path / "results")]
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "[fail]" in out


def test_cli_run_missing_task_md_exit_one(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    task_dir = tmp_path / "no-task"
    task_dir.mkdir()
    code = run_evals.main(["run", str(task_dir)])
    assert code == 1
    assert "no task.md" in capsys.readouterr().err


def test_cli_summary_shows_table_rows(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    results_dir = tmp_path / "results"
    _write_result(results_dir, "demo", status="pass", duration_seconds=1.5)
    code = run_evals.main(["summary", str(results_dir)])
    out = capsys.readouterr().out
    assert code == 0
    assert "task" in out
    assert "demo" in out
    assert "pass" in out
    assert "1.5s" in out