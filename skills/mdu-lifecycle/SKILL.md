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
7. **Commit and push** — after the MDU is fully validated, commit and push before moving on.

## Model-tier selection decision table

Choose the cheapest reliable model for each task; rotate variants to spread token cost across tiers.

| Task | Default | Mid | Pro | Free |
|------|---------|-----|-----|------|
| Coding | just-code (deepseek-v4-flash) | just-code-mid (kimi-k2.7-code) | just-code-pro (deepseek-v4-pro) | just-code-free (big-pickle) |
| Testing | test-agent (deepseek-v4-flash) | test-agent-mid (minimax-m3) | test-agent-pro (kimi-k2.7-code) | test-agent-free (big-pickle) |
| Review | code-reviewer (minimax-m3) | — | code-reviewer-pro (deepseek-v4-pro) | code-reviewer-free (big-pickle) |
| Architecture | architect (deepseek-v4-pro) | — | architect-premium (glm-5.2) | — |
| DevOps | devops (minimax-m3) | — | devops-pro (deepseek-v4-pro) | devops-free (big-pickle) |
| QA | qa (minimax-m3) | — | qa-pro (kimi-k2.7-code) | qa-free (big-pickle) |
| UI/UX | ui-ux-designer (minimax-m3) | — | ui-ux-designer-pro (kimi-k2.7-code) | — |
| Research | research (ling-3.0-flash-fin-free) | deepseek-research (nemotron-3-ultra-free) | nemotron-research (nemotron-3.5-lightning-free) | deep-research (mimo-v2.5) |

Rules:

- Default to the cheapest adequate variant; upgrade only when the task genuinely requires deeper reasoning.
- Free-tier research agents are independent of the Go budget — prefer them for all research tasks.
- On token or rate-limit errors, retry with a different variant (e.g., `just-code` → `just-code-free`).
- Reserve `architect-premium` and `code-reviewer-pro` for the most complex tasks.

## Failure routing

- Code, logic, or application bugs → back to `just-code` (and `test-agent` for verification).
- Infrastructure, pipeline, or deployment configuration → back to `devops` (possibly with `architect` input).
- Re-execute the affected phases (re-deploy and/or re-validate) until the MDU is fully green; only then mark it complete.

## Guardrails

- Max 3 retry attempts per MDU per failure type; then STOP and escalate with a summary.
- If a subagent is stuck ~5 minutes with no progress, cancel it and decompose or escalate.
- If an MDU exceeds ~30 minutes without reaching Commit and Push, checkpoint, summarize, and break the remaining work down.