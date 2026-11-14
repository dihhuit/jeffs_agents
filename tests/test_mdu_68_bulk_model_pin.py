"""MDU-68 bulk model pin, base side.

Constants are the design-doc fences in docs/design/mdu-68-bulk-model-pin.md
(Exact prompt clause, D5, D6, Exact toml block). The one mutation copies
grok/agents/orchestrator.md under /tmp, deletes the clause line, and expects
the presence check to exit non-zero. It does not write the worktree or
~/.grok/config.toml.

The rejected sentence may remain in agent-improvements.md as the historical
suggestion quote. This module does not assert that it is absent there.

Hermetic apart from that /tmp copy: no network, no git calls.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

DESIGN_DOC = Path("docs") / "design" / "mdu-68-bulk-model-pin.md"
BACKLOG = Path("FEATURE_BACKLOG.md")
IMPROVEMENTS = Path("agent-improvements.md")
GROK_ORCHESTRATOR = Path("grok") / "agents" / "orchestrator.md"
PROMPTS_ORCHESTRATOR = Path("prompts") / "orchestrator.md"

# Exact prompt clause. Leading "- " is part of the line.
CLAUSE_LINE = (
    "- On the Grok harness, `spawn_subagent` may have no `model` argument because subagent model inheritance is on and every picker model is xAI. Do not invent one; a named model fails while the argument is hidden. The honored per-type pin is `[subagents.models]` in `~/.grok/config.toml`, read at the next grok process, not by this session. Agent-file `model:` is not that pin. Append the child `effective_model_id` to the manifest phase `notes`. A bulk profile (frontmatter `grok-build-0.1`) whose `effective_model_id` is `grok-4.7` is a tier miss."
)

# Carrier-table successor for grok/agents/orchestrator.md. The dash in the
# D5/D6 lines below is U+2014, matching the design fences.
SUCCESSOR_LINE = (
    "- Rotate through role variants for repeated tasks to avoid exhausting any single agent's rate limits."
)

STATUS_LINE = (
    "- **Status:** Done — 2026-11-14 (user-config `[subagents.models]` pins plus the Grok-only clause; inheritance stays on; the pin is read by the next grok process, not this session.)"
)

CHECKED_LINE = (
    "- [x] id: 20261114-3 | severity: warn | target: orchestrator | kind: expensive_model_on_bulk_role | **RESOLVED 2026-11-14 (mdu-68)**"
)

NOTE_LINE = (
    "  - note (2026-11-14, mdu-68): **RESOLVED** — shipped mechanism is the `[subagents.models]` pin for every frontmatter `grok-build-0.1` name under base `grok/agents/` and overlay `grok/agents/`, plus the Grok-only clause in `grok/agents/orchestrator.md` and overlay `grok/agents/grokestrator.md`. Not the suggestion sentence and not a spawn `model` argument: while inheritance is on, that argument is hidden. `prompts/orchestrator.md` unchanged. The pin is outside git and applies on the next grok process."
)

REJECTED_SENTENCE = "A subagent spawn must pass the profile's frontmatter model."

_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
_PIN_LINE = re.compile(r'^([A-Za-z0-9_-]+) = "([^"]*)"$')

_ORCHESTRATOR_FILES = (GROK_ORCHESTRATOR, PROMPTS_ORCHESTRATOR)


def _read(path: Path) -> str:
    resolved = path.resolve()
    assert resolved.is_relative_to(REPO_ROOT.resolve()), f"path escaped the repo: {resolved}"
    assert resolved.is_file(), f"missing target: {resolved}"
    return resolved.read_text(encoding="utf-8")


def _repo_text(rel: Path) -> str:
    assert not rel.is_absolute()
    return _read(REPO_ROOT / rel)


def _full_line_count(text: str, line: str) -> int:
    """`grep -F -x` equivalent: exact full-line matches only."""
    return sum(1 for candidate in text.splitlines() if candidate == line)


def _frontmatter(text: str) -> dict[str, str]:
    match = _FRONTMATTER.match(text)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def _toml_pins(doc: str) -> dict[str, str]:
    """Keys and values from the design doc's Exact toml block fence."""
    lines = doc.splitlines()
    start = next((i for i, line in enumerate(lines) if line == "## Exact toml block"), None)
    assert start is not None, "design doc is missing the Exact toml block heading"
    open_idx = next((i for i in range(start + 1, len(lines)) if lines[i] == "```toml"), None)
    assert open_idx is not None, "design doc is missing the toml fence"
    close_idx = next((i for i in range(open_idx + 1, len(lines)) if lines[i] == "```"), None)
    assert close_idx is not None, "design doc toml fence is unclosed"
    pins: dict[str, str] = {}
    for line in lines[open_idx + 1 : close_idx]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("["):
            continue
        match = _PIN_LINE.fullmatch(stripped)
        assert match, f"toml fence line is not a pin assignment: {line!r}"
        key, value = match.group(1), match.group(2)
        assert key not in pins, f"duplicate pin key in the toml fence: {key}"
        pins[key] = value
    assert pins, "toml fence has no pin assignments"
    return pins


