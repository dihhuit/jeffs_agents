"""MDU-24 contract: the test agent must never discard a dirty tree.

After MDU-23 a test-agent ran ``git checkout -- .`` against uncommitted MDU
edits and destroyed the work. Guards the real repo (not a synthetic build):
all three test-agent prompt mirrors carry the verbatim **Dirty tree** bullet
before the Step Limit bullet, and ``validate.py`` ROLE_KEYWORDS checks it.
"""

from __future__ import annotations

from pathlib import Path

import validate

REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPT_FILES = (
    REPO_ROOT / "prompts" / "test-agent.md",
    REPO_ROOT / "grok" / "agents" / "test-agent.md",
    REPO_ROOT / "grok" / "agents" / "test-agent-pro.md",
)

# Required substrings from the design doc, all three files.
REQUIRED_SUBSTRINGS = (
    "git checkout --",
    "git reset --hard",
    "git clean",
    "uncommitted work",
)

# The three new ROLE_KEYWORDS clauses for "test-agent".
NEW_KEYWORD_CLAUSES = [
    ("git checkout --",),
    ("git reset --hard",),
    ("git clean",),
]

# Pre-existing clause that must survive the addition.
EXISTING_CLAUSE = ("never modify source", "never modify production")


def test_prompt_mirrors_contain_dirty_tree_substrings() -> None:
    for path in PROMPT_FILES:
        text = path.read_text(encoding="utf-8")
        for substring in REQUIRED_SUBSTRINGS:
            assert substring in text, f"{path} missing {substring!r}"


def test_dirty_tree_bullet_precedes_step_limit() -> None:
    for path in PROMPT_FILES:
        text = path.read_text(encoding="utf-8")
        dirty = text.find("**Dirty tree:**")
        step = text.find("**Step Limit:**")
        assert dirty != -1, f"{path} missing the Dirty tree bullet"
        assert step != -1, f"{path} missing the Step Limit bullet"
        assert dirty < step, f"{path}: Dirty tree bullet must precede Step Limit"


def test_role_keywords_include_new_clauses() -> None:
    clauses = validate.ROLE_KEYWORDS["test-agent"]
    for clause in NEW_KEYWORD_CLAUSES:
        assert clause in clauses, f"missing clause {clause!r}"


def test_role_keywords_keep_existing_clause() -> None:
    assert EXISTING_CLAUSE in validate.ROLE_KEYWORDS["test-agent"]
