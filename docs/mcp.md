# MCP Reference Configuration

How to wire Model Context Protocol (MCP) servers into this agent harness, which
servers each agent role should see, and how the loop degrades when MCP is
absent. Companion to the runnable example in
[`examples/mcp/`](../examples/mcp/).

## What MCP is and why the loop needs it

The **Model Context Protocol** is an open standard (spec revision
**2025-03-26**, stable) that lets an LLM client expose external capabilities as
three primitives:

- **Tools** — callable functions the model can invoke (browse, query, mutate).
- **Resources** — data the client can read (files, DB rows, docs).
- **Prompts** — reusable prompt templates served by the server.

An MCP server is a small process (stdio or HTTP) that speaks this protocol; the
client (OpenCode, Claude Code, Grok) spawns it and surfaces its tools alongside
the built-in ones. The agent loop here needs MCP for three things the built-in
toolset cannot do well:

1. **Browser verification** — QA must navigate, snapshot, and screenshot real
   web UIs. The `webapp-verification` skill prefers `@playwright/mcp` with
   `browser-os` as fallback; without an MCP browser server, QA can only report
   BLOCKED (see [Degradation contract](#degradation-contract)).
2. **Git host operations** — PRs, issues, and reviews against GitHub without
   hand-rolled `gh`/curl plumbing in prompts.
3. **Database access** — read-only DB inspection for devops/QA when a DB MCP
   server is added later.

## Reference server choices

| Server | Purpose | Install / run |
| --- | --- | --- |
| **Playwright MCP** | Browser verification: accessibility snapshots, screenshots, console/network inspection, interaction | `npx @playwright/mcp@latest` — add `--caps vision` to enable screenshot analysis; `--caps=devtools,network,testing` matches the harness default. Docker sandbox: `docker run --rm -i -p 8931:8931 mcr.microsoft.com/playwright/mcp` |
| **Filesystem MCP** | Scoped file read/write for agents that need it | `npx -y @modelcontextprotocol/server-filesystem /path/to/dir` — pass **only** the directories you intend to expose; the server refuses paths outside the allowlist |
| **GitHub MCP** | PRs, issues, reviews, repo metadata | `docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN ghcr.io/github/github-mcp-server` or `npx -y @modelcontextprotocol/server-github` — scope the PAT to the repos/orgs the devops agent actually touches |
| **Memory MCP** (optional) | Persistent cross-session memory for the orchestrator | `npx -y @modelcontextprotocol/server-memory` — an optional upgrade path that ties into the memory notes in [`docs/observability.md`](observability.md); not required for the loop |

Keep the server set small: every MCP server adds tools to the model context,
and the GitHub server in particular is token-hungry.

### Playwright MCP details

- Server name is typically `playwright`; the package is `@playwright/mcp`.
- `--caps vision` enables screenshot analysis (the model can "see" pages);
  `--caps=devtools,network,testing` enables console/network inspection and
  browser testing tools. The harness default on this machine is
  `npx -y @playwright/mcp@latest --caps=devtools,network,testing`.
- The Docker image `mcr.microsoft.com/playwright/mcp` runs the same server in
  a sandboxed container with browsers pre-installed — use it when you want
  isolation from the host (no local browser install, no host filesystem
  exposure beyond what the container mounts).
- The `webapp-verification` skill (`skills/webapp-verification/SKILL.md`) is
  the recipe that consumes these tools: navigate → snapshot → interact →
  console/network → screenshot, then BLOCKED reporting if the tools are absent.

### GitHub MCP details

- The Docker image `ghcr.io/github/github-mcp-server` is the officially
  maintained server; the npm variant `@modelcontextprotocol/server-github`
  runs the same protocol via `npx`. Both read the token from the
  `GITHUB_PERSONAL_ACCESS_TOKEN` environment variable.
- **Token scoping matters**: use a fine-grained PAT limited to the repos the
  devops agent actually operates on, with an expiry. A broad classic token
  turns the GitHub MCP server into a wide-open API surface for the model.
- The GitHub server is verbose — its tools add a lot of tokens to context.
  Scope it to the `devops*` agents only (see the table below).

## Per-CLI configuration

| CLI | Location | Verified? |
| --- | --- | --- |
| **OpenCode** (v1.17.x) | `mcp` key in project `opencode.json` (or global `~/.config/opencode/opencode.json`). Local servers: `{ "type": "local", "command": ["npx", "-y", "..."], "environment": {...}, "enabled": true }`. Per-agent scoping via the `tools` key (glob `"playwright_*": true` on the agent, `"playwright*": false` globally). | **Verified** against opencode.ai docs and the installed v1.17.11 binary/source. Note: `.mcp.json` is **not** auto-loaded by OpenCode 1.17.x; it is the Claude Code convention. Use `.mcp.json` only as a portable cross-tool file and merge it into `opencode.json` for OpenCode. |
| **Claude Code** (v2.1.x) | Project-level `.mcp.json` at the repo root; user-level servers in `~/.claude.json`. Manage with `claude mcp add/list`. | **Verified** locally (`claude mcp list` shows the configured `playwright` server; `claude mcp --help` documents project-scoped `.mcp.json`). |
| **Grok** | `grok mcp add <name> <cmd-or-url>` CLI; config written to `~/.grok/config.toml` (user scope, `-s user`) or `./.grok/config.toml` (project scope, `-s project`) under `[mcp_servers.<name>]`. Diagnose with `grok mcp doctor`. | **Verified** locally (`grok mcp list` shows `playwright` and `browser-os` already configured on this harness). |

The local harness already has `playwright` (`npx -y @playwright/mcp@latest
--caps=devtools,network,testing`) and `browser-os` configured for both Grok and
Claude Code; OpenCode is the gap this document closes.

### OpenCode config shape (v1 style, matches this repo's `opencode.json`)

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "playwright": {
      "type": "local",
      "command": ["npx", "-y", "@playwright/mcp@latest", "--caps=devtools,network,testing"],
      "enabled": true
    },
    "github": {
      "type": "local",
      "command": ["npx", "-y", "@modelcontextprotocol/server-github"],
      "environment": { "GITHUB_PERSONAL_ACCESS_TOKEN": "{env:GITHUB_PERSONAL_ACCESS_TOKEN}" },
      "enabled": true
    }
  },
  "tools": { "playwright*": false, "github*": false },
  "agent": {
    "qa": { "tools": { "playwright*": true } },
    "devops": { "tools": { "github*": true } }
  }
}
```

`{env:VAR}` is substituted from the environment at load time — never inline a
token. A ready-to-copy variant with playwright + filesystem + github is in
[`examples/mcp/opencode.mcp.json.example`](../examples/mcp/opencode.mcp.json.example).

## Per-agent scoping

| Agent role | MCP servers | Rationale |
| --- | --- | --- |
| `qa`, `qa-pro`, `qa-free` | **playwright** (browser verification) | The `webapp-verification` skill's preferred tool; `browser-os` only as fallback |
| `devops`, `devops-pro`, `devops-free` | **github** | PR/issue/release operations against the git host |
| `just-code`, `just-code-mid`, `just-code-pro`, `just-code-free` | **filesystem** (read) | Scoped read access to workspace dirs when needed; no write outside the allowlist |
| `code-reviewer`, `code-reviewer-pro`, `code-reviewer-free` | **none** | Review-only role; MCP tools add context and attack surface without adding review value |
| `orchestrator`, `research`, `architect`, `test-agent*`, `ui-ux-designer*` | **none by default** | Keep context lean; add per-task if a concrete need appears |

In OpenCode, enforce this with the `tools` key: disable MCP servers globally
(`"playwright*": false`), then re-enable per agent (`"playwright*": true`).

## Quick start

1. Pick the servers you need from the reference table (start with playwright
   for QA, github for devops).
2. Add them to your CLI's config (per-CLI table above) with `enabled: true`
   and tokens via `{env:VAR}`.
3. Scope servers to agents with the `tools` key (OpenCode) or equivalent
   per-agent tool permissions.
4. Sanity-check with the client's own tooling: `opencode mcp list`,
   `claude mcp list`, or `grok mcp doctor`.
5. If a server fails to start or connect, the loop still runs — see the
   degradation contract below.

## Degradation contract

The loop **must** work without MCP. MCP is an enhancement, never a hard
dependency: the `webapp-verification` skill already mandates **BLOCKED**
reporting when no browser tooling is available — QA reports which tools it
looked for, what failed, and that Playwright/browser-os needs configuring, then
still runs the non-browser checks (HTTP, CLI, logs, edge cases). The same
principle applies to every other server: if an MCP tool is missing or errors,
fall back to built-in tools (`bash`, `webfetch`, `gh`) or report the gap —
never silently skip coverage and never block the pipeline on MCP availability.

## Security

- **Origin allowlists** — for remote/HTTP servers, restrict to known endpoints
  and keep OAuth/header secrets out of the config file (use `{env:VAR}`
  substitution or the client's secret store).
- **Scoped file access** — filesystem MCP gets explicit directory args only
  (e.g. `./workspace`); never pass `/` or `~`.
- **Never mount `~/.ssh`** into any MCP server or container; git auth stays in
  the client's own credential helpers.
- **Short-lived tokens** — use fine-grained, expiring PATs for GitHub MCP,
  scoped to the repos the devops agent needs.
- **MCP consent** — approve/deny MCP server additions deliberately; treat a new
  server as a new tool with full context access. Disable servers you are not
  actively using.