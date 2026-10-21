# Security Posture

How this agent team handles credentials, permissions, and blast radius, and
where the posture stops. Companion documents: `docs/autonomy.md` (approval
gates and the autonomy ladder), `docs/opencode-v2.md` §5 (permission ordering),
`docs/design/mdu-30-shell-allowlist.md` (the shell deny wall), and
`skills/secret-scrub/SKILL.md` (the human checklist).

## 1. Threat model and scope

The loop runs autonomous agents that can edit files, run shell commands, and
commit and push to repositories the user owns. The realistic ways a run leaks
credentials or causes damage:

| Threat | Example | Primary control |
| --- | --- | --- |
| Secret committed in a diff | A key pasted into source, config, or docs | Workflow transcript detection (MDU-11) |
| Secret exposed in output | A full key echoed into logs or a report | Masking rule in the skill, scanner, and prompts |
| Unintended shell side effects | Redirect clobbering a file outside the repo | Shell deny wall (MDU-30) |
| Destructive operation | History rewrite, delete, DB migration | Human approval gates (MDU-12) |
| Push to the wrong repository | Upstream issue/PR on a third-party repo | Repository ownership rule |

What this posture **does** cover: preventing a newly staged credential from
being committed in this repo (prompt gate plus optional pre-commit hook),
keeping secrets out of agent output, and requiring human sign-off before
irreversible actions.

What it **does not** cover: a malicious dependency, a compromised model
provider, secrets that already exist in history, adversarial evasion of the
regex scanner (splitting a value across lines, alternate encodings), and
host-level isolation. Those are named as known limits in §6.

## 2. Least-privilege permissions

Each agent's shell access is scoped in `opencode.json`; the installed rule
order is behavior because the harness uses last-match-wins (see
`docs/opencode-v2.md` §5 — do not reorder rules without reading it).

| Agent group | Shell reality |
| --- | --- |
| orchestrator, just-code variants, test-agent variants, devops variants | Full shell `allow` — they implement, test, build, and deploy |
| code-reviewer variants, qa variants | `shell * deny` wall, then read-only allows (`git status`, `ls`, `head`, `tail`, `wc`, `sort`, `timeout`); qa adds `python3 -m pytest`, `pytest`, and `./build.sh` |
| introspector | Read-only allows plus `python3 *` / `python *`; it never gates |

The deny wall blocks command substitution, spaced and unspaced redirects,
destructive classes, git-mutation commands, and inline Python outside the
reviewers' narrow allows. Exact snippets and the probe matrix live in
`docs/design/mdu-30-shell-allowlist.md`.

**Known limit — Hole 8.** A `cd <dir> && <allowlisted command>` prefix defeats
the redirect denies for an absolute target (`cd /repo && git log -1
>/tmp/out` is allowed, while the same command without the `cd` prefix is
denied). This is harness behavior, not a rule-ordering bug; reordering the
wall does not close it. Treat `cd … &&` with a redirect as unguarded and do
not route secrets or protected files through it.

## 3. Secret hygiene

### The skill

`skills/secret-scrub/SKILL.md` is the checklist every committing agent loads.
Its pattern list is the scanner's rule set; the manual checklist is the
fallback when the scanner is unavailable.

### The scanner

`scripts/lib/secret_scan.py` is stdlib-only, offline, and deterministic. It
scans **added/modified lines of the staged diff** by default, so it checks
exactly what the next commit would publish.

```
python3 scripts/lib/secret_scan.py --staged                  # commit gate (default)
python3 scripts/lib/secret_scan.py --paths <file> [...]      # ad-hoc, full-file scan
python3 scripts/lib/secret_scan.py --staged --json           # machine-readable report
python3 scripts/lib/secret_scan.py --paths <file> --no-placeholder-filter  # filter self-test
```

Exit codes:

| Code | Meaning | Action |
| --- | --- | --- |
| 0 | Clean, including an empty stage | Commit may proceed |
| 1 | Findings | Do not commit; redact, then re-run |
| 2 | Operational failure (not a git repo, unreadable file) | Do not commit; escalate |

Exit 2 fails closed on purpose: an unrunnable check is not a passing check.

Output is masked in one function before any emit. Human mode prints one line
per finding, `<file>:<line> <rule-id> <first-4-chars>…`; JSON mode adds a
`{"status","scanned","findings"}` envelope with a masked `preview`. **Never
print full secrets** — not in a report, a diff, a chat message, or a commit
message. Four characters are enough to identify the finding.

Rule ids: `aws-access-key-id`, `openai-style-key`, `private-key-block`,
`github-pat`, `env-file-committed`, `env-assignment`, `high-entropy-string`,
`generic-assignment`. Six of the eight map onto the skill's patterns; GitHub
PATs and committed `.env` files are the two documented additions. The entropy
and assignment rules carry the skill's false-positive filters.

### Placeholder and allowlist policy

Suppression exists so templates and documentation remain usable. A finding is
suppressed when any of the following holds:

