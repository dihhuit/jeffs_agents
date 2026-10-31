# MDU-45 · Register base `grok-review` + grok-registry census + docs staleness sweep

- **Date:** 2026-10-31
- **Status:** Design complete — ready for implement → review → test → deploy → validate → commit
- **Repos touched:** this base repo (source + docs + tests + validator) and the sibling overlay (tracked `build/` rebuild only, no source edits)
- **Design agent:** architect

## 0. User decisions (2026-10-31, binding)

1. **Register, do not retire.** Base `grok/agents/grok-review.md` (read-only Grok code-review rung, MDU-25 bulk tier, frontmatter model `grok-build-0.1`) is the only base Grok profile with no same-name agent in `opencode.json`. The user ruled: register it in base `opencode.json` with a `prompts/` body per family convention. Retirement is out of scope.
2. **Bundle the docs-staleness sweep** (README progress line, stale Grok-model claim, `docs/model-registry.md` refresh caveat, backlog Status backfill) into this same MDU.

## 1. Context — verified facts (2026-10-31, this session)

- Base `opencode.json`: 20 agents, all `opencode-go/*`. Base `grok/agents/`: 20 profiles = the same 20 names minus `deep-research`/`test-agent-mid`, plus `grok-review` and `research`. So the "every grok profile has a registry counterpart" census fails today on exactly two names: `grok-review` (fixed here by registering) and `research` (MDU-40 deleted the `research` agent; `prompts/research.md` + `grok/agents/research.md` remain → needs a dated allowlist entry).
- Overlay root `grok/agents/` has 18 live personal profiles; `overlays/grok/agents/` has 3 full-file profiles (`grok-mdu-code`, `mdu-code`, `thought-leadership-coach`). Merged overlay build tree: 41 grok profile files, 42 `opencode.json` agents (20 base + 22 overlay-root, no name overlap). All frontmatter `name` values equal file stems in all three grok trees (verified).
- Overlay build validates the **merged** tree with the **base** validator (`scripts/lib/validate.py` via the thin overlay wrapper). A census on the build tree therefore sees the merged config in the overlay and the isolated config in the base — both pass once `grok-review` is registered and `research` is allowlisted.
- MDU-42 hard rule: any grok-named agent must resolve to `xai/*` in every config (validator `grok_xai_errors` + deploy gates + probe xai section). The new entry must be `xai/*`.
- Base `config/model-registry.txt` already contains `xai/grok-4.7` and `xai/grok-build-0.1` (rows verified present) → the base model-refs check passes with the new xai model; **the snapshot file is untouched**.
- Base paid-census prefixes are `("opencode-go/", "xai/")` in both validator and tests → an `xai/*` model passes the paid-only census.
- `schemas/opencode.schema.json` is shape-generic (`agents` is `additionalProperties` with a `mode` enum incl. `subagent`) → the new entry conforms by mirroring an existing sibling.
- Golden prompt-regression cases (7) target `prompts/orchestrator.md`, `grok/agents/orchestrator.md`, `prompts/just-code.md` only → the new/edited grok-review files affect no golden case; the gate is expected to exit 0 with an unchanged baseline (verify, do not assume).
- Count pins that must change: base `tests/test_mdu_40_paid_default.py` `assert len(agents) == 20`. Pins that already fit: `tests/test_grok_model_allowlist.py` `BULK_GROK_BUILD_PROFILES` already includes `grok-review`; overlay `AGENT_COUNT = 22` reads the overlay's own `opencode.json` (unchanged); overlay MDU-44 dead-copy pins forbid overlay-root `grok-review.md` copies (so the overlay gets **no** source edits); no test pins the merged 42/43 count or the parity-pair count (verified by grep).
- Machine-local probe reports (gitignored): overlay report dated 2026-10-30 shows both `xai/grok-4.7` and `xai/grok-build-0.1` exact-OK; the base report has an empty `xai_results` (base config has no xai model yet — MDU-45 changes that, see D11).

### Design-time live probe (apply-now 20261030-1 rule)

Both candidate models were probed live on **2026-10-31** with the one-shot rule
(`timeout 90 opencode run -m <id> "Reply with exactly: OK"`, success = stdout exactly `OK`):

