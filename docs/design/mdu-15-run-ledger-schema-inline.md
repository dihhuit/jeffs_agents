# MDU-15 — Cross-CLI run-ledger conformance: inline manifest schema in the orchestrator prompt

Branch: `mdu-15-run-ledger-schema-inline` (both repos). Design doc (this file):
`docs/design/mdu-15-run-ledger-schema-inline.md`.

## 0. Root cause and fix shape

The run-ledger contract lives only in `docs/observability.md` (schema tables, lines 9–48)
and in `scripts/lib/run_ledger.py` (module constants). A headless CLI in a bare scratch
workspace can read neither: the prompt's only pointers are the four ledger bullets
(`prompts/orchestrator.md` lines 162–166) plus "See `docs/observability.md` for the full
schema" (line 168). Result: introspector suggestion `20261014-5` (`manifest_gap`)
recurred for five MDUs, and the 2026-09-16 cross-CLI test caught each CLI improvising a
different dialect (`examples/upgrade-story.md` lines 114–124: opencode
`qa_grade: "manual-smoke-pass"` + missing `title`/timestamps; grok never finalized;
claude `status: "complete"` + `build: "n/a"`).

Fix: inline the full contract (fields, enums, one compact example, lifecycle, exact-value
rules) into both base orchestrator mirrors as one contiguous block; pin it with validator
clauses and pytest contracts so prompt and code cannot drift apart; re-verify on all
three CLIs with a bounded headless conformance task; document the claude permission flag
and the grok finalization outcome in `docs/observability.md`.

**Zero change to `scripts/lib/run_ledger.py`.** The code schema is already correct and
tested; this MDU changes prompts, docs, tests, and adds one eval driver.

## 1. Decisions at a glance

| # | Decision | Verdict |
| --- | --- | --- |
| D1 | Where the schema lives for agents | Inline block in both base mirrors + grokestrator; `run_ledger.py` constants stay authoritative |
| D2 | Normalizations (`complete`, `manual-smoke-pass`, `"n/a"`) | Prompt-side exact-value rules only; validator stays strict, accepts no aliases |
| D3 | Criterion 2 evidence: nested full MDU loop vs bounded task | **Bounded conformance task** (see §7.1) |
| D4 | Grok finalization gap | Built-in probe in the bounded task (commit is the deliverable); A/B re-run if it fails; fix or disclose |
| D5 | Repeatable protocol home | New eval task `evals/tasks/03-ledger-conformance/` (trigger: manual) |
| D6 | Overlay adoption | grokestrator gets the byte-identical generic block; no snippet channel changes |

## 2. The inline block (literal, paste verbatim)

### 2.1 Block text

The following replaces the seven ledger bullets in both mirrors (§3). It is generic —
zero personal names — so the identical bytes also go into the overlay grokestrator.

````markdown
- **Maintain a run ledger per MDU** — the full manifest contract is inline here; no external doc is needed. Lifecycle: when the MDU starts, write `runs/<mdu-id>/manifest.json` with `status: "in_progress"` and `started_at`; as each phase completes, append one `phases[]` entry; before the commit phase, finalize every remaining field and validate; then commit the manifest with the code.
  - Required fields: `mdu_id`, `title`, `status`, `harness`, `started_at`, `completed_at` (ISO-8601), `phases`, `fix_iterations`, `autonomy_level`, `verification`, `artifacts`, `summary`.
  - `phases[]` entry fields: `phase`, `agent`, `model_tier`, `outcome`, `notes` (errors, retries, sign-offs).
  - `verification` fields: `build` (bool), `tests_passed` (int), `tests_total` (int), `qa_grade`, `ci_green` (bool or null).
  - Allowed values: `status`: `in_progress|completed|failed|escalated`; `harness`: `opencode|grok|claude` (the CLI you are running in); `phases[].phase`: `design|implement|review|test|deploy|validate|commit`; `phases[].model_tier`: `free|budget|mid|premium|top-tier`; `phases[].outcome`: `pass|fail|pending`; `verification.qa_grade`: `PASS|FAIL|null`.
  - Field rules: the final status is `completed`, never `complete`. `qa_grade` is exactly `PASS` or `FAIL`, never free text like `manual-smoke-pass`. `build` is a JSON boolean, never `"n/a"`. `fix_iterations` (int) counts every fix/redo cycle in any phase — never `0` when phase notes describe a fix cycle. `autonomy_level` is an int 0–4. `artifacts` is an array of relative paths. `summary` is one free-text line.
  - Compact example (copy the shape, not the values):
    ```json
    {
      "mdu_id": "mdu-XX", "title": "Short title", "status": "completed", "harness": "opencode",
      "started_at": "2026-01-01T10:00:00Z", "completed_at": "2026-01-01T10:25:00Z",
      "phases": [
        {"phase": "design", "agent": "architect", "model_tier": "premium", "outcome": "pass", "notes": "docs/design/mdu-XX.md"},
        {"phase": "implement", "agent": "just-code", "model_tier": "budget", "outcome": "pass", "notes": "one fix cycle after review reject"},
        {"phase": "commit", "agent": "orchestrator", "model_tier": "budget", "outcome": "pass", "notes": "branch mdu-XX"}
      ],
      "fix_iterations": 1, "autonomy_level": 3,
      "verification": {"build": true, "tests_passed": 12, "tests_total": 12, "qa_grade": "PASS", "ci_green": true},
      "artifacts": ["docs/design/mdu-XX.md"], "summary": "One line."
    }
    ```
  - Finalize order: set final `status` (usually `completed`), `completed_at`, `verification`, `fix_iterations`, `autonomy_level`, `artifacts`, `summary` → run `python3 scripts/lib/run_ledger.py validate runs/<mdu-id>/manifest.json` (must exit 0; in a workspace without that script, still conform to this contract) → include the manifest path in your final summary → commit the manifest with the code.
