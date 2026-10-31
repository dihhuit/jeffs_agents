# MDU-47 · Definition-guards batch + orchestrator repoint

User-approved 2b batch (2026-10-31): apply the four queued definition clauses (20261017-1, 20261021-11, 20261021-8 reworded, 20261030-5) across base prompts + grok mirrors, fold the QA sentences into the overlay full-file override, and carry the 20261026-2 orchestrator-model repoint ruling. Base repo first; the overlay build inherits.

## 0. Surveyed files (reads only; grep-only beyond this list)

Base repo: `agent-improvements.md` (entries 20261017-1 L9-26, 20261021-8 L243-256, 20261021-11 L277-287, 20261030-5 L428-432, 20261026-2 L315-325; mdu-46 session record L470-476 with the QA-reword rationale); `prompts/test-agent.md`, `prompts/code-reviewer.md`, `prompts/qa.md`, `prompts/architect.md`, `prompts/grok-review.md`; `grok/agents/` mirrors `test-agent.md`, `test-agent-pro.md`, `code-reviewer.md`, `code-reviewer-pro.md`, `grok-review.md`, `qa.md`, `qa-pro.md`, `architect.md`, `architect-premium.md`; `opencode.json` (L1-40 orchestrator block); `evals/golden/cases.json`, `evals/golden/baseline.json`, `evals/README.md` (L130-209 protocol); `tests/test_mdu_24_test_agent_git_guard.py`; `tests/README.md` (L1-30); `docs/brief-checklist.md`; `docs/design/mdu-41-fallback-policy.md` (L190-234); `docs/design/mdu-46-apply-now-tooling.md` (L95-124); `FEATURE_BACKLOG.md` (L1-40, L425-449); `skills/mdu-lifecycle/SKILL.md` (L24-41).

Overlay repo: `overlays/prompts/qa.md`, `overlays/manifest.json`, `tests/test_mdu_44_dead_copy_hygiene.py` (L30-99).

Grep-only beyond the list (no full reads): `build/` prompt copies; `scripts/lib/probe_models.py` flags; `scripts/lib/validate.py` parity mentions; `tests/test_mdu_46_apply_now_tooling.py` count pins (none found); `docs/design/mdu-45-grok-review-registry.md` family conventions; overlay `opencode.json` (no orchestrator model override); `prompts/` glob (no `test-agent-pro` / `architect-premium` / `qa-pro` / `code-reviewer-pro` twins — grok-only variants); mdu-41 probe-clause landing census.

## 1. Verified facts that shape the design

1. **20261017-1 is already shipped.** All three test-agent bodies (`prompts/test-agent.md` L29, `grok/agents/test-agent.md` L30, `grok/agents/test-agent-pro.md` L29) carry a byte-identical **Dirty tree** bullet forbidding every command the entry names plus `git reset --merge`, `git stash clear`, script-hiding, with the reflog-restore/report path. Pinned by `tests/test_mdu_24_test_agent_git_guard.py` (substrings + ordering + ROLE_KEYWORDS) and mirrored in the overlay root grok test profiles. The introspector's "unapplied" notes track the entry's exact wording, not coverage; MDU-24 shipped a strictly broader guard.
2. No base `prompts/` twins exist for `-pro` variants (glob): `test-agent-pro`, `qa-pro`, `code-reviewer-pro`, `architect-premium` are grok-only profiles.
3. `overlays/manifest.json` snippets touch only mdu-code/grok-mdu-code and devops/grok-devops; nothing shadows the architect/test-agent/reviewer targets. The only shadow is `overlays/prompts/qa.md` (full-file replacement of base `prompts/qa.md` in the deployed OpenCode + Claude bodies).
4. Golden cases: 7, all targeting `prompts/orchestrator.md`, `grok/agents/orchestrator.md`, `prompts/just-code.md`; every `forbidden` list is empty; baseline records case pass/fail only (no file hashes).
5. Base `opencode.json`: orchestrator model L20 (`opencode-go/mimo-v2.6-flash`), description L19; 7 other agents keep `mimo-v2.6-flash` (L355, L483, L1623, L1761, L2437, L2501, L2659). The overlay has no orchestrator model override (merged build inherits base). The mdu-lifecycle tier table has no orchestration row — nothing to edit there.
6. The probe gate is config-driven via `config_sha256` (`scripts/lib/probe_models.py`): any `opencode.json` edit invalidates the recorded hash; the gate reds until `--refresh --gate` re-probes.

## 2. D1 — Clause texts, placement, and the 20261017-1 ruling

