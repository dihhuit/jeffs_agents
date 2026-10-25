# MDU-34 — Canonical resume-block format (emit-strict, read-permissive)

Backlog source: `FEATURE_BACKLOG.md` lines 289-305. Predecessors: MDU-14 (mirror
parity), MDU-15 (inline-schema precedent), MDU-23/26/28 (current gate wording).

## Surveyed files

- `FEATURE_BACKLOG.md` (280-319) — the MDU-34 spec and acceptance criteria.
- `prompts/orchestrator.md` (10-37, grep) — base mirror; gate span + emission paragraph at line 31.
- `grok/agents/orchestrator.md` (16-43) — base mirror; same emission paragraph at line 37; gate span verified content-identical to `prompts/orchestrator.md`.
- `../opencode_agents/grok/agents/grokestrator.md` (16-43) — third mirror; same paragraph at line 37; gate span content-identical.
- `scripts/lib/run_ledger.py` — validator conventions to copy (argparse, exit codes, `[ok]/[fail]` output, module-level schema constants, pure `validate_*` function).
- `tests/test_mdu_28_resume_detect.py` — the recognition-clause seed test; gate span byte-identity across all three mirrors is ALREADY enforced here (anchor → `Do not ask again this session.`).
- `tests/test_mdu_15_run_ledger_inline.py` — inline-schema-in-mirror precedent: constants cross-check + fence extraction + ROLE_KEYWORDS clause pinning.
- `scripts/lib/validate.py` (55-119) — `ROLE_KEYWORDS["orchestrator"]`; where new clauses land.
- `evals/golden/cases.json` — golden eval traces target other sections (secret gate, run ledger, prompt-regression); the emission paragraph is unpinned. Safe to replace.
- `tests/conftest.py`, `scripts/build.sh` (grep) — import path convention; build.sh runs `validate.py` only.
- `docs/design/` listing + `mdu-28-resume-detect.md` headers — doc outline convention.

## Why

Resume blocks are emitted three ways (JSON, `key: value`, prose). All are valid
input, but the variance costs the next session time and blocks validation.
MDU-34 fixes emission only: one canonical shape, a validator, and docs — with
zero narrowing of what the gate accepts.

## D1 — Canonical shape

A fenced `json` object. All 11 gate keys are **required-present**; `notes` is
the only optional key. Strict on shape, permissive on values (rationale:
read-permissive is the MDU's prime directive; value enums would create a second
vocabulary drifting from run-manifest `STATUSES` and invite false rejects).

| Key | Required | Type | Rule |
| --- | --- | --- | --- |
| `mdu_id` | yes | str | non-empty |
| `branch` | yes | str | non-empty |
| `commit_sha` | yes | str | non-empty; latest commit on `branch` the work sits on (if nothing committed this session, the SHA under the park — say so in `notes`) |
| `harness` | yes | str | enum `opencode\|grok\|claude`, **imported from `run_ledger.HARNESSES`** (one vocabulary, no drift) |
| `status` | yes | str | free-form non-empty; snake_case guidance (`design_done`, `implemented_tests_pending`, `ready_to_start`) — deliberately NOT an enum |
| `done` | yes | str[] | may be empty on a fresh start |
| `next` | yes | str[] | the next session's mandate source |
| `blocked_on` | yes | str[] | may be empty |
| `design` | yes | str | either-or with `backlog` (below) |
| `backlog` | yes | str | either-or with `design` |
| `artifacts` | yes | str[] | paths; may be empty |
| `notes` | no | str | free text; omit if empty |

Either-or rule (preserves the legacy "the design or backlog path" semantics):
`design` and `backlog` must both be present as keys, **at least one non-empty**;
violation reported as one error: `missing required field: 'design' or 'backlog'
(one must be non-empty)`. Extra keys: reported as warnings, never failures
(the backlog names only the required-key miss as the exit-1 condition).

Fixture-history drift note: past user-pasted JSON matches most canonical keys.
Known drift: `status` values like `ready_to_start` (accepted — free-form by
design); occasional `sha` for `commit_sha` and missing `harness`/`status` (the
unknown-key warning catches the rename family; the latter two are now required).
All validator/doc examples use realistic values (real paths, full 40-hex SHA,
`ready_to_start`-family status), per the "copy the shape, not the values" rule.

## D2 — Emit-strict mirror edit (exact text)

