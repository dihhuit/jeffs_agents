# MDU-28 — Resume-block recognition on the first turn

## Why

The SESSION BOUNDARY gate (deployed 2026-10-17) misfired on the first turn of a new session (OpenCode session `ses_eb2c7717effeCJneXAJfbhsA2U`, project `mmo`, 2026-10-17 21:15). The user's first message was a bare JSON object — no "RESUME BLOCK" header, no `continue <mdu-id>` prose — carrying `mdu_id`, `branch`, `commit_sha`, `done`, `next`, `blocked_on`, `design`, `backlog`, `artifacts`, `harness`. The orchestrator answered "…then stop as required" and stopped on turn one. A follow-up session worked only because the user manually prefixed "THIS IS A NEW SESSION." — that prefix should not be necessary.

Two defects:

1. **Recognition gap.** The exception only catches prose-shaped resume blocks (`continue <mdu-id> from the resume block`). A JSON/markdown payload with resume-block fields was not recognized as a resume block at all.
2. **State conflation.** The model read the block's `commit_sha` / "committed" status — the *previous* session's ending — as "THIS session has finished an MDU," so it treated turn one as a boundary crossing.

## Required behavior (user-approved)

1. **Deterministic first-turn rule.** The gate may fire only if THIS session has itself run an MDU loop to commit/park. On the first user turn the gate is OFF by construction; the gate needs evidence from this session's own transcript and work, never from pasted history.
2. **Broad resume-block recognition.** Recognize by purpose, not header or exact phrasing: prose, markdown, or JSON with ≥2 of the structured fields. The exact-phrase dependency stays ONLY for the override (`continue this session across MDUs`).
3. **Anti-conflation ban.** A commit/status inside a resume block is the previous session's ending — proof the gate is OFF here. This session's mandate is the block's `next:` minus anything in `blocked_on:`.
4. **Blocked-next handling.** If every `next:` item is blocked, end the turn by asking which item to unblock — a normal blocked-work turn end, never gate language ("stop as required", "boundary reached", "end of this MDU").

**Expected replay of the failed session:** turn one → gate OFF by construction; the JSON (10 keys ≥ 2) is a resume block; its `commit_sha` is the previous session's ending; mandate = `next:` minus `blocked_on:` = empty → ask the user which item to unblock, with no gate language.

## Files

| File | Change |
| --- | --- |
| `prompts/orchestrator.md` | Replace SESSION BOUNDARY section |
| `grok/agents/orchestrator.md` | Same replacement (section bodies are byte-identical today) |
| `../opencode_agents/grok/agents/grokestrator.md` | Same replacement (overlay repo, root full-file — live in the build because `grokestrator` is absent from the base) |
| `tests/test_mdu_28_resume_detect.py` | New regression test |

No change to `scripts/lib/validate.py` (see Tensions).

## Replacement text — apply verbatim to all three files

Replace the span from the line `- **SESSION BOUNDARY — ONE MDU PER SESSION:**` through the line ending `Do not ask again this session.` (the current section body is byte-identical in all three files, so one text serves all three). Paste verbatim, straight apostrophes, em-dashes as shown. Untouched: the Session Checkpoint bullet above it and the COMPACT AT 140000, CACHE MISS GATE, and CODER HANDOFF sections below it.

