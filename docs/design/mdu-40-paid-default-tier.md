# MDU-40 — Paid default tier (retire free-model agents and the Zen tier)

**Status:** design, ready for implementation
**Repos:** base (this repo) then overlay `opencode_agents`
**Supersedes:** MDU-33 Zen variant (default tier), MDU-36 overlay free fallback,
the MDU-40 backlog sentence about keeping `gen_zen_config` alive as an
emergency tier, and MDU-42 AC3 ("Zen tier still builds and deploys").

---

## 1. Goal

One canonical OpenCode config, all-paid, deployed by default:

- every OpenCode-native agent runs on `opencode-go/*`;
- every grok-named agent runs on `xai/*` (MDU-42 hard rule, unchanged);
- **zero** `opencode/*` free-model rows in any shipped config or tier;
- orchestrator prompts spawn only paid variants;
- the free-tier machinery (Zen map, generator, allowlist, tier flags, probe
  map) is removed rather than left as a second code path nobody exercises.

Outcome: the loop can no longer die on an account-shared daily free cap
(MDU-39: 429 `provider.quota`, account-shared, probe-OK is not exemption
evidence).

---

## 2. Verified facts (read from the tree, 2026-10-30)

1. Base `opencode.json` = 28 agents: 19 paid `opencode-go/*` + 9 free.
2. The 9 free rows are: `orchestrator` (`opencode/big-pickle`, L20),
   `just-code-free` (L288), `test-agent-free` (L549), `code-reviewer-free`
   (L1281), `devops-free` (L1891), `qa-free` (L2636), `research`
   (`opencode/mimo-v2.6-flash-free`, L2974), `deepseek-research`
   (`opencode/nemotron-3.5-lightning-free`, L3038), `nemotron-research`
   (same model, L3102). `deep-research` is paid (`opencode-go/mimo-v2.5`, L3166).
3. There are **five** `*-free` agents, not six (the design brief said six and
   named five; the tree has five).
4. `orchestrator` is the `default_agent` (L3) and is itself on a free model —
   not named in the user's removal list, but incompatible with "no agent maps
   to free anywhere". It must be repointed, not deleted.
5. 18 agent permission blocks carry `{"action":"subagent","resource":"research",
   "effect":"allow"}` followed by a `*` deny (e.g. L140). Deleting `research`
   orphans those allows.
6. `scripts/build.sh` L25-29 calls `scripts/lib/gen_zen_config.py` with
   `config/zen-model-map.json`; L31 runs `validate.py`.
7. `gen_zen_config.py` is fail-closed on targets: every mapping target must be
   in the free allowlist, and an empty `models` map still produces a parity
   file but a `models`-less map errors. Identity semantics do **not** exist.
8. `validate.py` has `validate_zen()` (L474), `--variant {go,zen,both}` (L619),
   `free_zen_models` import (L16), `GROK_MODEL_ALLOWLIST` (L27).
9. `probe_models.py` takes `--map` (default `config/zen-model-map.json`), has
   `alternates` (warn-only) and `map_sha256`; `--config` only supplies the xai
   model set; `--include-xai` forces the xai section.
10. Base `scripts/deploy.sh`: `TIER="zen"` (L28), accepts `zen|go`, installs
    both files (active + parked), probe gate is `--advisory` and passes
    `--map`, `grok_xai_gate` checks parked + active.
11. Overlay `opencode_agents/build.sh` runs the base build, then its own
    `build_zen_config()` (merged map, `xai/*` identity), then base
    `validate.py`; overlay `scripts/deploy.sh` also defaults `TIER="zen"`.
12. Overlay `opencode.json` has 22 agents, all paid: 20 grok-named + `mdu-code`
    (`opencode-go/deepseek-v4.1-flash`) + `thought-leadership-coach` (`xai/*`).
    **No overlay agent row needs a model change.**
