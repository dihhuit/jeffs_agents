"""Regression contracts for MDU-30 (deny-by-default shell allowlist, widened).

Live probes before MDU-30 showed `qa`/`code-reviewer`/`introspector` denying
ordinary read-only pipelines (`git diff | head -5`, `ls docs/design`,
`python3 -m pytest | tail -3`). MDU-30 keeps `shell * deny` first, expands the
read-only allows, and appends a trailing deny wall so the one broad allow
(`timeout *`) cannot be used as a prefix to smuggle a mutation.

Ordering is behavior here (last match wins, per pipeline segment), so the
structure checks are order-sensitive and the evaluator below is an independent
reference implementation of the observed semantics:

* the command splits into segments at ``&&``, ``||``, ``;`` and ``|`` (naive
  split — this mirrors observed behavior, it is not a proof of the harness);
* ``cd <dir>`` segments pass with no matching rule (OpenCode special case);
* inside a segment ``*`` matches any chars including spaces, never across
  segments (``fnmatch.fnmatchcase``);
* the last matching rule for a segment wins; one denied segment rejects the
  whole command.

Revision 2 (review) adds the unspaced redirect forms to the wall, the
`sort -o` write guard, the missing git mutation verbs, and the single
`2>/dev/null` null-sink exception that sits inside the wall after the redirect
denies and before every destructive class. Cwd-relative redirects stay
disclosed, not denied (design §5).

Design doc: ``docs/design/mdu-30-shell-allowlist.md`` (§3 wall, §4 blocks,
§9 test plan, §10 probe matrix).
"""

from __future__ import annotations

import fnmatch
import json
import re
import shutil
from pathlib import Path

import pytest

import validate

REPO_ROOT = Path(__file__).resolve().parents[1]
OPENCODE_JSON = REPO_ROOT / "opencode.json"
VALIDATOR = REPO_ROOT / "scripts" / "lib" / "validate.py"

ALLOW = "allow"
DENY = "deny"

# ---------------------------------------------------------------------------
# expected shape (§4). (resource, effect) pairs, in installed order.
# ---------------------------------------------------------------------------

READ_ONLY_ALLOWS = [
    ("git status*", ALLOW),
    ("ls*", ALLOW),
    ("head*", ALLOW),
    ("tail*", ALLOW),
    ("wc*", ALLOW),
    ("sort*", ALLOW),
    ("timeout *", ALLOW),
]

QA_ALLOWS = READ_ONLY_ALLOWS + [
    ("python3 -m pytest*", ALLOW),
    ("pytest*", ALLOW),
    ("./build.sh*", ALLOW),
]

INTROSPECTOR_ALLOWS = [
    ("ls*", ALLOW),
    ("head*", ALLOW),
    ("tail*", ALLOW),
    ("wc*", ALLOW),
    ("sort*", ALLOW),
    ("timeout *", ALLOW),
]

PYTHON_C_DENY = ("*python* -c*", DENY)

# §3 — the shared wall. Spaced AND unspaced redirects: `*> /*` needs a literal
# space, so `>/tmp/x`, `>>/home/u/.bashrc` and `2>/etc/cron.d/x` slipped past it
# before MDU-30 revision 2.
WALL_HEAD = [
    ("*$(*", DENY),
    ("*`*", DENY),
    ("*> /*", DENY),
    ("*> ~/*", DENY),
    ("*> ../*", DENY),
    ("*>/*", DENY),
    ("*>~/*", DENY),
    ("*>../*", DENY),
]

# The one allow inside the wall. `2>/dev/null` is the standard stderr sink and
# must keep working, but a glob cannot tell `/dev/null` from any other absolute
# path, so the exception is the literal form only and it sits *after* the
# redirect denies (last match wins) and *before* every destructive class, so it
# cannot launder `rm`/`sort -o`/`*python* -c*`.
NULL_SINK_ALLOW = ("*2>/dev/null*", ALLOW)

