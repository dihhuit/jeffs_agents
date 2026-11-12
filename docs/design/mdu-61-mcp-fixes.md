# MDU-61 — MCP harness-vs-reality fixes: playwright chromium + blender launcher gating

> Design phase (architect subagent), 2026-11-12. Executes MDU-48's unexecuted
> recommendations S2b + S3 (backlog queue head; mdu-48 evidence commit
> `c3b2d48`). Paths repo-relative, or `$WORKSPACE/<sub>` (base) and
> `$WORKSPACE_OVERLAY/<sub>` (sibling overlay `opencode_agents/`) — never
> literal absolute paths (secret-scan path-lexeme rule, mdu-47 D1e). No config
> or definition edit ships without the D8 approval protocol.

## 0. Surveyed sources

- `runs/mdu-48-sprite-connectivity/manifest.json` + `docs/analysis/mdu-48-connectivity-forensics.md` + `docs/design/mdu-48-sprite-connectivity.md` — S2b/S3 root causes, probe precedent.
- `scripts/probes/mdu48_conn_probe.sh` — existing deterministic env-facts probe (reused as P0).
- `FEATURE_BACKLOG.md` MDU-61 section (~L403-414) — authoritative scope + ACs.
- `$WORKSPACE_OVERLAY/overlays/opencode-mcp.json`, `$WORKSPACE_OVERLAY/scripts/deploy.sh` (MCP registration block), `$WORKSPACE_OVERLAY/scripts/build.sh` (the `--overlay-mcp` merge), `$WORKSPACE_OVERLAY/tests/test_mdu_29_blender_mcp.py` (pins the current UNPINNED playwright args).
- Base carrier trees: `prompts/`, `grok/agents/` (grep-censused for `blender|playwright|mcp`); overlay `grok/agents/` + `overlays/prompts/`.
- `docs/mcp.md` (existing MCP reference — the D4 target; no new file needed), `docs/brief-checklist.md`, `tests/test_mdu_60_qa_write_access.py` (env-gated pin class, 20261112-3), `docs/design/mdu-60-qa-write-access.md` (clause/pin/commit pattern), `.agents/memory/decisions.md` mdu-48/60/61 entries, `scripts/lib/probe_models.py:122-134` (config_sha256 surface), `tests/test_mdu_56_pi_port.py` (golden gates B/C).

## D1. Probe plan (AC-1) — dated re-verification BEFORE any fix

mdu-48 evidence is ~2 weeks old; every root cause is re-proven live before the
fix lands. All probes run in the **devops phase**, plain allowlisted forms,
`timeout`-wrapped, **before** any config/definition edit is applied. Evidence
file: `runs/mdu-61/probe-evidence.md` (gitignored with `/runs/`; the committed
pointer is the dated summary inlined in the MDU manifest — mdu-48 pattern).
Each probe row records: date, exact command, exit code, output excerpt,
expected-vs-observed, verdict.

