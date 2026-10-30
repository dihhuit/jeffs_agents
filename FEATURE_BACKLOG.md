# Feature Backlog — Bootstrap the Agent Team to the Bleeding Edge

**Date:** September 2026
**Source:** [GAP_ANALYSIS.md](GAP_ANALYSIS.md)
**Consumers:** this repository's own `orchestrator` agent (OpenCode / Grok / Claude variants)

---

## How to Use This Backlog

This backlog is written so the repo's **current** agent definitions can build the **next generation** of themselves. Feed it to the orchestrator:

> "Work through FEATURE_BACKLOG.md in priority order (P0 → P1 → P2), one MDU at a time. For each MDU run the full closed loop: design → implement → review → test → deploy → validate → commit & push. Decompose each item further as needed — they are intentionally coarse."

**Backlog conventions:**

- **Priority:** P0 = correctness/critical, P1 = autonomy, P2 = provability/safety/polish.
- **MDU = Minimum Deployable Unit** — each item must be fully designed, implemented, reviewed, tested, and validated before the next starts.
- **Acceptance criteria are the contract** — QA must be able to grade PASS/FAIL against them from the repo alone (no external services required unless stated).
- **Suggested agents** tell the orchestrator which of the current variants to use (e.g., `just-code`, `test-agent`, `architect`, `devops`, `qa`).
- **Dependencies** gate ordering; items with no dependencies can be parallelized.

---

## P0 — Prove It Works (correctness of the artifact itself)

### MDU-01 · Live model-registry drift check (critical — proven broken)

- **Why:** Two research agents currently fail at runtime: `opencode/deepseek-v4-flash-free` and `opencode/north-mini-code-free` no longer exist. Nothing catches this.
- **Description:** Extend `scripts/lib/validate.py` (or add a companion script) so the build validates every `model:` reference in `opencode.json` and every Grok frontmatter model against a **live model registry**. For OpenCode: query the configured API/registry for available models (or maintain a pinned, dated allowlist file with a freshness check). For Grok: keep the existing allowlist but emit a warning when a configured model is untested. Add a `--check-live` flag, and make the normal `./build.sh` fail on **stale** references found via a bundled registry snapshot, warning (not failing) when offline.
- **Acceptance criteria:**
  1. `./build.sh` fails (or warns per policy) when a model reference is not in the registry snapshot.
  2. The offending models above are fixed in `opencode.json` (use current equivalents, e.g. available free-tier IDs) or documented as deprecated with a replacement.
  3. A `docs/model-registry.md` lists every model used, its tier, and its last-verified date.
  4. `validate.py` unit tests cover: valid ref, stale ref, missing ref, offline mode.
- **Suggested agents:** just-code (impl), test-agent (tests), code-reviewer-pro (config/security review), qa (validation).
- **Dependencies:** none.

### MDU-02 · CI pipeline for agent definitions

- **Why:** There is no `.github/` at all; validation only runs locally. Recruiters and users must see automated checks.
- **Description:** Add a GitHub Actions workflow that runs on push/PR: `build.sh` → `validate.py` (including live-model check) → markdown lint of `prompts/` → JSON schema check of `opencode.json` against the pinned OpenCode config schema → YAML frontmatter check on `grok/agents/*` → a smoke test that attempts to spawn each agent type dry-run. Add status badges to the README.
- **Acceptance criteria:**
  1. `.github/workflows/ci.yml` runs all checks and passes on `main`.
  2. README shows CI badges (build / validate / lint).
  3. A deliberately broken commit (stale model) is demonstrated to fail CI.
  4. CI completes in under 3 minutes (cheap runner, no paid services).
- **Suggested agents:** devops (pipeline), just-code (config), test-agent (smoke scripts), qa (validation).
- **Dependencies:** MDU-01.

### MDU-03 · Definition hygiene & config normalization

- **Why:** `qa`, `qa-pro`, `qa-free` still use the legacy `tools` block while all other agents use `permission`; inconsistent tooling hints; stray untracked `deepseek_error.png` in repo root.
- **Description:** Migrate the three QA agents to the `permission` style, matching sibling agents (read/grep/glob/webfetch/websearch allowed; edit/write denied or allow-only-in-scratch; bash restricted). Remove the stray PNG (or move to `docs/` if it illustrates a real incident). Normalize descriptions to a consistent tense/format. Add a JSON Schema file for `opencode.json` (documenting the config contract) in `docs/` or `schemas/`.
- **Acceptance criteria:**
  1. No agent mixes `tools` and `permission` styles.
  2. `qa`/`qa-pro`/`qa-free` have explicit, least-privilege permissions documented and tested by `validate.py`.
  3. Repo root is clean (no stray binaries/images; git status clean after commit).
  4. Schema file exists and `validate.py` uses it in CI.
- **Suggested agents:** just-code (config edits), code-reviewer (permission correctness — security-sensitive), test-agent (schema tests), qa (validation).
- **Dependencies:** none.

---

## P1 — Make It Autonomous (self-contained loop capabilities)

### MDU-04 · Lightweight persistent memory convention

- **Status:** Done — 2026-10-21

