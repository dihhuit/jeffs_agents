"""Tests for the skills-library walker (validate_skills) in scripts/lib/validate.py.

Covers the frontmatter contract for ``build_dir/skills/*/SKILL.md`` (kebab-case
``name`` + ``description``), the missing-file/missing-frontmatter error paths,
the empty-skills-library no-op, and the ``[ok] skills:`` line from
``validate.main``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import validate

VALID_SKILL = (
    "---\n"
    "name: test-skill\n"
    "description: A synthetic skill used to exercise the skills validator.\n"
    "---\n"
    "\n"
    "# Test skill\n"
    "\n"
    "Use me in tests.\n"
)


def _write_skill(build: Path, name: str, *, body: str = VALID_SKILL) -> Path:
    """Write build/skills/<name>/SKILL.md; return the SKILL.md path."""
    skill_dir = build / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    path = skill_dir / "SKILL.md"
    path.write_text(body, encoding="utf-8")
    return path


def _full_build(tmp_path: Path, *, skill_name: str | None = "test-skill") -> Path:
    """A build dir that passes every validate.py check, plus one skill."""
    build = tmp_path / "build"
    (build / "grok" / "agents").mkdir(parents=True)
    (build / "claude" / "agents").mkdir(parents=True)
    (build / "prompts").mkdir(parents=True)

    (build / "opencode.json").write_text(
        json.dumps(
            {
                "agent": {
                    "test-agent": {
                        "mode": "subagent",
                        "description": "test",
                        "model": "model-a",
                        "prompt": "You are a test agent.",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (build / "grok" / "agents" / "test.md").write_text(
        "---\nname: test-agent\nmodel: grok-4.6\ndescription: \"test\"\n---\n",
        encoding="utf-8",
    )
    (build / "claude" / "agents" / "test.md").write_text(
        "---\nname: test-agent\ndescription: \"test\"\n---\n",
        encoding="utf-8",
    )
    if skill_name is not None:
        _write_skill(build, skill_name)
    return build


# ---------------------------------------------------------------------------
# validate_skills
# ---------------------------------------------------------------------------

def test_validate_skills_valid_frontmatter_passes(tmp_path: Path) -> None:
    build = tmp_path / "build"
    _write_skill(build, "test-skill")
    assert validate.validate_skills(build) == []


def test_validate_skills_multiple_valid_skills_pass(tmp_path: Path) -> None:
    build = tmp_path / "build"
    _write_skill(build, "test-skill")
    _write_skill(build, "another-skill")
    assert validate.validate_skills(build) == []


def test_validate_skills_missing_skill_md(tmp_path: Path) -> None:
    build = tmp_path / "build"
    (build / "skills" / "broken-skill").mkdir(parents=True)
    errors = validate.validate_skills(build)
    assert errors == ["skill directory missing SKILL.md: broken-skill"]


def test_validate_skills_missing_frontmatter(tmp_path: Path) -> None:
    build = tmp_path / "build"
    _write_skill(build, "plain-skill", body="# No frontmatter here\n")
    errors = validate.validate_skills(build)
    assert errors == ["skill missing YAML frontmatter: plain-skill"]


def test_validate_skills_non_kebab_case_name(tmp_path: Path) -> None:
    build = tmp_path / "build"
    body = "---\nname: Bad_Name\ndescription: \"bad\"\n---\n"
    _write_skill(build, "bad_skill", body=body)
    errors = validate.validate_skills(build)
    assert errors == ["skill name 'Bad_Name' is not kebab-case: bad_skill"]


def test_validate_skills_missing_name(tmp_path: Path) -> None:
    build = tmp_path / "build"
    body = "---\ndescription: Has a description but no name.\n---\n"
    _write_skill(build, "no-name", body=body)
    errors = validate.validate_skills(build)
    assert errors == ["skill missing 'name' in frontmatter: no-name"]


def test_validate_skills_missing_description(tmp_path: Path) -> None:
    build = tmp_path / "build"
    body = "---\nname: no-description\n---\n"
    _write_skill(build, "no-description", body=body)
    errors = validate.validate_skills(build)
    assert errors == [
        "skill missing 'description' in frontmatter: no-description"
    ]


def test_validate_skills_no_skills_dir_is_noop(tmp_path: Path) -> None:
    build = tmp_path / "build"
    build.mkdir()
    assert validate.validate_skills(build) == []


def test_validate_skills_empty_skills_dir_is_noop(tmp_path: Path) -> None:
    build = tmp_path / "build"
    (build / "skills").mkdir(parents=True)
    assert validate.validate_skills(build) == []


# ---------------------------------------------------------------------------
# validate.main integration
# ---------------------------------------------------------------------------

def test_validate_main_prints_ok_skills_line(
    tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    build = _full_build(tmp_path, skill_name="test-skill")
    snapshot = tmp_path / "model-registry.txt"
    snapshot.write_text("model-a\n", encoding="utf-8")
    monkeypatch.setattr(validate, "DEFAULT_SNAPSHOT", snapshot)

    code = validate.main([str(build)])
    out = capsys.readouterr().out
    assert code == 0
    assert "[ok]    skills: 1 valid skill(s)" in out


def test_validate_main_fails_on_broken_skill(
    tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    build = _full_build(tmp_path, skill_name=None)
    _write_skill(build, "bad_skill", body="---\nname: Bad_Name\n---\n")
    snapshot = tmp_path / "model-registry.txt"
    snapshot.write_text("model-a\n", encoding="utf-8")
    monkeypatch.setattr(validate, "DEFAULT_SNAPSHOT", snapshot)

    code = validate.main([str(build)])
    out = capsys.readouterr().out
    assert code == 1
    assert "skill name 'Bad_Name' is not kebab-case: bad_skill" in out
    assert "skill missing 'description' in frontmatter: bad_skill" in out