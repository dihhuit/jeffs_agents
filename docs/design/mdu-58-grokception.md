# MDU-58 · Grokception — `grok-inception` on the xAI provider

**Status:** design complete (2026-11-11) · **Repo:** base (`open-agent-definitions`) · **Type:** config + prompt MDU
**Authoritative ACs:** `FEATURE_BACKLOG.md` lines 346–358. This doc settles every fork; implementers follow it as written.

## 1. Probe evidence (20261030-1 rule — both candidates probed live before implementation)

| Model id | Method (2026-11-11) | Result | Notes |
| --- | --- | --- | --- |
| `xai/grok-build-0.1` | `probe_models.py --refresh` on `build/opencode.json` (base) | exact-OK, 1 attempt, 6.34 s | already a base config target via `grok-review` |
| `xai/grok-4.7` | `opencode run -m xai/grok-4.7 "Reply with exactly: OK"` | exact `OK` | **chosen id**; becomes a base config target via this MDU |

Both ids are in `GROK_MODEL_ALLOWLIST` (`scripts/lib/validate.py:26`) and in the registry snapshot `config/model-registry.txt` (`xai/grok-4.7` at line 54, `xai/grok-build-0.1` nearby) — the model-refs validator passes with **no snapshot change**.

## 2. Decision record

**Naming — `grok-inception` (user-fixed, 2026-11-11).** The `grok-` prefix triggers the MDU-42 hard rule: the name itself guarantees xAI billing in every enforcement layer (`model_registry.is_grok_named` → `grok_xai_errors`, validator `validate.py:183-184`, deploy gate). No alternative was considered.

**D1 — Model: `xai/grok-4.7`.**
- **Cross-harness behavioral parity:** Grok Build's `inception` (`grok/agents/inception.md`, frontmatter `model: grok-4.7`, MDU-20) already runs the interviewer on grok-4.7. The user's ask is the *same interviewer* billed to xAI in OpenCode — matching the flagship means identical model behavior across harnesses.
- **Role tier:** per the MDU-25 split, grok-4.7 is the reasoning/user-facing rung and grok-build-0.1 the bulk loop rung (`grok-review` is a bulk review). An interviewer is interactive, judgment-heavy, user-invoked, and *never auto-spawned* (base `inception` denies subagent), so flagship quality has no fleet-cost multiplier. Cost delta accepted: spend is per user session, not per MDU phase.
- Both candidates probed green (§1); loser (`xai/grok-build-0.1`) stays available for future bulk roles.

**D2 — Grok mirror: NO `grok/agents/grok-inception.md` ships.**
- Grok Build already has a user-invoked primary `inception` on grok-4.7; a second profile would be a duplicate user-invoked primary (two `grok --agent` entries, same behavior, different name). The xAI-billing intent is an OpenCode-harness concern only.
- **mdu-45 census:** `validate_grok_registry_census` is one-directional (grok profile → registry entry; `validate.py:255-257` — registry-only entries like `deep-research`/`test-agent-mid` are explicitly legal). No profile → no registration obligation.
- **Parity rule tolerance, verified:** `validate_parity` iterates `build/prompts/*.md`, looks up `GROK_MIRRORS.get(stem)`, and **skips stems absent from the dict** (`validate.py:370-374`). The summary count sums `len(GROK_MIRRORS[stem])` over dict keys whose prompt exists (`validate.py:658-662`) — an unmatched prompt never enters it. `prompts/grok-inception.md` keeps parity at **"20 prompt↔grok pairs consistent"** with zero errors.
- **Corollary (hard):** do NOT add a `"grok-inception"` key to `GROK_MIRRORS` (it would demand a missing mirror and fail the build) and do NOT add `ROLE_KEYWORDS["grok-inception"]` (dead entry; parity only consumes it for mirrored stems).

