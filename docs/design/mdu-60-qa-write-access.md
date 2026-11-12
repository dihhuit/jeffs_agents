# MDU-60 — QA write-access decision + durable-QA-output pattern

> Design phase, orchestrator-driven MDU. No code/config edits here — diffs are
> fenced proposals. Paths repo-relative, or `$WORKSPACE/<sub>` (base) and
> `$WORKSPACE_OVERLAY/<sub>` (sibling overlay `opencode_agents/`). Date 2026-11-12.

## 1. Decision

**Grant-write vs consume-and-persist? → consume-and-persist.**

Evidence (no store-row bodies — mdu-35 masking; pointers only):
- Sprite `ses_e6d1ac9c…` (agent `qa`): 11 rows `%Permission denied: shell%`,
  tool `shell` — child asked to write findings (mdu-48 §S1, commit `c3b2d48`).
- mdu-48 S1: route write/exec away from read-only agents; pre-scope denials
  (class `20261021-9`/`20261021-8`).
- `20261110-1` (resolved mdu-57, clause C): QA brief pre-states plain-form
  probes + file-tool fallback. Gap is UPSTREAM — briefs still ask read-only
  agents to produce files.
- `20261111-3` (open): content denials (`cp`,`mv`,`rm`,`python3 -c`,`curl`,
  git mutations) fire regardless of wrapper, never retry. New pattern's
  pre-statement COEXISTS (upstream fix vs this downstream symptom).
- Read-only sandbox precedent: `mdu-41`/`mdu-45` (decisions.md) — read-only is
  the grade's independence guarantee.
- Applied workaround (user 2026-11-12): orchestrator received QA output,
  dispatched a write-capable agent to persist. Worked → becomes the default.

**User rulings (2026-11-12, this session, verbatim):**
1. QA write policy = **consume-and-persist** (NOT grant-write). QA stays
   read-only; the QA reply IS the deliverable; a write-capable agent
   (just-code/devops) dispatched by the orchestrator persists durable artifacts;
   QA briefs pre-state this.
2. Definition-change path = **pre-approved in-MDU**: the pattern's definition
   edits apply directly in this MDU after review sign-off (backlog carve-out
   exercised). No `apply the definition diffs` round-trip for this batch.

Granting write recreates the exact failure class (read-only agent asked to
produce files) and adds tree-mutation risk during validation. Grant-write is
closed with rationale; no `qa` permission edit ships.

## 2. Codified pattern spec (what ships)

### 2a. ONE clause, byte-identical, three orchestrator mirrors

Live source carriers:
- `$WORKSPACE/prompts/orchestrator.md` (base OpenCode)
- `$WORKSPACE/grok/` + `agents/orchestrator.md` (base Grok)
- `$WORKSPACE_OVERLAY/grok/` + `agents/grokestrator.md` (overlay Grok — **cross-repo**:
  separate commit; base first, then overlay build + commit. NOT authored in the
  base repo — named as a carrier only.)

Anchor: insert immediately AFTER the existing `**Phase-routing pre-check:**`
clause (base `prompts/orchestrator.md:140`, base `grok/agents/orchestrator.md:140`,
overlay `grok/agents/grokestrator.md:122`) — that clause already routes exec/write
away from read-only agents at dispatch; this extends it to durable output.

Clause (byte-identical across all three; the test constant holds this verbatim
minus the emitted `- ` lead):

```text
- **Durable QA output (consume-and-persist):** When QA or any read-only grading
  agent must produce a durable artifact (answers_qa JSON, findings, reports,
  screenshots), the orchestrator consumes the QA reply — the reply IS the
  deliverable — and dispatches a write-capable agent (just-code/devops) to
  persist it, or writes the coordination artifact itself. The QA brief
  pre-states verbatim: "your reply is the deliverable; a write-capable agent
  persists artifacts; do not attempt writes." Do not grant QA write permission
  to work around this; the read-only sandbox is the grade's independence
  guarantee.
```

