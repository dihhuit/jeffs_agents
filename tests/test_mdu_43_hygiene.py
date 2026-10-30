#!/usr/bin/env python3
"""MDU-43 tests: registry, delegation, and backlog hygiene pins.

Three review findings from MDU-43, pinned so they cannot silently regress:

1. The upstream-deprecated ``opencode-go/mimo-v2.5`` and ``-pro`` rows are
   commented out of the registry snapshot, so ``model_registry.load_registry``
   can never resolve a dead model (while the successors stay active).
2. The five one-line delegation swaps name ``deep-research`` and no longer the
   retired bare ``research`` agent. The assertions are deliberately narrow:
   only *delegation* shapes and the backticked agent token are forbidden —
   ordinary prose still mentions "research", and ``grok/agents/orchestrator.md``
   legitimately lists ``research`` in its roster, so it is out of scope.
3. Four finished backlog entries carry their updated ``Status`` line.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import model_registry

REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / "config" / "model-registry.txt"
BACKLOG = REPO / "FEATURE_BACKLOG.md"

#: Rows MDU-43 retires (upstream-deprecated per the MDU-40 live probe).
MIMO_V25_ROWS = (
    "opencode-go/mimo-v2.5",
    "opencode-go/mimo-v2.5-pro",
)

#: The files whose one-line delegation target was swapped to ``deep-research``.
DELEGATION_SWAPS = (
    "prompts/devops.md",
    "grok/agents/devops.md",
    "prompts/code-reviewer.md",
    "grok/agents/code-reviewer.md",
    "grok/agents/architect-premium.md",
)

#: Delegation shapes the old lines used (plus the usual verb variants). Only
#: these are forbidden; free prose about "research" is untouched.
BARE_RESEARCH_DELEGATION = (
    r"(?i)\bdelegate\s+to\s+`research`",
    r"(?i)\b(?:ask|spawn|use|hand\s+off\s+to)\s+`research`",
    r"`research`\s+agent\b",
)

#: Backlog entries whose Status line MDU-43 brings up to date.
EXPECTED_STATUS = {
    "MDU-12": "Done — 2026-09-15",
    "MDU-14": "Done — 2026-09-15",
    "MDU-33": "Superseded by MDU-40 — 2026-10-30",
    "MDU-35": "Done — 2026-10-26",
}


# ---------------------------------------------------------------------------
# 1. registry: retired mimo-v2.5 rows are comments
# ---------------------------------------------------------------------------

def test_mimo_v2_5_rows_are_commented_out() -> None:
    text = REGISTRY.read_text(encoding="utf-8")
    registry = model_registry.load_registry(REGISTRY)

    for model in MIMO_V25_ROWS:
        assert model not in registry, model

    # Independent re-parse: no *uncommented* line may name mimo-v2.5(-pro).
    active = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
        and not line.lstrip().startswith("#")
        and re.fullmatch(r"opencode-go/mimo-v2\.5(?:-pro)?", line.strip())
    ]
    assert active == [], active

    # The retirement is documented, not silently deleted.
    for model in MIMO_V25_ROWS:
        assert f"# {model}" in text, model

    # ...and the successors the agents actually use stay active.
    assert "opencode-go/mimo-v2.6-flash" in registry
    assert "opencode-go/mimo-v2.6-pro" in registry


def test_load_registry_skips_commented_mimo_rows(tmp_path: Path) -> None:
    snapshot = tmp_path / "model-registry.txt"
    snapshot.write_text(
        "\n".join(
            [
                "# 2026-10-30 (MDU-43): deprecated upstream",
                "# opencode-go/mimo-v2.5",
                "   # opencode-go/mimo-v2.5-pro",
                "opencode-go/mimo-v2.6-flash",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    assert model_registry.load_registry(snapshot) == {
        "opencode-go/mimo-v2.6-flash"
    }


# ---------------------------------------------------------------------------
# 2. delegation swaps target deep-research, never bare `research`
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("relpath", DELEGATION_SWAPS)
def test_delegation_swaps_name_deep_research(relpath: str) -> None:
    path = REPO / relpath
    text = path.read_text(encoding="utf-8")

    for pattern in BARE_RESEARCH_DELEGATION:
        match = re.search(pattern, text)
        assert match is None, (relpath, pattern, match.group(0) if match else "")

    # The retired agent name must not survive as a backticked token at all.
    assert "`research`" not in text, relpath

    # The replacement is present in a delegation sentence.
    assert re.search(r"(?i)\bdelegat\w*\s+to\s+`deep-research`", text), relpath


# ---------------------------------------------------------------------------
# 3. backlog status lines
# ---------------------------------------------------------------------------

def _backlog_section(mdu: str) -> str:
    text = BACKLOG.read_text(encoding="utf-8")
    match = re.search(
        rf"^### {re.escape(mdu)}\b.*?(?=^### |\Z)", text, re.MULTILINE | re.DOTALL
    )
    assert match is not None, f"section {mdu} not found in FEATURE_BACKLOG.md"
    return match.group(0)


@pytest.mark.parametrize("mdu", sorted(EXPECTED_STATUS))
def test_backlog_status_lines_are_updated(mdu: str) -> None:
    section = _backlog_section(mdu)
    statuses = [
        line.strip()
        for line in section.splitlines()
        if line.strip().startswith("- **Status:**")
    ]
    assert len(statuses) == 1, (mdu, statuses)

    value = statuses[0].removeprefix("- **Status:**").strip()
    assert value == EXPECTED_STATUS[mdu], (mdu, value)
