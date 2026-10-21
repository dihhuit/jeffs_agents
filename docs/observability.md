# Observability: Run Ledger

Every MDU leaves a machine-readable record of what ran, which agents and model
tiers were used, and what the outcome was. The ledger lives under `runs/`
(gitignored — see `.gitignore`) with one manifest per MDU at
`runs/<mdu-id>/manifest.json`. `examples/runs/` holds sample manifests from the
live upgrade session.

## Manifest schema

| Field | Type | Notes |
| --- | --- | --- |
| `mdu_id` | string | e.g. `mdu-01` |
| `title` | string | short human-readable title |
| `status` | enum | `in_progress` \| `completed` \| `failed` \| `escalated` |
| `harness` | enum | `opencode` \| `grok` \| `claude` — which agentic CLI executed the MDU |
| `started_at` | string (ISO-8601) | when the MDU started |
| `completed_at` | string (ISO-8601) | when the MDU finished |
| `phases` | array | one entry per phase, see below |
| `fix_iterations` | integer | number of fix/redo cycles across any phase (implement, review, test, deploy, validate) |
| `autonomy_level` | integer 0–4 | autonomy ladder level at which the MDU ran |
| `verification` | object | build/tests/QA/CI results, see below |
| `artifacts` | array of strings | relative paths of produced artifacts |
| `summary` | string | free-text summary for the final report |

Each `phases` entry:

| Field | Type | Notes |
| --- | --- | --- |
| `phase` | enum | `design` \| `implement` \| `review` \| `test` \| `deploy` \| `validate` \| `commit` |
| `agent` | string | agent name, e.g. `just-code` |
| `model_tier` | enum | `free` \| `budget` \| `mid` \| `premium` \| `top-tier` |
| `outcome` | enum | `pass` \| `fail` \| `pending` |
| `notes` | string | free text (errors, retries, sign-offs) |

The `verification` object:

| Field | Type | Notes |
| --- | --- | --- |
| `build` | bool | did `./build.sh` succeed |
| `tests_passed` | integer | passing tests |
| `tests_total` | integer | total tests |
| `qa_grade` | `"PASS"` \| `"FAIL"` \| null | QA verdict |
| `ci_green` | bool \| null | CI pipeline result |

The schema is enforced in code by `scripts/lib/run_ledger.py` (module
constants `STATUSES`, `PHASES`, `MODEL_TIERS`, `OUTCOMES`, `QA_GRADES`,
`HARNESSES`).

Since MDU-15 the same contract is also inlined in both orchestrator mirrors
(`prompts/orchestrator.md` and `grok/agents/orchestrator.md`) so any CLI or subagent
can conform with zero external lookup — the 2026-09-16 cross-CLI test showed a bare
scratch workspace cannot read this doc. `run_ledger.py`'s module constants remain
the single source of truth; `tests/test_mdu_15_run_ledger_inline.py` cross-checks
the prompt's fields, enums, and example against them. To change the schema, edit
`run_ledger.py`, both mirrors, and this doc in the same commit — the tests fail
otherwise.

## Lifecycle of a manifest

1. **Start** — the orchestrator creates `runs/<mdu-id>/manifest.json` with
   `status: "in_progress"`, `started_at`, and an empty `phases` array.
2. **Per phase** — as each phase completes, the orchestrator appends a
   `phases` entry recording the agent, model tier, outcome, and notes.
3. **Finish** — before committing, the orchestrator sets the final `status`,
   `completed_at`, `verification`, `fix_iterations`, `autonomy_level`, and
   `artifacts`, then validates the manifest (see below).
4. **Aggregate** — `run_ledger.py summarize` rolls any number of manifests up
   into status counts, per-tier model usage, fix iterations, and QA results.

## CLI

Validate a single manifest (exit 0 on success, 1 with errors on violation):

```bash
python3 scripts/lib/run_ledger.py validate runs/mdu-01/manifest.json
```

Aggregate every `runs/*/manifest.json` under a directory:

```bash
python3 scripts/lib/run_ledger.py summarize            # defaults to runs/
python3 scripts/lib/run_ledger.py summarize examples/runs/
python3 scripts/lib/run_ledger.py summarize examples/runs/ --json
```

The `--json` output is a stable dict (status counts, phases by phase and by
model tier, fix iterations, QA PASS/FAIL, test totals) suitable for CI or
dashboards.

## Cross-CLI headless notes

The contract above is also inlined in both orchestrator mirrors, so a headless CLI in a
bare scratch workspace can conform without reading this doc. The three headless
invocations used by `evals/tasks/03-ledger-conformance/` (run from the scratch workspace):

