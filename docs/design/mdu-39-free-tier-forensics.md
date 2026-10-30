# MDU-39 — Free-tier cap forensics & symptom-attribution ledger (design)

- Date: 2026-10-29 (all timestamps UTC)
- Status: complete — the 2026-10-30 LIVE PROBE results have landed and are reflected below (§4, §8); the citable registry table lives in `docs/` `model-registry.md` under "Free-tier caps"
- Sources of record: `runs/mdu-39-cap-forensics/` `evidence.md` (storage sweep, ground truth for every verbatim string below) and the seed file `mdu-42-deploy-evidence.md` under `/tmp/opencode/`
- Style note (repo rule): long slash-heavy path lexemes are split across inline-code spans so the
  commit-time secret scanner does not trip on ≥32-char `/`-joined runs. Bear with the spacing.

## 1. Purpose & scope

MDU-39 produces a citable ledger of what the OpenCode free tier does when its usage cap
is hit: the exact refusal payload, which models refuse, when, and — critically — which of
our runs died of it and why (symptom attribution). It is the quality-gate input for
MDU-40 (free-exempt routing decision) and MDU-41 (fallback ladder); it designs neither.

Scope: OpenCode free-tier models (`opencode/*` free ids) only.
`xai/*` is paid and credentials-exempt per the MDU-42 hard rule
("grok-named agents on xai/*"); it has no cap class and is out of scope.
OpenCode Go / opencode-go paid models are out of scope except as fallback context.

## 2. Cap shape — what is known, what is unknown

### 2.1 Known (labeled by evidential class)

