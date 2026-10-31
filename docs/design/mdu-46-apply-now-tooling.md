# MDU-46 — Apply-now tooling: run-ledger `model` field, brief checklist, local upstream draft

**Date:** 2026-10-31 · **Kind:** chore MDU (base repo only) · **Status:** design

**What done looks like:** `scripts/lib/run_ledger.py` accepts and audits an
optional top-level `model` field; two new docs (`docs/brief-checklist.md`,
`docs/upstream-drafts/opencode-question-60min-kill.md`) stage recurring
apply-now discipline and the mdu-35 upstream draft locally; a new pin test
file locks all of it; backlog + tests README updated. Full pytest green,
`./build.sh` exit 0 twice, zero changes under `prompts/` or `grok/agents/`.

## 0. Files surveyed for this design (apply-now 20261024-1)

Exactly these were read; everything else in the tree was reached only by
narrow grep/glob:

1. `scripts/lib/run_ledger.py` — full (constants, `validate_manifest`,
   `_validate_phase`, `validate_file`, `load_manifests`, `summarize`,
   `format_summary`, CLI).
2. `tests/test_run_ledger.py` — full (fixture style, every enum/type case).
3. `tests/test_mdu_15_run_ledger_inline.py` — full (inline-parity contract).
4. `agent-improvements.md` — entries 20261014-1/-2/-5, 20261021-6/-9/-12,
   20261024-1, 20261026-2, 20261027-3, 20261029-1, 20261030-2, plus the
   run-history lines citing them.
5. `docs/design/mdu-35-question-tool.md` — appendix A (upstream draft).
6. `FEATURE_BACKLOG.md` — full (status sections, entry conventions).
7. `tests/README.md` — full (per-test-file table).
8. `.agents/memory/session-ses_e6d9f83e5ffenBVstFGsQ0nvba.md` — the
   2026-10-31 user rulings for this MDU (narrow grep only).

## 1. Context

apply-now 20261026-2 has been uncarried for 7 consecutive runs: manifests
record per-phase `model_tier` labels but no orchestrator-`model` audit
trail. This MDU makes the trail durable tooling instead of brief-side hope.
Separately, the highest-value apply-now clauses live only as prose inside
`agent-improvements.md` entries, and the mdu-35 upstream-issue draft is
buried in a design-doc appendix. User rulings 2026-10-31: full chore MDU;
file nothing upstream — the 60-min-kill draft goes **local only**; apply-all
definition changes are deferred to MDU-47, so **no file under `prompts/` or
`grok/agents/` may change this session**.

## 2. D1 — run-ledger optional `model` field

