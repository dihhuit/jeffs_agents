#!/bin/sh
# Smoke eval for task 01-repo-health: verify the repo's own gates pass.
#
# Runs ./build.sh (staging + validation of agent definitions) and the pytest
# suite from the repo root, echoing a PASS/FAIL line per gate. Exits 0 only
# when both gates succeed. POSIX-sh only; no bashisms.
set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)"

cd "$REPO_ROOT" || exit 1

build_ok=0
pytest_ok=0

if ./build.sh; then
  build_ok=1
  echo "PASS build.sh"
else
  echo "FAIL build.sh"
fi

if python3 -m pytest tests/ -q; then
  pytest_ok=1
  echo "PASS pytest"
else
  echo "FAIL pytest"
fi

if [ "$build_ok" -eq 1 ] && [ "$pytest_ok" -eq 1 ]; then
  echo "PASS repo-health"
  exit 0
fi

echo "FAIL repo-health"
exit 1