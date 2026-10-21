# MDU-11 — Secret Scanning & Leak Prevention in the Loop (Design)

- Status: approved design · Branch: `mdu-11-secret-gate` (both repos) · Date: 2026-10-21
- Backlog source: `FEATURE_BACKLOG.md` MDU-11 (lines 169–178). Dependency MDU-05 (`secret-scrub` skill) already shipped.
- Repos: base `open-agent-definitions` (generic scanner/gate/docs/tests) + overlay `opencode_agents` (grokestrator clause only). No scanner fork in the overlay.

## D1 — Scanner location and shape

- New module `scripts/lib/secret_scan.py` in the **base repo**: single file, Python 3 stdlib only (no deps, no network), alongside `run_ledger.py`.
- Rationale: stdlib-only keeps the gate deterministic, offline-testable, and deployable by `devops`/`orchestrator`/`just-code` (all `shell * allow`) with zero install steps; matches the `scripts/lib/*.py` shared-tooling convention.
- Overlay does **not** copy the module. Anything overlay-side that needs the gate resolves the base copy (D7).

## D2 — CLI surface, exit codes, output

`python3 scripts/lib/secret_scan.py [--staged | --paths P1 [P2 …]] [--json] [--no-placeholder-filter]`

- `--staged` (default): scan only **added/modified lines of the staged diff** via git plumbing.
- `--paths`: scan given files fully (ad-hoc scans, `just-code` pre-check, tests).
- Exit codes: `0` clean (including empty stage / nothing to scan); `1` findings (block commit); `2` operational failure (not a git repo, unreadable file) — **fail closed**: orchestrator treats any non-zero as "do not commit".
- Human output, one line per finding, nothing else:
  `<file>:<line> <rule-id> <first-4-chars>…`
- `--json`: `{"status":"pass|fail","scanned":{"files":N,"lines":N},"findings":[{"file","line","rule","preview"}]}`. `preview` is the masked prefix only.
- Masking is applied in one function on the single output path before any print/JSON emit; full matched values never leave the process (skill rule; audit point).
- Rationale: three-valued exit (clean/findings/broken) lets the orchestrator prompt distinguish "redact and retry" from "escalate"; JSON mode makes the gate machine-checkable by later phases without parsing prose.

## D3 — Rule set (1:1 onto `skills/secret-scrub/SKILL.md` plus two additions)

| id | pattern / trigger | scope | vs. skill |
|---|---|---|---|
| `aws-access-key-id` | `AKIA[0-9A-Z]{16}` | any line | as-is |
| `openai-style-key` | `sk-[A-Za-z0-9]{20,}` | any line | as-is |
| `private-key-block` | `-----BEGIN (RSA \|EC \|OPENSSH \|PGP )?PRIVATE KEY-----` | any line | as-is |
| `github-pat` | `gh[pousr]_[A-Za-z0-9]{36,}` | any line | **added** |
| `env-file-committed` | staged path basename `^\.env(\..+)?$` not ending `.example` | path rule | **added** |
| `env-assignment` | `(API_KEY\|SECRET\|TOKEN\|PASSWORD\|PASSWD\|PRIVATE_KEY)\s*=\s*\S+` | only files named `.env*` (not `.example`) | narrowed to `.env`-like files, per the skill's "in committed `.env` files" |
| `high-entropy-string` | candidate `[A-Za-z0-9+/]{32,}={0,2}` or `[0-9a-fA-F]{32,}` with Shannon entropy ≥ 3.5 bits/char, not UUID-shaped | any line, minus lockfile skip (D4) | entropy gate + UUID skip added |
| `generic-assignment` | `(password\|passwd\|secret\|token\|api[_-]?key)\s*[:=]\s*['"]?\S+` | source-ish files; fires only when the value is neither a placeholder nor a reference (D4) | placeholder/reference filter added |

- Additions, why: GitHub classic PATs are the most common leak class after AWS keys and the pattern is near-zero false positives; staging any real `.env` is itself the violation the skill's Rules forbid, even if its values look inert.
- Drops: none. Every skill pattern survives; the two scoping tweaks (env-assignment, generic-assignment) only reduce false positives, never coverage.
- Rule ids live in one ordered table (`RULES`) in the module; tests assert the exact id set so the skill↔scanner 1:1 mapping cannot silently drift.

