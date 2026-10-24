# MDU-33 Design — Zen Variant Set (two tiers: Zen default, Go switch-up)

**Date:** 2026-10-24 · **Status:** design complete, ready for implement
**Backlog:** `FEATURE_BACKLOG.md` §MDU-33 (AC-1..AC-4) · **Depends on:** MDU-01 (model registry — shipped)
**Adjacent:** `docs/model-registry.md` §Cost audit (MDU-32) is the documentation template; `docs/opencode-v2.md` §3 records the `opencode-zen/big-pickle` → `opencode/big-pickle` legacy alias.

## Context

`opencode.json` (28 agents) references Go models (`opencode-go/*`) in 19 agents; 9 are already free Zen (`opencode/*`). The user repeatedly hits Zen usage limits, so this is a **two-tier setup**, not a Go-free fallback: Zen tier is the default; the Go tier is the switch-up when Zen usage for the period is exhausted. Scope: the **OpenCode leg only** — Grok profiles use `xai/*` and Claude subagents are generated model-less, so neither is affected. The overlay repo is out of scope (D7).

---

## D1 — Generation strategy: build-time transform (RECOMMENDED) vs checked-in file

**Decision: build-time transform.** `build.sh` generates `build/opencode.zen.json` from the canonical `opencode.json` via a new `scripts/lib/gen_zen_config.py` + a checked-in mapping table `config/zen-model-map.json`. No second 3,700-line file is committed at repo root; `build/` is gitignored in the base repo, so CI regenerates and validates the artifact on every run.

| Option | Verdict | Why |
|---|---|---|
| **Build-time transform** | **chosen** | Single source of truth: any `opencode.json` edit (permissions, prompts, new agent) flows into the Zen variant by construction — zero two-file drift. The transform is total and tiny (model + description strings only). Validation gates the generated file every build (D4). Overlay can later reuse the same script on its merged config (D7). |
| Checked-in `opencode.zen.json` | rejected | A hand-maintained near-duplicate of a 3,700-line file is exactly the structural drift this repo's parity tests exist to prevent. Every permission tweak or new agent requires hand-mirroring; the enforcement test would have to re-implement the transform. |

Trade-off accepted: the Zen artifact is not human-diffable in PRs (it is generated). Mitigated by the committed, reviewable mapping table and build-time parity assertions (same agent set, same permissions/prompt refs/temps per agent — D4 checks).

## D2 — Model-mapping table (exact)

Free Zen catalog per `config/model-registry.txt` (verified 2026-10-08): models with the `opencode/` provider prefix — `big-pickle`, `exo-free`, `ling-3.0-flash-fin-free`, `ling-3.1-flash-free`, `longcat-2.5-preview-free`, `mimo-v2.6-flash-free`, `muse-spark-1.3-contributor-free`, `nemotron-3.5-lightning-free`, `nemotron-3-ultra-free`, `space-bunny-free`, `step-5-preview-free`. Note: `opencode/big-pickle` is free Zen despite no `-free` suffix. The legacy alias `opencode-zen/big-pickle` is NOT used (prefix `opencode-zen/` ≠ `opencode/`).

The free catalog preserves **none** of the Go budget/mid/premium distinction, and only four free models have in-repo usage evidence: `big-pickle` (orchestrator + all `-free` slots, eval driver default), `nemotron-3-ultra-free` (deepseek-research), `nemotron-3.5-lightning-free` (nemotron-research), `mimo-v2.6-flash-free` (research). The mapping therefore collapses the four Go tiers into the two proven free generalists, keyed by source model:

| Source (`opencode-go/*`) | Agents (count) | Zen target | Rationale |
|---|---|---|---|
| `opencode-go/deepseek-v4.1-flash` | just-code, test-agent, inception (3) | `opencode/big-pickle` | Strongest proven free model; already carries these exact roles via the `-free` variants. |
| `opencode-go/kimi-k2.7-code` | just-code-mid, test-agent-pro, qa-pro, ui-ux-designer-pro (4) | `opencode/nemotron-3-ultra-free` | Second proven free generalist; distinct model so the coding loop spreads across two free models. |
| `opencode-go/glm-5.2` | just-code-pro, code-reviewer-pro, architect, architect-premium, devops-pro (5) | `opencode/big-pickle` | **Documented capability regression** — nothing free matches glm-5.2's reasoning tier; premium slots get the best available free model. This regression is the primary documented trigger to switch up to Go mid-period. |
| `opencode-go/mimo-v2.5` | test-agent-mid, code-reviewer, devops, qa, deep-research, ui-ux-designer, introspector (7) | `opencode/nemotron-3-ultra-free` | Same rule as the kimi block: mid slots → the second free generalist, spreading load. |

