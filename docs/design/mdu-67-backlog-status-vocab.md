# MDU-67 — Backlog status vocabulary

One definition clause (suggestion `20261114-1`). mdu-66 wrote a `FEATURE_BACKLOG.md` status word the audit rejects (`Stopped`). `tests/test_mdu_45_grok_review_registry.py` `test_backlog_no_entry_remains_unresolved` accepts only `Done` or `Superseded`, plus an admitted Open (heading ends with `(queue head)`, or the Status text contains `queued`; at most 3 open). A second implement pass changed the word to `Done`. No prompt names the rule. The clause below is the byte source of truth (same text as `agent-improvements.md` line 1001). Do not paraphrase it.

No model id is assigned or changed. The live-probe rule is vacuous. Paths are repo-relative. Overlay sibling = `../opencode_agents/` (`$OVERLAY`). Workspace root, when a name is required, is `$WORKSPACE`.

## 0. Surveyed files

Reads (line spans are what was opened, not a claim that every other line was read):

| File | Span | Why |
| --- | --- | --- |
| agent-improvements.md | 992–1002 | suggestion text, byte source |
| prompts/just-code.md | 1–38 | Hard constraints + successor |
| grok/agents/just-code.md | 1–38 | same |
| grok/agents/just-code-mid.md | 1–38 | same |
| grok/agents/just-code-pro.md | 1–36 | same |
| $OVERLAY grok/agents/grok-just-code.md | all (23) | condensed carrier; rebuild is the last line |
| $OVERLAY grok/agents/grok-just-code-mid.md | all (21) | same |
| $OVERLAY grok/agents/grok-just-code-pro.md | all (21) | same |
| docs/design/mdu-63-definition-guards-batch.md | 1–220, 240–499 | carrier table, fence, pi, pins, commits |
| tests/test_mdu_63_guards.py | 90–269 | `JUST_CODE_CARRIERS`, adjacency |
| $OVERLAY tests/test_mdu_63_overlay.py | 1–250 | overlay pin shape |
| tests/test_mdu_45_grok_review_registry.py | 280–351 | status audit (do not edit) |
| tests/test_mdu_66_window_stop.py | 1–107 | backlog-row pin shape |
| tests/test_mdu_56_pi_port.py | 240–283 | Gate C golden match; count 23 stays |
| FEATURE_BACKLOG.md | 1–25, 600–644 | row shape; no MDU-67 yet |
| opencode.json | just-code rows | three OpenCode agents, one prompt file |
| $OVERLAY opencode.json | 1–40 | grok-just-code trio also uses `prompts/just-code.md` |
| scripts/build.sh | 1–36 | pi output is `build/pi` only |
| scripts/lib/gen_pi_templates.py | 1–80, 106–185 | body copied verbatim; roster ignores body |
| scripts/lib/validate.py | 20–109, 397–434 | keyword parity, not full-file equality |
| pi/README.md | 50–79 | golden refresh checklist |
| pi/port-config.json | all | audit lexicon; clause hits no term |
| tests/fixtures/pi_golden/prompts/just-code.md | 50–69 | successor after the rebuild bullet |
| $OVERLAY scripts/build.sh | 1–117 | root grok profiles copied only if the name is absent |
| $OVERLAY scripts/lib/common.sh | 108–119, stage_base | snippet append is a leading newline + cat; base layer is `build/` |
| $OVERLAY overlays/manifest.json | 1–13 | global snippets; no just-code agent snippet |
| $OVERLAY overlays/token-frugal.txt | 1–6 | appended after the file, not between bullets |
| $OVERLAY tests/test_mdu_54_overlay_grok_clause_parity.py | 160–209 | D5 order is not "last bullet" |
| $OVERLAY tests/test_mdu_54_parity_coverage.py | 120–176 | exclusion rows |

Grep or directory listing only (not full reads): rebuild-bullet hits in both repos including `build/` and the pi golden; `20261114-1`; backlog headings through MDU-66; `prompt_regression.py` gate (pass/fail vs `evals/golden/baseline.json`, not a prompt hash); `.gitignore` (`build/` ignored on the base); overlay `prompts/` (only `grok-plan.md`); overlay `grok/agents/` listing; `overlays/prompts/` and `overlays/grok/agents/` (mdu-code, grok-mdu-code, qa, thought-leadership-coach).

`secret_scan.py` was not re-read. Standing rule from the brief: no absolute path lexemes in this doc.

## 1. Carriers — 7 in, recommendation kept