Replace the legacy sentence — identical in all three mirrors, located by
content, not line number (currently `prompts/orchestrator.md:31`,
`grok/agents/orchestrator.md:37`, `grokestrator.md:37`):

```text
  The resume block must include: MDU id, branch, commit SHA, what is done, what is next, and the design or backlog path. Point at files. Do not paste file bodies.
```

with this block (2-space list-item indentation; the fenced `json` nest is the
MDU-15 precedent). The template lands **inside the gate span** (anchor →
`Do not ask again this session.`) so the existing MDU-28 byte-identity test
enforces three-way verbatim reproduction for free — no new byte-identity
machinery:

````text
  The resume block you write must be the canonical shape — a fenced `json` object with exactly these keys, arrays of strings, `notes` optional, validated by `scripts/lib/resume_block.py validate`. Copy the shape, not the values. Point at files. Do not paste file bodies.

  ```json
  {
    "mdu_id": "mdu-34",
    "branch": "main",
    "commit_sha": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
    "harness": "opencode",
    "status": "implemented_tests_pending",
    "done": [
      "scripts/lib/resume_block.py: validate subcommand",
      "docs/resume-block.md: canonical shape + prose fixture"
    ],
    "next": [
      "tests/test_mdu_34_resume_block.py: AC-1 through AC-4 coverage"
    ],
    "blocked_on": [],
    "design": "docs/design/mdu-34-resume-block.md",
    "backlog": "FEATURE_BACKLOG.md",
    "artifacts": ["docs/resume-block.md", "scripts/lib/resume_block.py"],
    "notes": "optional free text"
  }
  ```

  Emit-strict is emission-only. It does not narrow what this gate accepts as input: prose, a markdown block, a `key: value` list, or a JSON object with two or more of the keys above all still count, exactly as the recognition rule above states. Recognition stays by purpose, not by header or exact phrasing.
````

Placement rules: (1) all three mirrors get byte-identical text; (2) nothing
else in the gate span changes — the recognition, previous-session, STOP,
new-session, and override paragraphs are untouched; (3) no other gate
(one-MDU, compact-at-140000, cache-miss, coder-handoff, secret) is edited.

`validate.py` addition (MDU-15 pattern, 2 lines in `ROLE_KEYWORDS["orchestrator"]`):
`("resume_block.py",)` and `("canonical shape",)`. Both bind to the new text in
both base mirrors; the new test asserts membership + binding (D6).

## D3 — Read-permissive proof plan

The recognition language survives verbatim, proven six ways:

1. **Existing guard keeps working:** `test_mdu_28` pins its 8 phrases, the
   contiguous 11-key enumeration, and `resume-recognition precedes the STOP
   line` — all in the untouched paragraphs.
2. **Span byte-identity now covers the emission block:** `test_gate_section_spans_are_byte_identical` (MDU-28) compares the WHOLE span in all three mirrors; any rewording of the new paragraphs in any one mirror goes red automatically.
3. **New stronger pins:** MDU-28 pinned only the prefix `recognize a resume block by purpose, not by header`. MDU-34 pins the FULL clause `recognize a resume block by purpose, not by header or exact phrasing`, plus `any first-turn message whose purpose is to say where to pick up counts` and `two or more of these keys or their variants`, plus the new carve-outs `does not narrow what this gate accepts as input` and `recognition stays by purpose` — in all three mirrors (grokestrator via the conditional-skipif pattern).
4. **Ordering proof:** `index(recognition clause) < index(canonical-template fence)` in each mirror — the reader hits the permissive rule BEFORE the strict template, so the template can never be read as an input requirement.
5. **Negative guard (no strict parser introduced):** all three mirrors must NOT contain any of: `input must be canonical`, `only a json object`, `json-only`, `must be json to count`, `reject non-canonical`, `rejected as input`, `invalid as input`. `canonical` alone is NOT banned — it appears legitimately in emission context.
6. **Tool-side framing:** the validator's non-canonical failure message must state that prose and `key: value` blocks remain valid gate input (D4) — the tool itself cannot become the strict parser; the test pins that message wording.

## D4 — CLI contract: `scripts/lib/resume_block.py`

`run_ledger.py` conventions throughout (argparse, subcommand, exit codes,
`[ok]/[fail]` output, module-level constants, pure validator function).

