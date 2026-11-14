# MDU-68 — Bulk Grok model pins

Suggestion `20261114-3`. Bulk Grok children inherited the parent `grok-4.7`. The honored fix is a per-type pin in the user Grok config, plus one true clause. The suggestion's spawn sentence is not the byte source. Do not copy it into a prompt.

No OpenCode model id changes. Paths are repo-relative. Overlay sibling = `$OVERLAY`. User config is `~/.grok/config.toml`.

## Surveyed files

Reads (spans are what was opened):

| File | Span | Why |
| --- | --- | --- |
| docs/design/mdu-67-backlog-status-vocab.md | all | tone, status word, suggestion flip, pi refresh |
| docs/design/mdu-66-grokestrator-context-window.md | 1–55 | why a model-wide user-config table was not applied |
| grok/agents/orchestrator.md | 145–229 | bulk sentence, manifest `notes` |
| grok/agents/just-code.md | 1–25 | frontmatter shape |
| grok/agents/grok-review.md | 1–20 | `name:` vs filename |
| prompts/orchestrator.md | 1–30, 150–204 | OpenCode model section; no Grok rung sentence |
| $OVERLAY grok/agents/grokestrator.md | 125–154 | bulk sentence; does not inherit the base grok profile |
| $OVERLAY grok/agents/grok-just-code.md | all | overlay `name:` |
| FEATURE_BACKLOG.md | 610–650 | append after MDU-67 |
| agent-improvements.md | 990–1014 | `20261114-3` bytes |
| scripts/lib/gen_pi_templates.py | 63–112, 174–210, 299–337 | pi source is `grok/agents/`, body verbatim |
| pi/port-config.json | 1–123 | `agents_dir`, audit terms |
| tests/fixtures/pi_golden/prompts/orchestrator.md | 210–229 | golden is the grok orchestrator body |
| docs/pi-parity.md | orchestrator rows | existing hits |
| scripts/lib/secret_scan.py | 40–140 | no long slash-runs in this doc |
| $OVERLAY tests/test_mdu_67_overlay.py | 1–40 | sibling locator |
| $OVERLAY opencode.json | 445–454 | OpenCode grokestrator uses `prompts/orchestrator.md` |
| opencode.json | 17–26 | OpenCode orchestrator uses the same prompt |
| user-guide `16-subagents.md` | 260–309 | pin syntax; inheritance hides `model` |
| user-guide `05-configuration.md` | 320–341 | same table shape |
| install README, Subagents / Toggles and Model Overrides | that section | README claims frontmatter `model` applies after the pin |
| `~/.grok/config.toml` | `[agent]`, `[subagents.toggle]` | `name = "grokestrator"`, `grokestrator = true`; no models table |

Frontmatter extract (`name` and `model` only) of every `*.md` in base `grok/agents/` and `$OVERLAY grok/agents/`. Bodies of the other profiles were not opened.

Grep only: `^model:` across both repos, including `build/` and `overlays/grok/agents/` (not pin sources). No existing test pins the bulk sentence's successor.

## Root cause

Installed CLI is grok 1.0.77. The remote settings cache fetched 2026-11-14 (payload self-label grok_version 1.0.62) has `subagent_model_inheritance_enabled: true`. User config has `[subagents.toggle]` only. No `[subagents.models]`. No `[features] subagent_model_inheritance`. An explicit `subagent_model_inheritance = false` in user config would override the remote true, but only for the next process. This session does not change.

User guide: when inheritance is on and every picker model is xAI, `spawn_subagent` hides `model`. A spawn that still names a model fails. `[subagents.models]` pins, roles, and personas stay in effect. Without a per-type override, the child inherits the parent. Agent-file `model:` is not in that unaffected list. The guide's own example is a string table:

```toml
[subagents.models]
explore = "grok-4.6"
```

Per-type overrides apply for any parent. The install README says the opposite about frontmatter: the pin is highest, then the agent definition's `model`, both unconditional. Live meta contradicts that README while inheritance is on.

