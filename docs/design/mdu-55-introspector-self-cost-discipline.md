# MDU-55 · Introspector self-cost discipline

Codifies suggestion `20261102-2` (warn, target: introspector, kind: token_hotspot). Root causes: (a) the loop-mode pass re-reads the ever-growing `agent-improvements.md` in full instead of grepping the open `[ ]` ids and reading only those blocks; (b) the signal script runs at pass start, so the pass's own token/long_context/stall signals are captured mid-pass and structurally under-report (the mdu-51 record claimed "no long_context" — true only for the pre-script window). Done: both introspector mirrors carry one new loop-mode sub-bullet — grep the open ids, read only those sections, targeted edits only, one script run, 140k wrap-up — byte-identically; SKILL.md documents the run-timing capture window; a new pin test holds all of it; the suggestion flips to resolved pending the first post-deploy live exercise. No registry, model, evals, or script change ships.

`$WORKSPACE` = base repo root (`open-agent-definitions`), `$OVERLAY` = overlay repo root (`opencode_agents`, sibling). Line numbers are survey-time (2026-11-10); **anchor text is authoritative** — the implementer greps every anchor before editing.

## 0. Scope — files surveyed (exactly)

Reads (in place): `prompts/introspector.md` full (70 ln); `grok/agents/introspector.md` full (76 ln; body identical to the OpenCode mirror plus frontmatter, `model: grok-4.7`); `skills/session-introspect/SKILL.md` full (150 ln); `tests/test_mdu_49_definition_batch.py` + `tests/test_mdu_47_definition_batch.py` full (pin/test shape authority); `tests/test_mdu_51_v2_text_extraction.py` L718-762; `tests/test_mdu_43_hygiene.py` L125-154; `docs/design/mdu-49-definition-batch-3.md` L414-458 + headings; `docs/design/mdu-54-overlay-grok-personal-variant-parity.md` L1-60 + headings; `.gitignore` full.

Grep-only: `docs/design/` census; `scripts/lib/` CLI shapes (prompt_regression, secret_scan, run_ledger); `evals/` "introspector" (zero hits); `tests/` pin census (introspector, SKILL.md, README/backlog); `$OVERLAY/tests/` build-copy + sibling-source pins; `agent-improvements.md` existence at both roots only (**not read** — carry 20261024-1; the §7 flip is executed grep-first by the implementer).

Change set, behavior-carrying (the 4-file ceiling): two mirrors, `skills/session-introspect/SKILL.md`, one new test file. Books (§8), the flip (§7), the manifest (§10) are bookkeeping.

## 1. Verified facts that shape the design

1. Mirror bodies are byte-identical modulo grok frontmatter; read bullet at `prompts/introspector.md` L13 / `grok/agents/introspector.md` L19, manifest bullet after it (L14 / L20).
2. No test pins adjacency between the read and manifest bullets; the only introspector-body pins are mdu-49's D6 ordering (Update < D6 < Also-write) and mdu-41's session-id sentence — both outside the insertion window.
3. Only test_mdu_51 reads this SKILL.md (v2 permission-UNKNOWN block — untouched by §4); no line-count pins exist.
4. Base `.gitignore` ignores `build/` and `/runs/`; overlay `build/` is tracked, so the overlay commit carries regenerated build copies.
5. Zero evals cases reference the introspector prompt → the prompt-regression gate cannot red from this edit; mdu-49 precedent: snapshot/diff, gate green on the unchanged baseline, no refresh, any case delta is reject-and-fix.
6. Overlay tests pin the *built* introspector copy and read base sibling sources directly → overlay validation = `./build.sh` then overlay suite; no overlay source edit.
7. `agent-improvements.md` exists at both roots, not base-gitignored; the `20261102-2` block is expected at the base root (mdu-51 ran on base-repo work); implementer greps, reads only that block, checks `git ls-files` for commit eligibility.
8. No meta-test enforces tests/README or backlog coverage; test_mdu_45 enforces exactly one `- **Status:**` line per backlog section present; test_mdu_46 pins the `## introspector` checklist section exists (untouched — §8 adds no row).
9. `run_ledger.py` PHASES = design, implement, review, test, deploy, validate, commit; CLI `run_ledger.py validate <manifest.json>`.
10. No machine-verifiable live probe of introspector behavior exists in-tree (it is an agent prompt) — acceptance is static pins + suites + gates; the flip is scoped pending live exercise (§7).

## 2. D1 — reading-discipline sub-bullet (clause + insertion)

Emitted line, byte-identical in BOTH mirrors, one physical line, inserted immediately after the read bullet, before the manifest bullet:

```markdown
  - Read `agent-improvements.md` once at the start — grep for the open `[ ]` suggestion ids and read only those sections, not the whole file — and update it by targeted section edits; never re-read the full file after the first pass. Run the signal script once at the start; if your own prompt context approaches 140,000 tokens, stop gathering evidence and write the report from the notes you already have.
```

