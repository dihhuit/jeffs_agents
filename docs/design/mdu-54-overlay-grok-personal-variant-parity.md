# MDU-54 · Overlay Grok personal-variant clause parity

Closes the two recorded deferrals: the MDU-49 follow-up
(`FEATURE_BACKLOG.md` L371 — the overlay root personal coder family) and the
MDU-47 follow-up (`FEATURE_BACKLOG.md` L493 — the overlay root personal qa,
architect, test-agent, and reviewer variants). Those two batches landed their
clauses in the base prompts, the base `grok/agents/` mirrors, the overlay `qa`
prompt override, and the overlay `grokestrator` — and explicitly deferred the
overlay-root personal Grok profiles. Done looks like: the 8 lagging overlay
root profiles carry the exact clause bytes their base siblings carry; the 2
test-agent profiles are confirmed already clause-complete (verify-only, no
edit); a new overlay test file pins all 10 with non-vacuous presence +
ordering + mutation coverage; **no base definition edit, no `prompts/` edit,
no `opencode.json` or model change ships** — pure definition-text parity in
the overlay repo, plus this doc and a backlog entry in the base repo.

Path variables used throughout: `$WORKSPACE` = the base repo root
(`open-agent-definitions`), `$OVERLAY` = the overlay repo root
(`opencode_agents`, sibling directory). Line numbers are survey-time
(2026-11-04); **anchor text is authoritative** — the implementer greps each
anchor before editing.

## 0. Surveyed files (reads only; grep-only beyond this list)

Base repo (`$WORKSPACE`):
- `docs/design/`
  `mdu-49-definition-batch-3.md` — full (clause texts, anchor table, pin and
  gate patterns, the §6 overlay coder-family deferral ruling).
- `docs/design/`
  `mdu-47-definition-guards-batch.md` — full (D1a-D1e texts and anchors, the
  D1a verify-only ruling, the open-question deferral of the overlay personal
  variants).
- `docs/design/`
  `mdu-53-verdict-line-precedence.md` — L1-70 (house style, §0 format, the
  "no model-id assignments" precedent).
- `FEATURE_BACKLOG.md` — L365-378 (MDU-49 follow-up L371), L487-495 (MDU-47
  follow-up L493).
- `grok/agents/` — directory census (20 files); targeted reads: `just-code.md`
  L15-28, `qa.md` L1-33, `qa-pro.md` L1-26, `architect.md` L14-27,
  `architect-premium.md` L12-24, `code-reviewer-pro.md` L12-24.
- `prompts/` — glob census (12 files) + clause-fragment grep (which base
  prompts carry which clause).
- `evals/README.md` — L122-211 (Prompt change protocol, exit semantics,
  authoring rules).
- `tests/`
  `test_mdu_47_definition_batch.py` — grep: overlay references L16-22, L81-102,
  L139-192, Dirty-tree verify pins L201-227.

Overlay repo (`$OVERLAY`):
- `grok/agents/` — directory census (18 files); full reads of the 8 edit
  targets: `grok-just-code.md`, `grok-just-code-mid.md`,
  `grok-just-code-pro.md`, `grok-qa.md`, `grok-qa-pro.md`,
  `grok-architect.md`, `grok-architect-premium.md`,
  `grok-code-reviewer-pro.md` (each ≤28 lines).
- `overlays/grok/agents/` — census (3 files) + clause grep (zero hits).
- `overlays/prompts/` — clause grep (qa fold already present; zero hits in
  `mdu-code.md` and `thought-leadership-coach.md`).
- `prompts/` — clause grep (zero hits).
- `overlays/manifest.json` — full (13 lines).
- `scripts/build.sh` — full (L24-128: build order, root-added logic L84-93,
  base validator call L123).
- `scripts/lib/overlays.sh` — full (snippet resolution L9-35, tree walkers
  L37-61, full-file install L63-77).
- `scripts/deploy.sh` — grep: probe gate L16-24, L117-167.
- `tests/` — census; full reads: `test_mdu_49_grokestrator_clauses.py`
  (the pin pattern to copy), `test_mdu_47_overlay_qa_fold.py` (fold pin
  pattern), `test_mdu_09_overlay_prompt_regression.py` (wrapper semantics);
  targeted read `test_mdu_30_overlay_shell_allowlist.py` L100-147; grep of
  target-name pins across the suite.
- `build/grok/agents/` — glob (all 10 target names present as built copies).

Grep-only beyond the lists: the clause-fragment census over
`$WORKSPACE/grok/agents/`, `$WORKSPACE/prompts/`, `$OVERLAY/grok/agents/`,
`$OVERLAY/overlays/`, `$OVERLAY/prompts/` (fragments: `Dirty tree`,
`trace it as a procedure`, `fails the criterion even when`,
`no pipes, no redirects`, `write file paths repo-relative`,
`looks corrupted or unexpected`, plus the four MDU-49 orchestrator clause
leads); pre-commit / secret-scan references in both repos; manifest snippet
references.