````

The example is deliberately valid: every `REQUIRED_FIELDS` key present, all enums legal,
`fix_iterations: 1` with the implement `notes` naming the fix cycle (teaches the mdu-31
defect rule by example), `Z`-suffixed timestamps that `datetime.fromisoformat` accepts
(`run_ledger.py` line 102 handles the `Z` → `+00:00` rewrite).

### 2.2 Size budget

The seven removed bullets ≈ 960 chars; the block ≈ 2.6 KB → net ≈ +1.7 KB on a ~10.9 KB
prompt (~16%). Each line is single-purpose so a future trim can drop the example bullet
alone. The block is the last item of the responsibilities list; nothing else moves.

### 2.3 Rejected alternative: schema as a Skill

A `run-ledger` Agent Skill would be deployed user-level (~/.config/opencode/skills,
~/.grok/skills) and readable from any workspace — but per the overlay deploy rules,
skills are **not deployed to Claude** ("Deployed to OpenCode, Grok, and (skills excepted)
Claude locations", overlay `AGENTS.md`), so claude would still be schema-less; and skill
loading is on-demand/harness-dependent, while the backlog text mandates inlining into the
prompt. Inline is deterministic for all three CLIs; rejected.

## 3. Placement and mirror-identity rule

### 3.1 `prompts/orchestrator.md` (base)

Replace lines 162–168 (the seven bullets from "- **Maintain a run ledger per MDU:**" through "- See `docs/observability.md` for the full schema; `examples/runs/` has sample manifests.") with the §2.1 block. The block becomes the last item of the "Your responsibilities" list, immediately before the blank line + "Hard constraints:".

### 3.2 `grok/agents/orchestrator.md` (base mirror)

Replace lines 154–160 (the same seven bullets, currently byte-identical to the
canonical's) with the §2.1 block, same position (last item before "Hard constraints:").

### 3.3 Byte-identity rule

The span from the literal anchor `- **Maintain a run ledger per MDU**` up to (exclusive)
the next `\nHard constraints:` must be **byte-identical** across:
`prompts/orchestrator.md`, `grok/agents/orchestrator.md`, and the overlay
`opencode_agents/grok/agents/grokestrator.md`. The anchor must occur exactly once per
file. Enforced by pytest (§6), not just by the substring parity validator.

### 3.4 Grokestrator (overlay)

`opencode_agents/grok/agents/grokestrator.md` currently has **no** ledger text at all
(verified: no "run ledger" string in the file). Insert the §2.1 block verbatim between
line 97 (the agent-improvements/introspector bullet, last item of its responsibilities
list) and line 99 ("Hard constraints:"). This is a live source file (grokestrator exists
only in the overlay; it is not a dead same-name root copy). The block is generic, so no
snippet channel is involved and no personal names are introduced.

## 4. Normalization rules — where they live

| Drift (2026-09-16) | Canonical encoding | Enforcement |
| --- | --- | --- |
| `qa_grade: "manual-smoke-pass"` | exactly `"PASS"` or `"FAIL"` (or `null` pre-QA) | Prompt "Field rules" line + `QA_GRADES` enum |
| `status: "complete"` | final state is `completed` | Prompt "Field rules" line + `STATUSES` enum |
| `build: "n/a"` | JSON boolean `true`/`false` | Prompt "Field rules" line + `validate_manifest` bool check |
| missing `title`/timestamps | all `REQUIRED_FIELDS` always present | Prompt "Required fields" line + validator |

**The validator accepts no aliases — deliberately.** `run_ledger.py` stays strict because
strictness is what caught all three dialects in the first place
(`examples/upgrade-story.md` line 116: "The validator found all three manifests
deviated"); alias acceptance would legitimize drift and corrupt `summarize`'s
`by_status`/`qa` buckets. All normalization is prompt-side exact-value text (the
"Field rules" bullet), which is the actual fix for the improvising CLI. The
`complete`/`completed` alias question is answered **no** for the same reason.

`examples/runs/` needs no normalization: all 9 manifests already use `status:
"completed"`, `qa_grade: "PASS"`, boolean `build`, bool-or-null `ci_green`, and integer
`fix_iterations` (checked by grep across every manifest; `mdu-07` even models
`fix_iterations: 2`). They stay as-is.

## 5. Validator clauses (`scripts/lib/validate.py`)

Append six tuples to `ROLE_KEYWORDS["orchestrator"]` (after the existing nine — all nine
stay intact, untouched, in their current order):

```python
    "orchestrator": [
        ("mdu",),
        ("delegat",),
        ("140000",),
        ("continue this session across mdus",),
        ("cache miss",),
        ("compact and continue",),
        ("repositories the user owns",),
        ("per-action human approval",),
        ("never file upstream",),
        ("run ledger",),                # MDU-15: ledger section headline exists
        ("run_ledger.py validate",),     # MDU-15: the validate-before-commit gate exists
        ("qa_grade",),                   # MDU-15: verification field contract exists
        ("model_tier",),                # MDU-15: phases[] tier contract exists
        ("fix_iterations",),            # MDU-15: fix-counting rule exists
        ("in_progress",),                # MDU-15: start-state value exists
    ],
```

What each tuple catches (parity errors fire when a clause is present in one mirror but
not the other; since the block is byte-identical, each clause binds both):

- `("run ledger",)` — deletion or rewording of the whole ledger headline (the anchor).
- `("run_ledger.py validate",)` — loss of the validate step, the gate that makes drift visible instead of latent.
- `("qa_grade",)` — loss of the `verification` field contract (covers the `manual-smoke-pass` rule).
- `("model_tier",)` — loss of the `phases[]` structure contract.
- `("fix_iterations",)` — loss of the fix-counting rule (the mdu-31 defect: `0` while notes described fixes).
- `("in_progress",)` — loss of the start-state value in the lifecycle sentence.

`("completed",)` is deliberately **not** added: it matches `completed_at` and incidental
prose, so it would pass even with the exact-value rule deleted. That rule is pinned by
the pytest phrase list instead (§6.1). No existing test pins an exact orchestrator clause
count (checked `test_mdu_23_session_hygiene.py` line 109 and
`test_mdu_31_repo_ownership.py` lines 235–239: membership/subset only), so appending is
safe for the current 303-test suite.

## 6. Test plan

House style: `test_mdu_31_repo_ownership.py` (base) — path constants, lowercase phrase
matching, raw-text span slicing for byte-identity, clause-tuple membership, binding
check; overlay module imports the base module via `GENERIC_DIR`/sibling auto-detect with
module-level skip when the base is absent (built-output tests FAIL on stale `build/`,
they do not skip).

### 6.1 Base — `tests/test_mdu_15_run_ledger_inline.py` (new, written by test-agent)

Constants:

```python
ORCHESTRATOR_PROMPT = REPO_ROOT / "prompts" / "orchestrator.md"
ORCHESTRATOR_GROK = REPO_ROOT / "grok" / "agents" / "orchestrator.md"
BLOCK_ANCHOR = "- **Maintain a run ledger per MDU"
BLOCK_END = "\nHard constraints:"
OLD_DOC_POINTER = "for the full schema"          # the removed bullet's tail
OLD_PHASE_BULLET = "Append a phase entry (`phase`, `agent`, `model_tier`, `outcome`, `notes`) to `phases` as each phase completes."

MDU_15_PHRASES = [  # lowercase; file contents are lowercased before matching
    "maintain a run ledger per mdu",
    "no external doc is needed",
    "the final status is `completed`, never `complete`",
    "never free text like `manual-smoke-pass`",
    'never `"n/a"`',
    "never `0` when phase notes describe a fix cycle",
    "the cli you are running in",
    "must exit 0",
    "copy the shape, not the values",
    "in_progress|completed|failed|escalated",
    "run_ledger.py validate",
    "finalize every remaining field",
]

PRE_EXISTING_ORCHESTRATOR_CLAUSES = [  # the nine that must stay (MDU-23/28/31 era)
    ("mdu",), ("delegat",), ("140000",),
    ("continue this session across mdus",), ("cache miss",), ("compact and continue",),
    ("repositories the user owns",), ("per-action human approval",), ("never file upstream",),
]
MDU_15_ORCHESTRATOR_CLAUSES = [
    ("run ledger",), ("run_ledger.py validate",), ("qa_grade",),
    ("model_tier",), ("fix_iterations",), ("in_progress",),
]
```

Tests (each asserts against BOTH base mirrors unless noted):

1. `test_phrase_list_is_the_agreed_contract` — `len(MDU_15_PHRASES) == 12`, all lowercase; guards the guard (imported by the overlay module).
2. `test_ledger_block_present_in_both_mirrors` — anchor present; all 12 phrases present.
3. `test_ledger_block_byte_identical_across_mirrors` — `_block_span()` (raw text, anchor → `BLOCK_END`) equal across both mirrors, non-empty, and `text.count(BLOCK_ANCHOR) == 1` per file.
4. `test_old_bullets_and_doc_pointer_removed` — `OLD_DOC_POINTER`, `OLD_PHASE_BULLET`, and `"observability.md"` absent from the whole file (the block must not need any external lookup; the current prompt references the doc only in the removed bullet).
5. `test_inline_required_fields_line_matches_run_ledger` — regex the `Required fields:` line; `re.findall(r"`([^`]+)`", line)` as a set `== set(run_ledger.REQUIRED_FIELDS)`.
6. `test_inline_verification_fields_line_matches_run_ledger` — regex the `` `verification` fields: `` line; backtick tokens after the label `== set(run_ledger.REQUIRED_VERIFICATION_FIELDS)`.
7. `test_inline_phases_entry_fields_pinned` — the `` `phases[]` entry fields: `` line's backtick tokens `== {"phase", "agent", "model_tier", "outcome", "notes"}` (no module constant exists; `_validate_phase` hardcodes them — the example test below cross-checks transitively).
8. `test_inline_enums_match_run_ledger_constants` — regex `r"`([a-z_.[\]]+)`: `([^`]+)`"` over the `Allowed values:` line; require exactly the six keys `status`, `harness`, `phases[].phase`, `phases[].model_tier`, `phases[].outcome`, `verification.qa_grade`; split each value on `|` and assert set equality against `run_ledger.STATUSES`, `HARNESSES`, `PHASES`, `MODEL_TIERS`, `OUTCOMES`, and for `qa_grade`: `{"PASS", "FAIL"} == {v for v in run_ledger.QA_GRADES if v is not None}` plus the literal alternative `"null"` representing `None`. This is the no-drift fuse: change a code enum without the prompt → red.
9. `test_inline_example_is_valid_manifest` — extract the ```json fence inside the block span (`r"```json\s*\n(.*?)\n\s*```"` with `re.DOTALL`; indented JSON is fine — whitespace between tokens is insignificant to `json.loads`); `json.loads` it; `run_ledger.validate_manifest(example) == []`; and every `REQUIRED_FIELDS` key is present (explicit assert for a better failure message than "missing required field").
10. `test_role_keywords_orchestrator_locks_ledger_clauses` — the 9 pre-existing + 6 new clauses present as literal tuples in `validate.ROLE_KEYWORDS["orchestrator"]`; each new clause has at least one alternative occurring (case-insensitively) in BOTH mirror texts (mdu-31-style binding check — a clause that would track nothing fails).
11. `test_docs_observability_names_the_inline_location` — `docs/observability.md` contains `prompts/orchestrator.md` (the canonical-location note, §8) and still contains `run_ledger.py`.

### 6.2 Overlay — `opencode_agents/tests/test_mdu_15_overlay_run_ledger_inline.py` (new)

Imports `test_mdu_15_run_ledger_inline` as `base` from the sibling base repo
(`GENERIC_DIR` env or `../open-agent-definitions`, module-level `pytest.skip` if absent —
same `_base_repo()` pattern as `test_mdu_31_overlay_repo_ownership.py`).

1. `test_grokestrator_source_carries_ledger_block` — anchor + all 12 `base.MDU_15_PHRASES` in `grok/agents/grokestrator.md`; single anchor occurrence.
2. `test_grokestrator_block_byte_identical_to_base` — `_block_span(grokestrator) == _block_span(base prompts/orchestrator.md)` (the overlay adopts the identical generic block).
3. `test_grokestrator_block_carries_no_personal_names` — the block span contains none of `["dihhuit", "jeffs_agents", "opencode_agents"]` (public-private boundary; the block is generic by construction — this pins it).
4. `test_built_grokestrator_carries_ledger_block` — `build/grok/agents/grokestrator.md` exists (FAIL with "run ./build.sh" on stale build, house convention) and carries the anchor + phrases (global snippets append at EOF and cannot disturb the mid-file block).
5. `test_built_orchestrators_carry_ledger_block` — `build/prompts/orchestrator.md` **and** `build/grok/agents/orchestrator.md` both carry the anchor (the block flowed from the base through the overlay build; the base validator ran inside `./build.sh`).
6. `test_built_claude_orchestrator_inherits_block` — `build/claude/agents/orchestrator.md` (generated, never hand-edited) carries the anchor — proves the Claude generator flows the block through unchanged.

## 7. Cross-CLI verification protocol (criteria 2 and 3)

### 7.1 Adjudication: bounded conformance task, not a nested MDU loop

**Recommendation: the bounded task.** The 2026-09-16 run already proved the full nested
loop mechanics work on all three CLIs — grok completed design → implement → test → review
→ QA with PASS grades, and all three recorded `harness` correctly
(`examples/upgrade-story.md` lines 96–108). The unproven variables are exactly two:
schema conformance without doc access, and final-phase landing (commit + manifest
finalization). A bounded task isolates those variables; a nested loop buries them under
loop dynamics that are already green.

Cost discipline: a full nested loop is 3 × 10–30 min of subagent runtime (30–90 min) at
3–6× the token burn — the orchestrator's own rules cap a subagent at ~10 min and warn
that bigger loops signal bad decomposition. The bounded task is ≤ 8 min per CLI.

| Option | Wall clock | Token cost | Evidence for criteria 2+3 |
| --- | --- | --- | --- |
| Bounded conformance task (chosen) | ~30–35 min total (3 × ≤8 min runs + seeding/grading), + ≤10 min grok probe if needed | ~3 single-agent runs | Direct: manifest validates, harness correct, status completed, commit present |
| Full nested MDU loop (rejected) | 30–90 min | 3 full design→commit loops (dozens of subagent calls) | Same checks, plus re-proving loop mechanics already proven 2026-09-16 |

The bounded task still exercises criterion 3's finalization path directly: the git
commit is the **deliverable**, not a trailing phase after the "real" work.

### 7.2 The golden task (literal `TASK.md`, identical for all three CLIs)

````markdown
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
````

### 7.3 Seeding and invocation

Scratch workspaces under `/tmp/opencode/mdu-15/` (pre-approved external dir), one per CLI.
Per-CLI seed (idempotent — recreate on every run):

```bash
SCRATCH=/tmp/opencode/mdu-15/<cli>            # opencode | grok | claude
rm -rf "$SCRATCH" && mkdir -p "$SCRATCH/scripts/lib"
cp <base-repo>/scripts/lib/run_ledger.py "$SCRATCH/scripts/lib/"
cp TASK.md "$SCRATCH/"
git -C "$SCRATCH" init -q
```

Headless invocations (sequential, not parallel, to avoid rate-limit cross-talk; always
`timeout`-prefixed; on timeout, report — do not raise and retry):

| CLI | Command (from `$SCRATCH`) |
| --- | --- |
| opencode | `timeout 480 opencode run --agent orchestrator "$(cat TASK.md)"` |
| grok | `timeout 480 grok --agent orchestrator -p "$(cat TASK.md)"` |
| claude | `timeout 480 claude --agent orchestrator -p "$(cat TASK.md)" --dangerously-skip-permissions` |

The claude flag is mandatory: without it, headless claude denies Write to its own
scratch dir and reports BLOCKED (2026-09-16 finding, `examples/upgrade-story.md` lines
109–112). Scratch access otherwise: opencode via the base `opencode.json`
`permission.external_directory` `/tmp/**` (verified present, lines 6–13); grok via
`~/.grok/config.toml` global `/tmp` rw. Precondition: the overlay `./build.sh &&
./deploy.sh --force` has installed the new prompts (deploy phase, §11) — the deployed
orchestrator on this machine is the overlay build (base prompt + appended global
snippets; the mid-file block survives the append).

### 7.4 Grading (per CLI; grade with the BASE repo's validator, not the seeded copy — a CLI could have edited its workspace copy)

1. `runs/mdu-ledger-check/manifest.json` exists.
2. `python3 <base-repo>/scripts/lib/run_ledger.py validate <scratch>/runs/mdu-ledger-check/manifest.json` exits 0.
3. `manifest["harness"] == "<cli>"`.
4. `manifest["status"] == "completed"`.
5. `git -C <scratch> log --oneline` shows ≥ 1 commit.
6. `manifest["phases"]` contains an entry with `"phase": "commit"` (ledger finalization landed, not just the git commit).

Echo `PASS/FAIL ledger-conformance/<cli>` per check set; a CLI absent from PATH echoes
`SKIP ledger-conformance/<cli>` and does not fail the driver (but QA must confirm three
PASS lines on this machine for criterion 2).

### 7.5 Grok session-finalization probe (criterion 3)

Built in: step 4 of the task makes the commit the deliverable, so a dropped commit is
detected by check 5/6 above. If grok's run again exits 0 without the commit (or without
the `commit` phase entry), run the A/B probe (each `timeout 300`, ≤ 5 min):

- **(a) baseline** — the §7.2 task unchanged (commit is the last numbered instruction, followed only by the summary reply).
- **(b) reordered** — swap steps 4/5 so a trivial action follows the commit: step 4 commit, step 5 "write one line to `final-report.txt` naming the manifest validation exit code."

Adjudication:
- (a) drops the commit, (b) keeps it → root cause: the grok workflow runner cuts the session's **final action**. Fix prompt-side is not possible for a generic base (the commit phase is last by design in the loop), so disclose in `docs/observability.md` per the mdu-30 "disclosed, not fixable from config" pattern, with the probe evidence. Criterion 3 is satisfied as "root-caused and documented". Upstream filing requires an explicit user instruction (repo-ownership rule) — propose it, do not do it.
- Both variants drop the commit → deeper finalization gap: record evidence (exit code, transcript tail, `git log` empty), disclose in `docs/observability.md`, and escalate to the user with the root-cause summary rather than burning retries.
- The commit lands → gap was the schema-lookup failure all along (the CLI improvised and stalled); the inline block is the fix; document the resolution in `docs/observability.md`.

### 7.6 Eval task home (repeatable protocol)

New `evals/tasks/03-ledger-conformance/` following the `01-repo-health` house style
(POSIX sh, no bashisms, PASS/FAIL lines, exit 0 only when green):

- `task.md` — frontmatter: `name: ledger-conformance`, `trigger: manual` (needs the CLIs on PATH + deployed agents; not CI-able), `timeout_minutes: 45`, `expect:` the §7.4 PASS lines. Body: goal, the §7.2 task text by reference, the §7.3 seed/invocation table, the §7.4 checks, and the §7.5 probe.
- `driver.sh [opencode|grok|claude|all]` — seeds, invokes, grades. Single-CLI mode keeps every invocation inside the ~10-minute subagent rule (the orchestrator's qa phase runs it three times, once per CLI); `all` runs sequentially for manual use. Skip (with `[info]`) CLIs absent from PATH; never silently skip a present CLI.

## 8. `docs/observability.md` changes (criterion 4)

1. **Canonical-location note** — insert after the "The schema is enforced in code…" paragraph (currently line 46–48):

   > Since MDU-15 the same contract is also inlined in both orchestrator mirrors
   > (`prompts/orchestrator.md` and `grok/agents/orchestrator.md`) so any CLI or subagent
   > can conform with zero external lookup — the 2026-09-16 cross-CLI test showed a bare
   > scratch workspace cannot read this doc. `run_ledger.py`'s module constants remain
   > the single source of truth; `tests/test_mdu_15_run_ledger_inline.py` cross-checks
   > the prompt's fields, enums, and example against them. To change the schema, edit
   > `run_ledger.py`, both mirrors, and this doc in the same commit — the tests fail
   > otherwise.

2. **New "## Cross-CLI headless notes"** section (after the CLI section, ~line 81):
   the three headless invocations from §7.3; **claude requires
   `--dangerously-skip-permissions` or Write is denied and the run reports BLOCKED**;
   the 2026-09-16 dialect findings (one line each: opencode `manual-smoke-pass` +
   missing `title`/timestamps; grok `in_progress` + null verification; claude `complete`
   + `build: "n/a"`); the 2026-10-21 re-test outcome (filled by the qa phase — three
   PASS lines + grok probe result); pointer to `evals/tasks/03-ledger-conformance/`.
3. **Doc hygiene** — delete the stray duplicate `## Heavy upgrade path: OTel GenAI /
   Langfuse` heading at line 82 (an empty duplicate of the line-97 heading; it breaks
   the section order).
4. One-line edit in `examples/runs/README.md`: "See `docs/observability.md` for the full
   schema and lifecycle" → "…, or the inline contract in the orchestrator prompt."

## 9. Overlay scope

**Changes in `opencode_agents/`:**
- `grok/agents/grokestrator.md` — insert the §2.1 block (§3.4). Byte-identical to the base block; zero personal names.
- `tests/test_mdu_15_overlay_run_ledger_inline.py` — new (§6.2).
- `build/` regenerated by `./build.sh` (tracked; commit per standard flow) — inherits the base's new mirrors automatically.
- `./deploy.sh --force` during the deploy phase installs the new prompts to all three CLIs (deploy the user's daily agents from the overlay, never the base alone).

**Explicitly NOT changed:**
- `opencode_agents/prompts/orchestrator.md` — **dead same-name root copy**; the build adds root prompts only when the name is absent from the base, and the base provides `orchestrator`. Editing it changes nothing.
- `overlays/manifest.json`, `overlays/*.txt` — the block is generic; no personal snippet content exists to add.
- `opencode.json`, root `skills/`, `build/claude/` (generated, never hand-edited).
- No base file receives any overlay content: the public base keeps zero personal names (pinned by §6.1 test 4-analog in the overlay suite and the existing mdu-31 boundary tests).

Cross-repo order (workspace rule): base edits → base tests green → base `./build.sh`
green → then overlay edits → overlay `./build.sh` (re-runs the base validator inside) →
commit each repo separately (two commits, two pushes).

## 10. Risks and rollback

| Risk | Likelihood/impact | Mitigation | Rollback |
| --- | --- | --- | --- |
| Prompt bloat: +~1.7 KB per turn on both mirrors + the generated Claude subagent | Certain, bounded (~16%) | Single-purpose lines; example is one bullet; future trim can drop it alone | `git revert` the single base commit; the block is one contiguous span, tests localize it |
| Mirror drift (byte-identity broken by a later edit) | Medium | §6.1 test 3 byte-identity + single-anchor count; parity validator clauses gate the build too | Fix-forward: tests print the span diff; re-paste §2.1 |
| Validator clause false-pass (substring matches stray prose) | Low | All six clauses bind to the byte-identical block; pytest binding check requires presence in BOTH mirrors; strong pins live in the pytest phrase list, not the substring validator | Adjust the clause tuple + its test in one commit |
| Claude generator mangling the JSON fence | Very low | `gen_claude_agents.py` does no string templating (verified: no `format()`/`Template` use); body flows through unchanged; claude validator needs only frontmatter | None needed; §6.2 test 6 watches the built output |
| Overlay snippet mechanics disturbing the block | Very low | Global snippets `append_file` at EOF only; grokestrator is root-source live, not a replaced full-file | §6.2 tests 4–6 watch the built output |
| Someone edits the dead overlay root `prompts/orchestrator.md` | Medium (human error) | §9 names it dead; §6.2 test 5 asserts the BUILT artifact carries the block, so a dead-copy edit shows up as a missing block only if the base lost it | Restore from base mirror |
| Grok finalization gap is harness-level and stays broken | Medium | §7.5 A/B probe root-causes it; criterion 3 is satisfiable via documented disclosure (mdu-30 pattern); upstream filing only on explicit user instruction | Documentation is the deliverable; no code rollback |
| Eval driver silently skipping coverage | Low | Driver echoes `SKIP` lines for absent CLIs; QA must confirm three PASS lines; single-CLI mode prevents the >10-min subagent violation | Run `driver.sh <cli>` per CLI and inspect output |
| Stale `build/` making overlay tests fail confusingly | Low | House convention: built-output tests FAIL with "run ./build.sh", never skip | Run `./build.sh` |

## 11. Phase plan

Every phase produces a `phases[]` entry in this MDU's own manifest — this MDU dogfoods
the new inline block, including a truthful `fix_iterations`. Deploy runs AFTER review
and the last fix cycle. Tests are written by test-agent, never just-code; just-code
never edits test files.

| # | Phase | Agent / tier | Content |
| --- | --- | --- | --- |
| 1 | design | `architect` (premium) | This doc |
| 2 | implement | `just-code` (budget) | Base first: §2.1 block into both mirrors; §5 clauses into `validate.py`; §8 doc edits; `evals/tasks/03-ledger-conformance/`. Then overlay: grokestrator block (§3.4). No test files |
| 3 | review | `code-reviewer` (mid) | Sign-off gate: byte-identity, clause binding, personal-name boundary, driver correctness |
| 4 | test | `test-agent` (budget) | §6.1 base file + §6.2 overlay file; run both suites (base 303 → ~314; overlay 63 → ~69); fix cycles: contract gaps → test-agent fixes tests, implementation gaps → just-code fixes non-test files |
| 5 | deploy | `devops` (mid) | Base: `python3 -m pytest tests/ -q` + `./build.sh` green. Overlay: `./build.sh` + `./deploy.sh --force` (installs new prompts to all three CLIs). Runs only after review sign-off and the last fix cycle |
| 6 | validate | `qa` (mid) | Run `evals/tasks/03-ledger-conformance/driver.sh` once per CLI (three ≤10-min invocations); confirm three PASS lines; run the §7.5 grok probe if check 5/6 fails; route any resulting `docs/observability.md` findings-fill through `just-code` (one micro fix cycle + affected-test rerun + review-lite if docs change) |
| 7 | introspect | `introspector` (loop mode) | Pass mdu-15 id, harness, cwd, `runs/mdu-15/manifest.json` |
| 8 | commit | `orchestrator` (free) | Base commit + push (include `FEATURE_BACKLOG.md` MDU-15 status update); then overlay commit + push (build/ output included). Two commits, two pushes |

Budget: ~50–70 min subagent runtime total, each invocation ≤ 10 min; ~1 fix iteration
expected (review nits or test contract gaps). The qa phase's per-CLI invocations are
process-wait dominated (≤ 8 min CLI run each), inside the rule.

## 12. Out of scope / follow-ups

- No `run_ledger.py` change of any kind (no alias acceptance, no new constants). If a
  `PHASE_FIELDS` module constant is ever wanted, that is a separate MDU.
- No grokestrator parity entry in the base `GROK_MIRRORS` (grokestrator is overlay-only;
  the base validator never sees it — overlay pytest covers it).
- Grok upstream harness bug filing (if the probe shows a runner cutoff): user-decision,
  not an MDU step.
- `mdu-lifecycle` / `git-autonomy` skills could later reference the inline block; not
  needed for conformance.

## Post-implementation notes

**Phase-6 routing correction.** Phase 6 assigned the conformance driver to `qa`. In the
deployed harness that is not executable: the `qa` agent's shell permission is
deny-by-default with a narrow inspection allowlist, so it cannot run an arbitrary
script. The driver must be executed by `devops` (unrestricted shell) or the
orchestrator, and QA grades the produced artifacts. QA *can* run a command behind a
`timeout` prefix (the `timeout *` allowlist entry), which is how the grok leg was
executed from a QA subagent. This is a harness-permission fact, not a defect in the
deliverable.

**The opencode `docs/` artifact.** The opencode CLI wrote
`docs/design/mdu-ledger-check.md` into its scratch workspace while running the task.
The seed contains only `scripts/lib/run_ledger.py` and the extracted task text, so the
CLI could not have read the schema from an external document; the conformance claim is
unaffected. The claude leg additionally requires `--dangerously-skip-permissions`.
