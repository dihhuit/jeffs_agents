# MDU-35 — Question-tool failure: classification + agent-definition mitigation

Backlog source: `FEATURE_BACKLOG.md` lines 307-322. Evidence source:
`runs/mdu-35-question-tool/evidence.md` (authoritative — this doc cites it,
never re-derives). Predecessors: MDU-14 (mirror parity), MDU-28/34 (span
byte-identity + conditional-grokestrator test machinery this design reuses).

## Surveyed files (read surface — apply-now 20261024-1)

- `runs/mdu-35-question-tool/evidence.md` (full) — authoritative evidence: census, verbatim extracts, determinism table, gaps.
- `FEATURE_BACKLOG.md` (300-322) — MDU-35 contract, classification vocabulary (a)-(d), acceptance criteria.
- `docs/design/mdu-34-resume-block.md` (full) — doc-shape exemplar; routing-table and test-plan house style.
- `prompts/orchestrator.md` (1-109) — base mirror 1; gate span 13-33; Human Approval Gates 73-77; Repository Ownership 79-83.
- `grok/agents/orchestrator.md` (66-115) — base mirror 2; Human Approval Gates 79-83; Repository Ownership 85-89.
- `../opencode_agents` sibling — third mirror at `grok/agents/grokestrator.md` (60-104). **Path correction:** the brief named a nonexistent `overlays/grok/agents/…grokestrator` path; the live source is overlay-root `grok/agents/grokestrator.md` (glob-confirmed; MDU-34 survey agrees). It is not a dead same-name copy — `grokestrator` has no base counterpart.
- `opencode.json` (3748-3765) — the `{"action":"question","resource":"*","effect":"allow"}` entry (line 3759).
- `scripts/lib/validate.py` (48-82) — `ROLE_KEYWORDS["orchestrator"]` fuse list.
- `tests/test_mdu_28_resume_detect.py` (grep) — `OVERLAY_GROKESTRATOR` path constant + `skipif` pattern; span byte-identity precedent.
- `docs/opencode-v2.md` (grep) — v2 `permissions` framing: array of `{action, resource, effect}`; allow/deny only.
- `evals/golden/cases.json` (grep) — no golden case targets the insertion region; prompt-regression risk low.
- `.gitignore` (full) — base `build/` ignored (transient); overlay `build/` is tracked.

## Reproduction path (from evidence §8.1, §2, §4)

1. OpenCode `v2.0.31` (Linux, bun bundle). Run a long autonomous orchestrator
   turn that ends by emitting a `question` tool call (sprite pattern: end-of-MDU
   design/next-step decisions asked while the user is away).
2. Do not answer. Leave the session idle > 60 minutes.
3. Observe the kill, in order: part flips to
   `{"type":"aborted","message":"Tool execution interrupted"}` with
   `executed:false`, `state.status:"error"`; the assistant message ends
   `"finish":"error"` + `"Step interrupted"`; an `idle` row with
   `outcome:"interrupted"` appears at the same epoch second; TUI shows red
   "Asked N questions" with no visible prompt (user-reported; consistent with
   part state — TUI rendering itself not directly observed, evidence §8.4).
4. Verify in storage with the inline-era join (evidence §2):
   `session_message m, json_each(m.data,'$.content')` where
   `json_extract(je.value,'$.type')='tool'` and `$.name='question'`.
5. Nothing re-asks. Forward progress stalls until a manual user message.
   Fast variant (evidence §4d): the identical abort fires in 0.4 min on a manual
   Esc/interrupt — same kill path, different trigger.

## Extracted payloads + exact error (masked; copied from evidence §4)

**Mode A — canonical 60-min abort** (sprite, `ses_e96f46cc3…`, asked
2026-10-24 02:14:34 UTC, orchestrator/glm-5.3-flash). Input head:

```json
{"questions":[{"header":"OQ-1 flag name","options":[{"description":"Top-level pose-JSON boolean, absent = grounded. Becomes corpus-schema vocabulary for jump/attack/hurt/die.","label":"airborne (Recommended)"},…
```

Result, verbatim (60.5 min pending): `"state":{"status":"error","error":{"type":"aborted","message":"Tool execution interrupted"}}`, `"executed":0`; message-level `"finish":"error", … "error":{"type":"aborted","message":"Step interrupted"}}`; session `idle` row `{"time":{"created":…},"outcome":"interrupted"}` at the same instant.

