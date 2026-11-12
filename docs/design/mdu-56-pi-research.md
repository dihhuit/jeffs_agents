# pi coding agent — customization surface research (for MDU-56)

**Provenance (read first):**
- `github.com/badlogic/pi-mono` now **redirects to `github.com/earendil-works/pi`** ("AI agent toolkit", ~121k stars, 7,845 commits). Docs live at `packages/coding-agent/docs/`.
- npm package **`@mariozechner/pi-coding-agent` is legacy** (registry `dist-tags.latest` = **0.73.1**). Current package is **`@earendil-works/pi-coding-agent`, latest = 1.5.2** — that is exactly the local install (`~/.pi/agent/install/releases/1.5.2/`). So "pi 1.5.2" = earendil package, not mariozechner.
- Repo HEAD verified: commit **`a40abec`** (short sha; full hash in the repo log, 2026-11-12, mitsuhiko). Docs cited below are `main` at that commit; where behavior is version-specific I checked the **bundled 1.5.2 docs/code** in the local install instead.

---

## 1. Agent directory + settings (`~/.pi/agent/`)

Agent directory defaults to `~/.pi/agent`; docs: configuration.md.

| Path | Purpose | Managed by |
|---|---|---|
| `settings.json` | user settings (models, tools, resource paths, packages); supports `"$schema": "https://pi.dev/schemas/settings.schema.json"` | **user** (also written by `pi install`, `/settings`) |
| `auth.json` | API keys + OAuth tokens (can hold `!command` lookups) | **machine-written** via `/login`, user-owned secret; do not commit |
| `models.json` | compatible endpoints, custom models, `modelOverrides` | **user** |
| `models-store.json` | dynamic model-catalog store (file-backed dynamic catalogs, per-provider pi.dev catalog overlays, offline cache) | **machine-managed** — code `src/core/models-store.ts` (`join(getAgentDir(), "models-store.json")`, 1.5.2 `dist/core/models-store.js:30`) |
| `sessions/` | session JSONL, one subdir per working directory (observed: `sessions/--home-dihhuit-temp--/<ts>_<uuid>.jsonl`) | machine-written |
| `install/` | pi.dev installer payload: `managed-install.json` (`kind: "pi-managed-install"`, `layout: "releases-v1"`, entrypoint symlink `~/.local/bin/pi`), `releases/<ver>/node_modules/`, `current-version` | **machine-managed** (installer/`pi update`) |
| `bin/` | helper binaries (local: `pi`, `rg`, `fd`) — `join(getAgentDir(), "bin")` in 1.5.2 `dist/config.js:539` | machine-managed |
| `npm/`, `git/`, `tmp/extensions/` | installed Pi packages (see Q3) | machine-managed |
| `trust.json` | saved project-trust decisions (docs/security.md) | machine-written (`/trust`) |
| `keybindings.json`, `mcp.json` | keybinds, global MCP servers | user |
| `AGENTS.md`/`CLAUDE.md`(+`AGENTS.override.md`), `SYSTEM.md`, `APPEND_SYSTEM.md` | instructions / system-prompt replace & append | user |
| `extensions/`, `skills/`, `prompts/`, `themes/` | auto-discovered personal resources | user |

**Can settings point at a different agent directory? No setting does that.** The only switches are env/SDK: `PI_CODING_AGENT_DIR` (config dir), `PI_CODING_AGENT_SESSION_DIR` + `--session-dir` + `sessionDir` setting, `PI_PACKAGE_DIR` (docs/environment-variables.md). `sessionDir` is the only setting read before project trust resolves.

## 2. Prompt templates vs skills vs extensions