```markdown
- **SESSION BOUNDARY — ONE MDU PER SESSION:**

  This gate fires only after this session itself has finished an MDU. A commit or resume note from an earlier session does not count. If this session has not finished an MDU, the boundary has not been reached. The gate needs evidence from this session's own transcript and work — this session itself has run an MDU loop to a commit or a park. On the first user turn of a session there is no such evidence: the gate is OFF by construction, and resume material in that turn cannot satisfy it. Do not read pasted history as this session's history.

  **A pasted resume block in a new session is the start of work, not a boundary crossing.** Recognize a resume block by purpose, not by header or exact phrasing: any first-turn message whose purpose is to say where to pick up counts — prose ("resume", "continue <mdu-id>", "THIS IS A NEW SESSION"), a markdown block, or a JSON object with two or more of these keys or their variants: `mdu_id`, `branch`, `commit_sha`, `done`, `next`, `blocked_on`, `design`, `backlog`, `artifacts`, `harness`, `status`. Do that MDU. Do not ask for an override. Recognition never requires an exact phrase; the only exact phrase in this gate is the override below.

  A commit or "done" recorded inside a resume block is the previous session's ending — proof the gate is OFF here, not proof it is reached. Never reason "the resume block shows the MDU committed, so this session's boundary is reached". This session's mandate is the block's `next:` items minus anything listed in `blocked_on:`.

  If every `next:` item is blocked, end the turn by asking the user which item to unblock. That is a normal blocked-work turn end, not a session boundary stop. Do not describe it with gate language ("stop as required", "boundary reached", "end of this MDU").

  **STOP AT THE END OF THIS MDU. DO NOT START THE NEXT MDU IN THIS SESSION.**

  When this session's current MDU is committed, or parked with durable artifacts, end your turn. In that reply, tell the user to start a new session and paste the resume block you just wrote.

  How they start a new session:
  - OpenCode: press **Ctrl+X**, then **N**. Same project directory.
  - Grok: start a new session in the same directory. Do not pass `--continue`.

  The resume block must include: MDU id, branch, commit SHA, what is done, what is next, and the design or backlog path. Point at files. Do not paste file bodies.

  The only override to start another MDU in a session that has already finished one is the user typing this exact phrase: `continue this session across MDUs`. A resume block is not that phrase. "keep going", "next", "looks good", and "start now" are not that phrase. If they send the exact phrase, acknowledge it once and proceed. Do not ask again this session.
```

What was kept verbatim vs replaced:

- **Kept verbatim** (already compliant + MDU-23 test locks): the first three sentences of the opening paragraph; the bold "A pasted resume block in a new session is the start of work…"; the bold STOP line; the "When this session's current MDU is committed…", "How they start a new session", and resume-block-contents paragraphs; the entire override paragraph.
- **Replaced/broadened**: the recognition sentence (was prose-only, `continue <mdu-id>`-dependent) and the old implicit assumption that "this session has finished an MDU" was self-evident — in the live failure it was satisfied by *pasted* history, so the paragraph now states the evidence source and the turn-one construction explicitly, and adds the anti-conflation and blocked-next paragraphs.

## Required test phrases

Case-insensitive substring asserts (the test lowercases file text; phrases use straight apostrophes):

| Phrase | Locks |
| --- | --- |
| `own transcript and work` | Rule 1 — evidence source is this session's transcript/work |
| `the gate is off by construction` | Rule 1 — first-turn determinism |
| `do not read pasted history as this session's history` | Rule 1 — pasted history ban |
| `recognize a resume block by purpose, not by header` | Rule 2 — purpose-based recognition |
| `two or more of these keys` | Rule 2 — JSON field threshold (≥2 keys) |
| `proof the gate is off here, not proof it is reached` | Rule 3 — anti-conflation direction |
| `this session's mandate is the block's` | Rule 3 — `next:` minus `blocked_on:` mandate |
| `a normal blocked-work turn end` | Rule 4 — all-blocked turn end is not a gate stop |

None of these substrings occur in the COMPACT, CACHE MISS, or CODER HANDOFF sections, so they cannot collide. MDU-23's existing phrases (`stop at the end of this mdu`, `a pasted resume block in a new session is the start of work`, `a resume block is not that phrase`, `continue this session across mdus`, `cache miss`, `compact and continue`, `140000`) all remain present — the first two via the kept-verbatim bold lines, the rest via untouched sections.

## Tests

New `tests/test_mdu_28_resume_detect.py`, following `test_mdu_23_session_hygiene.py` conventions (`REPO_ROOT = Path(__file__).resolve().parents[1]`, read + lowercase + substring asserts):

1. `test_base_orchestrator_files_carry_resume_detection` — hard assert all 8 phrases in BOTH base files (`prompts/orchestrator.md`, `grok/agents/orchestrator.md`).
2. `test_resume_detection_rules_precede_the_stop_line` — in both base files, `text.index("recognize a resume block by purpose") < text.index("stop at the end of this mdu")`. Locks the required ordering: first-turn/resume rules hit the reader before the bold STOP line.
3. `test_overlay_grokestrator_carries_resume_detection` — same 8 phrases against `REPO_ROOT.parent / "opencode_agents" / "grok" / "agents" / "grokestrator.md"`, with `pytest.skip("overlay sibling opencode_agents/ not present")` when that path is absent.