- **Why:** Every session starts from zero; long projects lose context; no resume story.
- **Description:** Define a dependency-free memory convention consumed by the orchestrator and subagents:
  - `.agents/memory/` directory: `project.md` (stable facts), `decisions.md` (ADR-lite entries), `session-<id>.md` (per-session log).
  - YAML frontmatter convention (`type`, `created`, `updated`) + append rules ("never rewrite history, append only").
  - Orchestrator prompt update: on session start, read `project.md`/`decisions.md`; after each MDU, append a summary; on interruption, write a `checkpoint` entry so the next session resumes.
  - Prompt updates in `prompts/orchestrator.md` + mirrored `grok/agents/orchestrator.md` (files are dual-authored; Claude regenerates at build).
  - Document mem0/Letta as the optional heavy upgrade path.
- **Acceptance criteria:**
  1. A fresh session with the updated orchestrator reads existing memory files and references project facts in its plan.
  2. Completing a mock MDU writes a session file + checkpoint entry automatically.
  3. Resume test: interrupting a multi-step task and restarting produces a plan that continues from the checkpoint (no re-derivation).
  4. `README.md` documents the memory convention.
- **Suggested agents:** architect (design the convention), just-code (prompt edits), test-agent (resume simulation test), qa (validation).
- **Dependencies:** none.

### MDU-05 · Seed a real skills library

- **Why:** `skills/` is empty while "Agent Skills" is a 30+ tool open standard (SKILL.md + progressive disclosure).
- **Description:** Author 4–6 high-value skills in the open Agent Skills format (dir + `SKILL.md` with `name`/`description` frontmatter and focused markdown body + optional `scripts/`/`references/`):
  1. `mdu-lifecycle` — the MDU closed-loop checklist (used by just-code/qa).
  2. `code-review-checklist` — the code-reviewer's security/style rubric.
  3. `webapp-verification` — Playwright-first browser verification recipe for QA.
  4. `test-patterns` — property-based/fuzz/edge-case patterns for test-agent.
  5. `secret-scrub` — scan diff for hardcoded secrets before commit (see MDU-11).
  6. `git-autonomy` — branch/commit/PR hygiene for autonomous runs.
  Wire the prompts to reference skills where relevant ("if the `xxx` skill is available, load it"). Deploy skills in `deploy.sh` (already handled for OpenCode; extend for Grok/Claude).
- **Acceptance criteria:**
  1. `skills/<name>/SKILL.md` exists for each, frontmatter-validated by `validate.py`.
  2. At least one prompt references a skill by name with a load condition.
  3. `deploy.sh` installs skills to all three CLIs and a dry-run log proves it.
  4. QA can activate a skill in a fresh session and follow its checklist.
- **Suggested agents:** architect (skill design), just-code (skill authoring), test-agent (validation tests), devops (deploy), qa (validation).
- **Dependencies:** MDU-03 (for validate.py extension).

### MDU-06 · MCP reference configuration & browser verification path

- **Why:** QA prefers Playwright MCP but nothing configures or documents MCP; the browser verification path is unsupported.
- **Description:** Ship a reference `.mcp.json` (or `docs/mcp.md` + config snippets per CLI) covering: Playwright MCP (browser verification), filesystem MCP (scoped), GitHub MCP (PR operations), and optionally a memory server. Document per-agent scoping (which servers each agent may use). Update `qa` prompt to specify exact server names and a concrete fallback chain (Playwright MCP → browser-os MCP → CLI + screenshots → BLOCKED report). Document remote MCP via SSE for shared servers.
- **Acceptance criteria:**
  1. `docs/mcp.md` documents server choices, install commands, and per-agent scoping for all three CLIs.
  2. QA prompt's browser preference order is concrete and testable (server names + package names).
  3. A local smoke run proves Playwright MCP can navigate, snapshot, and screenshot a local page when configured.
  4. No hard dependency on external servers — repo remains usable without MCP (documented degradation).
- **Suggested agents:** architect (integration design), just-code (config/docs), devops (install/smoke), qa (validation).
- **Dependencies:** none.

### MDU-07 · Run ledger & observability hooks

- **Why:** Zero telemetry; autonomy claims can't be evidenced; token spend unknowable.
- **Description:** Add a machine-readable run ledger:
  - `runs/<mdu-id>/manifest.json` written by the orchestrator per MDU: agents invoked, model tiers, step counts, outcomes (PASS/FAIL), fix iterations, token estimates (if derivable), timestamps.
  - Orchestrator prompt update: persist the manifest after each MDU, include it in the final summary.
  - `scripts/lib/run_ledger.py` to aggregate ledgers into `docs/runs-summary.md` (totals, success rates, cost estimates).
  - Document OTel GenAI / Langfuse drop-in integration (how to wrap subagent calls and export traces) in `docs/observability.md`.
- **Acceptance criteria:**
  1. Completing a mock MDU produces `runs/<id>/manifest.json` with all required fields.
  2. The aggregate script outputs a summary with success rate and per-tier model usage.
  3. `docs/observability.md` exists with a working export example.
  4. Ledger files are gitignored by default (or namespaced) so personal runs don't pollute the public repo — but a sample ledger lives in `examples/runs/`.
