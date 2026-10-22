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

**Gate 5 — prompt regression gate** (MDU-09) sits directly after gate 4. It runs
`python3 scripts/lib/prompt_regression.py gate` (golden ordered traces vs the
committed baseline) plus `check-config` (offline promptfoo config validation)
on **every push to `main`**; on a `pull_request` it runs only when the PR changed
anything under `prompts/`, `grok/agents/`, `evals/`, or `scripts/lib/`, and it
prints an explicit `SKIP prompt-regression-gate (...)` line instead of skipping
silently. Gates 1–4 stay unconditional — the filter lives on the step, not on the
workflow. The gate fails **closed**: a missing or malformed
`evals/golden/baseline.json` makes `gate` exit 2 and the job fails. The protocol
that produces a green gate is documented in
[Prompt change protocol](#prompt-change-protocol) below.

## Results

- Manifests land in `evals/results/<task>-<ts>.json` and are gitignored
  (`evals/results/` in `.gitignore`) — they are run artifacts, not sources.
- `python3 scripts/lib/run_evals.py summary evals/results/` prints the
  compact table. The manifest schema mirrors run_ledger's conventions
  (`status`, `started_at`, `completed_at`, `phases`, `verification`), so the
  same summarize logic applies; note that `run_ledger.py summarize` globs
  `*/manifest.json`, so pointing it at `evals/results/` currently reports
  zero manifests until the results are laid out per-directory.

## Prompt change protocol

Editing a prompt is a behavior change to every agent that reads it, so it is
gated exactly like code. Snapshot → edit → snapshot → diff. The commands are
run from the base repo root.

1. **Before editing** anything under `prompts/` or `grok/agents/`, snapshot the
   clean tree:

   ```sh
   timeout 120 python3 scripts/lib/prompt_regression.py snapshot --out /tmp/opencode/mdu-09/before.json
   ```

   Forgot to snapshot first? `git stash` the edit, snapshot, `git stash pop`.

2. **Edit the prompt.**

3. **Snapshot after** — same command with the after path:

   ```sh
   timeout 120 python3 scripts/lib/prompt_regression.py snapshot --out /tmp/opencode/mdu-09/after.json
   ```

   `snapshot` exits 1 when any case fails, but the snapshot is still written —
   that is expected mid-protocol and gives you the evidence for `diff`.

4. **Diff** before against after:

   ```sh
   timeout 120 python3 scripts/lib/prompt_regression.py diff \
     --before /tmp/opencode/mdu-09/before.json \
     --after  /tmp/opencode/mdu-09/after.json
   ```

5. **Interpret exit codes:** `0` → clean, proceed through the normal MDU loop.
   `1` → ≥1 golden case regressed (pass→fail, or a case deleted): **the prompt
   edit is rejected** — revert the offending hunk or fix the regression, then
   repeat steps 3–4 until clean. Never delete or weaken the failing case
   instead. `2` → operational failure: do not proceed; investigate before any
   further gate run.

6. **Intentional behavior change** that a case encodes (e.g. a deliberate
   reordering): update the case in `evals/golden/cases.json` *first*, re-run
   steps 1–4 so both snapshots use the updated case, and only after the MDU is
   QA-validated refresh the record with

   ```sh
   timeout 60 python3 scripts/lib/prompt_regression.py baseline --update
   ```

   committing cases + baseline together.

7. **Pre-commit / CI:** the same judgment is replayed by
   `prompt_regression.py gate` (the orchestrator clause) and CI gate 5 against
   the committed baseline.

8. **Commit-time (this repo):** commits that touch `prompts/` or `grok/agents/`
   must pass the gate — see the orchestrator clause; it runs alongside the
   secret gate.

### Authoring rules for golden cases

A golden case is an **ordered trace**, not a set of standalone assertions: the
markers must appear in the recorded order in the target file. Presence alone
does not satisfy a case, and reordering two clauses *is* a regression.

- Markers must be **stable anchors** — clause headings, exact commands, file
  paths, literal keywords. Never volatile prose that a copy edit would reword
  (that turns every wording tweak into a false regression).
- Use **2–4 markers per trace**. Fewer does not pin the behavior; more makes
  the case brittle without adding signal.
- A `forbidden` marker must not be a substring of the negated phrasing of the
  rule it forbids — otherwise the correct "never do X" sentence trips it.

### Files

- `evals/golden/cases.json` — the golden cases (case id, target file,
  description, ordered `trace`, optional `forbidden` markers). Committed;
  shared by the gate, `snapshot`, and `diff`.
- `evals/golden/baseline.json` — the committed record of which cases passed,
  plus a git rev. Written only by `baseline --update`, after a QA-validated,
  intentional prompt change. Refuses to overwrite an existing baseline without
  `--update`; the first creation needs no flag.
- `evals/tasks/04-prompt-golden-cases/` — the harness task that wraps the gate
  (`task.md` + `driver.sh`). Run it directly or through the harness:

  ```sh
  bash evals/tasks/04-prompt-golden-cases/driver.sh
  python3 scripts/lib/run_evals.py run evals/tasks/04-prompt-golden-cases
  ```

  Set `GOLDEN_ROOT=<path>` to point the driver at an arbitrary tree (e.g. a
  scratch copy of the repo with a deliberately reordered prompt). Before
  gating, the driver verifies the tree's `evals/golden/cases.json` and
  `evals/golden/baseline.json` are byte-identical to this repo's trusted copies;
  the gate script always comes from this repo. Default is this repo.
