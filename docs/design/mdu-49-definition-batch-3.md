# MDU-49 · Definition batch 3 — codify the six queued orchestrator/coder/introspector clauses

User-approved definition batch (2026-11-01, MDU-47 style): land the six still-unapplied
definition-change clauses from `agent-improvements.md` — 20261027-3 (finalize-before-QA),
20261030-3 (grep-driven sweeps), 20261021-9 (design-time routing pre-check), 20261031-1
(bounded design allowance), 20261031-2 (edit-result display integrity), 20261101-1
(introspector unapplied-claim verification) — into the live agent definitions across the
three orchestrator mirrors, the base just-code family, and the two introspector bodies.
Base repo first; the overlay build inherits everything except `grokestrator`, which is
patched explicitly. **No registry (`opencode.json`) change ships in this MDU** — prompt
files, tests, and books only.

## 0. Surveyed files (reads only; grep-only beyond this list)

Base repo: `agent-improvements.md` (entries 20261021-9 L282-295, 20261027-3 L382-393,
20261030-3 L460-468, 20261031-1 L483-487, 20261031-2 L489-493, 20261101-1 L502-505, plus
the 20261014-5/20261021-8 cross-evidence notes); `docs/design/mdu-47-definition-guards-batch.md`
(batch + pin pattern); `tests/test_mdu_47_definition_batch.py` (pin pattern);
`prompts/orchestrator.md` and `grok/agents/orchestrator.md` (full); `prompts/just-code.md`
+ `grok/agents/just-code.md`, `just-code-mid.md`, `just-code-pro.md` (constraint blocks);
`prompts/introspector.md` + `grok/agents/introspector.md` (full);
`skills/session-introspect/SKILL.md` and `skills/mdu-lifecycle/SKILL.md` (scope rulings);
`evals/golden/cases.json` (7 cases); `docs/brief-checklist.md`; `opencode.json`
(introspector block L2656-2740); `tests/README.md` (row pattern); `FEATURE_BACKLOG.md`
(queue section + MDU-47 entry, the shape to copy); `tests/test_mdu_31_repo_ownership.py`
L168-197 (gap-pin hazard, cleared); `tests/test_mdu_46_apply_now_tooling.py` L225-254
(checklist pins, cleared).

Overlay repo: `grok/agents/grokestrator.md` (full); `overlays/manifest.json` (full).

Grep-only beyond the list (no full reads): `build/opencode.json` (`{file:./prompts/…}`
references only — no embedded prompt bodies); `scripts/lib/probe_models.py`
(`config_sha256` hashes the config file, not prompts); `EVERY manifest edit` across the
base repo (5 hits, **all** in `agent-improvements.md`, zero in any prompt body);
`Always verify your work` across the grok coder family; existing pins mentioning
orchestrator/ grokestrator/ introspector/ just-code across both `tests/` trees; overlay root
`prompts/` glob (exactly `grok-plan.md` — no dead same-name copies of any target);
overlay `tests/README.md` (absent). `prompts/qa.md` was NOT read — no MDU-49 clause
targets QA; the overlay-fold precedent is already captured by the MDU-47 design doc and
`overlays/prompts/qa.md`'s existence.

Line numbers below are survey-time references; **anchor text is authoritative** — the
implementer greps each anchor before editing (20261030-3's own discipline applied to this
batch: the file table below is the census, not a hand-waved list).

## 1. Verified facts that shape the design

1. **The three orchestrator mirrors all carry the same ledger-block tail** — a
   `Finalize order:` line ending with `→ commit the manifest with the code`
   (`prompts/orchestrator.md` L220, `grok/agents/orchestrator.md` L216,
   `grokestrator.md` L161) — a uniform anchor for D1. The base mirrors also share the
   loop-steps list and the `- Decide which agents to invoke…` line; `grokestrator` is
   condensed (single-line loop, no loop-steps list, no Human Approval Gates block).
2. **No overlay fold is needed.** `overlays/prompts/` = {mdu-code, thought-leadership-coach,
   qa}; `overlays/grok/agents/` = {mdu-code, grok-mdu-code, thought-leadership-coach};
   `overlays/manifest.json` snippets touch only mdu-code/grok-mdu-code and
   devops/grok-devops; overlay root `prompts/` holds only `grok-plan.md`. **None of the
   MDU-49 targets is shadowed.** The only overlay source edit is `grokestrator.md`
   itself (a live personal agent, not an override; it never inherits base clauses).
3. **D3 is not duplicated anywhere.** Full reads of all three orchestrator bodies show no
   allowlist/routing text; the word "allowlist" does not appear in any of them. The
   checklist row (docs/brief-checklist.md L18, `[20261021-9]`) is a DOC, not a
   definition. Same for D1: the ledger lifecycle line says "before the commit phase,
   finalize every remaining field and validate" — that is a *later, looser* trigger; the
   QA-dispatch timing, the pass-exact-path requirement, and the post-QA only-flip rule
   exist in no body.
