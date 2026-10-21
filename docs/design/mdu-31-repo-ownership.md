# MDU-31 — Repository ownership rule for write actions

After an upstream issue was filed and then withdrawn, the user set a standing hard rule:

> - commit / push / open PR / file issues ONLY on repos the user owns (`dihhuit/jeffs_agents`, `dihhuit/opencode_agents`)
> - any third-party or OSS repo needs explicit, per-action human approval; if ownership is unclear, STOP and ask
> - never file upstream issues/PRs as a default step of an MDU; the upstream report path must be an explicit user instruction

The rule lands in the agent configs themselves, not in a README. The public base gets the repo-agnostic half; the private overlay gets the half that names the two owned remotes.

## 1. Landing sites

| Repo | File | What lands |
| --- | --- | --- |
| base | `prompts/orchestrator.md` | generic inline block (§3, byte-identical to its mirror) |
| base | `grok/agents/orchestrator.md` | same block, byte-identical (§3) |
| base | `scripts/lib/validate.py` | 3 new `ROLE_KEYWORDS["orchestrator"]` clauses (§7) |
| base | `tests/test_mdu_31_repo_ownership.py` | new (§8.1) |
| overlay | `overlays/repo-ownership.txt` | new personal global snippet (§4) |
| overlay | `overlays/manifest.json` | register the snippet in `global_snippets` (§4) |
| overlay | `grok/agents/grokestrator.md` | condensed generic inline bullet (§5) |
| overlay | `overlays/prompts/mdu-code.md`, `overlays/grok/agents/mdu-code.md`, `overlays/grok/agents/grok-mdu-code.md` | inline personal block appended at EOF (§6) |
| overlay | `tests/test_mdu_31_overlay_repo_ownership.py` | new (§8.2) |

Do not edit: `build/` in either repo (generated), `build/claude/` ever, overlay root `prompts/*.md` / `grok/agents/*.md` same-name copies (dead — the base orchestrator files live only in the base repo), `deploy.sh`, either `build.sh`, `AGENTS.md`, `README.md`. Both repos are already on branch `mdu-31-repo-ownership-rule`.

## 2. Generic vs personal split

**Base (public) carries the rule, overlay-agnostic:** "repositories the user owns", "third-party or open-source repository", "STOP and ask". Any user of the public repo can deploy this rule as-is; nobody's personal remotes leak into it. This is the same split the repo already uses for every other overlay boundary.

**Overlay (private) carries the instantiation:** the two owned remotes by name, stated as the default-green path, everything else third-party. The overlay snippet must restate the full three-clause rule (not just the names) because it is appended to ~50 built agents whose sources carry no generic rule — on those agents the snippet is the only copy.

### 2.1 Base text (paste verbatim into both orchestrator mirrors)

```markdown
- **Repository Ownership:**
  - Commit, push, open PRs, and file issues ONLY on repositories the user owns.
  - Any third-party or open-source repository requires explicit, per-action human approval BEFORE the write — one approval never covers the next action.
  - If repository ownership is unclear, STOP and ask the user. Do not guess it from the remote name or the task.
  - Never file upstream issues or open upstream PRs as a default step of an MDU. Reporting anything upstream requires an explicit user instruction naming the repo and the action.
```

### 2.2 Overlay snippet — `overlays/repo-ownership.txt` (new file, full content, single trailing newline)

```markdown
Repository ownership (hard rule, all agents):
- Commit, push, open PRs, and file issues ONLY on repositories the user owns: `dihhuit/jeffs_agents` and `dihhuit/opencode_agents`. These two remotes are the default-green path for every write action.
- Every other remote — third-party, open-source, or unclear — requires explicit, per-action human approval BEFORE the write; one approval never covers the next action.
- If repository ownership is unclear, STOP and ask the user. Do not guess it from the remote name or the task.
- Never file upstream issues or PRs as a default step of an MDU. Reporting anything upstream requires an explicit user instruction naming the repo and the action.
```

Plain header + bullets, matching `overlays/safety-guardrails.txt` style. `append_file` prepends exactly one newline (`printf '\n'`), which yields a blank separator line only when the target file already ends with a newline. Hence the invariant: **every snippet file must end with a newline**, otherwise the next appended snippet's first line becomes a lazy continuation of the previous snippet's last line instead of a standalone Markdown block. `overlays/safety-guardrails.txt` was missing that trailing newline; it has been fixed in this MDU, and the overlay test suite now pins the invariant for every `overlays/*.txt` snippet.