13. Free-variant spawn defaults live in base `prompts/orchestrator.md`
    L141-143, L150, L156, L161, L170, L175, L184, L186, and in overlay
    `grok/agents/grokestrator.md` L120, L128. Base `grok/agents/orchestrator.md`
    is already paid-only (grok model names) — it needs the new parity sentence
    plus one "delegate to research" → "delegate to `deep-research`" phrase
    (L179), not a table rewrite.
14. `skills/mdu-lifecycle/SKILL.md` L30-43 still documents a free column and
    `just-code → just-code-free` fallback. `docs/opencode-v2.md` L40 lists the
    five `*-free` agents under a legacy alias mapping.
    `evals/tasks/03-ledger-conformance/driver.sh` L24 defaults
    `OPENCODE_MODEL=opencode/big-pickle`.
15. Three-way mirror parity already has a test pattern:
    `tests/test_mdu_34_resume_block.py` `_all_mirrors()` reaches the overlay
    `grokestrator.md` via `REPO_ROOT.parent`.

---

## 3. Decisions

### D1 — Tier model: retire the Zen tier entirely [RECOMMENDED]

Delete `gen_zen_config.py`, `config/zen-model-map.json`, the
`build/opencode.zen.json` artifact, the `--variant` validator flag, and the
`--tier` machinery's second path. Deploy installs exactly one file,
`opencode.json` → `~/.config/opencode/opencode.json`.

Why not (b) "keep the plumbing, zen = identity": an identity generator has no
legal mapping rows, so the fail-closed target check has to be rewritten to
accept an empty map — i.e. new semantics for a file that is byte-identical to
its input. That is pure maintenance cost plus a second validator surface, and
it re-opens exactly the "which file is live?" confusion that caused the mmo
incident.

Emergency tier replacement: rollback is a git operation, not a config flag
(`git revert <mdu-40> && ./build.sh && ./deploy.sh --force`). Record this in
README so nobody looks for `--tier=zen`.

Supersession to document verbatim in the backlog/status note: the AC1 sentence
"Validate the map_sha256 / gen_zen_config path keeps working so the emergency
tier stays buildable" was written before the user's 2026-10-30 decision
("free exempt list: none at all"), and is superseded. MDU-42 AC3 is likewise
superseded (there is no Zen tier left to build).

### D2 — Canonical agent removals and re-baseline

[DECIDED-user] Delete these 8 rows from `opencode.json`:

| Agent | Was |
| --- | --- |
| `just-code-free` | `opencode/big-pickle` |
| `test-agent-free` | `opencode/big-pickle` |
| `code-reviewer-free` | `opencode/big-pickle` |
| `devops-free` | `opencode/big-pickle` |
| `qa-free` | `opencode/big-pickle` |
| `research` | `opencode/mimo-v2.6-flash-free` |
| `deepseek-research` | `opencode/nemotron-3.5-lightning-free` |
| `nemotron-research` | `opencode/nemotron-3.5-lightning-free` |

Plus one repoint (not a deletion): `orchestrator` — `opencode/big-pickle` →
`opencode-go/mimo-v2.5`, still `default_agent`. Final agent count: **28 → 20**
(19 existing paid `opencode-go/*` incl. `deep-research`, + orchestrator now
paid).

[DECIDED-design] `orchestrator` keeps its name, `default_agent` stays
`"orchestrator"`, model becomes `opencode-go/mimo-v2.5`. Rationale: the
orchestrator holds the longest context and runs the whole loop; `deepseek-v4.1-
flash` is the busiest coder slot (three agents share it) and is the weakest at
long-horizon planning. Alternative if cost dominates: `opencode-go/deepseek-
v4.1-flash` (one-line change, same design).

[DECIDED-design] Repoint all 18 `"resource": "research"` subagent allows to
`"resource": "deep-research"` (grep `"resource": "research"`; confirm 18 hits
before committing). Leaving them would silently remove children's ability to
delegate research; deleting them would leave the following `*` deny as the only
rule (same effect, less intent).

