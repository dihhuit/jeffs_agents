# Example run manifests

These manifests are **illustrative examples** written during the live upgrade
session that shipped MDU-07 (run ledger & observability hooks). They mirror
what actually happened in this repo for MDU-01 (model drift fix) and MDU-02
(CI pipeline), but they are samples — the live ledger lives under `runs/`
(gitignored) and is written by the orchestrator per MDU.

Use them as reference for the manifest schema and as fixtures for
`scripts/lib/run_ledger.py`:

```bash
python3 scripts/lib/run_ledger.py validate examples/runs/mdu-01-example/manifest.json
python3 scripts/lib/run_ledger.py validate examples/runs/mdu-02-example/manifest.json
python3 scripts/lib/run_ledger.py summarize examples/runs/
python3 scripts/lib/run_ledger.py summarize examples/runs/ --json
```

See `docs/observability.md` for the full schema and lifecycle.