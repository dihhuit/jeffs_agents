# MDU-51 · OpenCode v2 session-store text/tool extraction

Done looks like: `_collect_opencode_v2` in `skills/session-introspect/scripts/session_signals.py` interprets the `content` parts array of `session_message.data` so text- and tool-based detectors work on v2 session trees (backlog 20261101-3 part b); the script emits a machine-readable `info["v2_extraction"]` marker plus opaqueness notes so a structural zero can never masquerade as a clean run (part a, post-fix form); `skills/session-introspect/SKILL.md` discloses that text/tool kinds are live on v2 while `permission_thrash` stays UNKNOWN; a new `tests/test_mdu_51_v2_text_extraction.py` (hermetic sqlite fixtures, mdu-50 pattern) plus two pins in `tests/test_session_signals.py`; all 754 existing tests stay green; base and sibling-overlay `./build.sh` both run. No prompt, agent-definition, `opencode.json`, registry, or model-map rows change — no model re-probe required.

## 0. Surveyed files

`skills/session-introspect/scripts/session_signals.py` (full read, 1392 lines); `skills/session-introspect/SKILL.md`; `docs/design/mdu-50-session-signals.md` (house conventions; its §9.1 exclusion is what this MDU lifts); `tests/test_mdu_50_session_store_selection.py` (17 tests — the fixture pattern to reuse); `tests/test_session_signals.py` (`_event` helper L36-60 — a `role` kwarg already exists); `agent-improvements.md` L565-568 (entry 20261101-3, high, detector_gap); `.agents/memory/project.md` L75 (the "treat v2 zeros as UNKNOWN" guidance this design makes machine-readable); live-store probe results gathered by the orchestrator on 2026-11-01 (DB ~2.7 GB, 500 newest assistant messages sampled).

## 1. Live-probe facts (orchestrator probe 2026-11-01; reconciled against current code)

- **FACT 1** — v2 assistant `session_message.data` keys: `['time', 'agent', 'model', 'content', ('tokens')]`; `content` is an array of typed parts. 497/500 newest assistant messages carry `tokens`; 3 do not (too-fresh rows).
- **FACT 2** — part types across those 500 messages: `reasoning` 435, `text` 202, `tool` 737. Shapes: `{type:"text", text:"…"}`; `{type:"reasoning", text:"…", state:{reasoningField:…}, time:{…}}`; `{type:"tool", id, name, executed, state, time}` with `state` keys `['status','input','metadata']`. Tool statuses in the window: completed 699, error 35, streaming 2, running 1. `state.input` keys seen: path 407, command 258, limit 135, newString 132, oldString 132, offset 124, pattern 121, timeout 65, include 40, workdir 29, agent 20, description 20. `state.metadata` shapes (`{exit,status,truncated}` / `{truncated}` / `{files,truncated}` / `{matches,truncated}` / `{toolCalls,truncated}`) carry no error-message field. `streaming`/`running` marks a live in-flight call, observable when reading a live session.
- **FACT 3** — a separate `permission` table `(id, project_id NOT NULL, action, resource, time_created, time_updated)` is keyed by **project**, not session; no permission-shaped parts appear in `content[]`.
- **FACT 4** — the collector's existing query (`session_message WHERE session_id IN <tree ids> AND type='assistant' ORDER BY time_created`) is exactly right — verified at script L1056-1061. Extraction is a change in row interpretation, not new SQL.
- **FACT 5** — current detectors lean on text phrases (`REJECTION_PHRASES` incl. `"reject"`, L27-33; `QA_FAIL_VERDICT` line-anchored, L38) and tool fields the v2 collector never sets (`text=""` at L1081; no tool/tool_path/tool_error/permission_requested). Reviewer/QA messages DO quote verdicts in plain text parts — the mechanism by which MDU-50's genuine round-1 REQUEST CHANGES read `review_rejections: 0` (0/216 events carried text).

Code reconciliations (verified this design, beyond the probe):

