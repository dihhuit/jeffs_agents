# Tests for model-registry validation (MDU-01)

This suite covers the offline/live model registry validation added in
`scripts/lib/model_registry.py` and its integration in
`scripts/lib/validate.py` (the `--live-models` flag and model-ref check).

## Files

| File | What it covers |
| --- | --- |
| `test_model_registry.py` | `load_registry`, `find_model_refs`, `check_models`, `check_live`, and the `model_registry.py` CLI (`--check`, `--snapshot`, `--live`) |
| `test_validate_integration.py` | `validate_model_refs`, `print_live_drift`, and `validate.main` with `--live-models` |
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