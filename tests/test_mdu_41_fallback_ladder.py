#!/usr/bin/env python3
"""MDU-41 tests: the paid-spawn fallback ladder.

The ladder is prompt-only policy: one retry, exactly one rotation to a verified
live ``opencode-go/*`` model, then stop and escalate with evidence; ``xai/*``
spawns get no ladder at all. It replaces the old "escalate one rung" bullet.

Coverage maps to design doc ``docs/design/mdu-41-fallback-policy.md`` D11:

* D3 block byte-identical (and unique) in every orchestrator mirror, overlay
  grokestrator included via the ``test_mdu_34`` optional-sibling pattern;
* D6 root-session-id sentence in every orchestrator mirror;
* D5 architect live-probe clause in both architect mirrors + the
  ``research`` -> ``deep-research`` delegation fix;
* drift tokens (``mimo-v2.5``, ``big-pickle``, ``zen``, ``-free``, the retired
  "escalate one rung" wording) absent from the live prompt surface;
* rotation-list membership in the allowed seven-model set;
* ``docs/fallback-ladder.md`` carries the block, the dead list, the ``xai/*``
  rationale, the free-model guard and the maintenance procedure;
* ``evals/tasks/05-fallback-ladder/driver.sh`` is executable, offline, passes
  against this repo, and reds on a tampered mirror copy.

Path independence: every path resolves off ``__file__``, and the driver test
runs with an unrelated cwd, so the suite passes from any directory.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

ORCHESTRATOR_PROMPT = REPO_ROOT / "prompts" / "orchestrator.md"
ORCHESTRATOR_GROK = REPO_ROOT / "grok" / "agents" / "orchestrator.md"
BASE_ORCHESTRATOR_FILES = (ORCHESTRATOR_PROMPT, ORCHESTRATOR_GROK)

#: Private overlay sibling; absent in a standalone clone of the public base.
OVERLAY_GROKESTRATOR = (
    REPO_ROOT.parent / "opencode_agents" / "grok" / "agents" / "grokestrator.md"
)

ARCHITECT_PROMPT = REPO_ROOT / "prompts" / "architect.md"
ARCHITECT_GROK = REPO_ROOT / "grok" / "agents" / "architect.md"
ARCHITECT_FILES = (ARCHITECT_PROMPT, ARCHITECT_GROK)

DOC = REPO_ROOT / "docs" / "fallback-ladder.md"
SKILL = REPO_ROOT / "skills" / "mdu-lifecycle" / "SKILL.md"
DRIVER = REPO_ROOT / "evals" / "tasks" / "05-fallback-ladder" / "driver.sh"
TASK = REPO_ROOT / "evals" / "tasks" / "05-fallback-ladder" / "task.md"

#: D3 — the exact policy block, byte-identical in all three mirrors.
LADDER_BLOCK = (
    "- **PAID-SPAWN FAILURE LADDER — ONE RETRY, ONE ROTATION, THEN STOP:**\n"
    "  When a paid `opencode-go/*` spawn dies on a cap/provider error, quota refusal, or credit exhaustion (e.g. a child reporting `provider.quota`, a 429, or a spent-credit refusal):\n"
    "  1. Retry the same failure once — same model, in the same or a fresh spawn. One retry only; it exists to absorb transient blips.\n"
    "  2. If the failure repeats, make exactly ONE rotation to a different `opencode-go/*` model from the verified live rotation list: deepseek-v4.1-flash, glm-5.2, glm-5.3, glm-5.3-flash, kimi-k2.7-code, mimo-v2.6-flash, mimo-v2.6-pro. A role-rung escalation (`just-code` → `just-code-mid`) counts as the one rotation. Never rotate to an unverified model, and never substitute a free model — free variants no longer exist; fallback drift must not reintroduce them.\n"
    "  3. If the rotated spawn also fails, STOP. Escalate to the user with the failure evidence: both error reports and both model ids. Never a second silent rotation.\n"
    "  This ladder specializes the retry guardrail for this failure class; it never expands the fourth-retry gate.\n"
    "  `xai/*` (grok-family) spawns get NO ladder: a cap, credit, or auth error there escalates directly to the user with the evidence. The xAI account auto-tops-up, so such errors are auth-shaped — silent self-recovery would mask them.\n"
)
LADDER_ANCHOR = "- **PAID-SPAWN FAILURE LADDER"

#: D6 — appended to the introspect step of every orchestrator mirror.
SESSION_ID_SENTENCE = (
    "Include the root session id when introspecting (`--session-id`, e.g. "
    "`OPENCODE_SESSION_ID`); without it the introspector reads a stale session "
    "tree."
)

#: D5 — design-time live-probe clause, byte-identical in both architect mirrors.
ARCHITECT_PROBE_CLAUSE = (
    '- **Probe every model id you assign, at design time:** a registry "active" '
    "status is untrusted — a listed model can be dead upstream. Before handing a "
    "design to implementation, verify each `opencode-go/*` / `xai/*` model id the "
    'design assigns with a one-shot live probe (e.g. `timeout 90 opencode run -m '
    '<id> "Reply with exactly: OK"`) and require exactly `OK` back. On a failed '
    "probe, assign a different live model, record the swap in the design doc, and "
    "re-probe. Never hand implementers or test-agents a model id you have not "
    "seen answer."
)

#: The seven verified live rotation targets, in block order.
ROTATION_ALLOWED = (
    "deepseek-v4.1-flash",
    "glm-5.2",
    "glm-5.3",
    "glm-5.3-flash",
    "kimi-k2.7-code",
    "mimo-v2.6-flash",
    "mimo-v2.6-pro",
)
#: Dead upstream; allowed only in docs/fallback-ladder.md's dead list.
DEAD_MODEL_IDS = ("mimo-v2.5",)
#: Retired tier tokens; must never reappear on the live prompt surface.
RETIRED_TIER_TOKENS = ("big-pickle", "zen")
#: The superseded MDU-40 fallback wording.
OLD_RUNG_PHRASE = "escalate one rung"

CANONICAL_SENTENCE = (
    "All loop phases run on paid models; free-tier variants are retired (MDU-40)."
)
ROTATION_PREFIX = "rotation list: "
ROTATION_SUFFIX = ". A role-rung escalation"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _all_mirrors() -> list[Path]:
    files = list(BASE_ORCHESTRATOR_FILES)
    if OVERLAY_GROKESTRATOR.exists():
        files.append(OVERLAY_GROKESTRATOR)
    return files


def _mirror_ids() -> list[Path]:
    return [path for path in _all_mirrors() if path.is_file()]


def _extract_block(text: str) -> str | None:
    """Slice the ladder block by indentation shape, not by assumed length."""
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if not line.startswith(LADDER_ANCHOR):
            continue
        block = [line]
        for following in lines[index + 1:]:
            if not following.startswith("  ") or not following.strip():
                break
            block.append(following)
        return "".join(block)
    return None


def _rotation_ids(block: str) -> list[str]:
    start = block.find(ROTATION_PREFIX)
    assert start != -1, "block has no inline rotation list"
    start += len(ROTATION_PREFIX)
    end = block.find(ROTATION_SUFFIX, start)
    assert end != -1, "block's rotation list is not terminated by the rung note"
    return [part.strip() for part in block[start:end].split(",")]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _run_driver(repo_root: Path, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["sh", str(repo_root / "evals" / "tasks" / "05-fallback-ladder" / "driver.sh")],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


# ---------------------------------------------------------------------------
# 1. D3 block parity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", _mirror_ids(), ids=lambda p: p.name)
def test_ladder_block_appears_exactly_once(path: Path) -> None:
    text = _read(path)
    assert text.count(LADDER_BLOCK) == 1, f"{path}: block missing or duplicated"


def test_ladder_block_is_byte_identical_across_mirrors() -> None:
    mirrors = _mirror_ids()
    assert len(mirrors) >= 2, "no base mirrors found"
    extracted = {}
    for path in mirrors:
        block = _extract_block(_read(path))
        assert block is not None, f"{path}: no ladder block anchor"
        extracted[path] = block
    reference = extracted[mirrors[0]]
    assert reference == LADDER_BLOCK, (
        f"{mirrors[0].name}: block drifted from the pinned D3 text\n"
        f"expected:\n{LADDER_BLOCK}\nactual:\n{reference}"
    )
    for path, block in extracted.items():
        assert block == reference, f"{path.name}: block differs from {mirrors[0].name}"


def test_block_carries_the_readable_failure_aliases() -> None:
    for path in _mirror_ids():
        block = _extract_block(_read(path))
        assert block is not None, path
        assert "spawns get NO ladder" in block, path
        assert "never substitute a free model" in block, path
        assert "STOP" in block and "both error reports and both model ids" in block, path


def test_block_is_self_contained() -> None:
    """No doc paths or per-harness wording inside the block (runtime portability)."""
    for path in _mirror_ids():
        block = _extract_block(_read(path))
        assert block is not None, path
        assert "docs/" not in block, path
        assert "fallback-ladder.md" not in block, path


def test_mirrors_keep_the_mdu_40_paid_sentence() -> None:
    """The MDU-41 block is additive; MDU-40's canonical sentence stays."""
    for path in _mirror_ids():
        assert CANONICAL_SENTENCE in _read(path), path