1. Detector field usage: `text` → `review_reject_streak` (detector 1), `qa_fail_repeat` (7), `metrics.review_rejections` (L1268); `tool`+`tool_error` → `repeated_tool_error` (4); `tool`+`tool_path` → `context_reread` (6) — **the only reader of `tool_path`**; `permission_requested` → `permission_thrash` (5) — its only reader.
2. The v1 part loop (L954-984) is **not reusable** on v2 parts: it reads `part["state"]` as a *string* and args at `part["arguments"] or part["input"]`; v2 nests input under `state.input` and `state` is an object. A v2-specific part interpreter is required.
3. `_compute_metrics` counts `messages += 1` per event (L1262) — unguarded synthetic events would inflate per-agent message counts (agent-row names must stay exact, mdu-50 fact 4).
4. mdu-50 fixtures write v2 rows with **no `content`** (`_add_v2_message` in the store-selection test file): they become graceful-degradation pins, and the new guard note fires on them — its wording must not contain `v1` or `store selected` (pinned by `test_v2_only_rows_select_v2_without_v1_notes`).
5. `_strip_think` (L124) is applied inside `_is_rejection`/`_is_approval`, never in collectors — so v2 reasoning exclusion must happen at extraction time (D-1).

## 2. D-1 — text composition: `text` parts only, `reasoning` excluded

Per assistant message, event text = `" ".join()` of every `content` item with `type == "text"` and a str `text` field. Reasoning parts are excluded entirely.

- Rationale: chain-of-thought must not count as verdicts — that is exactly `_strip_think`'s v1 semantics; v2 separates CoT structurally, so the strip happens at extraction instead of after. Including reasoning (435 vs 202 parts — it dominates) would reintroduce the 20261021-5 false-positive class at scale: CoT routinely quotes "QA GRADE: FAIL" and deliberates about rejecting while the visible text approves. Reviewer/QA verdicts demonstrably live in `text` parts (FACT 5).
- No collector-side `_strip_think` call: detectors already strip, and text parts carry no `<think>` markup; keeps collector behavior parallel to v1 (raw text in, detectors strip).
- Scope stays `type='assistant'` rows only. User rows stay excluded: the orchestrator relays reviewer verdicts in its own messages, and counting those would misattribute rejections to the orchestrator (never a reviewer agent) or double-count.
- Join with `" "` matches the v1 collector's part join (L961).

## 3. D-2 — event shape: message event + synthetic `role="tool"` events per tool part

Each parsed row emits **one message event** (text from D-1, tokens/model/t exactly as today, tool fields unset) **plus one synthetic event per finalized tool part**: `role="tool"`, `agent` copied from the message, `t` = the message's `time_created` seconds, `text=""`, `tokens_in/out/cache_read=0`, `model=""`, and `tool`/`tool_path`/`tool_error` per D-3. `permission_requested` is always False (D-5). Emit the message event first, then its tool events in content order — `collect_signals` sorts stably by `t`, so same-`t` order is deterministic.

- Rationale vs the alternative (attach tool fields to the message event, v1-style last-part-wins): the live distribution is 737 tool parts across 500 messages (1.47/message) — multi-part messages are common. Attach-to-message collapses within-message parallel calls to one tool name and one target and caps errors at 1 per message, undercounting `repeated_tool_error` and `context_reread` exactly where they cluster (batched reads, parallel edits). Synthetic events count per tool call, which is what both detectors' thresholds mean.
- Consequences handled by D-4 (metrics/duration guards). Event-count growth is bounded (~1.5× on the mdu-50 tree: 216 → ~530) and `collect_signals` is O(n log n) — no performance concern.
- Tokens stay on the message event only — tokens on tool events would double-bill `token_hotspot`, `cache_miss`, `long_context`.

## 4. D-3 — tool-part interpretation and the detector derivations

`state.status` is the single authoritative field:

- **Skip** parts with `state.status` in `("running", "streaming")` — un-finalized mid-flight observations; a later re-read sees the final status, and an abandoned in-flight call has no outcome worth counting. Also **skip** parts with no non-empty `name` (no detector keys without a name).
- `tool_error = state.status in ("error", "failed")` — `"failed"` kept for v1 vocabulary parity. Live sample: 35 error parts (e.g. `edit` with `status:"error"`).
- `tool = str(name)`.
- **Target selection** — new `_v2_tool_target(name, state.input) -> str | None`: if `"grep" in name.lower()`, prefer `("pattern", "path", "filePath", "file", "command")`; else `("path", "filePath", "file", "command")`; first non-empty value, `str()`-ed. Rationale: `tool_path` feeds only `context_reread`, and grep inputs carry `pattern` (121 live occurrences) — without pattern-preference, N *distinct* greps pool under the key `(agent, "grep")` and false-fire at threshold 4. Pattern-first mirrors the detector's own read/grep bifurcation. The v1 preference list stays untouched (v1 behavior is pinned by existing tests; its grep pooling is a pre-existing quirk, §9).
- `state.metadata` is not parsed (no error-message field exists in any observed shape); `repeated_tool_error` evidence stays count-based. `executed` is ignored — semantics unverified (§9).
- **`repeated_tool_error` derivation**: detector 4 keys `(family(agent), tool)` over events with `tool_error` — synthetic events make it per-call correct; mdu-50 family pooling applies unchanged. **`context_reread` derivation**: detector 6 over tool events whose name contains `read`/`grep`, keyed `(family(agent), target or tool)` — the target per the rule above.

## 5. D-4 — guards so synthetic events cannot distort metrics or durations

