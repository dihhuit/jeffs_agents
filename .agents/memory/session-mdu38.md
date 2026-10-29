---
type: session
created: 2026-10-29T09:00:00Z
updated: 2026-10-29T10:30:00Z
---

## 2026-10-29T10:30:00Z — mdu-complete (mdu-38-model-health-probe)
- mdu_id: mdu-38-model-health-probe
- branch: main (base + overlay)
- commit: 3ae713a (open-agent-definitions), 411c5b6 (opencode_agents)
- summary: Pre-spawn model-health probe landed end-to-end: probe_models.py (--refresh/--gate) with exact-match OK liveness check, warn-only base deploy / hard overlay deploy gate, docs + mdu-37 stale-row corrections, 533 base tests green, live probe 7/7 ok on both repos, live overlay --force deploy green.
- key_decisions: warn-only base gate (public-repo portability) vs hard overlay gate (daily machine); report-last-wins refresh; canonical JSON hash so overlay re-emits stay fresh; CI deliberately stays CLI-free.
- manifest: open-agent-definitions/runs/mdu-38-model-health-probe/manifest.json (runs/ gitignored — local-only)
