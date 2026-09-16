---
name: secret-scrub
description: Pre-commit secret scan — regex patterns for common credential formats, the flag, redact, report workflow, and rules for never printing full secrets. Load before finishing a change to make sure no keys, tokens, or private keys are about to be committed.
license: Unlicense
metadata:
  audience: [just-code, devops]
---

# Secret Scrub

Scan your changes for secrets before committing. Run the scan on the diff (`git diff`, staged files, and any new files) and on the working tree.

## Patterns to flag

- AWS access key IDs: `AKIA[0-9A-Z]{16}`
- OpenAI-style API keys: `sk-[A-Za-z0-9]{20,}`
- Private keys: `-----BEGIN (RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----`
- `.env` values: `(API_KEY|SECRET|TOKEN|PASSWORD|PASSWD|PRIVATE_KEY)\s*=\s*\S+` in committed `.env` files
- High-entropy strings: 32+ chars of base64 or hex (`[A-Za-z0-9+/]{32,}={0,2}` or `[0-9a-fA-F]{32,}`) that look random
- Generic assignments: `(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*['"]?\S+` in source files

## Workflow

1. **Flag** — list every match with `file:line` and the pattern that matched. Do NOT print the matched value in full.
2. **Redact** — replace the secret with a reference to an environment variable (e.g., `os.environ["API_KEY"]`, `$API_KEY`) or a config value that is not committed. Remove the secret from the diff entirely.
3. **Report** — confirm in your summary that the scan ran clean, or list what was redacted.

## Rules

- NEVER print full secrets in logs, diffs, or reports — show only `file:line` and a masked prefix (first 4 chars).
- NEVER commit `.env` files or files containing live credentials; use `.env.example` with placeholders.
- If a secret was already committed, flag it to the orchestrator so it can be rotated and purged from history — do not silently leave it.
- Reference secrets via environment variables or a secret manager; never hardcode defaults.