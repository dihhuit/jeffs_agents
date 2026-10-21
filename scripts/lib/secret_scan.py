#!/usr/bin/env python3
"""Secret scan: staged-diff / path scanner for the commit gate.

Deterministic, offline, stdlib-only. The rule set is the `secret-scrub` skill's
pattern list (1:1) plus two documented additions (GitHub PATs and committed
``.env`` files). See ``docs/security.md`` and
``docs/design/mdu-11-secret-gate.md``.

Usage:
    secret_scan.py [--staged | --paths P1 [P2 ...]] [--json] [--no-placeholder-filter]

Exit codes:
    0  clean (including an empty stage / nothing to scan)
    1  findings (block the commit)
    2  operational failure (not a git repo, unreadable file) -- fail closed

Output is always masked: full matched values never leave the process. Human
mode prints one line per finding (``<file>:<line> <rule-id> <prefix>...``);
``--json`` prints the machine-readable report.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

# --- Rule table (ordered; ids are the skill-scanner contract) ---------------
#
# Each entry: ``id`` (stable rule id), ``kind`` (``content`` = regex on lines,
# ``path`` = filename trigger), ``scope`` (``any``, ``env`` = only ``.env*``
# files, ``source`` = source-ish files), ``patterns`` (compiled regexes; a
# named ``value`` group selects the secret text), and a human ``note``.
#
# The ordering is intentional and stable, and is not the skill's listed order:
# credential formats first (aws, openai, private-key, github-pat), then the two
# heuristic rules (high-entropy, generic-assignment), then the `.env` rules,
# with the path rule last. ``RULE_IDS`` is the tiebreaker for findings that
# share a file and line, so this order is part of the output contract.

RULES: tuple[dict, ...] = (
    {
        "id": "aws-access-key-id",
        "kind": "content",
        "scope": "any",
        "patterns": (re.compile(r"(?P<value>AKIA[0-9A-Z]{16})"),),
        "note": "AWS access key ids (skill pattern, unchanged).",
    },
    {
        "id": "openai-style-key",
        "kind": "content",
        "scope": "any",
        "patterns": (re.compile(r"(?P<value>sk-[A-Za-z0-9]{20,})"),),
        "note": "OpenAI-style API keys (skill pattern, unchanged).",
    },
    {
        "id": "private-key-block",
        "kind": "content",
        "scope": "any",
        "patterns": (
            re.compile(
                r"(?P<value>-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----)"
            ),
        ),
        "note": "PEM private-key headers (skill pattern, unchanged).",
    },
    {
        "id": "github-pat",
        "kind": "content",
        "scope": "any",
        "patterns": (re.compile(r"(?P<value>gh[pousr]_[A-Za-z0-9]{36,})"),),
        "note": "GitHub classic PATs (added: near-zero false positives).",
    },
    {
        "id": "high-entropy-string",
        "kind": "content",
        "scope": "any",
        "patterns": (
            # Base64-ish and hex candidates; the entropy gate below decides.
            re.compile(r"(?P<value>[A-Za-z0-9+/]{32,}={0,2})"),
            re.compile(r"(?P<value>[0-9a-fA-F]{32,})"),
        ),
        "note": "Random-looking 32+ char tokens (entropy-gated, UUIDs skipped).",
    },
    {
        "id": "generic-assignment",
        "kind": "content",
        "scope": "source",
        "patterns": (
            re.compile(
                r"(?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*"
                r"['\"]?(?P<value>\S+)",
                re.IGNORECASE,
            ),
        ),
        "note": "Generic assignments, minus placeholders and env references.",
    },
    {
        "id": "env-assignment",
        "kind": "content",
        "scope": "env",
        "patterns": (
            re.compile(
                r"(?:API_KEY|SECRET|TOKEN|PASSWORD|PASSWD|PRIVATE_KEY)"
                r"\s*=\s*(?P<value>\S+)"
            ),
        ),
        "note": "Values inside committed .env* files (skill pattern, narrowed).",
    },
    {
        "id": "env-file-committed",
        "kind": "path",
        "scope": "any",
        "patterns": (),
        "note": "Staging a real .env file at all (added; .example excluded).",
    },
)

RULE_IDS: tuple[str, ...] = tuple(rule["id"] for rule in RULES)

# --- Placeholder / false-positive allowlist (in-code by design) -------------
#
# The allowlist is code, not a data file, so silencing the gate shows up as a
# security-sensitive diff. Every entry below names the legitimate artifact it
# permits. Never add a blanket path skip or a bare-substring exemption (e.g.
# "sk-"): widen only through review, and only with a justification comment.

# Documentation/template artifacts that intentionally contain placeholder
# values: ``.env.example``, ``examples/mcp/opencode.mcp.json.example`` and
# friends. These are the files the repo tells users to copy.
PLACEHOLDER_PATH_SUFFIXES: tuple[str, ...] = (".example", ".sample", ".template")

# Placeholder value prefixes used by the templates above and by the skill's
# own documentation (``your-api-key``, ``changeme``, ``<token>``).
# ``replace_me``/``replaceme`` are the same value-shape class as ``changeme``:
# they mark a slot to fill in (``replace_me_with_a_real_token``). D4.2 lists
# them for that reason -- they are not path or substring exemptions.
PLACEHOLDER_PREFIXES: tuple[str, ...] = (
    "your-",
    "your_",
    "example_",
    "changeme",
    "replace_me",
    "replaceme",
)

# Env-var / secret-manager references are the *correct* way to hold a secret,
# so they must not be reported as hardcoded values (``$API_KEY``,
# ``${VAULT_TOKEN}``, ``{env:OPENAI_KEY}``, ``os.environ["KEY"]``).
ENV_REFERENCE_MARKERS: tuple[str, ...] = (
    "os.environ[",
    "os.getenv(",
    "process.env",
    "environ.get(",
    "{env:",
)

# Lockfiles are generated integrity hashes (sha512-...): long base64 runs are
# expected there. Name-exact, and it suppresses only the entropy rule -- a
# credential literal in a lockfile still fires. ``env-assignment`` is
# deliberately absent: its scope requires a ``.env*`` basename, which no
# lockfile has, so listing it here would be an unreachable suppression.
LOCKFILE_NAMES: frozenset[str] = frozenset(
    {
        "package-lock.json",
        "npm-shrinkwrap.json",
        "yarn.lock",
        "poetry.lock",
        "Pipfile.lock",
        "go.sum",
        "Cargo.lock",
    }
)
LOCKFILE_SUPPRESSED_RULES: frozenset[str] = frozenset({"high-entropy-string"})

# Entropy threshold in bits per character for the high-entropy rule. Random
# base64/hex sits around 4-6; natural-language words and identifiers that long
# are rare, and the lockfile/UUID/placeholder filters cover the known benign
# classes. Deliberately not lowered: it is a heuristic, not a guarantee.
ENTROPY_THRESHOLD = 3.5

# Source-ish files where generic assignments are meaningful. Docs are included
# because a leaked key in a README is as bad as one in code.
SOURCE_SUFFIXES: frozenset[str] = frozenset(
    {
        ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs",
        ".java", ".kt", ".kts", ".rb", ".php", ".cs", ".c", ".h", ".cc",
        ".cpp", ".hpp", ".m", ".mm", ".swift", ".scala", ".sh", ".bash",
        ".zsh", ".fish", ".ps1", ".lua", ".pl", ".r", ".jl", ".ex", ".exs",
        ".erl", ".hs", ".clj", ".vue", ".svelte", ".astro", ".yaml", ".yml",
        ".json", ".jsonc", ".toml", ".ini", ".cfg", ".conf", ".properties",
        ".gradle", ".xml", ".sql", ".tf", ".tfvars", ".dockerfile", ".md",
        ".mdx", ".rst", ".txt", ".env",
    }
)
SOURCE_BASENAMES: frozenset[str] = frozenset(
    {"Dockerfile", "Makefile", "Procfile", "Gemfile", "Rakefile"}
)

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_ENV_FILE_RE = re.compile(r"^\.env(\..+)?$")
_X_RUN_RE = re.compile(r"^[xX]{4,}$")
_TRIM_CHARS = "'\",;)("
# A quoted template (``token = '<insert-token>'``) must reach the placeholder
# tests unquoted. The assignment rules consume an optional opening quote, so the
# captured value can carry a trailing quote only; both ends are normalised.
_QUOTE_CHARS = "'\"`"

# Chars of a matched value the masked preview may reveal. See ``_mask``.
_MASK_PREFIX_LEN = 4


@dataclass(frozen=True)
class Finding:
    """One match. ``value`` is the raw secret and is never emitted directly."""

    file: str
    line: int
    rule: str
    value: str

    @property
    def preview(self) -> str:
        return _mask(self.value)


def _mask(value: str) -> str:
    """The single masking function: first 4 chars plus an ellipsis.

    A value shorter than twice the prefix yields no characters at all: its
    "prefix" would be most or all of the secret, so only the ellipsis is shown.
    """
    if len(value) < 2 * _MASK_PREFIX_LEN:
        return "\u2026"
    return value[:_MASK_PREFIX_LEN] + "\u2026"


def _shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def _basename(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def _is_env_file(path: str) -> bool:
    name = _basename(path)
    return bool(_ENV_FILE_RE.match(name)) and not name.endswith(".example")


def _is_source_file(path: str) -> bool:
    name = _basename(path)
    # .env* files belong to the narrower env-assignment rule; do not report the
    # same value twice through generic-assignment.
    if _ENV_FILE_RE.match(name):
        return False
    if name in SOURCE_BASENAMES:
        return True
    return any(name.lower().endswith(suffix) for suffix in SOURCE_SUFFIXES)


def _clean_value(value: str) -> str:
    """Strip trailing punctuation picked up by greedy ``\\S+`` captures."""
    return value.strip().strip(_TRIM_CHARS)


def _strip_quotes(value: str) -> str:
    """Drop surrounding quote characters (single, double, backtick).

    Applied before the placeholder-shape tests so a quoted template
    (``token = '<insert-token>'``, ``token = "<your-token>"``, a backticked
    Markdown value) is recognised as a placeholder. This normalises the
    candidate only; a real credential inside quotes matches none of the
    placeholder shapes and still fires.
    """
    stripped = value
    while stripped and stripped[0] in _QUOTE_CHARS:
        stripped = stripped[1:]
    while stripped and stripped[-1] in _QUOTE_CHARS:
        stripped = stripped[:-1]
    return stripped


def _is_placeholder(value: str) -> bool:
    """True when a matched value is a documented placeholder or reference."""
    cleaned = _strip_quotes(_clean_value(value))
    if not cleaned:
        return True
    lowered = cleaned.lower()
    if any(lowered.startswith(prefix) or lowered == prefix for prefix in PLACEHOLDER_PREFIXES):
        return True
    if cleaned.startswith("<") and cleaned.endswith(">"):
        return True
    if _X_RUN_RE.match(cleaned):
        return True
    if cleaned.endswith("\u2026") or cleaned.endswith("..."):
        return True
    if any(marker in cleaned for marker in ENV_REFERENCE_MARKERS):
        return True
    # Shell-style references: $VAR and ${VAR} start with "$" (a bare "$"
    # elsewhere in a value is not treated as a reference).
    if cleaned.startswith("$"):
        return True
    return False


def _rule_applies(rule: dict, path: str) -> bool:
    scope = rule["scope"]
    if scope == "env":
        return _is_env_file(path)
    if scope == "source":
        return _is_source_file(path)
    return True


def _suppress(finding: Finding, path: str, use_filters: bool) -> bool:
    """Apply the D4 suppression policy. ``use_filters`` is False for the flag."""
    if not use_filters:
        return False
    # 1. Template paths (.env.example and other documented copies).
    if _basename(path).endswith(PLACEHOLDER_PATH_SUFFIXES):
        return True
    # 2. Placeholder values and env references. Path findings have no value,
    #    so they are exempt from this check (an empty value is not a placeholder).
    if finding.rule != "env-file-committed" and _is_placeholder(finding.value):
        return True
    # 3. UUID-shaped values (run ledgers, session ids).
    if _UUID_RE.match(_clean_value(finding.value)):
        return True
    # 4. Lockfiles: integrity hashes only (the entropy rule).
    if (
        _basename(path) in LOCKFILE_NAMES
        and finding.rule in LOCKFILE_SUPPRESSED_RULES
    ):
        return True
    return False


def scan_line(path: str, line_no: int, line: str, use_filters: bool = True) -> list[Finding]:
    """Run every applicable content rule against one line."""
    findings: list[Finding] = []
    for rule in RULES:
        if rule["kind"] != "content" or not _rule_applies(rule, path):
            continue
        seen_spans: set[tuple[int, int]] = set()
        for pattern in rule["patterns"]:
            for match in pattern.finditer(line):
                span = match.span("value")
                if span in seen_spans:
                    continue
                seen_spans.add(span)
                raw = match.group("value")
                value = _clean_value(raw)
                if not value:
                    continue
                if rule["id"] == "high-entropy-string":
                    if _UUID_RE.match(value):
                        continue
                    if _shannon_entropy(value) < ENTROPY_THRESHOLD:
                        continue
                finding = Finding(file=path, line=line_no, rule=rule["id"], value=value)
                if _suppress(finding, path, use_filters):
                    continue
                findings.append(finding)
    return findings


def scan_text(path: str, text: str, use_filters: bool = True) -> list[Finding]:
    """Scan a whole file body (``--paths`` and unit tests)."""
    findings: list[Finding] = []
    if _is_env_file(path):
        path_rule = Finding(file=path, line=1, rule="env-file-committed", value="")
        if not _suppress(path_rule, path, use_filters):
            findings.append(path_rule)
    for index, line in enumerate(text.splitlines(), start=1):
        findings.extend(scan_line(path, index, line, use_filters=use_filters))
    return findings


def _unquote_git_path(raw: str) -> str:
    """Best-effort decode of git's quoted paths (only when special chars exist)."""
    if len(raw) >= 2 and raw.startswith('"') and raw.endswith('"'):
        inner = raw[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\")
    return raw


def staged_added_lines() -> tuple[list[tuple[str, int, str]], list[str]]:
    """Return added ``(path, line_no, text)`` rows and every touched path.

    Uses ``git diff --cached --unified=0`` so only lines this commit adds are
    scanned; context and removed lines are out of scope (the gate stops what is
    about to be pushed, it does not re-litigate history). Touched paths include
    files with no added lines (e.g. an empty new ``.env``).
    """
    check = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    if check.returncode != 0:
        raise RuntimeError("not a git repository")

    diff = subprocess.run(
        [
            "git",
            "-c",
            "core.quotepath=false",
            "diff",
            "--cached",
            "--unified=0",
            "--no-color",
            "--no-ext-diff",
            "--diff-filter=ACMRT",
        ],
        capture_output=True,
        check=False,
    )
    if diff.returncode != 0:
        raise RuntimeError("git diff failed while reading the staged diff")

    names = subprocess.run(
        [
            "git",
            "diff",
            "--cached",
            "--name-only",
            "-z",
            "--diff-filter=ACMRT",
        ],
        capture_output=True,
        check=False,
    )
    if names.returncode != 0:
        raise RuntimeError("git diff failed while listing the staged paths")
    # ``-z`` keeps paths verbatim, so no unquoting is needed here.
    files = [
        name
        for name in names.stdout.decode("utf-8", errors="replace").split("\0")
        if name
    ]

    added: list[tuple[str, int, str]] = []
    current_file: str | None = None
    new_line = 0
    hunk_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
    for raw_line in diff.stdout.decode("utf-8", errors="replace").splitlines():
        if raw_line.startswith("+++ "):
            target = _unquote_git_path(raw_line[4:].strip())
            if target == "/dev/null":
                current_file = None
            else:
                current_file = target[2:] if target.startswith("b/") else target
            continue
        if raw_line.startswith("--- "):
            continue
        match = hunk_re.match(raw_line)
        if match:
            new_line = int(match.group(1))
            continue
        if current_file is None:
            continue
        if raw_line.startswith("+"):
            added.append((current_file, new_line, raw_line[1:]))
            new_line += 1
        elif raw_line.startswith(" "):
            new_line += 1
    return added, files


def scan_staged(use_filters: bool = True) -> tuple[list[Finding], int, int]:
    """Scan added/modified lines of the staged diff.

    Returns ``(findings, files_scanned, lines_scanned)``. ``files_scanned`` is
    the number of files actually scanned, i.e. files with at least one added
    line; a path that appears in the staged diff with deletions only is not
    scanned and is not counted.
    """
    added, touched = staged_added_lines()
    findings: list[Finding] = []
    for path, line_no, text in added:
        findings.extend(scan_line(path, line_no, text, use_filters=use_filters))
    # A staged real .env file is a finding even when its values look inert.
    for path in touched:
        if not _is_env_file(path):
            continue
        finding = Finding(file=path, line=1, rule="env-file-committed", value="")
        if not _suppress(finding, path, use_filters):
            findings.append(finding)
    files_scanned = len({path for path, _line_no, _text in added})
    findings.sort(key=lambda f: (f.file, f.line, RULE_IDS.index(f.rule)))
    return findings, files_scanned, len(added)


def scan_paths(paths: list[str], use_filters: bool = True) -> tuple[list[Finding], int, int]:
    """Scan whole files (``--paths``). Unreadable/missing files raise."""
    findings: list[Finding] = []
    files_scanned = 0
    lines_scanned = 0
    for path in paths:
        source = Path(path)
        try:
            text = source.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise RuntimeError(f"cannot read {path}: {exc}") from exc
        files_scanned += 1
        lines_scanned += len(text.splitlines())
        findings.extend(scan_text(path, text, use_filters=use_filters))
    findings.sort(key=lambda f: (f.file, f.line, RULE_IDS.index(f.rule)))
    return findings, files_scanned, lines_scanned


def _emit(findings: list[Finding], files: int, lines: int, as_json: bool) -> None:
    """The single output path: every value is masked here, once."""
    if as_json:
        payload = {
            "status": "fail" if findings else "pass",
            "scanned": {"files": files, "lines": lines},
            "findings": [
                {
                    "file": finding.file,
                    "line": finding.line,
                    "rule": finding.rule,
                    "preview": _mask(finding.value),
                }
                for finding in findings
            ],
        }
        print(json.dumps(payload, sort_keys=True))
        return
    for finding in findings:
        print(f"{finding.file}:{finding.line} {finding.rule} {_mask(finding.value)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan staged changes or given files for secrets."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--staged",
        action="store_true",
        help="scan added/modified lines of the staged diff (default)",
    )
    mode.add_argument(
        "--paths",
        nargs="+",
        metavar="PATH",
        help="scan these files fully",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--no-placeholder-filter",
        action="store_true",
        help="disable placeholder/lockfile/UUID suppression (filter self-test)",
    )
    args = parser.parse_args(argv)
    use_filters = not args.no_placeholder_filter

    try:
        if args.paths:
            findings, files, lines = scan_paths(args.paths, use_filters=use_filters)
        else:
            findings, files, lines = scan_staged(use_filters=use_filters)
    except RuntimeError as exc:
        print(f"secret_scan: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # operational failure must fail closed, never crash-open
        # Exception text can embed the value that triggered the failure, so it
        # goes through the masking helper too. The type stays visible for
        # diagnostics; exit 2 keeps the failure closed.
        print(
            f"secret_scan: unexpected error ({type(exc).__name__}): {_mask(str(exc))}",
            file=sys.stderr,
        )
        return 2

    _emit(findings, files, lines, args.json)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
