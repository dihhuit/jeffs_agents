# MDU-30 — Widen the deny-by-default per-agent shell allowlist

**Branch:** `mdu-30-shell-allowlist` (base). **Decision (fixed):** targeted allowlist expansion; deny-by-default stays; no blanket `shell * allow`.

**Revision 3 (QA Bug #1, HIGH — disclosed, no config change):** `cd <dir> && <allowlisted cmd> > <absolute path>` bypasses every redirect deny while the same command without the `cd` prefix is denied. Harness-level, pre-existing, not fixable by rule order; documented as §5 Hole 8 with an upstream follow-up, pinned by one additive test, and demoted to a disclosed-hole probe in §10. Config (`opencode.json`) unchanged.

**Revision 2 (review REJECT, 4 findings):** the wall gained the unspaced redirect trio (`*>/*`, `*>~/*`, `*>../*`), the null-sink exception (`*2>/dev/null*`, allow), the `sort` write guards (`*sort -o*`, `*sort*-o*`) and five git mutation verbs (`add`, `branch`, `tag`, `clone`, `worktree`); cwd-relative redirects are disclosed as an accepted hole instead of denied (§5 Hole 5). Wall size 29 → 40 entries. §3, §5, §9, §10 updated.

## 1. Problem (live-probe ground truth)

- Affected: qa/qa-pro/qa-free and code-reviewer/-pro/-free (allow `git diff*`, `git log*`, `git show*`, `grep *`, `rg *`), introspector (`python3 *`, `python *`). All: `shell * deny` first, last-match-wins per pipeline segment.
- Observed denials: `git diff | head -5`, `timeout 30 git log -1`, `git status -sb | head -5`, `ls`, `python3 -m pytest | tail -3`. Cost: mdu-29 reviewer 492s/22 events on a denied `git diff`; introspector blocked from `session_signals.py` 4 MDUs; mdu-28 QA pass 1 BLOCKED on denial.
- Unaffected/untouched: orchestrator, just-code*, test-agent*, devops* (allow-all); architect*, ui-ux-designer* (`npx *`), deep-research, inception (deny, zero exceptions); research family (`ask`, §8).

## 2. Matching semantics (observed; treat as the contract)

- Command splits into segments at `&&`, `||`, `;`, `|`; each segment matched against ordered rules, last match wins; one denied segment rejects the whole command (`permission.rejected: shell`).
- `cd <dir>` segments pass with no matching rule (OpenCode special-case; relied on, not changed).
- `*` matches any chars incl. spaces within one segment, never across segments. `git show*` already matches `git show-ref …` — no new rule needed.

## 3. The shared deny wall

The only broad new allow is `timeout *` (§6 explains why not enumerated `timeout *git log*` pairs). A broad allow passes anything after its token, so the trailing wall — the shell rules after every allow — keeps the sandbox meaningful. Every entry is `{"action":"shell","resource":R,"effect":E}`. The wall is **40 entries — 39 denies plus the one null-sink allow** — identical in all 11 blocks, in this installed order (`*python* -c*`, §4, is the 41st shell rule for qa/reviewers and rides between the exception and the tail):

```
# wall head — substitution, then every redirect that escapes cwd
"*$(*"   "*`*"                    # $()/backtick substitution inside an allowed segment (closes pre-existing grep * hole too)
"*> /*"  "*> ~/*"  "*> ../*"       # spaced:   cmd > /abs,  >> ~/file,  > ../file
"*>/*"   "*>~/*"   "*>../*"        # unspaced: cmd >/tmp/x, >>/home/u/.bashrc, 2>/etc/cron.d/x
# null-sink exception — the one ALLOW inside the wall
"*2>/dev/null*"  allow
# destructive / mutation classes
"rm *"  "* rm *"                   # rm at segment start; rm after an allowed prefix (timeout 30 rm -rf /)
"*xargs*"  "*sudo*"                # exec-from-stdin; privilege escalation
"cp *"  "* cp *"  "mv *"  "* mv *" # overwrite/move via the timeout prefix
"*curl*"  "*wget*"                 # downloaders: -o writes anywhere, pipe-to-sh
"*sh -c*"                          # sh/bash/zsh/dash -c ("sh -c" is a substring of "bash -c")
"* git push*"  "* git pull*"  "* git reset*"  "* git checkout*"  "* git restore*"
"* git switch*"  "* git clean*"  "* git stash*"  "* git commit*"  "* git rebase*"
"* git merge*"  "* git cherry-pick*"  "* git apply*"
"* git add*"  "* git branch*"  "* git tag*"  "* git clone*"  "* git worktree*"
"*sort -o*"  "*sort*-o*"           # sort is allowed plumbing, but -o writes
```

Why each revision-2 block exists:

- **Unspaced redirects.** `*> /*` requires a *literal space* after `>`. `git log --oneline -1 >/tmp/x`, `timeout 30 cmd >>/home/u/.bashrc` and `head f 2>/etc/cron.d/x` matched no entry and were allowed under `git log*` / `timeout *` / `head*`. The unspaced trio closes them. The spaced trio is kept because `cmd > /abs` is the common human form; both are needed.
- **Null-sink exception instead of a blanket `*>*` deny.** A blanket `*>*` (or even just `*>/*`) would deny `cmd 2>/dev/null`, because `/dev/null` is an absolute path and globs are string-level — no pattern can say "absolute path except `/dev/null`". `2>/dev/null` is everyday stderr suppression, not a write workflow, so instead of losing it the exception `*2>/dev/null*` is installed **after** the redirect denies (last match wins — it must outrank them) and **before** every destructive class *and before the `*python* -c*` guard* (it must not launder them). Verified by `test_null_sink_exception_is_not_a_general_write_launderer` and the `NULL_SINK_LAUNDER_REDS` matrix.
- **`sort -o`.** `sort*` is allowed because sorting is legitimate pipeline plumbing, but `sort -o <path> <input>` (and `-o` after other flags, `--output=`) writes. Two trailing denies: the reviewed literal `*sort -o*`, plus `*sort*-o*`, which also catches `sort -k2 -o out`, `sort -t. -o out` and `sort --output=out` — none of which contain the contiguous string `sort -o`. Both are trailing so no allow can outrank them.
- **Git mutation class, round 2.** `git add`, `git branch`, `git tag`, `git clone` and `git worktree` are reachable through `timeout *`, which allow-lists `timeout 30 <anything>`. `* git add*` only fires with a space before `git`, so the allow prefix (`timeout 30 `) is still required — a bare `git add -A` is stopped by the first `shell * deny`, as intended.

Segment-start destructive commands (`rm -rf /`, `git reset --hard`, `git push`) need no wall entry — no allow matches them; the first `shell * deny` rejects. Contains-form denials can false-positive on arguments containing the same words (`git log --grep ' git push'`); contrived for these roles, accepted.

## 4. Final blocks (insert inside the existing shell run; non-shell rules stay byte-identical, same order)

### 4.1 code-reviewer / -pro / -free — after the `rg *` allow, before `read`:

```json
{ "action": "shell", "resource": "git status*",   "effect": "allow" },
{ "action": "shell", "resource": "ls*",           "effect": "allow" },
{ "action": "shell", "resource": "head*",         "effect": "allow" },
{ "action": "shell", "resource": "tail*",         "effect": "allow" },
{ "action": "shell", "resource": "wc*",           "effect": "allow" },
{ "action": "shell", "resource": "sort*",         "effect": "allow" },
{ "action": "shell", "resource": "timeout *",     "effect": "allow" },
```
…then the §3 wall, except that `*python* -c*` is installed between the null-sink exception and the destructive classes (so the exception cannot launder it):

```json
{ "action": "shell", "resource": "*$(*",  "effect": "deny" },   // §3 wall head
…
{ "action": "shell", "resource": "*2>/dev/null*", "effect": "allow" },
{ "action": "shell", "resource": "*python* -c*", "effect": "deny" },
{ "action": "shell", "resource": "rm *",   "effect": "deny" },  // §3 wall tail
…
```

### 4.2 qa / qa-pro / qa-free — same as 4.1, plus after `timeout *`:

```json
{ "action": "shell", "resource": "python3 -m pytest*", "effect": "allow" },
{ "action": "shell", "resource": "pytest*",             "effect": "allow" },
{ "action": "shell", "resource": "./build.sh*",         "effect": "allow" },
```
…then the §3 wall with `*python* -c*` placed after the null-sink exception (same position as §4.1). pytest/`./build.sh` execute repo code by design — in-scope trust for the validator role; reviewers only read diffs, so they get neither.

### 4.3 introspector — keep `python3 *` / `python *` (MDU-19 trust, unchanged); after `python *`:

```json
{ "action": "shell", "resource": "ls*",       "effect": "allow" },
{ "action": "shell", "resource": "head*",     "effect": "allow" },
{ "action": "shell", "resource": "tail*",     "effect": "allow" },
{ "action": "shell", "resource": "wc*",       "effect": "allow" },
{ "action": "shell", "resource": "sort*",     "effect": "allow" },
{ "action": "shell", "resource": "timeout *", "effect": "allow" },
```
…then the §3 wall WITHOUT `*python* -c*` (inline python is part of introspector's by-design python trust). No git allows: minimality — no observed need; it has the read tool. The null-sink exception is still installed (it is not python-specific).

## 5. What the globs match; residual holes (named)

- `head*` does NOT let `sh -c 'rm -rf /'`: that segment matches no allow; `*sh -c*` denies it even under `timeout *`. `timeout *` DOES allow `timeout 30 <anything>` — the wall is the only guard, hence it must be trailing.
- Hole 1: `timeout N <interpreter> <inline code>` with no wall-matching strings (`timeout 30 node -e '…'`); `*python* -c*` closes the python form for qa/reviewers. Glob walls are string-level, not semantic — a determined child escapes. Accepted: observed failures are agents wanting read/pytest, not malice. Revisit trigger: any observed adversarial use.
- Hole 2: wall-list-external destructive binaries under `timeout *` (`dd`, `shred`, `chmod`, `chown`, `truncate`) — the wall is a floor, not a ceiling.
- Hole 3: introspector `python3 *` is arbitrary execution by design (subprocess); its wall is defense-in-depth for shell-level strings only.
- Hole 4: if OpenCode's splitter is quote-aware, `;`/`|` inside quotes stay in-segment (wall `* rm *` still catches `…; rm …`); if naive, they split and rule 1 denies. Either way §10's red probes are the gate.
- Hole 5 (**disclosed, not denied**): **cwd-relative redirects.** `head -5 f >> ./prompts/qa.md`, `grep x README.md > README.md` (truncate) and `timeout 30 x >> ./.git/hooks/pre-commit` match no wall entry: the target is not absolute, not `~`, not `../`, so neither the spaced nor the unspaced redirect denies fire. Why disclosure was chosen over denial:
  (a) the only blanket alternative is `*>*`, and a glob cannot distinguish `> file` from `2>/dev/null`. Denying it breaks the most common shell suffix and would re-create the very problem MDU-30 fixes — agents blocked on ordinary commands — for a workflow §12 records **zero** observations of;
  (b) the wall exists for the *observed* failure mode (accidental sprawl under a broad `timeout *` allow), not for a malicious child; a child that wants to damage the tree already has Hole 1/2 open, and files it can truncate this way are ones its `edit`/`write` policy already governs;
  (c) a deny that agents trip over daily gets worked around or switched off, which is strictly worse than a named, monitored hole.
  Revisit trigger: the first observed cwd-relative redirect in a run log. Closing it later is additive: insert `*>*` in the wall head and keep the existing null-sink exception after it.
- Hole 6: **null-sink + later redirect.** `head f 2>/dev/null > ~/x` is allowed: the exception outranks the redirect denies and a glob cannot look at position. It requires the literal `2>/dev/null` *and* a second redirect to launder, and it does **not** launder any destructive class (`rm`, `sort -o`, `cp/mv`, `*python* -c*` all sit after it — see the `NULL_SINK_LAUNDER_REDS` matrix). Accepted; revisit with Hole 5.
- Hole 7: `sort` write forms that contain neither `-o` nor a contiguous `sort -o` — e.g. `sort -no out file` (`-n` and `-o` in one cluster). `*sort*-o*` closes the realistic forms (`-k2 -o`, `-t. -o`, `--output=`). Accepted: contrived, same class as Hole 2.
- Hole 8 (**disclosed, not fixable by rule order — harness-level**): **a `cd … &&` prefix bypasses every redirect deny.** Exact repros, spaced and unspaced, any absolute target:
  `cd /repo && git log --oneline -1 >/tmp/opencode/out` · `cd /repo && git log --oneline -1 > /tmp/opencode/out` · `cd /repo && timeout 30 git log -1 >>/home/user/.config/opencode/opencode.json`.
  Both forms **execute** (QA-verified live: the first created `/tmp/opencode/mdu30-red-probe.txt`; a `cd` variant also created a 0-byte file at a non-scratch absolute path). The **identical command with no `cd` prefix** (working directory supplied by the tool) is correctly **DENIED** — all six redirect denies fire (`*> /*`, `*> ~/*`, `*> ../*`, `*>/*`, `*>~/*`, `*>../*`).
  Why this is not a rule-ordering defect and not a regression: the wall is installed in the reviewed order and demonstrably works when no `cd` is present; a reordered deny cannot fire on a segment whose redirect the matcher never sees. Before MDU-30 there were no redirect rules at all, so `cd X && git log >/path` was allowed then too — this cycle did not introduce it.
  Working hypothesis: the harness treats the `cd … &&` prefix as a special case and strips/re-shapes the redirect string before glob matching, so the remaining segment (`git log --oneline -1`) matches the `git log*` allow and nothing else is checked. The rules are correct; the input has been rewritten underneath them.
  Impact: a `cd`-prefixed allowlisted command can truncate or overwrite **any user-writable absolute path** — including `~/.config/opencode/opencode.json`, a repo's `opencode.json`, and `prompts/*.md`. `edit * deny` does **not** constrain shell redirects: it governs the `edit` tool only, so there is no second line of defense behind the wall.
  Disposition: **disclosed, not denied.** It cannot be closed by adding or reordering config rules; closing it requires the harness fix in the Upstream follow-up note below. Do not "repair" it by juggling wall position — that changes nothing and hides the hole.
- **Upstream follow-up (Hole 8):** this warrants an OpenCode harness bug report — redirect strings appear to be stripped before glob matching when the command carries a `cd … &&` prefix, while the same command without a prefix is matched correctly. Until that is fixed, treat `cd <dir> && <allowlisted cmd> > <absolute path>` as unguarded and keep §10's disclosed-hole probe in the matrix.


## 6. Rejected additions (minimality — every added pattern is a hole)

- `find *` — `-exec`/`-delete` are destructive flags; the glob tool covers discovery.
- `sed -n *` — still matches `sed -n -i …` (in-place edit); read/grep cover the need.
- `cat *` — read tool covers it; not in observed failures.
- `git branch*` — `git status -sb` already shows branch state; `git branch <name>` creates refs.
- Enumerated `timeout *git log*`-style pairs — explosion per future command, and contains-globs match smuggled code inside quotes (`timeout 30 sh -c 'pytest; rm -rf'` contains "pytest"). One broad allow + greppable wall is more auditable.

## 7. Overlay grok-* mirrors — YES (same MDU, after base is green)

Edit `opencode_agents/opencode.json`: `grok-qa`, `grok-qa-pro` get §4.2; `grok-code-reviewer`, `grok-code-reviewer-pro` get §4.1. Same prompts, same repos, same OpenCode permission engine (xai models) → identical failure mode; otherwise base agents work while overlay mirrors stay broken. Accompanying fix, same edit: the grok-code-reviewer* blocks have no read/glob/grep/list allows at all (unlisted actions default to deny, so those mirrors cannot read files today) — add those four allows. Leave `grokestrator` (allow-all), `grok-architect*`, `grok-plan`, `grok-ui-ux*`, `thought-leadership-coach`, grok-research/grok-deep-research untouched.

## 8. Research family `effect: ask` — DEFERRED

`ask` auto-denies in headless children, but (a) it exists for the MDU-21 free-tier gateway quirk (shell must stay in the toolset or the gateway rejects the request) — changing it needs a fresh gateway probe; (b) zero observed research-agent shell failures; they have webfetch/websearch/read tools. If observed later, reuse the §3–§4 pattern.

## 9. Test plan

New `tests/test_mdu_30_shell_allowlist.py` (naming per `test_mdu_24_*`/`test_mdu_28_*`). No existing file changes: the mdu-21 permission tests (`_check_scratch_permissions` params in `tests/test_validate_integration.py`) cover only the top-level scratch array — untouched, stays green; per-agent ordering had no prior test — that is the gap this closes.

1. Structure (order-sensitive), all 7 base agents: first shell rule is `* deny`; every allow except the null-sink exception sits between it and the wall head; the single in-wall allow is exactly `*2>/dev/null*`, positioned after the six redirect denies and before every destructive class (and before `*python* -c*` where present); the wall tail is the trailing run of shell rules; the non-shell rule sequence equals the pre-change sequence verbatim (hard-code it; `subagent research` allow still precedes `subagent * deny` where present).
2. Reference evaluator: split on `|`, `&&`, `||`, `;` (naive split; in-test comment says it mirrors observed behavior, not a proof), match each segment with `fnmatch.fnmatchcase`, last-match-wins. Assert GREEN matrix = §10 greens, RED matrix = §10 reds, against the qa, code-reviewer, and introspector permission lists.
3. Mutation checks: (a) move the first `shell * deny` after the allows → all greens flip to DENY; (b) move every wall deny (head + tail) above the allows → all reds flip to ALLOW, including the unspaced-redirect, `sort -o`/`--output`, git-verb and null-sink-launder reds; (c) with the wall moved, `git reset --hard HEAD~1` stays DENY (it is caught by deny-first, not the wall). Proves order-dependence is guarded, not accidental.
   3b. Null-sink contract: `head -5 f 2>/dev/null` and `python3 -m pytest … 2>/dev/null` are green, while `rm -rf x 2>/dev/null`, `sort -o out in 2>/dev/null` and `python3 -c … 2>/dev/null` stay red — the exception must not launder a class.
4. Regression net: `validate.main` still exits 0 on the edited `opencode.json` (validator NOT modified — it only checks top-level scratch permissions; the schema's action/resource/effect + `allow|deny|ask` enum accepts every new entry).

## 10. Live probe matrix (post-deploy empirical gate; child runs the exact command and reports raw output/error)

GREEN (must return real output): `git diff --stat HEAD~1 HEAD | head -5` · `timeout 30 git log --oneline -1` · `git status -sb | head -5` · `ls docs/design` · qa: `timeout 120 python3 -m pytest tests/ -q | tail -3` and `timeout 300 ./build.sh` · introspector: `timeout 60 python3 -m pytest tests/test_session_signals.py -q | tail -3` · **null-sink** (must stay green): `head -5 README.md 2>/dev/null`, qa: `python3 -m pytest tests/ -q 2>/dev/null | tail -3`.
RED (must return `permission.rejected: shell`; orchestrator pre-creates a throwaway fixture — junk files plus a scratch clone at `/tmp/opencode/mdu30-red` — so nothing real is at risk): `git reset --hard HEAD~1` (in fixture) · `timeout 30 git push --dry-run origin HEAD:refs/heads/mdu30-red-probe` · `timeout 30 rm -rf /tmp/opencode/mdu30-red/junk` · `head $(echo pwned)` · `git log --oneline -1 > /tmp/opencode/mdu30-red/out` · `timeout 30 sh -c 'git push'` · `timeout 30 curl http://example.com -o /tmp/opencode/mdu30-red/f`. Revision-2 additions, all in the same fixture:

- **unspaced redirects**: `git log --oneline -1 >/tmp/opencode/mdu30-red/out` · `timeout 30 head -5 notes.md >>/home/user/.bashrc` (use a fixture-HOME path in the probe) · `head f 2>/etc/cron.d/x`
- **sort writes**: `sort -o /tmp/opencode/mdu30-red/out notes.md` · `sort -k2 -o /tmp/opencode/mdu30-red/out notes.md` · `sort --output=/tmp/opencode/mdu30-red/out notes.md`
- **git mutation verbs under `timeout *`**: `timeout 30 git add -A` · `timeout 30 git branch mdu30-red` · `timeout 30 git tag mdu30-red` · `timeout 30 git clone /tmp/opencode/mdu30-red repo` · `timeout 30 git worktree add /tmp/opencode/mdu30-red wt`
- **null-sink does not launder**: `timeout 30 rm -rf /tmp/opencode/mdu30-red/junk 2>/dev/null` · `sort -o /tmp/opencode/mdu30-red/out notes.md 2>/dev/null` (qa/reviewer only) `python3 -c 'print(1)' 2>/dev/null`
- **cwd-relative redirect is a DISCLOSED hole (§5 Hole 5)**: `git log --oneline -1 > out.txt` is expected to ALLOW. Do not record it as a probe failure.
- **cd-prefixed redirect is a DISCLOSED hole (§5 Hole 8)**: `cd <fixture> && git log --oneline -1 >/tmp/opencode/mdu30-red/out` and the spaced form `cd <fixture> && git log --oneline -1 > /tmp/opencode/mdu30-red/out` are expected to ALLOW (harness strips the redirect around the `cd … &&` special case). Probe them into the throwaway fixture, then delete the file; do not record them as probe failures. The **same strings with no `cd` prefix** — `git log --oneline -1 > /tmp/opencode/mdu30-red/out` (RED list above) and `git log --oneline -1 >/tmp/opencode/mdu30-red/out` (unspaced list above) — remain **reds** and must return `permission.rejected: shell`. That contrast is the evidence the wall itself is intact.
Overlay: repeat greens 1–4 and reds 2–4 via `grok-qa` after overlay deploy. Spot-check orchestrator/just-code still allow `git status -sb | head -5`.

## 11. Rollout (cross-repo order per workspace AGENTS.md)

1. Base: edit `opencode.json` (7 agents only) and `docs/opencode-v2.md` §5 in the same MDU — the "copy installed order verbatim" bullet gets: the seven affected families use `shell * deny` → expanded read-only allows → trailing wall per this design; all other agents keep installed order verbatim; any future broad `token *` allow must carry the wall.
2. Grep `prompts/qa.md`, `prompts/code-reviewer.md`, `prompts/introspector.md` for wall-class commands — expect zero; any hit is a prompt/config conflict to resolve before merge.
3. Base gates: `python3 -m pytest tests/ -q` green; `./build.sh` green.
4. Commit base on `mdu-30-shell-allowlist`; merge per normal MDU flow after QA PASS.
5. Overlay: edit `opencode.json` per §7; `./build.sh` (re-runs base build + merge + base validator); `./deploy.sh --force`.
6. Live re-probe §10; record evidence in the run manifest; commit/push overlay separately.

## 12. Risks

- Holes 1/2 (§5): `timeout *` + interpreters/binary-of-the-day — accepted, revisit trigger defined.
- Redirect denies (spaced and unspaced) block every absolute-path write, including `> /tmp` — pipe instead; if a real workflow needs it, add one `*> /tmp/*` allow placed BEFORE the redirect denies (last-match-wins), only if observed.
- Null-sink exception (`*2>/dev/null*`) is the only allow inside the wall. It is order-critical twice: after the redirect denies (else useless) and before `*python* -c*` and the destructive classes (else a launderer). Both are asserted in `tests/test_mdu_30_shell_allowlist.py`; do not move it when editing the wall.
- Cwd-relative redirects stay open by decision (§5 Hole 5) — a future reviewer must not treat it as a regression without also supplying the observed-workflow trigger.
- `cd … &&` prefixed redirects stay open by harness behavior (§5 Hole 8): not a rule-ordering problem, not a regression, and not closable from config. A reviewer must not "fix" it by moving wall entries — file the upstream harness bug instead.
- Splitter/glob model drift: tests mirror observed behavior; the live probes are the gate.
- Wall false positives on argument substrings (§3) — contrived, accepted.
- Overlay drift if mirrors lag base — §7 keeps them in the same MDU.

## 13. Acceptance criteria

1. `git diff` on base touches only the 7 agent blocks in `opencode.json`, §5 of `docs/opencode-v2.md`, and the new test file; every other agent is byte-identical.
2. Structure test green for all 7 agents: deny-first, allows per §4, single null-sink allow in the documented wall position, wall tail trailing, non-shell sequence unchanged.
3. Evaluator green/red matrices pass; both mutation checks flip exactly as specified in §9.3.
4. `python3 -m pytest tests/ -q` and `./build.sh` green in base; validator file unmodified.
5. Overlay build green; 4 grok mirrors carry identical blocks (+ read-class allows on grok-code-reviewer*).
6. Post-deploy: every §10 green returns output, every red returns `permission.rejected: shell`, including grok-qa overlay probes; orchestrator/just-code spot-check unaffected.
7. `docs/opencode-v2.md` no longer contradicts the installed config.
8. No prompt file changed; no blanket `shell * allow` added anywhere.

## Out of scope

- Blanket `shell * allow` for any family (fixed user decision).
- Research-family `ask` semantics (§8) — needs its own free-tier gateway probe.
- architect/ui-ux*/deep-research/inception deny blocks; pre-existing `npx *` on ui-ux-designer* (a broad allow without a wall — apply the wall template in a future MDU, not here).
- Introspector's `python3 *` trust (shipped MDU-19 behavior).
- OpenCode matcher semantics themselves (harness-level).
