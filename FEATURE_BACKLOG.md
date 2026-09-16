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

- **Why:** Prompt edits are unmeasured; "improvements" can silently degrade behavior.
- **Description:** Add a lightweight comparison flow: before changing a prompt, `just-code` (or the orchestrator) snapshot-diffs the golden-eval results (MDU-08) for the old vs new prompt on the affected eval tasks; a prompt change that regresses ≥1 golden case is rejected by the orchestrator (or CI on PR). Implement as a documented workflow + optional promptfoo config (`evals/promptfoo.yaml`) for teams that want the standard tool.
- **Acceptance criteria:**
  1. A documented "prompt change protocol" exists in `evals/README.md`.
  2. CI (or the orchestrator) can demonstrate a prompt change rejected due to golden-case regression.
  3. promptfoo config is valid and runs against ≥3 eval tasks.
- **Suggested agents:** architect (protocol design), test-agent (regression harness), qa (validation).
- **Dependencies:** MDU-08.

### MDU-10 · Checkpoint/resume protocol for long-running work

- **Why:** The current "Session Checkpoint" guardrail is a safety valve, not a resume primitive; interrupted autonomous runs lose everything.
- **Description:** Define a checkpoint format (plain markdown checkpoint file per MDU: goal, completed steps, current step, artifacts, next actions, blockers) and add orchestrator rules: write a checkpoint after every completed phase and before any human-escalation; on session start, if a checkpoint exists for an incomplete MDU, resume from it. Coordinate with MDU-04 memory. Optional: document host-level resume (e.g., Claude Code `--resume`, opencode session persistence) in the README.
- **Acceptance criteria:**
  1. Interrupting a task mid-MDU and restarting yields a plan that resumes exactly (tested, MDU-04 resume test extended).
  2. Checkpoint files follow the documented format and are validated by `validate.py` if committed.
  3. README documents which hosts support native resume and how this convention complements them.
- **Suggested agents:** architect (protocol), just-code (orchestrator prompt), test-agent (resume tests), qa (validation).
- **Dependencies:** MDU-04.

### MDU-11 · Secret scanning & leak prevention in the loop

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