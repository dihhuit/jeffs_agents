# Fallback ladder — the canonical shape

A paid spawn can die for reasons that are nobody's fault: the provider caps a
model, refuses a quota, or the account's credit is spent. The fallback ladder is
the fixed answer to that failure class, and it is deliberately tiny — one retry,
one rotation, then stop. It is carried **verbatim** in the three orchestrator
mirrors (`prompts/orchestrator.md`, `grok/agents/orchestrator.md`, and the
overlay `grokestrator.md`), and introduced by MDU-41.

There is no free budget to police any more: MDU-40 deleted every free-tier
variant from both configs. This document governs **paid-spawn death** on
`opencode-go/*`, and the explicit no-ladder rule for `xai/*`. It supersedes the
old "escalate one rung" wording — a rung escalation
(`just-code` → `just-code-mid`) is now one *instance* of the single allowed
rotation, not a separate mechanism.

## The exact block

Byte-identical in all three mirrors. Do not reword per harness; past drift came
from per-mirror rewording.

```markdown
- **PAID-SPAWN FAILURE LADDER — ONE RETRY, ONE ROTATION, THEN STOP:**
  When a paid `opencode-go/*` spawn dies on a cap/provider error, quota refusal, or credit exhaustion (e.g. a child reporting `provider.quota`, a 429, or a spent-credit refusal):
  1. Retry the same failure once — same model, in the same or a fresh spawn. One retry only; it exists to absorb transient blips.
  2. If the failure repeats, make exactly ONE rotation to a different `opencode-go/*` model from the verified live rotation list: deepseek-v4.1-flash, glm-5.2, glm-5.3, glm-5.3-flash, kimi-k2.7-code, mimo-v2.6-flash, mimo-v2.6-pro. A role-rung escalation (`just-code` → `just-code-mid`) counts as the one rotation. Never rotate to an unverified model, and never substitute a free model — free variants no longer exist; fallback drift must not reintroduce them.
  3. If the rotated spawn also fails, STOP. Escalate to the user with the failure evidence: both error reports and both model ids. Never a second silent rotation.
  This ladder specializes the retry guardrail for this failure class; it never expands the fourth-retry gate.
  `xai/*` (grok-family) spawns get NO ladder: a cap, credit, or auth error there escalates directly to the user with the evidence. The xAI account auto-tops-up, so such errors are auth-shaped — silent self-recovery would mask them.
```

The block is self-contained on purpose — no doc paths, and the rotation list is
inlined. At run time the orchestrator works in the *target* project, where this
document does not exist.

## Decision table

| Failure class | Mandated action |
| --- | --- |
| `opencode-go/*` spawn fails once (cap, provider, quota, credit) | one retry: same model, same or fresh spawn |
| the retry fails identically | exactly one rotation to a different live `opencode-go/*` model; a role-rung escalation counts as it |
| the rotated spawn also fails | STOP; escalate with both error reports and both model ids |
| any `xai/*` (grok-family) failure | no ladder; escalate directly with the evidence |

Design rationale for the shape: one retry absorbs the most common failure class
(transient provider blips) at zero cost; exactly one rotation bounds blast
radius when a single model is having a bad hour, while avoiding the
naive-rotation spiral; escalation-with-evidence reuses the existing
retry-guardrail ceiling and the human approval gates — it never expands the
fourth-retry gate.

## Verified live rotation list

Seven ids, all `opencode-go/*`, all answering live as of 2026-10-30:

| Model | Verified by |
| --- | --- |
| deepseek-v4.1-flash | base probe report, 2026-10-30T04:18:54Z, status ok |
| glm-5.2 | base probe report, 2026-10-30T04:18:54Z, status ok |
| kimi-k2.7-code | base probe report, 2026-10-30T04:18:54Z, status ok |
| mimo-v2.6-flash | base probe report, 2026-10-30T04:18:54Z, status ok |
| glm-5.3 | overlay MDU-40 live census, 2026-10-30 |
| glm-5.3-flash | overlay MDU-40 live census, 2026-10-30 |
| mimo-v2.6-pro | overlay MDU-40 live census, 2026-10-30 |

The union is exactly the list in the block. Probe artefacts: the base
`config/model-probe-report.json` and the overlay census test's live-ok set.

**Dead list — never a rotation target:** `mimo-v2.5` died upstream before this
policy was written (caught by the MDU-40 test-phase live probe; its absence from
both configs is pinned by the retired-model-ids test). A dead id belongs in
*this* document only. The mirrors must never name it: a dead id in a prompt
invites an LLM to spawn it.

Staleness fails safe. If a listed model dies after this document is written, the
rotated spawn fails, step 3 fires, and the loop escalates. The ladder never
loops and never picks a second target silently; a stale entry costs at most one
wasted spawn.

## Why `xai/*` has no ladder

The xAI account auto-tops-up, so a cap or credit condition there does not look
like "out of budget" — it looks like auth (an expired key, a revoked scope, a
billing gate). Retrying an auth failure is noise, and a silent rotation would
**mask** the class: the grok-family spawns would quietly move to Go models and
the broken credential would never be reported. So `xai/*` errors escalate
straight to the user, with the evidence, on the first failure.

The base Grok mirror's own spawns are all `xai/*`, so the ladder clause is inert
there in practice while the `xai/*` clause is the live one. The byte-identical
requirement still holds: policy wording must not fork per harness.

## The free-model guard

The block says "never substitute a free model" even though the substitution is
currently impossible. That sentence guards future drift. Enforcement chain:

1. **Deletion** — MDU-40 removed every free-tier variant from both configs.
2. **Paid census** — the config validator fail-closes on anything outside the
   `opencode-go/` and `xai/` prefixes, in both repos.
3. **Parity tests** — the exact block is pinned across the three mirrors, so a
   per-mirror reword reds the suite before it reaches a deploy.

A rotation target that is not in the verified list is out of policy by
definition, and an unverified id is not a fallback — it is a guess.

## Worked dry-run example

`evals/tasks/05-fallback-ladder/driver.sh` walks six scripted cases offline and
prints the mandated action plus how many reachable mirrors carry the governing
sentence. Representative transcript:

```
[case 1] opencode-go/deepseek-v4.1-flash spawn reports provider.quota -> one retry, same model [policy sentence found in 3/3 mirrors]
[case 2] the retry fails identically -> one rotation to a live-list model, not the original [policy sentence found in 3/3 mirrors]
[case 3] the rotated spawn fails -> stop; escalate with both errors and both model ids [policy sentence found in 3/3 mirrors]
[case 4] a second rotation is contemplated -> forbidden; never a second silent rotation [policy sentence found in 3/3 mirrors]
[case 5] xai/grok-4.7 spawn reports credit/auth error -> no ladder; escalate directly [policy sentence found in 3/3 mirrors]
[case 6] any spawn failure -> never substitute a free model [policy sentence found in 3/3 mirrors]
PASS fallback-ladder
```

The overlay mirror counts only when the sibling checkout exists, so the public
repo stays self-contained. The driver makes no model calls and needs no network:
it is a demonstration of the decision path, not a live cap-error induction.

## Maintenance procedure

When a model dies upstream, or a new one is verified live, update **in the same
commit**:

1. the block in all three mirrors;
2. this document (live list and/or dead list);
3. the block constant in the base and overlay test files.

A partial update reds the parity tests by naming the missing sentence — that is
the drift guard working, not friction. Do not name dead models in the mirrors;
the dead list lives here only.