4. **D5's entry text references a rule that does not exist in any prompt body.** Grep
   `EVERY manifest edit` across the base repo: 5 hits, all in `agent-improvements.md`
   (the 20261014-5/20261031-2 entries themselves). Verbatim insertion would ship a
   dangling reference — see §6 for the narrowing.
5. **The introspector cannot reliably run git or shell-grep.** Its `opencode.json`
   permissions (L2667-2740): `shell` deny `*`, allow only `python3 *`, `python *`,
   `ls*`, `head*`, `tail*`, `wc*`, `sort*`, `timeout *`, plus substitution/redirect
   walls. No bare `git*`/`grep*` allow. The mdu-46/mdu-48 notes record the
   `timeout`-wrapped form itself being denied in live QA sessions (twice). File tools
   (read/grep) are the reliable floor — see §7 for the D6 executability reword.
6. **Golden cases cannot collide with any insertion.** All 7 cases target
   `prompts/orchestrator.md`, `grok/agents/orchestrator.md`, or `prompts/just-code.md`
   with ordered marker traces; no MDU-49 clause text contains any traced marker
   contiguously (checked per case — e.g. D1 says "run scripts/lib/run_ledger.py validate
   and require exit 0", which does not contain the marker
   `run_ledger.py validate runs/<mdu-id>/manifest.json`). Baseline records case
   pass/fail only, no file hashes (MDU-47 fact).
7. **Existing pins stay green (additive only).** `test_mdu_31`'s gap pin measures the
   text between the last Human Approval Gates bullet and the Repository Ownership anchor
   (it must contain only the QUESTION TOOL block) — D5 inserts BEFORE the Human Approval
   Gates bullet, outside the measured gap. `test_mdu_46` pins checklist role-heading
   presence only (no row counts). `test_mdu_04/11/12/15/23/28/31/34/35/40/41/47` pin
   content that MDU-49 only appends around, never reorders or edits.
8. **No probe refresh is required.** `build/opencode.json` references prompts via
   `{file:./prompts/…}` and embeds no prompt bodies, so prompt-file edits leave it
   byte-identical and `config_sha256` unchanged. The gate must still be RUN and verified
   green in both repos (verify, do not assume); if it reds with no registry change, STOP
   and investigate — do not auto-refresh.
9. The introspector definition is base-only: `prompts/introspector.md` +
   `grok/agents/introspector.md` (near-identical; grok mirror offset +6 lines by
   frontmatter). No overlay override, no overlay introspector agent.
   `skills/session-introspect/SKILL.md` is a run-guide (log locations, signal kinds) —
   it carries no note-writing discipline; D6 belongs in the prompt bodies only.
10. MDU-47 precedent bank: batch commit 8c1b41a base / c2f2416 overlay (brief-attested,
    not re-verified this session); clause bytes identical across bodies with local
    anchors differing per mirror; per-clause pin pairs as (id, text, files) constants in
    the test; reword deviations are recorded with grep evidence (the 20261021-8 reword).
11. Suite sizes at design time: base ~671, overlay ~197 (brief-attested; re-verify at
    test time). Prompt-change protocol and gate semantics per `evals/README.md`
    ("Prompt change protocol", exit 0/1/2 as quoted in the MDU-47 design doc §6).

## 2. D1 — 20261027-3 finalize-before-QA (APPROVED verbatim)

