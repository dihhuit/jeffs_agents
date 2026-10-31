# MDU-48 — Sprite connectivity forensics: design

> Erratum (2026-10-31, post-review): the early-evidence line "`pgrep -af blender` empty" is stale —
> the corrected reading (see the forensics doc) is app-vs-launcher: `pgrep -x blender` → 0 app
> processes; 26 launcher processes (13 idle `uvx mcp-for-blender` pairs) match the fuzzy pattern. Design intent
> unchanged; the launcher accumulation became its own S3 recommendation.

## Symptom → early evidence (gathered live 2026-10-31, orchestrator session)

Triggers recorded in the store: session `ses_e6d1ac9c…` "M9 blind review — reviewer B" ran as
agent = **qa** (mimo-v2.6-flash). All three symptoms:

| # | Symptom | Live evidence already gathered |
| --- | --- | --- |
| 1 | `shell` "Permission denied: shell" x3 | qa agents are read-only BY DESIGN (deployed config qa block + the closed 20261018-1 / 20261021-8 class). Verify the qa block. |
| 2 | Playwright "Chromium distribution 'chrome' is not found at /opt/google/chrome/chrome" | REPRODUCED in orchestrator session via `browser_navigate` — machine-wide, not sprite-specific. No Google Chrome installed: only `/snap/bin/chromium`, `/usr/bin/chromium-browser`. Server args: `npx -y @playwright/mcp@latest --caps=devtools,network,testing`; `--browser` possible values chrome/firefox/webkit/msedge; chrome is the default channel. |
| 3 | Blender "Could not connect to Blender" despite harness "connected" | REPRODUCED in orchestrator session via `get_addon_status` — same error. `pgrep -af blender` empty: the Blender app + addon server is simply not running. The harness "connected" status = the `uvx mcp-for-blender` LAUNCHER process, not the addon socket. |

## Deliverable

One findings doc: `docs/analysis/mdu-48-connectivity-forensics.md` (masked: no session-file bodies;
per mdu-35 masking discipline). Sections:

1. Per-symptom root cause, each with: evidence lines (DB query fingerprints + config line refs +
   probe outputs), and the blame class: (1) by-design sandbox + task-paper mismatch (same class as
   20261021-9/20261021-8 — a review/QA child asked to WRITE files), (2) machine env gap (Chrome not
   installed) + channel default, (3) launcher-vs-addon status semantics (expected behavior of
   mcp-for-blender, Harness reporting is process-level).
2. Recommended fix per symptom (RECOMMENDATION ONLY — config edits need per-diff user approval):
   - S1: route file-writing/screenshot steps to an execution-capable agent; pre-scope denials
     in child briefs (the MDU-47-clause now shipping covers the reviewer/QA side).
   - S2 (pick one, user rules): `a` install Google Chrome stable (`npx playwright install chrome`
     per the error text), or `b` add `--browser chromium` + a one-time `npx playwright install
     chromium` to the overlay MCP entry (bundled browser, no system install). Snap chromium is
     KNOWN-fragile under playwright (confinement) — NOT recommended as executable-path target.
   - S3: run Blender with the mcp-for-blender addon enabled before designating blender-dependent
     verify steps; treat "connected" claims as launcher-level; add a pre-token addon probe.
3. A verbatim evidence appendix: the reproduced error strings, pgrep result, PATH lookups, the
   npx `--browser` option list, config refs (paths short/split to avoid 32+ char lexemes).

## Constraints

- Masking: reference sessions by id prefix only, never paste row bodies (mdu-35, skill note).
- No config edits: overlay mcp json, deployed configs untouched. Diffs shown as fenced proposals.
- Lexeme discipline in the doc (secret-scan FP class).
- Hermetic `test` phase: a small probe script (tmp) re-runs the two reproductions so the
  environment-gap claims are re-verified independently.
- Loop notes: design was conducted in-conversation (orchestrator) on evidence-freshness grounds;
  recorded as a deliberate deviation in the manifest for the introspector to judge.
