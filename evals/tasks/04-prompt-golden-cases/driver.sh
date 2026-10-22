#!/bin/sh
# Eval driver for task 04-prompt-golden-cases.
#
# GOLDEN_ROOT (optional) points the gate at an arbitrary tree (scratch copies);
# default is this repo. The gate script always comes from THIS repo (trusted
# grader), the tree under test comes from GOLDEN_ROOT.
set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)"
GATE="$REPO_ROOT/scripts/lib/prompt_regression.py"
ROOT="${GOLDEN_ROOT:-$REPO_ROOT}"

if [ ! -f "$GATE" ]; then
  echo "FAIL prompt-golden-cases (missing gate script: $GATE)"
  exit 1
fi

# Golden cases and baseline must come from the trusted repo, not the tree under test.
for golden_file in evals/golden/cases.json evals/golden/baseline.json; do
  if [ ! -f "$REPO_ROOT/$golden_file" ]; then
    echo "FAIL prompt-golden-cases (trusted golden file missing: $golden_file)"
    exit 1
  fi
  if [ ! -f "$ROOT/$golden_file" ] || ! cmp -s "$ROOT/$golden_file" "$REPO_ROOT/$golden_file"; then
    echo "FAIL prompt-golden-cases (golden files differ from the trusted repo)"
    exit 1
  fi
done

if python3 "$GATE" gate --root "$ROOT"; then
  echo "PASS prompt-golden-cases"
  exit 0
fi

echo "FAIL prompt-golden-cases"
exit 1
