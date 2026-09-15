# Model Registry

Every model referenced by agents in `opencode.json`, grouped by tier. All
entries were verified against `opencode models` on **2026-09-15**.

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
| `orchestrator`   | `opencode-zen/big-pickle` |

## Research (free)

| Agent                 | Model                              |
|-----------------------|------------------------------------|
| `research`            | `opencode/ling-3.0-flash-fin-free` |
| `deepseek-research`   | `opencode/nemotron-3-ultra-free`   |
| `nemotron-research`   | `opencode/nemotron-3.5-lightning-free` |
| `deep-research`       | `opencode-go/mimo-v2.5` (Go budget) |

## Coding

| Agent             | Model                              |
|-------------------|------------------------------------|
| `just-code`       | `opencode-go/deepseek-v4-flash`    |
| `just-code-mid`   | `opencode-go/kimi-k2.7-code`       |
| `just-code-pro`   | `opencode-go/deepseek-v4-pro`      |
| `just-code-free`  | `opencode-zen/big-pickle`          |

## Testing

| Agent             | Model                              |
|-------------------|------------------------------------|
| `test-agent`      | `opencode-go/deepseek-v4-flash`    |
| `test-agent-mid`  | `opencode-go/minimax-m3`           |
| `test-agent-pro`  | `opencode-go/kimi-k2.7-code`       |
| `test-agent-free` | `opencode-zen/big-pickle`          |

## Review

| Agent                 | Model                              |
|-----------------------|------------------------------------|
| `code-reviewer`       | `opencode-go/minimax-m3`           |
| `code-reviewer-pro`   | `opencode-go/deepseek-v4-pro`      |
| `code-reviewer-free`  | `opencode-zen/big-pickle`          |

## Architecture

| Agent                | Model                              |
|----------------------|------------------------------------|
| `architect`          | `opencode-go/deepseek-v4-pro`      |
| `architect-premium`  | `opencode-go/glm-5.2`              |

## DevOps

| Agent          | Model                              |
|----------------|------------------------------------|
| `devops`       | `opencode-go/minimax-m3`           |
| `devops-pro`   | `opencode-go/deepseek-v4-pro`      |
| `devops-free`  | `opencode-zen/big-pickle`          |

## QA

| Agent    | Model                              |
|----------|------------------------------------|
| `qa`     | `opencode-go/minimax-m3`           |
| `qa-pro` | `opencode-go/kimi-k2.7-code`       |
| `qa-free`| `opencode-zen/big-pickle`          |

## UI/UX

| Agent                  | Model                              |
|------------------------|------------------------------------|
| `ui-ux-designer`       | `opencode-go/minimax-m3`           |
| `ui-ux-designer-pro`   | `opencode-go/kimi-k2.7-code`       |