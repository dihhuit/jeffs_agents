---
name: fallback-ladder
description: walk the paid-spawn fallback ladder's six decision cases offline and check every mirror carries the governing sentence
trigger: manual
timeout_minutes: 5
expect:
  - "PASS fallback-ladder"
---

# fallback-ladder

## Goal

Demonstrate the MDU-41 paid-spawn fallback ladder — one retry, one rotation,
then stop; `xai/*` gets no ladder — as an executable, deterministic decision
path, and prove the governing sentence for every case is present in every
reachable orchestrator mirror.

This task is a **scripted dry run**, not a live cap-error spawn. No free caps
remain to die (MDU-40 deleted every free-tier variant), and forcing a real
cap/credit error on a paid account is not something anyone should script. The
ladder's correctness here is decision-path correctness plus mirror parity.

Trigger is `manual`: it needs no network and no deployed agents, so it is safe
to run any time the prompt text changes.

## What it checks

Six scripted cases, each mapped to the sentence of the ladder block that
governs it:

| Case | Scripted event | Mandated action |
| --- | --- | --- |
| 1 | `opencode-go/deepseek-v4.1-flash` spawn reports `provider.quota` | one retry, same model |
| 2 | the retry fails identically | one rotation to a live-list model, not the original |
| 3 | the rotated spawn fails | stop; escalate with both errors and both model ids |
| 4 | a second rotation is contemplated | forbidden; never a second silent rotation |
| 5 | `xai/grok-4.7` spawn reports credit/auth error | no ladder; escalate directly |
| 6 | any spawn failure | never substitute a free model |

Mirrors walked:

- `prompts/orchestrator.md` and `grok/agents/orchestrator.md` — always.
- `../opencode_agents/grok/agents/grokestrator.md` — only when the sibling
  checkout exists, so the public base repo stays self-contained (same optional
  pattern as the MDU-34 resume-block test).

The driver is read-only: it greps the mirrors and writes nothing except a
temporary path list under the OS temp dir, removed on exit.

## Running it

```bash
timeout 60 sh evals/tasks/05-fallback-ladder/driver.sh
```

## Reading the output

One line per case:

```
[case 1] opencode-go/deepseek-v4.1-flash spawn reports provider.quota -> one retry, same model [policy sentence found in 3/3 mirrors]
```

- `k/k mirrors` — the governing sentence was found in every reachable mirror.
  A shortfall prints `[warn] case n: governing sentence missing in: <paths>`
  and names the expected sentence (the missing-sentence report is deliberately
  mechanical — the fix is to re-sync the mirror, not to reword the sentence).
- Final line `PASS fallback-ladder` / `FAIL fallback-ladder`.

Exit codes: `0` — every case resolved and every governing sentence is present
in every reachable mirror. `1` — at least one mirror is missing a sentence, or
no mirror was reachable. The driver takes no arguments.

## Why the sentences are byte-pinned

The block is byte-identical in all three mirrors by design (MDU-41 D3): the
policy is short enough to pin exactly, and past drift came from per-mirror
rewording. When a rotation target changes, update all three mirrors, this
document's sibling `docs/fallback-ladder.md`, and the parity tests in the same
commit — see the maintenance procedure there.

## Non-goals

- No model calls, no live spawns, no network, no account interaction.
- Not wired into `build.sh`, `deploy.sh`, or the validator: it is a
  demonstration artifact under `evals/tasks/`, invoked read-only by the suite.
- Not a semantic proof of the policy — it pins wording and presence. Semantic
  fidelity is a human review check (MDU-41 D10.1).
