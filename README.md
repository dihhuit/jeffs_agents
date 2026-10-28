# Open Agent Definitions

[![CI](https://github.com/dihhuit/jeffs_agents/actions/workflows/ci.yml/badge.svg)](https://github.com/dihhuit/jeffs_agents/actions/workflows/ci.yml)
[![License: Unlicense](https://img.shields.io/badge/license-Unlicense-blue.svg)](https://unlicense.org/)
[![OpenCode](https://img.shields.io/badge/OpenCode-compatible-blue)](https://opencode.ai)
[![Grok Build](https://img.shields.io/badge/Grok%20Build-compatible-black)](https://x.ai)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-compatible-orange)](https://claude.com/claude-code)

> **Disclaimer**: All of the code and agent definitions in this repo were written by AI, not by the author directly, so use with caution. Just because this repo's author trusts them doesn't mean you should.

These are generic, reusable agent definitions for [OpenCode](https://opencode.ai), [Grok Build](https://x.ai) (the `grok` CLI from xAI), and [Claude Code](https://claude.com/claude-code) (the `claude` CLI from Anthropic) which have been distilled from my own, very personal and workflow specific agent definitions into something shareable. How I use these is overlaying my own workflow specific deltas (see below for details) to personalize them for how I like to work. These agents represent a "team" with specific focus or specialization areas. Whenever I'm working on a project, I start with the orchestrator, and have it farm out tasks to the other agents. Having specialized agents like this allows me to a) minimize per-agent context, and b) implement guardrails in the form of inter-agent checks and balances (e.g. to prevent the just-code agent from cheating on tests by updating the tests).

I'm not promising these are the best agents out there, nor the best agent team/stack, but they are MY agents, and this is the setup I use daily. It's constantly being refined, so if you're following, check back every now and again.

This repository provides a **base layer** of agent definitions designed to be broadly applicable across different projects and users. The prompts have been kept focused on core responsibilities rather than any single team's specific workflows or tooling.

## Prerequisites

### Model Tiers — Zen (default) / Go (switch-up)

The OpenCode agents ship as **two tiers generated from the same `opencode.json` source**:

| Tier | Config file | Models | Use it |
| --- | --- | --- | --- |
| **Zen (default)** | `build/opencode.zen.json` (generated) | Free Zen (`opencode/*`) | Default. No subscription required. |
| **Go (switch-up)** | `opencode.json` | OpenCode Go (`opencode-go/*`) | When the period's Zen usage is exhausted, or a premium slot needs a stronger model. |

`./build.sh` generates the Zen file from `opencode.json` with `scripts/lib/gen_zen_config.py` and the mapping table `config/zen-model-map.json`, then validates that no `opencode-go/*` reference survives. The mapping collapses Go budget/mid/premium slots onto the two proven free generalists (`opencode/big-pickle` and `opencode/nemotron-3.5-lightning-free`); premium slots are a **documented capability regression** and the primary reason to switch up. See [docs/model-registry.md](docs/model-registry.md#zen-variant-mapping-mdu-33) for the table, alternates, and per-agent overrides.

**Install the default (Zen) tier:**

```bash
./deploy.sh --force                # same as --tier=zen
```

**Switch up to Go when Zen usage for the period is exhausted:**

```bash
./deploy.sh --force --tier=go      # then start a new session
```

Deploy always installs both tier files: the selected tier becomes `~/.config/opencode/opencode.json` (active), the other is parked beside it as `~/.config/opencode/opencode.zen.json` or `opencode.go.json` (inert — config discovery only reads `opencode.json`). Switch back at any time with `./deploy.sh --force --tier=zen`.

**Switch without the repo (manual one-liner):**

```bash
cp ~/.config/opencode/opencode.zen.json ~/.config/opencode/opencode.json   # back to Zen
cp ~/.config/opencode/opencode.go.json  ~/.config/opencode/opencode.json   # up to Go
```

Config is read at session start, so **start a new session** (or `opencode service restart`) after a swap. Prompt/skill deploys are tier-independent — both configs reference the same `./prompts/` tree.

> **Go subscription:** Go models (`opencode-go/deepseek-v4.1-flash`, `opencode-go/kimi-k2.7-code`, `opencode-go/glm-5.2`, `opencode-go/mimo-v2.5`) require an active [OpenCode Go subscription](https://opencode.ai/docs/go) ($10/month). The Zen tier needs no subscription.

> **Overlay users:** this two-tier setup is built by the base repo's `build.sh`. The private overlay constructs its own `opencode.json` and must add the equivalent `gen_zen_config.py` call to its own build — see the overlay repo.

### Grok Build / Claude Code

The Grok Build profiles and Claude Code subagents use their own model backends and are not affected by the tier setup — they work as long as you have the respective CLI installed.

## Using These Agents As-Is

1. Clone or download this repository.
2. (Optional) Stage a validated `build/` directory:

   ```bash
   ./build.sh
   ```

3. Deploy to your local OpenCode, Grok Build, and/or Claude Code config directories:

   ```bash
   ./deploy.sh --force
   ```

   Or rebuild and deploy in one step:

   ```bash
   ./deploy.sh --force --rebuild
   ```

This installs:
- **OpenCode**: the selected tier as `opencode.json` plus the other tier parked as `opencode.zen.json`/`opencode.go.json`, and `prompts/` → `~/.config/opencode/`
- **Grok Build**: `grok/agents/*.md` → `~/.grok/agents/`
- **Claude Code**: `claude/agents/*.md` → `~/.claude/agents/` (user-level subagents)

`deploy.sh` auto-detects which of the three CLIs (`opencode`, `grok`, `claude`) are installed and only deploys to the ones present; it errors only if none are found.

The `opencode.json` file in the root provides a ready-to-use set of agents. You can use it directly, copy sections from it, or merge it with your existing configuration.

The Claude Code subagents are **generated at build time** from `opencode.json` (roster + descriptions) and `prompts/*.md` (the canonical, provider-neutral system prompts), so there is no separate `claude/` source tree to maintain — they always stay in sync with the OpenCode definitions. Each generated file is Markdown with YAML frontmatter (`name`, `description`) followed by the system prompt body; `model` is intentionally omitted so each subagent inherits your configured Claude Code model.

The shipped `opencode.json` also includes a top-level `permissions` array that lets all agents read `/tmp` and `/proc` — and write `/tmp` for agents with write access — without prompting. Read-only agents keep their `edit`/`write` deny, so the scratch allowance does not widen their reach.

### For Grok Build only

After `./deploy.sh --force`, invoke profiles with:

You can also use profiles directly with:

```bash
grok --agent just-code -p "Implement a small feature..."
```

(Profiles can be copied manually to `~/.grok/agents/` or project `.grok/agents/` if preferred.)

### For Claude Code only

After `./deploy.sh --force`, the subagents are installed to `~/.claude/agents/`. Claude Code discovers user-level subagents there automatically — list and inspect them with the interactive `/agents` command, or invoke one for a session with:

```bash
claude --agent just-code -p "Implement a small feature..."
```

(Files can be copied manually to `~/.claude/agents/` or project `.claude/agents/` if preferred.)

### What's Inside

The agent definitions follow a **model tier variant** pattern — each role has multiple clones configured with different models so the orchestrator can spread token cost and choose the cheapest reliable model for each subtask. See [docs/model-registry.md](docs/model-registry.md) for the full model allowlist and verification dates.

### OpenCode agents (defined in [`opencode.json`](opencode.json) and [`prompts/`](prompts/))

| Role group | Agent | Prompt | Notes |
| --- | --- | --- | --- |
| Orchestrator | [`orchestrator`](prompts/orchestrator.md) | [prompts/orchestrator.md](prompts/orchestrator.md) | Primary coordinator (free Zen: big-pickle). MDU lifecycle, gates, ledger. |
| Research | [`research`](prompts/research.md) | [prompts/research.md](prompts/research.md) | Quick web lookups (free). |
|  | [`deepseek-research`](prompts/research.md) | [prompts/research.md](prompts/research.md) | Coding patterns, library docs (free). |
|  | [`nemotron-research`](prompts/research.md) | [prompts/research.md](prompts/research.md) | Thorough doc research (free). |
|  | [`deep-research`](prompts/research.md) | [prompts/research.md](prompts/research.md) | Comprehensive multi-source research (Go budget). |
| Coding | [`just-code`](prompts/just-code.md) | [prompts/just-code.md](prompts/just-code.md) | Default coder (Go budget). |
|  | [`just-code-mid`](prompts/just-code.md) | [prompts/just-code.md](prompts/just-code.md) | Complex features needing deeper reasoning (Go mid). |
|  | [`just-code-pro`](prompts/just-code.md) | [prompts/just-code.md](prompts/just-code.md) | Architecture-sensitive code, refactoring (Go premium). |
|  | [`just-code-free`](prompts/just-code.md) | [prompts/just-code.md](prompts/just-code.md) | Boilerplate, simple changes (free). |
| Testing | [`test-agent`](prompts/test-agent.md) | [prompts/test-agent.md](prompts/test-agent.md) | Default test writer (Go budget). |
|  | [`test-agent-mid`](prompts/test-agent.md) | [prompts/test-agent.md](prompts/test-agent.md) | Complex test suites, property-based tests (Go mid). |
|  | [`test-agent-pro`](prompts/test-agent.md) | [prompts/test-agent.md](prompts/test-agent.md) | Security tests, deep coverage (Go premium). |
|  | [`test-agent-free`](prompts/test-agent.md) | [prompts/test-agent.md](prompts/test-agent.md) | Simple unit tests (free). |
| Code Review | [`code-reviewer`](prompts/code-reviewer.md) | [prompts/code-reviewer.md](prompts/code-reviewer.md) | Standard review (Go mid). |
|  | [`code-reviewer-pro`](prompts/code-reviewer.md) | [prompts/code-reviewer.md](prompts/code-reviewer.md) | Deep security audit, architecture review (Go premium). |
|  | [`code-reviewer-free`](prompts/code-reviewer.md) | [prompts/code-reviewer.md](prompts/code-reviewer.md) | Quick lint/style check (free). |
| Architecture | [`architect`](prompts/architect.md) | [prompts/architect.md](prompts/architect.md) | Design docs, API specs (Go premium). |
|  | [`architect-premium`](prompts/architect.md) | [prompts/architect.md](prompts/architect.md) | Complex system design, ADRs (Go premium). |
| DevOps | [`devops`](prompts/devops.md) | [prompts/devops.md](prompts/devops.md) | Standard deploys, Docker, CI/CD (Go mid). |
|  | [`devops-pro`](prompts/devops.md) | [prompts/devops.md](prompts/devops.md) | Complex multi-service deploys, IaC (Go premium). |
|  | [`devops-free`](prompts/devops.md) | [prompts/devops.md](prompts/devops.md) | Simple config changes (free). |
| QA | [`qa`](prompts/qa.md) | [prompts/qa.md](prompts/qa.md) | Standard validation (Go mid). |
|  | [`qa-pro`](prompts/qa.md) | [prompts/qa.md](prompts/qa.md) | Thorough regression, edge case validation (Go premium). |
|  | [`qa-free`](prompts/qa.md) | [prompts/qa.md](prompts/qa.md) | Basic smoke tests (free). |
| UI/UX Design | [`ui-ux-designer`](prompts/ui-ux-designer.md) | [prompts/ui-ux-designer.md](prompts/ui-ux-designer.md) | Standard design work (Go mid). |
|  | [`ui-ux-designer-pro`](prompts/ui-ux-designer.md) | [prompts/ui-ux-designer.md](prompts/ui-ux-designer.md) | Polished production UI, design systems (Go premium). |
| Introspection | [`introspector`](prompts/introspector.md) | [prompts/introspector.md](prompts/introspector.md) | Post-MDU session introspection (Go mid). |
| Inception | [`inception`](prompts/inception.md) | [prompts/inception.md](prompts/inception.md) | Idea → spec interviewer (Go budget; user-invoked). |

### Grok Build profiles (in [`grok/agents/`](grok/agents/))

All profiles currently use **grok-4.7** (grok-4.6 and grok-4.5 remain available). Invoke with `grok --agent <name>`.

| Role group | Agent | Profile | Notes |
| --- | --- | --- | --- |
| Orchestrator | [`orchestrator`](grok/agents/orchestrator.md) | [grok/agents/orchestrator.md](grok/agents/orchestrator.md) | Grok orchestrator variant. |
| Research | [`research`](grok/agents/research.md) | [grok/agents/research.md](grok/agents/research.md) | Research. |
| Coding | [`just-code`](grok/agents/just-code.md) / [`just-code-mid`](grok/agents/just-code-mid.md) / [`just-code-pro`](grok/agents/just-code-pro.md) | [grok/agents/](grok/agents/) | Coding variants. |
| Testing | [`test-agent`](grok/agents/test-agent.md) / [`test-agent-pro`](grok/agents/test-agent-pro.md) | [grok/agents/](grok/agents/) | Testing variants. |
| Code Review | [`code-reviewer`](grok/agents/code-reviewer.md) / [`code-reviewer-pro`](grok/agents/code-reviewer-pro.md) / [`grok-review`](grok/agents/grok-review.md) | [grok/agents/](grok/agents/) | Review variants. |
| Architecture | [`architect`](grok/agents/architect.md) / [`architect-premium`](grok/agents/architect-premium.md) | [grok/agents/](grok/agents/) | Design variants. |
| DevOps | [`devops`](grok/agents/devops.md) / [`devops-pro`](grok/agents/devops-pro.md) | [grok/agents/](grok/agents/) | Deploy variants. |
| QA | [`qa`](grok/agents/qa.md) / [`qa-pro`](grok/agents/qa-pro.md) | [grok/agents/](grok/agents/) | Validation variants. |
| UI/UX Design | [`ui-ux-designer`](grok/agents/ui-ux-designer.md) / [`ui-ux-designer-pro`](grok/agents/ui-ux-designer-pro.md) | [grok/agents/](grok/agents/) | Design variants. |
| Introspection | [`introspector`](grok/agents/introspector.md) | [grok/agents/introspector.md](grok/agents/introspector.md) | Post-MDU introspection. |
| Inception | [`inception`](grok/agents/inception.md) | [grok/agents/inception.md](grok/agents/inception.md) | Idea → spec interviewer. |

### Claude Code subagents (generated into `claude/agents/` during the build)

Every OpenCode agent is emitted as a Claude Code user-level subagent — generated from [`opencode.json`](opencode.json) + [`prompts/`](prompts/) at build time. The `model` is intentionally omitted so each subagent inherits your configured Claude Code model. Invoke them with `claude --agent <name>` or pick them in the interactive `/agents` view.


## How the Agents Work Together

These definitions are designed as a **collaborative team** rather than standalone tools. The `orchestrator` acts as the project manager, breaking work into **Minimum Deployable Units (MDUs)** and delegating to specialists. Built-in handoffs (especially mandatory review + test sign-off) create guardrails.

### Autonomy & Guardrails

The team currently operates at **L2 (session-autonomous)** on the industry-standard autonomy ladder and is targeting **L3 (goal-directed with approval gates)**. The orchestrator requires human approval before four classes of risky operations: pushing to protected branches, deploying non-green MDUs to production, destructive operations (deletes, DB migrations, irreversible ops), and exceeding 3 fix-retries on the same issue. Everything else flows autonomously. See [docs/autonomy.md](docs/autonomy.md) for the full ladder and gate definitions — per-MDU `autonomy_level` recorded in run manifests may exceed the team's declared position when approval gates were honored.

## Memory & Skills

- **Persistent memory:** Every orchestrator variant maintains dependency-free memory in `.agents/memory/` at the project being worked on (`project.md`, `decisions.md`, `session-<id>.md`) with append-only rules. See [Persistent Memory](#persistent-memory) below for details and [docs/design/mdu-04-lightweight-persistent-memory.md](docs/design/mdu-04-lightweight-persistent-memory.md).
- **Agent Skills:** The repo ships a skills library in [`skills/`](skills/) (e.g. `mdu-lifecycle`, `code-review-checklist`, `webapp-verification`, `test-patterns`, `secret-scrub`, `git-autonomy`). Skills follow the open Agent Skills format and are referenced by prompts where relevant. See each skill's `SKILL.md` for details.

### Orchestrator Delegation Flow

```mermaid
graph TD
    User[User Prompt / Task] --> Orch[Orchestrator]
    Orch --> JustCode[Just-Code<br/>Implements the MDU]
    JustCode --> Reviewer[Code-Reviewer<br/>Reviews for quality &amp; issues]
    Reviewer -->|Issues found| JustCode
    JustCode --> Tester[Test-Agent<br/>Writes tests &amp; validates]
    Tester -->|Tests failing| JustCode
    Tester -->|All green + sign-off| DevOps[DevOps<br/>Deploys the MDU if applicable]
    DevOps -->|success| QA[QA<br/>Manual validation]
    DevOps -->|failure or issues + report| Orch
    QA -->|PASS| Orch2[Orchestrator]
    QA -->|FAIL + detailed bug report| Orch
    Orch -->|root cause analysis + re-delegate fixes| JustCode
    Orch -->|root cause analysis + re-delegate fixes| DevOps
    Orch2 -->|Next MDU or done| Done[Summary + Artifacts]
    Orch --> Arch[Architect<br/>Produces design for current MDU]
    Orch --> Research[Research<br/>Gathers info if needed]
```

The orchestrator ensures every MDU is **designed → implemented → reviewed → tested → deployed → validated** before moving on.

### Post-MDU introspection

After QA PASS (or when any non-MDU task finishes), the orchestrator calls
[`introspector`](prompts/introspector.md) in **loop mode**. It reads the whole
session tree, detects friction signals (review rejection streaks, long cycles,
token hotspots, repeated tool errors, permission thrash, context reread, QA fail
repeat, stalled subagents), and writes durable suggestions to
`agent-improvements.md` at the project root. When an MDU id is provided, it also
writes `runs/<mdu-id>/introspection.md`. Long-cycle detection uses **active
time** (excluding idle gaps of 10+ minutes), not wall-clock time. The
introspector reports apply-now items back to the orchestrator, and every
orchestrator variant folds those items into the next loop by changing the next
brief, model tier/variant, and/or MDU slice. Agent definition files are **never
auto-edited** in loop mode.

**Review mode** is invoked by the user only (for example, when the project is
paused, blocked, or completed). In review mode the introspector proposes concrete
agent-definition diffs and records them in the log. It writes definition files
only after the user says the exact phrase `apply the definition diffs`;
"start now" and "looks good" are not consent.

**Failure / feedback loops for autonomy:**
- On DevOps failure or post-deploy issues: DevOps returns a diagnostic report. The orchestrator performs (or delegates) root cause analysis and re-delegates fixes — typically back to DevOps for infra retries, or to Just-Code/Architect if code or config changes are needed. The MDU is re-deployed and re-validated until it succeeds.
- On QA FAIL: QA returns detailed, severity-ranked bug reports with reproduction steps. The orchestrator routes the fixes (usually to Just-Code + Test-Agent for functional issues, or DevOps for deployment-related problems), then re-executes the deploy + validate phases. The loop continues until the MDU receives a clean PASS from QA (and successful DevOps).

### Persistent Memory

Every orchestrator variant maintains a dependency-free memory in `.agents/memory/`
**at the project being worked on** (not in this repo), so a fresh session starts
with the project's stable facts and past decisions instead of from zero:

| File | `type` | Purpose |
| --- | --- | --- |
| `.agents/memory/project.md` | `project` | Stable facts — stack, build/test commands, conventions, gotchas |
| `.agents/memory/decisions.md` | `decisions` | ADR-lite entries (Context / Decision / Consequences, one line each) |
| `.agents/memory/session-<id>.md` | `session` | Per-session log: `session-start`, `mdu-complete`, `checkpoint` entries |

Each file carries YAML frontmatter (`type`, `created`, `updated` — ISO-8601) and an
**append-only** body — entries are never edited or deleted; the only permitted
mutation is bumping `updated` when appending. The orchestrator reads `project.md`
and `decisions.md` at session start, appends an MDU summary (`mdu_id`, branch,
commit SHA, key decisions, ledger path) after each MDU is committed and pushed,
and appends a `checkpoint` entry (`completed` / `next` / `blockers` / `artifacts`)
whenever a session is interrupted or parked — the durable on-disk twin of the
resume block handed to the user. A resuming session starts from the newest
checkpoint (the pasted resume block wins if they disagree) instead of re-deriving
completed work.

The convention is plain markdown — no MCP server, no database, no SDK — so it
works identically on OpenCode, Grok Build, and Claude Code (Claude inherits it via
the generated orchestrator). Commit `project.md` and `decisions.md` (durable
knowledge that survives clones); commit session logs for the audit trail or
gitignore them per project. Never store secrets in memory — the secret gate scans
staged memory files like any other diff. Full format spec, edge cases, and test
plan: [docs/design/mdu-04-lightweight-persistent-memory.md](docs/design/mdu-04-lightweight-persistent-memory.md).

**Optional heavy upgrade path:** if a project outgrows file-based memory (semantic
recall across thousands of entries, cross-repo knowledge graphs),
[mem0](https://mem0.ai) or [Letta](https://letta.com) can layer on top as an
optional MCP memory server without changing the orchestrator's read/append
contract. Not recommended by default — it adds a runtime dependency for marginal
benefit at typical project scale.

### Just-Code + Review + Test Iteration Loop

The `just-code` agent is deliberately not allowed to declare victory alone:

```mermaid
graph TD
    K[Hand back to Orchestrator<br/>MDU considered complete]
    J[Just-Code: Implement per design spec] --> R[Code-Reviewer: Full review<br/>security, style, architecture]
    R -->|Issues or suggestions| J
    J --> T[Test-Agent: Add tests<br/>unit + integration + e2e]
    T -->|Failing tests or gaps| J
    T -->|All tests pass + sign-off| K
```

This loop continues until **both** the reviewer and tester are satisfied. The orchestrator will not mark the MDU done without these sign-offs.

### Example Project Prompt

```text
Build a simple REST API for a todo list using Node.js and Express.

Core requirements:
- Full CRUD for todos (title, description, completed status)
- In-memory storage to start (we can add a DB later)
- Basic input validation and error handling
- Follow clean, maintainable code practices

Please treat this as a series of Minimum Deployable Units. Start by having the architect produce a short design, then deliver one small, fully tested and reviewed slice at a time. I want working code + tests + review sign-off for each unit before moving to the next.
```

### How It Triggers the Agents (Example Walkthrough)

1. You run the prompt above against the `orchestrator` (e.g. `grok --agent orchestrator -p "..."` or via your OpenCode setup).

2. **Orchestrator** decomposes into MDUs (e.g.):
   - MDU 1: Project skeleton + basic Express server + health endpoint
   - MDU 2: Todo model + GET /todos + POST /todos
   - MDU 3: PUT /todos/:id + DELETE /todos/:id + validation
   - MDU 4: Error handling + basic tests across all endpoints

3. For MDU 1 it calls:
   - `architect` → produces `design-mdu1.md`
   - `just-code` (passing the design) → implements the server

4. **Just-Code** finishes its changes → hands off.

5. **Iteration Loop** (just-code ↔ reviewer ↔ test-agent):
   - `code-reviewer` reviews → finds missing error handling on one endpoint → sends feedback
   - `just-code` fixes → re-submits
   - `test-agent` writes tests → one test fails because of a status code bug → sends feedback
   - `just-code` fixes again
   - Both reviewer and tester now sign off

6. **Orchestrator** receives the completed MDU (with design doc, code diff, review comments, passing tests) and hands it to `devops`.

7. **DevOps** attempts deployment. If it fails or produces errors (e.g., port conflict or missing env var), it returns a diagnostic report. The orchestrator routes the fix (e.g., back to `just-code` for a config change or to `devops` for retry with better logging). The MDU is re-deployed until DevOps succeeds cleanly.

8. **QA** then performs validation. On FAIL (e.g., an endpoint returns 500 under load or a UI flow is broken), QA returns detailed bug reports with reproduction steps. The orchestrator root-causes the issue (delegating to `research` if needed) and re-delegates fixes — typically to `just-code` + `test-agent` for functional bugs, or `devops` for infra-related problems. It then re-triggers deploy + QA until the MDU receives a clean PASS.

9. Process repeats for subsequent MDUs. Final response from the orchestrator includes:
   - Summary of delivered units
   - Links to design docs, code, tests, deploy outputs
   - Any open questions or next steps

This structure keeps context small per agent while enforcing quality through mandatory collaboration, MDU discipline, **and autonomous failure recovery loops** at every phase (including post-deploy and post-QA).

This structure keeps context small per agent while enforcing quality through mandatory collaboration and the MDU discipline.

## Updating These Definitions with an AI Agent


One of the most powerful (and meta) things you can do with this repository is use an AI coding agent to improve the agent definitions themselves.

This repo is structured so that the OpenCode versions live in `prompts/<name>.md` and the corresponding Grok Build versions live in `grok/agents/<name>.md`. This makes it easy to keep behavior consistent across both tools. The Claude Code subagents are not hand-authored — they are generated from `prompts/<name>.md` + `opencode.json` during the build, so editing the OpenCode prompt is enough to update the Claude Code version too.

### Example Prompt to Update Both Versions at Once

If you have this repo checked out and are using an AI coding agent (such as the `grok` CLI or OpenCode itself), you can give it a prompt like this:

```
Please update BOTH the OpenCode version and the Grok Build version of the "just-code" agent so that it is only allowed to write code in x86 assembly language.

- OpenCode version: prompts/just-code.md
- Grok Build version: grok/agents/just-code.md

Make the constraints and instructions as consistent as possible between the two files. Do not change the overall structure or responsibilities of the agent unless necessary to enforce the x86 assembly rule. After editing, briefly summarize what you changed in each file.
```

Key tips:
- Always be explicit: say "BOTH the file in prompts/ AND the file in grok/agents/".
- Reference the exact relative paths.
- Ask the agent to keep the two versions consistent.
- You can use the same pattern for any agent (orchestrator, code-reviewer, architect, etc.).

This approach lets you evolve the entire "dual" definition set (OpenCode + Grok) in a single conversation without having to remember the internal structure.

## Extending with Your Own Overlays (Recommended Pattern)

The most powerful way to use this repository is as a **stable base** that you layer your own customizations on top of.

### The Two-Layer Model

- **Base (this repo)**: Generic, well-tested agent roles and prompts.
- **Overlays (your repo)**: Project-specific rules, domain knowledge, custom agents, MCP integrations, style guides, and workflow instructions.

This separation keeps the public base clean while letting you (or your team) maintain powerful, opinionated behavior.

### Base ↔ Overlay Contract

This repo is the **public generic base**. Your private or team-specific customizations belong in a **separate overlay repository** — never committed here.

Overlay projects consume this base via the `GENERIC_DIR` environment variable (or by placing this repo as a sibling directory named `base_agents`, `open-agent-definitions`, or `open_agent_definitions`).

**Expected overlay build flow:**

1. Run **this repo's** `./build.sh` (or read from `build/` if already staged) to get validated generic definitions.
2. Merge personal overlays (appended rules, custom agents, MCP config, extra skills).
3. Regenerate Claude Code subagents from the merged `opencode.json` + `prompts/` so overlay deltas flow through to Claude too.
4. Validate the combined `build/` output (JSON syntax, prompt file references, Grok frontmatter, Claude subagent frontmatter).
5. Deploy **only** from the combined `build/` directory — do not re-deploy the generic base separately.

### Creating Your Own Overlay Repository

A typical private overlay repo structure:

```
my-overlays/                   # private repo — your rules, MCPs, custom agents
├── README.md
├── build.sh                   # thin entry point → scripts/build.sh
├── deploy.sh                  # thin entry point → scripts/deploy.sh
├── scripts/
│   ├── build.sh               # stage base + merge overlays + validate
│   ├── deploy.sh              # install from build/ + CLI validation
│   └── lib/                   # shared helpers (detect GENERIC_DIR, merge JSON, etc.)
├── overlays/
│   ├── manifest.json          # which snippet files apply globally vs per-agent
│   ├── team-coding-standards.txt   # example: snippet appended to all agents
│   ├── prompts/               # full prompt overrides (optional)
│   ├── grok/agents/           # full grok profile overrides (optional)
│   └── opencode-mcp.json      # MCP servers to merge into opencode.json
└── build/                     # generated output (gitignored) — deploy from here
```

#### overlays/manifest.json (recommended)

Declare overlay snippets declaratively instead of hard-coding agent names in build scripts:

```json
{
  "global_snippets": ["team-coding-standards.txt"],
  "agent_snippets": {
    "devops": ["deploy-safety-rules.txt"],
    "just-code": ["monorepo-conventions.txt"]
  }
}
```

Global snippets are appended to every base prompt/profile. Per-agent snippets are appended only to matching agent stems (e.g. `devops` applies to both `prompts/devops.md` and `grok/agents/devops.md`).

Full files in `overlays/prompts/` or `overlays/grok/agents/` replace the base copy for that agent name.

You don't author overlays for Claude Code separately: because the Claude Code subagents are generated from the merged `opencode.json` + `prompts/` *after* overlays are applied, any global/per-agent snippet or full-prompt override automatically flows into the corresponding `~/.claude/agents/<name>.md` file.

### What Belongs in an Overlay?

Useful things to put in overlays include:

- **Shared rules** — Coding standards, commit message formats, architectural principles, or safety constraints you want every agent to follow.
- **Domain-specific agents** — Custom agents for your tech stack, company processes, or niche problem domain.
- **MCP and tool configuration** — Private or project-specific MCP servers.
- **Workflow instructions** — How you like tasks broken down, review processes, deployment pipelines, etc.
- **Model preferences** — Default models, temperatures, or effort levels for certain roles.
- **Additional prompts** — Full specialized agents that build on the base roles.

### Tips for Healthy Overlays

- Prefer **appending** rules to base prompts rather than forking them when possible. This makes it easier to pull updates from the base repo later.
- Keep your overlay prompts focused and well-documented.
- Version your overlay repo together with your main projects so the combination stays consistent.
- Document in your overlay README which base agents you use and what customizations you've applied.

## Repository Layout (Base)

```
base_agents/                   # this public repo
├── .github/workflows/ci.yml   # CI: build, validate, lint, JSON/schema/frontmatter, smoke evals
├── build.sh                   # stage source → build/, generate Claude agents, validate
├── deploy.sh                  # install from build/ (or root fallback)
├── scripts/                   # build/deploy + libs
│   ├── build.sh
│   ├── deploy.sh
│   └── lib/                   # validate.py, run_ledger.py, run_evals.py, prompt_regression.py, secret_scan.py, model_registry.py, gen_claude_agents.py
├── schemas/
│   └── opencode.schema.json   # JSON Schema for opencode.json
├── config/
│   └── model-registry.txt     # Model allowlist (pinned)
├── opencode.json              # OpenCode agent registry (28 agents across model tiers)
├── prompts/                   # OpenCode prompt bodies (canonical system prompts) — 11 files
│   ├── orchestrator.md
│   ├── just-code.md
│   ├── test-agent.md
│   ├── code-reviewer.md
│   ├── architect.md
│   ├── devops.md
│   ├── qa.md
│   ├── research.md
│   ├── ui-ux-designer.md
│   ├── introspector.md
│   └── inception.md
├── grok/agents/               # Grok Build agent profiles (20 profiles)
│   ├── orchestrator.md, research.md, inception.md, introspector.md, grok-review.md
│   ├── just-code.md, just-code-mid.md, just-code-pro.md
│   ├── test-agent.md, test-agent-pro.md
│   ├── code-reviewer.md, code-reviewer-pro.md
│   ├── architect.md, architect-premium.md
│   ├── devops.md, devops-pro.md
│   ├── qa.md, qa-pro.md
│   └── ui-ux-designer.md, ui-ux-designer-pro.md
├── skills/                    # Agent Skills (7 skills)
│   ├── mdu-lifecycle/, code-review-checklist/, webapp-verification/, test-patterns/, secret-scrub/, git-autonomy/
├── docs/                      # Design docs, autonomy, security, MCP, observability, model registry
│   ├── autonomy.md, security.md, mcp.md, observability.md, model-registry.md
│   └── design/
├── evals/                     # Golden evaluation suite
│   ├── README.md, promptfoo.yaml, golden/, tasks/
├── examples/                  # Artifact gallery
│   ├── README.md, gallery/, runs/, mcp/, upgrade-story.md
├── tests/                     # Test suite
└── build/                     # generated output (gitignored)
    ├── opencode.json, prompts/, grok/agents/, claude/agents/
```

## Getting Started with Your Own Setup

1. Clone **this repository** as your public/generic base.
2. Create a **separate private overlay repository** for your workflow rules, MCP servers, and custom agents.
3. Point the overlay at this base via `GENERIC_DIR` or a sibling directory.
4. Have the overlay `build.sh` run this repo's `build.sh`, merge overlays, and validate.
5. Have the overlay `deploy.sh` install only from the combined `build/` output.
6. Iterate on overlays independently; pull base updates when the generic layer improves.

This pattern gives you powerful, personalized agents while still benefiting from improvements to the shared foundation.

**Discoverability note for AI agents / overlay projects**: When this base is used from a personal or team overlay project (often a sibling directory on disk with its own `overlays/`, `build.sh`, and `deploy.sh`), the AI session context will typically start in the overlay project. That project's steering files (README.md or AGENTS.md) will explicitly instruct the AI to read *this* README first for the generic foundation before applying any local overlays. This ensures the root shareable repo is always discoverable.

## Roadmap

This repo is actively being upgraded to the bleeding edge of autonomous agentic development. See:

- **[GAP_ANALYSIS.md](GAP_ANALYSIS.md)** — a full gap analysis against mid-2026 best practice (memory, skills, MCP, observability, evals, CI, security), including a live demonstration of model drift in the research agent configs.
- **[FEATURE_BACKLOG.md](FEATURE_BACKLOG.md)** — a prioritized, MDU-sized implementation backlog consumable by this repo's own orchestrator. The agent team builds its own upgrade.

(last verified 2026-10-23) **Progress:** **14/15** backlog items complete (MDU-01, 02, 03, 05, 06, 07, 08, 09, 11, 12, 13, 14, 15) — see [examples/upgrade-story.md](examples/upgrade-story.md) and [examples/gallery/](examples/gallery/) for worked examples.

## How This Repo Was Upgraded by Its Own Agents

This repository's own orchestrator and subagents executed the backlog above over a single autonomous session. Every change went through the closed loop — **design → implement → review → test → validate** (with deploy included whenever infrastructure was touched) — with code-reviewer sign-off and a QA PASS before the orchestrator committed and pushed. CI (introduced during MDU-02) was green on every push from MDU-02 onward — including one caught-and-fixed workflow failure in the first MDU-02 run (missing pip dependency manifest).

The session grew the test suite from **33 → 136 tests** (all passing) and shipped CI, skills, a run ledger, evals, MCP reference docs, autonomy gates, and cross-CLI parity. The two broken free-tier research agents were repaired to current models.

- Full dogfooding narrative, commit trail, and lessons learned: **[examples/upgrade-story.md](examples/upgrade-story.md)**
- Real run manifests from the session: **[examples/runs/](examples/runs/)** (`mdu-05/`, `mdu-06/`, `mdu-07/`, `mdu-08/`, `mdu-12/`, `mdu-14/` are real session manifests; `mdu-01-example/` and `mdu-02-example/` are illustrative)

## Contributing

Improvements to the generic layer are welcome. When contributing, please keep prompts focused on general-purpose behavior so they remain useful as a base for many different overlay projects.

---

*This repository is intended to be used as a foundation. The real power comes when you combine it with your own overlays.*

## License

This project is released under [The Unlicense](https://unlicense.org/).