Clause text (byte-identical in all three mirrors, inserted as a plain ledger sub-bullet
with no label — the clause's own lead is the lead):

> Before dispatching QA, ensure runs/<mdu-id>/manifest.json has all completed phases, the verification block, a summary and completed_at; run scripts/lib/run_ledger.py validate and require exit 0; pass the exact manifest path to QA and require QA to validate it. After QA, only flip qa_grade (and re-run the validator).

| File | Anchor neighborhood |
| --- | --- |
| `prompts/orchestrator.md` | run-ledger block; new 2-space sub-bullet immediately BEFORE the `Finalize order:` line (survey L220) |
| `grok/agents/orchestrator.md` | same block, before `Finalize order:` (survey L216) |
| `grok/agents/grokestrator.md` (overlay) | same block, before `Finalize order:` (survey L161) |

Insertion-order rationale (20261021-11 trace, per variant): the agent dispatching QA at
loop step 6 reads the ledger block top-down: lifecycle ("append one phases[] entry" …
"before the commit phase, finalize") → fields → rules → example → **D1: the when —
finalize + validate + pass the exact path BEFORE QA dispatch, and after QA only
qa_grade flips** → `Finalize order:` (the how — commit-phase mechanics, now a re-check).
When-before-how: placing D1 after `Finalize order:` would leave the commit-phase
trigger as the primary reading, the exact lapse mdu-40/41/44 recorded. The lifecycle
line's "before the commit phase" stays unedited — D1 is the stricter, earlier trigger
and the lifecycle line remains the backstop; editing it would touch pinned-adjacent text
for no behavioral gain (additive-only discipline).

## 3. D2 — 20261030-3 grep-driven sweeps (APPROVED verbatim)

Clause text (byte-identical in all three mirrors, as a flat bullet with bold lead
`- **Wording/term sweeps:**`):

> For any wording/term sweep, do not hand-list target files: grep the old term across BOTH repos (source and built/installed trees), attach the full file:line hit list to the implement brief, and require the pin test to fail on any remaining live hit rather than pinning a file count. Name dead/ignored copies explicitly as excluded, with the reason.

Placement: inside the new delegation-discipline cluster (with D4 and D3, §8) — in the
base mirrors, three new flat bullets after loop step 8's sub-bullets and before the
`**MODEL SELECTION` header; in `grokestrator`, after the PROMPT REGRESSION GATE
sub-bullet and before `- **MODEL SELECTION`. Cluster order is D4 → D3 → D2.

Trace: an orchestrator writing an implement brief for a sweep MDU (loop step 1→2) has
just passed the loop-steps list; the cluster's third bullet is the sweep rule, followed
immediately by MODEL SELECTION (the tier choice it makes anyway). The rule fires at
brief-construction time, before any child is spawned — which is exactly when the
enumeration drift it prevents (mdu-43's two fix cycles) would otherwise be seeded.

## 4. D3 — 20261021-9 design-time routing pre-check (APPROVED verbatim)

Clause text (byte-identical in all three mirrors, flat bullet with bold lead
`- **Phase-routing pre-check:**`):

> Before delegating a phase, check the target agent's shell allowlist in opencode.json against the commands that phase requires. A phase that must execute an arbitrary script or an unrestricted command routes to devops or runs in the orchestrator session; QA and other inspection agents receive the produced artifacts to grade. Do not assign a phase to an agent whose allowlist cannot run its commands — verify the permission profile at design time, not mid-run.

Placement: cluster position 2 (between D4 and D2), same neighborhoods as §3.

Drop/narrow ruling: **not a duplicate** — grep + full-read evidence (fact 3): no
allowlist-check text exists in any orchestrator body; the only current carrier is the
brief-checklist DOC row. "opencode.json" is kept verbatim: it is the canonical allowlist
surface for every OpenCode-registered agent all three orchestrators dispatch (the grok
mirrors and grokestrator already reference base scripts and OpenCode-registered agents
the same way).

Trace: the pre-delegation check is read before the MODEL SELECTION table (feasibility
before economy) and before the `- Decide which agents to invoke…` line (base mirrors,
survey L194/L191) — an agent about to delegate encounters the allowlist check ahead of
the tier guidance it would otherwise consult first. mdu-15/30/41 and the mdu-48 S1 root
cause (a read-only qa agent asked to write files) are all this clause firing late; the
placement makes it fire at decision time.

## 5. D4 — 20261031-1 bounded in-conversation design allowance (APPROVED verbatim; scope = mirrors only)

Clause text (byte-identical in all three mirrors, flat bullet with bold lead
`- **Design-phase delegation:**`):

> Design may be conducted in-conversation by the orchestrator INSTEAD of dispatching the architect only when (a) the orchestrator has already gathered the design inputs live in this session (evidence, probes, config reads), (b) the MDU is diagnosis/recommendation rather than new-code-shaping, and (c) the deviation is recorded in the manifest design note with its justification. Any other in-conversation design is a delegation-loop violation (20261014-1 class).

Placement: cluster position 1 (first bullet of the cluster, immediately after the loop
steps / gate sub-bullets, before D3 and D2). The `(20261014-1 class)` tag is kept
verbatim as lineage metadata (grep-able, harmless to an executing agent).

**Scope decision: the three orchestrator mirrors ONLY — not
`skills/mdu-lifecycle/SKILL.md`.** Rationale: (a) the allowance governs a delegation
decision the orchestrator makes mid-loop, and the operative text for that decision is
the orchestrator's own prompt body (all four orchestrator surfaces are live: base prompt
→ OpenCode + generated Claude; base grok mirror → Grok generic; grokestrator → Grok
personal); (b) the mdu-lifecycle skill is an on-demand tier/checklist reference whose
audience is [just-code, qa, orchestrator] — MDU-47's precedent puts operative clauses in
prompt bodies and one-line pointers in docs; (c) a fifth duplicated surface is
maintenance cost without a live gap. Flagged as an open question (§17) if the user wants
belt-and-suspenders in the skill too.

Trace: the exception is read immediately after the loop-steps list whose step 1
("Design (via architect…") it qualifies — an orchestrator deciding whether to dispatch
an architect encounters the three conditions at the decision point, before the routing
check (D3) that then validates whichever delegation it chooses.

## 6. D5 — 20261031-2 edit-result display integrity (NARROWED; two shapes)

Sentence 3 of the entry text references "The standing 'validator after EVERY manifest
edit' rule" — grep evidence (fact 4): that rule exists in **zero** prompt bodies (all 5
hits are the agent-improvements.md entries themselves). Ruling (MDU-47 20261021-8-reword
precedent): sentences 1-2 ship byte-identical everywhere; sentence 3 is corrected in the
orchestrator shape and dropped from the coder shape. After D1 lands in the same bodies
in this same MDU, "the run-ledger validation discipline" is a real referent.