def _profiles(agents_dir: Path) -> list[tuple[str, str, str]]:
    """(path under agents_dir, frontmatter name, frontmatter model)."""
    assert agents_dir.is_dir(), f"missing agents dir: {agents_dir}"
    found: list[tuple[str, str, str]] = []
    for path in sorted(agents_dir.rglob("*.md")):
        if not path.is_file():
            continue
        meta = _frontmatter(path.read_text(encoding="utf-8"))
        name = meta.get("name", "")
        model = meta.get("model", "")
        rel = path.relative_to(agents_dir).as_posix()
        if model in ("grok-build-0.1", "grok-4.7") and not name:
            raise AssertionError(f"{rel}: model {model} without a frontmatter name")
        if name and model:
            found.append((rel, name, model))
    return found


def _census(agents_dir: Path, pins: dict[str, str]) -> None:
    """Every grok-build-0.1 name is a fence key pinned to that model.

    No grok-4.7 name is a fence key. This does not count files.
    """
    profiles = _profiles(agents_dir)
    bulk = [(rel, name) for rel, name, model in profiles if model == "grok-build-0.1"]
    flagship = [(rel, name) for rel, name, model in profiles if model == "grok-4.7"]
    assert bulk, f"{agents_dir}: census found no grok-build-0.1 frontmatter names"
    missing = sorted(
        f"{name} ({rel})" for rel, name in bulk if pins.get(name) != "grok-build-0.1"
    )
    assert missing == [], f"grok-build-0.1 names missing from the toml fence: {missing}"
    leaked = sorted(f"{name} ({rel})" for rel, name in flagship if name in pins)
    assert leaked == [], f"grok-4.7 names must not be toml pin keys: {leaked}"


def _assert_base_orchestrator_clause(text: str, where: str) -> None:
    """Presence and adjacency for the base grok orchestrator clause."""
    lines = text.splitlines()
    count = _full_line_count(text, CLAUSE_LINE)
    assert text.count(CLAUSE_LINE) == 1 and count == 1, (
        f"{where}: the clause line must occur once as a full line; "
        f"substring {text.count(CLAUSE_LINE)}, full-line {count}"
    )
    idx = lines.index(CLAUSE_LINE)
    assert idx > 0, f"{where}: the clause line has no previous line"
    prev = lines[idx - 1]
    prev_body = prev[2:] if prev.startswith("- ") else prev
    assert prev_body.startswith("Grok Build currently exposes"), (
        f"{where}: previous line does not start with the bulk-rung anchor"
    )
    assert "Bulk profiles use" in prev, (
        f"{where}: previous line does not contain 'Bulk profiles use'"
    )
    assert idx + 1 < len(lines), f"{where}: the clause line has no successor"
    successor = lines[idx + 1]
    successor_body = successor[2:] if successor.startswith("- ") else successor
    assert successor_body.startswith("Rotate through role variants"), (
        f"{where}: successor does not start with the rotate-variants bullet"
    )
    assert successor == SUCCESSOR_LINE, f"{where}: successor drifted: {successor!r}"


def _under_tmp(path: Path) -> None:
    resolved = path.resolve()
    tmp = Path("/tmp").resolve()
    assert resolved == tmp or resolved.is_relative_to(tmp), (
        f"mutation path is not under /tmp: {resolved}"
    )
    assert not resolved.is_relative_to(REPO_ROOT.resolve()), (
        f"mutation path is inside the base worktree: {resolved}"
    )
    overlay = REPO_ROOT.parent / "opencode_agents"
    if overlay.exists():
        assert not resolved.is_relative_to(overlay.resolve()), (
            f"mutation path is inside the overlay worktree: {resolved}"
        )


def _stat_fingerprint(path: Path) -> tuple | None:
    if not path.exists():
        return None
    st = path.stat()
    return (st.st_mode, st.st_size, st.st_mtime_ns, st.st_ino)


# ---------------------------------------------------------------------------
# Design fences — the constants above are the doc lines, not a paraphrase
# ---------------------------------------------------------------------------

def test_design_doc_pins_are_single_full_lines():
    doc = _repo_text(DESIGN_DOC)
    for line, label in (
        (CLAUSE_LINE, "exact prompt clause"),
        (STATUS_LINE, "D6 status line"),
        (CHECKED_LINE, "D5 checked id"),
        (NOTE_LINE, "D5 note"),
    ):
        assert _full_line_count(doc, line) == 1, (
            f"design doc: {label} must be one full line"
        )


# ---------------------------------------------------------------------------
# Clause — once, previous line is the bulk-rung anchor, successor stays
# ---------------------------------------------------------------------------