### 2.3 Grokestrator source bullet (condensed generic, §5)

```markdown
- **Repository Ownership:** Commit, push, open PRs, and file issues ONLY on repositories the user owns. Any third-party or open-source repository requires explicit, per-action human approval BEFORE the write. If repository ownership is unclear, STOP and ask the user. Never file upstream issues or PRs as a default step of an MDU — the upstream report path must be an explicit user instruction naming the repo and the action.
```

### 2.4 mdu-code override block (personal, §6 — same text in all three files, appended at EOF after a blank line)

```markdown
Repository ownership (hard rule):
- Commit, push, open PRs, and file issues ONLY on repositories the user owns: `dihhuit/jeffs_agents` and `dihhuit/opencode_agents`.
- Every other remote — third-party, open-source, or unclear — requires explicit, per-action human approval BEFORE the write. If ownership is unclear, STOP and ask the user.
- Never file upstream issues or PRs as a default step of an MDU — the upstream report path must be an explicit user instruction naming the repo and the action.
```

All four texts carry the same required phrases (§8.3), so one phrase list tests every landing site.

## 3. Placement in the base orchestrators

Insert in **both** mirrors at the same anchor: in the `**Safety Guardrails:**` section, immediately after the last Human Approval Gates bullet, with one blank line before the block, and before the blank line + `Your responsibilities:` heading.

Preceding text (identical in both files today):

```markdown
  - Require human approval before exceeding 3 fix-retries on the same issue.

Your responsibilities:
```

Result:

```markdown
  - Require human approval before exceeding 3 fix-retries on the same issue.

- **Repository Ownership:**
  - Commit, push, open PRs, and file issues ONLY on repositories the user owns.
  - Any third-party or open-source repository requires explicit, per-action human approval BEFORE the write — one approval never covers the next action.
  - If repository ownership is unclear, STOP and ask the user. Do not guess it from the remote name or the task.
  - Never file upstream issues or open upstream PRs as a default step of an MDU. Reporting anything upstream requires an explicit user instruction naming the repo and the action.

Your responsibilities:
```

**Sibling labelled block, not inside the `Human Approval Gates` bullet list.** Reasons:

1. `tests/test_mdu_12_06_contracts.py` pins the gates as exactly four "Require human approval" lines, identical across mirrors. Folding the rule into that list either breaks that regression contract or forces a rewrite of an existing test for zero gain.
2. The established structure of the section is bold-labelled bullets with sub-content (`- **Max Retry Count:**` … `- **Human Approval Gates:**`). The new block matches that pattern.
3. The rule is a scope prohibition plus a default-behavior change, not a one-line approval gate; it needs sub-bullets the one-line gate style cannot hold.
4. Adjacent placement keeps all write-approval semantics contiguous.

In `grok/agents/orchestrator.md` the anchor is byte-identical (gates block, then `Your responsibilities:`). No other text moves.

## 4. Overlay snippet registration

`overlays/manifest.json` — the full new `global_snippets` array (append only; do not reorder the existing entries):

```json
  "global_snippets": [
    "token-frugal.txt",
    "safety-guardrails.txt",
    "repo-ownership.txt"
  ],
```

Consequences (verified from `scripts/lib/overlays.sh` + `build.sh`): the snippet is appended to every copied base prompt and grok agent, and — via `sync_root_additions` → `apply_overlays_to_file` — to the built `grokestrator.md` (root addition, name absent from the base). Full-file overrides (`install_overlay_full_files`) never receive it; that is §6's problem.

The built orchestrators therefore end up with the generic block inline plus the personal snippet appended. That is intended, not duplication: the two texts are different wordings at different scopes (principle vs instantiation), and the snippet must stand alone on the ~50 agents whose sources have no inline copy.

## 5. Grokestrator (the third orchestrator)

The grokestrator is a condensed, hand-maintained mirror of the base orchestrator; it does not inherit the base Grok profile, and it is never a validator parity pair (no `prompts/grokestrator.md`, per the MDU-28 note).

**Decision (a) — what the source gets inline:** the condensed generic bullet (§2.3), inserted as the last item of its `**Safety Guardrails:**` section — immediately after the `- **CODER HANDOFF:**` bullet (its last line is `… Never edit production code yourself.`), one blank line, then the block, then the blank line + `Your responsibilities:` heading. The source gets **no personal names**.

