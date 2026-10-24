# Model Registry

Every model referenced by agents in `opencode.json`, grouped by tier. All
entries were verified against `opencode models` on **2026-10-08**.

To re-verify (and refresh the committed snapshot `config/model-registry.txt`):

```bash
opencode models
opencode models > config/model-registry.txt
```

The build pipeline (`scripts/lib/validate.py`) fails if any agent model
reference is missing from the snapshot, so a stale reference cannot ship.

## Orchestrator

| Agent            | Model                    |
|------------------|--------------------------|
| `orchestrator`   | `opencode/big-pickle` |

## Research (free)

| Agent                 | Model                              |
|-----------------------|------------------------------------|
| `research`            | `opencode/mimo-v2.6-flash-free` |
| `deepseek-research`   | `opencode/nemotron-3-ultra-free`   |
| `nemotron-research`   | `opencode/nemotron-3.5-lightning-free` |
| `deep-research`       | `opencode-go/mimo-v2.5` (Go budget) |

## Coding

| Agent             | Model                              |
|-------------------|------------------------------------|
| `just-code`       | `opencode-go/deepseek-v4.1-flash`    |
| `just-code-mid`   | `opencode-go/kimi-k2.7-code`       |
| `just-code-pro`   | `opencode-go/glm-5.2`      |
| `just-code-free`  | `opencode/big-pickle`          |

## Testing

| Agent             | Model                              |
|-------------------|------------------------------------|
| `test-agent`      | `opencode-go/deepseek-v4.1-flash`    |
| `test-agent-mid`  | `opencode-go/mimo-v2.5`           |
| `test-agent-pro`  | `opencode-go/kimi-k2.7-code`       |
| `test-agent-free` | `opencode/big-pickle`          |

## Review

| Agent                 | Model                              |
|-----------------------|------------------------------------|
| `code-reviewer`       | `opencode-go/mimo-v2.5`           |
| `code-reviewer-pro`   | `opencode-go/glm-5.2`      |
| `code-reviewer-free`  | `opencode/big-pickle`          |

## Architecture

| Agent                | Model                              |
|----------------------|------------------------------------|
| `architect`          | `opencode-go/glm-5.2`      |
| `architect-premium`  | `opencode-go/glm-5.2`              |

## DevOps

| Agent          | Model                              |
|----------------|------------------------------------|
| `devops`       | `opencode-go/mimo-v2.5`           |
| `devops-pro`   | `opencode-go/glm-5.2`      |
| `devops-free`  | `opencode/big-pickle`          |

## QA

| Agent    | Model                              |
|----------|------------------------------------|
| `qa`     | `opencode-go/mimo-v2.5`           |
| `qa-pro` | `opencode-go/kimi-k2.7-code`       |
| `qa-free`| `opencode/big-pickle`          |

## UI/UX

| Agent                  | Model                              |
|------------------------|------------------------------------|
| `ui-ux-designer`       | `opencode-go/mimo-v2.5`           |
| `ui-ux-designer-pro`   | `opencode-go/kimi-k2.7-code`       |

## Inception

User-invoked primary. Not part of the orchestrator's MDU loop.

| Agent        | Model                              |
|--------------|------------------------------------|
| `inception`  | `opencode-go/deepseek-v4.1-flash`    |

## Cost audit — glm-5.2 premium agents (MDU-32)

Prices were read from live model metadata with `opencode models` (model id,
cost per Mtok, release date) on **2026-10-24**, USD per 1M tokens (input /
output / cache read). That read is newer than the committed
`config/model-registry.txt` snapshot, which is the 2026-10-08 catalog and
carries bare model ids only — it does not carry prices.
`opencode-go/kimi-k3.1-pro` is absent from that snapshot and is not referenced
by any agent. `glm-5.3`, `glm-5.3-flash` and `qwen3.8-max` are in the snapshot
but are not referenced by any agent, so no rebase of the snapshot was needed
for this pricing-only audit. Cache write is 0 on every row below except
`kimi-k3` (3.00), `kimi-k3.1-pro` (2.00) and `qwen3.8-max` (2.50).
Per-model usage and spend are
Console-only and were not available, so this audit compares list prices, not
actual spend.

