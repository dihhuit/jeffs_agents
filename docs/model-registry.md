# Model Registry

Every model referenced by agents in `opencode.json`, grouped by tier. Since
MDU-40 there is one paid configuration: every agent runs on `opencode-go/*`
(OpenCode Go subscription) and grok-named agents on `xai/*`. All entries were
verified against `opencode models` on **2026-10-08**.

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
| `orchestrator`   | `opencode-go/mimo-v2.6-flash` |

## Research (paid)

| Agent                 | Model                              |
|-----------------------|------------------------------------|
| `deep-research`       | `opencode-go/mimo-v2.6-flash` (Go budget) |

## Coding

| Agent             | Model                              |
|-------------------|------------------------------------|
| `just-code`       | `opencode-go/deepseek-v4.1-flash`    |
| `just-code-mid`   | `opencode-go/kimi-k2.7-code`       |
| `just-code-pro`   | `opencode-go/glm-5.2`      |

## Testing

| Agent             | Model                              |
|-------------------|------------------------------------|
| `test-agent`      | `opencode-go/deepseek-v4.1-flash`    |
| `test-agent-mid`  | `opencode-go/mimo-v2.6-flash`           |
| `test-agent-pro`  | `opencode-go/kimi-k2.7-code`       |

## Review

| Agent                 | Model                              |
|-----------------------|------------------------------------|
| `code-reviewer`       | `opencode-go/mimo-v2.6-flash`           |
| `code-reviewer-pro`   | `opencode-go/glm-5.2`      |

## Architecture

| Agent                | Model                              |
|----------------------|------------------------------------|
| `architect`          | `opencode-go/glm-5.2`      |
| `architect-premium`  | `opencode-go/glm-5.2`              |

## DevOps

| Agent          | Model                              |
|----------------|------------------------------------|
| `devops`       | `opencode-go/mimo-v2.6-flash`           |
| `devops-pro`   | `opencode-go/glm-5.2`      |

## QA

| Agent    | Model                              |
|----------|------------------------------------|
| `qa`     | `opencode-go/mimo-v2.6-flash`           |
| `qa-pro` | `opencode-go/kimi-k2.7-code`       |

## UI/UX

| Agent                  | Model                              |
|------------------------|------------------------------------|
| `ui-ux-designer`       | `opencode-go/mimo-v2.6-flash`           |
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
3. Cheap-tier work is already off glm-5.2 (budget = `opencode-go/deepseek-v4.1-flash`, mid = `opencode-go/kimi-k2.7-code`), so glm-5.2 volume is bounded by the small number of premium escalations.

### Re-open conditions

- (a) The OpenCode Console shows premium escalation share above ~30% of spend.
- (b) A bake-off shows `opencode-go/deepseek-v4-pro` or `opencode-go/mimo-v2.6-pro` matching glm-5.2 on the golden eval suite.
- (c) `opencode-go/glm-5.3` shows a capability gain over `opencode-go/glm-5.2` on the golden eval suite at identical cost — a capability consideration for a future MDU, not a saving.

## Live model-health probe (MDU-38)

`opencode models` can list a model as `active` after upstream has killed it —
that is exactly what caused the mdu-37 incident (12 agents routed to a dead
`opencode/nemotron-3-ultra-free`, three spawns failed with
`Model is unavailable`). A listing is not proof of life, so deploys are gated
on a real inference:

```bash
timeout 90 opencode run -m opencode-go/deepseek-v4.1-flash "Reply with exactly: OK"
```

`scripts/lib/probe_models.py` runs that command once per model, records the
result in `config/model-probe-report.json` (machine-local, gitignored), and
grades the report. Success is strict: exit 0 **and** stdout stripped exactly
`OK` — a truncated run, or an answer that merely contains `OK` (`NOT OK`), is
not proof the model answered.

```bash
# Bootstrap and routine refresh (probe, then gate):
python3 scripts/lib/probe_models.py --refresh --gate --config build/opencode.json

# Gate only (what deploy.sh runs):
python3 scripts/lib/probe_models.py --gate --config build/opencode.json
```

### Probe set — the canonical config

The config is the single source of truth (MDU-40): every distinct agent model
is a hard target, grouped by provider. For the shipped config that is the
`opencode-go/*` models plus the `xai/*` grok models; `--include-xai` is an
accepted no-op because xai probing is always on. There are no alternates and
no map to edit — a remap, add, or removal re-reds the gate through the hash.

### Report

