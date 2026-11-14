# MDU-63 — Definition-guards batch: survey clause, rebuild clause, cache-miss clause

> Design phase. Apply path user-approved 2026-11-14 (mirrors the mdu-47/49/60/62
> batch pattern). Three introspector suggestions, each with clause text already
> drafted in `agent-improvements.md`; insertion is byte-identical to the approved
> drafts (single design-time approval, mdu-60 carve-out pattern). Paths
> repo-relative — base repo = this repo; overlay sibling = `../opencode_agents/`
> (`$OVERLAY` in prose). No model ids are assigned anywhere in this design (pure
> prompt-text edits) — the live-probe rule is satisfied vacuously.

## 0. Surveyed files (reads only; grep-only beyond this list)

Base repo:

| File | Lines read | Why |
| --- | --- | --- |
| agent-improvements.md | 471–500, 902–916, 977–981 | the three suggestion entries + clause texts (byte source of truth) |
| prompts/architect.md | all (22) | placement |
| grok/agents/ · architect.md | all (27) | mirror census |
| grok/agents/ · architect-premium.md | all (24) | mirror census |
| prompts/just-code.md | all (36) | placement |
| grok/agents/ · just-code.md / just-code-mid.md / just-code-pro.md | all (37/37/35) | family census + anchors |
| prompts/orchestrator.md | 45–109 | compact-at-140000 + CACHE MISS GATE block (adjacency target) |
| docs/design/ · mdu-62-pr-policy.md | 1–146 | batch precedent: gates, mutation matrix, commit plan |
| tests/ · test_mdu_62_pr_policy.py | all | pin-suite precedent |
| tests/ · test_mdu_49_definition_batch.py | 106–150 | carrier/anchor pin precedent |
| tests/ · test_mdu_56_pi_port.py | 1–60, 286–400 | Gate A–E mechanics |
| pi/README.md | 53–74 | golden refresh checklist |
| pi/port-config.json | all (126) | audit lexicon (constructs/terms) |
| scripts/lib/ · secret_scan.py | rule block | the 32-char token rule (path-lexeme trap) |

Overlay repo (`../opencode_agents/`):

| File | Lines read | Why |
| --- | --- | --- |
| grok/agents/ · grokestrator.md | 82–97 | cache-miss block (mirror anchor) |
| grok/agents/ · grok-just-code.md | all (22) | condensed carrier shape |
| grok/agents/ · grok-architect.md | all (20) | carrier shape |
| tests/ · test_mdu_54_overlay_grok_clause_parity.py | all | overlay pin precedent |
| tests/ · test_mdu_54_parity_coverage.py | 1–55 | byte-identity/coverage addendum precedent |

Grep-only census (no reads): near-duplicate fragments ("authoritative state",
"read surface is auditable", "generated copies are fresh", "store probe or
signal run") across both repos — hits only in agent-improvements.md (the log
itself; zero live carriers, i.e. all three clauses are net-new text); carrier
anchors ("- **Be token efficient**", "Before reporting", "- Always verify",
"CACHE MISS GATE", 140000/compact); grok/agents directory listings (both
repos); pi-parity rows for delegation / keybindings-compact × orchestrator;
FEATURE_BACKLOG.md (no MDU-63 row); base tests inventory + region-pin greps
(no pin locks the pre-insertion state of any edit region); overlay tests
pin-greps for grokestrator / grok-just-code / grok-architect; overlays/
full-file-override listing (no architect or just-code overrides).

Path-lexeme note: every path in this doc is repo-relative (no absolute
paths). Slash-joined compounds ≥ 32 chars are split at slash boundaries in
prose/tables; the few full-length script paths inside command fences are
dot-broken below the scanner's entropy-gated `[A-Za-z0-9+/]{32,}` run
threshold (rule verified against the scanner source this session), so the
secret gate stays green.

## 1. D-1 — Carrier set and census disposition

**Carrier set = 15 files** (clause per family; emitted forms in §3):

