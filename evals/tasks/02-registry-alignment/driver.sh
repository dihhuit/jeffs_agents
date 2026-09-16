#!/bin/sh
# Smoke eval for task 02-registry-alignment: verify every model reference in
# opencode.json resolves against the committed model-registry snapshot.
#
# Runs `python3 scripts/lib/model_registry.py --check opencode.json` from the
# repo root, echoing a PASS/FAIL line. Exits 0 only on success. POSIX-sh only;
# no bashisms. Resolves the repo root via the script location so the driver
# works whether invoked from the harness or by hand.
set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)"

cd "$REPO_ROOT" || exit 1

registry_ok=0

if python3 scripts/lib/model_registry.py --check opencode.json; then
  registry_ok=1
  echo "PASS model_registry --check opencode.json"
else
  echo "FAIL model_registry --check opencode.json"
fi

if [ "$registry_ok" -eq 1 ]; then
  echo "PASS registry-alignment"
  exit 0
fi

echo "FAIL registry-alignment"
exit 1