`config/model-probe-report.json`, schema version 1: one report-level
`probed_at` (no per-model timestamps), `config_path`, `config_sha256` over the
sorted `agent=model` pairs (so re-indenting hashes identically while any
remap changes it), `results` for the `opencode-go/*` targets, `xai_results`
for the `xai/*` targets, and one entry per model with `status` `ok` / `fail` /
`skipped`, `attempts`, `latency_s` and `error`. Captured CLI output is
ANSI-stripped before it is stored, so `error` is readable text (a bare colour
reset never becomes the recorded error). Each `--refresh` rewrites the
whole report: any merge union could keep an `ok` for a model that has since
died. `--refresh` exits 0 whenever the report was written, even with failing
models — the result is data; grading is `--gate`.

Permanent failures (`Model is unavailable`, `not found`, `404`, invalid model)
are not retried; transient ones (timeout, `429`, `5xx`, connection errors) get
one retry. A missing `opencode` CLI writes **no** report and exits 2.

### Gate rules and exit codes

Evaluated in order; every offence is listed one per line.

1. Report missing/unreadable/malformed, wrong `schema_version`, or an
   unparsable / more-than-1-hour-future `probed_at` → red.
2. `config_sha256` is absent (a cache written before the MDU-40 schema →
   `report cache predates MDU-40 schema; run --refresh --gate --config <file>`)
   or differs from the current config → red (`config changed since last
   probe`). Remapping, adding, or removing an agent therefore forces a
   re-probe.
3. Older than `--max-age-days` (default **7**) → red. `--max-age-days 0`
   disables only the age rule; `ok` and the hash match are still required.
4. Every `opencode-go/*` target needs exactly one `ok` result. Missing, `fail`
   and `skipped` are all red — a skipped probe never satisfies freshness.
5. Every `xai/*` target needs exactly one `ok` result in `xai_results`
   (MDU-42); a missing section is red.
6. Models outside the paid provider set → `[warn]` only (the validator rejects
   them outright).

| Exit | Meaning |
| --- | --- |
| 0 | green: every target ok, report fresh, config hash matches |
| 1 | red: any rule 1–5 offence, offenders listed |
| 2 | cannot evaluate: no `opencode` CLI, missing config, bad arguments |

### Where it runs

Documented order: **(1) build → (2) probe gate → (3) install →
(4) `opencode debug agents`**.

- `open-agent-definitions/scripts/deploy.sh` runs the gate **advisory only**
  (it is the public repo: a stranger with no report or no CLI must still
  deploy). Red prints a `[warn]` and continues.
- The overlay `opencode_agents/scripts/deploy.sh` runs the same gate **hard**
  before any copy, with its own report under the overlay tree. A dry run warns
  and continues; `--force` aborts on red. `--skip-probe` is the documented
  escape hatch.
- Never in CI: no `opencode` CLI there by design, and the probe is a live,
  machine-local check.

**Trust rule:** every model in `opencode.json` must probe green to deploy.
Probe answers "can it answer at all", not "is it good" — model choice stays a
reviewed config edit, with the report as evidence.

## Grok-xai hard rule (MDU-42)

Grok-named agents (any agent whose name starts with `grok-`, or is exactly
`grokestrator` or `grok-plan`) run **only** on the user's xAI account models
(`xai/*`, currently `xai/grok-4.7` for reasoning roles and
`xai/grok-build-0.1` for build roles) — in every harness. They are never
delegated to a free (`opencode/*`) or Go-substituted (`opencode-go/*`) opencode
model. MDU-40 removed the Zen transform that used to rewrite their model.

Enforcement layers, in documented order:

1. **Build validator** (`scripts/lib/validate.py`): every grok-named agent in
   `opencode.json` must resolve to an `xai/*` model; violations are named
   errors (agent → model) and fail the build.
2. **Probe** (`scripts/lib/probe_models.py`): the grok-named agents' `xai/*`
   models are probed with the same exact-match OK rule as the Go targets, into
   the report's distinct `xai_results` section. `--gate` goes red when an xai
   entry is red or missing from the report. `--include-xai` is a deprecated
   no-op — xai probing is always on (MDU-40).
3. **Deploy gate** (`scripts/deploy.sh`): the single config is checked with
   `model_registry.py --grok-xai-check` before install; a named failure exits
   non-zero and the deploy aborts.

**Refusal stance (D6):** there is no runtime fallback. If xAI credentials are
missing or the account model is dead, the probe gate fails with a named
(credential-naming) error and deploy refuses to install — the grok-named agent
staying unavailable is the intended outcome, not silently running it on a
substitute model. Refresh with
`python3 scripts/lib/probe_models.py --refresh --gate --config build/opencode.json`.

## Free-tier caps (2026-10-29)

Historical: free models are no longer used (MDU-40). Kept verbatim as the
evidence that drove the decision.

