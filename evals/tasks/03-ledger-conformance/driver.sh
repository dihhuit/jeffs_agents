#!/bin/sh
# Eval driver for task 03-ledger-conformance.
#
# Seeds a throwaway git workspace per CLI under /tmp/opencode/mdu-15/, runs the
# CLI headless on the golden TASK.md with no docs/ directory, then grades the
# manifest it wrote with the BASE repo's validator. POSIX sh; no bashisms.
#
# Usage: driver.sh [opencode|grok|claude|all]   (default: all)
#
# Echoes PASS/FAIL ledger-conformance/<cli> per check set (with the CLI's exit
# status, informational only), and SKIP for a CLI absent from PATH. Exits 0
# only when everything it ran is green.
set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)"
VALIDATOR="$REPO_ROOT/scripts/lib/run_ledger.py"
TASK_DOC="$SCRIPT_DIR/task.md"
WORK_ROOT="/tmp/opencode/mdu-15"
MANIFEST_REL="runs/mdu-ledger-check/manifest.json"
# Explicit model for the opencode leg: the agent's default alias can resolve to
# a free endpoint that is unavailable. Overridable from the environment; an
# empty value falls back to the default.
OPENCODE_MODEL="${OPENCODE_MODEL:-opencode/big-pickle}"

if [ ! -f "$VALIDATOR" ]; then
  echo "[warn] missing base validator: $VALIDATOR"
  echo "FAIL ledger-conformance"
  exit 1
fi

if [ ! -f "$TASK_DOC" ]; then
  echo "[warn] missing task doc: $TASK_DOC"
  echo "FAIL ledger-conformance"
  exit 1
fi

# grade <cli> <scratch> <cli_rc> — run the six checks; return 0 only when all
# pass. cli_rc is the CLI's own exit status; it is reported, never scored.
grade() {
  cli="$1"
  scratch="$2"
  cli_rc="$3"
  manifest="$scratch/$MANIFEST_REL"
  ok=1

  if [ -f "$manifest" ]; then
    echo "[ok] manifest exists"
  else
    echo "[warn] manifest missing: $manifest"
    ok=0
  fi

  if [ -f "$manifest" ]; then
    if python3 "$VALIDATOR" validate "$manifest"; then
      echo "[ok] base validator accepts manifest"
    else
      echo "[warn] base validator rejected manifest"
      ok=0
    fi

    if python3 - "$manifest" "$cli" <<'PY'
import json
import sys

path, cli = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as fh:
    manifest = json.load(fh)

checks = [
    ("harness == %s" % cli, manifest.get("harness") == cli),
    ("status == completed", manifest.get("status") == "completed"),
    (
        "phases[] has commit entry",
        any(
            isinstance(p, dict) and p.get("phase") == "commit"
            for p in (manifest.get("phases") or [])
        ),
    ),
]
bad = [name for name, passed in checks if not passed]
for name, passed in checks:
    print("[%s] %s" % ("ok" if passed else "warn", name))
sys.exit(1 if bad else 0)
PY
    then
      :
    else
      ok=0
    fi
  fi

  if [ -n "$(git -C "$scratch" log --oneline 2>/dev/null)" ]; then
    echo "[ok] at least one commit"
  else
    echo "[warn] scratch repo has no commits"
    ok=0
  fi

  if [ "$ok" -eq 1 ]; then
    echo "PASS ledger-conformance/$cli (cli exit $cli_rc)"
    return 0
  fi
  echo "FAIL ledger-conformance/$cli (cli exit $cli_rc)"
  return 1
}

# run_one <cli> — seed, invoke headless, grade.
run_one() {
  cli="$1"

  if ! command -v "$cli" >/dev/null 2>&1; then
    echo "[info] $cli not on PATH"
    echo "SKIP ledger-conformance/$cli"
    return 0
  fi

  scratch="$WORK_ROOT/$cli"
  echo "[info] seeding $scratch"
  rm -rf "$scratch"
  mkdir -p "$scratch/scripts/lib" || return 1
  cp "$VALIDATOR" "$scratch/scripts/lib/run_ledger.py" || return 1

  # Extract the golden task text between the markers in task.md.
  awk '/^<!-- task-text:start -->$/{f=1;next} /^<!-- task-text:end -->$/{f=0} f' \
    "$TASK_DOC" >"$scratch/TASK.md" || return 1
  if [ ! -s "$scratch/TASK.md" ]; then
    echo "[warn] extracted TASK.md is empty"
    echo "FAIL ledger-conformance/$cli"
    return 1
  fi

  git -C "$scratch" init -q || return 1

  echo "[info] invoking $cli headless (timeout 480)"
  # The subshell's status is the last command's status, i.e. the CLI's own
  # exit code (timeout reports 124 on expiry). No pipe, so no PIPESTATUS.
  (
    cd "$scratch" || exit 1
    case "$cli" in
      opencode) timeout 480 opencode run --agent orchestrator --model "$OPENCODE_MODEL" "$(cat TASK.md)" ;;
      grok) timeout 480 grok --agent orchestrator -p "$(cat TASK.md)" ;;
      claude) timeout 480 claude --agent orchestrator -p "$(cat TASK.md)" --dangerously-skip-permissions ;;
    esac
  )
  rc=$?
  if [ "$rc" -eq 124 ]; then
    echo "[warn] $cli timed out after 480s (reported, not retried)"
  elif [ "$rc" -ne 0 ]; then
    echo "[warn] $cli exited $rc"
  fi

  grade "$cli" "$scratch" "$rc"
}

mode="${1:-all}"
overall=0

case "$mode" in
  opencode | grok | claude)
    run_one "$mode" || overall=1
    ;;
  all)
    for cli in opencode grok claude; do
      run_one "$cli" || overall=1
    done
    ;;
  *)
    echo "usage: $0 [opencode|grok|claude|all]"
    exit 2
    ;;
esac

if [ "$overall" -eq 0 ]; then
  echo "PASS ledger-conformance"
  exit 0
fi

echo "FAIL ledger-conformance"
exit 1
