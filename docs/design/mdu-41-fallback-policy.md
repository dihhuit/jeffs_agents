# MDU-41 — Paid-spawn fallback ladder (prompt-only policy)

**Status:** design, ready for implementation
**Repos:** base (this repo) first, then overlay `opencode_agents`
**Supersedes:** the MDU-41 backlog entry's "free-tier budgeting … while any
free models remain" framing. MDU-40 removed every free model from both
configs, so there is no free budget left to police; this MDU governs
**paid-spawn** failures (cap/provider error, quota refusal, credit
exhaustion) on `opencode-go/*`, and the explicit no-ladder rule for `xai/*`.

---

## 1. Goal

One canonical fallback policy, byte-identical on policy wording, carried by
all three orchestrator mirrors, plus two small adjacent clauses (architect
live-probe, introspector session-id) and its supporting docs/tests:

- a compact **PAID-SPAWN FAILURE LADDER** block in `prompts/orchestrator.md`,
  `grok/agents/orchestrator.md`, and the overlay `grokestrator.md`;
- a design-time **live-probe clause** in both architect mirrors
  (apply-now 20261030-1);
- a **root session id** clause for introspector runs in all three
  orchestrator mirrors (apply-now 20261030-2);
- `docs/fallback-ladder.md`, the human explanation (mirrors how
  `docs/resume-block.md` documented MDU-34);
- a scripted dry-run demonstration under `evals/tasks/` and parity tests in
  both repos.

**This MDU is prompt-only.** No changes to `opencode.json` (either repo),
`scripts/lib/validate.py`, `scripts/lib/probe_models.py`, `build.sh`, or
`deploy.sh`. The paid census (`opencode-go/`|`xai/` prefixes, fail-closed)
already constrains configs; this MDU adds behavioral policy on top. The
standard deploy step ships the new prompt text; no deploy-machinery change.

---

## 2. Verified facts (read from the tree, 2026-10-30)

1. `prompts/orchestrator.md` L176 carries the pre-MDU-41 fallback bullet:
   "If a subagent reports token/rate limit errors, retry once on the same
   variant, then escalate one rung (e.g. `just-code` → `just-code-mid`).
   Never fall back to a free variant — there is none — and never exceed the
   existing fourth-retry gate." The new block **replaces** this bullet.
2. `grok/agents/orchestrator.md` (token frugality L172-177) and the overlay
   `grok/agents/grokestrator.md` (L128) have **no** cap-error bullet at all;
   both end their frugality block with the MDU-40 canonical sentence
   "All loop phases run on paid models; free-tier variants are retired
   (MDU-40)." — which stays.
3. Distinct `opencode-go/*` models in the canonical base `opencode.json`:
   deepseek-v4.1-flash, kimi-k2.7-code, glm-5.2, mimo-v2.6-flash. Base probe
   report `config/model-probe-report.json` (probed 2026-10-30T04:18:54Z):
   all four `status: "ok"`. The overlay MDU-40 census
   (`opencode_agents/tests/test_mdu_40_overlay_paid_default.py`
   `LIVE_OK_MODELS`) additionally verified live: glm-5.3, glm-5.3-flash,
   mimo-v2.6-pro (plus `xai/grok-4.7`, `xai/grok-build-0.1`). The union is
   exactly the user's seven-model rotation list.
4. `opencode-go/mimo-v2.5` is dead upstream (caught by the MDU-40 test-phase
   live probe; `RETIRED_MODEL_IDS` pins its absence from both configs). It
   must never appear as a rotation target; the mirrors must not name it.
5. No golden case pins the old bullet: grep over `evals/` for
   `rung|rate limit|fallback` matches only an unrelated sequencing note in
   `evals/tasks/03-ledger-conformance/task.md` L67. The prompt regression
   gate will run (prompts change) but has no case on this text.
6. `skills/mdu-lifecycle/SKILL.md` L43 repeats the old rung wording — a
   third copy of the fallback policy that must be synced (D8).
7. Both architect mirrors still delegate to `research`
   (`prompts/architect.md` L9, `grok/agents/architect.md` L15) — an agent
   MDU-40 **deleted**. Same dead-agent drift exists in `prompts/devops.md`
   L11 and `prompts/code-reviewer.md` L13 (and their grok mirrors) — noted
   as an out-of-scope follow-up in D5.
