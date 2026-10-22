# MDU-09 · Prompt regression gate — design

Status: proposed · Date: 2026-10-21 · Author: architect
Tree verified against: branch `mdu-09-prompt-regression-gate` (base `b7bd321`, overlay `6959b91`). All quoted marker strings and line numbers were read from this tree.

## Context and problem statement

Prompt edits in this repo are behavioral changes with no measurement. The eval harness (MDU-08) can run tasks, but nothing compares *before vs after* a prompt edit, nothing is committed as an expected state, and nothing rejects a prompt change that regresses behavior. `evals/README.md` even states the gap: "a prompt change can silently regress the team". `evals/results/` is gitignored, so no run artifact can serve as a CI comparison anchor. Today's only prompt guard is `validate.py`'s `ROLE_KEYWORDS` parity check — presence-only, case-insensitive, and only between `prompts/<stem>.md` and its `GROK_MIRRORS`. Presence is not enough: two clauses can be present but reordered, weakened, or nested inside the wrong parent step.

The substrate that exists and is reused as-is: `scripts/lib/run_evals.py` (`list` / `run` / `summary`; exit 0 pass / 1 fail; drivers run as `timeout <n>m bash driver.sh` with cwd = task dir), the `run_ledger.py` manifest conventions, `secret_scan.py`'s exit-code contract (0 clean / 1 findings / 2 operational, `--json`), `evals/tasks/01..03`, and `.github/workflows/ci.yml` gates 1–4.

## Scope / non-goals

**Scope:** ordered-trace golden cases over prompt/mirror files, a committed baseline, a gate script, one new eval task, the documented prompt change protocol, a promptfoo config + offline validator, a CI gate, the orchestrator clause in all three mirrors, the overlay re-exec wrapper.

**Non-goals:**
- No LLM-driven golden suite. All checks are deterministic, free, offline (backlog AC + workspace rule). Task `03-ledger-conformance` stays the only agent-driven task and is *not* bound into promptfoo.
- No PyYAML / third-party runtime deps. Stdlib only; YAML parsed with hand-rolled subset parsers (house rule).
- No promptfoo installation in CI. CI stays fast and offline; promptfoo-live is opt-in and local.
- No behavioral grading of *meaning* — the gate checks structural order of markers, not semantics.
- No change to `run_evals.py`'s CLI or manifest schema.
- Grok-mirror *ordering* is not golden-checked (see risks); mirrors keep presence-parity via `ROLE_KEYWORDS`.

---

## D1 — Golden case = ordered trace of markers over one target file

**Statement.** A golden case is a JSON object: one `target` file (repo-relative), an ordered `trace` list of exact substrings that must all appear in the target in that relative order, and an optional `forbidden` list of substrings that must not appear anywhere. All cases live in one committed file `evals/golden/cases.json`:

```json
{
  "version": 1,
  "cases": [
    {
      "id": "orchestrator-commit-step-secret-gate-order",
      "target": "prompts/orchestrator.md",
      "description": "secret gate markers appear in commit-step order",
      "trace": [
        "Secret gate (before every commit)",
        "timeout 60 python3 scripts/lib/secret_scan.py --staged",
        "never print full secrets"
      ],
      "forbidden": []
    }
  ]
}
```

**Semantics (exact, implemented in `evaluate_case`):** read `<root>/<target>` (missing file → case fails, reason `missing target`). Scan left to right: for each marker in trace order, `text.find(marker, pos)`; a marker not found after the previous match's end → fail `out of order or missing: <marker>`. Any `forbidden` substring found → fail `forbidden present: <marker>`. Matching is case-sensitive exact substring (per-file markers; the base and grok mirrors phrase things differently — e.g. base `prompts/orchestrator.md` line 100 has `never print full secrets`, grok mirror line 102 has `Never print full secrets` — so cases are written per target). `forbidden` defaults to `[]`.

**Rationale.** Presence-only checks cannot catch reordering — the introspector mandate. The trace is a subsequence check, which catches: deletion (missing marker), reordering (find fails), relocation into the wrong section (order breaks), and weakening via forbidden markers. JSON because the runner, ledger, and secret scanner all use stdlib `json`; a nested YAML case file would exceed the house subset parsers.

**Alternatives rejected.** (a) Presence-only keyword lists — already covered by `ROLE_KEYWORDS`, cannot catch order. (b) Full-file golden copies + diff — brittle against legitimate additions (every unrelated prompt edit would be a "regression"). (c) Regex per case — more power, more authoring cost, no current need.

**Artifact.** `evals/golden/cases.json` (committed; **not** under gitignored `evals/results/` — `.gitignore` currently lists `build/`, `__pycache__/`, `/runs/`, `evals/results/` only).

**Seed cases (markers verified against this tree; the implementer commits exactly these five plus any additional ones they derive):**

