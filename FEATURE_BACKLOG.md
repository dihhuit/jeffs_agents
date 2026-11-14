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

- **Status:** Done — shipped 2026-09/10 (Status line backfilled 2026-10-31 during the MDU-45 docs sweep; verified via in-repo tests and artifacts)

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

- **Status:** Done — shipped 2026-09/10 (Status line backfilled 2026-10-31 during the MDU-45 docs sweep; verified via in-repo tests and artifacts)

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

- **Status:** Done — shipped 2026-09/10 (Status line backfilled 2026-10-31 during the MDU-45 docs sweep; verified via in-repo tests and artifacts)

- **Why:** `qa`, `qa-pro`, `qa-free` still use the legacy `tools` block while all other agents use `permission`; inconsistent tooling hints; stray untracked `deepseek_error.png` in repo root.
- **Description:** Migrate the three QA agents to the `permission` style, matching sibling agents (allow read, grep, glob, webfetch, and websearch; deny edit and write or allow them only in scratch; restrict bash). Remove the stray PNG (or move to `docs/` if it illustrates a real incident). Normalize descriptions to a consistent tense/format. Add a JSON Schema file for `opencode.json` (documenting the config contract) in `docs/` or `schemas/`.
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

- **Status:** Done — shipped 2026-09/10 (Status line backfilled 2026-10-31 during the MDU-45 docs sweep; verified via in-repo tests and artifacts)

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

- **Status:** Done — shipped 2026-09/10 (Status line backfilled 2026-10-31 during the MDU-45 docs sweep; verified via in-repo tests and artifacts)

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

- **Status:** Done — shipped 2026-09/10 (Status line backfilled 2026-10-31 during the MDU-45 docs sweep; verified via in-repo tests and artifacts)

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

- **Status:** Done — shipped 2026-09/10 (Status line backfilled 2026-10-31 during the MDU-45 docs sweep; verified via in-repo tests and artifacts)

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

- **Status:** Done — 2026-09-15

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

- **Status:** Done — 2026-09-15

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

- **Status:** Superseded by MDU-40 — 2026-10-30
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

- **Status:** Done — shipped 2026-09/10 (Status line backfilled 2026-10-31 during the MDU-45 docs sweep; verified via in-repo tests and artifacts)

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

- **Status:** Done — 2026-10-26
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

## Queue — operational incident foreground (2026-10-31)

### MDU-58 · Grokception — grok-flavored Inception on the xAI provider