**Decision (b) — avoiding verbatim repetition:** the personal rule reaches the built grokestrator exactly once, through the global snippet — the same channel as every other built agent. If the source also carried the personal text, the built file would carry it twice verbatim. Instead:

- The source alone carries the rule in generic form — honest for a file people read as the third orchestrator's source of truth, and unmistakable on its own.
- The build adds the personal instantiation once.
- Tests pin the channel: source phrase-present + personal-name-count 0; built grokestrator phrase-present + each owned-remote name exactly once (§8.2). A future inline personal copy in the source trips the count assertions mechanically.

The user named the grokestrator as a landing site; this design lands the rule in the source (generic, condensed to its style) and in the built artifact (generic + personal), with zero duplication anywhere.

Not in scope, do not fix here: the grokestrator's condensed body does not carry the four Human Approval Gates at all (pre-existing omission). This MDU adds the ownership rule only.

## 6. Full-file overrides (coverage gap)

Full-file overrides never receive global snippets. Audited per file:

| Override file | Shell permissions (OpenCode config) | Role body | Decision |
| --- | --- | --- | --- |
| `overlays/prompts/mdu-code.md` | `mdu-code`: `shell * allow`, no wall | monorepo/Android/PyTorch coding; no git verbs today | **ADD inline (§2.4)** |
| `overlays/grok/agents/mdu-code.md` | (Grok profiles have no permission layer) | same, Grok profile | **ADD inline (§2.4)** |
| `overlays/grok/agents/grok-mdu-code.md` | (no permission layer) | same, Grok profile | **ADD inline (§2.4)** |
| `overlays/prompts/qa.md` | base `qa` permissions carry the MDU-30 wall (`* git commit*`, `* git push*`, `* git clone*` … all denied) | validation/Playwright; reports grades, never writes to remotes | **out** |
| `overlays/prompts/thought-leadership-coach.md` | `shell * deny` | coaching/writing; zero git or repo operations in the body | **out** |
| `overlays/grok/agents/thought-leadership-coach.md` | (no permission layer) | same | **out** |

Rationale:

- **mdu-code family — add.** These are the only overlay agents that combine `shell * allow` (or a Grok profile, which has no permission enforcement at all) with an override body that never receives the snippet. Without an inline copy they carry no ownership rule whatsoever, and they are the likeliest non-orchestrator upstream writers. The overrides' own convention (per `overlays.sh`: full files "typically already include global/agent rules" — `qa.md` embeds its safety constraints by hand) is to embed needed global rules inline. Appending at EOF mirrors exactly what the build would have appended.
- **`qa.md` — out.** It is an operative full QA prompt override (Playwright/BLOCKED semantics; it embeds its safety constraints by hand). Its role never performs repo writes, and on OpenCode — the only harness where this prompt is the deployed body — the MDU-30 permission wall already denies every git mutation verb. The Grok `grok-qa` counterpart is not an override (built from base + snippet) and does carry the personal rule where no permission layer exists. The asymmetry is deliberate: prompt text where permissions cannot enforce, permission enforcement where it already exists.
- **thought-leadership-coach — out.** A repo-write rule on a writing coach with `shell * deny` and no git operations is noise.

Blanket coverage for all overrides would require changing the overlay build to append global snippets to full-file overrides too — a build-semantics change affecting all six overrides. Out of scope; note as a possible follow-up only if the user asks.

## 7. Enforcement surface

**Permission-level (`opencode.json`) — not viable for the orchestrator, out of scope.** The base orchestrator is `mode: primary` with `shell * allow` because step 8 of the loop requires `git commit`/`git push` on owned repos. The harness permission layer cannot distinguish repos by ownership; walling the orchestrator would break the owned-repo commit/push the whole loop depends on. The MDU-30 wall already covers every agent that can be safely walled (qa, code-reviewer, introspector deny `* git push*`, `* git commit*`, …). A follow-up MDU could explore ordered rules on the orchestrator (`git push*dihhuit/*` allow above `* git push*` deny) — rejected for this MDU: it duplicates ownership policy in a second source of truth, only covers `git push` (not PRs/issues, which are web/API actions), and false-denying a legitimate owned push violates the loop's hard "you MUST commit and push" constraint.