```bash
timeout 480 opencode run --agent orchestrator "$(cat TASK.md)"
timeout 480 grok --agent orchestrator -p "$(cat TASK.md)"
timeout 480 claude --agent orchestrator -p "$(cat TASK.md)" --dangerously-skip-permissions
```

**claude requires `--dangerously-skip-permissions` or Write is denied and the run reports BLOCKED**

2026-09-16 dialect findings, before the inline block:

- opencode: `qa_grade: "manual-smoke-pass"` plus missing `title` and timestamps.
- grok: `status: "in_progress"` with null verification, never finalized.
- claude: `status: "complete"` plus `build: "n/a"`.

### 2026-10-21 re-test outcome

All three CLIs re-verified against the inlined schema on 2026-10-21, each in its own
scratch workspace seeded with only `scripts/lib/run_ledger.py` and the golden task text
(no `docs/` directory, no schema document). Each CLI produced a manifest that the base
validator accepts, with the correct `harness` value and `status: "completed"`, and each
scratch workspace contains a git commit.

| CLI | manifest | validator | `harness` | `status` | commit |
| --- | --- | --- | --- | --- | --- |
| opencode | `runs/mdu-ledger-check/manifest.json` | exit 0 | `opencode` | `completed` | `6d47d54` |
| grok | `runs/mdu-ledger-check/manifest.json` | exit 0 | `grok` | `completed` | `cb87dc8` |
| claude | `runs/mdu-ledger-check/manifest.json` | exit 0 | `claude` | `completed` | `422fc44` |

Driver: `evals/tasks/03-ledger-conformance/driver.sh <opencode|grok|claude|all>` — all three
legs exited 0 with every check `[ok]`.

Notes on what the re-test actually established:

- The old dialect did not reappear in any CLI. The pre-inline prompt wording produced
  `status: "complete"`, `build: "n/a"` and `qa_grade: "manual-smoke-pass"`; all three
  manifests now use `status: "completed"`, a JSON boolean `build`, and
  `qa_grade: "PASS"`. These three rules live only in the inlined prompt — `run_ledger.py`
  enforces none of them — so a conformant manifest is direct evidence that the inline
  block, not the validator, carried the contract.
- The claude leg requires `--dangerously-skip-permissions`; headless claude denies writes
  otherwise and produces no manifest. Claude Code needs that flag (or an interactive
  approval) for the conformance task to complete.
- The grok leg needed no adjudication probe. The known grok defect of stopping before the
  final commit did not reproduce: the commit and the `commit` phase entry both landed
  unprompted.
- The opencode leg reported `fix_iterations: 1` where grok and claude reported `0`; each
  value matches the fix cycles actually described in that manifest's phase notes.
- A CLI may write its own documentation into the scratch workspace while it works (the
  opencode leg produced `docs/design/mdu-ledger-check.md`). That file is CLI output, never
  seed: the seed contains only `scripts/lib/run_ledger.py` and the task text, so it cannot
  have supplied the schema.

Protocol, seeding, grading, and the grok finalization probe:
`evals/tasks/03-ledger-conformance/`.

## Agent improvement log

In addition to the run ledger, the [`introspector`](../prompts/introspector.md)
writes durable agent-definition improvement suggestions after each MDU:

- `agent-improvements.md` at the project root — a rolling, committed log of open
  suggestions and session records. Orchestrators read this at session start and
  after every MDU and apply the `apply-now` items in the next delegation loop.
  Agent definition files are not auto-edited; only the user may change them.
- `runs/<mdu-id>/introspection.md` — a per-run snapshot written when the
  orchestrator passes an MDU id. This file may be gitignored along with the rest
  of `runs/`; it exists mainly for local traceability and post-hoc review.

## Heavy upgrade path: OTel GenAI / Langfuse

The manifest ledger is a lightweight, dependency-free record. When you want
per-call traces, token counts, and cost telemetry, the drop-in upgrade is to
instrument the orchestrator's subagent invocations with OpenTelemetry GenAI
semantic conventions and export to an OTel-compatible backend such as Langfuse.
The [OpenTelemetry semantic conventions for generative AI](https://github.com/open-telemetry/semantic-conventions-genai)
define span attributes for model calls (model name, tier, token usage,
latency); wrapping each subagent call in a span and exporting via OTLP gives
you the per-phase detail the manifest summarizes. [Langfuse](https://langfuse.com/)
provides a hosted OTel endpoint, dashboards, and cost tracking out of the box.
The manifest `model_tier` values map directly onto span attributes, so the two
systems complement each other: the ledger is the durable audit trail, OTel is
the live trace.