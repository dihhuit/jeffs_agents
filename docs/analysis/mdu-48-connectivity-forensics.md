# MDU-48 — Sprite connectivity forensics: findings

Session referenced by id prefix only: `ses_e6d1ac9c…`  
Agent: `qa` (model `mimo-v2.6-flash`).

## 1. Per-symptom root cause

### S1 — `shell` "Permission denied: shell" x3

**Evidence**
- Deployed config `agents.qa` block (`~/.config/opencode/` + `opencode.json`, L1758-2094): broad `shell` with resource `"*"` is `"deny"`; allowlisted forms are `git diff*`, `git log*`, `git show*`, `grep *`, `rg *`, `git status*`, `ls*`, `head*`, `tail*`, `wc*`, `sort*`, `timeout *`, `python3 -m pytest*`, `pytest*`, `./build.sh*`, and `*2>/dev/null*`.
- Session-store query on `session_message` for the stuck session:
  - `data LIKE '%Permission denied: shell%'` → **11 rows**.
  - Tool name extracted from content → `shell`.
- The child was asked to write findings/screenshots, which `qa` is not scoped to do.

**Blame class**  
By-design sandbox + task-paper mismatch (same class as incidents 20261021-9 / 20261021-8): a read-only review/QA child was given execution- or file-writing steps.

### S2 — Playwright "Chromium distribution 'chrome' is not found at /opt/google/chrome/chrome"

**Evidence**
- Reproduced in the orchestrator session via `tools.playwright.browser_navigate` to `about:blank`; same error text.
- Machine browsers: `/snap/bin/chromium`, `/usr/bin/chromium-browser`; no `/opt/google/chrome/chrome`.
- `npx -y @playwright/mcp@latest --help` lists `--browser` possible values: `chrome`, `firefox`, `webkit`, `msedge`.
- Deployed MCP entry (`~/.config/opencode/` + `opencode.json`, L4917-4927) server args: `npx -y @playwright/mcp@latest --caps=devtools,network,testing`.
- Session-store query: `data LIKE '%Chromium distribution%chrome%is not found%'` → **5 rows**, tool name `execute` (MCP bridge call).

**Blame class**  
Machine environment gap (Google Chrome not installed) + channel default (`chrome` is the default channel when `--browser` is omitted).

### S3 — Blender "Could not connect to Blender" despite harness "connected"

**Evidence**
- Reproduced in the orchestrator session via `tools.blender.get_addon_status`; error: "Could not connect to Blender. Make sure the Blender addon is running."
- `pgrep -x blender` → 0 (no Blender app); `pgrep -fc blender` → 26 but ALL are idle `uvx mcp-for-blender` launcher pairs (13 uvx + 13 python), zero blender app processes; launcher accumulation is itself a leak finding.
- Deployed MCP entry (`~/.config/opencode/` + `opencode.json`, L4929-4935): local server `uvx mcp-for-blender`, `disabled: false`.
- Session-store query: `data LIKE '%Could not connect to Blender%addon is running%'` → **2 rows**, tool name `execute`.
- Session-store query `data LIKE '%mcp%' AND data LIKE '%connected%'` → **6 rows**. These are agent-reasoning rows, not harness logs. One row records the agent recalling that the user said both MCPs are "connected" per OpenCode. The store therefore does **not** contain a harness-level "MCP connected" assertion; the claim is a user assertion recalled by the agent.

**Blame class**  
Launcher-vs-addon status semantics: the harness "connected" status refers to the `uvx mcp-for-blender` launcher process, not the Blender addon socket. Expected behavior of `mcp-for-blender`; Harness reporting is process-level.

**Launcher accumulation (new finding)**  
Per-session spawned `uvx` launchers are not reaped after the session closes. At forensics time on this machine, 13 `uvx` + 13 `python` pairs (26 processes) were alive and idle with no Blender app running — none of them can serve a session. This is a process leak independent of the connectivity symptom: the launcher count is a proxy for sessions that opened Blender MCP and never cleaned up.

## 2. Recommended fixes

No config edits are made in this forensics phase. Diffs below are proposals only.

### S1 — Route write/exec steps away from `qa`; pre-scope denials in child briefs