| Model                            | Tier in this repo                                          | Input $/Mtok | Output $/Mtok | Cache read $/Mtok | Price vs glm-5.2              | Fit (premium tier)                      |
|----------------------------------|------------------------------------------------------------|--------------|---------------|-------------------|-------------------------------|-----------------------------------------|
| `opencode-go/glm-5.2`            | current premium                                            | 1.40         | 4.40          | 0.26              | baseline (100%)               | Current model. Only Go model with evidence at ADR-grade design, security review, and multi-service deploy work. |
| `opencode-go/glm-5.3`            | not used                                                   | 1.40         | 4.40          | 0.26              | 100% (identical pricing)      | Newer release in the same family. An in-family upgrade would be cost-neutral, not a saving — out of scope for a cost audit. |
| `opencode-go/kimi-k3.1-pro`      | not used                                                   | 2.00         | 10.00         | 0.20              | 143% input, 227% output       | More expensive. Family upgrade of `kimi-k2.7-code`; no case for premium work. |
| `opencode-go/kimi-k3`            | not used                                                   | 3.00         | 15.00         | 0.30              | 214% input, 341% output       | More expensive. Previous generation of `kimi-k3.1-pro`; no case for premium work. |
| `opencode-go/qwen3.8-max`        | not used                                                   | 2.00         | 6.00          | 0.25              | 143% input, 136% output       | More expensive. No case for premium work. |
| `opencode-go/kimi-k2.7-code`     | mid (`just-code-mid`, `test-agent-pro`, `qa-pro`, `ui-ux-designer-pro`) | 0.95 | 4.00 | 0.19         | 68% input / 91% output        | Cheapest model already carrying pro-slot work (test/QA/UI). Code-specialised mid tier; not established for architecture/security judgement. |
| `opencode-go/deepseek-v4-pro`    | not used                                                   | 0.66         | 1.98          | 0.022             | 47% input / 45% output        | General-purpose pro-shaped candidate, but no capability evidence in this repo for ADR-grade design or security review. |
| `opencode-go/mimo-v2.6-pro`      | not used                                                   | 0.435        | 0.87          | 0.003625          | 31% input / 20% output        | Cheapest general-purpose pro-shaped candidate; same capability-evidence gap, and cache-read pricing implies a different usage mix. |
| `opencode-go/glm-5.3-flash`      | not used                                                   | 0.15         | 0.50          | 0.03              | ~11% input / 11% output       | Flash tier. Below the reasoning level these agents are selected for. |

### Fit assessment

The orchestrator prompt (`prompts/orchestrator.md`) labels four of these five
pro-slot agents "Go premium" — `just-code-pro`, `code-reviewer-pro`,
`architect` and `devops-pro` — with `architect-premium` labelled "Go
top-tier"; the Grok mirror (`grok/agents/orchestrator.md`) is provider-neutral
and carries no such labels. This document's agent tables list
`opencode-go/kimi-k2.7-code` on the mid agent `just-code-mid` *and* on three
`-pro` agents (`test-agent-pro`, `qa-pro`, `ui-ux-designer-pro`), which is
exactly why concentrating all five premium agents on it is unattractive.