## D4 — Placeholder / false-positive policy (default, in-code, narrow)

A finding is suppressed when **any** of:

1. **Path suffix**: file ends `.example`, `.sample`, `.template` (this is what `examples/mcp/opencode.mcp.json.example` and `.env.example` rely on).
2. **Placeholder value**: the matched value starts with or equals `your-`/`YOUR_`/`EXAMPLE_`/`changeme`/`CHANGEME`/`replace_me`/`replaceme`, is `<…>`-wrapped, `x`-run, `…`/`...`-tail, or is an env reference (`os.environ[…]`, `process.env…`, `$VAR`, `${VAR}`, `{env:VAR}`). `replace_me`/`replaceme` are value-shape placeholders like `changeme` — a marked slot to fill in — not path or substring exemptions.
3. **UUID shape**: `^[0-9a-f]{8}-[0-9a-f]{4}-…$` (run ledgers, session ids).
4. **Lockfile paths** (`package-lock.json`, `npm-shrinkwrap.json`, `yarn.lock`, `poetry.lock`, `Pipfile.lock`, `go.sum`, `Cargo.lock`): suppresses **only** `high-entropy-string` (integrity hashes); credential rules still fire there. The lockfile skip does not list `env-assignment` because that rule's scope requires a `.env*` basename, which no lockfile has — the entry would be unreachable.

