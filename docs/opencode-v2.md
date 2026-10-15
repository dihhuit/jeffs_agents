# MDU-21 — Native OpenCode V2 config (public base)

**Status:** approved contract for `just-code` / `test-agent`. Deliverable: the base repo's OpenCode config
moves from the V1-with-fixes shape to native V2, preserving every verified fix.

**Sources of truth**
- Field names: https://opencode.ai/v2/docs/migrate-v1 and https://opencode.ai/v2/docs/permissions.
- Behavior, ordering, and values: installed `~/.config/opencode/opencode.json`, fixed and verified in
  OpenCode session `ses_ec2e00d02ffeoez60JTsK6eEeG`.
- Do not invent a "cleaner" shape that undoes those fixes. If this doc and the installed file disagree,
  the installed file wins.

## 1. Shape conversion (mechanical, whole file)

`$schema` and `default_agent` stay. Everything else maps:

| V1 (repo today) | V2 (target) |
| --- | --- |
| top-level `permission` object | top-level `permissions` array of `{action, resource, effect}` |
| `permission.external_directory` map | two top-level entries `{"action":"external_directory","resource":"/tmp/**","effect":"allow"}` and `/proc/**` — exact installed form; the `validate.py` scratch check reads this |
| `agent` | `agents` |
| agent `prompt` | agent `system`; value keeps `{file:./prompts/...}` |
| `temperature` | `request.body.temperature` (per agent) |
| `bash` | `shell` |
| `task` | `subagent` |
| `write` + `edit` when equal | one `edit` rule (e.g. `"edit":"deny","write":"deny"` → single `edit * deny`) |
| legacy `tools` boolean map | permissions for the listed keys **only** — never invent denies for unlisted tools |
| MCP (example + docs) | entries under `mcp.servers`; `enabled` → `disabled` (inverted); scalar `timeout` → `timeout.catalog` + `timeout.execution` |

## 2. Custom provider block — must be absent

The converted file must contain **no top-level `provider` or `providers` block**. The installed fix deleted
the `aisdk:@ai-sdk/openai-compatible` override of built-in `opencode-go`/`opencode-zen`; that override made
the gateway reply "OpenCode's free tier can only be used from within OpenCode." Re-adding it is a regression.

## 3. Model retargets

All target IDs already exist in `config/model-registry.txt` — no registry edits needed.

- `opencode-zen/big-pickle` → `opencode/big-pickle` — orchestrator, just-code-free, test-agent-free, code-reviewer-free, devops-free, qa-free
- `opencode-go/deepseek-v4-flash` → `opencode-go/deepseek-v4.1-flash` — just-code, test-agent, inception
- `opencode/ling-3.0-flash-fin-free` → `opencode/mimo-v2.6-flash-free` — research
- `opencode-go/deepseek-v4-pro` → `opencode-go/glm-5.2` — just-code-pro, code-reviewer-pro, architect, devops-pro
- `opencode-go/minimax-m3` → `opencode-go/mimo-v2.5` — test-agent-mid, code-reviewer, devops, qa, ui-ux-designer, introspector

Leave unchanged: architect-premium (already `opencode-go/glm-5.2`), the kimi-k2.7-code agents, qa-pro,
ui-ux-designer-pro, test-agent-pro, just-code-mid, deep-research (`opencode-go/mimo-v2.5`),
deepseek-research (`opencode/nemotron-3-ultra-free`), nemotron-research (`opencode/nemotron-3.5-lightning-free`).

## 4. Shell `ask` on the three free research agents

On **research, deepseek-research, and nemotron-research only**, the shell rule is
`{"action":"shell","resource":"*","effect":"ask"}` — not `deny`. Verified reason: the free-tier gateway
rejects a request whose toolset omits shell entirely; `ask` keeps the tool present and still prompts.
Do **not** touch shell `deny` on deep-research or any other agent.

## 5. Permission ordering — copy the installed order

- Copy installed rule order verbatim; under last-match-wins, order is behavior.
- Do **not** reorder `subagent` rules. Installed order is `subagent allow research` **before**
  `subagent deny *`; last-match means research stays denied — identical net effect to the converted V1
  nested map `{"research":"allow","*":"deny"}`. "Fixing" the order changes semantics.
- Shell exception blocks keep `shell * deny` first, then specific allows in installed order
  (`git diff*`, `git log*`, `git show*`, `grep *`, `rg *`, `npm run dev`, `npx *`, `python3 *`, `python *`).

## 6. Before / after — code-reviewer nested permission

Before (repo, V1):