> Preface: the OpenCode free-tier cap is **undocumented in published docs as of 2026-10-29**. One official figure — "200 requests a day" — stood in the Go-page FAQ until 2026-10-22 and was then removed without replacement; treat it as retracted, not current. Maintainers describe the cap as per-account, server-enforced, daily-resetting with a per-user reset clock shown in the error; no cap size, fixed hour, or timezone is published. Community reports (~2026-10-22→25 tightening wave, aggregated in pinned GitHub thread #59387) say the limit is shared across all free models; that is community-observed, not official. All numbers below are labeled: **live probe** / **storage sweep** (68 `status:429` rows in the OpenCode DB) / **deploy evidence** (2026-10-29 probe gate) / **community-observed**. The quota is account-shared, so a model probing OK on a given day is not exemption evidence. **Standing statement: caps are undocumented/unstable as of 2026-10-29 — no official cap size since the 200/day figure was retracted 2026-10-22; numbers below are labeled by source (live probe / storage sweep / deploy evidence / community-observed).** 2026-10-30 ~02:57 UTC live probes — all four refused-until-now models returned exact-OK (`big-pickle`, `mimo-v2.6-flash-free`, `nemotron-3.5-lightning-free`, `deepseek-v4.1-flash-free`), i.e. the daily reset came back through for the whole free family at once; this live cycle confirms the reset is account-shared, not per-model.

| Model | Role in our maps | Observed cap behavior (date) | Refusal state (string) | Source |
| --- | --- | --- | --- | --- |
| `big-pickle` | Primary free workhorse: 19 of 50 zen agents (orchestrator, architect, just-code & variants, mdu-code, qa-free, test-agent*, devops-free/pro, code-reviewer-free/pro, qa-pro, inception, ui-ux-designer-pro) | Shared account quota refused; first hit in our logs 2026-10-24 (8 rows, all old wording); canonical 8 rows on 2026-10-28 and 52 rows on 2026-10-29 (last error row 2026-10-29 13:12:49Z); 0 error rows on 2026-10-30; **exact-OK live probe 2026-10-30 ~02:57 UTC** — same-day probe-OK is reset recovery, not exemption evidence | 429 `provider.quota` / `FreeUsageLimitError` — 60× "Free usage limit reached. Free models work in OpenCode (https://opencode.ai); subscribe to OpenCode Go to keep going: https://opencode.ai/go"; 8× older "Free usage limit reached. Subscribe to OpenCode Go to keep going: https://opencode.ai/go" | Storage sweep + deploy evidence + 2026-10-30 live probe; every real-work death row in the sweep ran on big-pickle |
| `deepseek-v4.1-flash-free` | Alternate in older zen map slots; not in the currently deployed config | Refused at probe gate, 2 attempts, 2026-10-29 | Same 429 `FreeUsageLimitError` refusal string (canonical wording of 2026-10-29) | Live probe (deploy evidence Step 3) + storage-sweep probe burst (4 probe sessions, 10-29 14:32Z) |
| `mimo-v2.6-flash-free` | Free tier: 1 agent (`research`) | Refused at probe gate, 2 attempts, 2026-10-29 — despite being a current-deploy agent model, consistent with account-shared quota | Same refusal string | Live probe (deploy evidence Step 3) + storage-sweep probe burst ×4 |
| `nemotron-3.5-super-vl-free` | Alternate, not in the currently deployed config | Refused at probe gate, 2 attempts, 2026-10-29 | Same refusal string | Live probe (deploy evidence Step 3) + storage-sweep probe burst ×4 |
| `nemotron-3.5-lightning-free` | Free tier: 9 agents (code-reviewer, deep-research, deepseek-research, devops, introspector, nemotron-research, qa, test-agent-mid, ui-ux-designer) | Probed **OK** 2026-10-29 (alternates `beam-free` / `flint-40b-free` also OK) — not exemption evidence: quota is account-shared across all free models; **exact-OK live probe 2026-10-30 ~02:57 UTC**, again not exemption evidence | None observed to date | Live probe (deploy evidence Step 3) + 2026-10-30 live probe |
| `xai/grok-4.7`, `xai/grok-build-0.1` | Paid: 13 + 8 agents, exempt by the MDU-42 grok-xAI hard rule | No cap class — free-tier caps are out of scope for xai/* | None | Live probe 2026-10-29 (2/2 exact-OK; CLI probe exit 0) |

One clean day-cycle observation (2026-10-29 → 10-30): retracted-official stale cap economics + daily reset, account-shared across all free models, confirmed live — account-shared free quota reset across the 2026-10-29→30 boundary (last fatal block-mode row in storage 2026-10-29 13:12:49Z; refusal persisted through the 2026-10-29 probe gate; all four refused models probed OK together the next morning UTC). The user's paid-default decision (MDU-40) is unchanged: free models still cap mid-loop after heavy morning use.