Description text: strip "free model" / "free ... model" / "using free" phrasing
from all remaining descriptions (no `-free`, no `big-pickle` may remain in the
file). `prompts/research.md` stays — `deep-research` still references it.
No `*-free` prompt or grok-mirror files exist, so no prompt deletions.

Re-baseline: OpenCode harness agent count 28 → 20; Claude subagents are
generated by iterating the agent map (no code change, count follows); grok
profile count is unchanged (mirror files are keyed by prompt stem).

### D3 — Generator fate and build wiring

[DECIDED-design] `scripts/lib/gen_zen_config.py` and
`config/zen-model-map.json` are deleted. `scripts/build.sh`: drop the zen step
(L25-29) and keep `gen_claude_agents` + `validate.py`. `build/opencode.zen.json`
is no longer produced; stale copies in a dirty `build/` must be removed by the
build (or deleted manually before validating, so nobody deploys a stale file).

`config/model-registry.txt` **stays** — `validate_model_refs()` still uses it
as the dead-model guard. Only the free-allowlist helper goes:
`model_registry.free_zen_models()` is deleted (no remaining caller).

### D4 — Probe gate: probe the canonical config, not a map

[DECIDED-design]

- `--config` becomes the single source of truth and is required for both
  `--refresh` and `--gate` (default `build/opencode.json`).
- `--map` is removed (argparse rejects it → exit 2, which is the correct
  "bad invocation" signal).
- New pure function `collect_models(config)` → `{"opencode-go": [...],
  "xai": [...]}` deduped+sorted; replaces `probe_set()`.
- `map_sha256` → `config_sha256`, hashing the sorted `agent=model` pairs so any
  remap or agent add/remove re-reds a stale report.
- `alternates` retire with the map. Every distinct model in the config is a
  hard target. (The old alternates were free models we no longer use.)
- `--include-xai` is kept as an accepted, documented-deprecated no-op for one
  release so existing operator muscle memory / scripts do not exit 2; xai
  probing is auto-enabled whenever the config resolves an `xai/*` model (it
  always will, 20/20 grok agents).
- Grouped output: `opencode-go: n probed`, `xai: n probed`, then per-model rows.
- CI stays CLI-free: pytest only calls `collect_models`, `config_sha256`,
  `gate_offences` with fixtures. No live call in the suite.

### D5 — Orchestrator mirror rewrite (three mirrors, behavioral parity)

Canonical paid routing (unchanged names, unchanged prices-tier language):

- research → `deep-research` (Go budget, mimo-v2.5)
- `just-code` / `test-agent` / `inception` → deepseek-v4.1-flash
- `just-code-mid` / `test-agent-pro` / `qa-pro` / `ui-ux-designer-pro` → kimi-k2.7-code
- `just-code-pro` / `architect` / `architect-premium` / `code-reviewer-pro` /
  `devops-pro` → glm-5.2
- `test-agent-mid` / `code-reviewer` / `devops` / `qa` / `deep-research` /
  `ui-ux-designer` / `introspector` → mimo-v2.5

[DECIDED-design] Each mirror must lose every `*-free` bullet and every
"free model"/"free-tier" spawn default, and must contain this one canonical
sentence verbatim (this is the parity token the test asserts):

> All loop phases run on paid models; free-tier variants are retired (MDU-40).

Per file:

1. `prompts/orchestrator.md` — delete bullets L141-143 (free research), L150
   (`just-code-free`), L156, L161, L170, L175. Research section becomes one
   bullet: `deep-research` (Go budget, mimo-v2.5) covering quick lookups and
   deep investigations. Rewrite L184 fallback: on a model error, retry once on
   the same variant, then escalate one rung (`just-code` → `just-code-mid`),
   never to a free variant, and never more than the existing fourth-retry gate.
   Replace L186 with the canonical sentence. L189 "delegate to research" →
   "delegate to `deep-research`". Keep the `model_tier` enum
   (`free|budget|mid|premium|top-tier`) at L205 untouched — it is the MDU-15
   ledger schema, still valid for historical manifests and covered by
   three-way parity tests; MDU-40 simply never emits `free`.
