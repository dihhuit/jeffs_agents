# Gap Analysis: Open Agent Definitions vs. the Bleeding Edge of Autonomous Agentic Development

**Date:** September 2026
**Subject:** this repository (OpenCode + Grok Build + Claude Code agent definitions)
**Goal:** identify gaps blocking the repo from representing the current state of the art in fully autonomous agentic software development, so it can be upgraded (and showcased) credibly.

---

## TL;DR

This repo has an unusually solid **foundation**: an MDU-driven closed-loop lifecycle, model-tier cost routing, failure-routing with root-cause analysis, safety guardrails, multi-CLI deployment, and a build/validate pipeline. That is genuinely ahead of most personal agent repos.

However, measured against mid-2026 best practice, it lags in **eight dimensions**:

1. **No CI or automated checks on the agent definitions themselves** — demonstrated live by the fact that two research agents in this repo currently fail to launch because their models (`opencode/deepseek-v4-flash-free`, `opencode/north-mini-code-free`) no longer exist. Without CI, model drift goes unnoticed.
2. **No memory/persistence** — every session starts from zero; no checkpoint/resume, no cross-session learning, no context retention between MDUs.
3. **Zero skills** — the `skills/` directory exists but is empty, despite "Agent Skills" being a 30+ tool open standard in 2026.
4. **No MCP strategy** — QA references Playwright MCP but no MCP config, registry choices, or per-agent scoping is shipped or documented.
5. **No observability/tracing** — no OTel GenAI instrumentation, no token/cost telemetry, no audit trail of agent actions.
6. **No evaluation harness** — no golden datasets, no prompt regression tests, no SWE-bench-style validation of the agent team itself. QA is manual-only.
7. **Security posture is permissive** — everything is `"allow"`; no sandboxing guidance, no secret-scanning guardrails, no approval gates for destructive ops.
8. **Definition hygiene** — inconsistent config styles (`tools` vs `permission`), stale model references, no schema pinning for the config format.

The good news: the repo's own MDU discipline and multi-agent loop are exactly the machinery needed to bootstrap the fixes. A prioritized, implementation-ready backlog lives in **[FEATURE_BACKLOG.md](FEATURE_BACKLOG.md)** — feed it to the orchestrator and the current agent definitions build the next generation of themselves.

---

## Method

- **Repo audit:** full read of `opencode.json`, all 9 `prompts/*.md`, `grok/agents/*`, `scripts/`, `README.md`.
- **Live runtime test:** spawned the repo's own research agents in this environment. **Result: 2 of 4 failed to start** with `Model not found: opencode/deepseek-v4-flash-free` / `opencode/north-mini-code-free`. This is primary evidence for the model-drift gap (see §2).
- **Research:** four parallel literature/framework surveys (mid-2026):
  - Orchestration patterns & autonomy levels (LangGraph/A2A/MCP, spec-driven dev, checkpointing)
  - Memory & context engineering (mem0/Letta/Zep, CLAUDE.md/AGENTS.md, RAG)
  - Skills & MCP ecosystems (Agent Skills standard, MCP spec, Playwright)
  - Observability, evals, and CI for agents (OTel GenAI, Langfuse/LangSmith/promptfoo, sandboxing)

---

## What Is Already Strong (keep, and advertise)

| Strength | Why it's genuinely good |
|---|---|
| **MDU closed-loop lifecycle** | Design → implement → review → test → deploy → validate, with commit-and-push gates. This is the generate-and-verify loop the industry converged on. |
| **Model-tier cost routing** | 26 agents across free/budget/mid/premium tiers with a delegation guide. Token-frugal model selection is a real differentiator. |
| **Failure routing & root-cause loop** | DevOps/QA failures route back to the orchestrator for root-cause analysis and re-delegation, retried until green. Matches "self-healing" expectations. |
| **Safety guardrails** | Retry caps, subagent watchdog, session checkpoints — most personal repos have none of this. |
| **Multi-CLI parity** | One canonical prompt set compiled to OpenCode + Grok + Claude Code. Rare and impressive. |
| **Overlay pattern** | Base/overlay separation with a documented contract is a mature architecture for a shareable artifact. |
| **Build/validate pipeline** | `build.sh` + `validate.py` + generated Claude agents is already "CI-shaped" — it just isn't wired into CI. |

---

## The Eight Gaps (Detailed)

### 1. No CI / no drift detection on the definitions themselves — **critical, proven**

