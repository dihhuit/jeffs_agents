---
name: git-autonomy
description: Branch, commit, and PR hygiene for autonomous runs — feature branch per MDU, conventional commit subjects with the MDU id, sign-off discipline, PR description contents, and push safety rules. Load when committing or opening a PR for completed work.
license: Unlicense
metadata:
  audience: [just-code, orchestrator]
---

# Git Autonomy

Hygiene rules for committing and pushing work from autonomous runs. Follow these exactly so history stays reviewable and recoverable.

## Branch

- Create a feature branch per MDU: `mdu-<id>-<short-slug>` (e.g., `mdu-05-skills-library`).
- Branch from the latest `main`/default branch; never branch from a stale base.
- Keep the branch scoped to the MDU — no unrelated changes.

## Commit

- Conventional commit subject with the MDU id: `feat(mdu-05): seed skills library`.
- Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `build`, `ci`.
- One logical change per commit; commit messages explain the why, not just the what.
- Sign-off discipline: include a `Signed-off-by:` trailer if the project requires it; match repo conventions.

## PR description

Include:

- **Design ref** — link or path to the design doc or MDU spec the work implements.
- **Test results** — what was run (build, lint, test suite) and the outcome.
- **Run manifest** — agents used per step and model tiers (e.g., just-code/deepseek-v4-flash), plus artifacts (logs, screenshots, coverage reports).
- **Validation** — QA grade and/or deploy status if applicable.

## Push safety

- NEVER force-push to shared branches; if history needs fixing, use a new commit or a dedicated branch.
- Fetch before push: `git fetch`, then rebase/merge the latest base so the push is not rejected.
- Push the feature branch and open the PR; do not push directly to `main` unless the project explicitly allows it.
- If a push fails (non-fast-forward), fetch, rebase, and retry — never `--force`.

## Checklist before commit

- [ ] `git status` and `git diff` reviewed — only intended files staged.
- [ ] No secrets in the diff (see the secret-scrub skill).
- [ ] Build, lint, and tests pass.
- [ ] Commit message includes the MDU id and follows the repo's style.