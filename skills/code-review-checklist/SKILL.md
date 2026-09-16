---
name: code-review-checklist
description: Condensed code-review rubric covering security, input validation, concurrency, error handling, performance antipatterns, and conventions, with the required file:line + severity output format and approve criteria. Load when reviewing a diff or deciding whether to sign off on a change.
license: Unlicense
metadata:
  audience: [code-reviewer]
---

# Code Review Checklist

Review all code diffs and new files. Use `git diff`, `git show`, and grep/rg to inspect changes. Be concise, specific, and actionable — "this is bad" is not useful; explain why and suggest the fix.

## Security

- [ ] Injection: SQL/command/template injection — untrusted input never reaches an interpreter unescaped or unparameterized.
- [ ] XSS: user input rendered in HTML/JS contexts is escaped or uses safe APIs.
- [ ] CSRF: state-changing requests are protected (tokens, same-site cookies, origin checks).
- [ ] Authz: every endpoint/action checks the caller is authorized, not merely authenticated.
- [ ] Secret leakage: no keys, tokens, passwords, or connection strings in code, logs, or committed files.
- [ ] Dependency risk: no known-vulnerable or unnecessary dependencies introduced.

## Input validation

- [ ] Bounds/range checks on all external input (length, type, allowed values).
- [ ] No dangerous implicit type coercion; explicit validation before use.
- [ ] File paths and URLs from input are canonicalized and confined to allowed roots.

## Concurrency

- [ ] Shared state is protected (locks, atomics, or immutable data); no data races.
- [ ] No deadlocks: consistent lock ordering; no blocking calls while holding locks.
- [ ] Async/threading: no unhandled exceptions that strand resources.

## Error handling

- [ ] Failures are caught and propagated with context; no silent `except: pass`.
- [ ] Errors map to appropriate status codes/messages; no internal details leaked to users.
- [ ] Resources (files, sockets, DB connections) are released on all paths.

## Performance antipatterns

- [ ] No N+1 queries; batch or join where needed.
- [ ] No O(n²) in hot paths; no unnecessary allocations in loops.
- [ ] No blocking I/O in event loops; caching used where it genuinely helps.

## Conventions

- [ ] Matches project style, patterns, and architecture.
- [ ] Clear naming; no dead code; no unnecessary abstractions.

## Output format

For each issue, report exactly:

```
<file>:<line> [severity] <what is wrong> — <why it matters> — <suggested fix>
```

Severity levels: `critical` (security/data loss), `high` (correctness), `medium` (robustness), `low` (style/nit).

## Approve criteria

Approve only when ALL of the following hold:

- No unresolved critical or high issues.
- Medium/low issues are either fixed or explicitly acknowledged with a reason.
- Code is correct, clean, and follows all conventions.

If any issue is unresolved, do NOT approve — list the blocking issues and return for a fix.