# MDU-57 · Form-denial retry discipline

Codifies suggestion `20261110-1` (warn, target: introspector + qa, kind: repeated_tool_error / permission family). Root cause: the mdu-30 allowlist works when the command form is plain, but the plain-form rule lived only in closed-suggestion notes — each new introspector/QA pass re-learns it, misreads by-design denials as lockouts, and improvises ad-hoc probe workarounds (mdu-55: 14 shell tool errors + a sed -i probe workaround, still graded PASS round 1). Done: two clause families land byte-identically — an introspector plain-form retry sub-bullet (both mirrors), a QA denial-as-form-event bullet (6 carriers: 3 base + the overlay full-file override + 2 overlay-root Grok profiles) — plus two brief-checklist lines (the orchestrator-side apply-now half), one new pin test file, regenerated builds. No registry, evals, script, validator, or baseline change ships.

`$WORKSPACE` = base repo root (`open-agent-definitions`); `$OVERLAY` = overlay repo root (`opencode_agents`, sibling). Line numbers are survey-time (2026-11-10); **anchor text is authoritative** — the implementer greps every anchor before editing.

## 0. Scope and non-goals

**Scope (prompt bodies + one doc + one test file):**
- Clause A (introspector plain-form retry): base `prompts/introspector.md` + base `grok/agents/introspector.md` — 1 insertion each.
- Clause B (QA denial-as-form-event): base `prompts/qa.md`, base `grok/agents/qa.md`, base `grok/agents/qa-pro.md`, OVERLAY full-file `overlays/prompts/qa.md`, plus OVERLAY-ROOT `grok/agents/grok-qa.md` and `grok/agents/grok-qa-pro.md` — 1 insertion each (6 carriers total).
- Clause C (brief-side lines): `docs/brief-checklist.md` — 2 lines.
- Pins: one new base test file (name below).
- Books: FEATURE_BACKLOG row, the `20261110-1` flip in `agent-improvements.md` (grep-first, implementer), run manifest.

**Non-goals:** no `opencode.json` changes; no registry/model changes; no probe/evals changes (evals reference neither the introspector nor the qa prompt — grep-verified, so the prompt-regression gate cannot red from these edits); no validator changes; no prompt-regression baseline refresh; no SKILL.md edit (considered, rejected — §2); no new overlay-repo test file (mdu-47 precedent: overlay source pinned from the base suite).

## 1. Verified facts that shape the design

1. Introspector mirrors are byte-identical modulo grok frontmatter; the script bullet ends with the `--cwd`/`--session-id` pass line (base L12 / grok L18), followed by the read parent `- Read \`agent-improvements.md\`...` (L13 / L19).
2. The only introspector-body pins are mdu-49's D6 ordering (Update < D6 < Also-write, all at L22+) and mdu-55's parent < sub-bullet < manifest window (L13–L15) — all strict `find()` inequalities; inserting clause A inside the script bullet (above L13) breaks none, and no pin asserts adjacency between the pass line and the read parent.
3. The D1d denied-shell bullet (20261021-8, mdu-47/mdu-54 shape) is byte-identical in all SIX QA carriers: base `prompts/qa.md:18`, base `grok/agents/qa.md:24`, base `grok/agents/qa-pro.md:14`, overlay `overlays/prompts/qa.md:18`, overlay-root `grok/agents/grok-qa.md:28`, overlay-root `grok/agents/grok-qa-pro.md:12`. There is no `prompts/qa-pro.md` — qa-pro exists only as a grok profile, so OpenCode has no qa-pro carrier. The two overlay-root `grok-qa*` files are root-ADDED sources (no base same-name file: the base carries `qa.md`/`qa-pro.md`, the overlay root carries `grok-qa.md`/`grok-qa-pro.md`), which build step 4 promotes add-if-absent and `deploy.sh` installs into the Grok harness — they are LIVE carriers, not dead same-name copies.
4. Overlay `overlays/prompts/qa.md` is a full-file override: snippets are NOT re-applied to it, so clause B must be edited into the full file itself (mdu-54 D2 lesson).
5. Overlay-repo order pins (`test_mdu_54_overlay_grok_clause_parity.py` tests 182/200) assert browser < D1d < trace < On FAIL and D1d < Provide-PASS < D1c < token-efficient as strict positions on the BUILT profiles — inserting clause B immediately after D1d keeps every inequality true.
6. `docs/brief-checklist.md` is a doc, not a prompt source; it is the standing carrier for brief-side apply-now items (mdu-46). Its `## qa` section already carries the 20261021-8 denial line; `## introspector` is the file's last section.
7. mdu-47's `@needs_overlay` gate pins the sibling overlay source from the base suite; base `build/` is gitignored (no base build pins — mdu-55 precedent), overlay `build/` is tracked (regenerated + committed).

