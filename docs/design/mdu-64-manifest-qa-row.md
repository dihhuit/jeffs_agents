# MDU-64 — Manifest rows before introspection

## 0. Surveyed files

Read this session, and nothing else:

- `open-agent-definitions/`
  `prompts/orchestrator.md` lines 130–141 (step 7 at 132, step 8 at 133).
- `open-agent-definitions/`
  `grok/agents/orchestrator.md` lines 136–143 (step 7 at 138, step 8 at 139).
- `opencode_agents/`
  `grok/agents/grokestrator.md` lines 154–159 (introspect bullet, then the ledger bullet).
- `open-agent-definitions/tests/`
  `test_mdu_63_guards.py` lines 100–129. `GROKESTRATOR = OVERLAY_ROOT / "grok" / "agents" / "grokestrator.md"` (repo-state pin). `OVERLAY_ROOT` itself was not in that window; copy it from the same module. Do not re-read the rest of that file to invent a second path.

`docs/brief-checklist.md` was not read.

## 1. Problem

Step 7 (base) and the grokestrator introspect bullet already run `introspector` in loop mode before commit and pass `runs/<mdu-id>/manifest.json`. They do not require finished phases to be in that file first. A handoff brief is not run evidence.

Apply-now **20261029-4** requires those rows before the introspector runs. Deviation from the logged sentence, which must stay visible: the log says "set status to complete". `scripts/lib/run_ledger.py` STATUSES are `in_progress|completed|failed|escalated`, and the inline field rule already in these mirrors says the final status is `completed`, never `complete`. The word `complete` is rejected. Every other obligation of the logged sentence is kept. The commit-row sentence is the standing apply-now on the same id, made explicit so the pre-introspect bar does not demand a row for a phase that has not run.

No `run_ledger.py` change. The clause only tells the orchestrator to fill fields the inline contract already names (`status`, `phases[]` `outcome` and `notes`, `verification`). Set `verification.qa_grade` when QA has graded. If a strict schema rejects that key, stop and report. Do not "fix" it by editing the ledger.

## 2. Clause

Normative text. Bytes identical in all three sources. No leading indent inside the fence. No line wrap inside the sentence.

```
Before invoking the introspector, append every phase that has already finished, including qa and validate and deploy when deploy ran, to runs/<mdu-id>/manifest.json with outcome and notes, and set status to `completed` (never `complete`). Set verification.qa_grade when QA has graded. Append the commit phase row at commit time, not before introspection. Never rely on the handoff brief alone as run evidence.
```

`deploy` is included only when deploy ran. Do not invent a deploy row. Do not write the commit phase row in this pre-introspect append. Copy the QA grade; do not invent one.

## 3. Per-carrier insertion

Do not rewrite the step-7 sentence. Do not renumber step 8.

### Base mirrors (same edit in both)

- `open-agent-definitions/`
  `prompts/orchestrator.md`
- `open-agent-definitions/`
  `grok/agents/orchestrator.md`

Insert one new paragraph immediately after the step-7 line and immediately before the line that starts `  8. Commit and push`. Five-space indent (the continuation column of `  7. `), then the clause on that single line. Not a new number. Not a `- ` bullet. In the prompts mirror this sits above the secret-gate sub-bullets, not inside them. The grok mirror has no those sub-bullets on the step-8 line; use the same five-space paragraph anyway so the two insertions match.

Surveyed step-7 line (both mirrors; leave it unchanged, including the ending `stale session tree.`):

`  7. Introspect (via `introspector` in **loop mode** only) — after QA PASS (or when a non-MDU task is done), before commit.`

### Overlay grokestrator — following sentence, same bullet

`opencode_agents/`
  `grok/agents/grokestrator.md` is one flat prose bullet (surveyed line 156). It is not a nested list. The next bullet is `- **Maintain a run ledger per MDU**`, a different topic.

**Form chosen: following sentence inside that same bullet.** A new bullet would split the introspect instruction from this precondition and would land between two existing bullets. Appending a sentence does not break the bullet.

Append on that same physical line: the existing bullet ends at `stale session tree.` Add one space, then the clause. Do not start a new `- ` item. Do not wrap the clause onto its own list item. Leave the ledger bullet and its nested field lines untouched.