| Agent               | Current model          | Cheaper candidate would be                                                        | Why it stays on `glm-5.2`                                                                                                       |
|---------------------|------------------------|-----------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| `just-code-pro`     | `opencode-go/glm-5.2`  | `opencode-go/kimi-k2.7-code` (mid, 0.95 / 4.00), `opencode-go/deepseek-v4-pro`    | Complex cross-service refactors are the failure mode cheap tiers show first; savings on premium-only calls do not offset a regression. |
| `code-reviewer-pro` | `opencode-go/glm-5.2`  | `opencode-go/deepseek-v4-pro` (0.66 / 1.98), `opencode-go/mimo-v2.6-pro`          | Security review depends on judgement, and none of the cheaper candidates has review-quality evidence here.                       |
| `architect`         | `opencode-go/glm-5.2`  | `opencode-go/deepseek-v4-pro` (0.66 / 1.98), `opencode-go/mimo-v2.6-pro`          | ADR-grade design and trade-off reasoning is the core requirement; a cheaper model has no bake-off evidence at that tier.         |
| `architect-premium` | `opencode-go/glm-5.2`  | `opencode-go/deepseek-v4-pro` (0.66 / 1.98), `opencode-go/mimo-v2.6-pro`          | This agent deliberately escalates for hard design problems, so it must not be the first place to economize.                     |
| `devops-pro`        | `opencode-go/glm-5.2`  | `opencode-go/kimi-k2.7-code` (mid), `opencode-go/deepseek-v4-pro`, `opencode-go/mimo-v2.6-pro` | Multi-service deploy and rollback decisions carry the highest blast radius per token.                                |

### Decision

**No-op — no functional changes.** `opencode-go/glm-5.2` keeps all five premium agents.

1. No cheaper candidate is established at premium reasoning tier. `opencode-go/kimi-k2.7-code` (0.95 / 4.00 / 0.19) is the cheapest model in the catalog that already carries pro-slot work in this repo and is cheaper than `opencode-go/glm-5.2` on both axes — 68% of its input price and 91% of its output price — but it is a code-specialised model already carrying the pro test/QA/UI slots (`test-agent-pro`, `qa-pro`, `ui-ux-designer-pro`), so it is not an available fallback for the reasoning- and security-heavy agents. Moving those five onto it would concentrate the whole pro tier on one model with no capability evidence at that tier, and its family upgrade `opencode-go/kimi-k3.1-pro` costs 143% input / 227% output of `opencode-go/glm-5.2`. `opencode-go/deepseek-v4-pro` (0.66 / 1.98) and `opencode-go/mimo-v2.6-pro` (0.435 / 0.87) are genuinely cheaper — 53–55% saved on `deepseek-v4-pro`, 69–80% on `mimo-v2.6-pro` — but have no capability evidence in this repo for ADR-grade design or security review. `docs/opencode-v2.md` records `opencode-go/deepseek-v4-pro` previously powering four of these five agents before the migration to `opencode-go/glm-5.2`, so the current assignment is a deliberate capability decision already made in this repo, not an unexamined default. The eval and prompt-regression suites grade prompt/contract conformance, not model quality, so a swap would trade unknown regressions for those savings on premium-tier calls only.
2. `opencode-go/glm-5.3` is priced identically to `opencode-go/glm-5.2`; upgrading family is cost-neutral and out of scope for a cost audit. Record it as a candidate for a future capability MDU, not as a saving.
3. Cheap-tier work is already off glm-5.2 (budget = `opencode-go/deepseek-v4.1-flash`, mid = `opencode-go/kimi-k2.7-code`, free = `opencode/big-pickle`), so glm-5.2 volume is bounded by the small number of premium escalations.

### Re-open conditions

- (a) The OpenCode Console shows premium escalation share above ~30% of spend.
- (b) A bake-off shows `opencode-go/deepseek-v4-pro` or `opencode-go/mimo-v2.6-pro` matching glm-5.2 on the golden eval suite.
- (c) `opencode-go/glm-5.3` shows a capability gain over `opencode-go/glm-5.2` on the golden eval suite at identical cost — a capability consideration for a future MDU, not a saving.

## Zen variant mapping (MDU-33)

The Zen tier (`build/opencode.zen.json`, generated at build time from
`opencode.json` + `config/zen-model-map.json`) replaces every paid
`opencode-go/*` model with a free Zen model. The map was verified against
`opencode models` on **2026-10-24**: `opencode/big-pickle` and
`opencode/nemotron-3-ultra-free` were both present, and both are free Zen
(`opencode/big-pickle` despite carrying no `-free` suffix). The free allowlist
is derived from the committed snapshot by provider prefix — every
`opencode/*` entry in `config/model-registry.txt`.

Re-verify before changing the map:

```bash
opencode models | grep '^opencode/'
```

