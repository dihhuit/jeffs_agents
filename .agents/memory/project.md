---
type: project
created: 2026-10-27T13:24:20Z
updated: 2026-10-31T02:50:00Z
---

# Project facts — open-agent-definitions (base agent-team repo)

- Verify: `python3 -m pytest tests/ -q` + `./build.sh` (both must be green); overlay sibling `opencode_agents/` builds via its own `./build.sh` (re-runs base build, then merges overlays); live deploy from overlay `./deploy.sh --force`.
- Oracle storage layout (learned 2026-10-27, mdu-35): OpenCode v2 moved parts inline into `session_message.data.$.content[]` between 2026-10-13/15; the legacy `part` table is frozen after that cutoff (0 rows for all newer sessions). Census/forensics over recent sessions must go `part.message_id = session_message.id` → `session_v2`; tool parts for post-cutoff sessions are NOT in the `part` table.
- `scripts/lib/secret_scan.py` high-entropy rule (`[A-Za-z0-9+/]` runs of 32+, threshold 3.5 bpc) trips on plain repo paths of 32+ chars because `/` is in the char class (the overlay mirror path under `overlays/` reaches 33 chars). **Irony noted:** the example path in this very line trips the scanner — that is why the mdu-35 design doc reworded its path lexemes; keep paths short or split them in committed docs.
- The overlay third orchestrator mirror is overlay-root `grok/agents/grokestrator.md` (full file, snippets not re-applied onto it); there is no `overlays/grok/agents/` path.

## 2026-10-27T14:32:09Z
- scripts/lib/resume_block.py validate <fixture> — exit 0 canonical / 1 violations / 2 usage; canonical resume-block shape documented in docs/resume-block.md; grokestrator mirror edited via overlay repo (both repos must be committed for one orchestrator-file change).
- The completed_at manifest field must be an ISO-8601 string even while status is in_progress (set an interim timestamp, update at finalize) — run_ledger validate rejects null.

