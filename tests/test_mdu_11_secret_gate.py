"""Tests for MDU-11 — secret scanning and leak prevention in the loop.

Covers:

* ``scripts/lib/secret_scan.py`` — rule matrix, placeholder/allowlist policy,
  exit codes (0 clean / 1 findings / 2 operational failure), masked output, and
  the staged-diff commit gate.
* ``scripts/install_secret_gate.sh`` — marked, idempotent, non-clobbering hook
  installer, plus the fail-open notice when no scanner resolves.
* The prompt/docs contract for the commit gate (design D6/D8/D10/D11).
* The skill ↔ scanner rule-id 1:1 mapping (design D3/D12).

Fixture discipline (design D13): no contiguous live-format secret literal
appears in this file. Every realistic value is assembled from concatenated
fragments or generated deterministically, and assertions check exit codes,
rule ids, ``file:line`` and the masked prefix only — so a failing test prints
no secret either.

Hermeticity: every git repo is created under ``tmp_path``; the developer's git
config is neutralised (``GIT_CONFIG_GLOBAL``/``GIT_CONFIG_SYSTEM`` =
``/dev/null``, ``HOME`` redirected) and the real repository is never staged in.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import shutil
import string
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import pytest

import secret_scan

REPO_ROOT = Path(__file__).resolve().parents[1]
SCANNER = REPO_ROOT / "scripts" / "lib" / "secret_scan.py"
INSTALLER = REPO_ROOT / "scripts" / "install_secret_gate.sh"

_ALNUM = string.ascii_letters + string.digits


# ---------------------------------------------------------------------------
# helpers — deterministic fixture values (never live-format literals)
# ---------------------------------------------------------------------------

def _alnum(length: int, seed: str) -> str:
    """A deterministic pseudo-random alnum string, so lengths stay exact."""
    out: list[str] = []
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    while len(out) < length:
        for byte in digest:
            if len(out) >= length:
                break
            out.append(_ALNUM[byte % len(_ALNUM)])
        digest = hashlib.sha256(digest).digest()
    return "".join(out)


AWS_KEY = "AK" + "IA" + "IOSFODNN7" + "EXAMPLE"
OPENAI_KEY = "sk-" + _alnum(24, "mdu-11-openai")
GITHUB_PAT = "gh" + "p_" + _alnum(36, "mdu-11-github")
PEM_HEADER = "-----BEGIN RSA " + "PRIVATE KEY-----"
GENERIC_VALUE = _alnum(24, "mdu-11-generic")
ENV_VALUE = _alnum(20, "mdu-11-env")
ENTROPY_VALUE = secrets.token_hex(32)  # generated per run, never a literal
UUID_VALUE = "123e4567-e89b-42d3-a456-" + "426614174000"

ALL_RULE_IDS = frozenset(
    {
        "aws-access-key-id",
        "openai-style-key",
        "private-key-block",
        "github-pat",
        "high-entropy-string",
        "generic-assignment",
        "env-assignment",
        "env-file-committed",
    }
)


def _write(root: Path, name: str, body: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _run_scan(
    *args: str, cwd: Path | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCANNER), *args],
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def _findings(stdout: str) -> list[tuple[str, str, str]]:
    """Parse human output into ``(file:line, rule, masked)`` triples."""
    rows = []
    for line in stdout.splitlines():
        parts = line.split()
        assert len(parts) == 3, f"unexpected output line shape: {line!r}"
        rows.append((parts[0], parts[1], parts[2]))
    return rows


# --- hermetic git -----------------------------------------------------------

_GIT_OPTS = [
    "-c",
    "diff.noprefix=false",
    "-c",
    "diff.mnemonicprefix=false",
    "-c",
    "core.quotepath=false",
    "-c",
    "commit.gpgsign=false",
    "-c",
    "init.defaultBranch=main",
    "-c",
    "user.name=Secret Gate Test",
    "-c",
    "user.email=test@example.invalid",
]


def _hermetic_env(root: Path, ceiling: Path | None = None) -> dict[str, str]:
    """An env that cannot inherit the developer's git config or GENERIC_DIR."""
    home = root / "home"
    home.mkdir(parents=True, exist_ok=True)
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(home),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_NAME": "Secret Gate Test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "Secret Gate Test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
    }
    if ceiling is not None:
        # Keep git from discovering a repository *above* the scratch tree.
        env["GIT_CEILING_DIRECTORIES"] = str(ceiling)
    return env