Orthogonal to `20261110-1` clause C (downstream denial retry) — neither
supersedes the other. Editing `qa` prompt bodies is out of scope; the brief
pre-statement rides the checklist lines below.

### 2b. TWO `docs/brief-checklist.md` lines (`## qa` section, after :58)

```text
- Name the durable-artifact writer (just-code/devops) in every QA brief whose verdict must persist as a file; QA does not write artifacts. [20261112-2]
- The QA reply is the deliverable; a write-capable agent persists durable artifacts; QA briefs pre-state "do not attempt writes." [20261112-2]
```

New agent-improvements entry `20261112-2` opened `[x]` resolved-by-shipping
(pre-approved carve-out); reopen trigger = first post-deploy QA child that
attempts a write despite the pre-stated brief.

### 2c. AC-2 state pin

Pin the UNCHANGED read-only state: `qa` (opencode.json:1758) and `qa-pro`
(:2096) each have `{"action":"edit","resource":"*","effect":"deny"}` and NO
`{"action":"edit"|"write",…,"effect":"allow"}`. Confirmed at design time — both
blocks: `edit` deny + `shell` deny + narrow shell allowlist; no `write` action.
No permission edit ships.

### 2d. Pins (mdu-49 batch pattern)

- Byte-identity: clause present exactly once in each of the 3 mirrors,
  sha256-equal across them. Non-vacuous — asserts clause TEXT, not file existence.
- 2 brief-checklist pins: each line present exactly once in `## qa`.
- Doc-consistency pin: test constant == §2a blockquote.
- AC-2 state pin: 2 cases (qa + qa-pro).
- Mutation matrix via `MDU60_TEST_ROOT` → /tmp copy, one clause stripped → each
  pin fails as designed.
- Prompt-regression gate: `prompts/` + `grok/agents/` touched →
  `timeout 60 python3 scripts/lib/prompt_regression.py gate`; expect **7/7
  unchanged baseline** (clause is procedural, not exercised by golden cases).

## 3. Carrier survey (grep-censused, not hand-counted)

Census: `grep -rn "Phase-routing pre-check"` (anchor) and
`grep -rn "consume-and-persist\|reply is the deliverable\|write-capable agent"`
(new-clause distinctive terms) across both repos.

**Live source carriers — 3:**

| Carrier | Anchor line |
| --- | --- |
| `$WORKSPACE/prompts/orchestrator.md` | :140 |
| `$WORKSPACE` + `grok/agents/orchestrator.md` | :140 |
| `$WORKSPACE_OVERLAY` + `grok/agents/grokestrator.md` | :122 |

**Old/improvised wording to sweep:** ZERO live hits in any prompt/agent
definition. Distinctive-term hits are only in `decisions.md`/`FEATURE_BACKLOG.md`
(docs) and the unrelated `durable artifacts` in the checkpoint clause. Clause is
**net-new** — no collision, nothing to remove.

**Excluded copies (named with reasons):**
- `$WORKSPACE_OVERLAY/build/{prompts,grok/agents,claude/agents}/orchestrator.md`
  + `…/grokestrator.md` (5 files) — GENERATED build outputs; regenerate at
  `./build.sh`; not hand-edited.
- `$WORKSPACE/tests/fixtures/pi_golden/prompts/orchestrator.md:170` — FROZEN
  pi-port golden (mdu-56). See Q1.
- `$WORKSPACE/docs/design/mdu-49-definition-batch-3.md:153` — design doc quoting
  the anchor; not a carrier.
- No dead overlay-root `prompts/orchestrator.md` or `grok/agents/orchestrator.md`
  exists (glob confirmed). `grokestrator` is a distinct root-added third mirror,
  not a same-name override.

## 4. Implementation, test, QA plans

**Implementation (just-code) — base first, then overlay:**
1. Insert §2a clause after Phase-routing pre-check in
   `$WORKSPACE/` + `prompts/orchestrator.md:140` + `$WORKSPACE/grok/` +
   `agents/orchestrator.md:140` (byte-identical).