- `_compute_metrics`: skip events with `role == "tool"` — per-agent `messages`, token sums, and `duration_s` stay per-assistant-message; `metrics["agents"]` rows keep exact names and honest counts.
- `collect_signals` detector 2 (`long_cycle`) `by_agent` accumulation: skip `role == "tool"` — same-`t` duplicates cannot change active/wall time, only the `across N events` evidence count; keep the evidence honest.
- No other detector or consumer reads `role`; `_time_range` is unaffected (tool events share the message `t`); v1/grok/claude never emit `role == "tool"` (grok uses `assistant`/`""`, claude `assistant`/`user`, v1 the message's own role), so both guards are v1-neutral one-liners. `main()`'s zero-token note check is unaffected (tool events carry zeros; message events carry the tokens).

## 6. D-5 — permission handling: not extractable on v2; documented UNKNOWN, never faked

Extraction of permission events is **out of scope**: the `permission` table is project-keyed, not session-keyed, and no permission-shaped parts exist in `content[]` (FACT 3). Any join (project_id + time-window overlap with the tree) would attribute *other* sessions' permission events to this tree — worse than a documented zero.

- `permission_requested` stays False on every v2 event, by construction.
- Bookkeeping instead: `info["v2_extraction"]["permission"] = False`, an unconditional note on every v2 run with events (D-6), and the SKILL.md disclosure that `permission_thrash` reads zero **by construction** on v2 — treat as UNKNOWN, not clean; derive permission friction from the run narrative/manifest. This is the 20261101-3 part (a) wording in its post-fix form.
- Revisit trigger: an upstream per-session permission surface (schema change or a session-scoped table) — until then the note is the contract.

## 7. D-6 marker + notes; D-7 graceful degradation for odd/legacy rows

**D-6 — opaqueness bookkeeping.** `_collect_opencode_v2`'s info dict gains (flows into the outer `info` via the existing `info.update` at both call sites):

```json
"v2_extraction": {"messages": 216, "text_events": 190, "tool_events": 318,
                  "text": true, "tools": true, "permission": false}
```

- `messages` = assistant rows that emitted a message event; `text_events` = those with non-empty text; `tool_events` = synthetic tool events. The booleans are capability constants (self-describing: text and tool extraction on, permission off) so the introspector can branch on `info` alone, without version-guessing.
- Note P (always, when v2 events exist): `v2 permission extraction: none (permission table is project-scoped, not session-scoped); permission_thrash reads zero — treat as UNKNOWN`.
- Note T (guard, when `messages > 0 and text_events == 0` — legacy content-less rows, mid-flight odd shapes): `v2 text extraction: none of {N} assistant message(s) carried extractable text; text-based signals read zero — treat as UNKNOWN`.
- Both wordings are greppable and deliberately avoid the substrings `v1` and `store selected` (reconciliation 4). A zero can no longer masquerade as a clean run on any v2 tree, including pre-fix legacy rows.

**D-7 — tokens/content-missing rows.** Rows lacking `tokens` (3/500, too-fresh) keep the existing `msg.get("tokens") or {}` → zeros path; **text/tool extraction never gates on tokens**. Rows lacking `content` (or `content` not a list) → text `""`, no tool events, still counted in `messages` so Note T can fire. Unparseable `data` rows are skipped entirely (existing `JSONDecodeError` path). Non-dict `content` items and parts with unknown `type` are skipped. Every access is `isinstance`-guarded; no shape may crash the collector.

## 8. D-8 fixtures; D-9 module boundaries; D-10 docs

**D-8 — fixture strategy.** New `tests/test_mdu_51_v2_text_extraction.py`, self-contained per the per-MDU convention: its own `importlib` module load and a `SCHEMA`/helpers copy adapted from the mdu-50 file, with `_add_v2_message` gaining `content` (list of part dicts) and `agent` params. File DBs under `tmp_path` driven through `_collect_opencode(..., db_path=db)` so store selection + extraction run end-to-end; direct `_collect_opencode_v2(conn, ...)` calls are fine for narrow unit cases; one CLI subprocess test with `HOME` override (the mdu-50 `_run_cli` pattern) pins the JSON `info` end to end. **Never the developer's real store.** `tests/test_session_signals.py` gains only the two D-4 guard pins via the existing `_event` helper (its `role` kwarg already exists). The 17 mdu-50 store tests are regression pins: content-less v2 rows must not crash, Note T fires, and no existing assertion breaks (notes/info are additive).

**D-9 — module boundaries / v1 isolation.** Single file, stdlib only (`sqlite3`, `json`, `re` already imported). Three new private helpers placed next to `_collect_opencode_v2`: `_v2_extract_message(msg) -> tuple[str, list[dict]]` (joined text + finalized tool parts), `_v2_tool_event(agent, t, part) -> dict | None` (builds the synthetic event via `_normalize_event`, `None` when skipped), `_v2_tool_target(name, input) -> str | None`. The v1 collector loop, all mdu-50 targets, `__all__`, and the CLI surface are untouched; the two `SELECT` statements in `_collect_opencode_v2` are byte-identical (no new SQL, no scanning expansion on the 2.7 GB store — extraction is pure interpretation of rows already fetched). `_compute_metrics` and detector 2 take only the D-4 one-line guards.

**D-10 — docs.** `SKILL.md`: (a) log-locations OpenCode row gains the v2 content-part shape (`text`/`reasoning`/`tool` with `state.status`/`state.input`); (b) signal-kind section gains the post-fix 20261101-3 disclosure — on v2 stores text and tool kinds are live (text parts; finalized tool parts; reasoning excluded; in-flight parts skipped) while `permission_thrash` reads zero by construction and must be treated as UNKNOWN; (c) "How to run" documents `info.v2_extraction` and the two notes with their exit-0 semantics. The script's module docstring gains one line saying v2 text/tool parts are extracted and permission is not.

## 9. Out of scope (deliberate exclusions)

1. **v1 part-interpretation unification** — v1 loop stays byte-identical, including its per-message tool-field attachment and string-state semantics; its undercount quirks are inherited, not introduced.
2. **Permission-table extraction or heuristics** — project-scoped data cannot be per-session attributed (D-5); follow-up gated on an upstream per-session surface.
3. **User-message extraction** (`type='user'` rows) — verdict relays would misattribute/double-count (D-1).
4. **Any use of reasoning text** — excluded wholesale, including for evidence or context signals.
5. **`executed` flag semantics** — unverified; `state.status` is authoritative.
6. **Per-part token attribution / synthesizing tokens for the 3/500 rows** — zeros; no inference.
7. **Part-level timestamps** — message `time_created` remains the event time (part `time` shape unverified beyond existence).
8. **`token_hotspot` / `long_cycle` family pooling** — still deferred from mdu-50 §9.5.
9. **Grep-target tuning beyond pattern-first** — non-read/grep tools' targets have no detector consumer.
10. **Deploy mechanics** — devops continues the mdu-50 3/3 install-marker discipline over the installed skill copies; nothing here is personal-only, so no overlay source edits.

## 10. Acceptance criteria

- **AC-1** A v2 message whose content is `[text("…"), reasoning("…")]` yields one event whose text equals the text part only; no event ever contains reasoning text.
- **AC-2** Two reviewer v2 messages ("REQUEST CHANGES …" ×2) followed by an APPROVE message → `review_reject_streak` fires (count 2, family agent); a single REQUEST CHANGES message → `metrics["review_rejections"] == 1` (the MDU-50 live blind spot, revived).
- **AC-3** Two QA v2 messages each with a standalone `QA GRADE: FAIL` line → `qa_fail_repeat` fires (count 2); a message quoting the format instruction mid-line does not fire (mdu-50 pin holds on v2 events).
- **AC-4** A v2 message with content `[text, tool(read, path X), tool(edit, status error)]` → exactly one `role="assistant"` event (text + tokens, no tool fields) plus two `role="tool"` events with correct `tool`, target, `tool_error`, copied agent, equal `t`, zero tokens, empty model/text.
- **AC-5** Three `edit` parts with `state.status "error"` across messages → `repeated_tool_error` fires with count 3; `completed` parts never set `tool_error`.
- **AC-6** Four `read` parts on the same path → `context_reread` fires; grep parts with `pattern` and no `path` key on `pattern` (target == the pattern string); four distinct grep patterns do NOT fire.
- **AC-7** Parts with `state.status` `streaming`/`running`, and nameless tool parts, produce no events.
- **AC-8** No v2 event ever has `permission_requested` truthy; every v2 run with events emits Note P and `info["v2_extraction"]["permission"] is False`; SKILL.md states `permission_thrash` is UNKNOWN (not clean) on v2.
- **AC-9** Rows with no `content`, no `tokens`, non-dict content items, or unparseable `data` → no crash; when rows exist but zero text is extracted, Note T fires and `info["v2_extraction"]["text_events"] == 0`; all 17 mdu-50 store tests pass unchanged.
- **AC-10** `role="tool"` events are excluded from `metrics["agents"]` counts and from `long_cycle`'s `across N events` evidence (two pins in `tests/test_session_signals.py`).
- **AC-11** v1 behavior is unchanged: the existing suite passes unmodified; a v1 fixture still attaches tool fields to its single message event and never emits `role="tool"`.
- **AC-12** The two `SELECT` statements in `_collect_opencode_v2` are byte-identical to pre-MDU (no new SQL or table scans); the script remains stdlib-only and single-file.
- **AC-13** SKILL.md carries the D-10 edits (log-locations row, post-fix 20261101-3 signal-kind disclosure, `v2_extraction` info fields and note semantics); the script docstring mentions v2 extraction.

## 11. Phase order for the implement brief

1. **implement-1 (script):** the three `_v2_*` helpers, the `_collect_opencode_v2` row-loop rewrite, the D-4 guards in `_compute_metrics` and detector 2, `v2_extraction` + Notes P/T, the docstring line; plus the two pure-function guard pins in `tests/test_session_signals.py`.
2. **implement-2 (fixtures + docs):** `tests/test_mdu_51_v2_text_extraction.py` covering AC-1..AC-11 (sqlite fixtures + one HOME-override CLI test), SKILL.md per D-10; `timeout 300 python3 -m pytest tests/ -q` green (754 existing + new); base `./build.sh`, then the sibling overlay `$WORKSPACE/opencode_agents` `./build.sh`.
3. Standing loop tail: review → test → QA (`QA GRADE: PASS|FAIL`) → validate → introspect → commit, per the mdu-lifecycle order. Introspection note: this MDU's own run is the first v2 tree where the revived detectors are live — expect non-zero `text_events`/`tool_events` in `info.v2_extraction` and treat any `permission_thrash` zero as UNKNOWN per the new SKILL wording.
