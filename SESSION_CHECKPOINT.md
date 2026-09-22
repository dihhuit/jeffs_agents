# Session Checkpoint — 2026-09-16

**Why this exists:** the previous session made the machine laggy. Stop here. Resume from this file in a **new session** (do not try to resume the old conversation forever).

**Repos:**
- Base (public): `/mnt/FastSSDXFS/projects/agents/open-agent-definitions` → `github.com:dihhuit/jeffs_agents.git` — HEAD **`db42cad`** (plus this checkpoint commit)
- Overlay (personal): `/mnt/FastSSDXFS/projects/agents/opencode_agents` → `github.com:dihhuit/opencode_agents.git` — HEAD **`7d2799e`**

---

## Read these first (in this order)

1. This file.
2. `FEATURE_BACKLOG.md` — remaining work. **Next item: MDU-15.**
3. `examples/upgrade-story.md` — what the last session actually did, including Cross-CLI Headless Validation (honest per-CLI verdicts).
4. Overlay `AGENTS.md` at `/mnt/FastSSDXFS/projects/agents/opencode_agents/AGENTS.md`.

Then: `git log --oneline -15` and `git status` in **both** repos before touching anything.

---

## What is done (do not redo)

### Base — 10 of 14 original MDUs + harness provenance

| ID | What | Commit |
|---|---|---|
| MDU-01 | Stale research models fixed; `scripts/lib/model_registry.py` + `config/model-registry.txt` | `a04fc3a` |
| MDU-02 | GitHub Actions CI, 4 gates, README badge. First run failed (pip cache); fixed. | `44f152b` + `ac77c1c` + `c7e776c` |
| MDU-03 | QA `tools` → least-privilege `permission`; `schemas/opencode.schema.json` | `8d5a02f` |
| MDU-05 | 6 Agent Skills + `validate_skills` gate | `0d8990d` |
| MDU-06 | `docs/mcp.md` + `examples/mcp/opencode.mcp.json.example` | `5caf6d1` |
| MDU-07 | `scripts/lib/run_ledger.py`; `/runs/` gitignored; `examples/runs/` committed | `0d8990d` |
| MDU-08 | `scripts/lib/run_evals.py` + 2 smoke evals; CI gate 4 | `5caf6d1` |
| MDU-12 | `docs/autonomy.md`; 4 Human Approval Gates in both orchestrator mirrors | `5caf6d1` |
| MDU-13 | README roster links, upgrade story, examples gallery | `3fa9ca1` + `8f1d7e6` |
| MDU-14 | `validate_parity` — 17 prompt↔grok pairs | `5caf6d1` |
| **A** | **`harness` field** (`opencode\|grok\|claude`) required; `by_harness` in summarize | `d511c21` |
| Cross-CLI docs | Honest findings + **MDU-15** added to backlog | `db42cad` |

**CI:** workflow `ci` on `dihhuit/jeffs_agents`. Last observed green: `35100132230`. **Tests:** `python3 -m pytest tests/ -q` → **136 passed**.

### Overlay

- Combined build **passes all new base gates**: 49 agents, 40 grok, 49 claude, 9 skills, 17 parity pairs, 49 model refs current.
- Process fix: overlay `scripts/build.sh` calls `${GENERIC_DIR}/scripts/lib/validate.py`. Overlay `scripts/lib/validate.py` is a thin wrapper. Commit **`7d2799e`**.
- Overlay `build/` is **tracked**. Last rebuild dirtied `build/claude/agents/*.md`. **Do not `git add -A` in the overlay** unless the user wants generated output committed.

### Deployed machine state

`./deploy.sh --force --rebuild` was run **from the overlay**. Live configs are the **combined overlay**, not the public base:

- OpenCode: `~/.config/opencode/` — 19 prompts, 9 skills, 49-agent `opencode.json`
- Grok: `~/.grok/agents/` — 40 profiles
- Claude: `~/.claude/agents/` — 49 subagents

Headless `opencode run` already used the new defs. Interactive opencode needed a **restart** (and a new session is that restart).

---

## Cross-CLI golden task (do not re-run unless doing MDU-15)

Scratch dirs under `/tmp/opencode/work-{opencode,grok,claude}` (ephemeral):

| CLI | Grade | Tests | Git | Manifest |
|---|---|---|---|---|
| opencode | **PASS** | 10/10 | 2 commits | `harness: opencode`; missing title/timestamps; `qa_grade: "manual-smoke-pass"` |
| grok | **PARTIAL** | 17/17 | **no `.git/`** | `harness: grok`; `status: in_progress`; null verification |
| claude | **PASS** | 33/33 | 1 commit | `harness: claude`; `status: "complete"` (want `completed`); `build: "n/a"` |