| id | target | trace (in this order) | verified at |
|---|---|---|---|
| `orchestrator-commit-step-secret-gate-order` | `prompts/orchestrator.md` | `Secret gate (before every commit)` → `timeout 60 python3 scripts/lib/secret_scan.py --staged` → `never print full secrets` | lines 97, 99, 100 |
| `orchestrator-run-ledger-finalize-order` | `prompts/orchestrator.md` | `Maintain a run ledger per MDU` → `run_ledger.py validate runs/<mdu-id>/manifest.json` | lines 167, 188 |
| `orchestrator-responsibilities-loop-order` | `prompts/orchestrator.md` | `Design (via architect` → `Implement (via a just-code variant` → `Commit and push` | lines 89, 90, 96 |
| `orchestrator-mirror-secret-gate-order` | `grok/agents/orchestrator.md` | `Before every commit run the secret gate` → `timeout 60 python3 scripts/lib/secret_scan.py --staged` → `Never print full secrets` | all inside line 102 |
| `just-code-constraints-order` | `prompts/just-code.md` | `NEVER edit test files` → `NEVER commit secrets` → `never print full secrets` | lines 13, 18, 19 |

Authoring rules (documented in the protocol, D5): markers must be *stable anchors* — clause headings, exact commands, file paths — never volatile prose; 2–4 markers per trace; `forbidden` markers must not be substrings of negated phrasing (a `forbidden: ["skip this check silently"]` would false-positive inside the real text `never skip this check silently`, base line 98). `load_cases` rejects any case whose `trace` has fewer than 2 markers as malformed (exit 2). Targets must be repo-relative; absolute paths and `..` segments are refused, and `evaluate_case` resolves the target and refuses any path that escapes the resolved repo root as defense in depth. `trace` and `forbidden` entries must be non-empty strings.

---

## D2 — Golden baseline: committed, refresh-protected

**Statement.** `evals/golden/baseline.json` is the committed record of the passing state:

```json
{
  "version": 1,
  "generated_at": "2026-10-22T00:00:00Z",
  "source_commit": "<git rev-parse --short=12 HEAD at creation>",
  "case_results": { "orchestrator-commit-step-secret-gate-order": "pass", "...": "pass" }
}
```

The source commit is stored as a 12-character short SHA. The secret scanner's
high-entropy rule matches hex runs of 32 or more characters, so a 40-character
full SHA would be a false-positive candidate. A 12-character short SHA is below
that threshold and needs no scanner exemption, avoiding a credential blind spot.

Rules, enforced mechanically by the script (D3):
1. `baseline` **refuses to write if any case fails** (exit 1, nothing written) — a regressed tree can never be baselined.
2. Overwriting an existing baseline requires the explicit `--update` flag. Initial creation (no existing file) needs no flag; within MDU-09 the baseline is created in slice (a) against the pre-clause tree (the D8 clause is a pure addition, so existing traces stay green).
3. Refresh discipline (documented + orchestrator-enforced, not script-enforceable): `baseline --update` is run **only after QA PASS**, for an intentional behavior change, in the same commit as the updated `cases.json`. Never to make a red gate green.

**Rationale.** CI must compare a PR's tree against an expected state; gitignored run artifacts can't anchor that. The refusal rule is the anti-tamper core: the only path to a new baseline is a fully passing tree plus an explicit flag, so a regression cannot slip into the record. The baseline also makes *case deletion* detectable (D3 `gate`: a baseline `case_results` id missing from `cases.json` = regression-by-deletion).

**Alternatives rejected.** (a) Baseline under `evals/results/` — gitignored, unusable by CI. (b) No baseline, gate = "all cases pass" — permits deleting/weakening a failing case to go green; the baseline cross-check closes that. (c) Git notes / tags — extra plumbing, no JSON shape.

**Artifact.** `evals/golden/baseline.json` (committed).

---

## D3 — `scripts/lib/prompt_regression.py`: the gate script

**Statement.** One stdlib-only multi-subcommand script, house style of `run_evals.py` / `run_ledger.py` / `secret_scan.py`. Pure, importable helpers (`load_cases`, `evaluate_case`, `evaluate_all`, `compare_snapshots`, `check_baseline`, `parse_promptfoo_config`) + a thin CLI.

**CLI contract:**

| subcommand | args | exit 0 | exit 1 | exit 2 |
|---|---|---|---|---|
| `cases` | `[--root DIR]` | listed | — | cases.json missing/malformed |
| `snapshot` | `[--root DIR] [--out PATH] [--json]` | all cases pass (snapshot always written) | any case fails (snapshot still written — it is evidence) | cases.json missing/malformed, target unreadable |
| `diff` | `--before P --after P [--json]` | no regression | ≥1 regression | missing/malformed snapshot files |
| `gate` | `[--root DIR] [--json]` | all cases pass AND baseline intact | any case fails, or a baseline id missing from cases.json | missing `cases.json` or `baseline.json`, malformed JSON |
| `baseline` | `[--root DIR] [--update]` | written | refused: ≥1 case fails (nothing written) | git failure, IO error, malformed cases |
| `check-config` | `[--config P] [--live]` | config valid (offline); with `--live`, also promptfoo ran | config findings (see D6) | config missing/unparseable |

`--root` default: the script's own repo root (`Path(__file__).resolve().parents[2]`, same as `validate.py`'s `REPO_ROOT`) — every `<root>/evals/golden/...` and `<root>/<target>` resolves under it. Exit-2 = fail-closed operational failure, mirroring `secret_scan.py` (verified: it returns 2 on operational errors, `return 1 if findings else 0`).