- **Current:** `validate.py` checks JSON syntax, prompt file references, and a hardcoded Grok model allowlist. It only runs when the author remembers to run `./build.sh`.
- **Bleeding edge:** eval-as-test CI gates. Promptfoo/Langfuse/LangSmith experiments run on every PR touching `prompts/**`; model IDs are treated as versioned config; deprecations are caught by eval drift + registry checks, not silence.
- **Gap:** No `.github/workflows/` exists in the repo. Nothing validates `opencode.json` model references against the live model registry — so agents silently break.
- **Evidence (live):**
  - `Model not found: opencode/deepseek-v4-flash-free. Did you mean: ling-3.0-flash-fin-free, mimo-v2.5-free, muse-spark-1.2-contributor-free?`
  - `Model not found: opencode/north-mini-code-free. Did you mean: ...`
- **Fix:** ship a GitHub Actions workflow that runs `validate.py` plus a new live-model check (fetch the model registry and fail on stale references/completions). See backlog **MDU-01, MDU-02**.

### 2. No memory or session persistence — **critical for a job-search artifact**

- **Current:** warm-start only (orchestrator prompt) plus todo lists. Every conversation forgets the last; long multi-MDU projects lose context; no resume after interruption.
- **Bleeding edge:** persistent memory layers (mem0/Letta/Zep — vector stores, knowledge graphs, git-versioned context), structured context files (CLAUDE.md/AGENTS.md with hierarchical precedence), automatic context assembly, prompt caching for 75–90% cost cuts.
- **Gap:** no cross-session state, no memory file convention, no checkpoint/resume, no artifact handoff format between agents. The orchestrator's "Session Checkpoint" is a *safety* mechanism, not a *resume* mechanism.
- **Fix:** add a lightweight, dependency-free memory convention (e.g., `.agents/memory/*.md` with frontmatter + auto-append rules), a checkpoint/resume protocol in the orchestrator, and document integration points for mem0/Letta if the user wants heavier memory. See **MDU-04, MDU-10**.

### 3. Empty skills system — **high visibility gap**

- **Current:** `skills/` exists but is empty.
- **Bleeding edge:** "Agent Skills" is an open standard adopted by 30+ tools (Claude Code, Cursor, Copilot, Gemini CLI, OpenCode, OpenHands…). Format: directory with `SKILL.md` (YAML frontmatter `name`/`description`/`allowed-tools` + markdown body), progressive disclosure (~100 tokens loaded until activated), layered discovery enterprise > user > project > nested.
- **Gap:** zero skills shipped. No reusable workflows (code-review checklists, test-pattern libraries, deploy safety checklists, incident playbooks).
- **Fix:** seed the skills library with a handful of high-value skills used by the loop itself (e.g., `code-review-checklist`, `mdu-lifecycle`, `webapp-verification`, `secret-scrub`), then document the convention. See **MDU-05**.

### 4. No MCP strategy — **moderate, foundational**

- **Current:** QA prefers "Playwright MCP" but there is no MCP configuration shipped, no `.mcp.json` guidance, no documented server choices, no per-agent scoping.
- **Bleeding edge:** MCP spec (2025-03-26) with Tools/Resources/Prompts is the standard agent-tool substrate; official registry for server discovery; Playwright MCP is the browser-verification standard; per-project `.mcp.json` with per-agent tool scoping; remote servers via SSE.
- **Gap:** the loop's capabilities implicitly depend on MCP (browsers, git hosts, DBs) but nothing is configured or documented; QA's browser verification has no supported path in OpenCode/Grok/Claude configs here.
- **Fix:** ship a reference `.mcp.json` + docs; make QA's browser preference order concrete and testable; add per-agent `tools` scoping where the host supports it. See **MDU-06**.

### 5. No observability or tracing — **moderate**

- **Current:** zero telemetry. The orchestrator "knows" what happened only via subagent summaries; token spend is mental arithmetic; no audit trail.
- **Bleeding edge:** OTel GenAI semantic conventions (`invoke_agent`, `execute_tool`, usage tokens) exported via Langfuse/LangSmith/AgentOps/OpenLLMetry; cost/latency dashboards; loop metrics (duration, tool calls) as SLOs; trace→dataset→eval pipelines.
- **Gap:** unmeasurable autonomy is unprovable autonomy — for a job-search artifact this is the difference between "I built it" and "I can prove it works."
- **Fix:** add telemetry hooks to the orchestrator (run manifest per MDU: agents invoked, model tiers, token estimates, outcomes), a machine-readable `runs/` ledger, and document OTel GenAI / Langfuse drop-in integration. See **MDU-07**.

### 6. No evaluation harness — **high value, high visibility**

