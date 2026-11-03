# MDU-53 · Verdict-line precedence — the reviewer's own verdict wins

Closes **20261102-1** (high, detector_gap): on mdu-52's own session tree
(`ses_e63839af6ffe3a6SM2Iv0Gqgm7`) the matcher reported `review_rejections: 3`
plus a false `review_reject_streak` HIGH against a manifest truth of 0
rejections (both review rounds APPROVE). The three matching code-reviewer
messages were (1) a verdict-less mid-review analysis saying "it's not a
rejection", (2) an APPROVE-verdict message whose body quotes the regex source
and writes "a reviewer discussing the detector is not rejecting", and (3) the
cycle-2 APPROVE-verdict message whose body quotes guard branches and example
strings. Compounding bug: `_is_approval` requires `not _rejects(...)`, so an
APPROVE-verdict message that discusses rejection vocabulary BOTH increments
the streak AND fails to reset it — the FP fires and sticks.

Done looks like: `skills/session-introspect/`
`scripts/session_signals.py` gains verdict-line precedence (a standalone verdict line
classifies the whole message; body prose never overrides or vetoes it), an
extended prose-negation guard, and a backtick-span mention guard; a new
`tests/`
`test_mdu_53_verdict_line_precedence.py` pins the three live FP shapes, the
precedence contract, and the true-verdict retention; the mdu-52 test file gets
an invariant-wording reconciliation only (zero assertion edits);
`skills/session-introspect/`
`SKILL.md` gains one behavior-note sentence; `agent-improvements.md` entry
20261102-1 is flipped to RESOLVED with the exact note in §D-8 (applied in the
implement phase, not by the introspector); the full suite is green at 800
existing + new with zero edits to existing assertions; base + overlay builds
exit 0 and the deployed copies are byte-identical to the source of record,
with a live re-probe of the FP session tree reading `review_rejections: 0`
and `review_approvals >= 2`. No agent-definition files, no overlay source, no
config/registry/model-map rows → **no model re-probe**. No model-id
assignments are made by this design; tier selection follows the mdu-lifecycle
table. Verdict format: implement reports per-target `file:function`
completion; QA ends with `QA GRADE: PASS` or `QA GRADE: FAIL`.

## 0. Scope — files surveyed (exactly)

- `skills/session-introspect/`
  `scripts/session_signals.py` — full read (L1-1583): L39-77 (REJECTION_RE,
  APPROVAL_RE, VERDICT_MENTION_RE, QA_FAIL_VERDICT), L176-233 (text helpers,
  `_verdict_text`, `_rejects`, `_is_rejection`, `_is_approval`), L301-387
  (streak loop + end-of-session streak), L432-467 (`_compute_metrics`),
  L1506-1579 (CLI `main` and the result JSON).
- `tests/`
  `test_mdu_52_rejection_matcher.py` — full (15 cases, the narrowing pins).
- `tests/test_session_signals.py` — L55-134, L340-394, plus a grep inventory
  of every reject/approve fixture (L71-72, 85, 93-95, 103-104, 114, 119,
  357-359, 372-373).
- `tests/`
  `test_mdu_50_session_store_selection.py` — L190-244 (live-shape v1 streak
  fixture).
- `tests/`
  `test_mdu_51_v2_text_extraction.py` — L250-335, L950-994 (v2 streak/metrics
  and CLI-level `review_rejections == 2`), plus grep inventory.
- `skills/session-introspect/`
  `SKILL.md` — L105-133 (signal-kind bullets, v2 disclosure).
