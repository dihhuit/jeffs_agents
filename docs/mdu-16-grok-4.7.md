# MDU-16 — Upgrade Grok model bindings to grok-4.7

- **Date:** 2026-10-08
- **Scope:** Every Grok model binding across TWO git repos (public base + private overlay)
- **Flag:** `xai/grok-4.7` is the current xAI flagship (per docs.x.ai/docs/models). grok-4.6 and grok-4.5 remain available and stay allowlisted as legacy.
- **Pattern:** Mirror prior upgrades — public `e7db0f4` ("Update Grok Build agents to grok-4.6"), overlay `e285669` ("Rev overlay grok agents to grok-4.6").

## Goal

Move all Grok agents from `grok-4.6` to `grok-4.7` (model ID + model-selection prose only). No behavior changes, no non-Grok model changes, no git history rewriting.

## Repo 1 — public base

`open-agent-definitions` (`github.com:dihhuit/jeffs_agents`, branch `main`)

| File | Change |
|------|--------|
| `grok/agents/*.md` (18 files) | frontmatter `model: grok-4.6` → `model: grok-4.7` |
| `grok/agents/orchestrator.md` | MODEL SELECTION + TOKEN FRUGALITY prose: grok-4.7 flagship; grok-4.6/4.5 legacy; all profiles use grok-4.7 |
| `README.md` (~lines 133–148, Grok Build profiles) | same wording |
| `scripts/lib/validate.py` | `GROK_MODEL_ALLOWLIST = {"grok-4.7", "grok-4.6", "grok-4.5"}` |
| `config/model-registry.txt` | refresh from `opencode models`; at minimum add `xai/grok-4.7` + `opencode-go/grok-4.7` |
| `docs/model-registry.md` | last-verified date → 2026-10-08 |
| `tests/test_validate_*.py` | **DO NOT edit (test-agent owns).** Add one focused test: production `grok/agents/*.md` frontmatter models ∈ allowlist AND grok-4.7 allowed. Existing `model: grok-4.6` fixtures MAY stay (4.6 still allowlisted). |

**Do NOT touch:** `Github_readme_bug.png`, `examples/` historical manifests, `FEATURE_BACKLOG` (one-line note only if useful).

## Repo 2 — private overlay

`opencode_agents` (`github.com:dihhuit/opencode_agents`, branch `main`). **Must run AFTER Repo 1** — overlay `./build.sh` merges sibling `../open-agent-definitions`.

| File | Change |
|------|--------|
| `opencode.json` | all 22 `xai/grok-4.6` → `xai/grok-4.7` |
| `grok/agents/*.md` | frontmatter grok-4.6 → grok-4.7 |
| `grok/agents/grokestrator.md` | MODEL SELECTION / TOKEN FRUGALITY prose |
| `overlays/grok/agents/{grok-mdu-code,mdu-code,thought-leadership-coach}.md` | frontmatter grok-4.6 → grok-4.7 |
| `README.md`, `AGENTS.md` | flagship grok-4.7; 4.6/4.5 legacy; example `-m grok-4.7` |
| `build/` (~158 files, tracked) | regenerate via `./build.sh` |

Keep `xai/` prefix for OpenCode grok-* agents — do **not** switch to `opencode-go/grok-4.7`.

**Validate script:** overlay `scripts/lib/validate.py` already delegates to the base validator — do **not** reintroduce a local allowlist.

**Staging hygiene:** do NOT stage `.rollback-20260916-054427/`, `__pycache__/`, or unrelated dirty build leftovers. Stage only this model bump + regenerated build output.

## Allowlist policy

Single source of truth: `scripts/lib/validate.py::GROK_MODEL_ALLOWLIST` in the **base** repo.

- `{"grok-4.7", "grok-4.6", "grok-4.5"}`
- 4.6 and 4.5 retained as legacy so historical manifests, fixtures, and rollbacks still validate.
- OpenCode-prefixed forms (`xai/grok-4.7`, `opencode-go/grok-4.7`) live in `config/model-registry.txt`, not the validate allowlist.

## Test plan

1. **Repo 1:** `./build.sh` succeeds; `python3 -m pytest tests/ -q` passes (focused allowlist test added by test-agent).
2. **Grep gates (Repo 1):** no production `grok/agents/*.md` still on `model: grok-4.6`; allowlist contains 4.7/4.6/4.5.
3. **Repo 2:** after Repo 1 updated, `./build.sh` succeeds against the new base.
4. **Grep gates (Repo 2):** no source `model: grok-4.6` or `"xai/grok-4.6"` remains (rollback dir excluded — must not be staged); `build/` grok profiles and `opencode.json` match 4.7.

## Deploy

- `./deploy.sh --force` in each repo (public first, then overlay).
- Optional: `grok update` so the CLI lists grok-4.7 (local Grok CLI 1.0.30 still defaults to grok-4.6; 1.0.50 available). Docs direct users to confirm with `grok models`.

## Order

Public base → verify → private overlay (overlay build depends on updated base).

## Commit messages

- Public: `feat(mdu-16): upgrade Grok Build agents to grok-4.7`
- Overlay: `feat(mdu-16): rev overlay grok agents to grok-4.7`

## Risks

- **Grok CLI 1.0.30** may not yet list grok-4.7; OpenCode already does. Mitigation: allowlist grok-4.7 regardless, keep 4.6/4.5 legacy, advise `grok update` + `grok models`.
- **Overlay merge ordering** — building overlay before base update silently yields stale 4.6 in merged output.
- **Staging leakage** — rollback dir / pycache must not enter the overlay commit.