## 1. Verified facts that shape the design

1. **Overlay-root Grok profiles are root-added live sources.** The base
   `grok/agents/` holds 20 kebab-named profiles (no `grok-*` names); the
   overlay full-file dir `$OVERLAY/overlays/grok/agents/` holds only
   `grok-mdu-code.md`, `mdu-code.md`, `thought-leadership-coach.md`.
   `build.sh` L84-93 (`sync_root_additions`) copies each
   `$OVERLAY/grok/agents/*.md` into the build **only if the name is absent**
   — no overlay root name collides with a base or overlay-full-file name, so
   all 18 root profiles are live sources: **the edit lands in the root file**,
   the built copy is generated.
2. **Global snippets append to every built profile.** `overlays.sh` L17-19
   resolves `global_snippets` for every agent stem; L28-35 appends them; the
   root-added pass calls it (`build.sh` L90). So
   `build/grok/agents/grok-just-code.md` = root source + `token-frugal.txt` +
   `safety-guardrails.txt` + `repo-ownership.txt`. `overlays/manifest.json`
   agent_snippets touch only `mdu-code`, `grok-mdu-code`, `devops`,
   `grok-devops` — none of the 10 targets gets an agent snippet. Consequence:
   build pins assert clause **presence**, and the deploy `cmp` target is the
   **build copy**, not the root source.
3. **Base-sibling clause census (grep, `$WORKSPACE/grok/agents/` at HEAD).**
   `just-code.md` L24, `just-code-mid.md` L25, `just-code-pro.md` L23 carry
   the D5 coder clause; `qa.md` L24 (D1d) + L28 (D1c); `qa-pro.md` L14 (D1d)
   + L16 (D1c); `architect.md` L24 and `architect-premium.md` L21 (D1e);
   `code-reviewer-pro.md` L21 (D1b); `test-agent.md` L30 and
   `test-agent-pro.md` L29 (Dirty tree, D1a); `orchestrator.md` L103/L139-141
   /L222 (D5_ORCH, D4, D3, D2, D1). No other base grok profile carries any
   batch clause — `devops.md`, `devops-pro.md`, `ui-ux-designer.md`,
   `ui-ux-designer-pro.md`, `research.md`, `inception.md`, `introspector.md`
   are zero-hit (introspector's D6 lives in the base `prompts/` +
   `grok/agents/` introspector bodies, which have no overlay personal
   variant).
4. **Overlay clause census (grep, `$OVERLAY/grok/agents/`).** Only
   `grokestrator.md` (L103, L121-123, L167 — all five MDU-49 orchestrator
   clauses, landed by MDU-49) and `grok-test-agent.md` L17 /
   `grok-test-agent-pro.md` L16 (Dirty tree) carry anything. The 8 edit
   targets carry **zero** clauses. `$OVERLAY/overlays/prompts/qa.md` L18/L22
   already folds D1d + D1c (MDU-47 D2).
5. **D1a is shipped and already pinned for the test-agent family.** The base
   `tests/`
   `test_mdu_47_definition_batch.py` L201-227 pins `**Dirty tree:**` and
   `git stash clear` in the three base test-agent bodies **and** the two
   overlay root profiles (L210-211; `needs_overlay` gated per the mdu-35
   convention). MDU-54 makes no test-agent edit — the family is at full
   clause parity today.
6. **The overlay full-file trio has no base sibling.** Base `prompts/` is 12
   files (no `mdu-code.md`, no `thought-leadership-coach.md`); base
   `grok/agents/` has no `mdu-code` or `grok-mdu-code`. They are personal-only
   agents, not replacements of base same-name bodies — there is no
   "base carries it, overlay lags" parity relationship for them.
7. **The overlay prompt-regression wrapper evaluates the BASE tree.**
   `$OVERLAY/scripts/lib/prompt_regression.py` is a thin `os.execv` delegator
   (pinned by `test_mdu_09_overlay_prompt_regression.py` L90-136: a default
   run from the overlay cwd records the base repo as the evaluated root). All
   7 golden cases target base files (`prompts/orchestrator.md`,
   `grok/agents/` `orchestrator.md`, `prompts/just-code.md`) — MDU-54 touches
   no base file, so the gate is expected to exit 0 with the unchanged
   baseline (verify, do not assume; never `baseline --update`).
8. **No registry/config impact → no probe refresh.** `build.sh` L53-60 builds
   `build/opencode.json` from the base `opencode.json` + overlay MCP json +
   root `opencode.json` agents — Grok profiles are not inputs; Claude agents
   generate from the merged registry + `prompts/` (`build.sh` L62-65), not
   from Grok profiles. Grok-profile edits leave `build/opencode.json`
   byte-identical, so `config_sha256` is unchanged and the model-health gate
   is green WITHOUT `--refresh` (the gate still RUNS — `deploy.sh` L117-167
   refuses to install on red; a red gate with no config change is a STOP and
   an investigation, never an auto-refresh).
