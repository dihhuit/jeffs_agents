---
name: session-introspect
description: Extract signals from the current OpenCode, Grok, or Claude session (review-reject streaks, long cycles, token hotspots, repeated tool errors) and turn them into agent-definition suggestions. Use after an MDU or when improving prompts from run evidence.
license: Unlicense
metadata:
  audience: [introspector, orchestrator]
---

# Session Introspection

Use this skill after an MDU finishes (or after any non-trivial task) to read the
*current* session logs, detect process friction, and produce concrete, durable
suggestions for the orchestrator. The outputs are suggestions only — **never edit
agent definitions or source code**.

## When to run

- After a code review comes back with rejections.
- After QA reports FAIL more than once.
- After any subagent runs for a long time, burns many tokens, or stalls.
- At the end of every MDU, before commit.

## Log locations (verified on this machine)

| Harness | Path | Notes |
| --- | --- | --- |
| OpenCode | `~/.local/share/opencode/opencode.db` | SQLite; v1 tables `session`, `message.data` JSON, `part.data` JSON; v2 tables `session_v2`, `session_message.data` JSON with a typed `content` array — `text` (`{type, text}`), `reasoning` (`{type, text, state, time}`), `tool` (`{type, id, name, executed, state, time}` where `state` is `{status, input, metadata}`) |
| Grok | `~/.grok/sessions/<urlencoded-cwd>/<session-id>/` | `summary.json`, `events.jsonl`, `chat_history.jsonl` |
| Claude | `~/.claude/projects/<cwd-with-slashes-as-dashes>/<sessionId>.jsonl` | records have `type`, `timestamp`, `message.usage`, `message.model` |

Child subagent sessions have `parent_id` set in OpenCode. The current work tree is
the orchestrator session plus its children. If the newest session for the cwd has
a `parent_id`, analyze that parent and all sessions whose `parent_id` equals it.

## How to run the helper

Try these paths in order until the script is found:

1. `skills/session-introspect/scripts/session_signals.py` (repo checkout)
2. `~/.config/opencode/skills/session-introspect/scripts/session_signals.py`
3. `~/.grok/skills/session-introspect/scripts/session_signals.py`

CLI:

```bash
python3 session_signals.py [--cwd DIR] [--session-id ID] [--harness auto|opencode|grok|claude] [--manifest PATH]
```

It prints one JSON object to stdout and exits 0 even when logs are missing. If
logs are missing, a note is added to the `notes` array and signals may be empty.

### OpenCode store selection and `info`

Without `--session-id` the script compares the two OpenCode stores (`session`,
`session_v2`) using each store's freshest `time_updated` row for the cwd (the
cwd itself or any ancestor directory). v2 is the live schema and wins ties and
near-ties (within 5 minutes); v1 is used only when it is clearly fresher. A note
reads `store selected: v2 (newest …; v1 newest …)`.

The JSON object also carries an additive `info` object (top-level `harness`,
`session_id`, and `cwd` are unchanged for compatibility):

- `store` — `"v1"`, `"v2"`, or `""` (nothing matched).
- `store_candidates` — only when `--session-id` was omitted:
  `[{"store": "v1", "id": …, "newest": …}, {"store": "v2", …}]`.
- `time_range` — `{"oldest": …, "newest": …}` UTC ISO-8601 for the selected
  tree, `null` when the tree has no positive timestamps.
- `v2_extraction` — present whenever a v2 tree was selected:
  `{"messages": N, "text_events": N, "tool_events": N, "text": true,
  "tools": true, "permission": false}`. The booleans are capability constants
  (text and tool extraction on, permission extraction unavailable); the counts
  are what was actually extracted from `content` parts.

#### v2 `content` extraction and its opaqueness notes

On a v2 tree, message text comes from `text` parts only — `reasoning` parts
are chain-of-thought and are **never** counted as verdicts. Each finalized
`tool` part (`state.status` not `running`/`streaming`, with a non-empty `name`)
becomes its own synthetic `role="tool"` event, so per-call tool detectors count
calls rather than messages. Those synthetic events are excluded from
`metrics.agents` message/token/duration rows and from `long_cycle`'s event
count.

Two notes keep a structural zero from reading as a clean run. Both are
exit-0 notes, not errors:

- always on a v2 run with events: `v2 permission extraction: none (permission
  table is project-scoped, not session-scoped); permission_thrash reads zero —
  treat as UNKNOWN`.
- when assistant rows exist but none carried extractable text: `v2 text
  extraction: none of <N> assistant message(s) carried extractable text;
  text-based signals read zero — treat as UNKNOWN`.

Rows missing `content` or `tokens` degrade gracefully (empty text, zero token
counters); unparseable `data` rows are skipped.

With `--session-id` the id pins the tree and no comparison runs; a session whose
directory is the cwd **or any ancestor of the cwd** matches. If the id exists
only under an unrelated directory the script keeps `session_id` empty, emits no
events and adds `session id <S> belongs to <D>, not <cwd>` (plus `propose parent
as root: rerun with --session-id <P>` and a children-under-cwd hint when those
apply). That is still an exit-0 result: read the `notes` array, not the exit
code, and treat the empty `session_id` as unknown.

## Signal kinds

The script emits these signal types:

- `review_reject_streak` — one reviewer **family** emitted 2+ consecutive rejections before an approval; rotated tier variants (`-pro`/`-mid`/`-premium`/`-free`) pool, and the evidence lists them. Bare `REJECT` verdicts count.
- `long_cycle` — per-agent active time (sum of gaps < 10 min) exceeded 8 min (warn) or 15 min (high); wall clock is recorded but not acted on.
- `token_hotspot` — an agent consumed >= 80k tokens, or >= 40% of session tokens and >= 20k.
- `cache_miss` — a turn with `cache.read` <= 1152 and `input` >= 80000. The transcript was rebilled. (family-pooled across tier variants)
- `long_context` — a turn with `input + cache.read` >= 140000. High if any turn is >= 200000. (family-pooled across tier variants)
- `expensive_model` — a bulk role (default coding, test, standard review, QA, devops, research, UI — including the `-free` tier) ran on grok-4.7, glm-5.2, or kimi-k3. Orchestrator, architecture, and mid/pro roles are not this signal.
- `repeated_tool_error` — same agent+tool errored >= 3 times. (family-pooled across tier variants)
- `permission_thrash` — >= 5 permission requests in the session. On an OpenCode **v2** store this reads zero **by construction** (the `permission` table is project-scoped, not session-scoped): treat it as UNKNOWN, never as clean, and derive permission friction from the run narrative/manifest instead.
- `context_reread` — same agent read/grepped the same path >= 4 times. (family-pooled across tier variants)
- `qa_fail_repeat` — a standalone verdict line `QA GRADE: FAIL` (case-insensitive, line-anchored) in >= 2 messages, family-pooled. A message quoting the format instruction mid-line no longer counts.
- `stalled_subagent` — >= 10 min gap between consecutive events.
- `fix_loop` (manifest) — `fix_iterations >= 2`.
- `phase_fail_streak` (manifest) — same phase failed >= 2 times.

**On OpenCode v2 stores**, text- and tool-dependent kinds
(`review_reject_streak`, `qa_fail_repeat`, `repeated_tool_error`,
`context_reread`) are live via `text` parts (reasoning excluded) and finalized
`tool` parts — this is new in the v2 `content` extraction. The cost kinds
(`cache_miss`, `long_context`, `expensive_model`, `token_hotspot`) are also
live, but they read `tokens`/model rather than `content` parts and were already
live before that extraction.
`permission_thrash` alone reads zero by construction and must be treated as
UNKNOWN. Before reading any zero as a clean result, check
`info.v2_extraction` and the two opaqueness notes above — a v2 tree that
extracted no text at all says so and is not a clean run.


## Hard rule

**Suggest, don't edit definitions.** The introspector writes durable artifacts
(`agent-improvements.md` and `runs/<mdu-id>/introspection.md`) and returns a short
report to the orchestrator. The orchestrator folds `apply_now` items into the next
loop. Only the user may change agent definition files.

Review mode is a user-invoked prompt mode of the same agent, not a second script.
It proposes concrete definition diffs and writes files only after the user says
the exact phrase `apply the definition diffs`.

## Redaction

The script redacts strings that look like API keys, tokens, secrets, or passwords
before printing JSON. Never paste raw log output without checking it first.
