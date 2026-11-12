# pi parity — what does not port to the pi harness

The pi port copies each `grok/agents` profile body **byte-verbatim**; all
adaptation lives in the shared adapter preamble (`pi/adapter-preamble.md`),
which states that it overrides conflicting harness-specific instructions in
the body. This document is the human-curated record of every construct the
generator's audit finds, and how the port resolves it.

Regenerate the audit with:

    python3 scripts/lib/gen_pi_templates.py --audit

Dispositions:

- `reframed-by-preamble` — the body text stays, the preamble redirects it.
- `ports-as-is` — works unchanged on pi.
- `dropped (reason)` — not ported at all.
- `verify-live` — survives as prose but depends on a live pi capability check.

`PARITY.md` inside the generated package is rendered from the same lexicon and
defaults; this file is the authoritative hand-curated version (Gate D).

## Construct notes

- **delegation** — pi has no named-persona registry and no sub-agents. Clause 2
  either performs the phase in-session under the target role's discipline
  (interactive: `/x`) or emits a `/x <brief>` brief for the user.
- **todowrite** — no TodoWrite tool exists. Track work in the response and in
  durable notes; the intent (visible progress) stands.
- **question-tool** — no question tool exists. Ask in plain text, end the turn,
  and never invent the user's answer.
- **mcp-playwright** — MCP is opt-in through `mcp.json` and nothing is
  configured by default. qa, qa-pro, devops, and devops-pro keep their own
  BLOCKED-or-PASS discipline; a missing server can never become a silent PASS.
- **mcp-blender** — an overlay-only personal server. The base profile clause
  (MDU-61) gates blender-dependent steps on an app probe and is inert wherever
  no blender MCP is registered; the server itself is not ported.
- **opencode-env** — pi has no OpenCode environment variables or session ids.
  Clause 3 drops the mechanics and keeps the checkpoint intent.
- **keybindings-compact** — keybindings, `/compact`, cache-miss and compaction
  gates are harness mechanics. Token frugality, checkpointing, and wrapping up
  at high effort all still stand.
- **shell-allowlist** — pi allowlists select which tools the model may call;
  they are configuration, not an approval gate. The safety gates behind them
  port as-is.
- **model-tables** — tier tables survive as prose, but availability must be
  checked live with `pi --list-models xai`. `grok-4.7` is pi's default
  (`xai/grok-4.7`); `grok-build-0.1` is never a hard dependency.
- **introspector (scope reduction, not a lexicon hit)** — session-tree
  forensics is reduced: pi sessions are JSONL files under the agent dir, so
  session-id-specific clauses are inert under clause 3 while the review and
  `agent-improvements.md` contract is unchanged.
- **Literal step counters** — every profile carries the step-limit safety
  statement. It is harness-agnostic and stands; only literal counter mechanics
  are inert under clause 3.

## Hits (one row per construct × profile)

| Construct | Profile | Disposition |
|---|---|---|
| delegation | architect | reframed-by-preamble |
| delegation | architect-premium | reframed-by-preamble |
| delegation | code-reviewer | reframed-by-preamble |
| delegation | devops | reframed-by-preamble |
| delegation | introspector | reframed-by-preamble |
| delegation | just-code | reframed-by-preamble |
| delegation | just-code-mid | reframed-by-preamble |
| delegation | just-code-pro | reframed-by-preamble |
| delegation | orchestrator | reframed-by-preamble |
| keybindings-compact | introspector | reframed-by-preamble |
| keybindings-compact | just-code | reframed-by-preamble |
| keybindings-compact | just-code-mid | reframed-by-preamble |
| keybindings-compact | just-code-pro | reframed-by-preamble |
| keybindings-compact | orchestrator | reframed-by-preamble |
| mcp-blender | devops | dropped (overlay-only MCP; base clause is inert gating) |
| mcp-blender | devops-pro | dropped (overlay-only MCP; base clause is inert gating) |
| mcp-blender | qa | dropped (overlay-only MCP; base clause is inert gating) |
| mcp-blender | qa-pro | dropped (overlay-only MCP; base clause is inert gating) |
| mcp-playwright | devops | reframed-by-preamble |
| mcp-playwright | devops-pro | reframed-by-preamble |
| mcp-playwright | qa | reframed-by-preamble |
| mcp-playwright | qa-pro | reframed-by-preamble |
| model-tables | architect | verify-live |
| model-tables | introspector | verify-live |
| model-tables | orchestrator | verify-live |
| opencode-env | just-code | reframed-by-preamble |
| opencode-env | just-code-mid | reframed-by-preamble |
| opencode-env | just-code-pro | reframed-by-preamble |
| opencode-env | orchestrator | reframed-by-preamble |
| question-tool | inception | reframed-by-preamble |
| question-tool | orchestrator | reframed-by-preamble |
| shell-allowlist | introspector | reframed-by-preamble |
| shell-allowlist | orchestrator | reframed-by-preamble |
| shell-allowlist | qa | reframed-by-preamble |
| shell-allowlist | qa-pro | reframed-by-preamble |
| todowrite | orchestrator | reframed-by-preamble |

Total: 36 hits across 9 constructs with hits.

## Known limit

The audit is lexicon-driven. A new harness-specific construct that matches no
lexicon term is not auto-detected. The golden-refresh checklist in
`pi/README.md` therefore requires reviewing the regenerated diff and extending
both the lexicon (`pi/port-config.json`) and this file whenever a new
harness-specific line appears.