**Coder shape** (sentences 1-2, byte-identical to the entry; plain bullet, no label) —
`prompts/just-code.md`, `grok/agents/just-code.md`, `grok/agents/just-code-mid.md`,
`grok/agents/just-code-pro.md`, inserted immediately after
`- Always verify your work: build, lint, test.` and before `- **NEVER commit secrets**`
(uniform anchor, grep-verified in all four files; survey L17/L23/L24/L22):

> An edit/write tool result that looks corrupted or unexpected (oldString mismatch, phantom content in the echoed result, truncated output) is UNTRUSTED until verified: grep or read the target file on disk and confirm the actual state before quoting the result anywhere — manifests, briefs, verdicts. Never propagate edit-result display text as truth.

**Orchestrator shape** (coder shape + corrected sentence 3; guardrail bullet with bold
label `- **DISPLAY INTEGRITY:**`) — the three orchestrator mirrors, inserted immediately
after the CODER HANDOFF block and before `- **Human Approval Gates:**` (base mirrors;
survey L95/L101 → L97/L103) or before `- **QUESTION TOOL` (`grokestrator`, which has no
Human Approval Gates block; survey L101 → L103):

> An edit/write tool result that looks corrupted or unexpected (oldString mismatch, phantom content in the echoed result, truncated output) is UNTRUSTED until verified: grep or read the target file on disk and confirm the actual state before quoting the result anywhere — manifests, briefs, verdicts. Never propagate edit-result display text as truth. The run-ledger validation discipline covers the manifest side; this covers the general case.

The coder shape is a strict substring of the orchestrator shape (sentences 1-2 are
byte-identical and concatenated identically) — one pin can cover both.

Ordering rationale: in the guardrails sequence the rule lands between child-management
(CODER HANDOFF) and approval gates — an agent that just received a suspicious edit
result scans guardrails top-down and hits DISPLAY INTEGRITY in the trust/verification
neighborhood, next to the read-discipline bullet it already follows. In the coder
bodies it extends "Always verify your work" from the work to the tool-reported state —
the verification neighborhood, exactly where a coder looking for "did my edit land?"
searches. Placement before the `NEVER commit secrets` bullet keeps the golden case
`just-code-constraints-order` markers (`NEVER edit test files` → `NEVER commit secrets`
→ `never print full secrets`) in their pinned order — D5 contains none of them, and it
inserts before the second marker without moving it.

**Scope ruling for the overlay personal coder family:** the overlay root
`grok-just-code`, `grok-just-code-mid`, `grok-just-code-pro` are NOT edited (consistent
with the standing MDU-47 follow-up ruling on overlay personal variants). Record the
extension as the MDU-49 backlog follow-up. The BASE coder bodies flow into the overlay
build automatically (OpenCode + Claude deployments); only the Grok personal mirrors lag.

## 7. D6 — 20261101-1 introspector unapplied-claim verification (REWORDED for executability)

Entry text mandates "grep the target file(s) at HEAD … and cite the commit hash" — but
the introspector's permission profile (fact 5) denies bare shell with only narrow
allows (`python3 *`, `ls*`, `head*`, `tail*`, `wc*`, `sort*`, `timeout *`), and the
mdu-46/mdu-48 evidence records the `timeout`-wrapped form itself being denied in live
sessions. Verbatim insertion would assign the introspector work its allowlist cannot
reliably run — the exact 20261021-9/20261021-8 failure class this batch is codifying
against. Ruling: reword with a degradation ladder (file tools are the floor;
timeout-wrapped git when shell is available; a denial is recorded, never skipped), keep
the entry's closing sentences verbatim:

> Before recording that a definition change is unapplied (or letting that claim drive a closure decision), grep the target file(s) for the clause text — file tools on the working tree are the floor; when shell is available, check HEAD and cite the commit hash that added or last changed it (a `timeout`-wrapped `git log`, e.g. `timeout 30 git log --oneline -- <file>`, works); if shell is denied, record the on-disk grep and the denial instead of skipping the check. A stale claim is corrected with evidence, not repeated; if the clause is present, close or re-scope the suggestion instead of noting 'still unapplied'.

