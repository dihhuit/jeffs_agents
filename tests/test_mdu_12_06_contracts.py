"""Regression contracts for MDU-12 (Human Approval Gates) and MDU-06 wiring.

Cheap dependency-free checks that guard the prompts ↔ grok mirror gate
wording, the README → docs/autonomy.md link, the MCP example's JSON validity,
and the repo-health eval task's file layout against accidental drift.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PROMPTS_ORCHESTRATOR = REPO_ROOT / "prompts" / "orchestrator.md"
GROK_ORCHESTRATOR = REPO_ROOT / "grok" / "agents" / "orchestrator.md"
README = REPO_ROOT / "README.md"
MCP_EXAMPLE = REPO_ROOT / "examples" / "mcp" / "opencode.mcp.json.example"
REPO_HEALTH_TASK = REPO_ROOT / "evals" / "tasks" / "01-repo-health"


def _gate_lines(text: str) -> list[str]:
    """All "Require human approval..." gate bullets in an orchestrator prompt."""
    return [
        line.strip()
        for line in text.splitlines()
        if "Require human approval" in line
    ]


def test_human_approval_gates_present_and_identical_in_both_orchestrators() -> None:
    canonical = PROMPTS_ORCHESTRATOR.read_text(encoding="utf-8")
    mirror = GROK_ORCHESTRATOR.read_text(encoding="utf-8")

    assert "Human Approval Gates" in canonical
    assert "Human Approval Gates" in mirror

    canonical_gates = _gate_lines(canonical)
    mirror_gates = _gate_lines(mirror)
    # Each file must carry the full 4-gate set, and the wording must be
    # identical between the canonical prompt and the grok mirror.
    assert len(canonical_gates) == 4
    assert canonical_gates == mirror_gates
    assert "pushing to protected branches" in canonical_gates[0]
    assert "deploying non-green MDUs to production" in canonical_gates[1]
    assert "destructive operations" in canonical_gates[2]
    assert "exceeding 3 fix-retries" in canonical_gates[3]


def test_readme_links_autonomy_doc() -> None:
    text = README.read_text(encoding="utf-8")
    assert "docs/autonomy.md" in text


def test_mcp_example_is_valid_json() -> None:
    data = json.loads(MCP_EXAMPLE.read_text(encoding="utf-8"))
    assert "mcp" in data
    assert "agent" in data


def test_repo_health_eval_task_files_exist() -> None:
    task_md = REPO_HEALTH_TASK / "task.md"
    driver = REPO_HEALTH_TASK / "driver.sh"
    assert task_md.is_file()
    assert driver.is_file()
    assert driver.read_text(encoding="utf-8").lstrip().startswith("#!")