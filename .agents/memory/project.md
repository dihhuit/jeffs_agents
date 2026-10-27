---
type: project
created: 2026-10-27T13:24:20Z
updated: 2026-10-27T13:24:20Z
---

# Project facts — open-agent-definitions (base agent-team repo)

- Verify: `python3 -m pytest tests/ -q` + `./build.sh` (both must be green); overlay sibling `opencode_agents/` builds via its own `./build.sh` (re-runs base build, then merges overlays); live deploy from overlay `./deploy.sh --force`.
- Oracle storage layout (learned 2026-10-27, mdu-35): OpenCode v2 moved parts inline into `session_message.data.$.content[]` between 2026-10-13/15; the legacy `part` table is frozen after that cutoff (0 rows for all newer sessions). Census/forensics over recent sessions must go `part.message_id = session_message.id` → `session_v2`; tool parts for post-cutoff sessions are NOT in the `part` table.
- `scripts/lib/secret_scan.py` high-entropy rule (`[A-Za-z0-9+/]` runs of 32+, threshold 3.5 bpc) trips on plain repo paths of 32+ chars because `/` is in the char class (the overlay mirror path under `overlays/` reaches 33 chars). **Irony noted:** the example path in this very line trips the scanner — that is why the mdu-35 design doc reworded its path lexemes; keep paths short or split them in committed docs.
- The overlay third orchestrator mirror is overlay-root `grok/agents/grokestrator.md` (full file, snippets not re-applied onto it); there is no `overlays/grok/agents/` path.
