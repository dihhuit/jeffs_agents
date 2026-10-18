# MDU-24 — Test agent must not discard a dirty tree

On MDU-23 a test-agent ran `git checkout -- .` while the MDU edits were uncommitted. That discarded the work. It was restored by hand. Do not let that happen again.

## Files

1. `prompts/test-agent.md` — OpenCode `test-agent`, `test-agent-mid`, `test-agent-pro`, `test-agent-free`, and every `grok-test-agent*` OpenCode agent that uses this prompt.
2. `grok/agents/test-agent.md`
3. `grok/agents/test-agent-pro.md`
4. `scripts/lib/validate.py` `ROLE_KEYWORDS["test-agent"]` — add clauses. Do not remove `("never modify source", "never modify production")`.
5. `tests/test_mdu_24_test_agent_git_guard.py`

Do not edit `opencode_agents/prompts/test-agent.md`. That root copy is ignored by the overlay build. Do not edit `build/`. Do not commit. Do not run `git checkout`, `git restore`, `git reset`, `git clean`, or `git stash`.

## Insert

In each of files 1–3, under Safety constraints, immediately before the Step Limit bullet, insert this text verbatim:

```markdown
- **Dirty tree:** NEVER discard uncommitted work. Forbidden, even to reset before a test or to prove a mutation: `git checkout --`, `git restore`, `git reset --hard`, `git reset --merge`, `git clean`, `git stash drop`, `git stash clear`. Do not hide those commands inside a script. If you need a clean tree, copy the files under test to `/tmp` or a new worktree and mutate the copy. If you revert by mistake, restore from `git reflog` or `git stash` and report it before doing anything else.
```

Required substrings, all three files: `git checkout --`, `git reset --hard`, `git clean`, `uncommitted work`.

## ROLE_KEYWORDS

Add to the `"test-agent"` list:

- `("git checkout --",)`
- `("git reset --hard",)`
- `("git clean",)`

The parity check lowercases. These substrings match the inserted backticks.

## Test

Assert files 1–3 contain those four substrings, and that `ROLE_KEYWORDS["test-agent"]` contains the three new clauses. Run `timeout 120 python3 -m pytest tests/ -q` from this repo. Do not weaken existing tests.