No deviation from the seven-carrier recommendation. The new bullet is byte-identical in every row. Bodies around it differ. Do not hand-edit `build/` or `tests/fixtures/pi_golden/`.

| # | Repo | Path | In | Current line after the rebuild bullet | Why |
| --- | --- | --- | --- | --- | --- |
| 1 | base | prompts/just-code.md | in | `- **Token budget**:` (long form: continues "…and implement incrementally…") | OpenCode `just-code`, `just-code-mid`, and `just-code-pro` share this file (`opencode.json`). The overlay OpenCode `grok-just-code` trio also sets `system` to this same file. One edit covers all six OpenCode agents and the Claude copies generated from it. |
| 2 | base | grok/agents/just-code.md | in | `- **Token budget**:` (short form: ends at "subtasks.") | Grok mirror. Not the same body as the prompt. |
| 3 | base | grok/agents/just-code-mid.md | in | blank line, then `Behavior:` | Rebuild bullet is the last Hard-constraint bullet today. |
| 4 | base | grok/agents/just-code-pro.md | in | blank line, then `Behavior:` | Same as mid. |
| 5 | overlay | grok/agents/grok-just-code.md | in | EOF (rebuild bullet is the last line) | Root-added live Grok profile. Does not inherit base bullets. Global snippets are appended only in `build/`. |
| 6 | overlay | grok/agents/grok-just-code-mid.md | in | EOF | Same. |
| 7 | overlay | grok/agents/grok-just-code-pro.md | in | EOF | Same. |

Anchor in every carrier, one full line, already present, do not reword:

```text
- A fix is incomplete until the generated copies are fresh: after editing any source file that has build/generated copies (skills, prompts, grok builds, pi goldens, build/ trees), run the build/gate that regenerates them in the SAME cycle and re-diff the copies against the source before reporting done — a source fix with stale copies will be returned by review.
```

Insertion: the new bullet is the immediate next line after that anchor. No blank line between them. On rows 1 and 2 that puts it between the rebuild bullet and the token-budget bullet (mdu-63 erratum: not "at the tail"). On rows 3–7 the anchor is already the tail, so the new bullet becomes the last Hard-constraint bullet. Do not move the token-budget bullet, the `Behavior:` heading, or any other line.

Existing mdu-63 pins stay green without edits. They require the rebuild bullet to follow the before-reporting-done bullet (base) or the display-integrity bullet (overlay) and to stay inside Hard constraints. They do not require the rebuild bullet to be last, and they do not pin its successor. Do not edit `tests/test_mdu_63_guards.py` or `$OVERLAY tests/test_mdu_63_overlay.py`.

### Out (not carriers)

| Hit | Why out |
| --- | --- |
| overlays/prompts/mdu-code.md, overlays/grok/agents/mdu-code.md, overlays/grok/agents/grok-mdu-code.md | Personal divergent coders. Not just-code mirrors. |
| overlay prompts/ (only grok-plan.md) | No just-code prompt. The grok-just-code OpenCode agents do not use a private prompt file. |
| orchestrator, grokestrator, architect, test-agent, other roles | Suggestion target is just-code. Widening is a new surface. |
| base `build/` | Gitignored. `./build.sh` regenerates it. Never hand-edited. |
| overlay `build/` | Tracked, regenerated by `$OVERLAY ./build.sh`. Commit the regeneration. Never hand-edited. |
| tests/fixtures/pi_golden/ | Snapshot of generator output. Refresh by copy (§5). Never typed by hand. |
| skills/, evals/golden/baseline.json, scripts/lib/validate.py | No edit. Parity is keyword presence; the new bullet removes no keyword. |
| test_backlog_no_entry_remains_unresolved | Do not weaken, retarget, or special-case MDU-67. |

## 2. Clause — one line, no wording drift

Emitted form everywhere is this full line (leading `- `, then the suggestion text). The fence is the authority. Pin constants must match it byte for byte, backticks included.

```text
- When you write a FEATURE_BACKLOG `- **Status:**` line, the resolving word is `Done` or `Superseded` only. `Stopped`, `Stop`, and `Closed` fail `test_backlog_no_entry_remains_unresolved`. A deliberate stop is still `Done`, with the stop reason in the same bullet.
```

## 3. Backlog row

Append one section at the end of `FEATURE_BACKLOG.md` (after MDU-66). Paste this. Exactly one `- **Status:**` line. Heading must not end with `(queue head)` and must not contain `queue head`. The resolving word is `Done`. The parenthetical is the reason, in that same bullet. Do not write `Stopped`, `Stop`, or `Closed` on the status line (the audit fails those only when `Done` / `Superseded` is absent; this row still must not use them).

