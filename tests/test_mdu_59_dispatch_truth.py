"""MDU-59 dispatch-truth: dormant clause pin + live forensics-doc pin.

Two contracts, deliberately asymmetrical in activation:

* **Test A (dormant).** The Dispatch-truth clause proposed by MDU-59 is *not yet
  applied* to any carrier. This pin stays skipped until the clause text lands in
  at least one of the three orchestrator mirrors, and then flips on hard: from
  that moment the marker plus a second distinctive fragment of the clause must
  be present in **all three** mirrors. That ordering is the point — a
  half-applied clause (base mirrors only, overlay forgotten) fails instead of
  passing quietly, which is the mdu-49/mdu-57/mdu-60 third-mirror convention.
* **Test B (live).** The forensics doc that motivates the clause is non-vacuous
  today: it must name the actually-dispatched agent variant and state the direct
  answer in its own words. If someone trims the evidence out of the doc, the
  clause loses its provenance and that should break the build.

Hermetic: repo + sibling-overlay reads only. No writes, no git calls, no network,
no secrets. Paths are resolved from ``Path(__file__)`` so the suite is
cwd-independent, exactly like ``test_mdu_34_resume_block.py`` and
``test_mdu_60_qa_write_access.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Third carrier is the private overlay sibling; absent in a standalone clone of
# the public base. Resolved to a concrete path (not a conditional list entry) so
# the "all three" assertion can name the missing file explicitly.
OVERLAY_GROKESTRATOR = (
    Path(__file__).resolve().parents[1].parent
    / "opencode_agents"
    / "grok"
    / "agents"
    / "grokestrator.md"
)

CARRIERS = [
    REPO_ROOT / "prompts" / "orchestrator.md",
    REPO_ROOT / "grok" / "agents" / "orchestrator.md",
    OVERLAY_GROKESTRATOR,
]

FORENSICS_DOC = REPO_ROOT / "docs" / "design" / "mdu-59-forensics.md"

# Opening of the proposed clause. Presence of this string in ANY carrier is the
# activation signal for the strict cross-mirror pin.
CLAUSE_MARKER = (
    "Dispatch statements must name harness + agent id + resolved model explicitly"
)

# Second distinctive fragment: proves a carrier holds the *whole* clause
# (the bare-role-name prohibition), not just an echoed headline. Guards against a
# partial apply that pastes the first line and drops the normative half.
CLAUSE_SECOND_FRAGMENT = (
    "never refer to a dispatched agent by a bare role name"
)

# Test B pins: the agent variant that actually ran, and the doc's direct answer.
DISPATCHED_VARIANT = "grok-architect-premium"
DIRECT_ANSWER_FRAGMENT = "ran as a real dispatched subagent"


def _read(path: Path) -> str:
    """Strict read: a missing carrier is an error, never a silent pass."""
    assert path.is_file(), f"missing expected file: {path}"
    return path.read_text(encoding="utf-8")


def _carrier_label(path: Path) -> str:
    """Repo-relative label when possible, absolute path otherwise."""
    for root in (REPO_ROOT, OVERLAY_GROKESTRATOR.parents[3]):
        try:
            return str(path.relative_to(root))
        except ValueError:
            continue
    return str(path)


def _carriers_with_marker() -> list[Path]:
    found = []
    for path in CARRIERS:
        if path.is_file() and CLAUSE_MARKER in path.read_text(encoding="utf-8"):
            found.append(path)
    return found


# ---------------------------------------------------------------------------
# Test A — dormant clause pin (activates the moment the clause is applied)
# ---------------------------------------------------------------------------


def test_dispatch_truth_clause_pinned_in_all_three_mirrors() -> None:
    assert len(CARRIERS) == 3, "the clause has exactly three carrier mirrors"

    applied = _carriers_with_marker()
    if not applied:
        pytest.skip("dispatch-truth clause proposal (MDU-59) not applied yet")

    # At least one carrier has it: from here it is all-or-nothing.
    missing: list[str] = []
    for path in CARRIERS:
        label = _carrier_label(path)
        if not path.is_file():
            missing.append(f"{label} (file does not exist)")
            continue
        text = path.read_text(encoding="utf-8")
        absent = [
            fragment
            for fragment in (CLAUSE_MARKER, CLAUSE_SECOND_FRAGMENT)
            if fragment not in text
        ]
        if absent:
            missing.append(f"{label} (missing {absent!r})")

    assert not missing, (
        "the MDU-59 Dispatch-truth clause is partially applied; it must be "
        "byte-consistent across all three orchestrator mirrors. Missing from: "
        + "; ".join(missing)
        + f". Mirror(s) already carrying it: "
        + ", ".join(_carrier_label(p) for p in applied)
    )


# ---------------------------------------------------------------------------
# Test B — forensics doc pin (non-vacuous today)
# ---------------------------------------------------------------------------


def test_forensics_doc_exists_and_names_the_dispatched_variant() -> None:
    assert FORENSICS_DOC.is_file(), (
        f"MDU-59 forensics doc is missing: {FORENSICS_DOC}. The dispatch-truth "
        "clause proposal cites it as evidence and cannot be reviewed without it."
    )
    text = _read(FORENSICS_DOC)
    assert DISPATCHED_VARIANT in text, (
        f"{_carrier_label(FORENSICS_DOC)}: does not name {DISPATCHED_VARIANT!r}; "
        "the forensics finding must identify the agent variant that actually ran"
    )


def test_forensics_doc_states_the_direct_answer() -> None:
    assert FORENSICS_DOC.is_file(), (
        f"MDU-59 forensics doc is missing: {FORENSICS_DOC}. The dispatch-truth "
        "clause proposal cites it as evidence and cannot be reviewed without it."
    )
    text = _read(FORENSICS_DOC)
    assert DIRECT_ANSWER_FRAGMENT in text, (
        f"{_carrier_label(FORENSICS_DOC)}: missing the direct-answer statement "
        f"{DIRECT_ANSWER_FRAGMENT!r}; the doc must answer whether the architect "
        "was a real dispatched subagent rather than leaving it implied"
    )