WALL_TAIL = [
    ("rm *", DENY),
    ("* rm *", DENY),
    ("*xargs*", DENY),
    ("*sudo*", DENY),
    ("cp *", DENY),
    ("* cp *", DENY),
    ("mv *", DENY),
    ("* mv *", DENY),
    ("*curl*", DENY),
    ("*wget*", DENY),
    ("*sh -c*", DENY),
    ("* git push*", DENY),
    ("* git pull*", DENY),
    ("* git reset*", DENY),
    ("* git checkout*", DENY),
    ("* git restore*", DENY),
    ("* git switch*", DENY),
    ("* git clean*", DENY),
    ("* git stash*", DENY),
    ("* git commit*", DENY),
    ("* git rebase*", DENY),
    ("* git merge*", DENY),
    ("* git cherry-pick*", DENY),
    ("* git apply*", DENY),
    ("* git add*", DENY),
    ("* git branch*", DENY),
    ("* git tag*", DENY),
    ("* git clone*", DENY),
    ("* git worktree*", DENY),
    # `sort*` stays allowed (pipeline plumbing); these trailing denies close its
    # `-o <path>` write primitive. The literal form is the reviewed fix; the
    # broader `*sort*-o*` also covers flag-order variants (`sort -k2 -o out`,
    # `sort --output=out`) that do not contain the contiguous "sort -o".
    ("*sort -o*", DENY),
    ("*sort*-o*", DENY),
]

WALL = WALL_HEAD + [NULL_SINK_ALLOW] + WALL_TAIL

# Pre-change shell run (§4 "insert inside the existing shell run").
BASE_SHELL_RUN = [
    ("git diff*", ALLOW),
    ("git log*", ALLOW),
    ("git show*", ALLOW),
    ("grep *", ALLOW),
    ("rg *", ALLOW),
]

REVIEWER_SHELL_RUN = (
    [("*", DENY)] + BASE_SHELL_RUN + READ_ONLY_ALLOWS
    + WALL_HEAD + [NULL_SINK_ALLOW, PYTHON_C_DENY] + WALL_TAIL
)
QA_SHELL_RUN = (
    [("*", DENY)] + BASE_SHELL_RUN + QA_ALLOWS
    + WALL_HEAD + [NULL_SINK_ALLOW, PYTHON_C_DENY] + WALL_TAIL
)
INTROSPECTOR_SHELL_RUN = (
    [("*", DENY), ("python3 *", ALLOW), ("python *", ALLOW)] + INTROSPECTOR_ALLOWS
    + WALL_HEAD + [NULL_SINK_ALLOW] + WALL_TAIL
)

AGENT_SHELL_RUNS = {
    "code-reviewer": REVIEWER_SHELL_RUN,
    "code-reviewer-pro": REVIEWER_SHELL_RUN,
    "code-reviewer-free": REVIEWER_SHELL_RUN,
    "qa": QA_SHELL_RUN,
    "qa-pro": QA_SHELL_RUN,
    "qa-free": QA_SHELL_RUN,
    "introspector": INTROSPECTOR_SHELL_RUN,
}

# Pre-change non-shell sequence (§9.1 "hard-code it"). Untouched byte-for-byte,
# including `subagent allow research` before `subagent deny *` where present.
REVIEWER_NON_SHELL = [
    ("edit", "*", DENY),
    ("read", "*", ALLOW),
    ("glob", "*", ALLOW),
    ("grep", "*", ALLOW),
    ("list", "*", ALLOW),
    ("webfetch", "*", DENY),
    ("websearch", "*", DENY),
    ("todowrite", "*", DENY),
    ("subagent", "research", ALLOW),
    ("subagent", "*", DENY),
]

QA_NON_SHELL = [
    ("edit", "*", DENY),
    ("read", "*", ALLOW),
    ("glob", "*", ALLOW),
    ("grep", "*", ALLOW),
    ("list", "*", ALLOW),
    ("webfetch", "*", ALLOW),
    ("websearch", "*", ALLOW),
    ("todowrite", "*", DENY),
    ("subagent", "*", DENY),
]