- **Suggested agents:** architect (schema), just-code (ledger + script), test-agent (schema/serialization tests), qa (validation).
- **Dependencies:** MDU-04 (memory dir conventions can host the ledger).

---

## P2 — Make It Provable & Safe (evals, security, polish)

### MDU-08 · Golden evaluation suite

- **Why:** Nothing evaluates the agent definitions themselves; regression is invisible.
- **Description:** Create `evals/` with a golden task set (5–10 realistic tasks across domains: REST API, CLI tool, UI page, config change, bugfix) each with: task statement, acceptance criteria, and expected artifacts. Add a `run-evals` skill (or script) that runs the tasks against the current definitions in a scratch workspace and records PASS/FAIL per task. Wire a smoke subset into CI (MDU-02) so every PR to `prompts/` re-runs the golden suite.
- **Acceptance criteria:**
  1. `evals/README.md` documents the suite and how to run it (one command).
  2. All golden tasks are executable in a scratch workspace with no external paid services.
  3. CI runs at least 2 smoke evals and reports pass/fail as a check.
  4. Results land in `runs/` ledger format (MDU-07).
- **Suggested agents:** architect (task design), just-code (task scaffolding + runner), test-agent (scoring checks), devops (CI wiring), qa (grading methodology).
- **Dependencies:** MDU-02, MDU-07.

### MDU-09 · Prompt regression gate (eval-driven prompt dev)

- **Status:** Done — 2026-10-21

- **Why:** Prompt edits are unmeasured; "improvements" can silently degrade behavior.
- **Description:** Add a lightweight comparison flow: before changing a prompt, `just-code` (or the orchestrator) snapshot-diffs the golden-eval results (MDU-08) for the old vs new prompt on the affected eval tasks; a prompt change that regresses ≥1 golden case is rejected by the orchestrator (or CI on PR). Implement as a documented workflow + optional promptfoo config (`evals/promptfoo.yaml`) for teams that want the standard tool.
- **Acceptance criteria:**
  1. A documented "prompt change protocol" exists in `evals/README.md`.
  2. CI (or the orchestrator) can demonstrate a prompt change rejected due to golden-case regression.
  3. promptfoo config is valid and runs against ≥3 eval tasks.
- **Suggested agents:** architect (protocol design), test-agent (regression harness), qa (validation).
- **Dependencies:** MDU-08.

### MDU-10 · Checkpoint/resume protocol for long-running work

- **Status:** Superseded by MDU-28 (session boundaries and resume block protocol) — 2026-10-24
- **Why:** The current "Session Checkpoint" guardrail is a safety valve, not a resume primitive; interrupted autonomous runs lose everything.
- **Description:** Define a checkpoint format (plain markdown checkpoint file per MDU: goal, completed steps, current step, artifacts, next actions, blockers) and add orchestrator rules: write a checkpoint after every completed phase and before any human-escalation; on session start, if a checkpoint exists for an incomplete MDU, resume from it. Coordinate with MDU-04 memory. Optional: document host-level resume (e.g., Claude Code `--resume`, opencode session persistence) in the README.
- **Acceptance criteria:**
  1. Interrupting a task mid-MDU and restarting yields a plan that resumes exactly (tested, MDU-04 resume test extended).
  2. Checkpoint files follow the documented format and are validated by `validate.py` if committed.
  3. README documents which hosts support native resume and how this convention complements them.
- **Suggested agents:** architect (protocol), just-code (orchestrator prompt), test-agent (resume tests), qa (validation).
- **Dependencies:** MDU-04.

### MDU-11 · Secret scanning & leak prevention in the loop

- **Status:** Done — 2026-10-21
- **Why:** Permissive autonomous agents can commit secrets; no guardrail exists.
- **Description:** Add `secret-scrub` skill (MDU-05) with rules: before any commit, scan the diff for high-entropy keys, `AKIA*`, `sk-*`, private keys, `.env` values; flag or auto-redact; never print full secrets in logs. Update the orchestrator's commit gate and `just-code`'s constraints ("NEVER commit secrets; if a secret is needed, reference an env var / secret store"). Add `docs/security.md` covering: least-privilege perms, secret hygiene, sandboxing options (devcontainer profile, E2B, Firecracker as external execution), and approval gates (below).
- **Acceptance criteria:**
  1. `secret-scrub` skill exists and its checklist is followed by the commit gate.
  2. A test diff containing a realistic secret is flagged/rejected by the gate.
  3. `docs/security.md` documents the full security posture.
- **Suggested agents:** just-code (skill + gate), code-reviewer-pro (security review), test-agent (leak tests), qa (validation).
- **Dependencies:** MDU-05.

### MDU-12 · Approval gates & autonomy ladder documentation

