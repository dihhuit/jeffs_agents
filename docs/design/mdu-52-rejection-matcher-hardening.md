# MDU-52 · Rejection-matcher hardening — word-boundary verdicts + mention guards

Closes **20261101-4** (warn, detector_gap): the live mdu-51 false positive where
`_is_rejection` substring-matched the bare word `reject` inside a code-reviewer NIT's
quotation of the signal kind `review_reject_streak`, recording `review_rejections: 1`
for a session whose manifest truth was APPROVE round 1, 0 rejections.

Done looks like: `skills/session-introspect/scripts/session_signals.py` swaps its
substring phrase-list matching for word-boundary regex matching with three narrow
mention/negation guards; a new `tests/test_mdu_52_rejection_matcher.py` pins the FP
classes and the true-verdict negatives; `skills/session-introspect/SKILL.md` gains one
behavior-note sentence; `agent-improvements.md` entry 20261101-4 is flipped to RESOLVED
with the exact note in §8 (applied in the implement phase, not by the introspector);
the full suite is green with zero edits to existing assertions; base + overlay builds
exit 0 and the deployed copies are byte-identical to the source of record, with a live
re-probe of the mdu-51 session reading `review_rejections: 0`. No agent-definition
files, no overlay source, no config/registry/model-map rows → **no model re-probe**.
No model-id assignments are made by this design; tier selection follows the
mdu-lifecycle table. Verdict format: implement reports per-target `file:function`
completion; QA ends with `QA GRADE: PASS` or `QA GRADE: FAIL`.

## 0. Scope — files surveyed (exactly)

- `skills/session-introspect/scripts/session_signals.py` — L1-60 (constants),
  L140-184 (`_strip_think`, `_contains_any`, `_is_rejection`, `_is_approval`),
  L275-349 (streak loop), L1380-1434 (`_compute_metrics`); grep of every
  `_contains_any|_is_rejection|_is_approval|REJECTION_PHRASES|APPROVAL_PHRASES`
  call site (they are L298, L303, L1421 only).
- `runs/mdu-51-v2-text-extraction/introspection.md` L1-40 (FP trace, L20).
- `agent-improvements.md` L600-609 (20261101-3 closure style; 20261101-4 entry) + grep.
- `tests/test_session_signals.py` L60-124, L345-384 (rejection/approval fixtures).
- `tests/test_mdu_51_v2_text_extraction.py` L290-334, L993-994 (AC-2 fixtures).
- `tests/test_mdu_50_session_store_selection.py` L193-243 (v1 streak fixture).
- `skills/session-introspect/SKILL.md` — grep anchors L109, L124.
- `docs/design/mdu-50-session-signals.md` §1, §7-8; `docs/design/mdu-51-v2-text-extraction.md`
  §10-11 (deploy/AC conventions mirrored here).
- Overlay deploy surface: `opencode_agents/deploy.sh` (entry point) and
  `opencode_agents/AGENTS.md` (install targets); glob confirms
  `opencode_agents/build/skills/session-introspect/scripts/session_signals.py` exists.

## 1. The live defect

`_is_rejection` (session_signals.py:161) lowers the text and tests
`_contains_any(..., REJECTION_PHRASES)` — plain substring `in`. The list (L34-40)
ends with the bare `"reject"`, added by mdu-50 so bare `REJECT` verdicts match. Any
occurrence of the character sequence counts, so a reviewer NIT that *mentions the
detector* — quoting the signal kind `review_reject_streak`, the constant
`REJECTION_PHRASES`, or the phrase entries themselves — is scored as a rejection
round. Consequences: `metrics.review_rejections` over-reports (observed: 1 vs true 0)
and, with two such NITs, the streak detector (L286-349) would fabricate a
`review_reject_streak` signal and drive unnecessary fix rounds. Same substring class
exists on the approval side (`APPROVAL_PHRASES = ["approve", "lgtm", "sign-off"]`,
L50): e.g. "these changes are **unapproved**" contains "approve" and today reads as
`_is_approval == True`.

