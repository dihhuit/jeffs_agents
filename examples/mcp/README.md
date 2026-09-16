# MCP config example

`opencode.mcp.json.example` is an **inert** OpenCode MCP configuration
(playwright + filesystem scoped to `./workspace` + github). The `.example`
suffix keeps OpenCode from auto-loading it, and every server ships
`enabled: false`.

To activate: copy it to project `.mcp.json` (Claude Code reads it natively) or
merge the `mcp`/`tools` blocks into `opencode.json` (OpenCode does not
auto-load `.mcp.json` — see `docs/mcp.md`), then set `enabled: true` and export
`GITHUB_PERSONAL_ACCESS_TOKEN` in your environment. Plain JSON (no comments):
annotations live in the `_notes` key so the file stays `json.load`-able.

Full reference, per-CLI locations, and per-agent scoping: [`docs/mcp.md`](../../docs/mcp.md).