```json
"code-reviewer": {
  "mode": "subagent",
  "description": "Reviews code using mid-tier Go model. Signs off on changes for quality, security, and maintainability",
  "model": "opencode-go/minimax-m3",
  "temperature": 0.1,
  "color": "#3b82f6",
  "prompt": "{file:./prompts/code-reviewer.md}",
  "permission": {
    "edit": "deny", "write": "deny",
    "bash": { "*": "deny", "git diff*": "allow", "git log*": "allow", "git show*": "allow", "grep *": "allow", "rg *": "allow" },
    "read": "allow", "glob": "allow", "grep": "allow", "list": "allow",
    "webfetch": "deny", "websearch": "deny", "todowrite": "deny",
    "task": { "research": "allow", "*": "deny" }
  }
}
```

After (installed, V2 — this exact order):

```json
"code-reviewer": {
  "mode": "subagent",
  "description": "Reviews code using mid-tier Go model. Signs off on changes for quality, security, and maintainability",
  "model": "opencode-go/mimo-v2.5",
  "color": "#3b82f6",
  "system": "{file:./prompts/code-reviewer.md}",
  "request": { "body": { "temperature": 0.1 } },
  "permissions": [
    { "action": "edit",      "resource": "*",         "effect": "deny"  },
    { "action": "shell",     "resource": "*",         "effect": "deny"  },
    { "action": "shell",     "resource": "git diff*", "effect": "allow" },
    { "action": "shell",     "resource": "git log*",  "effect": "allow" },
    { "action": "shell",     "resource": "git show*", "effect": "allow" },
    { "action": "shell",     "resource": "grep *",    "effect": "allow" },
    { "action": "shell",     "resource": "rg *",      "effect": "allow" },
    { "action": "read",      "resource": "*",         "effect": "allow" },
    { "action": "glob",      "resource": "*",         "effect": "allow" },
    { "action": "grep",      "resource": "*",         "effect": "allow" },
    { "action": "list",      "resource": "*",         "effect": "allow" },
    { "action": "webfetch",  "resource": "*",         "effect": "deny"  },
    { "action": "websearch", "resource": "*",         "effect": "deny"  },
    { "action": "todowrite", "resource": "*",         "effect": "deny"  },
    { "action": "subagent",  "resource": "research",  "effect": "allow" },
    { "action": "subagent",  "resource": "*",         "effect": "deny"  }
  ]
}
```

Visible here: `write`+`edit` → one `edit`; `bash` → `shell` with deny-`*` first; `task` → `subagent` with
`allow research` before `deny *`; `prompt` → `system`; `temperature` → `request.body.temperature`;
model retarget `minimax-m3` → `mimo-v2.5`.

## 7. Files to touch

| File | Change |
| --- | --- |
| `opencode.json` | everything above |
| `schemas/opencode.schema.json` | required top-level `agents`; agent requires `mode`,`description`,`system`; permission items require `action`,`resource`,`effect`; no required `provider` |
| `scripts/lib/validate.py` | scratch check reads the top-level `permissions` array for the two `external_directory` allows; `validate_opencode` reads `agents` + `system` |
| `scripts/lib/model_registry.py` | reads `agents` |
| `scripts/lib/gen_claude_agents.py` | reads `agents`, resolves `system` |
| `tests/test_validate_schema.py`, `test_validate_integration.py`, `test_validate_skills.py`, `test_validate_parity.py`, `test_model_registry.py`, `test_inception_agent.py`, `test_mdu_12_06_contracts.py` | swap v1 fixture keys (`agent`, `prompt`, `permission`, `temperature`, `bash`, `task`, `tools`) for v2; keep behavioral assertions |
| `examples/mcp/opencode.mcp.json.example` + OpenCode section of `docs/mcp.md` | `mcp.servers`, `disabled` (inverse of `enabled`), `timeout.catalog`/`timeout.execution`; stop claiming v1.17 `enabled` + top-level `agent`/`tools` |
| `README.md` | roster model names; the `permission.external_directory` sentence → `permissions`-array phrasing |
| `docs/model-registry.md` | rows for retargeted agents |
| `docs/mdu-20-inception.md` | copy-paste snippet only: v2 shape + `opencode-go/deepseek-v4.1-flash` |
| `prompts/orchestrator.md` **and** `grok/agents/orchestrator.md` | model-selection lines: only the stale names in §3; keep mirrors aligned; do not change the loop |

## 8. Out of scope

- `opencode_agents/` overlay (later MDU).
- Grok profile bodies other than the orchestrator model-name lines.
- `FEATURE_BACKLOG.md` historical text; `SESSION_CHECKPOINT.md`.
- No `xai/` inception. Base inception stays generic: mode `primary`, model `opencode-go/deepseek-v4.1-flash`,
  `system` `{file:./prompts/inception.md}`, shell `deny`, `subagent *` deny, no `tools`, no `xai/`.

## 9. Acceptance

1. `python3 -m pytest tests/ -q` passes.
2. `./build.sh` passes.
3. Built `opencode.json` has no top-level `agent`, `permission`, `provider`, or `providers`.
4. Every `system` file ref resolves.
5. The three free research agents have shell `ask`.
6. Retargeted model IDs match §3 exactly.
7. Prompt bodies other than the orchestrator model-name lines are unchanged.