Call-site blast radius (verified by grep): `_is_rejection`/`_is_approval` are consumed
only at L298/L303 (streak loop) and L1421 (`_compute_metrics`). `_contains_any` has
exactly one caller (`_is_rejection`, L162). No test imports the phrase constants or
`_contains_any`; the only direct test call into the matchers is
`session_signals._is_rejection(...)` (test_mdu_51 L273). The fix is therefore fully
contained in the constants block + three helper functions.

## 2. D-1 — Python `\b` semantics with underscores (verified analysis)

Python 3 `re` (str patterns, default Unicode): `\w` ≡ `[a-zA-Z0-9_]` plus Unicode
word characters; **underscore is a word character**. `\b` matches only at a
transition between a `\w` and a non-`\w` character (or a string edge).

Applied to `review_reject_streak`: the character before the inner `reject` is `_`
(`\w`) and `r` is `\w` → no boundary; the character after `reject` is `_` (`\w`) and
`t` is `\w` → no boundary. Therefore **`\breject…\b` cannot match inside
`review_reject_streak`** — word-boundary matching alone kills the observed live FP.
Same for the constant token `REJECTION_PHRASES`: a *leading* boundary does exist at
the token edge (string start or a quote before `R`), but the trailing `N`→`_` pair is
`\w`↔`\w`, so `\breject(?:ion)?\b` fails there too. This is documented, stable
`re` behavior — and `re.ASCII` does **not** remove `_` from `\w`, so the property
holds under either flag set. The design still compiles without `re.ASCII`.

Two limits of `\b` alone, which force the guards in D-3:

1. **Non-underscore spellings of the kind.** In prose forms `review reject streak`
   and `review-reject-streak`, the separators (space, hyphen) are non-`\w`, so
   boundaries *do* exist around `reject` and `\breject\b` **would** match. Word
   boundary alone does not exclude these.
2. **Quoted phrase-list entries.** In a NIT like `…lists the bare 'reject' entry and
   the 'request changes' phrase…`, the quotes are non-`\w`, so
   `\brequest changes\b` matches the quoted mention. Word boundary alone does not
   exclude this either.

## 3. D-2 — the new matcher contract

Replace the two phrase lists and `_contains_any` with module-level compiled regexes
(place them in the constants block where L34-40/L50 now sit, with a short comment in
the existing QA_FAIL_VERDICT comment style explaining mention-guard semantics):

```python
REJECTION_RE = re.compile(
    r"\b(?:request changes|changes requested|do not approve|not approved"
    r"|reject(?:ed|s|ing|ion|ions)?)\b",
    re.IGNORECASE,
)
APPROVAL_RE = re.compile(
    r"\b(?:approv(?:e|es|ed)|lgtm|sign-offs?)\b",
    re.IGNORECASE,
)
VERDICT_MENTION_RE = re.compile(
    r"(?i)\b(?:review[\s_-]+)?reject[\s_-]+streak\b"       # the signal kind, any spelling
    r"|\b(?:no|zero)\s+rejections?\b"                      # adjacent negated plural
    r"|[`'\"]\s*(?:request changes|changes requested|do not approve"
    r"|not approved|reject(?:ed|s|ing|ion|ions)?)\s*[`'\"]"  # quoted standalone phrase
)
```

Helpers (rewrite `_is_rejection`/`_is_approval` at L156-169; delete `_contains_any`;
add `_verdict_text` next to `_strip_think`):

```python
def _verdict_text(text: str) -> str:
    """Think-stripped text with mention/negation guards neutralized.

    Each guard match is replaced by a single space (never the empty string)
    so stripping cannot join two fragments into a verdict phrase.
    """
    return VERDICT_MENTION_RE.sub(" ", _strip_think(text))


def _is_rejection(text: str) -> bool:
    return REJECTION_RE.search(_verdict_text(text)) is not None


def _is_approval(text: str) -> bool:
    return APPROVAL_RE.search(_verdict_text(text)) is not None and not _is_rejection(text)
