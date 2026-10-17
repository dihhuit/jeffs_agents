# MDU-23 — Session hygiene gates

Status: approved by the user on 2026-10-17. Implement the text below. Do not invent a headless session supervisor. Do not change model IDs. Do not edit `build/` by hand.

## Why

Measured on the MMO OpenCode logs (Oct 4–16, $232 xAI):

- Auto-compaction fires near the model limit (grok-4.7 is 500k). Sessions grew to 401k and never compacted. The price cliff is 200k.
- Prompt size is `input + cache.read`, not `input` alone.
- A cache miss rebills the transcript as fresh `input` with `cache.read` of 0, 512, or 1152. That was about $26 of parent spend. A miss at 250–300k costs about $1 before a child even starts.
- One `grok-just-code-mid` child ran 100 turns, 74 of them over 200k, and cost $23. A review-reject was appended to that same session.
- Orchestrators re-read `session.rs` / `udp.rs` up to 21 times and sometimes edited code.
- Subagent briefs were already short (max ~5k). Do not add a "shrink the brief" rule.

## Threshold

**140000** prompt tokens (`input + cache.read`). Not 150000. 140000 leaves room for the compact turn and keeps a miss under the 200000 2× cliff ($4 / $1 / $12 instead of $2 / $0.50 / $6 on grok-4.7 and grok-4.6).

## Files

Edit all of these. The two base orchestrator files must stay behaviorally aligned (`validate_parity`).

1. `open-agent-definitions/prompts/orchestrator.md` — also the OpenCode `grokestrator` system prompt.
2. `open-agent-definitions/grok/agents/orchestrator.md`
3. `opencode_agents/grok/agents/grokestrator.md` — does not inherit (2). Patch it explicitly.
4. `open-agent-definitions/prompts/just-code.md` — OpenCode `just-code`, `just-code-mid`, `just-code-pro`, and every `grok-just-code*` OpenCode agent.
5. `open-agent-definitions/grok/agents/just-code.md`
6. `open-agent-definitions/grok/agents/just-code-mid.md`
7. `open-agent-definitions/grok/agents/just-code-pro.md`
8. `open-agent-definitions/scripts/lib/validate.py` `ROLE_KEYWORDS` — add the clauses below so a mirror cannot drop them.
9. A pytest that fails if any of files 1, 2, 4, 5, 6, 7 is missing its required phrases. QA will grep file 3; a test in the overlay is optional.

Do not edit dead copies under `opencode_agents/prompts/` or `opencode_agents/grok/agents/` except `grokestrator.md`.

## Replace this sentence

In files 1, 2, and 3, replace:

`Long-running sessions (hours/days) are fine — but each individual MDU should make steady progress.`

with:

`A session may run for hours on a single MDU. It must not start the next MDU, and it must compact at 140000 once durable artifacts exist.`

## Orchestrator block

Insert this section in files 1, 2, and 3, immediately after the Session Checkpoint bullet (the one you just edited). Wording may be slightly shorter in the grok mirrors, but every required phrase must appear verbatim.

Required verbatim phrases: `140000`, `continue this session across MDUs`, `cache miss`, `compact and continue`.

