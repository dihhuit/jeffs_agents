# Tests for model-registry validation (MDU-01)

This suite covers the offline/live model registry validation added in
`scripts/lib/model_registry.py` and its integration in
`scripts/lib/validate.py` (the `--live-models` flag and model-ref check). It
also covers the `validate_schema` JSON Schema check against
`schemas/opencode.schema.json` (MDU-03) and the per-MDU run ledger
(`scripts/lib/run_ledger.py`: manifest schema validation incl. the `harness`
enum, `summarize` aggregation with `by_harness`, and the validate/summarize
CLI).

## Files

| File | What it covers |
| --- | --- |
| `test_model_registry.py` | `load_registry`, `find_model_refs`, `check_models`, `check_live`, and the `model_registry.py` CLI (`--check`, `--snapshot`, `--live`) |
| `test_validate_integration.py` | `validate_model_refs`, `print_live_drift`, and `validate.main` with `--live-models` |
| `test_validate_schema.py` | `validate_schema` against `schemas/opencode.schema.json`: valid config passes, violations report the offending field, missing `jsonschema` skips with a warning, missing/malformed schema or config handled gracefully |
| `test_run_ledger.py` | `validate_manifest` (required fields incl. `harness`, status/harness enums, phase/verification structure), `validate_file`, `load_manifests`, `summarize` (by_status, by_harness, phases, QA) and `format_summary` plus the `validate` / `summarize` CLI paths |
| `test_mdu_46_apply_now_tooling.py` | optional top-level `model` field (absent/valid/empty/non-string, `REQUIRED_FIELDS` parity pin, `by_model` + `format_summary` + CLI) and doc pins for `docs/brief-checklist.md` clause ids plus the local upstream draft (filing gate, masked evidence pointer, no submission mechanics) |
| `test_mdu_47_definition_batch.py` | clause pins (16 prompt-file assertions across code-reviewer, grok-review, qa, architect), mirror parity, ordering pins, dirty-tree verify pins, orchestrator model repoint pin, and checklist pins |
| `test_mdu_49_definition_batch.py` | full-clause pins for the six MDU-49 clauses (21 file-level assertions across the 3 orchestrator mirrors, 4 coder bodies, 2 introspector bodies), design-doc blockquote consistency, D5 coder/orchestrator shape parity, D4→D3→D2 cluster and D1/D5/D6 ordering pins, checklist pins, and an `MDU49_TEST_ROOT` override for the mutation matrix |
| `test_mdu_55_introspector_discipline.py` | introspector self-cost discipline pins: the loop-mode reading sub-bullet present exactly once in each mirror and byte-identical across them, its position between the read parent and the manifest bullet, the read parent byte-unchanged, design-doc constant consistency, and the SKILL.md run-timing note (heading once, body verbatim, between `## How to run the helper` and `## Signal kinds`), with an `MDU55_TEST_ROOT` override for the mutation matrix |
| `conftest.py` | Puts `scripts/lib/` on `sys.path` so tests import the modules the same way `scripts/build.sh` does |

## Running

pytest is required (available on this machine via Homebrew):

```bash
pytest --version   # should print pytest 9.x
```

From the repository root:

```bash
python3 -m pytest tests/ -q
```

Run a single file:

```bash
python3 -m pytest tests/test_model_registry.py -q
```

The tests are offline-only: the `--live` paths monkeypatch
`shutil.which` / `subprocess.run` so no `opencode` CLI or network is needed.
All fixtures are created under pytest's `tmp_path`; nothing is committed.

## Notes

- Tests never modify production code. If a test fails, the failure points at
  a bug in `scripts/lib/model_registry.py` or `scripts/lib/validate.py` —
  report it, do not fix it in the test suite.
- Build validation is intentionally hermetic: the repo's real
  `config/model-registry.txt` is only exercised implicitly through
  `validate.py`'s default `DEFAULT_SNAPSHOT`; unit tests use temporary
  snapshots.