Claude **without** `--dangerously-skip-permissions` failed cleanly (Write denied; BLOCKED). Always use that flag headless.

**Root cause of ledger drift:** orchestrator prompt *points at* `docs/observability.md`; agents in a bare scratch dir cannot read it. Fix = **MDU-15** (inline schema + re-test). Raw non-conforming manifests in gitignored `runs/mdu-sumdump-*`. Do not put them in `examples/runs/` until they validate.

---

## Rollback

**Snapshot:** `/tmp/opencode/rollback-20260916-054427/` (opencode.json+prompts+skills, grok agents/skills/config.toml+mcp list, claude agents/JSON+mcp list).

**This is in `/tmp` — gone on reboot.** Copy it somewhere durable if you care:

```bash
cp -a /tmp/opencode/rollback-20260916-054427 \
  /mnt/FastSSDXFS/projects/agents/opencode_agents/.rollback-20260916-054427
```

Restore (only if live config is broken):

```bash
RB=/mnt/FastSSDXFS/projects/agents/opencode_agents/.rollback-20260916-054427
cp "$RB/opencode.json" ~/.config/opencode/opencode.json
rsync -a --delete "$RB/opencode-prompts/" ~/.config/opencode/prompts/
rsync -a --delete "$RB/opencode-skills/" ~/.config/opencode/skills/
rsync -a --delete "$RB/grok-agents/" ~/.grok/agents/
rsync -a --delete "$RB/grok-skills/" ~/.grok/skills/
cp "$RB/grok-config.toml" ~/.grok/config.toml
rsync -a --delete "$RB/claude-agents/" ~/.claude/agents/
```

Nothing was rolled back; live state is the new overlay deploy.

---

## Remaining backlog

| ID | Status | Notes |
|---|---|---|
| **MDU-15** | **NEXT** | Inline run-manifest schema into both orchestrator prompts; re-run golden task on all 3 CLIs until `run_ledger.py validate` passes; grok git-finalize; document claude `--dangerously-skip-permissions`. Criteria already in FEATURE_BACKLOG.md. |
| MDU-04 | not started | Persistent memory (`.agents/memory/`). |
| MDU-09 | not started | Promptfoo regression gate. |
| MDU-10 | not started | Checkpoint/resume protocol. |
| MDU-11 | partial | `secret-scrub` skill exists. Still need `docs/security.md` + commit-gate wiring. |

Original 14: **10 done** (01,02,03,05,06,07,08,12,13,14). Remaining original: 04,09,10,11. Plus MDU-15.

---

## New-session starter prompt (paste this)

> Read `SESSION_CHECKPOINT.md` in `/mnt/FastSSDXFS/projects/agents/open-agent-definitions` first. Then `FEATURE_BACKLOG.md` and the Cross-CLI section of `examples/upgrade-story.md`. Confirm git HEAD is `db42cad` (base, plus the checkpoint commit) and `7d2799e` (overlay). Do **not** re-run MDU-01–14 or the overlay validator migration. Next work is **MDU-15**. Keep the session short, commit often, don't spawn 4 parallel long CLI runs unless asked.

**Still applies:**
- Orchestrator does not implement production code; delegates.
- After each validated MDU: commit **and push**.
- Overlay combined build: run from `opencode_agents/` (sibling `open-agent-definitions` is GENERIC_DIR).
- Claude headless: `--dangerously-skip-permissions`.
- Overlay: never `git add -A` (tracked `build/`).
- Base `runs/` and `evals/results/` gitignored. Public gallery `examples/runs/` has 8 clean manifests, all `harness: opencode`.

```bash
cd /mnt/FastSSDXFS/projects/agents/open-agent-definitions
python3 -m pytest tests/ -q && ./build.sh
python3 scripts/lib/run_ledger.py summarize examples/runs/

cd /mnt/FastSSDXFS/projects/agents/opencode_agents
./build.sh          # now runs ALL new base gates
./deploy.sh         # dry-run
```

---

## Don't assume

- Overlay `build/` dirty — user decides whether to commit generated output.
- `/tmp/opencode/rollback-*` is not durable.
- Untracked in base: `Github_readme_bug.png` — leave it.
- Last interactive opencode process was not restarted after deploy; a new session is.

## Session end

All work from the last user message (harness field, overlay validation, cross-CLI tests + rollback snapshot) is **done and pushed**. No in-flight base-repo code. Overlay `build/` still dirty (expected). **Do not start MDU-15 in a laggy session.**