**Unchanged (already free, 9):** orchestrator, just-code-free, test-agent-free, code-reviewer-free, devops-free, qa-free (`opencode/big-pickle`); research (`opencode/mimo-v2.6-flash-free`); deepseek-research (`opencode/nemotron-3-ultra-free`); nemotron-research (`opencode/nemotron-3.5-lightning-free`).

Resulting Zen distribution: `big-pickle` = 14 agents, `nemotron-3-ultra-free` = 12, lightning/flash = 3 research agents. Concentration on `big-pickle` is a known limitation, mitigated by (a) the tier switch-up (D5) — the primary response to exhaustion; (b) per-agent overrides (below) for cheap retuning without code changes; (c) premium slots being low-volume (MDU-32: premium escalation share is small).

**Alternates (unevaluated — not placed on hot paths; candidates for a future bake-off):** `exo-free`, `space-bunny-free`, `step-5-preview-free`, `longcat-2.5-preview-free`, `muse-spark-1.3-contributor-free`, `ling-3.1-flash-free`.

**Per-agent overrides:** the map file also carries `overrides: { "<agent-name>": "<model>" }`, applied after the model-keyed rules; empty by default. Documented as the tuning knob when live usage shows one slot rate-limiting.

**Implementer must re-verify before finalizing:** run `opencode models` and confirm the catalog and the free set (snapshot is 2026-10-08); if a target is gone or a stronger free model exists, update the map — it is data, not code.

**Tier-variant note:** in the Zen tier the `-mid`/`-pro`/`-free` variants keep distinct names, permissions, and temperatures but share models (e.g. just-code ≡ just-code-pro ≡ just-code-free, all `big-pickle`). Variant identity and the orchestrator's model-tier ledger remain meaningful per variant; the model string collapses. Documented limitation.

## D3 — Generator: `scripts/lib/gen_zen_config.py`

CLI: `gen_zen_config.py --input <opencode.json> --map <config/zen-model-map.json> --output <opencode.zen.json>` (input/output parameterized precisely so the overlay can later run it on its merged config — D7).

Transform semantics (total, whole-file):
1. Load input config; for each agent, if `model` is a string in the model-keyed map → replace with target. Already-free refs (`opencode/*`) pass through unchanged (they are not map keys). Apply `overrides` last.
2. Apply `description_substitutions` (list of `[from, to]` exact substrings from the map file) — e.g. `Go budget model` → `Zen free model`, `mid-tier Go model` → `Zen free model`, `premium Go model` → `Zen free model`, `top-tier reasoning model` → `Zen free model`, `mid-tier coding-optimized model` → `Zen free model`. Implementer scans all 28 descriptions and finalizes the rows.
3. Copy everything else byte-for-identical (permissions arrays and their order, `system` refs, `mode`, `color`, `request.body.temperature`, `default_agent`, top-level `permissions`, `$schema`).

**Fail-closed rules (the generator exits non-zero):** (a) an agent whose model is not in the map and not already `opencode/*` — a new Go agent without a mapping must never silently leak into the Zen file; (b) a map target that is not in the free Zen set (D4 derivation); (c) a map source that no longer appears in any agent (stale table row — warn, not fail); (d) a map `overrides` agent name not present in the config.

## D4 — Validator support

1. `scripts/lib/model_registry.py`: add `free_zen_models(registry) -> set[str]` = `{m for m in registry if m.startswith("opencode/")}`. The prefix filter automatically excludes `opencode-go/*`, `opencode-zen/*`, and `xai/*`. This is the **OPENCODE_ZEN_ALLOWLIST** — derived from the committed registry snapshot (dated, refreshed per MDU-01 flow) rather than hardcoded, unlike `GROK_MODEL_ALLOWLIST`, because the snapshot already is the pinned source of truth for model IDs.
2. `scripts/lib/validate.py`: add `validate_zen(build_dir) -> list[str]`, run when `build/opencode.zen.json` exists: (a) every `find_model_refs` pair is in the free set and no ref starts with `opencode-go/`; (b) the raw file text contains no `opencode-go/` substring anywhere (models *and* descriptions); (c) agent-set parity: same agent names, and per agent the `permissions`, `system`, `mode`, `color`, `request.body.temperature` are deep-equal to `build/opencode.json` (only `model` and `description` may differ); (d) schema check: extend `validate_schema` to also validate `opencode.zen.json` against `schemas/opencode.schema.json`.
3. `validate.py` CLI: add `--variant {go,zen,both}` (default `both`; when the zen file is absent, zen checks are skipped with an `[info]` line — a pre-MDU-33 build tree stays valid — but an explicit `--variant zen` on a missing file is an error, so a caller that asked for Zen cannot silently pass). `zen` validates only the zen variant, `go` only the base config. This, plus the deploy flag (D5), is the documented "selecting the Zen variant" surface (AC-2); `./build.sh` itself always produces and validates both — forking the build to emit only one variant would break Claude generation, which consumes `opencode.json`.
4. `scripts/build.sh`: after `gen_claude_agents.py`, before `validate.py`, invoke `gen_zen_config.py` on the staged `build/opencode.json`. No `stage_source_tree` change (the file is generated, not staged). CI (`ci.yml` gate 1) needs no edit — it runs `./build.sh`, which now emits and validates the zen file; gate 4's registry-alignment eval checks only `opencode.json` and stays green.