INTROSPECTOR_NON_SHELL = [
    ("edit", "*", ALLOW),
    ("read", "*", ALLOW),
    ("glob", "*", ALLOW),
    ("grep", "*", ALLOW),
    ("list", "*", ALLOW),
    ("webfetch", "*", DENY),
    ("websearch", "*", DENY),
    ("todowrite", "*", DENY),
    ("subagent", "*", DENY),
    ("external_directory", "~/.local/share/opencode/**", ALLOW),
    ("external_directory", "~/.grok/**", ALLOW),
    ("external_directory", "~/.claude/**", ALLOW),
    ("external_directory", "~/.config/opencode/skills/**", ALLOW),
    ("external_directory", "/tmp/**", ALLOW),
    ("external_directory", "/proc/**", ALLOW),
]

AGENT_NON_SHELL = {
    "code-reviewer": REVIEWER_NON_SHELL,
    "code-reviewer-pro": REVIEWER_NON_SHELL,
    "code-reviewer-free": REVIEWER_NON_SHELL,
    "qa": QA_NON_SHELL,
    "qa-pro": QA_NON_SHELL,
    "qa-free": QA_NON_SHELL,
    "introspector": INTROSPECTOR_NON_SHELL,
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _load_permissions() -> dict[str, list[dict]]:
    config = json.loads(OPENCODE_JSON.read_text(encoding="utf-8"))
    return {name: agent["permissions"] for name, agent in config["agents"].items()}


def _shell(perms: list[dict]) -> list[tuple[str, str]]:
    return [(r["resource"], r["effect"]) for r in perms if r["action"] == "shell"]


def _non_shell(perms: list[dict]) -> list[tuple[str, str, str]]:
    return [(r["action"], r["resource"], r["effect"]) for r in perms if r["action"] != "shell"]


# ---------------------------------------------------------------------------
# reference evaluator (independent of the config under test)
# ---------------------------------------------------------------------------

SPLIT_RE = re.compile(r"\|\||&&|\||;")
CD_RE = re.compile(r"cd\s+\S+")


def split_segments(command: str) -> list[str]:
    """Split like the observed harness: `&&`, `||`, `|`, `;` are hard boundaries."""
    return [part.strip() for part in SPLIT_RE.split(command) if part.strip()]


def decide(perms: list[dict], command: str) -> str:
    """ALLOW only if every segment allows; last matching shell rule wins per segment."""
    rules = [(r["resource"], r["effect"]) for r in perms if r["action"] == "shell"]
    for segment in split_segments(command):
        if CD_RE.fullmatch(segment):
            continue  # OpenCode special-cases `cd <dir>`
        effect = None
        for resource, rule_effect in rules:
            if fnmatch.fnmatchcase(segment, resource):
                effect = rule_effect
        if effect != ALLOW:
            return DENY
    return ALLOW


# ---------------------------------------------------------------------------
# §10 probe matrix, per agent family
# ---------------------------------------------------------------------------

REVIEWER_GREENS = [
    "git diff --stat HEAD~1 HEAD | head -5",
    "timeout 30 git log --oneline -1",
    "git status -sb | head -5",
    "ls docs/design",
    "git diff --stat 2>/dev/null | head -5",
]

QA_GREENS = REVIEWER_GREENS + [
    "timeout 120 python3 -m pytest tests/ -q | tail -3",
    "timeout 300 ./build.sh",
    "python3 -m pytest tests/ -q | tail -3",
    "python3 -m pytest tests/ -q 2>/dev/null | tail -3",
]

# Introspector has no git allows (§4.3 minimality); its greens ride on
# `timeout *` / `ls*` / `head*` and its shipped python trust.
INTROSPECTOR_GREENS = [
    "ls docs/design",
    "timeout 30 git log --oneline -1",
    "timeout 60 python3 -m pytest tests/test_session_signals.py -q | tail -3",
    "head -20 docs/design/mdu-30-shell-allowlist.md",
    "head -20 docs/design/mdu-30-shell-allowlist.md 2>/dev/null",
]

GREEN_MATRIX = {
    "qa": QA_GREENS,
    "qa-pro": QA_GREENS,
    "qa-free": QA_GREENS,
    "code-reviewer": REVIEWER_GREENS,
    "code-reviewer-pro": REVIEWER_GREENS,
    "code-reviewer-free": REVIEWER_GREENS,
    "introspector": INTROSPECTOR_GREENS,
}

# Reds caught by the trailing wall (i.e. an allow matches the segment first).
WALL_GUARDED_REDS = [
    "timeout 30 git push --dry-run origin HEAD:refs/heads/mdu30-red-probe",
    "timeout 30 rm -rf /tmp/opencode/mdu30-red/junk",
    "head $(echo pwned)",
    "git log --oneline -1 > /tmp/opencode/mdu30-red/out",
    "timeout 30 sh -c 'git push'",
    "timeout 30 curl http://example.com -o /tmp/opencode/mdu30-red/f",
    # Review revision 1: spaced-only redirect entries were bypassable.
    "git log --oneline -1 >/tmp/opencode/mdu30-red/out",
    "timeout 30 head -5 notes.md >>/home/user/.bashrc",
    "head f 2>/etc/cron.d/x",
    # Each redirect form has its own rule, so each needs its own probe: `*>/*`
    # cannot match `>~/x` or `>../x`, and the spaced `*> /*` cannot match
    # either unspaced form. Dropping `*> ~/*`, `*>~/*`, `*> ../*` or `*>../*`
    # used to be invisible to this matrix. `head` is the prefix because every
    # family allows it, which also makes the wall-mutation check meaningful.
    "head -5 notes.md > ~/.bashrc",
    "head -5 notes.md >>~/.bashrc",
    "head -5 notes.md > ../out.txt",
    "head -5 notes.md >../out.txt",
    # Review revision 1: `sort -o <path>` is a write primitive under `sort*`.
    "sort -o /tmp/opencode/mdu30-red/out notes.md",
    "sort -k2 -o /tmp/opencode/mdu30-red/out notes.md",
    "sort -t. -o /tmp/opencode/mdu30-red/out notes.md",
    "sort --output=/tmp/opencode/mdu30-red/out notes.md",
    # Review revision 1: wall git-mutation class was incomplete.
    "timeout 30 git add -A",
    "timeout 30 git branch mdu30-red",
    "timeout 30 git tag mdu30-red",
    "timeout 30 git clone /tmp/opencode/mdu30-red repo",
    "timeout 30 git worktree add /tmp/opencode/mdu30-red wt",
    # The other git verbs sit in the same wall class but had no behavioural
    # probe at all — only the structural equality check above guarded them.
    "timeout 30 git pull --ff-only",
    "timeout 30 git checkout main",
    "timeout 30 git restore notes.md",
    "timeout 30 git switch main",
    "timeout 30 git clean -fdx",
    "timeout 30 git stash push",
    "timeout 30 git commit -m probe",
    "timeout 30 git rebase main",
    "timeout 30 git merge main",
    "timeout 30 git cherry-pick deadbeef",
    "timeout 30 git apply probe.patch",
    # Remaining wall classes reachable only through the `timeout *` /
    # `head*` / `ls*` allows: backtick substitution, downloader, copy/move,
    # privilege escalation, exec-from-stdin, and `bash -c` (caught by the
    # `*sh -c*` substring, per §3).
    "head -5 `echo pwned`",
    "timeout 30 wget http://example.com -O /tmp/opencode/mdu30-red/f",
    "timeout 30 cp notes.md /tmp/opencode/mdu30-red/copy",
    "timeout 30 mv notes.md /tmp/opencode/mdu30-red/moved",
    "timeout 30 sudo head -1 notes.md",
    "timeout 30 xargs -a notes.md echo pwned",
    "timeout 30 bash -c 'git push'",
]

# The null-sink exception must not launder a destructive class: the exception is
# narrower than the wall, so `rm`/`sort -o` stay denied when `2>/dev/null` is
# appended.
NULL_SINK_LAUNDER_REDS = [
    "timeout 30 rm -rf /tmp/opencode/mdu30-red/junk 2>/dev/null",
    "sort -o /tmp/opencode/mdu30-red/out notes.md 2>/dev/null",
]

# Introspector has no `git log*` allow, so those probes are red for it via the
# leading deny rather than via the wall (§4.3 minimality).
INTROSPECTOR_WALL_GUARDED_REDS = [
    command for command in WALL_GUARDED_REDS if not command.startswith("git log")
]

# Red caught by the leading `shell * deny`: no allow matches it at all (§3).
DENY_FIRST_RED = "git reset --hard HEAD~1"

RED_MATRIX = WALL_GUARDED_REDS + NULL_SINK_LAUNDER_REDS + [DENY_FIRST_RED]


# ---------------------------------------------------------------------------
# 1. structure — order-sensitive, all 7 agents
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("agent", sorted(AGENT_SHELL_RUNS))
def test_shell_run_matches_design_in_order(agent: str) -> None:
    perms = _load_permissions()[agent]
    assert _shell(perms) == AGENT_SHELL_RUNS[agent], f"{agent}: shell run/order drifted from §4"


@pytest.mark.parametrize("agent", sorted(AGENT_SHELL_RUNS))
def test_deny_star_is_first_shell_rule(agent: str) -> None:
    assert _shell(_load_permissions()[agent])[0] == ("*", DENY)


@pytest.mark.parametrize("agent", sorted(AGENT_SHELL_RUNS))
def test_every_allow_sits_between_deny_star_and_wall(agent: str) -> None:
    rules = _shell(_load_permissions()[agent])
    null_at = rules.index(NULL_SINK_ALLOW)
    wall_head_start = null_at - len(WALL_HEAD)
    assert wall_head_start > 1, f"{agent}: no room for allows before the wall"
    assert rules[wall_head_start:null_at] == WALL_HEAD, f"{agent}: wall head drifted"
    # Above the wall head: the leading `shell * deny` and allows, nothing else.
    pre_head = rules[:wall_head_start]
    assert pre_head[0] == ("*", DENY)
    for index, (resource, effect) in enumerate(pre_head):
        if effect == ALLOW:
            assert index > 0, f"{agent}: allow '{resource}' above deny-first"
        else:
            assert resource == "*", f"{agent}: unexpected deny '{resource}' above the wall"
    assert sum(1 for _, effect in pre_head if effect == DENY) == 1
    # The one allow inside the wall is the null-sink exception, and it must be
    # followed by the destructive classes so it cannot launder them.
    assert [effect for _, effect in rules[null_at:]].count(ALLOW) == 1
    assert rules[null_at] == NULL_SINK_ALLOW
    assert rules.index(("* rm *", DENY)) > null_at


@pytest.mark.parametrize("agent", sorted(AGENT_SHELL_RUNS))
def test_wall_is_the_trailing_run(agent: str) -> None:
    rules = _shell(_load_permissions()[agent])
    assert rules[-len(WALL_TAIL):] == WALL_TAIL, f"{agent}: trailing deny wall incomplete or reordered"
    body = rules[: -len(WALL_TAIL)]
    if PYTHON_C_DENY in AGENT_SHELL_RUNS[agent]:
        # The inline-python guard sits after the null-sink exception, otherwise
        # `python3 -c … 2>/dev/null` would be laundered by it.
        assert body[-1] == PYTHON_C_DENY
        body = body[:-1]
    assert body[-len(WALL_HEAD) - 1:] == WALL_HEAD + [NULL_SINK_ALLOW]


@pytest.mark.parametrize("agent", sorted(AGENT_SHELL_RUNS))
def test_no_blanket_shell_allow(agent: str) -> None:
    rules = _shell(_load_permissions()[agent])
    assert ("*", ALLOW) not in rules
    assert rules.count(("*", DENY)) == 1


@pytest.mark.parametrize("agent", sorted(AGENT_NON_SHELL))
def test_non_shell_rules_unchanged(agent: str) -> None:
    assert _non_shell(_load_permissions()[agent]) == AGENT_NON_SHELL[agent]


def test_subagent_research_allow_still_precedes_deny_star() -> None:
    perms = _load_permissions()
    for agent in ("code-reviewer", "code-reviewer-pro", "code-reviewer-free"):
        pairs = [(r["resource"], r["effect"]) for r in perms[agent] if r["action"] == "subagent"]
        assert pairs == [("research", ALLOW), ("*", DENY)]


# ---------------------------------------------------------------------------
# 2. reference evaluator — green / red matrices
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("agent", sorted(GREEN_MATRIX))
def test_green_matrix_allows(agent: str) -> None:
    perms = _load_permissions()[agent]
    for command in GREEN_MATRIX[agent]:
        assert decide(perms, command) == ALLOW, f"{agent} denied a green probe: {command}"


@pytest.mark.parametrize("agent", sorted(GREEN_MATRIX))
def test_red_matrix_denies(agent: str) -> None:
    perms = _load_permissions()[agent]
    for command in RED_MATRIX:
        assert decide(perms, command) == DENY, f"{agent} allowed a red probe: {command}"


def test_cd_segment_passes_without_a_rule() -> None:
    perms = _load_permissions()["qa"]
    assert decide(perms, "cd open-agent-definitions && git status -sb | head -5") == ALLOW


def test_one_denied_segment_rejects_the_command() -> None:
    perms = _load_permissions()["qa"]
    assert decide(perms, "ls docs/design && git push origin main") == DENY


@pytest.mark.parametrize("agent", ["qa", "code-reviewer"])
def test_null_sink_exception_is_not_a_general_write_launderer(agent: str) -> None:
    perms = _load_permissions()[agent]
    # The exception keeps the stderr sink usable …
    assert decide(perms, "head -5 notes.md 2>/dev/null") == ALLOW
    # … but it is placed before the destructive classes and is narrower than
    # the redirect denies, so it cannot launder inline python.
    assert decide(perms, "python3 -c 'open(\"x\", \"w\")' 2>/dev/null") == DENY


# ---------------------------------------------------------------------------
# 2b. targeted contracts the matrices cannot express
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "agent",
    ["qa", "qa-pro", "qa-free", "code-reviewer", "code-reviewer-pro", "code-reviewer-free"],
)
def test_inline_python_guard_blocks_the_timeout_prefix(agent: str) -> None:
    """`*python* -c*` is only load-bearing under a broad allow.

    A bare `python3 -c …` is already stopped by the leading `shell * deny`
    (except for introspector, which by design allows `python3 *`). Under
    `timeout *` an allow matches first, so the guard is the only thing left —
    and the null-sink launderer test does not exercise that path.
    """
    perms = _load_permissions()[agent]
    assert decide(perms, "timeout 30 python3 -c 'print(1)'") == DENY
    # The guard is narrow: pytest still runs under the same prefix on qa.
    if agent.startswith("qa"):
        assert decide(perms, "timeout 30 python3 -m pytest tests/ -q") == ALLOW