```

Design points:

- **Stem coverage preserves every old whole-word match.** The old bare `"reject"`
  substring matched `reject/rejected/rejects/rejecting/rejection(s)`; the
  `reject(?:ed|s|ing|ion|ions)?` alternation covers exactly those whole-word forms
  (per the 20261101-4 definition change: `\brejected?\b|\brejection\b`, plus the
  inflections the old substring implicitly caught). `approv(?:e|es|ed)` covers
  `approve/approves/approved` — every form the old `"approve"` substring could match
  as a whole word. `sign-offs?` preserves the old `"sign-off"` substring's whole-word
  and plural forms. Deliberately **not** added: `approving` / `approval` (neither
  contains the old substring — adding them would widen, not narrow; see D-4).
- **Case handling** moves from `.lower()` + substring to `re.IGNORECASE` — equivalent
  for this corpus (existing fixtures use `REQUEST CHANGES`, `I REJECT`, `LGTM`).
- **`_is_approval` keeps its precedence**: an approval match vetoes nothing; a
  rejection match still vetoes approval (`do not approve` / `not approved` remain
  rejections, not approvals — both phrases are in `REJECTION_RE`).
- **Consumers untouched.** L298/L303/L1421 call the same two functions with the same
  signatures; the streak loop, `_compute_metrics`, `__all__`, and the CLI surface are
  byte-unchanged. `QA_FAIL_VERDICT` (line-anchored, mdu-50-hardened) is untouched.

## 4. D-3 — the three guards (each narrow, each test-pinned)

`VERDICT_MENTION_RE` is stripped (space-substituted) from the text *after*
`_strip_think` and *before* verdict matching:

1. **Signal-kind mention** — `\b(?:review[\s_-]+)?reject[\s_-]+streak\b`: the kind in
   any spelling — `review_reject_streak` (redundant with `\b` but harmless),
   `review-reject-streak`, `review reject streak`, bare `reject streak`. This is the
   "explicit exclusion for mentions of the signal kind itself". A genuine verdict
   never contains this collocation; a detector-discussing NIT usually does.
2. **Quoted standalone phrase** — a quote/backtick delimiter on both sides of an
   exact phrase/stem (`'reject'`, `` `request changes` ``): the mention form a NIT
   uses when quoting the phrase list. Verdicts in this corpus are unquoted
   (`REJECT`, `REQUEST CHANGES: …`); a scare-quoted verb (`the matcher "rejects" the
   NIT`) is metalanguage and is correctly a mention. Asymmetric or missing closing
   quotes simply don't strip — the word then matches normally.
3. **Adjacent negation** — `\b(?:no|zero)\s+rejections?\b`: exactly the
   20261101-4-required `"no rejections"` class. Local strip, not a global veto:
   `"no rejections in round 1, but round 2 must be rejected: tests missing"` strips
   the negation and still matches `rejected`.

**Space substitution is a hard requirement** (D-2 docstring says so; AC-8 pins it):
replacing with `""` could splice fragments into a phrase; a single space provably
cannot complete a `\b`-anchored phrase that wasn't already contiguous.

## 5. D-4 — narrowing invariant and backward compatibility

**Claim: for every input text, new `_is_rejection` ⇒ old `_is_rejection`.** Each new
regex match implies an old substring match — `reject(?:ed|s|ing|ion|ions)?` always
contains `reject`; `request changes`/`changes requested`/`do not approve`/
`not approved` are literal in both — and the guards only *remove* text. So no input
flips rejection False→True: **no true verdict is lost, no new false positive of the
rejection kind can appear.** Every True→False flip is one of the three mention/negation
forms or an underscore/prefix-embedded token — precisely the FP classes 20261101-4
names.

**Approval side.** New approval matches also imply old substring matches
(`approve/approves/approved` ⊇ `approve`; `sign-offs` ⊇ `sign-off`; `lgtm` literal).
`_is_approval = approval ∧ ¬rejection` with rejection strictly narrower means
approval can flip False→True **only** where an old rejection *false positive* was
vetoing a real approval (the exact interplay AC-6 pins), and True→False only where
the approval word was prefix-embedded — `unapproved`/`nonapproved` (today live FPs:
"unapproved" contains "approve") and `preapproved` (an accepted, rare FN: reviewers
approve with `approve/approved/LGTM/sign-off` as standalone words; all existing
fixtures use exactly those forms).

**Existing-test impact: none.** Grep-verified fixture inventory — no existing
assertion needs editing:

- `tests/test_session_signals.py`: L68 (`I request changes…` ×2), L82, L91
  (`LGTM, approving` → `lgtm`), L101 (think-stripped → empty), L110
  (`I REQUEST CHANGES…`), L355 (`REQUEST CHANGES:…` / `I REJECT this` / `LGTM`),
  L370 (bare `REJECT` ×2) — all whole-word verdict texts; every asserted-True stays
  True (invariant), every asserted-False (think-strip) stays False (narrowing cannot
  create matches).
- `tests/test_mdu_50_session_store_selection.py` L198 (`I request changes: tests
  missing` / `docs missing` ×2).
- `tests/test_mdu_51_v2_text_extraction.py` L297/L324/L993-994 (`REQUEST CHANGES…`,
  `Approved, LGTM`) and L256/L273 (QA approval text — contains no rejection stem).

## 6. D-5 — test plan

New file `tests/test_mdu_52_rejection_matcher.py` (conventions: import
`session_signals`, reuse the `_event` helper style from `tests/test_session_signals.py`;
direct matcher asserts plus two end-to-end asserts through
`collect_signals`/`_compute_metrics`). Required cases:

1. `test_kind_mention_underscore_token_is_not_a_rejection` — reviewer NIT text
   quoting `` `review_reject_streak` `` (bare and backticked forms) →
   `_is_rejection` False. End-to-end (the live mdu-51 FP replay, amplified to the
   streak threshold): two reviewer events of that NIT shape followed by
   `"APPROVE round 1 — NIT folded: the quoted kind is a matcher mention, not a verdict"`
   → **no** `review_reject_streak` signal and
   `_compute_metrics(...)["review_rejections"] == 0` (pre-fix: 1 and, with two NITs,
   a fabricated streak).
2. `test_kind_mention_prose_spellings_are_not_rejections` — `review reject streak`
   and `review-reject-streak` → False (guard, since `\b` alone matches these).
3. `test_nit_quoting_the_phrase_list_is_not_a_rejection` — NIT fixture:
   `NIT (D-2): REJECTION_PHRASES still lists the bare 'reject' entry and the
   'request changes' phrase; word-boundary matching must not treat this note as a
   verdict.` → False. (Without the quoted-phrase guard this input matches.)
4. `test_adjacent_negation_is_not_a_rejection` — `no rejections in this round` /
   `zero rejections recorded` → False; `no rejections, but I must request changes` →
   True (guard is local, verdict survives).
5. `test_genuine_request_changes_verdict_is_a_rejection` — `REQUEST CHANGES: tests
   missing` → True.
6. `test_standalone_rejected_is_a_rejection` — `I rejected this change because tests
   are missing` → True.
7. `test_bare_reject_and_i_reject_still_match` — `REJECT` → True; `I REJECT this` →
   True (in-file companions to the mdu-50 pins).
8. `test_approve_round_one_with_kind_mention_reads_as_approval` — reviewer text
   `APPROVE round 1 — one NIT: the matcher fires on the quoted kind
   "review_reject_streak" (20261101-4); fold the guard into the matcher MDU.` →
   `_is_approval` True, `_is_rejection` False (the 20261101-4 interplay: approval
   with a `reject` lexeme inside a quoted kind must read as approval).
9. `test_unapproved_is_not_approval` — `these changes are unapproved` →
   `_is_approval` False (pre-MDU-52 substring FP on the approval side).
10. `test_do_not_approve_still_rejects_not_approves` — `do not approve this yet` →
    `_is_rejection` True and `_is_approval` False; `not approved` likewise.
11. `test_guard_strip_substitutes_a_space` — `_verdict_text("x'reject'y") == "x y"`
    (pins the space substitution; an empty-string substitution would yield `"xy"`).

Test-agent guidance: cases 1-4 are the FP classes (priority order per
test-patterns), 5-8 the true-negative retention, 9-11 the interplay/implementation
pins; mutation-check by reverting the matcher to substring semantics (or deleting one
guard alternative) and confirming 1-4 and 8-9 fail.

## 7. D-6 — SKILL.md behavior note (one sentence)

Append to the `review_reject_streak` bullet (SKILL.md L109, after "Bare `REJECT`
verdicts count."):

> Verdict matching is word-boundary based; quoted or underscore-joined mentions of
> the signal kind or the phrase list, and adjacent negations ("no rejections"), are
> mentions, not verdicts — a reviewer discussing the detector is not rejecting.

No other SKILL.md line changes (the L124 v2 disclosure is untouched).

## 8. D-7 — agent-improvements.md closure edit (exact; applied in implement phase)

Transform entry 20261101-4 (currently L606-609):

- Header line →
  `- [x] id: 20261101-4 | severity: warn | target: session-introspect-skill | kind: detector_gap | **RESOLVED 2026-11-02 (mdu-52)**`
- Append this note line after the existing `apply-now` line (update the two
  line-number citations to the post-edit locations of the matchers):

```markdown
  - note (2026-11-02, mdu-52): **RESOLVED — verdict matching is now word-boundary based
    with mention/negation guards** (`REJECTION_RE`/`APPROVAL_RE`/`VERDICT_MENTION_RE`
    in session_signals.py replace the substring lists and `_contains_any`), pinned by
    tests/test_mdu_52_rejection_matcher.py: the live mdu-51 FP class (reviewer NIT
    quoting `review_reject_streak`) reads `review_rejections: 0`, a NIT quoting the
    phrase list reads 0, "no rejections" reads 0, while REQUEST CHANGES / bare REJECT /
    "I rejected this change" verdicts still match. Matching is strictly narrowing —
    every new match implied the old substring match, so no true verdict was lost and
    `_is_approval` only gained where a rejection false positive had been vetoing a real
    approval; the mirror substring FP ("unapproved" containing "approve") no longer
    reads as approval. Deploy gate per the mdu-52 design §9: byte-identity across the
    overlay build and every installed skill copy, plus a live re-probe of the mdu-51
    session (ses_e65b5a915ffeqZoJthaEIP04DN) reading `review_rejections: 0` (manifest
    truth: APPROVE round 1). The apply-now is retired in favor of the standing rule:
    when the script's rejection count disagrees with the manifest phase notes, trust
    the manifest and trace the matching event — residual prose-noun mentions (e.g. a
    reviewer discussing "the rejection count") remain possible and are disclosed in
    SKILL.md.
