#!/usr/bin/env python3
"""MDU-45 tests: register base `grok-review`, grok-registry census, docs refresh."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

import validate

REPO = Path(__file__).resolve().parent.parent
OPENCODE_JSON = REPO / "opencode.json"
PROMPT = REPO / "prompts" / "grok-review.md"
GROK_PROFILE = REPO / "grok" / "agents" / "grok-review.md"
README = REPO / "README.md"
BACKLOG = REPO / "FEATURE_BACKLOG.md"
MODEL_REGISTRY_DOC = REPO / "docs" / "model-registry.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config() -> dict:
    return json.loads(OPENCODE_JSON.read_text(encoding="utf-8"))


def _write_grok_profile(build: Path, name: str, model: str = "grok-build-0.1") -> Path:
    agents = build / "grok" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    profile = agents / f"{name}.md"
    profile.write_text(
        f"---\nname: {name}\nmodel: {model}\ndescription: \"synthetic\"\n---\n",
        encoding="utf-8",
    )
    return profile


def _write_config(build: Path, agents: dict | None = None) -> None:
    build.mkdir(parents=True, exist_ok=True)
    config = {
        "default_agent": "orchestrator",
        "agents": agents or {},
    }
    (build / "opencode.json").write_text(json.dumps(config), encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Registry entry pins
# ---------------------------------------------------------------------------


def test_grok_review_registered() -> None:
    agents = _config()["agents"]
    assert "grok-review" in agents
    entry = agents["grok-review"]
    assert entry["mode"] == "subagent"
    assert entry["model"] == "xai/grok-build-0.1"
    assert entry["system"] == "{file:./prompts/grok-review.md}"
    assert entry["request"]["body"]["temperature"] == 0.1


def test_grok_review_permissions_equal_code_reviewer() -> None:
    agents = _config()["agents"]
    assert agents["grok-review"]["permissions"] == agents["code-reviewer"]["permissions"]


def test_grok_review_read_only_invariants() -> None:
    perm_list = _config()["agents"]["grok-review"]["permissions"]
    perms = {p["action"]: p["effect"] for p in perm_list}
    assert perms.get("edit") == "deny"
    assert perms.get("shell") != "allow"
    assert {"action": "subagent", "resource": "*", "effect": "deny"} in perm_list


def test_grok_review_agent_count_is_21() -> None:
    assert len(_config()["agents"]) == 21


def test_grok_review_prompt_file_exists_and_ref_resolves() -> None:
    assert PROMPT.is_file()
    match = re.search(r"\{file:\./prompts/([^}]+)\}", _config()["agents"]["grok-review"]["system"])
    assert match is not None
    assert (REPO / "prompts" / match.group(1)).is_file()


# ---------------------------------------------------------------------------
# 2. Census unit tests (synthetic builds)
# ---------------------------------------------------------------------------


def test_census_rejects_orphan_profile(tmp_path: Path) -> None:
    build = tmp_path / "build"
    _write_config(build, {"orchestrator": {"model": "opencode-go/mimo-v2.6-flash"}})
    _write_grok_profile(build, "orphan-agent")
    errors = validate.validate_grok_registry_census(build)
    assert len(errors) == 1
    err = errors[0]
    assert "orphan-agent" in err
    assert "grok/agents/orphan-agent.md" in err
    assert "census" in err.lower()
    assert "GROK_CENSUS_ALLOWLIST" in err


def test_census_accepts_registered_profile(tmp_path: Path) -> None:
    build = tmp_path / "build"
    _write_config(build, {"grok-review": {"model": "xai/grok-build-0.1"}})
    _write_grok_profile(build, "grok-review")
    assert validate.validate_grok_registry_census(build) == []


def test_census_accepts_allowlisted_research_without_registry(tmp_path: Path) -> None:
    build = tmp_path / "build"
    _write_config(build, {"orchestrator": {"model": "opencode-go/mimo-v2.6-flash"}})
    _write_grok_profile(build, "research")
    assert validate.validate_grok_registry_census(build) == []


def test_census_prefers_frontmatter_name_over_stem(tmp_path: Path) -> None:
    build = tmp_path / "build"
    _write_config(build, {"front-name": {"model": "xai/grok-build-0.1"}})
    agents = build / "grok" / "agents"
    agents.mkdir(parents=True)
    profile = agents / "stem-name.md"
    profile.write_text(
        "---\nname: front-name\nmodel: grok-build-0.1\ndescription: x\n---\n",
        encoding="utf-8",
    )
    assert validate.validate_grok_registry_census(build) == []


def test_census_ignores_opencode_only_entries(tmp_path: Path) -> None:
    build = tmp_path / "build"
    _write_config(build, {"deep-research": {"model": "opencode-go/mimo-v2.6-flash"}})
    assert validate.validate_grok_registry_census(build) == []


def _write_claude_agent(build: Path, name: str) -> None:
    agents = build / "claude" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / f"{name}.md").write_text(
        f"---\nname: {name}\ndescription: synthetic\n---\n", encoding="utf-8"
    )


def test_census_wired_into_validate_main(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    build = tmp_path / "build"
    _write_config(build, {"orchestrator": {"model": "opencode-go/mimo-v2.6-flash"}})
    _write_grok_profile(build, "orphan-agent")
    _write_claude_agent(build, "orchestrator")
    rc = validate.main([str(build)])
    stdout = capsys.readouterr().out
    # The synthetic config lacks top-level permissions, so validate.main fails
    # for that reason too. Pin the census error itself to prove the wiring.
    assert (
        "grok registry census: profile 'orphan-agent' "
        "(grok/agents/orphan-agent.md) has no same-name agent in opencode.json" in stdout
    )
    assert "GROK_CENSUS_ALLOWLIST" in stdout
    assert rc == 1


# ---------------------------------------------------------------------------
# 3. Census production pin
# ---------------------------------------------------------------------------


def test_census_passes_on_real_tree() -> None:
    assert validate.validate_grok_registry_census(REPO) == []


# ---------------------------------------------------------------------------
# 4. Allowlist pin
# ---------------------------------------------------------------------------


def test_census_allowlist_keys() -> None:
    assert set(validate.GROK_CENSUS_ALLOWLIST.keys()) == {"research"}
    assert "2026-10-31" in validate.GROK_CENSUS_ALLOWLIST["research"]


# ---------------------------------------------------------------------------
# 5. Parity pins
# ---------------------------------------------------------------------------


def test_grok_review_in_grok_mirrors() -> None:
    assert validate.GROK_MIRRORS["grok-review"] == ["grok-review.md"]


def test_grok_review_role_keywords() -> None:
    assert validate.ROLE_KEYWORDS["grok-review"] == [("read-only",), ("security",)]


@pytest.mark.parametrize(
    ("path", "marker"),
    [
        (PROMPT, "read-only"),
        (PROMPT, "security"),
        (PROMPT, "hard constraints"),
        (PROMPT, "safety constraints"),
        (GROK_PROFILE, "read-only"),
        (GROK_PROFILE, "security"),
        (GROK_PROFILE, "hard constraints"),
        (GROK_PROFILE, "safety constraints"),
    ],
)
def test_parity_markers_present(path: Path, marker: str) -> None:
    assert marker in path.read_text(encoding="utf-8").lower()


# ---------------------------------------------------------------------------
# 6. Mirror-edit pin
# ---------------------------------------------------------------------------


def test_grok_mirror_heading_alignment() -> None:
    text = GROK_PROFILE.read_text(encoding="utf-8")
    assert "Hard constraints:" in text
    assert "Rules:" not in text


def test_grok_mirror_frontmatter_model_unchanged() -> None:
    meta = validate.parse_frontmatter(GROK_PROFILE.read_text(encoding="utf-8"))
    assert meta.get("name") == "grok-review"
    assert meta.get("model") == "grok-build-0.1"


def test_grok_mirror_summary_structure_preserved() -> None:
    text = GROK_PROFILE.read_text(encoding="utf-8")
    assert "summary, strengths" in text


# ---------------------------------------------------------------------------
# 7. Docs pins
# ---------------------------------------------------------------------------


def test_readme_has_grok_review_roster_row() -> None:
    text = README.read_text(encoding="utf-8")
    assert "[`grok-review`](prompts/grok-review.md)" in text


def test_readme_stale_grok_claim_replaced() -> None:
    text = README.read_text(encoding="utf-8")
    assert "All profiles currently use **grok-4.7**" not in text
    assert "grok-build-0.1" in text
    assert "MDU-25 split" in text


def test_readme_layout_counts_21_12() -> None:
    text = README.read_text(encoding="utf-8")
    idx = text.find("## Repository Layout")
    assert idx >= 0
    rest = text[idx:idx + 2000]
    assert "(21 agents, all paid)" in rest
    assert "— 12 files" in rest


def test_readme_progress_line_date_and_structure() -> None:
    text = README.read_text(encoding="utf-8")
    idx = text.find("## Roadmap")
    assert idx >= 0
    rest = text[idx:idx + 1200]
    assert "last verified 2026-10-31" in rest
    assert "14/15" not in rest


def test_backlog_has_mdu_45_entry() -> None:
    text = BACKLOG.read_text(encoding="utf-8")
    assert "### MDU-45" in text
    assert "register it in base `opencode.json`" in text
    assert "docs-staleness sweep" in text


@pytest.mark.parametrize(
    "mdu",
    ["MDU-01", "MDU-02", "MDU-03", "MDU-05", "MDU-06", "MDU-07", "MDU-08", "MDU-34"],
)
def test_backlog_status_backfilled(mdu: str) -> None:
    text = BACKLOG.read_text(encoding="utf-8")
    match = re.search(rf"^### {re.escape(mdu)}\b.*?(?=^### |\Z)", text, re.MULTILINE | re.DOTALL)
    assert match is not None
    section = match.group(0)
    statuses = [line.strip() for line in section.splitlines() if line.strip().startswith("- **Status:**")]
    assert len(statuses) == 1
    assert "backfilled 2026-10-31" in statuses[0]


def test_backlog_no_entry_remains_unresolved() -> None:
    """AC 8 (D8 audit confirmation): every backlog entry has a resolution.

    Each ``### MDU-XX`` section in FEATURE_BACKLOG.md must carry exactly one
    ``- **Status:**`` line whose value resolves the entry (Done or Superseded).
    A section with zero or duplicate Status lines, or with a value that is
    neither Done nor Superseded, fails the audit.
    """
    text = BACKLOG.read_text(encoding="utf-8")
    sections = re.split(r"(?m)^(?=### MDU-)", text)
    audited = 0
    for section in sections:
        heading = re.match(r"### (MDU-\d+)", section)
        if heading is None:
            continue
        audited += 1
        statuses = [
            line.strip()
            for line in section.splitlines()
            if line.strip().startswith("- **Status:**")
        ]
        assert len(statuses) == 1, (
            f"{heading.group(1)}: expected exactly one Status line, got {statuses}"
        )
        assert re.search(r"\b(Done|Superseded)\b", statuses[0]), (
            f"{heading.group(1)}: Status line does not resolve the entry: {statuses[0]}"
        )
    assert audited >= 20, f"audit saw implausibly few backlog entries: {audited}"


def test_model_registry_doc_has_safe_refresh_caveat() -> None:
    text = MODEL_REGISTRY_DOC.read_text(encoding="utf-8")
    assert "Safe-refresh caveat (2026-10-31, MDU-45)" in text
    assert "A blind `opencode models > config/model-registry.txt` would **resurrect**" in text


# ---------------------------------------------------------------------------
# 8. Integration: validate.main on the real repo is green
# ---------------------------------------------------------------------------


def test_validate_main_green_on_real_tree() -> None:
    build_dir = REPO / "build"
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "lib" / "validate.py"), str(build_dir)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