- **Current:** QA validates *deliverables* manually. Nothing evaluates *the agent definitions themselves*.
- **Bleeding edge:** golden datasets + LLM-as-judge, prompt regression gates in CI, SWE-bench-style task suites for coding agents, trace mining for new cases, versioned prompts.
- **Gap:** the team can't prove it doesn't regress when prompts or models change; "fully autonomous" claims aren't benchmarkable.
- **Fix:** add an `evals/` directory (golden task set + expected outcomes), a `run-evals` agent/skill, and wire scoring into CI. See **MDU-08, MDU-09**.

### 7. Permissive security posture — **moderate**

- **Current:** all agents have broad `"allow"` permissions; no sandboxing guidance; no secret scanning; no approval gates for destructive ops beyond the 3-retry human-escalation rule.
- **Bleeding edge:** least-privilege tool scoping, `allowed-tools`/`disallowed-tools` at skill level, devcontainer/E2B/Firecracker sandboxing, secret scanning on agent-generated artifacts, human-approval gates for delete/deploy/push-to-prod, short-lived tokens.
- **Gap:** defaults are "trust the agent", which is the opposite of the governance posture enterprises (and recruiters evaluating risk maturity) expect.
- **Fix:** add a security hardening MDU: secret-scrub skill, deploy approval gate, least-privilege permission review, sandbox docs. See **MDU-11, MDU-12**.

### 8. Definition hygiene & job-search polish — **moderate**

- **Current:** `qa`/`qa-pro`/`qa-free` use the legacy `tools` config block while every other agent uses `permission` (inconsistent); stale model references; README TODO has one stale item; staggered model names; a stray `deepseek_error.png` sits untracked in the repo root.
- **Bleeding edge:** versioned config with pinned schemas, consistent permission style, a documented autonomy-level ladder (L0–L4) so claims are precise, badges, demo outputs.
- **Fix:** normalize config styles, add an autonomy ladder doc, curate the README (badges, "what's inside" table, examples), remove stray artifacts. See **MDU-03, MDU-13, MDU-14**.

---

## Autonomy Ladder Positioning

Industry standard reference (2026): **L0** tool-assisted → **L1** task-autonomous → **L2** session-autonomous (multi-step with human checkpoint review) → **L3** goal-directed with human approval gates → **L4** fully autonomous multi-agent pipeline.

- **This repo today: L2.** A human kicks off the orchestrator; the loop self-heals within an MDU and the 3-retry cap escalates to the user; commit-and-push is autonomous.
- **Missing for L3:** checkpoint/resume, explicit approval gates, persistent memory, and an eval gate that proves the loop didn't regress.
- **Missing for L4:** sandboxed execution, telemetry-driven circuit breakers, A2A/agent-to-agent interop.

**Recommendation:** target and *document* **L3** (the enterprise ceiling per Forrester 2026) — it is achievable with the backlog below and is the most credible claim for a job-search artifact.

---

## Target State (what "up to speed" looks like)

1. **CI runs on every push:** definition lint + schema validation + live-model-registry check + a golden-eval smoke suite. Broken agents are caught in minutes, not discovered by the next user.
2. **The loop remembers:** `.agents/` memory convention, checkpoint/resume, structured MDU handoff artifacts — plus documented upgrade path to mem0/Letta.
3. **A real skills library:** 4–6 SKILL.md skills used by the loop itself, proving progressive disclosure and the open standard.
4. **MCP documented and configured:** reference `.mcp.json`, Playwright for browser verification, per-agent scoping.
5. **Observable:** per-MDU run manifest + tracing hooks + OTel GenAI guidance; the README can show real telemetry screenshots.
6. **Benchmarked:** `evals/` golden suite graders in CI; SWE-bench-style task for the coding agents.
7. **Hardened:** least-privilege permissions, secret-scrub skill, approval gates, sandboxing docs.
8. **Polished:** badges, autonomy ladder, examples gallery, consistent config — an artifact that sells itself.

---

## Priority Summary → See FEATURE_BACKLOG.md

| Priority | Theme | Backlog items |
|---|---|---|
| P0 — proves it works | CI + drift detection, schema hygiene, autonomy ladder | MDU-01..03 |
| P1 — makes it autonomous | memory/checkpoint, skills, MCP, observability, run ledger | MDU-04..07 |
| P2 — makes it provable + safe | evals harness, sandboxing/approvals, polish | MDU-08..14 |

Each backlog item is written as an MDU with acceptance criteria consumable by this repository's own orchestrator — the agent team builds its own upgrade.