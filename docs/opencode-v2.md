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
- Seven agents moved past the original allowlist in MDU-30: **code-reviewer / -pro / -free**, **qa / qa-pro /
  qa-free**, and **introspector**. Their installed order is now `shell * deny` → expanded read-only allows
  (`git status*`, `ls*`, `head*`, `tail*`, `wc*`, `sort*`, `timeout *`; qa also `python3 -m pytest*`,
  `pytest*`, `./build.sh*`; introspector keeps `python3 *` / `python *` and adds only the read-only set) →
  the 40-entry deny wall (39 denies + one allow). The wall runs: substitution denies → **spaced and
  unspaced** redirect denies (`*> /*`, `*>/*`, …) → the single in-wall exception `*2>/dev/null*` (allow) →
  destructive and git-mutation classes, ending with `*sort -o*` / `*sort*-o*`. qa/reviewers also carry
  `*python* -c*` immediately after the exception (the 41st shell rule from the wall head).
  All other agents keep the installed order verbatim — do not retro-fit this shape onto them.
  The null-sink exception is order-critical: after the redirect denies (else it is dead), before every
  destructive class and the inline-python guard (else it launders them).
  Known limit, disclosed in MDU-30 (design §5 Hole 8): a `cd … &&` prefix defeats the redirect denies for
  any absolute target (`cd /repo && git log -1 >/tmp/x` is allowed, while the same command without the
  prefix is denied) — harness-level, not fixable by rule order, so do not reorder the wall to chase it.
- The wall sits after every allow on purpose: `timeout *` is a broad allow, so only rules *after* it can
  constrain a segment. Any future broad `token *` allow must be inserted **above** the wall and the wall must stay the
  last shell run in the block. Full rationale, exact snippets, and the red/green probe matrix:
  `docs/design/mdu-30-shell-allowlist.md`.

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
    { "action": "shell",     "resource": "git status*", "effect": "allow" },
    { "action": "shell",     "resource": "ls*",       "effect": "allow" },
    { "action": "shell",     "resource": "head*",     "effect": "allow" },
    { "action": "shell",     "resource": "tail*",     "effect": "allow" },
    { "action": "shell",     "resource": "wc*",       "effect": "allow" },
    { "action": "shell",     "resource": "sort*",     "effect": "allow" },
    { "action": "shell",     "resource": "timeout *", "effect": "allow" },
    { "action": "shell",     "resource": "*$(*",      "effect": "deny"  },
    { "action": "shell",     "resource": "*`*",       "effect": "deny"  },
    { "action": "shell",     "resource": "*> /*",     "effect": "deny"  },
    { "action": "shell",     "resource": "*> ~/*",    "effect": "deny"  },
    { "action": "shell",     "resource": "*> ../*",   "effect": "deny"  },
    { "action": "shell",     "resource": "*>/*",      "effect": "deny"  },
    { "action": "shell",     "resource": "*>~/*",     "effect": "deny"  },
    { "action": "shell",     "resource": "*>../*",    "effect": "deny"  },
    { "action": "shell",     "resource": "*2>/dev/null*", "effect": "allow" },
    { "action": "shell",     "resource": "*python* -c*", "effect": "deny" },
    { "action": "shell",     "resource": "rm *",      "effect": "deny"  },
    { "action": "shell",     "resource": "* rm *",    "effect": "deny"  },
    { "action": "shell",     "resource": "*xargs*",   "effect": "deny"  },
    { "action": "shell",     "resource": "*sudo*",    "effect": "deny"  },
    { "action": "shell",     "resource": "cp *",      "effect": "deny"  },
    { "action": "shell",     "resource": "* cp *",    "effect": "deny"  },
    { "action": "shell",     "resource": "mv *",      "effect": "deny"  },
    { "action": "shell",     "resource": "* mv *",    "effect": "deny"  },
    { "action": "shell",     "resource": "*curl*",    "effect": "deny"  },
    { "action": "shell",     "resource": "*wget*",    "effect": "deny"  },
    { "action": "shell",     "resource": "*sh -c*",   "effect": "deny"  },
    { "action": "shell",     "resource": "* git push*", "effect": "deny" },
    { "action": "shell",     "resource": "* git pull*", "effect": "deny" },
    { "action": "shell",     "resource": "* git reset*", "effect": "deny" },
    { "action": "shell",     "resource": "* git checkout*", "effect": "deny" },
    { "action": "shell",     "resource": "* git restore*", "effect": "deny" },
    { "action": "shell",     "resource": "* git switch*", "effect": "deny" },
    { "action": "shell",     "resource": "* git clean*", "effect": "deny" },
    { "action": "shell",     "resource": "* git stash*", "effect": "deny" },
    { "action": "shell",     "resource": "* git commit*", "effect": "deny" },
    { "action": "shell",     "resource": "* git rebase*", "effect": "deny" },
    { "action": "shell",     "resource": "* git merge*", "effect": "deny" },
    { "action": "shell",     "resource": "* git cherry-pick*", "effect": "deny" },
    { "action": "shell",     "resource": "* git apply*", "effect": "deny" },
    { "action": "shell",     "resource": "* git add*", "effect": "deny" },
    { "action": "shell",     "resource": "* git branch*", "effect": "deny" },
    { "action": "shell",     "resource": "* git tag*", "effect": "deny" },
    { "action": "shell",     "resource": "* git clone*", "effect": "deny" },
    { "action": "shell",     "resource": "* git worktree*", "effect": "deny" },
    { "action": "shell",     "resource": "*sort -o*",  "effect": "deny"  },
    { "action": "shell",     "resource": "*sort*-o*",  "effect": "deny"  },
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
model retarget `minimax-m3` → `mimo-v2.5`. The expanded read-only allows and the deny wall in this
block are the MDU-30 shape (§5); the other six allowlist agents differ only in their allow set. The wall is
40 entries (39 denies + the `*2>/dev/null*` allow); this block also carries `*python* -c*` right after the
exception. A block missing `*>/*` (unspaced) or `*sort*-o*` has drifted from `opencode.json`.

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