| | Prompt templates | Skills | Extensions |
|---|---|---|---|
| What | single Markdown file, optional YAML frontmatter (`description`, `argument-hint`) | directory with `SKILL.md` (+ `scripts/`, `references/`, `assets/`), Agent Skills spec | TypeScript module, `export default function (pi: ExtensionAPI)` |
| Purpose | reusable **prompt text** as a `/`-command; no executable behavior | **on-demand instructions** + supporting files, lazily loaded | **executable behavior**: tools, commands, events, UI, flags, providers |
| Discovery | `<agent-dir>/prompts/` (direct `.md` children only), `.pi/prompts/` (trust-gated), settings `prompts[]` (globs/nested ok), packages, `--prompt-template <path>` | `<agent-dir>/skills/`, `.pi/skills/` (recursive, found from cwd up to repo root), plus `~/.agents/skills/` and `.agents/skills/`, settings `skills[]`, packages, `--skill <path>` | `<agent-dir>/extensions/`, `.pi/extensions/`, settings `extensions[]`, packages, `-e/--extension`; built-ins `builtin:mcp`, `builtin:llama.cpp`, `builtin:codemode`, `builtin:tool-search` |
| Invocation | type `/name [args]`; substitutions `$1`, `$ARGUMENTS`, `${1:-default}`, `${@:N:L}`; expanded **before** text reaches the model (extensions see raw input first via `input` event) | name+description go into the system prompt at startup; model reads `SKILL.md` when needed; force with `/skill:name args`; `disable-model-invocation: true` restricts to manual; setting `enableSkillCommands` | loaded at startup automatically; may `registerCommand()` (own `/`-commands), `registerTool()`, `pi.on(...)` |
| Disable flags | `-np/--no-prompt-templates` | `-ns/--no-skills` | `-ne/--no-extensions` (explicit `-e` still loads) |

Docs: prompt-templates.md, skills.md, extensions.md. `/reload` picks up changes in auto-discovered dirs.

## 3. Packages

- **What:** an ordinary directory or npm package containing any/all of `extensions/`, `skills/`, `prompts/`, `themes/` — **yes, all four resource types ship together in one package**. Explicit manifest via a `pi` key in `package.json` with glob arrays (and `"keywords": ["pi-package"]` for the gallery); without it, conventional dirs are auto-discovered. Runtime deps go in `dependencies`; host packages (`@earendil-works/pi-ai`, `pi-agent-core`, `pi-coding-agent`, `pi-tui`, `typebox`) as `peerDependencies: "*"`. Docs: packages.md.
- **Install:** `pi install npm:@scope/pkg@1.0.0 | git:github.com/user/repo@v1 | https://... | ./local`; `pi remove/uninstall`, `pi list`, `pi config` (enable/disable resources), `pi update --extensions`. `--local/-l` writes to project `.pi/settings.json` (trust-gated); default writes to `~/.pi/agent/settings.json`.
- **Where installed (1.5.2 code, `dist/core/package-manager.js`):** npm → `<agentDir>/npm/node_modules/<name>` (legacy global-npm fallback path exists); git → `<agentDir>/git/` (line 1966) or `<cwd>/.pi/git/` (project, line 1964); `-e`-style sources cached under `<agentDir>/tmp/extensions/` (line 87). npm packages are pinned; git tags/commits are pinned and reconciled.
- **Registry:** no bespoke registry — distribution is npm/git. Discovery exists: the **Pi package gallery at https://pi.dev/packages**, eligible via the `pi-package` npm keyword (+ optional `pi.image`/`pi.video`).

## 4. Custom system prompts per role

**pi has no native named persona/agent-profile registry and no built-in sub-agents** — README (HEAD): "Pi ships with powerful defaults but skips features like sub-agents and plan mode." No `profiles`/`personas` key exists in settings.md.

Ways to model role-specialized behavior:
1. **Per-run system prompt:** `--system-prompt <text|path>` (replaces) and `--append-system-prompt <text|path>` (repeatable) — launch one process per role. 1.5.2 `--help`: `dist/cli/args.js:297-298`.
2. **Per-directory system prompt:** `<agent-dir>/SYSTEM.md` / `APPEND_SYSTEM.md` (global) and `.pi/SYSTEM.md` / `APPEND_SYSTEM.md` (per project; trusted project file wins, files not combined) — docs/configuration.md. Combined with a per-role `PI_CODING_AGENT_DIR`, this yields fully isolated "profiles" (each dir has its own SYSTEM.md, settings.json, extensions).
3. **Template chosen at launch:** pass `/template-name args` as the message of a one-shot run; the template expands (see Q8) — but this injects a **user** message, not the system prompt.
4. **Extension mechanisms (the intended pi way):**
   - `before_agent_start` event can replace/patch the system prompt per turn, or mutate structured `systemPromptOptions` sections/tools (docs/extensions.md §Agent Events; examples `pirate.ts` "Modify system prompt per-turn", `prompt-customizer.ts`, `system-prompt-header.ts`).
   - `examples/extensions/preset.ts` — "Named presets for model, thinking level, tools, and instructions" (registerCommand / registerFlag / setModel / setActiveTools).
   - `examples/extensions/subagent/` — "Delegate tasks to specialized subagents with isolated context windows" (`registerTool`, `exec`); also docs/extensions.md example table line 3346.
   - `dynamic-tools.ts` — register tools after startup with prompt snippets.