```text
Usage:   resume_block.py validate <fixture>

Exit 0  canonical: 11 required keys present, types correct, harness in enum,
        design-or-backlog non-empty. Extra keys allowed (warn, exit stays 0).
Exit 1  violations: unreadable file; invalid JSON; top-level not an object;
        missing required key; wrong type; empty required scalar; harness not
        in {opencode|grok|claude}; both design and backlog empty.
Exit 2  usage error (argparse default).

Output: "  [ok]    <path> is a canonical resume block"
        "  [warn]  extra key '<k>' is not part of the canonical shape"
        "  [fail]  <path>:" then "          - <violation>" per line.
        Non-JSON input: [fail] "not valid JSON" plus the fixed second line
        "this tool checks canonical emission only; prose and key: value
        blocks remain valid gate input (docs/resume-block.md)"

Module surface (importable; pytest-tested via tests/conftest.py path):
  REQUIRED_KEYS / OPTIONAL_KEYS / ARRAY_KEYS / EITHER_OR_KEYS  (tuples)
  HARNESSES  — `from run_ledger import HARNESSES` (single vocabulary)
  validate_block(data) -> list[str]   # pure; violations only
  main(argv=None) -> int              # warnings computed here
```

Decisions: JSON-parseable-but-wrong-shape input IS validated (it is just the
normal failure path with a full missing/extra report) — the tool checks
canonical OUTPUT; it never judges gate INPUT. **No build.sh wiring**: no repo
tree artifact is a resume block (blocks live in chat transcripts), so a build
gate would be vacuous; pytest covers the module, and the orchestrator/user
runs it on demand against a draft emission. Validator error-message strings
are lowercase with straight ASCII quotes, matching the pinned-phrase style.

## D5 — `docs/resume-block.md` outline (~90 lines)

1. **Title + what/why** — the canonical shape's single documented source;
   reproduced verbatim in the three orchestrator mirrors (MDU-34).
2. **Canonical shape** — the fenced `json` template, byte-identical to the
   mirrors modulo list indentation, plus the D1 key table.
3. **What the next session consumes** — `branch`, `commit_sha`, `next[]`,
   `blocked_on[]` (mandate = `next` minus `blocked_on`); `mdu_id`, `design`,
   `backlog` for context; **bookkeeping** (not mandate): `harness`, `status`,
   `artifacts`.
4. **Value guidance** — `commit_sha` park semantics, snake_case `status`
   examples, arrays point at files.
5. **Read-permissive** — canonical is emission-only; the gate still accepts
   prose / markdown / `key: value` / JSON with ≥ 2 keys.
6. **Prose fixture — VALID GATE INPUT, NOT CANONICAL OUTPUT** (marked): one
   real paragraph captured from the resume material that seeded the MDU-34
   implementation session; if capture fails, use the representative shape
   below and mark provenance "representative, not captured" in the doc:

   > Resuming MDU-34 (canonical resume block) — design is done and committed on
   > main at deadbeef…: design doc docs/design/mdu-34-resume-block.md, backlog
   > entry FEATURE_BACKLOG.md lines 289-305. Done: architect delivered the
   > design; no code yet. Next: just-code lands the emit-strict template in the
   > three orchestrator mirrors plus scripts/lib/resume_block.py, then
   > test-agent adds tests/test_mdu_34_resume_block.py. Blocked on nothing.
   > Harness opencode.

7. **Validator usage** — the D4 command, exit codes, extra-key warnings.
8. **Non-goals** — checkpoint format (`session-*.md`) unchanged; input
   recognition unchanged.

## D6 — Test plan (AC-mapped)

One new file: `tests/test_mdu_34_resume_block.py` (house style: path constants,
lowercase phrase matching, raw span slicing, conditional grokestrator checks;
no changes to `test_mdu_28_resume_detect.py` — its pins keep passing).

