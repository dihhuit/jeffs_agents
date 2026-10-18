# MDU-25 — Put bulk Grok agents on grok-build-0.1

The xAI provider this machine can actually call has two models:

- `grok-4.7` — $2 / $6 / $0.50 cached, doubles at 200k. Variants low/medium/high/xhigh are reasoning effort, not a cheaper price.
- `grok-build-0.1` — $1 / $2 / $0.20 cached, doubles at 200k, 256k context. Already in `config/model-registry.txt` as `xai/grok-build-0.1`.

`grok-4.6` and `grok-4.5` are the same price as 4.7 and are not in the OpenCode xAI list. Do not use them as a savings rung. Do not wire `grok-4.3`. It is on the xAI docs page and not available here.

Do not change OpenCode Go assignments. Review, QA, and devops stay on `opencode-go/mimo-v2.5`. Do not change architect models. Design stays on GLM 5.2 / grok-4.7 on purpose.

## Stay on grok-4.7

Flagship only where reasoning is the point.

Base `grok/agents/`: orchestrator, just-code-mid, just-code-pro, architect, architect-premium, code-reviewer-pro, qa-pro, test-agent-pro, devops-pro, ui-ux-designer-pro, inception, introspector.

Overlay `grok/agents/` and `opencode.json`: grokestrator, grok-plan, thought-leadership-coach, grok-just-code-mid, grok-just-code-pro, grok-architect, grok-architect-premium, grok-code-reviewer-pro, grok-qa-pro, grok-test-agent-pro, grok-devops-pro, grok-deep-research, grok-ui-ux-designer-pro.

## Move to grok-build-0.1

Base `grok/agents/` frontmatter `model:`: just-code, test-agent, code-reviewer, qa, devops, research, ui-ux-designer, grok-review.

Overlay `grok/agents/` frontmatter `model:` and the matching `opencode.json` `"model"` field (`xai/grok-build-0.1`): grok-just-code, grok-test-agent, grok-code-reviewer, grok-qa, grok-devops, grok-research, grok-ui-ux-designer, grok-mdu-code.

## Allowlist and tests

In `scripts/lib/validate.py`, add `grok-build-0.1` to `GROK_MODEL_ALLOWLIST`. Keep 4.7, 4.6, and 4.5.

In `tests/test_grok_model_allowlist.py`:

- `EXPECTED_ALLOWLIST` includes `grok-build-0.1`.
- Replace `test_production_grok_profiles_use_grok_4_7` with an explicit map. The profiles listed above under "Move" must be `grok-build-0.1`. Every other production profile in `grok/agents/` must be `grok-4.7`. Fail if a profile is on 4.6 or 4.5.

## Prompt text

In `grok/agents/orchestrator.md`, the model-selection list and the token-frugality sentence currently say every role is grok-4.7 and "same model today". Change the bulk roles (research, just-code, test-agent, code-reviewer, devops, qa, ui-ux-designer) to say `grok-build-0.1`. Leave mid/pro/architect/orchestrator on `grok-4.7`. Replace the sentence that says all profiles use grok-4.7 with: bulk profiles use `grok-build-0.1`; flagship `grok-4.7` is for the orchestrator, architecture, and mid/pro roles. Do not say to spend Grok to save Go budget.

In `opencode_agents/grok/agents/grokestrator.md`, replace the same false sentence. Bulk grok agents are `grok-build-0.1`. Flagship stays on grokestrator, architecture, and mid/pro. Do not tell it to use Grok when Go budget is tight.

## Do not

- Edit `build/` by hand.
- Commit or push.
- Run git checkout, restore, reset, clean, or stash.
- Change `opencode-go/` models.
- Change architect or architect-premium models.