| File | Anchor neighborhood |
| --- | --- |
| `prompts/introspector.md` | loop mode; new bullet immediately after the `- Update agent-improvements.md …` bullet (survey L21), before `- Also write runs/<mdu-id>/introspection.md` |
| `grok/agents/introspector.md` | same position (survey L27) |

Scope: loop-mode bullet only — that is where unapplied claims get written; review mode
proposes diffs against current files by construction. `skills/session-introspect/SKILL.md`
is not edited (fact 9: it is a run-guide, not the note-writing discipline).

Trace: the clause sits exactly between the introspector's read of prior notes and its
write of new ones — the claim is checked at the moment of recording. The working-tree
floor also makes MDU-49's own introspection (pre-commit, clauses in the tree, not yet at
HEAD) both executable and correct: the grep finds the just-landed clauses and the
suggestions close instead of accumulating false "still unapplied" notes.

## 8. Delegation-discipline cluster — consolidated execution-order walkthrough

New flat bullets (identical bytes, order D4 → D3 → D2) in each mirror:

| Mirror | Insertion point |
| --- | --- |
| `prompts/orchestrator.md` | after loop step 8's sub-bullets (survey L135), before `**MODEL SELECTION` (L137) |
| `grok/agents/orchestrator.md` | after loop step 8 (survey L135), before `**MODEL SELECTION` (L137) |
| `grok/agents/grokestrator.md` | after the PROMPT REGRESSION GATE sub-bullet (survey L118), before `- **MODEL SELECTION` (L119) |

Per-variant procedure trace (20261021-11, one line each):