- **Why:** Claims of "fully autonomous" need precision; destructive ops need gates.
- **Description:** Define and document an autonomy ladder (L0–L4, per industry 2026 reference) and position the team on it. Add explicit approval-gate rules to the orchestrator: always require human approval for (a) push to protected branches, (b) production deploys of non-green MDUs, (c) destructive operations (deletes, DB migrations), (d) >3 retries (existing cap, formalized). Add an `autonomy` field to the run manifest (MDU-07) recording the level at which each MDU ran. Document target: L3 goal-directed with gates.
- **Acceptance criteria:**
  1. `docs/autonomy.md` defines the ladder and the team's current vs target level.
  2. Orchestrator prompt contains explicit gate rules with the four cases above.
  3. Run manifests record the autonomy level per MDU.
  4. README section "Autonomy & Guardrails" summarizes the ladder and gates.
- **Suggested agents:** architect (ladder design), just-code (prompt edits), code-reviewer (safety review), qa (validation).
- **Dependencies:** MDU-03, MDU-07.

### MDU-13 · README modernization & artifact gallery

- **Status:** Done — 2026-10-23

- **Why:** Job-search artifact needs to sell itself: badges, gallery, quickstart, evidence.
- **Description:** Rebuild README sections: add CI badges (MDU-02); add a "What's inside" table linking each agent to its prompt and docs; add an `examples/` gallery (2–3 worked examples including a summary, manifest, and ledger excerpt from the golden evals); move the current single-item TODO into the backlog (this file); add "Autonomy & Guardrails" and "Memory & Skills" sections; link GAP_ANALYSIS.md and FEATURE_BACKLOG.md from a "Roadmap" section; add a short "How this repo was upgraded by its own agents" story (meta-narrative is the best artifact).
- **Acceptance criteria:**
  1. README renders correctly on GitHub (links, badges, no broken anchors).
  2. Every agent listed in the roster has a clickable prompt link.
  3. `examples/` contains ≥2 complete worked examples with real manifests/ledgers.
  4. Roadmap section links both analysis docs.
- **Suggested agents:** ui-ux-designer (structure), just-code (content), qa (link/badge verification with a fresh clone).
- **Dependencies:** MDU-02, MDU-07, MDU-08.

### MDU-14 · Cross-CLI parity & contract tests

- **Why:** OpenCode/Grok/Claude definitions can drift; the build generates Claude but nothing verifies behavioral parity.
- **Description:** Add a parity check to `validate.py`: for each `prompts/*.md` vs `grok/agents/*.md`, verify that key behavioral clauses (responsibilities, hard constraints, safety constraints) are present in both (fuzzy keyword checks, not exact match). Fail on missing sections. Optionally add a smoke test that generates Claude agents (existing generator) and verifies frontmatter parity with the source. Document the "dual-authoring" contract (README already partly covers it).
- **Acceptance criteria:**
  1. `validate.py` parity checks pass for all current pairs.
  2. Removing a constraint clause from one side is caught as a test failure.
  3. Build regenerates Claude agents with identical frontmatter counts (26) as documented.
- **Suggested agents:** just-code (validator), test-agent (parity tests), devops (CI wiring), qa (validation).
- **Dependencies:** MDU-02, MDU-03.

### MDU-15 · Cross-CLI run-ledger conformance (schema-inline + re-validation)

- **Status:** Done — 2026-10-21
- **Why:** The 2026-09-16 headless cross-CLI test (opencode/grok/claude on the same golden task) proved the harness-provenance feature works — all three recorded `harness` correctly — but also caught the ledger schema drifting per CLI: opencode omitted `title`/timestamps and used `qa_grade: "manual-smoke-pass"`; grok never finalized (`in_progress`, null verification); claude used `status: "complete"` + `build: "n/a"`. Root cause: the orchestrator prompt references `docs/observability.md` for the schema, which subagents cannot read in a bare scratch dir. Grok also revealed a session-finalization gap (its run exited 0 but the git-commit phase and ledger finalization never landed).
- **Description:** Inline the run-manifest contract (required fields + enums + one compact example) directly into the orchestrator prompt (both `prompts/orchestrator.md` and `grok/agents/orchestrator.md`), so any CLI can conform without external docs. Re-run the golden cross-CLI task (reuse `evals/tasks/` "sumdump"-style task or the same golden prompt) through all three harnesses and require: manifest validates on `run_ledger.py validate`, git commit present in all three, final status `completed`. Add a `manual-smoke-pass`→`PASS` normalization rule and the `complete`/`completed` alias question to the prompt. Also document the claude headless permission flag (`--dangerously-skip-permissions`) and re-test grok session finalization (its workflow runner cutoff the final phase).
- **Acceptance criteria:**
  1. Orchestrator prompt (both mirrors) embeds the full manifest schema inline (fields, enums, example), no doc lookup required.
  2. Re-running the golden task headless on all 3 CLIs yields manifests that pass `run_ledger.py validate` with `harness` set correctly and `status: completed`.
  3. All three workspaces contain a git commit (grok finalization fixed or root-caused).
  4. Findings + claude permission flag documented in `docs/observability.md`.
- **Suggested agents:** architect (schema-inline design), just-code (prompt edits both mirrors), test-agent (manifest conformance tests), devops (deploy + headless re-runs), qa (cross-CLI grading).
- **Dependencies:** none (uses the A-harness work already shipped; can start immediately).

---

## Suggested Execution Order