## 4. Non-edits

- Do not edit the CACHE MISS GATE (MDU-63) text in either base orchestrator mirror.
- Do not edit `tests/test_mdu_63_guards.py`.
- Do not edit `scripts/lib/run_ledger.py`.
- Do not hand-edit generated trees or fixtures. Base `build/` is gitignored.
- Do not add `opencode_agents/tests/`
  `test_mdu_64_overlay.py`. The third mirror is pinned from the base suite.
- Do not pin a file count. Do not backfill MDU-63. Do not flip any improvements id except 20261029-4.
- Do not refresh `evals/golden/baseline.json`. A prior grep of `evals/golden/cases.json` found no pin of the introspect sentence. No new golden case. Gate C stays 23.
- Do not commit `runs/` or any manifest. `runs/` is gitignored.
- Out of scope: any other suggestion, and any MDU-63 clause edit.

### Generated carriers (rebuild, do not hand-edit)

Census of the introspect sentence is 9 hits. Sources are the three files above. The other six refresh only by build:

- `opencode_agents/build/`
  `prompts/orchestrator.md`
- `opencode_agents/build/`
  `grok/agents/orchestrator.md`
- `opencode_agents/build/`
  `grok/agents/grokestrator.md`
- `opencode_agents/build/`
  `claude/agents/orchestrator.md`
- `opencode_agents/build/`
  `claude/agents/grokestrator.md`
- `open-agent-definitions/tests/`
  `fixtures/pi_golden/`
  `prompts/orchestrator.md` (the generator `build.sh` already runs; MDU-63 refreshed this golden)

Order: from the base repo, `./build.sh`. Then from `opencode_agents`, `./build.sh`. Implement must not hand-edit the fixture. If Gate C is not 23 after that, stop and report. Do not change the expected count.

## 5. Pin plan

New file: `open-agent-definitions/tests/`
  `test_mdu_64_manifest_qa_row.py`.

Locate the overlay the same way as MDU-63: copy `OVERLAY_ROOT` from `tests/test_mdu_63_guards.py`, then `GROKESTRATOR = OVERLAY_ROOT / "grok" / "agents" / "grokestrator.md"`. Do not invent another relative path.

Source carriers only:

1. `prompts/orchestrator.md` (base)
2. `grok/agents/orchestrator.md` (base)
3. `GROKESTRATOR`

Extract the clause as the exact fenced character sequence (no indent). Assertions:

- Present once in each source carrier.
- The three extracts are equal to each other and to the fence.
- Base adjacency: the step-7 line is unchanged (still starts with `  7. Introspect (via `introspector` in **loop mode** only)` and still ends at `stale session tree.`; the clause is not on that line). The next non-empty line is five spaces plus the clause. The next non-empty line after that starts with `  8. Commit and push`.
- Grokestrator adjacency: the introspect bullet contains both `run ` + `` `introspector` `` + ` in **loop mode** only before commit` and the clause. The clause is the next sentence after `stale session tree.` on that bullet. The following list item still starts with `- **Maintain a run ledger per MDU**`.
- CACHE MISS GATE unchanged: load `tests/test_mdu_63_guards.py` by path and re-check case `20261110-2` (`CACHE_LINE`, `CACHE_FRAGMENTS`, `ORCH_CARRIERS`) against the two base orchestrator files. Do not retype the gate from memory. Do not loosen the fragments. The new clause line must not contain the cache-miss marker.
- Named mutation test `test_deleting_clause_from_one_carrier_fails`: for each carrier, a copy of the text with the one clause removed fails the once-and-identical check. Do not write the working tree.

No assertion that N files contain the sentence. No pin of `build/` or the pi golden in this test (those move only when build runs).

## 6. Backlog outline

In `open-agent-definitions/`
  `FEATURE_BACKLOG.md`, add one new section. Do not edit other headings. Do not add an MDU-63 section.

```
### MDU-64 — Pre-introspect manifest rows

- **Status:** Done — 2026-11-14
```

Exactly one line matching `- **Status:** Done — 2026-11-14`. A bare Open status fails `tests/`
  `test_mdu_45_grok_review_registry.py::test_backlog_no_entry_remains_unresolved`. One short scope sentence under that heading is allowed. No second Status line.