```text
### MDU-67 · Backlog status vocabulary

- **Why:** Suggestion 20261114-1. A FEATURE_BACKLOG status word outside Done or Superseded fails the backlog audit. The coder prompts did not name the allowed words.
- **Description:** One Hard-constraint bullet, byte-identical to suggestion 20261114-1, immediately after the rebuild-freshness bullet, in the seven just-code carriers in docs/design/mdu-67-backlog-status-vocab.md.
- **Status:** Done — 2026-11-14 (CLI-independent prompt clause so a deliberate non-ship is still Done.)
```

This row is Done, so it does not consume the open-queue budget. Do not add a second status line anywhere in the section.

## 4. Suggestion flip — 20261114-1 only

In `agent-improvements.md`, change only the `20261114-1` checkbox line. Leave evidence, definition change, and apply-now bytes as they are. Do not flip any other id. Do not edit the session-record paragraph that mentions this id.

From:

```text
- [ ] id: 20261114-1 | severity: low | target: just-code | kind: backlog_status_vocab
```

To:

```text
- [x] id: 20261114-1 | severity: low | target: just-code | kind: backlog_status_vocab | **RESOLVED 2026-11-14 (mdu-67)**
```

Add this one note immediately after that entry's apply-now bullet:

```text
  - note (2026-11-14, mdu-67): **RESOLVED** — clause shipped byte-identical to the suggestion in prompts/just-code.md, grok/agents/just-code.md, grok/agents/just-code-mid.md, grok/agents/just-code-pro.md, and overlay grok/agents/grok-just-code.md, grok/agents/grok-just-code-mid.md, grok/agents/grok-just-code-pro.md.
```

## 5. Pi goldens — regenerate, do not hand-edit

Pi sources are base `grok/agents/` only. Rows 2–4 change. Row 1 is not a pi source. Overlay profiles are not pi sources.

`./build.sh` runs `scripts/lib/gen_pi_templates.py` into gitignored `build/pi`. It does not write `tests/fixtures/pi_golden/`. Gate C compares a fresh generation to that snapshot (`tests/test_mdu_56_pi_port.py`).

Refresh, in order (pi/README.md checklist):

1. `./build.sh` (or the generator into a temp dir).
2. Diff `build/pi` against `tests/fixtures/pi_golden/`. Expect exactly three files to differ, each by the one inserted bullet and nothing else: `prompts/just-code.md`, `prompts/just-code-mid.md`, `prompts/just-code-pro.md` under both trees. Roster, `PARITY.md`, and `package.json` stay unchanged. The clause matches no term in `pi/port-config.json` (checked this session), so Gate D adds no row. Do not edit `pi/port-config.json` or `docs/pi-parity.md`. If the diff is anything else, stop.
3. Copy those three generated templates over the same relative paths under `tests/fixtures/pi_golden/`. That copy is the refresh. Do not type the bullet into a golden file. Do not edit any other golden file. Do not change `./build.sh` to auto-copy the fixture in this MDU.
4. File count stays 23. The existing Gate C count assertion is untouched. The new tests must not add a file-count pin (`len(tree) == N` or equivalent).

## 6. Pins

### 6a. Base — `tests/test_mdu_67_backlog_status_vocab.py`

Hermetic reads. Specimen root overridable with `MDU67_TEST_ROOT` for the four base carriers only. Design doc, `FEATURE_BACKLOG.md`, and `agent-improvements.md` always read the real repo, so a carrier mutant does not fail them for the wrong reason.

1. Doc consistency: the §2 fence line and the §3 status line appear as full lines in this design doc.
2. Each of the four base carriers contains the §2 line as a full line exactly once.
3. Adjacency: that line is the immediate next line after the rebuild anchor (no blank between). Successor of the new line stays the current successor from §1 (token-budget line on rows 1–2; a blank line then `Behavior:` on rows 3–4).
4. Backlog: one heading that starts with `### MDU-67`, no `queue head` in the heading, exactly one status line, and that line equals the §3 status line.
5. Suggestion: the §4 checked id line is present, the unchecked id line is absent, and the §4 note is present. Do not assert any other id.
6. Census, not a file count: under `prompts/` and `grok/agents/`, the §2 line appears only in the four base carriers.