**Validator-level — in scope, cheap, follows the MDU-24 precedent.** Add three clauses to `ROLE_KEYWORDS["orchestrator"]` in `scripts/lib/validate.py`:

```python
    "orchestrator": [
        ("mdu",),
        ("delegat",),
        ("140000",),
        ("continue this session across mdus",),
        ("cache miss",),
        ("compact and continue",),
        ("repositories the user owns",),
        ("per-action human approval",),
        ("upstream",),
    ],
```

Verified preconditions: neither "upstream" nor "ownership" appears in either orchestrator file today, so the clauses bind only to the inserted block; the parity check lowercases, and both mirrors carry identical text, so parity stays green. Effect: deleting or rewording the rule out of either mirror fails `./build.sh` in **both** repos (the overlay build re-runs this validator on its `build/`), which is the cheapest real enforcement hook available. `test_validate_parity.py::test_real_orchestrator_pair_consistent` and `test_validate_integration.py` automatically extend to the new clauses — no edits to those files.

## 8. Test plan

### 8.1 Base — `tests/test_mdu_31_repo_ownership.py` (new)

Style of `test_mdu_12_06_contracts.py` / `test_mdu_28_resume_detect.py`: path constants, lowercase phrase matching, `import validate` (conftest already puts `scripts/lib` on `sys.path`).

Shared contract constants (imported by the overlay test — one contract, no second copy to drift):

```python
MDU_31_PHRASES = [  # lowercase; files are lowercased before matching
    "repository ownership",
    "only on repositories the user owns",
    "per-action human approval",
    "stop and ask",
    "default step of an mdu",
    "explicit user instruction",
    "upstream",
]
PERSONAL_NAMES = ["dihhuit", "jeffs_agents", "opencode_agents"]
```

Tests:

1. `test_ownership_block_present_in_both_mirrors` — for `prompts/orchestrator.md` and `grok/agents/orchestrator.md`: every `MDU_31_PHRASES` entry is in the lowercased text.
2. `test_ownership_block_byte_identical_across_mirrors` — extract the span from `- **Repository Ownership:**` up to (not including) the `Your responsibilities:` line in each file; assert the two spans are byte-identical (MDU-28 `_gate_span` pattern).
3. `test_ownership_block_sits_after_gates_before_responsibilities` — in both files, char offsets satisfy: last gates bullet (`  - Require human approval before exceeding 3 fix-retries on the same issue.`) < `- **Repository Ownership:**` < `Your responsibilities:`.
4. `test_gates_list_untouched_by_mdu_31` — the MDU-12 contract still holds locally: exactly four "Require human approval" lines per file, identical across mirrors, gate[0] "pushing to protected branches", gate[3] "exceeding 3 fix-retries"; and the ownership span contains no "Require human approval" line (proves the block is not folded into the gates list). Precedent: MDU-28's `test_mdu_23_locked_phrases_survive_mdu_28`.
5. `test_public_agent_bodies_leak_no_personal_names` — for every `prompts/*.md` and `grok/agents/*.md` in the base: no `PERSONAL_NAMES` entry in the lowercased text. Scope is the deployed bodies only — `README.md` and `docs/` legitimately name the base's own remote.
6. `test_role_keywords_orchestrator_locks_ownership_clauses` — `validate.ROLE_KEYWORDS["orchestrator"]` contains the three new clauses and still contains the six pre-existing ones.
7. `test_overlay_grokestrator_source_carries_generic_rule_only` — `@pytest.mark.skipif(not OVERLAY_GROKESTRATOR.exists(), reason="overlay sibling opencode_agents/ not present")` (MDU-28 pattern; a standalone public clone stays green); path `REPO_ROOT.parent / "opencode_agents" / "grok" / "agents" / "grokestrator.md"`; every phrase present, every `PERSONAL_NAMES` count == 0.

### 8.2 Overlay — `tests/test_mdu_31_overlay_repo_ownership.py` (new)

Style of `tests/test_mdu_30_overlay_shell_allowlist.py`: `GENERIC_DIR` env or sibling names (`open-agent-definitions`, `base_agents`, `open_agent_definitions`); module-level `pytest.skip(allow_module_level=True)` when the base is absent; insert the base `tests/` dir on `sys.path`; `import test_mdu_31_repo_ownership as base`; reuse `base.MDU_31_PHRASES` / `base.PERSONAL_NAMES`. Built-output assertions require `./build.sh` to have run (same as test_mdu_29/30); they fail, not skip, on a stale `build/`.

