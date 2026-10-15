---
name: webapp-verification
description: Playwright recipe for verifying web deliverables, with BLOCKED reporting when Playwright is unavailable. Load when QA-grading a web UI to run navigate, snapshot, interact, console/network, and screenshot checks without silently skipping coverage.
license: Unlicense
metadata:
  audience: [qa]
---

# Webapp Verification

Verify the delivered functionality with browser automation, then back it with non-browser checks. Never silently skip browser validation for a web UI, and never give a PASS that implies browser coverage you could not perform.

## Tool

**Playwright MCP** (server name typically `playwright`, package `@playwright/mcp`). Use it for navigation, snapshots, screenshots, console/network inspection, and testing tools when exposed.

## Browser recipe

1. **Navigate** — load the target URL; wait for the page to settle.
2. **Snapshot** — capture the accessibility snapshot; verify the expected UI structure and content is present.
3. **Interact** — exercise the critical flows (forms, buttons, navigation); verify state changes and results.
4. **Console/network** — inspect console messages (errors/warnings) and network requests (failed, 4xx/5xx, unexpected calls).
5. **Screenshot** — capture evidence of the verified states.

## BLOCKED reporting

If Playwright MCP is not available, or it fails when you try to use it:

- Do NOT silently skip; do NOT give a PASS that implies browser coverage.
- Report a **BLOCKED** status (distinct from PASS/FAIL) including:
  - Which tools you looked for (Playwright MCP).
  - What failed (not in tool list / connection error / runtime error — include the error text).
  - That Playwright MCP needs configuring on the harness (OpenCode, Grok Build, or Claude Code).
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