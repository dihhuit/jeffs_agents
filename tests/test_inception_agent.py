"""MDU-20 contract tests for the public ``inception`` agent.

Guards the real repo (not a synthetic build): both prompt mirrors exist and
carry the parity clauses, the Grok frontmatter is allowlisted, the OpenCode
registry entry matches the design snippet, and ``validate.py`` registers the
mirror. Overlay particulars (browser-os, safekids) must not leak into the base.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import validate

REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPT = REPO_ROOT / "prompts" / "inception.md"
GROK_PROFILE = REPO_ROOT / "grok" / "agents" / "inception.md"
OPENCODE_JSON = REPO_ROOT / "opencode.json"

# Case-insensitive substrings required in both mirrors. "50 loop steps" is
# the step-limit statement ("Maximum of 50 loop steps per invocation").
REQUIRED_PHRASES = (
    "hard constraints",
    "interview",
    "spec.md",
    "moscow",
    "complete enough",
    "question",
    "50 loop steps",
)

STEP_LIMIT = re.compile(r"50\s+loop[\s-]*steps", re.IGNORECASE)
OVERLAY_LEAKS = ("browser-os", "safekids")

EXPECTED_ROLE_KEYWORDS = [
    ("interview",),
    ("spec.md",),
    ("moscow",),
    ("complete enough",),
    ("question",),
]


def _read(path: Path) -> str:
    assert path.is_file(), f"missing {path.relative_to(REPO_ROOT)}"
    return path.read_text(encoding="utf-8")


def _inception_agent() -> dict:
    config = json.loads(OPENCODE_JSON.read_text(encoding="utf-8"))
    agents = config.get("agents")
    assert isinstance(agents, dict), "opencode.json missing 'agents' object"
    assert "inception" in agents, "opencode.json missing agent 'inception'"
    agent = agents["inception"]
    assert isinstance(agent, dict), "opencode.json agent 'inception' must be an object"
    return agent


# ---------------------------------------------------------------------------
# 1. both mirrors exist
# ---------------------------------------------------------------------------


def test_inception_prompt_files_exist() -> None:
    assert PROMPT.is_file(), "prompts/inception.md missing"
    assert GROK_PROFILE.is_file(), "grok/agents/inception.md missing"


# ---------------------------------------------------------------------------
# 2. required clauses in both mirrors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", [PROMPT, GROK_PROFILE], ids=["prompt", "grok"])
@pytest.mark.parametrize("phrase", REQUIRED_PHRASES)
def test_both_mirrors_contain_required_phrase(path: Path, phrase: str) -> None:
    text = _read(path).lower()
    assert phrase in text, f"{path.relative_to(REPO_ROOT)} missing {phrase!r}"


@pytest.mark.parametrize("path", [PROMPT, GROK_PROFILE], ids=["prompt", "grok"])
def test_both_mirrors_state_50_loop_step_limit(path: Path) -> None:
    text = _read(path)
    assert STEP_LIMIT.search(text), (
        f"{path.relative_to(REPO_ROOT)} missing a 50 loop-step limit"
    )


# ---------------------------------------------------------------------------
# 3. Grok frontmatter
# ---------------------------------------------------------------------------


def test_grok_inception_frontmatter() -> None:
    meta = validate.parse_frontmatter(_read(GROK_PROFILE))
    assert meta.get("name") == "inception"
    assert meta.get("model") == "grok-4.7"
    assert meta.get("description"), "grok/agents/inception.md missing description"


# ---------------------------------------------------------------------------
# 4. OpenCode registry entry
# ---------------------------------------------------------------------------


def test_opencode_inception_agent_entry() -> None:
    agent = _inception_agent()
    assert agent.get("mode") == "primary"
    assert agent.get("model") == "opencode-go/deepseek-v4.1-flash"
    assert agent.get("system") == "{file:./prompts/inception.md}"

    permissions = agent.get("permissions")
    assert isinstance(permissions, list), "inception.permissions must be an array"
    # shell deny
    assert any(
        p.get("action") == "shell" and p.get("resource") == "*" and p.get("effect") == "deny"
        for p in permissions
    ), "inception must deny shell *"
    # subagent deny-all
    assert any(
        p.get("action") == "subagent" and p.get("resource") == "*" and p.get("effect") == "deny"
        for p in permissions
    ), "inception must deny subagent *"

    assert "tools" not in agent, "inception must not use a legacy tools block"
    blob = json.dumps(agent)
    assert "xai/" not in blob, "inception must not use an xai/ model string"
    assert "xai/" not in str(agent.get("model"))


# ---------------------------------------------------------------------------
# 5. validate.py mirror registration
# ---------------------------------------------------------------------------


def test_validate_registers_inception_mirror() -> None:
    assert validate.GROK_MIRRORS["inception"] == ["inception.md"]
    assert "inception" in validate.ROLE_KEYWORDS
    assert validate.ROLE_KEYWORDS["inception"] == EXPECTED_ROLE_KEYWORDS


# ---------------------------------------------------------------------------
# 6. no overlay particulars
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", [PROMPT, GROK_PROFILE], ids=["prompt", "grok"])
@pytest.mark.parametrize("leak", OVERLAY_LEAKS)
def test_inception_prompts_omit_overlay_particulars(path: Path, leak: str) -> None:
    text = _read(path).lower()
    assert leak not in text, f"{path.relative_to(REPO_ROOT)} contains overlay token {leak!r}"