- **Status:** Done — 2026-11-11 (grok-inception shipped in base `opencode.json` on `xai/grok-4.7`, prompt `prompts/grok-inception.md`, no grok/agents mirror by design D2; QA PASS round 1, 5/5 ACs; both probe gates green; commits in this repo and the overlay)
- **Why:** user directive (2026-11-11): the base `inception` interview agent runs `opencode-go/deepseek-v4.1-flash` in the OpenCode harness; the user wants a grok-flavored variant ("Grokception") billed to the xAI account instead of the opencode-go one. The `grok-` name prefix triggers the mdu-42 hard rule: grok-named agents MUST resolve to xai/* account models in every tier and harness (validator clauses, deploy gates, probe coverage).
- **Description:** add a `grok-inception` OpenCode primary agent: prompt body = grok-flavored Inception (adapted from base `prompts/inception.md` — same interview/spec contract and hard constraints; Grok-family tone; role-applicability of any batch clauses judged at design); model = xai/* picked by design-time live probe (20261030-1 rule: probe every model id before implementation; candidates xai/grok-4.7 and xai/grok-build-0.1, both already allowlisted); registered in base `opencode.json` (the overlay build inherits it; merged census grows to 44 agents); permissions mirror base `inception` (edit/read allows + question tool). Explicit design fork to record: the Grok Build harness already has `inception` (grok/agents/inception.md on grok-4.7), so a second `grok/agents/grok-inception.md` profile is expected NOT to ship — if the design rules otherwise, the mdu-45 census requires its registration. Second fork: base vs overlay placement (default base — inception is generic; overlay only if the user rules personal-only).
- **Acceptance criteria:**
  1. `grok-inception` registered in base `opencode.json` on an xai/* model with design-time live-probe evidence recorded (both candidate ids probed; the chosen id exact-OK); `probe_models.py --refresh --gate` green in BOTH repos (any agent addition invalidates config_sha256 — D11 runbook).
  2. Prompt body exists at the design-chosen location; `./build.sh` passes in both repos; merged overlay census 44 agents; Claude subagent regenerated by the build.
  3. The Grok-mirror decision is recorded with rationale in the design doc.
  4. Validator grok census + paid census green (xai/* prefix exempt per mdu-42); both suites green with new registry pins (agent present, model prefix xai, census counts); prompt-regression gate 7/7 unchanged baseline; secret gate exit 0.
  5. Deploy is NOT part of this MDU's default path — installed trees refresh at the next routine deploy, or an explicit user-approved `--force` (per-action gate) if the user wants it live immediately.
- **Suggested agents:** architect (design: naming, model pick, mirror + placement forks), just-code (registry entry + prompt + pins), test-agent (pins), devops (builds + probe refresh), qa (validate).
- **Dependencies:** MDU-42 (xai hard rule + enforcement layers), MDU-45 (grok census), MDU-40 (single paid config), MDU-38 (probe gate), MDU-20 (inception promotion — behavior source).

### MDU-56 · pi harness research + port the grok agents

- **Status:** Done — 2026-11-12 (research, design, port, pins, and live smoke complete; QA pending at row-write time). Premise correction: pi = `@earendil-works/pi-coding-agent` 1.5.2 (`badlogic/pi-mono`/`@mariozechner` are legacy names). Port = generated pi template package (`build/pi/`: 20 role prompts + `/roster`, byte-verbatim bodies + adapter preamble), generator `scripts/lib/gen_pi_templates.py` hooked into `./build.sh`, Gates A–E pinned in `tests/test_mdu_56_pi_port.py` (33 cases, suite 905), parity in `docs/pi-parity.md` (30 rows). Live: `pi install ./build/pi` referenced-install (re-run after rebuild), 8/8 smoke PASS on xai/grok-4.7; `grok-build-0.1` absent from pi's xai catalog (D2 fallback operative). Docs: docs/design/mdu-56-pi-research.md + mdu-56-pi-port.md.
- **Why:** The user adopted a third harness: **pi** (`badlogic/pi-mono`, the `@mariozechner/pi-coding-agent` npm CLI — minimal terminal coding harness, extended via TypeScript extensions, skills, prompt templates, and themes bundled as pi packages; no native sub-agents; four modes: interactive, print/JSON, RPC, SDK). Only the **xAI API is registered/authenticated in pi** (`XAI_API_KEY`; pi's default xai model is `grok-4.7`). The 20 grok agent profiles under `grok/agents/*.md` (plus the grokestrator mirror) are authored for Grok Build's frontmatter format and cannot be consumed by pi — the user wants them available there.
- **Description:** (1) Research pi's customization surface in its docs — agent directory (`~/.pi/agent`), `models.json`, prompt templates vs skills vs extensions, tool/permission model, how per-role system prompts and delegations map (or fail to map, given no sub-agents). (2) Design the port: decide the pi-side artifact shape (likely a pi package of prompt templates/skills mirroring the grok profiles), what ports faithfully vs needs pi-native constructs, and whether the port is generated by the base build or a standalone script. (3) Implement the port for the grok profiles (xai-only; no other provider is registered in pi). (4) Verify against a live pi run in print mode using `XAI_API_KEY`; document what did not port.
- **Acceptance criteria:**
  1. Research doc with citation-backed facts (docs URLs + commit refs) covering the customization surface, agent dir, and provider/model selection in pi.
  2. Ported artifacts exist in-repo, are installed into the pi agent directory only after explicit user approval (per-action gate; pi is the user's machine), and a live `pi -p` smoke run loads at least the orchestrator-equivalent and one coder profile on xai.
  3. Parity notes record every grok-profile construct that did not port (e.g. frontmatter permissions) and how its intent is reproduced or consciously dropped.
  4. If a generator ships, `test-agent` pins it (idempotent output, fail on upstream profile drift); otherwise static artifacts are pinned byte-wise.
- **Suggested agents:** deep-research (pi docs), architect (port design), just-code (implementation), test-agent (pins), devops (install/live verify), qa (validation).
- **Dependencies:** user approval for any pi-side install; base-vs-overlay placement decided at design time (grok profiles are base-owned; a pi port for personal use may belong in the overlay).

### MDU-59 · Grokestrator dispatch-truth debug — "architect is on xAI / no shell" claim in suburb_sim (queue head)

- **Status:** Done — 2026-11-13 (forensics + root-cause + docs clarification shipped; clause staged, not applied). Answer: the architect DID run as a dispatched subagent — `grok-architect-premium` on `xai/grok-4.7` (child `ses_e351e3922ffeZUMTsCdTw303R8`, completed 14:09:31 UTC 2026-11-11, wrote `docs/architecture/hld.md` + ADRs 0001–0010); NOT the stock glm-5.2 architect, and no in-conversation design. Classification: correct routing, misleading disclosure — bare `architect` collides across harnesses (OpenCode = glm-5.2; base Grok mirror labels bare `architect` grok-4.7 at `grok/agents/orchestrator.md:172-173`); suburb_sim has no project override. Ship: `docs/design/mdu-59-forensics.md` (evidence + Resolution), Dispatch-truth clause staged `status: not applied` for all three orchestrator mirrors (user decision 2026-11-13: docs + proposal via apply path), dormant pin `tests/test_mdu_59_dispatch_truth.py` (skips until the clause lands, hardens to all-three-mirrors on partial apply). Suite 967 passed / 1 skipped. QA PASS round 1; review REJECT→fix→APPROVE (fix_iterations=1).
- **Why:** user report (2026-11-11): in the user's recent **suburb_sim** session, the grokestrator, when asked to dispatch the HLD to the architect agent, said: *"The architect is on xAI and can write the design, not run shell. I'll send a full HLD brief and wait for the documents before cutting the backlog."* The user read this as possibly meaning the architect did NOT run as an OpenCode-harness subagent. Grounded config facts (verified 2026-11-11, base repo): in the OpenCode harness `architect` = `opencode-go/glm-5.2` with `shell: *: deny` (the no-shell half of the claim is TRUE by design), while the xAI-billed architect variants are `grok-architect` / `grok-architect-premium` on `xai/grok-4.7` (grokestrator.md model table, line 130). So the statement mixes a true tool fact with a model claim that is false for the stock harness — unless suburb_sim ships its own `opencode.json` that re-models `architect` onto xai/*, or the grokestrator actually dispatched a `grok-architect*` variant, or it never dispatched and did in-conversation design (a 20261014-1-class delegation-loop violation if unrecorded).
- **Description:** (1) **Session-store forensics** on the suburb_sim session (explore agent): locate the session tree (user's suburb_sim project storage; grokestrator as primary), extract the exact user request, the grokestrator's full message, and any child session rows — determine: was ANY subagent dispatched, which agent id and which model resolved (store row `model` field), did the child write an HLD design doc, and did the parent record a manifest/design-note deviation if design ran in-conversation. (2) **Root-cause the "on xAI" belief**: check suburb_sim's own `opencode.json` / project agents for a local `architect` override on an xai/* model; re-read the grokestrator model-selection table and mdu-42 wording for ambiguous phrasing that could induce the conflation; if the store shows a `grok-architect*` dispatch, classify whether that was correct routing (user asked for "the architect agent" — which variant should the grokestrator pick in the Grok harness?) or an mdu-42/misroute problem. (3) **Fix by evidence**: if the belief came from prompt ambiguity, add a grokestrator clause (and the base `prompts/orchestrator.md` mirror if the same ambiguity lives there) requiring dispatch statements to name harness + agent id + resolved model explicitly ("dispatching `<agent>` via subagent on `<model>` in `<harness>`"); if routing was wrong, fix the routing rule; if behavior was correct, write a docs clarification instead and close. (4) Pin whatever clause lands (test-agent), and record the case in `agent-improvements.md` if it maps to an existing open suggestion.
- **Acceptance criteria:**
  1. Forensics doc (docs/design/mdu-59-*.md or a findings doc) answers all three questions with store-row evidence: dispatched yes/no, agent id + resolved model from the store, and whether the design was written by a child session vs in-conversation.
  2. Root cause identified and classified: prompt ambiguity / routing error / correct-but-confusing behavior — with file:line evidence in the grokestrator (and suburb_sim config if an override exists).
  3. The evidence-backed fix ships: prompt clause (mirrored per cross-repo change order if generic) or routing fix or docs-only clarification; test-agent pins it; both suites green after the change; prompt-regression gate 7/7 unchanged baseline.
  4. The user's original question gets a direct written answer in the findings doc: did the architect run as an OpenCode-harness subagent, and on which model.
  5. If a definition change is needed, it lands only via the user-invoked review-mode path (`apply the definition diffs`) — the MDU ships the proposal + pins, not the definition edit, unless the user pre-approves in this MDU's scope.
- **Suggested agents:** explore (suburb_sim session-store forensics, very thorough), deep-research (only if suburb_sim config turns out to use a third-party harness), architect (fix design if prompt/routing change needed), just-code (prompt/config fix), test-agent (pins), qa (validation).
- **Dependencies:** none in the agent repos; evidence lives in the user's suburb_sim session storage (session id unknown — user can supply it to skip discovery). Overlaps 20261014-1 (in-conversation design violations) only if forensics show no dispatch happened.

### MDU-62 · PR policy rule: no PR for dihhuit/ private repos; explicit approval anywhere else (queued)

- **Status:** Done — 2026-11-13 (two-tier clause + PR-desc guard shipped byte-exact in `skills/git-autonomy/SKILL.md`; user-approved MDU-59 Dispatch-truth clause applied to 3 mirrors, dormant pin active; pin suite `tests/test_mdu_62_pr_policy.py` 11 cases + mutation matrix; base 979/979 + overlay 286/286; QA PASS round 1; commits in both repos this date)
- **Why:** user observed agents opening PRs instead of pushing/merging, and ~99% of their projects are private repos where a push without a PR is fine. User ruling 2026-11-13 (verbatim intent): private GitHub repos under `/dihhuit/` need no PR — push directly; for ANY repo anywhere else, opening/publishing a PR requires explicit per-action human approval (guard against unnoticed AI-generated contributions to OSS repos). The PR-by-default behavior traces to `skills/git-autonomy/SKILL.md:39`: "Push the feature branch and open the PR; do not push directly to `main` unless the project explicitly allows it" — the default is inverted for the user's own repos (the user's projects ARE the explicit allowance, but only for dihhuit/).
- **Description:** (1) Grep-census PR-creating/push-gating wording across both repos: `skills/git-autonomy/SKILL.md` (base skill, the primary carrier), the three orchestrator mirrors' repository-ownership sections, and any deploy/CI scripts that suggest PRs — attach the full file:line hit list to the implement brief. (2) Codify the two-tier rule byte-identically where it belongs: (a) repos under `github.com/dihhuit/` → no PR required; direct push to `main` remains the sanctioned default-green path (still subject to the existing secret + prompt gates and the protected-branch approval rule if `main` is ever branch-protected); (b) any other remote (OSS, third-party, unclear ownership) → explicit per-action human approval BEFORE opening a PR or pushing any branch; one approval never covers the next action. (3) Decide carrier set at design time: at minimum the git-autonomy SKILL.md push-safety rules section; the orchestrator mirrors get it only if their ownership wording conflicts (the mirrors already say "assuming there's a configured remote" without PR mandates — verify, do not assume). (4) Pins: census test that no carrier instructs opening a PR for a dihhuit/ repo without the approval tier distinction; mutation check that reverting SKILL.md:39 to PR-by-default reds the pin. (5) Wording approval: the user ruling sets the policy; present the exact clause text at design time for a single approval (mdu-60 carve-out pattern) or defer to the apply path if the user prefers.
- **Acceptance criteria:**
  1. Census doc lists every live PR-creating or push-gating line in both repos with its disposition (edited / left-as-is + why).
  2. The two-tier rule ships in the chosen carriers with non-vacuous pins; both suites green; prompt-regression gate unchanged baseline if prompt files are touched.
  3. A dihhuit/ repo scenario and a third-party repo scenario are both pinned: first = no PR required (direct push allowed), second = approval required before any PR/push.
  4. Secret gate clean both repos; commits split per cross-repo order if the overlay is touched.
- **Suggested agents:** architect (carrier census + clause design), just-code (clause edits), test-agent (pins), qa (validation).
- **Dependencies:** none (evidence in-tree); user approval of the exact clause wording at design time.




### MDU-60 · QA write-access decision + durable-QA-output pattern

- **Status:** Done — 2026-11-12 (user ruled consume-and-persist + pre-approved-in-MDU; clause byte-identical in 3 orchestrator mirrors, 2 checklist lines, 20-case pin suite incl. AC-2 read-only state pins; base 925/0 + overlay 275/0; QA PASS; manifest runs/mdu-60)
- **Why:** the sprite_generator session stuck on the qa_agent being unable to write its findings/results files (no write access; the mdu-48 "Permission denied: shell"×3 / answers_qa write-path class). Short-term unstick (applied by the user 2026-11-12): the orchestrator receives the QA output itself and finds another agent to write it to disk. This is also a recurring class: QA children repeatedly hit file-tool denials (20261110-1), and QA's sandbox is read-only by design (mdu-41/45 precedent). The open question is policy, not just mechanics: grant QA write permissions, or codify the orchestrator-consumes-and-persists pattern.
- **Recommendation (orchestrator, 2026-11-12, to be confirmed at design time):** **do NOT grant QA write access.** QA's value is independent read-only grading of a tree under test; granting write recreates the exact failure class that caused the stuck session (a read-only agent asked to produce files) and adds tree-mutation risk during validation. Codify the **consume-and-persist** pattern instead: the orchestrator consumes the QA reply as it already does (verdicts arrive in the reply per the QA protocol), and whenever a durable artifact is required (answers_qa JSON, findings files, reports), the ORCHESTRATOR dispatches a write-capable agent (just-code/devops) to persist it — or writes coordination artifacts itself. The QA brief pre-states this: "your output is consumed via your reply; a write-capable agent persists artifacts; do not attempt writes."
- **Description:** (1) Decision doc (docs/design/mdu-60-*.md) weighing both options with evidence: the sprite session store rows (permission.rejected write attempts), mdu-48 S1, 20261110-1, the 20261111-3 form-vs-content denial split, and the user's applied workaround — recommendation above is the default; the user rules at design time (per-diff approval gate for ANY qa permission change in opencode.json). (2) Ship the confirmed pattern: if consume-and-persist — one clause in the three orchestrator mirrors (base prompts/orchestrator.md, base grok/agents/orchestrator.md, overlay grok/agents/grokestrator.md), two docs/brief-checklist.md lines (name the durable-artifact writer in QA briefs; QA reply = the deliverable), QA-brief pre-statement folded into the existing probe-prestating clause carriers if wording allows; pins per the mdu-49 batch pattern. If grant-write — scoped permission edit for qa agents only + validator/gate pin + explicit rationale. (3) Definition changes go through the user-invoked `apply the definition diffs` path unless pre-approved in this MDU's scope.
- **Acceptance criteria:**
  1. Decision doc answers the grant-vs-consume question with store-row + precedent evidence and records the user ruling.
  2. The chosen pattern ships with pins; no QA agent can (or now can) write findings files in the stock config — pin the actual post-decision state.
  3. Both suites green; prompt-regression gate unchanged baseline if prompt files touched; secret gate clean.
  4. The stuck-session pattern is reproduced in the doc: what the orchestrator did (receive output, dispatch writer) is now the codified default, not an improvisation.
- **Suggested agents:** architect (decision doc + clause design), just-code (clause insertion or permission edit), test-agent (pins), qa (validation). Forensics input may reuse MDU-48 evidence (commit c3b2d48) without re-running the store sweep.
- **Dependencies:** MDU-48 evidence; 20261110-1 (QA brief pre-stating); user ruling at design time.

### MDU-61 · MCP harness-vs-reality fixes: playwright chromium + blender launcher gating

- **Status:** Done — 2026-11-12 (both root causes re-verified with dated probes 2026-11-12: the chrome-channel error reproduced byte-identically, the blender launcher-vs-app split confirmed live; chromium installed and a headless launch proven; overlay MCP config pinned `--browser chromium` across all sync points; blender gating clause shipped byte-identical in 6 base + 5 overlay carriers; QA pending at row-write time)
- **Why:** MDU-48 (done 2026-10-31, commit c3b2d48) already root-caused both "harness says connected, reality says broken" symptoms, but the recommended fixes were never executed: (a) Playwright MCP pins browser distribution 'chrome' at /opt/google/chrome/chrome, which does not exist; snap chromium is fragile and not the recommended target — fix S2b: pin `--browser chromium` (bundled) + one-time `npx playwright install chromium`; (b) Blender MCP "connected" verifies the server process only (launcher-level), not the addon socket in the running Blender — fix S3: gate blender-dependent steps on `pgrep -x blender` + the mcp-for-blender addon being enabled, else BLOCKED-report; harness "connected" must be treated as launcher-level only. The sprite session hit both live.
- **Description:** re-verify each root cause with one minimal probe (mdu-48 evidence is a week old; confirm before fixing), then implement: (1) overlay `opencode-mcp.json` playwright server args pinned to `--browser chromium` + a documented one-time `npx -y playwright install chromium` step (docs + deploy check); (2) blender gating clause in the devops/qa mirrors and docs/brief-checklist.md (probe `pgrep -x blender` + addon status before any blender step; absent → BLOCKED-report, mirroring the QA Playwright-or-BLOCKED discipline); (3) docs/mcp reference note: harness "connected" = launcher-level, app-vs-launcher probes distinguished (mdu-48 decision entry). MCP config is overlay-personal: per-diff approval gate still applies to each config edit; prompt-side clauses go through the definition path.
- **Acceptance criteria:**
  1. Each root cause re-verified with a dated probe reproduction (playwright: chrome-channel error reproduced then chromium fix proven with a real headless browser call; blender: launcher-only probe reproduced then gating demonstrated).
  2. Playwright MCP works via bundled chromium (or BLOCKED-documents the exact remaining env gap with the fix command).
  3. Blender gating clause shipped in the affected mirrors + checklist; a blender-dependent step without the pre-probe would fail the pin.
  4. Pins for both; suites green; overlay config commits separately from base prompt commits (cross-repo change order).
- **Suggested agents:** deep-research or architect (re-verification design), devops (MCP config + probes), just-code (clause/checklist), test-agent (pins), qa (validation incl. the webapp-verification Playwright recipe).
- **Dependencies:** MDU-48 (evidence + recommendations S2b/S3); overlay repo (MCP config); user per-diff approval for each MCP config edit.

### MDU-48 · Harness-reported MCP/shell connectivity vs agent reality mismatch (sprite_generator debugging incident)


- **Status:** Done — 2026-10-31 (diagnosis + recommendations delivered; live transparency in the mdu-48 manifest; **fixes now queued for execution: MDU-61 carries S2b/S3, MDU-60 carries the S1 write-access policy ruling** — both added 2026-11-12 at user priority) Paraphrased from the stuck session's question tool (`ses_e6d1ac9c…`): every write path was blocked, so the child could not write its `answers_qa` JSON files. The three symptom strings it reported were "Permission denied: shell" (x3), "Chromium distribution 'chrome' is not found at /opt/google/chrome/chrome", and "Could not connect to Blender".
- **Symptoms to root-cause (each independently):**
  1. `shell` "Permission denied: shell" ×3 — same denial class the mdu-45/mdu-46 QA children hit by design; which agent/allowlist was the sprite session running, and was the denial by-design or a config defect?
  2. Playwright MCP: "Chromium distribution 'chrome' is not found at /opt/google/chrome/chrome" — a pinned browser distribution/path that does not exist on this machine; find where the chrome channel/path is pinned (MCP server args, env, config) and what the correct playwright-mode/bundled-chromium fix is.
  3. Blender MCP: harness says connected, addon says "Could not connect to Blender" — the status check apparently verifies the server process, not the addon socket; find what "connected" actually probes.
- **Description:** DB forensics on the sprite session(s) (session store, tool call/error parts) + inspection of the live config the sprite session ran under (deployed opencode.json agent block incl. its shell permissions, MCP entries, playwright/blender server args). Reproduce each failure with a minimal probe. Deliverable: per-symptom root cause + a RECOMMENDED fix per symptom (config-level; no config change committed without user approval — the fix goes to the user for a ruling first, then is approved into a follow-up or folded into this MDU with approval).
- **Acceptance criteria:** each of the three symptoms has a named root cause with evidence (session store + config lines + probe reproduction); a written recommendation per symptom with the exact config diff it would apply; unit-of-work confined to diagnosis + recommendation unless the user approves the fix in-loop.
- **Suggested agents:** deep-research or architect (forensics design), devops or just-code (probes), orchestrator (synthesis + user report).
- **Dependencies:** none.

### MDU-49 · Definition batch 3 — six queued orchestrator/coder/introspector clauses

- **Why:** Six still-unapplied definition-change clauses from `agent-improvements.md` (20261027-3 finalize-before-QA, 20261030-3 grep-driven sweeps, 20261021-9 design-time routing pre-check, 20261031-1 bounded design allowance, 20261031-2 edit-result display integrity, 20261101-1 introspector unapplied-claim verification) were each recorded but never landed in the live definitions, so the same lapse classes (mdu-40/41/44 unfinalized manifests, mdu-43 enumeration drift, mdu-15/30/41 wrong-agent routing, mdu-48 read-only qa asked to write) kept recurring.
- **Description:** Insert the six clauses byte-identically into the three orchestrator mirrors (base `prompts/orchestrator.md`, base `grok/agents/orchestrator.md`, overlay `grok/agents/grokestrator.md`), the four base just-code bodies, and the two introspector bodies per the design doc's anchor table — 21 insertions across 9 source files. D2/D3/D4 form a delegation-discipline cluster ordered D4 → D3 → D2 before MODEL SELECTION; D1 lands in the run-ledger block before `Finalize order:`; D5 ships two shapes (coder sentences 1-2, orchestrator sentences 1-2 + corrected sentence 3); D6 ships the executability reword with a degradation ladder. Add `tests/test_mdu_49_definition_batch.py` (full-clause constants, doc-consistency, mirror parity, ordering, checklist pins, `MDU49_TEST_ROOT` mutation override) and overlay `tests/test_mdu_49_grokestrator_clauses.py` (grokestrator clauses + build inheritance). No `opencode.json` change ships.
- **Acceptance criteria:**
  1. Base suite green incl. `tests/test_mdu_49_definition_batch.py`; overlay suite green incl. `tests/test_mdu_49_grokestrator_clauses.py`; both builds idempotent; all pre-existing pins (mdu-04/11/12/15/23/28/31/34/35/40/41/44/45/46/47) unaffected — additive only.
  2. All 21 clause insertions byte-match the design doc §2-§7 blockquotes; prompt-regression gate exit 0 with unchanged baseline (7/7, no cases.json/baseline.json edit); secret gate exit 0.
  3. Probe gate green in both repos without `--refresh` (no registry change).
  4. The 7×FAIL mutation matrix from /tmp copies is recorded (each stripped clause reds its pins; doc/checklist pins stay green) with zero git state commands against the working tree.
  5. Deployed == build (`cmp`) for every edited prompt on all three CLIs; checklist rows, tests README row, and this entry land in the same base commit.
- **Suggested agents:** architect (design — done), just-code-mid (implement), code-reviewer (review), test-agent-mid (tests), devops (builds/deploy), qa (validate).
- **Dependencies:** MDU-47 (batch + pin pattern, personal-variant ruling), MDU-45 (non-vacuity lesson), MDU-46 (checklist pins), MDU-48 (D6 reword evidence: denied `timeout`-wrapped shell in live QA).
- **Follow-up:** the overlay root personal coder family (`grok-just-code`, `grok-just-code-mid`, `grok-just-code-pro`) was NOT edited — it extends the standing MDU-47 personal-variant follow-up. The base coder bodies reach OpenCode and Claude through the build; only the Grok personal mirrors lag. D4 in `skills/mdu-lifecycle/SKILL.md` was considered and rejected (mirrors only); extend later if belt-and-suspenders is wanted.
- **Status:** Done — 2026-11-01 (definition batch 3 landed: 21 byte-identical clause insertions across 9 base bodies + overlay grokestrator per the anchor table; D5 two-shape + D6 degradation-ladder reword shipped; 52-case pin suite + overlay fold/order test; base 723 + overlay 210 tests green; prompt gate 7/7 unchanged baseline; probe gates green without refresh (no registry change); mutation matrix 7×FAIL recorded; live deploy 0 mismatches at 27 cells; 2 QA rounds spent on orchestrator manifest self-consistency, both fixed, substantive checks 9/9 from round 1; QA GRADE: PASS. Personal grok-just-code* family parity remains queued with the MDU-47 follow-up.)

## P0bis — Free-tier quota crisis (new strategy, 2026-10-29)

**Context (user-confirmed, live-diagnosed):** OpenCode drastically tightened free-tier (Zen) model usage caps — Zen models are heavily capped even when a Go subscription is purchased. In the user's `mmo` project session, the `grok-architect` spawn died with an opencode free-tier limit: the deployed zen default tier maps ~40 of 50 agents (all `opencode-go/*` AND both `xai/*` agents, via the mdu-36 overlay fallback) onto `opencode/big-pickle`, so all loop traffic crowds one free model until it caps out. The xAI API key + auto-top-up were not involved (the agent ran through OpenCode, which never calls xAI for those agents in the zen tier). New strategy direction set by the user: **stop using free-tier models entirely (Go tier + xAI via API key), or reduce free usage to a tiny explicit set**.


### MDU-42 · HARD RULE — Grok-named agents must use XAI account models

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

### MDU-45 · Register base `grok-review` + grok-registry census + docs staleness sweep

- **Why:** Base `grok/agents/grok-review.md` (read-only Grok code-review rung, MDU-25 bulk tier) was the only base Grok profile with no same-name agent in `opencode.json`. User decision (2026-10-31): register it in base `opencode.json` with a `prompts/` body per family convention; retirement is out of scope. The same user decision bundled the docs-staleness sweep (README progress line, stale Grok-model claim, `docs/model-registry.md` refresh caveat, backlog Status backfill) into this MDU.
- **Description:** Add `grok-review` to base `opencode.json` as a subagent on `xai/grok-build-0.1` with `system: {file:./prompts/grok-review.md}`, temperature 0.1, and permissions byte-identical to `code-reviewer`. Author `prompts/grok-review.md` as the canonical OpenCode body (minimal reviewer contract, no new policy text). Align `grok/agents/grok-review.md` section heading `Rules:` → `Hard constraints:` with no other behavior change. Add `validate_grok_registry_census` to `scripts/lib/validate.py`: every `grok/agents/*.md` profile must have a same-name agent in the build tree's `opencode.json`; fail closed with a dated `GROK_CENSUS_ALLOWLIST = {"research": ...}` for the MDU-40 retired-but-files-retained bare `research` agent. Update README (roster row, 21-agent/12-prompt counts, two-rung Grok wording, re-derived progress line with last-verified 2026-10-31). Backfill Status lines for MDU-01/02/03/05/06/07/08/34. Add dated safe-refresh caveat to `docs/model-registry.md`; leave `config/model-registry.txt` untouched.
- **Acceptance criteria:**
  1. Base `opencode.json` registers `grok-review` per D2 and `./build.sh` is green end-to-end.
  2. Design-time live probes (2026-10-31) recorded: both `xai/grok-build-0.1` and `xai/grok-4.7` answered exactly `OK`; chosen model is `xai/grok-build-0.1`.
  3. `prompts/grok-review.md` exists with the D3 body; prompt ref resolves; parity pair pinned in `GROK_MIRRORS` and `ROLE_KEYWORDS`.
  4. `grok/agents/grok-review.md` carries only the D4 heading alignment edit.
  5. `validate_grok_registry_census` ships wired after `validate_grok_agents`, with dated allowlist (`research` only); base and overlay merged builds both pass.
  6. Negative-fail: synthetic orphan profile fails `validate.main` with the named census error; allowlist pass and key-set pinned.
  7. README (D7): roster row, layout counts 21/12, stale wording replaced, progress line re-derived with last-verified 2026-10-31.
  8. `FEATURE_BACKLOG.md` (D8): MDU-45 entry with both user decisions; Status backfilled for MDU-01/02/03/05/06/07/08/34; no entry unresolved.
  9. `docs/model-registry.md` carries dated safe-refresh caveat; snapshot untouched.
  10. Tests (D10): `tests/test_mdu_45_grok_review_registry.py` green (~20 tests); `test_mdu_40_paid_default.py` count pin updated to 21; full suites green.
  11. Prompt-regression gate exits 0 with baseline unchanged.
  12. Deploy (D11): both builds green; overlay `deploy.sh --force` installs 43 OpenCode agents (from 42) with 21/21 grok-named entries on `xai/*`; evidence file written; run manifest created and validated.
- **Suggested agents:** architect (design — done), just-code-mid (implement), code-reviewer (review), test-agent-mid (tests), devops (deploy + probes), qa (validate), orchestrator (commit).
- **Dependencies:** MDU-42 (grok-xai hard rule), MDU-25 (build rung), MDU-40 (paid census), MDU-44 (overlay dead-copy pins).
- **Status:** Done — 2026-10-31 — QA PASS 13/13 ACs (base `opencode.json` 20→21 agents; `prompts/` 11→12 files; parity pairs 19→20; `validate_grok_registry_census` ships with `GROK_CENSUS_ALLOWLIST={"research"}`; base build 21 agents/20 grok profiles passes; overlay merged build 43 agents/41 grok profiles passes; base 594 + overlay 192 tests green; prompt-regression gate 7/7 green; base and overlay probe gates refreshed green; live deploy installs 43 agents with 21/21 grok-named entries on `xai/*`; evidence file written to `/tmp/opencode/mdu-45-deploy-evidence.md`; run manifest finalized pre-QA per 20261027-3 and validated).

### MDU-46 · Apply-now tooling — run-ledger `model` field, brief checklist, local upstream draft

- **Why:** apply-now 20261026-2 (record the orchestrator model in the run manifest) went uncarried for 7 runs because the manifest schema had no field for it; the highest-value apply-now clauses live only as prose inside `agent-improvements.md`; and the MDU-35 upstream draft is buried in a design appendix. Promote all three into durable, test-pinned tooling/docs.
- **Description:** (D1) add the OPTIONAL top-level `model` field to `scripts/lib/run_ledger.py` — validated only when present (non-empty string, no enum/allowlist), never added to `REQUIRED_FIELDS`; `summarize()` gains additive `by_model` and `format_summary()` a `by model:` block. (D2) new `docs/brief-checklist.md`: an Every-brief block plus seven role templates (architect, just-code/fix child, code-reviewer, test-agent, devops, qa, introspector), each clause a one-liner carrying its `[id]`. (D3) new `docs/upstream-drafts/opencode-question-60min-kill.md`: FILING GATED banner, masked evidence pointers, zero submission mechanics, status = local staging for a possible someday fork; one pointer line under the MDU-35 appendix. (D5) backlog and tests README updates.
- **Acceptance criteria:**
  1. `validate` exits 0 with a valid `model`, exits 1 with `'model' must be a non-empty string` on empty/non-string, absent stays valid.
  2. `model` stays out of `REQUIRED_FIELDS`; full suite green including every untouched test_mdu_15 parity test.
  3. `by_model` appears additively in text and `--json`; no existing key changes.
  4. `docs/brief-checklist.md` exists with all seven role templates, the nine pinned ids on one line each with their clause, and the "DOC, not a prompt/definition file" statement.
  5. The upstream draft opens with the FILING GATED banner, cites only `runs/mdu-35-question-tool/evidence.md` sections, and contains no submission mechanics.
  6. `tests/test_mdu_46_apply_now_tooling.py` is green and hermetic (tmp_path only, no network, no git state).
  7. Tests README gains its row; backlog gains this entry and the prep-fork follow-up.
  8. Both builds exit 0; secret scan clean; zero changes under `prompts/` and `grok/agents/`.
- **Suggested agents:** architect (design — done), just-code-budget (code + docs), code-reviewer-mid (static trace), test-agent (pins), devops (builds + scan), qa (final validation).
- **Dependencies:** MDU-35 (draft source), MDU-45 (preceding chore MDU). Deferred to MDU-47: turning `model` into a required field and applying the checklist clauses to the definitions.
- **Status:** Done — 2026-10-31 (run_ledger gains the optional `model` field + `by_model`; REQUIRED_FIELDS untouched so the MDU-15 inline parity pins still bind; brief checklist carries 9 pinned clauses across 7 role templates; upstream draft staged locally with no filing mechanics; 44 new tests)

#### Follow-up · Upstream draft staging — 60-min question kill (prep-fork)

- **Why:** The MDU-35 evidence for the ~60-min `question`-call kill is a real upstream bug, but filing anything upstream is gated: the base rule requires an explicit per-action user instruction naming the repository and the action, and the 2026-10-31 ruling is local staging only.
- **Description:** Keep `docs/upstream-drafts/opencode-question-60min-kill.md` as the maintained standalone copy (the appendix in `docs/design/mdu-35-question-tool.md` stays the frozen record with a pointer). If a future OpenCode fork or an explicit user instruction arrives, this file is the ready text. Nothing here is to be submitted as a routine MDU step.
- **Acceptance criteria:** the draft exists, is gated by its banner, keeps masked evidence pointers only, and stays free of submission mechanics (pinned by the MDU-46 test file). Unblocking requires a user instruction that names the repository and the action.
- **Suggested agents:** orchestrator (hold), user (ruling).
- **Dependencies:** MDU-46 (staged it). Fork itself: someday, unplanned.
- **Follow-up status:** Staged — 2026-10-31 (filing gated; fork unplanned per the 2026-10-31 user ruling; MDU-46 test pins keep the draft clean)

### MDU-47 · Definition-guards batch + orchestrator repoint

- **Why:** Four queued apply-now clauses (20261017-1, 20261021-11, 20261021-8 reworded, 20261030-5) needed to land in the live agent definitions, plus the 20261026-2 orchestrator-model repoint ruling needed to be recorded rather than silently applied.
- **Description:** Insert the clause texts into base `prompts/` and their `grok/agents/` mirrors (code-reviewer, grok-review, qa, architect) with byte-identical wording and correct ordering; fold both QA sentences into the overlay `overlays/prompts/qa.md` full-file override so OpenCode/Claude deployments see them. Repoint base `opencode.json` orchestrator model to `opencode-go/glm-5.3-flash` and update its description tail, leaving the seven other `mimo-v2.6-flash` rows untouched. Add verify pins for the already-shipped 20261017-1 Dirty-tree guard (MDU-24) and update `docs/brief-checklist.md`, `tests/README.md`, and this backlog entry.
- **Acceptance criteria:**
  1. Base suite green incl. new `tests/test_mdu_47_definition_batch.py` pins; overlay suite green incl. `tests/test_mdu_47_overlay_qa_fold.py` fold pins; both builds idempotent; MDU-24/44/45/46 pins unaffected.
  2. All 16 prompt-file clause insertions byte-match the design doc blockquotes; prompt-regression gate exit 0 with unchanged baseline.
  3. Orchestrator model + description repointed; the other seven `mimo-v2.6-flash` rows untouched; no other registry edit.
  4. Overlay build carries both folded QA sentences into `build/prompts/qa.md`.
  5. Checklist, tests README, and backlog rows land in the same base commit.
- **Suggested agents:** architect (design — done), just-code-mid (implement), code-reviewer (review), test-agent-mid (tests), devops (builds), qa (validate).
- **Repoint ruling:** user ruling 2026-10-31 — orchestrator repointed to `opencode-go/glm-5.3-flash`. Design-time one-shot probes returned exactly `OK` on BOTH `glm-5.3-flash` and `mimo-v2.6-flash`, so the repoint is a sizing choice, not a capability fix; the seven other `mimo-v2.6-flash` rows stay put.
- **Follow-up:** the overlay root personal `grok-*` variants (`grok-qa`, `grok-qa-pro`, `grok-architect`, `grok-architect-premium`, `grok-test-agent`, `grok-test-agent-pro`, `grok-code-reviewer-pro`) were NOT edited in this batch — the clauses landed in the base prompts, their `grok/agents/` mirrors, and the overlay `qa` override only. Extend to those files in a future user-approved MDU if parity is wanted.
- **Dependencies:** MDU-24 (20261017-1 already shipped), MDU-41 (trace/procedure precedent), MDU-45 (grok-review registry), MDU-46 (checklist + model field).
- **Status:** Done — 2026-11-01 (definition clauses shipped in base prompts and grok mirrors, overlay qa override folded both sentences, orchestrator repointed to `opencode-go/glm-5.3-flash`, verify pins added, builds and suites green)

### MDU-54 · Overlay personal grok-* definition-parity batch

- **Why:** The MDU-47 and MDU-49 deferral follow-ups left the overlay-root personal `grok-*` full files without the definition-batch clauses the base siblings carry — the personal Grok mirrors lagged every behavioral guard shipped since, in the harness the user actually deploys from.
- **Description:** Land the role-applicable MDU-47/49 clauses byte-identically on the overlay-root personal grok profiles: D5 (always-verify) x3 coder family, D1d + D1c (denied-shell + QA sencence pair, base `qa.md` shapes) x2 qa, D1e ($WORKSPACE notation) x2 architect, D1b (read-only trace) x1 code-reviewer-pro — 10 clause insertions across 8 files, plus regenerated build copies, plus this backlog row. Extend the recorded deferral list with an evidence-backed exclusion table (devops/ui-ux/research carry no batch clauses; grokestrator complete since MDU-49; overlays/grok/agents personal-only trio needs a prompt-side fold — deferred).
- **Acceptance criteria:**
  1. Overlay diff = 24 insertions, 0 deletions, confined to the 8 root profiles + their 8 tracked build copies; clause text byte-matches the base carrier files (grep `-x` proven).
  2. Excluded profiles and `overlays/grok/agents/` trio carry zero batch-clause text (absence-pinned).
  3. grok-test-agent{,-pro}.md untouched (verify-only; Dirty-tree guard already present, MDU-24 shipment).
  4. Overlay suite green incl. two new MDU-54 test files (59 tests); base suite 813 unchanged; overlay build idempotent; prompt-regression gate 7/7 baseline intact; probe gate green (no registry change).
  5. Deploy 8/8 byte-identical (build copies vs installed, all 3 global snippets present); manifest validated and committed.
- **Suggested agents:** architect (design — done), just-code (implement — done), code-reviewer (review — done), test-agent (tests — done), devops (build/deploy — done), qa (validate — done).
- **Dependencies:** MDU-47 (deferral + clause set), MDU-49 (clause set + batch codification pattern), MDU-53 (20261024-1 architect cap carry honored).
- **Status:** Done — 2026-11-04 (10 clause insertions byte-identical; review APPROVE round 1; 59 new tests, overlay 269 / base 813 green; gate+probe+deploy green; QA PASS round 2 after one manifest bookkeeping fix)

### MDU-57 · Form-denial retry discipline — plain-form retry (introspector) + brief-named probes/denial-as-form-event (qa, 6 carriers)

- **Why:** suggestion `20261110-1` (warn, target orchestrator-briefs, kind brief_wording) — mdu-55's QA children hit 14 shell tool errors and improvised a sed -i in-place probe workaround in-child, and the same run's introspection mis-read two by-design command-form denials (`echo hi`; an `ls … && echo` compound) as a shell lockout; the mdu-45 practical rule ("run the script plain, no pipes, no redirects") existed only as notes on closed 20261014-6, never in any prompt or brief, so each pass re-learned it. Root cause of the reopened 20261102-2 script-timing slip.
- **Description:** three clauses per docs/design/mdu-57-form-denial-retry-discipline.md: Clause A (introspector plain-form retry, verbatim suggestion wording) in both mirrors inside the script-run bullet; Clause B (brief names the probes + file-tool fallback, denial reported as a form/permission event, no improvised in-place rewrites) immediately after D1d in SIX carriers — 3 base qa bodies, overlay full-file `overlays/prompts/qa.md`, overlay-root `grok/agents/grok-qa.md` + `grok/agents/grok-qa-pro.md` (the last two caught by review round 1; the design's original four-carrier survey missed the root-added live sources); Clause C as two `docs/brief-checklist.md` lines. 26-case base pin file + 3-case overlay build-copy pin + mdu-45 backlog-audit pin widened with a heading-gated queue-head Open exemption (MDU-56's honest Open status exposed the pin's inability to admit queued work). Build-only deploy (mdu-55 D5 precedent); 20261110-1 flipped resolved-pending-first-live-exercise with an explicit reopen trigger.
- **Acceptance criteria:**
  1. Clause A once per introspector mirror, byte-identical, positionally pinned inside the script bullet; pass/read lines byte-unchanged.
  2. Clause B once in each of the six QA carriers, byte-identical including the lead, immediately after D1d; D1d byte-unchanged everywhere.
  3. Both Clause C lines present in their checklist sections and order.
  4. Base suite green (825 + 26 = 851); overlay suite green (269 + 3 = 272); no file-count pins; mutation matrix 12/12 as designed (stripped clause reds pins, doc-only mutant green).
  5. Prompt-regression gate 7/7 exit 0 unchanged baseline; secret gate exit 0; run-ledger validate exit 0; both builds exit 0 with overlay build copies carrying the clauses byte-identically.
  6. `agent-improvements.md` 20261110-1 flipped with on-disk grep evidence + reopen trigger; this row records the MDU.
- **Suggested agents:** architect (design — done), just-code (implement — done), code-reviewer (review — done), test-agent (mutation matrix — done), devops (builds — done), qa (validate).
- **Dependencies:** MDU-45 (audit pin), MDU-47 (D1d anchor + batch pattern), MDU-54 (root-added-source carrier rule), MDU-55 (the live evidence run).
- **Status:** Done — 2026-11-10 (definition batch shipped: clauses A/B/C across 9 files + pins; review APPROVE-equivalent after 2 rounds — round 1 MAJOR fixed, round 2 single medium folded docs-only; base 851 / overlay 272 green; mutation matrix 12/12; prompt gate 7/7; QA GRADE PASS round 1 with 10/10 ACs; build-only deploy; 20261110-1 flipped resolved-pending-live-exercise)

### MDU-55 · Introspector self-cost discipline

- **Why:** suggestion `20261102-2` (warn, target introspector, kind token_hotspot) — the loop-mode pass re-read the growing `agent-improvements.md` in full and ran the signal script at pass start, so the pass's own token/long_context/stall signals structurally under-reported.
- **Description:** one new indented sub-bullet under the loop-mode read bullet in both introspector mirrors (byte-identical bodies; grok keeps its frontmatter) carrying the grep-open-ids / targeted-edit / one-script-run / 140k wrap-up discipline; the SKILL.md run-timing subsection; a 12-case pin file; the suggestion flip to resolved pending live exercise.
- **Artifacts:** `prompts/introspector.md`, `grok/agents/introspector.md`, `skills/session-introspect/SKILL.md`, `tests/test_mdu_55_introspector_discipline.py`, `agent-improvements.md` flip; design doc `docs/design/mdu-55-introspector-self-cost-discipline.md`.
- **Status:** Done — 2026-11-10 (clause and note shipped and pinned, 12 new tests, base suite 825 green; no deploy — static acceptance, pending the first post-deploy live exercise)

### MDU-64 — Pre-introspect manifest rows

- **Status:** Done — 2026-11-14

### MDU-65 · Grok CLI context window check

- **Why:** The Grok CLI meter shows about 50k of 256k while grokestrator and the Grok orchestrator are declared as Grok 4.7, and an older design note calls that model a 500k window.
- **Description:** Read-only check of the resolved model id in source frontmatter, installed copies, both opencode.json registries, the Grok allowlist, the user Grok config, and the live CLI catalog. No agent-definition edits.
- **Acceptance criteria:**
  1. The row records the resolved model id and whether 256k is the window or a display cap.
  2. No agent definition file changes.
  3. No follow-up model-change MDU is added when the id is already correct.
- **Artifacts:** `docs/design/mdu-65-context-window.md`. Manifest stays local under `runs/`.
- **Status:** Done — 2026-11-14 (Grok CLI model id is grok-4.7 for both the orchestrator profile and grokestrator; OpenCode grokestrator is xai/grok-4.7; the OpenCode stock orchestrator stays opencode-go/glm-5.3-flash and is not the CLI meter. Catalog default context_window for grok-4.7 is 256000, with 500000 as a second selectable size. The meter denominator is that selected window, the same value auto-compact uses, not a display cap. No definition edit. No follow-up MDU.)
