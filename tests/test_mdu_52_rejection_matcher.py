"""Tests for the mdu-52 word-boundary verdict matcher.

Pins the false-positive classes 20261101-4 recorded (a reviewer NIT that
mentions the signal kind or quotes the phrase list must not read as a verdict)
and the true verdicts that must survive the narrowing.  The script is imported
via importlib, matching ``tests/test_session_signals.py``.

mdu-53 layers verdict-line precedence on top (a standalone verdict line
classifies the whole message; see the mdu-53 design doc and
``test_mdu_53_verdict_line_precedence.py``): the narrowing claim below is
scoped to the guard set and the no-verdict-line body tier -- all 15 cases here
hold byte-identical.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPO_ROOT
    / "skills"
    / "session-introspect"
    / "scripts"
    / "session_signals.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("session_signals", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


session_signals = _load_module()


def _event(
    agent: str,
    text: str,
    t: float,
    *,
    role: str = "assistant",
    tokens_in: int = 0,
    tokens_out: int = 0,
    tool: str | None = None,
    tool_path: str | None = None,
    tool_error: bool = False,
    permission_requested: bool = False,
) -> dict:
    return {
        "agent": agent,
        "role": role,
        "text": text,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "t": t,
        "tool": tool,
        "tool_path": tool_path,
        "tool_error": tool_error,
        "permission_requested": permission_requested,
    }


NIT_KIND = (
    "NIT (D-2): a reviewer message naming `review_reject_streak` is a mention, "
    "not a verdict; word-boundary matching makes the kind unambiguous."
)


# ---------------------------------------------------------------------------
# 1. The live mdu-51 false positive (kind mention), direct + end-to-end
# ---------------------------------------------------------------------------


def test_kind_mention_underscore_token_is_not_a_rejection() -> None:
    assert session_signals._is_rejection("review_reject_streak") is False
    assert session_signals._is_rejection("`review_reject_streak`") is False
    assert session_signals._is_rejection('"review_reject_streak"') is False
    assert session_signals._is_rejection(NIT_KIND) is False

    events = [
        _event("just-code", "implemented the fix", t=1.0),
        _event("code-reviewer", NIT_KIND, t=2.0),
        _event("code-reviewer", NIT_KIND, t=3.0),
        _event(
            "code-reviewer",
            "APPROVE round 1 — NIT folded: the quoted kind is a matcher mention, "
            "not a verdict",
            t=4.0,
        ),
    ]
    signals = session_signals.collect_signals(events)
    assert "review_reject_streak" not in [s["kind"] for s in signals]
    assert session_signals._compute_metrics(events)["review_rejections"] == 0


# ---------------------------------------------------------------------------
# 2. Prose / hyphen spellings of the kind (\b alone would match these)
# ---------------------------------------------------------------------------


def test_kind_mention_prose_spellings_are_not_rejections() -> None:
    assert session_signals._is_rejection("review reject streak") is False
    assert session_signals._is_rejection("review-reject-streak") is False
    assert (
        session_signals._is_rejection(
            "the review reject streak counter over-reported again"
        )
        is False
    )


# ---------------------------------------------------------------------------
# 3. A NIT quoting the phrase list
# ---------------------------------------------------------------------------


def test_nit_quoting_the_phrase_list_is_not_a_rejection() -> None:
    nit = (
        "NIT (D-2): REJECTION_PHRASES still lists the bare 'reject' entry and the "
        "'request changes' phrase; word-boundary matching must not treat this note "
        "as a verdict."
    )
    assert session_signals._is_rejection(nit) is False


# ---------------------------------------------------------------------------
# 4. Adjacent negation (local strip, not a global veto)
# ---------------------------------------------------------------------------


def test_adjacent_negation_is_not_a_rejection() -> None:
    assert session_signals._is_rejection("no rejections in this round") is False
    assert session_signals._is_rejection("zero rejections recorded") is False
    assert (
        session_signals._is_rejection("no rejections, but I must request changes")
        is True
    )


# ---------------------------------------------------------------------------
# 5-7. Genuine verdicts still match
# ---------------------------------------------------------------------------


def test_genuine_request_changes_verdict_is_a_rejection() -> None:
    assert session_signals._is_rejection("REQUEST CHANGES: tests missing") is True
    assert session_signals._is_rejection("changes requested: docs missing") is True


def test_standalone_rejected_is_a_rejection() -> None:
    assert (
        session_signals._is_rejection(
            "I rejected this change because tests are missing"
        )
        is True
    )


def test_bare_reject_and_i_reject_still_match() -> None:
    assert session_signals._is_rejection("REJECT") is True
    assert session_signals._is_rejection("I REJECT this") is True


# ---------------------------------------------------------------------------
# 8-10. Approval interplay
# ---------------------------------------------------------------------------


def test_approve_round_one_with_kind_mention_reads_as_approval() -> None:
    text = (
        'APPROVE round 1 — one NIT: the matcher fires on the quoted kind '
        '"review_reject_streak" (20261101-4); fold the guard into the matcher MDU.'
    )
    assert session_signals._is_approval(text) is True
    assert session_signals._is_rejection(text) is False


def test_unapproved_is_not_approval() -> None:
    assert session_signals._is_approval("these changes are unapproved") is False
    assert session_signals._is_approval("Approved, LGTM") is True


def test_do_not_approve_still_rejects_not_approves() -> None:
    for text in ("do not approve this yet", "not approved"):
        assert session_signals._is_rejection(text) is True
        assert session_signals._is_approval(text) is False


# ---------------------------------------------------------------------------
# 11. Guard substitution is a single space, never the empty string
# ---------------------------------------------------------------------------


def test_guard_strip_substitutes_a_space() -> None:
    assert session_signals._verdict_text("x'reject'y") == "x y"


# ---------------------------------------------------------------------------
# 12. Stem retention — the "no true verdict lost" half of D-4's narrowing claim
#     (still true under mdu-53: guards only remove matches, and verdict-line
#     precedence never removes a true verdict — these assertions are unchanged)
# ---------------------------------------------------------------------------


def test_alternation_stems_keep_the_old_inflections() -> None:
    # The old substring "reject" matched every inflection; the new alternation
    # re-encodes those forms explicitly, so a dropped branch is a silent false
    # negative rather than a failure anywhere else.  Design §10 cites
    # "Verdict: REJECTION" as a true verdict that must keep matching.
    assert session_signals._is_rejection("Verdict: REJECTION") is True
    assert (
        session_signals._is_rejection("the reviewer rejects this change: tests missing")
        is True
    )
    assert (
        session_signals._is_rejection(
            "the reviewer kept rejecting the fix: tests still missing"
        )
        is True
    )
    # APPROVAL_RE covers approve/approves/approved and sign-off(s) (design §3).
    assert session_signals._is_approval("the reviewer approves these changes") is True
    assert session_signals._is_approval("sign-off given; merging") is True
    assert session_signals._is_approval("sign-offs recorded for both reviewers") is True


# ---------------------------------------------------------------------------
# 13. Live cycle-2 false positive: an AC table quoting the counter and its
#     evidence template is a metric mention, not a verdict
# ---------------------------------------------------------------------------

AC_METRIC_LINE = (
    '| AC-2 | test_mdu_51:297 (streak fires, evidence "2 consecutive rejections") '
    "+ :324 (review_rejections == 1) |"
)


def test_quantified_metric_mention_in_ac_table_is_not_a_rejection() -> None:
    assert session_signals._is_rejection(AC_METRIC_LINE) is False
    assert session_signals._is_approval("APPROVE round 2\n" + AC_METRIC_LINE) is True
    # Guard substitution stays idempotent.
    once = session_signals._verdict_text(AC_METRIC_LINE)
    assert session_signals._verdict_text(once) == once

    events = [
        _event("just-code", "implemented the fix", t=1.0),
        _event("code-reviewer", AC_METRIC_LINE, t=2.0),
        _event("code-reviewer", AC_METRIC_LINE, t=3.0),
    ]
    assert session_signals._compute_metrics(events)["review_rejections"] == 0
    assert "review_reject_streak" not in [
        s["kind"] for s in session_signals.collect_signals(events)
    ]


# ---------------------------------------------------------------------------
# 14. Evidence-tail and counter-comparison mentions (no verdict)
# ---------------------------------------------------------------------------


def test_evidence_tail_and_counter_comparison_are_not_rejections() -> None:
    assert (
        session_signals._is_rejection(
            "1/2 rejections from code-reviewer; review_rejections == 1"
        )
        is False
    )
    assert session_signals._is_rejection("review_rejection == 0") is False


# ---------------------------------------------------------------------------
# 15. The new guard must not over-strip genuine verdicts
# ---------------------------------------------------------------------------


def test_quantified_metric_guard_keeps_genuine_verdicts() -> None:
    assert session_signals._is_rejection("Verdict: REJECTED, request changes") is True
    assert session_signals._is_rejection("these two verdicts REJECT the design") is True
    # Span locality: only the ``rejections from`` tail is stripped; the
    # REQUEST CHANGES verdict that follows it survives.
    assert (
        session_signals._is_rejection(
            "rejections from the two rounds: REQUEST CHANGES"
        )
        is True
    )
    assert session_signals._is_rejection("3 rejections and I request changes") is True