2. Add §2b two lines to `$WORKSPACE/docs/brief-checklist.md` `## qa` (after :58).
3. Open `$WORKSPACE/agent-improvements.md` entry `20261112-2` `[x]`.
4. (No opencode.json edit — AC-2 pins the unchanged state.)
5. `cd $WORKSPACE && ./build.sh && timeout 120 python3 -m pytest -q &&
   timeout 60 python3 scripts/lib/prompt_regression.py gate`. Commit + push base.
6. Overlay: `cd $WORKSPACE_OVERLAY && ./build.sh`; insert SAME clause into
   `$WORKSPACE_OVERLAY/grok/` + `agents/grokestrator.md:122`; re-run `./build.sh`;
   overlay pytest + gate; commit + push overlay (build/ tracked).

**Test plan (test-agent) — `tests/test_mdu_60_qa_write_access.py`, ≈18 cases:**
clause constant (mdu-49 convention) · 3 mirror presence · 1 cross-mirror sha256 ·
2 checklist-line presence · 1 doc-consistency · 2 AC-2 state (qa+qa-pro) ·
≈7 mutation matrix (`MDU60_TEST_ROOT`) · 1 negative-boundary (distinctive terms
absent from excluded build/+pi_golden carriers pre-build) · `needs_overlay` skip
for the grokestrator pin in a standalone base clone.

**QA plan (probes pre-stated per clause C; content-denied verb list carried):**
QA probes use plain allowlisted forms or file-tool fallbacks ONLY. Pre-stated:
- `timeout 60 python3 -m pytest tests/test_mdu_60_qa_write_access.py -q`
  (allowlisted `timeout *` + `python3 -m pytest*`).
- `timeout 60 python3 scripts/lib/prompt_regression.py gate`.
- `grep -c "Durable QA output" prompts/orchestrator.md grok/agents/orchestrator.md`
  + `grep -c "Durable QA output" ../opencode_agents/grok/agents/grokestrator.md`.
- AC-2 via `grep '"action": "edit"' opencode.json` + `read` — never a shell mutation.
- **Content-denied verbs QA must NOT use** (`20261111-3` carry): `cp`, `mv`, `rm`,
  `python3 -c`, `curl`, git mutations — fire regardless of wrapper, never retry.
  Inspect the built overlay copy via `grep`/`read`, NOT `cp -r` to tmp.
- File-tool fallback: read/grep/sed; verdict labels "verified via file inspection";
  a denial is a form/permission event, not missing coverage.

## 5. Loop notes

- Design authored by the architect subagent (normal dispatch) on mdu-48 evidence
  (commit `c3b2d48`); no fresh store sweep — reused per backlog's mdu-60 note.
- Pre-approved-in-MDU carve-out exercised (user ruling 2): definition edits land
  directly after review sign-off; no `apply the definition diffs` round-trip.
- Clause is net-new (§3 sweep = zero live old wording) — wording-sweep "zero live
  hits" satisfied trivially for the old term.
- **Scope boundary:** MDU-61 (playwright chromium + blender launcher gating) NOT
  touched. Only overlap is the QA-plan content-denied-verb carry, which is
  `20261111-3`/clause C territory, not MDU-61's MCP fixes.
- Cross-repo order: base commits first (2 mirrors + checklist + agent-improvements
  + test), then overlay build + grokestrator edit + commit.

## Open questions

- **Q1:** Does any pin assert `$WORKSPACE/tests/fixtures/pi_golden/prompts/orchestrator.md`
  byte-matches the live source? If yes, inserting the clause drifts the fixture —
  regenerate it here, or relax the pin with rationale. Implementer: grep the test
  suite first.
- **Q2:** Confirm `20261112-2` is grep-free before insertion (`20261104-1`
  duplicate-id discipline); design-time `grep "id: 20261112-2" agent-improvements.md`
  → zero hits expected.
- **Q3:** mdu-48 S1's "MDU-47 clause" for the QA file-tool fallback is superseded
  by `20261110-1` clause C; the new clause coexists with clause C by reference,
  not the older mdu-47 wording. Confirm no stale mdu-47 reference in touched files.