- `agent-improvements.md` — L660-676 (20261102-1 verbatim; mdu-52 closure
  note) and L773 (the introspector's recorded probe output for the FP tree).
- `.agents/memory/` — the `session-ses_e638…` summary and `decisions.md`
  L108-111 (mdu-52 decision; the routed residual "verdict-less analytic
  quoting … can still FP"). Orchestrator-owned; not MDU diff surface.
- `docs/design/`
  `mdu-52-rejection-matcher-hardening.md` — full (house style, D-4 invariant,
  §9 deploy/probe conventions mirrored here).
- `prompts/code-reviewer.md`, `prompts/grok-review.md`, `prompts/qa.md` —
  grep: **no agent definition mandates a verdict-line format**; reviewers
  approve/request changes in free-form prose. The observed `## Verdict: …`
  lines are review-brief convention, not prompt contract — the detector must
  handle both line and prose verdicts.

Design-time probe disclosure: the architect sandbox for this MDU is read-only
without a shell, so the FP session tree was **not** re-probed at design time.
The three message shapes below are the introspector's probe-traced records
(agent-improvements.md 20261102-1 evidence, L668) — recorded probe output, not
paraphrase — and are used here as design evidence only. The implement and
validate phases re-run the probe as a hard gate (§D-10).

## 1. The live defect — three shapes, one compounding bug

| # | Message shape (recorded) | Verdict line? | Why the mdu-52 matcher fires |
|---|---|---|---|
| 1 | Verdict-less mid-review analysis; prose contains "it's not a rejection" | none | "rejection" is a correct word-boundary match; the negation guard covers only "no/zero rejections" |
| 2 | `## Verdict: APPROVE` + body quoting the regex source `reject(?:ed|s|ing|ion|ions)?` and writing "a reviewer discussing the detector is not rejecting" | APPROVE | the backticked regex source is not an exact quoted phrase, so the quoted-phrase guard misses; "reject" then matches at the `(` boundary |
| 3 | `## Verdict: APPROVE (cycle-2 delta)` + body quoting guard branches and example strings (`rejections? <op> <digit>`, `"rejections from the two rounds: REQUEST CHANGES"`) | APPROVE | the quoted example strings are longer than the quoted-phrase guard's exact-phrase shape; the metric guards strip only their own templates |

Compounding bug (session_signals.py:205-207): `_is_approval` is
`APPROVAL_RE.search(vt) and not _rejects(vt)`. On shapes 2 and 3 the body
vocabulary vetoes the approval, so the message increments the streak (via
`_is_rejection`) and never resets it (via `_is_approval`) — the false streak
both fires and sticks across rounds. Cheap tell, recorded in the suggestion:
a streak whose evidence string contains `## Verdict: APPROVE` is self-evidently
false. After this MDU that tell becomes impossible by construction: an
APPROVE-verdict message can never enter `streak_texts`.

This class recurs deterministically on any MDU that touches the script
(mdu-50/51/52 all did): the reviewer messages that review a matcher change
quote the matcher's own vocabulary. MDU-53's own review rounds will quote
`VERDICT_LINE_RE` and the phrase alternations — the fix must survive its own
dogfood (§ phase order).

## 2. D-1 — verdict-line detection: shapes, anchoring, exclusions

Two line shapes are verdict lines. New module constants, placed in the
constants block between `VERDICT_MENTION_RE` and `QA_FAIL_VERDICT`
(session_signals.py L72-77):

```python
# --- mdu-53: verdict-line precedence --------------------------------------
# A message that states its verdict on a standalone line is classified by
# that line alone; body prose can never override or veto it.  Two line
# shapes count:
#   1. labelled: "## Verdict: APPROVE (cycle-2 delta)" -- heading marks
#      optional, "verdict" + ":" + a value on one line;
#   2. bare: a line starting with a decision word (REJECT / REJECTED /
#      APPROVE / APPROVED / REQUEST CHANGES / LGTM).
# Noun forms (rejection/rejections) and the progressive (rejecting) are
# deliberately NOT bare decision words: noun-initial lines are the observed
# quoted-example shape ("rejections from the two rounds: ..."), and those
# wordings still count via the labelled shape or the body fallback.
# Excluded structurally: fenced-code content (skipped by _verdict_line),
# blockquoted lines (">" fails the anchor), and 4+-space-indented lines
# (markdown indented code).  The FIRST verdict line in the message wins.
VERDICT_LINE_RE = re.compile(
    r"(?im)^[ \t]{0,3}#{0,6}[ \t]*verdict[ \t]*:[ \t]*(?P<value>.+)$"
    r"|^[ \t]{0,3}(?P<word>request changes|reject(?:ed)?"
    r"|approv(?:e|ed)|lgtm)\b"
)
# The deciding phrase is matched ANCHORED (re.match, never re.search): the
# text after the verdict word is a qualifier ("(cycle-2 delta)") and is
# exactly where a body-quoting FP could hide -- "## Verdict: APPROVE
# (rejections all addressed)" must stay an approval.
VERDICT_REJECT_PHRASE_RE = re.compile(
    r"(?i)^(?:request changes|changes requested|do not approve|not approved"
    r"|reject(?:ed|s|ing|ion|ions)?)\b"
)
VERDICT_APPROVE_PHRASE_RE = re.compile(
    r"(?i)^(?:approv(?:e|es|ed)|lgtm)\b"
)
```

Decisions inside D-1, each justified:

- **Prefix match, not full-line equality** (the brief's open question): the
  labelled value is classified by its *first phrase*, anchored at the value's
  start; the suffix is ignored. Rationale: the live shape
  `## Verdict: APPROVE (cycle-2 delta)` carries a qualifier suffix, and the
  suffix is precisely where shape 3's quoted examples would hide — an
  anywhere-search on the value would let `(rejections all addressed)` flip an
  approval into a rejection, re-creating FP #3 inside the fix. Classification
  therefore uses `VERDICT_*_PHRASE_RE.match(candidate)` — **match, never
  search** — and the suffix-ignoring behavior is test-pinned.
- **Bare-word set is decision verbs/adjectives only**: `reject`, `rejected`,
  `approve`, `approved`, `request changes`, `lgtm`. Nouns
  (`rejection`/`rejections`) and the progressive (`rejecting`) are excluded:
  a noun-initial line is the observed quoted-example/mention shape
  (`rejections from the two rounds: REQUEST CHANGES`, `rejections? <op>
  <digit>`), and nothing is lost — noun verdicts still count via the
  labelled shape (`Verdict: REJECTION` is a pinned true verdict, mdu-52
  case 12) or via the no-line body fallback. Note the deliberate asymmetry:
  the *labelled* value vocabulary (VERDICT_REJECT_PHRASE_RE) keeps the full
  REJECTION_RE stem set including nouns, because a `Verdict:` label has
  already announced a verdict; a bare line has no such announcement, so only
  unambiguous decision words count.
- **Labelled values keep the full stem set, bare words do not** — see above;
  both reuse the exact REJECTION_RE/APPROVAL_RE vocabularies so the line
  classifier and the body matcher can never disagree about *words*, only
  about *which text wins*.
- **First verdict line wins**: `_verdict_line` returns the first match, so a
  later quoted opposite verdict (e.g. a reviewer pasting the next round's
  template) cannot override the message's own. Pinned in §D-6 case 8.
- **Fenced code is never verdict lines**: `_verdict_line` walks lines and
  skips content between ``` / ~~~ fences. A fenced `## Verdict: REQUEST
  CHANGES` quoted as an example is metalanguage. Blockquoted (`>`-prefixed)
  and 4+-space-indented (markdown indented-code) lines are excluded by the
  `^[ \t]{0,3}` anchor itself — no extra machinery.

New helper, placed next to `_strip_think` (session_signals.py L176):

```python
def _verdict_line(text: str) -> str | None:
    """Return the first standalone verdict line's deciding phrase, or None.

    Input is think-stripped by the caller.  Fenced code blocks are skipped;
    blockquoted and 4+-space-indented lines cannot match VERDICT_LINE_RE's
    anchor.  The first verdict line wins.
    """
    in_fence = False
    for line in text.splitlines():
        stripped = line.lstrip(" \t")
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = VERDICT_LINE_RE.match(line)
        if m:
            return m.group("value") or m.group("word") or ""
    return None
```

## 3. D-2 — the precedence contract, and the required adaptation of rule 2

### 3.1 Precedence order (precise)

Classification of one message, in order:

1. **Think-strip** (`_strip_think`): chain-of-thought is never verdict text
   (unchanged mdu-50 rule).
2. **Verdict line?** `_verdict_line` over the think-stripped text.
3. **Line present → the line alone decides**: the line's deciding phrase is
   anchored-matched — reject vocabulary → `"reject"`; approval vocabulary →
   `"approve"`; **anything else → `"none"`** (an explicit unrecognized
   verdict, e.g. `## Verdict: NEEDS WORK`, is not a round, and the body does
   NOT get to override it — that would reintroduce prose-veto through the
   back door).
4. **No line → guarded body fallback** (mdu-52 semantics, plus the D-3 guard
   extensions): `_rejects(_verdict_text(text))` → `"reject"`;
   `APPROVAL_RE.search(_verdict_text(text))` → `"approve"`; else `"none"`.

Body guards (VERDICT_MENTION_RE) apply **only** in tier 4 — when no verdict
line exists. They never run against a verdict line, because the verdict line
is authoritative by design; guards exist to neutralize body prose.

### 3.2 Where it binds

```python
def _review_class(text: str) -> str:
    """Classify a review message: "reject", "approve", or "none".

    Verdict-line precedence (mdu-53): a standalone verdict line decides the
    message alone -- body prose never overrides or vetoes it, including when
    the verdict word is one the phrase regexes do not know (an explicit
    unrecognized verdict is not a round).  A message with no verdict line
    falls back to the guarded body matchers (mdu-52 semantics).
    """
    candidate = _verdict_line(_strip_think(text))
    if candidate is not None:
        if VERDICT_REJECT_PHRASE_RE.match(candidate):
            return "reject"
        if VERDICT_APPROVE_PHRASE_RE.match(candidate):
            return "approve"
        return "none"
    vt = _verdict_text(text)
    if _rejects(vt):
        return "reject"
    if APPROVAL_RE.search(vt):
        return "approve"
    return "none"


def _is_rejection(text: str) -> bool:
    """True when the message classifies as a rejection round."""
    return _review_class(text) == "reject"


def _is_approval(text: str) -> bool:
    """True when the message classifies as an approval round."""
    return _review_class(text) == "approve"
```

`_is_rejection`/`_is_approval` (rewritten in place at session_signals.py
L196-207) become thin wrappers, so **both existing call sites stay
byte-unchanged**: the streak loop (`session_signals.py:336` /
`session_signals.py:341`, `if _is_rejection(text): … elif _is_approval
(text): …` — a `"none"` message no-ops, an `"approve"` message resets, which
is exactly the un-sticking of the compounding bug) and the metrics counter
(`session_signals.py:1459`). The suggestion's "(or any agent)" reading is
satisfied structurally: `_review_class` is agent-agnostic; the *call sites*
keep their existing reviewer gating (round counting stays reviewer-only —
changing that would alter streak semantics and is out of scope). Cost note:
the if/elif loop calls `_review_class` twice per reviewer message (once per
wrapper); texts are small and this runs once per message — accepted for
byte-identical call sites.

### 3.3 The adaptation: suggestion rule 2 is NOT shippable literally

The suggestion (and the brief) states: *"a message with no verdict line
(mid-review analysis) is not a rejection or approval round"*, i.e. verdict-less
messages would never count as rounds. **This rule does not adapt to the code**
— the brief's own instruction — because prose verdicts without verdict lines
are the canonical *true-positive* shape of this detector, pinned green since
mdu-50:

- `tests/test_session_signals.py:71-72` — "I request changes because tests
  are missing" / "I still request changes; docs missing" → streak MUST fire
  (both lines start with "I" — no verdict line under any defensible bare-word
  set). Same file L85, L93/L95, L114/L119 (think-stripped prose), L358
  ("I REJECT this: docs missing").
- `tests/`
  `test_mdu_50_session_store_selection.py:211,220` — "I request changes:
  tests missing" / "docs missing" ×2, the v1-tree streak fixture.
- `tests/`
  `test_mdu_52_rejection_matcher.py` cases 4, 5 ("changes requested: docs
  missing"), 6, 7 ("I REJECT this"), 12, 15 — all prose, all pinned True.

No agent prompt mandates a verdict-line format (§0), so live reviewers can
and do reject in prose; under the literal rule the detector goes blind on its
primary historical shape and ~10 pinned true positives across three files
invert. The brief's re-pin authority names only the mdu-52 file, which is
incompatible with that blast radius.

**Adapted rule (equivalent intent, shippable):** a verdict-less message is
classified by its guarded body, and the guard set is extended (D-3) so that
the two *observed* verdict-less FP modes — prose negation ("it's not a
rejection") and quoted matcher vocabulary (backticked regex source and
example strings) — read as non-rounds. Verdict-bearing FP modes are killed
structurally by precedence (D-1/D-2). The residual — unquoted *affirmative*
rejection vocabulary in verdict-less prose (e.g. a NIT writing "REJECTION_RE
misses the rejects inflection" without quoting) — remains possible, is
disclosed in SKILL.md, and stays covered by the standing manifest-disagreement
rule (trust the manifest, trace the matching event). This is the same residual
mdu-52's decisions log routed to 20261102-1, now narrowed from "any quoted
matcher vocabulary" to "unquoted affirmative prose only".

## 4. D-3 — guard extensions: prose negation + backtick spans

Two edits to `VERDICT_MENTION_RE` (session_signals.py L52-72), nothing else in
the guard set:

1. **Prose negation** (suggestion item 3, literal). Replace the
   `\b(?:no|zero)\s+rejections?\b` branch with:

   ```python
   r"|\b(?:no|zero|not)\s+(?:an?\s+)?rejections?\b"  # adjacent/prose negation
   r"|\bnot\s+rejecting\b"                           # negated progressive
   ```

   Covers "no/zero rejections" (unchanged), "not a rejection", "not an
   rejection", "not rejections", "not rejecting" — the FP #1 wording.
   Locality preserved: "not a rejection, but I must request changes" strips
   only the negation and still matches (pinned). "not approved" is untouched
   by this guard (it is a REJECTION_RE phrase, not a negation of one) — mdu-52
   case 10 holds.

2. **Backtick-span mention** (new branch, placed FIRST in the alternation so
   the longest backtick span strips in one pass):

   ```python
   r"(?i)`[^`\n]*(?:request changes|changes requested|do not approve"
   r"|not approved|reject(?:ed|s|ing|ion|ions)?)[^`\n]*`"
   ```

   Any single-line backtick-delimited span *containing* rejection vocabulary
   is metalanguage: the regex source `reject(?:ed|s|ing|ion|ions)?`, the
   guard-branch quote `rejections? <op> <digit>`, and the backticked evidence
   template `"rejections from the two rounds: REQUEST CHANGES"` (shape 3's
   body quotes are backtick-wrapped around the inner double quotes — that is
   how the recorded message quotes them). This generalizes mdu-52's
   quoted-standalone-phrase stance ("verdicts in this corpus are unquoted")
   from exact phrases to any backticked span. The `'`/`"` exact-phrase branch
   is kept verbatim — apostrophe contractions ("I'd", "don't") make
   generalized quote-pair spans unsafe (two apostrophes with a stem between
   them would swallow prose), while backticks are unambiguous in this corpus.

**Narrowing proofs** (the mdu-52 invariant, extended): every span the two new
branches strip contains a `reject`/`rejection` stem, so space-substitution
can only remove potential matches, never create one. Idempotence: each
substitution removes the span *including its delimiters*, so a second pass
cannot re-match. The no-newline constraint (`[^`\n]`) prevents a stray
backtick from swallowing a paragraph, and fenced blocks are safe because a
fence marker line ("```") cannot satisfy the span pattern (backticks are
excluded from span content). Existing mdu-52 pins re-verified: the
backtick-span branch subsumes only spans that already contained a stem —
`` `review_reject_streak` `` was already stripped by the kind-collocation
branch and stays False; case 11's `_verdict_text("x'reject'y") == "x y"`
uses `'` delimiters and is untouched.

## 5. D-4 — reconciling the strictly-narrowing invariant

Where it is pinned: the mdu-52 design doc §5 (D-4), the mdu-52 test file
docstring L1-7 and case-12 comment L198, and `.agents/memory/decisions.md`
L110 (orchestrator-owned). The claim has two halves that now part ways:

- **Guard-set half — still true, unchanged**: VERDICT_MENTION_RE branches may
  only remove matches (D-3 proofs). No input flips rejection False→True
  *within the body tier*.
- **Matcher-level half — superseded**: verdict-line precedence is not a
  guard; it is a precedence rule that by design flips `_is_rejection`
  True→False (APPROVE-verdict message with rejection-vocabulary body —
  shapes 2 and 3) and `_is_approval` False→True (the same messages, whose
  approval was being vetoed by the FP). These flips ARE the fix. The
  "no true verdict is lost" half remains true and is now test-pinned from
  both sides: all 15 mdu-52 cases and every mdu-50/51 fixture assert
  unchanged values under mdu-53 (§D-5).

**Decision: reword and scope, in the mdu-52 test file only** (the mdu-52
design doc is a historical record of its MDU and is not edited;
decisions.md is updated by the orchestrator at commit, not by the
implementer):

- Docstring L1-7 gains one sentence: *"mdu-53 layers verdict-line precedence
  on top (a standalone verdict line classifies the whole message; see the
  mdu-53 design doc and* `tests/` *`test_mdu_53_verdict_line_precedence.py`):
  the narrowing claim below is scoped to the guard set and the no-verdict-line
  body tier — all 15 cases here hold byte-identical."*
- Case-12 comment L198 gains: *"; still true under mdu-53 — guards only
  remove matches, and verdict-line precedence never removes a true verdict
  (these assertions are unchanged)."*

Zero assertion edits accompany either reword (AC-10).

## 6. D-5 — existing-test impact: zero assertion edits

Every fixture that touches rejection/approval classification, re-derived
under the new two-tier rule (verified case-by-case during this design):

| Fixture (file:line, text) | Tier | New class | Pinned value holds |
|---|---|---|---|
| test_session_signals.py:71,72,85,93,95 — "I request changes…" prose | body | reject | ✓ |
| test_session_signals.py:94 — "LGTM, approving" | bare line | approve | ✓ |
| test_session_signals.py:103-104 — think-only | — | none | ✓ (empty after strip) |
| test_session_signals.py:114,119 — think + prose REQUEST CHANGES | body | reject | ✓ |
| test_session_signals.py:357 — "REQUEST CHANGES: tests missing" | bare line | reject | ✓ |
| test_session_signals.py:358 — "I REJECT this: docs missing" | body | reject | ✓ |
| test_session_signals.py:359 — "LGTM" / 372,373 — "REJECT" | bare line | approve / reject | ✓ |
| test_mdu_50…py:211,220 — "I request changes: …" ×2 | body | reject | ✓ (streak fires) |
| test_mdu_51…py:302,307,327,960,970 — "REQUEST CHANGES: …" | bare line | reject | ✓ (`review_rejections == 2` holds) |
| test_mdu_51…py:312 — "Approved, LGTM" | bare line | approve | ✓ (streak resets) |
| test_mdu_52…py cases 1-15 | mixed | — | ✓ all 15 (incl. case 8: "APPROVE round 1 — …" moves from guard-based approval to precedence-based approval, same asserted values; case 12 "Verdict: REJECTION" and case 15 "Verdict: REJECTED, request changes" via the labelled shape; case 15's unquoted "rejections from the two rounds: REQUEST CHANGES" via body fallback with the metric-guard span locality) |

The mdu-52 file's only edits are the §D-4 rewordings. The additive
`review_approvals` metrics key (§D-9) breaks nothing: every existing metrics
assertion is key-access (`["review_rejections"]`, `["agents"]`), never a
full-dict equality (grep-verified across `tests/`).

## 7. D-6 — test plan: new file

New file `tests/`
`test_mdu_53_verdict_line_precedence.py` (conventions: importlib module load
and `_event` helper copied from the mdu-52 file). Required cases:

1. `test_labelled_approve_verdict_beats_rejection_vocabulary` — FP #2 shape:
   a `## Verdict: APPROVE` line + body quoting the backticked regex source
   and "a reviewer discussing the detector is not rejecting" →
   `_is_rejection` False, `_is_approval` True, `_review_class == "approve"`.
2. `test_labelled_approve_with_suffix_qualifier_stays_approval` — FP #3
   shape: `## Verdict: APPROVE (cycle-2 delta)` + body quoting
   `rejections? <op> <digit>` and the backticked evidence template →
   approval; PLUS the flip-trap pin: `## Verdict: APPROVE (rejections all
   addressed)` must stay approval (suffix can never flip the class — this is
   the pin that fails if phrase classification uses search instead of match).
3. `test_matcher_analysis_session_reads_zero_rejections_and_two_approvals` —
   end-to-end FP replay: just-code event + the three FP-shaped reviewer
   messages (shapes 1-3 above) → `_compute_metrics` reads
   `review_rejections == 0` and `review_approvals == 2`; no
   `review_reject_streak` signal.
4. `test_approve_verdict_resets_a_real_streak` — the compounding-bug pin:
   two genuine rejections, then the FP #2-shaped APPROVE message → NO streak
   signal (pre-fix: the streak fires AND sticks because the approval was
   vetoed).
   Case-4 wording, reconciled at implement (2026-11-03): "NO streak signal"
   is pinned as *exactly one* streak closed by that approval — the two
   genuine rejections still fire it and the APPROVE-verdict message never
   enters `streak_texts`, so the pre-fix failure mode is still caught, while
   a zero-signal assertion would have erased two true rejections (AC-6 reads
   through this reconciliation).
5. `test_verdictless_analysis_is_not_a_round` — verdict-less analysis fixture
   quoting REJECTION_RE by name, the backticked regex source, "it's not a
   rejection", and backticked example strings → `_is_rejection` False,
   `_is_approval` False, `_review_class == "none"`; end-to-end: two such
   events + an approval → `review_rejections == 0`, no streak.
6. `test_reject_and_request_changes_verdict_lines_still_count` —
   `## Verdict: REJECT`, `## Verdict: REQUEST CHANGES — tests missing`, bare
   `REJECT`, `REQUEST CHANGES: tests missing` → all rejection; end-to-end:
   two labelled REJECT lines fire the streak.
7. `test_bare_decision_words_at_line_start` — "APPROVE round 1 — …" →
   approval; "LGTM, approving" → approval; "REJECTED — cycle 2" → rejection;
   "Approved, LGTM" → approval.
8. `test_noun_initial_and_quoted_lines_are_not_verdict_lines` —
   "rejections from the two rounds: REQUEST CHANGES" as a full message stays
   a body-tier rejection (mdu-52 case 15 continuity) BUT is not a verdict
   line (`_verdict_line` returns None); a message with `## Verdict: APPROVE`
   plus a *later* opposite verdict line classifies approve (first line
   wins); a fenced block containing `## Verdict: REQUEST CHANGES` plus a
   real `## Verdict: APPROVE` line classifies approve; a blockquoted
   `> ## Verdict: REQUEST CHANGES` is not a verdict line.
9. `test_unrecognized_verdict_value_is_not_a_round` — `## Verdict: NEEDS
   WORK` with a body containing "I request changes" → `"none"` (body prose
   must not override even an unrecognized verdict); `## Verdict: I approve`
   → `"none"` (disclosed residual, pinned as documented behavior).
10. `test_extended_negation_guard` — "it's not a rejection" → False; "we are
    not rejecting this design" → False; "not a rejection, but I must request
    changes" → True (locality); "no rejections"/"zero rejections" → False
    (mdu-52 continuity).
11. `test_backtick_span_guard` — the backticked regex source alone → False;
    backticked `rejections? <op> <digit>` → False; backticked evidence
    template → False; `_verdict_text` idempotence on each; locality: a
    backticked mention followed by an unquoted "but I request changes" →
    True.
12. `test_metrics_approvals_key_is_additive` — a reviewer reject/approve/
    none mix counts `review_approvals` for approvals only;
    `review_rejections` behavior unchanged; non-reviewer approval-vocabulary
    messages count nowhere (agent gate unchanged).

Mutation guidance for the test agent: (a) revert `_is_rejection` to
body-only semantics → cases 1, 2, 4 fail; (b) delete the negation branch →
case 5 and the case-10 negation half fail; (c) delete the backtick-span
branch → cases 2, 5, 11 fail; (d) switch phrase classification from match to
search → the case-2 suffix-flip pin fails; (e) add nouns to the bare-word
set → case 8 fails.

## 8. D-7 — SKILL.md behavior note (exact)

Append to the `review_reject_streak` bullet (SKILL.md L109, after "…a
reviewer discussing the detector is not rejecting."):

> A standalone verdict line — `## Verdict: …` or a line starting with
> REJECT / APPROVE / REQUEST CHANGES / LGTM — classifies the whole message:
> an APPROVE-verdict message whose body discusses rejection vocabulary is an
> approval round, not a rejection, and a message with no verdict line is
> classified by its body, where prose negations ("not a rejection", "not
> rejecting") and backtick-quoted spans are mentions, not verdicts.

No other SKILL.md line changes.

## 9. D-8 — agent-improvements.md closure edit (exact; implement phase)

Transform entry 20261102-1 (agent-improvements.md L667-670): header →
`- [x] id: 20261102-1 | severity: high | target: session-introspect-skill | kind: detector_gap | **RESOLVED 2026-11-03 (mdu-53)**`, and append after the
apply-now line:

```markdown
  - note (2026-11-03, mdu-53): **RESOLVED — verdict lines now have
    precedence** (`VERDICT_LINE_RE` + `_verdict_line` + `_review_class` in
    session_signals.py; `_is_rejection`/`_is_approval` are `_review_class`
    wrappers, both call sites byte-unchanged): a standalone verdict line
    (`## Verdict: …` with prefix-matched value, or a line starting with
    REJECT / REJECTED / APPROVE / APPROVED / REQUEST CHANGES / LGTM)
    classifies the message alone — body prose never overrides or vetoes it, which fixes the
    approval-veto compounding bug in one rule. The negation guard extends to
    "not a(n) rejection(s)" and "not rejecting"; a new backtick-span guard
    treats any backticked span containing rejection vocabulary as a mention.
    Pinned by tests/test_mdu_53_verdict_line_precedence.py: the three live FP
    shapes read review_rejections 0 (approvals 2, streak resets), a
    verdict-less analysis message is not a round, REJECT/REQUEST CHANGES
    verdict lines still count, and all 15 mdu-52 pins plus the mdu-50/51
    fixtures hold byte-identical (zero assertion edits; the mdu-52 file's
    narrowing wording is re-scoped to the guard set per the mdu-53 design
    §D-4). Design §D-2 documents the one adaptation: "no verdict line ⇒ not
    a round" was NOT shippable literally (it would invert ~10 pinned
    prose-verdict true positives across three test files and blind the
    detector to the canonical live rejection shape); the equivalent-intent
    rule is verdict-line precedence + the extended guards, with the residual
    (unquoted affirmative rejection vocabulary in verdict-less prose)
    disclosed in SKILL.md. Deploy gate per mdu-53 design §D-10: 4-way
    byte-identity plus the live re-probe of the FP session tree
    (ses_e63839af6ffe3a6SM2Iv0Gqgm7) reading review_rejections 0 and
    review_approvals >= 2. The apply-now is retired in favor of the standing
    rule: when the script's rejection count disagrees with the manifest
    phase notes, trust the manifest and trace the matching event.
```

The `.agents/memory/` watch note ("treat `review_rejections>0` as unverified
until verdict-line precedence lands") is orchestrator-owned memory — the
orchestrator may retire it at commit; the implementer does not touch it.

## 10. D-9 — output spec: additive only, one key

- **No change**: `signals[]` (all kinds, all evidence/suggestion/apply-now
  templates — the streak evidence string keeps its exact shape so future FPs
  remain diagnosable against it), `notes[]`, `info{}` (store selection,
  v2_extraction, time_range), `metrics["agents"]`, and the CLI surface
  (`--cwd / --session-id / --harness / --manifest`, exit codes).
- **Additive**: `metrics` gains `review_approvals` (int; reviewer-gated,
  counted in `_compute_metrics` next to `review_rejections` via
  `elif _is_approval(text)`), mirroring the rejection counter. This is the
  minimal additive change that makes the live AC machine-checkable: the
  brief's gate ("approvals ≥ 2") is otherwise unobservable — the script emits
  no approval count, and the QA history (mdu-52) shows inline
  `python3 -c` probes get shell-denied while plain `python3 <script>` runs
  pass, so the gate must read the script's own JSON. It is a *new* counter;
  every existing counter and key is untouched (the brief's
  "counters untouched" clause is satisfied in the same sense as mdu-52's
  additive `info` keys: existing bytes identical, additions only).
- `__all__` and every public signature unchanged.

## 11. D-10 — verification, deploy, and the live gate

1. **Base**: `timeout 300 python3 -m pytest tests/ -q` green (800 existing +
   new, zero existing-assertion edits); `./build.sh` exit 0.
2. **Overlay**: from `$WORKSPACE/`
   `opencode_agents` run `./build.sh` exit 0 — no overlay source edits;
   the fixed skill flows through the base layer.
3. **Deploy**: `./deploy.sh` dry-run clean, then `./deploy.sh --force`.
4. **Byte-identity (4-way, mdu-52 convention)** — `cmp`/`sha256sum` the
   source of record against: the overlay build copy
   (`$WORKSPACE/` `opencode_agents/build/` `skills/session-introspect/`
   `scripts/session_signals.py`), the installed opencode copy
   (`~/.config/opencode/skills/` `session-introspect/scripts/`
   `session_signals.py`), and the installed grok copy
   (`~/.grok/skills/` `session-introspect/scripts/`
   `session_signals.py`).
   Verify every target that actually deployed; record any skipped CLI.
5. **Live FP regression gate** (this is the deploy/validation gate the brief
   designates). Run from the base repo root — the FP session's directory is
   the base repo, and wrong-directory detection needs the cwd match. The
   backslash continuations are part of the command (they keep every line
   under the secret-scan path-lexeme limit and are plain shell syntax):

   ```bash
   cd $BASE   # base repo root: $WORKSPACE/ open-agent-definitions
   timeout 120 python3 ~/.config/opencode/skills/\
   session-introspect/scripts/\
   session_signals.py --session-id ses_e63839af6ffe3a6SM2Iv0Gqgm7
   ```

   Expected JSON (assert these fields, record before/after in the run
   manifest — before: `metrics.review_rejections == 3` plus a false
   `review_reject_streak` HIGH):

   - `harness == "opencode"`, `session_id == "ses_e63839af6ffe3a6SM2Iv0Gqgm7"`
     (a mismatched/empty id means wrong-directory selection — fix the cwd,
     do not re-run blind);
   - `metrics.review_rejections == 0`;
   - `metrics.review_approvals >= 2` (expected exactly 2: the two
     APPROVE-verdict reviewer messages; ≥2 is the asserted bound because a
     further verdict-less approval-vocabulary reviewer message would also
     legitimately count);
   - no `review_reject_streak` entry in `signals[]`.

   Fallback if the session id no longer resolves (store rotation): replay
   the three recorded FP shapes (§1 table) through a `/tmp/opencode` sqlite
   v2 fixture and assert the same three fields; note the substitution in the
   run manifest (mdu-52 §9.5 precedent).
6. **No model re-probe**: zero config/registry/model-map rows change; this
   design assigns no model ids (mdu-52 §9.6 precedent).

## 12. Out of scope (deliberate exclusions)

1. Distant negation ("no reason to reject", "not rejected", "doesn't
   reject") — negation stays adjacent-only; disclosed, not pinned.
2. Unquoted affirmative rejection vocabulary in verdict-less prose — the
   D-2 residual; standing manifest-disagreement rule covers it.
3. Generalized `'`/`"` span stripping — apostrophe contractions make
   quote-pair spans unsafe (D-3); only exact quoted phrases and backtick
   spans are mentions.
4. Fenced-block stripping *inside* `_verdict_text` (fences are skipped only
   for verdict-line detection); a fenced quote in a verdict-less message can
   still body-match. Not observed live; disclosed.
5. "changes requested" / "rejecting" / nouns as bare decision words; label
   values that do not start with a verdict word ("## Verdict: I approve" →
   non-round, pinned as documented behavior).
6. Reviewer-only round counting (the agent gate) — unchanged; the
   suggestion's "(or any agent)" is satisfied by the agent-agnostic
   classifier function, not by widening the gates.
7. `QA_FAIL_VERDICT` and all other detectors; the streak-loop consumer
   logic, `_family` pooling, and both extraction pipelines — byte-unchanged.
8. Historical re-interpretation of recorded signals — past introspections
   stand as written; only future runs get the fix.

## 13. Acceptance criteria

- **AC-1** Precedence implemented per §D-1/§D-2: `VERDICT_LINE_RE`,
  `VERDICT_REJECT_PHRASE_RE`, `VERDICT_APPROVE_PHRASE_RE`, `_verdict_line`,
  `_review_class` added; `_is_rejection`/`_is_approval` rewritten as
  wrappers; the call sites at session_signals.py:336, :341, :1459 are
  byte-unchanged; `REJECTION_RE`, `APPROVAL_RE`, `QA_FAIL_VERDICT`, the
  extraction pipelines and `_family` pooling are byte-unchanged.
- **AC-2** Labelled verdict lines classify by prefix-matched value:
  `## Verdict: APPROVE (cycle-2 delta)` → approval; `## Verdict: REJECT` /
  `REQUEST CHANGES` / `REJECTED` / `REJECTION` / `NOT APPROVED` → rejection;
  a value suffix can never flip the class (the "(rejections all addressed)"
  pin).
- **AC-3** Bare decision words (REJECT / REJECTED / APPROVE / APPROVED /
  REQUEST CHANGES / LGTM) at line start (≤3 leading spaces) classify the message;
  noun-initial and progressive-initial lines are not verdict lines.
- **AC-4** Fenced-code lines are skipped; blockquoted and 4+-space-indented
  lines never match; the first verdict line wins over later opposite lines.
- **AC-5** FP #1 pin: a verdict-less analysis message (prose "it's not a
  rejection", backticked regex source, backticked example strings) is not a
  round — matcher-level and end-to-end (`review_rejections == 0`, no
  increment).
- **AC-6** FP #2/#3 pins: APPROVE-verdict messages quoting matcher
  vocabulary read `review_rejections == 0`, count as approvals
  (`review_approvals`), and reset an open streak (case 4: no streak signal
  after two genuine rejections + the APPROVE-verdict message).
- **AC-7** REJECT / REQUEST CHANGES verdict lines still count as rejections
  (matcher-level and end-to-end streak from two labelled REJECT lines).
- **AC-8** Extended negation guard: "not a(n) rejection(s)" and "not
  rejecting" do not match; "not a rejection, but I must request changes"
  still matches; "no/zero rejections" behavior unchanged.
- **AC-9** Backtick-span guard: backticked spans containing rejection
  vocabulary are mentions (regex source, `rejections? <op> <digit>`,
  backticked evidence template); `_verdict_text` idempotence holds; span
  locality keeps a following unquoted verdict matching.
- **AC-10** Zero existing-assertion edits: the full suite is green at 800 +
   new; the mdu-52 file changes only its docstring and case-12 comment per
   §D-4; the §D-5 fixture inventory holds.
- **AC-11** Output is additive-only: `metrics` gains `review_approvals`;
   every existing JSON key, signal template, note, and CLI behavior is
   byte-identical.
- **AC-12** SKILL.md gains exactly the §D-7 sentence; no other SKILL.md
   change.
- **AC-13** agent-improvements.md 20261102-1 flipped to
   `[x] … **RESOLVED 2026-11-03 (mdu-53)**` with the exact §D-8 note,
   applied in the implement phase (not by the introspector).
- **AC-14** Deploy + live gate: base and overlay `./build.sh` exit 0;
   `./deploy.sh` dry-run clean then `--force`; 4-way byte-identity; the §D-10
   probe command against `ses_e63839af6ffe3a6SM2Iv0Gqgm7` (installed script,
   from the base repo root) reads `metrics.review_rejections == 0`,
   `metrics.review_approvals >= 2`, and no `review_reject_streak` in
   `signals[]`; fallback fixture replay + manifest note if the id no longer
   resolves; before/after recorded in the run manifest.
- **AC-15** Diff surface is exactly: `skills/session-introspect/`
   `scripts/session_signals.py`, `tests/`
   `test_mdu_53_verdict_line_precedence.py` (new), the mdu-52 test file
   (docstring + one comment), `skills/session-introspect/` `SKILL.md` (one
   sentence), `agent-improvements.md` (§D-8 closure), and this design doc.
   No agent-definition files, no overlay source, no config/registry/
   model-map rows → no model re-probe.

## 14. Phase order for the implement brief

1. **implement-1**: the §D-1 constants and helpers, the §D-2 `_review_class`
   rewrite, the §D-3 guard branches, and the §D-9 additive counter in
   `session_signals.py`; `tests/`
   `test_mdu_53_verdict_line_precedence.py` per §D-6; the §D-4 rewordings in
   the mdu-52 test file; the §D-7 SKILL.md sentence; the §D-8 closure edit;
   `timeout 300 python3 -m pytest tests/ -q` green; base `./build.sh`.
2. **Standing loop tail:** review → test → deploy (§D-10 steps 2-6, including
   the live FP regression gate) → validate → introspect → commit, per the
   mdu-lifecycle order.
3. **Introspection note (dogfood):** this MDU's own review rounds will quote
   `VERDICT_LINE_RE`, the phrase alternations, and verdict-line examples —
   the exact recurring class this MDU fixes. Expect the script run on this
   MDU's own tree to read `review_rejections` equal to the *true* verdict
   count only; any disagreement with the manifest phase notes still follows
   the standing rule (trust the manifest, trace the matching event).

## Appendix A — the three live FP shapes (design evidence)

Recorded probe output (agent-improvements.md 20261102-1, L668), quoted as
evidence; the full session texts are not committed:

1. **Verdict-less mid-review analysis** — prose contains "it's not a
   rejection". No verdict line. Fails today because the negation guard covers
   only "no/zero rejections".
2. **`## Verdict: APPROVE` + matcher-quoted body** — body quotes the regex
   source `reject(?:ed|s|ing|ion|ions)?` (backticked) and writes "a reviewer
   discussing the detector is not rejecting". Fails today because a
   backticked regex source is not an exact quoted phrase, and the body veto
   suppresses the approval reset.
3. **`## Verdict: APPROVE (cycle-2 delta)` + guard-branch quotes** — body
   quotes `rejections? <op> <digit>` and the evidence template
   `"rejections from the two rounds: REQUEST CHANGES"` (backticked around
   the inner quotes). Fails today because quoted example strings are longer
   than the exact-phrase guard, and the suffix-bearing verdict line is not
   consulted at all.

All three become non-rejections under the two-tier rule: shapes 2 and 3 via
verdict-line precedence (tier 3), shape 1 via the extended negation and
backtick-span guards (tier 4).