**D1a (20261017-1, git guard): VERIFY-ONLY, do not re-add.** The entry's verbatim sentence would duplicate the shipped Dirty tree bullet (two git enumerations in one prompt; pin/golden confusion risk). No test-agent text edit ships. MDU-47 adds verify pins (D5 item 4) asserting the existing bullet in the three base files **and** the overlay root `grok/agents/grok-test-agent.md` + `grok/agents/grok-test-agent-pro.md` (live personal mirrors, currently unpinned), and records fulfillment in the backlog (D8). Apply-now lineage honored: 14 clean runs + carried stash snapshots.

**D1b (20261021-11, reviewer trace sentence).** Insert verbatim as a column-0 bullet in each file's Hard constraints block, immediately before the final sign-off/approve bullet:

> - When a mandated check verifies prompt TEXT (a clause, a gate, a fallback), trace it as a procedure, not a presence tick: in order, from the position of an agent in each repo variant (base and overlay), what does the text make you DO when the primary path is unavailable? A clause whose ordering sends the executing agent down the wrong branch fails the check even when every element is present. State the trace in one line per variant in the verdict.

Files + anchors: `prompts/code-reviewer.md` (before L22 "If the code is correct…"); `grok/agents/code-reviewer.md` (before L27, same anchor text); `grok/agents/code-reviewer-pro.md` (after L20 "Be specific…", before L21 "Reserve this level…"); `prompts/grok-review.md` (before L17 "Only sign off…"); `grok/agents/grok-review.md` (before L22, same). grok-review gets it per the mdu-45 family convention (census family shares behavior; the pair is parity-pinned). Clause bytes identical everywhere; local anchors differ per mirror (mdu-41 D6 pattern).

**D1c (20261021-11 QA copy).** Same sentence with exactly two word swaps ("a mandated check verifies" → "an acceptance criterion covers"; "fails the check" → "fails the criterion"):

> - When an acceptance criterion covers prompt TEXT (a clause, a gate, a fallback), trace it as a procedure, not a presence tick: in order, from the position of an agent in each repo variant (base and overlay), what does the text make you DO when the primary path is unavailable? A clause whose ordering sends the executing agent down the wrong branch fails the criterion even when every element is present. State the trace in one line per variant in the verdict.

Files + anchors: `prompts/qa.md` (new paragraph after L21 "Be thorough…", before "On FAIL…"); `grok/agents/qa.md` (after L24, same); `grok/agents/qa-pro.md` (bullet after L14 "Provide PASS or FAIL grade…"); overlay `overlays/prompts/qa.md` (paragraph, D2).

**D1d (20261021-8 QA timeout sentence, reworded).** Reworded per the mdu-46 grounding note (agent-improvements.md 20261021-8, mdu-46 note): ONE simple single-command attempt, fast fallback, wrapper not presented as reliable:

> - **Denied shell:** If `shell` is permission-denied, make exactly ONE retry with the simple single-command wrapper form `timeout <n> <command>` — no pipes, no redirects, no command substitution (e.g. `timeout 120 python3 -m pytest -q`). If that is also denied, do not conclude that shell is unavailable and do not report BLOCKED for it: fall back immediately to file tools plus orchestrator-attached outputs, labelling the affected checks "verified via orchestrator-attached output".

Files + anchors: `prompts/qa.md` (new paragraph after L16 "Use available tools…"); `grok/agents/qa.md` (after L22, same); `grok/agents/qa-pro.md` (bullet after L13 "Use available tools…", before the D1c bullet); overlay `overlays/prompts/qa.md` (paragraph after L16 "For web apps…", before the D1c paragraph). The mdu-46 diagnostic (record the exact denied command string verbatim once) stays brief-side — carry it in THIS MDU's QA brief, not the definition.

**D1e (20261030-5 architect path notation).** New last bullet of each Hard constraints block:

> - In design docs, write file paths repo-relative, or as `$WORKSPACE/<subpath>` when a workspace-absolute reference is unavoidable — never as literal absolute paths (the secret-scan gate counts long absolute-path lexemes as secret-shaped and will red).

