# Evals

Golden evaluation harness for the agent **definitions** themselves. Nothing
else in the repo evaluates the prompts/definitions — a prompt change can
silently regress the team. This scaffold delivers the task format, a
pure-Python runner, one executable smoke eval, a results artifact, and
documented paths for agent-driven evals and CI wiring.

## One-command usage

```sh
# Enumerate available tasks with their frontmatter
python3 scripts/lib/run_evals.py list

# Execute a task's driver and write a result manifest
python3 scripts/lib/run_evals.py run evals/tasks/01-repo-health

# Summarize all result manifests as a compact table
python3 scripts/lib/run_evals.py summary evals/results/
```

`run` exits 0 on pass, 1 on fail — so it can gate CI directly. Results land
in `evals/results/<task>-<ts>.json` (gitignored, see below).

## Task format

Each task is a directory `evals/tasks/<name>/` containing:

- `task.md` — YAML frontmatter + markdown body (required).
- `driver.sh` — executable gate (optional; tasks without a driver fail with
  a clear note until a driver is written).

### Frontmatter fields

| Field            | Type            | Required | Meaning                                              |
|------------------|-----------------|----------|------------------------------------------------------|
| `name`           | string          | yes      | Task identifier (also used in result filenames).     |
| `description`    | string          | yes      | One-line summary shown by `list`.                    |
| `trigger`        | `manual`\|`ci`  | yes      | How the task is meant to be run.                     |
| `timeout_minutes`| int             | yes      | Hard timeout enforced on the driver.                 |
| `expect`         | array of string | yes      | Artifact-relative paths or invariants the task must satisfy. |

### Body contract

The markdown body documents the task for humans and future agent graders:

- `## Goal` — what the task verifies and why.
- `## Acceptance criteria` — checkable statements the driver (or an
  agent-driven grader) must satisfy for a pass.

### Driver contract

The runner executes `driver.sh` with cwd = task dir and a timeout:

```sh
timeout <timeout_minutes>m bash driver.sh
```

- Exit 0 → **pass**; non-zero → **fail**; timeout (exit 124) → **fail**
  with a "timed out" note.
- The driver should echo `PASS`/`FAIL` lines per gate and a final verdict
  line; the runner surfaces those lines in its output.
- Keep drivers POSIX-sh simple and deterministic — no LLM cost.

## Runner design

`scripts/lib/run_evals.py` (no third-party dependencies; the YAML
frontmatter is parsed with a small built-in subset parser):

- `parse_task(task_dir)` — read `task.md`, return frontmatter + body.
- `run_task(task, results_dir)` — run the driver via
  `subprocess.run([...], capture_output=True)` (no `shell=True`), interpret
  the exit code, write the result manifest, return it.
- `summarize_results(results_dir)` / `format_summary_table(results)` —
  aggregate `evals/results/*.json` into the compact table.

Result manifests mirror the `run_ledger.py` conventions (`status`,
`started_at`, `completed_at`, `phases` with `phase: "eval"` + `outcome` +
`notes`, and a simplified `verification` with `tests_passed`/`tests_total`),
so the same summarize logic can aggregate them if pointed at
`evals/results/`. `pytest` counts are parsed from the driver output when
present.

## Agent-driven golden tasks (next step)

The smoke eval (`01-repo-health`) is deterministic and free. The full golden
suite spawns real LLM agents per task and is expensive — that is the next
step. A task becomes agent-driven by replacing/augmenting its `driver.sh`
with a driver that:

1. Creates a scratch workspace (e.g. under `/tmp`) containing the repo.
2. Spawns the agent team: orchestrator → just-code → test-agent.
3. Grades the result against the task's `## Acceptance criteria` plus a QA
   pass, then echoes `PASS`/`FAIL` and exits accordingly — so the same
   `run`/`summary` pipeline works unchanged.

### CI wiring

The smoke evals are CI-gated today. `.github/workflows/ci.yml` is the single
source of truth for "what does main need to pass?" — **gate 4 is committed and
active** (ci.yml, ~lines 80–83):

```yaml
- name: gate 4 — smoke evals (01-repo-health + 02-registry-alignment; doubles as harness wiring check)
  run: |
      python3 scripts/lib/run_evals.py run evals/tasks/01-repo-health && \
      python3 scripts/lib/run_evals.py run evals/tasks/02-registry-alignment
```

Both eval tasks run in CI on **every push to `main` and every PR**, and an eval
failure fails the job (no `continue-on-error`). The agent-driven tasks stay out
of CI (LLM cost) and run on demand or in a scheduled, labeled workflow.

## Results

- Manifests land in `evals/results/<task>-<ts>.json` and are gitignored
  (`evals/results/` in `.gitignore`) — they are run artifacts, not sources.
- `python3 scripts/lib/run_evals.py summary evals/results/` prints the
  compact table. The manifest schema mirrors run_ledger's conventions
  (`status`, `started_at`, `completed_at`, `phases`, `verification`), so the
  same summarize logic applies; note that `run_ledger.py summarize` globs
  `*/manifest.json`, so pointing it at `evals/results/` currently reports
  zero manifests until the results are laid out per-directory.