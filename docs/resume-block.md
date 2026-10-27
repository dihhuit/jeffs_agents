# Resume block — the canonical shape

A resume block is the handoff the orchestrator gives the user at the end of a
session: a short, portable statement of where the work sits so a new session can
pick it up without re-deriving anything. It is the next session's only durable
input, so its shape is fixed here and reproduced verbatim in the three
orchestrator mirrors (`prompts/orchestrator.md`, `grok/agents/orchestrator.md`,
and the overlay `grokestrator.md`).

Resume blocks used to be emitted three ways — JSON, `key: value`, and prose. All
three remain valid *input*, but the variance cost every next session time and
made the block impossible to check. This document fixes **emission** only: one
canonical shape, one validator, zero narrowing of what the gate accepts.

## Canonical shape

Emit a fenced `json` object. All eleven gate keys are required-present; `notes`
is the only optional key. Arrays are arrays of strings — point at files, do not
paste file bodies.

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

| Key | Required | Type | Rule |
| --- | --- | --- | --- |
| `mdu_id` | yes | str | non-empty |
| `branch` | yes | str | non-empty |
| `commit_sha` | yes | str | non-empty; latest commit the work sits on (park semantics below) |
| `harness` | yes | str | `opencode`, `grok`, or `claude` (run-manifest vocabulary) |
| `status` | yes | str | free-form non-empty; snake_case by convention — deliberately not an enum |
| `done` | yes | str[] | may be empty on a fresh start |
| `next` | yes | str[] | the next session's mandate source |
| `blocked_on` | yes | str[] | may be empty |
| `design` | yes | str | either-or with `backlog` |
| `backlog` | yes | str | either-or with `design` |
| `artifacts` | yes | str[] | paths; may be empty |
| `notes` | no | str | free text; omit if empty |

Either-or rule: both `design` and `backlog` must be present as keys, and at
least one must be non-empty — this preserves the legacy "the design or backlog
path" semantics. A violation reports exactly one error: `missing required field:
'design' or 'backlog' (one must be non-empty)`.

Unknown keys are warnings, never failures: a stray `sha` beside `commit_sha`
still exits 0, and the warning names the rename that slipped in.

## What the next session consumes

The mandate is `next[]` minus `blocked_on[]`; everything else is context.

- **Mandate:** `branch`, `commit_sha`, `next[]`, `blocked_on[]`.
- **Context:** `mdu_id`, `design`, `backlog`.
- **Bookkeeping, not mandate:** `harness`, `status`, `artifacts`.

If every `next[]` item is blocked, the next session asks which one to unblock
rather than guessing. `done[]` is a record, not a plan.

## Value guidance

- **`commit_sha` park semantics.** Record the latest commit on `branch` the work
  sits on, even if it predates this session. If nothing was committed, do not
  invent or blank the SHA: park on the base commit and say so in `notes`
  (`"uncommitted: parked on the branch tip, artifacts written"`).
- **`status` is prose, snake_case.** `design_done`,
  `implemented_tests_pending`, `review_rejected`, `ready_to_start`,
  `blocked_on_credentials`. No enum, so no value is "wrong"; the next session
  reads it for tone, not control flow.
- **Arrays point at files.** One path or one narrow claim per item
  (`"docs/design/mdu-34-resume-block.md: D2 mirror text"`), never a body.
- **`blocked_on` names the blocker,** not the symptom: `"AWS profile safekids
  not configured"` beats `"deploy fails"`.
- **`notes` only when it earns its line** — parked SHAs, deviations, known-red
  checks. Not narrative.

## Read-permissive: canonical is emission-only

This shape constrains what the orchestrator *writes*, never what the gate
*accepts*. The session-boundary gate still recognizes prose ("resume", "continue
<mdu-id>", "THIS IS A NEW SESSION"), a markdown block, a `key: value` list, or a
JSON object with two or more of the keys above. Recognition stays by purpose,
not by header or exact phrasing — emitting the canonical shape is a courtesy to
the next session, not a tax on the user.

## Prose fixture — VALID GATE INPUT, NOT CANONICAL OUTPUT

The paragraph below is the opposite end of the spectrum: plain prose the gate
must still accept. Provenance: **representative, not captured (seed paste
arrived canonical-shaped JSON)**.

> Resuming MDU-34 (canonical resume block) — design is done and committed on
> main at deadbeef…: design doc docs/design/mdu-34-resume-block.md, backlog
> entry FEATURE_BACKLOG.md lines 289-305. Done: architect delivered the
> design; no code yet. Next: just-code lands the emit-strict template in the
> three orchestrator mirrors plus scripts/lib/resume_block.py, then
> test-agent adds tests/test_mdu_34_resume_block.py. Blocked on nothing.
> Harness opencode.

The live seed block for this MDU also demonstrates value-permissiveness: its
`commit_sha` carried a parenthetical comment and still validated as a non-empty
string, because the shape is strict and the values are not.

## Validator

```
python3 scripts/lib/resume_block.py validate <fixture>
```

- Exit **0** — canonical: eleven required keys, correct types, harness in the
  enum, `design`/`backlog` at least one non-empty. Extra keys warn (`[warn] extra
  key '<k>' is not part of the canonical shape`) and the exit stays 0.
- Exit **1** — violations: unreadable file, invalid JSON, top-level not an
  object, missing required key, wrong type, empty required scalar, harness
  outside the enum, both `design` and `backlog` empty.
- Exit **2** — usage error (argparse default).

Non-JSON input fails with `not valid JSON` plus the fixed line `this tool checks
canonical emission only; prose and key: value blocks remain valid gate input
(docs/resume-block.md)` — the tool grades an emission, it never gates a session
start. It is not wired into `build.sh`: no repo tree artifact is a resume block,
so run it on demand against a draft emission.

## Non-goals

- **Checkpoint format unchanged.** `session-*.md` memory checkpoints keep their
  own shape; this document governs the resume block only.
- **Input recognition unchanged.** No phrase, key-name, or ordering requirement
  is added to what counts as a resume.
- **No status vocabulary.** A status enum would fork a second vocabulary from the
  run manifest and invite false rejects.