## D5 — Tier selection and mid-period switching (first-class)

Verified facts about the OpenCode CLI (2026-10-24):
- There is **no `--config <file>` CLI flag**. The request (anomalyco/opencode issue #2066) was closed unimplemented (automated inactivity close, 2025-12-28).
- The **`OPENCODE_CONFIG` env var** is documented in V1-era docs as highest-precedence config selection, but is absent from V2 docs. **Verify on V2 before documenting**: `OPENCODE_CONFIG=~/path/opencode.zen.json opencode debug agents`. If unverified, ship only the file-swap mechanism below; if verified, document it as the per-invocation option.
- V2 config discovery is filename-based (`opencode.json(c)`, `.opencode/opencode.json(c)`, global→project precedence). A file named `opencode.zen.json` sitting in `~/.config/opencode/` is ignored by discovery — it is inert until swapped in.

**Mechanism (primary):** `scripts/deploy.sh` gains `--tier {zen,go}`, **default `zen`** (AC-3: Zen is the default tier). Deploy always installs **both** files: the selected tier lands as `~/.config/opencode/opencode.json` (active), the other is parked as `~/.config/opencode/opencode.zen.json` / `opencode.go.json` (inert by discovery). Prompts/skills deploy unchanged — both tier files reference the same `./prompts/` tree, so a tier swap is safe.

Mid-period switch, three documented paths:
1. **Redeploy switch:** `./deploy.sh --force --tier=go` (or `--tier=zen` to switch back). Seconds, no rebuild needed.
2. **Manual one-liner (no repo needed):** `cp ~/.config/opencode/opencode.zen.json ~/.config/opencode/opencode.json` (parked files survive).
3. **Per-session/headless (if V2-verified):** `OPENCODE_CONFIG=...` env var, or `opencode run --model <id>` for single-shot model pinning (the eval drivers already use `--model`).

Config is read at session start: after a swap, **start a new session** (or `opencode service restart`). Switching tiers is safe mid-period — sessions are stateless w.r.t. config; the run ledger keeps recording per-phase tiers. `deploy_opencode_json()` edits: parse `--tier` in the arg loop, choose the source file accordingly, keep the `opencode debug agents` smoke gate (it now validates whichever tier is active), and log which tier was installed.

## D6 — Documentation changes

1. **`README.md`** — rewrite the Prerequisites block (currently "OpenCode Go Subscription" + the manual-swap bullet at line 27, which this MDU replaces): two-tier section "Model Tiers — Zen (default) / Go (switch-up)": Zen is the default tier (`./deploy.sh --force`); switch up when Zen usage for the period is exhausted (`./deploy.sh --force --tier=go`); the manual `cp` one-liner; the new-session/restart note; the OPENCODE_CONFIG option only if verified (D5); link `docs/model-registry.md` §Zen variant for the mapping table.
2. **`docs/model-registry.md`** — new section "Zen variant mapping (MDU-33)" in the MDU-32 cost-audit style: the D2 tables (model-keyed + unchanged list), the two-block rationale, alternates, overrides knob, dated catalog verification, the `opencode models` re-verify command, and the premium-regression note (glm-5.2 slots → big-pickle is the documented switch-up trigger).

## D7 — Overlay consequence (out of scope, must be noted)

The overlay build (`opencode_agents/scripts/build.sh`) constructs its own `opencode.json` from the base **source** tree + overlay merges; it does not consume base `build/`, so it is unaffected — and the user's daily deployed config does NOT change with this MDU. Because the generator is `--input/--output` parameterized, overlay adoption later is a one-line `gen_zen_config.py --input build/opencode.json --output build/opencode.zen.json` call in the overlay build plus an overlay `--tier` flag — a follow-up MDU in the overlay repo, explicitly not in scope here. Record this in the README section as "overlay users: see overlay repo" and in the run manifest notes.

## Acceptance-criteria mapping

| AC | Requirement | Design element | Gradeable check |
|---|---|---|---|
| AC-1 | Zen-only config exists, all models in free Zen allowlist | D1–D3: `build.sh` emits `build/opencode.zen.json` via transform | `validate.py` zen gate green: every ref in `free_zen_models(snapshot)`, zero `opencode-go/` occurrences |
| AC-2 | build/validation supports selecting the Zen variant, documented | D4 `--variant`, D5 `--tier`, D6 README | `python3 scripts/lib/validate.py build --variant zen` exits 0; README documents both flags |
| AC-3 | README: two-tier setup, Zen default, Go switch-up, concrete commands | D5, D6 | README contains default-zen + `--tier=go` switch-up instructions with commands |
| AC-4 | Run manifest created and validated | `runs/mdu-33/manifest.json` per MDU-15 inlined schema | `run_ledger.py validate runs/mdu-33/manifest.json` exits 0 |

## Model-tier routing for this MDU (stated for the orchestrator)

Agents are addressed **by name**; both tiers serve every name (Zen: D2 two-block models).

| Phase | Agent | Does |
|---|---|---|
| design | architect | This doc only; no production code |
| implement | just-code (budget) | Edits `scripts/`, `config/zen-model-map.json`, `README.md`, `docs/model-registry.md` |
| test | test-agent (budget) | Writes `tests/test_mdu_33_zen_variant.py`; runs `pytest` + `./build.sh` (allowlisted shell) |
| review | code-reviewer / code-reviewer-pro | Read-only; grade from attached artifacts |
| deploy | devops | Runs `./deploy.sh` dry-run; `--force` installs only with user confirmation |
| validate/QA | qa | Read-only + allowlisted `pytest*`/`./build.sh*` shell; grades AC-1..4 from the repo |
| gates | — | `./build.sh` (includes validate.py), pytest, `run_ledger.py validate` — run by test-agent/qa/devops per the allowlisted-shell rule |

## Test plan sketch (`tests/test_mdu_33_zen_variant.py`)

1. Transform on the real `opencode.json`: output has the same 28 agent names; every model in the free set; zero `opencode-go/` bytes in the file.
2. Per-agent deep parity: `permissions`/`system`/`mode`/`color`/`request.body.temperature` identical to source; only `model`/`description` differ.
3. Fail-closed: synthetic config with an unmapped Go model → non-zero exit; map target outside the free set → non-zero exit; stale map source → warning; unknown override agent → non-zero exit.
4. `free_zen_models` derivation from a fixture registry: includes `opencode/*`, excludes `opencode-go/*`, `opencode-zen/*`, `xai/*`.
5. `validate_zen` on fixtures: a zen config with a Go model → errors; zen file absent → skipped gracefully.
6. `--variant` flag: `main()` on a prepared build dir with `--variant zen`/`go`/`both` behaves as specified.
7. Description substitutions: output descriptions carry no `Go `-tier phrasing covered by the substitution rows.
8. Integration (existing `test_validate_integration.py` pattern): full build emits `build/opencode.zen.json` and validate passes; README strings test (default-zen, `--tier=go`) in the MDU-13 README-test style.

## Verify-live checklist for the implementer

1. `opencode models` — confirm the 11-model free set and targets before freezing the map (D2).
2. Confirm the zen file's per-agent `request.body.temperature` values are accepted by the free models (drop-temperature fallback is a follow-up if any model rejects it).
3. `opencode debug agents` with the zen config installed (deploy smoke gate already covers this).
4. `OPENCODE_CONFIG` on V2 (D5) — document only if verified.
5. `./deploy.sh` dry-run then `--force` on the user's machine is a **user-confirmed** step (deploy to user config dirs).

## Risks / limitations (documented, not blocking)

- **Capability regression** on premium slots (glm-5.2 → big-pickle) — by design; the switch-up path is the mitigation.
- **Model concentration** (14 agents on big-pickle) — mitigated by overrides + switch-up.
- Zen per-model vs account-wide usage limits are **not established** here; the design assumes spreading helps but treats `--tier=go` as the primary exhaustion response.
- Generated artifact is not committed (gitignored `build/`); the committed, reviewable surface is the map file + tests + docs.

---

DESIGN: READY

Files the implementer creates/edits:
- `config/zen-model-map.json` — NEW: model-keyed mapping, overrides, description_substitutions, alternates metadata.
- `scripts/lib/gen_zen_config.py` — NEW: transform generator (D3), fail-closed.
- `scripts/lib/model_registry.py` — EDIT: `free_zen_models()` helper (D4.1).
- `scripts/lib/validate.py` — EDIT: `validate_zen()`, `--variant` flag, schema check on the zen file (D4.2–D4.3).
- `scripts/build.sh` — EDIT: invoke the generator between Claude generation and validation (D4.4).
- `scripts/deploy.sh` — EDIT: `--tier {zen,go}` (default zen), install active + parked config files, tier-aware logging (D5).
- `README.md` — EDIT: replace Prerequisites/manual-swap bullet with the two-tier section (D6.1).
- `docs/model-registry.md` — EDIT: add "Zen variant mapping (MDU-33)" section (D6.2).
- `tests/test_mdu_33_zen_variant.py` — NEW: test plan above.
- `runs/mdu-33/manifest.json` — NEW at run end (orchestrator, AC-4; gitignored dir, validated via `run_ledger.py`).
