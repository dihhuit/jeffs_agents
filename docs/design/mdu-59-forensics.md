# MDU-59 Forensics Evidence Sweep — suburb_sim dispatch truth

**Status:** raw evidence only. No interpretation beyond what the rows show (interpretation is routed back to the orchestrator). (the Resolution section at the end adds interpretation and classification)
**Date of sweep:** 2026-11-13 (MST).
**Evidence source:** `/home/dihhuit/.local/share/opencode/opencode.db` (SQLite, ~2.7 GB), opened **read-only** for every query via the URI `file:/home/dihhuit/.local/share/opencode/opencode.db?mode=ro`, every call wrapped in `timeout 300`. No write ever issued to the store.
**Project source (disk, read-only):** `/mnt/FastSSDXFS/projects/suburb_sim` (stat/ls/find only; `/home/dihhuit/projects` resolves to `/mnt/FastSSDXFS/projects`, verified with `readlink -f`, so both path prefixes are the same directory).

**Schema facts used:** legacy V1 sessions are not in `session_v2`/`session`/`session_part`/`message`/`job`; their rows live in `session_message(id, session_id, type, seq, time_created, time_updated, data)` where `data` is JSON (`$.agent`, `$.model.id`, `$.model.providerID`, `$.text`, `content[]` with `type: tool` parts carrying `name` + `state.input` + `state.metadata`).

Timestamps below are quoted as raw epoch-ms with a UTC conversion (host local zone is `America/Phoenix`, MST = UTC-7).

---

## Q1. THE QUOTE

**Finding: the exact sentence exists once in the whole shortlist, in the target session.**

SQL:

```sql
select id, time_created, json_extract(data,'$.agent'), json_extract(data,'$.model.id'), json_extract(data,'$.model.providerID')
from session_message
where session_id='ses_e378d7aa2ffeFWkHd8BXgC7aqb'
  and (data like '%not run shell%' or data like '%full HLD brief%' or data like '%on xAI%' or data like '%cutting the backlog%');
```

Result (2 rows; the second matched only on `on xAI` in its reasoning, see §5):

```
msg_1cadf5326001ttJHxG0tzP2SPy|1794404995888|grokestrator|grok-4.7|xai
msg_1cae0fdd6001Jq7RtBozMrVJn8|1794405105120|grokestrator|grok-4.7|xai
```

