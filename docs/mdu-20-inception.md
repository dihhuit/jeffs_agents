# MDU-20 — Promote `inception` to the public base

## Goal

Promote the personal `inception` agent (a user-invoked "idea → spec" interviewer) from
`opencode_agents` into `open-agent-definitions` so any user of the public base gets it,
with the OpenCode and Grok mirrors behaviorally aligned and parity-validated.

## Non-goals

- No tier variants — one agent, name `inception`.
- No `xai` provider in the base, no legacy `tools` block.
- Not added to the orchestrator's automatic MDU loop.
- No overlay cleanup in this repo (see Out of scope).

## Model choice

`opencode-go/deepseek-v4.1-flash` — already in `config/model-registry.txt`,
and it is the budget tier this repo assigns to structured-writing roles
(just-code, test-agent), which matches inception's low-compute interview-and-write
workload.

## File list

Add:
- `prompts/inception.md` — canonical OpenCode prompt (also flows to Claude via the build).
- `grok/agents/inception.md` — Grok profile, frontmatter + thinner body.

Edit:
- `opencode.json` — add the `inception` agent entry (snippet below).
- `scripts/lib/validate.py` — add `"inception": ["inception.md"]` to `GROK_MIRRORS`
  and an `"inception"` entry to `ROLE_KEYWORDS`.
- `docs/model-registry.md` — add an `inception` row (new "Inception" section, model `opencode-go/deepseek-v4.1-flash`).
- `README.md` — roster entry + layout counts (see README touch points).

No change needed: `config/model-registry.txt`, `provider` block, schema (`permission`
is an open object; `question` is accepted as an additional key).

## OpenCode registry snippet (exact)

Insert inside `"agent"`:

```json
"inception": {
  "mode": "primary",
  "description": "Interviews you on a new project idea and iteratively refines it into an actionable spec document",
  "model": "opencode-go/deepseek-v4.1-flash",
  "color": "#f97316",
  "system": "{file:./prompts/inception.md}",
  "request": { "body": { "temperature": 0.4 } },
  "permissions": [
    { "action": "edit", "resource": "*", "effect": "allow" },
    { "action": "read", "resource": "*", "effect": "allow" },
    { "action": "glob", "resource": "*", "effect": "allow" },
    { "action": "grep", "resource": "*", "effect": "allow" },
    { "action": "webfetch", "resource": "*", "effect": "allow" },
    { "action": "websearch", "resource": "*", "effect": "allow" },
    { "action": "question", "resource": "*", "effect": "allow" },
    { "action": "todowrite", "resource": "*", "effect": "allow" },
    { "action": "shell", "resource": "*", "effect": "deny" },
    { "action": "subagent", "resource": "*", "effect": "deny" }
  ]
}
```

Notes: `mode: primary` (schema enum allows it; orchestrator is the only primary today).
`question` is an additional permission key (unused elsewhere in the base) that the schema
permits; the overlay prompt depends on the question tool, so keep it.

## Behavioral clauses — must appear in BOTH mirrors

Both `prompts/inception.md` and `grok/agents/inception.md` must contain:

Section markers (validated structurally):
- `## Hard constraints` heading.
- `## Safety constraints` with the standard sentence:
  `**Step Limit:** Maximum of 50 loop steps per invocation. At step 45, begin wrapping up
  — finalize current work and summarize progress. At step 50, you MUST exit ...`

Behavior (validated by ROLE_KEYWORDS + review; literal tokens in parentheses are the
parity keywords and must appear verbatim in both):
- Welcome the user and ask for the initial idea; **interview** iteratively.
- Ask one or two focused questions at a time.
- Cover: problem/context, users/personas, **MoSCoW** (must-have vs nice-to-have),
  technical constraints, NFRs, timeline/budget, success metrics, integrations, risks.
- Summarize and confirm after each round.
- Stop when "**complete enough**" — residual ambiguity is fine unless it would block
  writing an actionable spec.
