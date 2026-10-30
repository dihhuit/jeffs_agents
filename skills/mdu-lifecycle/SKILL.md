---
name: mdu-lifecycle
description: The closed-loop MDU checklist (design, implement, review, test, deploy, validate, commit) plus the model-tier selection decision table. Load when starting, driving, or grading an MDU so the loop stays on track and the cheapest adequate model is used for each step.
license: Unlicense
metadata:
  audience: [just-code, qa, orchestrator]
---

# MDU Lifecycle

An MDU (minimum deployable unit) is the smallest slice of functionality that can be fully designed, implemented, tested, reviewed, and deployed as an independent, valuable increment. Drive every MDU through the closed loop below until DevOps succeeds cleanly AND QA gives PASS.

## Closed-loop checklist

1. **Design** — via `architect` (or `architect-premium` for complex systems). Produce a design doc or API spec.
2. **Implement** — via a `just-code` variant (see decision table). Code must build, lint, and pass existing tests.
3. **Review** — via `code-reviewer` (or `code-reviewer-pro` for security-sensitive changes). Must receive explicit sign-off.
4. **Test** — via a `test-agent` variant. All tests must pass; coverage gaps reported.
5. **Deploy** — via `devops` (or `devops-pro` for complex deploys). Must succeed without errors.
6. **Validate** — via `qa` (or `qa-pro` for thorough validation). Must receive a PASS grade.
7. **Introspect** — via `introspector` after validate, before commit. It reads session logs, writes `agent-improvements.md`, and reports apply-now items. Do not rewrite agent definitions unless the user asked.
8. **Commit and push** — after the MDU is fully validated, commit and push before moving on.

## Model-tier selection decision table

Choose the cheapest reliable model for each task; rotate variants to spread token cost across tiers.

| Task | Default | Mid | Pro |
|------|---------|-----|-----|
| Coding | just-code (deepseek-v4.1-flash) | just-code-mid (kimi-k2.7-code) | just-code-pro (glm-5.2) |
| Testing | test-agent (deepseek-v4.1-flash) | test-agent-mid (mimo-v2.6-flash) | test-agent-pro (kimi-k2.7-code) |
| Review | code-reviewer (mimo-v2.6-flash) | — | code-reviewer-pro (glm-5.2) |
| Architecture | architect (glm-5.2) | — | architect-premium (glm-5.2) |
| DevOps | devops (mimo-v2.6-flash) | — | devops-pro (glm-5.2) |
| QA | qa (mimo-v2.6-flash) | — | qa-pro (kimi-k2.7-code) |
| UI/UX | ui-ux-designer (mimo-v2.6-flash) | — | ui-ux-designer-pro (kimi-k2.7-code) |
| Research | deep-research (mimo-v2.6-flash) | — | — |

Rules:

- Default to the cheapest adequate variant; upgrade only when the task genuinely requires deeper reasoning.
- All loop phases run on paid models; free-tier variants are retired (MDU-40).
- On a cap/provider error, quota refusal, or credit exhaustion from a paid `opencode-go/*` spawn: one retry, then exactly one rotation to a different live `opencode-go/*` model, then stop and escalate with evidence. `xai/*` spawns: no ladder — escalate directly. Never substitute a free model (MDU-41).
- Reserve `architect-premium` and `code-reviewer-pro` for the most complex tasks.

## Failure routing

- Code, logic, or application bugs → back to `just-code` (and `test-agent` for verification).
- Infrastructure, pipeline, or deployment configuration → back to `devops` (possibly with `architect` input).
- Re-execute the affected phases (re-deploy and/or re-validate) until the MDU is fully green; only then mark it complete.

## Guardrails

- Max 3 retry attempts per MDU per failure type; then STOP and escalate with a summary.
- If a subagent is stuck ~5 minutes with no progress, cancel it and decompose or escalate.
- If an MDU exceeds ~30 minutes without reaching Commit and Push, checkpoint, summarize, and break the remaining work down.