**Mode A — reordering round-trip** (agents workspace, `ses_e8c5def5…`): asked 15:17:30 → pending 67.6 min → abort 16:25:06 (`Tool execution interrupted`; idle `interrupted` 54 ms later) → user 16:51:53 "Question tool keeps failing… Please re-ask the question" → retry 16:52:12, same substance, **completed in 5.4 min**.

**Mode B — schema-validation rejection** (sprite, 2026-10-23 14:35:14, instant):

```json
{"type":"tool.execution","message":"Invalid arguments for tool \"question\":\n- questions[0].question: Missing key\n- questions[1].question: Missing k…
```

Self-corrected 2 s later; the corrected retry then hit Mode A.

## Root-cause classification (backlog vocabulary a-d)

- **PRIMARY = (c) harness behavior.** Any `question` call pending ~60.0-61.0 min
  is hard-killed with no recovery or requeue. Evidence: 15/18 inline-era error
  calls machine-wide at exactly 60.x min (evidence §1.3, §3b/c); same-substance
  retry succeeded in 5.4 min (§4b) — not data-, payload-, model-, or
  agent-dependent (§5); no auto-retry ever observed (§5); the constant is not in
  our config (§1.5, §8.1). Not merely TUI rendering: the persisted part state
  (`executed:false`, `status:"error"`) shows the call is genuinely dead
  server-side; the red banner is a faithful rendering.
- **SECONDARY = (b) model tool-call shape, benign.** 3/18 errors are
  schema-validation rejections (`Missing key`), all self-corrected on immediate
  retry (§4c). No fix warranted.
- **(a) agent-definition/config NOT defective.** `opencode.json` globally
  allows the tool (`"action":"question","resource":"*","effect":"allow"`); the
  v2 `permissions` schema is an allow/deny list with no timeout knob to be
  wrong (`docs/opencode-v2.md`); no prompt disables the tool. **The mitigation
  still belongs at the agent-definition level because we own the prompts, not
  the harness.** (d) ruled out by §5.
- Sprite's "every time" is sampling bias: its orchestrator asks questions at
  the END of long autonomous turns while the user is away (11/18 asks aborted
  in the Oct 24-25 window; worst case 6 consecutive aborts in `ses_e91a69978…`).

## Fix design (agent-definition mitigation; OpenCode is third-party — visualize, don't patch)

1. **What:** one bounded, ordered, loggable clause in BOTH base orchestrator
   mirrors + the overlay grokestrator (three-file rule) — the four numbered
   rules drafted verbatim below (ask early / never leave one pending; batch
   into one call; post-pause death check; abort hard rule + dropped-gate
   treatment). Design rationale: the defect is deterministic-per-absence, so
   the defense is procedural — minimize pending windows, detect death, recover
   without a user retry round-trip.
2. **Where:** new standalone section immediately before `- **Repository Ownership:**`
   in all three mirrors — adjacent to the approval-gate/ownership material it
   extends (a dead question is treated like a dropped approval gate). NOT
   inside the MDU-28-pinned resume-gate span: it is an interaction rule, not a
   resume-gate rule, and a dedicated span test keeps concerns separate.
3. **Config: no `opencode.json` change.** Evidence found no timeout knob
   (§1.5); nothing to fix or tune there. Say-so is normative for this MDU.
4. **Scope:** orchestrators only. `inception.md` untouched — its 23 inline-era
   question calls have 0 errors (§3b; interactive loops have the user present;
   the failing pattern is orchestrator end-of-long-turn asks). Mode B
   unfixed — payload-shape guidance for a 3/18 self-healing mode is bloat.

## Prompt-clause diffs (DRAFTS — for just-code; byte-identical in all three mirrors)

Anchor lines (insert on the blank line before `- **Repository Ownership:**`):

- `prompts/orchestrator.md` — after line 77 `  - Require human approval before exceeding 3 fix-retries on the same issue.`, before line 79 `- **Repository Ownership:**`.
- `grok/agents/orchestrator.md` — same block at lines 83/85.
- `../opencode_agents/grok/agents/grokestrator.md` — after line 77 (CODER HANDOFF last paragraph `…Never edit production code yourself.`), before line 79 `- **Repository Ownership:** Commit, push…` (one-line form there).