| Candidate | Result |
| --- | --- |
| `xai/grok-build-0.1` | exactly `OK` |
| `xai/grok-4.7` | exactly `OK` |

Both live; no swap needed. Corroborated by the 2026-10-30 overlay probe report (both `ok`, strict exact-match rule).

## 2. D-decisions

### D1 — Model: `xai/grok-build-0.1`

Chosen over `xai/grok-4.7` because all three signals agree:
1. The Grok mirror's own frontmatter says `grok-build-0.1` (MDU-25 bulk rung).
2. `tests/test_grok_model_allowlist.py` pins `grok-review` in `BULK_GROK_BUILD_PROFILES` (bulk rung = `grok-build-0.1`); putting the OpenCode twin on `grok-4.7` would make the two rungs disagree.
3. The overlay's `grok-code-reviewer` (the same role, personal variant) runs `xai/grok-build-0.1`.

Review is a bulk-tier role: high volume, checklist-shaped, not reasoning-critical. `xai/grok-4.7` stays the flagship rung for reasoning roles.

### D2 — Registry entry (base `opencode.json`)

Insert immediately **after the `code-reviewer-pro` block** (keeps the review family grouped). Entry:

```json
"grok-review": {
  "mode": "subagent",
  "description": "Read-only code review rung on the xAI Grok build model (MDU-25 bulk tier). Reviews diffs for quality, security, and maintainability; never edits code",
  "model": "xai/grok-build-0.1",
  "color": "#60a5fa",
  "system": "{file:./prompts/grok-review.md}",
  "request": {
    "body": {
      "temperature": 0.1
    }
  },
  "permissions": []
}
```

`permissions` is **byte-identical to the existing `code-reviewer` agent's permissions array** — copy it verbatim (edit deny; shell deny-all plus the read-only allow sandwich `git diff*/log*/show*/status*`, `grep *`, `rg *`, `ls*`, `head*`, `tail*`, `wc*`, `sort*`, `timeout *` and the deny sandwich; `read`/`glob`/`grep`/`list` allow; `webfetch`/`websearch`/`todowrite` deny; `subagent deep-research` allow; `subagent *` deny).

Rationale:
- **Sibling-of-`code-reviewer` shape** makes the diff trivially reviewable and lets a test pin permission equality (D10) instead of re-enumerating 60 lines.
- The overlay `grok-code-reviewer` entry proved the same read-only pattern on the same model; the base entry simply uses the base formatting (one object per line) and the base's fuller deny set.
- The body (D3) does not mention webfetch/websearch or delegation, so those entries are inert-but-inherited shape — harmless, and removing them would break the equality pin for no benefit.
- `temperature: 0.1` matches both base reviewers (review = low temperature). Color `#60a5fa` (blue-400) is distinct from `#3b82f6`/`#2563eb`.
- Description avoids any `-free` token (paid-census scans raw text for free-model tokens).

### D3 — `prompts/grok-review.md` (new canonical OpenCode body)

Exact file content:

```markdown
You are a code review specialist. Your job is to thoroughly review code changes, proposed implementations, or existing code for:

- Correctness and bugs
- Security issues and vulnerabilities
- Performance problems
- Edge cases and error handling
- Adherence to best practices and style
- Test coverage and quality
- Maintainability and clarity

Hard constraints:
- You have READ-ONLY access. Never use write, edit, or destructive bash commands.
- Never edit or write files. Never run arbitrary bash commands beyond git diff, git log, git show, git status, grep, and rg.
- When a code change doesn't have an obvious "best path" — i.e. there are different tradeoffs — force the coding agent to justify why it chose the tradeoffs it chose, then back off and move on.
- Always provide specific, actionable feedback with file:line references where possible. "This is bad" is not useful — explain why and suggest the fix.
- Structure your reviews clearly: summary, strengths, issues (numbered by severity), suggestions.
- Only sign off when the code meets high standards for the task.
- Do not approve changes that have unresolved issues.

Safety constraints:
- **Step Limit:** Maximum of 50 loop steps per invocation. At step 45, begin wrapping up — finalize current work and summarize progress. At step 50, you MUST exit and return your results to the orchestrator, even if the task is incomplete. The orchestrator will decompose remaining work if needed.
```

