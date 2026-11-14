# MDU-66 — Grokestrator context window

Files surveyed: none. Evidence is the 2026-11-14 probe brief (CLI 1.0.77). No agent file, user config, overlay, or binary was opened.

## Question

Can the Grokestrator agent file raise grok-4.7 above the catalog default of 256000 without a model-wide user-config change?

## Resolution

Stop. Do not ship a carrier. Acceptance criterion 4: if the only honored knob is model-wide, stop and report. Do not apply it.

No agent edit. No deploy. No model-wide table.

## Evidence

Agent profile frontmatter fields the CLI parses, from the AgentDefinition field list: promptMode, capabilityMode, permissionMode, skills, discoverSkills, inheritSkills, injectDefaultTools, tools, disallowedTools, effort, isolation, color, initialPrompt, mcpServers, mcpInheritance, hooks, memory, model, completionRequirement, toolOverrides, userMessageTemplate. There is no context-window field.

Probe A. An agent file with model grok-4.7 plus an unknown frontmatter key loaded and ran. Unknown keys are ignored, not rejected. Session 01a1da90-3355-7883-a886-b87304d7f119 signal: primaryModelId grok-4.7, contextWindowTokens 256000.

Probe B. The same shape with frontmatter context_window set to 500000. The file loaded. Session 01a1da90-b28a-7142-9a22-d1d456c12c69 signal: primaryModelId grok-4.7, contextWindowTokens 256000. The key is ignored. A dead key. Do not ship it.

Probe C. These model strings are rejected locally as an unknown model id, before a session: "grok-4.7 999k", "grok-4.7[context_window=500000]", "grok-4.7[window=500k]", "grok-4.7@500k", "grok-4.7:500000", "grok-4.7/500k". The model id cannot carry the window. The id stays grok-4.7.

Probe D. A YAML model object (id plus context_window) fails parse at line 5 column 3. No session.

Catalog fact from MDU-65, unchanged: grok-4.7 default context_window is 256000, and context_windows also lists 500000.

Session command /context-window lasts for that session only. It is not stored in the agent file. A new Grokestrator session does not inherit it from grok/agents/grokestrator.md.

OpenCode registry entry for grokestrator is the string model id xai/grok-4.7. That entry has no window field. Leave it.

## Honored knobs

Documented honored knob: a quoted model table in the user config, key context_window, on the grok-4.7 id. That table is model-wide. It would move every grok-4.7 agent off the catalog default 256000. Out of scope. Not applied.

The session command /context-window is honored for that session only. It is not an agent-file carrier and is not stored.

## Non-changes

- Overlay grok/agents/grokestrator.md untouched.
- Base grok/agents/orchestrator.md untouched.
- Other grok-4.7 agents untouched.
- User config untouched.
- OpenCode grokestrator model id untouched.

## Pin sentences

Frontmatter context_window is ignored.
Probe contextWindowTokens stayed 256000.
The model id stayed grok-4.7.
The model-wide user-config table was not applied.
No agent definition was edited.

Status: Done — 2026-11-14 (CLI 1.0.77 ignores a frontmatter context_window key. Probe signals stayed at contextWindowTokens 256000 with primaryModelId grok-4.7. The only honored persistent knob is the model-wide user-config table, which was not applied. No agent file edit. No deploy.)
