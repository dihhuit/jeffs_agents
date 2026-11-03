"""Tests for the mdu-53 verdict-line precedence rule.

Pins the three live false positives 20261102-1 recorded on the mdu-52 session
tree (a verdict-less analysis whose prose negates the word "rejection", and two
APPROVE-verdict rounds whose bodies quote the matcher's own vocabulary), the
precedence contract (a standalone verdict line classifies the whole message and
body prose can neither override nor veto it), the extended prose-negation and
backtick-span guards, and the true verdicts that must keep counting.  The
script is imported via importlib, matching ``tests/test_session_signals.py``.
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


# ---------------------------------------------------------------------------
# The three recorded live FP shapes (design §1 / Appendix A)
# ---------------------------------------------------------------------------

# Shape 1: verdict-less mid-review analysis.  Prose negates the word
# "rejection" and quotes the matcher vocabulary.
FP_ANALYSIS = (
    "Before the verdict: the detector is doing what it was built to do. "
    "It's not a rejection of the design -- the guards only strip mentions, "
    "the backticked source `reject(?:ed|s|ing|ion|ions)?` is evidence, and "
    "`rejections? <op> <digit>` is one branch example."
)

# Shape 2: an APPROVE verdict whose body quotes the regex source and writes
# "a reviewer discussing the detector is not rejecting".
FP_APPROVE_1 = (
    "## Verdict: APPROVE\n"
    "\n"
    "One NIT: the matcher's own source is `reject(?:ed|s|ing|ion|ions)?`, and "
    "the message that quotes it reads as a round only because of the bare "
    "stem; a reviewer discussing the detector is not rejecting anything.\n"
)

# Shape 3: an APPROVE verdict with a qualifier suffix whose body quotes guard
# branches and example strings.
FP_APPROVE_2 = (
    "## Verdict: APPROVE (cycle-2 delta)\n"
    "\n"
    "Body quotes the guard branch `rejections? <op> <digit>` and the evidence "
    'template `"rejections from the two rounds: REQUEST CHANGES"`; neither is '
    "a verdict.\n"
)


# ---------------------------------------------------------------------------
# 1. FP #2: the verdict line beats rejection vocabulary in the body
# ---------------------------------------------------------------------------


def test_labelled_approve_verdict_beats_rejection_vocabulary() -> None:
    assert session_signals._verdict_line(FP_APPROVE_1) == "APPROVE"
    assert session_signals._review_class(FP_APPROVE_1) == "approve"
    assert session_signals._is_rejection(FP_APPROVE_1) is False
    assert session_signals._is_approval(FP_APPROVE_1) is True


# ---------------------------------------------------------------------------
# 2. FP #3: a qualifier suffix can never flip the verdict
# ---------------------------------------------------------------------------


def test_labelled_approve_with_suffix_qualifier_stays_approval() -> None:
    assert session_signals._verdict_line(FP_APPROVE_2) == "APPROVE (cycle-2 delta)"
    assert session_signals._review_class(FP_APPROVE_2) == "approve"
    assert session_signals._is_rejection(FP_APPROVE_2) is False
    assert session_signals._is_approval(FP_APPROVE_2) is True

    # Flip trap: classification is an anchored match on the deciding phrase,
    # never a search over the value.  A suffix-bearing rejection clause is
    # still part of an approval verdict line.
    flip_trap = "## Verdict: APPROVE (rejections all addressed)"
    assert session_signals._review_class(flip_trap) == "approve"
    assert session_signals._is_rejection(flip_trap) is False


# ---------------------------------------------------------------------------
# 3. End-to-end replay of the mdu-52 session tree's reviewer rounds
# ---------------------------------------------------------------------------


def test_matcher_analysis_session_reads_zero_rejections_and_two_approvals() -> None:
    events = [
        _event("just-code", "implemented the matcher hardening", t=1.0),
        _event("code-reviewer", FP_ANALYSIS, t=2.0),
        _event("code-reviewer", FP_APPROVE_1, t=3.0),
        _event("code-reviewer", FP_APPROVE_2, t=4.0),
    ]
    assert session_signals._compute_metrics(events)["review_rejections"] == 0
    assert session_signals._compute_metrics(events)["review_approvals"] == 2
    assert "review_reject_streak" not in [
        s["kind"] for s in session_signals.collect_signals(events)
    ]


# ---------------------------------------------------------------------------
# 4. The compounding-bug pin: an APPROVE verdict resets a real streak
# ---------------------------------------------------------------------------


def test_approve_verdict_resets_a_real_streak() -> None:
    events = [
        _event("just-code", "implemented the fix", t=1.0),
        _event("code-reviewer", "REQUEST CHANGES: tests missing", t=2.0),
        _event("code-reviewer", "changes requested: docs missing", t=3.0),
        _event("code-reviewer", FP_APPROVE_1, t=4.0),
    ]
    streaks = [
        s for s in session_signals.collect_signals(events)
        if s["kind"] == "review_reject_streak"
    ]
    # The approval lands, so the streak is closed by the two genuine
    # rejections alone: the APPROVE-verdict message never enters streak_texts
    # (pre-fix it both incremented the streak and failed to reset it).
    assert len(streaks) == 1
    assert streaks[0]["evidence"].startswith("2 consecutive rejections from code-reviewer")
    assert "## Verdict: APPROVE" not in streaks[0]["evidence"]
    assert session_signals._compute_metrics(events)["review_rejections"] == 2


# ---------------------------------------------------------------------------
# 5. FP #1: a verdict-less analysis message is not a round
# ---------------------------------------------------------------------------


def test_verdictless_analysis_is_not_a_round() -> None:
    assert session_signals._verdict_line(FP_ANALYSIS) is None
    assert session_signals._review_class(FP_ANALYSIS) == "none"
    assert session_signals._is_rejection(FP_ANALYSIS) is False
    assert session_signals._is_approval(FP_ANALYSIS) is False

    events = [
        _event("just-code", "implemented the fix", t=1.0),
        _event("code-reviewer", FP_ANALYSIS, t=2.0),
        _event("code-reviewer", FP_ANALYSIS, t=3.0),
        _event("code-reviewer", "LGTM", t=4.0),
    ]
    assert session_signals._compute_metrics(events)["review_rejections"] == 0
    assert "review_reject_streak" not in [
        s["kind"] for s in session_signals.collect_signals(events)
    ]


# ---------------------------------------------------------------------------
# 6. True verdict lines still count
# ---------------------------------------------------------------------------


def test_reject_and_request_changes_verdict_lines_still_count() -> None:
    for text in (
        "## Verdict: REJECT",
        "## Verdict: REQUEST CHANGES — tests missing",
        "REJECT",
        "REQUEST CHANGES: tests missing",
        "## Verdict: REJECTED",
        "## Verdict: REJECTION",
        "## Verdict: NOT APPROVED",
    ):
        assert session_signals._is_rejection(text) is True, text
        assert session_signals._is_approval(text) is False, text

    events = [
        _event("just-code", "implemented the fix", t=1.0),
        _event("code-reviewer", "## Verdict: REJECT — tests missing", t=2.0),
        _event("code-reviewer", "## Verdict: REJECT — docs still missing", t=3.0),
    ]
    streaks = [
        s for s in session_signals.collect_signals(events)
        if s["kind"] == "review_reject_streak"
    ]
    assert len(streaks) == 1
    assert "2 consecutive rejections" in streaks[0]["evidence"]
    assert session_signals._compute_metrics(events)["review_rejections"] == 2


# ---------------------------------------------------------------------------
# 7. Bare decision words at line start
# ---------------------------------------------------------------------------


def test_bare_decision_words_at_line_start() -> None:
    assert session_signals._review_class("APPROVE round 1 — NIT folded") == "approve"
    assert session_signals._review_class("LGTM, approving") == "approve"
    assert session_signals._review_class("REJECTED — cycle 2") == "reject"
    assert session_signals._review_class("Approved, LGTM") == "approve"
    # Up to three leading spaces still anchor.
    assert session_signals._review_class("   REJECT: tests missing") == "reject"


# ---------------------------------------------------------------------------
# 8. Line-shape exclusions: nouns, later lines, fences, blockquotes
# ---------------------------------------------------------------------------


def test_noun_initial_and_quoted_lines_are_not_verdict_lines() -> None:
    noun_line = "rejections from the two rounds: REQUEST CHANGES"
    assert session_signals._verdict_line(noun_line) is None
    # Body-tier continuity (mdu-52 case 15): it still reads as a rejection.
    assert session_signals._is_rejection(noun_line) is True

    # The first verdict line wins over a later opposite line.
    first_wins = "## Verdict: APPROVE\n\n```\nexample\n```\n\n## Verdict: REQUEST CHANGES"
    assert session_signals._verdict_line(first_wins) == "APPROVE"
    assert session_signals._review_class(first_wins) == "approve"

    # Fenced verdict lines are metalanguage; the real line decides.
    fenced = "```\n## Verdict: REQUEST CHANGES\n```\n\n## Verdict: APPROVE\n"
    assert session_signals._verdict_line(fenced) == "APPROVE"
    assert session_signals._review_class(fenced) == "approve"

    # Blockquoted (">") and 4+-space-indented lines fail the anchor.
    quoted = "> ## Verdict: REQUEST CHANGES\n\nThe tests are missing."
    assert session_signals._verdict_line(quoted) is None
    indented = "    ## Verdict: APPROVE\n\nThe tests are missing."
    assert session_signals._verdict_line(indented) is None


# ---------------------------------------------------------------------------
# 9. An explicit but unrecognized verdict is not a round, and the body cannot
#    override it
# ---------------------------------------------------------------------------


def test_unrecognized_verdict_value_is_not_a_round() -> None:
    needs_work = "## Verdict: NEEDS WORK\n\nI request changes: tests missing."
    assert session_signals._review_class(needs_work) == "none"
    assert session_signals._is_rejection(needs_work) is False
    assert session_signals._is_approval(needs_work) is False

    # Disclosed residual (design §12): a label value that does not start with
    # a verdict word is not a round.
    assert session_signals._review_class("## Verdict: I approve") == "none"


# ---------------------------------------------------------------------------
# 10. Extended adjacent/prose negation guard
# ---------------------------------------------------------------------------


def test_extended_negation_guard() -> None:
    assert session_signals._is_rejection("it's not a rejection") is False
    assert session_signals._is_rejection("this is not an rejection either") is False
    assert session_signals._is_rejection("these are not rejections") is False
    assert session_signals._is_rejection("we are not rejecting this design") is False
    # Locality: only the negated span strips, the following verdict survives.
    assert (
        session_signals._is_rejection("not a rejection, but I must request changes")
        is True
    )
    # mdu-52 continuity.
    assert session_signals._is_rejection("no rejections in this round") is False
    assert session_signals._is_rejection("zero rejections recorded") is False
    assert (
        session_signals._is_rejection("no rejections, but I must request changes")
        is True
    )
    # "not approved" is a rejection phrase, not a negation of one.
    assert session_signals._is_rejection("not approved") is True


# ---------------------------------------------------------------------------
# 11. Backtick-span mention guard
# ---------------------------------------------------------------------------


def test_backtick_span_guard() -> None:
    spans = (
        "`reject(?:ed|s|ing|ion|ions)?`",
        "`rejections? <op> <digit>`",
        '`"rejections from the two rounds: REQUEST CHANGES"`',
    )
    for text in spans:
        assert session_signals._is_rejection(text) is False, text
        assert session_signals._is_approval(text) is False, text
        once = session_signals._verdict_text(text)
        assert session_signals._verdict_text(once) == once, text

    # Locality: an unquoted verdict after a backticked mention still counts.
    assert (
        session_signals._is_rejection(
            "`rejections? <op> <digit>` is a guard branch, but I request changes"
        )
        is True
    )


# ---------------------------------------------------------------------------
# 12. metrics.review_approvals is additive; the rejection counter is unchanged
# ---------------------------------------------------------------------------


def test_metrics_approvals_key_is_additive() -> None:
    events = [
        _event("just-code", "implemented the fix", t=1.0),
        _event("code-reviewer", "REQUEST CHANGES: tests missing", t=2.0),
        _event("code-reviewer", "## Verdict: APPROVE", t=3.0),
        _event("code-reviewer", FP_ANALYSIS, t=4.0),
        _event("code-reviewer", "changes requested: docs missing", t=5.0),
        _event("code-reviewer", "## Verdict: APPROVE (cycle-2 delta)", t=6.0),
        # Non-reviewer approval vocabulary counts nowhere (agent gate).
        _event("just-code", "Approved, LGTM", t=7.0),
    ]
    metrics = session_signals._compute_metrics(events)
    assert metrics["review_rejections"] == 2
    assert metrics["review_approvals"] == 2
    assert metrics["agents"][0]["name"] == "just-code"


# ---------------------------------------------------------------------------
# 13. Precedence over UNQUOTED body vocabulary.  The guard set cannot
#     neutralize this text (no backticks, no negation), so only verdict-line
#     precedence keeps the class -- a regression to body-tier classification,
#     or a body veto on the approve branch, flips every assertion below.
# ---------------------------------------------------------------------------


def test_verdict_line_beats_unquoted_body_vocabulary() -> None:
    approve_with_rejection_body = (
        "## Verdict: APPROVE (cycle-2 delta)\n"
        "\n"
        "The two rejections were both addressed; request changes no longer apply.\n"
    )
    assert session_signals._review_class(approve_with_rejection_body) == "approve"
    assert session_signals._is_rejection(approve_with_rejection_body) is False
    assert session_signals._is_approval(approve_with_rejection_body) is True

    # Reverse direction: an approval-flavoured body cannot soften a REJECT line.
    reject_with_approval_body = "## Verdict: REJECT\n\nLGTM once the docs land.\n"
    assert session_signals._review_class(reject_with_approval_body) == "reject"
    assert session_signals._is_approval(reject_with_approval_body) is False

    # The un-sticking half: this approval closes a real streak even though its
    # body carries rejection vocabulary the guards deliberately leave intact.
    events = [
        _event("just-code", "implemented the fix", t=1.0),
        _event("code-reviewer", "REQUEST CHANGES: tests missing", t=2.0),
        _event("code-reviewer", "changes requested: docs missing", t=3.0),
        _event("code-reviewer", approve_with_rejection_body, t=4.0),
    ]
    streaks = [
        s for s in session_signals.collect_signals(events)
        if s["kind"] == "review_reject_streak"
    ]
    assert len(streaks) == 1
    assert streaks[0]["evidence"].startswith(
        "2 consecutive rejections from code-reviewer"
    )
    assert "## Verdict: APPROVE" not in streaks[0]["evidence"]
    metrics = session_signals._compute_metrics(events)
    assert metrics["review_rejections"] == 2
    assert metrics["review_approvals"] == 1