9. **The overlay owns no secret scanner by design** (mdu-44 rule, pinned by
   `test_mdu_11_overlay_secret_gate.py`; grep confirms no
   `scripts/lib/secret_scan.py` under `$OVERLAY`). The overlay commit uses the
   manual secret-scrub checklist over the staged diff, restricted to added
   lines (mdu-44 design precedent). Neither repo ships a
   `.pre-commit-config.yaml`; the base installs its secret-scan git hook via
   `scripts/`
   `install_secret_gate.sh`, and the base commit here is docs-only.
10. **Existing pins are additive-safe.** Overlay: `test_mdu_44` pins file
    presence (keep-list) — no file is added or removed;
    `test_mdu_30` pins registry permissions parsed from `opencode.json`, not
    profile bodies — body edits cannot disturb it. Base: the mdu-47 overlay
    pins (qa fold, test-agent Dirty tree) read files this MDU does not touch.
11. **The `grokestrator` is complete** (fact 4) and pinned by
    `$OVERLAY/tests/`
    `test_mdu_49_grokestrator_clauses.py` — out of scope, already done.
12. **No model-id assignments are made by this design** (mdu-53 precedent):
    executors are named by role + tier per the mdu-lifecycle table; nothing to
    design-time-probe. The deploy-time probe gate is config-driven (fact 8).

## 2. Scope table — every overlay Grok profile × clause applicability

"Action" values: **EDIT** (insert clause bytes), **VERIFY** (already present;
assert-only), **EXCLUDE** (no applicable clause / no parity relationship).
Every in-or-out claim cites the grep census (facts 3-6).

| Overlay file (`$OVERLAY/grok/agents/`) | Base sibling | Clauses base carries | Present in overlay | Action | Justification |
| --- | --- | --- | --- | --- | --- |
| `grok-just-code.md` | `just-code.md` | D5 coder (L24) | none | **EDIT** +D5 | MDU-49 follow-up L371 names it |
| `grok-just-code-mid.md` | `just-code-mid.md` | D5 coder (L25) | none | **EDIT** +D5 | same follow-up |
| `grok-just-code-pro.md` | `just-code-pro.md` | D5 coder (L23) | none | **EDIT** +D5 | same follow-up |
| `grok-qa.md` | `qa.md` | D1d (L24), D1c (L28) | none | **EDIT** +D1d +D1c | MDU-47 follow-up L493 names it |
| `grok-qa-pro.md` | `qa-pro.md` | D1d (L14), D1c (L16) | none | **EDIT** +D1d +D1c | same follow-up |
| `grok-architect.md` | `architect.md` | D1e (L24) | none | **EDIT** +D1e | same follow-up |
| `grok-architect-premium.md` | `architect-premium.md` | D1e (L21) | none | **EDIT** +D1e | same follow-up (mdu-47 included premium deliberately: path hygiene is tier-independent) |
| `grok-code-reviewer-pro.md` | `code-reviewer-pro.md` | D1b (L21) | none | **EDIT** +D1b | same follow-up (only the `-pro` reviewer variant exists in the overlay; base `code-reviewer.md` L27 also carries D1b but there is no overlay `grok-code-reviewer.md` file) |
| `grok-test-agent.md` | `test-agent.md` | D1a Dirty tree (L30) | Dirty tree L17 | **VERIFY** | named in L493, but MDU-47's own D1a ruling was verify-only; already present and pinned (fact 5) |
| `grok-test-agent-pro.md` | `test-agent-pro.md` | D1a Dirty tree (L29) | Dirty tree L16 | **VERIFY** | same |
| `grok-devops.md` | `devops.md` | none (zero-hit) | n/a | **EXCLUDE** | no clause applies to the devops role in either batch; nothing to mirror |
| `grok-devops-pro.md` | `devops-pro.md` | none (zero-hit) | n/a | **EXCLUDE** | same |
| `grok-ui-ux-designer.md` | `ui-ux-designer.md` | none (zero-hit) | n/a | **EXCLUDE** | same |
| `grok-ui-ux-designer-pro.md` | `ui-ux-designer-pro.md` | none (zero-hit) | n/a | **EXCLUDE** | same |
| `grok-research.md` | `research.md` | none (zero-hit) | n/a | **EXCLUDE** | same |
| `grok-deep-research.md` | *(none)* | n/a | n/a | **EXCLUDE** | personal-only agent, no base sibling (fact 6) — no parity relationship |
| `grok-plan.md` | *(none)* | n/a | n/a | **EXCLUDE** | no base sibling; the D1-D4 orchestrator clauses were scoped by MDU-49 to the three orchestrator mirrors only — extending them to a planner profile would be a new clause-surface decision, not parity |
| `grokestrator.md` | `orchestrator.md` | D1-D5 | all five (L103, L121-123, L167) | **EXCLUDE** | landed by MDU-49; pinned by the overlay mdu-49 test |

