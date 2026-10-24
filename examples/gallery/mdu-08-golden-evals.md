# MDU-08 — Golden evaluation suite

## Task
Bootstrap a golden evaluation suite for the agent team itself (5–10 realistic tasks) with a runner, smoke subset, and ledger integration. See [FEATURE_BACKLOG.md](../../FEATURE_BACKLOG.md#MDU-08).

## Phases
| Phase | Agent | Model tier | Outcome | Notes |
| --- | --- | --- | --- | --- |
| design | architect | premium | pass | `docs/design/mdu-08-golden-eval-suite.md` |
| implement | just-code | budget | pass | `evals/`, runner, `run-evals` skill support |
| review | code-reviewer | mid | pass | sign-off |
| test | test-agent | budget | pass | suite validation |
| validate | qa | mid | pass | PASS |
| commit | orchestrator | budget | pass | committed and pushed |

## Narrative
The team created `evals/` with a golden task set, a runner that records results in the run ledger format, and wired a smoke subset into CI (introduced in MDU-02). The suite runs in a scratch workspace with no external paid services.

## Manifest
- Path: [examples/runs/mdu-08/manifest.json](../runs/mdu-08/manifest.json)

```json
{
  "mdu_id": "mdu-08",
  "title": "Golden evaluation suite",
  "status": "completed",
  "harness": "opencode",
  "started_at": "2026-09-16T00:00:00+00:00",
  "completed_at": "2026-09-16T00:30:00+00:00",
  "verification": {"build": true, "tests_passed": 89, "tests_total": 89, "qa_grade": "PASS", "ci_green": true},
  "artifacts": ["evals/"],
  "summary": "Golden evaluation suite with runner and CI smoke subset."
}
```

## Evidence
- Docs: `evals/README.md`
- Artifacts: `evals/` directory with tasks and runner
