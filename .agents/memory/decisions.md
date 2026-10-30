---
type: decisions
created: 2026-10-27T13:24:20Z
updated: 2026-10-30T15:55:00Z
---

# Decision log

## 2026-10-27 — Question-tool failures: harness 60-min pending-question hard-kill; agent-definition mitigation (mdu-35)
- Context: sprite_generator sessions showed every question call failing ("Asked N questions" red, no prompt). Evidence (runs/mdu-35-question-tool/evidence.md): 42 sprite question calls = 30 completed / 12 error; 15/18 inline-era error calls machine-wide are unanswered questions killed at 60.0-61.0 min with `Tool execution interrupted` and no requeue; secondary benign mode = 3 schema-shape rejections that self-correct on retry. Agent-definition/config NOT defective (opencode.json allows question for `*`; no timeout knob exists).
- Decision: fix at the layer we own — QUESTION TOOL discipline clause (ask/batch early, post-pause dead-question check, abort → restate questions inline as numbered plain text, dead question = dropped approval gate never consent) landed byte-identical in base `prompts/orchestrator.md`, base `grok/agents/orchestrator.md`, overlay-root `grok/agents/grokestrator.md`, plus two validator fuse tuples and a pinned adjacency test. Upstream bug-report DRAFT kept unfiled (appendix A, do-not-file marker).
- Consequences: deployed live to all three CLIs next session; the 60-min kill itself is OpenCode-native and remains (user accepts it as workable — adapt by answering/re-asking on return; do not treat a killed question as consent). Filing upstream requires an explicit future user instruction.

## 2026-10-27T14:32:09Z — Canonical resume-block emission: fenced-json template, emissions-only strictness (mdu-34)
- Context: resume blocks were emitted in three shapes (JSON/key:value/prose); variance cost the next session lookup time and blocked validation. MDU-34 resume block + design doc D1-D7.
- Decision: one canonical fenced-json block (11 required keys + optional notes) emitted byte-identically in base prompts/orchestrator.md, base grok/agents/orchestrator.md, overlay-root grok/agents/grokestrator.md; validator scripts/lib/resume_block.py (validate subcommand, exit 0/1/2) and docs/resume-block.md as the single documented source; emission-only — the read-permissive recognition clause ("by purpose, not by header or exact phrasing") survives verbatim and the validator's fail message itself states prose/key:value remain valid gate input. No build.sh wiring for the validator (nothing in-tree is a resume block).
- Consequences: next sessions should emit the canonical shape; prose inputs stay accepted with no narrowing; test_mdu_34 (25 cases) + MDU-28 span test enforce three-way parity; seed capture resolved via D5's representative fallback (seed paste arrived canonical-shaped JSON).