New section text (verbatim, all three mirrors):

```text
- **QUESTION TOOL — ASK EARLY, NEVER LEAVE ONE PENDING, NEVER TRUST A DEAD ONE:**

  The harness kills any `question` call left pending about 60 minutes: the part records `{"type":"aborted","message":"Tool execution interrupted"}` with `executed:false`, the turn ends in error, and nothing re-asks. Four rules, in this order:

  1. Ask early. Pose questions at the start of a turn or before starting long unattended work — never at the end of it. Never leave a question pending while you orchestrate a long autonomous phase.
  2. Batch. Fold every approval and open question you need into one `question` call, so a single answer window covers them all.
  3. After resuming from a long pause (idle > 30 minutes, e.g. overnight): first check whether your previous question was never answered. If it died unanswered, say so explicitly and re-ask it inline in your reply.
  4. HARD RULE — if a `question` call fails with `type: "aborted"` / `Tool execution interrupted`, or the session shows the question was killed while pending: do not silently continue, and do not wait for the user to notice. Immediately restate the outstanding questions as plain text in your reply, numbered, and ask the user to answer by number. A dead question is a dropped approval gate, never user consent.
```

`scripts/lib/validate.py` `ROLE_KEYWORDS["orchestrator"]` additions (MDU-15/34
no-drift fuse; both bind case-insensitively to both base mirrors — the clause
is byte-identical in them): `("question tool",)` and `("dropped approval gate",)`.

Pin vocabulary for tests/review (lowercase, backtick-free substrings):
`never leave a question pending`, `a single answer window covers them all`,
`if it died unanswered`, `dropped approval gate, never user consent`,
`restate the outstanding questions as plain text`, `answer by number`,
`do not silently continue`, `left pending about 60 minutes`.

## Acceptance criteria + review/test/validate plan

AC (backlog-mapped):
1. This doc exists with repro path, payloads, exact error, classification, evidence (backlog AC-1). Met at merge of this doc.
2. Clause present, byte-identical, in all three mirrors; `./build.sh`, pytest, parity gates green; prompt-regression gate exit 0 (or re-baselined per protocol only after a green tree) (backlog AC-2).
3. Guidance survives the build: pins present in the generated grok + claude orchestrator pins and the tracked grok + claude grokestrator copies under `build/`, and grep-able anchor `- **QUESTION TOOL` immediately precedes `- **Repository Ownership:**` in each (backlog AC-3).
4. Run manifest `runs/mdu-35-question-tool/manifest.json` created and `run_ledger.py validate` passes (backlog AC-4).

Mandated review checks (apply-now 20261021-11 — the clause is procedural; the
reviewer must trace the text, not just read it):
- Trace A (abort → recovery, in order): given a synthetic abort
  (`Tool execution interrupted`), the text alone must force (a) do not silently
  continue → (b) do not wait for the user → (c) restate inline, numbered →
  (d) classify as dropped approval gate; each locate-able, in that order.
- Trace B (post-pause): resuming after idle > 30 min with an unanswered
  question must force an explicit "it died" statement + inline re-ask.
- Trace C (ordering): rules 1-4 appear in ascending order; the hard rule is 4.
- Trace D (no interference): insertion adds text only — Human Approval Gates,
  Repository Ownership, resume gate, secret/prompt-regression gates unweakened.
- Trace E (identity): the section span is byte-identical across the three
  source mirrors.

Test plan — new `tests/test_mdu_35_question_tool.py` (house style: path
constants, lowercase pins, conditional grokestrator `skipif`):
- T1 anchor+placement: `- **QUESTION TOOL` present in all three mirrors; its
  index < index of `- **Repository Ownership:**` in each.
- T2 pins: all 8 pin substrings present in all three mirrors.
- T3 span byte-identity: extracted section (anchor → Repository Ownership
  bullet) byte-identical across the three source mirrors.
- T4 ordering: `never leave a question pending` < `a single answer window
  covers them all` < `if it died unanswered` < `dropped approval gate, never
  user consent`, per mirror.