One mutation, in `/tmp`, never the working tree. Copy the four base carriers into a temp tree that keeps repo-relative paths. Delete the §2 line from `prompts/just-code.md` only. Run:

```bash
MDU67_TEST_ROOT=/tmp/mdu67-mut timeout 120 python3 -m pytest tests/test_mdu_67_backlog_status_vocab.py -q
```

Expect non-zero. The presence or adjacency case is the failure. Restore nothing in the worktree (the copy is the only edit). Do not add M2–Mn.

### 6b. Overlay — `$OVERLAY tests/test_mdu_67_overlay.py`

Require `$OVERLAY ./build.sh` first for build pins. Presence in build copies is count == 1 of the full line, not byte-equality with the source: `append_file` writes a newline and then the global snippets at EOF, so the two bullets stay adjacent and the file tail differs.

1. Each of rows 5–7 contains the §2 line once, immediately after the rebuild anchor. On the source files that line is last.
2. The emitted line matches base `grok/agents/just-code.md`, `just-code-mid.md`, and `just-code-pro.md` respectively (same bytes, same `- ` lead).
3. Built copies, explicit paths, adjacency preserved (rebuild line, then the §2 line):
   - `build/prompts/just-code.md`
   - `build/grok/agents/just-code.md`
   - `build/grok/agents/just-code-mid.md`
   - `build/grok/agents/just-code-pro.md`
   - `build/grok/agents/grok-just-code.md`
   - `build/grok/agents/grok-just-code-mid.md`
   - `build/grok/agents/grok-just-code-pro.md`
   - `build/claude/agents/just-code.md`
   - `build/claude/agents/just-code-mid.md`
   - `build/claude/agents/just-code-pro.md`
   - `build/claude/agents/grok-just-code.md`
   - `build/claude/agents/grok-just-code-mid.md`
   - `build/claude/agents/grok-just-code-pro.md`
4. Negative, not a file count: the §2 line is absent from `grok/agents/grokestrator.md`, `overlays/prompts/mdu-code.md`, `overlays/grok/agents/mdu-code.md`, and `overlays/grok/agents/grok-mdu-code.md`.

Claude files are generated from `prompts/just-code.md` (all six agents point at that file). Do not hand-edit them.

## 7. Gates (ordered)

Prompt edit is additive. `prompt_regression.py gate` compares case pass/fail to the baseline. It must exit 0. If it fails, fix or revert the prompt. Do not run `baseline`, do not pass `--update`, and do not edit `evals/golden/baseline.json`.

```bash
cd <base repo>
timeout 300 python3 -m pytest tests/ -q
./build.sh
# §5 golden copy of the three templates, then:
timeout 120 python3 -m pytest tests/test_mdu_56_pi_port.py -q
timeout 60 python3 scripts/lib/prompt_regression.py gate
# mutation §6a in /tmp only
timeout 60 python3 scripts/lib/secret_scan.py --staged

cd ../opencode_agents
./build.sh
timeout 300 python3 -m pytest tests/ -q
```

`./build.sh` has no timeout wrapper in the snippet above because the workspace rule caps a retry, not the first run: if a build exceeds a few minutes, stop and report. Do not raise a timeout and rerun. `runs/` is gitignored. Do not assign session memory or a run manifest to implement; the orchestrator owns those.

## 8. Deploy

Both builds are required before deploy. After QA PASS, from `$OVERLAY`:

```bash
./deploy.sh
./deploy.sh --force
```

Dry-run first, then `--force`. This installs local OpenCode, Grok, and Claude CLIs. It is not an application production deploy. No model-id change, so no live model probe.