```markdown
- **SESSION BOUNDARY — ONE MDU PER SESSION:**

  **STOP AT THE END OF THIS MDU. DO NOT START THE NEXT MDU IN THIS SESSION.**

  When the current MDU is committed, or parked with durable artifacts, end your turn. In that reply, tell the user to start a new session and paste the resume block you just wrote.

  How they start a new session:
  - OpenCode: press **Ctrl+X**, then **N**. Same project directory.
  - Grok: start a new session in the same directory. Do not pass `--continue`.

  The resume block must include: MDU id, branch, commit SHA, what is done, what is next, and the design or backlog path. Point at files. Do not paste file bodies.

  The only override is the user typing this exact phrase: `continue this session across MDUs`. "keep going", "next", "looks good", and "start now" are not that phrase. If they send the exact phrase, acknowledge it once and proceed. Do not ask again this session.

- **COMPACT AT 140000, ONLY AFTER ARTIFACTS:**

  Prompt size is `input + cache.read` of the latest assistant turn. Not `input` alone.

  Compact only when both are true:
  1. Prompt size is >= 140000.
  2. Durable artifacts exist: a commit on the feature branch (unmerged is fine), and any backlog, spec, steering, or resume doc this MDU changed is saved. Uncommitted reasoning is not an artifact.

  If (1) is true and (2) is not, do not compact. Write the artifacts first. If you cannot (tests red, conflict), stop and tell the user. Do not compact away the only copy of the plan.

  If both are true, request compaction, then stop expensive work for this turn:
  - OpenCode, when `OPENCODE_SESSION_ID` is set: `timeout 60 opencode api post /api/session/$OPENCODE_SESSION_ID/compact --data '{}'`
  - OpenCode, user alternative: **Ctrl+X**, then **C**.
  - Grok: tell the user to type `/compact`. Do not invent a grok shell command. `/compact-mode` is display density, not compaction.

  Compaction is lossy and uses this session's model once. That is cheaper than staying over the 200000 price cliff. Tell the user it was requested and applies before the next prompt.

- **CACHE MISS GATE:**

  A cache miss is the latest assistant turn with `cache.read` <= 1152 and `input` >= 80000. That pattern rebills the whole transcript. On the first turn of a session, skip this check.

  OpenCode: before any delegate, grep, commit, or read of source, if `OPENCODE_SESSION_ID` is set, check the latest assistant row (timeout 30). Use the session id from the environment. Do not print message content.

  On a cache miss, STOP. Do not delegate, grep, commit, or read more files this turn. Do not revert, delete, or abandon the branch. The stop is not a project failure. Work on disk is the source of truth.

  Then give the user these next steps, plus a filled resume block:
  1. Preferred: start a new session (OpenCode **Ctrl+X** then **N**. Grok: new session, no `--continue`). Paste the resume block. Say `continue <mdu-id> from the resume block`.
  2. To stay in this session: compact first (OpenCode **Ctrl+X** then **C**, or the API call above; Grok: type `/compact`), then reply with the exact phrase `compact and continue`.
  3. "keep going" is not an override. If they send `compact and continue` and the next check is still a cache miss, stop again and tell them compaction did not take — use step 1.

- **CODER HANDOFF:**

  Do not continue a coder child for a review reject or a follow-up fix. Spawn a new child. The brief is the verdict, file paths with line ranges, and the acceptance command. Do not paste file bodies. Do not pass the old session id.

  If a coder reports prompt size >= 140000, or step 40, do not send it more work. Spawn a fresh child with its handoff.

  Do not re-read implementation files to check a child. Read the child's summary. If you must look, one read of one path and line range, once per file per MDU. Never edit production code yourself.
```

## Coder block

Insert in files 4, 5, 6, and 7, in Safety constraints, before the existing Step Limit bullet. Required verbatim phrases: `step 40`, `new child`, `140000`.

```markdown
- **Context cap:** At step 40, stop implementing even if the task is incomplete. Commit whatever is green on the feature branch. Return a handoff: files touched, what is left, failing command if any, and file paths with line ranges. Do not keep editing. If `OPENCODE_SESSION_ID` is set and the latest assistant turn has `input + cache.read` >= 140000, stop the same way immediately. Do not compact the parent session yourself.
- **Review-reject:** If this brief is a review reject, a follow-up fix, or a continuation of a long session, do not continue. Return immediately and tell the orchestrator to spawn a new child. The return text must include the phrase `new child`, the reject summary, the file paths with line ranges, and the acceptance command. Do not paste file bodies.
```

## ROLE_KEYWORDS

In `scripts/lib/validate.py`, extend:

- `"orchestrator"`: add `("140000",)`, `("continue this session across mdus",)`, `("cache miss",)`, `("compact and continue",)`. The parity check lowercases, so the phrase in the prompt may keep its original case.
- `"just-code"`: add `("step 40",)`, `("new child",)`, `("140000",)`.

## Tests

Add assertions (new test or extend an existing one) that files 1, 2, 4, 5, 6, and 7 contain the required phrases for that role. Run `python3 -m pytest tests/ -q` from `open-agent-definitions`. Do not lower existing tests.

## Out of scope

- A supervisor that shells out to headless `opencode run` / `grok` sessions.
- Changing `compaction.buffer` globally (that is a fraction of each model's limit; grok-4.7 would still compact far above 140000).
- Model routing / "use Grok when Go is tight". Leave that line alone.
- Editing `build/`, deploying, or committing. The orchestrator does those after review.