# ---------------------------------------------------------------------------
# 2. rotation list membership
# ---------------------------------------------------------------------------

def test_every_rotation_id_is_from_the_verified_live_set() -> None:
    allowed = set(ROTATION_ALLOWED)
    for path in _mirror_ids():
        block = _extract_block(_read(path))
        assert block is not None, path
        ids = _rotation_ids(block)
        assert ids == list(ROTATION_ALLOWED), (path, ids)
        assert set(ids) == allowed, (path, set(ids) - allowed)
        for dead in DEAD_MODEL_IDS:
            assert dead not in ids, (path, dead)


def test_rotation_list_is_not_narrowed_in_any_mirror() -> None:
    for path in _mirror_ids():
        block = _extract_block(_read(path))
        assert block is not None, path
        for model in ROTATION_ALLOWED:
            assert model in block, (path, model)


# ---------------------------------------------------------------------------
# 3. drift tokens
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", _mirror_ids(), ids=lambda p: p.name)
def test_dead_and_retired_model_tokens_absent(path: Path) -> None:
    text = _read(path)
    for token in DEAD_MODEL_IDS:
        assert token not in text, (path, token)
    for token in RETIRED_TIER_TOKENS:
        assert token not in text, (path, token)


@pytest.mark.parametrize("path", _mirror_ids(), ids=lambda p: p.name)
def test_no_free_variant_token_in_mirrors(path: Path) -> None:
    text = _read(path)
    assert re.search(r"\b[\w.]*-free\b", text) is None, path
    assert "free-tier variants are retired" in text, path  # the only free mention


