"""Regression contracts for MDU-23 (Session hygiene gates).

Cheap dependency-free checks that the orchestrator and just-code prompts
(and their grok mirrors) carry the required verbatim session-boundary,
compaction, cache-miss, and context-cap phrases.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

ORCHESTRATOR_PROMPT = REPO_ROOT / "prompts" / "orchestrator.md"
ORCHESTRATOR_GROK = REPO_ROOT / "grok" / "agents" / "orchestrator.md"
JUST_CODE_PROMPT = REPO_ROOT / "prompts" / "just-code.md"
JUST_CODE_GROK = REPO_ROOT / "grok" / "agents" / "just-code.md"
JUST_CODE_MID_GROK = REPO_ROOT / "grok" / "agents" / "just-code-mid.md"
JUST_CODE_PRO_GROK = REPO_ROOT / "grok" / "agents" / "just-code-pro.md"

ORCHESTRATOR_FILES = [
    ORCHESTRATOR_PROMPT,
    ORCHESTRATOR_GROK,
]

JUST_CODE_FILES = [
    JUST_CODE_PROMPT,
    JUST_CODE_GROK,
    JUST_CODE_MID_GROK,
    JUST_CODE_PRO_GROK,
]


def test_orchestrator_files_have_session_boundary_phrases() -> None:
    for path in ORCHESTRATOR_FILES:
        text = path.read_text(encoding="utf-8").lower()
        assert "140000" in text, f"{path.name} missing 140000"
        assert "continue this session across mdus" in text, f"{path.name} missing continue this session across MDUs"
        assert "cache miss" in text, f"{path.name} missing cache miss"
        assert "compact and continue" in text, f"{path.name} missing compact and continue"


def test_orchestrator_files_no_long_running_sessions_sentence() -> None:
    old = "Long-running sessions (hours/days) are fine"
    for path in ORCHESTRATOR_FILES:
        text = path.read_text(encoding="utf-8")
        assert old not in text, f"{path.name} still contains the old long-running sessions sentence"


def test_just_code_files_have_context_cap_phrases() -> None:
    for path in JUST_CODE_FILES:
        text = path.read_text(encoding="utf-8").lower()
        assert "step 40" in text, f"{path.name} missing step 40"
        assert "new child" in text, f"{path.name} missing new child"
        assert "140000" in text, f"{path.name} missing 140000"


def test_just_code_step_40_is_the_phrase_not_a_prefix() -> None:
    # "step 400" would satisfy a plain substring check; lock the exact cap.
    for path in JUST_CODE_FILES:
        text = path.read_text(encoding="utf-8").lower()
        assert re.search(r"step 40(?!\d)", text), f"{path.name} has no exact 'step 40' phrase"


def test_orchestrator_files_carry_the_session_boundary_replacement() -> None:
    # Design MDU-23 requires replacing the old sentence, not only deleting it:
    # one MDU per session plus the 140000 compaction trigger.
    required = [
        "stop at the end of this mdu",
        "must compact at 140000 once durable artifacts exist",
        "a pasted resume block in a new session is the start of work",
        "a resume block is not that phrase",
    ]
    for path in ORCHESTRATOR_FILES:
        text = path.read_text(encoding="utf-8").lower()
        for phrase in required:
            assert phrase in text, f"{path.name} missing {phrase!r}"


def test_just_code_context_cap_names_the_cap_and_handoff() -> None:
    # The coder cap must pair the step/token stop with a handoff instruction,
    # not merely mention the numbers.
    for path in JUST_CODE_FILES:
        text = path.read_text(encoding="utf-8").lower()
        assert "stop implementing" in text, f"{path.name} missing stop implementing"
        assert "spawn a new child" in text, f"{path.name} missing spawn a new child"


def test_opencode_orchestrator_defines_the_gates_not_just_headings() -> None:
    # The section headings alone lower-case to the required phrases, so lock the
    # bodies too: the cache-miss definition and the 140000 compaction condition.
    text = ORCHESTRATOR_PROMPT.read_text(encoding="utf-8").lower()
    for phrase in [
        "cache miss is the latest assistant turn",  # cache-miss gate body
        "1152",
        ">= 80000",
        "prompt size is >= 140000",  # compaction condition
        "opencode_session_id",
    ]:
        assert phrase in text, f"{ORCHESTRATOR_PROMPT.name} missing {phrase!r}"


def test_validator_role_keywords_lock_the_new_clauses() -> None:
    # scripts/lib/validate.py is the mirror-drift gate; if these clauses are
    # dropped a grok mirror could silently lose the MDU-23 contract.
    import validate  # noqa: PLC0415 - provided by tests/conftest.py

    orchestrator = [clause for group in validate.ROLE_KEYWORDS["orchestrator"] for clause in group]
    just_code = [clause for group in validate.ROLE_KEYWORDS["just-code"] for clause in group]
    for clause in ["140000", "continue this session across mdus", "cache miss", "compact and continue"]:
        assert clause in orchestrator, f"validate.py orchestrator keywords missing {clause!r}"
    for clause in ["step 40", "new child", "140000"]:
        assert clause in just_code, f"validate.py just-code keywords missing {clause!r}"
