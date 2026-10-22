---
name: prompt-golden-cases
description: verify prompt files keep their golden ordered traces and the committed baseline is intact (GOLDEN_ROOT env points the gate at an arbitrary tree)
trigger: manual
timeout_minutes: 2
expect:
  - "prompt_regression.py gate exit 0 on the current tree"
  - "GOLDEN_ROOT override evaluates an arbitrary tree"
---

# prompt-golden-cases

## Goal

Verify that prompt files keep their golden ordered traces and that the
committed baseline is intact. The check is deterministic, free, and offline:
every case scans one target file for an ordered subsequence of stable anchor
markers.

## Acceptance criteria

- The trusted gate script from this repo evaluates the tree under test.
- `GOLDEN_ROOT` (optional) points the gate at an arbitrary tree, e.g. a scratch
copy with a deliberately reordered prompt; default is this repo.
- The driver echoes `PASS prompt-golden-cases` and exits 0 only when the gate
reports all cases passing and the baseline is intact.
- Any gate failure echoes `FAIL prompt-golden-cases` and the driver exits 1.