## 2. D1 — Clause A: introspector plain-form retry (sub-bullet)

Emitted line, byte-identical in BOTH mirrors, one physical line, two-space-indent sub-bullet inserted at the END of the script bullet (immediately after the pass line, before the read parent):

```markdown
  - Shell denials under the deny-first wall are command-form-specific: before recording 'shell denied / signals UNKNOWN', retry ONCE in the plain allowlisted form (`timeout N python3 <script>`; no compounds, pipes, or redirects) — bare `echo`/`pwd` and compound forms are denied BY DESIGN and are not evidence of a lockout.
```

- Text is the suggestion's definition change verbatim (zero normalization needed).
- Sub-bullet under the script parent, mdu-55 D1 precedent: attaches the discipline to the act it disciplines, keeps the parent bullet and the pass line byte-stable, gives the clause its own line for the parity pin.
- Loop-mode placement is correct: review mode never runs the script.
- SKILL.md note REJECTED: the skill documents the script's flags and output, not the agent's shell-invocation permission form; the mirrors are where the retry rule is read at the moment of denial. Keeps the change set at the mdu-47 shape.

## 3. D2 — Clause B: QA denial-as-form-event (bullet after D1d)

Emitted line, byte-identical in ALL SIX QA carriers, standalone `- ` bullet:

```markdown
- **Denied probes:** the brief names the expected probe commands and the file-tool fallback (read/grep/sed); run them as named, in the plain allowlisted form. Report a shell denial in the verdict as a form/permission event with the checks re-routed to attached or file-tool evidence — never improvise in-place rewrites of repo files as a probe.
```

- One addressee normalization from the suggestion: "Name the expected probe commands ... in the brief" is orchestrator-side wording; the QA clause reframes it as the QA-side expectation ("the brief names ...; run them as named"). Every semantic element is preserved: (a) probes + file-tool fallback (read/grep/sed) named in the brief, (b) denial reported in the verdict as a form/permission event, (c) checks re-routed to attached or file-tool evidence, (d) never improvise in-place rewrites of repo files as a probe. The orchestrator half ships as Clause C.
- Consistency with D1d: no contradiction, no fork — D1d owns the retry form (`timeout <n> <command>`) and the fallback label; clause B owns brief-named probes, verdict reporting, and the no-improvised-rewrites ban. "the plain allowlisted form" references D1d's form rather than restating it. Placement immediately AFTER D1d makes the two bullets one denial block.
- qa-pro carries it (role-applicable, mdu-54 rule): qa-pro already carries D1d and the same denial family governs it; base sibling shape = contiguous list bullet, same emitted bytes.
- Overlay-root profiles are root-ADDED sources (mdu-54 rule): the build appends global snippets to them in the build copies, so root-vs-installed is not byte-identical by design — Clause B is edited into the ROOT files only and the build regenerates the installed copies.

## 4. D3 — Clause C: brief-checklist lines (orchestrator side)

The apply-now half ("pre-state probes in the next QA brief; plain-form retry line in the next introspector brief") becomes standing via `docs/brief-checklist.md` — one line each, pasted verbatim:

```markdown
- Pre-state the exact probe commands (plain allowlisted form) and the file-tool fallback (read/grep/sed) in every command-bearing QA brief; a denial QA reports is a form/permission event, not missing coverage. [20261110-1]
```

```markdown
- Add the plain-form retry line to the introspector brief: run the signal script as `timeout N python3 <script>`, no compounds, pipes, or redirects; bare `echo`/`pwd` and compound denials are by design. [20261110-1]
```

Placement ruling: BOTH halves land in the checklist (the doc IS the dispatch-time mirror of apply-now items); the QA prompt additionally carries its QA-side half (D2). The immediate next-brief application is orchestrator behavior, out of repo scope — the checklist lines make it standing.

## 5. Anchor table (grep every anchor before editing)