**D3 — Placement: base repo. `inception` is generic (MDU-20 promoted it public); its xAI-billed variant is equally generic — any base user may want it. The overlay is for personal deltas, not shareable agents.**
- Overlay inheritance verified: overlay root `opencode.json` declares no `inception`/`grok-inception` entry → build rule "add root entries only if the name is absent" flows the base `grok-inception` into the merged registry untouched. **Merged census 43 → 44.**
- Overlay needs **no** `agents` entry, no overlay source edit, and no overlay test widening: the only overlay count pin is `AGENT_COUNT = 22` (`opencode_agents/tests/test_mdu_40_overlay_paid_default.py:48`) which counts the overlay *root* registry (unchanged by this MDU). No overlay test pins the merged count; the merged 44 is verified by the validator census line during the overlay build (§7).
- Overlay grok-xai tests read the overlay root registry only (`test_mdu_42_grok_xai.py:41-61`) — unaffected. The merged config's grok-xai rule is enforced by the base validator at overlay build time (`validate.py:184`) and the deploy gate.

**D4 — Prompt body: new file `prompts/grok-inception.md`, adapted from `prompts/inception.md`.**
- **Clause-by-clause review finding:** `prompts/inception.md` carries **no shared/batch clauses** (no orchestrator-loop delegation text, no secret-scan, no ledger, no repo-ownership block) — every clause is inception-specific. Therefore the adaptation is **identity + tone only**; the interview/spec contract, hard constraints, and safety constraints carry over with the 50-step cap **verbatim**.
- Identity line: name the agent **Grok-Inception**, state it is the xAI-Grok-flavored variant of the Inception interviewer running on the user's xAI flagship, and keep "user-invoked; not part of the orchestrator's automatic MDU loop" verbatim (matches the subagent-deny permission).
- Keep the full responsibilities list (one-two focused questions, MoSCoW coverage, summarize-and-confirm, gap-fill existing spec, `spec.md` section list, question-tool usage, architect/orchestrator handoff offer, token-efficiency bullet).
- Keep the tone precedent of `prompts/grok-review.md` (the only existing xai-billed base prompt): grok-* prompts are near-copies with identity adjustments — do not invent new behavioral clauses.
- **No overlay tokens** (`browser-os`, `safekids`) — base-file hygiene, pinned for `inception` by `tests/test_inception_agent.py:37,151-155`; the new test file pins it for `grok-inception` too.

## 3. Exact `opencode.json` block (insert immediately after the `"inception"` block — the registry's current last agent, ending `opencode.json:3052` — keeping the interviewers adjacent in the role-grouped order)

```json
"grok-inception": {
  "mode": "primary",
  "description": "Grok-flavored project inception specialist — interviews you on a new idea on the xAI Grok flagship and iteratively refines it into a complete spec/requirements document (user-invoked; xAI-billed)",
  "model": "xai/grok-4.7",
  "system": "{file:./prompts/grok-inception.md}",
  "permissions": [
    { "action": "edit", "resource": "*", "effect": "allow" },
    { "action": "read", "resource": "*", "effect": "allow" },
    { "action": "glob", "resource": "*", "effect": "allow" },
    { "action": "grep", "resource": "*", "effect": "allow" },
    { "action": "webfetch", "resource": "*", "effect": "allow" },
    { "action": "websearch", "resource": "*", "effect": "allow" },
    { "action": "question", "resource": "*", "effect": "allow" },
    { "action": "todowrite", "resource": "*", "effect": "allow" },
    { "action": "shell", "resource": "*", "effect": "deny" },
    { "action": "subagent", "resource": "*", "effect": "deny" }
  ],
  "request": {
    "body": {
      "temperature": 0.4
    }
  }
}
```