| # | Probe | Command (plain form) | Expected | Verdict criterion |
| --- | --- | --- | --- | --- |
| P0 | Env re-baseline (mdu-48 facts) | `timeout 60 bash scripts/probes/mdu48_conn_probe.sh` | `APP_RUNNING=no`, `CHROME_PATH_FOUND=no`, `MCP_ARGS=…browser=<absent…>`; `LAUNCHER_COUNT` informational | PASS = the two gap facts re-confirmed. If either flipped (chrome installed / app running), re-rule D2/D3 with the user before editing. |
| P1 | Playwright chrome-channel failure REPRODUCED (expected-FAIL) | `timeout 120 npx -y playwright@latest screenshot --channel chrome about:blank /tmp/opencode/mdu61-chrome-repro.png` | exit ≠ 0; error class **"Chromium distribution 'chrome' is not found"** (the mdu-48 symptom string family) | PROBE PASSES BY FAILING: the exact error class is reproduced on this machine today. If a different error fires, record it verbatim and stop for a re-rule. |
| P2 | One-time bundled-chromium install | `timeout 600 npx -y playwright install chromium` (one-time env step, not a repo edit; 600s because it is a ~150 MB download — a timeout is reported, never retried longer) | exit 0; browser cache populated under `~/.cache/ms-playwright/chromium-*` | PASS = install exit 0 + cache dir listing recorded. |
| P3 | Fix PROVEN with a real headless launch | `timeout 120 npx -y playwright@latest screenshot --browser chromium about:blank /tmp/opencode/mdu61-about-blank.png` | exit 0 + a real PNG (real bundled-chromium launch of `about:blank`) | PASS = exit 0, valid PNG. If `--browser` spelling is rejected by the CLI, use the documented equivalent flag and record it — the criterion is the real launch, not the flag spelling. MCP-level proof (b) below. |
| P4 | Blender launcher-only state REPRODUCED (expected-FAIL) | (1) `timeout 5 pgrep -x blender` → no output/exit 1; (2) `timeout 5 pgrep -fc mcp-for-blender` → ≥ 1 (launcher present); (3) call the blender MCP addon-status tool from the session → error class **"Could not connect to Blender"** | App absent + launcher present + addon error = the harness-"connected"-but-broken state | PROBE PASSES BY FAILING: all three legs recorded. If the user has Blender open, record the positive addon status and cite mdu-48 `c3b2d48` + P0 for the negative branch (contingency, noted in evidence). |
| P5 | Gating DEMONSTRATED | Execute the D3 clause procedure as the devops child would, against the live env: pre-probe `pgrep -x blender` BEFORE any blender-dependent step; app absent → emit the BLOCKED-shaped report (probe named, gap named, no "connected" claim) | The branch taken matches the app state; no launcher-status claim substitutes for the app probe | PASS = drill recorded in evidence: probe ran first, branch = absent-app → BLOCKED-shaped report. This is a synthetic drill (MDU-61 has no live blender dependency); the validate brief also pre-states the probe per the D5 checklist line. |

MCP-level proof of P3 (runs at **validate**, after the approved D2 diff is
built + deployed, per the webapp-verification Playwright recipe): live
`playwright` MCP navigate to `about:blank` (or a `browser.version()`-class
call) through the deployed pinned config. If it cannot run in-loop, P3(a) +
the config-presence pins satisfy AC-2 and the MCP-level check is
BLOCKED-documented with the exact remaining gap.

Probe P3 runs BEFORE the D2 edit lands: it proves `--browser chromium` is a
value the toolchain actually accepts. If the MCP server later rejects it, that
is an env-gap BLOCKED per AC-2's alternative branch — record the exact error,
stop, re-rule (D8).

## D2. Overlay config diff — playwright pinned to bundled chromium

**Diff A (per-diff user approval, D8 — presented before implementation).**
Three sync points, applied atomically (a partial yes would split the harness:
OpenCode pinned, Grok/Claude unpinned):

**A1 — `$WORKSPACE_OVERLAY/overlays/opencode-mcp.json`** (playwright server
only; blender entry unchanged — not reproduced here, see the overlay file):

```json
"playwright": {
  "type": "local",
  "command": [
    "npx",
    "-y",
    "@playwright/mcp@latest",
    "--caps=devtools,network,testing",
    "--browser",
    "chromium"
  ],
  "disabled": false
}
```

Rationale: mdu-48 S2b — `@playwright/mcp` resolves to the **chrome** channel
by default; Google Chrome is absent on this machine (P0/P1), so every launch
fails. `--browser chromium` selects the bundled build that P2/P3 install and
prove. Snap chromium was ruled out by mdu-48 (fragile, not the recommended
target).

**A2 — `$WORKSPACE_OVERLAY/scripts/deploy.sh`** `PLAYWRIGHT_MCP_ARGS` array
(~L327, under the "keep in sync with overlays/opencode-mcp.json" comment):
append the two tokens `"--browser" "chromium"`. All registration paths
(`configure_grok_mcp`, `configure_claude_mcp`, dry-run echoes, the
not-installed hints) consume the array and follow automatically — EXCEPT:

**A3 — hardcoded Claude fallback (~L374)**: the no-`--` retry line spells the
playwright args out literally; it must gain the same two tokens or Claude Code
gets registered unpinned when the primary form fails.

**One-time install step (documented, not a repo diff):** P2's
`npx -y playwright install chromium`, run once per machine. Documented in:

- **docs**: `docs/mcp.md` Playwright-details bullet (D4) names the command and
  the symptom it prevents.
- **deploy check**: new warn-level `check_playwright_chromium()` in overlay
  `deploy.sh`, invoked before MCP registration in both dry-run and `--force`:
  if no `~/.cache/ms-playwright/chromium-*` dir exists, `log_warn` with the
  exact fix command (`npx -y playwright install chromium`). Warn, not
  hard-fail — the deploy must not brick on a fresh machine; the warning makes
  the gap visible with its fix (consistent with base deploy warn-only
  conventions).

`probe_models --refresh` is **not** needed: MDU-61 changes no agent, model, or
registry row, and `config_sha256` hashes only sorted `agent=model` pairs
(`scripts/lib/probe_models.py:122-134`); MCP server args live in the `mcp`
section, outside the hashed surface (`opencode-mcp.json` merges into
`build/opencode.json` via overlay `build.sh` `--overlay-mcp`, after the agent
map). Verified at design time.

## D3. Blender gating clause — byte-identical, 11 carriers

**Carrier census (grep-verified, not hand-counted).** Blender is mentioned by
ZERO base prompt/grok files today (it is an overlay-only MCP server); the
Playwright-or-BLOCKED discipline lives in the qa bodies. MDU-61 adds the
blender sibling of that discipline to every carrier that can execute or
verify a blender-dependent step. `prompts/qa.md` serves the OpenCode
`qa`+`qa-pro` agents (opencode.json:1762/2100) and `prompts/devops.md` serves
`devops`+`devops-pro` (:1625/1694); `-pro` OpenCode agents have no separate
prompt body, Grok `-pro` variants are separate profiles.

**Base carriers (6):**

| Carrier | Family | Placement |
| --- | --- | --- |
| `prompts/qa.md` | qa | new column-0 bullet, blank-line separated, immediately after the Playwright BLOCKED block's last bullet (`- Still run non-browser checks you can (HTTP/API, CLI, logs) and list what browser coverage was blocked.`) |
| `grok/agents/qa.md` | qa | same anchor, same shape |
| `grok/agents/qa-pro.md` | qa | same anchor, same shape |
| `prompts/devops.md` | devops | appended as the LAST bullet of the `Hard constraints:` list (after the systematic-debugging bullet) |
| `grok/agents/devops.md` | devops | last bullet of `Hard constraints:` |
| `grok/agents/devops-pro.md` | devops | last bullet of `Hard constraints:` |

**Overlay carriers (5, personal — edited directly, not via snippets; the
overlay build inherits the base copies automatically for same-named agents,
but these are root-added personal profiles / a full-file override):**

| Carrier | Family | Placement |
| --- | --- | --- |
| `overlays/prompts/qa.md` (full-file override — authoritative body) | qa | after the same long anchor bullet as base |
| `grok/agents/grok-qa.md` | qa | its anchor bullet is the SHORT variant (`- Still run non-browser checks you can and list what browser coverage was blocked.`) |
| `grok/agents/grok-qa-pro.md` | qa | long anchor variant |
| `grok/agents/grok-devops.md` | devops | last bullet of `Hard constraints:` |
| `grok/agents/grok-devops-pro.md` | devops | last bullet of `Hard constraints:` |

**Orchestrator mirrors are NOT carriers (verified):** `prompts/orchestrator.md`
carries no MCP mention (grep-censused); the backlog scope is devops/qa mirrors
+ checklist; the orchestrator's role is brief-writing, covered by the D5
checklist lines. MDU-60's orchestrator clause was orchestrator-addressed
behavior; this clause is executor-addressed (qa/devops).

**Clause text — byte-identical across all 11 carriers (the test constant
holds this verbatim minus the emitted `- ` lead; blank-line separation is
placement, not clause bytes):**

```text
- **App-backed MCP gating (Blender):** Before any blender-dependent step (tool
  call, verification item, deploy check), probe the application first:
  `pgrep -x blender` must show the Blender app running with the
  `mcp-for-blender` addon enabled. A running `mcp-for-blender` server process
  alone is launcher-level only and is NOT sufficient — a harness "connected"
  status reports the launcher, not the application. If the app is absent,
  immediately report a BLOCKED status (distinct from PASS/FAIL) naming the
  probe, what failed, and that Blender must be running with the addon
  enabled — mirroring the Playwright-or-BLOCKED discipline; never report
  blender as "connected" from launcher status alone. The same app-vs-launcher
  rule applies to any MCP server that fronts a running application.
```

