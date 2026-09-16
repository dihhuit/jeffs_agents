---
name: registry-alignment
description: verify every agent model ref in opencode.json resolves against the committed model registry
trigger: ci
timeout_minutes: 2
expect:
  - "model registry check green"
---

# registry-alignment

## Goal

Verify that every model reference declared by an agent in `opencode.json`
resolves to a known entry in the committed model-registry snapshot
(`config/model-registry.txt`). This catches silent breakage when a model ID is
renamed upstream or when a new agent is wired to a model the registry doesn't
yet list.

The check is deterministic and costs no LLM tokens — it invokes
`scripts/lib/model_registry.py --check opencode.json`, which exits non-zero
when any reference is missing from the snapshot.

## Acceptance criteria

- `python3 scripts/lib/model_registry.py --check opencode.json` exits 0.
- The driver echoes a `PASS` line and a final `PASS registry-alignment` line
  on success.
- Any non-zero exit (missing model, drift, parse error) echoes a `FAIL` line
  and the driver exits non-zero, gating the CI job.