Overlay full-file dir (`$OVERLAY/overlays/grok/agents/`):

| File | Base sibling | Action | Justification |
| --- | --- | --- | --- |
| `grok-mdu-code.md` | *(none)* | **EXCLUDE** | personal-only coder, no base sibling (fact 6); D5's MDU-49 scope ruling named the just-code family only — extending D5 here would be a new surface decision and would also require the `overlays/prompts/` twin, which is `prompts/` territory (out of scope). Recorded as an open question (§12.2) |
| `mdu-code.md` | *(none)* | **EXCLUDE** | same reasoning; the OpenCode-side body is `$OVERLAY/overlays/prompts/` `mdu-code.md` |
| `thought-leadership-coach.md` | *(none)* | **EXCLUDE** | personal-only, non-engineering role; no batch clause applies |

Totals: **10 clause insertions across 8 files** (D5×3, D1d×2, D1c×2, D1e×2,
D1b×1) + 2 verify-only rows. No base definition edit, no `prompts/` edit, no
skill edit, no registry edit.

## 3. Clause texts (byte-identical to the base bodies at HEAD)

Precedence reconciliation: the MDU-47 D1b/D1c/D1d/D1e texts below are copied
verbatim from the live base `grok/agents/` carriers (fact 3 line cites), which
the base `tests/`
`test_mdu_47_definition_batch.py` pins — the MDU-49 batch did not reword any
of them (its D1/D2/D3/D4/D5/D6 are separate clauses; its only interaction with
MDU-47 text is that D5's sentence-3 referent "the run-ledger validation
discipline" became real when D1 landed). The base bodies are the authority;
the blockquotes match them byte-for-byte.

**D1b — 20261021-11 reviewer trace** (copy source: `$WORKSPACE/grok/agents/`
`code-reviewer-pro.md` L21):

> - When a mandated check verifies prompt TEXT (a clause, a gate, a fallback), trace it as a procedure, not a presence tick: in order, from the position of an agent in each repo variant (base and overlay), what does the text make you DO when the primary path is unavailable? A clause whose ordering sends the executing agent down the wrong branch fails the check even when every element is present. State the trace in one line per variant in the verdict.

**D1c — 20261021-11 QA copy** (two word swaps vs D1b; copy source: base
`qa.md` L28):

> When an acceptance criterion covers prompt TEXT (a clause, a gate, a fallback), trace it as a procedure, not a presence tick: in order, from the position of an agent in each repo variant (base and overlay), what does the text make you DO when the primary path is unavailable? A clause whose ordering sends the executing agent down the wrong branch fails the criterion even when every element is present. State the trace in one line per variant in the verdict.

**D1d — 20261021-8 denied-shell ladder, reworded** (copy source: base
`qa.md` L24):

> - **Denied shell:** If `shell` is permission-denied, make exactly ONE retry with the simple single-command wrapper form `timeout <n> <command>` — no pipes, no redirects, no command substitution (e.g. `timeout 120 python3 -m pytest -q`). If that is also denied, do not conclude that shell is unavailable and do not report BLOCKED for it: fall back immediately to file tools plus orchestrator-attached outputs, labelling the affected checks "verified via orchestrator-attached output".

**D1e — 20261030-5 path notation** (copy source: base `architect.md` L24):

> - In design docs, write file paths repo-relative, or as `$WORKSPACE/<subpath>` when a workspace-absolute reference is unavoidable — never as literal absolute paths (the secret-scan gate counts long absolute-path lexemes as secret-shaped and will red).

**D5 coder — 20261031-2 display integrity, coder shape** (copy source: base
`just-code.md` L24; identical in `just-code-mid.md` L25 and
`just-code-pro.md` L23):

> - An edit/write tool result that looks corrupted or unexpected (oldString mismatch, phantom content in the echoed result, truncated output) is UNTRUSTED until verified: grep or read the target file on disk and confirm the actual state before quoting the result anywhere — manifests, briefs, verdicts. Never propagate edit-result display text as truth.

**D1a — 20261017-1 Dirty-tree guard: NOT inserted.** MDU-47's D1a ruling was
verify-only (the guard shipped with MDU-24 and re-adding the entry text would
duplicate a pinned bullet). Both overlay test-agent profiles already carry it
(fact 5). Nothing to edit; the MDU-54 test adds local presence pins so the
overlay suite alone attests the family.

Shape note (mdu-47 erratum): D1c ships byte-identical **sentences**; only the
leading `- ` differs between bullet contexts (`qa-pro`) and paragraph contexts
(`qa`). Each file below uses the shape its base sibling uses.

## 4. Anchor table (verify each anchor by grep before editing)

| File | Clause(s) | Insert AFTER (exact anchor text; survey line) | Insert BEFORE | Emitted shape | Per-file notes |
| --- | --- | --- | --- | --- | --- |
| `grok-just-code.md` | D5 | `- Always verify your work: build, lint, test.` (L21, last line) | *(end of file — new last bullet)* | plain bullet `- ` + D5 text | base anchor's second half (`NEVER commit secrets`) does not exist in the personal variant — personal condensation, not a conflict; D5 becomes the final Hard-constraints bullet, same relative position as base L23→L24 |
| `grok-just-code-mid.md` | D5 | `- Always verify your work: build, lint, test.` (L19, last line) | *(end of file)* | plain bullet | same note; base sibling L24→L25 |
| `grok-just-code-pro.md` | D5 | `- Always verify your work: build, lint, test.` (L19, last line) | *(end of file)* | plain bullet | same note; base sibling L22→L23 |
| `grok-qa.md` | D1d then D1c | `- Still run non-browser checks you can and list what browser coverage was blocked.` (L26, last browser bullet) | `On FAIL, return complete report to orchestrator.` (L28) | D1d = bullet `- ` + full text incl. `**Denied shell:**` lead; D1c = paragraph, no lead; blank lines around both | mirrors base `qa.md` shape exactly (bullet L24, paragraph L28) and its relative order browser → D1d → D1c → On FAIL (base L20/L24/L28/L30) |
| `grok-qa-pro.md` | D1d, D1c | D1d: `- Design complex test scenarios for concurrent usage and failure modes.` (L11); D1c: `- Provide PASS or FAIL with detailed bug reports.` (L12) | D1d before the L12 bullet; D1c before `- **Be token efficient**: Depth of analysis over breadth of output.` (L13) | both bullets `- ` + sentence text | mirrors base `qa-pro.md` relative order (D1d L14 < Provide-PASS L15 < D1c L16 < token-efficient L17) — the two clauses bracket the Provide-PASS bullet exactly as the base sibling does |
| `grok-architect.md` | D1e | `- Design docs must be implementable by just-code and testable by test-agent.` (L19, last line) | *(end of file — new last bullet)* | plain bullet | base ruling "new last bullet of each Hard constraints block" (base `architect.md` L24 is the last bullet); overlay lacks the base's `Consider and document` bullet — D1e still lands as the final bullet |
| `grok-architect-premium.md` | D1e | `- Design docs must be precise enough for implementation and testing.` (L18, last line) | *(end of file)* | plain bullet | base sibling L21 is its last Hard-constraints bullet; premium included deliberately (tier-independent clause) |
| `grok-code-reviewer-pro.md` | D1b | `- Do not approve unresolved issues.` (L18, last line) | *(end of file — new last bullet)* | plain bullet | base sibling order is Read-only → Do-not-approve → Be-specific → D1b → Reserve-level (L18-L22); overlay keeps the shared prefix Read-only → Do-not-approve → D1b — relative order preserved; `Be specific` and `Reserve this level` are absent personal condensations |
| `grok-test-agent.md` | *(none)* | n/a | n/a | n/a | verify-only; Dirty tree bullet present at L17 |
| `grok-test-agent-pro.md` | *(none)* | n/a | n/a | n/a | verify-only; Dirty tree bullet present at L16 |

Conflict scan (required by the brief): **no personal delta textually
contradicts any clause to ship.** Closest call: `grok-qa.md` L22 / 
`grok-qa-pro.md` L22 mandate a **BLOCKED** status when Playwright is
unavailable, while D1d says "do not report BLOCKED for it" — these coexist
verbatim-adjacent in the base `qa.md` (browser-BLOCKED rule L16, D1d L24):
D1d's prohibition scopes to *shell denial* only, the browser rule is a
different domain and stays untouched. Resolution follows how MDU-47/49 divided
responsibility: ship both, byte-identical, no rewording of either.

## 5. Delta evidence — what the base sibling carries vs the overlay lag

Parity delta being closed (before → after):

| Role family | Base sibling carries (grep cite) | Overlay before | Overlay after |
| --- | --- | --- | --- |
| coder | D5 in `just-code.md` L24, `just-code-mid.md` L25, `just-code-pro.md` L23 | zero hits | D5 in all three `grok-just-code*` profiles |
| qa | D1d + D1c in `qa.md` L24/L28 and `qa-pro.md` L14/L16 | zero hits | D1d + D1c in both `grok-qa*` profiles |
| architect | D1e in `architect.md` L24, `architect-premium.md` L21 | zero hits | D1e in both `grok-architect*` profiles |
| reviewer | D1b in `code-reviewer-pro.md` L21 | zero hits | D1b in `grok-code-reviewer-pro.md` |
| test-agent | Dirty tree in `test-agent.md` L30, `test-agent-pro.md` L29 | already present (L17/L16) | unchanged — at parity |

The implementer copies clause text from the base sibling lines cited above
(they are byte-identical to §3) — no re-derivation.

**Scope-of-parity ruling (recorded explicitly):** this MDU closes the
**clause** parity gap only. The overlay personal profiles are condensed
variants that differ from their base siblings by more than the clauses (no
secrets block in the coder family, no Safety-constraints section, condensed
responsibilities, grok-specific frontmatter). Full-body sync is out of scope —
the deferral language in both backlog follow-ups is about the clauses
("the clauses landed in the base prompts, their `grok/agents/` mirrors, and
the overlay `qa` override only. Extend to those files … if parity is wanted").
After this MDU each overlay profile carries every clause its base sibling
carries; the remaining differences are the personal condensations listed
above, untouched.

## 6. Parity-verification test — `$OVERLAY/tests/`
`test_mdu_54_overlay_grok_clause_parity.py` (new; hermetic: repo reads only,
no network, no git state, no writes)

Follows the `test_mdu_49_grokestrator_clauses.py` pattern (full-clause
constants as the byte-identity authority; `test_mdu_47_overlay_qa_fold.py`
for the build-content pin):

1. **Full-clause constants** — `D1B_20261021_11`, `D1C_20261021_11`,
   `D1D_20261021_8` (with the `**Denied shell:**` lead), `D1E_20261030_5`,
   `D5_CODER_20261031_2` — hold the §3 texts verbatim. Emitted-form constants
   per file shape (e.g. `"- " + D5_CODER` for the coder family;
   `"- " + D1D` / bare `D1C` paragraph for `grok-qa.md`; both `- `-led for
   `grok-qa-pro.md`).
2. **Presence pins (non-vacuous, 20261031 rule).** Each scoped file's emitted
   clause form asserted `in` the file text with a failure message quoting the
   expected bytes (the mdu-49 `f"expected: {emitted!r}"` pattern — asserts
   emitted content, not just rc). 10 file-level assertions across the 8 edit
   targets + Dirty-tree pins (`**Dirty tree:**` and `git stash clear`) for the
   2 verify-only profiles (local coverage; the base mdu-47 pins are
   `needs_overlay`-gated and remain the cross-repo authority — additive, not
   conflicting).
3. **Ordering pins** (find()-position asserts): D5 follows
   `Always verify your work: build, lint, test.` in each coder profile;
   `grok-qa.md`: browser block < D1d < D1c < `On FAIL`;
   `grok-qa-pro.md`: D1d < `- Provide PASS or FAIL with detailed bug reports.`
   < D1c < the token-efficient bullet; D1e follows
   `NEVER write production code.` and its file's last pre-existing constraint
   bullet; D1b follows `- Do not approve unresolved issues.`
4. **Build-inheritance pins.** After `./build.sh`, each clause's emitted form
   present in `build/grok/agents/` `<same filename>` for all 8 edited profiles
   (mdu-44 precedent of asserting tracked build content; the built copy =
   source + appended global snippets, fact 2, so presence — not byte-equality
   with the root source — is the correct pin).
5. **Doc-consistency pins.** Each of the five constants must appear in this
   design doc (§3 blockquotes) — doc and test cannot drift (mdu-49 §11.2
   pattern). The doc lives in the base sibling: resolve via the
   `test_mdu_09` `_find_base()` sibling-resolution helper and skip with
   `needs_base` when the base is absent. Doc pins always read the real repo
   doc, never the mutation override.
6. **Mutation override (REQUIRED).** Resolve the profile-tree root through a
   helper honoring `MDU54_TEST_ROOT` (default: `$OVERLAY`); presence and
   ordering pins read through it; build and doc pins ignore it. This makes
   AC-6 executable without touching the working tree.

### Mutation-check protocol (test phase; `/tmp` copies ONLY — 20261017-1 guard)

The working tree holds uncommitted MDU edits; NEVER run git state commands
against it. For each of the five constants: copy `$OVERLAY/grok/agents/` to
`/tmp/opencode/mdu-54/mutation/grok/agents/`, strip that one clause from every
scoped file in the copy, then from the `$OVERLAY` root run

```sh
MDU54_TEST_ROOT=/tmp/opencode/mdu-54/mutation \
  timeout 120 python3 -m pytest tests/test_mdu_54_overlay_grok_clause_parity.py -q
```

and require: the stripped clause's presence + ordering pins FAIL with named
failures quoting the expected bytes; every other pin (incl. build, doc, and
Dirty-tree pins) stays green. Re-copy between rounds. Record the 5×FAIL matrix
in the test-phase note. (Precedent: mdu-49's `MDU49_TEST_ROOT` protocol and
`test_mdu_41_fallback_ladder.py` tmp-copy mutations.)

## 7. Gates plan (exact commands; devops/test-agent run, QA attests)

1. **Overlay build (idempotent):** from `$OVERLAY`:
   `timeout 300 ./build.sh` twice — green both times; it re-runs the base
   build, merges overlays, root-adds the profiles, generates Claude agents,
   and validates via the BASE validator (`scripts/build.sh` L123 calls
   `$WORKSPACE/scripts/lib/validate.py` on the build; the overlay
   `scripts/lib/validate.py` is the thin re-exec — do not fork it).
2. **Overlay suite:** from `$OVERLAY`:
   `timeout 300 python3 -m pytest tests/ -q` — green including the new
   `test_mdu_54_overlay_grok_clause_parity.py`; all pre-existing overlay pins
   unaffected (additive only, fact 10). Suite size at design time ~210+
   (re-verify at test time).
3. **Base suite (docs-only change, still verify):** from `$WORKSPACE`:
   `timeout 300 python3 -m pytest tests/ -q` — green; no base definition
   changed.
4. **Prompt-change protocol** (the overlay commit touches `grok/agents/`, so
   the grokestrator's commit-gate clause applies). Snapshot → edit → snapshot
   → diff, run from the `$OVERLAY` root (the wrapper delegates to the base
   gate, which evaluates the BASE tree — fact 7):

   ```sh
   timeout 120 python3 scripts/lib/prompt_regression.py snapshot --out /tmp/opencode/mdu-54/before.json
   # ... edit the 8 profiles ...
   timeout 120 python3 scripts/lib/prompt_regression.py snapshot --out /tmp/opencode/mdu-54/after.json
   timeout 120 python3 scripts/lib/prompt_regression.py diff \
     --before /tmp/opencode/mdu-54/before.json \
     --after  /tmp/opencode/mdu-54/after.json
   ```

   Exit semantics per `$WORKSPACE/evals/README.md` L171-176: `0` clean;
   `1` ≥1 golden case regressed — reject the edit, fix the hunk, repeat, never
   weaken the case; `2` operational — stop and investigate. Expected result:
   exit 0, 7/7 unchanged baseline (no case targets any overlay file; no
   `cases.json` or `baseline.json` edit; `baseline --update` must NOT run).
   Commit-time gate: `timeout 120 python3 scripts/lib/prompt_regression.py gate`
   — exit 0 required.
5. **Probe gate:** no `opencode.json` / registry change (fact 8) →
   **no `--refresh` needed**. Verify green, do not assume:
   `./deploy.sh --force` runs it automatically (red = refuse to install);
   explicit form from `$OVERLAY`:
   `timeout 300 python3 ../open-agent-definitions/scripts/lib/probe_models.py --gate --config build/opencode.json --report config/model-probe-report.json`
   (the `deploy.sh` L22-23 documented form). If it reds with no config change,
   STOP and investigate — never auto-refresh to force green.
6. **Deploy + installed==build:** from `$OVERLAY`: `./deploy.sh` (dry run)
   clean, then `./deploy.sh --force`. Then `cmp` each of the 10 scoped
   profiles: `cmp build/grok/agents/<name>.md ~/.grok/agents/<name>.md` —
   byte-identical (the build copy, snippets included, is the deployed truth,
   fact 2). OpenCode and Claude surfaces are unaffected (no prompt or registry
   input changed), but the dry-run output is checked for unexpected
   diff reports.
7. **Secret gate:** overlay owns no scanner (fact 9) — manual secret-scrub
   checklist over the **staged diff, added lines only** (the 8 profile hunks,
   the new test file, the regenerated `build/` copies): AWS `AKIA…`, GitHub
   `ghp_`/`gho_`, Stripe `sk_live_`, Slack `xoxb_`, PEM blocks, unexplained
   high-entropy strings. Record the result in the run notes. The base commit
   is docs-only; the base hook scans it and is expected green.

## 8. Books

- `$WORKSPACE/FEATURE_BACKLOG.md` — new `### MDU-54` entry in the Queue
  section (after MDU-53), field set copied from the MDU-49 entry (Why /
  Description / Acceptance criteria / Suggested agents / Dependencies /
  Follow-up / Status filled at commit). The entry records both deferrals
  closed (L371, L493), the verify-only outcome for the test-agent family, and
  the exclusions of §2 with their evidence.
- This design doc (already in `$WORKSPACE/docs/design/`).
- No `docs/brief-checklist.md` rows — every clause shipped here already has
  its checklist row from MDU-47/49; this MDU is parity extension only.
- No `tests/README.md` row — MDU-54 adds no base test file; the overlay test
  has no overlay tests README (mdu-49 precedent: recorded in the backlog
  entry instead).

## 9. Acceptance criteria

1. **AC-1 suites:** overlay suite green incl. the new test; base suite green
   (docs-only); both builds idempotent; all pre-existing pins in both repos
   unaffected — additive only.
2. **AC-2 byte-identity:** all 10 insertions byte-match §3 (the test's
   full-clause constants are the authority; doc-consistency pins keep doc ==
   test; snapshot/diff evidence attached to the review and validate briefs).
3. **AC-3 golden + secret gates:** prompt-regression gate exit 0 with the
   unchanged 7/7 baseline on the overlay commit (no cases.json/baseline.json
   edit); manual secret-scrub checklist recorded; base docs commit gate-clean.
4. **AC-4 probe gate:** green WITHOUT `--refresh` (no registry change; if
   red, stopped and investigated — the run record shows the verification).
5. **AC-5 ordering:** every §6.3 ordering pin green (per the §4 anchor
   neighborhoods).
6. **AC-6 mutation:** the 5×FAIL matrix from `/tmp` copies recorded in the
   test-phase note; zero git state commands against the working tree.
7. **AC-7 deployed == build:** `cmp` byte-identical for all 10 scoped
   profiles under `~/.grok/agents/`.
8. **AC-8 books:** base commit = this doc + the MDU-54 backlog entry; overlay
   commit = 8 profile edits + the new test + regenerated tracked `build/`.
9. **AC-9 attestation:** QA attests it validated the exact final manifest
   path (20261014-5 protocol); the run dogfoods D1 (manifest finalized and
   validated before QA dispatch) and D3 (routing checked against allowlists
   at design time).

## 10. Who executes / who grades

| # | Phase | Scope | Who executes (tier) | Who grades |
| --- | --- | --- | --- | --- |
| 1 | design | this doc | architect (premium) — done | code-reviewer (static trace) + qa |
| 2 | implement | 8 profile edits + test file, snapshot/diff protocol | just-code (mid) | code-reviewer + test-agent |
| 3 | review | static trace of anchors/bytes vs §3-§4 | code-reviewer (mid) | orchestrator |
| 4 | test | suites ×2 repos, mutation matrix in `/tmp` | test-agent (mid) | qa + orchestrator |
| 5 | deploy | builds ×2, deploy dry-run/`--force`, `cmp`, probe gate | devops (mid) | qa |
| 6 | validate | file inspection of the 10 profiles vs §2-§4 | qa (mid) | orchestrator |
| 7 | introspect | session signals + file-tool greps | introspector (budget) | orchestrator |
| 8 | commit | gates + git commit/push, base first then overlay | orchestrator | user (push visibility) |

No model-id assignments are made by this design; tier selection follows the
mdu-lifecycle table (mdu-53 precedent — nothing to design-time-probe). Loop
order per the standard phase sequence; any fix cycle re-runs the affected
suite and both builds (20261021-6). Reviewer and qa are read-only by design
(D3): every command in §7 is executed by devops, test-agent, or the
orchestrator; gate outputs are pre-attached to the gate-bearing briefs.

## 11. Manifest discipline (implementer notes)

- Manifest: `runs/mdu-54-overlay-grok-personal-variant-parity/`
  `manifest.json` (base-repo-root relative; `runs/` is gitignored — a run
  artifact, never committed). **Whole-file rewrites only, never
  edit-anchored**, contents per the inline run-ledger contract
  (`scripts/lib/` `run_ledger.py`; schema inlined by MDU-15, cross-CLI
  conformance driven by `evals/tasks/` `03-ledger-conformance`).
- Per D1: before QA dispatch the manifest has all completed phases, the
  verification block, a summary and `completed_at`;
  `timeout 60 python3 scripts/lib/run_ledger.py validate runs/mdu-54-overlay-grok-personal-variant-parity/manifest.json`
  exits 0 (run from `$WORKSPACE`); the exact manifest path is passed to QA and
  QA validates it; after QA only `qa_grade` flips and the validator re-runs.
- The manifest's verification block records the exact commands from §6/§7
  (suite invocations, mutation-matrix command, build/deploy/gate commands,
  `cmp` list) with their exit codes, so QA can attest against the record
  rather than re-deriving the protocol.
- Per D5: any edit/write tool result that looks corrupted is verified on disk
  before being quoted in the manifest or a brief.

## 12. Open questions / risks

1. **Anchor drift risk:** 8 files × short anchors; the implementer greps each
   §4 anchor text before editing (line numbers are survey-time only). A
   missed anchor costs a fix cycle — the §6 presence pins catch it
   immediately.
2. **`grok-mdu-code` / `mdu-code` D5 extension (excluded, §2):** if the user
   wants the personal monorepo coder to carry the D5 coder clause, that is a
   separate user-approved MDU covering BOTH the Grok profile and its
   `overlays/prompts/` twin (a fold, MDU-47-D2-style) — recorded here so the
   exclusion is a decision, not an oversight.
3. **`grok-plan` orchestrator-clause extension (excluded, §2):** same shape —
   a new-surface decision, not parity; queue separately if wanted.
4. **Verify-only rows could rot silently:** the base mdu-47 pins are
   `needs_overlay`-gated (skipped in a standalone base clone); the new overlay
   pins close that gap by pinning the two profiles in the overlay suite where
   the files always exist.
5. **Full-body sync temptation:** §5's scope ruling is deliberate — if the
   user later wants the personal profiles to be true base+delta mirrors
   (secrets block, Safety constraints, etc.), that is a separate MDU with its
   own anchor survey; do not let an implementer "helpfully" expand the diff.