- The path ends `.example`, `.sample`, or `.template` (for instance, the
  repository's `.env.example` and MCP config templates).
- The matched value is a placeholder: a `your-`/`YOUR_`/`EXAMPLE_` prefix,
  `changeme`, an angle-bracket value, an all-`x` run, a trailing ellipsis, or
  an environment reference (`$VAR`, `${VAR}`, `{env:VAR}`,
  `os.environ[...]`, `process.env...`).
- The value is UUID-shaped (run ledgers and session ids).
- The file is an exact lockfile name (`package-lock.json`, `yarn.lock`,
  `go.sum`, and peers) **and** the rule is the entropy rule (integrity hashes
  are expected there). A credential literal in a lockfile still fires; the
  `.env`-scoped rule never applies to lockfiles.

Discipline: the allowlist is an in-code constant in `secret_scan.py`, not a
data file, so silencing the gate shows up in review as a diff to a
security-sensitive file. Every entry carries a comment naming the legitimate
artifact it permits. Blanket path skips (`docs/`) and bare-substring
exemptions such as `sk-` are forbidden — they would gut a rule while looking
like a fix. `--no-placeholder-filter` exists so tests can prove the filters
are real rather than rule rot.

### Optional pre-commit hook

`scripts/install_secret_gate.sh` writes a marked `.git/hooks/pre-commit` that
runs the scanner on the staged diff. Run it once per clone:

```
scripts/install_secret_gate.sh             # install (idempotent)
scripts/install_secret_gate.sh --uninstall # remove the managed hook
```

The installer refuses to overwrite a foreign hook, and only removes hooks
carrying its marker comment. `build.sh` never calls it — build does not touch
`.git`. Hooks are not committable, which is why this is an installer plus
documentation.

The hook resolves the scanner at `./scripts/lib/secret_scan.py` first, then at
`${GENERIC_DIR:-../open-agent-definitions}/scripts/lib/secret_scan.py`. When
neither exists it exits 0 with a stderr notice (deliberate fail-open: a
fail-closed hook would block every commit on machines without the sibling
repo). The prompt-level gate and the skill checklist remain the primary
layers; the hook is defense-in-depth.

### Rotation on leak

If a live secret reaches a commit, in this order:

1. **Flag** it to the user and the orchestrator with `file:line`, rule id, and
   the masked prefix only.
2. **Rotate** the credential at the provider. Rotation comes first because
   history cleanup cannot un-publish a pushed secret.
3. **Purge** it from history — a manual, human-approved operation
   (`git filter-repo` or the provider's tooling). Rewrites are destructive:
   they require approval and coordination with every clone. Local commits
   that were never pushed can simply be amended.
4. **Note** the incident (what leaked, where, rotation time, purge status) so
   the next run does not re-introduce the value.

## 4. Sandboxing options (documented, not wired in)

The default loop runs agents on the host with the permission rules above. The
options below are **not** wired into the default loop; they are documented so
a user can choose stronger isolation for high-stakes work.

| Option | What it contains | Cost / trade-off | Prefer when |
| --- | --- | --- | --- |
| Devcontainer profile | Runs the agent and toolchain inside a container with only the workspace mounted; limits host filesystem and credential reach | Extra image build and mount wiring; MCP and harness config must be reproduced inside the container | Repos with broad shell allows and no host-level secrets |
| E2B (ephemeral external execution) | Sends command execution to a disposable remote sandbox; the host keeps only the repo | Network round-trips, sandbox lifetime, data leaves the machine | Untrusted code, or when the host holds unrelated credentials |
| Firecracker (microVM) | Hardware-virtualized microVM per run; strongest isolation with fast boot | Operational complexity (KVM, image management) | Regulated or high-value environments, CI runners |

Selection guidance: containers for everyday isolation; E2B when execution
must be remote and disposable; Firecracker when the workload justifies a
microVM control plane. None of them replaces the secret gate — a sandbox
limits blast radius, it does not stop a credential from being committed.

## 5. Approval gates

`docs/autonomy.md` defines the four human approval gates: pushing to protected
branches, deploying a non-green MDU to production, destructive operations,
and a fourth fix-retry on the same issue. The repository-ownership rule is the
fifth boundary: writes go only to repositories the user owns, and every
action against any other remote needs explicit per-action approval.

The secret gate is a **mechanical** gate that adds to those human gates: it
runs on every commit and blocks on a non-zero exit without asking anyone.
Passing it does not authorize a push, a deploy, or a history rewrite, and it
does not weaken any existing gate. When the mechanical gate and a human gate
disagree, the human gate wins — stop and ask.

## 6. Known limits and incident runbook

Known limits:

- **Regex plus entropy is a heuristic.** Structured or low-entropy secrets can
  slip through; minified blobs and unusual hashes can false-positive. New
  false-positive classes get a commented allowlist entry through review, never
  a blanket skip. High-stakes repositories should add a dedicated scanner
  (gitleaks, trufflehog) in CI in addition to this gate.
- **Staged-diff scope.** The gate checks what is about to be committed, not
  history. Amends, rebases, and history rewrites of old content bypass it —
  hence rotation-first remediation.
- **Adversarial evasion** (splitting a value across lines, alternate
  encodings) is out of scope for this scanner; treat it as a determined
  insider, not a guardrail case.
- **Staged binaries are not scanned.** Binary diffs emit no text hunks, so the
  gate sees nothing in them and a secret embedded in a staged binary bypasses
  it. Keep secrets out of binaries and scan build artifacts with a dedicated
  tool; treat an added binary in a diff as a manual-review item.
- **Prompt-following is model-dependent.** Three layers compensate: the
  orchestrator prompt clause, the hook where installed, and the skill
  checklist. There is no CI runner enforcing the prompt layer.
- **The scanner can be edited** by an agent with write access. Keeping the
  allowlist in code makes that edit visible; treat any diff touching
  `secret_scan.py`'s rules or allowlist as security-sensitive in review.
- **Hole 8** (§2) leaves redirects behind a `cd … &&` prefix unguarded.

Incident runbook (suspected or confirmed leak):

1. Stop the commit or push; do not rewrite anything yet.
2. Rotate the credential (§3 rotation-on-leak, step 2) — assume it is public.
3. Remove the value from the working tree and stage the redacted replacement.
4. Re-run the scanner until it exits 0.
5. Only then decide, with the user, whether history needs purging and whether
   the push can proceed.
6. Record the incident note; escalate to the user for any further push or
   history rewrite.