## 2026-10-27T22:20:00Z — Overlay adopts the two-tier deploy; zen default downgrades the two OpenCode xai agents (mdu-36)
- Context: base MDU-33 shipped two-tier (zen default / go switch-up) but the overlay build and deploy never adopted it (documented debt), and the overlay deploy.sh had a grok-dir edge that aborted/mis-counted dry-runs.
- Decision: overlay build synthesizes build/zen-model-map.json = base map + xai/*-only big-pickle fallback, fail-closed for any other unknown model, and deploy.sh ports the --tier contract with zen active by default. The two OpenCode xai agents (grok-architect, grok-code-reviewer) therefore run on opencode/big-pickle in the active default tier, visible via an aggregated warn line; switch up with --tier=go.
- Consequences: live deploy runs twice, idempotent; QA PASS A-H landed via a free-tier rotation after mid/premium QA model outages (suggestion 20261027-2); manifest pre-finalized before QA (20261014-5 protocol first fully clean run). Live deploy of MDU-34/35 shipped clauses also completed in this session (dry-run + --force, all checks green).
## 2026-10-28 — Rotate dead nemotron-3-ultra-free to big-pickle + lightning-free (mdu-37)
- Context: Upstream killed opencode/nemotron-3-ultra-free while the OpenCode registry still listed it "active"; the Zen map routed 12 agents to it.
- Decision: kimi-k2.7-code row → opencode/big-pickle; mimo-v2.5 row + deepseek-research → opencode/nemotron-3.5-lightning-free; refresh alternates/registry with live-probed models only.
- Consequences: Free-tier load spread over two models; registry "active" status is untrusted — live-probe before adding any model to the map; pre-spawn model-health probe is a backlog candidate.

## 2026-10-29 — Live model-health gate is now pre-deploy (mdu-38)
- Context: mdu-37 burned three subagent spawns on a registry-"active" dead model; nothing ran inference before trust.
- Decision: scripts/lib/probe_models.py --refresh/--gate (exact-match OK probe, canonical map hash, dated report); base deploy warn-only, overlay deploy hard-gates with --skip-probe escape; CI stays CLI-free.
- Consequences: no map edit lands without a green probe (--gate red on hash mismatch); report files gitignored both repos; refresh --gate is the routine pre-deploy command.

## 2026-10-29 — Free-tier quota crisis: paid-first strategy decided by user (mmo session)
- Context: opencode drastically tightened Zen/free caps (drastic even with a Go subscription); in the user's mmo session the grok-architect spawn died on an opencode free-tier limit.
- Decision: root cause = deployed zen default tier remaps ~40/50 agents (all opencode-go/* and xai/grok-* via the mdu-36 fallback) onto opencode/big-pickle, crowding ONE free model until it caps; xAI API/auto-top-up was never involved (agent ran through OpenCode). User strategy: default tier becomes paid — Go models for OpenCode agents, xai/grok via API key for grok-family, zen demoted to emergency tier with tiny explicit free-exempt list; free models must never be a loop default.
- Consequences: backlog gained MDU-39 (cap forensics), MDU-40 (paid default tier), MDU-41 (free-budgeting policy); `grok-*` agents in the OpenCode harness will be rebuilt to actually hit the paid xAI endpoint; mmo-session cap evidence to be pinned next session.

## 2026-10-29 — HARD RULE: grok-named agents must use XAI account models (user, effective now)
- Context: mdu-36's overlay zen fallback sent xai/grok-* agents to free opencode/big-pickle, causing the mmo cap burn.
- Decision: every agent whose name starts with grok- (plus grokestrator, grok-plan) must resolve to xai/* billed to the user's xAI account, in every tier/harness; xai/* is exempt from every zen/go/free remap; validator + deploy gates fail named on violations; mdu-38 probe covers xai models.
- Consequences: MDU-42 added at the HEAD of the backlog queue (commit 60280b7), runs before MDU-39/40/41; the mdu-36 decision's 'xai-only big-pickle fallback' is now a superseded defect to remove.

## 2026-10-29 — Grok agents pinned to xai account models, four enforcement layers (mdu-42)
- Context: user hard rule after the mmo cap burn; mdu-36's 'xai-only big-pickle fallback' marked superseded (that entry stays appended, never rewritten).
- Decision: enforce in four layers — validator clauses in both variants, deploy gates in both repos (base hard both tiers; overlay hard on --force over active+parked before install), probe_models.py --include-xai gate, and the mirrors delegation sentence; overlay build xai/* identity pass-through ends the big-pickle fallback.
- Consequences: xAI account is the billing surface for all grok-family spawns; missing xai auth refuses via the named gates (no runtime fallback); live deploy verified 20/20 grok-named agents on xai/* in both installed tiers with xai/grok-4.7 and grok-build-0.1 both probing OK; free zen targets still cap-fail so the documented --skip-probe escape carried the deploy until MDU-40 makes the paid tier default.

## 2026-10-30 — Single paid config; zen tier retired; free models removed everywhere (mdu-40)
- Context: MDU-39's cap forensics (daily account-shared cap, 18-agent big-pickle concentration) + user strategy (paid over free pain). Design forks put to the user: default-tier strictness → "Remove them"; zen exempt list → "None at all"; both answered 2026-10-30.
- Decision: canonical opencode.json = the only tier (20 agents, all opencode-go/*, orchestrator on mimo-v2.6-flash after mimo-v2.5 proved dead upstream). Zen machinery (gen_zen_config, zen-model-map, two-file deploys, parked tier) deleted in BOTH repos; --tier=zen exit 2; probe/gate config-driven (config_sha256); validator paid census fail-closed; three orchestrator mirrors paid-only with two byte-identical parity sentences pinned by tests.
- Consequences: MDU-41 becomes cap-error/fallback policy for paid spawns (no in-config free usage remains). The mdu-36 "overlay zen map synthesis" and mdu-38 "probe targets = zen map" decisions are superseded (older entries stay). New apply-now: design-time live probes (20261030-1); pass --session-id to introspector runs.

## 2026-10-30 — Paid-spawn failure ladder across all three orchestrator mirrors (mdu-41)
- Context: post-MDU-40 the old free-quota-budgeting MDU-41 entry was moot (zero free usage remains); user answered two design forks 2026-10-30: ladder = one retry → exactly one rotation (verified 7-model list; a role-rung escalation counts as the rotation) → stop+escalate for `opencode-go/*` spawns, and xai/* gets NO ladder (auto-top-up ⇒ errors are auth-shaped; direct escalation with evidence).
- Decision: byte-identical 7-line block in base prompts/orchestrator.md (replacing the old one-up-escalation bullet), base grok/agents/orchestrator.md and overlay-root grok/agents/grokestrator.md (additive column-0 bullets); same wording copied into skills/mdu-lifecycle/SKILL.md (third policy copy); "never substitute a free model" guard stated explicitly as drift armor. Architect mirrors gained the design-time live-probe clause (apply-now 20261030-1) + a research→deep-research delegation fix; all three orchestrator mirrors gained the introspector `--session-id` sentence (20261021-4). docs/fallback-ladder.md documents the ladder; evals/tasks/05-fallback-ladder/ six-case offline driver demo replaces the impossible "live cap-error spawn" AC.
- Consequences: parity/tests — base 541 + overlay 148 rows green (test_mdu_40's free-model check narrowed to tolerate the sanctioned prohibition); rotation-list maintenance = 3 mirrors + docs + skill + driver in one commit (D4). Left as MINOR/followups: overlay grokestrator lacks the base free-model-span helper; config/model-registry.txt still lists dead opencode-go/mimo-v2.5; devops/code-reviewer mirrors have stale `research` delegation wording (D5 out-of-scope). New apply-now 20261030-2: reviewer briefs must scope static-only + attach gate outputs and never REJECT on a tool denial.

## 2026-10-30 — Registry dead rows are commented, never deleted (mdu-43-hygiene-sweep)
- Context: opencode models still lists mimo-v2.5/-pro while the MDU-40 live probe proved the family deprecated; the registry snapshot must stay reference-checked for other models.
- Decision: comment the two rows with a dated kill note (load_registry ignores # lines) instead of deleting; a blind `opencode models >` refresh would resurrect them, so the refresh caveat is a recorded follow-up (docs/model-registry.md MINOR). Same-family IDs without probe evidence (mimo-v2.5-pro) carry the note's "never reference or re-activate" intent and a no-probe caveat in the manifest.
- Consequences: test pins (tests/test_mdu_43_hygiene.py) forbid active mimo-v2.5 rows; `--live` drift will show the two IDs as catalog-only info noise, expected.

## 2026-10-30 — Dead overlay-root same-name copies vs live root-added agents (mdu-43-hygiene-sweep)
- Context: MDU-43 found bare `research` wording in dead overlay-root prompts/{architect,devops,ui-ux-designer}.md (ignored by build, left untouched by decision) AND in the LIVE overlay root grok/agents/grok-architect.md (deployed!) — the two classes needed opposite handling.
- Decision: rule of thumb recorded — an overlay root prompt/grok file whose name also exists in the base is DEAD (agent definition lives in base + overlays/); a root file naming an agent the base lacks (grok-architect, grok-research, grokestrator) is the LIVE source and must be edited directly.
- Consequences: grok-architect.md fixed live (11 new overlay tests? no — pin is base-side; overlay verified via build copy grep); dead-copy cleanup (delete dead root copies + the 2026-09-16 .rollback- dir) deferred to a future user-approved hygiene MDU; secret gate in the overlay remains the manual secret-scrub checklist (no scripts/lib/secret_scan.py there).