## 5. Provider/model selection

- **`models.json` (user-managed)** = custom/proxy endpoints, extra models, `modelOverrides`. **`models-store.json` (machine-managed)** = pi's own dynamic catalog cache (bundled + pi.dev overlay + offline) — do not hand-edit. Docs: models.md, configuration.md.
- **Credential precedence** (models.md §Authenticate): runtime `--api-key` → stored `auth.json` credential → `apiKey` from `models.json` → provider env vars/ambient credentials.
- **xai auth:** `/login xai` (writes `auth.json`) **or** env var **`XAI_API_KEY`** (providers.md env table). Both supported; env is preferred for CI ("where Pi should not write credentials").
- **Default xai model id in pi 1.5.2 = `grok-4.7`** — `defaultModelPerProvider.xai: "grok-4.7"`, source `packages/coding-agent/src/core/model-resolver.ts` at HEAD (identical at 1.5.2, `dist/core/model-resolver.js:25`). Used by `findInitialModel()` as step 3. The local `~/.pi/agent/settings.json` also pins `{"defaultProvider":"xai","defaultModel":"grok-4.7"}` (user-set, same value).
- **Selecting a non-default model:** CLI `--model <pattern>` (exact/fuzzy, `provider/id`, optional `:<thinking>` suffix), `--provider <name>` (requires `--model`), `--thinking <level>`, `--models <patterns>` (cycle scope, globs), `--api-key <key>` (non-persistent), `--list-models [search]`. Interactive `/model` (Ctrl+S saves default); `Ctrl+P` cycles; `--models`/`enabledModels` bound the cycle. A session **records** model/thinking changes and restores them on resume without changing defaults.

## 6. Tool/permission model

- **Built-in tools:** `read`, `bash`, `powershell`, `edit`, `write`, `grep`, `find`, `ls`; defaults enabled = `read`, `bash`, `edit`, `write`. Built-in extensions add `codemode` and `tool_search` (off by default). MCP tools are separate.
- **Configuration:** `defaultTools` in `~/.pi/agent/settings.json` and `.pi/settings.json` (plain names replace; `+name`/`-name` modify; project appends on top of user), CLI `--tools/-t <allowlist|+/-list>`, `--exclude-tools/-xt`, `--no-tools/-nt`, `--no-builtin-tools/-nbt`. Docs: settings.md §Tools, cli.md §Tools.
- **Permissions: pi has NO built-in permission system.** README §Permissions & Containerization: "Pi does not include a built-in permission system for restricting filesystem, process, network, or credential access… containerize or sandbox Pi." Tool allowlists only control what the **model can call**, not a security boundary. Two mitigation layers: (a) **extensions** as gates (`examples/extensions/permission-gate.ts`, `protected-paths.ts`, `confirm-destructive.ts`, `tool-override.ts`), (b) **containerization** (docs/containerization.md).
- **Custom tools: yes, via extensions** — `pi.registerTool({...})` with `promptSnippet`/`promptGuidelines`; examples `hello.ts`, `todo.ts`, `question.ts`, `dynamic-tools.ts`.

## 7. Modes + CLI

Invocation: `pi [options] [--] [@files...] [messages...]` (plus subcommands `install|remove|uninstall|update|list|config|auth|mcp`).

- **`-p` / `--print`:** "Run the supplied prompts, write the final assistant text to stdout, then exit." Examples: `pi --print "Summarize this repository"`, `git diff | pi --print "Review this change"`.
- **`--mode json`:** one-shot, writes **JSONL events** to stdout (docs/json.md). `--mode text` selects text output but does **not** force one-shot when stdin/stdout are terminals — use `--print` for that. If stdin **or** stdout is redirected and no mode chosen → print mode automatically.
- **RPC mode (brief):** long-lived child process, strict JSONL on stdin/stdout. `pi --mode rpc --no-session`; rejects `@file` args. TS clients use exported `RpcClient`.
- **SDK (brief):** embeds Pi in-process (Node/Bun): `createAgentSession()` → `session.prompt()` / `getLastAssistantText()`, `session.systemPrompt`, `SessionManager.inMemory()`, **`cwd` option**.
- **Working directory: there is NO `--cwd`/`-d` flag**; pi uses the process cwd for `@path` resolution, project config, resource discovery, session grouping.
- **Prompt/system flags:** `--system-prompt <text|path>`, `--append-system-prompt <text|path>` (repeatable). **Resource flags:** `-e/--extension <path>` (repeatable), `-ne`, `--no-mcp`, `--skill <path>`, `-ns`, `--prompt-template <path>`, `-np`, `--theme <path>`, `--use-theme`, `--no-themes`, `-nc` (no AGENTS.md/CLAUDE.md). **One-shot:** `-p`. **Trust:** `-a/--approve`, `-na`. **Sessions:** `-c/--continue`, `-r/--resume`, `--session`, `--session-id`, `--fork`, `--session-dir`, `--no-session`, `-n/--name`. **Misc:** `--offline`, `--verbose`, `--tui-mode`, `--export <file> [out]`, `--list-models`, `-h`, `-v`.

