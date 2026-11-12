---
type: session
created: 2026-11-12T01:39:47Z
updated: 2026-11-12T03:45:00Z
---

# Session ses_e3298eb27ffe26mrOwhldIcreM — 2026-11-12

## 2026-11-12T01:39:47Z — session-start
- Resumed from MDU-58's resume block; MDU-56 (pi harness research + port) is queue head. User answered batched questions: D-U1 port lives in the base repo (generic); D-U2 install into ~/.pi/agent pre-approved once artifacts exist; suburb_sim session id for MDU-59 supplied: ses_e378d7aa2ffeFWkHd8BXgC7aqb.

## 2026-11-12T03:45:00Z — mdu-complete (mdu-56)
- mdu_id: mdu-56
- branch: main
- commit: 2a62a0c
- summary: Ported the 20 grok profiles to pi as a generated template package (build/pi: 20 role prompts + /roster; byte-verbatim bodies + hand-authored adapter preamble that wins conflicts); generator scripts/lib/gen_pi_templates.py hooked into ./build.sh after Claude generation; Gates A–E pinned (33 cases, suite 905); parity docs/pi-parity.md (30 rows); live smoke 8/8 PASS on xai/grok-4.7 (referenced install — re-run pi install after rebuild).
- key_decisions: D1 template package over skills/subagent-extension/--system-prompt; D2 preamble-wins over prose edits (deterministic, drift-proof); D3 generator over static (golden-gated); D5 smoke: phase-1 isolated (copied agent dir minus sessions; /name expansion in pi -p is docs-UNVERIFIED but proven LIVE), phase-2 real install; deploy/smoke phase ran in the orchestrator session per the 20261021-9 phase-routing pre-check (children denied external ~/.pi access).
- manifest: runs/mdu-56/manifest.json
