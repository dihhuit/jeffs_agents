"""Focused tests for MDU-16: Grok model allowlist + production grok-4.7 bump.

Guards three things:
  * the single-source allowlist in ``scripts/lib/validate.py``,
  * every production ``grok/agents/*.md`` profile staying inside that
    allowlist, and
  * the MDU-16 regression: all production profiles specifically on
    ``grok-4.7`` (so a future edit cannot silently leave one on 4.6).

The last two tests exercise ``validate.validate_grok_agents`` against a
synthetic build dir in ``tmp_path`` so the real tree is never mutated.
"""

from __future__ import annotations

from pathlib import Path

import validate

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_GROK_DIR = REPO_ROOT / "grok" / "agents"

EXPECTED_ALLOWLIST = {"grok-4.7", "grok-4.6", "grok-4.5"}


def _production_profiles() -> list[Path]:
    profiles = sorted(PRODUCTION_GROK_DIR.glob("*.md"))
    assert profiles, f"no production grok profiles found in {PRODUCTION_GROK_DIR}"
    return profiles


def _write_grok_profile(build: Path, name: str, model: str) -> Path:
    """Write one synthetic grok profile under <build>/grok/agents/."""
    agents = build / "grok" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    profile = agents / f"{name}.md"
    profile.write_text(
        f"---\nname: {name}\nmodel: {model}\ndescription: \"synthetic\"\n---\n",
        encoding="utf-8",
    )
    return profile


# ---------------------------------------------------------------------------
# 1. allowlist contents
# ---------------------------------------------------------------------------

def test_grok_model_allowlist_exact_contents() -> None:
    assert validate.GROK_MODEL_ALLOWLIST == EXPECTED_ALLOWLIST


# ---------------------------------------------------------------------------
# 2. production profiles are within the allowlist
# ---------------------------------------------------------------------------

def test_production_grok_profiles_models_allowlisted() -> None:
    for profile in _production_profiles():
        meta = validate.parse_frontmatter(profile.read_text(encoding="utf-8"))
        assert "model" in meta, f"{profile.name} missing 'model' in frontmatter"
        assert meta["model"] in validate.GROK_MODEL_ALLOWLIST, (
            f"{profile.name} model '{meta['model']}' outside allowlist "
            f"{sorted(validate.GROK_MODEL_ALLOWLIST)}"
        )


# ---------------------------------------------------------------------------
# 3. MDU-16 regression: production profiles use grok-4.7
# ---------------------------------------------------------------------------

def test_production_grok_profiles_use_grok_4_7() -> None:
    outdated = []
    for profile in _production_profiles():
        meta = validate.parse_frontmatter(profile.read_text(encoding="utf-8"))
        if meta.get("model") != "grok-4.7":
            outdated.append(f"{profile.name}={meta.get('model')!r}")
    assert not outdated, (
        "production grok profiles not on grok-4.7 (MDU-16 regression): "
        + ", ".join(outdated)
    )


# ---------------------------------------------------------------------------
# 4. negative: non-allowlisted model is rejected
# ---------------------------------------------------------------------------

def test_validate_grok_agents_rejects_non_allowlisted_model(tmp_path: Path) -> None:
    build = tmp_path / "build"
    _write_grok_profile(build, "bad", "grok-composer-2.5-fast")

    errors = validate.validate_grok_agents(build)

    assert len(errors) == 1
    assert "grok-composer-2.5-fast" in errors[0]
    assert "allowlist" in errors[0]


# ---------------------------------------------------------------------------
# 5. positive: legacy grok-4.6 still passes the allowlist
# ---------------------------------------------------------------------------

def test_validate_grok_agents_accepts_legacy_grok_4_6(tmp_path: Path) -> None:
    build = tmp_path / "build"
    _write_grok_profile(build, "legacy", "grok-4.6")

    assert validate.validate_grok_agents(build) == []