- The allowlist is a **code constant in `secret_scan.py`**, not a data file. Why: an agent could edit a data file to silence the gate; an in-code edit shows up as a diff to a file reviewers must treat as security-sensitive. Every entry carries a comment naming the legitimate artifact it permits (`.env.example`, the skill's own regex docs, lockfiles).
- `--no-placeholder-filter` disables suppression for that run — used by tests to prove the filters are real, not rule rot.
- Over-broad skip-list risk (accepted + mitigated): a bare substring like `sk-` or a blanket `docs/` path skip would gut a rule — forbidden; entries are value-shapes and specific file names only, and any widening goes through code review with the entry's justification comment.
- The skill's own text is safe by construction: `sk-[A-Za-z0-9]{20,}` does not self-match (`[` ∉ the char class) and design docs must paste patterns, not live-format secrets.

## D5 — Content selection

- The commit gate scans the **staged diff only** (added/modified lines, new files included). Rationale: the gate's job is to stop what is about to be pushed; whole-tree scans re-litigate history the current commit cannot fix and slow every commit.
- History, rebase, and amend of pre-existing content are explicitly out of scope (D17, security.md incident runbook covers rotation).
- Not a git repo (`--staged`): exit 2. Empty stage: exit 0 `pass`.

## D6 — Commit-gate wiring in the orchestrator (base `prompts/orchestrator.md`)

Edit step 8 ("Commit and push") — add a gate sub-step with these required elements (implementer writes final prose, all elements mandatory):

1. Before every `git commit`, run: `timeout 60 python3 scripts/lib/secret_scan.py --staged`.
2. Exit 0 → commit. Exit 1 → **do not commit**; relay findings to a just-code variant to redact (replace with an env-var/secret-manager reference per the `secret-scrub` skill), re-run until clean. Exit 2 → do not commit; escalate to the user.
3. Relay findings using the scanner's masked output only — **never print full secrets**.
4. If the repo has no `scripts/lib/secret_scan.py` (non-base projects): apply the `secret-scrub` skill checklist on the staged diff manually. Never skip the check silently.
5. This gate **adds to** the existing approval gates (protected-branch push, deploy, destructive ops) — it does not replace or weaken them.

Mirror the same elements in base `grok/agents/orchestrator.md`. Rationale for prompt+script pairing: the script is the deterministic check; the prompt is what guarantees it runs at the right moment and defines fallback behavior where the script cannot exist.

## D7 — `pre-commit` hook and installer (base `scripts/install_secret_gate.sh`)

- New installer, base repo, `set -euo pipefail`, idempotent: writes `.git/hooks/pre-commit` only if absent or carrying our marker comment; refuses to overwrite a foreign hook; `--uninstall` removes marked hooks. `build.sh` must NOT call it (build never touches `.git`).
- Hook body: resolve scanner as (1) `./scripts/lib/secret_scan.py`, (2) `${GENERIC_DIR:-../open-agent-definitions}/scripts/lib/secret_scan.py`; if neither exists → `exit 0` with a stderr notice (**fail-open**, see D17); else `exec python3 "$SCANNER" --staged`.
- Deployment: `devops` runs the installer once in each repo during this MDU's deploy phase; `docs/security.md` documents it for other clones. `.git/hooks` is not committable, hence installer + docs instead of a tracked hook.
- Overlay never forks scanner logic — the resolution order above is the whole delegation story, and the absent-sibling case degrades to the prompt-level skill checklist.

## D8 — `just-code` hard constraint (base `prompts/just-code.md`)

Add to the "Hard constraints" block (mirrored into `grok/agents/just-code.md`, `-mid`, `-pro`):

1. **NEVER commit secrets** — no API keys, tokens, passwords, or private keys in code, config, or docs. If a secret is needed, reference an env var or secret manager (`os.environ["API_KEY"]`, `$API_KEY`, `{env:VAR}`) — never a hardcoded default.
2. Before reporting work done: `timeout 60 python3 scripts/lib/secret_scan.py --paths <files you changed>` (or the `secret-scrub` skill checklist if the script is absent); on findings, redact and re-run. Report findings masked only — never print full secrets.

## D9 — Overlay: `opencode_agents/grok/agents/grokestrator.md`

Add the D6 gate elements (command, exit-code handling, masked relaying, skill fallback) to its step-8 commit line (line 83) and "Hard constraints" block (line 121). No overlay snippet, no overlay scanner copy — grokestrator is a full-file override edited directly, per workspace steering (three orchestrator files, one change). Verified in deploy phase by grep of the merged `build/` output.

## D10 — Parity enforcement: new `ROLE_KEYWORDS` tuples (`scripts/lib/validate.py`)

```python
"orchestrator": [... existing ...,
    ("secret_scan.py",),
    ("never print full secrets",),
],
"just-code": [... existing ...,
    ("never commit secrets",),
    ("secret_scan.py",),
],
```

- All four substrings must appear in `prompts/orchestrator.md` + `grok/agents/orchestrator.md`, and in `prompts/just-code.md` + all three grok just-code mirrors. `./build.sh` fails if any mirror loses the clause (MDU-15 precedent).
- `grokestrator` is not in `GROK_MIRRORS` by design (it is not a base mirror); its compliance is checked by grep of the overlay build output during deploy (D15), not by base parity.

## D11 — `docs/security.md` outline (base, new file)

| § | Content | Backlog topic |
|---|---|---|
| 1 | Threat model & scope: autonomous agents with shell access committing to public/private remotes; what the posture does/doesn't cover | — |
| 2 | Least-privilege permissions: per-agent shell reality (orchestrator/just-code/test-agent/devops full; reviewers/qa read-only wall + `pytest*`/`./build.sh*`; introspector `python3 *`), cross-ref `docs/opencode-v2.md` §5 and `docs/design/mdu-30-shell-allowlist.md`, Hole 8 disclosure | 1 |
| 3 | Secret hygiene: the skill, the scanner CLI (usage + exit codes), placeholder/allowlist policy and its discipline, "never print full secrets", rotation-on-leak runbook (flag → rotate → purge history → note; history purge is manual) | 2 |
| 4 | Sandboxing options — devcontainer profile, E2B (ephemeral external execution), Firecracker (microVM): what each contains, cost, when to prefer; **documented options, not wired into the default loop** (this MDU documents, does not implement) | 3 |
| 5 | Approval gates: cross-ref `docs/autonomy.md` "The Four Approval Gates" + repository ownership; the secret gate as a new *mechanical* gate that adds to, never replaces, human gates | 4 |
| 6 | Known limits & incident runbook (mirrors D17) | — |

## D12 — `skills/secret-scrub/SKILL.md` update (base, small edit)

Add one line to the Workflow: if `scripts/lib/secret_scan.py` exists in the repo, run it — its rule set is this skill's pattern list; the manual checklist below is the fallback when it doesn't. Keeps skill ↔ scanner visibly 1:1 (AC1) without duplicating patterns in two places.

## D13 — Test plan (base, new `tests/test_mdu_11_secret_gate.py`)

`conftest.py` already puts `scripts/lib` on `sys.path` → unit tests `import secret_scan`; CLI tests use `subprocess.run([sys.executable, …])`.

| test | asserts |
|---|---|
| `test_rule_matrix_fires` | each rule id fires on a synthetic sample written to `tmp_path` and scanned with `--paths` |
| `test_placeholders_suppressed` | `.example` path, `your-`/`EXAMPLE_`/`<…>`/`changeme` values, `{env:VAR}` references → exit 0 |
| `test_placeholder_filter_is_real` | same samples with `--no-placeholder-filter` → exit 1 (proves suppression, not rule rot) |
| `test_lockfile_skip_is_narrow` | sha512 integrity hash in `package-lock.json` suppressed; a `ghp_…` value in the same file still fires |
| `test_exit_codes` | clean → 0; findings → 1; empty stage → 0; `--staged` outside a git repo → 2 |
| `test_output_never_contains_secret` | for every fixture: full value ∉ stdout/stderr/JSON; masked 4-char prefix present |
| `test_staged_diff_gate_rejects_realistic_secret` (AC2) | tmp git repo (`git init` in `tmp_path`, `git add`), staged file containing a realistic AWS key and an OpenAI-style key → `--staged` exits 1 with both rule ids and correct `file:line` |
| `test_hook_installer` | installer in tmp repo creates marked hook, is idempotent (run ×2), hook exits 1 on a staged secret, 0 on clean, 0 with stderr notice when no scanner resolves |
| `test_prompt_contract_mdu_11` | the four new clause substrings (D10) present in the two orchestrator files and four just-code files; `docs/security.md` exists with the four topic headings and cross-refs |
| `test_rule_ids_match_skill_set` | scanner rule id set == expected mapping of the skill's pattern list + 2 documented additions |

**Fixture discipline (AC2, "realistic"):** realistic-shape secrets are **constructed from concatenated fragments** in the test (`"AK"+"IA"+"IOSFODNN7"+"EXAMPLE"`, `"sk-" + seeded alnum(24)`, `secrets.token_hex(32)` for entropy, `"-----BEGIN RSA " + "PRIVATE KEY-----"` header which is itself a public pattern, not a secret). No contiguous live-format secret literal is committed anywhere; assertions check exit code, rule ids, `file:line`, and masked prefix, and explicitly assert the full value never appears in output — so even a failing test prints no secret.

## D14 — Who executes / who grades (verified against `opencode.json` + `docs/opencode-v2.md` §5)

| Phase | Commands | Executor (permissions) | Grader |
|---|---|---|---|
| Design | none (doc write) | architect (write tool only) | orchestrator reads doc |
| Implement | edits + targeted pytest | just-code (`shell * allow`) | code-reviewer sign-off (static — its read-only wall cannot execute tests) |
| Review | `git diff/log/show/status`, `grep/rg` | code-reviewer (deny wall + read-only allows) | orchestrator accepts sign-off |
| Test | full `timeout 120 python3 -m pytest tests/ -q` | test-agent (`shell * allow`) | orchestrator reads suite result |
| Deploy | base `timeout 60 ./build.sh`; overlay `./build.sh`; `./deploy.sh` dry-run; `scripts/install_secret_gate.sh` in both repos | devops (`shell * allow`) | orchestrator checks build output |
| Validate | `timeout 120 python3 -m pytest tests/ -q`, `./build.sh` | qa (`python3 -m pytest*`, `pytest*`, `./build.sh*` allows) | orchestrator grades PASS/FAIL |
| Commit | `timeout 60 python3 scripts/lib/secret_scan.py --staged` → commit/push | orchestrator (`shell * allow`) | gate exit code; non-zero blocks |

- **Do not widen any permission block in this MDU.** qa cannot invoke the scanner CLI and doesn't need to — the pytest suite covers it. introspector's `python3 *` allow could run it, but introspector stays non-gating by charter ("cannot run → note the skip; do not block").
- Reviewer instruction (goes in the review brief, not a prompt edit): treat any diff touching `secret_scan.py`'s rules or allowlist as security-sensitive.

## D15 — Cross-repo change order and green definitions

| # | Step | Green means |
|---|---|---|
| 1 | Base `mdu-11-secret-gate`: implement D1–D13 | `timeout 120 python3 -m pytest tests/ -q` — 314 existing + all new pass |
| 2 | Base `timeout 60 ./build.sh` | exit 0 — validator + parity pass with new `ROLE_KEYWORDS` tuples |
| 3 | Base MDU loop: review → test → deploy(build) → qa PASS → introspector (loop mode) | explicit reviewer sign-off; qa grade PASS |
| 4 | Base commit+push (gate runs on its own commit — dogfood) | scanner exit 0 on the staged MDU diff; push per ownership rules |
| 5 | Overlay `mdu-11-secret-gate`: D9 edit, then `./build.sh` | exit 0 (base gates inherited); merged build contains the gate clause (grep check) |
| 6 | Overlay `./deploy.sh` (dry-run), installer in both repos, overlay commit+push | dry-run exit 0; hooks installed and marked |
| 7 | `runs/mdu-11/manifest.json` written + `run_ledger.py validate` exit 0 | manifest conforms to the inline contract; note: base `runs/` is gitignored → local artifact |

Base first, then overlay, per workspace change order; commit and push each repo separately.

## D16 — Acceptance criteria → test/artifact mapping

| Criterion | Artifact(s) | Proof |
|---|---|---|
| AC1 skill exists & checklist followed by the commit gate | `skills/secret-scrub/SKILL.md` (D12), gate clause D6, `scripts/lib/secret_scan.py` | `test_prompt_contract_mdu_11` + `test_rule_ids_match_skill_set`; orchestrator prompt names the skill as fallback |
| AC2 realistic secret diff flagged/rejected by the gate | `scripts/lib/secret_scan.py`, `tests/test_mdu_11_secret_gate.py` | `test_staged_diff_gate_rejects_realistic_secret` (exit 1, rule ids, masked output, no secret in output) |
| AC3 `docs/security.md` documents full posture | `docs/security.md` (D11 outline, 4 topics + runbook) | `test_prompt_contract_mdu_11` asserts headings + cross-refs; qa reads it |
| AC4 (added) mirrors cannot silently drop the clause | `scripts/lib/validate.py` ROLE_KEYWORDS | parity suite (existing `test_validate_parity.py`) + new tuples; `./build.sh` fails on drift |
| AC5 (added) gate never leaks secrets itself | masking function + tests | `test_output_never_contains_secret` |
| AC6 (added) hook installable & idempotent | `scripts/install_secret_gate.sh` | `test_hook_installer` |

## D17 — Risks and known limits

| Risk / limit | Handling |
|---|---|
| Hole 8 (`cd … &&` redirect bypass of the deny wall) | harness-level, documented in security.md §2; not chased by rule reorder (MDU-30 decision stands) |
| Scanner self-modification: an agent could edit `secret_scan.py` (or its allowlist) to silence the gate | allowlist is in-code (not a data file) so the edit is a visible diff; review brief flags scanner diffs as security-sensitive; residual risk accepted |
| Entropy heuristic FNs (structured/low-entropy secrets) and FPs (minified blobs, hashes outside lockfiles) | lockfile skip is name-exact; new FP classes get a commented allowlist entry via review, never a blanket path skip |
| Adversarial evasion (splitting a secret across lines, base85, etc.) | out of scope for a regex+entropy gate; security.md recommends dedicated scanners (gitleaks/trufflehog) for high-stakes repos |
| Staged-diff-only: history rewrites (`filter-repo`, rebase, amend of old content) bypass the gate | rotation runbook in security.md §3; leak remediation is rotate-first |
| Hook fails open when no scanner resolves (overlay without base sibling) | deliberate: a fail-closed hook would brick commits on machines without the sibling; the orchestrator prompt gate + skill checklist are the primary layers, the hook is defense-in-depth |
| Prompt-following is model-dependent; repo has no CI runner | three layers (prompt clause, hook where installed, skill checklist); per-clone install documented |
| Placeholder values could shield a genuinely-named secret (real key literally `changeme`) | accepted; generic-assignment still fires on non-placeholder shapes; rotation policy covers leftovers |
