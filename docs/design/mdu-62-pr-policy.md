# MDU-62 — Two-tier PR/push policy in git-autonomy

> Design phase, orchestrator-driven. Paths repo-relative; overlay sibling =
> `$WORKSPACE_OVERLAY` (`../opencode_agents/`). Date 2026-11-13. User ruling
> 2026-11-13 is fixed policy (backlog MDU-62 row): owned repos → no PR, direct
> push; any other remote → per-action human approval BEFORE any PR/branch push;
> one approval never covers the next.

## 1. Decision

**Carrier set = ONE source file: `skills/git-autonomy/SKILL.md`.** Orchestrator
mirrors NOT edited (§4). The clause is a skill-body edit → prompt-regression
gate does not apply to it; secret gate and validator still do.

Carve-out: MDU-62 additionally applies the separately user-approved MDU-59
Dispatch-truth clause to the three orchestrator mirrors (base ×2 + overlay
grokestrator, plus the gate-required `pi_golden` fixture refresh), so the
prompt-regression gate DID run (snapshot/diff/gate all exit 0, baseline intact).

**Rendering: generic two-tier keyed to repository ownership, not the literal
`dihhuit` name.** Tier 1 = "repositories the user owns" — the exact concept
mdu-31 pinned into both mirrors; in the user's deployment that concept IS
`dihhuit/*` (mdu-31 + overlay snippet), so tier 1 is the ruled dihhuit tier
with no new mapping to drift. The base is public/Unlicense/provider-neutral —
mdu-31's `PERSONAL_NAMES` discipline keeps personal identifiers out of deployed
public bodies, and a dihhuit-keyed public skill is useless to anyone else.
Tier 1 keys to ownership, not privacy, because the backlog codification keys
tier (a) to `github.com/dihhuit/` (privacy is incidental). If the user later
wants the dihhuit literal in the daily deployment: overlay full-file skill
override (build step 5), NOT a base edit — out of scope here.

## 2. D1 — byte-exact edits (the clause the user approves, single approval)

**2a. Replace `skills/git-autonomy/SKILL.md:39` (old line, verbatim):**

```text
- Push the feature branch and open the PR; do not push directly to `main` unless the project explicitly allows it.
```

**with these two lines (verbatim):**

```text
- **Two-tier push policy:** On repositories the user owns, no PR is required — push the branch or push directly to `main` (the sanctioned default-green path); the existing secret and prompt gates still apply, and if `main` is branch-protected the protected-branch approval rule still applies.
- On any other remote (OSS, third-party, or unclear ownership), obtain explicit per-action human approval BEFORE opening a PR or pushing any branch; one approval never covers the next action.
```

**2b. Recommended companion guard — `SKILL.md:28`, `## PR description` intro.**
Old (verbatim): `Include:` → new (verbatim):

```text
Only when a PR is actually required under Push safety (any remote you do not own, or an explicit user request). Include:
```

Rationale: a section presupposing a PR re-frames PRs as the norm for the 99%
no-PR case; the guard makes the skill self-consistent. Severable if vetoed.

**2c. `SKILL.md:3` description: LEAVE AS-IS.** "Load when committing or opening
a PR" is a conditional load trigger, not a directive; locked by a state pin (§5 case 7).

## 3. D2 — census disposition (every live hit, this session's greps)