Installed-copy check (QA, count 1 of the clause's distinctive fragment `test_backlog_no_entry_remains_unresolved`): the deployed Grok profiles for the seven carriers, the deployed OpenCode prompt `prompts/just-code.md`, and one generated Claude just-code agent. A miss is FAIL.

## 9. Commits

Two repos, two commits, base first. Explicit paths only. Never `git add -A` in the overlay. Owned remotes; no PR.

**Base** — message `feat(mdu-67): pin backlog status words to Done or Superseded`

- prompts/just-code.md
- grok/agents/just-code.md
- grok/agents/just-code-mid.md
- grok/agents/just-code-pro.md
- tests/test_mdu_67_backlog_status_vocab.py
- tests/fixtures/pi_golden/prompts/just-code.md
- tests/fixtures/pi_golden/prompts/just-code-mid.md
- tests/fixtures/pi_golden/prompts/just-code-pro.md
- FEATURE_BACKLOG.md
- agent-improvements.md
- docs/design/mdu-67-backlog-status-vocab.md

Not in the commit: `build/` (gitignored), `runs/`, `evals/golden/baseline.json`.

**Overlay** — message `feat(mdu-67): carry the backlog status clause into grok-just-code`

- grok/agents/grok-just-code.md
- grok/agents/grok-just-code-mid.md
- grok/agents/grok-just-code-pro.md
- tests/test_mdu_67_overlay.py
- the thirteen `build/` paths listed in §6b (regenerated; do not stage any other `build/` dirt)

Push each repo after its commit. Base push before the overlay build, so `$OVERLAY ./build.sh` reads the updated base `build/` (it re-runs the base build from the sibling).

Who edits what: just-code inserts the clause, the backlog section, and the suggestion flip, runs both builds, and copies the three golden templates from generator output. just-code does not author pin tests and does not type into a golden file. test-agent writes the two pin files and runs the one mutation in `/tmp`. Review does not rewrite the clause. This design doc is already written; implement does not restyle it.

## 10. Acceptance criteria

1. `grep -F -x -f` (or the pin's full-line count) finds the §2 line exactly once in each of the seven source carriers, and the previous line is the rebuild anchor.
2. Rows 1–2: the line after the new bullet is still that file's token-budget bullet. Rows 3–4: blank line then `Behavior:`. Rows 5–7: the new bullet is the last source line.
3. `grep -F -x` of the §3 status line in `FEATURE_BACKLOG.md` returns one hit. The MDU-67 heading does not contain `queue head`. `python3 -m pytest tests/test_mdu_45_grok_review_registry.py::test_backlog_no_entry_remains_unresolved -q` is green and that test file has no diff.
4. `grep -n 'id: 20261114-1' agent-improvements.md` shows one `[x]` line and the §4 note, and no remaining `- [ ] id: 20261114-1`. No other id's checkbox changes (`git diff -U0 agent-improvements.md`).
5. `tests/test_mdu_67_backlog_status_vocab.py` green. The §6a mutation exits non-zero. No assertion of the form "N files".
6. After `$OVERLAY ./build.sh`, `tests/test_mdu_67_overlay.py` green, including the thirteen build paths.
7. `timeout 120 python3 -m pytest tests/test_mdu_56_pi_port.py -q` green. Golden diff against `build/pi` is empty. Only the three named golden templates differ from HEAD, each by one inserted line.
8. Base `timeout 300 python3 -m pytest tests/ -q` green and `./build.sh` exit 0. Overlay `./build.sh` exit 0 and overlay `timeout 300 python3 -m pytest tests/ -q` green.
9. `timeout 60 python3 scripts/lib/prompt_regression.py gate` exit 0. `git diff -- evals/golden/baseline.json` empty.
10. `timeout 60 python3 scripts/lib/secret_scan.py --staged` exit 0 on the base commit.
11. QA PASS. `$OVERLAY ./deploy.sh` dry-run, then `./deploy.sh --force`. Installed copies match §8. Two commits, two pushes, base first, file lists as §9.

## 11. Implement brief

Files: the §9 lists. Do not touch orchestrator, grokestrator, mdu-code, grok-mdu-code, `validate.py`, `prompt_regression.py`, `evals/golden/baseline.json`, `tests/test_mdu_45_grok_review_registry.py`, `tests/test_mdu_63_guards.py`, `$OVERLAY tests/test_mdu_63_overlay.py`, or any other suggestion id.

Bullet, one line, every carrier, immediately after the line that begins `A fix is incomplete until the generated copies are fresh`:

```text
- When you write a FEATURE_BACKLOG `- **Status:**` line, the resolving word is `Done` or `Superseded` only. `Stopped`, `Stop`, and `Closed` fail `test_backlog_no_entry_remains_unresolved`. A deliberate stop is still `Done`, with the stop reason in the same bullet.
```

Backlog status line, alone, under `### MDU-67 · Backlog status vocabulary` (not a queue head):

```text
- **Status:** Done — 2026-11-14 (CLI-independent prompt clause so a deliberate non-ship is still Done.)
```

Commands: §7, then the §6a mutation, then §9 commits, then §8 deploy only after QA PASS. Apply-now for this backlog edit: status word is `Done` or `Superseded`, never `Stopped`; put the reason after the date on that same bullet. If a source with generated copies changes, run the build, re-diff the copies, and report the build exit code before reporting done. Do not refresh the prompt-regression baseline to force a green gate.