Uniqueness check of the verbatim sentence (`grep -c "The architect is on xAI and can write the design"` over both rows' JSON) returns **1**.

**The quote** — `session_message.id = msg_1cae0fdd6001Jq7RtBozMrVJn8`, `session_id = ses_e378d7aa2ffeFWkHd8BXgC7aqb`, `type = assistant`, `time_created = 1794405105120` (2026-11-11 13:51:45 UTC / 06:51:45 MST), `time_updated = 1794406171909`, `$.time.completed = 1794406171907`:

```text
The architect is on xAI and can write the design, not run shell. I'll send a full
HLD brief and wait for the documents before cutting the backlog.
```

(146 chars, `content[1]`, `type:text`. The same message row also holds `content[0]` = reasoning and `content[2]` = the `subagent` tool call — see §2. So the claim and the dispatch are in **one** message.)

Row fields on that message: `$.agent = "grokestrator"`, `$.model = {"id":"grok-4.7","providerID":"xai","variant":"default"}`.

**The surrounding user request that prompted it** — nearest preceding `type='user'` row, `msg_1cade710e0016PQPTS8fXXvRkx`, `time_created = 1794404938112` (2026-11-11 13:48:58 UTC):

```text
Ok, switched to Grokestrator. Kick off the architect to do the full e2e HLD.
Once it's done, your next job is to build the deep, complete backlog of tasks
that get us all the way to the finished v1 of the game. Then, give me a resume
block to start the first MDU.
```

Immediately before that user message sits a `model-switched` row, `msg_1cade7135001fv2ALggRUPXWe5`, `time_created = 1794404938037`:

```json
{"time":{"created":1794404938037},"model":{"id":"grok-4.7","providerID":"xai"},
 "previous":{"id":"grok-4.7","providerID":"opencode-go","variant":"xhigh"}}
```

i.e. the hand-off to grokestrator also switched the **primary** model from `opencode-go/grok-4.7` (variant `xhigh`) to `xai/grok-4.7`.

**Session context:** the target session began as `inception` on `grok-4.7`/`opencode-go` (first assistant row `msg_1c8728625001QGA3ggsJ3Lnf3v`, 1794364311086, 2026-11-11 02:31:51 UTC) and only became `grokestrator` at 13:48:58 UTC. All 35 `inception` rows in the shortlist are `grok-4.7`/`opencode-go` (1 row `deepseek-v4.1-flash`).

---

## Q2. THE ARCHITECT DISPATCH

**Finding: YES — exactly one architect-design subagent was dispatched from the target session, it ran to completion, and it was the `grok-architect-premium` variant (xAI), not the stock `architect`.**

SQL:

```sql
select session_id, id, time_created, data from session_message
where session_id in (<58 ids from /tmp/opencode/mdu-59/suburb_sessions.txt>)
  and data like '%"name":"subagent"%' order by time_created;
```

71 rows across the shortlist (full inventory printed by the sweep script to `/tmp/opencode/mdu-59/subagent_calls.txt`). **In the target session there is exactly one** (tool-part counter over the target's 70 rows: `question 24, read 13, shell 11, glob 9, write 6, grep 6, execute 5, webfetch 4, websearch 2, skill 2, subagent 1`).

**The dispatch** — inside `msg_1cae0fdd6001Jq7RtBozMrVJn8` (same row as the quote), tool part `content[2]`, `name = "subagent"`, id `call-e2e76102-5e89-4884-8f8d-dd32fd330b82-62`:

```json
"state": {"status": "completed",
  "input": {"agent": "grok-architect-premium", "description": "Full e2e game HLD",
            "prompt": "Produce the full end-to-end high-level design for the suburb_sim game. Design only. No production code, ..."},
  "metadata": {"sessionID": "ses_e351e3922ffeZUMTsCdTw303R8", "status": "completed", "truncated": false}}
```

Prompt excerpt (from the same `state.input.prompt`, lines 1–6):

```text
Produce the full end-to-end high-level design for the suburb_sim game. Design only.
No production code, no Godot project, no scenes, no scripts, no tests, no git init,
no commit, no push, no questions to the user.

Working directory is the project root. Read `spec.md` in full before writing. It is
binding. Confirmed decisions stay. The Tunables table (T-01 through T-27) stays data,
not hard-coded constants. Do not reopen interview decisions.

You cannot run shell. Do not try. You may read, grep, glob, websearch, and webfetch.
```

**The child session `ses_e351e3922ffeZUMTsCdTw303R8` (13 rows)** — SQL: `select id, time_created, type, json_extract(data,'$.agent'), json_extract(data,'$.model.id'), json_extract(data,'$.model.providerID') from session_message where session_id='ses_e351e3922ffeZUMTsCdTw303R8' order by time_created;`

| ts (epoch-ms) | type | agent | model.id | providerID |
|---|---|---|---|---|
| 1794405156615 | user | — | — | — |
| 1794405156632 … 1794406163576 (11 rows) | assistant | `grok-architect-premium` | `grok-4.7` | `xai` |
| 1794406171887 | idle | — | — | — (`outcome: "succeeded"`) |

**Brief-echo match (linkage #1):** the child's first user row opens verbatim with the parent's prompt:

```text
You are a subagent spawned by another session.
Produce the full end-to-end high-level design for the suburb_sim game. Design only.
No production code, no Godot project, no scenes, no scripts, no tests, no git init,
```

Timing is consistent end-to-end: dispatch row created 13:51:45 UTC → child first row 13:52:36 → child `idle/succeeded` 14:09:31 (1794406171887) → parent message `$.time.completed = 1794406171907` (14:09:31). The child ran ~17 minutes and the parent waited for it.

**No `architect` (glm-5.2) dispatch exists in the target session's tree.** The stock `architect` agent *did* run elsewhere in the shortlist — 113 `architect`/`glm-5.2`/`opencode-go` rows, but only in these **other** child sessions: `ses_e2af67b71ffeCpIrxJQVRmVhcD` (9), `ses_e301face8ffemwZWXPnYMwfPtr` (16), `ses_e321d8286ffevmyZCjJwAmJ1cf` (22), `ses_e324757f8ffeDvhqr1nIQjFzaY` (7), `ses_e32720563ffentHeQpLIiYq7zg` (10), `ses_e328c3608ffecsF2dtnJwYZCs2` (33), `ses_e3296fe73ffeGPPzh2e6NBSUPx` (16) — all of them children of later MDU-loop parents (see §4), none of them in the target's tree.

Agent/model distribution over all 1435 rows of the 58-session shortlist:

```sql
select type, json_extract(data,'$.agent'), json_extract(data,'$.model.id'), json_extract(data,'$.model.providerID'), count(*)
from session_message where session_id in (<58 ids>) group by 1,2,3,4 order by 5 desc;
```

```
assistant|orchestrator|glm-5.3-flash|opencode-go   290   assistant|architect|glm-5.2|opencode-go   113
assistant|grokestrator|grok-4.7|xai                198   assistant|test-agent|deepseek…|opencode-go  58
assistant|just-code|deepseek…|opencode-go          180   assistant|introspector|mimo…|opencode-go    54
assistant|code-reviewer|mimo…|opencode-go          130   assistant|just-code-mid|kimi…|opencode-go    50
assistant|qa|mimo…|opencode-go                    128   assistant|devops|mimo…|opencode-go          50
assistant|grok-architect-premium|grok-4.7|xai       11   assistant|inception|grok-4.7|opencode-go    35
user 65 | idle 61 | system 4 | synthetic 2 | model-switched 2 | agent-switched 1
```

---

## Q3. THE HLD ARTIFACT

**Finding: the HLD was WRITTEN BY THE CHILD (`ses_e351e3922…`), not by the parent; the parent only READ it afterwards.**

SQL (write/edit tool parts across the shortlist whose input path contains `docs/`):

```sql
select session_id, id, time_created, data from session_message
where session_id in (<58 ids>)
  and (data like '%"name":"write"%' or data like '%"name":"edit"%')
  and data like '%docs/%';
```

`docs/architecture/hld.md` and the ADRs — **every write is from `ses_e351e3922ffeZUMTsCdTw303R8`** (the HLD child):

| ts (UTC) | tool | path |
|---|---|---|
| 2026-11-11 13:56:47 | write | `docs/architecture/hld.md` |
| 2026-11-11 14:06:26 | write ×10 | `docs/adr/0001-renderer.md` … `docs/adr/0010-perception-and-grade.md` |
| 2026-11-11 14:09:11 ×2, 14:09:15 | edit ×3 | `docs/architecture/hld.md` |

Parent (`ses_e378d7aa2…`) write parts — **none touch `docs/`** (SQL: same filter restricted to the target session):

```
1794402084378 write  /mnt/FastSSDXFS/projects/suburb_sim/spec.md
1794406345203 write  /home/dihhuit/projects/suburb_sim/FEATURE_BACKLOG.md
1794406434227 write  /home/dihhuit/projects/suburb_sim/.agents/memory/project.md
1794406434227 write  /home/dihhuit/projects/suburb_sim/.agents/memory/decisions.md
1794406434227 write  /home/dihhuit/projects/suburb_sim/.agents/memory/session-ses_e378d7aa2ffeFWkHd8BXgC7aqb.md
1794406434227 write  /tmp/opencode/resume_mdu0.json
```

Parent **reads** of the HLD (grep/read tool inputs, all after the child finished):

```
14:09:42 grep  ^#{1,3}   /home/dihhuit/projects/suburb_sim/docs/architecture/hld.md
14:09:47 read  offset 1   limit 165
14:09:47 read  offset 800 limit 80
14:09:54 read  offset 165 limit 250
14:10:13 read  offset 408 limit 400
```

**Disk corroboration** (`stat`, read-only):

```
2026-11-11 07:09:23 -0700  /mnt/FastSSDXFS/projects/suburb_sim/docs/architecture/hld.md   (43387 bytes)
2026-11-11 07:06–07:09 -0700  docs/adr/0001…0010 (10 files)
```

07:09:23 MST = 14:09:23 UTC, i.e. inside the child's final edit window (created 14:09:15, message completed 14:09:23.777). File mtime matches the child's last edit to the second. `head -3 hld.md` → `# Suburb Sim — High-Level Design / Status: design only. Binding input is spec.md …`.

**Other `docs/design/*` files (different, later session trees):**

| file (mtime MST) | written by | parent that dispatched it |
|---|---|---|
| `docs/design/mdu-0-godot-pin.md` (11-11 18:44) | child `ses_e3296fe73ffeGPPzh2e6NBSUPx` (architect/glm-5.2) write at 1794447779288 | `ses_e3299afcaffeOD0PxbPYPmBhIA` ("Design mdu-0 Godot pin") |
| `docs/design/mdu-1-clock-rules.md` (11-11 21:12) | child `ses_e32720563ffentHeQpLIiYq7zg` | `ses_e32744c97ffeQevgPkQdnFljzc` |
| `docs/design/mdu-2-skip-decay-save.md` (11-11 21:12) | child `ses_e324757f8ffeDvhqr1nIQjFzaY` | `ses_e324af9c4ffeFAEuSrcZsYoUM2` |
| `docs/design/mdu-3-schedule-eval.md` (11-12 07:21) | child `ses_e301face8ffemwZWXPnYMwfPtr` (write + 2 edits) | `ses_e30249172ffencRRw4Wf1maPKF` |
| `docs/design/mdu-4-meter-grade-burns.md` (11-13 06:19) | child `ses_e2af67b71ffeCpIrxJQVRmVhcD` (architect/glm-5.2) write at 1794575477… window | `ses_e2af9fb2cffeprrIVW0qZsmGlm` (dispatch still `running` at snapshot) |
| `docs/architecture/import-checklist.md` (11-11 18:47) | child `ses_e3291339effewf0OrpMuIYeIDs` (just-code) | `ses_e3299afcaffeOD0PxbPYPmBhIA` |

Some shortlist sessions belong to the **agents-repo** trees and wrote there instead (e.g. `ses_e328c3608…` → `open-agent-definitions/docs/design/mdu-56-pi-port.md`, `ses_e321d8286…` → `…/mdu-60-qa-write-access.md`); those are not suburb_sim artifacts.

---

## Q4. TREE MAP

Linkage evidence used: (1) `state.metadata.sessionID` on `subagent` tool parts (authoritative), (2) brief-echo of the child's first user row against the parent's `state.input.prompt` (used only where metadata was null), (3) path/agent-of-record in the child's own rows.

**Top-level (user-initiated) sessions in the shortlist — 12:**

| session | role | first user row (truncated) | dispatches |
|---|---|---|---|
| `ses_e37971c36ffevR2v7LR19C0sKF` | **abandoned first attempt** at the same project start ("I interrupted due to the gateway being overloade, and switched models") — separate user session, 7 rows, never dispatched | "Ok inception. New workspace. We're making a simple(ish) 3d computer game…" | 0 |
| `ses_e378d7aa2ffeFWkHd8BXgC7aqb` | **target**: inception → grokestrator, suburb_sim | same "Ok inception. New workspace…" (restart, 02:31:51 UTC) | 1 child |
| `ses_e354caa59ffeOJNQBFI1dMCTgK` | agents-repo MDU-58 "Grokception" — **the user already re-reported this same grokestrator sentence here** | "In my recent session in suburb_sim, the Grokestrator agent said the following when I asked…" | 8 children |
| `ses_e3299afcaffeOD0PxbPYPmBhIA` | suburb mdu-0 (Godot pin) | "Ok, I saw the note about git. I created a remote repo on github…" | 10 children |
| `ses_e3298eb27ffe26mrOwhldIcreM` | agents-repo MDU-56 (pi port) | "OK, new high-priorty issue: the sprite_generator session is stuck…" | 8 children |
| `ses_e32744c97ffeQevgPkQdnFljzc` | suburb mdu-1 (clock rules) | run-manifest JSON `{ "mdu_id": "mdu-1" … }` | 8 children |
| `ses_e324af9c4ffeFAEuSrcZsYoUM2` | suburb mdu-2 (skip decay) | run-manifest `{ "mdu_id": "mdu-1" … }` | 8 children |
| `ses_e3224f1dcffeQMyZGKyIUsIxnZ` | agents-repo MDU-60 | run-manifest `{ "mdu_id": "mdu-60" … }` | 10 children |
| `ses_e3025295affeayYpYS7e8lKm1w` | agents-repo MDU-61 | "I also noticed my agents are now submitting PRs instead of merging…" | 12 children |
| `ses_e30249172ffencRRw4Wf1maPKF` | suburb mdu-3 (schedule eval) | run-manifest `{ "mdu_id": "mdu-2" … }` | 9 children |
| `ses_e2af9fb2cffeprrIVW0qZsmGlm` | suburb mdu-4 (meter rules), dispatch `running` at snapshot | run-manifest `{ "mdu_id": "mdu-3" … }` | 1 child |
| `ses_e2afa3a1bffelTZ298WANuQD8O` | agents-repo MDU-59 (this sweep) | run-manifest `{ "mdu_id": "mdu-59" … }` | 1 child (`running`, `child=None`) |

**Children inside the shortlist: 44 of the 58 ids** appear as `metadata.sessionID` of some `subagent` call (exact list produced by the sweep script; e.g. `ses_e351e3922…` ← target, `ses_e3296fe73…`/`ses_e3291339…`/`ses_e328ca75b…` ← mdu-0, `ses_e32720563…` ← mdu-1, … `ses_e2fe9dd7d…` ← mdu-3 introspector).

**Not linked by metadata: 3 ids**

- `ses_e2af67b71ffeCpIrxJQVRmVhcD` — **brief-echo link to `ses_e2af9fb2c…`**: its first user row is `You are a subagent spawned by another session. / You are the architect for suburb_sim mdu-4. Write ONE design doc…` and it wrote `docs/design/mdu-4-meter-grade-burns.md`. The parent's dispatch row (`msg_1d508a986001…`, ts 1794575477136, agent `architect`, desc "Design mdu-4 meter rules") still has `metadata.sessionID = null` and `status = running` at snapshot time → **HIGH-CONFIDENCE link, metadata UNRESOLVED (dispatch in flight)**.
- `ses_e37971c36…` — separate aborted user session (see table).
- `ses_1d664be55ffe37hkjRoVengXRe` — unrelated `nemotron-research` "capital of France" test row from 2026-05 that merely contains the word "suburb"; **false-positive member of the 58**.

**Depth:** the tree is 2 levels in the evidence (user session → subagent session). No `subagent` tool call was found **inside** any child session, so no 3rd level exists in the shortlist.

**Sibling-cluster note (as hypothesised):** the id prefixes are *not* a reliable ordering signal — e.g. `ses_e351e3922…` (the target's child, 11-11) sits numerically far from `ses_e378d7aa2…` (its parent) while `ses_e2af…`/`ses_e2ff…`/`ses_e30…`/`ses_e32…` are just later-created sessions across both projects. Creation order ≈ timestamp order; use `time_created`, not prefix.

---

## Q5. THE "on xAI" BELIEF

**Finding: the suburb_sim project defines NO local agent override at all — no `opencode.json`, no `.opencode/`, no `agents/`, no `AGENTS.md`, and zero files under the project contain the string `xai`.**

```bash
find /mnt/FastSSDXFS/projects/suburb_sim -maxdepth 2 \( -name 'opencode*.json' -o -name '.opencode' -o -name 'AGENTS.md' \) -print   # → empty
ls -la /mnt/FastSSDXFS/projects/suburb_sim | grep -iE 'opencode|agents|\.claude'   # → only ".agents" (memory dir)
grep -rl 'xai' /mnt/FastSSDXFS/projects/suburb_sim --include='*.json' --include='*.md'   # → no matches
ls /home/dihhuit/projects/suburb_sim/opencode.json   # → "no opencode.json at old path" (same dir via symlink)
```

`/mnt/FastSSDXFS/projects/suburb_sim/.agents/` contains only `memory/` (session memory files, no config).

**The real definitions live in the user's global config** `~/.config/opencode/opencode.json` (read-only `jq`), verbatim excerpts:

```json
"architect": {"mode":"subagent","model":"opencode-go/glm-5.2",
  "permissions":[{"action":"edit","resource":"*","effect":"allow"},
                 {"action":"shell","resource":"*","effect":"deny"}, …]}

"grok-architect-premium": {"mode":"subagent","model":"xai/grok-4.7",
  "permissions":[{"action":"edit","resource":"*","effect":"allow"},
                 {"action":"shell","resource":"*","effect":"deny"}, …]}

"grokestrator": {"mode":"primary","model":"xai/grok-4.7",
  "permissions":[{"action":"edit","resource":"*","effect":"allow"},
                 {"action":"shell","resource":"*","effect":"allow"}]}
```

So: stock `architect` = **`opencode-go/glm-5.2`** (shell deny), the xAI-billed variants = `grok-architect` / `grok-architect-premium` = **`xai/grok-4.7`** (shell deny), `grokestrator` itself = **`xai/grok-4.7`**.

**How the belief formed — reasoning trace in `msg_1cadf5326001ttJHxG0tzP2SPy` (grokestrator/xai, 13:49:55 UTC, i.e. the message right before the quote), `content[0]` reasoning excerpt:**

```text
Cache read returned 1152. Proceeding with the architect.

Input 7914 is below the 80000 cache-miss threshold, so proceeding. The orchestrator
is running grok-4.7 via opencode-go rather than xai, which is unexpected for a
Grokestrator setup.

Grok-named agents must run on xAI models. The Go architect is not an option. I will
use grok-architect or grok-architect-premium instead. I need to verify the premium
agent is configured for xai.
```

And the tool-fact half of the quote is config-true for *both* architect variants (shell `deny`), quoted from the dispatch prompt: `You cannot run shell. Do not try.`

**Ground truth for the report:** the dispatch that actually ran was `grok-architect-premium` on `xai/grok-4.7` (§2), so "the architect is on xAI" was *accurate about the agent it chose* while being *false about the stock `architect`* — the sentence names a generic agent but refers to the grok variant, with no project-level override to justify the conflation (§5).

---

## UNRESOLVED

| # | Item | Reason |
|---|---|---|
| U1 | `metadata.sessionID` for the mdu-4 architect dispatch (`ses_e2af9fb2c…` → `ses_e2af67b71…`) | dispatch row still `status=running` with `sessionID=null` at snapshot; linked by brief-echo only |
| U2 | Whether xAI was actually *billed* for the HLD run | no billing/usage tables consulted (out of evidence source); only `providerID=xai` on the model field is proven |
| U3 | First-message briefs for the other 43 children | not individually extracted; linkage rests on `metadata.sessionID` (authoritative) — cluster-level mapping only |
| U4 | Whether the user's reading ("architect did NOT run as an OpenCode subagent") was stated anywhere else in-session | only `ses_e354caa59…` (MDU-58) first message re-quotes the sentence; its body was not swept |
| U5 | `ses_1d664be55ffe…` and any other incidental 'suburb' matches in the 58-list | classified false-positive from row content; full-text justification per row not produced |
| U6 | Whether `job`-level parent/child rows exist for these V1 sessions | pre-verified by the requester: `job.child_session_id` empty, `job`/`message`/`session_part` have no suburb rows — no further evidence available in the store |

## Appendix — scratch artefacts

All under `/tmp/opencode/mdu-59/` (not committed): `suburb_sessions.txt` (input), `ids.txt`, `ids_sql.txt`, `all_rows_meta.txt` (1435 rows: session, msg, ts, agent, model, provider, type), `target_all.txt` (target's 70 rows), `quote_rows.txt` (the two candidate quote rows), `subagent_calls.txt` (71 dispatch rows), `docswrites.txt` (docs write/edit rows), `user_prev.txt`, `prev_row.txt`.

## Resolution (2026-11-13, MDU-59)

**Direct answer to the user's original question:** Yes — the architect ran as a real dispatched subagent. The grokestrator dispatched `grok-architect-premium` (child session `ses_e351e3922ffeZUMTsCdTw303R8`) on `xai/grok-4.7`; the child wrote `docs/architecture/hld.md` plus `docs/adr/0001`–`0010` and completed at 14:09:31 UTC on 2026-11-11, and the parent read the HLD afterward. It was NOT the stock OpenCode `architect` (`opencode-go/glm-5.2`), and no stock-architect dispatch exists in the target session's tree (the later mdu-0 loop did dispatch the stock `architect`/glm-5.2 — see §2/§3). Design was written by the child session, not in-conversation — no 20261014-1-class violation.

**Classification: correct routing, misleading disclosure.**
- Routing was correct: suburb_sim has no project-level agent override (§5); the grokestrator's pre-dispatch reasoning correctly applied the "Grok-named agents run only on xAI models" rule; the dispatch tool call and the child's completed model rows prove a real run (§2).
- The wording defect: "The architect is on xAI and can write the design, not run shell" names a bare role word that collides across harnesses — in the OpenCode harness `architect` = `opencode-go/glm-5.2` (shell deny), in the Grok family `grok-architect*` = `xai/grok-4.7` (also shell deny, so the no-shell half was true for the variant actually used), and the base Grok mirror's model table (`grok/agents/orchestrator.md:172-173`) even labels bare `architect` as grok-4.7. A reader who knows the OpenCode table reads the sentence as false, or as "no subagent ran".
- Because the residue ambiguity lives in the prompt mirrors, the clause fix is a definition change and ships via the user-invoked apply path (`apply the definition diffs`), not inside MDU-59 (AC-5). The proposal is staged in `agent-improvements.md` under "Definition proposals" targeting all three orchestrator mirrors, per user decision 2026-11-13 (approval answered via the question tool in the MDU-59 session).

**Disposition:** docs clarification (this section) ships in MDU-59; the dispatch-truth clause is staged as a not-applied proposal; a dormant pin test (`tests/test_mdu_59_dispatch_truth.py`, written by test-agent in the same MDU) asserts the direct-answer line here and activates marker + normative-fragment checks for the clause when it is applied.