- **Base OpenCode/Claude (`prompts/orchestrator.md`)**: loop steps → D4 gates the
  step-1 design delegation (exception conditions a/b/c) → D3 gates every delegation
  (allowlist vs the phase's commands; route execution to devops/self, artifacts to QA)
  → D2 gates step-1→2 briefs for sweep MDUs → MODEL SELECTION (tier choice) → … →
  step 6: D1 finalizes/validates the manifest before QA dispatch → step 8: gates.
  Mid-loop, a suspicious edit result → guardrails → DISPLAY INTEGRITY (D5) → verify on
  disk. No pinned marker is reordered (fact 6/7).
- **Base Grok mirror (`grok/agents/orchestrator.md`)**: identical body structure and
  trace; MODEL SELECTION lists grok models; D3's `opencode.json` referent is the
  canonical allowlist surface for the OpenCode-registered agents it also dispatches.
- **Overlay `grokestrator.md`**: condensed loop line + gates → the same cluster in the
  same order → mixed Go/grok MODEL SELECTION → ledger (D1 before `Finalize order:`) →
  memory → hard constraints; D5 sits in the guardrails region after CODER HANDOFF.

Cluster order rationale: D4 (whether to delegate design at all) → D3 (whether the
delegatee can run the phase) → D2 (how the implement brief for a sweep is built) reads
as decision → feasibility → brief construction, matching the chronological order in
which the three fire.

## 9. Golden-case audit (per-case verdict)

| Case id | Target | Insertion touches it? | Marker in any clause? | Verdict |
| --- | --- | --- | --- | --- |
| orchestrator-commit-step-secret-gate-order | prompts/orchestrator.md | yes (D1/D4/D3/D2/D5 elsewhere in file) | no | safe |
| orchestrator-run-ledger-finalize-order | prompts/orchestrator.md | yes (D1 adjacent) | no (D1's validate phrase ≠ marker) | safe |
| orchestrator-responsibilities-loop-order | prompts/orchestrator.md | yes (cluster after loop) | no (D4 lacks "Design (via architect") | safe |
| orchestrator-mirror-secret-gate-order | grok/agents/orchestrator.md | yes | no | safe |
| just-code-constraints-order | prompts/just-code.md | yes (D5 before 2nd marker) | no | safe |
| orchestrator-prompt-regression-gate-clause | prompts/orchestrator.md | yes | no | safe |
| orchestrator-mirror-prompt-regression-gate-clause | grok/agents/orchestrator.md | yes | no | safe |

No clause contains any traced marker; no insertion moves a marker ahead of a predecessor.
**No cases.json edit, no baseline refresh; the gate is expected to exit 0 on the
unchanged baseline — the implementer still runs the snapshot/diff protocol and the gate,
and treats any red as a reject-and-fix (never a baseline update).**

## 10. Overlay exploitation (what must change in the overlay repo to survive the build)

- **Folds needed: NONE.** No MDU-49 target has an overlay full-file override or
  manifest snippet (fact 2). Base prompt edits flow into the overlay build
  automatically (build precedence: base build copied, snippets appended only to the
  four named agents, no same-name replacement for any target).
- **Explicit patch required: `grok/agents/grokestrator.md`** (overlay source) carries
  D1, D2, D3, D4 (cluster + ledger, §8/§2) and D5-orchestrator-shape (§6). It never
  inherits base clauses — skipping it would leave the user's daily Grok orchestrator
  without five of the six clauses.
- **Out of scope, recorded as backlog follow-up:** overlay root personal coder family
  (`grok-just-code`, `grok-just-code-mid`, `grok-just-code-pro`) — extends the standing
  MDU-47 personal-variant follow-up.
- Overlay repo also gains: `tests/test_mdu_49_grokestrator_clauses.py` and the
  regenerated tracked `build/` tree. Committed as the separate overlay commit.

## 11. Pin tests

### Base: `tests/test_mdu_49_definition_batch.py` (new; hermetic, tmp/no git state/no network)

1. **Full-clause constants, not fragments.** Seven constants — `D1_20261027_3`,
   `D2_20261030_3`, `D3_20261021_9`, `D4_20261031_1`, `D5_ORCH_20261031_2`,
   `D5_CODER_20261031_2`, `D6_20261101_1` — hold the §2-§7 blockquote texts verbatim.
   Presence pins assert the full constant `in` each target file's text (21 file-level
   assertions: D1×3 mirrors, D2×3, D3×3, D4×3, D5_ORCH×3, D5_CODER×4 coder files,
   D6×2 introspector files). This makes the test file the byte-identity authority
   (MDU-45 non-vacuity lesson + mdu-47 round-1 tautological-pin MAJOR: a pin that
   cannot fail is not a pin).
2. **Doc-consistency pins.** Each constant must also appear in
   `docs/design/mdu-49-definition-batch-3.md` — doc and test cannot drift. These pins
   ALWAYS read the real repo doc (not the mutation override, below).
3. **Mirror parity.** D5_CODER is a substring of D5_ORCH — one pin asserts D5_CODER in
   all 7 D5 files; a second asserts the full D5_ORCH (sentence 3 included) only in the
   3 orchestrator mirrors. Grokestrator pins are overlay-gated (`needs_overlay`,
   mdu-35 convention).
4. **Ordering pins** (find()-position asserts, per the mdu-47 pattern):
   D1 precedes `Finalize order:` in each mirror; cluster integrity — D4 < D3 < D2 and
   D2 precedes `**MODEL SELECTION` in each mirror; D5_ORCH follows `CODER HANDOFF` and
   precedes `**Human Approval Gates:**` (base mirrors) / `**QUESTION TOOL`
   (grokestrator); D5_CODER follows `Always verify your work: build, lint, test.` and
   precedes `NEVER commit secrets` in each coder file; D6 follows
   `Update \`agent-improvements.md\`` in both introspector files.
5. **Checklist pins.** The three new rows (§14) each present with their `[id]` on the
   same line (mdu-46 pin-pair pattern). Existing `[20261027-3]` / `[20261021-9]` rows
   remain (unasserted beyond mdu-46's heading pins — additive only).
6. **Mutation override (REQUIRED, not optional).** The module resolves the clause-file
   root through a helper honoring the `MDU49_TEST_ROOT` env var (default: the repo
   root); checklist and doc-consistency pins ignore the override. This is what makes
   AC-6 executable without touching the working tree.

### Overlay: `tests/test_mdu_49_grokestrator_clauses.py` (new)

1. `grok/agents/grokestrator.md` source carries all five orchestrator clauses (D1, D2,
   D3, D4, D5_ORCH — full constants duplicated in this file, same byte-identity
   discipline).
2. Build inheritance (tracked `build/` tree, mdu-44 precedent of asserting build
   content): `build/prompts/orchestrator.md` carries D1-D5; `build/prompts/just-code.md`
   carries D5_CODER; `build/prompts/introspector.md` carries D6. (Built grok/claude
   copies are devops cmp targets, not test pins — implementer confirms exact built paths
   with a glob at implement time before writing pin #2.)

### Mutation-check protocol (test phase; /tmp copies ONLY — 20261017-1 guard)

The working tree holds uncommitted MDU edits; NEVER `git checkout`/`reset`/`stash` in
it. For each of the seven constants: copy `prompts/` and `grok/agents/` to
`/tmp/opencode/mdu-49/mutation/`, strip that one clause from the copy, then from the
base repo run
`MDU49_TEST_ROOT=/tmp/opencode/mdu-49/mutation timeout 120 python3 -m pytest tests/test_mdu_49_definition_batch.py -q`
and require: the stripped clause's presence + ordering pins FAIL with named failures,
every other pin (incl. doc-consistency and checklist) stays green. Re-copy between
rounds. Record the 7×FAIL matrix in the test phase note. (Precedent:
`test_mdu_41_fallback_ladder.py` already copies files to tmp for its mutation checks.)

## 12. Prompt-change protocol (verbatim, mdu-49 tmp paths)

Snapshot → edit → snapshot → diff, from the base repo root, for every edit under
`prompts/` or `grok/agents/` (overlay `grokestrator` edit: same commands from the
overlay root, which carries the script via its wrapper):

```sh
timeout 120 python3 scripts/lib/prompt_regression.py snapshot --out /tmp/opencode/mdu-49/before.json
# ... edit ...
timeout 120 python3 scripts/lib/prompt_regression.py snapshot --out /tmp/opencode/mdu-49/after.json
timeout 120 python3 scripts/lib/prompt_regression.py diff \
  --before /tmp/opencode/mdu-49/before.json \
  --after  /tmp/opencode/mdu-49/after.json
```

Exit semantics per `evals/README.md`: `0` clean; `1` ≥1 golden case regressed — reject
the edit, fix the hunk, repeat, never weaken the case; `2` operational — stop and
investigate. No case change is expected (§9); `baseline --update` must NOT run.

## 13. Deploy plan (devops)

1. Base: `timeout 300 python3 -m pytest tests/ -q` green → `./build.sh` twice
   (idempotent, byte-stable) → `timeout 300 python3 scripts/lib/probe_models.py --gate`
   — **expected green WITHOUT `--refresh`** (fact 8: no registry change; the config
   hash is unchanged). If it reds, STOP and investigate; do not auto-refresh to force
   green.
2. Overlay: `./build.sh` → overlay pytest green → overlay probe gate green (same
   no-refresh expectation).
3. `./deploy.sh` dry-run clean, then `./deploy.sh --force` (combined overlay build to
   all CLIs present).
4. Installed == build byte checks (`cmp`) for every edited prompt on all three CLIs —
   OpenCode `~/.config/opencode/prompts/`, Grok `~/.grok/agents/`, Claude
   `~/.claude/agents/` (generated copies included) — covering the 8 base prompt/grok
   bodies, `grokestrator`, and the 2 introspector bodies.
5. Commits: base first (commit-time gates: prompt-regression gate exit 0 + secret-scan
   gate exit 0), then overlay (prompt-regression gate from the overlay root +
   secret-scrub checklist per the fallback — the overlay has no scanner script).
   Two commits, two pushes, repos never mixed.

## 14. Books (all in the same base commit; overlay files in the overlay commit)

- `docs/brief-checklist.md` — three new one-line rows (id on the same line):
  - `## Every brief`, after the `[20261027-3]` row:
    `- For wording/term sweeps, grep the old term across BOTH repos (source and built/installed trees), attach the file:line hit list to the implement brief, pin zero live hits rather than a file count, and name excluded dead copies with the reason. [20261030-3]`
  - `## Every brief`, after that:
    `- If any edit/write tool result looks corrupted or unexpected, verify the file on disk (grep/read) before quoting it in a brief, manifest, or verdict. [20261031-2]`
  - `## introspector`, appended:
    `- Before recording a definition change unapplied, grep the target file(s) for the clause text and cite the commit hash when git is available; correct or close stale claims with evidence. [20261101-1]`
  - Existing `[20261027-3]` and `[20261021-9]` rows are NOT edited or deleted — the
    checklist stays the dispatch-time fallback (defense-in-depth) now that the
    definitions carry the clauses. No row for D4 (orchestrator self-discipline, not
    brief content — ruling recorded here).
- `tests/README.md`: new row for `test_mdu_49_definition_batch.py` (clause pins, doc
  consistency, ordering, checklist pins, mutation override) — following the mdu-47 row
  format. The overlay test file has no overlay tests README; record it in the backlog
  entry instead.
- `FEATURE_BACKLOG.md`: new `### MDU-49` entry in the Queue section (after the MDU-48
  entry), field set copied from the MDU-47 entry (Why / Description / Acceptance
  criteria / Suggested agents / Dependencies / Follow-up / Status filled at commit).
  Follow-up line names the overlay personal coder family as the parity extension.

## 15. Acceptance criteria

1. **AC-1 suites:** base suite green incl. `tests/test_mdu_49_definition_batch.py`;
   overlay suite green incl. `tests/test_mdu_49_grokestrator_clauses.py`; both builds
   idempotent; all pre-existing pins (mdu-04/11/12/15/23/28/31/34/35/40/41/44/45/46/47)
   unaffected — additive only.
2. **AC-2 byte-identity:** all 21 clause insertions byte-match this doc's §2-§7
   blockquotes (the test's full-clause constants are the authority; doc-consistency
   pins keep doc == test; snapshot/diff evidence attached to the review and validate
   briefs).
3. **AC-3 golden + secret gates:** prompt-regression gate exit 0 on both commits with
   the unchanged baseline (7/7 cases, no cases.json/baseline.json edit); secret gate
   exit 0 on the base commit, secret-scrub checklist on the overlay commit.
4. **AC-4 probe gate:** green in both repos WITHOUT `--refresh` (no registry change; if
   red, stopped and investigated — the run record shows the verification, not an
   assumption).
5. **AC-5 ordering:** every §11.4 ordering pin green (D1 before `Finalize order:`;
   D4→D3→D2 cluster before MODEL SELECTION; D5 in its guardrail/coder neighborhoods;
   D6 after the update bullet).
6. **AC-6 mutation:** the 7×FAIL matrix from /tmp copies recorded in the test phase
   note (each stripped clause reds its pins; doc/checklist pins stay green); zero git
   state commands against the working tree (20261017-1).
7. **AC-7 deployed == build:** `cmp` byte-identical for every edited prompt on all
   three CLIs, including generated Claude copies and `grokestrator`.
8. **AC-8 books:** the 3 checklist rows, tests/README row, and FEATURE_BACKLOG MDU-49
   entry land in the same base commit; overlay commit carries `grokestrator`, the
   overlay test, and the regenerated tracked `build/`.
9. **AC-9 attestation:** QA attests it validated the exact final manifest path
   (20261014-5 protocol); any denied command strings recorded verbatim (mdu-46
   diagnostic apply-now). The run itself dogfoods D1 (manifest finalized and validated
   before QA dispatch) and D3 (the §16 routing table checked against allowlists at
   design time).

## 16. Who executes / who grades + phase order and pricing

| # | Phase | Commands required | Who executes (model) | Who grades |
| --- | --- | --- | --- | --- |
| 1 | design | reads/writes docs only | architect (premium, glm-5.2) — this doc | code-reviewer (static trace) + qa |
| 2 | implement | file edits, snapshot/diff protocol | just-code-mid (mid, kimi-k2.7-code) | code-reviewer + test-agent |
| 3 | review | none — static-trace scope, shell denied by design, pre-scoped (20261030-2) | code-reviewer (mid, mimo-v2.6-flash) | orchestrator |
| 4 | test | pytest ×2 repos, mutation matrix in /tmp | test-agent-mid (mid, mimo-v2.6-flash) | qa + orchestrator |
| 5 | deploy | builds ×2, deploy dry-run/--force, cmp, probe gate | devops (mid, mimo-v2.6-flash) | qa |
| 6 | validate | file inspection (shell denied by design; 20261021-8 landed sentence governs any retry) | qa (mid, mimo-v2.6-flash) | orchestrator |
| 7 | introspect | session_signals.py via allowlisted wrapper; file-tool greps (D6's own floor) | introspector (budget, mimo-v2.6-flash per registry) | orchestrator |
| 8 | commit | gates + git commit/push ×2 repos | orchestrator (glm-5.3-flash per the mdu-47 repoint) | user (push visibility) |

Loop order: design → implement → review → test → deploy → validate → introspect →
commit; devops runs after review and after the last fix cycle; any fix cycle re-runs the
affected suite and both builds (20261021-6). Base commit first, overlay commit second.
Per D1: the manifest is finalized and `run_ledger.py validate` exits 0 BEFORE the qa
dispatch; after QA only `qa_grade` flips and the validator re-runs. Per D3 (applied to
this very table at design time): reviewer and qa are read-only by design — every
command above is executed by devops, test-agent, or the orchestrator, and the two
gate-bearing children get pre-attached outputs.

Implement-brief requirements (D2 discipline even though this is not a term sweep): the
brief attaches this doc's per-file anchor table verbatim, requires the implementer to
grep each anchor text before editing (anchors are authoritative, line numbers are
survey-time), and includes the §12 protocol commands.

## 17. Open questions / risks

1. **D5 narrowing** (sentence-3 referent corrected + dropped for coders) and **D6
   reword** (degradation ladder) both deviate from the entry texts — recorded with grep
   evidence in §6/§7; flagged for review sign-off. Reverting either to verbatim is a
   one-line change if the user prefers fidelity over executability, at the cost of a
   dangling reference (D5) or an unexecutable mandate (D6).
2. D4 in `skills/mdu-lifecycle/SKILL.md` was considered and rejected (§5) — mirrors
   only. Extend later if the user wants the skill to carry it.
3. The ledger lifecycle line ("before the commit phase, finalize…") is deliberately
   left unedited (§2) — D1 is the stricter trigger; a future MDU may unify the wording.
4. The probe-gate no-refresh expectation (fact 8) rests on `build/opencode.json` using
   `{file:}` references — devops must verify green, and a red gate is a STOP, not a
   refresh (AC-4).
5. 21 insertions across 9 source files in one implement phase: the anchor table is the
   census; a missed anchor costs a fix cycle. The mutation override (§11.6) is a
   required test feature — if the implementer omits it, AC-6 is unverifiable.
6. `grokestrator`'s built-copy path for overlay pin #2 (§11) is to be glob-verified at
   implement time before the pin is written — do not hand-assume the built path.