| Hit | Disposition |
| --- | --- |
| `skills/git-autonomy/SKILL.md:39` | **Edited** — the primary PR-by-default carrier; §2a. |
| `skills/git-autonomy/SKILL.md:26-33` (`## PR description`) | **Edited** — one-line conditional guard (§2b); section content unchanged. |
| `skills/git-autonomy/SKILL.md:3` (description) | **Left as-is** — load trigger, no PR mandate; state-pinned. |
| `build/skills/git-autonomy/SKILL.md:39` (base, gitignored) | **Regenerated** by `./build.sh`; never hand-edited; not committed. |
| `../opencode_agents/build/skills/git-autonomy/SKILL.md:39` (tracked) | **Regenerated** by overlay `./build.sh`; commit of the dirty build tree is a user call (§6), never `git add -A`. |
| overlay `skills/courier` resource `mcp.md:30` | **Left as-is** — "save a note in project docs or PR description" is an either/or save location, not PR creation or push gating; overlay-only resource, outside the automated census scope (SKILL.md surfaces only). |
| `open-agent-definitions/.github/workflows/ci.yml:38` (QA-added row) | **Left as-is** — CI comment "git fetch on pull requests" describes the workflow mechanism, not a PR-creating or push-gating rule for agents. |
| overlay `skills/courier` legacy `inbox-v7-legacy.md:28` (QA-added row) | **Left as-is** — migration pointer "in the PR or task notes" is the same either-or save-location class as `mcp.md:30`; no gating. |
| `FEATURE_BACKLOG.md:387-396` (row at :390) | **Edited at commit time** — standard lifecycle: status Open→Done + MDU-62 commit ref added in the MDU commit; a backlog row, not a live carrier. |
| `prompts/orchestrator.md:114-118` | **Left as-is** — no PR mandate; "commit and push (assuming there's a configured remote)" is direct-push-compatible; mdu-31 block already gates non-owned repos. State-pinned (§5 case 8). |
| `grok/agents/orchestrator.md:121-123` | **Left as-is** — same as above (mirror). State-pinned. |
| `../opencode_agents/grok/agents/grokestrator.md:114` | **Left as-is** — same; overlay source untouched → no overlay source commit. |

## 4. D3 — carrier-set decision: orchestrator mirrors NOT edited

1. Census verified no PR mandate and no conflict in any mirror — nothing to fix.
2. Tier 2's approval gate already exists at dispatch level (mdu-31: "per-action
   human approval", "stop and ask"); the skill restates it at the point of
   action — complementary, no drift.
3. Editing mirrors costs the prompt-regression gate, three-mirror byte-identity
   choreography (base ×2 + overlay grokestrator → second repo commit) for zero
   behavioral gain. Defensive state pins (§5 case 8) lock the no-PR-mandate
   state instead.

## 5. D4 — pin-test plan: `tests/test_mdu_62_pr_policy.py`

Constants: `CLAUSE_LINES` (the two §2a lines, raw, verbatim), `OLD_DIRECTIVE` (lowercased old :39 fragment `"push the feature branch and open the pr"`), `GUARD_LINE` (§2b verbatim). File root resolves through `MDU62_TEST_ROOT` (mdu-60 pattern) for the mutation matrix.