Design notes (deliberate omissions, all recorded so review does not re-litigate):
- **No model mention in prose** — model provenance lives in config/frontmatter, not bodies.
- **No webfetch/websearch in the tools sentence** — the D2 permission block denies them; a body must not promise tools its config denies. The Grok mirror keeps its own sentence listing webfetch/websearch (Grok harness allows them) — a harness-context wording difference, tolerated by the parity design (D5 pins only the reviewer contract, not tool enumerations).
- **No `deep-research` delegation sentence, no skill-load line, no token-efficiency line** — this MDU adds no new policy text; the body is the minimal reviewer contract already present in the Grok mirror, so the pair stays exactly behaviorally aligned.
- The summary-structure rule ("summary, strengths, issues, suggestions") is **carried over as-is** from the existing Grok body — no new summary rule is introduced (per user scope note).

### D4 — `grok/agents/grok-review.md` alignment edit (behavior-only)

Exactly one change: the section heading `Rules:` becomes `Hard constraints:`. Every rule line, the bullets, and the `Safety constraints:` block stay byte-identical. Frontmatter untouched (`name: grok-review`, `model: grok-build-0.1`).

Why: D5 pins the pair in `GROK_MIRRORS`, and the parity checker requires the "Hard constraints" structural marker in both files of a pair. The rename aligns the mirror with every other grok mirror's section shape with zero behavior change. No summary-structure rule is added, removed, or reworded.

### D5 — Parity wiring (`scripts/lib/validate.py`)

- `GROK_MIRRORS` gains: `"grok-review": ["grok-review.md"]`
- `ROLE_KEYWORDS` gains: `"grok-review": [("read-only",), ("security",)]` — the same two-clause contract as `code-reviewer`.

Rationale: family convention is that every canonical prompt ↔ grok mirror pair is parity-pinned; the pair now exists, so pin it. Consequences (all verified safe): parity-pair count print goes 19 → 20 (nothing pins the number); `test_inception_agent.py` pins only its own `GROK_MIRRORS` key; both bodies contain "read-only" and "security" (case-insensitive) and, after D4, the "Hard constraints" marker; both carry safety/step-limit markers.

### D6 — Validator census clause (`scripts/lib/validate.py`)

**Rule (one direction only):** every `grok/agents/*.md` profile must have a same-name agent in the build tree's `opencode.json`. A Grok profile with no registry entry is a profile no OpenCode orchestrator can spawn — fail closed. The reverse direction is intentionally **not** checked: opencode-only entries (`deep-research`, `test-agent-mid`) are legal.

**Name source:** frontmatter `name` (fallback: file stem). Every current profile in all three grok trees has `name == stem` (verified).

**Allowlist** — explicit, dated, commented, kept next to the rule:

```python
#: grok/agents profiles deliberately NOT registered in opencode.json, each
#: with a dated reason. This is a standing decision list, not a permanent
#: exemption: remove an entry when its profile is registered or retired.
GROK_CENSUS_ALLOWLIST: dict[str, str] = {
    # 2026-10-31 (MDU-45): MDU-40 removed the bare `research` agent from
    # opencode.json (deep-research replaced it); prompts/research.md and
    # grok/agents/research.md remain until an explicit retire-or-register
    # decision. Registering the agent or deleting both files retires this
    # entry.
    "research": "MDU-40 removed the opencode.json agent; files retained pending retire-or-register",
}
```

**Function** (full body — it is short; slot as a sibling of `validate_grok_agents`):

```python
def validate_grok_registry_census(build_dir: Path) -> list[str]:
    """Every grok/agents profile needs a same-name opencode.json agent (MDU-45).

    One direction only: a Grok profile with no registry entry is a profile no
    OpenCode orchestrator can spawn, so it fails closed. opencode.json-only
    entries (deep-research, test-agent-mid) are legal and not checked. The
    check runs on the build tree in hand — the overlay build passes its
    MERGED config, so overlay-only profiles (grok-architect, grokestrator,
    grok-plan, ...) resolve against the merged registry and pass; the base
    tree is validated in isolation. Names come from frontmatter ``name``
    (falling back to the file stem).
    """
    errors: list[str] = []
    agents_dir = build_dir / "grok" / "agents"
    config_path = build_dir / "opencode.json"
    if not agents_dir.is_dir() or not config_path.is_file():
        return []  # already reported by validate_grok_agents / validate_opencode
    try:
        agents = load_json(config_path).get("agents") or {}
    except json.JSONDecodeError:
        return []  # already reported by validate_opencode
    for profile in sorted(agents_dir.glob("*.md")):
        meta = parse_frontmatter(profile.read_text(encoding="utf-8"))
        name = meta.get("name") or profile.stem
        if name in GROK_CENSUS_ALLOWLIST or name in agents:
            continue
        errors.append(
            f"grok registry census: profile '{name}' (grok/agents/{profile.name}) "
            "has no same-name agent in opencode.json — register it or add a "
            "GROK_CENSUS_ALLOWLIST entry with a dated reason "
            f"(current allowlist: {sorted(GROK_CENSUS_ALLOWLIST)})"
        )
    return errors
```