## 8. Loading custom content for one run

- **Per-run flags (process-only, not persisted):** `--extension`, `--skill`, `--prompt-template`, `--theme` (all repeatable; relative paths resolve from cwd); pair with `-ne/-ns/-np` to suppress all discovery. System prompt for one run: `--system-prompt` / `--append-system-prompt`.
- **Invoking a specific template/skill in a one-shot run:** pass `/my-template args` or `/skill:name args` as the **message**; `session.prompt()` defaults to `expandPromptTemplates: true` — 1.5.2 `dist/core/agent-session.js:1700-1747`, print mode calls exactly `session.prompt(...)` (`dist/modes/print-mode.js:112,115`). **Code-verified only — docs never explicitly state template expansion in print mode (UNVERIFIED in docs).**
- **Project-local discovery:** `.pi/{settings.json,SYSTEM.md,extensions,skills,prompts,themes,mcp.json}` — in print/JSON/RPC modes the trust prompt cannot appear, so these load **only** if a saved `trust.json` decision exists, `defaultProjectTrust: "always"`, or you pass **`-a/--approve`**; otherwise they are skipped (docs/security.md). Context files (`AGENTS.md`, `CLAUDE.md`) load regardless of trust unless `-nc`.
- **Package install:** `pi install … [-l]` is persistent (writes settings.json) — wrong tool for a single run; use explicit path flags instead.
- **"Don't touch ~/.pi" isolated mode: none exists** — no `--isolated`/`--no-config` flag in 1.5.2 `--help`. Closest recipe: `PI_CODING_AGENT_DIR=/tmp/… pi-agent PI_CODING_AGENT_SESSION_DIR=/tmp/…sessions pi -p --no-session -na -ne --offline …` plus containerization.

---

### Docs vs README / premise disagreements
1. Task premise package name `@mariozechner/pi-coding-agent` is **stale**; current is `@earendil-works/pi-coding-agent@1.5.2`. Repo `badlogic/pi-mono` → `earendil-works/pi`.
2. Old README (tag `v0.66.1`, legacy npm package) shows template syntax `{{focus}}` and package roots `~/.pi/agent/git/` + global npm; current docs/code use `${1:-…}`/`$ARGUMENTS` and managed roots. HEAD README and docs agree.
3. HEAD README and `docs/cli.md` agree on modes/permissions/sub-agent stance.

### UNVERIFIED
- `https://pi.dev/install.sh` — fetch rejected, installer internals evidenced by local `managed-install.json` + code only.
- `/name` template expansion in `-p`: code-verified only, not docs-stated (live smoke will verify).
- Not exhaustively diffed: every 1.5.2 doc vs HEAD doc.
- Full RPC command set / SDK surface: kept brief per scope.

### Primary sources
- Repo/README: https://github.com/earendil-works/pi (HEAD `a40abec`, 2026-11-12)
- Docs: packages/coding-agent/docs/{configuration,settings,cli,prompt-templates,skills,extensions,packages,models,providers,security,environment-variables,rpc,sdk,cli-integration,containerization}.md
- Code: model-resolver.ts (default xai = `grok-4.7`); 1.5.2 dist/{core/*,modes/print-mode.js,cli/args.js,config.js}
- npm: @earendil-works/pi-coding-agent (1.5.2), @mariozechner/pi-coding-agent (0.73.1 legacy)
- Local evidence: `~/.pi/agent/{settings.json,models-store.json,auth.json,sessions/,bin/,install/}` (auth.json contents not read)