```

This edit is applied by the implement phase (per the MDU brief), not by the
introspector. The `.agents/memory/project.md` watch note (L80, "treat
`review_rejections>0` as UNVERIFIED … until matcher hardening MDU lands") is
orchestrator-owned memory, not MDU diff surface — the orchestrator may retire it at
commit time; the implementer does not touch it.

## 9. D-8 — verification and deploy (mirrors mdu-51)

1. **Base**: `timeout 300 python3 -m pytest tests/ -q` green (785 existing + new,
   zero existing-assertion edits); `./build.sh` exit 0.
2. **Overlay**: `cd $WORKSPACE/opencode_agents && ./build.sh` exit 0 (the fixed skill
   flows through the base layer; **no overlay source edits** — nothing here is
   personal-only).
3. **Deploy**: `./deploy.sh` dry-run clean, then `./deploy.sh --force` (auto-deploys
   to the CLIs on PATH; opencode + grok expected).
4. **Byte-identity (4-way, mirroring mdu-51)** — `cmp` (or `sha256sum`) the source of
   record against every copy:
   - `skills/session-introspect/scripts/session_signals.py` (source of record)
   - `$WORKSPACE/opencode_agents/build/skills/session-introspect/scripts/session_signals.py`
   - `~/.config/opencode/skills/session-introspect/scripts/session_signals.py`
     (when opencode deployed)
   - `~/.grok/skills/session-introspect/scripts/session_signals.py`
     (when grok deployed)

   If a CLI is absent from PATH, verify identity for every target that *was*
   deployed (deploy.sh auto-detects) and record which were skipped.
5. **Live FP regression probe** — run the *installed* script against the exact
   session that produced the FP, from the base repo directory (wrong-directory
   detection requires the session's repo):

   `timeout 60 python3 ~/.config/opencode/skills/session-introspect/scripts/session_signals.py --session-id ses_e65b5a915ffeqZoJthaEIP04DN`

   Expect `metrics.review_rejections == 0` (pre-fix: 1). Record before/after in the
   run manifest. Fallback if that session id no longer resolves (store rotation):
   replay the NIT text through a `/tmp/opencode` sqlite fixture and assert 0 — note
   the substitution in the manifest.
6. **No model re-probe**: zero config/registry/model-map rows change (mdu-50 §8
   precedent).

## 10. Out of scope (deliberate exclusions)

1. Distant negation ("no reason to reject") — negation handling is intentionally
   adjacent-only; general negation is NLP-shaped and unneeded for the observed class.
2. Prose-noun mentions not adjacent to a negator ("the rejection count is wrong") —
   still matches; removing the noun would lose true verdicts ("Verdict: REJECTION").
   Disclosed in SKILL.md; watch via the standing manifest-disagreement rule.
3. Scare-quoted multi-word verdicts and `preapproved`-class approval FNs — accepted
   trade-offs (§5).
4. `QA_FAIL_VERDICT` / QA verdict matching — different mechanism, already
   line-anchored by mdu-50.
5. Streak-loop and `_compute_metrics` consumer logic (L286-349, L1394-1429) —
   untouched; the fix is matcher-local.
6. Any agent-definition file, overlay source file, or memory book — explicitly none.
7. Historical re-interpretation of recorded signals — past introspections stand as
   written; only future runs get the hardened matcher.

## 11. Acceptance criteria

- **AC-1** Word-boundary regex matching (`REJECTION_RE`, `APPROVAL_RE`,
  `re.IGNORECASE`, module-level compiled) replaces substring matching;
  `REJECTION_PHRASES`, `APPROVAL_PHRASES`, and `_contains_any` are deleted; the only
  script edits are the constants block, `_verdict_text`, `_is_rejection`,
  `_is_approval`; consumers (L298/L303/L1421), `__all__`, and the CLI surface are
  byte-unchanged.
- **AC-2** `review_reject_streak` — bare, backticked, or quoted — does not match
  `_is_rejection`; two reviewer events of that NIT shape followed by an approval emit
  **no** `review_reject_streak` signal and `_compute_metrics(...)["review_rejections"]
  == 0`.
- **AC-3** A NIT quoting the phrase list (the `REJECTION_PHRASES` token plus quoted
  `'reject'` and `'request changes'`) does not match `_is_rejection`.
- **AC-4** Prose/hyphen spellings (`review reject streak`, `review-reject-streak`) do
  not match (kind-mention guard; `\b` alone matches these).
- **AC-5** `no rejections` / `zero rejections` does not match; `no rejections, but I
  must request changes` still matches.
- **AC-6** Genuine verdicts still match: `REQUEST CHANGES: tests missing`, bare
  `REJECT`, `I REJECT this`, `I rejected this change because tests are missing`,
  `changes requested`, `do not approve`, `not approved`.
- **AC-7** Approval interplay: `APPROVE round 1 …` text containing a quoted
  `review_reject_streak` reads `_is_approval` True and `_is_rejection` False;
  `do not approve` / `not approved` read rejection-not-approval; `these changes are
  unapproved` is **not** approval; `Approved, LGTM` remains approval.
- **AC-8** Guard substitution replaces each mention with a single space
  (`_verdict_text("x'reject'y") == "x y"`); stripping can never join fragments into a
  verdict phrase.
- **AC-9** Narrowing invariant holds by construction (§5): every regex stem is a
  superstring of an old substring phrase and guards only remove text — no input flips
  rejection False→True (inspection criterion; mutation-checkable per §6).
- **AC-10** Existing suite green with zero assertion edits, including the named pins:
  `tests/test_session_signals.py` (L68, L82, L91, L101, L110, L355, L370),
  `tests/test_mdu_50_session_store_selection.py` (L198),
  `tests/test_mdu_51_v2_text_extraction.py` (L297, L324, L256/L273, L993-994);
  `timeout 300 python3 -m pytest tests/ -q` green at 785 + new.
- **AC-11** `tests/test_mdu_52_rejection_matcher.py` implements the §6 case list
  (1-11), with the two end-to-end asserts in case 1.
- **AC-12** SKILL.md L109 gains exactly the §7 sentence; no other SKILL.md change.
- **AC-13** `agent-improvements.md` 20261101-4 flipped to
  `[x] … **RESOLVED 2026-11-02 (mdu-52)**` with the exact §8 note, applied in the
  implement phase (not by the introspector).
- **AC-14** Deploy: base and overlay `./build.sh` exit 0; `./deploy.sh` dry-run clean
  then `--force`; byte-identity between the source-of-record script, the overlay
  build copy, and every installed skill copy (4-way when opencode + grok both
  deploy); live FP regression probe on the installed script re-running session
  `ses_e65b5a915ffeqZoJthaEIP04DN` reads `review_rejections: 0` (fallback + manifest
  note if the id no longer resolves).
- **AC-15** Diff surface is exactly: `skills/session-introspect/scripts/session_signals.py`,
  `tests/test_mdu_52_rejection_matcher.py` (new),
  `skills/session-introspect/SKILL.md` (one sentence),
  `agent-improvements.md` (§8 closure), and this design doc. No agent-definition
  files, no overlay source, no config/registry/model-map rows → no model re-probe.

## 12. Phase order for the implement brief

1. **implement-1 (script + tests + docs):** the D-2 constants and helpers in
   `session_signals.py`; `tests/test_mdu_52_rejection_matcher.py` per §6; SKILL.md
   sentence per §7; the §8 closure edit in `agent-improvements.md`;
   `timeout 300 python3 -m pytest tests/ -q` green; base `./build.sh`.
2. **Standing loop tail:** review → test → deploy (D-8: overlay build, deploy,
   4-way byte-identity, live FP regression probe) → validate → introspect → commit,
   per the mdu-lifecycle order.
3. **Introspection note (dogfood):** this MDU's own session will contain reviewer and
   agent messages quoting `review_reject_streak` and the phrase list (the subject
   guarantees it). Under the hardened matcher those must read as mentions — expect
   `review_rejections` to equal the *true* verdict count only, and treat any
   disagreement with the manifest phase notes per the standing rule in §8.

## Appendix A — cycle-2 live FP: guard 4 (quantified-metric mention)

The deployed probe found one remaining false positive: an AC-verification report
containing `| AC-2 | test_mdu_51:297 (streak fires, evidence "2 consecutive
rejections") + :324 (review_rejections == 1) |` counted as a rejection round.
These spans are the reject counter's metric name and its evidence/report
templates, not verdicts (the "delete line 678" hypothesis was wrong). Guard 4
extends `VERDICT_MENTION_RE` with four narrow shapes: `review_rejections?`,
`<count> consecutive rejections?` (the word is mandatory — see below),
`rejections? <op> <digit>`, and
`rejections? from`. Narrowing proof: every matched span contains the
`reject`/`rejection` stem, so substitution can only remove matches, never create
one; bare prose "rejections" and all `rejects`/`rejected`/`REJECT`/`request
changes`/`do not approve`/`not approved` verdicts are unchanged.

`consecutive` is mandatory (not `[consecutive]`): a bare `<count> rejections`
span matched prose like "2 rejections remain unaddressed", over-stripping real
verdicts and breaking idempotence ("two review_rejections rejections" lost the
metric name on pass 1, the count span on pass 2). Quantifier/operator coverage
is finite (spelled counts ≥ "four", "several"/"many", `[:|]` separators not
stripped; the tool's own evidence emitter uses digits, so live risk is low) —
accepted limit.
