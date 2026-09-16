---
name: repo-health
description: verify the repo's own gates pass (build + tests + skills + parity + model registry)
trigger: ci
timeout_minutes: 5
expect:
  - "./build.sh green"
  - "pytest green"
---

# repo-health

## Goal

Verify that the repository's own gates pass: `./build.sh` (staging the agent
definitions into `build/` and validating them — opencode.json schema, prompt
refs, skills, parity, model registry) and the pytest suite under `tests/`.

This is an honest "does the team's repo pass its own gates" self-check: it is
deterministic, CI-able, and costs no LLM tokens.

## Acceptance criteria

- `./build.sh` exits 0 (build + validation green).
- `python3 -m pytest tests/ -q` reports all tests passing.
- The driver echoes a `PASS` line per gate and a final `PASS repo-health`
  line, exiting 0 only when both gates succeed.
- Any gate failure echoes a `FAIL` line and the driver exits non-zero.