**Cross-repo path note (confirmed):** the overlay path relative to the base repo root is `../opencode_agents/grok/agents/grokestrator.md` — i.e. `REPO_ROOT.parent / "opencode_agents" / ...`; the file exists in this workspace. No existing base test references cross-repo files, and the overlay repo has no `tests/` of its own. The base validator's parity checker cannot cover grokestrator either: `GROK_MIRRORS["orchestrator"] = ["orchestrator.md"]` iterates `prompts/*.md` stems, and there is no `prompts/grokestrator.md`, so grokestrator is never a parity pair — and the overlay `./build.sh` step 8 re-executes the same base validator, which therefore adds no grokestrator phrase coverage. The conditional cross-repo pytest check is the only mechanism that gates the third file, hence the skip-when-absent design: the base repo stays green in a standalone clone (public GitHub), while the workspace (where both repos are siblings) gets the full three-file lock.

## Acceptance

Run in order (by the MDU implementer/orchestrator; the overlay build re-runs the base build and validator itself, so steps 3–4 are one gate):

```bash
cd /mnt/FastSSDXFS/projects/agents/open-agent-definitions
timeout 300 python3 -m pytest tests/ -q      # includes new test_mdu_28 + all MDU-23 locks
timeout 300 ./build.sh                       # regenerate build/ (validate.py checks build output)
timeout 60 python3 scripts/lib/validate.py   # base validator on fresh build/; parity keywords must stay satisfied

cd /mnt/FastSSDXFS/projects/agents/opencode_agents
timeout 300 ./build.sh                       # re-runs base build, merges grokestrator, re-validates
```

`validate.py` is run by whoever runs the build, immediately after it — it validates `build/` output, so a stale build would validate stale text. The overlay `./build.sh` executes the base validator as its final step automatically; the explicit `validate.py` run is only needed in the base repo.

## Tensions and resolutions

1. **Parity checker vs. new wording.** `validate_parity` + `ROLE_KEYWORDS["orchestrator"]` clauses (`mdu`, `delegat`, `140000`, `continue this session across mdus`, `cache miss`, `compact and continue`) are whole-file substring checks, not section-scoped. The replacement keeps every clause: `delegat` and `140000` survive in untouched sections, `continue this session across mdus` in the kept override paragraph. Identical text in all three files makes parity trivially green.
2. **Not extending `ROLE_KEYWORDS`.** Considered adding MDU-28 clauses to `validate.py`; rejected. Parity cannot see grokestrator (no `prompts/grokestrator.md` stem), so validator clauses would lock only the two base files that the pytest already locks more precisely, while growing the validator diff. pytest is the real three-file gate here.
3. **Public base vs. private overlay in tests.** A hard cross-repo assert would break any standalone clone of the public base (and its CI). Resolved with the conditional check (assert when the sibling exists, skip otherwise) — the only file not otherwise gated.
4. **Forbidden gate-language strings appear in the section.** The blocked-next paragraph deliberately quotes "stop as required", "boundary reached", "end of this MDU" as *banned* examples. Any future test asserting the ABSENCE of gate language in the section would misfire on these quotes; MDU-28's test asserts phrase PRESENCE only. Likewise "end of this MDU" (a banned quote) must not be confused with the required `stop at the end of this mdu` (the bold STOP line) — different strings, no collision.
5. **Exact-phrase dependency narrowed, not the override.** Recognition no longer depends on `continue <mdu-id>` phrasing, but the override stays exact-phrase-only (`continue this session across MDUs`), and "keep going"/"next"/"looks good"/"start now" remain non-overrides — the gate is not weakened; after THIS session commits/parks its own MDU it still STOPs and directs the user to a new session.

## Out of scope

- COMPACT AT 140000, CACHE MISS GATE, CODER HANDOFF sections (untouched; the CACHE MISS "Say `continue <mdu-id> from the resume block`" user instruction stays as-is — it is user guidance, consistent with recognition).
- `scripts/lib/validate.py`, `ROLE_KEYWORDS`, `GROK_MIRRORS`.
- Any other agent prompts, the overlay manifests/snippets, `build/` outputs (regenerated), deploy, and commit/push handling (workspace cross-repo commit order applies when the loop reaches commit).