def test_grok_orchestrator_clause_once_and_adjacent():
    _assert_base_orchestrator_clause(
        _repo_text(GROK_ORCHESTRATOR), GROK_ORCHESTRATOR.as_posix()
    )


def test_prompts_orchestrator_does_not_contain_the_clause():
    text = _repo_text(PROMPTS_ORCHESTRATOR)
    assert CLAUSE_LINE not in text, (
        "prompts/orchestrator.md must not contain the Grok pin clause"
    )
    assert _full_line_count(text, CLAUSE_LINE) == 0


@pytest.mark.parametrize(
    "rel",
    _ORCHESTRATOR_FILES,
    ids=[rel.as_posix() for rel in _ORCHESTRATOR_FILES],
)
def test_rejected_sentence_absent_from_base_orchestrators(rel):
    text = _repo_text(rel)
    assert REJECTED_SENTENCE not in text, (
        f"{rel.as_posix()} must not contain the rejected spawn sentence"
    )


# ---------------------------------------------------------------------------
# D6 backlog row and D5 suggestion checkbox
# ---------------------------------------------------------------------------

def test_backlog_d6_status_line_and_heading():
    text = _repo_text(BACKLOG)
    assert _full_line_count(text, STATUS_LINE) == 1, (
        "FEATURE_BACKLOG.md must contain the D6 status line once"
    )
    headings = [line for line in text.splitlines() if line.startswith("### MDU-68")]
    assert len(headings) == 1, (
        f"FEATURE_BACKLOG.md must have one MDU-68 heading; found {headings!r}"
    )
    assert "queue head" not in headings[0], (
        f"MDU-68 heading contains 'queue head': {headings[0]!r}"
    )


def test_suggestion_20261114_3_checked_and_noted():
    text = _repo_text(IMPROVEMENTS)
    assert _full_line_count(text, CHECKED_LINE) == 1, (
        "agent-improvements.md is missing the D5 checked id line"
    )
    assert _full_line_count(text, NOTE_LINE) == 1, (
        "agent-improvements.md is missing the D5 mdu-68 note"
    )
    assert "- [ ] id: 20261114-3" not in text, (
        "agent-improvements.md still has an unchecked 20261114-3 id"
    )


# ---------------------------------------------------------------------------
# Frontmatter census against the design-doc toml fence. Not a file count.
# ---------------------------------------------------------------------------

def test_frontmatter_census_matches_toml_fence():
    pins = _toml_pins(_repo_text(DESIGN_DOC))
    _census(REPO_ROOT / "grok" / "agents", pins)


# ---------------------------------------------------------------------------
# Mutation — /tmp copy only. Presence check must fail. Worktree stays put.
# ---------------------------------------------------------------------------

def test_mutation_deleted_clause_fails_presence():
    src = REPO_ROOT / GROK_ORCHESTRATOR
    original = src.read_bytes()
    config = Path.home() / ".grok" / "config.toml"
    config_before = _stat_fingerprint(config)
    mutant_root = Path(tempfile.mkdtemp(prefix="mdu68-bulk-model-pin-", dir="/tmp"))
    try:
        _under_tmp(mutant_root)
        dest = mutant_root / "grok" / "agents" / "orchestrator.md"
        _under_tmp(dest)
        assert dest.resolve() != config.resolve()
        dest.parent.mkdir(parents=True)
        text = original.decode("utf-8")
        lines = text.splitlines()
        assert _full_line_count(text, CLAUSE_LINE) == 1, (
            "refusing to mutate a copy that does not carry the clause once"
        )
        stripped = [line for line in lines if line != CLAUSE_LINE]
        payload = "\n".join(stripped)
        if text.endswith("\n"):
            payload += "\n"
        dest.write_text(payload, encoding="utf-8")
        _under_tmp(dest)
        assert CLAUSE_LINE not in dest.read_text(encoding="utf-8")
        assert src.read_bytes() == original

        script = "\n".join(
            (
                "import importlib.util",
                "import pathlib",
                f"path = {str(Path(__file__).resolve())!r}",
                "spec = importlib.util.spec_from_file_location('mdu68_pin_check', path)",
                "assert spec and spec.loader",
                "mod = importlib.util.module_from_spec(spec)",
                "spec.loader.exec_module(mod)",
                f"text = pathlib.Path({str(dest)!r}).read_text(encoding='utf-8')",
                "mod._assert_base_orchestrator_clause(text, 'mutant')",
            )
        )
        proc = subprocess.run(
            [sys.executable, "-c", script],
            cwd="/tmp",
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert proc.returncode != 0, (
            "presence check on the clause-deleted copy exited 0\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
        assert "clause line" in proc.stderr, proc.stderr
        assert src.read_bytes() == original
        assert _stat_fingerprint(config) == config_before
    finally:
        shutil.rmtree(mutant_root, ignore_errors=True)
        assert src.read_bytes() == original
        assert _stat_fingerprint(config) == config_before
