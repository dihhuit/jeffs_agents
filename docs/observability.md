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