def test_inline_python_guard_is_not_installed_for_introspector() -> None:
    # §4.3: introspector keeps MDU-19's `python3 *` trust, so inline python
    # under `timeout *` is allowed by design (§5 Hole 3), not a bug.
    perms = _load_permissions()["introspector"]
    assert decide(perms, "timeout 30 python3 -c 'print(1)'") == ALLOW
    assert PYTHON_C_DENY not in _shell(perms)


def test_cwd_relative_redirect_is_the_disclosed_hole() -> None:
    """§5 Hole 5 / §10: cwd-relative redirects are disclosed, not denied.

    If this test ever fails because the wall gained `*>*`, that is the
    documented additive fix — update §5 Hole 5 and this test in the same
    change instead of "repairing" the wall.
    """
    perms = _load_permissions()
    for agent in ("qa", "code-reviewer"):
        assert decide(perms[agent], "git log --oneline -1 > out.txt") == ALLOW
    # Introspector has no git allow, so the same hole is demonstrated with a
    # command its allowlist does cover.
    assert decide(perms["introspector"], "head -5 notes.md > out.txt") == ALLOW


CD_PREFIX_RE = re.compile(r"^cd\s+\S+$")
REDIRECT_TAIL_RE = re.compile(r"\d*>>?.*$")


def _strip_redirect(segment: str) -> str:
    """Drop a redirect tail — models what the harness appears to match instead."""
    return REDIRECT_TAIL_RE.sub("", segment).strip()