## 7. Flip text

File: `open-agent-definitions/`
  `agent-improvements.md` only. Find open item **20261029-4**. Set its checkbox to `[x]`. Keep the original suggestion text. Append this resolution and do not flip any other id. If the id is absent, stop and report. Do not create a second copy under `opencode_agents`.

`[x] RESOLVED 2026-11-14 (mdu-64). Carriers: prompts/orchestrator.md, grok/agents/orchestrator.md, and opencode_agents/
grok/agents/grokestrator.md. Status word is completed, never complete. The commit phase row is appended at commit time. Reopen only if a later introspection finds QA finished and no qa or validate phases[] row.`

## 8. Checklist line

Not read. Checklist line optional. Implement adds one sentence under the existing orchestrator or manifest heading only when that heading exists. If the heading is absent, add nothing. Do not create a new heading. The checklist sentence is not a fourth source carrier and must not be the fenced clause.

Suggested sentence, only under that existing heading: Before introspection, finished phases (qa, validate, and deploy when deploy ran) are already manifest rows with outcome and notes, status is completed never complete, and verification.qa_grade is set when QA has graded; the commit row waits until commit.

## 9. Acceptance criteria

- AC-1. The fenced clause occurs once in `prompts/orchestrator.md`.
- AC-2. The fenced clause occurs once in `grok/agents/orchestrator.md`.
- AC-3. The fenced clause occurs once in `opencode_agents/`
  `grok/agents/grokestrator.md`.
- AC-4. The three extracts are byte-identical to the fence.
- AC-5. Both base step-7 lines are unchanged. The clause paragraph is the next non-empty line. The line after that starts with `  8. Commit and push`.
- AC-6. Grokestrator keeps the clause as the next sentence of the existing introspect bullet. The ledger bullet is unchanged and still follows.
- AC-7. MDU-63 cache-miss fragments still match both base orchestrator mirrors. That paragraph was not edited.
- AC-8. `tests/`
  `test_mdu_64_manifest_qa_row.py` exists and `test_deleting_clause_from_one_carrier_fails` fails a one-carrier deletion on a copy. No overlay twin. No file-count pin.
- AC-9. `FEATURE_BACKLOG.md` has one `### MDU-64` section and exactly one `- **Status:** Done — 2026-11-14` line. No MDU-63 backfill. `test_backlog_no_entry_remains_unresolved` stays green.
- AC-10. Only 20261029-4 is flipped, with the section 7 resolution text.
- AC-11. `git diff` does not touch `scripts/lib/run_ledger.py` or the MDU-63 clause text.
- AC-12. From the base repo, `timeout 60 python3 scripts/`
  `lib/prompt_regression.py gate` exits 0. Baseline file is not updated.
- AC-13. Base `./build.sh` then `opencode_agents` `./build.sh` are green. Pi golden is regenerated by that generator only. Gate C stays 23. Generated files are not hand-edited.
- AC-14. Secret scan passes. Docs and prompts use repo-relative paths only. No 32+ character run of letters, digits, plus, or slash.
- AC-15. Checklist sentence exists only if section 8's heading was already there.
- AC-16. After both builds are green, deploy per section 10. Installed OpenCode, Grok, and Claude copies contain the clause. Base repo is not deployed alone.
- AC-17. No `runs/` manifest is committed.

## 10. Deploy

Do not deploy the base repo alone. From `opencode_agents`, after both builds are green: `./deploy.sh` (dry run) then `./deploy.sh --force`.

Verify the clause in the installed OpenCode, Grok, and Claude copies of the orchestrator and of grokestrator, using the destination paths that `./deploy.sh` prints. Do not hard-code a home-directory absolute path in this doc or in the test.

Commits are two repos, separately, after that verification. Base: the two orchestrator mirrors, the new test, `FEATURE_BACKLOG.md`, `agent-improvements.md`, the checklist only if edited, and the pi golden if `./build.sh` changed it. Overlay: `grok/agents/grokestrator.md` and the `build/` outputs `./build.sh` updated for these carriers. Do not `git add -A`. Do not commit `runs/`.