**Comparison semantics.**
- `gate` (CI / orchestrator / pre-commit): evaluate all cases under root; cross-check against `<root>/evals/golden/baseline.json` — every `case_results` id must exist in `cases.json` (deletion = regression), and every `case_results` value must be exactly `"pass"` (a hand-edited non-`pass` value is treated as tampering and exits 2); every case must pass. A passing case absent from the baseline prints `[info] new case not yet baselined: <id>` (allowed).
- `snapshot`→`diff` (pre-change protocol): `diff` validates that both snapshots have the expected shape (`version == 1`, non-empty `case_results` dict) before comparing and exits 2 if either is malformed. It then maps case ids across the two snapshots. **Regression = id with `pass` in before and (`fail` or absent) in after.** Improvements (`fail`→`pass`) and new cases are info lines, never failures.
- Scratch trees: copy the repo to a scratch dir, edit the prompt, `gate --root <scratch>` (copy `baseline.json` in, or use `snapshot`+`diff` which needs no baseline).

**Output format.** Human table for evaluation subcommands (mirrors `format_summary_table`):

```
case                                     result  reason
----                                     ------  ------
orchestrator-commit-step-secret-gate...  pass    3/3 markers in order
just-code-constraints-order              fail    out of order or missing: NEVER commit secrets
PASS prompt-regression-gate (5/5 cases, baseline intact)      ← final line, exit 0
```

The human table prints `case  result  reason` rows (one per case) followed by a final `PASS`/`FAIL` line naming the subcommand, so `run_evals._gate_lines` (`^\s*(PASS|FAIL)\b`) surfaces the overall result. `--json` prints `{"exit_code", "case_results": {...}, "regressions": [...], "notes": [...]}` for machine/agent use.

**Rationale.** One file, subcommands, mirrors the two existing script conventions; exit 0/1/2 matches the secret gate the orchestrator already knows how to interpret; `--root` enables the scratch-tree regression proof without changing `run_evals.py` (which passes no argv to drivers).

**Alternatives rejected.** (a) Separate scripts per concern (`promptfoo_check.py`, `baseline.py`, ...) — more files, more overlay wrappers, no benefit at this size. (b) Subprocess git plumbing inside `diff` to auto-snapshot HEAD — extra machinery; the protocol orders snapshot-before-edit instead (D5), and `git stash` covers the forgot-to-snapshot case procedurally. (c) sqlite/markdown baselines — JSON only, house convention.

**Artifact.** `scripts/lib/prompt_regression.py` (new, ~450 lines stdlib).

---

## D4 — Eval task `evals/tasks/04-prompt-golden-cases/`

**Statement.** `task.md` frontmatter:

```yaml
---
name: prompt-golden-cases
description: verify prompt files keep their golden ordered traces and the committed baseline is intact (GOLDEN_ROOT env points the gate at an arbitrary tree)
trigger: manual
timeout_minutes: 2
expect:
  - "prompt_regression.py gate exit 0 on the current tree"
  - "GOLDEN_ROOT override evaluates an arbitrary tree"
---
```

Body: `## Goal` (ordered traces + baseline tamper-evidence, deterministic and free) and `## Acceptance criteria` (gate exit 0; `PASS prompt-golden-cases` final line; non-zero gate → `FAIL prompt-golden-cases`, driver exits 1). `driver.sh` (POSIX sh, no bashisms, house pattern of task 01/03):

```sh
#!/bin/sh
# Eval driver for task 04-prompt-golden-cases.
# GOLDEN_ROOT (optional) points the gate at an arbitrary tree (scratch copies);
# default is this repo. The gate script always comes from THIS repo (trusted
# grader), the tree under test comes from GOLDEN_ROOT.
set -u
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)"
GATE="$REPO_ROOT/scripts/lib/prompt_regression.py"
ROOT="${GOLDEN_ROOT:-$REPO_ROOT}"

if [ ! -f "$GATE" ]; then
  echo "FAIL prompt-golden-cases (missing gate script: $GATE)"
  exit 1
fi

# Golden cases and baseline must come from the trusted repo, not the tree under test.
for golden_file in evals/golden/cases.json evals/golden/baseline.json; do
  if [ ! -f "$REPO_ROOT/$golden_file" ]; then
    echo "FAIL prompt-golden-cases (trusted golden file missing: $golden_file)"
    exit 1
  fi
  if [ ! -f "$ROOT/$golden_file" ] || ! cmp -s "$ROOT/$golden_file" "$REPO_ROOT/$golden_file"; then
    echo "FAIL prompt-golden-cases (golden files differ from the trusted repo)"
    exit 1
  fi
done

if python3 "$GATE" gate --root "$ROOT"; then
  echo "PASS prompt-golden-cases"
  exit 0
fi
echo "FAIL prompt-golden-cases"
exit 1
```

Arbitrary-tree invocation (env var, because `run_evals.py` runs `timeout 2m bash driver.sh` with no argv):

```sh
GOLDEN_ROOT=/tmp/opencode/mdu-09/scratch python3 scripts/lib/run_evals.py run evals/tasks/04-prompt-golden-cases
```

