"""Focused tests for the Grok model allowlist and the MDU-25 build rung.

Guards three things:
  * the single-source allowlist in ``scripts/lib/validate.py``,
  * every production ``grok/agents/*.md`` profile staying inside that
    allowlist, and
  * the MDU-25 split: bulk profiles on ``grok-build-0.1``, flagship
    profiles on ``grok-4.7``, and none on retired ``grok-4.6`` /
    ``grok-4.5``.

The last two tests exercise ``validate.validate_grok_agents`` against a
synthetic build dir in ``tmp_path`` so the real tree is never mutated.
"""

from __future__ import annotations

from pathlib import Path

import validate

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_GROK_DIR = REPO_ROOT / "grok" / "agents"

EXPECTED_ALLOWLIST = {"grok-4.7", "grok-4.6", "grok-4.5", "grok-build-0.1"}

# MDU-25: bulk (non-reasoning-critical) profiles move to the cheaper
# grok-build-0.1 rung. Every other production profile stays on the
# flagship grok-4.7. Anything on grok-4.6 or grok-4.5 is a failure.
BULK_GROK_BUILD_PROFILES = {
    "just-code",
    "test-agent",
    "code-reviewer",
    "qa",
    "devops",
    "research",
    "ui-ux-designer",
    "grok-review",
}
FLAGSHIP_MODEL = "grok-4.7"
BULK_MODEL = "grok-build-0.1"
RETIRED_MODELS = {"grok-4.6", "grok-4.5"}


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
# 3. MDU-25: explicit per-profile model map
#    bulk profiles -> grok-build-0.1, everything else -> grok-4.7,
#    and nothing on the retired grok-4.6 / grok-4.5.
# ---------------------------------------------------------------------------

def test_production_grok_profiles_use_expected_model() -> None:
    wrong = []
    for profile in _production_profiles():
        stem = profile.stem
        meta = validate.parse_frontmatter(profile.read_text(encoding="utf-8"))
        expected = BULK_MODEL if stem in BULK_GROK_BUILD_PROFILES else FLAGSHIP_MODEL
        actual = meta.get("model")
        if actual != expected:
            wrong.append(f"{profile.name}={actual!r} (expected {expected!r})")
    assert not wrong, (
        "production grok profiles on the wrong MDU-25 rung: " + ", ".join(wrong)
    )


def test_no_production_grok_profile_on_retired_models() -> None:
    retired = []
    for profile in _production_profiles():
        meta = validate.parse_frontmatter(profile.read_text(encoding="utf-8"))
        if meta.get("model") in RETIRED_MODELS:
            retired.append(f"{profile.name}={meta.get('model')!r}")
    assert not retired, (
        "production grok profiles on retired grok-4.6/grok-4.5: "
        + ", ".join(retired)
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
