"""Acceptance contracts for MDU-04 (lightweight persistent memory convention).

MDU-04 adds a normative memory rule block to both base orchestrator mirrors
(Claude inherits via build-time generation) and documents the convention in the
README. Memory is plain markdown in ``.agents/memory/`` at the project being
worked on: ``project.md`` / ``decisions.md`` / ``session-<id>.md``, each with
YAML frontmatter (``type``, ``created``, ``updated``) and an append-only body.

These tests cover the *scriptable* half of the design doc's acceptance plan
(``docs/design/mdu-04-lightweight-persistent-memory.md``). Harness-level
behavior - a fresh session actually quoting seeded facts, resume without
re-deriving phase 1 - is graded by QA from session transcripts, not here.

Coverage map:

- Test 1: the rule block tells a fresh session to read memory on start and
  tail-read only the newest checkpoint; the seeded facts a project would carry
  are greppable.
- Test 2: the ``mdu-complete`` entry shape (frontmatter regex, entry header,
  field set, SHA/ledger cross-references) and append-only discipline.
- Test 3: the ``checkpoint`` entry shape and its four non-empty fields.
- Test 4: README section content and its link to this design doc.

Design doc: ``docs/design/mdu-04-lightweight-persistent-memory.md``.
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

ORCHESTRATOR_PROMPT = REPO_ROOT / "prompts" / "orchestrator.md"
ORCHESTRATOR_GROK = REPO_ROOT / "grok" / "agents" / "orchestrator.md"
README = REPO_ROOT / "README.md"
DESIGN_DOC = REPO_ROOT / "docs" / "design" / "mdu-04-lightweight-persistent-memory.md"

# Private overlay sibling; absent in a standalone clone of the public base.
OVERLAY_GROKESTRATOR = (
    REPO_ROOT.parent / "opencode_agents" / "grok" / "agents" / "grokestrator.md"
)

BASE_ORCHESTRATOR_FILES = [ORCHESTRATOR_PROMPT, ORCHESTRATOR_GROK]

# Block span: anchor line through the line before the next top-level section.
MEMORY_ANCHOR = (
    "- **Maintain persistent memory in `.agents/memory/` at the project being worked on**"
)
MEMORY_END = "\nHard constraints:"

# Contract points 1-7 of the design doc, as lowercase substrings that survive
# rewording. Each tuple is (label, required fragment).
CONTRACT_FRAGMENTS = [
    ("read on session start", "on session start:** read `.agents/memory/project.md`"),
    ("tail-read tactic", "do not bulk-read session history"),
    ("mdu-complete append", "**after each mdu is committed and pushed:**"),
    ("checkpoint before turn end", "append the checkpoint **before** ending the turn"),
    ("resume block wins", "the pasted resume block wins if it disagrees"),
    ("project facts", "**append to `project.md`:**"),
    ("single writer", "**single writer:**"),
    ("secret / unwritable safety", "never write secrets into memory"),
]

ISO_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
FRONTMATTER = re.compile(
    r"\A---\ntype: (project|decisions|session)\n"
    r"created: (\S+)\nupdated: (\S+)\n---\n"
)
# Closed entry set: session-start, mdu-complete (<id>), checkpoint (<id>).
ENTRY_HEADER = re.compile(
    r"^## (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) — "
    r"(session-start|mdu-complete \(([a-z0-9-]+)\)|checkpoint \(([a-z0-9-]+)\))$"
)
MD_COMPLETE_FIELDS = {"mdu_id", "branch", "commit", "summary", "key_decisions", "ledger"}
CHECKPOINT_FIELDS = {"completed", "next", "blockers", "artifacts"}

SEED_PROJECT = """---
type: project
created: 2026-10-01T09:00:00Z
updated: 2026-10-01T09:00:00Z
---
## Build & Test
- ZUNIQUE_FACT: run `timeout 60 ./run_tests.sh` before any commit.
"""

SEED_DECISIONS = """---
type: decisions
created: 2026-10-01T09:00:00Z
updated: 2026-10-01T09:00:00Z
---
## 2026-10-01 — Use tabs not spaces (TEST-00)
- Context: mixed indentation caused diff noise.
- Decision: tabs everywhere in scripts.
- Consequences: editorconfig updated.
"""

SEED_SESSION = """---
type: session
created: 2026-10-01T09:00:00Z
updated: 2026-10-01T09:30:00Z
---
## 2026-10-01T09:30:00Z — checkpoint (mdu-test-prev)
completed: prior phase done
next: nothing pending
blockers: none
artifacts: none
"""


# --------------------------------------------------------------- helpers


def _lower(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def _memory_span(path: Path) -> str:
    """Return the raw rule block, anchor through the line before 'Hard constraints:'."""
    text = path.read_text(encoding="utf-8")
    start = text.find(MEMORY_ANCHOR)
    assert start != -1, f"{path.name} has no memory rule block anchor"
    end = text.find(MEMORY_END, start)
    assert end != -1, f"{path.name}: memory block has no 'Hard constraints:' after it"
    return text[start:end]


def _frontmatter_ok(text: str) -> bool:
    """True when frontmatter matches the shape *and* both stamps are ISO-8601 Z."""
    match = FRONTMATTER.match(text)
    return bool(
        match
        and ISO_TS.match(match.group(2))
        and ISO_TS.match(match.group(3))
    )


def _parse_frontmatter(text: str) -> tuple[re.Match[str], str]:
    match = FRONTMATTER.match(text)
    assert match, f"frontmatter does not match the MDU-04 contract:\n{text[:120]!r}"
    return match, text[match.end():]


def _entries(body: str) -> list[tuple[re.Match[str], dict[str, str]]]:
    """Entry headers plus their field maps (keys split on '·' for packed lines)."""
    lines = body.splitlines()
    found: list[tuple[re.Match[str], dict[str, str]]] = []
    for index, line in enumerate(lines):
        header = ENTRY_HEADER.match(line)
        if not header:
            continue
        fields: dict[str, str] = {}
        for follow in lines[index + 1:]:
            if follow.startswith("## "):
                break
            for part in follow.split(" · "):
                if ": " in part:
                    key, value = part.split(": ", 1)
                    fields[key.strip()] = value.strip()
        found.append((header, fields))
    return found


def _removed_lines(before: str, after: str) -> list[str]:
    """Diff lines removed from a pre-existing entry, ignoring the `updated:` bump.

    Design doc: appends add only `+` lines; the sole permitted mutation is the
    frontmatter `updated:` bump, so a removal outside that is a violation.
    """
    diff = list(difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm=""))
    return [
        line
        for line in diff
        if line.startswith("-")
        and not line.startswith("---")
        and not line.startswith("-updated: ")
    ]


# ------------------------------------------------------- rule block exists


def test_memory_block_present_in_both_mirrors() -> None:
    for path in BASE_ORCHESTRATOR_FILES:
        assert path.exists(), f"missing {path}"
        low = _lower(path)
        assert MEMORY_ANCHOR.lower() in low, f"{path.name} missing the memory rule block"
        assert ".agents/memory/" in low
        for label, fragment in CONTRACT_FRAGMENTS:
            assert fragment in low, f"{path.name} missing contract point: {label}"


def test_memory_block_byte_identical_across_mirrors() -> None:
    spans = {path: _memory_span(path) for path in BASE_ORCHESTRATOR_FILES}
    reference_path = BASE_ORCHESTRATOR_FILES[0]
    reference = spans[reference_path]
    assert len(reference) > 1000, "memory block span looks truncated"
    for path in BASE_ORCHESTRATOR_FILES[1:]:
        assert spans[path] == reference, (
            f"memory block in {path} differs from {reference_path} "
            f"({len(spans[path])} vs {len(reference)} chars)"
        )


def test_memory_block_sits_after_run_ledger_before_hard_constraints() -> None:
    for path in BASE_ORCHESTRATOR_FILES:
        text = path.read_text(encoding="utf-8")
        ledger = text.find("run_ledger.py validate")
        anchor = text.find(MEMORY_ANCHOR)
        constraints = text.find(MEMORY_END)
        assert ledger != -1, f"{path.name}: run-ledger bullet missing"
        assert -1 < ledger < anchor < constraints, (
            f"{path.name}: memory block must follow the run-ledger bullet "
            f"({ledger}) and precede 'Hard constraints:' ({constraints}), "
            f"found at {anchor}"
        )
        # Immediate adjacency: one blank line, no invented sub-section.
        between = text[ledger:anchor]
        assert between.rstrip().endswith(
            "commit the manifest with the code."
        ), f"{path.name}: unexpected content between ledger and memory blocks"


def test_memory_block_present_in_overlay_grokestrator() -> None:
    if not OVERLAY_GROKESTRATOR.is_file():
        pytest.skip("overlay sibling not present (standalone base clone)")
    low = _lower(OVERLAY_GROKESTRATOR)
    assert MEMORY_ANCHOR.lower() in low, "grokestrator missing the memory rule block"
    for label, fragment in CONTRACT_FRAGMENTS:
        assert fragment in low, f"grokestrator missing contract point: {label}"


# ------------------------------------------------ Test 1: facts are readable


def test_seeded_project_facts_are_greppable(tmp_path: Path) -> None:
    memory = tmp_path / ".agents" / "memory"
    memory.mkdir(parents=True)
    (memory / "project.md").write_text(SEED_PROJECT, encoding="utf-8")
    (memory / "decisions.md").write_text(SEED_DECISIONS, encoding="utf-8")

    project = (memory / "project.md").read_text(encoding="utf-8")
    assert "ZUNIQUE_FACT" in project
    assert "run_tests.sh" in project
    assert "tabs" in (memory / "decisions.md").read_text(encoding="utf-8").lower()


def test_frontmatter_regex_accepts_spec_shape_and_rejects_drift(tmp_path: Path) -> None:
    good = tmp_path / "session.md"
    good.write_text(SEED_SESSION, encoding="utf-8")
    match, body = _parse_frontmatter(good.read_text(encoding="utf-8"))
    assert match.group(1) == "session"
    assert ISO_TS.match(match.group(2)) and ISO_TS.match(match.group(3))

    bad_variants = {
        "offset not Z": SEED_SESSION.replace("2026-10-01T09:00:00Z", "2026-10-01T09:00:00+00:00"),
        "no seconds": SEED_SESSION.replace("2026-10-01T09:00:00Z", "2026-10-01T09:00Z"),
        "unknown type": SEED_SESSION.replace("type: session", "type: journal"),
        "missing created": SEED_SESSION.replace("created: 2026-10-01T09:00:00Z\n", ""),
    }
    for label, text in bad_variants.items():
        assert not _frontmatter_ok(text), f"frontmatter accepted drift: {label}"
    assert body.startswith("## ")


# ------------------------------------------- Test 2: mdu-complete + append-only


def test_mdu_complete_entry_shape(tmp_path: Path) -> None:
    path = tmp_path / "session-20261021-1002.md"
    path.write_text(
        "---\ntype: session\ncreated: 2026-10-21T10:02:00Z\n"
        "updated: 2026-10-21T10:41:00Z\n---\n"
        "## 2026-10-21T10:02:00Z — session-start\n"
        "harness: opencode · goal: MDU-TEST-04 mock\n"
        "\n"
        "## 2026-10-21T10:41:00Z — mdu-complete (mdu-test-04)\n"
        "mdu_id: mdu-test-04 · branch: mdu-test-04-memory · commit: 1a2b3c4 · qa: PASS\n"
        "summary: appended one line to NOTES.md via the full loop\n"
        "key_decisions: memory writes are append-only; one line per field\n"
        "ledger: runs/mdu-test-04/manifest.json\n",
        encoding="utf-8",
    )
    _, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
    entries = _entries(body)
    assert [m.group(2).split(" ")[0] for m, _ in entries] == ["session-start", "mdu-complete"]

    header, fields = entries[1]
    assert header.group(3) == "mdu-test-04"
    assert MD_COMPLETE_FIELDS <= fields.keys(), f"missing {MD_COMPLETE_FIELDS - fields.keys()}"
    assert re.fullmatch(r"[0-9a-f]{7,40}", fields["commit"]), fields["commit"]
    assert re.fullmatch(r"runs/mdu-test-04/manifest\.json", fields["ledger"]), fields["ledger"]
    assert "\n" not in fields["summary"]


def test_checkpoint_entry_shape(tmp_path: Path) -> None:
    path = tmp_path / "session-20261021-1002.md"
    path.write_text(
        SEED_SESSION
        + "\n## 2026-10-21T11:05:00Z — checkpoint (mdu-test-05)\n"
        "completed: design doc written (docs/design/mdu-test-05.md)\n"
        "next: phase 2 — implement from DESIGN.md\n"
        "blockers: none\n"
        "artifacts: DESIGN.md\n",
        encoding="utf-8",
    )
    _, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
    checkpoints = [f for m, f in _entries(body) if m.group(4) == "mdu-test-05"]
    assert checkpoints, "no checkpoint entry for mdu-test-05"
    fields = checkpoints[0]
    assert CHECKPOINT_FIELDS <= fields.keys(), f"missing {CHECKPOINT_FIELDS - fields.keys()}"
    assert all(fields[name] for name in CHECKPOINT_FIELDS), "checkpoint fields must be non-empty"
    assert "DESIGN.md" in fields["artifacts"] and "phase 2" in fields["next"]


def test_tail_read_finds_newest_checkpoint_across_sessions(tmp_path: Path) -> None:
    """Contract point 2: resume reads only the newest checkpoint of the newest session.

    A session that follows the rule must locate the newest `checkpoint` entry
    across `session-*.md` by header timestamp, must not mistake an `mdu-complete`
    entry for a checkpoint, and must not need the whole file.
    """
    memory = tmp_path / ".agents" / "memory"
    memory.mkdir(parents=True)
    (memory / "session-20261001-0900.md").write_text(
        SEED_SESSION, encoding="utf-8"
    )
    (memory / "session-20261021-1002.md").write_text(
        "---\ntype: session\ncreated: 2026-10-21T10:02:00Z\n"
        "updated: 2026-10-21T11:05:00Z\n---\n"
        "## 2026-10-21T10:02:00Z — session-start\nharness: opencode · goal: mdu-32\n"
        "\n## 2026-10-21T10:41:00Z — mdu-complete (mdu-31)\n"
        "mdu_id: mdu-31 · branch: mdu-31-repo-ownership · commit: 1a2b3c4 · qa: PASS\n"
        "summary: repo-ownership gate added\n"
        "key_decisions: per-action approval\n"
        "ledger: runs/mdu-31/manifest.json\n"
        "\n## 2026-10-21T10:50:00Z — checkpoint (mdu-32)\n"
        "completed: design doc written\n"
        "next: implement-phase brief to just-code\n"
        "blockers: none\n"
        "artifacts: docs/design/mdu-32-*.md\n"
        "\n## 2026-10-21T11:05:00Z — checkpoint (mdu-32)\n"
        "completed: design doc reviewed\n"
        "next: implement-phase brief to just-code\n"
        "blockers: none\n"
        "artifacts: docs/design/mdu-32-*.md\n",
        encoding="utf-8",
    )

    def newest_checkpoint() -> tuple[str, dict[str, str]]:
        best: tuple[str, dict[str, str]] | None = None
        for path in sorted(memory.glob("session-*.md")):
            _, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
            for header, fields in _entries(body):
                if header.group(4) is None:  # checkpoint only, never mdu-complete
                    continue
                if best is None or header.group(1) > best[0]:
                    best = (header.group(1), fields)
        assert best is not None, "no checkpoint entry found"
        return best

    stamp, fields = newest_checkpoint()
    assert stamp == "2026-10-21T11:05:00Z", f"picked stale checkpoint {stamp}"
    assert fields["completed"] == "design doc reviewed"
    assert CHECKPOINT_FIELDS <= fields.keys()


def test_entry_header_rejects_out_of_set_entries() -> None:
    for line in (
        "## 2026-10-21T11:05:00Z — session-end",
        "## 2026-10-21T11:05:00Z — mdu-complete",
        "## 2026-10-21 — checkpoint (mdu-test-05)",
        "## 2026-10-21T11:05:00Z — checkpoint (MDU-Test-05)",
    ):
        assert ENTRY_HEADER.match(line) is None, f"accepted out-of-set header {line!r}"
    for line in (
        "## 2026-10-21T11:05:00Z — session-start",
        "## 2026-10-21T11:05:00Z — mdu-complete (mdu-31)",
        "## 2026-10-21T11:05:00Z — checkpoint (mdu-32)",
    ):
        assert ENTRY_HEADER.match(line) is not None, f"rejected valid header {line!r}"


def test_append_only_bump_of_updated_is_the_only_allowed_mutation(tmp_path: Path) -> None:
    before = SEED_DECISIONS
    appended = before.replace(
        "updated: 2026-10-01T09:00:00Z", "updated: 2026-10-21T12:00:00Z"
    ) + (
        "\n## 2026-10-21 — Memory writes are append-only (mdu-test-04)\n"
        "- Context: session logs are reviewed in PRs.\n"
        "- Decision: append entries, never rewrite them.\n"
        "- Consequences: corrections are superseding lines.\n"
    )
    assert _removed_lines(before, appended) == [], "legitimate append flagged"

    rewritten = before.replace("tabs everywhere in scripts.", "spaces everywhere.")
    assert _removed_lines(before, rewritten), "rewrite of an old line was not flagged"

    reordered = SEED_DECISIONS.replace(
        "- Context: mixed indentation caused diff noise.\n"
        "- Decision: tabs everywhere in scripts.\n",
        "- Decision: tabs everywhere in scripts.\n"
        "- Context: mixed indentation caused diff noise.\n",
    )
    assert _removed_lines(SEED_DECISIONS, reordered), "field reorder was not flagged"


# ------------------------------------------------- Test 4: README documents it


def _readme_section() -> str:
    text = README.read_text(encoding="utf-8")
    heading = re.search(r"^#{2,3} Persistent Memory\s*$", text, re.MULTILINE)
    assert heading, "README has no 'Persistent Memory' section"
    start = heading.end()
    following = re.search(r"^#{2,3} ", text[start:], re.MULTILINE)
    return text[start:start + following.start()] if following else text[start:]


def test_readme_documents_the_convention() -> None:
    section = _readme_section().lower()
    for name in ("project.md", "decisions.md", "session-<id>.md"):
        assert name in section, f"README section does not name {name}"
    for key in ("`type`", "`created`", "`updated`"):
        assert key in section, f"README section does not document frontmatter key {key}"
    assert "append-only" in section
    assert "orchestrator" in section
    for entry_type in ("mdu-complete", "checkpoint"):
        assert entry_type in section, f"README section omits the {entry_type} entry type"


def test_readme_links_to_the_design_doc() -> None:
    text = README.read_text(encoding="utf-8")
    link = re.search(r"\]\((docs/design/mdu-04-[^)\s]+)\)", text)
    assert link, "README has no link to the MDU-04 design doc"
    target = REPO_ROOT / link.group(1)
    assert target.is_file(), f"README link target missing: {link.group(1)}"
    assert target.stat().st_size > 2000, "design doc looks empty"
    assert "Acceptance test plan" in target.read_text(encoding="utf-8")