**Rationale.** `trigger: manual` because CI's gate 5 (D7) calls the script directly — running task 04 in CI would double-run the same check. The task exists for harness parity (run_evals integration + result manifest), for the scratch-tree proof, and as a promptfoo binding target (D6). Grader-from-trusted-repo mirrors task 03, which seeds the base validator into its scratch rather than trusting the scratch's own.

**Alternatives rejected.** (a) `--root` as a driver argument — `run_evals.py` passes no argv; an env var is the only pass-through. (b) `trigger: ci` + joining gate 4's list — redundant with gate 5, adds ~1s for no signal.

**Artifacts.** `evals/tasks/04-prompt-golden-cases/{task.md,driver.sh}` (driver executable).

---

## D5 — Prompt change protocol (the AC-1 deliverable)

**Statement.** A new `## Prompt change protocol` section appended to `evals/README.md` (plus a one-paragraph pointer in its CI wiring section for gate 5). Exact content:

1. **Before editing** any file under `prompts/` or `grok/agents/`, snapshot the clean tree (from the base repo root):
   `timeout 120 python3 scripts/lib/prompt_regression.py snapshot --out /tmp/opencode/mdu-09/before.json`
   Forgot to snapshot first? `git stash` the edit, snapshot, `git stash pop`.
2. **Edit the prompt.**
3. **Snapshot after**: same command with `--out /tmp/opencode/mdu-09/after.json`.
4. **Diff**: `timeout 120 python3 scripts/lib/prompt_regression.py diff --before /tmp/opencode/mdu-09/before.json --after /tmp/opencode/mdu-09/after.json`
5. **Interpret exit codes:** 0 → clean, proceed through the normal MDU loop. 1 → ≥1 golden case regressed (pass→fail or case deleted): **the prompt edit is rejected** — revert the offending hunk or fix the regression, then repeat 3–4 until clean. Never delete or weaken the failing case instead. 2 → operational failure: do not proceed; investigate before any further gate run.
6. **Intentional behavior change** that a case encodes (e.g. deliberate reordering): update the case in `evals/golden/cases.json` *first*, re-run steps 1–4 so both snapshots use the updated case, and only after the MDU is QA-validated refresh the record with `timeout 60 python3 scripts/lib/prompt_regression.py baseline --update`, committing cases + baseline together.
7. **Pre-commit / CI:** the same judgment is replayed by `prompt_regression.py gate` (orchestrator clause, D8) and CI gate 5 (D7) against the committed baseline.
8. **Commit-time (this repo):** commits that touch `prompts/` or `grok/agents/` must pass the gate — see the orchestrator clause; it runs alongside the secret gate.

**Rationale.** The protocol is the lightweight comparison flow the backlog asks for; ordered steps 1→4 make the before-snapshot always available; step 6 is the only sanctioned way to change expectations, and it is QA-gated.

**Alternatives rejected.** (a) Gate-only protocol (skip snapshots) — loses case-level before/after evidence and the ability to distinguish new failures from pre-existing ones. (b) Baseline refresh as part of every green gate run — that is exactly how regressions get baselined away; refresh stays explicit + QA-gated.

**Artifact.** `evals/README.md` (section appended; file exists, lines 1–123 today).

---

## D6 — `evals/promptfoo.yaml` + offline validator (`check-config` subcommand)

**Statement.** A committed promptfoo config binding ≥3 deterministic eval tasks (01, 02, 04 — all free and offline; 03 is agent-driven and deliberately excluded), authored in a **constrained YAML grammar** that both real promptfoo and our subset parser accept:

```yaml
# promptfoo config for the deterministic golden evals (MDU-09).
# Teams wanting the standard tool run, from the repo root:
#   timeout 300 npx -y promptfoo@latest eval -c evals/promptfoo.yaml
prompts:
  - "{{task}}"
providers:
  - "exec: bash promptfoo_driver.sh"
tests:
  - description: "01-repo-health driver passes"
    vars:
      task: evals/tasks/01-repo-health
    assert:
      - type: contains
        value: "PASS repo-health"
  - description: "02-registry-alignment driver passes"
    vars:
      task: evals/tasks/02-registry-alignment
    assert:
      - type: contains
        value: "PASS registry-alignment"
  - description: "04-prompt-golden-cases gate passes"
    vars:
      task: evals/tasks/04-prompt-golden-cases
    assert:
      - type: contains
        value: "PASS prompt-golden-cases"
```

The provider runs with cwd equal to the config's directory (`evals/`), so a
single `exec: bash promptfoo_driver.sh` dispatcher receives the interpolated
`{{task}}` value as `$1` and maps it to `tasks/${task##*/}/driver.sh`. The
`prompts:` stanza must be the literal `"{{task}}"` so promptfoo passes the test's
`vars.task` through to the command; any other value runs the wrong driver or
passes no task at all.

