# pi package — role prompt templates

`build/pi/` is a generated pi package that ports the 20 `grok/agents` role
profiles to pi prompt templates, plus a generated `/roster`. It is produced by
`scripts/lib/gen_pi_templates.py` during `./build.sh` and is **never
hand-edited**.

## What it is

- `package.json` — manifest, `"keywords": ["pi-package"]`, no timestamps.
- `prompts/<role>.md` — one template per role, 20 total. Each is the shared
  adapter preamble, a model note, the source profile body byte-verbatim, and a
  trailing `## Task` section that receives `$ARGUMENTS`.
- `prompts/roster.md` — `/roster` lists roles, argument hints, and model notes.
- `PARITY.md` — what does not port to pi and how each construct is resolved.
  The hand-curated tracked version is `docs/pi-parity.md`.

## Usage

```bash
./build.sh                 # regenerate build/pi from grok/agents
pi install ./build/pi      # persistent install into the pi agent dir
pi list                    # confirm the package and its prompts
```

Then, in any pi session:

```
/just-code implement the retry wrapper in src/client.py
/orchestrator break this task into MDUs and drive them
/roster
```

`$ARGUMENTS` becomes the brief under the template's `## Task` heading. Without
arguments the role instructions still load.

### Power-user fallback (no install)

```bash
pi --system-prompt build/pi/prompts/just-code.md -p "state your role and reply OK"
```

Same generated files, strongest placement (system prompt instead of a user
message). Use this when you want a per-run role without touching the installed
package.

### After rebuilding

If your local install referenced the gitignored `build/pi/` rather than copying
it, re-run `pi install ./build/pi` after every `./build.sh` so the installed
templates match the sources. (Verified live in the MDU-56 smoke phase: a local
directory install REFERENCES the path rather than copying it — `pi list`
resolves to the repo's `build/pi`, so the re-run after rebuild is required.)

## Golden refresh checklist

`tests/fixtures/pi_golden/` is a tracked snapshot of `build/pi/`. Any change
under `grok/agents/` or `pi/` turns the golden gate red until the snapshot is
refreshed on purpose:

1. Regenerate: `./build.sh`, or
   `python3 scripts/lib/gen_pi_templates.py <dir>` into a temp dir.
2. Review the diff against `tests/fixtures/pi_golden/`. Read every changed
   template line; confirm no unintended prose drift.
3. For any new harness-specific construct, extend the audit lexicon in
   `pi/port-config.json` and the dispositions in `docs/pi-parity.md` —
   construct notes and one hit row per profile.
4. Copy the regenerated tree over `tests/fixtures/pi_golden/` and commit the
   golden snapshot together with the parity rows in one change.

Do not refresh the golden to make a red test pass: an unreviewed refresh hides
exactly the drift the gate exists to catch.

## Scope

Base-repo profiles only. The overlay `grok-*` family and `grokestrator` are
deferred (overlay-owned). Blender MCP is overlay-only and not ported. Repo
skills are not shipped in this package; pi discovers `~/.agents/skills/`
natively, so shipping base skills is a possible later MDU.
