# FILING GATED — local draft only, not submitted anywhere

**Status (2026-10-31):** local staging for a possible future OpenCode fork —
"someday, unplanned". Off the critical path. This file is a record, not an
instruction: nothing here is to be submitted as part of any MDU or routine
step. Any upstream submission requires an explicit, per-action instruction
from the user that names both the repository and the action. One approval
never covers a second action.

Extracted from the MDU-35 design appendix (the frozen historical copy); this
standalone version is the maintained one.

## Title

Pending `question` tool call hard-killed at ~60 min with no re-prompt: turn
ends `finish:"error"`, session idle `interrupted`, user must manually retry.

## Minimal repro

1. OpenCode v2.0.31 (Linux): in a long-running turn, emit a `question` tool
   call near the end of the turn.
2. Leave it unanswered for more than 60 minutes (session idle).
3. Observe: tool part becomes `{"type":"aborted","message":"Tool execution
   interrupted"}`, `executed:false`, `state.status:"error"`; assistant message
   `finish:"error"` plus `"Step interrupted"`; `idle` row
   `outcome:"interrupted"` at the same epoch second; the TUI shows a red
   "Asked N questions" line with no visible prompt; no forward progress until
   the user manually messages.

## Observed

15/18 inline-era error question calls across three projects all aborted at
60.0-61.0 min pending. The identical abort also fires on manual interrupt
(0.4 min), so the 60-min timer is the most frequent trigger rather than the
only one. A same-substance retry succeeded in 5.4 min when the user was
present, so the failure is not payload-, model-, or agent-dependent. No
auto-retry or requeue was ever observed.

Evidence (masked pointers only, no session dumps, no raw storage paths):
`runs/mdu-35-question-tool/evidence.md` sections §1.3, §3c, §4a, §4b, §4e
and §5. Session IDs in that file are non-secret per its masking note.

## Expected

A pending question outlives the 60-min window, OR the harness re-prompts or
requeues on abort so the question still reaches the user instead of dying
silently.

## Version

v2.0.31 on disk at report time; failures span 2026-10-15 → 25; historical
versions at the time of each failure are unrecorded (the session store keeps
no version field).

## Evidence

`runs/mdu-35-question-tool/evidence.md` — §1.3 (call inventory), §3c (timer
correlation), §4a / §4b (abort part and message state), §4e (idle row),
§5 (retry success timing).