def decide_with_cd_prefix_redirect_stripped(perms: list[dict], command: str) -> str:
    """Model only the QA-verified `cd … &&` rewrite of design §5 Hole 8.

    Live behavior (MDU-30 QA Bug #1): when a command starts with a `cd <dir>`
    segment, the harness appears to strip the redirect tail before glob
    matching, so `cd /repo && git log -1 >/tmp/x` is ALLOWED although `*>/ *`
    and `*>/*` are installed. This helper reproduces that one observed rewrite
    so the hole is pinned; `decide()` stays the naive-split reference
    evaluator, and no rule is changed anywhere.
    """
    segments = split_segments(command)
    if not segments or not CD_PREFIX_RE.match(segments[0]):
        return decide(perms, command)
    rest = " && ".join(
        _strip_redirect(segment) if REDIRECT_TAIL_RE.search(segment) else segment
        for segment in segments[1:]
    )
    return decide(perms, rest)


def test_cd_prefix_redirect_is_the_disclosed_hole() -> None:
    """§5 Hole 8 / §10: `cd <dir> && <allowlisted cmd> > <absolute path>` is ALLOWED.

    This is a disclosed, harness-level hole, not a rule-ordering defect: the
    identical command without the `cd` prefix is denied by the redirect wall —
    asserted below, which proves the rules are installed and firing and that
    the defect is the `cd` prefix, not the wall order. It is also not a
    regression — before MDU-30 there were no redirect denies at all.

    If this test ever starts failing because the harness was fixed, that is the
    good outcome: update design §5 Hole 8 (and §10's disclosed-hole probe) and
    this test together, in the same change, instead of "repairing" the wall.
    """
    perms = _load_permissions()
    for agent in ("qa", "code-reviewer"):
        # No `cd` prefix: the redirect wall is intact and denies both forms.
        assert decide(perms[agent], "git log --oneline -1 >/tmp/opencode/out") == DENY
        assert decide(perms[agent], "git log --oneline -1 > /tmp/opencode/out") == DENY
        # `cd` prefix: the same redirect never reaches the matcher (Hole 8).
        for command in (
            "cd /tmp/opencode/mdu30-red && git log --oneline -1 >/tmp/opencode/out",
            "cd /tmp/opencode/mdu30-red && git log --oneline -1 > /tmp/opencode/out",
        ):
            assert decide_with_cd_prefix_redirect_stripped(perms[agent], command) == ALLOW
        # `edit * deny` governs the edit tool only — it is no backstop here.
        assert ("edit", "*", DENY) in _non_shell(perms[agent])
    # Introspector has no git allow, so demonstrate the same hole with `head`.
    assert decide(perms["introspector"], "head -5 notes.md >/tmp/opencode/out") == DENY
    assert (
        decide_with_cd_prefix_redirect_stripped(
            perms["introspector"],
            "cd /tmp/opencode/mdu30-red && head -5 notes.md >/tmp/opencode/out",
        )
        == ALLOW
    )


