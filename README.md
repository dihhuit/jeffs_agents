# Open Agent Definitions

These are generic, reusable agent definitions for [OpenCode](https://opencode.ai) and [Grok Build](https://x.ai) (the `grok` CLI from xAI) which have been distilled from my own, very personal and workflow specific agent definitions into something shareable. How I use these is overlaying my own workflow specific deltas (see below for details) to personalize them for how I like to work. These agents represent a "team" with specific focus or specialization areas. Whenever I'm working on a project, I start with the orchestrator, and have it farm out tasks to the other agents. Having specialized agents like this allows me to a) minimize per-agent context, and b) implement guardrails in the form of inter-agent checks and balances (e.g. to prevent the just-code agent from cheating on tests by updating the tests).

This repository provides a **base layer** of agent definitions designed to be broadly applicable across different projects and users. The prompts have been kept focused on core responsibilities rather than any single team's specific workflows or tooling.

## Using These Agents As-Is

### For OpenCode

1. Clone or download this repository.
2. Run the included deploy script:

   ```bash
   ./deploy.sh --force
   ```

   This installs the configuration to `~/.config/opencode/`.

3. The `opencode.json` file in the root provides a ready-to-use set of agents. You can use it directly, copy sections from it, or merge it with your existing configuration.

### For Grok Build

Agent profiles live in `grok/agents/`. You can use them directly:

```bash
grok --agent just-code -p "Implement a small feature..."
```

Or copy the `.md` files into your user-level (`~/.grok/agents/`) or project-level (`.grok/agents/`) directories so they are always available.

### Core Agents Included

**OpenCode agents** (defined in `opencode.json` and `prompts/`):

- `orchestrator` — Primary coordinator that decomposes tasks and delegates to specialists.
- `just-code` — Focused production coder (writes code that builds, lints, and passes tests).
- `code-reviewer` — Gatekeeper that reviews changes for quality, security, and maintainability.
- `architect` — Produces high-level and low-level design documents and architecture.
- `test-agent` — Writes and maintains tests across the testing pyramid.
- `devops` — Generic infrastructure and deployment specialist.
- `qa` — Quality assurance and manual validation.
- `research` — Web research and documentation gathering.
- `ui-ux-designer` — UI/UX design, mocks, and interaction flows.

**Grok Build profiles** (in `grok/agents/`):

A full matching set of profiles is provided so you can use the same agent roles with Grok models:

- `orchestrator`
- `just-code`
- `test-agent`
- `code-reviewer`
- `architect`
- `devops`
- `qa`
- `research`
- `ui-ux-designer`

You can invoke them with `grok --agent <name>` (e.g. `grok --agent just-code` or `grok --agent code-reviewer`).

You can extend or override any of these in your own setups. The old `grok-review` profile is still present for compatibility but `code-reviewer` is the recommended name going forward.

## Updating These Definitions with an AI Agent

One of the most powerful (and meta) things you can do with this repository is use an AI coding agent to improve the agent definitions themselves.

This repo is structured so that the OpenCode versions live in `prompts/<name>.md` and the corresponding Grok Build versions live in `grok/agents/<name>.md`. This makes it easy to keep behavior consistent across both tools.

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

### Creating Your Own Overlay Repository

A typical overlay repo can be very small. Here's a recommended starting structure:

```
my-overlays/
├── README.md
├── build.sh                 # Combines base + your overlays
├── overlays/
│   ├── prompts/
│   │   └── common-rules.md  # Rules you want appended to many agents
│   ├── grok/
│   │   └── agents/
│   │       └── my-specialist.md
│   └── opencode-additions.json
└── deploy.sh                # Your deploy script (points at build/ output)
```

#### Example: Simple Build Script

A minimal `build.sh` might look like this:

```bash
#!/usr/bin/env bash
set -euo pipefail

GENERIC_DIR="${GENERIC_DIR:-../open-agent-definitions}"
OVERLAY_DIR="./overlays"
BUILD_DIR="./build"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/prompts" "$BUILD_DIR/grok/agents"

# Copy generic prompts and append overlay rules
for prompt in "$GENERIC_DIR"/prompts/*.md; do
  name=$(basename "$prompt")
  cp "$prompt" "$BUILD_DIR/prompts/"
  if [ -f "$OVERLAY_DIR/prompts/common-rules.md" ]; then
    echo "" >> "$BUILD_DIR/prompts/$name"
    cat "$OVERLAY_DIR/prompts/common-rules.md" >> "$BUILD_DIR/prompts/$name"
  fi
done

# Copy generic Grok profiles + your custom ones
cp "$GENERIC_DIR"/grok/agents/*.md "$BUILD_DIR/grok/agents/" 2>/dev/null || true
cp "$OVERLAY_DIR"/grok/agents/*.md "$BUILD_DIR/grok/agents/" 2>/dev/null || true

# Merge opencode.json additions (example using a simple approach)
cp "$GENERIC_DIR/opencode.json" "$BUILD_DIR/opencode.json"
# You can use jq, a small Python script, or manual merging here for agent additions/MCPs.

echo "Build complete. Output in $BUILD_DIR"
```

Then point your personal `deploy.sh` at the `build/` directory.

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

## Getting Started with Your Own Setup

1. Clone this repository as your base.
2. Create a separate (private or team) overlay repository.
3. Write a small `build.sh` that produces a combined `build/` directory.
4. Use or adapt the deploy script to install from your build output.
5. Iterate on your overlays independently of the generic base.

This pattern gives you powerful, personalized agents while still benefiting from improvements to the shared foundation.

## Contributing

Improvements to the generic layer are welcome. When contributing, please keep prompts focused on general-purpose behavior so they remain useful as a base for many different overlay projects.

---

*This repository is intended to be used as a foundation. The real power comes when you combine it with your own overlays.*