1. `test_clause_constant_matches_design_doc` — both `CLAUSE_LINES` appear verbatim in this doc's §2a fence (doc-consistency, mdu-49/60 convention).
2. `test_two_tier_clause_present_once_in_push_safety` — both lines exactly once, located between `## Push safety` and `## Checklist before commit`; `OLD_DIRECTIVE` absent.
3. `test_census_no_pr_by_default_directive_in_any_skill` — every `skills/*/SKILL.md` (under the test root): `OLD_DIRECTIVE` absent; marker `"two-tier push policy"` present in `git-autonomy/SKILL.md`. Covers census requirement (1).
4. `test_scenario_owned_repo_no_pr_direct_push` — tier-1 line contains, verbatim: `repositories the user owns`, `no PR is required`, "push directly to `main`", `default-green path`, `secret and prompt gates`, `branch-protected`. Docstring: dihhuit/* are the owned remotes (mdu-31 + overlay snippet) → this pins the dihhuit→no-PR scenario. Census req (3a).
5. `test_scenario_any_other_remote_approval_first` — tier-2 line contains: `any other remote`, `explicit per-action human approval`, `BEFORE opening a PR or pushing any branch`, `one approval never covers the next action`. Census requirement (3b).
6. `test_pr_description_section_is_conditional` — `GUARD_LINE` exactly once between `## PR description` and `## Push safety`.
7. `test_skill_description_frontmatter_unchanged` — :3 state pin: exact current description string still present (locks §2c).
8. `test_mirrors_still_carry_no_pr_mandate` — both base orchestrator mirrors: `"open a pull request"` and `"open a pr"` (lowercased) absent from the ownership span (§4). Overlay mirror covered by the skipif overlay census below.
9. `test_overlay_skill_census` (skipif `../opencode_agents/` absent) — every overlay `skills/**/SKILL.md` free of `OLD_DIRECTIVE`.

**Mutation matrix — RUNS in /tmp, never the working tree.** Per run:
`mkdir -p /tmp/opencode/mdu62-mut<N> && cp -r skills docs/design/mdu-62-pr-policy.md /tmp/opencode/mdu62-mut<N>/` → apply one mutation → `MDU62_TEST_ROOT=/tmp/opencode/mdu62-mut<N> timeout 120 python3 -m pytest tests/test_mdu_62_pr_policy.py -q`:

- **M1 (required):** revert the two clause lines to the old :39 sentence → cases 2, 3, 4, 5 red.
- **M2:** delete the tier-2 line → cases 2, 5 red. **M3:** delete `no PR is required` from tier-1 (keep both lines) → case 4 red. **M4:** revert the guard to bare `Include:` → case 6 red.

## 6. D5 — test/build/QA acceptance

```bash
cd $WORKSPACE                                   # open-agent-definitions
timeout 300 python3 -m pytest tests/ -q         # expect 979 passed / 0 skipped; the new-file targeted run (tests/test_mdu_62_pr_policy.py) adds 11
./build.sh                                      # validator green; regenerates build/skills/git-autonomy/SKILL.md
grep -c "Two-tier push policy" build/skills/git-autonomy/SKILL.md   # QA probe: 1 occurrence (tier-2 line has no marker; generated copy carries both clause lines)
timeout 60 python3 scripts/lib/run_ledger.py validate runs/mdu-62/manifest.json   # gates QA
# mutation matrix per §5 in /tmp/opencode/ (never the working tree); prompt-regression gate DID run — MDU-59 Dispatch-truth carve-out touched prompts/ + grok/agents/ (snapshot/diff/gate exit 0, baseline intact)
# secret gate: secret-scrub pass over the diff (mdu-11 suite already in the run above)
git add skills/git-autonomy/SKILL.md docs/design/mdu-62-pr-policy.md tests/test_mdu_62_pr_policy.py FEATURE_BACKLOG.md prompts/orchestrator.md grok/agents/orchestrator.md tests/fixtures/pi_golden/prompts/orchestrator.md agent-improvements.md
git commit -m "feat(mdu-62): two-tier push policy in git-autonomy (no PR on owned repos)"
git push origin main                            # dihhuit/jeffs_agents = tier 1: direct push, no PR

cd $WORKSPACE_OVERLAY && ./build.sh && ./deploy.sh --force   # regenerate tracked build/ + refresh installed daily copy
# overlay HAS a source change (MDU-59 carve-out): separate commit of grok/agents/grokestrator.md + regenerated build/ per the cross-repo order — never git add -A
```

## 6b. Commit plan correction (QA finding 1, pre-commit)

§6/§7 originally read "overlay: no source change" — wrong once the user-approved
Dispatch-truth carve-out expanded scope mid-MDU. Actual overlay surface:
`grok/agents/grokestrator.md` (+2 clause lines, source) + regenerated tracked
`build/` tree. Two commits, two pushes, per the cross-repo change order:
base first, then the overlay source+build commit. `test_mdu_59_dispatch_truth.py`
pins that overlay source file, so it must be committed, not left dirty.

QA (read-only, mdu-60 clause-C discipline): pytest run above, the two greps,
`run_ledger.py validate`, `git diff --stat`; no content-denied verbs — mutants
live in /tmp only.

## 7. Loop notes

- Wording approval = single design-time approval of §2a (mdu-60 carve-out
  pattern); §2b rides the same approval, severable without touching §2a.
- One base repo commit + one overlay commit (source grokestrator + regenerated
  build/), per the cross-repo change order; `runs/`
  gitignored (manifest local). No existing test pins the old wording
  (grep-verified) — pins are net-new, no suite edits.
