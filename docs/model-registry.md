# Model Registry

Every model referenced by agents in `opencode.json`, grouped by tier. All
entries were verified against `opencode models` on **2026-10-08**.

To re-verify (and refresh the committed snapshot `config/model-registry.txt`):

```bash
opencode models
opencode models > config/model-registry.txt
```

The build pipeline (`scripts/lib/validate.py`) fails if any agent model
reference is missing from the snapshot, so a stale reference cannot ship.

## Orchestrator

| Agent            | Model                    |
|------------------|--------------------------|
| `orchestrator`   | `opencode/big-pickle` |

## Research (free)

| Agent                 | Model                              |
|-----------------------|------------------------------------|
| `research`            | `opencode/mimo-v2.6-flash-free` |
| `deepseek-research`   | `opencode/nemotron-3-ultra-free`   |
| `nemotron-research`   | `opencode/nemotron-3.5-lightning-free` |
| `deep-research`       | `opencode-go/mimo-v2.5` (Go budget) |

## Coding

| Agent             | Model                              |
|-------------------|------------------------------------|
| `just-code`       | `opencode-go/deepseek-v4.1-flash`    |
| `just-code-mid`   | `opencode-go/kimi-k2.7-code`       |
| `just-code-pro`   | `opencode-go/glm-5.2`      |
| `just-code-free`  | `opencode/big-pickle`          |

## Testing

| Agent             | Model                              |
|-------------------|------------------------------------|
| `test-agent`      | `opencode-go/deepseek-v4.1-flash`    |
| `test-agent-mid`  | `opencode-go/mimo-v2.5`           |
| `test-agent-pro`  | `opencode-go/kimi-k2.7-code`       |
| `test-agent-free` | `opencode/big-pickle`          |

## Review

| Agent                 | Model                              |
|-----------------------|------------------------------------|
| `code-reviewer`       | `opencode-go/mimo-v2.5`           |
| `code-reviewer-pro`   | `opencode-go/glm-5.2`      |
| `code-reviewer-free`  | `opencode/big-pickle`          |

## Architecture

| Agent                | Model                              |
|----------------------|------------------------------------|
| `architect`          | `opencode-go/glm-5.2`      |
| `architect-premium`  | `opencode-go/glm-5.2`              |

## DevOps

| Agent          | Model                              |
|----------------|------------------------------------|
| `devops`       | `opencode-go/mimo-v2.5`           |
| `devops-pro`   | `opencode-go/glm-5.2`      |
| `devops-free`  | `opencode/big-pickle`          |

## QA

| Agent    | Model                              |
|----------|------------------------------------|
| `qa`     | `opencode-go/mimo-v2.5`           |
| `qa-pro` | `opencode-go/kimi-k2.7-code`       |
| `qa-free`| `opencode/big-pickle`          |

## UI/UX

| Agent                  | Model                              |
|------------------------|------------------------------------|
| `ui-ux-designer`       | `opencode-go/mimo-v2.5`           |
| `ui-ux-designer-pro`   | `opencode-go/kimi-k2.7-code`       |

## Inception

User-invoked primary. Not part of the orchestrator's MDU loop.

| Agent        | Model                              |
|--------------|------------------------------------|
| `inception`  | `opencode-go/deepseek-v4.1-flash`    |