Tests:

1. `test_snippet_file_exists_and_is_registered` — `overlays/repo-ownership.txt` exists; `overlays/manifest.json` `global_snippets` == `["token-frugal.txt", "safety-guardrails.txt", "repo-ownership.txt"]` (exact list — pins presence and that neither existing snippet was dropped).
2. `test_snippet_carries_personal_rule` — lowercased snippet text contains every `base.MDU_31_PHRASES` entry plus both `dihhuit/jeffs_agents` and `dihhuit/opencode_agents`.
3. `test_grokestrator_source_generic_only` — source `grok/agents/grokestrator.md`: every phrase present; `jeffs_agents` count == 0 and `opencode_agents` count == 0 (personal names arrive only via the snippet).
4. `test_built_orchestrators_carry_generic_and_personal` — for `build/prompts/orchestrator.md` and `build/grok/agents/orchestrator.md`: every phrase present and both owned-remote names present.
5. `test_built_grokestrator_carries_personal_rule_exactly_once` — `build/grok/agents/grokestrator.md`: every phrase present; `dihhuit/jeffs_agents` count == 1 and `dihhuit/opencode_agents` count == 1 (== 2 would mean someone added an inline personal copy to the source; == 0 means the snippet was unregistered).
6. `test_mdu_code_overrides_carry_inline_personal_rule` — for `overlays/prompts/mdu-code.md`, `overlays/grok/agents/mdu-code.md`, `overlays/grok/agents/grok-mdu-code.md`: every phrase present and both owned-remote names present.
7. `test_built_mdu_code_bodies_carry_rule_once` — for `build/prompts/mdu-code.md`, `build/grok/agents/mdu-code.md`, `build/grok/agents/grok-mdu-code.md`: every phrase present; each owned-remote name count == 1 (they are full-file installs, no snippet append — a count of 2 would expose a double-write channel).
8. `test_base_deployed_bodies_carry_no_personal_names` — walk the discovered base repo's `prompts/*.md` and `grok/agents/*.md`: no `base.PERSONAL_NAMES` (the overlay-side boundary check; guards the overlay process from ever writing personal names into the public base).

### 8.3 Phrase coverage matrix

Every landing text (§2.1–§2.4) contains all seven `MDU_31_PHRASES` in lowercase; the personal texts additionally contain both owned-remote names. The phrase list is the single contract across both test modules.

## 9. Acceptance criteria (mechanical, in order)

1. Base: `timeout 120 python3 -m pytest tests/ -q` → 0 failed (295 existing + the new module; the grokestrator cross-repo test runs, not skipped, in this workspace).
2. Base: `timeout 300 ./build.sh` → exit 0.
3. Overlay: `timeout 300 ./build.sh` → exit 0 (its final step re-runs the base validator on `build/`, proving the new `ROLE_KEYWORDS` clauses hold over the built orchestrator pair).
4. Overlay: `timeout 120 python3 -m pytest tests/ -q` → 0 failed (base sibling present; no module-level skip).
5. `grep -n "Repository Ownership" build/prompts/orchestrator.md build/grok/agents/orchestrator.md build/grok/agents/grokestrator.md` (overlay repo) → exactly one hit per file.
6. `grep -c "dihhuit/opencode_agents" build/grok/agents/grokestrator.md` → exactly `1`.
7. `grep -rniE "dihhuit|jeffs_agents|opencode_agents" open-agent-definitions/prompts open-agent-definitions/grok/agents` → no hits (README/docs hits are out of scope).
8. `grep -n "Repository Ownership" opencode_agents/build/claude/agents/orchestrator.md` → ≥ 1 hit (the generated Claude mirror inherits the merged prompt for free; no Claude source edits exist).
9. No diffs outside the files in §1; `deploy.sh` untouched; no deploy run as part of this MDU.

Commits (later phase, after QA PASS): one commit per repo, base first, then overlay (its `build/` is tracked — commit the regenerated build output). Push only to the two owned remotes, on the existing `mdu-31-repo-ownership-rule` branches.

## 10. Out of scope / follow-ups

- No `opencode.json` permission changes (§7 rationale).
- No overlay build-semantics change (appending global snippets to full-file overrides).
- No grokestrator Human Approval Gates backport (§5 note).
- No upstream issue/PR anywhere — this MDU is itself the first application of the rule.