Rationale: generic behavior (harness "connected" is launcher-level; gate
app-backed MCP on an app probe) ships in the base with Blender as the named
instance — the same publishability precedent as the Playwright-or-BLOCKED
discipline (Playwright MCP registration is also overlay-personal config, yet
its discipline lives in base qa bodies). The clause is inert for users
without a blender MCP (no blender-dependent step → nothing to gate).

**Golden regeneration (mdu-60 Q1 precedent, now mandatory):** the pi-port
golden (`tests/fixtures/pi_golden/`) derives byte-verbatim from the base Grok
profiles and is enforced by gates B/C (`tests/test_mdu_56_pi_port.py`).
Editing 4 base Grok profiles drifts 4 golden templates — regenerate
`tests/fixtures/pi_golden/prompts/{qa,qa-pro,devops,devops-pro}.md` via the
mdu-56 generator in the same base commit. (mdu-60 already regenerated
`orchestrator.md` this way — golden L171 carries the shipped clause.)

**agent-improvements entry:** new id `20261112-4` (grep-free check before
insertion — 20261104-1 discipline; `20261112-3` is taken, `20261112-1`
dangling), kind `env_gap`, opened `[x]` resolved-by-shipping if the clause
lands in-MDU, else `[ ]` open with the clause text recorded as the named
resolution (D8 branch 2).

## D4. docs/mcp.md reference note (base doc — exists, no new file)

Three edits to `docs/mcp.md`:

1. **Playwright details section** — new bullet after the caps bullet:
   ```text
   - **Browser channel:** the server defaults to the **chrome** channel and
     expects Google Chrome at its system path (Linux:
     `/opt/google/chrome/chrome`). On a machine without it, every launch fails
     with `Chromium distribution 'chrome' is not found`. Fix: pass
     `--browser chromium` (the bundled build) and run the one-time
     `npx -y playwright install chromium` (mdu-48 S2b, executed by MDU-61);
     this machine's overlay config pins `--browser chromium`.
   ```
2. **"harness default on this machine" sentence (~L49-50)** — updated to end
   `--caps=devtools,network,testing --browser chromium` with a pointer to the
   channel bullet.
3. **Degradation contract section** — new subsection before `## Security`:
   ```text
   ### App-backed servers: "connected" is launcher-level

   A harness "connected" status for an MCP server verifies the server process
   (launcher), not the application the server fronts. For app-backed servers,
   the application must be running and its addon/socket enabled before any
   dependent step: probe the app with `pgrep -x blender` (Blender via
   `mcp-for-blender`); count launcher processes separately with
   `pgrep -fc mcp-for-blender` — idle launcher pairs are a leak signal (mdu-48
   observed 13 stale pairs), and a live launcher with no app still answers
   "Could not connect to Blender". Absent application → report BLOCKED
   (distinct from PASS/FAIL) naming the probe; never report the server as
   "connected" from launcher status alone (qa/devops gating clause, MDU-61).
   ```

The per-agent scoping table is untouched (blender is not a base server).

## D5. docs/brief-checklist.md lines

One line, byte-identical in two sections (the orchestrator's dispatch-time
mirror of D3; the same discipline read at brief-writing time):

```text
- Pre-state the app probe before any blender-dependent step (`pgrep -x blender`; a running mcp-for-blender server process is launcher-level only); absent app → the child reports BLOCKED, never "connected". [20261112-4]
```

- `## devops` — appended as the section's last line.
- `## qa` — inserted immediately after the `[20261110-1]` pre-state line
  (adjacency mirrors the mdu-60 checklist pin style).

## D6. Pin / test plan

**Base — `tests/test_mdu_61_mcp_fixes.py`** (mdu-49/60 conventions: constants
are the byte-identity authority; every pin asserts TEXT, never file counts;
`MDU61_TEST_ROOT` moves the clause-file root for the mutation matrix while
overlay pins always read the real sibling):