Files + anchors: `prompts/architect.md` (after L18 "Output files…"); `grok/agents/architect.md` (after L23 "Consider and document…"); `grok/agents/architect-premium.md` (after L20 "Consider operational…"). Deliberate deviation from mdu-41 precedent (which skipped premium for the probe clause): path hygiene is tier-independent and the FP fix cycle was paid regardless of tier; one bullet, byte-identical. The scanner path-shape exemption stays a backlog item (20261030-5's other half) — NOT in this MDU.

Pin fragments (byte-stable, one per clause): "trace it as a procedure, not a presence tick"; "fails the criterion even when every element is present"; "no pipes, no redirects, no command substitution"; "verified via orchestrator-attached output"; "write file paths repo-relative".

## 3. D2 — Overlay qa fold + overlay pin

Both QA sentences (D1c + D1d) must land in `overlays/prompts/qa.md` or the deployed OpenCode/Claude qa never sees them (full-file replacement wins over the base prompt). Placement per D1c/D1d. No other overlay source changes (fact 3). New overlay `tests/test_mdu_47_overlay_qa_fold.py` asserting: (a) both pinned fragments in `overlays/prompts/qa.md`; (b) both fragments in `build/prompts/qa.md` after `./build.sh` (build is tracked; mdu-44 tests already assert build content); (c) mdu-44 keep-list pins still pass (additive only). No existing overlay test pins qa-override content (grep verified).

## 4. D3 — Orchestrator repoint (user ruling 2026-10-31)

- `opencode.json` L20: `"model": "opencode-go/mimo-v2.6-flash"` → `"model": "opencode-go/glm-5.3-flash"`; L19 description tail "(Go mid, mimo-v2.6-flash)" → "(Go mid, glm-5.3-flash)".
- Live probes at design time (reported by the dispatching session, 2026-10-31, one-shot `opencode run -m <id> "Reply with exactly: OK"`): **both `opencode-go/glm-5.3-flash` and `opencode-go/mimo-v2.6-flash` returned exactly `OK`.** Cite this line in the manifest.
- Probe-refresh consequence: the edit changes `config_sha256`, so the gate reds until `timeout 300 python3 scripts/lib/probe_models.py --refresh --gate` runs — MANDATORY from BOTH repos (base first, then overlay after its build merges the config); recorded in D7, never skipped.
- No registry comment or allowlist change for `mimo-v2.6-flash`: 7 other agents still use it (fact 5). No mdu-lifecycle table edit (no orchestration row, fact 5). Record the ruling in the backlog (D8) so the 20261026-2 deviation stops being silent.

## 5. D4 — Golden-case audit (per-case verdict)

| Case id | Target | Trace touches our files? | Forbidden at risk? | Verdict |
| --- | --- | --- | --- | --- |
| orchestrator-commit-step-secret-gate-order | prompts/orchestrator.md | no | empty list | safe |
| orchestrator-run-ledger-finalize-order | prompts/orchestrator.md | no | empty list | safe |
| orchestrator-responsibilities-loop-order | prompts/orchestrator.md | no | empty list | safe |
| orchestrator-mirror-secret-gate-order | grok/agents/orchestrator.md | no | empty list | safe |
| just-code-constraints-order | prompts/just-code.md | no | empty list | safe |
| orchestrator-prompt-regression-gate-clause | prompts/orchestrator.md | no | empty list | safe |
| orchestrator-mirror-prompt-regression-gate-clause | grok/agents/orchestrator.md | no | empty list | safe |

No case traces any edited target file, no `forbidden` list is non-empty (the git-guard markers cannot trip anything — and the guard text is not being added anyway, D1a), and no appended clause reorders a pinned trace. Verdict: **no collision — no cases.json edit, no baseline refresh; the gate is expected to exit 0 with the unchanged baseline (verify, do not assume).**

## 6. D5 — Pin tests

Base `tests/test_mdu_47_definition_batch.py` (hermetic, tmp_path only, no git state, no network):

1. Per-clause presence: each pinned fragment in every file named by its D1 row (16 prompt-file assertions).
2. Mirror parity: trace fragment in base prompt AND grok mirror AND (qa only) overlay body; timeout fragment in all four qa bodies; workspace fragment in all three architect files.
3. Ordering pins: D1b bullet precedes the sign-off bullet in each reviewer file; D1d paragraph precedes D1c paragraph in each qa body.
4. Dirty-tree verify pins: "**Dirty tree:**" and "git stash clear" present in the three base test-agent files and the two overlay root grok test profiles (assert-only).
5. Repoint pin: orchestrator `model` equals `opencode-go/glm-5.3-flash`, description carries the new tail, and the other 7 mimo rows are untouched.
6. Checklist pins: each new D8 clause line present with its `[id]` on the same line (mdu-46 pin-pair pattern).

Pin-pair decision: NO id comments inside prompt bodies (prompts ship to models; comments bloat every call). The (id, fragment, files) triples live as paired constants in the test file, named per mdu id — the auditable equivalent of mdu-46's same-line rule, which applies only to the checklist doc lines. Overlay pin file per D2.

## 7. D6 — Prompt-change protocol (verbatim, mdu-47 tmp paths)

Snapshot → edit → snapshot → diff, run from the base repo root, for every edit under `prompts/` or `grok/agents/` (overlay edits: same commands from the overlay root, which carries the script via its wrapper):

```sh
timeout 120 python3 scripts/lib/prompt_regression.py snapshot --out /tmp/opencode/mdu-47/before.json
# ... edit ...
timeout 120 python3 scripts/lib/prompt_regression.py snapshot --out /tmp/opencode/mdu-47/after.json
timeout 120 python3 scripts/lib/prompt_regression.py diff \
  --before /tmp/opencode/mdu-47/before.json \
  --after  /tmp/opencode/mdu-47/after.json
```

Exit semantics (evals/README.md steps 171-176): `0` clean, proceed; `1` = ≥1 golden case regressed — the edit is rejected, revert or fix the hunk and repeat, never weaken the case; `2` = operational failure — stop and investigate. Forgot the before-snapshot: `git stash` the edit, snapshot, `git stash pop`. No case change is expected (D4), so `baseline --update` must NOT run; if a case reds anyway, follow evals/README.md steps 178-187 (case-first update + baseline refresh only after QA, committed together).

## 8. D7 — Deploy plan (devops; config changed → probe refresh mandatory)

1. Base: `timeout 300 python3 -m pytest tests/ -q` green → `./build.sh` twice (idempotent) → `timeout 300 python3 scripts/lib/probe_models.py --refresh --gate`.
2. Overlay: `./build.sh` → overlay pytest green → overlay probe refresh + gate green (merged config).
3. `./deploy.sh` dry-run clean, then `./deploy.sh --force` (combined overlay build to all CLIs present).
4. Installed == build byte checks (`cmp`) for every edited prompt on all three CLIs — OpenCode `~/.config/opencode/prompts/`, Grok `~/.grok/agents/`, Claude `~/.claude/agents/` — including the folded overlay qa body and the generated claude copies.
5. Commit and push each repo separately (base first). Commit-time gates on the base commit: prompt-regression gate exit 0 + secret-scan gate exit 0.

## 9. D8 — Books

- `docs/brief-checklist.md` one-line additions (id on the same line): architect — "Design docs write paths repo-relative or as `$WORKSPACE/<subpath>`, never literal absolute paths. [20261030-5]"; code-reviewer — "Prompt-text checks are traced as procedures (one line per repo variant), not presence-ticked. [20261021-11]"; test-agent — "The working tree is the source of truth; never run destructive git state commands. [20261017-1]"; qa — "Denied shell → one simple `timeout <n> <command>` attempt, then fast fallback with 'verified via orchestrator-attached output' labels. [20261021-8]" and "Prompt-text acceptance criteria are traced, not presence-ticked. [20261021-11]". The checklist stays the fallback (definitions now carry the clauses).
- `tests/README.md`: new row for `test_mdu_47_definition_batch.py` covering the clause pins, verify pins, and repoint pin.
- `FEATURE_BACKLOG.md`: new `### MDU-47` entry (Why/Description/ACs/Status Done line filled at commit) recording the four fulfillments — 20261017-1 as fulfilled-by-MDU-24 with MDU-47 adding verify pins — the repoint ruling line (user ruling 2026-10-31: orchestrator repointed to `opencode-go/glm-5.3-flash`; design-time probes OK on both ids), and a follow-up note that the overlay root personal grok-* variants were not edited in this batch.

## 10. Acceptance criteria

1. Base suite green incl. new pins; overlay suite green incl. fold pins; both builds idempotent; mdu-24/44/45/46 pins unaffected (additive only).
2. All 16 prompt-file clause insertions byte-match this doc's quoted texts (D6 diff evidence attached to the review and validate briefs).
3. Golden gate exit 0 on the base commit with the unchanged baseline; secret gate exit 0; probe gate green in both repos post-refresh.
4. `opencode.json` orchestrator model + description repointed; the 7 other mimo rows untouched; no other registry edit.
5. Installed == build byte-identical for every edited prompt on all three CLIs; deployed overlay qa carries both folded sentences.
6. QA attestation per the closed 20261014-5 protocol (final manifest path, file-inspection ATTEST line; record any denied-command strings verbatim per the mdu-46 diagnostic apply-now).
7. Backlog + checklist + tests README rows land in the same base commit.

## 11. Open questions

1. Confirm D1a verify-only for 20261017-1 (guard already shipped by MDU-24; re-adding the entry text would duplicate a pinned bullet).
2. Overlay root personal variants (`grok-qa`, `grok-qa-pro`, `grok-architect`, `grok-architect-premium`, `grok-test-agent*`, `grok-code-reviewer-pro`) are NOT edited (out of the approved scope). One-line backlog follow-up recorded — extend now if the user wants parity there too.
3. `architect-premium` included for the path-notation clause (deliberate deviation from mdu-41's probe-clause precedent) — flag for review.
4. The 20261030-5 scanner path-shape exemption remains open as its own backlog item; this batch ships only the notation clause.
