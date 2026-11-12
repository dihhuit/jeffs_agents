# Introspection — MDU-56 (loop mode, post-QA PASS, pre-commit)

- Harness: opencode | Root session: ses_e3298eb27ffe26mrOwhldIcreM | Manifest: runs/mdu-56/manifest.json (completed, qa_grade PASS, 7 phases, fix_iterations=1, validator [ok] re-run this pass)
- Artifact: agent-improvements.md (session record + inline notes + 2 new suggestions appended). No agent definitions edited; no review mode; manifest untouched; no commit.

## Signals (script, first plain attempt, explicit --session-id — 20261021-4 clean; 10 signals)

- long_cycle HIGH orchestrator (2270s/3885s/46) + warns: just-code 523s, code-reviewer 482s, qa 792s
- token_hotspot: orchestrator 445,414 (46%), deep-research 109,305 (11%), architect 119,240 (12%), just-code 99,452 (10%)
- repeated_tool_error qa ×5 — store-probed: all `permission.rejected` (2 by-design compound forms, 2 byte-identical `cp` retries, 1 `python3 -c`)
- context_reread architect ×7 (own design doc, authoring loop)
- cache_miss orchestrator ×1 — store-probed: QA-child-wait expiry (895s), warm next turn, fresh session
- review_rejections 0 / approvals 1 = manifest truth; NO long_context, expensive_model, qa_fail_repeat, stalled_subagent, fix_loop, phase_fail_streak
- permission: v2 UNKNOWN → direct store probe: 12 denied rows tree-wide, all absorbed, zero verdict flips; all models match the mdu-lifecycle tier table (store probe)

## Notes written (all grep-verified against HEAD a5fbae5; definition dirs clean vs HEAD)

- Recurred: 20261014-1 (long_cycle HIGH), 20261014-2 (orchestrator at 445k record level), 20261014-3 (just-code, fresh-child-per-cycle held), 20261024-1 (architect in-band), 20261029-4 (phase-clean + forward-projected completed_at wrinkle; no commit row — append at commit), 20261110-2 (cache miss, pause-class; suggested carve-out before its clause ships)
- Clean/positive: 20261021-6 did not recur (execution order verified by store timestamps), 20261021-9 live-exercised for the first time (manifest cites the pre-check as the ~/.pi routing reason), 20261021-11 thirteenth trace-style catch (vacuous empty-sources MINOR on an APPROVE round), 20261017-1 clean (zero git-state commands in 8 children), 20261014-5/-6 stay closed, 20261014-4/20261027-1/20261030-2 did not recur, 20261101-2 apply-now carried (reviewer model id recorded)
- 20261110-1 stays resolved (both reopen triggers unmet; residual: installed prompts/introspector.md still lacks clause A — pi-only deploy did not refresh opencode installs)

## New suggestions

- 20261111-2 (low, deep-research, token_hotspot): first deep-research hotspot; definition change = numbered open questions + stop condition + incremental summarization in prompts/research.md + grok mirror
- 20261111-3 (low, qa, denial_retry_discipline): byte-identical retry of a content-denied `cp`; definition change = form-vs-content denial split in the six QA carriers

## Apply-now for the orchestrator

1. Append the commit row to runs/mdu-56/manifest.json and re-run `run_ledger.py validate` before commit (20261029-4 standing apply-now); normalize the forward-projected completed_at if the commit lands materially later than 03:10Z.
2. The next routine `--force` deploy should refresh installed `prompts/introspector.md` so clause A reaches the runtime prompt (stale since mdu-57/58; still stale after this pi-only deploy).
3. Carry the content-denial list (cp/mv/rm/python3 -c → no retry, straight to fallback) into the next QA brief even before 20261111-3 ships.
4. Before 20261110-2's clause ships, add its pause-class carve-out (fresh session + warm next row = log, don't stop).

Not blocking the commit.