## 2026-10-27T22:20:00Z (mdu-36)
- Overlay now builds two tiers: its build.sh runs the base gen_zen_config.py (via GENERIC_DIR) on the MERGED config -> build/opencode.zen.json (zen map = base map + optional config/zen-model-map.json layer + xai/*-only big-pickle fallback; any other unmapped model fails the build). Overlay deploy.sh gained --tier=zen|go (default zen; both tiers installed; parked file inert by name). Invalid --tier exits 1 in the overlay but exit 2 in base — intentional local convention.
- Overlay deploy.sh grok-dir edge fixed: missing harness source dirs warn-skip (never abort, dry-run or --force); true find-based counts; the old live bug printed '1 grok agent profile(s)' with 41 profiles; regression test asserts the anchored count line.
- runs/ is gitignored in the OVERLAY repo (mdu-29/mdu-36 manifests stay local-only, unlike the base).
- Gotcha (2026-10-28): OpenCode's model registry can list dead models as "active" — verify with `timeout 90 opencode run -m <id> "Reply with exactly: OK"` before adding to zen-model-map.json or prompts (mdu-37).

## 2026-10-29 (mdu-38)
- scripts/lib/probe_models.py --refresh --gate: probes zen-map targets (hard, exit 1 if any not ok/stale/missing) + alternates (warn-only); success = exit 0 AND stdout stripped == "OK" exactly; success rule pins the F1 "NOT OK"/"OKChrome" substring finding; report exits 0 as data even when models fail — only --gate grades.
- Base /runs/ is gitignored too (manifests local-only in BOTH repos now, contrary to the older mdu-36 note); runs/ ledger validate still required pre-commit.
- qa child regression (new 20261029-1): a QA subagent can return an empty/corrupted first reply; the protocol is to re-request in the same session before accepting.

## 2026-10-29 (mdu-42)
- Grok-xai hard rule, four enforcement layers: base validate.py clauses (go + zen variants), base deploy.sh grok_xai_gate (hard, both tier files), overlay deploy.sh run_grok_xai_gate over active+parked (inline scripts/lib/check_grok_xai.py), probe_models.py --include-xai (xai_results report section + gate rule 6.5; ok==1-among-duplicates is green, mirroring the zen branch). Grok-named = grok-* prefix or exactly grokestrator/grok-plan; bare `xai/` suffix is a violation in both engines.
- Overlay zen build treats xai/* as IDENTITY pass-through for ALL agents (family rule, not name-scoped; thought-leadership-coach stays on xai in zen — correct, not a violation); no xai rows ever land in zen-model-map.json.
- Spawn model overrides: the deployed default tier still routes coder/reviewer/test/qa/devops defaults to free models (big-pickle / lightning-free) that cap mid-loop — every dispatch this MDU used an explicit paid model override `opencode-go/glm-5.3-flash` on the spawn (apply-now 20261029-2). Keep until MDU-39/40/41 change the default tier; mutate away from big-pickle defaults then.
- Verbatim free-cap refusal string (for MDU-39): `Error: Free usage limit reached. Free models work in OpenCode (https://opencode.ai); subscribe to OpenCode Go to keep going: https://opencode.ai/go` — big-pickle + deepseek-v4.1-flash-free + mimo-v2.6-flash-free + nemotron-3.5-super-vl-free; evidence /tmp/opencode/mdu-42-deploy-evidence.md.
- Introspector shell permission regression (first denial since the mdu-30 fix): session_signals.py did not run in this MDU's introspection — regression watch attached to closed suggestion 20261014-6; machine signals UNKNOWN, not zero (20261029-2 note).

## 2026-10-30 (mdu-39)
- Free-cap census gotcha: `session_message.data` free-cap rows carry the refusal text TWICE (error message + `response.body` echo), and sweep by-day buckets were mis-slotted, inflating/deflating substring counts — the discriminating count is per JSON object with `"type":"provider.quota"`, not per substring mention. Reconciled truth: 68 objects = 60 canonical wording + 8 old wording (old only on 2026-10-24); real-agent rows 34 (orchestrator 18, just-code 5, just-code-mid 4, just-code-free 2, architect 2, qa-free 1, grok-architect 1, devops-free 1), probe/cli rows 34 (no agent field).
- Live-measured (2026-10-30 ~02:57 UTC): all four refused-while-capped free models (big-pickle, deepseek-v4.1-flash-free, mimo-v2.6-flash-free, nemotron-3.5-super-vl-free) probe exact-OK simultaneously after the 10-29→30 boundary — the free cap is account-shared DAILY (reset confirmed live), never per-model; a probe-OK model is not quota-exempt. Cap size remains undocumented (official 200/day figure retracted 2026-10-22).
- Free-cap refusal error shape in the DB: inline part `error = {"type":"provider.quota","status":429,"message":"<refusal>","response.body":"{\"error\":...FreeUsageLimitError...}"}` on assistant rows with `finish:"error"`; legacy `part`/`message` tables have 0 cap rows.
- Known high-entropy scanner trap (next fix): `mdu-42-deploy-evidence.md` "(text refs remain)" phrasing ok; but 40-char `/tmp/...` lexemes in committed docs trip the split rule — always split at the directory slash as docs/design does on its own line 5.

## 2026-10-30 (mdu-40)
- POST-MDU-40 REALITY: single paid config — zen tier machinery deleted from both repos; canonical opencode.json is 20 agents, ALL opencode-go/* (no free opencode/* rows; 5 *-free agents + 3 free research agents deleted; research delegation = deep-research). Validator paid census is fail-closed (rejects any non opencode-go|xai prefix, big-pickle/free tokens, missing default_agent). Deploy default TIER=paid; --tier=zen exits 2 (retired); paid|go synonyms.
- Live model gotcha confirmed again: opencode-go/mimo-v2.5 deprecated upstream (registry listed it anyway) — paid rotation now deepseek-v4.1-flash, glm-5.2, glm-5.3, glm-5.3-flash, kimi-k2.7-code, mimo-v2.6-flash, mimo-v2.6-pro, xai/grok-4.7, xai/grok-build-0.1 (all exact-OK probed 2026-10-30). Run a live probe on EVERY model id chosen by design, before implementation (introspection 20261030-1).
- probe_models.py is config-driven now (no --map; alternates retired; map_sha256 → config_sha256; --include-xai accepted no-op; ANSI stripped from captured errors). Pre-deploy routine: `--refresh --gate --config build/opencode.json`.
- Commit-stage gotcha: `git add -A` in the overlay sweeps long-standing untracked dirs (.rollback-20260916-054427/, untracked personal skill files, gitignored runs) into the commit — stage the intended file list explicitly; restore build/ via a fresh `./build.sh` after any HEAD checkout.
- Dispatch note: per-dispatch paid override (opencode-go/glm-5.3-flash) is NO LONGER required — the paid default deployed mid-MDU-40 (20261029-2 closed). If a spawn still dies on a free-cap refusal, suspect a stale deployed config, not the repo.
- Introspector: always pass `--session-id <root session id>` in the brief — a bare run silently returns a stale session tree (20261021-4 recurred twice).

## 2026-10-30 (mdu-41)
- Paid-spawn failure ladder live in all three orchestrator mirrors (base prompt replaced the old one-up-escalation bullet; base grok mirror + overlay grokestrator got it as an additive column-0 bullet; byte-identical block pinned by 3-repo tests + docs/fallback-ladder.md + skills/mdu-lifecycle/SKILL.md line + evals/tasks/05-fallback-ladder six-case offline driver demo; evals numbering now has an 05-*).
- Scanner path-lexeme trap hit twice more (new design doc + new overlay test file): works reliably = split the path at a directory slash across lines, or build the path from an existing constant; lexemes as short as 32 chars trip it. Also: grepping a staged diff for that pattern innocent hits diff file headers (`b/build/claude/agents/…`) — restrict manual scans to `^\+` lines.
- Overlay repo has NO local scripts/lib/secret_scan.py but its pre-commit hook runs the base scanner anyway — overlay commits are gated, plan 2 free minutes for a text-only fix cycle.
- Child-subagent sandbox regression this loop: code-reviewer AND qa ran with shell hard-denied in the same MDU (reviewer correctly refused to fake gate runs). Reactive fix: orchestrator runs the 4 gates itself and re-issues the verdict. Durable fix waiting on introspection apply-now 20261030-2: briefs must state "shell denied by design / static-trace scope + gate outputs attached" BEFORE dispatch.
- The overlay repo has NO `scripts/lib/secret_scan.py`; only the base scanner exists (and the overlay prompt wrappers re-exec only validate.py). Overlay commits therefore run the secret gate as the manual `secret-scrub` checklist on the staged diff (applied mdu-43, clean).
- `timeout 60 opencode models` catalog output still lists deprecated/dead IDs (e.g. mimo-v2.5, commented out of config/model-registry.txt in mdu-43); the catalog is NOT a liveness oracle — probe_models.py live probes are.

## 2026-10-30 (mdu-44)
- Design docs must write repo paths WITHOUT the absolute workspace prefix — use a `$WORKSPACE`-style variable (20261030-5); the secret-scan high-entropy rule flags 32+ char [A-Za-z0-9+/] runs regardless of credential content, and the fixed rule costs a fix cycle (base scanner runs it), so write it clean the first time (20261024-1 style: also survey-proof design docs to the read-file range).
- Post-mdu-44 overlay layout: overlay root prompts/ contains exactly grok-plan.md; root grok/agents/ = 18 LIVE grok profiles; dead copies no longer exist — do not recreate shadow copies at overlay root.
- process slip to watch: mdu-44 finalized the manifest AFTER QA again (20261027-3 regression facet #2); apply-before-QA is the rule and QA/introspector should be dispatched against the finalized file.

## 2026-10-31 (mdu-45)
- Registry convention: every grok/agents/*.md needs a same-name agent in the merged build-tree opencode.json (census in validate.py, allowlist research only, dated). grok-review was REGISTERED (user ruling) on xai/grok-build-0.1; base 21 agents / 12 prompts / 20 grok profiles; merged overlay 43 agents / 41 profiles.
- probe_models.py config_sha256: ANY opencode.json agent addition invalidates the committed probe report — mandatory --refresh --gate from both repos follows every registry change (D11 runbook step; caught live in mdu-45).
- Test-writing rule (review-derived): a validator-wiring test pinning rc==1 alone is vacuous if an unrelated validator error also fires — assert the emitted error text in captured stdout (capsys) as well as rc.