def test_old_rung_phrase_retired() -> None:
    assert OLD_RUNG_PHRASE not in _read(ORCHESTRATOR_PROMPT)
    assert OLD_RUNG_PHRASE not in _read(SKILL)
    # The replacement semantics are explicit in the prompt mirror.
    assert "one retry" in _read(ORCHESTRATOR_PROMPT).lower()
    assert "exactly ONE rotation" in _read(ORCHESTRATOR_PROMPT)


# ---------------------------------------------------------------------------
# 4. D6 introspector session-id sentence
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", _mirror_ids(), ids=lambda p: p.name)
def test_root_session_id_sentence_present_once(path: Path) -> None:
    text = _read(path)
    assert text.count(SESSION_ID_SENTENCE) == 1, f"{path}: D6 sentence missing or duplicated"
    # It must live in the introspect step, not somewhere unrelated.
    assert "--session-id" in text, path


# ---------------------------------------------------------------------------
# 5. D5 architect clause + dead-agent delegation fix
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", ARCHITECT_FILES, ids=lambda p: p.parent.name)
def test_architect_probe_clause_byte_identical(path: Path) -> None:
    text = _read(path)
    assert text.count(ARCHITECT_PROBE_CLAUSE) == 1, (
        f"{path}: probe clause missing or duplicated"
    )
    assert '"Reply with exactly: OK"' in text, path