| Fact | Class | Guardrail on the number |
| --- | --- | --- |
| Refusal is a 429 error object, `type: provider.quota`, provider body `FreeUsageLimitError` | **live-probed** (68 DB rows, deploy gate) | stable, per-row facts |
| Error is per-account, server-enforced, daily-resetting; reset clock shown in the error | **official** (maintainer statements) | no cap size attached |
| One official figure existed: "200 requests a day", on the Go-page FAQ until 2026-10-22, then removed without replacement | **official-but-retracted** | treat as stale, not current |
| Cap is shared across all free models on the account | **community-observed** (thread #59387 wave) | not verified by us; consistent with our data |
| Severe tightening window ~2026-10-22→25: first-request lockouts, non-resetting countdowns | **community-observed** | characterize, do not quantify |
| Cap undocumented in published docs as of 2026-10-29 | **research finding** | re-check each MDU |
| Go plans: $10/mo (Go), $40 (Plus), $20/member (Teams); rolling-window quotas (20% per 5 h, 50% per week, 100% per month); Go docs state limits are monthly dollar amounts (GLM-5.3-Flash $60/mo on Go) | **official** | paid side; context only |

### 2.2 Unknown — and design stance

- Cap size (the retracted 200/day may or may not still be the real size).
- Reset hour and timezone — the reset clock is per-user relative, not a fixed wall-clock hour.
- Per-network vs per-device vs per-IP exposure — DB cannot distinguish; only account identity is recoverable.

**Standing statement (acceptance criterion 3):** OpenCode free-tier caps are
**undocumented and unstable** as of 2026-10-29. No cap number, window, or reset hour in
this repo may be cited as official; anything numeric is `live-probe`,
`official-but-retracted`, or `community-observed` and must carry that label. Downstream
routers (MDU-40/41) must assume the cap can move under us at any deploy without notice.

## 3. Refusal strings — verbatim

Two wordings of one error, `FreeUsageLimitError`, both carried in a `provider.quota`
error object with `status: 429`. These are the only two free-cap refusal wordings in the
DB; nothing else exists.

Canonical (60 of 68 rows; spans 2026-10-28 through last hit 2026-10-29 13:12:49Z):

```json
"error": {"type": "provider.quota", "message": "Free usage limit reached. Free models work in OpenCode (https://opencode.ai); subscribe to OpenCode Go to keep going: https://opencode.ai/go", "status": 429, "response": {"body": "{\"type\":\"error\",\"error\":{\"type\":\"FreeUsageLimitError\",\"message\":\"Free usage limit reached. Free models work in OpenCode (https://opencode.ai); subscribe to OpenCode Go to keep going: https://opencode.ai/go\"}}"}}
```

Old wording (8 of 68 rows; first era 2026-10-24; last seen 2026-10-29 13:12:49Z in a
same-day straddle with canonical — both epochs alive the day the wording flipped):

```json
"error": {"type": "provider.quota", "message": "Free usage limit reached. Subscribe to OpenCode Go to keep going: https://opencode.ai/go", "status": 429, "response": {"body": "{\"type\":\"error\",\"error\":{\"type\":\"FreeUsageLimitError\",\"message\":\"Free usage limit reached. Subscribe to OpenCode Go to keep going: https://opencode.ai/go\"}}"}}
```

The matching `idle` row carries the same body plus `"outcome": "failed"` — a turn that
ended in a refusal is therefore independently countable, not just the assistant row.

Row census (from the discriminating check — error rows with `"status": 429`):

| timing (UTC) | rows | wording |
| --- | --- | --- |
| 2026-09-28 → 2026-10-23 | 0 | — (free-cap era not started) |
| 2026-10-24 | 8 | old |
| 2026-10-28 | 8 | canonical |
| 2026-10-29 (last error row 13:12:49Z) | 52 | canonical |
| 2026-10-30 (last seen 02:57Z) | 0 error rows (text refs remain) | — |

## 4. Affected models

Three distinct roles must not be conflated:

**(a) Models that returned the refusal** (deploy evidence 2026-10-29, 2 probe attempts each, verbatim string above):
`big-pickle`, `deepseek-v4.1-flash-free`, `mimo-v2.6-flash-free`,
`nemotron-3.5-super-vl-free`. The sweep's 16-session probe burst (2026-10-29 14:32Z)
reinforces it: 4 sessions × 4 of these models. Note `deepseek-v4.1-flash-free` and
`nemotron-3.5-super-vl-free` are older zen map slots, not present in the deployed config.

**(b) The one free model that probed OK** the same day: `nemotron-3.5-lightning-free`
(also `beam-free`, `flint-40b-free` as probed alternates, per deploy Step 3). But —
**all 34 real-work death rows went through big-pickle exclusively**, never a
`-free`-named model.

**(c) Why (b) is not exemption evidence:** the research finding — the quota is
**account-shared across all free models** — means a model probing OK one day is a
statement about the account's remaining headroom at probe time, not about the model.
The registry table must not encode "lightning is exempt" from a single OK probe.
This was confirmed live: **2026-10-30 ~02:57 UTC, all four refused-until-now models**
(`big-pickle`, `mimo-v2.6-flash-free`, `nemotron-3.5-lightning-free`,
`deepseek-v4.1-flash-free`) **returned exact-OK** from
`opencode run -m <model> "Reply with exactly: OK"` (exit 0 each) — the daily reset
came back through for the whole free family at once, so the reset is account-shared,
not per-model. The citable table lives in `docs/` `model-registry.md` under
"Free-tier caps (2026-10-29)" (see §8).

## 5. Symptom attribution (acceptance criterion 2)

### 5.1 The reported mmo event — pinned in one DB row

- Project: `/mnt/FastSSDXFS/projects/mmo` (project id as hashed in `evidence.md` §2).
- Parent: grokestrator session `ses_e783c1acdffeXWboGB1BczHIZf` ("mdu-113 bridge rework"),
  on `xai/grok-4.7` — itself not cap-exposed.
- Child: `ses_e783552c9ffeA7cEUeqnlps1gA`, agent `grok-architect`, model
  `opencode/big-pickle`, died **2026-10-29 13:12:49Z** with the canonical refusal
  (`finish: "error"`; closing `idle` row carries `"outcome": "failed"`).
- Twin: `ses_e7835caf8ffePZlc0DNhqk8X0t` (agent `architect`, same brief) died 24 s earlier,
  13:12:25Z, same error. Dispatcher retried zen→zen→xai within 74 s.
- Resolution: grokestrator re-spawned the identical task at 13:13:23Z and it ran on
  `xai/grok-4.7` (`ses_e7834ce8affe3t1rt8J59ytep1`); all 16 follow-up children
  (13:13–14:03) completed on xAI with zero further cap errors. **The day shipped** — the
  diagnosis is degradation-with-fallback, not outage. [inferred: MDU-42 deploy had landed]

### 5.2 Earlier mmo cap events (2026-10-24, first wall)

- `devops-free` on big-pickle, 17:59:25Z (old wording); parent "mdu-109 vertical
  connectors"; retried 56 s later as paid `devops` → `opencode-go/mimo-v2.5` — success.
- `just-code-free` on big-pickle, 18:06:53Z (old wording); retried 9 s later as
  `just-code` → `opencode-go/deepseek-v4.1-flash` — success.

### 5.3 Root-cause chain

The zen tier concentrates **19 of 50 agents** on `big-pickle` (§6), and the cap is
account-shared, so every zen child call draws from one pool. Coordinator-heavy phases
(design/implement loops spawning architect + coder children) are the highest-rate
consumers; when the pool empties, deaths first appear exactly where concurrency ×
per-call cost is highest — the architect/grok-architect children of a
grokestrator/orchestrator parent. The 2026-10-29 event (two children failing within
24 s at 13:12) matches a drained-account state, not a per-model outage: the same
account had been probing/quota-refused since 10-24 and canonical-era rows filled
10-28→10-29.

## 6. Per-agent audit & current zen free-routing table

From the affected-session ledger (68 free-cap error rows; **34 assistant error rows,
33 sessions** carry an `agent` field — real-agent rows; the other 34 are 2026-10-29
deploy-gate probe/cli rows with no `agent` field; drops: `/agents` 23 rows,
`sprite_generator` 7, `mmo` 4). Agents affected, 8 classes, their row counts, and
models — **all 34 agent rows on `opencode/big-pickle`**:

| agent | error rows | note |
| --- | --- | --- |
| orchestrator | 18 | MDU-32 cost-audit 10-24 (old wording) + coordinator hot path |
| just-code | 5 | — |
| just-code-mid | 4 | sprite ×2, MDU-42 edits ×2 |
| qa-free | 1 | QA smoke, mdu-37 deploy |
| just-code-free | 2 | mmo 10-24 + sprite 10-29 |
| architect | 2 | sprite 10-28, mmo mdu-113 twin 13:12:25Z |
| grok-architect | 1 | the reported event |
| devops-free | 1 | mmo 10-24 |

Current deployed zen config (50 agents, post-MDU-42; cross-checked identical between
base build and overlay build):

| model | role | agents | count |
| --- | --- | --- | --- |
| big-pickle | free, **capped** | architect, architect-premium, code-reviewer-free, code-reviewer-pro, devops-free, devops-pro, inception, just-code, just-code-free, just-code-mid, just-code-pro, mdu-code, orchestrator, qa-free, qa-pro, test-agent, test-agent-free, test-agent-pro, ui-ux-designer-pro | **19** |
| mimo-v2.6-flash-free | free, refused at probe | research | **1** |
| nemotron-3.5-lightning-free | free, probed OK (not exempt) | code-reviewer, deep-research, deepseek-research, devops, introspector, nemotron-research, qa, test-agent-mid, ui-ux-designer | **9** |
| xai/grok-4.7 | paid, exempt | 13 incl. grokestrator, thought-leadership-coach | **13** |
| xai/grok-build-0.1 | paid, exempt | 8 | **8** |

**~60% of the zen tier still routes to the capped model** — unchanged since MDU-42
(zero config change since deploy). That residual is MDU-40 scope, recorded here as a
ledger fact only.

## 7. Consequences for MDU-40 / MDU-41 (inputs only — no design here)

- **MDU-40 (free-exempt decision):** needs **per-phase economics, not per-agent**. Even
  with 19 agents on big-pickle, real deaths clustered on the coordinator/architect/coder
  hot path (orchestrator, architect/grok-architect, just-code*) — surfacing is driven by
  call rate × cost of owned phases, not by the number of agents mapped to a model. Any
  "exempt this agent" framing will mis-target; frame as "exempt this phase's calls".
- **MDU-41 (fallback ladder):** must treat **"lights on" independent of "work goes"**.
  The 10-24 and 10-29 events both show the account can be refuse-everything while
  paid/xAI paths run fine; a ladder that only checks "does the model answer a probe"
  will report green while real children die. The Nemotron-OK-probe result must not be
  readable as "free tier alive" while the account cap is the binding constraint.
- Standing hazard: the cap is undocumented and unstable (§2.2) — both decisions must
  survive a silent cap change (new size, new hour, new error wording) without code edits.

## 8. Evidence register

- Storage sweep (read-only, `mode=ro`, no checkpoint): `runs/mdu-39-cap-forensics/`
  `evidence.md` — 68 `status:429` rows (60 canonical + 8 old), 33 sessions, census table,
  pinned rows §2, per-agent audit §3, zen config audit §4.
- Seed evidence: `mdu-42-deploy-evidence.md` under `/tmp/opencode/` — the four refused
  model ids verbatim on 2026-10-29 (Step 3), Nemotron OK same day, xAI probe 2/2 OK.
- Probe commands referenced by the sweep: full scans of every `session_message.data`
  row for refusal substrings, filtered to error objects with `"status": 429`
  (both `message` and legacy `part` show 0 free-cap rows); plus the deploy-time
  `probe_models.py --refresh --gate --include-xai` gate and the live
  `opencode run -m xai/grok-4.7 "Reply with exactly: OK"` probe (exit 0).
- 2026-10-30 live probe (~02:57 UTC, log at `/tmp/opencode/` + `mdu39-probes-20261030.log`):
  `opencode run -m <model> "Reply with exactly: OK"` on all four refused models —
  exit 0, stdout ends with a line `OK` exactly, for `opencode/big-pickle`,
  `mimo-v2.6-flash-free`, `nemotron-3.5-lightning-free`, `deepseek-v4.1-flash-free`.
  Interpretation: the account-shared free quota reset across the 2026-10-29→30 UTC
  boundary (last fatal block-mode storage row 2026-10-29 13:12:49Z; refusal persisted
  through the 2026-10-29 probe gate; all four probed OK together the next morning UTC).
  The registry table landed in `docs/` `model-registry.md` under
  "Free-tier caps (2026-10-29)" — no longer pending.
