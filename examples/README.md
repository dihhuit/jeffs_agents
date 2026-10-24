# Examples Gallery

Worked examples of MDUs executed by this repo's own agent team, with manifests and key artifacts. Links below point to committed manifests in `examples/runs/` and the source docs.

| Example | MDU | What it shows |
| --- | --- | --- |
| [MDU-08 — Golden evaluation suite](gallery/mdu-08-golden-evals.md) | mdu-08 | Bootstrap of `evals/` with golden tasks and a runner wired into the loop. |
| [MDU-09 — Prompt regression gate](gallery/mdu-09-prompt-regression.md) | mdu-09-prompt-regression-gate | 3-rejection regression loop against golden tasks with promptfoo integration. |
| [MDU-15 — Cross-CLI run-ledger conformance](gallery/mdu-15-cross-cli-ledger.md) | mdu-15-run-ledger-schema-inline | Schema inlined into both orchestrator mirrors; manifests conform across OpenCode/Grok/Claude. |

See also [upgrade-story.md](upgrade-story.md) for the full narrative and [runs/](runs/) for all committed example manifests.