**Wiring:** in `main()`, immediately after `errors.extend(validate_grok_agents(build_dir))` add `errors.extend(validate_grok_registry_census(build_dir))`. Add one success print after the existing grok/agents ok line (recomputing counts by re-reading frontmatter is fine — 20–41 small files):

```python
    print(f"  [ok]    grok census: {census_registered}/{census_total} profiles registered "
          f"({census_allowlisted} allowlisted)")
```

**Merge-context behavior (documented in the docstring, repeated here for the brief):** the census validates the build tree it is handed. Base `./build.sh` → base `build/` (21 agents, 20 profiles, `research` allowlisted). Overlay `./build.sh` → merged `build/` (43 agents, 41 profiles, overlay-only names all registered, `research` allowlisted). The overlay's `scripts/lib/validate.py` thin re-exec needs **no change** — the census flows to overlay builds automatically. Overlay dead-copy hygiene (MDU-44) is orthogonal: dead root copies never reach the build tree, so they are invisible to the census by design; MDU-44's pins continue to guard the source tree.

**Census accounting after this MDU:**

| Tree | grok profiles | registry agents | unmatched | allowlisted |
| --- | --- | --- | --- | --- |
| base build | 20 | 21 | `research` | 1 |
| overlay merged build | 41 | 43 | `research` | 1 |

### D7 — README.md

1. **What's Inside — OpenCode agents table:** insert after the `code-reviewer-pro` row (required by the mdu-13 roster test once the agent exists):

   `|  | [`grok-review`](prompts/grok-review.md) | [prompts/grok-review.md](prompts/grok-review.md) | Read-only review rung on the xAI Grok build model (xai/grok-build-0.1). |`

2. **Grok Build profiles section:** the claim "All profiles currently use **grok-4.7**" is stale (MDU-25 moved 8 bulk profiles to `grok-build-0.1`). Replace that sentence with: "Flagship roles run **grok-4.7**; bulk roles (just-code, test-agent, code-reviewer, qa, devops, research, ui-ux-designer, grok-review) run **grok-build-0.1** (MDU-25 split). grok-4.6 and grok-4.5 remain allowlisted." Keep the existing "Invoke with `grok --agent <name>`." sentence.
3. **Repository Layout section:** `opencode.json` line "(20 agents, all paid)" → "(21 agents, all paid)"; `prompts/` line "— 11 files" → "— 12 files" and add `│   ├── grok-review.md` to the tree listing (after `code-reviewer.md`); `grok/agents/` "(20 profiles)" is unchanged (`grok-review.md` already listed there).
4. **Roadmap progress line** — re-derived per the MDU-13 D6 protocol (audit `FEATURE_BACKLOG.md` Status fields; cited list must match the audit; keep the "last verified" date, set to 2026-10-31). Exact replacement text (written at commit time, when MDU-45 is complete — the same self-reporting convention prior MDUs used):

   > (last verified 2026-10-31) **Progress:** the original 15-item backlog is fully resolved — 14 complete (MDU-01–09, 11–15), MDU-10 superseded by MDU-28; later backlog entries MDU-32, 34, 35, 39–42 complete (MDU-33 superseded by MDU-40); post-backlog MDUs 16–31, 36–38, 43–45 complete per `git log`. Derived from FEATURE_BACKLOG.md Status fields (MDU-13 D6) — see [examples/upgrade-story.md](examples/upgrade-story.md) and [examples/gallery/](examples/gallery/) for worked examples.

   The old line was internally inconsistent (claimed 14/15 but listed only 13 names, omitting the Done MDU-04). **Derivation audit** (this is the table QA grades against):

   | Entry | Status pre-MDU-45 | MDU-45 action |
   | --- | --- | --- |
   | MDU-01, 02, 03, 05, 06, 07, 08 | no Status line (shipped Sept 2026; artifacts in-repo: CI workflows, schema, skills, MCP docs, ledger, evals) | backfill Done (D8) |
   | MDU-04, 09, 11, 15 | Done — 2026-10-21 | none |
   | MDU-10 | Superseded by MDU-28 — 2026-10-24 | none |
   | MDU-12, 14 | Done — 2026-09-15 (mdu-43 pinned) | none |
   | MDU-13 | Done — 2026-10-23 | none |
   | MDU-32 | Done — 2026-10-24 | none |
   | MDU-33 | Superseded by MDU-40 — 2026-10-30 (mdu-43 pinned) | none |
   | MDU-34 | no Status line (shipped; `resume_block.py` + docs + tests in-repo) | backfill Done (D8) |
   | MDU-35 | Done — 2026-10-26 (mdu-43 pinned) | none |
   | MDU-39, 40, 41 | Done — 2026-10-30 | none |
   | MDU-42 | Done — 2026-10-29 | none |
   | MDU-16–31, 36–38, 43, 44 | not backlog-tracked | cited as complete per `git log` |
   | MDU-45 | — | new entry (D8), Status filled at commit |

   Derived counts: original 15 = 14 Done + 1 superseded (MDU-10). The mdu-13 tests pin structure only (roster rows, link resolution, layout count, roadmap links + date); they stay green — the derivation itself is this documented protocol.

