#!/usr/bin/env python3
"""MDU-58 tests: register base ``grok-inception`` on the xAI provider.

Pins the registry entry (primary, ``xai/grok-4.7``, base-``inception``
permissions and temperature), the mdu-42 xAI rule on the real config, the
adapted prompt contract, README roster row, and the design decision that no
Grok Build mirror ships (``grok/agents/grok-inception.md`` must not exist and
``grok-inception`` must stay out of ``GROK_MIRRORS``).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import model_registry
import validate

REPO = Path(__file__).resolve().parents[1]
OPENCODE_JSON = REPO / "opencode.json"
PROMPT = REPO / "prompts" / "grok-inception.md"
GROK_PROFILE = REPO / "grok" / "agents" / "grok-inception.md"
README = REPO / "README.md"

AGENT_NAME = "grok-inception"
MODEL = "xai/grok-4.7"
SYSTEM_REF = "{file:./prompts/grok-inception.md}"

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


def _read(path: Path) -> str:
    assert path.is_file(), f"missing {path.relative_to(REPO)}"
    return path.read_text(encoding="utf-8")


def _config() -> dict:
    return json.loads(OPENCODE_JSON.read_text(encoding="utf-8"))


def _agent() -> dict:
    agents = _config().get("agents")
    assert isinstance(agents, dict), "opencode.json missing 'agents' object"
    assert AGENT_NAME in agents, f"opencode.json missing agent {AGENT_NAME!r}"
    entry = agents[AGENT_NAME]
    assert isinstance(entry, dict), f"agent {AGENT_NAME!r} must be an object"
    return entry


# ---------------------------------------------------------------------------
# 1. Registry entry pins
# ---------------------------------------------------------------------------


def test_grok_inception_registered() -> None:
    entry = _agent()
    assert entry.get("mode") == "primary"
    assert entry.get("model") == MODEL
    assert entry.get("system") == SYSTEM_REF
    assert entry.get("request", {}).get("body", {}).get("temperature") == 0.4
    assert "tools" not in entry, "grok-inception must not use a legacy tools block"


def test_grok_inception_permissions() -> None:
    permissions = _agent().get("permissions")
    assert isinstance(permissions, list), "grok-inception.permissions must be an array"

    def has(action: str, effect: str) -> bool:
        return any(
            p.get("action") == action
            and p.get("resource") == "*"
            and p.get("effect") == effect
            for p in permissions
        )

    assert has("question", "allow"), "grok-inception must allow question *"
    assert has("shell", "deny"), "grok-inception must deny shell *"
    assert has("subagent", "deny"), "grok-inception must deny subagent *"


def test_grok_inception_permissions_match_base_inception() -> None:
    agents = _config()["agents"]
    assert agents[AGENT_NAME]["permissions"] == agents["inception"]["permissions"]


def test_grok_inception_prompt_ref_resolves() -> None:
    match = re.search(r"\{file:\./prompts/([^}]+)\}", _agent()["system"])
    assert match is not None
    assert (REPO / "prompts" / match.group(1)) == PROMPT


# ---------------------------------------------------------------------------
# 2. mdu-42 xAI rule on the real config
# ---------------------------------------------------------------------------


def test_grok_xai_rule_green_on_real_config() -> None:
    assert model_registry.grok_xai_errors(_config()["agents"], label="opencode.json") == []
    assert model_registry.is_grok_named(AGENT_NAME)


# ---------------------------------------------------------------------------
# 3. Prompt contract
# ---------------------------------------------------------------------------


def test_prompt_exists() -> None:
    assert PROMPT.is_file(), "prompts/grok-inception.md missing"


@pytest.mark.parametrize("phrase", REQUIRED_PHRASES)
def test_prompt_contains_required_phrase(phrase: str) -> None:
    text = _read(PROMPT).lower()
    assert phrase in text, f"prompts/grok-inception.md missing {phrase!r}"


def test_prompt_states_50_loop_step_limit() -> None:
    assert STEP_LIMIT.search(_read(PROMPT)), (
        "prompts/grok-inception.md missing a 50 loop-step limit"
    )


def test_prompt_names_grok_variant() -> None:
    text = _read(PROMPT).lower()
    assert "grok-inception" in text
    assert "xai" in text
    assert "not part of the orchestrator's automatic mdu loop" in text


# ---------------------------------------------------------------------------
# 4. No-mirror decision (design D2)
# ---------------------------------------------------------------------------


def test_no_grok_mirror_ships() -> None:
    assert not GROK_PROFILE.exists(), (
        "grok/agents/grok-inception.md must not ship: Grok Build already has "
        "the `inception` primary on grok-4.7 (design D2)"
    )
    assert AGENT_NAME not in validate.GROK_MIRRORS


def test_parity_stays_green_without_mirror() -> None:
    assert validate.validate_parity(REPO) == []


# ---------------------------------------------------------------------------
# 5. No overlay particulars
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("leak", OVERLAY_LEAKS)
def test_prompt_omits_overlay_particulars(leak: str) -> None:
    assert leak not in _read(PROMPT).lower(), (
        f"prompts/grok-inception.md contains overlay token {leak!r}"
    )


# ---------------------------------------------------------------------------
# 6. README roster row
# ---------------------------------------------------------------------------


def test_readme_has_grok_inception_roster_row() -> None:
    text = _read(README)
    assert f"[`{AGENT_NAME}`](prompts/grok-inception.md)" in text


def test_readme_row_is_in_whats_inside_section() -> None:
    text = _read(README)
    idx = text.find("## What's Inside")
    assert idx >= 0
    rest = text[idx:]
    match = re.search(r"\n## [^#]", rest)
    section = rest[: match.start()] if match else rest
    pattern = r"\|\s*\[`" + re.escape(AGENT_NAME) + r"`\]\([^)]+\)"
    assert re.search(pattern, section)