# ---------------------------------------------------------------------------
# 3. mutation checks — proves the ordering, not just the presence, is guarded
# ---------------------------------------------------------------------------

def _mutate_move_deny_star_last(perms: list[dict]) -> list[dict]:
    out = list(perms)
    index = next(i for i, r in enumerate(out) if r["action"] == "shell" and r["resource"] == "*")
    rule = out.pop(index)
    last_shell = max(i for i, r in enumerate(out) if r["action"] == "shell")
    out.insert(last_shell + 1, rule)
    return out


WALL_DENIES = frozenset(WALL_HEAD + WALL_TAIL)


def _mutate_wall_above_allows(perms: list[dict]) -> list[dict]:
    """Move every wall deny directly after the leading `*` deny (above all allows)."""
    wall = [r for r in perms if r["action"] == "shell" and (r["resource"], r["effect"]) in WALL_DENIES]
    assert len(wall) == len(WALL_HEAD) + len(WALL_TAIL), "wall deny set drifted"
    rest = [r for r in perms if not (r["action"] == "shell" and (r["resource"], r["effect"]) in WALL_DENIES)]
    first_shell = next(i for i, r in enumerate(rest) if r["action"] == "shell")
    return rest[: first_shell + 1] + wall + rest[first_shell + 1:]


@pytest.mark.parametrize("agent", ["qa", "code-reviewer", "introspector"])
def test_mutation_deny_star_after_allows_flips_greens_to_deny(agent: str) -> None:
    mutated = _mutate_move_deny_star_last(_load_permissions()[agent])
    for command in GREEN_MATRIX[agent]:
        assert decide(mutated, command) == DENY, f"{agent}: green survived a late deny: {command}"


