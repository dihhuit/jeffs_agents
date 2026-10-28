---
type: decisions
created: 2026-10-27T13:24:20Z
updated: 2026-10-27T13:24:20Z
---

# Decision log

## 2026-10-27 — Question-tool failures: harness 60-min pending-question hard-kill; agent-definition mitigation (mdu-35)
- Context: sprite_generator sessions showed every question call failing ("Asked N questions" red, no prompt). Evidence (runs/mdu-35-question-tool/evidence.md): 42 sprite question calls = 30 completed / 12 error; 15/18 inline-era error calls machine-wide are unanswered questions killed at 60.0-61.0 min with `Tool execution interrupted` and no requeue; secondary benign mode = 3 schema-shape rejections that self-correct on retry. Agent-definition/config NOT defective (opencode.json allows question for `*`; no timeout knob exists).
- Decision: fix at the layer we own — QUESTION TOOL discipline clause (ask/batch early, post-pause dead-question check, abort → restate questions inline as numbered plain text, dead question = dropped approval gate never consent) landed byte-identical in base `prompts/orchestrator.md`, base `grok/agents/orchestrator.md`, overlay-root `grok/agents/grokestrator.md`, plus two validator fuse tuples and a pinned adjacency test. Upstream bug-report DRAFT kept unfiled (appendix A, do-not-file marker).
- Consequences: deployed live to all three CLIs next session; the 60-min kill itself is OpenCode-native and remains (user accepts it as workable — adapt by answering/re-asking on return; do not treat a killed question as consent). Filing upstream requires an explicit future user instruction.

## 2026-10-27T14:32:09Z — Canonical resume-block emission: fenced-json template, emissions-only strictness (mdu-34)
- Context: resume blocks were emitted in three shapes (JSON/key:value/prose); variance cost the next session lookup time and blocked validation. MDU-34 resume block + design doc D1-D7.
- Decision: one canonical fenced-json block (11 required keys + optional notes) emitted byte-identically in base prompts/orchestrator.md, base grok/agents/orchestrator.md, overlay-root grok/agents/grokestrator.md; validator scripts/lib/resume_block.py (validate subcommand, exit 0/1/2) and docs/resume-block.md as the single documented source; emission-only — the read-permissive recognition clause ("by purpose, not by header or exact phrasing") survives verbatim and the validator's fail message itself states prose/key:value remain valid gate input. No build.sh wiring for the validator (nothing in-tree is a resume block).
- Consequences: next sessions should emit the canonical shape; prose inputs stay accepted with no narrowing; test_mdu_34 (25 cases) + MDU-28 span test enforce three-way parity; seed capture resolved via D5's representative fallback (seed paste arrived canonical-shaped JSON).