```
P0: MDU-01 → MDU-02 → MDU-03          (parallelizable after MDU-01)
P1: MDU-04 ─┬─ MDU-05                 (MDU-05 needs MDU-03)
            ├─ MDU-06                 (independent)
            └─ MDU-07                 (needs MDU-04)
P2: MDU-08 → MDU-09 → MDU-10 → MDU-11 → MDU-12 → MDU-13 → MDU-14
    (MDU-08 needs 02+07; MDU-12 needs 03+07; MDU-13 needs 02+07+08; MDU-14 needs 02+03)
```

Each MDU above is sized for the repo's own orchestrator to complete in one closed-loop pass. Decompose further if any item exceeds ~10 minutes of subagent runtime — that's a sign it needs splitting.

---

## Definition of Done (applies to every MDU)

- [ ] Design recorded (design doc or ADR-lite entry in `.agents/memory/decisions.md`)
- [ ] Implementation done by a `just-code` variant; **no test-file edits by just-code**
- [ ] Code review sign-off from `code-reviewer`/`code-reviewer-pro`
- [ ] Tests written by a `test-agent` variant and passing
- [ ] Build/deploy succeeds (via `devops` where infrastructure is touched)
- [ ] QA PASS graded against this file's acceptance criteria
- [ ] Committed and pushed with a descriptive message referencing the MDU ID

### MDU-32 · Cheaper replacement for glm-5.2 on OpenCode Go

- **Status:** Done — 2026-10-24 (no-op with rationale; comparison table in `docs/model-registry.md` § Cost audit — glm-5.2 premium agents)
- **Why:** `opencode-go/glm-5.2` powers `just-code-pro`, `code-reviewer-pro`, `architect`, `architect-premium`, and `devops-pro` and is the single largest driver of credits spend beyond the $10/mo subscription.
- **Description:** Audit the available models in the OpenCode Go catalog (OpenCode Console → Models for the Go workspace) for a model with equivalent or near-equivalent capability at lower cost. Compare against current usage patterns (design-heavy, security review, complex refactors, multi-service deploys). If a suitable replacement exists, update `opencode.json`, orchestrator prompts (both mirrors), `docs/model-registry.md`, `README.md`, and `config/model-registry.txt`. Keep `architect-premium` reasoning needs in mind (may need to stay on a top-tier model even if others drop). If none exists at meaningfully lower cost with acceptable capability, document findings in `docs/model-registry.md` and close as "no-op with rationale".
- **Acceptance criteria:**
  1. Comparison table written to `docs/model-registry.md` with model, tier, input/output pricing (if available), and fit assessment for each of the 5 agents.
  2. If replacing: all references updated consistently, `./build.sh` passes, parity maintained, prompt-regression gate passes.
  3. If not replacing: explicit rationale documented, no functional changes made.
  4. Run manifest created and validated.
- **Suggested agents:** architect (capability/cost analysis), just-code (config/prompt updates if needed), test-agent (regression checks), qa (validation).
- **Dependencies:** none.

### MDU-33 · Zen-only variant set (two tiers: Zen default, Go switch-up)

- **Status:** Open — 2026-10-24 (scope clarified same day)
- **Why:** The current `opencode.json` assumes an OpenCode Go subscription for most agents. Users without a Go subscription need a parallel set using only free Zen models (`opencode/*`). **Scope clarification (2026-10-24, user):** the user has repeatedly hit Zen usage limits, so this is a **two-tier setup, not just a Go-free fallback** — run the Zen tier by default, and switch up to the Go tier when a session runs out of Zen usage for the period. Switching between tiers mid-period must be a first-class, documented workflow.
- **Description:** Create two parallel agent sets for OpenCode: a Zen-only set (free `opencode/*` models) and the existing Go-subscription set, kept side by side. Options: a separate config file (e.g. `opencode.zen.json` alongside the Go default) or a build-time flag emitting both variants. Update docs to document both paths and the switch-up workflow. Ensure parity where possible, document limitations, and add validation.
- **Acceptance criteria:**
  1. A Zen-only config exists (e.g. `opencode.zen.json`) with all referenced models in the free Zen allowlist.
  2. `./build.sh`/validation supports selecting the Zen variant (documented).
  3. README documents the two-tier setup: Zen as the default tier, the Go subscription tier as the switch-up path when Zen usage for the period is exhausted, and how to switch between them (which command/file each tier uses).
  4. Run manifest created and validated.
- **Suggested agents:** just-code (config/docs), test-agent (validation), qa (validation).
- **Dependencies:** MDU-01 (model registry).

### MDU-34 · Canonical resume-block format (emit-strict, read-permissive)