MDU-67 child meta, subagent_type `grok-just-code`, description "Insert MDU-67 status clause": `effective_model_id` `grok-4.7`, `effective_context_source` `new`. That profile's frontmatter is `model: grok-build-0.1`. Same effective id on grok-test-agent, grok-code-reviewer, grok-qa, and grok-devops in that session. grok-architect frontmatter is already `grok-4.7`, so its match is not evidence that frontmatter is honored.

This session's `spawn_subagent` schema has no `model` argument. The suggestion sentence "A subagent spawn must pass the profile's frontmatter model." is false here. Do not ship it. Do not tell the orchestrator to pass `grok-build-0.1` on the spawn.

MDU-66 did not apply the model-wide context table, because that knob moves every agent on the model id. Do not repeat that. Do not change `default_model`. There is no `default_model` line in the user config today; do not add one.

## D1 — Behavior knob

Use `[subagents.models]` pins for bulk types only. Leave inheritance on. Do not write `[features]`. Do not set `subagent_model_inheritance`. Do not set an env override.

Pins are the mechanism the user guide leaves in effect while inheritance is on. Turning inheritance off is rejected: it is a wider knob (the model argument comes back for every type, including flagship), and it has the same next-process boundary as a pin, so it does not fix this session either. A prompt that tells the orchestrator to pass a model argument is rejected: the argument is hidden, and naming a model fails.

## D2 — Pin table

Config key is frontmatter `name:`, not the filename. Source trees are base `grok/agents/` and `$OVERLAY grok/agents/` only. `build/` is generated. `overlays/grok/agents/` is not this census.

Included: every extracted profile whose `model` is `grok-build-0.1`. Both families are present, so both are pinned: unprefixed base names and overlay `grok-*` names.

Excluded on purpose: every extracted profile whose `model` is `grok-4.7`, including architect, architect-premium, orchestrator, introspector, inception, the mid and pro rungs, grokestrator, grok-plan, grok-deep-research, and the overlay `grok-*-mid`, `grok-*-pro`, and `grok-architect*` profiles. Their match to the parent is not a miss.

`overlays/grok/agents/grok-mdu-code.md` is also `grok-build-0.1` and is not pinned. Out of scope with `mdu-code`. It will keep inheriting until a later MDU.

Keys below are the full set. Alphabetical. Bare keys are valid. Values are the string `grok-build-0.1`.

## D3 — User config is the behavior change

Yes. Implement writes `~/.grok/config.toml`. That file is outside both git repos. Do not commit it. `./deploy.sh` does not install this table.

The table is read when a grok process starts. It does not change this session. Acceptance in this session is that the file contains the table. A same-session spawn is still allowed to inherit `grok-4.7`. That inherit is not a FAIL. Do not restart grok inside this MDU. Do not spawn a child to prove `effective_model_id`.

Edit rules:

- Insert the new table immediately after the existing `[subagents.toggle]` block.
- Leave `[subagents.toggle] grokestrator = true` and `[agent] name = "grokestrator"` as they are.
- Do not edit `[cli]`, `[mcp_servers]`, `[privacy]`, `[consent]`, or any other table.
- The models table must end as exactly the 14 keys below. It is absent today. If a listed key is already `grok-build-0.1`, leave it. If a listed key is any other value, or the table has an extra key, stop and report. Do not overwrite and do not delete unrelated keys.
- Do not print the rest of the file in notes. The consent section is not part of this MDU.

## D4 — Clause, grok-only pair

Ship the clause. It is not the suggestion sentence.

`prompts/orchestrator.md` stays unchanged. That file is the OpenCode orchestrator and the OpenCode grokestrator (`system` points at it). It has no Grok bulk-vs-flagship sentence. Its children are Go model ids in `opencode.json`, not `spawn_subagent`. A Grok pin instruction there would be a false spawn rule. Claude copies are generated from that prompt, so they stay put too.

