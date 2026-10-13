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
| OpenCode | `~/.local/share/opencode/opencode.db` | SQLite; tables `session`, `message.data` JSON, `part.data` JSON |
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

## Signal kinds

The script emits these signal types:

- `review_reject_streak` — reviewer agents emitted 2+ consecutive rejections before an approval.
- `long_cycle` — per-agent span exceeded 8 min (warn) or 15 min (high).
- `token_hotspot` — an agent consumed >= 80k tokens, or >= 40% of session tokens and >= 20k.
- `repeated_tool_error` — same agent+tool errored >= 3 times.
- `permission_thrash` — >= 5 permission requests in the session.
- `context_reread` — same agent read/grepped the same path >= 4 times.
- `qa_fail_repeat` — QA text contained `FAIL` at least twice.
- `stalled_subagent` — >= 10 min gap between consecutive events.
- `fix_loop` (manifest) — `fix_iterations >= 2`.
- `phase_fail_streak` (manifest) — same phase failed >= 2 times.

## Hard rule

**Suggest, don't edit definitions.** The introspector writes durable artifacts
(`agent-improvements.md` and `runs/<mdu-id>/introspection.md`) and returns a short
report to the orchestrator. The orchestrator folds `apply_now` items into the next
loop. Only the user may change agent definition files.

## Redaction

The script redacts strings that look like API keys, tokens, secrets, or passwords
before printing JSON. Never paste raw log output without checking it first.