- Stay in interview mode until the user explicitly says they are ready for the final spec.
- Write **spec.md** (or a user-chosen name) with the section list: Executive Summary,
  Problem Statement, Goals & Success Metrics, User Personas & Journeys, Functional
  Requirements (prioritized MoSCoW), Non-Functional Requirements, Technical Constraints
  & Stack Recommendations, Scope & Out-of-Scope, Risks & Mitigations, High-Level
  Architecture Suggestions, Next Steps / MVP Definition.
- Gap-fill an existing/partial spec instead of starting over.
- Offer handoff to the architect/orchestrator when the spec is written.
- Use the **question** tool for interactive follow-ups; end every turn with a next step
  or confirmation **question**.
- Never assume the user's preferences.

## ROLE_KEYWORDS entry (proposed)

```python
"inception": [
    ("interview",),
    ("spec.md",),
    ("moscow",),
    ("complete enough",),
    ("question",),
],
```

(Parity matching is case-insensitive, so "MoSCoW" → "moscow".)

## README touch points

- Add `inception` to the OpenCode roster under a new "Inception" heading, marked
  **user-invoked primary** (not part of the orchestrator's MDU loop).
- Add `inception` to the Grok profiles list (`grok/agents/inception.md`, grok-4.7).
- Update layout counts: OpenCode `27 → 28` agents, Grok `19 → 20` profiles,
  Claude `27 → 28` generated subagents (the build emits a Claude subagent for every
  OpenCode agent regardless of mode).

## Acceptance criteria (QA-gradable from the repo alone)

1. `prompts/inception.md` and `grok/agents/inception.md` both exist.
2. Both files contain a `Hard constraints` section and a `Safety constraints` / Step Limit
   statement; both contain the five parity keywords (interview, spec.md, moscow,
   complete enough, question).
3. `grok/agents/inception.md` frontmatter: `name: inception`, `model: grok-4.7`
   (allowlisted), `description` present.
4. `opencode.json` `inception` entry: `mode: primary`, model `opencode-go/deepseek-v4.1-flash`,
   `system` ref `{file:./prompts/inception.md}`, `permissions` array with `shell: "deny"`,
   `subagent: { "resource": "*", "effect": "deny" }`, and **no `tools` key, no `xai/` model**.
5. `scripts/lib/validate.py` `GROK_MIRRORS` includes `"inception": ["inception.md"]` and
   `ROLE_KEYWORDS` includes `"inception"`.
6. `python3 -m pytest tests/ -q && ./build.sh` passes; validator reports 28 agents,
   20 grok profiles, and the parity pair count includes inception.
7. `docs/model-registry.md` lists `inception` → `opencode-go/deepseek-v4.1-flash`.
8. README lists inception (user-invoked primary) and shows 28/20/28 counts.
9. No test files modified by the implementer.

## Do not copy

- The overlay `browser-os` "never create a window / tabs only" block.
- AWS / safekids, monorepo `/frontend`+`/backend`, Android SDK, PyTorch/ROCm,
  thought-leadership content.
- The overlay registry shape: legacy `tools` block, `model: xai/grok-4.7`.
- The thin `opencode_agents/grok/agents/inception.md` body (use the OpenCode prompt's
  behavior, restated concisely).

## Out of scope (follow-up in `opencode_agents`, not this repo)

After the base ships: delete overlay root `prompts/inception.md`, `grok/agents/inception.md`,
and the `inception` key in overlay `opencode.json`, then rebuild the overlay (it will
inherit the base copy and re-append personal snippets). Not designed in detail here.

## Risks that would block implementation

1. **`question` permission key at runtime** — `question` is not used elsewhere in the
   base, so there is no in-repo proof OpenCode honors `"question": "allow"` as a
   permission key. The schema accepts it (open object); if the runtime ignores unknown
   permission keys it degrades to default (ask) rather than failing, so this is low risk
   but the implementer should smoke-test once.
2. **Parity keyword drift** — if the grok mirror omits any of the five literal tokens
   (e.g. "moscow" or "complete enough"), `validate.py` parity fails; the implementer must
   keep those exact substrings in both files.