@pytest.mark.parametrize("agent", ["qa", "code-reviewer", "introspector"])
def test_mutation_wall_above_allows_flips_walled_reds_to_allow(agent: str) -> None:
    mutated = _mutate_wall_above_allows(_load_permissions()[agent])
    reds = (
        INTROSPECTOR_WALL_GUARDED_REDS if agent == "introspector" else WALL_GUARDED_REDS
    ) + NULL_SINK_LAUNDER_REDS
    for command in reds:
        assert decide(mutated, command) == ALLOW, f"{agent}: red stayed denied without the wall: {command}"


@pytest.mark.parametrize("agent", ["qa", "code-reviewer", "introspector"])
def test_mutation_wall_above_allows_leaves_deny_first_red_denied(agent: str) -> None:
    # `git reset --hard HEAD~1` is caught by the leading `shell * deny`, not by
    # the wall — moving the wall must not make it reachable.
    mutated = _mutate_wall_above_allows(_load_permissions()[agent])
    assert decide(mutated, DENY_FIRST_RED) == DENY


def _mutate_null_sink_before_redirects(perms: list[dict]) -> list[dict]:
    """Move the null-sink allow above the redirect denies (the order it must not have)."""
    out = list(perms)
    index = next(
        i for i, r in enumerate(out)
        if r["action"] == "shell" and (r["resource"], r["effect"]) == NULL_SINK_ALLOW
    )
    rule = out.pop(index)
    head_index = next(
        i for i, r in enumerate(out)
        if r["action"] == "shell" and (r["resource"], r["effect"]) == WALL_HEAD[0]
    )
    out.insert(head_index, rule)
    return out


