---
type: session
created: 2026-11-12T14:45:00Z
updated: 2026-11-12T14:45:00Z
---

## 2026-11-12T13:00:00Z — session-start (ses_e3025295affeayYpYS7e8lKm1w)
- mdu_id: mdu-61
- note: resumed from the mdu-60 resume block; MDU-61 queue head; Diff A (config) + Diff B (clause) user rulings collected at dispatch time via batched question tool

## 2026-11-12T14:45:00Z — mdu-complete (mdu-61)
- mdu_id: mdu-61
- branch: main (both repos)
- commit: base 00d37ac, overlay 6a06d55 + 4f648f4 (all pushed)
- summary: playwright MCP pinned --browser chromium across OpenCode + Grok + Claude (split-brain found in deploy, fixed fail-closed); blender app-backed MCP gating clause byte-identical in 11 carriers; mdu-48 root causes re-verified with dated probes; QA PASS round 1; base 965 / overlay 286 tests green
- key_decisions: Diff A approved with deploy (per-diff, atomic 3-point sync); Diff B pre-approved in-MDU (mdu-60 carve-out); deploy.sh gains remove-before-add + post-add verify so a half-deploy can never exit 0
- manifest: runs/mdu-61/manifest.json
