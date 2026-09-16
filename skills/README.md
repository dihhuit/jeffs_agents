# Skills Library

This directory holds reusable "Agent Skills" for the agents defined in this repo. Skills are loaded on demand: an agent sees only the `name` and `description` until it activates a skill, so keep descriptions informative about WHEN to use each skill.

## Why skills

Skills package the team's hard-won process knowledge — checklists, rubrics, and recipes — into files any agent can load. They keep prompts short while still giving agents the full procedure when they need it.

## The open standard

Each skill follows the open "Agent Skills" format: a directory per skill containing a `SKILL.md` file with YAML frontmatter (`name`, `description`, optional `license`, `metadata`, `allowed-tools`) followed by a focused markdown body. Optional `scripts/`, `references/`, and `assets/` subfolders may accompany the skill.

## How to add one

1. Create `skills/<kebab-case-name>/SKILL.md`.
2. Add YAML frontmatter with `name` (kebab-case) and `description` (2-3 sentences saying when to activate).
3. Write a focused, actionable body — checklists and steps the agent should follow.
4. Add `references/` or `scripts/` only if they genuinely add value.
5. Run `./build.sh` — `validate.py` checks every skill's frontmatter.

## Progressive disclosure

Skills load progressively: only `name` + `description` are visible until the skill is activated. Write descriptions to help an agent decide when to load the skill, and keep the body actionable.

## Deploy path

`scripts/build.sh` stages `skills/` into `build/skills/`, and `scripts/deploy.sh` copies each `skills/*/` directory into the OpenCode and Grok skills directories (`~/.config/opencode/skills/`, `~/.grok/skills/`).