# MDU-13 — README modernization & artifact gallery (completion pass)

**Date:** 2026-10-23
**Source:** [FEATURE_BACKLOG.md](../../FEATURE_BACKLOG.md) MDU-13
**Scope:** base repo only. The overlay repo is untouched — its build consumes `build/` output, not `README.md`, `FEATURE_BACKLOG.md`, or `examples/`.

## 0. State of the world

Pass 1 of MDU-13 (commit `3fa9ca1`, 2026-09-16) already delivered: the CI badge, "Autonomy & Guardrails" subsection, "Persistent Memory" subsection, Roadmap links to `GAP_ANALYSIS.md` + `FEATURE_BACKLOG.md`, the "How This Repo Was Upgraded by Its Own Agents" section, `examples/upgrade-story.md`, and `examples/runs/` (now 11 committed manifests). Do not redo any of that.

What remains, mapped to the acceptance criteria:

| Gap | AC |
| --- | --- |
| Agent roster is prose bullets, not a "What's inside" table; no per-role docs links | AC-2 |
| Badge row is a single CI badge; no mechanical link/anchor/badge check anywhere | AC-1 |
| `examples/` has raw manifests but zero *worked examples* (summary + manifest + ledger excerpt) | AC-3 |
| README still carries a `### TODO` section the backlog says to move into `FEATURE_BACKLOG.md` | — |
| Stale content: "Progress: 9/14 as of 2026-09-16" line; manifest list naming only mdu-05–14; Repository Layout tree missing `skills/`, `docs/`, `evals/`, `examples/`, `config/`, `schemas/`, `tests/`, `.github/`; a TODO item ("seed the empty `skills/`") that MDU-05 completed | AC-1/AC-4 credibility |

## 1. Landing sites

| File | Change |
| --- | --- |
| `README.md` | restructure per §3–§7, §9 |
| `FEATURE_BACKLOG.md` | append MDU-33 (§6), absorbing the README TODO item |
| `examples/README.md` | new — gallery index (§8) |
| `examples/gallery/mdu-08-golden-eval-suite.md` | new (§8) |
| `examples/gallery/mdu-09-prompt-regression-gate.md` | new (§8) |
| `examples/gallery/mdu-15-cross-cli-ledger-conformance.md` | new (§8) |
| `tests/test_mdu_13_readme_gallery.py` | new (§10) |
| `examples/runs/README.md` | one added line pointing at `examples/gallery/` |

Do not edit: `prompts/`, `grok/agents/`, `opencode.json`, `scripts/`, `.github/workflows/ci.yml`, `docs/*` (existing docs are linked, not modified), `build/`, the overlay repo. No infrastructure is touched, so no deploy/devops phase is required by the Definition of Done.

## 2. Decisions (rationale)