2. `grok/agents/orchestrator.md` — tables are already paid-only. Add the
   canonical sentence in the token-frugality block and change the failure
   triage phrase "delegate to research" (L179) to "delegate to
   `deep-research`". No table edits.
3. Overlay `opencode_agents/grok/agents/grokestrator.md` — L120
   `research (free deepseek)` → `deep-research (Go mimo-v2.5)`; L128 drop
   "Free-tier research agents save OpenCode Go budget" and replace with a
   paid-only rotation sentence + the canonical sentence. Keep the MDU-42
   delegation sentence at L174 unchanged.

Parity is behavioral, not literal: base OpenCode mirror names Go models, the
base Grok mirror names Grok models, the overlay mirror names both harnesses.
The test asserts the canonical sentence and the absence of free tokens, not
identical bullets.

### D6 — Validator clauses

[DECIDED-design] In `scripts/lib/validate.py`:

- Delete `validate_zen()` and the `--variant` flag (default behaviour becomes
  the only behaviour).
- Delete the `free_zen_models` import.
- Add `validate_paid_census(build_dir, snapshot)`:
  - every agent model must start with `opencode-go/` or `xai/`; otherwise
    `"agent '<name>' uses non-paid model '<model>' (paid-only census)"`;
  - the raw file text must not contain `big-pickle` or a `-free` model token
    (catches description drift that `find_model_refs` misses);
  - `default_agent` must exist in `agents`.
- Keep `validate_model_refs()` (registry existence), `GROK_MODEL_ALLOWLIST`,
  `grok_xai_errors()` — the MDU-42 hard rule now applies to exactly one file.
- No agent-count constant anywhere (count comes from the map).

### D7 — Deploy gates (both repos)

[DECIDED-design]

Base `scripts/deploy.sh`:
- `TIER="paid"`; accept `paid` and `go` as synonyms (same single config);
  `--tier=zen` exits 2 with `"zen tier retired in MDU-40; use paid (single config)"`.
- Drop `ensure_tier_sources`' zen branch and the parked-file copy. Active file
  is always `${DEPLOY_ROOT}/opencode.json` (build output, or repo root in the
  source checkout).
- `probe_gate_advisory`: `python3 scripts/lib/probe_models.py --gate
  --report config/model-probe-report.json --config <active>`; no `--map`.
  Stays advisory in the public base (stranger with no CLI must still deploy).
- `grok_xai_gate` runs once, on the active config (no parked loop).
- Dry-run banner prints `Tier: paid` and the single target path.

Overlay `scripts/deploy.sh`: same default flip and parked removal; its probe
gate stays **hard** (`--force` install aborts on red). Overlay bootstrap line
in messages becomes `--refresh --gate --config build/opencode.json`.

### D8 — Docs and skills

- `docs/model-registry.md`: rewrite "Orchestrator" (mimo-v2.5), replace
  "Research (free)" with "Research (paid)" (one row: `deep-research`), delete
  every `*-free` row, delete the "Zen variant mapping (MDU-33)" section, keep
  "Free-tier caps (2026-10-29)" **verbatim as historical evidence** with a
  one-line preamble: "Historical: free models are no longer used (MDU-40)."
  Update the probe section to `--config` + `config_sha256`.
- `README.md`: replace "Model Tiers — Zen (default) / Go" with "Single paid
  configuration (MDU-40)"; delete the tier table, the zen build paragraph, the
  switch-up/switch-back recipes (replace with rollback = git revert); remove
  `*-free` rows from the agent table; orchestrator row says `opencode-go/mimo-
  v2.5`; note Go subscription required.
- `docs/opencode-v2.md` L40 legacy alias list: drop the `*-free` names.
- `skills/mdu-lifecycle/SKILL.md` L30-43: drop the free column and the
  `just-code → just-code-free` fallback; keep budget/mid/premium columns.