- Constants: `CLAUSE_20261112_4` (D3 blockquote minus `- ` lead),
  `EMITTED_CLAUSE`, `CHECKLIST_LINE` (D5), the two qa anchor bullet variants,
  `Hard constraints:` heading, docs distinctive terms.
- Presence exactly once per base carrier (6 cases) + block byte-match.
- Cross-carrier sha256 equality across all base carriers (and overlay
  carriers when live-present).
- Adjacency: qa family — clause preceded (one blank line) by one of the two
  anchor bullets; devops family — clause is the LAST bullet of the
  `Hard constraints:` block (line after the clause block is not a `- ` line).
- Checklist: line exactly once in `## devops` and once in `## qa`; `## qa`
  copy sits after the `[20261110-1]` line.
- Docs pins (3): `Chromium distribution 'chrome' is not found` present in
  `docs/mcp.md`; `pgrep -x blender` present in `docs/mcp.md`; `--browser
  chromium` appears ≥ 2 times (details bullet + default sentence).
- Golden pins (4): each regenerated golden template carries `EMITTED_CLAUSE`
  exactly once (gate B enforces byte-fidelity vs the Grok sources; these pins
  make the MDU-61 link explicit).
- Census: `App-backed MCP gating` matches ONLY the 6 base carriers across
  `prompts/*.md` + `grok/agents/*.md` (no strays — this is also the negative
  boundary vs orchestrator/just-code/code-reviewer/test-agent bodies).
- Mutation matrix: `MDU61_TEST_ROOT` → /tmp copy, one carrier stripped at a
  time → each presence/sha/adjacency pin fails as designed (~6 cases).
- **Overlay carriers (5) — the 20261112-3 env-gated pin class** (exactly
  `test_mdu_60_qa_write_access.py` §9): the gate is derived from LIVE sibling
  content, not operator action — sibling absent → skip (standalone base
  clone); sibling present, clause absent → skip with a reason naming the
  pending overlay step (strict pins flip on automatically when the overlay
  commit lands, no human step); sibling present, clause present → strict pins
  (exactly once per overlay carrier + sha equality across all 11).
  `MDU61_OVERLAY_SHIPPED=1` is an optional force flag that only asserts and
  cannot fake green.
- **Deferral variant (D8 branch 2):** if the user defers the clause to the
  apply path, the BASE presence/adjacency pins take the same live-content
  gate (skip naming the pending apply-path step; auto-flip strict when it
  lands). Primary spec is strict (branch 1, mdu-60 carve-out); the fallback is
  a one-constant change documented here so just-code does not re-design.
- Prompt-regression gate (REQUIRED — prompts touched):
  `timeout 60 python3 scripts/lib/prompt_regression.py gate`, expect the
  unchanged baseline (procedural clause, not exercised by golden cases); if
  red, follow the gate's own drift protocol with rationale.

**Overlay — `tests/test_mdu_61_mcp_config.py`** (runs after `./build.sh` so
`build/opencode.json` is refreshed):

- `overlays/opencode-mcp.json` parses; playwright `command` == the exact
  6-token sequence `["npx","-y","@playwright/mcp@latest",
  "--caps=devtools,network,testing","--browser","chromium"]` (exact order —
  non-vacuous).
- `build/opencode.json` playwright `command` == the same 6 tokens (proves the
  `--overlay-mcp` merge carried the pin into the deployable config).
- Blender entry unchanged in both files (2-token command, `disabled: false`).
- `scripts/deploy.sh`: `PLAYWRIGHT_MCP_ARGS` carries the two new tokens in
  order; the hardcoded Claude fallback line carries them too (no unpinned
  fallback path left); `check_playwright_chromium` exists and its warn text
  contains `npx -y playwright install chromium`.
- **Update `tests/test_mdu_29_blender_mcp.py`** in the same commit: its
  `PLAYWRIGHT_CMD` constant (currently the 5-token unpinned list, asserted by
  `test_playwright_entry_unchanged` over both config files) gains the two
  tokens — otherwise the overlay suite reds on the D2 edit. The new file adds
  a meta-pin that the constant block contains both tokens (guards a silent
  revert). Verified: no other test in either repo pins the playwright command
  (grep-censused).