grokestrator does not inherit base `grok/agents/orchestrator.md`. Both Grok profiles need the same new bullet, next to the bullet that already states the rung split. The two anchor bullets are not the same text. Do not reword them. No blank line between the anchor and the new bullet.

Pi: `pi/port-config.json` `source.agents_dir` is `grok/agents`. The generator copies that body verbatim. The golden path `tests/fixtures/pi_golden/prompts/orchestrator.md` is that output, not a copy of `prompts/orchestrator.md`. Leaving the OpenCode prompt untouched does not freeze the golden. Refresh that one golden from the generator after the base grok edit. Every other golden stays put. The new bullet adds no audit term that orchestrator does not already hit (`spawn`, `subagent`, `grok-4.7`, `grok-build-0.1`). Do not edit `pi/port-config.json` or `docs/pi-parity.md`. If `PARITY.md` or Gate D changes, stop.

## D5 — Suggestion checkbox

Flip only `20261114-3` to resolved. Leave evidence, definition change, and apply-now bytes. Those bytes still say to pass a model. The note is the correction: the shipped mechanism is the pin plus the clause, not that sentence, and not the apply-now line that says to pass `grok-build-0.1`. Do not flip `20261114-2` or any other id.

From:

```text
- [ ] id: 20261114-3 | severity: warn | target: orchestrator | kind: expensive_model_on_bulk_role
```

To:

```text
- [x] id: 20261114-3 | severity: warn | target: orchestrator | kind: expensive_model_on_bulk_role | **RESOLVED 2026-11-14 (mdu-68)**
```

Add this note immediately after that entry's apply-now bullet:

```text
  - note (2026-11-14, mdu-68): **RESOLVED** — shipped mechanism is the `[subagents.models]` pin for every frontmatter `grok-build-0.1` name under base `grok/agents/` and overlay `grok/agents/`, plus the Grok-only clause in `grok/agents/orchestrator.md` and overlay `grok/agents/grokestrator.md`. Not the suggestion sentence and not a spawn `model` argument: while inheritance is on, that argument is hidden. `prompts/orchestrator.md` unchanged. The pin is outside git and applies on the next grok process.
```

## D6 — Backlog row

Append after MDU-67. One status line. Heading must not contain `queue head`. Status word is `Done`. The reason is in that same bullet: user-config pins plus the clause.

```text
### MDU-68 · Bulk Grok model pins

- **Why:** Suggestion 20261114-3. With subagent model inheritance on, bulk Grok children inherited the parent `grok-4.7`. Frontmatter `model` was not honored, and `spawn_subagent` has no `model` argument to pass.
- **Description:** `[subagents.models]` pins for the fourteen `grok-build-0.1` names in docs/design/mdu-68-bulk-model-pin.md. Inheritance stays on. One Grok-only clause in base `grok/agents/orchestrator.md` and overlay `grok/agents/grokestrator.md`. `prompts/orchestrator.md` unchanged.
- **Status:** Done — 2026-11-14 (user-config `[subagents.models]` pins plus the Grok-only clause; inheritance stays on; the pin is read by the next grok process, not this session.)
```

## Exact toml block

Paste this. The comment may differ. Keys and values may not.

```toml
[subagents.models]
code-reviewer = "grok-build-0.1"
devops = "grok-build-0.1"
grok-devops = "grok-build-0.1"
grok-just-code = "grok-build-0.1"
grok-qa = "grok-build-0.1"
grok-research = "grok-build-0.1"
grok-review = "grok-build-0.1"
grok-test-agent = "grok-build-0.1"
grok-ui-ux-designer = "grok-build-0.1"
just-code = "grok-build-0.1"
qa = "grok-build-0.1"
research = "grok-build-0.1"
test-agent = "grok-build-0.1"
ui-ux-designer = "grok-build-0.1"
```

Census those keys against frontmatter again at implement time. A new `grok-build-0.1` name in either source tree that is missing here is a stop, not a silent add. A `grok-4.7` name in this table is a stop.

## Exact prompt clause

One full line, both Grok carriers, backticks included. Do not paraphrase.

