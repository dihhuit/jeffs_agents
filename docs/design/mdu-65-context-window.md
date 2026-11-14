# MDU-65 — Grok CLI context window

## Question

The Grok CLI context meter shows about 50k of 256k. Grokestrator and the Grok orchestrator are supposed to be Grok 4.7, and an older design note calls that model a 500k window. This MDU checks which model id those agents resolve to, and whether 256k is the model window or a CLI display cap. It does not edit agent definitions.

## Resolution

The model id is already grok-4.7. 256k is the catalog default context window for that id. The meter denominator is that selected window, the same number auto-compact uses. It is not a display cap. 500k is a second size the same model offers. Nothing in the agent definition selects it. No follow-up MDU is added, because the model id is already correct and the definition cannot set the window.

## Evidence

Checked 2026-11-14. Grok CLI catalog version 1.0.77, fetched the same day from the CLI models endpoint.

### Model id

- User Grok config sets the active agent name to grokestrator. That file's frontmatter is `model: grok-4.7`.
- Installed copy of the base orchestrator profile: `model: grok-4.7`.
- Base source `grok/agents/orchestrator.md`: `model: grok-4.7`.
- Overlay source `grok/agents/grokestrator.md`: `model: grok-4.7`.
- Installed copies are longer than those sources because deploy appends global snippets. The model line matches in each pair.
- Overlay OpenCode registry entry for grokestrator: `xai/grok-4.7`.
- Base OpenCode registry entry for orchestrator: `opencode-go/glm-5.3-flash`. That is the OpenCode harness agent. It is not the process that draws the Grok CLI meter.
- `GROK_MODEL_ALLOWLIST` in `scripts/lib/validate.py` includes `grok-4.7`.
- This session's signal file records `primaryModelId` grok-4.7 and `contextWindowTokens` 256000.

### Window

Catalog row for grok-4.7:

- `context_window` is 256000 (the default).
- `context_windows` lists 256000 and 500000.
- The same pair is listed for grok-4.7-build-fast, grok-4.6, and grok-4.5.
- grok-build-0.1 is not in this CLI catalog.

The slash-command guide says `/context-window` is offered only when the model has more than one size, and the choice is the window used for auto-compact. The status-line guide names `context_window_size` as the maximum context size. The headless-mode guide says `contextWindow` is the current model's real total context window, the same value used for auto-compaction.

The user config has no model table and no `context_window` override, so the catalog default of 256000 applies.

Agent frontmatter `model` is a string id. The agent-mode guide does not give that file a context-window field. Changing the model id would not switch the default from 256k to 500k.

A 500000 value in one session resource file is the WebFetch tool parameter `context_window_tokens`. It is not the chat window.

### Stale sentence

`docs/design/mdu-23-session-hygiene.md` says grok-4.7 is 500k. That names the larger offered size, or an older default. The live catalog default on this date is 256000. This MDU does not rewrite that historical note.

## Outcome

Record the config as correct and stop. Picking 500k is the session command `/context-window 500k`, or a user-config `context_window` on the grok-4.7 model table. Neither is an agent-definition edit, and neither is queued.

## Non-changes

No edits under `prompts/`, `grok/agents/`, `opencode.json`, or the overlay repo.