- Permissions are **byte-identical in meaning** to base `inception` (`opencode.json:2995-3045`); compacted here for the doc — copy the file's exact one-key-per-line style at implementation.
- `temperature: 0.4` mirrors base `inception` (`opencode.json:3047-3051`) — the request-body value follows the **role** (interview warmth), not the provider; contrast `grok-review`'s 0.1 (review precision).
- No `color` (base `inception` has none). Schema requires only `mode`/`description`/`system` (`schemas/opencode.schema.json:33`); `primary` is in the mode enum.

## 4. Files to touch (base only, plus overlay rebuild)

| File | Change |
| --- | --- |
| `opencode.json` | insert §3 block after `inception` |
| `prompts/grok-inception.md` | new, per D4 |
| `README.md:474` | `(21 agents, all paid)` → `(22 agents, all paid)` |
| `README.md:475-487` | `— 12 files` → `— 13 files`; tree: `inception.md` becomes `├──`, add `│   └── grok-inception.md` after it |
| `README.md:~153` (What's Inside, OpenCode table) | new row: `` | Inception (xAI) | [`grok-inception`](prompts/grok-inception.md) | [prompts/grok-inception.md](prompts/grok-inception.md) | Idea → spec interviewer on the Grok flagship (xAI-billed; user-invoked). | `` |
| `tests/test_mdu_40_paid_default.py:79` | `== 21` → `== 22` |
| `tests/test_mdu_45_grok_review_registry.py:83` | `== 21` → `== 22` |
| `tests/test_mdu_45_grok_review_registry.py:264-265` | `"(21 agents, all paid)"` → `"(22 agents, all paid)"`; `"— 12 files"` → `"— 13 files"` (optionally rename `test_readme_layout_counts_21_12` → `…_22_13`) |
| `tests/test_mdu_58_grok_inception.py` | new pin file (§5) |
| `FEATURE_BACKLOG.md` | MDU-58 status → done at close (per house practice) |
| `docs/design/mdu-58-grokception.md` | this file |

No `scripts/lib/validate.py` change (GROK_MIRRORS / ROLE_KEYWORDS / allowlists / census code all stay put — see D2). No `config/model-registry.txt` change. No `docs/model-registry.md` change required (its line 253 "currently `xai/grok-4.7` for reasoning roles" becomes more true, and no test pins a base xai census there).

## 5. New test file `tests/test_mdu_58_grok_inception.py` (model: `tests/test_inception_agent.py` structure)

1. Registry: `grok-inception` present; `mode == "primary"`; `model == "xai/grok-4.7"`; `system == "{file:./prompts/grok-inception.md}"`; permissions deny `shell *` and `subagent *`, allow `question *`; `request.body.temperature == 0.4`; no legacy `tools` block.
2. xAI rule: `model_registry.grok_xai_errors(config["agents"], label="opencode.json") == []` on the real config; `is_grok_named("grok-inception")` is true.
3. Prompt file exists and contains the inception contract phrases (reuse `test_inception_agent.REQUIRED_PHRASES`): `hard constraints`, `interview`, `spec.md`, `moscow`, `complete enough`, `question`, `50 loop steps`; and the step-limit regex `50\s+loop[\s-]*steps`.
4. No-mirror decision pinned: `"grok-inception" not in validate.GROK_MIRRORS` and `grok/agents/grok-inception.md` does **not** exist.
5. Overlay-leak discipline: parametrized `("browser-os", "safekids")` absent from the prompt.
6. README roster row present: `[`grok-inception`](prompts/grok-inception.md)` in the What's Inside section (also enforced generically by `test_mdu_13_readme_gallery.py:56-69` + link-resolution at `:72`).

## 6. Out of scope (explicit)

- **No `grok/agents/grok-inception.md`** (D2) — and no `GROK_MIRRORS`/`ROLE_KEYWORDS`/`GROK_CENSUS_ALLOWLIST`/`GROK_MODEL_ALLOWLIST` edits.
- **No deploy `--force`** — build-only MDU; installed trees refresh at the next routine deploy. An immediate `--force` requires the per-action user approval gate (AC5).
- **No overlay source edits** — no `opencode_agents/opencode.json` agents entry, and **no overlay root `prompts/grok-inception.md`** (same-name overlay root copies are dead per build precedence and forbidden by the MDU-44 dead-copy hygiene pins).
- No base `inception` entry change (`tests/test_inception_agent.py:110-132` scopes its "no xai/" prohibition to the base `inception` agent dict only — verified unaffected).
- No prompt-regression baseline change (no golden-targeted file — `prompts/orchestrator.md`, `grok/agents/orchestrator.md`, `prompts/just-code.md` — is touched).

## 7. Runbook (ordered; every long command under `timeout`)

1. Base build: `timeout 300 ./build.sh` — expect census line `opencode.json: 22 agents`, parity `20 prompt↔grok pairs consistent`, grok census unchanged (`research` only allowlisted), paid census green, grok-xai green, schema green.
2. Base tests: `timeout 120 python3 -m pytest tests/ -q` — full suite green with widened pins + new file.
3. Prompt-regression gate: `timeout 60 python3 scripts/lib/prompt_regression.py gate` — exit 0, baseline unchanged (7/7).
4. Secret gate: exit 0 (per MDU-11 discipline).
5. **Base probe refresh (mandatory, hash-driven):** adding any agent changes `config_sha256`; the report goes red until refreshed. `timeout 300 python3 scripts/lib/probe_models.py --refresh --gate --config build/opencode.json` — the base report's `xai_results` gains its first `xai/grok-4.7` ok entry.
6. Overlay build (from overlay root): `timeout 300 ./build.sh` — merged census `44 agents`, 44 Claude subagents including `build/claude/agents/grok-inception.md`, parity 20, grok-xai green on the merged config (22/22 grok-named on `xai/*`).
7. Overlay tests: `timeout 120 python3 -m pytest tests/ -q` — nothing to widen (D3); must stay green.
8. **Overlay probe refresh (mandatory):** `timeout 300 python3 ../open-agent-definitions/scripts/lib/probe_models.py --refresh --gate --config build/opencode.json --report config/model-probe-report.json`.
9. Evidence: commands, gate outputs, observed counts → `mdu-58-deploy-evidence.md` under `/tmp/opencode`; run manifest under `runs/mdu-58/` validated with `run_ledger.py validate` (gitignored, not committed). Missing logs do not block commit.

**Expected counts:**

| Artifact | Before | After |
| --- | --- | --- |
| base `opencode.json` agents | 21 | 22 |
| base `prompts/` files | 12 | 13 |
| base grok profiles | 20 | 20 |
| base Claude agents (build) | 21 | 22 |
| base grok-named registry entries on `xai/*` | 1/1 | 2/2 |
| parity pairs | 20 | 20 |
| merged `opencode.json` agents | 43 | 44 |
| merged grok-named entries on `xai/*` | 21/21 | 22/22 |
| merged Claude agents | 43 | 44 |

## 8. Commit plan (one commit per repo, user-owned remotes only)

**Base** — subject `feat(mdu-58): register base grok-inception on xai/grok-4.7` — stage exactly: `opencode.json`, `prompts/grok-inception.md`, `README.md`, `tests/test_mdu_40_paid_default.py`, `tests/test_mdu_45_grok_review_registry.py`, `tests/test_mdu_58_grok_inception.py`, `FEATURE_BACKLOG.md`, `docs/design/mdu-58-grokception.md`. Base `build/` and `runs/` are gitignored; anything else in `git status` → stop and investigate.

**Overlay** — after base push + fresh overlay build; never `git add -A` (`build/` is tracked) — stage exactly the dirtied build paths, expected: `build/opencode.json`, `build/prompts/grok-inception.md`, `build/claude/agents/grok-inception.md`. Subject: `feat(mdu-58): rebuild merged build tree with base grok-inception`. Verify with `git status --porcelain` first; no overlay source edits.