### Model-keyed mapping

The free catalog preserves none of the Go budget/mid/premium distinction, so
the four Go source models collapse onto the two free models with in-repo usage
evidence.

| Source (`opencode-go/*`) | Agents (count) | Zen target | Rationale |
| --- | --- | --- | --- |
| `opencode-go/deepseek-v4.1-flash` | just-code, test-agent, inception (3) | `opencode/big-pickle` | Strongest proven free model; already carries these roles via the `-free` variants. |
| `opencode-go/kimi-k2.7-code` | just-code-mid, test-agent-pro, qa-pro, ui-ux-designer-pro (4) | `opencode/nemotron-3-ultra-free` | Second proven free generalist; spreads the coding loop across two free models. |
| `opencode-go/glm-5.2` | just-code-pro, code-reviewer-pro, architect, architect-premium, devops-pro (5) | `opencode/big-pickle` | **Documented capability regression** — nothing free matches glm-5.2's reasoning tier. These premium slots are the primary documented trigger to switch up to Go mid-period. |
| `opencode-go/mimo-v2.5` | test-agent-mid, code-reviewer, devops, qa, deep-research, ui-ux-designer, introspector (7) | `opencode/nemotron-3-ultra-free` | Mid slots → the second free generalist, spreading load. |

### Unchanged (already free, 9)

| Agent | Model |
| --- | --- |
| orchestrator, just-code-free, test-agent-free, code-reviewer-free, devops-free, qa-free | `opencode/big-pickle` |
| research | `opencode/mimo-v2.6-flash-free` |
| deepseek-research | `opencode/nemotron-3-ultra-free` |
| nemotron-research | `opencode/nemotron-3.5-lightning-free` |

Resulting Zen distribution (28 agents): `opencode/big-pickle` 14 agents,
`opencode/nemotron-3-ultra-free` 12, plus the two remaining research agents
above (`opencode/mimo-v2.6-flash-free` 1, `opencode/nemotron-3.5-lightning-free`
1); `deepseek-research`'s `opencode/nemotron-3-ultra-free` is counted in the 12.
Concentration on `big-pickle` is a known limitation, mitigated by the Go
switch-up, the per-agent `overrides` knob in `config/zen-model-map.json`, and
premium slots being low-volume (see the MDU-32 cost audit).

### Alternates and overrides

Alternates are catalogued in the map but **not placed on hot paths** (no
bake-off evidence): `opencode/exo-free`, `opencode/space-bunny-free`,
`opencode/step-5-preview-free`, `opencode/longcat-2.5-preview-free`,
`opencode/muse-spark-1.3-contributor-free`, `opencode/ling-3.1-flash-free`.

`config/zen-model-map.json` also carries `overrides: { "<agent-name>": "<model>" }`,
applied after the model-keyed rules. It is empty by default and is the tuning
knob when live usage shows one slot rate-limiting; override targets must be in
the free allowlist or the build fails.

### Tier selection

Zen is the **default deploy tier**; Go is the switch-up when Zen usage for the
period is exhausted. `./deploy.sh --force` installs Zen;
`./deploy.sh --force --tier=go` switches up. Both configs are always installed
(active + parked). See the README "Model Tiers" section for the concrete
commands and the manual `cp` one-liner.

### Known limitations

- **Premium capability regression:** `opencode-go/glm-5.2` slots (just-code-pro,
  code-reviewer-pro, architect, architect-premium, devops-pro) run on
  `opencode/big-pickle` in the Zen tier. This is by design and the documented
  switch-up trigger.
- **Variant names persist while models collapse:** e.g. just-code ≡
  just-code-pro ≡ just-code-free (all `big-pickle`). Names, permissions, and
  temperatures stay distinct, so the orchestrator's tier ledger remains
  meaningful; only the model string collapses.
- Zen per-model vs account-wide usage limits are not established; the primary
  response to exhaustion is `--tier=go`.
- The overlay repo builds its own `opencode.json` and does not consume this
  generated file; adopting the Zen tier there is a follow-up in that repo.