```text
- On the Grok harness, `spawn_subagent` may have no `model` argument because subagent model inheritance is on and every picker model is xAI. Do not invent one; a named model fails while the argument is hidden. The honored per-type pin is `[subagents.models]` in `~/.grok/config.toml`, read at the next grok process, not by this session. Agent-file `model:` is not that pin. Append the child `effective_model_id` to the manifest phase `notes`. A bulk profile (frontmatter `grok-build-0.1`) whose `effective_model_id` is `grok-4.7` is a tier miss.
```

Do not add a manifest field. `phases[].notes` already exists. Do not edit the required-fields line or the example JSON. Recording `grok-4.7` on a bulk profile is how the miss is visible. It does not fail this MDU when the child was spawned by this process.

Rejected sentence, absent from every carrier:

```text
A subagent spawn must pass the profile's frontmatter model.
```

## Carrier table

| # | Repo | Path | In | Insert after | Successor stays |
| --- | --- | --- | --- | --- | --- |
| 1 | base | grok/agents/orchestrator.md | in | the bullet that starts `Grok Build currently exposes` and contains `Bulk profiles use` | `- Rotate through role variants for repeated tasks to avoid exhausting any single agent's rate limits.` |
| 2 | overlay | grok/agents/grokestrator.md | in | the bullet that starts `**TOKEN FRUGALITY:**` and contains `Bulk Grok agents use` | `- **PAID-SPAWN FAILURE LADDER — ONE RETRY, ONE ROTATION, THEN STOP:**` |
| 3 | base | prompts/orchestrator.md | out | — | file byte-identical to HEAD |

No other prompt, grok profile, or `opencode.json` model field is a carrier. Do not hand-edit `build/`. Overlay `./build.sh` regenerates `build/grok/agents/orchestrator.md` and `build/grok/agents/grokestrator.md`. Global snippets append at EOF, so pins are full-line presence and adjacency, not whole-file equality. `build/prompts/orchestrator.md` and the Claude orchestrator copies stay unchanged because row 3 is unchanged.

## Acceptance checks

No new grok process. Do not call `grok`. Do not spawn. A same-session child with `effective_model_id` `grok-4.7` is allowed.

User config (implement and QA; not a committed pytest, because the file is outside the repo):

```bash
timeout 30 python3 -c 'import pathlib, tomllib; p = pathlib.Path.home() / ".grok" / "config.toml"; text = p.read_text(); data = tomllib.loads(text); exp = {"code-reviewer","devops","grok-devops","grok-just-code","grok-qa","grok-research","grok-review","grok-test-agent","grok-ui-ux-designer","just-code","qa","research","test-agent","ui-ux-designer"}; got = data["subagents"]["models"]; assert set(got) == exp; assert all(got[k] == "grok-build-0.1" for k in exp); assert data["subagents"]["toggle"]["grokestrator"] is True; assert data["agent"]["name"] == "grokestrator"; assert "subagent_model_inheritance" not in data.get("features", {}); assert "default_model" not in text; print("config pin ok", len(got))'
```

Repo, hermetic:

1. The clause line occurs once in each in-carrier, and the previous line is that row's anchor. The successor line is unchanged.
2. `prompts/orchestrator.md` has no diff. The rejected sentence occurs in none of the three orchestrator files.
3. `grep -F -x` of the D6 status line in `FEATURE_BACKLOG.md` returns one hit. The MDU-68 heading does not contain `queue head`. `python3 -m pytest tests/test_mdu_45_grok_review_registry.py::test_backlog_no_entry_remains_unresolved -q` is green and that test file has no diff.
4. `grep -n 'id: 20261114-3' agent-improvements.md` shows one `[x]` line and the D5 note, and no remaining `- [ ] id: 20261114-3`. No other id's checkbox changes (`git diff -U0 -- agent-improvements.md`).
5. Base `tests/test_mdu_68_bulk_model_pin.py`: the clause line, adjacency, rejected-sentence absence, D6 status line, D5 checkbox and note, and a frontmatter census of base `grok/agents/` (every `grok-build-0.1` `name` is in the toml fence in this design doc; no `grok-4.7` `name` is). One `/tmp` mutation, delete the clause from a copy of `grok/agents/orchestrator.md`, expect non-zero. Do not mutate the worktree or the user config. No "N files" assertion.
6. Overlay `tests/test_mdu_68_overlay.py`, after `$OVERLAY ./build.sh`: clause once in `grok/agents/grokestrator.md` with the row-2 successor; the same line in `build/grok/agents/orchestrator.md` and `build/grok/agents/grokestrator.md`; clause absent from `overlays/grok/agents/mdu-code.md`, `overlays/grok/agents/grok-mdu-code.md`, and `build/prompts/orchestrator.md`. Census `$OVERLAY grok/agents/` the same way against the base design-doc fence, via the sibling locator in `tests/test_mdu_67_overlay.py`. `grok-mdu-code` must not be a pin key.
7. Pi: `./build.sh`, then copy the generated orchestrator template over `tests/fixtures/pi_golden/prompts/orchestrator.md`. Do not type the bullet into the golden. Expect that file to differ from HEAD by the one inserted line and nothing else. `timeout 120 python3 -m pytest tests/test_mdu_56_pi_port.py -q` green. File count unchanged. Do not add a count pin.
8. Base `timeout 300 python3 -m pytest tests/ -q` and `./build.sh` exit 0. `timeout 60 python3 scripts/lib/prompt_regression.py gate` exit 0. Do not run `baseline`, do not pass `--update`, do not edit `evals/golden/baseline.json`. Overlay `./build.sh` and `timeout 300 python3 -m pytest tests/ -q` exit 0.
9. `timeout 60 python3 scripts/lib/secret_scan.py --staged` exit 0 on the base commit. The user-config file is not staged.

Deploy, after QA PASS, from `$OVERLAY`: dry-run `./deploy.sh`, then `./deploy.sh --force`. That installs the clause into the Grok profiles. It does not write the pin. QA re-runs the tomllib check and confirms installed `orchestrator.md` and `grokestrator.md` contain the clause once. Still no new grok process.

Commits, base first, explicit paths, no `git add -A` in the overlay. Owned remotes. No PR. The user-config edit is in neither commit.

Base message `feat(mdu-68): pin bulk grok profiles in the orchestrator clause`: this design doc, `grok/agents/orchestrator.md`, `tests/test_mdu_68_bulk_model_pin.py`, `tests/fixtures/pi_golden/prompts/orchestrator.md`, `FEATURE_BACKLOG.md`, `agent-improvements.md`.

Overlay message `feat(mdu-68): carry the bulk model-pin clause into grokestrator`: `grok/agents/grokestrator.md`, `tests/test_mdu_68_overlay.py`, and the regenerated `build/grok/agents/orchestrator.md` and `build/grok/agents/grokestrator.md` only.

Who edits what: just-code inserts the clause, the backlog section, the suggestion flip, the user-config table, and copies the one golden from generator output. just-code does not author the pin tests and does not type into a golden. test-agent writes the two pin files and the one `/tmp` mutation. Review does not rewrite the clause or the toml keys. This design doc is already written.

## Out of scope

- Suggestion `20261114-2` (session store lookup). Do not flip it.
- OpenCode `opencode.json` model fields, including `xai/grok-build-0.1` rows. Those already name the rung. This bug is Grok inheritance, not the registry.
- Turning subagent model inheritance off, in config, `/settings`, or the environment.
- `default_model`, and the model-wide context-window table MDU-66 refused.
- `mdu-code` and `grok-mdu-code`, including the overlay `grok-build-0.1` profile.
- Flagship profiles (`grok-4.7`), mid/pro rungs, grokestrator's own model id, and architect.
- A restart, a fresh grok process, or a proof spawn inside this MDU.
- Editing the install README or the user guide so they agree. The clause records which one matches live meta.