- `evals/tasks/03-ledger-conformance/driver.sh` L24: default
  `OPENCODE_MODEL=opencode-go/deepseek-v4.1-flash`; update the task README line
  that names the old default.
- `docs/design/mdu-33-zen-variant.md`: add a one-line banner "Superseded by
  MDU-40 (paid default, Zen retired)" — no body rewrite.

### D9 — Test plan

Enumerated (base suite, 561 passing at MDU-39):

| File | Action |
| --- | --- |
| `tests/test_mdu_33_zen_variant.py` | **Delete.** Machinery gone. Keep nothing; its `free_zen_models` and README/docs cases are re-expressed in the new test. |
| `tests/test_mdu_38_model_probe.py` | **Reduce + update.** Fixture map → fixture config; `probe_set` → `collect_models`; `map_sha256` → `config_sha256`; delete alternates cases; replace the docs-table assertion (L556-562) with a paid-only row assertion; keep xai cases. ~20 of ~45 remain. |
| `tests/test_mdu_42_grok_xai.py` | **Update.** Drop the zen-build fixtures and the `--variant zen` case (L98-150); keep the canonical grok-xai clause and deploy-gate cases. |
| `tests/test_grok_model_allowlist.py` | **Verify only** — it enumerates prompt stems (incl. `research`, which stays), so no change expected. |
| `tests/test_validate_integration.py`, `test_validate_schema.py`, `test_validate_parity.py` | **Verify/update** only where they assume the zen artifact or `--variant`. No free-model assumptions found by grep. |
| `tests/test_mdu_13_readme_gallery.py` | **Verify** — counts agents dynamically; expected to pass unchanged after README edits. |
| `tests/test_model_registry.py` | **Update** — drop `free_zen_models` tests, keep registry/parse tests. |
| `tests/test_mdu_40_paid_default.py` | **New.** See below. |

New test file `tests/test_mdu_40_paid_default.py`:

1. census: canonical `opencode.json` has 20 agents, every model matches
   `^(opencode-go|xai)/`, zero names end in `-free`, no `big-pickle` in text;
   `default_agent` exists and is paid.
2. removed names absent: the 8 deleted agent names are not keys.
3. `research` permission allows are gone (no `"resource": "research"`).
4. mirror parity: for each of the 3 mirror paths, the canonical sentence is
   present and `-free`/`big-pickle`/`free model` tokens are absent
   (`_all_mirrors()` pattern from test_mdu_34, overlay path optional-skip when
   the sibling repo is absent).
5. validator: a fixture config with one `opencode/*` agent fails
   `validate_paid_census`; a paid fixture passes.
6. probe: `collect_models` groups/dedupes; `config_sha256` changes when a
   model changes; `gate_offences` reds on a missing target and on a stale hash.
7. deploy: `scripts/deploy.sh` contains `TIER="paid"`; `--tier=zen` exits 2
   with the retirement message; `--tier=paid` dry run reports `Tier: paid` and
   one target file (no parked file); overlay equivalents live in the overlay
   suite.

Estimated count: 561 − ~100 to ~110 removed + ~28-32 added ≈ **480-495**.
Treat the number as a range; the acceptance condition is "suite green, no
skipped zen cases, no test that asserts free-model presence".

Overlay suite: `tests/test_mdu_36_tier_deploy.py` — reduce to single-config
deploy assertions (default paid, no parked file, invalid tier message,
grok profile count); `tests/test_mdu_42_grok_xai.py` — drop the zen-map and
zen-build cases (keep "no xai downgrade in the built config"), ~10-14 tests
removed, ~4 added.

### D10 — Overlay work list (second commit, after base is green)