- **Why:** Resume blocks are emitted in three different shapes today — a JSON object, a flat `key: value` list, and a prose paragraph. All three work because the session-boundary gate recognizes a resume block *by purpose, not by header or exact phrasing*, but the variance costs the next session time (hunting for the commit SHA, branch, and artifact paths), makes resume blocks unvalidatable, and is the same cross-CLI drift problem MDU-14 and MDU-15 fixed for prompts and run manifests.
- **Description:** Define one canonical machine-readable block and a validator, without narrowing what the gate accepts as input:
  - Canonical shape: a fenced `json` object carrying the gate's own key list — `mdu_id`, `branch`, `commit_sha`, `harness`, `status`, `done[]`, `next[]`, `blocked_on[]`, `design`, `backlog`, `artifacts[]`, plus optional `notes`.
  - **Emit-strict:** all three orchestrator mirrors must produce exactly this shape — base `prompts/orchestrator.md`, base `grok/agents/orchestrator.md`, and overlay `grok/agents/grokestrator.md` (the three-file rule; the overlay orchestrator does not inherit the base Grok profile).
  - **Read-permissive (non-negotiable):** the existing recognition language — "recognize a resume block by purpose, not by header or exact phrasing", and the rule that a first-turn prose or `key: value` block also counts — must survive verbatim in all three mirrors. Standardizing emission must never turn the gate into a strict parser that rejects a hand-written block.
  - Ship `scripts/lib/resume_block.py` (validate a pasted block: report missing/extra keys, exit non-zero on a required-key miss) and document the shape plus one real prose fixture in `docs/resume-block.md`.
  - Note in the docs which fields the next session actually consumes (branch, commit SHA, `next[]`, `blocked_on[]`) versus which are bookkeeping (harness, status, artifacts).
- **Acceptance criteria:**
  1. The canonical shape is documented in exactly one place (`docs/resume-block.md`) and reproduced verbatim in all three orchestrator mirrors.
  2. A test asserts the "not by header or exact phrasing" recognition clause is still present in all three mirrors (read-permissive regression guard).
  3. `python3 scripts/lib/resume_block.py validate <fixture>` exits 0 on the canonical example and non-zero on a block missing `commit_sha`.
  4. A prose resume block captured from a real session is committed as a fixture and asserted to remain valid *input* to the gate, proving the mechanism still accepts non-canonical blocks.
  5. `./build.sh` passes, parity tests still green, run manifest created and validated.
- **Suggested agents:** architect (shape + docs design), just-code (three mirrors + template + validator), test-agent (validator, mirror-parity, prose-fixture tests), qa (validation).
- **Dependencies:** MDU-14 (parity tests), MDU-26 and MDU-28 (current gate wording; do not contradict them).

### MDU-35 · Question-tool failure deep dive (sprite_generator sessions)

- **Status:** Open — 2026-10-24
- **Why:** In the user's `sprite_generator` project sessions, every `question` tool call renders as "Asked N questions" in red with no question prompt visible to the user; the user must manually prompt the agent to retry. This breaks the interactive-question loop that `prompts/inception.md` explicitly relies on ("Use the question tool for interactive follow-ups") and wastes turns. The repo already has a known family of harness-level subagent defects (shell permission denials, cf. `sprite_generator/agent-improvements.md` 20261017-1/-5), so this may be harness, config, model tool-call shape, or agent-definition — which is exactly what needs to be determined.
- **Description:** Deep dive the failing sessions, then fix at whatever level the evidence supports:
  1. **Evidence gathering.** Locate the failing question tool calls in OpenCode session storage (`~/.local/share/opencode/...`, project dir `/mnt/FastSSDXFS/projects/sprite_generator`). Extract: exact tool call payload (params, model, session id), the error/result event, timestamps, and whether the failure is deterministic (every call) or intermittent. Confirm which agent/model/CLI actually ran those sessions (user confirmation if storage is ambiguous).
  2. **Root-cause classification.** Classify the failure as one of: (a) agent-definition (e.g. prompt or config disabling/misconfiguring the tool, `permission` block mismatch — note `opencode.json` globally allows `action: "question"` for `*`), (b) model tool-call shape (the model emitting params the tool rejects), (c) harness/TUI bug (rendering of the interactive prompt), or (d) data-dependent (payload size/format). Write the classification up with verbatim evidence in `docs/design/mdu-35-question-tool.md`.
  3. **Fix or workaround.** If (a): fix the agent definition/config, run `./build.sh` + parity + pytest gates. If (b)/(c)/(d): implement the agent-definition-level mitigation — guidance in the affected prompt(s) (e.g. "if a question tool call fails, immediately restate the questions inline as plain text instead of asking the user to retry") — keeping the three-mirror rule in mind if an orchestrator prompt is touched. Draft (do not file) an upstream issue with masked evidence for the harness case.
  4. If evidence is inconclusive at agent-definition level, close with a documented no-op + the minimal reproduction case for the harness owners.
- **Acceptance criteria:**
  1. `docs/design/mdu-35-question-tool.md` exists with: reproduction path, extracted tool-call payload(s), the exact error, a root-cause classification, and the evidence for it (or "inconclusive" with the minimal repro).
  2. If agent-definition fix: `./build.sh`, pytest, and parity gates pass; affected prompt mirrors updated consistently.
  3. If workaround-only: the retry-avoidance guidance is present in the affected agent prompt(s) and survives `./build.sh`.
  4. Run manifest created and validated.
- **Suggested agents:** explore (session-storage forensics, quick), deep-research or research (known OpenCode issues), architect (classification + fix design), just-code (prompt/config fix), test-agent (gates), qa (validation).
- **Dependencies:** none in this repo; evidence lives in the user's sprite_generator session storage.