- T5 validator fuse: the 2 new `ROLE_KEYWORDS["orchestrator"]` tuples present
  AND each binds to both base mirrors (MDU-15 binding pattern).
- T6 deployed copies: pins present in base `build/` copies and overlay
  `build/` copies (all `skipif`-absent; base `build/` is transient — devops
  greps it post-build, overlay `build/` is tracked and testable).
- T7 existing suite green: `timeout 120 python3 -m pytest tests/ -q`;
  `timeout 300 ./build.sh`; `timeout 60 python3 scripts/lib/prompt_regression.py
  gate` (mandatory — prompts/ and grok/agents/ change).

Routing (apply-now 20261021-9 — who executes / who grades): just-code lands
the three-mirror clause + 2 `validate.py` fuse lines (file write); test-agent
writes `tests/test_mdu_35_question_tool.py` and runs targeted
`timeout 120` pytest; code-reviewer runs the trace checks read-only;
**devops executes all command-bearing phases** — base `./build.sh`, full
pytest, prompt-regression gate, run-ledger validate, then overlay `./build.sh`
and build-copy greps (all `timeout`-wrapped); **qa grades** from artifacts +
transcript. Two commits/pushes (base, then overlay) per the cross-repo rule;
overlay regenerated `build/` committed only per user policy.

## Risks

1. Prompt-regression gate red on an intentional addition → revert/fix or, only
   after a fully green tree, re-baseline per the protocol (never to force green).
2. The preamble states a harness constant ("about 60 minutes") that upstream
   may change → wording is approximate and the rules stay valid hygiene even
   if the timeout is fixed; no urgent rewording.
3. Wrong-mirror edit: the grokestrator source is overlay-root
   `grok/agents/grokestrator.md` — not `overlays/grok/agents/` (nonexistent)
   and not a dead-copy case.
4. Mode B left unfixed (3/18, self-healing) — recorded as a decision, not an
   oversight. Pins avoid inline-code spans (backtick trap) per MDU-34 risk 6.

## Decisions made (recorded rationale)

1. Standalone section before Repository Ownership, not inside the MDU-28 gate
   span — interaction rule ≠ resume-gate rule; dedicated span test.
2. Byte-identical across all three mirrors (CODER HANDOFF precedent).
3. Four ordered rules + one preamble line — bounded; ordered for traceability.
4. No config change (no knob exists — evidence §1.5).
5. Upstream report stays a text appendix (Repository Ownership rule: explicit
   per-action user approval before any file).
6. Inception and non-orchestrator prompts untouched (census: 0 errors there).

## Appendix A — Upstream-issue DRAFT (text only — DO NOT FILE without explicit per-action user approval)

**Title:** Pending `question` tool call hard-killed at ~60 min with no re-prompt: turn ends `finish:"error"`, session idle `interrupted`, user must manually retry

**Minimal repro:** (1) OpenCode v2.0.31 (Linux): in a long-running turn, emit a `question` tool call near the end of the turn; (2) leave it unanswered > 60 min (session idle); (3) observe: tool part → `{"type":"aborted","message":"Tool execution interrupted"}`, `executed:false`, `state.status:"error"`; assistant message `finish:"error"` + `"Step interrupted"`; `idle` row `outcome:"interrupted"` at the same epoch second; TUI shows red "Asked N questions" with no visible prompt; no forward progress until the user manually messages.

**Observed:** 15/18 inline-era error question calls across three projects all at 60.0-61.0 min pending; identical abort also fires on manual interrupt (0.4 min) — the 60-min timer is its most frequent trigger. Same-substance retry succeeded in 5.4 min when the user was present, so it is not payload-, model-, or agent-dependent. No auto-retry or requeue ever observed. Masked evidence: `runs/mdu-35-question-tool/evidence.md` §1.3, §3c, §4a, §4b, §4e, §5 (session IDs non-secret per its masking note).

**Expected:** a pending question out-lives the 60-min window, OR the harness re-prompts/requeues on abort so the question still reaches the user instead of dying silently.

**Version:** v2.0.31 on disk at report time; failures span 2026-10-15→25; historical versions at failure times unrecorded (DB stores no version field).

**DRAFT — do not file without user approval.** Filing also requires the repo named by the user and per-action approval (base orchestrator Repository Ownership rule); never file as a default MDU step.