| File | Change |
| --- | --- |
| `opencode_agents/scripts/build.sh` | delete `build_zen_config()` and the merged map; drop the `opencode-go/` grep gate; call base `validate.py` unchanged. |
| `opencode_agents/scripts/deploy.sh` | `TIER="paid"`, accept `paid|go`, reject `zen`, drop parked logic and `ensure_tier_sources` zen branch, probe gate `--config build/opencode.json` (hard), `grok_xai_gate` on the single config. |
| `opencode_agents/grok/agents/grokestrator.md` | D5 item 3. |
| `opencode_agents/opencode.json` | **No model edits** (all 22 rows already paid). Only verify with the new census. |
| `opencode_agents/build/opencode.zen.json` | generated artifact: stop regenerating; commit the removal only if `build/` is committed in that change (per workspace rule, do not sweep unrelated dirty build output). |
| `opencode_agents/tests/test_mdu_36_tier_deploy.py`, `tests/test_mdu_42_grok_xai.py` | per D9. |
| Overlay docs (`README.md` if it names tiers) | mirror the base README wording. |

Ordering: base commit + push (green suite, `./build.sh`), then overlay
`./build.sh` → tests → `./deploy.sh` dry run → commit + push. Two separate
commits; never mix the repos.

---

## 4. Implementation file list (base)

Config/data:
- `opencode.json` (delete 8 rows, repoint orchestrator, 18 permission allows, descriptions)
- `config/zen-model-map.json` (delete)
- `config/model-registry.txt` (keep)

Code:
- `scripts/lib/gen_zen_config.py` (delete)
- `scripts/lib/model_registry.py` (drop `free_zen_models`)
- `scripts/lib/validate.py` (D6)
- `scripts/lib/probe_models.py` (D4)
- `scripts/build.sh` (drop zen step)
- `scripts/deploy.sh` (D7)

Prompts/docs:
- `prompts/orchestrator.md`, `grok/agents/orchestrator.md`
- `docs/model-registry.md`, `README.md`, `docs/opencode-v2.md`
- `skills/mdu-lifecycle/SKILL.md`
- `evals/tasks/03-ledger-conformance/driver.sh` (+ its README)
- `docs/design/mdu-33-zen-variant.md` (banner), this doc
- `FEATURE_BACKLOG.md` (MDU-40 status + supersession note)

Tests: as in D9.

Overlay: as in D10.

---

## 5. Risks

| Risk | Mitigation |
| --- | --- |
| Daily driver breaks: `deploy.sh` invoked with `--tier=zen` out of habit | explicit exit-2 message naming MDU-40 and the single paid config; README rollback recipe |
| Probe gate reds at deploy because the old report has no `config_sha256` | gate prints the bootstrap `--refresh --gate --config …` command; base is advisory, overlay fails closed but documents the one-line fix |
| Deleting `research` silently removes research delegation for children | D2 repoints the 18 `subagent/research` allows to `deep-research`; test asserts none remain |
| Orchestrator moves to a pricier model → cost surprise | mimo-v2.5 is already used by 7 agents; alternative is deepseek-v4.1-flash, one line |
| Stale `build/opencode.zen.json` deployed by an old script copy | build removes stale zen artifacts; deploy never reads them (file name retired) |
| Docs/tests drift (test_mdu_38 asserts the old free rows in the registry doc) | D8/D9 update them in the same commit; the new census test is the backstop |
| Overlay repo built before base is pushed | strict order: base green + pushed, then overlay `./build.sh` (it re-runs the base build) |
| Loss of an "emergency cheap tier" | accepted by user decision; rollback is git revert of the MDU-40 commit + redeploy of the prior `opencode.json` |

**Rollback:** `git revert <mdu-40-commit>` (or checkout the previous
`opencode.json`), `./build.sh`, `./deploy.sh --force`, start a new OpenCode
session. No data migration, no state to repair.

---

## 6. Acceptance criteria mapping

