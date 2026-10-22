# Introspection — mdu-09-prompt-regression-gate

- Date: 2026-10-21T23:58Z
- Harness: opencode
- Session: ses_e9f7afef9ffegjxHo8qXwpkZ4Z
- Mode: loop (suggest-only; no agent definition files were edited)

## Coverage caveat

This MDU spanned two sessions: design, the first implementation pass, and review round 1 ran in an earlier session (before a checkpoint); the fix cycles, re-reviews, test, devops, QA and manifest finalisation ran in the session above. `session_signals.py` was run with an explicit `--cwd /mnt/FastSSDXFS/projects/agents` and `--session-id ses_e9f7afef9ffegjxHo8qXwpkZ4Z`; the returned session id matched (no silent stale-store substitution — 20261021-4's apply-now held), and the agent rows cover the manifest's full phase list (architect → commit), so the tree appears to include both halves. Per-row attribution to the pre-checkpoint half cannot be verified from the script (it keys by session id + parent_id only), so whole-run attribution below is inferred from that phase-list match, not proven. Missing logs did not block anything.

## Signals (16)

- long_cycle HIGH: orchestrator 4018s active / 8658s wall / 93 events (series-record active time; wall inflated by the checkpoint gap), just-code-mid 2191s / 5743s wall / 241 events (fix cycles 1+2 in one child), code-reviewer 1904s / 44, qa 1079s / 62 (workload — CLI cross-checks + live gate demos, not churn).
- long_cycle warn: architect 488s, code-reviewer-pro 547s active / 2289s wall.
- token_hotspot warn: orchestrator 412,077 (24%), just-code-mid 373,183 (22%), code-reviewer 235,761 (14%), code-reviewer-pro 148,933 (9%), just-code 145,627 (9%), architect 133,752 (8%), qa 126,429 (7%), test-agent 100,074 (6%).
- fix_loop HIGH: manifest fix_iterations=3.
- phase_fail_streak HIGH: review failed 2 times (manifest-derived, correct).
- review_rejections: 0 — **incorrect**; the manifest records two review phases with outcome "fail" (code-reviewer-pro REJECT → code-reviewer REJECT). Second live confirmation of detector gap 20261021-3.
- No cache_miss, no long_context, no expensive_model, no permission_thrash, no qa_fail_repeat, no stalled_subagent.

## Counter cross-check vs manifest

- fix_loop=3 = manifest `fix_iterations: 3` — agreed.
- review_rejections=0 vs two recorded review failures — disagreed (20261021-3; the phase_fail_streak fallback carried the signal).
- Agent rows match all 10 manifest phases; model tiers matched the mdu-lifecycle table at every phase (premium only on architect + reviewer-pro, both appropriate).
- Manifest was fully populated before introspection: `status: "completed"`, `completed_at`, full verification block (build true, 380 tests, qa_grade PASS), accurate fix_iterations, outcome summary — the 20261014-5 closure holds, second consecutive clean manifest.

## Notable frictions

1. **Review found what review missed** — each of the two REJECT rounds caught defects the previous round had missed: round 1 (premium) found behavioural defects (F1 promptfoo config did not run, F4 secret_scan git-SHA blind spot); round 2 (mid) found 3 MAJOR defects that were all on *error paths* (an OSError handler that itself crashed via an invalid `reasons=` kwarg; vacuous anti-tamper under a hand-edited non-pass value; diff missing snapshot-shape validation) plus 2 MINOR + 6 NITs. A presence tick passes all of them. 20261021-11 EXTENDED: the blindness is not only clause ordering (the mdu-11 case) but failure-path execution of procedure text generally — and the gate this MDU ships (ordered-trace golden cases, committed anti-tamper baseline, fail-closed exit contract) is the automated countermeasure, validated live by QA (reorder → exit 1, tamper → exit 2, missing case → exit 1).
2. **Orchestrator absorbed an execution phase** — review agents are sandboxed read-only, so the orchestrator ran the execution-evidence battery itself into `/tmp/opencode/mdu-09/review-evidence.md` for the reviewer. Correct routing per 20261021-9, but the cost landed on the most expensive agent (4018s / 412k tokens) → new 20261021-12: route the battery to devops, one dated evidence file per review round, re-run after each fix cycle.
3. **Model availability** — code-reviewer-pro was refused on the re-review dispatch ("Model access is disabled"), forcing a rotation to code-reviewer (mid). No dedicated availability signal exists in the script; the visible footprint is the ~385k dual-reviewer spend (20261014-4 note). Brief-side: plan the rotation before dispatching the premium reviewer.
4. **Coder child shape** — fix cycles 1+2 ran in ONE just-code-mid child (241 messages, long_cycle HIGH, 373k tokens); only polish cycle 3 used a fresh child. Contradicts the fresh-child-per-cycle discipline that made mdu-11's coder burn track child count (20261014-3 note).
5. **Test-agent hotspot despite the brief** — the brief asked for summary counts and `--tb=short`, yet test-agent still crossed the threshold at 100,074 tokens on the largest suite yet (380 + 93). Brief-side log discipline is insufficient alone; the definition change (20261021-7) remains unapplied.

## Suggestion set changes

- New: **20261021-12** (warn, code-reviewer, phase_routing) — reviewer execution-evidence routing.
- Recurred with evidence appended: 20261014-1 (record active time), 20261014-2 (412k), 20261014-3 (519k family; one long-lived coder child), 20261014-4 (~385k family, not denial-driven; pro→mid rotation), 20261021-3 (confirmed second time), 20261021-7 (mild recurrence despite the apply-now).
- Did not recur (left open per rule): 20261017-1 (seventh clean run), 20261021-1 (no cache misses), 20261021-6 (phase order correct), 20261021-8 (no qa permission thrash), 20261021-9 (routing handled at brief time).
- Confirmed/extended: 20261021-11 (extended from ordering to error paths), 20261021-4 (apply-now carried and worked), 20261014-5 (closure holds — second consecutive fully-populated manifest).
- No definition files were edited. No suggestions were auto-resolved.

## Apply-now for the next delegation

- Give test-agent the definition-change discipline in the brief AND expect it to be insufficient alone: run full once, then only failing/changed; `-q --tb=short`; summary counts + failing tracebacks only.
- Fresh coder child per fix cycle — do not resume one child across multiple cycles (mdu-09's just-code-mid cost).
- For reviews needing execution evidence: devops (not the orchestrator) writes a dated `review-evidence.md` before dispatch; re-run the battery after each fix cycle.
- Keep explicit `--session-id` on every signals run (20261021-4 apply-now).
- Derive review-rejection counts from manifest phase outcomes while 20261021-3 is open.
- When dispatching code-reviewer-pro, plan for the possible "Model access is disabled" rotation to mid up front.

Not blocking the commit.
