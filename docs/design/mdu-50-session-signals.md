# MDU-50 · session-introspect detector fixes: fresh-store, wrong-dir, family streaks, QA verdict

Done looks like: the four detector defects fixed in the script under `skills/session-introspect/` (subpath `scripts/session_signals.py`, 1143 lines) via surgical function-level edits — no collector rewrite; `skills/session-introspect/SKILL.md` updated to match; regression tests added to `tests/test_session_signals.py` plus a new `tests/test_mdu_50_session_store_selection.py`; `python3 -m pytest tests/ -q` green in the base repo; base `./build.sh` and the sibling overlay `./build.sh` both run. Verdict format: implement reports per-target file:function completion; QA ends with `QA GRADE: PASS` or `QA GRADE: FAIL`. Base repo only — no opencode.json, registry, or model-map rows change, so no model re-probe is required.

## 0. Surveyed files

`agent-improvements.md` L202-237 (entries 20261021-3/-4/-5, recurrence histories mdu-30→47); the script (full read, 1143 lines); `skills/session-introspect/SKILL.md`; `tests/test_session_signals.py`; `docs/brief-checklist.md`; glob `tests/*.py` (naming convention `test_mdu_<nn>_<topic>.py`; no test_mdu_50 exists).

## 1. Verified facts that shape the design

1. The rejection-streak loop (L240-289) has **no same-name gate** — `streak_agent` is only the last rejector's label; rejections from any reviewer variant already accumulate. The record's mechanism diagnosis is inaccurate. The real blindness: (a) bare `REJECT` is not in `REJECTION_PHRASES` (L26-31), so REJECT-round verdicts never matched (mdu-30/45/47); (b) v2 rows carry empty text (L833), so no text detector can fire on a v2 tree at all. The fix ships family grouping AND the vocabulary patch; the v2-no-text limit is out of scope (§9.1).
2. The with-id lookup requires exact directory equality (L647-650, L784-787) while no-id accepts a prefix ancestor (L652-656, L790-793). That asymmetry IS the mdu-45 facet (session rooted at the workspace parent, `--cwd` at the repo child → "No matching OpenCode session for cwd" despite a valid id). And the no-id flow tries v1 first — v2 is only a fallback when v1 has no row (L658-667) or zero tokens (L758-766); no freshness comparison exists (the mdu-31/mdu-40 stale-tree mechanism).
3. Per-agent count dicts — `qa_fails` L425, `error_counts` L359, `read_counts` L399, `misses`/`long_counts`/`long_high` L478-480 — key on the exact name, so tier rotation splits every "N times" threshold: the record's blindness class.
4. The JSON result (L1130-1138) has no `info` key; `main()` copies only harness/session_id/cwd from collector info. `metrics["agents"]` rows keep exact names and the introspector matches them to manifest phase lists (mdu-41/43/44 apply-now) — they must NOT be family-collapsed.
5. `_is_bulk_agent` (L468-472) strips `-mid/-pro/-premium` but not `-free`; `code-reviewer-free` (a real rotation tier, mdu-30) can never be a bulk role. No SQLite fixture exists in `tests/`; the existing CLI test uses the developer's real home, so new store tests must be hermetic (§7).

## 2. D-1 — fresh-store selection (20261021-4, HIGH)

Targets: `_collect_opencode` (L631-771), `_collect_opencode_v2` (L774-843), new helpers.

- New `_to_epoch_ms(value)`: numeric or digit-string → epoch ms (a value < 1e11 is seconds, ×1000); ISO-8601 string → `datetime.fromisoformat` with `Z`→`+00:00`; else 0.0.
- New `_store_freshness(cur, cwd)`: per store (v1 → table `session`, v2 → `session_v2`), run `SELECT id, time_updated` with the existing cwd predicate (`directory = ? OR ? LIKE directory || '%'`), take the max row by `_to_epoch_ms` **in Python** — no cross-store format assumption, no SQL ORDER BY on an untyped column. Returns per-store `{id, newest_ms}` or None.
- Selection in `_collect_opencode` when `--session-id` is omitted: neither store has rows → keep the existing "No matching OpenCode session for cwd" note; exactly one → that store; both → **v2 wins unless v1.newest_ms > v2.newest_ms + EPS_MS**, `EPS_MS = 300_000` (5 min). Rationale: v2 is the live schema; near-ties are dual-write artifacts, not a fresher v1; v1 wins only when clearly fresher (a pre-migration project never revisited).
- v1 selected → the existing message/part flow unchanged. v2 selected → call `_collect_opencode_v2(conn, cwd, None)` as a **primary** path (today it is only a fallback). The existing zero-token v2 fallback inside the v1 flow stays; when it swaps the tree, flip `info["store"]` to "v2" and add a note.
- When both stores have candidates, emit one greppable note: `store selected: v2 (newest 2026-10-21T09:24Z; v1 newest 2026-10-14T17:13Z)`. Default cwd when `--cwd` is omitted: unchanged (argparse default `os.getcwd()`).
- With `--session-id` supplied: no freshness comparison runs (the id pins the tree); the §4 predicate + wrong-dir detection apply instead.

