---
name: ledger-conformance
description: verify each CLI writes a conforming run-ledger manifest headless, with no doc access
trigger: manual
timeout_minutes: 45
expect:
  - "PASS ledger-conformance/opencode"
  - "PASS ledger-conformance/grok"
  - "PASS ledger-conformance/claude"
---

# ledger-conformance

## Goal

Prove that a headless CLI given a bare scratch workspace can produce a run-ledger
manifest that conforms to the contract, with no `docs/` directory and no external
schema lookup — the only source is the inline contract in the orchestrator prompt.
The 2026-09-16 cross-CLI run caught each CLI improvising a different dialect
(opencode `qa_grade: "manual-smoke-pass"` + missing `title`/timestamps, grok
`in_progress` + null verification, claude `complete` + `build: "n/a"`). This task
re-checks all three against the same golden task.

Trigger is `manual`: it needs the three CLIs on `PATH` and the agents deployed, so
it is not CI-able.

## Task text (identical for all three CLIs)

The literal `TASK.md` seeded into each scratch workspace. The driver extracts the
text between the two markers so this doc can carry the protocol around it.

<!-- task-text:start -->
# Task: mdu-ledger-check (one unit of work; the schema source is in your own instructions)

This workspace is a fresh git repo. `scripts/lib/run_ledger.py` is provided; no other
files exist. There is no docs directory and no external schema — conform to the
run-ledger contract written in your instructions.

1. Configure git locally: `user.name "mdu-15-check"`, `user.email "mdu-15-check@example.invalid"`.
2. You have just completed a small design + implement + test loop for this task itself.
   Record it as `runs/mdu-ledger-check/manifest.json` following your run-ledger contract
   exactly: all required fields, one `phases[]` entry per phase you actually performed
   (at minimum design, implement, test, commit), `harness` set to the CLI you are running
   in, final `status: "completed"`, real ISO-8601 timestamps, `verification` filled from
   the self-check in step 3, `fix_iterations` 0 unless you actually fixed something.
3. Validate: `python3 scripts/lib/run_ledger.py validate runs/mdu-ledger-check/manifest.json`
   must exit 0. If you performed no formal tests, `tests_passed`/`tests_total` may be 0/0
   and `qa_grade` "PASS" — the schema allows it.
4. `git add -A && git commit -m "mdu-15 ledger conformance check"` — the commit must land
   before you finish.
5. Reply with a one-line summary that includes the manifest path.
<!-- task-text:end -->

## Seeding and invocation

Scratch workspaces under `/tmp/opencode/mdu-15/`, one per CLI, recreated on every run
(idempotent):

```bash
SCRATCH=/tmp/opencode/mdu-15/<cli>            # opencode | grok | claude
rm -rf "$SCRATCH" && mkdir -p "$SCRATCH/scripts/lib"
cp <base-repo>/scripts/lib/run_ledger.py "$SCRATCH/scripts/lib/"
cp TASK.md "$SCRATCH/"
git -C "$SCRATCH" init -q
```

Headless invocations, from `$SCRATCH`, sequential (never parallel — rate-limit
cross-talk), always `timeout`-prefixed. On timeout, report; do not raise and retry.

| CLI | Command |
| --- | --- |
| opencode | `timeout 480 opencode run --agent orchestrator "$(cat TASK.md)"` |
| grok | `timeout 480 grok --agent orchestrator -p "$(cat TASK.md)"` |
| claude | `timeout 480 claude --agent orchestrator -p "$(cat TASK.md)" --dangerously-skip-permissions` |

The claude flag is mandatory: without it, headless claude denies Write to its own
scratch dir and reports BLOCKED.

Precondition: the overlay `./build.sh && ./deploy.sh --force` has installed the new
prompts. The deployed orchestrator is the overlay build (base prompt + appended global
snippets; the mid-file block survives the append).

## Grading

Grade with the base repo's validator, not the seeded copy — a CLI could have edited
its workspace copy.

1. `runs/mdu-ledger-check/manifest.json` exists.
2. `python3 <base-repo>/scripts/lib/run_ledger.py validate <scratch>/runs/mdu-ledger-check/manifest.json` exits 0.
3. `manifest["harness"]` equals the CLI name.
4. `manifest["status"] == "completed"`.
5. `git -C <scratch> log --oneline` shows at least one commit.
6. `manifest["phases"]` contains an entry with `"phase": "commit"`.

The driver echoes `PASS ledger-conformance/<cli>` or `FAIL ledger-conformance/<cli>`
per check set, and `SKIP ledger-conformance/<cli>` only for a CLI absent from `PATH`.
It exits 0 only when everything it ran is green.

## Grok session-finalization probe

Built in: step 4 of the task makes the commit the deliverable, so a dropped commit is
caught by checks 5 and 6. If grok exits 0 without the commit or without the `commit`
phase entry, run the A/B probe (each `timeout 300`, ≤ 5 min):

- **(a) baseline** — the task text above unchanged: commit is the last numbered
  instruction, followed only by the summary reply.
- **(b) reordered** — swap steps 4 and 5 so a trivial action follows the commit:
  step 4 commit, step 5 "write one line to `final-report.txt` naming the manifest
  validation exit code."

Adjudication:

- (a) drops the commit, (b) keeps it → the grok workflow runner cuts the session's
  final action. Not fixable from a generic base prompt (the commit phase is last by
  design in the loop), so disclose it in `docs/observability.md` with the probe
  evidence. Criterion satisfied as "root-caused and documented". Filing upstream needs
  an explicit user instruction naming the repo and the action — propose, never do it.
- Both variants drop the commit → deeper finalization gap: record exit code, transcript
  tail, and empty `git log`, disclose in `docs/observability.md`, escalate to the user
  instead of burning retries.
- The commit lands → the gap was the schema-lookup failure all along; the inline block
  is the fix. Record the resolution in `docs/observability.md`.