- **Refusal branch (D8, Diff A refused):** the config pins invert — assert
  `--browser` ABSENT from config + deploy.sh, AND the `docs/mcp.md` env-gap
  documentation present — so any later silent pin/unpin drifts red. Only the
  ruled branch ships.

## D7. Cross-repo commit order (both builds green; two commits, two pushes)

1. **Base commit FIRST** (after probes P0-P5 recorded + D8 rulings):
   clause ×6 base carriers; regenerate the 4 golden templates; 2 checklist
   lines; `docs/mcp.md` ×3 edits; agent-improvements `20261112-4`;
   `tests/test_mdu_61_mcp_fixes.py`; backlog MDU-61 status → Done (rewrite the
   `(queue head)` heading per the mdu-57/58 discipline; MDU-59 becomes the
   next queue head). Gates: `./build.sh`;
   `timeout 120 python3 -m pytest -q`;
   `timeout 60 python3 scripts/lib/prompt_regression.py gate`;
   base `secret_scan` on staged paths at commit. Commit + push base
   (`jeffs_agents`).
2. **Overlay commit SECOND** (never `git add -A`; build/ is tracked):
   Diff A (A1+A2+A3 + `check_playwright_chromium`) as approved;
   `test_mdu_29_blender_mcp.py` constant update; new
   `tests/test_mdu_61_mcp_config.py`; Diff B overlay carriers (clause ×5) if
   ruled in-MDU. Then `./build.sh` (re-runs the base build — inherits the
   base clause into same-named build copies — and re-merges the pinned MCP
   config into `build/opencode.json`); overlay pytest green; **manual
   secret-scrub checklist** (the overlay repo has no local secret_scan.py —
   mdu-43 precedent). Commit + push overlay (`opencode_agents`).
3. **Post-overlay verification:** re-run the base suite once from the base
   repo — the env-gated overlay pins have auto-flipped strict; show them
   green (no stale-skip state left behind).
4. **Deploy:** unlike MDU-60 (deploy-time refresh only), MDU-61's deliverable
   IS the live config — the deploy phase runs overlay `./deploy.sh` (dry-run)
   then `--force` under the Diff A approval, and verifies `grok mcp list` /
   `claude mcp list` show the pinned args. The one-time P2 install precedes
   it so the post-deploy MCP-level P3(b) proof can run.

Order rationale: the overlay build re-runs the base build, so the base must
be committed first for the overlay build to inherit the clause; the base
suite's overlay pins skip (naming the pending overlay step) at base-commit
time and flip strict only after the overlay edit lands.

## D8. Approval-gate protocol (per the resume-block structure)

The orchestrator presents diffs to the user BEFORE implementation — never
bundled into one approval (different repos, different gates):

- **Diff A (overlay MCP config — per-diff approval, each edit shown as a
  diff):** one atomic approval covering A1 (config JSON), A2+A3 (deploy.sh
  sync points + the new check function), the `test_mdu_29` constant update,
  the one-time install command (P2), and the deploy that carries it. Atomic
  because a partial yes leaves the "keep in sync" contract broken mid-state.
  On approval → implement per D7. **On refusal:** no config edit ships;
  record the ruling (manifest + a decisions.md entry); AC-2 is met through
  its BLOCKED alternative — `docs/mcp.md` documents the exact env gap + fix
  command, P1-P3 evidence documents the working CLI-level chromium path, and
  the overlay config pins assert the refused state (D6 refusal branch). No
  re-ask within this MDU; a future MDU may re-propose.
- **Diff B (definition clause — the definition path):** the D3 blockquote +
  11-carrier table + golden regen + checklist lines. The user rules:
  (1) **pre-approve in-MDU** (the mdu-60 carve-out — clause lands directly
  after review sign-off; strict base pins), or (2) **defer to the
  user-invoked `apply the definition diffs` path** (carriers untouched this
  MDU; pins ship live-gated per 20261112-3 and auto-flip when the apply path
  lands it; checklist/docs/tests still land now; `20261112-4` stays `[ ]`
  open). "start now"/"looks good" are not consent for branch (1) — only an
  explicit ruling is.