**Schema decision.** `model` is a top-level OPTIONAL field: when the key is
absent, nothing changes; when present it must be a non-empty string (the
session's orchestrator model id, e.g. `opencode-go/glm-5.3-flash`). No enum,
no allowlist — model ids churn per registry and an allowlist would turn a
chore MDU into a registry MDU. Whitespace-only strings pass (non-empty is
the whole rule; no trimming logic).

**Code change** (`scripts/lib/run_ledger.py`, after the `harness` check in
`validate_manifest`):

```python
if "model" in data:
    if not isinstance(data["model"], str) or not data["model"]:
        errors.append("'model' must be a non-empty string")
```

- `REQUIRED_FIELDS` and `REQUIRED_VERIFICATION_FIELDS` are **unchanged** —
  this is the load-bearing decision (see §2.1).
- Module docstring gains one line documenting the optional field (the only
  "code docs" edit; `examples/runs/*.json` fixtures stay untouched — absent
  `model` there demonstrates optionality and keeps MDU artifacts historical).
- stdlib-only preserved: the new code needs no new import.

**Summarize surfacing (minimal).** `summarize()` gains an additive
`"by_model"` dict (only models that actually occur; no pre-seeded keys since
values are free-form). `format_summary()` gains a `by model:` block after
`by harness:`, same style — per-model counts, `  (none)` when no manifest
carries a model. Trade-off, accepted: `--json` output shape changes
additively. Verified safe: existing tests assert known keys, never exact
dict equality, and `evals/tasks/03-ledger-conformance/` greps show no
`summarize` dependency at all.

### 2.1 test_mdu_15 parity analysis (why OPTIONAL keeps it green)

- `test_inline_required_fields_line_matches_run_ledger` — compares the
  prompt's `Required fields:` line to `set(REQUIRED_FIELDS)`. We do not add
  `model` to the tuple and do not touch the prompt → still equal.
- `test_inline_verification_fields_line_matches_run_ledger` and
  `test_inline_phases_entry_fields_pinned` — untouched surfaces.
- `test_inline_enums_match_run_ledger_constants` — `ENUM_KEYS` unchanged;
  `model` has no enum, so no new enum key exists to drift.
- `test_inline_example_is_valid_manifest` — the inline example carries no
  `model` key; the new check is conditional on key presence → still valid.
- Overlay import of `MDU_15_PHRASES` and all `ROLE_KEYWORDS` clause pins are
  prompt-side; prompts untouched → all still bind.

**Inline-parity protection is itself pinned:** D4a asserts
`"model" not in run_ledger.REQUIRED_FIELDS`, so a future edit that makes the
field required goes red against the (still ungated) prompt text instead of
silently breaking parity.

## 3. D2 — `docs/brief-checklist.md`

One brief template per delegated role: **architect, just-code/fix child,
code-reviewer, test-agent, devops, qa, introspector** — each a short `ul`
of apply-now clauses, every clause ending with its `[id]` citation.
**This is a DOC, not a prompt or agent-definition file** — the doc says so
in its first paragraph; nothing under `prompts/` or `grok/agents/` changes
by it existing. `agent-improvements.md` remains the canonical source; this
checklist is the dispatch-time mirror.

Layout: an "Every brief" section (orchestrator discipline) followed by the
seven role sections. Exact one-line clause text (copy verbatim; the pinned
fragments in §5 D4b must land on the same line as their id):

- Open every brief with a one-paragraph what-done-looks-like (file list,
  tests run, verdict format); one single deliverable per brief; split any
  brief over ~200 lines. [20261014-1]
- Pass file paths plus a 20-line excerpt at most, never full file bodies;
  keep per-child summaries to 5 lines. [20261014-2]
- Sequence phases explicitly: devops runs after review and after the last
  fix cycle; any fix cycle is followed by re-running the affected suite and
  both builds. [20261021-6]
- Carry a who-executes/who-grades routing table for every command-bearing
  phase; never assign commands the target agent's allowlist cannot run.
  [20261021-9]
- Record a top-level model field in the manifest (the session's orchestrator
  model) so tier compliance is auditable. [20261026-2]
- Finalize the manifest fully before dispatching QA (all phases,
  verification block, summary, completed_at) and validate to exit 0; after
  QA only qa_grade flips. [20261027-3]
- QA must attest it validated the exact final manifest path; append every
  completed phase including qa and validate. [20261014-5]
- Architect briefs list the authoritative files with short excerpts, forbid
  full-tree reads, and the design doc opens with its surveyed-file list.
  [20261024-1]
- Name the evidence producer before dispatching the reviewer (devops
  preferred); a dated review-evidence.md lists each command, exit code, and
  output path; re-run it after each fix cycle. [20261021-12]
- Tell the reviewer up front: shell is denied by design — scope this
  static-trace, gate outputs are attached, report a denial in one line and
  never as a REJECT. [20261030-2]
- If the first QA reply is empty or lacks the GRADE line, request a re-run
  and accept only a second response. [20261029-1]

Role mapping (repeat the relevant clause lines per section):
architect → 20261024-1, 20261014-1, 20261014-2 · just-code/fix child →
20261014-1, 20261014-2 · code-reviewer → 20261030-2, 20261021-12 ·
test-agent → 20261014-1, 20261021-6 · devops → 20261021-6, 20261021-12,
20261021-9 · qa → 20261029-1, 20261014-5, 20261027-3, 20261021-9 ·
introspector → 20261014-5, 20261026-2.

## 4. D3 — `docs/upstream-drafts/opencode-question-60min-kill.md`

New directory `docs/upstream-drafts/` (first occupant). Standalone draft
extracted from the mdu-35 appendix A: banner, status note, Title, Minimal
repro, Observed, Expected, Version, Evidence. Rules:

- **FILING GATED banner in the first lines:** local draft only, not filed;
  filing requires an explicit user instruction naming the repository and
  the action (user ruling 2026-10-31); never file as a default MDU step.
- **Masked evidence pointers only** — cite
  `runs/mdu-35-question-tool/evidence.md` sections (§1.3, §3c, §4a, §4b,
  §4e, §5) as the appendix does; no session dumps, no raw storage paths.
- **No filing mechanics anywhere in the file:** no gh-command text, no
  git-remote/push text, no "file it now" phrasing — the file must be
  unmistakably a draft, not an instruction (pinned by D4c).
- Status note records intent: local staging for a possible future OpenCode
  fork ("someday, unplanned" per the 2026-10-31 ruling); off critical path.
- One pointer line is added under the mdu-35 appendix heading naming the
  standalone copy (docs-only edit; the appendix itself stays byte-stable as
  the historical record, the standalone copy is the maintained one).

## 5. D4 — `tests/test_mdu_46_apply_now_tooling.py`

Hermetic: local fixture builder (no import from other test modules),
`tmp_path` for anything written, repo-doc reads for pins, no network, no
git state commands.

**(a) Ledger model field** — cases: absent → valid; valid string
(`opencode-go/glm-5.3-flash`) → valid; empty string → one error
`'model' must be a non-empty string`; non-string (int, list, null) → same
error; `"model" not in run_ledger.REQUIRED_FIELDS` (parity protection);
`summarize` tallies `by_model` (one manifest with model, one without);
`format_summary` prints `by model:` + the model string, and `  (none)` when
no manifest carries one; CLI `validate` on a tmp_path manifest carrying
`model` exits 0.

**(b) Checklist doc pins** — parametrized over these (id, fragment) pairs,
asserting one lowercased line contains BOTH:

| id | pinned fragment |
| --- | --- |
| 20261014-1 | `what-done-looks-like` |
| 20261014-2 | `20-line excerpt` |
| 20261021-12 | `evidence producer` |
| 20261030-2 | `denied by design` |
| 20261027-3 | `before dispatching qa` |
| 20261014-5 | `final manifest path` |
| 20261026-2 | `model field` |
| 20261024-1 | `surveyed-file list` |
| 20261029-1 | `second response` |

Plus: the doc states it is a DOC, not a prompt/definition file, and names
all seven role templates.

**(c) Upstream draft pin** — file exists; `FILING GATED` appears within the
first 10 lines; none of `gh issue`, `gh pr`, `git remote`, `git push`,
`git clone`, `file this issue`, `file it now` appears anywhere
(case-insensitive); the masked evidence pointer
(`runs/mdu-35-question-tool/evidence.md`) is present.

## 6. D5 — backlog + tests README

- `FEATURE_BACKLOG.md`: append an MDU-46 entry (Why/Description/ACs from
  this doc; Status line `Done — 2026-10-31` filled at commit per repo
  convention) and a new short follow-up entry — "Upstream draft staging —
  60-min question kill (prep-fork)" — whose Status points at the D3 doc,
  records the local-only ruling, filing gated, fork someday unplanned.
- `tests/README.md`: add one row for `test_mdu_46_apply_now_tooling.py`
  (ledger `model` cases + checklist/draft pins).

## 7. Routing and sequencing (20261021-9 / 20261021-6 / 20261021-12)

| Phase | Executes | Grades |
| --- | --- | --- |
| design | architect | orchestrator (D1..Dn verdict) |
| implement | just-code (code+docs only, no test edits) | code-reviewer (static-trace) |
| review | code-reviewer — static-trace scope, gate outputs attached | orchestrator |
| test | test-agent | qa |
| deploy | devops — pytest, build x2, secret scan, dated evidence file | qa |
| validate | qa — static scope, attached evidence, attests final manifest path | orchestrator |

devops writes the dated review-evidence.md BEFORE the reviewer is
dispatched and re-runs it after any fix cycle. devops runs after review and
after the last fix cycle; any fix cycle re-runs the affected suite. The QA
brief carries 20261029-1 (re-request on empty first reply) and
20261027-3/20261014-5 (finalized manifest, validator exit 0, attestation
of the exact final path). Reviewer brief carries 20261030-2 verbatim.

## 8. Acceptance criteria

- **AC-1** (D1) `validate` exits 0 on a manifest carrying a valid `model`;
  exits 1 with the named error on empty-string and non-string; absent
  `model` stays valid.
- **AC-2** (D1) `REQUIRED_FIELDS` still excludes `model`; full
  `python3 -m pytest tests/ -q` green, including all test_mdu_15 parity
  tests untouched.
- **AC-3** (D1) `summarize` text and `--json` surface `by_model` as an
  additive key; no existing key or value changes.
- **AC-4** (D2) `docs/brief-checklist.md` exists with the seven role
  templates; every pinned id appears with its clause text; the doc states
  it is a DOC, not a definition file.
- **AC-5** (D3) the upstream draft exists, opens with the FILING GATED
  banner, carries masked evidence pointers only, and contains zero
  git-remote/gh-command text.
- **AC-6** (D4) the new test file is green and hermetic.
- **AC-7** (D5) backlog gains the MDU-46 entry + prep-fork follow-up
  pointer; tests README gains the row.
- **AC-8** `./build.sh` exits 0 twice consecutively (idempotent).
- **AC-9** secret scan clean on every new/changed file; no 32+ char
  `[A-Za-z0-9+/]` lexeme in the new docs (repo-relative paths only).
- **AC-10** `git diff` shows zero modifications under `prompts/` and
  `grok/agents/`.
- **AC-11** this MDU's own run manifest records `model`
  (`opencode-go/glm-5.3-flash`), validates exit 0 on the final path, and QA
  attests that validation.

## 9. Risks / trade-offs

- `by_model` changes `--json` additively — accepted; no exact-shape
  consumer exists (verified §2).
- `model` staying optional means the audit trail is voluntary until the
  MDU-47 definition changes land — intentional; prompts are user-gated
  this session, and required-ness is exactly what MDU-47 should decide.
- The checklist duplicates agent-improvements wording by design; the pin
  test locks presence + fragment, not full wording — accepted (the
  canonical log stays authoritative; ids keep the two linkable).
- Two copies of the upstream draft (appendix + standalone) — appendix is
  the frozen historical record with a pointer; the standalone is the
  maintained one. Accepted.
