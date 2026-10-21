#!/usr/bin/env bash
# install_secret_gate.sh — install or remove the secret-scan pre-commit hook.
#
# The hook is defense-in-depth behind the orchestrator prompt gate: it runs
# ``scripts/lib/secret_scan.py --staged`` before every commit. If no scanner
# resolves (e.g. an overlay clone without the base sibling), the hook fails
# OPEN with a stderr notice — a fail-closed hook would brick commits on
# machines that never had the base repo.
#
# Usage:
#   scripts/install_secret_gate.sh            # install (idempotent)
#   scripts/install_secret_gate.sh --uninstall
#
# build.sh must NOT call this: build never touches .git.

set -euo pipefail

MARKER="# secret-gate: managed by scripts/install_secret_gate.sh"
UNINSTALL=0
case "${1:-}" in
  "") ;;
  --uninstall) UNINSTALL=1 ;;
  -h|--help)
    echo "usage: $0 [--uninstall]" >&2
    exit 0
    ;;
  *)
    echo "install_secret_gate: unknown argument: $1" >&2
    echo "usage: $0 [--uninstall]" >&2
    exit 2
    ;;
esac

if ! REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  echo "install_secret_gate: not inside a git repository" >&2
  exit 2
fi
if [[ -z "$REPO_ROOT" ]]; then
  echo "install_secret_gate: could not resolve the repository root" >&2
  exit 2
fi

# ``git rev-parse --git-path`` handles worktrees and separate git dirs.
HOOK="$(git rev-parse --git-path hooks/pre-commit)"
if [[ "$HOOK" != /* ]]; then
  HOOK="$REPO_ROOT/$HOOK"
fi

if [[ "$UNINSTALL" -eq 1 ]]; then
  if [[ ! -f "$HOOK" ]]; then
    echo "install_secret_gate: no pre-commit hook at $HOOK (nothing to remove)"
    exit 0
  fi
  if grep -qF "$MARKER" "$HOOK"; then
    rm -f "$HOOK"
    echo "install_secret_gate: removed managed pre-commit hook at $HOOK"
  else
    echo "install_secret_gate: $HOOK is not managed by this installer; leaving it alone" >&2
  fi
  exit 0
fi

if [[ -f "$HOOK" ]] && ! grep -qF "$MARKER" "$HOOK"; then
  echo "install_secret_gate: refusing to overwrite a foreign hook at $HOOK" >&2
  echo "install_secret_gate: move it aside, or merge the scan into it manually" >&2
  exit 1
fi

mkdir -p "$(dirname "$HOOK")"

# A non-default core.hooksPath moves where git reads hooks from: a hook in
# .git/hooks is then never executed — a silent gate absence. Do not retarget
# the install (``git rev-parse --git-path`` already follows the setting); warn
# so the user can confirm the effective directory is the one they expect.
HOOKS_PATH="$(git config --get core.hooksPath || true)"
if [[ -n "$HOOKS_PATH" ]]; then
  EFFECTIVE_HOOKS="$HOOKS_PATH"
  if [[ "$EFFECTIVE_HOOKS" == "~"* ]]; then
    EFFECTIVE_HOOKS="${HOME}${EFFECTIVE_HOOKS#\~}"
  fi
  if [[ "$EFFECTIVE_HOOKS" != /* ]]; then
    EFFECTIVE_HOOKS="$REPO_ROOT/$EFFECTIVE_HOOKS"
  fi
  echo "install_secret_gate: WARNING: core.hooksPath is set to '$HOOKS_PATH'" >&2
  echo "install_secret_gate: git reads hooks from $EFFECTIVE_HOOKS, not .git/hooks." >&2
  echo "install_secret_gate: this installer targets that directory ($(dirname "$HOOK"));" >&2
  echo "install_secret_gate: if it is a shared or global hooks dir, confirm the scan belongs there." >&2
fi

cat > "$HOOK" <<'HOOK_EOF'
#!/bin/sh
# secret-gate: managed by scripts/install_secret_gate.sh
# Remove with: scripts/install_secret_gate.sh --uninstall
# Masks all output; exits 1 on findings, 2 on operational failure (fail closed).

SCANNER="./scripts/lib/secret_scan.py"
if [ ! -f "$SCANNER" ]; then
  SCANNER="${GENERIC_DIR:-../open-agent-definitions}/scripts/lib/secret_scan.py"
fi
if [ ! -f "$SCANNER" ]; then
  echo "secret-gate: no scanner found (looked in ./scripts/lib and ${GENERIC_DIR:-../open-agent-definitions});" \
       "skipping the secret scan — apply the secret-scrub skill checklist manually" >&2
  exit 0
fi

exec python3 "$SCANNER" --staged
HOOK_EOF

chmod +x "$HOOK"
echo "install_secret_gate: installed pre-commit hook at $HOOK"