def test_architect_mirrors_agree_on_the_probe_clause() -> None:
    texts = [_read(path) for path in ARCHITECT_FILES]
    for text in texts[1:]:
        start = text.find("- **Probe every model id you assign")
        assert start != -1
        line = text[start:].splitlines()[0]
        assert line == ARCHITECT_PROBE_CLAUSE, "architect mirrors drifted"


def test_architect_mirrors_delegate_to_deep_research() -> None:
    for path in ARCHITECT_FILES:
        text = _read(path)
        assert "Delegate to `deep-research`" in text, path
        # The MDU-40-deleted bare research agent must not be named as a target.
        assert "Delegate to `research`" not in text, path
        assert "the research agent" not in text, path
        assert "agent: research" not in text, path
        assert "`research` agent" not in text, path


# ---------------------------------------------------------------------------
# 6. docs/fallback-ladder.md
# ---------------------------------------------------------------------------

def test_docs_file_carries_the_block_byte_identically() -> None:
    assert DOC.is_file(), "docs/fallback-ladder.md is missing"
    text = _read(DOC)
    assert text.count(LADDER_BLOCK) == 1, "docs block drifted from the mirrors"
    fenced = re.search(r"```markdown\n(.*?)\n```", text, re.S)
    assert fenced is not None, "docs has no fenced markdown block"
    assert fenced.group(1) + "\n" == LADDER_BLOCK


def test_docs_file_has_the_required_sections() -> None:
    text = _read(DOC)
    for heading in (
        "## The exact block",
        "## Decision table",
        "## Verified live rotation list",
        "## Why `xai/*` has no ladder",
        "## The free-model guard",
        "## Worked dry-run example",
        "## Maintenance procedure",
    ):
        assert heading in text, heading


def test_docs_dead_list_and_live_list() -> None:
    text = _read(DOC)
    assert "**Dead list — never a rotation target:**" in text
    for dead in DEAD_MODEL_IDS:
        assert f"`{dead}`" in text, dead
    for model in ROTATION_ALLOWED:
        assert model in text, model


def test_docs_xai_rationale_and_free_guard() -> None:
    text = _read(DOC)
    assert "auto-tops-up" in text
    assert "auth" in text
    assert "mask" in text
    assert "never substitute a free model" in text
    # Enforcement chain: deletion, paid census, parity tests.
    for link in ("Deletion", "Paid census", "Parity tests"):
        assert link in text, link


def test_docs_maintenance_procedure_names_the_five_touch_points() -> None:
    text = _read(DOC)
    section = text[text.index("## Maintenance procedure"):]
    assert "the block in all three mirrors" in section
    assert "this document" in section
    assert "the block constant in the base and overlay test files" in section
    assert "same" in section and "commit" in section


def test_docs_worked_example_matches_the_driver_shape() -> None:
    text = _read(DOC)
    section = text[text.index("## Worked dry-run example"):]
    for case in range(1, 7):
        assert f"[case {case}]" in section, case
    assert "PASS fallback-ladder" in section


# ---------------------------------------------------------------------------
# 7. skills/mdu-lifecycle/SKILL.md — the third copy
# ---------------------------------------------------------------------------

def test_skill_carries_the_ladder_wording() -> None:
    text = _read(SKILL)
    assert "one retry, then exactly one rotation" in text
    assert "`xai/*` spawns: no ladder — escalate directly" in text
    assert "Never substitute a free model (MDU-41)" in text


# ---------------------------------------------------------------------------
# 8. evals/tasks/05-fallback-ladder — scripted dry run
# ---------------------------------------------------------------------------

