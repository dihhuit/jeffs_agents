# Autonomy Ladder & Approval Gates

This document defines the autonomy-level ladder this agent team operates on,
where the team sits on it today, and the explicit human-approval gates that
govern risky operations. It is the canonical reference for the run ledger's
`autonomy_level` field (see `docs/observability.md` and
`scripts/lib/run_ledger.py`) and for the orchestrator's **Human Approval
Gates** guardrail (see `prompts/orchestrator.md` and
`grok/agents/orchestrator.md`).

## The Autonomy Ladder

The industry-standard autonomy ladder, from least to most autonomous:

| Level | Name | Definition |
|-------|------|------------|
| L0 | Tool-assisted | The human drives every step; the agent only executes individual tool calls on request. |
| L1 | Task-autonomous | The agent completes a single well-scoped task end-to-end without step-by-step human direction. |
| L2 | Session-autonomous | The agent works through multi-step sessions autonomously, with human checkpoints at defined boundaries. |
| L3 | Goal-directed with approval gates | The agent pursues a goal across many steps and sessions, pausing only for human approval at defined risky operations. |
| L4 | Fully autonomous multi-agent pipeline | Multiple agents coordinate end-to-end with no human in the loop; humans only review outcomes. |

## Where the Team Sits

**Current position: L2 (session-autonomous).** The orchestrator decomposes work
into MDUs and drives the full design → implement → review → test → deploy →
validate loop across sessions, with human checkpoints at the start of each MDU
and on escalation. The run ledger records an `autonomy_level` (integer 0–4)
per MDU in `runs/<mdu-id>/manifest.json`, so each unit's autonomy is tracked
and auditable.

**Target: L3 (goal-directed with approval gates).** The team is deliberately
not pursuing L4. L3 keeps a human in the loop at the four approval gates below
while letting everything else flow autonomously.

## Level-by-Level Assessment

- **L0 (tool-assisted):** Fully supported — every agent executes tool calls
  only within an interactive session. Nothing here blocks higher levels.
  *To unlock L1:* already unlocked; no additional definitions required.
- **L1 (task-autonomous):** Fully supported — subagents (just-code,
  test-agent, code-reviewer, devops, qa) each complete a single scoped task
  end-to-end with sign-off. *To unlock L2:* already unlocked; no additional
  definitions required.
- **L2 (session-autonomous):** Supported today — the orchestrator runs
  multi-step MDU loops with human checkpoints (MDU kickoff, escalation on
  repeated failure). *To unlock L3:* formalize the approval gates (done in
  this document and the orchestrator prompt) and enforce them in the
  orchestrator's decision loop.
- **L3 (goal-directed with approval gates):** The target. Requires the four
  approval gates below to be enforced by the orchestrator before risky
  operations, plus the run ledger recording `autonomy_level` per MDU.
  *To unlock L4:* remove the human from the loop entirely — not planned.
- **L4 (fully autonomous multi-agent pipeline):** Not targeted. Would require
  automated approval of protected-branch pushes, production deploys, and
  destructive operations, which this team deliberately keeps human-gated.

## The Four Approval Gates

The orchestrator must require human approval before:

1. **Pushing to protected branches** (e.g. `main`, release branches).
2. **Deploying non-green MDUs to production** — an MDU whose build, tests,
   or QA are not fully green must not reach production without approval.
3. **Performing destructive operations** — deletes, database migrations, and
   other irreversible operations.
4. **Exceeding 3 fix-retries on the same issue** — the existing retry cap,
   now formalized as an approval gate: after 3 failed attempts on the same
   issue, stop and get human approval (or explicit direction) before
   continuing.

These gates are mirrored verbatim in the orchestrator's **Safety Guardrails**
section (`prompts/orchestrator.md` / `grok/agents/orchestrator.md`) so the
documentation and the agent behavior stay consistent.

## Why Gates, Not Approval-Everything

The point of approval gates is to make humans **gatekeepers at defined points
of risk**, not reviewers of every action. Everything that is reversible,
low-risk, or routine flows autonomously — implementation, testing, review,
deploys to non-production environments, and normal commits. Only operations
that are hard to undo (protected-branch pushes, production deploys of
non-green MDUs, destructive operations) or that indicate a loop is not
converging (exceeding the fix-retry cap) pause for human judgment. This keeps
throughput high while ensuring a human owns every irreversible decision.

As of the 2026 enterprise reference point, **L3 (goal-directed with approval
gates) is the enterprise ceiling** — organizations standardize on keeping a
human accountable for risky operations rather than granting full autonomy.
This team's L2-today / L3-target position aligns with that industry norm.