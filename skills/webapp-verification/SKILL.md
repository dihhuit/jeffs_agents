---
name: webapp-verification
description: Playwright-first recipe for verifying web deliverables — preferred @playwright/mcp, browser-os MCP fallback, and BLOCKED reporting when no browser tooling works. Load when QA-grading a web UI to run navigate, snapshot, interact, console/network, and screenshot checks without silently skipping coverage.
license: Unlicense
metadata:
  audience: [qa]
---

# Webapp Verification

Verify the delivered functionality with browser automation, then back it with non-browser checks. Never silently skip browser validation for a web UI, and never give a PASS that implies browser coverage you could not perform.

## Tool preference order

1. **Playwright MCP** (server name typically `playwright`, package `@playwright/mcp`) — PREFERRED. Use it for navigation, snapshots, screenshots, console/network inspection, and testing tools when exposed.
2. **browser-os MCP** — FALLBACK only if Playwright MCP tools are missing from the tool list, fail to connect, or error on first use.

## Browser recipe

1. **Navigate** — load the target URL; wait for the page to settle.
2. **Snapshot** — capture the accessibility snapshot; verify the expected UI structure and content is present.
3. **Interact** — exercise the critical flows (forms, buttons, navigation); verify state changes and results.
4. **Console/network** — inspect console messages (errors/warnings) and network requests (failed, 4xx/5xx, unexpected calls).
5. **Screenshot** — capture evidence of the verified states.

## BLOCKED reporting

If neither Playwright nor browser-os is available, or both fail when you try to use them:

- Do NOT silently skip; do NOT give a PASS that implies browser coverage.
- Report a **BLOCKED** status (distinct from PASS/FAIL) including:
  - Which tools you looked for (Playwright MCP, then browser-os MCP).
  - What failed (not in tool list / connection error / runtime error — include the error text).
  - That Playwright MCP (preferred) or browser-os MCP needs configuring on the harness (OpenCode, Grok Build, or Claude Code).
- Still run the non-browser checks you can and list what browser coverage was blocked.

## Non-browser checks (always alongside)

- HTTP/API: status codes, response bodies, headers, auth behavior.
- CLI: commands the deliverable exposes; exit codes and output.
- Logs: errors, warnings, stack traces.
- Edge cases: inputs at boundaries, empty states, error paths.

## Grading

- Prioritize critical-path testing over exhaustive edge exploration per pass.
- PASS only if the claimed functionality works and evidence exists.
- FAIL → return a severity-ranked bug report with detailed reproduction steps and a suspected category (functional bug, deployment issue, infra misconfiguration). Do not attempt fixes yourself.