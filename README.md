# Open Agent Definitions\n\nGeneric, shareable agent definitions for OpenCode and Grok Build.\n\nSee README for usage.
## Usage

This is the **generic** layer of agent definitions for OpenCode and Grok Build (xAI).

### Deploy (generic)
```bash
./deploy.sh          # dry run
./deploy.sh --force  # deploys to default ~/.config/opencode/ and ~/.grok/ for ubuntu
```

Supports both tools out of the box with distilled, broadly applicable prompts (no personal MDU, browser-os, SAM, pytorch, mobile specifics).

### For developers
- Prompts in `prompts/` are for OpenCode.
- `grok/agents/*.md` for direct use with `grok --agent <name>`.
- `opencode.json` example config (add your providers/MCP as needed).
- Customize by forking or using as base for overlays.

See the personal overlay repo for examples of how to extend with workflow-specific rules (e.g. MDU process, browser MCP).

## Two-layer model
Generic (this repo) + Overlays (personal) -> build/ (combined for your use).

Generic definitions are validated with both grok and opencode.