- AC-1a: fenced template in `docs/resume-block.md` == fence in each mirror (extract, dedent per line, byte-compare).
- AC-1b: template key set == `resume_block.REQUIRED_KEYS ∪ OPTIONAL_KEYS` (no-drift fuse).
- AC-1c: template example passes `resume_block.validate_block()` (imported, `json.loads` on the extracted fence).
- AC-2a: full recognition clause verbatim in all three mirrors (D3.3 pins).
- AC-2b: first-turn acceptance rule phrases + `two or more of these keys or their variants`.
- AC-2c: carve-outs `does not narrow what this gate accepts as input` + `recognition stays by purpose` in all three mirrors.
- AC-2d: ordering — recognition clause index < template-fence index per mirror (D3.4).
- AC-2e: negative — banned strict-parser phrases (D3.5 list) absent from all three mirrors.
- AC-3a: `main(["validate", str(fixture)])` exit 0 on the canonical example (`tmp_path` file).
- AC-3b: missing `commit_sha` → exit 1 + `missing required key: 'commit_sha'` in output.
- AC-3c: extra key → exit 0 + `[warn]` line.
- AC-3d: parametrized type/enum/either-or violations → exit 1.
- AC-3e: prose file → exit 1 + the read-permissive message (D3.6 wording pin).
- AC-3f: no-args → exit 2 (argparse `SystemExit`).
- AC-4a: prose-fixture section present in `docs/resume-block.md`; extracted fixture contains the recognition-relevant facts (mdu id, branch, sha, next, blocked_on mentions).
- AC-4b: `validate.ROLE_KEYWORDS["orchestrator"]` contains the 2 new clauses AND each binds (case-insensitive) to both base mirrors (MDU-15 binding pattern).
- AC-5: no new test — existing suite green: `timeout 120 python3 -m pytest tests/ -q`, `timeout 300 ./build.sh`, `timeout 60 python3 scripts/lib/prompt_regression.py gate` (commit touches prompt files — mandatory), `runs/mdu-34/manifest.json` created + `run_ledger.py validate` it.

## D7 — Routing table

Verified against `opencode.json` permissions (checked by the orchestrator:
qa / code-reviewer / introspector are read-only; devops and orchestrator can
run scripts; just-code and test-agent write files, test-agent runs
timeout-wrapped shell).

| Work item | Agent | Mode | Gate |
| --- | --- | --- | --- |
| This design doc | architect | read-only | done — design phase |
| 3 mirrors + `docs/resume-block.md` + `scripts/lib/resume_block.py` + 2 `validate.py` clause lines | just-code | file write | review next |
| `tests/test_mdu_34_resume_block.py` | test-agent | write + `timeout 120` pytest | D6 coverage |
| Diff review | code-reviewer | read-only | review phase |
| Fix cycles from review | just-code / test-agent | write | bounded, 3 retries |
| `./build.sh` + full pytest + prompt-regression gate | devops | `timeout`-wrapped exec | **runs after review and after the last fix cycle** |
| QA grade | qa | read-only | validates from transcript + artifacts |
| Introspector loop | introspector | read-only | after QA PASS |
| Commit + push base repo; then overlay repo (`grokestrator.md`, overlay `./build.sh`; commit regenerated `build/` only per user policy) | orchestrator | exec | two commits, two pushes — the three-file rule spans two repos |
| Run manifest `runs/mdu-34/manifest.json` | orchestrator | write | MDU-15 inline contract |

## Risks

1. **Gate-span growth (~24 lines)** — accepted; MDU-15 inlined a larger schema, byte-identity already covers the span, and the template sits at point-of-use.
2. **Template drift doc ↔ mirrors** — mitigated by AC-1a dedent-equality test; cross-mirror identity is free via the MDU-28 span test.
3. **Validator misused as an input gate** — mitigated by D3.5/D3.6 wording, exit-0 extras, and no build wiring; the fail message itself carries the carve-out.
4. **Prompt-regression gate** — golden traces target other sections (verified); if it reds on the intentional mirror change, re-baseline with `prompt_regression.py baseline --update` ONLY after the full tree is green ("never refresh" stands).
5. **Prose-fixture provenance** — capture from this MDU's own seed material; the fallback representative is marked, and the presence test tolerates either.
6. **Pinned-phrase typography** — all new pins are lowercase straight-ASCII em-dash-free substrings; the raw template keeps house em-dash style but no pin touches it.

## Decisions made (recorded rationale)

1. Template lives **inside the gate span** → MDU-28 byte-identity enforces
   three-way verbatim for free; AC-1 needs no new identity machinery.
2. All 11 keys required-present + either-or non-empty `design`/`backlog`
   (preserves the legacy "design or backlog path" semantics).
3. `status` stays free-form (no enum) — shape-strict, value-permissive.
4. `HARNESSES` imported from `run_ledger` — one vocabulary.
5. No build.sh wiring for the validator (nothing in-tree to gate).
6. `ROLE_KEYWORDS` gains 2 clauses (MDU-15 no-drift-fuse precedent).
7. No overlay test module — grokestrator covered by the conditional base
   pattern (MDU-28 precedent, unlike MDU-15's overlay import).
