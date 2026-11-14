"""MDU-64 pin: pre-introspect manifest clause in the three source carriers.

Overlay root matches tests/test_mdu_63_guards.py. The cache-miss gate is
re-checked through that module so its line and fragments are not retyped.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
OVERLAY_ROOT = REPO_ROOT.parent / "opencode_agents"
GROKESTRATOR = OVERLAY_ROOT / "grok" / "agents" / "grokestrator.md"

CLAUSE = (
    "Before invoking the introspector, append every phase that has already finished, including qa and validate and deploy when deploy ran, to runs/<mdu-id>/manifest.json with outcome and notes, and set status to `completed` (never `complete`). Set verification.qa_grade when QA has graded. Append the commit phase row at commit time, not before introspection. Never rely on the handoff brief alone as run evidence."
)

BASE_RELS = (
    Path("prompts") / "orchestrator.md",
    Path("grok") / "agents" / "orchestrator.md",
)

STEP7_PREFIX = "  7. Introspect (via `introspector` in **loop mode** only)"
STEP7_END = "stale session tree."
STEP8_PREFIX = "  8. Commit and push"
INTROSPECT_RUN = "run `introspector` in **loop mode** only before commit"
LEDGER_ITEM = "- **Maintain a run ledger per MDU**"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing carrier: {path}"
    return path.read_text(encoding="utf-8")


def _carriers() -> tuple[Path, Path, Path]:
    return (
        REPO_ROOT / BASE_RELS[0],
        REPO_ROOT / BASE_RELS[1],
        GROKESTRATOR,
    )


def _extract(text: str) -> str:
    """Clause body only: the fenced sequence, indent stripped by the match."""
    count = text.count(CLAUSE)
    assert count == 1, f"clause count {count}, expected 1"
    start = text.find(CLAUSE)
    return text[start : start + len(CLAUSE)]


def _once_and_identical(texts: list[str]) -> None:
    assert len(texts) == 3
    extracts = [_extract(text) for text in texts]
    assert extracts[0] == extracts[1] == extracts[2] == CLAUSE


def _nonempty(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def _load_mdu63():
    path = Path(__file__).resolve().parent / "test_mdu_63_guards.py"
    spec = importlib.util.spec_from_file_location("mdu63_guards_pin", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _cache_miss_marker(cache_clause: str) -> str:
    """Bytes of the cache-miss marker as they appear in the imported clause."""
    needle = "cache miss"
    idx = cache_clause.lower().find(needle)
    assert idx != -1, "imported cache clause has no cache-miss marker"
    return cache_clause[idx : idx + len(needle)]


def test_clause_once_and_extracts_match_fence() -> None:
    texts = [_read(path) for path in _carriers()]
    _once_and_identical(texts)


def test_base_step7_adjacency() -> None:
    for rel in BASE_RELS:
        lines = _nonempty(_read(REPO_ROOT / rel))
        step7 = [line for line in lines if line.startswith(STEP7_PREFIX)]
        assert len(step7) == 1, rel
        line = step7[0]
        assert line.endswith(STEP7_END), rel
        assert CLAUSE not in line, rel
        idx = lines.index(line)
        assert lines[idx + 1] == (" " * 5) + CLAUSE, rel
        assert lines[idx + 2].startswith(STEP8_PREFIX), rel


def test_grokestrator_clause_is_next_sentence() -> None:
    text = _read(GROKESTRATOR)
    bullets = [line for line in text.splitlines() if INTROSPECT_RUN in line]
    assert len(bullets) == 1
    bullet = bullets[0]
    assert CLAUSE in bullet
    end_at = bullet.find(STEP7_END)
    assert end_at != -1
    assert bullet.find(STEP7_END, end_at + 1) == -1
    assert bullet[end_at + len(STEP7_END) :] == " " + CLAUSE
    lines = text.splitlines()
    following = next(
        line for line in lines[lines.index(bullet) + 1 :] if line.startswith("- ")
    )
    assert following.startswith(LEDGER_ITEM)


def test_cache_miss_gate_unchanged() -> None:
    m63 = _load_mdu63()
    assert tuple(m63.ORCH_CARRIERS) == BASE_RELS
    marker = _cache_miss_marker(m63.CACHE_CLAUSE)
    for rel in m63.ORCH_CARRIERS:
        m63.test_clause_present_once_as_full_line("20261110-2", m63.CACHE_LINE, rel)
        m63.test_orchestrator_clause_inside_cache_miss_gate(rel)
        for fragment in m63.CACHE_FRAGMENTS:
            m63.test_clause_fragments("20261110-2", m63.CACHE_LINE, fragment, rel)
        clause_lines = [line for line in _read(REPO_ROOT / rel).splitlines() if CLAUSE in line]
        assert len(clause_lines) == 1, rel
        assert marker not in clause_lines[0], rel
        assert m63.CACHE_LINE not in clause_lines[0], rel
        for fragment in m63.CACHE_FRAGMENTS:
            assert fragment not in clause_lines[0], rel


def test_deleting_clause_from_one_carrier_fails() -> None:
    originals = [_read(path) for path in _carriers()]
    _once_and_identical(originals)
    for index, original in enumerate(originals):
        mutated = list(originals)
        mutated[index] = original.replace(CLAUSE, "", 1)
        assert CLAUSE not in mutated[index]
        with pytest.raises(AssertionError):
            _once_and_identical(mutated)
