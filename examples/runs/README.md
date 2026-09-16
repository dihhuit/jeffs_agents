# Example run manifests

This directory holds the run manifests referenced by the dogfooding story
(`examples/upgrade-story.md`). Two kinds of manifests live here:

- **`mdu-01-example/` and `mdu-02-example/`** — illustrative reconstructions of
  the pre-ledger MDUs (model drift fix and CI pipeline). The run ledger did not
  exist yet when those landed, so these are written to mirror what actually
  happened, not recorded live.
- **`mdu-05/`, `mdu-06/`, `mdu-07/`, `mdu-08/`, `mdu-12/`, `mdu-14/`** — real
  session manifests recorded live by the orchestrator during the upgrade session
  (`autonomy_level` 3, approval gates honored).

Use them as reference for the manifest schema and as fixtures for
`scripts/lib/run_ledger.py`:

```bash
python3 scripts/lib/run_ledger.py validate examples/runs/mdu-01-example/manifest.json
python3 scripts/lib/run_ledger.py validate examples/runs/mdu-02-example/manifest.json
python3 scripts/lib/run_ledger.py summarize examples/runs/
python3 scripts/lib/run_ledger.py summarize examples/runs/ --json
```

`summarize examples/runs/` regenerates the "Run Ledger Summary" numbers quoted
in `examples/upgrade-story.md`.

See `docs/observability.md` for the full schema and lifecycle.