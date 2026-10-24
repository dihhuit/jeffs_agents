# MDU-15 — Cross-CLI run-ledger conformance

## Task
Inline the run-manifest contract into both orchestrator mirrors so all three CLIs (OpenCode/Grok/Claude) produce conformant manifests. Fix normalization and session finalization issues discovered in cross-CLI testing. See [FEATURE_BACKLOG.md](../../FEATURE_BACKLOG.md#MDU-15).

## Phases
| Phase | Agent | Model tier | Outcome | Notes |
| --- | --- | --- | --- | --- |
| design | architect | premium | pass | schema-inline design |
| implement | just-code | budget | pass | updated both orchestrator mirrors |
| review | code-reviewer | mid | pass | sign-off |
| test | test-agent | budget | pass | manifest conformance tests |
| deploy | devops | mid | pass | headless runs across CLIs |
| validate | qa | mid | pass | PASS |
| commit | orchestrator | budget | pass | committed and pushed |

## Narrative
The manifest schema was inlined into `prompts/orchestrator.md` and `grok/agents/orchestrator.md`. Added normalization (`manual-smoke-pass`→`PASS`, `complete`→`completed`) and fixed Grok session finalization. Headless runs across all three harnesses produced manifests passing `run_ledger.py validate` with correct `harness` and `status: completed`.

## Manifest
- Path: [examples/runs/mdu-15-run-ledger-schema-inline/manifest.json](../runs/mdu-15-run-ledger-schema-inline/manifest.json)

```json
{
  "mdu_id": "mdu-15-run-ledger-schema-inline",
  "title": "Cross-CLI run-ledger conformance (schema-inline + re-validation)",
  "status": "completed",
  "harness": "opencode",
  "started_at": "2026-10-21T00:00:00Z",
  "completed_at": "2026-10-21T01:00:00Z",
  "verification": {"build": true, "tests_passed": 393, "tests_total": 393, "qa_grade": "PASS", "ci_green": true},
  "artifacts": ["prompts/orchestrator.md", "grok/agents/orchestrator.md", "docs/observability.md", "scripts/lib/run_ledger.py"],
  "summary": "Schema inlined into both orchestrator mirrors; cross-CLI conformance validated."
}
```

## Evidence
- Docs: `docs/observability.md` (cross-CLI findings)
- Tooling: `scripts/lib/run_ledger.py` validate
- Eval: `evals/tasks/03-ledger-conformance/`