| Backlog AC | Satisfied by |
| --- | --- |
| AC1 — paid tier ships and deploys; deployed default has zero free models | D1 (single canonical config), D2 (all-paid census), D6 (validator census), D7 (deploy default `paid`). AC1's map_sha256/gen_zen sentence is superseded per D1. |
| AC2 — `xai/grok-4.7` wired and live-probed | already done in MDU-42; D4 keeps the xai group as hard gate targets under `--config`; D7 runs the probe against the single config. |
| AC3 — live deploy + `opencode run` probe ok; probe gate covers the new tier's model set | D4 (canonical probe set), D7 (both deploy scripts), D10 (overlay deploy + live verification). |
| AC4 — free-tier agents removed per design; both builds exit 0; tests + docs updated | D2 (8 removals + orchestrator repoint), D3 (build wiring), D8 (docs/skills), D9 (suite), D10 (overlay). |

---

## 7. Carried apply-now item — resolved

`agent-improvements.md` 20261029-2: "use `opencode-go/glm-5.3-flash` for every
bulk-role child because the zen default routes to free big-pickle". After this
MDU the dispatch default is paid (`just-code` → deepseek-v4.1-flash,
mid/premium as tabled), so the per-dispatch override is **dropped**; the
20261029-2 entry is closed with "resolved by MDU-40 — default tier paid".

---

## 8. Spawn brief facts

- Base repo: this repo (docs/design cross-ref is `../mdu-39-free-tier-forensics.md`'s sibling root); overlay sibling: `opencode_agents` (second commit, after base green).
- Canonical `opencode.json`: 28 agents → **20**; delete `just-code-free`, `test-agent-free`, `code-reviewer-free`, `devops-free`, `qa-free`, `research`, `deepseek-research`, `nemotron-research`; repoint `orchestrator` to `opencode-go/mimo-v2.5` (stays `default_agent`).
- Zero `opencode/*` model rows may remain. `deep-research` (`opencode-go/mimo-v2.5`) is the only research agent.
- 18 sites: `"resource": "research"` → `"resource": "deep-research"` (grep first).
- Delete `scripts/lib/gen_zen_config.py` + `config/zen-model-map.json`; drop the zen step in `scripts/build.sh`; keep `config/model-registry.txt`.
- `validate.py`: delete `validate_zen` + `--variant`; add paid-only census (prefix `opencode-go/`|`xai/`, no `big-pickle`, `default_agent` exists); keep `GROK_MODEL_ALLOWLIST`.
- `probe_models.py`: `--config` is the source of truth; drop `--map` and alternates; `map_sha256` → `config_sha256` (sorted `agent=model`); `--include-xai` accepted-deprecated, xai auto-on; no live calls in pytest.
- Deploy (both repos): `TIER="paid"`, accept `paid|go`, reject `zen` exit 2, no parked file, probe `--gate --config build/opencode.json`, `grok_xai_gate` once on the active config.
- Mirrors: base `prompts/orchestrator.md` loses all `*-free` bullets and the free-research sentence; base `grok/agents/orchestrator.md` needs the new sentence + `research` → `deep-research` in failure triage (L179); overlay `grok/agents/grokestrator.md` lines 120/128 rewritten. All three must contain: `All loop phases run on paid models; free-tier variants are retired (MDU-40).`
- Keep the ledger `model_tier` enum (`free|budget|mid|premium|top-tier`) unchanged.
- Docs: `docs/model-registry.md` (keep the 2026-10-29 cap table as historical), `README.md`, `docs/opencode-v2.md`, `skills/mdu-lifecycle/SKILL.md`, `evals/.../driver.sh` default model → `opencode-go/deepseek-v4.1-flash`.
- Tests: delete `tests/test_mdu_33_zen_variant.py`; reduce `test_mdu_38_model_probe.py` and both `test_mdu_42_grok_xai.py` (base + overlay); reduce overlay `test_mdu_36_tier_deploy.py`; add `tests/test_mdu_40_paid_default.py`. Expect ~480-495 base tests, all green.
- No agent-definition or config edits outside the listed files. No `aws`, no upstream reports. Commit base, push, then overlay.