def _git(
    repo: Path, *args: str, env: dict[str, str], check: bool = True
) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", *_GIT_OPTS, *args],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed ({result.returncode}): {result.stderr.strip()}"
        )
    return result


@pytest.fixture()
def scratch_repo(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """A throw-away git repo under tmp_path with a neutralised environment."""
    repo = tmp_path / "scratch"
    repo.mkdir()
    env = _hermetic_env(tmp_path)
    _git(repo, "init", "-q", env=env)
    return repo, env


# ---------------------------------------------------------------------------
# 1. rule matrix
# ---------------------------------------------------------------------------

_PASSWORD_LHS = "pass" + "word = "
_API_KEY_LHS = "API_" + "KEY="
_SESSION_LHS = "session_" + "token: "


def test_rule_matrix_fires(tmp_path: Path) -> None:
    """Every one of the eight rule ids fires on its own synthetic sample."""
    cases = {
        "aws.py": ("aws-access-key-id", f'credential_one = "{AWS_KEY}"\n'),
        "openai.py": ("openai-style-key", f'credential_two = "{OPENAI_KEY}"\n'),
        "server.pem": ("private-key-block", PEM_HEADER + "\n"),
        "github.py": ("github-pat", f'credential_three = "{GITHUB_PAT}"\n'),
        "blob.txt": ("high-entropy-string", ENTROPY_VALUE + "\n"),
        "generic.py": (
            "generic-assignment",
            f'{_PASSWORD_LHS}"{GENERIC_VALUE}"' + "\n",
        ),
        ".env": ("env-assignment", f"{_API_KEY_LHS}{ENV_VALUE}" + "\n"),
        ".env.local": ("env-file-committed", "DEBUG=1\n"),
    }
    for name, (_, body) in cases.items():
        _write(tmp_path, name, body)

    paths = [str(tmp_path / name) for name in cases]
    result = _run_scan("--paths", *paths)

    assert result.returncode == 1, result.stderr
    rules_by_file: dict[str, set[str]] = defaultdict(set)
    for location, rule, _masked in _findings(result.stdout):
        file_part, _, line_part = location.rpartition(":")
        assert line_part.isdigit(), f"missing line number in {location!r}"
        rules_by_file[file_part].add(rule)

    for name, (expected, _) in cases.items():
        fired = rules_by_file.get(str(tmp_path / name), set())
        assert expected in fired, f"{expected} did not fire for {name} (fired: {sorted(fired)})"

    assert set(rules_by_file) == set(paths), "unexpected file leaked into the report"
    assert set().union(*rules_by_file.values()) == ALL_RULE_IDS


# ---------------------------------------------------------------------------
# 2./3. placeholder policy, and proof that the policy is what silences them
# ---------------------------------------------------------------------------

def _placeholder_assignments() -> str:
    """One assignment line per placeholder/reference shape from D4.2."""
    triggers = (
        "pass" + "word",
        "secret",
        "tok" + "en",
        "pass" + "wd",
        "api_" + "key",
        "pass" + "word",
        "secret",
        "tok" + "en",
    )
    values = (
        "your-api-key-here",
        "EXAMPLE_placeholder_value",
        "changeme",
        "replace_me_with_a_real_token",
        "<insert-token>",
        "{env:DB_PASSWORD}",
        "$VAULT_TOKEN",
        "${GITHUB_TOKEN}",
    )
    return "".join(f"{lhs} = {value!r}\n" for lhs, value in zip(triggers, values))


def _placeholder_fixtures(root: Path) -> dict[Path, str]:
    """Template path + placeholder values; all clean *only* because of D4."""
    return {
        _write(root, "templates/settings.json.example", f'{{"api_key": "{AWS_KEY}"}}\n'): (
            "aws-access-key-id"
        ),
        _write(root, "values.py", _placeholder_assignments()): "generic-assignment",
    }


def test_placeholders_suppressed(tmp_path: Path) -> None:
    """Template paths, placeholder values and env references produce no finding."""
    fixtures = _placeholder_fixtures(tmp_path)
    result = _run_scan("--paths", *[str(path) for path in fixtures])

    assert result.returncode == 0, f"expected a clean scan, got findings: {result.stdout}"
    assert result.stdout.strip() == ""


def test_placeholder_filter_is_real(tmp_path: Path) -> None:
    """The same fixtures fail once suppression is disabled — no rule rot."""
    fixtures = _placeholder_fixtures(tmp_path)
    result = _run_scan(
        "--paths", *[str(path) for path in fixtures], "--no-placeholder-filter"
    )

    assert result.returncode == 1
    rules_by_file: dict[str, set[str]] = defaultdict(set)
    for location, rule, _masked in _findings(result.stdout):
        file_part, _, _ = location.rpartition(":")
        rules_by_file[file_part].add(rule)

    for path, expected_rule in fixtures.items():
        assert expected_rule in rules_by_file.get(str(path), set()), (
            f"{expected_rule} was suppressed for {path.name} even with "
            "--no-placeholder-filter"
        )
    # The eight placeholder assignments are each still matched by their rule.
    values_file = next(p for p in fixtures if p.name == "values.py")
    assert sum(1 for loc, rule, _ in _findings(result.stdout) if loc.startswith(str(values_file)) and rule == "generic-assignment") == 8


def test_uuid_shaped_values_suppressed(tmp_path: Path) -> None:
    """A UUID-shaped value is suppressed, but only by the D4.3 UUID filter."""
    body = f"{_SESSION_LHS}{UUID_VALUE}" + "\n"
    path = _write(tmp_path, "config.yaml", body)

    clean = _run_scan("--paths", str(path))
    assert clean.returncode == 0, clean.stdout
    assert clean.stdout.strip() == ""

    raw = _run_scan("--paths", str(path), "--no-placeholder-filter")
    assert raw.returncode == 1
    assert "generic-assignment" in raw.stdout
    assert UUID_VALUE not in raw.stdout


# ---------------------------------------------------------------------------
# 4. lockfile skip is narrow
# ---------------------------------------------------------------------------

def test_lockfile_skip_is_narrow(tmp_path: Path) -> None:
    """Integrity hashes are skipped in lockfiles; credentials in them are not."""
    integrity = base64.b64encode(secrets.token_bytes(48)).decode("ascii")
    lock = tmp_path / "package-lock.json"
    _write(
        tmp_path,
        "package-lock.json",
        json.dumps(
            {
                "name": "fixture",
                "lockfileVersion": 3,
                "packages": {
                    "node_modules/left-pad": {
                        "version": "1.0.0",
                        "integrity": "sha512-" + integrity,
                    }
                },
            },
            indent=2,
        )
        + "\n",
    )

    hashes_only = _run_scan("--paths", str(lock))
    assert hashes_only.returncode == 0, hashes_only.stdout
    assert "high-entropy-string" not in hashes_only.stdout

    _write(
        tmp_path,
        "package-lock.json",
        json.dumps(
            {
                "name": "fixture",
                "lockfileVersion": 3,
                "packages": {
                    "node_modules/left-pad": {
                        "version": "1.0.0",
                        "integrity": "sha512-" + integrity,
                        "resolved": "https://registry.example/" + GITHUB_PAT,
                    }
                },
            },
            indent=2,
        )
        + "\n",
    )

    with_credential = _run_scan("--paths", str(lock))
    assert with_credential.returncode == 1
    assert "github-pat" in with_credential.stdout
    # The lockfile skip must not widen to credential rules.
    assert "high-entropy-string" not in with_credential.stdout
    assert GITHUB_PAT not in with_credential.stdout


# ---------------------------------------------------------------------------
# 5. exit codes
# ---------------------------------------------------------------------------

def test_exit_codes(
    tmp_path: Path, scratch_repo: tuple[Path, dict[str, str]]
) -> None:
    repo, env = scratch_repo

    clean = _write(tmp_path, "clean.py", "retries = 3\n")
    assert _run_scan("--paths", str(clean)).returncode == 0

    dirty = _write(tmp_path, "dirty.py", f'credential = "{AWS_KEY}"\n')
    assert _run_scan("--paths", str(dirty)).returncode == 1

    # Empty stage: nothing staged in a fresh repo is a pass, not an error.
    empty = _run_scan("--staged", cwd=repo, env=env)
    assert empty.returncode == 0, empty.stderr

    # --staged outside any repository: fail closed.
    outside = tmp_path / "outside"
    outside.mkdir()
    not_repo = _run_scan(
        "--staged", cwd=outside, env=_hermetic_env(tmp_path, ceiling=tmp_path)
    )
    assert not_repo.returncode == 2
    assert "not a git repository" in not_repo.stderr

    # Unreadable/missing --paths target: fail closed.
    missing = _run_scan("--paths", str(tmp_path / "does-not-exist.py"))
    assert missing.returncode == 2
    assert "cannot read" in missing.stderr


# ---------------------------------------------------------------------------
# 6. the gate never leaks a secret itself
# ---------------------------------------------------------------------------

def test_output_never_contains_secret(tmp_path: Path) -> None:
    """Full values never reach stdout/stderr/JSON; the 4-char prefix does."""
    fixtures = {
        "aws.py": (f'credential_one = "{AWS_KEY}"\n', AWS_KEY),
        "openai.py": (f'credential_two = "{OPENAI_KEY}"\n', OPENAI_KEY),
        "server.pem": (PEM_HEADER + "\n", PEM_HEADER),
        "github.py": (f'credential_three = "{GITHUB_PAT}"\n', GITHUB_PAT),
        "blob.txt": (ENTROPY_VALUE + "\n", ENTROPY_VALUE),
        "generic.py": (f'{_PASSWORD_LHS}"{GENERIC_VALUE}"' + "\n", GENERIC_VALUE),
        ".env": (f"{_API_KEY_LHS}{ENV_VALUE}" + "\n", ENV_VALUE),
    }
    paths = [_write(tmp_path, name, body) for name, (body, _) in fixtures.items()]
    args = ["--paths", *[str(path) for path in paths], "--no-placeholder-filter"]
    human = _run_scan(*args)
    machine = _run_scan(*args[:-1], "--json", args[-1])

    assert human.returncode == 1
    assert machine.returncode == 1

    for name, (_, value) in fixtures.items():
        for stream_name, stream in (
            ("human stdout", human.stdout),
            ("human stderr", human.stderr),
            ("json stdout", machine.stdout),
            ("json stderr", machine.stderr),
        ):
            assert value not in stream, f"full value from {name} leaked to {stream_name}"

    payload = json.loads(machine.stdout)
    assert payload["status"] == "fail"
    assert payload["scanned"]["files"] == len(paths)
    assert payload["scanned"]["lines"] == len(paths)
    pairs = {(finding["rule"], finding["preview"]) for finding in payload["findings"]}
    for rule, value in (
        ("aws-access-key-id", AWS_KEY),
        ("openai-style-key", OPENAI_KEY),
        ("private-key-block", PEM_HEADER),
        ("github-pat", GITHUB_PAT),
        ("high-entropy-string", ENTROPY_VALUE),
        ("generic-assignment", GENERIC_VALUE),
        ("env-assignment", ENV_VALUE),
    ):
        assert (rule, value[:4] + "\u2026") in pairs, f"{rule} preview is not the masked prefix"
    # Human mode prints the same masked prefix, not the value.
    assert AWS_KEY[:4] in human.stdout


# ---------------------------------------------------------------------------
# 6b. regression — a short value must be masked entirely
#
# The preview used to be ``value[:4] + "…"`` unconditionally, so a match of four
# characters or fewer was echoed back *in full* by the very helper meant to hide
# it. Detection is unchanged (the rule still fires, exit 1); only the preview
# must stop carrying any character of a value shorter than eight characters,
# while an eight-plus value keeps its four-character prefix.
# ---------------------------------------------------------------------------

# Fragments, so no credential-shaped literal appears in this file. The pool is
# deliberately 12 chars: every case below is a slice of it, and the characters
# (j, q, z, x, 7, 9) do not occur in the paths, rule ids or JSON keys the
# scanner prints, so a whole-output leak check is meaningful.
_MASK_POOL = "j" + "q" + "z" + "x" + "7" + "9" + "j" + "q" + "z" + "x" + "7" + "9"


def _scan_one_assignment(
    root: Path, name: str, value: str
) -> tuple[subprocess.CompletedProcess, subprocess.CompletedProcess]:
    """Scan one quoted ``password = ...`` assignment in human and JSON mode."""
    path = _write(root, name, f'{_PASSWORD_LHS}"{value}"' + "\n")
    human = _run_scan("--paths", str(path))
    machine = _run_scan("--paths", str(path), "--json")
    return human, machine


@pytest.mark.parametrize("length", [1, 2, 4, 5, 6, 7])
def test_short_values_are_masked_entirely(tmp_path: Path, length: int) -> None:
    """Values under eight chars are still flagged, but reveal no characters."""
    value = _MASK_POOL[:length]
    human, machine = _scan_one_assignment(tmp_path, f"short_{length}.py", value)

    assert human.returncode == 1, f"a {length}-char value stopped being flagged"
    rows = _findings(human.stdout)
    assert [rule for _loc, rule, _masked in rows] == ["generic-assignment"], rows
    masked = rows[0][2]
    assert masked == "\u2026", (
        f"the {length}-char value was not masked entirely: preview {masked!r}"
    )
    for char in set(value):
        assert char not in masked, f"preview {masked!r} still reveals {char!r}"

    assert machine.returncode == 1
    payload = json.loads(machine.stdout)
    previews = [(f["rule"], f["preview"]) for f in payload["findings"]]
    assert previews == [("generic-assignment", "\u2026")], previews
    assert value not in machine.stdout, "the full value reached the JSON report"


@pytest.mark.parametrize("length", [8, 9, 12])
def test_long_values_keep_the_four_char_prefix(tmp_path: Path, length: int) -> None:
    """Eight-plus chars keep the masked prefix — the fix must not over-correct."""
    value = _MASK_POOL[:length]
    human, machine = _scan_one_assignment(tmp_path, f"long_{length}.py", value)

    assert human.returncode == 1, f"a {length}-char value stopped being flagged"
    rows = _findings(human.stdout)
    assert rows == [(f"{tmp_path / f'long_{length}.py'}:1", "generic-assignment", value[:4] + "\u2026")], rows

    assert machine.returncode == 1
    payload = json.loads(machine.stdout)
    assert [(f["rule"], f["preview"]) for f in payload["findings"]] == [
        ("generic-assignment", value[:4] + "\u2026")
    ]
    assert value not in human.stdout
    assert value not in machine.stdout


# ---------------------------------------------------------------------------
# 7. AC2 — the staged-diff gate rejects a realistic secret diff
# ---------------------------------------------------------------------------

def test_staged_diff_gate_rejects_realistic_secret(
    scratch_repo: tuple[Path, dict[str, str]]
) -> None:
    repo, env = scratch_repo
    _write(
        repo,
        "app.py",
        "retries = 3\n"
        f'aws = "{AWS_KEY}"\n'
        f'client = "{OPENAI_KEY}"\n',
    )
    _git(repo, "add", "app.py", env=env)

    result = _run_scan("--staged", cwd=repo, env=env)
    assert result.returncode == 1
    rows = _findings(result.stdout)
    assert ("app.py:2", "aws-access-key-id", "AKIA\u2026") in rows
    assert ("app.py:3", "openai-style-key", OPENAI_KEY[:4] + "\u2026") in rows
    for name, value in (("aws key", AWS_KEY), ("openai key", OPENAI_KEY)):
        assert value not in result.stdout, f"the full {name} reached stdout"
        assert value not in result.stderr, f"the full {name} reached stderr"

    machine = _run_scan("--staged", "--json", cwd=repo, env=env)
    assert machine.returncode == 1
    payload = json.loads(machine.stdout)
    assert payload["status"] == "fail"
    assert {(f["file"], f["line"], f["rule"]) for f in payload["findings"]} == {
        ("app.py", 2, "aws-access-key-id"),
        ("app.py", 3, "openai-style-key"),
    }
    assert AWS_KEY not in machine.stdout
    assert OPENAI_KEY not in machine.stdout


# ---------------------------------------------------------------------------
# 8. hook installer
# ---------------------------------------------------------------------------

def _run_installer(
    repo: Path, env: dict[str, str], *args: str
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(INSTALLER), *args],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _commit(
    repo: Path, env: dict[str, str], message: str
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *_GIT_OPTS, "commit", "-m", message],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_hook_installer(scratch_repo: tuple[Path, dict[str, str]]) -> None:
    repo, env = scratch_repo
    # Hermetic: neither ./scripts/lib nor ${GENERIC_DIR} may resolve at first.
    assert "GENERIC_DIR" not in env
    hook = repo / ".git" / "hooks" / "pre-commit"

    first = _run_installer(repo, env)
    assert first.returncode == 0, first.stderr
    assert hook.is_file()
    hook_body = hook.read_text(encoding="utf-8")
    assert "managed by scripts/install_secret_gate.sh" in hook_body
    assert os.access(hook, os.X_OK)

    # Idempotent: a second run rewrites the same marked hook, byte for byte.
    second = _run_installer(repo, env)
    assert second.returncode == 0, second.stderr
    assert hook.read_text(encoding="utf-8") == hook_body

    # No scanner resolves -> fail open with a stderr notice, commit succeeds.
    _write(repo, "notes.txt", "nothing sensitive here\n")
    _git(repo, "add", "notes.txt", env=env)
    fail_open = _commit(repo, env, "clean commit")
    assert fail_open.returncode == 0, fail_open.stderr
    assert "no scanner found" in fail_open.stderr + fail_open.stdout

    # With the scanner present the hook enforces the gate.
    lib = repo / "scripts" / "lib"
    lib.mkdir(parents=True)
    shutil.copy2(SCANNER, lib / "secret_scan.py")

    _write(repo, "leak.py", f'credential = "{AWS_KEY}"\n')
    _git(repo, "add", "leak.py", env=env)
    blocked = _commit(repo, env, "leaky commit")
    assert blocked.returncode != 0
    combined = blocked.stdout + blocked.stderr
    assert "aws-access-key-id" in combined
    assert AWS_KEY not in combined

    # Clean stage passes the same hook.
    _git(repo, "reset", "-q", "HEAD", "--", "leak.py", env=env)
    _write(repo, "clean.txt", "still nothing sensitive\n")
    _git(repo, "add", "clean.txt", env=env)
    allowed = _commit(repo, env, "clean commit again")
    assert allowed.returncode == 0, allowed.stderr


def test_hook_installer_refuses_foreign_and_uninstalls_safely(
    scratch_repo: tuple[Path, dict[str, str]],
) -> None:
    repo, env = scratch_repo
    hook = repo / ".git" / "hooks" / "pre-commit"
    foreign = "#!/bin/sh\necho foreign hook\n"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(foreign, encoding="utf-8")

    refused = _run_installer(repo, env)
    assert refused.returncode == 1
    assert "refusing to overwrite" in refused.stderr
    assert hook.read_text(encoding="utf-8") == foreign

    untouched = _run_installer(repo, env, "--uninstall")
    assert untouched.returncode == 0
    assert hook.is_file()
    assert hook.read_text(encoding="utf-8") == foreign
    assert "not managed" in untouched.stderr + untouched.stdout

    # A marked hook is removed by --uninstall, and removal is idempotent.
    hook.unlink()
    assert _run_installer(repo, env).returncode == 0
    assert hook.is_file()
    removed = _run_installer(repo, env, "--uninstall")
    assert removed.returncode == 0
    assert not hook.exists()
    assert _run_installer(repo, env, "--uninstall").returncode == 0


# ---------------------------------------------------------------------------
# 9. prompt + docs contract
# ---------------------------------------------------------------------------

ORCHESTRATOR_MIRRORS = ("prompts/orchestrator.md", "grok/agents/orchestrator.md")
JUST_CODE_MIRRORS = (
    "prompts/just-code.md",
    "grok/agents/just-code.md",
    "grok/agents/just-code-mid.md",
    "grok/agents/just-code-pro.md",
)

SKILL_PATTERNS = (
    "AKIA[0-9A-Z]{16}",
    "sk-[A-Za-z0-9]{20,}",
    "-----BEGIN (RSA |EC " + "|OPENSSH |PGP )?PRIVATE KEY-----",
    "(API_KEY|SECRET|TOKEN|PASSWORD|PASSWD|PRIVATE_KEY)",
    "[A-Za-z0-9+/]{32,}={0,2}",
    "(password|passwd|secret|token|api[_-]?key)",
)


def test_prompt_contract_mdu_11() -> None:
    """All four prompt mirrors carry the clause; security.md documents it."""
    for rel in ORCHESTRATOR_MIRRORS:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8").lower()
        assert "secret_scan.py" in text, f"{rel} lost the secret-gate command"
        assert "secret_scan.py --staged" in text, f"{rel} does not name --staged"
        assert "never print full secrets" in text, f"{rel} lost the masking rule"
        assert "secret-scrub" in text, f"{rel} lost the skill fallback"

    for rel in JUST_CODE_MIRRORS:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8").lower()
        assert "never commit secrets" in text, f"{rel} lost the hard constraint"
        assert "secret_scan.py" in text, f"{rel} lost the pre-report scan command"

    security = REPO_ROOT / "docs" / "security.md"
    assert security.is_file(), "docs/security.md is missing"
    text = security.read_text(encoding="utf-8")
    lowered = " ".join(text.split()).lower()
    for heading in ("least-privilege", "secret hygiene", "sandboxing", "approval gates"):
        assert heading in lowered, f"docs/security.md lost the '{heading}' topic"
    for cross_ref in ("docs/autonomy.md", "docs/opencode-v2.md"):
        assert cross_ref in text, f"docs/security.md lost the {cross_ref} cross-reference"
    assert "never print full secrets" in lowered


# ---------------------------------------------------------------------------
# 10. skill ↔ scanner rule-id mapping
# ---------------------------------------------------------------------------

def test_rule_ids_match_skill_set() -> None:
    """Rule ids are exactly the skill's six patterns plus the two additions."""
    assert len(secret_scan.RULE_IDS) == len(ALL_RULE_IDS)
    assert set(secret_scan.RULE_IDS) == ALL_RULE_IDS
    assert len(set(secret_scan.RULE_IDS)) == len(secret_scan.RULE_IDS)

    skill = (REPO_ROOT / "skills" / "secret-scrub" / "SKILL.md").read_text(encoding="utf-8")
    for pattern in SKILL_PATTERNS:
        assert pattern in skill, f"the skill lost its documented pattern {pattern!r}"
    assert "secret_scan.py" in skill, "the skill no longer points at the scanner"