8. Introspector evidence (mdu-40 entry in `agent-improvements.md`): the
   brief supplied no `--session-id`, so `session_signals.py` silently
   returned the stale mdu-20 tree and every script-derived signal had to be
   discarded. Logged as apply-now 20261030-2. None of the three
   orchestrator mirrors' introspect steps (base L128, grok L134, overlay
   L132) mentions the session id; `prompts/introspector.md` L12 already
   accepts `--session-id` when supplied.
9. Parity pinning precedents: `tests/test_mdu_34_resume_block.py`
   `_all_mirrors()` reaches the overlay grokestrator via
   `REPO_ROOT.parent` and skips cleanly when the sibling is absent;
   `tests/test_mdu_40_paid_default.py` pins `CANONICAL_SENTENCE` over the
   two base mirrors; the overlay test pins `XAI_RULE_SENTENCE`
   byte-identically across grokestrator + both base mirrors.
10. `evals/tasks/` currently holds 01–04; the demonstration task takes index
    05.
11. Overlay build: grokestrator has no base counterpart, so the overlay-root
    `grok/agents/grokestrator.md` is the live source and is copied into
    `build/grok/agents/grokestrator.md` (the overlay test checks both).

---

## 3. Decisions

### D1 — Retarget the backlog entry: free budgeting → paid-spawn errors

[DECIDED-user] The backlog's "while any free models remain" premise died
with MDU-40 (zero free rows in either config). MDU-41's policy governs
paid-spawn death: cap/provider errors, quota refusals, credit exhaustion on
`opencode-go/*`, and the no-ladder rule for `xai/*`. The entry is retitled
"Paid-spawn fallback policy in agent definitions (cap/provider/credit
errors)" with a supersession note; AC1's "any free-variant prompts
(`*-free`)" clause is N/A-by-supersession (those prompts were deleted).
The policy still **says** "never substitute a free model" so future drift
is guarded even though the substitution is currently impossible.

### D2 — Ladder semantics [DECIDED-user, LOCKED — do not redesign]

For a paid `opencode-go/*` spawn that dies on a cap/provider error, quota
refusal, or credit exhaustion:

1. **One retry** of the same failure, same model, same or a fresh spawn
   (transient-blip tolerance).
2. **Exactly one rotation** to a different `opencode-go/*` model from the
   verified 2026-10-30 live rotation list: deepseek-v4.1-flash, glm-5.2,
   glm-5.3, glm-5.3-flash, kimi-k2.7-code, mimo-v2.6-flash, mimo-v2.6-pro.
   Never mimo-v2.5 (dead upstream). Never more than one silent rotation.
3. **Stop and escalate** to the user with the failure evidence (both error
   reports, both model ids).

`xai/*` (grok-family) spawns: **no ladder** — a cap/credit/auth error
escalates directly to the user. Rationale: the xAI account auto-tops-up, so
errors there are auth-shaped, and silent self-recovery would mask them.

Design rationale for the shape: one retry absorbs the most common failure
class (transient provider blips) at zero cost; exactly one rotation bounds
blast radius when a single model is having a bad hour, while still avoiding
the naive-rotation spiral; escalation-with-evidence reuses the existing
retry-guardrail ceiling (never expands the fourth-retry gate) and the human
approval gates. This supersedes the old "escalate one rung" bullet — a
rung escalation (`just-code` → `just-code-mid`) is now one *instance* of
the single allowed rotation, not a separate mechanism.

### D3 — Exact policy block, byte-identical in all three mirrors

[DECIDED-design] The following block is inserted **verbatim** (identical
bytes, including the leading `- ` and two-space continuation indents) into
all three orchestrator mirrors:

```markdown
- **PAID-SPAWN FAILURE LADDER — ONE RETRY, ONE ROTATION, THEN STOP:**
  When a paid `opencode-go/*` spawn dies on a cap/provider error, quota refusal, or credit exhaustion (e.g. a child reporting `provider.quota`, a 429, or a spent-credit refusal):
  1. Retry the same failure once — same model, in the same or a fresh spawn. One retry only; it exists to absorb transient blips.
  2. If the failure repeats, make exactly ONE rotation to a different `opencode-go/*` model from the verified live rotation list: deepseek-v4.1-flash, glm-5.2, glm-5.3, glm-5.3-flash, kimi-k2.7-code, mimo-v2.6-flash, mimo-v2.6-pro. A role-rung escalation (`just-code` → `just-code-mid`) counts as the one rotation. Never rotate to an unverified model, and never substitute a free model — free variants no longer exist; fallback drift must not reintroduce them.
  3. If the rotated spawn also fails, STOP. Escalate to the user with the failure evidence: both error reports and both model ids. Never a second silent rotation.
  This ladder specializes the retry guardrail for this failure class; it never expands the fourth-retry gate.
  `xai/*` (grok-family) spawns get NO ladder: a cap, credit, or auth error there escalates directly to the user with the evidence. The xAI account auto-tops-up, so such errors are auth-shaped — silent self-recovery would mask them.
```

Insertion points (structure of each mirror is otherwise unchanged):

| Mirror | Insert |
| --- | --- |
| `prompts/orchestrator.md` | inside **TOKEN FRUGALITY RULES**, **replacing** the L176 rung bullet (its semantics are absorbed: retry-once + one rotation) |
| `grok/agents/orchestrator.md` | immediately **after** the MDU-40 canonical sentence (L177), as a new top-level bullet in **TOKEN FRUGALITY RULES** |
| overlay `grok/agents/grokestrator.md` | as a new **top-level** bullet immediately after the L128 TOKEN FRUGALITY sub-bullet (i.e. before the current "- On failure, root-cause…" line) — column-0, so the bytes match the base mirrors |

Why byte-identical rather than behaviorally-equivalent: the policy is short
enough to pin exactly, and past drift (free-variant wording diverging per
mirror) came from per-mirror rewording. MDU-34 and MDU-42 already pin
multi-line/sentence policy byte-identically; this follows that precedent.
Note the base Grok mirror's spawns are all `xai/*`, so its ladder clause is
inert there in practice while its `xai/*` clause is the live one — the
byte-identical requirement is still correct: policy wording must not fork
per harness.

The block is self-contained by design (no doc paths): at run time the
orchestrator works in the *target* project, where `docs/fallback-ladder.md`
does not exist. The rotation list is inlined for the same reason.

### D4 — Rotation list: source, staleness behavior, maintenance

[DECIDED-design] The seven ids are the union of (a) the base
`config/model-probe-report.json` 2026-10-30 probe (4 models, all ok) and
(b) the overlay MDU-40 live census `LIVE_OK_MODELS` (which probed the
remaining three). `mimo-v2.5` is excluded — dead upstream, pinned absent
from both configs by `RETIRED_MODEL_IDS`.

Staleness fails safe: if a listed model dies after this doc is written, the
rotated spawn fails, the ladder's step 3 fires, and the loop escalates —
the ladder never loops and never picks a second target silently. A stale
entry costs at most one wasted spawn.

Maintenance procedure (documented in `docs/fallback-ladder.md`): when a
model dies upstream or a new one is verified, update (1) the block in all
three mirrors, (2) `docs/fallback-ladder.md`, (3) `LADDER_BLOCK` in the
base and overlay test files, in the same commit — the parity tests red on
any partial update, which is the drift guard working. Do not name dead
models in the mirrors (a dead id in a prompt invites an LLM to spawn it);
the dead list lives in the docs file only.

### D5 — Architect live-probe clause (apply-now 20261030-1) + dead-agent fix

[DECIDED-design] Insert the following bullet **verbatim into both**
`prompts/architect.md` and `grok/agents/architect.md`, in the **Hard
constraints** section, after the "Include rationale…" bullet:

```markdown
- **Probe every model id you assign, at design time:** a registry "active" status is untrusted — a listed model can be dead upstream. Before handing a design to implementation, verify each `opencode-go/*` / `xai/*` model id the design assigns with a one-shot live probe (e.g. `timeout 90 opencode run -m <id> "Reply with exactly: OK"`) and require exactly `OK` back. On a failed probe, assign a different live model, record the swap in the design doc, and re-probe. Never hand implementers or test-agents a model id you have not seen answer.
```

Rationale: MDU-40's worst catch (mimo-v2.5 already dead at design time,
discovered only at the test phase) was a design-time verification gap. The
clause moves the probe to the earliest, cheapest point. The command shown
is an example (`e.g.`), so the clause stays harness-neutral.

Drive-by in the same two files: L9/L15 still delegate to `research`, an
agent MDU-40 deleted. Change "Delegate to `research` agents when you need
to investigate…" → "Delegate to `deep-research` when you need to
investigate…" in both architect mirrors. No test pins this wording
(verified by grep). The same dead reference in `prompts/devops.md` L11 and
`prompts/code-reviewer.md` L13 (plus grok mirrors) is **out of MDU-41
scope** — record it in the backlog as a two-line follow-up; do not expand
this MDU's file list for it.

### D6 — Introspector root-session-id clause (apply-now 20261030-2)

[DECIDED-design] Append this sentence, byte-identical, to the introspect
step of all three orchestrator mirrors (base L128 item 7, grok L134 item 7,
overlay L132 bullet — surrounding wording already differs per mirror; the
pinned sentence does not):

> Include the root session id when introspecting (`--session-id`, e.g.
> `OPENCODE_SESSION_ID`); without it the introspector reads a stale session
> tree.

Rationale: the mdu-40 introspection ran against the stale mdu-20 tree
because the brief carried no session id, and every script-derived signal
had to be discarded. One sentence at the call site prevents the class.
`prompts/introspector.md` already forwards `--session-id` when supplied —
no introspector change needed.

### D7 — Docs deliverable: `docs/fallback-ladder.md`

[DECIDED-design] Path chosen: `open-agent-definitions/docs/` +
`fallback-ladder.md` — kebab-case in `docs/` beside
`docs/resume-block.md`, named after the mechanism, not the MDU (the
MDU number lives in the banner line). Outline (≈90-120 lines, same voice
as `docs/resume-block.md`):

1. Banner: what the ladder is, which MDU introduced it (41), which
   mirrors carry it verbatim.
2. The exact block (fenced, same bytes as the mirrors).
3. Decision table: failure class → mandated action (4 rows: Go-model
   first failure / repeat after retry / failure after rotation / any
   `xai/*` failure).
4. The verified live rotation list (7 ids + probe dates and sources) and
   the dead list (`mimo-v2.5`, dead upstream 2026-10-30, never a target).
5. Why `xai/*` has no ladder (auto-top-up; auth-shaped errors; masking
   risk).
6. The never-free guard and its enforcement chain (MDU-40 deletion, paid
   census, parity tests).
7. A worked dry-run example — the exact transcript shape the
   `evals/tasks/05-fallback-ladder/` driver walks.
8. Maintenance procedure (D4).

### D8 — Sync the third copy: `skills/mdu-lifecycle/SKILL.md` L43

[DECIDED-design] Replace the old rung line with ladder-consistent wording:

```markdown
- On a cap/provider error, quota refusal, or credit exhaustion from a paid `opencode-go/*` spawn: one retry, then exactly one rotation to a different live `opencode-go/*` model, then stop and escalate with evidence. `xai/*` spawns: no ladder — escalate directly. Never substitute a free model (MDU-41).
```

Rationale: the skill is the loop's checklist; leaving the old
"escalate one rung" line there would contradict the mirrors on the first
cap error. MDU-40 already edited this file for the same reason.

### D9 — Scripted dry-run demonstration (replaces "live cap-error spawn")

[DECIDED-design] New task dir `evals/tasks/05-fallback-ladder/` with
`task.md` + `driver.sh`, mirroring the `03-ledger-conformance` shape.
Rationale: no free caps remain to die live, and forcing a real
cap/credit error on a paid account is not a demonstration anyone should
script. The AC's own "scripted dry-run" wording is honored by making the
decision path itself executable and deterministic.

`driver.sh` (bash, offline, no live spawns, no network):

- Walks six scripted cases and prints the mandated ladder action per
  event, then verifies each case's governing sentence exists in every
  reachable orchestrator mirror (base two always; overlay grokestrator
  when the sibling checkout exists — same optional pattern as
  `test_mdu_34`):

| Case | Scripted event | Mandated action |
| --- | --- | --- |
| 1 | `opencode-go/deepseek-v4.1-flash` spawn reports `provider.quota` | one retry, same model |
| 2 | the retry fails identically | one rotation to a live-list model ≠ original |
| 3 | the rotated spawn fails | stop; escalate with both errors + both model ids |
| 4 | a second rotation is contemplated | forbidden — never a second silent rotation |
| 5 | `xai/grok-4.7` spawn reports credit/auth error | no ladder; escalate directly |
| 6 | any spawn failure | never substitute a free model |

- Output: one line per case `[case n] event → action [policy sentence
  found in k/k mirrors]`; exit 0 iff every case resolves and every
  dependency sentence is present in every reachable mirror; non-zero with
  a named missing sentence otherwise.
- All commands under `timeout`; no secrets, no model calls, no entropy
  traps (its output is plain words).

`task.md` documents how to run it and what the output means. This driver
is a demonstration artifact, not production code: it lives under
`evals/tasks/`, is invoked read-only by the test suite, and wires into no
build/deploy/validator path.

### D10 — QA pattern

QA brief for this MDU must check, in order:

1. **Policy fidelity (human check):** the block in any one mirror matches
   the locked D2 semantics step-for-step — one retry; exactly one
   rotation from the seven-model list; stop + escalate with evidence;
   `xai/*` excluded; "never substitute a free model" present. Presence
   alone (the tests) is not semantic fidelity.
2. **Parity:** new base + overlay tests green; block byte-identical
   across the three mirrors; architect clause byte-identical across the
   two architect mirrors; introspector sentence in all three.
3. **No drift tokens:** `mimo-v2.5`, `big-pickle`, and any `-free` token
   absent from every edited mirror; "escalate one rung" gone from the
   base prompt and the skill.
4. **Gates:** `timeout 120 python3 -m pytest tests/ -q` green (base),
   overlay suite green, `./build.sh` green in both repos, `./deploy.sh`
   dry-run green in both repos. Prompt regression gate:
   `timeout 60 python3 scripts/lib/prompt_regression.py gate` must exit 0
   (no golden case pins the old bullet — verified; if it reds, fix or
   revert, never baseline-refresh to force green; a baseline update
   happens only after QA PASS, committed with `cases.json`).
5. **Claude regeneration:** after `./build.sh`, the generated
   `build/claude/agents/` copy `orchestrator.md` contains the ladder
   block and the copy `architect.md` contains the probe clause — proof
   the policy flowed through the build, never hand-edited.
6. **Demonstration:** `timeout 60 bash` + the driver path exits 0 with
   all six case lines.
7. **Deployed copies (if `--force` deploy ran):** the installed
   orchestrator prompt and grokestrator profile under the user's config
   dirs carry the block (one grep each).

QA reports BLOCKED if Playwright-class tooling is unavailable for any
browser-adjacent check — none is needed here; this is a grep/pytest/bash
MDU.

### D11 — Test plan

New base file `tests/test_mdu_41_fallback_ladder.py` (suite was 640 green
at MDU-40; expect ~+18-22 here):

1. `LADDER_BLOCK` (the exact D3 string) present in both base mirrors;
   overlay grokestrator included via the `test_mdu_34` `_all_mirrors()`
   optional pattern (skip cleanly when the sibling checkout is absent, so
   the public repo stays self-contained).
2. `"mimo-v2.5"` absent from all three mirrors (docs file may name it —
   mirrors must not).
3. `"NO ladder"` and `"never substitute a free model"` present in all
   three (readable-failure aliases of test 1).
4. Each of the seven rotation ids appears inside the block in every
   mirror; no `-free` token introduced.
5. `"escalate one rung"` absent from `prompts/orchestrator.md` and
   `skills/mdu-lifecycle/SKILL.md` (old semantics retired).
6. Architect clause string present byte-identically in both architect
   mirrors; "Delegate to `research`" absent; "deep-research" present.
7. D6 sentence present in all three orchestrator mirrors.
8. `docs/fallback-ladder.md` exists and contains: the block, all seven
   live ids, the `mimo-v2.5` dead note, the `xai/*` no-ladder rationale,
   "never substitute a free model", and the maintenance procedure.
9. Driver: `subprocess.run(["bash", <driver path>], timeout=60)` exits 0
   and stdout contains `[case 1]` … `[case 6]`.

New overlay file `opencode_agents/tests/` +
`test_mdu_41_overlay_fallback_ladder.py` (pattern:
`test_mdu_40_overlay_paid_default.py`):

1. `LADDER_BLOCK` present in the grokestrator source **and** the built
   copy (when `build/` exists).
2. Block byte-identical with both base mirrors (read via the sibling
   path, like `GROKESTRATOR_BASE_MIRRORS`).
3. D6 sentence present; `"mimo-v2.5"` and `-free` tokens absent.
4. Overlay census untouched: existing `test_mdu_40_overlay…` still green
   (no config rows changed — do not duplicate its assertions).

Existing tests to **verify only** (no edits expected):
`test_mdu_40_paid_default.py` (canonical sentence retained — the new
block is additive to it), `test_mdu_34_resume_block.py`,
`test_grok_model_allowlist.py` (frontmatter untouched),
`test_validate_parity.py` (validator clause table untouched),
`test_mdu_35_question_tool.py`.

### D12 — Explicitly out of scope

- No `opencode.json` edits in either repo (census tests must stay green
  untouched — this is itself a QA check that the MDU stayed prompt-only).
- No validator, probe, build, or deploy script changes.
- No Claude hand-edits — regenerated by `./build.sh` and checked in D10.5.
- No `devops.md` / `code-reviewer.md` dead-`research` cleanup (backlog
  follow-up, D5).
- No live cap-error induction on any paid account.

---

## 4. Implementation file list

Base (commit 1):

| File | Change |
| --- | --- |
| `prompts/orchestrator.md` | D3 block replaces the L176 rung bullet; D6 sentence appended to introspect item 7 |
| `grok/agents/orchestrator.md` | D3 block after the MDU-40 canonical sentence; D6 sentence appended to introspect item 7 |
| `prompts/architect.md` | D5 clause + `research` → `deep-research` |
| `grok/agents/architect.md` | D5 clause + `research` → `deep-research` (byte-identical to the prompt copy) |
| `docs/fallback-ladder.md` | new, D7 outline |
| `skills/mdu-lifecycle/SKILL.md` | L43 ladder sync (D8) |
| `evals/tasks/05-fallback-ladder/task.md` | new, D9 |
| `evals/tasks/05-fallback-ladder/driver.sh` | new, D9 (executable, offline) |
| `tests/test_mdu_41_fallback_ladder.py` | new, D11 |
| `FEATURE_BACKLOG.md` | MDU-41 retitle + supersession note + status (D1) |
| `docs/design/mdu-41-fallback-policy.md` | this doc (status → implemented) |

Overlay (commit 2, after base is green and pushed):

| File | Change |
| --- | --- |
| `grok/agents/grokestrator.md` | D3 block (top-level bullet after L128) + D6 sentence in the L132 introspect bullet |
| `tests/` + `test_mdu_41_overlay_fallback_ladder.py` | new, D11 |
| `build/grok/agents/grokestrator.md` | regenerated by `./build.sh` (commit the rebuilt tree per workspace rule) |

Ordering: base suite green → `./build.sh` → prompt regression gate →
commit + push → overlay `./build.sh` → overlay suite → `./deploy.sh`
dry-run → commit + push. Two commits; never mix the repos. A
`./deploy.sh --force` at the end makes the policy live in the user's
daily agents — recommended, since prompt deployment is the point of the
MDU, but it changes no deploy machinery.

Secret-scan note: all new content is prose and known model ids; no
32+-char unbroken alnum runs are introduced (every path in the new files
contains separators). If any probe output is ever pasted into
`docs/fallback-ladder.md`, keep it to the plain-word transcript shape —
never raw base64/hex blobs.

---

## 5. Risks

| Risk | Mitigation |
| --- | --- |
| Rotation list goes stale (a listed model dies upstream) | ladder fails safe: the one rotation fails → step 3 escalates; maintenance procedure in the docs; parity tests force conscious list updates |
| Byte-identical pinning makes list edits touch 3 mirrors + 2 test files | intentional (parity fuse, MDU-42 precedent); the test names the missing sentence, so the fix is mechanical |
| Prompt bloat in the busiest prompt file | block is ~9 lines, comparable to the question-tool block; it *replaces* a bullet in the base prompt |
| Base Grok mirror carries a Go-model ladder it can never fire | accepted: policy wording must not fork per harness; the `xai/*` clause is the operative one there |
| Golden gate reds on an unforeseen case | grep found no case pinning the old bullet; if red, fix or revert per protocol — never refresh to force green |
| Overlay grokestrator insertion breaks its list nesting | insert at column 0 before the "- On failure…" line; overlay test checks the built copy, and build validity is a gate |
| Implementers hand-edit Claude mirrors | D10.5 greps the generated files; hand edits are overwritten by the next build anyway |
| Scope creep into devops/code-reviewer dead-`research` cleanup | explicitly out of scope (D5/D12); backlog follow-up instead |

Rollback: `git revert <mdu-41-commit>` in each repo + `./build.sh` +
`./deploy.sh --force`. No state, no config, no migration.

---

## 6. Acceptance criteria mapping

| Backlog AC (as retitled by D1) | Satisfied by |
| --- | --- |
| AC1 — policy blocks in both base mirrors + grokestrator, behaviorally equivalent (the "`*-free` prompts" tail is N/A — deleted in MDU-40) | D3 (byte-identical block, stronger than equivalent), D11 parity tests |
| AC2 — cap-error fallback demonstrated in a scripted dry-run | D9 (driver + worked example in the docs); the "live cap-error spawn" qualifier is superseded — no free caps remain to die, and inducing paid-account errors is out of scope (D12); historical live evidence lives in MDU-39/40 forensics |
| AC3 — full suite and both builds green; QA PASS | D10 (QA pattern), D11 (test plan), §4 ordering |

---

## 7. Spawn brief facts

- Prompt-only MDU: no `opencode.json`, validator, probe, build, or deploy
  script changes in either repo. Both censuses must stay green untouched.
- Insert the D3 block byte-identically into:
  `prompts/orchestrator.md` (replacing the L176 rung bullet),
  `grok/agents/orchestrator.md` (after the MDU-40 canonical sentence), and
  overlay `grok/agents/grokestrator.md` (top-level bullet after its L128
  frugality bullet). Copy it from this doc's fenced block — do not reword.
- Rotation list (verbatim in the block): deepseek-v4.1-flash, glm-5.2,
  glm-5.3, glm-5.3-flash, kimi-k2.7-code, mimo-v2.6-flash, mimo-v2.6-pro.
  Never `mimo-v2.5` (dead upstream — mirrors must not name it; the docs
  file records it as dead).
- The MDU-40 canonical sentence ("All loop phases run on paid models…")
  stays in all three mirrors — the new block is additive to it.
- Architect mirrors get the D5 probe clause (byte-identical in both) plus
  the one-word `research` → `deep-research` delegation fix.
- All three orchestrator mirrors get the D6 sentence:
  "Include the root session id when introspecting (`--session-id`, e.g.
  `OPENCODE_SESSION_ID`); without it the introspector reads a stale session
  tree."
- New files: `docs/fallback-ladder.md` (D7 outline),
  `evals/tasks/05-fallback-ladder/` (task.md + driver.sh, D9 case table),
  base `tests/test_mdu_41_fallback_ladder.py`, overlay
  `tests/test_mdu_41_overlay_fallback_ladder.py`.
- Sync `skills/mdu-lifecycle/SKILL.md` L43 to the D8 line.
- Gates: pytest both repos, `./build.sh` both repos, prompt regression
  gate, `./deploy.sh` dry-run both repos; verify the generated Claude
  orchestrator/architect carry the block/clause.
- Base commit + push first, then overlay commit + push. Do not touch
  `devops.md` / `code-reviewer.md` (dead-`research` drift there is a
  backlog follow-up). No live cap-error induction; no upstream reports.
