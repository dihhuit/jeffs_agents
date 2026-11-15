# MDU-69 — Reasoning watchdog

## Problem
Four CS-2 grok-test-agent spawns (01a1dcf2, 01a1dcf7, 01a1dcfd, 01a1df47) stayed in streaming_reasoning for about 345 seconds. Thoughts were 38k–49k unique characters. toolCallCount was 0 on the last three. The parent cancelled each turn with mid_turn_abort because no test file existed. The fourth thought ended with "The code is now considered ready." signals.json recorded no assistant message because the turn was cancelled first.

## Decision
One new bullet, Grok orchestrator mirrors only. prompts/orchestrator.md stays unchanged. Do not hand-edit build/. build.sh regenerates build/.

Insert the bullet as the next list item after the existing Subagent Watchdog bullet, before the Session Checkpoint bullet, in both of these files:
- grok/agents/orchestrator.md (this repo)
- ../opencode_agents/grok/agents/grokestrator.md (overlay repo, branch mdu-69-reasoning-watchdog)

## Exact clause

```
- On Grok, a child in `streaming_reasoning` with a growing thought is working, even when `toolCallCount` is 0 and the assigned file does not exist yet. Do not cancel it at the five-minute check. Cancel when phase events go idle, or when it is calling tools and still has not written the assigned file.
```

## Out of scope
- prompts/orchestrator.md
- Retargeting the grok-build-0.1 pin. That id is absent from the 2026-11-15 model catalog. Live models still default reasoning_effort to high.
- concept-sheet/agent-improvements.md suggestion 20261115-2. That file is on another remote. Do not edit it.

## Acceptance
- The exact clause line appears once in each of the two source files above.
- prompts/orchestrator.md does not contain streaming_reasoning.
- FEATURE_BACKLOG.md gains a MDU-69 entry whose Status line uses the word Done.
- A pin test fails if the clause line is removed from a copy of grok/agents/orchestrator.md.
- An overlay pin test fails if the clause line is removed from a copy of grok/agents/grokestrator.md.

## Tests
- tests/test_mdu_69_reasoning_watchdog.py in this repo.
- ../opencode_agents/tests/test_mdu_69_overlay.py in the overlay repo.

Do not implement those tests. Do not edit the agent files. Reply with the path you wrote and stop.