## P0bis — Free-tier quota crisis (new strategy, 2026-10-29)

**Context (user-confirmed, live-diagnosed):** OpenCode drastically tightened free-tier (Zen) model usage caps — Zen models are heavily capped even when a Go subscription is purchased. In the user's `mmo` project session, the `grok-architect` spawn died with an opencode free-tier limit: the deployed zen default tier maps ~40 of 50 agents (all `opencode-go/*` AND both `xai/*` agents, via the mdu-36 overlay fallback) onto `opencode/big-pickle`, so all loop traffic crowds one free model until it caps out. The xAI API key + auto-top-up were not involved (the agent ran through OpenCode, which never calls xAI for those agents in the zen tier). New strategy direction set by the user: **stop using free-tier models entirely (Go tier + xAI via API key), or reduce free usage to a tiny explicit set**.


### MDU-42 · HARD RULE — Grok-named agents must use XAI account models (queue head)

- **Status:** Done — 2026-10-29 (validator+deploy gates+probe+m one-sentence mirrors landed; live deploy verified 20/20 grok-named agents on `xai/*`; QA PASS)
- **Why:** The mdu-36 overlay zen fallback routed all `xai/grok-*` agents to `opencode/big-pickle` (free) — the direct cause of the mmo free-cap burn. The user's standing rule, effective immediately: **every agent whose name starts with `grok-` (and `grokestrator`, `grok-plan`) must run on `xai/*` models billed to the user's xAI account (paid, auto-top-up) in every tier, every harness — never an opencode free/Go-substituted model.** The xAI account is the billing surface for anything grok.
- **Description:**
  1. Kill the mdu-36 `xai/*-only big-pickle fallback` in the overlay zen map layer: `xai/*` agents become exempt from every zen/go/free remap (identity or explicit `xai/grok-4.7`).
  2. Validator clause (base + overlay): any build/deploy config in which a `grok`-named agent's `model` is not `xai/*` fails with a named error. Same check at deploy time in both deploy.sh gate functions.
  3. mdu-38 `probe_models.py` gains an xai probe path (`--include-xai` or automatic for grok-mapped models) so the hard rule is enforced with live evidence, not just config inspection.
  4. Orchestrator mirrors (base prompts/grok/claude + grokestrator): one-sentence delegation rule — "Grok-named agents run on the user's xAI account models; never delegate them to a free or Go-substituted opencode model, even in the zen tier."
  5. If xAI auth is unavailable in a harness, the grok agent should refuse cleanly (error naming the missing credential), not silently fall back.
- **Acceptance criteria:**
  1. Validator + deploy-time check both fail (named error) on any config where a grok-named agent resolves to a non-`xai/*` model.
  2. Live deploy: every `grok`-named agent in the deployed opencode config resolves to `xai/grok-4.7` (or an allowlisted `xai/*`), verified by the mdu-38 gate + config inspection.
  3. Zen tier still builds and deploys (grok agents excluded from remapping by design, not by accident).
  4. mdu-38 live probe covers the xai models now in use; suite + both builds green; docs + README updated.
- **Suggested agents:** just-code (map/validator/probe/mirror edits), test-agent (clause+probe tests), devops (deploy + live verification), qa (validation).
- **Dependencies:** none (this is a hard rule, run before MDU-39 forensics and MDU-40 paid-default design).

### MDU-39 · Free-tier cap forensics & symptom-attribution ledger

- **Why:** We do not know the actual new cap economics (requests/day? tokens/day? per-model? per-account?) and cannot design a usage strategy against unknown limits. The `mmo` failure needs to be pinned to exact cap events with evidence.
- **Description:** Live-measure opencode's free-tier caps: inspect the caps/limit messages in recent degraded sessions (OpenCode storage working across repos as in mdu-35); run controlled probes to enumerate the cap surface (cheap `Reply with exactly: OK` requests until refusal, per free model id used by our agents); locate any published cap documentation; write `docs/model-registry.md` cap table + `docs/design/mdu-39-free-tier-forensics.md` with: cap shape, which models are affected, observed refusal message strings, and a per-agent audit of what routed to free models in the affected sessions.
- **Acceptance criteria:**
  1. `docs/model-registry.md` gains a dated "Free-tier caps (2026-10-29)" table: per model id, measured/observed cap, refusal strings.
  2. A forensic note in the run design doc attributes at least the `mmo` grok-architect failure to concrete cap-evidence (session id, events) or the best available evidence; agent-to-free-model audit of the current zen tier included.
  3. If the caps are undocumented/unstable, the doc says so explicitly and marks which measurements are from live probing.
- **Suggested agents:** explore/devops (evidence sweep, probes), architect (cap table + attribution), qa (grading from evidence files).
- **Dependencies:** none.
- **Status:** Done — 2026-10-30 (cap table in docs/model-registry.md with documented-undocumented finding + retracted 200/day figure; design doc additionally gives the pinned mmo attribution — grok-architect died 2026-10-29 13:12:49Z on opencode/big-pickle, respawned on xai/grok-4.7 ran clean; 68 `provider.quota` rows = 60 canonical + 8 old refusals; 2026-10-30 reset probes OK; QA PASS)