## 3. D-2 — JSON `info` fields (backward compatibility)

`main()` result dict (L1130-1138) gains `"info": info` — additive; every existing key, shape, and CLI flag is unchanged; the introspector reads stdout JSON, so additive keys cannot break it. `info` (opencode collector only; grok/claude emit their dict without these keys):

- `store`: `"v1"` | `"v2"` | `""` — which OpenCode store produced the tree.
- `store_candidates` (no-id path, the stores compared): `[{"store": "v1", "id": <str|null>, "newest": <ISO|null>}, {"store": "v2", …}]` — the store ids tried. With-id path emits `store` + `time_range` only (no comparison ran).
- `time_range`: `{"oldest": <ISO|null>, "newest": <ISO|null>}` from the selected tree's events — min/max positive `t`, UTC `%Y-%m-%dT%H:%M:%SZ`; nulls when no positive timestamps.

Duplication of harness/session_id/cwd inside `info` is intentional: `info` is the collector's full dict; top-level copies stay for compatibility.

## 4. Wrong-directory detection (20261021-4, HIGH) + D-3 exit-code ruling

- Relax BOTH with-id lookups to the no-id prefix predicate: `WHERE id = ? AND (directory = ? OR ? LIKE directory || '%')` (v1 L647-650; v2 L784-787). Alone this fixes the mdu-45 ancestor-directory facet: the id matches, no note, no diagnostic runs.
- New `_wrong_directory_notes(cur, session_id, cwd)`, called when both with-id lookups miss; look the id up in `session` then `session_v2` WITHOUT the directory filter:
  - not found in either → `session id {S} not found in OpenCode stores` (splits the old conflated miss note; the old text survives only for the no-id empty case the existing CLI test greps);
  - found with directory D neither cwd nor an ancestor of cwd → exactly `session id {S} belongs to {D}, not {cwd}` — the record's required wording;
  - parent recovery: the row's `parent_id` P exists and P's directory satisfies the cwd predicate → `propose parent as root: rerun with --session-id {P}` (the mdu-35 recovery, script-visible);
  - children recovery: rows with `parent_id = S` under the cwd predicate exist → `supplied id has {n} child session(s) under {cwd}; rerun without --session-id (freshest-store selection) or with --cwd {D}` — the record's "children under cwd" clause under both readings; the no-id rerun lands on the freshest tree via §2.
- No substitution: events stay empty and `session_id` stays `""` — the 20261021-4 apply-now already tells introspectors to treat that as unknown; the note supplies the reason instead of costing diagnostic runs.
- **D-3 ruling: exit code stays 0.** SKILL.md documents "exits 0 even when logs are missing"; the introspector consumes stdout JSON, not rc; the existing CLI test pins rc 0 with notes; a second signal channel nobody reads adds break risk. The note text plus empty `session_id` are the machine contract.
- Auto-mode caveat (recorded, not changed): `_select_harness` (L1049-1064) drops a non-selected harness's notes; on this machine grok/claude dirs exist but the opencode-shaped id makes them miss, so the belongs-to note survives in the accumulated misses (pinned by `test_select_harness_skips_opencode_without_events_or_session`).

## 5. D-4 — family-prefix grouping (20261021-3, LOW)

