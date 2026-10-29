---
type: project
created: 2026-10-27T13:24:20Z
updated: 2026-10-29T15:05:00Z
---

# Project facts — open-agent-definitions (base agent-team repo)

- Verify: `python3 -m pytest tests/ -q` + `./build.sh` (both must be green); overlay sibling `opencode_agents/` builds via its own `./build.sh` (re-runs base build, then merges overlays); live deploy from overlay `./deploy.sh --force`.
- Oracle storage layout (learned 2026-10-27, mdu-35): OpenCode v2 moved parts inline into `session_message.data.$.content[]` between 2026-10-13/15; the legacy `part` table is frozen after that cutoff (0 rows for all newer sessions). Census/forensics over recent sessions must go `part.message_id = session_message.id` → `session_v2`; tool parts for post-cutoff sessions are NOT in the `part` table.
- `scripts/lib/secret_scan.py` high-entropy rule (`[A-Za-z0-9+/]` runs of 32+, threshold 3.5 bpc) trips on plain repo paths of 32+ chars because `/` is in the char class (the overlay mirror path under `overlays/` reaches 33 chars). **Irony noted:** the example path in this very line trips the scanner — that is why the mdu-35 design doc reworded its path lexemes; keep paths short or split them in committed docs.
- The overlay third orchestrator mirror is overlay-root `grok/agents/grokestrator.md` (full file, snippets not re-applied onto it); there is no `overlays/grok/agents/` path.

## 2026-10-27T14:32:09Z
- scripts/lib/resume_block.py validate <fixture> — exit 0 canonical / 1 violations / 2 usage; canonical resume-block shape documented in docs/resume-block.md; grokestrator mirror edited via overlay repo (both repos must be committed for one orchestrator-file change).
- The completed_at manifest field must be an ISO-8601 string even while status is in_progress (set an interim timestamp, update at finalize) — run_ledger validate rejects null.

## 2026-10-27T22:20:00Z (mdu-36)
- Overlay now builds two tiers: its build.sh runs the base gen_zen_config.py (via GENERIC_DIR) on the MERGED config -> build/opencode.zen.json (zen map = base map + optional config/zen-model-map.json layer + xai/*-only big-pickle fallback; any other unmapped model fails the build). Overlay deploy.sh gained --tier=zen|go (default zen; both tiers installed; parked file inert by name). Invalid --tier exits 1 in the overlay but exit 2 in base — intentional local convention.
- Overlay deploy.sh grok-dir edge fixed: missing harness source dirs warn-skip (never abort, dry-run or --force); true find-based counts; the old live bug printed '1 grok agent profile(s)' with 41 profiles; regression test asserts the anchored count line.
- runs/ is gitignored in the OVERLAY repo (mdu-29/mdu-36 manifests stay local-only, unlike the base).
- Gotcha (2026-10-28): OpenCode's model registry can list dead models as "active" — verify with `timeout 90 opencode run -m <id> "Reply with exactly: OK"` before adding to zen-model-map.json or prompts (mdu-37).

## 2026-10-29 (mdu-38)
- scripts/lib/probe_models.py --refresh --gate: probes zen-map targets (hard, exit 1 if any not ok/stale/missing) + alternates (warn-only); success = exit 0 AND stdout stripped == "OK" exactly; success rule pins the F1 "NOT OK"/"OKChrome" substring finding; report exits 0 as data even when models fail — only --gate grades.
- Base /runs/ is gitignored too (manifests local-only in BOTH repos now, contrary to the older mdu-36 note); runs/ ledger validate still required pre-commit.
- qa child regression (new 20261029-1): a QA subagent can return an empty/corrupted first reply; the protocol is to re-request in the same session before accepting.

## 2026-10-29 (mdu-42)
- Grok-xai hard rule, four enforcement layers: base validate.py clauses (go + zen variants), base deploy.sh grok_xai_gate (hard, both tier files), overlay deploy.sh run_grok_xai_gate over active+parked (inline scripts/lib/check_grok_xai.py), probe_models.py --include-xai (xai_results report section + gate rule 6.5; ok==1-among-duplicates is green, mirroring the zen branch). Grok-named = grok-* prefix or exactly grokestrator/grok-plan; bare `xai/` suffix is a violation in both engines.
- Overlay zen build treats xai/* as IDENTITY pass-through for ALL agents (family rule, not name-scoped; thought-leadership-coach stays on xai in zen — correct, not a violation); no xai rows ever land in zen-model-map.json.
- Spawn model overrides: the deployed default tier still routes coder/reviewer/test/qa/devops defaults to free models (big-pickle / lightning-free) that cap mid-loop — every dispatch this MDU used an explicit paid model override `opencode-go/glm-5.3-flash` on the spawn (apply-now 20261029-2). Keep until MDU-39/40/41 change the default tier; mutate away from big-pickle defaults then.
- Verbatim free-cap refusal string (for MDU-39): `Error: Free usage limit reached. Free models work in OpenCode (https://opencode.ai); subscribe to OpenCode Go to keep going: https://opencode.ai/go` — big-pickle + deepseek-v4.1-flash-free + mimo-v2.6-flash-free + nemotron-3.5-super-vl-free; evidence /tmp/opencode/mdu-42-deploy-evidence.md.
- Introspector shell permission regression (first denial since the mdu-30 fix): session_signals.py did not run in this MDU's introspection — regression watch attached to closed suggestion 20261014-6; machine signals UNKNOWN, not zero (20261029-2 note).