@pytest.mark.parametrize("agent", ["qa", "code-reviewer", "introspector"])
def test_mutation_null_sink_above_redirects_makes_the_exception_useless(agent: str) -> None:
    # Design §12: the exception is order-critical twice. The "before the
    # destructive classes" half is the launderer test; this is the "after the
    # redirect denies" half — earlier and every `2>/dev/null` form is denied.
    mutated = _mutate_null_sink_before_redirects(_load_permissions()[agent])
    null_sink_greens = {
        "qa": [
            "head -5 notes.md 2>/dev/null",
            "python3 -m pytest tests/ -q 2>/dev/null | tail -3",
        ],
        "code-reviewer": [
            "head -5 notes.md 2>/dev/null",
            "git diff --stat 2>/dev/null | head -5",
        ],
        "introspector": ["head -20 docs/design/mdu-30-shell-allowlist.md 2>/dev/null"],
    }[agent]
    for command in null_sink_greens:
        assert decide(_load_permissions()[agent], command) == ALLOW, f"{agent}: not a null-sink green: {command}"
        assert decide(mutated, command) == DENY, f"{agent}: null sink survived an early exception: {command}"


# ---------------------------------------------------------------------------
# 4. regression net — validator still accepts the edited config
# ---------------------------------------------------------------------------

def _build_dir(tmp_path: Path) -> Path:
    """Minimal build tree carrying the repo's edited opencode.json."""
    build = tmp_path / "build"
    (build / "grok").mkdir(parents=True)
    (build / "claude" / "agents").mkdir(parents=True)
    shutil.copytree(REPO_ROOT / "prompts", build / "prompts")
    shutil.copytree(REPO_ROOT / "grok" / "agents", build / "grok" / "agents")
    shutil.copy(OPENCODE_JSON, build / "opencode.json")
    (build / "claude" / "agents" / "test.md").write_text(
        "---\nname: test-agent\ndescription: \"test\"\n---\n", encoding="utf-8"
    )
    return build


def test_validate_main_still_exits_zero(tmp_path: Path) -> None:
    assert validate.main([str(_build_dir(tmp_path))]) == 0


def test_validator_does_not_encode_the_shell_allowlist() -> None:
    # Per-agent ordering is config-only; validate.py checks the top-level
    # scratch permissions. A wall entry leaking into it means someone tried to
    # enforce this MDU in the wrong layer.
    source = VALIDATOR.read_text(encoding="utf-8")
    assert "* git push*" not in source
    assert "*python* -c*" not in source