- **D1 — One live CI badge, not badge-per-gate.** CI is a single workflow (`ci.yml`, one job, five named gates). Splitting the workflow into build/validate/lint jobs purely to mint more badges duplicates gate 1's labeling for zero verification value. Badge row = live CI badge + four static, honest badges (License, OpenCode, Grok Build, Claude Code). Exact row in §4.
- **D2 — Role-grouped table, not 28 rows.** 28 roster agents share 11 prompt files; a row per agent would repeat each prompt link up to 4×. One row per role with the variants enumerated in a cell presents the model-tier pattern (the repo's selling point) and stays readable. Coverage is enforced mechanically (test 2, §10): every agent name in `opencode.json` must appear as an exact token in a table row that carries a resolvable link.
- **D3 — Tier labels in the table, model IDs in `docs/model-registry.md`.** The table shows `(free)`/`(budget)`/`(mid)`/`(premium)` per variant; exact model IDs live only in the maintained registry doc. Duplicating model IDs in the README is how the old stale-models incident read to visitors — one source of truth instead.
- **D4 — Gallery excerpts are embedded, never linked, for gitignored paths.** `evals/results/` is gitignored, so any "ledger excerpt from the golden evals" must be a trimmed copy committed inside the gallery entry. Same rule for anything under `runs/`. Only `examples/runs/` paths may be linked.
- **D5 — TODO migration:** the Zen-only split item becomes backlog item **MDU-33** (§6). The "seed the empty `skills/`" TODO is stale (MDU-05 shipped 7 skills) — delete it outright; the new Skills table (§5) supersedes it. The whole `### TODO` section disappears from the README.
- **D6 — Roadmap status is derived, not hardcoded.** The "9/14" line is 5 weeks stale and already wrong. Derivation protocol in §7; the written line carries a "last verified YYYY-MM-DD" date so future staleness is self-evident.
- **D7 — Mechanical README regression tests** (`tests/test_mdu_13_readme_gallery.py`) make AC-1/2/3/4 CI-enforced forever, matching the repo's culture (prompt parity tests, golden gates). A README that renders on GitHub is a contract, not a vibe.
- **D8 — Keep the author's voice.** The intro/disclaimer prose stays. This pass modernizes structure and adds evidence, it does not ghost-write the README.

## 3. README target structure

Section map (final `##` order; unlisted subsections keep their current content in place):

| # | Heading | Change |
| --- | --- | --- |
| 1 | title + badges + disclaimer + intro | badge row expanded (§4); prose unchanged |
| 2 | `## What's Inside` | **NEW** — replaces "Core Agents Included" bullets (§5) |
| 3 | `## Prerequisites` | unchanged |
| 4 | `## Using These Agents As-Is` | unchanged |
| 5 | `## How the Agents Work Together` | keeps flow diagrams, iteration loop, example prompt, walkthrough |
| 6 | `## Autonomy & Guardrails` | **promoted** from `###` inside §5; content unchanged (already links `docs/autonomy.md`) |
| 7 | `## Memory & Skills` | **promoted/renamed** from `### Persistent Memory`; memory content unchanged; new `### Skills` subsection (§5.2) |
| 8 | `## Updating These Definitions with an AI Agent` | unchanged |
| 9 | `## Extending with Your Own Overlays` | unchanged |
| 10 | `## Repository Layout` | regenerated tree (§9) |
| 11 | `## Roadmap` | status line refreshed (§7); `### TODO` deleted |
| 12 | `## How This Repo Was Upgraded by Its Own Agents` | refreshed manifest list + October note + gallery links (§7.3) |
| 13 | `## Examples Gallery` | **NEW** — 4 lines linking the three entries + `examples/README.md` |
| 14 | `## Contributing` / `## License` | unchanged |

Heading renames break only same-file anchors (no inbound `README.md#...` links exist anywhere in the workspace — verified). Test 4 (§10) enforces anchor integrity from now on.

## 4. Badge row (paste after the title, above the disclaimer)

```markdown
[![CI](https://github.com/dihhuit/jeffs_agents/actions/workflows/ci.yml/badge.svg)](https://github.com/dihhuit/jeffs_agents/actions/workflows/ci.yml)
[![License: Unlicense](https://img.shields.io/badge/license-Unlicense-blue.svg)](https://unlicense.org)
[![OpenCode](https://img.shields.io/badge/OpenCode-compatible-8A2BE2.svg)](https://opencode.ai)
[![Grok Build](https://img.shields.io/badge/Grok%20Build-compatible-1F2937.svg)](https://x.ai)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-compatible-D97757.svg)](https://claude.com/claude-code)
```

The live badge must stay first (it is the one that can turn red). Static badges are marketing-true claims: every CLI listed is actually deployed by `deploy.sh`.

## 5. What's Inside

### 5.1 Agent table (replaces the "Core Agents Included" bullet blocks)

```markdown
## What's Inside

One prompt per role, cloned into **model-tier variants** so the orchestrator can pick the
cheapest reliable model per subtask. Exact model IDs per variant live in
[docs/model-registry.md](docs/model-registry.md); the tiers below are the routing labels.

| Role | OpenCode agents | Prompt | Grok profiles | Docs & skills |
| --- | --- | --- | --- | --- |
| Orchestrator | `orchestrator` (free) | [orchestrator.md](prompts/orchestrator.md) | [orchestrator.md](grok/agents/orchestrator.md) | [docs/autonomy.md](docs/autonomy.md) · [docs/observability.md](docs/observability.md) |
| Research | `research` (free) · `deepseek-research` (free) · `nemotron-research` (free) · `deep-research` (budget) | [research.md](prompts/research.md) | [research.md](grok/agents/research.md) · [grok-review.md](grok/agents/grok-review.md) | [docs/model-registry.md](docs/model-registry.md) |
| Coding | `just-code` (budget) · `just-code-mid` (mid) · `just-code-pro` (premium) · `just-code-free` (free) | [just-code.md](prompts/just-code.md) | [just-code.md](grok/agents/just-code.md) · [just-code-mid.md](grok/agents/just-code-mid.md) · [just-code-pro.md](grok/agents/just-code-pro.md) | [docs/security.md](docs/security.md) · [skills/mdu-lifecycle/](skills/mdu-lifecycle/) |
| Testing | `test-agent` (budget) · `test-agent-mid` (mid) · `test-agent-pro` (premium) · `test-agent-free` (free) | [test-agent.md](prompts/test-agent.md) | [test-agent.md](grok/agents/test-agent.md) · [test-agent-pro.md](grok/agents/test-agent-pro.md) | [skills/test-patterns/](skills/test-patterns/) · [evals/README.md](evals/README.md) |
| Review | `code-reviewer` (mid) · `code-reviewer-pro` (premium) · `code-reviewer-free` (free) | [code-reviewer.md](prompts/code-reviewer.md) | [code-reviewer.md](grok/agents/code-reviewer.md) · [code-reviewer-pro.md](grok/agents/code-reviewer-pro.md) | [skills/code-review-checklist/](skills/code-review-checklist/) |
| Architecture | `architect` (premium) · `architect-premium` (premium) | [architect.md](prompts/architect.md) | [architect.md](grok/agents/architect.md) · [architect-premium.md](grok/agents/architect-premium.md) | [docs/design/](docs/design/) |
| DevOps | `devops` (mid) · `devops-pro` (premium) · `devops-free` (free) | [devops.md](prompts/devops.md) | [devops.md](grok/agents/devops.md) · [devops-pro.md](grok/agents/devops-pro.md) | [docs/security.md](docs/security.md) |
| QA | `qa` (mid) · `qa-pro` (premium) · `qa-free` (free) | [qa.md](prompts/qa.md) | [qa.md](grok/agents/qa.md) · [qa-pro.md](grok/agents/qa-pro.md) | [docs/mcp.md](docs/mcp.md) · [skills/webapp-verification/](skills/webapp-verification/) |
| UI/UX | `ui-ux-designer` (mid) · `ui-ux-designer-pro` (premium) | [ui-ux-designer.md](prompts/ui-ux-designer.md) | [ui-ux-designer.md](grok/agents/ui-ux-designer.md) · [ui-ux-designer-pro.md](grok/agents/ui-ux-designer-pro.md) | — |
| Introspection | `introspector` (mid) | [introspector.md](prompts/introspector.md) | [introspector.md](grok/agents/introspector.md) | [docs/observability.md](docs/observability.md) · [skills/session-introspect/](skills/session-introspect/) |
| Inception *(user-invoked, outside the MDU loop)* | `inception` (budget) | [inception.md](prompts/inception.md) | [inception.md](grok/agents/inception.md) | [docs/mdu-20-inception.md](docs/mdu-20-inception.md) |
```

Coverage facts the implementer must preserve (all mechanically asserted, §10): 28 OpenCode agent names across 11 rows; all 20 `grok/agents/*.md` profiles linked (orchestrator 1, research 2 incl. `grok-review`, coding 3, testing 2, review 2, architecture 2, devops 2, qa 2, ui/ux 2, introspection 1, inception 1 = 20).

The two prose blocks that follow today's bullet lists (Grok models note, Claude subagents note) stay as **compact paragraphs**: Grok — all profiles currently on `grok-4.7` (see [docs/mdu-16-grok-4.7.md](docs/mdu-16-grok-4.7.md)), invoke with `grok --agent <name>`; every profile is linked in the table above. Claude — subagents are generated at build time from `opencode.json` + `prompts/` (one per roster agent, `model` omitted so your configured model applies), invoke with `claude --agent <name>`. The per-profile bullet re-listing is dropped — the table now carries it.

### 5.2 Skills table (new `### Skills` subsection under `## Memory & Skills`)

Build from `skills/*/SKILL.md` frontmatter at implementation time; descriptions below are the expected shape:

| Skill | Used by | What it does |
| --- | --- | --- |
| [mdu-lifecycle](skills/mdu-lifecycle/) | just-code, qa, orchestrator | closed-loop MDU checklist + model-tier selection table |
| [code-review-checklist](skills/code-review-checklist/) | code-reviewer | review rubric + file:line severity output format |
| [test-patterns](skills/test-patterns/) | test-agent | priority ordering, property/fuzz guidance, assertion rules |
| [webapp-verification](skills/webapp-verification/) | qa | Playwright recipe; BLOCKED reporting when unavailable |
| [secret-scrub](skills/secret-scrub/) | commit gate (orchestrator, just-code) | pre-commit secret scan + redaction rules |
| [git-autonomy](skills/git-autonomy/) | autonomous runs | branch/commit/PR hygiene, push safety |
| [session-introspect](skills/session-introspect/) | introspector | session-log signal extraction → improvement suggestions |

One intro sentence: skills load on demand ("if the `xxx` skill is available, load it") and are deployed to all three CLIs by `deploy.sh`.

## 6. TODO → backlog item MDU-33 (paste verbatim into FEATURE_BACKLOG.md)

Placement: directly after the `### MDU-32` item at the file tail (that tail is where post-September items accumulate; do not restructure the P0/P1/P2 sections). Style matches sibling items.

```markdown
### MDU-33 · Zen-only (free-tier) agent variant set

- **Why:** Every default agent in the MDU loop requires an OpenCode Go subscription (`opencode-go/*`); without it the agents deploy but fail at runtime. The README has to warn these users away — a variant set removes the warning instead. (Absorbed from the README TODO, 2026-10-23.)
- **Description:** Produce a parallel agent set using only free Zen models (`opencode/*`): either a second registry file (`opencode.zen.json`) selected by a build flag (e.g. `./build.sh --zen`) or generated variant entries. Cover every MDU-loop role (orchestrator, just-code, test-agent, code-reviewer, architect, devops, qa at minimum) using current free-tier models from `config/model-registry.txt`. Update `docs/model-registry.md` and the README prerequisites accordingly; CI must validate whichever registry file(s) ship.
- **Acceptance criteria:**
  1. A no-subscription user can build and deploy a working default loop (every role resolves to a free model present in the registry).
  2. `./build.sh` (or the flagged variant) validates the Zen set with the existing registry check; CI runs it.
  3. `docs/model-registry.md` documents both sets and their tiers.
  4. README prerequisites section updated (the Go-subscription warning links the Zen path).
- **Suggested agents:** architect (variant-set design), just-code (build + config), test-agent (registry/variant tests), qa (fresh-clone deploy validation).
- **Dependencies:** none hard (uses MDU-01 registry machinery); coordinate with MDU-32 findings to avoid duplicate model churn.
```

In the README: delete the entire `### TODO` section (both items — the skills one is stale, MDU-05 shipped).

## 7. Roadmap, status, and the meta-narrative

### 7.1 Roadmap section (final shape)

Keep the existing two doc links (AC-4). Replace the stale progress line with a derived one:

```markdown
**Status:** derived from `git log` + backlog `Status:` markers — last verified 2026-10-23.
Original backlog (MDU-01…15): complete except MDU-10 (superseded by the MDU-28 resume
protocol). Post-September extensions MDU-16…31 are landed (see `git log --oneline`).
Open now: MDU-32 (glm-5.2 cost audit) and MDU-33 (Zen-only variant set).
```

### 7.2 Status derivation protocol (run at implementation; do not trust this doc's snapshot)

1. `git log --oneline --grep="mdu-"` → landed MDU ids (commit subjects carry `feat(mdu-XX)`).
2. `Status: Done` markers in `FEATURE_BACKLOG.md`.
3. Committed manifests under `examples/runs/`.
Union = done; on contradiction trust git log + Status markers and investigate before writing the line. Then stamp the line with the actual verification date.

### 7.3 "How This Repo Was Upgraded by Its Own Agents" refresh

- Replace the hard manifest enumeration ("mdu-05/06/07/08/12/14 are real…") with one sentence pointing at `examples/runs/README.md` as the authoritative index (it already separates real from illustrative).
- Add a 2–4 sentence "October continuation" paragraph: the September session was followed by further closed-loop work (schema-inlined orchestrator, prompt regression gate, secret gate, repo-ownership rules…), each with its own design doc under `docs/design/` and manifest under `examples/runs/`.
- Link the three gallery entries (§8) from this section — the narrative is the gallery's front door.

## 8. `examples/` gallery

### 8.1 Index — `examples/README.md` (new)

~15 lines: what lives here — [gallery/](gallery/) worked examples (the 3 entries, one line each), [runs/](runs/) raw run manifests + validator usage, [mcp/](mcp/) MCP config example, [upgrade-story.md](upgrade-story.md) the full dogfooding narrative. Add the matching one-line pointer in `examples/runs/README.md`.

### 8.2 Worked-example template (every entry, fixed six parts)

1. `# <title>` + one-line outcome banner: `Completed <date> · harness <harness> · QA <grade> · <n>/<n> tests green · autonomy L<a>`.
2. **The task** — 3–5 lines, quoted/condensed from the backlog item.
3. **What happened** — a compact phase table (phase · agent · tier · outcome) transcribed from the manifest + one short narrative paragraph (the human story: what went wrong, what the loop did).
4. **Run manifest** — trimmed excerpt in a fenced ```json block (keep: `mdu_id`, `title`, `status`, `harness`, `fix_iterations`, `autonomy_level`, `verification`, `summary`; drop long `phases[].notes` and full `artifacts`) **plus** a link to the full [runs/<id>/manifest.json](runs/<id>/manifest.json).
5. **Ledger / eval evidence** — the numbers, per entry below. Excerpts from gitignored paths are **embedded trimmed copies** (D4), never links.
6. **Artifacts** — bullet links to design doc, tests, scripts, eval task (all committed paths).

### 8.3 The three entries

| Entry | Why it earns a slot | Ledger/eval evidence (part 5) |
| --- | --- | --- |
| `gallery/mdu-08-golden-eval-suite.md` | bootstrapped the eval harness that CI gate 4 still runs; the "golden evals" the backlog names | embedded trimmed copy of a real `evals/results/repo-health-*.json` (status, verification, the `PASS build.sh` / `PASS pytest` lines from `output_tail`) + the `run_ledger.py summarize examples/runs/` session totals |
| `gallery/mdu-09-prompt-regression-gate.md` | the best *failure* story: REJECT → 3 fix cycles → APPROVE; shows review actually biting | verification block (380 tests, `ci_green` via CI run 39701688115) + golden-case count (7 ordered traces) + baseline refusal behavior |
| `gallery/mdu-15-cross-cli-ledger-conformance.md` | the flagship: one schema, three CLIs, headless; closes the 2026-09-16 dialect findings from `upgrade-story.md` | three harness legs (opencode/grok/claude each PASS six checks, driver exit 0) + base suite 314/314 + the three old-dialect strings confirmed absent |

Narrative angles: 08 = "the team learned to grade itself"; 09 = "the loop rejected its own work three times and that is the point"; 15 = "same prompt, three CLIs, one contract". Link each entry to its design doc (`docs/design/mdu-08…` does not exist — 08 predates design docs; use the backlog item as the task source and say so).

## 9. Repository Layout refresh (§10 of the section map)

Regenerate the tree from the real filesystem at implementation time (`ls`, not memory). Must appear with counts: `.github/workflows/ci.yml`, `scripts/lib/` (name `validate.py`, `run_ledger.py`, `run_evals.py`, `prompt_regression.py`, `secret_scan.py`, `model_registry.py`, `gen_claude_agents.py`), `schemas/opencode.schema.json`, `config/model-registry.txt`, `opencode.json` (28 agents), `prompts/` (11), `grok/agents/` (20 profiles), `skills/` (7), `docs/` + `docs/design/`, `evals/` (4 tasks, `golden/`, `promptfoo.yaml`), `examples/` (gallery, runs, mcp, upgrade story), `tests/`, `build/` (gitignored, generated). Counts are pinned by test 8 (§10) so the tree cannot silently rot again.

## 10. Test plan — `tests/test_mdu_13_readme_gallery.py`

Style of `test_mdu_12_06_contracts.py` / `test_mdu_28_resume_detect.py`: path constants, pure stdlib (`json`, `re`, `pathlib`), no network.

Shared helpers:

- `slugify(text)` — GitHub heading rules: lowercase; drop chars outside `[a-z0-9 _-]`; spaces → `-`; underscores kept. (E.g. `Autonomy & Guardrails` → `autonomy--guardrails`.)
- `md_links(text)` → list of `(label, target)` for `[x](y)` incl. badge lines (outer target only).
- `resolve(target)` → strip `#fragment`; empty → `README.md`; repo-relative existence check (file **or** dir).

Tests:

1. `test_badge_row_present_and_wellformed` — first ~15 README lines contain ≥1 `[![...](...)](...)` badge; every file in `.github/workflows/` is referenced by some badge (`actions/workflows/<name>/badge.svg`); all badge URLs are `https`.
2. `test_whats_inside_table_covers_every_roster_agent` — load `opencode.json` `agents` keys (28); locate the `## What's Inside` table; for each agent name find a row whose cells contain the name as an **exact token** (tokenize on chars outside `[a-z0-9-]`, so `just-code` ≠ `just-code-mid`); assert that row contains ≥1 markdown link that resolves.
3. `test_every_readme_relative_link_resolves` — every non-`http(s)`/`mailto` markdown link target in README resolves to an existing path (badges' https targets are skipped here).
4. `test_readme_anchors_resolve` — every `(#...)` or `path#anchor` link: `slugify` the target file's `^#+` headings; assert the anchor is in that set. Covers all same-file TOC/section links.
5. `test_todo_section_removed` — `### TODO` heading absent from README; the strings `Split agent definitions into Go-only and Zen-only variants` and `Seed the empty` absent.
6. `test_backlog_has_mdu33_zen_item` — `FEATURE_BACKLOG.md` contains `### MDU-33` and `Zen-only`; the entry has separate blocks covering intent, bounds, conditions, team, and references.
7. `test_roadmap_links_both_analysis_docs` — the `## Roadmap` section links `GAP_ANALYSIS.md` and `FEATURE_BACKLOG.md`; the section contains a `last verified` line with a `\d{4}-\d{2}-\d{2}` date.
8. `test_layout_tree_counts_match_reality` — parse the `## Repository Layout` fenced tree; assert the annotated counts equal live counts: `json.load(opencode.json)` agents == 28, `len(glob grok/agents/*.md)` == 20, `len(glob skills/*/SKILL.md)` == 7, `len(glob prompts/*.md)` == 11. (If a count legitimately changes later, this test forces the README to move with it — intended coupling.)
9. `test_gallery_index_and_entries` — `examples/README.md` exists and links ≥2 files under `examples/gallery/` that exist; each entry contains (a) ≥1 link to `examples/runs/<id>/manifest.json` that exists, (b) a fenced ```json block, (c) a ledger/eval-evidence part containing ≥1 line with digits.
10. `test_gallery_manifest_ids_match_runs` — for each gallery entry: extract `examples/runs/<id>/manifest.json` from its first such link; `json.load` it; assert `mdu_id == <id>` and `status == "completed"`.
11. `test_every_grok_profile_linked_from_readme` — every `grok/agents/*.md` stem appears in some README markdown link target; every `prompts/*.md` stem likewise.

## 11. Acceptance criteria → mechanical mapping

| Backlog AC | Enforced by |
| --- | --- |
| 1. README renders correctly (links, badges, no broken anchors) | tests 1, 3, 4, 11 + QA fresh-clone render check (§12) |
| 2. Every roster agent has a clickable prompt link | test 2 |
| 3. `examples/` contains ≥2 complete worked examples with real manifests/ledgers | tests 9, 10 (design delivers 3) |
| 4. Roadmap links both analysis docs | test 7 (+ both files exist) |

## 12. QA protocol

1. Fresh clone to a scratch dir under `/tmp/opencode/` (no build needed — README/docs are plain files).
2. Run the new module: `timeout 120 python3 -m pytest tests/test_mdu_13_readme_gallery.py -q`, then the full suite `timeout 120 python3 -m pytest tests/ -q` and `timeout 300 ./build.sh` (unchanged code must stay green).
3. Render check on the public README (post-push): badges resolve, table renders, no GitHub-broken anchor icons. Playwright MCP per `docs/mcp.md`; if no browser is available, grade from the fresh clone with the pytest module as the mechanical substitute and say so in the QA report.
4. Grade each AC from §11; report PASS/FAIL with file:line evidence.

## 13. Execution notes

- Suggested agents: just-code (all content edits — the table is mechanical, `ui-ux-designer` is optional for a structural pass over the section flow), test-agent (§10 module), qa (§12). No devops phase (no infra touched).
- One commit on branch `mdu-13-readme-modernization`, message `feat(mdu-13): complete README modernization — what's-inside table, badge row, examples gallery, mechanical link tests`, then push and fast-forward `main` per the git-autonomy skill. Run the manifest through `run_ledger.py validate` and commit it under `examples/runs/mdu-13/` with the code, per house convention.
- Secret gate: `python3 scripts/lib/secret_scan.py --staged` before commit (gallery entries quote CI run ids and dates only — no secrets by construction).

## 14. Out of scope / follow-ups

- No CI workflow changes (D1) — a future MDU may split gates into jobs if badge-per-gate is ever wanted.
- No restructuring of `FEATURE_BACKLOG.md`'s P0/P1/P2 sections (MDU-33 joins MDU-32 at the tail as-is).
- No upgrade-story rewrite beyond the §7.3 refresh; it is a historical record.
- No overlay-repo changes; no new docs under `docs/` (existing docs are linked).
- Zen variant set itself = MDU-33, not this MDU.