- Mechanism: `TIER_SUFFIXES = ("-pro", "-mid", "-premium", "-free")` and `_family(agent)`: lowercase, strip one trailing tier suffix, else the name as-is. No cross-harness unification (`grok-just-code` ≠ `just-code`) — one store per session makes collisions impossible; the record's example is `code-reviewer*`. Families pooled (examples; the suffix rule covers every agent, there is no name map): `code-reviewer`(+pro/mid/free), `grok-code-reviewer`, `grok-review`, `just-code`, `grok-just-code`, `grok-mdu-code`, `test-agent`, `grok-test-agent`, `qa`, `grok-qa`, `devops`, `grok-devops`, `research`, `ui-ux-designer`, `orchestrator`, `grokestrator`, `architect`, `educator`.
- **Scope ruling — grouping applies to:** the `review_reject_streak` signal's `agent` label (the family) and its evidence (append `variants: code-reviewer-pro, code-reviewer` when more than one raw name contributed); the count dicts `qa_fails`, `error_counts`, `read_counts`, `misses`, `long_counts`, `long_high` — pooling rotated variants into one threshold. Cheap (one key change each) and clearly safe (same role, rotated tier).
- **Explicitly NOT grouped:** `metrics["agents"]` rows (fact 4); `token_hotspot` and `long_cycle` aggregation (per-variant absolute spend is still meaningful, no evidence record — revisit with evidence); `_compute_metrics` `review_rejections` (a global counter, no per-agent key).
- Adjacent one-liner in the same concept: `_is_bulk_agent` (L468-472) strip list gains `"-free"` so `code-reviewer-free` counts as a bulk role for `expensive_model` (mdu-30 shows `-free` is a real rotation tier; without it that detector has the same variant blindness).
- Because the record's stated mechanism (a same-name gate) does not exist in the code (fact 1), its observable symptom also needs the vocabulary patch: add `"reject"` to `REJECTION_PHRASES` (L26-31) so bare REJECT/REJECTED verdicts match. `_is_rejection` runs before `_is_approval`, matching the existing "not approved" precedence. Residual false-positive risk ("nothing to reject" phrasing reads as a rejection) accepted; tests pin only the positive form.

## 6. QA verdict match (20261021-5, LOW)

Target: `collect_signals` section 7 (L424-443). New constant `QA_FAIL_VERDICT = re.compile(r"(?im)^qa grade:\s*fail\b")`; the detector becomes `if _is_qa(agent) and QA_FAIL_VERDICT.search(text)`, counted **once per message** (search is boolean), accumulated under `_family(agent)` per §5.

- Rationale: the QA prompt mandates a standalone terminal verdict line ("End with exactly: QA GRADE: PASS or QA GRADE: FAIL"). The mdu-31 false positive is that instruction quoted mid-line (the FAIL token follows "or") — a line-start anchor excludes it while still matching a real verdict wherever the QA agent places it on its own line. Case-insensitive for `QA Grade: FAIL`; `\b` rejects FAILED.
- Alternatives rejected: unanchored `QA GRADE:\s*FAIL` (matches the quoted instruction — the observed false positive); stripping quoted spans (no reliable quote markers in agent text, fragile).
- Residual: a message quoting the bare verdict token alone on its own line still counts; the 20261021-5 apply-now (confirm the QA phase outcome in the manifest) remains the backstop. The detector now couples to the mandated verdict format instead of any FAIL substring.

## 7. D-5 — test plan