| Family (clause) | Repo | Dir | File |
| --- | --- | --- | --- |
| Architect (20261024-1) | base | prompts/ | architect.md |
| | base | grok/agents/ | architect.md |
| | base | grok/agents/ | architect-premium.md |
| | overlay | grok/agents/ | grok-architect.md |
| | overlay | grok/agents/ | grok-architect-premium.md |
| Just-code (20261113-1) | base | prompts/ | just-code.md |
| | base | grok/agents/ | just-code.md |
| | base | grok/agents/ | just-code-mid.md |
| | base | grok/agents/ | just-code-pro.md |
| | overlay | grok/agents/ | grok-just-code.md |
| | overlay | grok/agents/ | grok-just-code-mid.md |
| | overlay | grok/agents/ | grok-just-code-pro.md |
| Orchestrator (20261110-2) | base | prompts/ | orchestrator.md |
| | base | grok/agents/ | orchestrator.md |
| | overlay | grok/agents/ | grokestrator.md |

Rulings:

1. **Overlay personal variants are included** (grok-architect ×2,
   grok-just-code ×3). mdu-54 established byte-parity as the standing
   discipline for overlay root grok-\* profiles vs their base siblings; the
   brief's just-code scope explicitly says "any overlay carriers"; and the
   user's daily deployment runs from the overlay, so leaving the overlay
   architect variants clause-free while their base siblings gain the clause
   is exactly the parity drift mdu-54 closed. **Veto note (Q-2):** to narrow
   to the strict approved set (base-only for architect), drop the two overlay
   architect rows — every AC/pin that names them severs cleanly.
2. **grokestrator is a root-added LIVE source**, not a full-file override —
   the clause must land in the file itself (mdu-49/54 precedent); the base
   prompt edits do not flow into it.
3. **Non-carriers (census disposition):**

| Hit | Disposition |
| --- | --- |
| prompts/orchestrator.md:76–87 CACHE MISS GATE block (+ grok mirror, grokestrator) | **Extended, not replaced** — D-4; the clause lands inside it. |
| Compact-at-140000 blocks (all three orchestrator mirrors) | **Left as-is** — different trigger (prompt size) and different remedy (compaction timing); no overlap with the clause. |
| overlay mdu-code / grok-mdu-code (overlays/prompts/, overlays/grok/agents/) | **Left as-is** — personal coder agents, deliberately divergent (monorepo/Android/ROCm); not just-code mirrors; extending them is a new clause-surface decision (mdu-54 exclusion-row discipline). |
| overlay root prompts/ (only grok-plan.md) | **Left as-is** — no dead same-name copies of any carrier (dead-copy hygiene suite enforces). |
| skills/, docs/, evals/ (both repos) | **Left as-is** — zero clause-marker hits (census grep); no carriers. |
| base build/ (gitignored) + overlay build/ (tracked) | **Regenerated** by the builds; never hand-edited (D-6). |
| tests/fixtures/pi_golden/ tree | **Regenerated** deliberately per D-5. |
| introspector carriers (prompts/, grok/agents/) | **Left as-is** — pinned by mdu-49 for other clauses; not these clauses' carriers. |
| agent-improvements.md | **The log** — only current home of the clause texts; gets the three RESOLVED flips in the base commit (§9). |

4. **No existing test locks the pre-insertion state of any edit region**
   (grep-verified: nothing pins the token-efficient bullet as last
   responsibility, no "Before reporting" adjacency pin, the grokestrator
   cluster pins are order-only). Every edit below is a pure insertion between
   existing lines — no text is displaced, so the existing suites
   (base mdu-41/43/47/49/57/61; overlay mdu-09/11/15/31/40/41/49/54) stay
   green by construction. The full pytest runs in D-8 are the gate.

## 2. Clause texts (byte-exact; these fences are the authority)

The pin-suite constants must match these fences byte-for-byte
(doc-consistency pin, mdu-49/60/62 convention). Entry lines noted for audit.

**2a. 20261024-1** — high, architect token_hotspot (recurring 14+ runs;
record 285,350 in mdu-62). Source: agent-improvements.md line 473.

```text
The design brief names the files and sections relevant to this MDU. Read those first and treat them as the authoritative state; survey the rest of the repository with grep/glob, not full reads. List every file you surveyed at the top of the design doc so the read surface is auditable.
```

