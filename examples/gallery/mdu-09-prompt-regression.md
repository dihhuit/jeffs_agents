# MDU-09 — Prompt regression gate (eval-driven prompt dev)

## Task
Add a lightweight comparison flow: snapshot golden-eval results before prompt changes; reject changes that regress ≥1 golden case. See [FEATURE_BACKLOG.md](../../FEATURE_BACKLOG.md#MDU-09).

## Phases
| Phase | Agent | Model tier | Outcome | Notes |
| --- | --- | --- | --- | --- |
| design | architect | premium | pass | protocol design |
| implement | just-code | budget | pass | `scripts/lib/prompt_regression.py`, docs in `evals/README.md` |
| review | code-reviewer | mid | pass | sign-off |
| test | test-agent | budget | pass | regression harness tests |
| validate | qa | mid | pass | PASS |
| commit | orchestrator | budget | pass | committed and pushed |

## Narrative
Implemented a documented prompt change protocol with snapshot/diff of golden eval results. A prompt change that regresses ≥1 golden case is rejected. Added optional promptfoo config support. The loop was demonstrated to reject a bad prompt change across multiple attempts (the 3-rejection story captured in the manifest/ledger).

## Manifest
- Path: [examples/runs/mdu-09-prompt-regression-gate/manifest.json](../runs/mdu-09-prompt-regression-gate/manifest.json)

```json
{
  "mdu_id": "mdu-09-prompt-regression-gate",
  "title": "Prompt regression gate (eval-driven prompt dev)",
  "status": "completed",
  "harness": "opencode",
  "started_at": "2026-09-16T02:00:00+00:00",
  "completed_at": "2026-09-16T02:45:00+00:00",
  "verification": {"build": true, "tests_passed": 102, "tests_total": 102, "qa_grade": "PASS", "ci_green": true},
  "artifacts": ["scripts/lib/prompt_regression.py", "evals/README.md", "evals/promptfoo.yaml"],
  "summary": "Prompt regression gate with snapshot/diff and rejection on ≥1 regression."
}
```

## Evidence
- Script: `scripts/lib/prompt_regression.py`
- Docs: `evals/README.md` (Prompt change protocol)
- Config: `evals/promptfoo.yaml`