def test_driver_and_task_exist_and_driver_is_executable() -> None:
    assert TASK.is_file(), "task.md is missing"
    assert DRIVER.is_file(), "driver.sh is missing"
    assert DRIVER.stat().st_mode & 0o111, "driver.sh is not executable"
    assert "PASS fallback-ladder" in _read(TASK)


def test_driver_is_offline_and_makes_no_model_calls() -> None:
    text = _read(DRIVER)
    for forbidden in ("curl", "wget", "opencode run", "npx", "pip install"):
        assert forbidden not in text, forbidden
    # No command in the driver can block: it only shells out to grep/mktemp.
    for blocking in ("sleep ", "read -p", "nc ", "ssh "):
        assert blocking not in text, blocking


def test_driver_passes_against_the_repo(tmp_path: Path) -> None:
    # Unrelated cwd: proves the driver's repo resolution is path-relative.
    proc = _run_driver(REPO_ROOT, tmp_path)
    output = proc.stdout + proc.stderr
    assert proc.returncode == 0, output
    for case in range(1, 7):
        assert f"[case {case}]" in proc.stdout, output
    assert "PASS fallback-ladder" in proc.stdout
    assert "FAIL" not in proc.stdout


def test_driver_reds_on_a_tampered_mirror_copy(tmp_path: Path) -> None:
    """Copy the tree to /tmp, mutate one mirror's block sentence, expect a red.

    The driver has no path argument (it derives the repo root from its own
    location), so the copy reproduces the same relative layout under tmp_path.
    """
    copy = tmp_path / "repo"
    (copy / "evals" / "tasks" / "05-fallback-ladder").mkdir(parents=True)
    (copy / "prompts").mkdir()
    (copy / "grok" / "agents").mkdir(parents=True)
    driver_copy = copy / "evals" / "tasks" / "05-fallback-ladder" / "driver.sh"
    shutil.copy2(DRIVER, driver_copy)
    prompt_copy = copy / "prompts" / "orchestrator.md"
    shutil.copy2(ORCHESTRATOR_PROMPT, prompt_copy)
    shutil.copy2(ORCHESTRATOR_GROK, copy / "grok" / "agents" / "orchestrator.md")

    # Control: the unmutated copy is green (the layout is sound).
    control = _run_driver(copy, tmp_path)
    assert control.returncode == 0, control.stdout + control.stderr

    # Tamper: drop the case-1 governing sentence from one mirror only.
    prompt_copy.write_text(
        _read(prompt_copy).replace(
            "Retry the same failure once — same model, in the same or a fresh spawn.",
            "Retry at most once.",
        ),
        encoding="utf-8",
    )
    proc = _run_driver(copy, tmp_path)
    output = proc.stdout + proc.stderr
    assert proc.returncode != 0, output
    assert "FAIL fallback-ladder" in proc.stdout, output
    assert "[warn] case 1" in proc.stdout, output
    assert "missing in:" in output, output
    # Cases 2-6 still resolve: only the tampered sentence is reported.
    assert "[warn] case 2" not in output, output


def test_driver_skips_the_overlay_mirror_when_absent(tmp_path: Path) -> None:
    """The public repo stays self-contained: 2/2 mirrors without the sibling."""
    copy = tmp_path / "repo"
    (copy / "evals" / "tasks" / "05-fallback-ladder").mkdir(parents=True)
    (copy / "prompts").mkdir()
    (copy / "grok" / "agents").mkdir(parents=True)
    shutil.copy2(DRIVER, copy / "evals" / "tasks" / "05-fallback-ladder" / "driver.sh")
    shutil.copy2(ORCHESTRATOR_PROMPT, copy / "prompts" / "orchestrator.md")
    shutil.copy2(ORCHESTRATOR_GROK, copy / "grok" / "agents" / "orchestrator.md")

    proc = _run_driver(copy, tmp_path)
    output = proc.stdout + proc.stderr
    assert proc.returncode == 0, output
    assert "[policy sentence found in 2/2 mirrors]" in proc.stdout, output