- **Docs, probes, tests, backlog status** (`docs/mcp.md`,
  `docs/brief-checklist.md`, probe evidence, both test files, golden regen):
  normal MDU review + QA flow — no per-diff user gate (they are not
  config/permission/definition files).

## Risks / gotchas

- **Secret-scan path-lexeme trap:** long absolute-path tokens red the
  high-entropy rule — write paths repo-relative or `$WORKSPACE` /
  `$WORKSPACE_OVERLAY`-notation; split long paths at slashes in prose. The
  blender server's absolute launcher path is intentionally NOT reproduced in
  this base-repo doc (it lives in overlay config/tests only). Known related
  traps: short-sha + slash-split camelCase in prose (mdu-56).
- **Overlay secret gate:** no `scripts/lib/secret_scan.py` in the overlay —
  run the manual secret-scrub checklist for the overlay commit (mdu-43
  precedent). Diff A touches configs + deploy.sh: no secrets expected, still
  check.
- **`probe_models --refresh` NOT needed:** no registry/agent/model change;
  `config_sha256` hashes only `agent=model` pairs — MCP args are outside the
  hashed surface and `opencode-mcp.json` merges after the agent map. A
  refresh would be a pointless drift risk.
- **Prompt-regression gate REQUIRED** (base `prompts/qa.md` + `prompts/devops.md`
  touched; overlay `overlays/prompts/qa.md` if Diff B lands): expect unchanged
  baseline; follow the gate's drift protocol if red.
- **pi_golden drift is real this time:** 4 golden templates MUST be
  regenerated in the base commit (mdu-60 precedent); gates B/C enforce
  byte-fidelity — forgetting reds the suite.
- **deploy.sh sync surface is 3 points** (A1/A2/A3): partial sync = split-brain
  harness state (OpenCode pinned, Grok/Claude unpinned).
- **`test_mdu_29_blender_mcp.py` pins the OLD args** — update its constant in
  the same overlay commit or the suite reds.
- **grok-qa.md anchor is the SHORT bullet variant** — adjacency pins must
  accept both anchor strings.
- **P4 needs the Blender app DOWN** (the normal state per mdu-48: 0 app
  processes). If it is up, record the positive branch and cite mdu-48
  `c3b2d48` + P0 for the negative branch.
- **`--browser chromium` validity is proven by P3 before the config lands**;
  a rejection = env-gap BLOCKED (AC-2 alternative), stop and re-rule.
- **`/runs/` is gitignored** — probe evidence stays local; the manifest
  carries the dated summary (mdu-48 pattern: "evidence inline in manifest").
- **`20261112-4` must be grepped free before insertion** (20261104-1; 20261112-3
  is taken, 20261112-1 is a dangling reference).
- **Chromium install is per-machine:** other machines need the same one-time
  step after pull — that is exactly what the deploy check + docs bullet make
  visible.

## Open questions

- **Q1:** does any overlay prompt-regression baseline hash
  `overlays/prompts/qa.md` (see `tests/test_mdu_09_overlay_prompt_regression.py`)?
  Implementer: run the overlay suite after the Diff B fold; if mdu-09 reds,
  follow the base drift protocol and record which cases.
- **Q2:** the exact rendered sentence for the `docs/mcp.md` L49-50 default
  update — keep the existing machine-specific phrasing pattern; grep the
  sentence and edit in place (do not restructure the paragraph).
- **Q3:** confirm `check_playwright_chromium` placement in the deploy flow
  (before `configure_grok_mcp`/`configure_claude_mcp`, after CLI detection)
  so the dry-run path prints it too.

## Loop notes

- Agents (backlog suggestion): devops (P0-P5 probes + Diff A + deploy),
  just-code (Diff B clause/checklist/docs/golden + tests), test-agent (pins),
  qa (validation incl. the MCP-level P3(b) Playwright check, probes pre-stated
  per 20261110-1). Design = this doc (architect).
- Probes run BEFORE any edit (AC-1 ordering); every probe verdict lands in
  `runs/mdu-61/probe-evidence.md` + the manifest summary.
- Scope boundary: no QA permission change (MDU-60 territory), no
  orchestrator-mirror edit (verified non-carrier), no registry/model change,
  no blender-config change (the blender MCP entry itself is untouched — only
  its gating discipline ships).