Pin constant (emitted line minus its `  - ` lead; also the doc-consistency blockquote):

> Read `agent-improvements.md` once at the start — grep for the open `[ ]` suggestion ids and read only those sections, not the whole file — and update it by targeted section edits; never re-read the full file after the first pass. Run the signal script once at the start; if your own prompt context approaches 140,000 tokens, stop gathering evidence and write the report from the notes you already have.

- One normalization from the suggestion's definition-change text: backticks around the filename (house style); every other byte identical.
- Sub-bullet, not appended sentences on the parent: keeps the parent bullet byte-stable (pinned, §5 test 5), attaches the discipline to the act it disciplines, gives the clause its own line for the parity pin (mdu-49 D1 pattern).
- Anchors (unique per body, loop mode): parent `- Read \`agent-improvements.md\` at the project root if it exists.`; following `- Read \`runs/<mdu-id>/manifest.json\` if the orchestrator passed an MDU id.`

## 3. D2 — the 140k wrap-up sentence placement (ruling)

Ships as the second sentence of the SAME loop-mode sub-bullet (§2), NOT a Hard constraints bullet, because: (1) it is conditional pass procedure ("stop gathering evidence and write the report from the notes you already have") — meaningless in review mode; (2) its threshold family already lives in loop mode (the cost bullet's 140000/200000 long_context thresholds) — same number, same neighborhood; (3) Hard/Safety constraints hold unconditional terse limits (never-edit, step cap) — a two-sentence conditional there breaks section shape and forks the number; (4) one passage = one pin = verbatim traceability to the suggestion (D6 grep discipline closes on clause text found in the file); (5) mdu-49 shipped multi-sentence procedural sub-bullets in loop procedure, and the mdu-53/54 standing carry carried all elements as one item.

Standing-carry coverage (mdu-53/54 briefs → clause): grep open `- [ ]` ids ✓; read only those blocks ✓; one script run at start ✓; no full re-read between edits ✓ ("never re-read the full file after the first pass"); wrap up before 140k ✓.

## 4. D3 — SKILL.md run-timing note

New subsection at the END of `## How to run the helper` — after the `--session-id` paragraph (survey L97-103), immediately before `## Signal kinds` (survey L105). Exact bytes (heading + wrapped body):

```markdown
### Run timing and the pass's own signals

The script runs at pass start, so the introspector's own token, long_context, and
stall signals are captured mid-pass and structurally under-report — a closing
re-run (or an orchestrator-side run after the pass) is needed to see them. A pass
record that claims no long_context is describing only the pre-script window;
check a closing run before treating the pass's own cost as clean.
```

- Not under `## Hard rule` (the suggestion's other guess): Hard rule is the suggest-don't-edit contract; this is an output-interpretation caveat about *when the run happens*, so it sits with run semantics, directly before the signal-kind list it qualifies. Not under `## When to run`: that lists invocation triggers; the note is about the capture window of a run already made.
- Near-verbatim from the suggestion; the final sentence records the mdu-51 lesson. No script change — documentation only (§8).

## 5. D4 — pin tests: `tests/test_mdu_55_introspector_discipline.py` (new)

Hermetic: repo reads only, no network, no git state, no writes. Constants are the byte-identity authority (mdu-49 convention): `D1_20261102_2` (§2 blockquote verbatim), `SKILL_NOTE_BODY` (§4 wrapped body, 5 lines, exact), `SKILL_NOTE_HEADING`. Base-file paths resolve through an `MDU55_TEST_ROOT` env override (default the real repo) for the mutation matrix; doc-consistency pins always read the real repo doc.

| # | Test | Cases |
| --- | --- | --- |
| 1 | `test_subbullet_present_exactly_once_in_each_mirror` — emitted line in text, count == 1 | 2 |
| 2 | `test_subbullet_line_byte_identical_across_mirrors` — mdu-49 `_line_containing` parity | 1 |
| 3 | `test_constant_matches_design_doc` — D1 clause, note body, note heading each verbatim in this doc | 3 |
| 4 | `test_subbullet_between_read_parent_and_manifest_bullet` — parent < sub-bullet < manifest bullet, per mirror | 2 |
| 5 | `test_read_parent_bullet_unchanged` — parent anchor still verbatim, per mirror | 2 |
| 6 | `test_skill_note_heading_once_and_body_present` — heading count == 1, body in text | 1 |
| 7 | `test_skill_note_between_howto_and_signal_kinds` — `## How to run the helper` < heading < `## Signal kinds` | 1 |

12 cases total. Non-vacuity: 4/5/7 pin position against pre-existing anchors (not the clause's own words); 2 pins cross-mirror parity; 3 pins doc == test; 1/6 pin presence with uniqueness. No per-sentence substring pins inside the already-byte-pinned line (tautological). Expected counts: new file collects exactly 12; base total = last-recorded 813 + 12 = **825 expected** (record actuals in the manifest; AC grades green + exact 12, not the absolute total); overlay count unchanged (last recorded 269).

Mutation matrix (test phase; `/tmp/opencode/mdu-55/mutation` copies ONLY — 20261017-1 guard): (a) sub-bullet stripped from one mirror copy → tests 1, 2, 4 red; (b) note stripped from the SKILL.md copy → tests 6, 7 red; doc-consistency stays green (reads the real repo). `MDU55_TEST_ROOT=/tmp/opencode/mdu-55/mutation timeout 120 python3 -m pytest tests/test_mdu_55_introspector_discipline.py -q`.

## 6. D5 — overlay validation + no-deploy ruling

- Overlay validation: YES (mdu-54 shape). `$WORKSPACE`: `./build.sh` twice (idempotent, byte-stable). `$OVERLAY`: `./build.sh` (its step 1 re-runs the base build), then the overlay suite. A pre-build overlay red on base-source↔built-copy pins is the expected "run ./build.sh first" trigger, not a failure.
- Overlay commit: regenerated `build/` copies (tracked) in one small overlay commit with the mdu-55 id; two commits, two pushes, repos never mixed; no overlay source edit.
- Deploy: NONE — `deploy.sh` is not run. Acceptance is static (fact 10) and verified at source + build-copy level; prompt-text-only change to one consumer agent; mdu-49/54 deployed because those batches changed loop-facing orchestrator bodies with installed-parity in scope; a mid-session swap of the running session's own agent set is risk without verification payoff. Installed trees refresh at the next routine deploy — §7's pending-live-exercise scope accounts for that. Optional add-on, NOT an AC: `./deploy.sh --force` from `$OVERLAY` after AC-6 if the user wants the next pass on the new clauses.

## 7. D6 — suggestion `20261102-2` flip (implementation phase)

Decision: FLIP to resolved, scoped pending live exercise — one targeted block edit during implementation.

- Locate grep-first (this MDU's discipline applied to itself): `grep -n "20261102-2" agent-improvements.md` at `$WORKSPACE` root (expected home; fallback the same grep at `$OVERLAY`); read ONLY the matched block.
- Edit: `- [ ]` → `- [x]` on that line; evidence / definition-change / apply-now lines untouched; append one resolution sub-line (floor wording — mirror the log's closure field style, e.g. the 20261017-1 closure, if it differs):
  `  - resolution (mdu-55, 2026-11-10): clause shipped byte-identical in both introspector mirrors (one-script-run reading discipline + 140k wrap-up) plus the SKILL.md run-timing note; pinned by the mdu-55 test file. No live pass has run under the clauses yet — resolved pending the first post-deploy introspection pass; re-open with that record as evidence if it still shows a full-file re-read, a second full read, or a mid-pass-only signal capture.`
- Commit: if `git ls-files --error-unmatch agent-improvements.md` succeeds, the flip ships in the base commit; if untracked, working-tree bookkeeping — attested in the manifest either way.
- Why flip now vs keep open with a "clause shipped" note: the shipped + pinned clause is exactly the mdu-49 D6 "clause present → close or re-scope" case; an open suggestion whose ask is verifiably in-tree forces the next pass to spend tokens re-verifying it — the very cost this MDU removes. The pending-live-exercise scope plus explicit re-open trigger preserves the honesty the keep-open option would buy.

## 8. D7 — books + explicitly out of scope

Books (convention; no test depends on them — first to drop if the orchestrator enforces the literal 4-file ceiling): `tests/README.md` one row for the new file (mdu-49 row format); `FEATURE_BACKLOG.md` one `### MDU-55` Queue entry with exactly one `- **Status:**` line (test_mdu_45 shape), Status filled at commit. NO `docs/brief-checklist.md` row: introspector self-cost discipline is agent self-discipline, not brief content (mdu-49 D4 no-row precedent); the definition + pins carry it.

Out of scope (do not touch): `20261104-1` duplicate-id fix; `20261030-5` scanner path exemption; evaluator and `session_signals.py` changes (§4 documents capture-window semantics, it does not edit the script); `opencode.json`, registry, any model id; evals `cases.json` / `evals/golden/baseline.json`; orchestrator prompts; whole-body mirror-parity tests (broader than this MDU — per-clause pins are the house pattern); `agent-improvements.md` restructuring or curation (the clause fixes how the log is read, not its growth — a still-large post-deploy pass is a new suggestion with fresh evidence).

## 9. Gates plan (exact commands)

```bash
# $WORKSPACE — snapshot BEFORE the edit, gate AFTER
timeout 120 python3 scripts/lib/prompt_regression.py snapshot --out /tmp/opencode/mdu-55/before.json
timeout 120 python3 scripts/lib/prompt_regression.py snapshot --out /tmp/opencode/mdu-55/after.json
timeout 120 python3 scripts/lib/prompt_regression.py diff /tmp/opencode/mdu-55/before.json /tmp/opencode/mdu-55/after.json
timeout 60 python3 scripts/lib/prompt_regression.py gate                       # exit 0, unchanged baseline, NO refresh
timeout 60 python3 -m pytest tests/test_mdu_55_introspector_discipline.py --collect-only -q   # 12 cases
timeout 300 python3 -m pytest tests/ -q
./build.sh && ./build.sh                                                       # idempotent, byte-stable
timeout 60 python3 scripts/lib/secret_scan.py --staged                         # clean (or --paths over changed files)
timeout 60 python3 scripts/lib/run_ledger.py validate runs/mdu-55-introspector-self-cost-discipline/manifest.json
# $OVERLAY
./build.sh
timeout 300 python3 -m pytest tests/ -q                                        # green, count unchanged
```

Any gate red is reject-and-fix; no gate is forced green by refreshing state. The overlay commit uses the secret-scrub checklist fallback (the overlay has no scanner script).

## 10. Manifest discipline

`runs/mdu-55-introspector-self-cost-discipline/manifest.json`: phases actually executed (design, implement, review, test, validate, commit); deploy intentionally not run — record the §6 ruling in the summary, and if the validator flags a missing phase record it as skipped with the ruling rather than inventing a run. All completed phases, verification block, summary, `completed_at` present; validator exit 0 BEFORE QA dispatch; after QA only `qa_grade` flips (mdu-49 D1). Record actual before/after suite counts and the mutation result.

## 11. Acceptance criteria

- **AC-1 Base suite green** incl. the new file; collect-only exactly 12 cases; total = prior + 12 (expected 825 from last-recorded 813; actuals in the manifest).
- **AC-2 Mutation matrix** reds only the new file's pins, `/tmp` copies only, under `MDU55_TEST_ROOT` (strips: mirror sub-bullet; SKILL note).
- **AC-3 Prompt regression** gate exit 0 on the unchanged baseline; snapshot/diff shows no case delta; no `cases.json`/`baseline.json` edit.
- **AC-4 Byte-identity** sub-bullet line byte-identical across both mirrors, exactly once each, between the read parent and the manifest bullet; parent bullet byte-unchanged.
- **AC-5 SKILL.md** note heading (once) + wrapped body verbatim, between `## How to run the helper` and `## Signal kinds`; the existing test_mdu_51 SKILL pin stays green (covered by AC-1; called out because it reads this file).
- **AC-6 Overlay** `./build.sh` from `$OVERLAY` regenerates build copies; overlay suite green, count unchanged (last recorded 269); no overlay source edit; overlay build-copy diff committed as its own commit.
- **AC-7 Secret scan** clean at commit time (base staged scan; overlay checklist fallback).
- **AC-8 Run ledger** manifest finalized, validator exit 0 before QA dispatch; after QA only `qa_grade` changes.
- **AC-9 Suggestion flip** `20261102-2` → `- [x]` with the §7 resolution line (grep-located, one block edit); committed if the log is tracked; attested in the manifest either way; scoped "resolved pending first post-deploy live exercise" with the re-open trigger recorded.
- **AC-10 Books** tests/README row + `### MDU-55` backlog entry (exactly one Status line); no brief-checklist row added.
- **AC-11 No deploy** no `deploy.sh` run; installed trees untouched (§6); the optional force-deploy add-on is NOT graded.
- **AC-12 Scope ceiling** no `opencode.json`/registry/model change; no evals edit; `20261104-1`, `20261030-5`, evaluator and script logic untouched.

## 12. Who executes / who grades

Design: architect (this doc). Implement: mdu-code (mid tier) — 4-file change + flip + books. Review: code-reviewer (mid). Test: test-agent (mid) — new file, mutation matrix, suites. Validate/QA: qa (mid) — gates + manifest attestation. Commit: orchestrator (base commit, then overlay build-copy commit; two pushes). Model tier per the mdu-lifecycle decision table; this design assigns no model id and changes no registry row, so no model probe is triggered.

## 13. Open questions / risks

- The suggestion block's real shape may differ from the §7 floor wording — adapt the resolution line to the log's closure style, keeping the semantics (shipped + pinned + pending live exercise + re-open trigger).
- Suite totals may have drifted from the last recorded 813/269 — AC-1/AC-6 grade on green + exact 12 / unchanged overlay count, with actuals in the manifest.
- Byte drift between doc, test constants, and files reds the doc-consistency and parity pins immediately — that is the pins working; copy the constant, do not reword.