- Split: pure-function defect tests (§5, §6) extend `tests/test_session_signals.py` (reuse its `_event` helper; ad-hoc `cache_read`/`model` keys as L193-195 already do). Store-selection and wrong-dir tests go in a NEW `tests/test_mdu_50_session_store_selection.py` — SQLite fixture machinery would bloat the unit file; the name follows the `test_mdu_<nn>_<topic>.py` convention.
- Fixtures: temp SQLite DBs under `tmp_path` with only the columns the script reads — `session(id, directory, parent_id, agent, time_updated)`, `message(id, session_id, data)`, `part(id, message_id, data)`, `session_v2` (same shape as `session`), `session_message(id, session_id, type, data, time_created INTEGER)`. ISO `time_updated` strings in most tests; one test with epoch-ms ints pins `_to_epoch_ms` both ways. **Never the developer's real session store.**
- Injectable path: `_collect_opencode` gains an optional `db_path: Path | None = None` parameter (default from a new `_opencode_db_path()` helper holding today's home-derived path); backward compatible with `main()`'s positional calls. CLI-level: one subprocess test per store flow with `env={**os.environ, "HOME": str(tmp_path)}` and the DB at `<tmphome>/.local/share/opencode/opencode.db` (POSIX `Path.home()` honors HOME) — pins `main()`'s JSON end to end, hermetically.
- Non-vacuous assertions (rc alone is vacuous — assert emitted JSON values too):
  - Defect 1: v1 newest 2026-10-14 + v2 newest 2026-10-21 → `info["store"] == "v2"`, `session_id` == the v2 root, and a token sum only the v2 tree can produce (metrics agents tokens_in totaling 5000); reversed fixture → store "v1" plus a v1-only text signal firing; v1-only rows → "v1"; v2 within EPS → v2. CLI test: `data["info"]["store_candidates"]` lists both ids and `data["info"]["time_range"]["newest"]` startswith the v2 date.
  - Defect 2: ancestor-directory id → `session_id` == the id, no belongs-to note (mdu-45 pin); genuinely wrong-dir id via CLI → rc == 0 AND `session_id == ""` AND the exact note `session id {S} belongs to {D}, not {cwd}` in `notes`; parent-recovery fixture → note contains `propose parent as root` and P; children fixture → note contains the child count.
  - Defect 3: pro `REQUEST CHANGES` → mid `I REJECT this` → free `LGTM` event list → `review_reject_streak` present, `sig["agent"] == "code-reviewer"`, evidence names both variants; a `_family` unit table (pro/mid/free strip; unknown passes through); qa-mid ×1 + qa ×1 verdict-FAIL events → `qa_fail_repeat` fires (pooled count 2); bare-REJECT ×2 → streak fires (phrase pin).
  - Defect 4: two QA messages containing ONLY the quoted instruction sentence → NO `qa_fail_repeat` (the regression pin); two standalone `QA GRADE: FAIL` lines → fires with count 2; a lowercase `qa grade: fail` line → fires.
- All existing tests must pass unchanged (no signature breaks; JSON is additive only).

## 8. D-6 — docs, verification, deploy

- SKILL.md edits: (a) the OpenCode log-locations row gains the v2 tables (`session_v2`, `session_message`); (b) signal-kind lines — `review_reject_streak` (one reviewer **family**, tier variants pool), `qa_fail_repeat` (a standalone verdict line `QA GRADE: FAIL` in >= 2 messages, family-pooled; quoted format instructions no longer count), plus a "(family-pooled across tier variants)" tail on `cache_miss`, `long_context`, `repeated_tool_error`, `context_reread`; (c) "How to run" documents the new `info` fields (`store`, `store_candidates`, `time_range`) and the wrong-directory note with its exit-0 semantics.
- Verification: `python3 -m pytest tests/ -q` green (both test files) in the base repo, then `./build.sh` (skill tooling copies into `build/`).
- Deploy: base `./build.sh` copies the fixed skill into `build/`; the sibling overlay `$WORKSPACE/opencode_agents` picks it up by running its own `./build.sh` over the base output — run it so the merged/deployed skill carries the fix. No overlay source edits (nothing here is personal-only). No model re-probe: zero config/registry rows change.
- Implementer constraints: keep edits surgical to the named functions; read the script rather than expecting pasted bodies; no collector refactors beyond the targets.

## 9. Out of scope (deliberate exclusions)

1. **v2 text extraction** (`session_message` part text) — the structural reason every text detector reads 0 on v2 trees. Excluded: the v2 text schema is unverified from the repo (no schema doc; the live DB is not probeable from this design step); guessing column shapes would burn implement cycles. Manifest-derived signals remain the compensating control. Follow-up candidate, gated on a live-store schema probe.
2. `_select_harness` note preservation for non-selected harnesses — pre-existing semantics pinned by an existing test; the belongs-to note survives in the real case (§4 caveat).
3. LIKE-wildcard escaping for directories containing `%` or `_` — a pre-existing quirk of the shared predicate, inherited not introduced by this MDU.
4. `metrics["agents"]` family collapse — would break the introspector's manifest phase-list name matching.
5. `token_hotspot` / `long_cycle` family pooling — deferred pending an evidence record.
6. With-id dual-store freshness (an id present in both v1 and v2) — the id pins the tree; the existing zero-token fallback covers the degenerate case; the returned-id sanity check backstops.

## 10. Phase order for the implement brief

1. **implement-1 (pure detectors):** constants + `_family` + `_to_epoch_ms` + the phrase/regex additions inside `collect_signals`, `_cost_signals`, `_is_bulk_agent`; unit tests for defects 3 and 4 in `tests/test_session_signals.py`.
2. **implement-2 (collector):** D-1 freshness selection + `db_path` parameter + D-2 `info` fields in `main()`, then the §4 relaxed predicate and `_wrong_directory_notes`; the new `tests/test_mdu_50_session_store_selection.py` covers defects 1 and 2. One child — both halves touch `_collect_opencode`.
3. **docs + verify:** SKILL.md edits; `python3 -m pytest tests/ -q`; base `./build.sh`; overlay `./build.sh`.
4. Standing loop tail: review → test → QA (`QA GRADE: PASS|FAIL`) → validate → introspect → commit, per the mdu-lifecycle order.