### D8 — FEATURE_BACKLOG.md

1. **Status backfill** — add exactly one Status line per entry (mdu-43 format, placed directly under the `### MDU-XX` heading like MDU-04's) for the eight done-but-unmarked entries: MDU-01, 02, 03, 05, 06, 07, 08, 34:

   `- **Status:** Done — shipped 2026-09/10 (Status line backfilled 2026-10-31 during the MDU-45 docs sweep; verified via in-repo tests and artifacts)`

   (Exact shipped month per entry is not worth pinning; the backfill date and the verification basis are the audit trail. The mdu-43 pins on MDU-12/14/33/35 are untouched.)
2. **Append the MDU-45 entry** at the end of the file (after MDU-41), same structure as its siblings: Why (registration gap + user decision + bundled docs sweep), Description (D1–D9 summary), Acceptance criteria (section 3 below), Suggested agents (section 4), Dependencies (MDU-42 grok-xai rule, MDU-25 rung, MDU-40 paid census, MDU-44 overlay dead-copy pins), and `**Status:** Done — 2026-10-31 (…)` filled at commit time with the deploy counts and QA grade.
3. **Audit confirmation:** after the backfill, no backlog entry remains without a resolution (Done/Superseded); the last open-looking entries (MDU-39/40/41) are all Done.

### D9 — docs/model-registry.md refresh caveat (doc-only)

Insert immediately after the existing refresh code block near the top:

> **Safe-refresh caveat (2026-10-31, MDU-45):** `opencode models` can still list upstream-dead models as `active` — the deprecated `opencode-go/mimo-v2.5`(-pro) rows are the current example (killed per the MDU-40 live probe; see the dated `#` kill-comments in the snapshot). A blind `opencode models > config/model-registry.txt` would **resurrect** those rows and silently re-allow dead models. Safe procedure: (1) diff the new snapshot against the old before committing; (2) re-add a dated `# <model>` kill-comment for every previously commented row that the catalog still lists; (3) remember a listing is not proof of life — only the exact-OK probe (below) is. The build's model-refs check fails closed on any referenced model missing from the snapshot.

`config/model-registry.txt` itself is **untouched** (both xai rows already present; the probes changed no catalog facts).

**Drift-warning test — decided doc-only.** Rationale: the invariant that matters (dead rows stay commented and out of `load_registry`) is already pinned by `tests/test_mdu_43_hygiene.py`; any comment-vs-catalog drift check needs the live `opencode` CLI, which is excluded from CI by design ("Never in CI", probe docs); a live-only test would either skip everywhere that matters or duplicate the probe gate's proof-of-life contract. Not cheap, not worth it.

### D10 — Test plan

**New file: `tests/test_mdu_45_grok_review_registry.py`** (~20 test functions, same `import validate` conftest pattern as its siblings):

- *Entry pins:* `grok-review` registered with mode `subagent`, model exactly `xai/grok-build-0.1`, `system` referencing `prompts/grok-review.md`, `temperature` 0.1; permissions array **equal** to `code-reviewer`'s (parsed-JSON equality); read-only invariants (edit deny, `shell *` deny, no allow-edit, `subagent *` deny); agent count 21; prompt file exists and the ref resolves.
- *Census unit (synthetic builds, `tmp_path`):* orphan profile → exactly one error containing the profile name, the file name, "census", and "GROK_CENSUS_ALLOWLIST"; registered profile → `[]`; allowlisted `research` without a registry entry → `[]`; frontmatter-name preferred over stem; opencode-only entries (registry without matching profiles) → `[]`; census wired into `validate.main` → orphan build exits 1.
- *Census production pin (read-only):* `validate_grok_registry_census(REPO_ROOT) == []` against the real tree (mirrors the `test_grok_model_allowlist` production style).
- *Allowlist pin:* `GROK_CENSUS_ALLOWLIST` keys == `{"research"}` (value contains a 2026-10-31 date) — creep must be deliberate.
- *Parity pins:* `GROK_MIRRORS["grok-review"] == ["grok-review.md"]`; `ROLE_KEYWORDS["grok-review"] == [("read-only",), ("security",)]`; both bodies contain read-only/security/hard-constraints/safety markers.
- *Mirror-edit pin:* `grok/agents/grok-review.md` has "Hard constraints:", no "Rules:", frontmatter model still `grok-build-0.1`, and still carries the "summary, strengths" structure sentence.
- *Docs pins:* README roster row for `grok-review` (mdu-13 pattern); stale "All profiles currently use" gone, "grok-build-0.1" + bulk wording present; layout section shows 21 agents / 12 prompt files; progress line has "last verified 2026-10-31" and no "14/15"; `FEATURE_BACKLOG.md` has the MDU-45 section and, parametrized, exactly one backfilled "Done" Status line for each of MDU-01/02/03/05/06/07/08/34; `docs/model-registry.md` contains the safe-refresh caveat.

**Existing tests to update (base):** `tests/test_mdu_40_paid_default.py` — `assert len(agents) == 20` → `== 21` (single line; `PAID_PREFIXES` already includes `xai/`).

**No updates needed (verified):** `test_grok_model_allowlist.py` (grok-review already a bulk profile), `test_mdu_13_*` (generic assertions absorb the changes), `test_mdu_42_grok_xai.py`, `test_mdu_43_hygiene.py` (different MDUs pinned), all overlay tests (overlay `opencode.json` unchanged at 22; MDU-44 pins are overlay-root-only and must stay green against the rebuilt merged tree; no merged-count pin exists).

### D11 — Deploy runbook (ordered; every long command under `timeout`)

1. **Base build:** `timeout 300 ./build.sh` — validates the 21-agent config: schema, prompt refs, paid census (xai counts), grok-xai rule, model refs vs snapshot, new parity pair, new census (only `research` allowlisted).
2. **Base tests:** `timeout 120 python3 -m pytest tests/ -q` — full suite green including the new file and the 21-count pin.
3. **Prompt-regression gate:** `timeout 60 python3 scripts/lib/prompt_regression.py gate` — expected exit 0, baseline unchanged (no golden case targets the touched files; verified at design time, re-verified here). The snapshot/diff protocol in `evals/README.md` applies **only** if a golden-targeted file (`prompts/orchestrator.md`, `grok/agents/orchestrator.md`, `prompts/just-code.md`) changes — this MDU must not touch them.
4. **Base probe refresh (new requirement):** the base config gains its first `xai/*` model, so the base machine-local report needs an `xai_results` entry. Run `timeout 300 python3 scripts/lib/probe_models.py --refresh --gate --config build/opencode.json` from the base root. The base deploy's advisory probe gate goes green.
5. **Overlay build:** from the overlay root, `timeout 300 ./build.sh` — re-runs the base build, then merges. Expected merged tree: 43 `opencode.json` agents, 41 grok profiles, 43 Claude agents; census green on the merged config.
6. **Overlay tests:** `timeout 120 python3 -m pytest tests/ -q`.
7. **Overlay probe refresh (mandatory, hash-driven):** the gate pins `config_sha256` over the sorted `agent=model` pairs — adding `grok-review` changes the hash **even though the model set is unchanged** (4 `opencode-go/*` + 2 `xai/*`), so the existing report goes red with "config changed since last probe" until refreshed. From the overlay root run `timeout 300 python3 ../open-agent-definitions/scripts/lib/probe_models.py --refresh --gate --config build/opencode.json --report config/model-probe-report.json` (the probe script lives in the base sibling; this is the documented overlay path).
8. **Overlay deploy:** `timeout 120 ./deploy.sh` (dry run — expect a clean plan over 43 agents, hard probe gate + grok-xai gate green) then `timeout 300 ./deploy.sh --force` (both hard gates must pass before any copy; `--skip-probe` is not to be used here).
9. **Post-deploy verification:** installed OpenCode agent count **43 (from 42)**; `grok-review` present with model `xai/grok-build-0.1`; **21/21 grok-named registry entries on `xai/***`; Claude copy present; record actual observed counts.
10. **Evidence + ledger:** write the evidence file (commands, gate outputs, observed counts, probe results) to the sanctioned external scratch path `mdu-45-deploy-evidence.md` under `/tmp/opencode`; create the run manifest under `runs/mdu-45/` and validate it with `run_ledger.py validate` (gitignored; not committed).

**Expected counts:**

| Artifact | Before | After |
| --- | --- | --- |
| base `opencode.json` agents | 20 | 21 |
| base `prompts/` files | 11 | 12 |
| base grok profiles | 20 | 20 (file already existed) |
| base Claude agents (build) | 20 | 21 |
| parity pairs | 19 | 20 |
| merged `opencode.json` agents | 42 | 43 |
| merged grok-named registry entries (all `xai/*`) | 20 | 21 |
| merged grok profile files | 41 | 41 |
| merged Claude agents | 42 | 43 |

### D12 — Commit plan (one commit per repo)

**Base commit** (after QA PASS; explicit list, conventional subject):

```
opencode.json
prompts/grok-review.md
grok/agents/grok-review.md
scripts/lib/validate.py
README.md
FEATURE_BACKLOG.md
docs/model-registry.md
docs/design/mdu-45-grok-review-registry.md
tests/test_mdu_45_grok_review_registry.py
tests/test_mdu_40_paid_default.py
```

Subject: `feat(mdu-45): register base grok-review, add grok-registry census, refresh docs`. Base `build/` and `runs/` are gitignored — nothing else should appear in `git status`; if it does, stop and investigate before staging.

**Overlay commit** (after the base push and a fresh overlay build; **never `git add -A`** — `build/` is tracked): stage exactly the paths the rebuild dirtied, expected to be:

```
build/opencode.json
build/prompts/grok-review.md
build/claude/agents/grok-review.md
build/grok/agents/grok-review.md
```

Verify with `git status --porcelain` first and stage exactly what changed under `build/`. Subject: `feat(mdu-45): rebuild merged build tree with base grok-review registration`. **No overlay source edits** — MDU-44 pins forbid root `grok-review.md` copies in both `prompts/` and `grok/agents/`, and the census needs none (the base registration flows through the merge).

## 3. Acceptance criteria

1. Base `opencode.json` registers `grok-review` per D2 (mode subagent, model `xai/grok-build-0.1`, `system` → `prompts/grok-review.md`, temperature 0.1, permissions byte-identical to `code-reviewer`'s) and `./build.sh` is green end-to-end.
2. Design-time live probes (2026-10-31) recorded: both `xai/grok-build-0.1` and `xai/grok-4.7` answered exactly `OK`; chosen model is `xai/grok-build-0.1` per D1; deploy-phase `--refresh --gate` is green in **both** repos.
3. `prompts/grok-review.md` exists with the D3 body; the prompt ref resolves; the `grok-review` parity pair is pinned (D5) and passes.
4. `grok/agents/grok-review.md` carries only the D4 heading alignment edit; frontmatter model unchanged; no summary rule added or removed.
5. `validate_grok_registry_census` (D6) ships in `scripts/lib/validate.py`, wired into `main()` after `validate_grok_agents`, with the dated `GROK_CENSUS_ALLOWLIST` (`research` only); base build and overlay merged build both pass it.
6. **Negative-fail:** a synthetic build containing a grok profile with no registry counterpart fails `validate.main` with the named census error; the `research` allowlist pass is pinned by test; the allowlist key set is pinned so creep is deliberate.
7. README (D7): `grok-review` roster row; layout counts 21 agents / 12 prompt files; stale "all profiles use grok-4.7" claim replaced with the two-rung wording; progress line re-derived per the D7 audit with "last verified 2026-10-31"; all mdu-13 README tests green.
8. `FEATURE_BACKLOG.md` (D8): MDU-45 entry appended with both user decisions recorded; Status lines backfilled for MDU-01/02/03/05/06/07/08/34; no entry remains unresolved; mdu-43 status pins stay green.
9. `docs/model-registry.md` carries the dated safe-refresh caveat (D9); `config/model-registry.txt` untouched; the doc-only drift-test decision is recorded with rationale.
10. Tests (D10): `tests/test_mdu_45_grok_review_registry.py` green (~20 tests); `test_mdu_40_paid_default.py` count pin updated to 21; full suites green in both repos.
11. Prompt-regression gate exits 0 with the golden baseline unchanged (verified, not assumed; no golden-targeted file is touched).
12. Deploy (D11): both builds green; overlay `deploy.sh --force` installs **43** OpenCode agents (from 42) with **21/21** grok-named entries on `xai/*`; evidence file written to the sanctioned scratch path; run manifest created and validated.
13. Commits (D12): base commit with the explicit file list, then a separate overlay commit staging exactly the dirtied `build/` paths; each repo pushed once (user-owned remotes only).

## 4. Phase plan — suggested agents

| Phase | Agent | Notes |
| --- | --- | --- |
| design | `architect` | this document (done) |
| implement | `just-code-mid` | multi-file config/validator/docs edits from this spec; mechanical but census semantics are subtle enough to avoid the budget rung |
| review | `code-reviewer` | read-only diff review; no deep security surface (config + validator + docs) |
| test | `test-agent-mid` | ~20-test file + one existing pin update |
| deploy | `devops` | D11 runbook: builds, both probe refreshes, dry-run, `--force`, evidence, manifest |
| validate | `qa` | grade against section 3 from the repo + evidence file |
| commit | orchestrator | D12 plan, both repos, in order |

## 5. Risks & edge cases

- **Census false positives in future overlay profiles** — intended (fail-closed). Remediation is always explicit: register the agent or add a dated allowlist entry; the error message says both.
- **Overlay root `grok-review.md` / `prompts/grok-review.md` temptation** — forbidden (dead copies shadowing base; MDU-44 pins). The overlay needs no source change.
- **Progress line is hand-derived** — the mdu-13 tests pin structure, not the derivation; this doc's audit table is the grading basis, and the D8 backfill makes future derivations mechanical.
- **Probe cost** — two design-time xAI probes (user-approved, done); deploy-phase refreshes probe 5 targets (base) + 6 (overlay), all tiny exact-OK calls.
- **jsonschema absent locally** — the schema check warns and skips (existing behavior); CI covers it.
- **README link/anchor drift** — the new row links a file that will exist; mdu-13 link-resolution tests enforce it.

## 6. Open forks — none

Every fork encountered was resolved and recorded:

| Fork | Resolution |
| --- | --- |
| `xai/grok-build-0.1` vs `xai/grok-4.7` | `grok-build-0.1` (D1; both probed exact-OK 2026-10-31) |
| register vs retire `grok-review` | register (user decision, §0) |
| census direction | grok profile → registry only; no reverse clause (D6) |
| `research` gap | dated allowlist entry, not deletion (retire-or-register is a future decision; deleting files is out of scope) |
| census match key | frontmatter `name` with stem fallback (D6) |
| drift-warning test vs doc-only | doc-only (D9 rationale) |
| canonical body extras (delegation, skills, token-efficiency lines) | omitted — no new policy text; pair stays exactly aligned (D3) |
| permission block shape | byte-identical to base `code-reviewer` (D2) |
| mirror edit scope | heading rename only (D4) |