**Offline validator** = `prompt_regression.py check-config` (no `--live` in CI, ever). It parses the file with a small hand-rolled line-oriented parser accepting *only* this grammar (top-level `key:` scalars/lists; `tests:` as a list of flat maps at 4-space indent; nested `assert:` list of flat maps — a ~70-line extension of the `run_evals._parse_frontmatter` subset pattern, explicitly documented to reject any other shape with exit 2). Checks, each printing `PASS`/`FAIL` lines:
1. Required top-level keys present and non-empty: `prompts`, `providers`, `tests`.
2. `tests` has **≥3** entries.
3. Each test: `description` non-empty, `vars.task` names an existing `<root>/evals/tasks/<dir>/` **with a runnable `driver.sh`** (executable bit or `-f`), `assert` is a non-empty list of `{type, value}` with `type` in an allowlist `{contains, equals, icontains}`.
4. With `--live`: if a `promptfoo` binary is on PATH, run `timeout 300 promptfoo eval -c <config>` and report its outcome. Else if `npx` is on PATH, probe first with `timeout 60 npx -y promptfoo@latest --version`; a probe failure prints `SKIP promptfoo-live (reason: promptfoo not acquirable via npx; offline validation only)` and adds **no finding** (the command exits by offline validation only). A probe success runs the eval as usual, and a non-zero eval exit stays a finding (exit 1). If neither CLI is on PATH, print `SKIP promptfoo-live (reason: promptfoo CLI not on PATH; offline validation only)` and continue to exit by the offline findings — never silently skipped, never a hard failure (mirrors task 03's `SKIP ledger-conformance/<cli>` pattern).

**Rationale.** The workspace forbids npm in CI and forbids PyYAML; a constrained grammar keeps the config simultaneously real-promptfoo-loadable and offline-provable. AC-3 is satisfiable without network: config parses, ≥3 tests, each bound to an existing task with a driver, assertions well-formed.

**Alternatives rejected.** (a) `promptfoo_check.py` as a separate script — folded into the gate script to keep one file + one overlay wrapper. (b) Binding task 03 into promptfoo — would make the standard-tool path spawn LLM agents (8-min timeouts, CLI deps): violates the deterministic-and-free rule. (c) Validating the full promptfoo schema offline — impossible without the tool; we validate our binding contract and let `--live` do the rest when available.

**Artifacts.** `evals/promptfoo.yaml` (committed); `check-config` subcommand inside `scripts/lib/prompt_regression.py`.

---

## D7 — CI wiring: `gate 5` in `.github/workflows/ci.yml`

**Statement.** A new named step after gate 4 (which today ends at ci.yml line 83), with a loud path filter — gates 1–4 stay unconditional; only gate 5 is filtered:

```yaml
      - name: gate 5 — prompt regression gate (golden ordered traces vs committed baseline + promptfoo offline check)
        run: |
          set -euo pipefail
          if [ "${{ github.event_name }}" = "pull_request" ]; then
            git fetch --no-tags --depth=1 origin "${{ github.event.pull_request.base.sha }}"
            if ! git diff --name-only "${{ github.event.pull_request.base.sha }}" HEAD -- prompts grok/agents evals scripts/lib | grep -q .; then
              echo "SKIP prompt-regression-gate (no changes under prompts/, grok/agents/, evals/, scripts/lib/)"
              exit 0
            fi
          fi
          python3 scripts/lib/prompt_regression.py gate
          python3 scripts/lib/prompt_regression.py check-config
```

Notes: runs on every push to `main` (no filter) and on PRs touching `prompts/`, `grok/agents/`, `evals/`, or `scripts/lib/`; the SKIP is an explicit printed line, never silent; no new actions, no npm, no network — the "No Docker, no npm. Only actions/checkout and actions/setup-python" header comment stays true; added runtime < 2 s (pure Python substring scans); `gate` missing-baseline exits 2 and fails the job (fail closed). Also update the workflow's header comment block with a `5.` entry describing the gate, keeping the single-source-of-truth comment honest.

**Rationale.** A filtered step satisfies the AC while keeping unrelated PRs fast; hand-rolled `git diff` avoids third-party path-filter actions; `check-config` without `--live` keeps CI offline. The gate failing closed on a missing baseline means a fresh clone without `evals/golden/baseline.json` cannot pass silently — it must be committed (D2).

**Alternatives rejected.** (a) `paths:` at the workflow `on:` level — would make gates 1–4 skippable too, weakening the always-on contract. (b) A second workflow file — the brief pins the gate inside `ci.yml`; also duplicates setup steps. (c) `dorny/paths-filter` — third-party action, violates the header constraint.

**Artifact.** `.github/workflows/ci.yml` (edit, ~15 added lines).

---

## D8 — Orchestrator clause in all three mirrors + `ROLE_KEYWORDS` tuples

**Statement.** One clause, phrased once canonically and twice condensed, all containing the same four parity keywords (case-insensitive substring, per `validate.py._parity_clause_errors`).

**Canonical** — `prompts/orchestrator.md`, inserted as a new bullet **inside step 8, immediately after the secret-gate block** (after current line 101, before `**MODEL SELECTION**`):

> - **Prompt regression gate (commits that touch prompt files):** if the MDU changed anything under `prompts/` or `grok/agents/`, run `timeout 60 python3 scripts/lib/prompt_regression.py gate` before committing. Exit 0 → proceed. Exit 1 (golden-case regression: a case the committed baseline records as passing now fails, or a baselined case was deleted) → **do not commit**; reject the prompt edit — revert the offending hunk or fix the regression, then re-run until clean. Never refresh the baseline to make a red gate green: `evals/golden/baseline.json` is only updated via `timeout 60 python3 scripts/lib/prompt_regression.py baseline --update`, after the change is QA-validated and intentional, committed together with `evals/golden/cases.json`. Exit 2 (operational failure) → do not commit; escalate to the user. Delegation: briefs for prompt-editing MDUs must include the snapshot/diff protocol commands from `evals/README.md` ("Prompt change protocol"). In a workspace without the script, apply that protocol manually. This gate adds to the secret gate and the approval gates; it never replaces or weakens them.

**Grok mirror** — `grok/agents/orchestrator.md`, appended as new sentences at the end of the step-8 paragraph (current line 102), condensed but containing the same keywords.

**Overlay orchestrator** — `opencode_agents/grok/agents/grokestrator.md`, added as a new nested bullet **immediately after the `SECRET GATE — BEFORE EVERY COMMIT` bullet** (current line 84), same condensed content. The overlay orchestrator does **not** inherit the base Grok profile, so it must be patched explicitly (workspace rule).

**Parity tuples** — appended to `ROLE_KEYWORDS["orchestrator"]` in `scripts/lib/validate.py` (currently 17 tuples, lines 67–85):

```python
("prompt regression gate",),
("prompt_regression.py gate",),
("prompt_regression.py baseline",),
("never refresh",),
```

`GROK_MIRRORS["orchestrator"]` already maps to `["orchestrator.md"]`, so `./build.sh` fails if either base mirror loses a keyword. The grokestrator is **not** in `GROK_MIRRORS` (overlay file, invisible to base validation) — its clause is enforced by review + the QA live phase (D9/D11), an accepted limitation (risks).

**Rationale.** The clause must live where the secret gate lives (step 8 = commit gates) so the orchestrator reads it at the same decision point; keyword tuples extend the existing parity mechanism rather than inventing a new one; the three-file rule is the workspace's cross-repo change order.

**Alternatives rejected.** (a) A new step 9 in the loop — renumbers the ledger contract's `phases[].phase` enum (design|implement|review|test|deploy|validate|commit); no. (b) Clause at implement-phase only — the orchestrator accepts implement summaries before QA; a commit-time hard gate is the last line of defense and matches "rejected by the orchestrator". (c) Sentence-exact parity across mirrors — `ROLE_KEYWORDS` deliberately tolerates grok's shorter phrasing; keyword tuples are the established mechanism.

**Artifacts.** `prompts/orchestrator.md`, `grok/agents/orchestrator.md`, `opencode_agents/grok/agents/grokestrator.md` (edits); `scripts/lib/validate.py` (4 tuples).

---

## D9 — Overlay story: thin re-exec wrapper + live command

**Statement.** `opencode_agents/scripts/lib/prompt_regression.py` is a structural copy of the existing `scripts/lib/validate.py` wrapper with the target filename swapped: resolves `$GENERIC_DIR`, else siblings `base_agents` / `open-agent-definitions` / `open_agent_definitions`, finds `<cand>/scripts/lib/prompt_regression.py`, and `os.execv(sys.executable, [sys.executable, base_script, *sys.argv[1:]])`. No forked logic, ever (workspace rule: "Do not fork the validator again" generalizes to all gate scripts). One intentional deviation from `validate.py`: if no base repo is found, the gate wrapper exits **2** (operational / fail-closed), matching the gate's own exit-code contract, whereas `validate.py` exits 1 in the same situation.

Because `os.execv` replaces the process with the **base** script, `__file__` resolves inside the base repo, so the script's default `--root` is the **base tree** — exactly the tree whose prompts the gate protects. The documented live-execution commands, run **from the overlay cwd** by devops/QA (constraint: prove the overlay path actually works):

```sh
cd <workspace>/opencode_agents          # the overlay checkout
timeout 120 python3 scripts/lib/prompt_regression.py gate          # exit 0 expected
timeout 60  python3 scripts/lib/prompt_regression.py check-config  # exit 0; promptfoo SKIP line expected
```

**Rationale.** The introspector `apply_now` mandates a runnable overlay path and a live execution phase; the wrapper pattern is already proven by `validate.py` and costs ~50 lines; evaluating the base tree from the overlay position is the correct semantics (golden cases + baseline live in the base repo).

**Alternatives rejected.** (a) Overlay runs `python3 ../open-agent-definitions/scripts/lib/prompt_regression.py` directly — bypasses the wrapper pattern the previous session mandated; breaks if the sibling is renamed and `GENERIC_DIR` is set. (b) Overlay-merged gate over `build/` — golden cases target source `prompts/` files, not merged output; wrong tree.

**Artifact.** `opencode_agents/scripts/lib/prompt_regression.py` (new wrapper).

---

## D10 — Who executes / who grades (verified against both `opencode.json` registries)

Agent names verified: base registry (28) — `orchestrator, just-code, just-code-mid, just-code-pro, just-code-free, test-agent, test-agent-mid, test-agent-pro, test-agent-free, code-reviewer, code-reviewer-pro, code-reviewer-free, architect, architect-premium, devops, devops-pro, devops-free, qa, qa-pro, qa-free, research, deepseek-research, nemotron-research, deep-research, ui-ux-designer, ui-ux-designer-pro, introspector, inception`. Overlay registry adds (22) — `grok-just-code{,-mid,-pro}, grok-test-agent{,-pro}, grok-code-reviewer{,-pro}, grok-architect{,-premium}, grok-devops{,-pro}, grok-qa{,-pro}, grok-research, grok-deep-research, grok-ui-ux-designer{,-pro}, grokestrator, grok-plan, mdu-code, grok-mdu-code, thought-leadership-coach`. Every name below exists.

| Protocol step | Executes | Grades | Read-only? |
|---|---|---|---|
| This design doc | `architect` | `code-reviewer` (+ orchestrator reads) | architect: docs only, never production code |
| `cases.json` seed cases | `just-code-mid` | `test-agent` (proves order-sensitivity) + `code-reviewer` | code-reviewer: read-only |
| `prompt_regression.py` + `baseline.json` creation | `just-code-mid` | `test-agent` + `code-reviewer` | — |
| Baseline refresh (post-QA, later MDUs) | `just-code` | `qa` (exit 0 + cases/baseline committed together) | — |
| Pre/post snapshots + `diff` (per prompt edit) | `just-code` (the prompt editor) | `orchestrator` (rejects on exit 1) | orchestrator never implements |
| `gate` pre-commit | `orchestrator` (runs it, rejects on exit 1) | `qa` (live, from overlay too) | — |
| Eval task 04 | `just-code` | `qa` (live `run_evals` run) | — |
| `promptfoo.yaml` + `check-config` | `just-code` | `test-agent` (offline findings) + `qa` (`--live` local) | — |
| CI gate 5 wiring | `devops` (after review + last fix cycle) | `code-reviewer` (read-only) + `qa` | — |
| Orchestrator clause, 3 mirrors | `just-code` | `code-reviewer` + automated parity (`./build.sh`) | — |
| Overlay wrapper | `just-code` | `devops` + `qa` (live commands from overlay cwd, D9) | — |
| Manifest finalization | `orchestrator` | `run_ledger.py validate` (exit 0) | — |
| Introspection | `introspector` (loop mode only) | user (review mode is user-invoked only) | introspector: never edits definitions |
| Research touch-ups if any | `research` / `deepseek-research` | `architect` | research family: never writes files |

---

## D11 — Phase order for the implementation MDU (fix-cycle discipline)

Constraint 4: devops runs **after review and after the last fix cycle**; every fix cycle is followed by re-test and re-validate. Constraint 6: the manifest is fully populated **before** the introspector runs.

1. **Design** — `architect` produces this doc; `code-reviewer` grades.
2. **Implement slice (a)** — `just-code-mid`: `prompt_regression.py` (core subcommands), `evals/golden/cases.json` (seed cases, D1), initial `evals/golden/baseline.json` creation (no prior baseline → no `--update` needed), eval task 04.
3. **Review (a)** — `code-reviewer` sign-off (read-only).
4. **Test (a)** — `test-agent`: `tests/test_mdu_09_prompt_regression.py` (functions in D12). Brief asks for summary counts + `--tb=short`, never full logs.
5. **Fix cycles (a)** — each fix (`just-code`) is followed by re-test (`test-agent`) and re-validate (`python3 -m pytest tests/ -q --tb=short` + `./build.sh`), until green. devops is not invoked yet.
6. **Implement slice (b)** — `just-code`: protocol section in `evals/README.md`, `check-config` subcommand + `evals/promptfoo.yaml`, ci.yml gate 5, the D8 clause in all three mirrors, `ROLE_KEYWORDS` tuples, overlay wrapper.
7. **Review (b)** — `code-reviewer` sign-off, including parity via `./build.sh` (gate 1 runs `validate.py`, which now enforces the new tuples).
8. **Test (b)** — `test-agent`: D12 parity/config/CI tests. Fix cycles as in step 5.
9. **Deploy** — `devops`, only now: verifies ci.yml offline (`python3 scripts/lib/prompt_regression.py gate` + `check-config` locally), runs the overlay build (`cd ../opencode_agents && ./build.sh`), and executes the **live documented commands from the overlay cwd** (D9) with `timeout` prefixes, reporting exit codes.
10. **Validate** — `qa`: full protocol walkthrough from the base root (snapshot → edit a scratch copy → diff exit 1 → gate exit 0) and the overlay live commands; grades PASS/FAIL.
11. **Finalize the run manifest fully** — `status: completed`, `completed_at`, `verification` block (`build`, `tests_passed`/`tests_total`, `qa_grade`, `ci_green`), accurate `fix_iterations` (count every cycle from steps 5 and 8). Then `python3 scripts/lib/run_ledger.py validate runs/mdu-09/manifest.json` exit 0. **Before** the introspector.
12. **Introspect** — `introspector` loop mode; writes `agent-improvements.md`; never edits definitions.
13. **Commit** — `orchestrator`: secret gate, then **the new prompt regression gate** — this MDU touches `prompts/orchestrator.md` and `grok/agents/orchestrator.md`, so `prompt_regression.py gate` must run and pass (dogfood; also the AC-2 demonstration in-repo). Push after the standard approvals.

---

## D12 — Acceptance criteria → tests (named functions, counts)

All in `tests/test_mdu_09_prompt_regression.py` (new) plus two additions to `tests/test_validate_parity.py` (existing). Fixtures follow `tests/conftest.py` (scripts/lib on `sys.path`); scratch trees under `/tmp/opencode/mdu-09/pytest-<name>/`.

| AC (backlog) | Proof | Named tests |
|---|---|---|
| 1 — documented protocol | README section exists with exact commands | `test_protocol_documented_in_evals_readme` (asserts `## Prompt change protocol`, `prompt_regression.py snapshot`, `diff --before`, `gate` all present in `evals/README.md`) |
| 2 — regression rejection demonstrated | order-sensitivity + gate behavior + CI presence | `test_evaluate_case_ordered_trace_pass`, `test_evaluate_case_reordered_markers_fail` (copy of a real target with two adjacent markers swapped → fail), `test_evaluate_case_missing_marker_fail`, `test_evaluate_case_forbidden_marker_fail`, `test_gate_clean_tree_exit_0`, `test_gate_scratch_regression_exit_1` (scratch copy, marker deleted), `test_gate_baseline_case_deletion_exit_1`, `test_diff_flags_regression_exit_1`, `test_diff_clean_exit_0`, `test_baseline_refuses_failing_tree_exit_1_and_writes_nothing`, `test_baseline_update_requires_flag`, `test_gate_missing_baseline_exit_2`, `test_ci_gate5_named_with_path_filter` (asserts the step name and the four path roots in ci.yml) |
| 3 — promptfoo valid + ≥3 tasks | offline binding proof + skip behavior | `test_check_config_valid_exit_0`, `test_check_config_binds_at_least_three_tasks`, `test_check_config_each_task_dir_has_driver`, `test_check_config_bad_binding_exit_1` (mutated copy pointing at a nonexistent task), `test_check_config_missing_file_exit_2`, `test_check_config_live_reports_skip_exit_0` (promptfoo absent on PATH → `SKIP promptfoo-live` printed, exit 0) |
| parity (D8) | mirrors keep the clause | `test_orchestrator_prompt_gate_clause_keywords` (parity: both base mirrors contain the four keywords — extends `test_validate_parity.py`), `test_role_keywords_orchestrator_extended` (tuple list assertion) |

Total: ~22 functions (20 new + 2 extended). The grokestrator clause has **no base test** (base CI cannot see the overlay repo) — QA's live phase greps it from the overlay cwd (`grep -c "prompt regression gate" grok/agents/grokestrator.md` → ≥1). Test-agent briefs request summary counts and `--tb=short` only.

---

## Risk table

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Over-strict traces false-positive on harmless rewording | M | blocks legit prompt edits | markers = stable anchors (headings, commands, paths), never prose; case-update path (protocol step 6); forbidden defaults empty |
| Baseline drift / regression baselined away | M | defeats the gate | `baseline` refuses failing trees; `--update` explicit; clause forbids refresh-to-green; cases + baseline committed together; gate fails closed on missing baseline |
| Forbidden-substring false positives (negation pitfall) | M | confusing failures | authoring rule in D1 (markers must not be substrings of "never …" phrasing); seed cases ship `forbidden: []` |
| promptfoo unavailable (by design in CI) | H | standard-tool path unproven live | offline validator proves the binding; `--live` prints `SKIP promptfoo-live` with reason — never silent, never a hard fail; exact `npx -y promptfoo@latest eval -c evals/promptfoo.yaml` documented |
| Base/overlay gate drift | L | inconsistent grading | thin re-exec wrapper, no forked logic; QA live-runs both positions every prompt-editing MDU |
| CI runtime | L | slower PRs | < 2 s added; path-filtered SKIP for unrelated PRs (printed, not silent); no new actions/deps |
| Grok-mirror & grokestrator ordering unenforced | M | mirror reorder slips through | parity keywords enforce presence in base mirrors; grokestrator checked manually by QA; ordering for mirrors is a documented limitation (open question 4) |
| Cases rot when prompts legitimately reworded | M | gate blocks unrelated work | protocol step 6 + QA-gated `baseline --update`; review asks "did the case anchors survive?" on prompt PRs |

## Open questions

1. **promptfoo exec-provider syntax** — the `providers:` stanza's exact exec form is not verifiable offline. Default assumed: a single exec provider invoking the task-04 driver, with per-test `contains` asserts on driver output; the offline validator deliberately does not parse `providers` beyond non-empty presence, so an invalid provider form cannot produce a false PASS offline. If the local `--live` run rejects it, fixing the stanza is a one-line follow-up that does not touch the gate.
2. **Should task 04 join CI gate 4?** Default: no (manual trigger; gate 5 calls the script directly) — avoids double-running the same check.
3. **Marker granularity** — default 2–4 clause-level anchors per trace; finer granularity rejected as brittle.
4. **Automated enforcement for the grokestrator clause** — none in base tests (overlay invisible to base CI). Default: QA live grep + review. A future overlay-side check could parse the wrapper, but the overlay has no pytest suite today; not worth inventing one in this MDU.
5. **Scratch root location** — default `/tmp/opencode/mdu-09/` (mirrors task 03's `/tmp/opencode/mdu-15`), pre-approved for external access per workspace env.