- The orchestrator should assign file-writing, screenshot-saving, and execution steps to an agent with `shell`/`edit` allow (e.g., `just-code`, `devops`, or a dedicated executor).
- The child brief should state up-front when shell is expected, so a read-only agent does not burn steps retrying.
- The MDU-47 clause now shipping (`docs/design/mdu-47-definition-guards-batch.md` D1d) instructs `qa` that, if `shell` is denied, it may make exactly one `timeout <n> <command>` retry and otherwise must fall back to file tools plus orchestrator-attached outputs, labelling checks "verified via orchestrator-attached output". That clause must land in `opencode_agents/overlays/prompts/qa.md` for OpenCode/Claude coverage because the overlay full-file replacement wins over the base prompt.

### S2 — Pick one Chrome/Playwright fix

Both options target `opencode_agents/overlays/opencode-mcp.json`.

#### Option S2a — install Google Chrome stable

No config edit needed — one-time `npx playwright install chrome` (system Google Chrome install; this is the remediation the playwright error itself prints). Keep the server args unchanged.

**Why:** Matches the error message verbatim; no config change.

#### Option S2b — switch to bundled Chromium

```diff
--- a/opencode_agents/overlays/opencode-mcp.json
+++ b/opencode_agents/overlays/opencode-mcp.json
@@ -7,7 +7,8 @@
           "npx",
           "-y",
           "@playwright/mcp@latest",
-          "--caps=devtools,network,testing"
+          "--caps=devtools,network,testing",
+          "--browser", "chromium"
         ],
         "disabled": false
       },
```

Plus a one-time `npx playwright install chromium` on the machine so the bundled browser is available.

**Why:** No system browser install; works with the Playwright-bundled Chromium. Snap Chromium is known-fragile under Playwright (confinement) and is NOT recommended as an executable-path target.

**Recommendation**  
Recommend **S2b** (bundled Chromium with explicit `--browser chromium`). It removes the external Chrome dependency, avoids Snap confinement issues, and makes the environment reproducible across machines.

### S3 — Blender pre-flight addon probe

- Before designating Blender-dependent verify steps, ensure Blender is running with the `mcp-for-blender` addon enabled.
- Treat any "connected" claim as launcher-level (process running), not addon-socket-level.
- Add a pre-token addon probe to the MDU brief: invoke `tools.blender.get_addon_status`. If it returns the addon-error, stop and route the Blender step to a machine where Blender is open, or attach the expected outputs from the orchestrator.
- Cleanup on session teardown: reap idle `uvx mcp-for-blender` launcher pairs when a session closes, so they do not accumulate (13 stale pairs observed).
- Add a leak-count probe: report `pgrep -fc mcp-for-blender` alongside the app check, so launcher accumulation is visible before it reaches dozens of idle processes.

## 3. Evidence appendix

Reproduced errors and environment checks gathered by the orchestrator session (not re-run here):

- Blender MCP error (from `tools.blender.get_addon_status`):  
  `Could not connect to Blender. Make sure the Blender addon is running.`
- Playwright MCP error (from `tools.playwright.browser_navigate about:blank`):  
  `Chromium distribution 'chrome' is not found at /opt/google/chrome/chrome / Run npx playwright install chrome`
- `pgrep -x blender` → 0 (no Blender app); `pgrep -fc blender` → 26 but ALL are idle `uvx mcp-for-blender` launcher pairs (13 uvx + 13 python), zero blender app processes; launcher accumulation is itself a leak finding.
- Browsers present on machine: `/snap/bin/chromium`, `/usr/bin/chromium-browser`.
- Browser not present: `/opt/google/chrome/chrome`.
- `npx -y @playwright/mcp@latest --help` `--browser` possible values: `chrome`, `firefox`, `webkit`, `msedge`.
- Config refs (split to avoid long lexemes):
  - Deployed: `~/.config/opencode/` + `opencode.json`, `agents.qa` L1758-2094.
  - Deployed MCP: `~/.config/opencode/` + `opencode.json`, `mcp.servers` L4917-4935.
  - Overlay source: `opencode_agents/` + `overlays/opencode-mcp.json`.
  - Base source for `qa` registry: `open-agent-definitions/` + `opencode.json`, `agents.qa` L1758-2094.

Session-store counts for the stuck session (`ses_e6d1ac9c…`):

| Pattern | Rows | Tool name |
| --- | --- | --- |
| `%Permission denied: shell%` | 11 | `shell` |
| `%Chromium distribution%chrome%is not found%` | 5 | `execute` |
| `%Could not connect to Blender%addon is running%` | 2 | `execute` |
| `%mcp%connected%` | 6 | `execute` / `question` (agent reasoning, not harness log) |