### MDU-40 · Go/xAI-paid default tier — kill zen as default (retitle: single paid config, zen retired)

- **Why:** Strategy decision (user): stop using free-tier models entirely for the working loop — paid Go models for OpenCode-native agents and `xai/grok-4.7` (direct API key with auto-top-up) for the grok-family agents — because the free cap breakage is worse than paid cost.
- **Description:** Introduce a new `paid` tier and make it the ACTIVE default everywhere (base build, overlay build, overlay deploy): OpenCode agents keep their true `opencode-go/*`+`xai/*` models (identity mapping, no zen remap); grok-family agents route to `xai/grok-4.7` (paid, API-key-authenticated); verify xAI auth works through opencode (`opencode models` shows the xai models; run the md-38 probe against xai endpoints — extend `probe_models.py` to probe xai models too). Keep zen available as an explicit emergency tier (`--tier=zen`) with a **hard tightened scope**: free models only for the small set that genuinely hurts cost (assign in design: candidates = `deep-research`/`research`/`qa-free` or none at all — decide from MDU-39's cap table). Validate the map_sha256 / gen_zen_config path keeps working so the emergency tier stays buildable.
- **Acceptance criteria:**
  1. `config/go-model-map.json` (or equivalent identity-map mechanism) ships; a `--tier=paid|go` (choose the name in design) tier builds and deploys; **the deployed default config has zero free-tier models** for loop agents.
  2. `xai/grok-4.7` wired for grok-family agents and verified live via an inference probe (`probe_models.py` extended or a `-‑probe-xai` flag; xAI calls count against the user's paid xAI balance, no opencode free quota).
  3. Live deploy with the new default tier; `opencode run` against the head/one agent probed ok; mdu-38 gate updated to cover the new tier's model set.
  4. Free-tier agents list shrunk or removed per design decision; both builds exit 0; tests + docs updated; README + model-registry docs updated.
- **Suggested agents:** architect (tier design, paid/free split), just-code (maps + probe extension + deploy wiring), devops (deploy + live verification), qa (validation), test-agent (tests).
- **Status:** Done — 2026-10-30 (single paid config in both repos; zen tier machinery RETIRED per user decision superseding this AC's "emergency tier stays buildable": gen_zen map deleted, deploy default TIER=paid, --tier=zen exit 2; 8 free-model agents removed 28→20; live-dead opencode-go/mimo-v2.5 caught by test-phase live probe → 8 agents repointed to mimo-v2.6-flash; probe config-driven with config_sha256; paid census fail-closed in validator; live deploy 42 agents 0 free rows 20/20 grok-on-xai, smokes OK; base 9d77510 + a9a8da4, overlay 33f5b47; QA PASS; 640 tests green)
- **Dependencies:** MDU-39 (cap economics to inform the free-exempt list).

### MDU-41 · Free-tier budgeting policy in agent definitions (while any free models remain)

- **Why:** Even after MDU-40, any residual free usage (emergency zen or a small free-exempt set) needs harness-side discipline so a loop can't spiral into cap death mid-MDU.
- **Description:** Update agent definitions (both mirrors) with an explicit free-quota policy: (a) orchestrator picks paid tiers for long-running phases (implement/large QA) and reserves free variants for tiny phases or emergencies; (b) on a cap-error from a free model, fallback order is documented (paid model or retry after waiting), never a naive free-variant rotation; (c) QA/test patterns for cap-error-handling branches; (d) docs section explaining the fallback ladder. Keep the changes sync'd across the opencode/grok/claude mirrors per repo conventions.
- **Acceptance criteria:**
  1. Policy blocks present in both `prompts/orchestrator.md` + `grok/agents/orchestrator.md` (+ grokestrator mirror) and any free-variant prompts (`*-free`), behaviorally equivalent.
  2. A live cap-error spawn is handled with the documented fallback in a scripted dry-run demonstration.
  3. Full suite and both builds green; QA PASS.
- **Dependencies:** MDU-40.
- **Suggested agents:** architect (policy wording), just-code (mirror edits), test-agent, qa.
- **Status:** Done — 2026-10-30 (superseded to PAID-spawn policy by the MDU-40 outcome: no free usage remains, so "free-quota budgeting" became the cap-error/fallback ladder — one retry → exactly one rotation from the verified live list → stop+escalate for `opencode-go/*` spawns; `xai/*` gets no ladder, direct escalation; "never substitute a free model" guard stated explicitly). Ladder block byte-identical in all three orchestrator mirrors; architect mirrors gained the design-time live-probe clause (apply-now 20261030-1) + research→deep-research delegation fix; introspector `--session-id` sentence (20261021-4) in all three mirrors; `docs/fallback-ladder.md` (D7); `evals/tasks/05-fallback-ladder/` scripted six-case driver demo (replaces the impossible live-cap-error AC); `skills/mdu-lifecycle/SKILL.md` ladder line; MDU-40 test freed-model check narrowed with sanctioned-prefix helper; base 541 tests + overlay 148 tests green; prompt-regression gate 7/7; live deploy (20 opencode / 41 grok / 42 claude) with installed-copy verification. QA PASS.