| # | File (base unless marked) | Insert AFTER (anchor text; survey line) | Insert BEFORE (anchor text; survey line) | Emitted shape |
| --- | --- | --- | --- | --- |
| 1 | `prompts/introspector.md` | `  Pass \`--cwd\`, \`--session-id\`, and \`--harness\` if the orchestrator supplied them; pass \`--manifest runs/<mdu-id>/manifest.json\` when an MDU id is given.` (L12) | `- Read \`agent-improvements.md\` at the project root if it exists.` (L13) | blank line not added; `  - ` + D1 text |
| 2 | `grok/agents/introspector.md` | same pass line (L18) | same read parent (L19) | same as #1 |
| 3 | `prompts/qa.md` | the D1d bullet `- **Denied shell:** ...` full line (L18) + its trailing blank line | `If the \`webapp-verification\` skill is available, load it.` (L20) | new paragraph bullet: blank line + `- ` + D2 text + blank line |
| 4 | `grok/agents/qa.md` | D1d full line (L24) + blank | `Be thorough but focused on the current deliverable's claimed functionality.` (L26) | same as #3 |
| 5 | `grok/agents/qa-pro.md` | D1d list item (L14), no blank line after | `- Provide PASS or FAIL grade with detailed bug reports.` (L15) | contiguous list bullet `- ` + D2 text, no blank lines |
| 6 | OVERLAY `overlays/prompts/qa.md` | D1d full line (L18) + blank | `When writing bug or issue reports to return with a FAIL grade,` (L20) | same as #3 |
| 6a | OVERLAY-ROOT `grok/agents/grok-qa.md` | D1d full line (L28) + blank | `When an acceptance criterion covers prompt TEXT` (L30) | same as #3 (paragraph bullet) |
| 6b | OVERLAY-ROOT `grok/agents/grok-qa-pro.md` | D1d list item (L12), no blank line after | `- Provide PASS or FAIL with detailed bug reports.` (L13) | contiguous list bullet `- ` + D2 text, no blank lines (same as #5) |
| 7 | `docs/brief-checklist.md` (## qa) | the `[20261021-8]` denial line (L57) | the `[20261021-11]` trace line (L58) | one checklist line (first C text) |
| 8 | `docs/brief-checklist.md` (## introspector) | the `[20261101-1]` line (L67, last line of file) | *(end of file)* | one checklist line (second C text) |

New file: `tests/test_mdu_57_form_denial_discipline.py` (base repo). Books: FEATURE_BACKLOG row; `agent-improvements.md` `20261110-1` flip; `runs/<mdu-id>/manifest.json`.

**Byte-identical mirror rule:** D1's emitted line (including the `  - ` lead) is the same bytes in #1 and #2. D2's emitted line (including the `- **Denied probes:**` lead) is the same bytes in #3, #4, #5, #6, #6a and #6b; grok frontmatter and surrounding spacing are the only permitted file-to-file differences. Checklist lines #7/#8 appear exactly once each.

## 6. Test plan — `tests/test_mdu_57_form_denial_discipline.py`

Hermetic: repo + sibling-overlay reads only, no network, no git state, no writes. Constants are the byte-identity authority (mdu-49 convention): `D1_20261110_1` (§2 line minus the `  - ` lead), `D2_20261110_1` (§3 line minus the `- ` lead), `C_QA_LINE`, `C_INTROSPECTOR_LINE` (full checklist lines). Base-file paths resolve through an `MDU57_TEST_ROOT` env override (default the real repo) for the mutation matrix; doc-consistency pins always read the real repo doc. File-count-free by construction: every pin is a substring/count-on/position check on clause text, never on file line counts. Reuse mdu-49's `_line_containing` parity helper shape and mdu-47's `@needs_overlay` gate for sibling reads.

| # | Test | Cases |
| --- | --- | --- |
| 1 | `test_d1_present_exactly_once_per_mirror` — emitted line in text, count == 1 | 2 |
| 2 | `test_d1_byte_identical_across_mirrors` | 1 |
| 3 | `test_d1_inside_script_bullet` — run-parent < pass line < D1 < read parent, per mirror | 2 |
| 4 | `test_pass_line_and_read_parent_unchanged` — both anchors still verbatim, per mirror | 2 |
| 5 | `test_d2_present_exactly_once_per_base_carrier` | 3 |
| 6 | `test_d2_byte_identical_across_base_carriers` | 1 |
| 7 | `test_d2_after_d1d_before_following_anchor` — per carrier: D1d < D2 < that carrier's BEFORE anchor | 3 |
| 8 | `test_d1d_bullet_unchanged` — full D1d line still verbatim, per base carrier | 3 |
| 9 | `test_overlay_qa_carries_d2` (`@needs_overlay`, parametrized over `OVERLAY_QA_CARRIERS`) — per overlay carrier (full-file override, root-added `grok-qa.md`, root-added `grok-qa-pro.md`): D2 count == 1, bytes == `EMITTED_D2`, D1d unchanged, D1d < D2 < that carrier's own following anchor | 3 |
| 10 | `test_constants_match_design_doc` — D1, D2, C_QA_LINE, C_INTROSPECTOR_LINE each verbatim in this doc | 4 |
| 11 | `test_checklist_lines_present_and_placed` — each C line count == 1; C_QA_LINE after the `[20261021-8]` line within `## qa`; C_INTROSPECTOR_LINE last within `## introspector` | 2 |

Overlay test placement: NO new overlay-repo test file. The overlay source is pinned from the base suite (test 9, mdu-47 `@needs_overlay` precedent); the overlay build copy is verified by the deploy phase and AC-9, because it is only guaranteed fresh after the overlay build runs. Non-vacuous: every assert names the missing clause/anchor and the file in its message (assert on emitted content, not just rc).

## 7. Acceptance criteria (QA grades from the repo alone)

1. Clause A present exactly once in each introspector mirror, byte-identical, inside the script bullet (between the pass line and the read parent); pass line and read parent byte-unchanged.
2. Clause B present exactly once in each of the six QA carriers (3 base + overlay full-file + the 2 overlay-root Grok profiles), byte-identical including the lead.
3. In every carrier, clause B sits immediately after the D1d bullet and before that carrier's following anchor; the D1d bullet is byte-unchanged everywhere (mdu-47/mdu-54 pins still green).
4. `docs/brief-checklist.md` carries both C lines exactly once each, in the sections and order specified (§5 #7/#8).
5. `tests/test_mdu_57_form_denial_discipline.py` exists with the §6 test set; full base suite green (prior count + 26 cases); no file-count pins anywhere in the new file.
6. Mutation matrix (test-agent, in a tmp copy via `MDU57_TEST_ROOT`): clause A stripped from one mirror → tests 1–3 red; clause B stripped from one carrier → 5–7 red; D2 moved before D1d → 7 red; D1d corrupted → 8 red; a C line removed → 11 red; constants drifted from the design doc → 10 red. Doc-only mutants (an unrelated line edited in this doc) → all green.
7. Prompt-regression gate exit 0 on the unchanged baseline (no `--update`); any red is reject-and-fix, not a refresh.
8. Secret gate exit 0 on staged files; run_ledger validate exit 0 on the finalized manifest before commit.
9. Overlay `./build.sh` exit 0 and the regenerated overlay `build/prompts/qa.md`, `build/grok/agents/grok-qa.md` and `build/grok/agents/grok-qa-pro.md` each carry clause B exactly once and byte-identically; overlay suite green; overlay `build/` changes committed with the overlay source edit (one commit per repo).
10. `agent-improvements.md` flips `20261110-1` to resolved pending the first post-deploy live exercise, with on-disk grep evidence cited (20261101-1 rule), and the FEATURE_BACKLOG row records this MDU.

## 8. Gates

- **Base suite:** `timeout 120 python3 -m pytest tests/ -q` — green.
- **Prompt regression:** run the gate subcommand exactly as `scripts/lib/prompt_regression.py` usage (L41) and the validator phase list name it; require exit 0 with the baseline untouched. Eval cases reference neither edited prompt family (§0), so a red means an unrelated regression — reject-and-fix per mdu-49.
- **Secret scan:** `timeout 60 python3 scripts/lib/secret_scan.py --staged` — exit 0. In-doc hygiene already applied here: no absolute paths, no `$WORKSPACE`-prefixed literals, and no 32+ char slash-joined underscore compounds; repo-relative file paths with extensions only (mdu-55 shipped green with the same shape).
- **Ledger:** `timeout 60 python3 scripts/run_ledger.py validate runs/<mdu-id>/manifest.json` — exit 0 after the last append and after the post-QA qa_grade flip.
- **Overlay:** from `$OVERLAY`: `./build.sh` exit 0, overlay pytest green.

## 9. Deploy decision

**Build-only; no `--force` this MDU** (mdu-55 D5 precedent). Rationale: prompt-body edits take effect at the next routine deploy regardless; a forced mid-loop deploy churns three CLI installed trees for zero grading value; QA acceptance is build-copy-vs-source byte-identity (AC-9), not installed-tree inspection. Devops phase: run both repos' builds, diff the overlay build copy against `overlays/prompts/qa.md`, record exit codes; the installed trees refresh at the next routine deploy.

## 10. Risks

- **Full-file override drift** (highest): shipping clause B to base only would leave the OpenCode qa persona without it — mitigated by carriers #6/#6a/#6b + test 9 (3 cases) + AC-2.
- **Order-pin collision:** mdu-54's built-profile pins are strict positions; inserting before D1d instead of after would still satisfy some but not test 7 — covered.
- **Addressee confusion:** the suggestion's QA sentence as-written would have QA authoring briefs; §3's normalization is the fix and is pinned by the doc-consistency test.
- **Baseline drift:** any prompt-regression red must not be absorbed by a refresh inside this MDU (AC-7 / §8).

## 11. Open questions (rulings; orchestrator may override)

1. **qa-pro inclusion** — RULED IN (role-applicable: it carries D1d; mdu-54 extended D1d to it).
2. **Overlay full-file fold** — RULED IN (mandatory; snippets never reach full-file overrides).
3. **Overlay build-copy pin location** — RULED: base-suite `@needs_overlay` pins the overlay SOURCE only; build copy is deploy-phase + AC-9 territory. If the orchestrator prefers an overlay-suite presence case on `build/prompts/qa.md`, it is a one-case append to an existing overlay test file, not a new file.
4. **SKILL.md note** — RULED OUT (§2).