**2b. 20261113-1** — warn, just-code rebuild_after_source_edit (new from
mdu-62's three-cycle rebuild debt). Source: line 979.

```text
A fix is incomplete until the generated copies are fresh: after editing any source file that has build/generated copies (skills, prompts, grok builds, pi goldens, build/ trees), run the build/gate that regenerates them in the SAME cycle and re-diff the copies against the source before reporting done — a source fix with stale copies will be returned by review.
```

**2c. 20261110-2** — warn, orchestrator cache_miss (recurring; mdu-62's miss
was a pasted-resume session). Source: line 904.

```text
If a store probe or signal run reports a cache miss on this session (cache.read ≤1152 with input ≥80k), do not spawn the next phase from this session — start fresh from the resume block (or compact) first; a miss on a ≥200k-token orchestrator prompt re-bills every subsequent child brief.
```

Glyph note: 2c ships with the drafted Unicode (≤, ≥, ≥200k) exactly as
approved; the existing gate block uses ASCII (`<= 1152`, `>= 80000`). The
difference is the approved text, not drift — pins use the clause's own bytes.

## 3. D-2 + D-3 — Insertion point and emitted form per carrier

**D-3, emitted forms** (mdu-47 erratum convention — form follows the file
shape; the clause bytes inside are identical everywhere):

- Architect + just-code carriers: a bullet — `- ` + clause text (one line).
- Orchestrator mirrors: a paragraph inside the bullet block — two-space
  indent + clause text, matching the CACHE MISS GATE paragraph style (e.g.
  the `  A cache miss is …` paragraph).

**D-2, insertion points** — anchor = existing line; the clause goes
immediately after it. Line numbers are current-HEAD; the implementer re-greps
by anchor text, not number.

**3a. Architect family** — new final bullet of the "Your responsibilities"
list, directly after the token-efficient bullet (before the blank line and
`Hard constraints:`). The five token-efficient bullets differ per carrier, so
adjacency pins locate them by the `- **Be token efficient**` marker:

| Carrier | Anchor (current line) |
| --- | --- |
| prompts/architect.md | :10 `- **Be token efficient**: Write focused design docs that are clear enough …` |
| grok/agents/ · architect.md | :16 `- **Be token efficient**: Write focused design docs. Surface key decisions …` |
| grok/agents/ · architect-premium.md | :15 `- **Be token efficient**: The reasoning model is for depth of analysis, not verbosity.` |
| $OVERLAY grok/agents/ · grok-architect.md | :15 `- **Be token efficient**: Focused design docs with key decisions.` |
| $OVERLAY grok/agents/ · grok-architect-premium.md | :14 `- **Be token efficient**: The reasoning model is for depth, not verbosity.` |

Rationale: the clause is design-phase read discipline — a responsibility,
adjacent to the token-frugality bullet it operationalizes (the same pairing
the 20261024-1 evidence diagnoses: spend = repo-survey reads).

**3b. Just-code family** — new bullet at the tail of the `Hard constraints:`
list. In the four base carriers it follows the before-reporting-done secret
bullet (the clause is itself a before-reporting-done check — "… before
reporting done"); in the condensed overlay profiles (no before-done bullet)
it follows the display-integrity bullet (the mdu-54 D5 bullet, the last
constraint), the closest relative position:

> **Erratum (2026-11-14, mdu-63):** "tail of the list" above is inaccurate and
> non-normative. The clause goes immediately AFTER the before-reporting-done
> bullet, NOT at the tail: in `prompts/just-code.md` and the base
> `grok/agents/just-code.md` mirror the token-budget bullet follows that
> anchor, so the clause is inserted between the two. D-2 is normative; this
> § is descriptive only. The overlay condensed profiles are unaffected — there
> the clause does sit last, after the D5 display-integrity bullet.

| Carrier | Anchor (current line) |
| --- | --- |
| prompts/just-code.md | :20 `- Before reporting work done, scan the files you changed: …` |
| grok/agents/ · just-code.md | :26 `- Before reporting done, run … secret_scan.py …` |
| grok/agents/ · just-code-mid.md | :27 same before-reporting-done bullet (last constraint) |
| grok/agents/ · just-code-pro.md | :25 same (last constraint) |
| $OVERLAY grok/agents/ · grok-just-code{,-mid,-pro}.md | the display-integrity (D5) bullet — last bullet of the constraints list (grep the `UNTRUSTED until verified` marker) |

**3c. Orchestrator family** — the clause lands **inside the CACHE MISS GATE
block**, as its final paragraph: immediately after gate step 3, before the
`- **CODER HANDOFF:**` bullet, blank-line separated. All three mirrors carry
the block byte-identically today (verified this session), so the same
two-space-indented paragraph is correct in each:

| Carrier | Anchor region (current lines) |
| --- | --- |
| prompts/orchestrator.md | step 3 at :87 → clause → CODER HANDOFF at :89 |
| grok/agents/ · orchestrator.md | step 3 at :93 → clause → CODER HANDOFF at :95 |
| $OVERLAY grok/agents/ · grokestrator.md | step 3 at :93 → clause → CODER HANDOFF at :95 |

Anchor markers for pins: step 3 = `"keep going" is not an override`; block
start = `- **CACHE MISS GATE:**`; next bullet = `**CODER HANDOFF:**`.

## 4. D-4 — 20261110-2 extends the existing CACHE MISS GATE (no duplication)

Census question: the mirrors already carry a compact-at-140000 regime and a
CACHE MISS GATE block (definition, latest-row self-check via
`OPENCODE_SESSION_ID`, STOP rule, user steps 1–3). Ruling — the clause
**extends** the gate, it does not duplicate it:

- Existing trigger = the orchestrator's own latest-row check before a
  delegate. Clause trigger = an **external report** (store probe / signal
  run / introspection JSON) — a source the gate does not cover.
- Existing remedy = stop this turn + hand the user the resume-block steps.
  Clause remedy = a **spawn-side rule** (do not start the next phase from
  this session; fresh session or compact first) — it reinforces steps 1–2
  rather than re-stating them.
- The clause's parenthetical signature matches the gate's definition (same
  thresholds; drafted glyphs per §2).
- Placement inside the block (D-2 3c) keeps ONE cache-miss authority per
  mirror; a second floating bullet would fork it. The compact-at-140000
  blocks are a different trigger class and stay untouched.

Known hazard (from the log, mdu-56 note on this suggestion): a benign
child-wait miss (cache cold across a long child wait, next row warm, fresh
session) would fire the clause spuriously and force an unnecessary
fresh-session restart; the log recommends a carve-out ("pause-class miss on
a fresh session where the next row is warm") before the clause ships. The
approved text has no carve-out → **Q-1 (§11)**. Design default: ship as
approved — the failure mode is cheap (one extra session restart) and the
carve-out is a one-line fast-follow amendment if the spurious class shows up
in the next runs' signal JSON.

## 5. D-5 — Pi-port impact (mdu-56 gates)

**Pi sources affected: the six base grok carriers** — architect,
architect-premium, just-code, just-code-mid, just-code-pro, orchestrator.
The generator reads grok/agents/ only; overlay files are not pi sources. Six
of the 20 sources change → six template bodies change.

**Golden regeneration** (pi/README.md checklist, in order — this is also the
20261113-1 dogfood, D-9):

1. Regenerate: `./build.sh` (refreshes build/pi), or
   `python3 scripts/lib/gen_pi_templates.py <dir>` into a temp dir.
2. Review the diff against the golden tree (tests/fixtures/pi_golden/) —
   read every changed template line; expect exactly the six clause
   insertions and nothing else.
3. Lexicon/parity: the architect and just-code clauses contain **no audit
   terms** (checked against every construct in pi/port-config.json this
   session). The orchestrator clause hits existing terms (cache miss,
   cache.read, compact → keybindings-compact; spawn → delegation) and both
   (construct, profile) pairs already have rows in docs/pi-parity.md
   (`| delegation | orchestrator |`, `| keybindings-compact | orchestrator |`)
   → **no new lexicon or parity rows expected**. Verify by running
   `python3 scripts/lib/gen_pi_templates.py --audit` and Gate D; if a new
   pair appears (it should not), add one hit row per profile per checklist
   step 3.
4. Copy the regenerated tree over tests/fixtures/pi_golden/ and commit the
   golden snapshot **together with the source edits in the same base
   commit** (the six changed role templates live under the golden tree's
   prompts/ directory).

Gate expectations: Gate B (byte-verbatim per role) green by construction;
Gate C green after the refresh — two generations identical and golden match,
file count stays 23 (no templates added/removed); Gate D green (no new
pairs); Gate E untouched (preamble unchanged).

## 6. D-6 — Overlay impact

**Overlay source edits (6 files, all under grok/agents/ in $OVERLAY):**
grok-architect.md, grok-architect-premium.md, grok-just-code.md,
grok-just-code-mid.md, grok-just-code-pro.md, grokestrator.md.

Build behavior: root grok profiles are live sources; `$OVERLAY ./build.sh`
copies them into the tracked build tree and appends the global snippets →
build pins assert clause **presence**, not byte-equality with the root source
(mdu-49/44/54 precedent). The base-layer copies (base grok agents + base
prompts) and the generated Claude subagents pick the clauses up via the base
build re-run — nothing hand-edited under build/.

**Overlay build-copy pins** (overlay suite, D-7): the built copies of the six
overlay profiles, the built base-layer copies of the nine base carriers, and
the built grokestrator each carry their clause (presence, exactly once).

**Cross-repo order:** base first (commit + push), then overlay (six sources +
regenerated tracked build/ + overlay suite) — never `git add -A` in the
overlay; the dirty build tree is committed as the intended regeneration
output (mdu-62 §6b pattern). Two commits, two pushes.

## 7. D-7 — Pin-test plan

**7a. Base suite: `tests/test_mdu_63_guards.py`** (mdu-49/62 shapes; hermetic
file reads; cwd-independent; specimen root overridable via `MDU63_TEST_ROOT`
for mutants; repo-state pins always read the real repos):

1. `test_constants_match_design_doc` — each clause constant appears verbatim
   in this doc's §2 fence (doc-consistency).
2. Presence + byte per base carrier (parametrized, 9): the exact emitted line
   (bullet or indented paragraph, lead included) appears as a FULL line
   (grep -F -x equivalent) exactly once.
3. Adjacency per family: architect clause after the carrier's
   `- **Be token efficient**` bullet and inside the responsibilities span
   (before `Hard constraints:`); just-code clause after the
   before-reporting-done bullet (base four; marker per carrier — the prompt
   says "Before reporting work done", the grok mirrors "Before reporting
   done, run") inside the Hard-constraints span; orchestrator clause after
   gate step 3 and before the CODER HANDOFF bullet (inside the CACHE MISS
   GATE block).
4. Fragments (scenario pins, mdu-62 style), 3–4 per clause, e.g.
   `authoritative state`, `grep/glob, not full reads`,
   `read surface is auditable`; `generated copies are fresh`,
   `in the SAME cycle`, `re-diff the copies against the source`;
   `store probe or signal run`, `do not spawn the next phase from this
   session`, `re-bills every subsequent child brief`.
5. Census negatives: clause markers appear in NO other live definition file
   under the test root (prompts/ + grok/agents/ + skills/ sweep); no carrier
   carries a second near-duplicate (count == 1).
6. Third-mirror pin: the grokestrator clause pinned via the overlay sibling
   with skipif (mdu-62 MIRRORS pattern); the overlay suite below owns the
   authoritative overlay pins.

**7b. Overlay suite: `tests/test_mdu_63_overlay.py`** (mdu-54 shapes; base
sibling resolved via the mdu-54 sibling discovery):

1. Presence (parametrized, 6): each overlay source carries its clause's
   emitted form exactly once.
2. Byte-identity with the base sibling (mdu-54 coverage-addendum pattern):
   the overlay emitted line == the base sibling's emitted line (same clause,
   same form) for each pair.
3. Ordering: architect clause after the token-efficient bullet; just-code
   clause after the display-integrity (D5) bullet and inside the
   Hard-constraints span; grokestrator clause inside the CACHE MISS GATE
   block (step 3 < clause < CODER HANDOFF).
4. Built copies (require `./build.sh` first): presence exactly once in the
   built copies named in D-6.

**7c. Mutation matrix — RUNS in /tmp/opencode/, never the working tree**
(mdu-62 §5 pattern): copy the carrier trees + this design doc into
`/tmp/opencode/mdu63-mut<N>/`, apply ONE mutation, run
`MDU63_TEST_ROOT=/tmp/opencode/mdu63-mut<N> timeout 120 python3 -m pytest tests/test_mdu_63_guards.py -q`,
expect the named red:

- **M1 (required):** delete the architect clause from prompts/architect.md →
  cases 2/3/4 red.
- **M2:** reword `authoritative state` → `canonical state` in one grok
  architect mirror → byte + fragment red.
- **M3:** delete the just-code clause from the just-code-pro mirror → case 2
  red.
- **M4:** move the just-code clause above the before-reporting-done anchor →
  case 3 red.
- **M5:** delete the orchestrator clause from the grok orchestrator mirror →
  case 2 red.
- **M6:** move the orchestrator clause after the CODER HANDOFF bullet →
  case 3 red.
- **M7:** strip `in the SAME cycle` from one carrier → case 4 red.

## 8. D-8 — Gates before commit (ordered)

```bash
cd <base repo>                                            # open-agent-definitions
timeout 300 python3 -m pytest tests/ -q                   # all green, incl. the new suite (after the golden refresh below)
./build.sh                                                # validator green; regenerates build/ (pi, claude, prompts, grok copies)
# pi golden refresh per §5: diff review → copy over tests/fixtures/pi_golden/
timeout 120 python3 -m pytest tests/test_mdu_56_pi_port.py -q   # Gates A-E green
timeout 60 python3 scripts/lib/prompt_regression.py gate  # prompts/ + grok/agents/ changed → gate required; expect exit 0, baseline intact (mdu-62 precedent). On an intentional-text red follow the evals/README.md snapshot/diff protocol — never refresh the baseline to force green.
timeout 60 python3 scripts/lib/run_ledger.py validate runs/mdu-63-definition-guards-batch/manifest.json   # model field recorded
timeout 60 python3 scripts/lib/secret_scan.py --staged    # exit 0
# mutation matrix per §7c in /tmp/opencode/ (never the working tree)
git add <base file list §12>
git commit -m "feat(mdu-63): definition-guards batch — architect survey clause, just-code rebuild clause, orchestrator cache-miss clause"
git push origin main                                      # owned repo: direct push, no PR (MDU-62 policy)

cd ../opencode_agents
./build.sh                                                # re-runs the base build + merges; regenerates the tracked build/ tree
timeout 300 python3 -m pytest tests/ -q                   # overlay suite green incl. test_mdu_63_overlay.py
# secret-scrub checklist over the staged diff (no secret_scan.py in this repo)
git add <overlay file list §12>
git commit -m "feat(mdu-63): carry the three guard clauses into the overlay variants + rebuilt tree"
git push origin main
./deploy.sh --force                                       # installs for whichever of opencode/grok/claude are on PATH
```

**Deploy verification (installed-copy probes, QA):** one grep per clause per
CLI present — `grep -c "authoritative state"` on the deployed architect
copies (`~/.grok/agents/` architect.md and grok-architect.md),
`grep -c "generated copies are fresh"` on the just-code copies, and
`grep -c "store probe or signal run"` on the orchestrator copies
(orchestrator.md, grokestrator.md) — expect 1 each; spot the same three
markers in the deployed OpenCode prompt copies under `~/.config/opencode/`
and one generated Claude agent per family under `~/.claude/agents/`.

## 9. D-9 — Apply-now carries into the briefs (this MDU dogfoods all three)

- **20261113-1 (verbatim into every fix-cycle brief of this MDU):** "If you
  touch a source file with generated copies, run the build, re-diff the
  copies against the source, and report the build exit code before
  reporting done." This MDU edits 15 source files with generated copies →
  the implement cycle MUST run both builds + re-diff (pi goldens, build
  trees) + report exit codes in the SAME cycle; review round 1 checks copy
  freshness FIRST (same suggestion's review-side apply-now).
- **20261110-2:** the orchestrator checks this session's signal JSON for
  cache_miss before spawning the next phase; on a miss, the implement phase
  starts from a fresh session (resume block), not from this session. The
  next run's signal JSON is the measurement for whether the fresh-session
  start removed the flag.
- **20261024-1:** already carried by this brief (authoritative file list +
  survey discipline + §0 of this doc); the mdu-63 implement/QA briefs keep
  naming files and sections instead of trees.
- **Manifest:** runs/mdu-63-definition-guards-batch/manifest.json records the model field; the
  commit row is appended at commit time; the three agent-improvements.md
  entries flip to `- [x]` + `**RESOLVED 2026-11-14 (mdu-63)**` in the base
  commit (line-9 precedent format; existing notes preserved).
- **Ledger:** no FEATURE_BACKLOG.md row exists for MDU-63 (grep-verified);
  appending a Done-section row at commit is optional bookkeeping, not an AC.

## 10. Acceptance criteria

- **AC-1** — 20261024-1 clause present byte-identical (bullet form, exactly
  once) in all 5 architect carriers.
- **AC-2** — 20261113-1 clause present byte-identical (bullet form, exactly
  once) in all 7 just-code carriers.
- **AC-3** — 20261110-2 clause present byte-identical (two-space indented
  paragraph, exactly once) in all 3 orchestrator mirrors, inside the CACHE
  MISS GATE block after step 3.
- **AC-4** — base pin suite `tests/test_mdu_63_guards.py` green (doc
  consistency, presence + byte full-line, adjacency, fragments, census
  negatives); mutation matrix M1–M7 red as named, /tmp only.
- **AC-5** — overlay pin suite `tests/test_mdu_63_overlay.py` green
  (presence, sibling byte-identity, ordering, built-copy presence after
  `$OVERLAY ./build.sh`).
- **AC-6** — pi goldens refreshed for the six templates per §5;
  `tests/test_mdu_56_pi_port.py` Gates A–E green; `--audit` adds no new
  (construct, profile) pairs; golden file count stays 23.
- **AC-7** — prompt-regression gate exit 0, baseline intact (no baseline
  refresh to force green).
- **AC-8** — base `timeout 300 python3 -m pytest tests/ -q` all green +
  `./build.sh` green; overlay `./build.sh` green + overlay pytest all green.
- **AC-9** — secret gate exit 0 on the base staged diff; secret-scrub
  checklist clean on the overlay diff; `run_ledger.py validate` exit 0 with
  the model field recorded.
- **AC-10** — `$OVERLAY ./deploy.sh --force` + installed-copy verification:
  the three clause markers present (count 1) in the deployed grok, OpenCode,
  and (generated) Claude copies per §8.
- **AC-11** — QA PASS (read-only probes, mdu-60 clause-C discipline); the
  three agent-improvements.md entries flipped RESOLVED (mdu-63); two commits
  + two pushes, base first.
- **AC-12** — apply-now dogfood: the implement brief carries the 20261113-1
  verbatim line; both build exit codes are reported before "done"; review
  round 1's first check is copy freshness.

## 11. Open questions

- **Q-1 (needs the user; default = ship as approved):** the 20261110-2
  spurious-fire carve-out. Log evidence (mdu-56 note): a benign child-wait
  miss (fresh session, next row warm) would fire the clause and force an
  unnecessary fresh-session restart. (a) **Recommended** — ship the approved
  text byte-identical now; treat the carve-out ("pause-class miss on a fresh
  session where the next row is warm") as a measured fast-follow amendment
  if the spurious class appears in the next runs' signal JSON. (b) Amend the
  clause text with the carve-out before implementation — requires a new
  wording approval and breaks byte-identity with the approved draft.
- **Q-2 (veto-only; default = include):** overlay architect variants in the
  carrier set (D-1 ruling 1). Say the word to drop them; the pins sever
  cleanly.

## 12. Commit plan + loop notes

**Base commit** — the 9 base carriers; this design doc (docs/design/ +
mdu-63-definition-guards-batch.md); `tests/test_mdu_63_guards.py`; the six
refreshed golden templates under tests/fixtures/pi_golden/ (prompts/
subdirectory); agent-improvements.md (three RESOLVED flips). If Gate D
surfaced a new parity pair (not expected), docs/pi-parity.md rides the same
commit.

**Overlay commit** — the 6 overlay sources; the regenerated tracked build/
tree; `tests/test_mdu_63_overlay.py`.

**Loop notes:** wording approval = the user's 2026-11-14 apply-path approval
of the three drafted clause texts (single approval; byte-identical
insertion; mdu-47/49/60/62 discipline). No existing test pins the old
wording or the pre-insertion state of any edit region (grep-verified) — all
pins are net-new; no existing suite is edited. The pi golden refresh rides
the same base commit as the source edits (checklist step 4 + the 20261113-1
dogfood). `runs/` stays gitignored (manifest local).
