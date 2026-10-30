#!/bin/sh
# Eval driver for task 05-fallback-ladder.
#
# Walks six scripted cap/provider/credit failure cases and prints the ladder
# action each one mandates, then verifies the governing sentence for each case
# is present in every reachable orchestrator mirror (the two base mirrors
# always; the overlay grokestrator only when the sibling checkout exists).
#
# Offline and read-only: no model calls, no network, no writes to the mirrors.
# POSIX sh; no bashisms.
#
# Usage: driver.sh
#
# Echoes "[case n] event -> action [policy sentence found in k/k mirrors]" per
# case, then PASS/FAIL fallback-ladder. Exits 0 only when every case resolves
# and every governing sentence is present in every reachable mirror.
set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)"
OVERLAY_MIRROR="$REPO_ROOT/../opencode_agents/grok/agents/grokestrator.md"

# Reachable mirrors, one absolute path per line.
mirrors() {
  printf '%s\n' "$REPO_ROOT/prompts/orchestrator.md"
  printf '%s\n' "$REPO_ROOT/grok/agents/orchestrator.md"
  if [ -f "$OVERLAY_MIRROR" ]; then
    printf '%s\n' "$OVERLAY_MIRROR"
  fi
}

TMPLIST=$(mktemp) || {
  echo "[warn] cannot create a temp file"
  echo "FAIL fallback-ladder"
  exit 1
}
trap 'rm -f "$TMPLIST"' EXIT INT TERM

mirrors >"$TMPLIST"
TOTAL=0
while IFS= read -r m; do
  TOTAL=$((TOTAL + 1))
  if [ ! -f "$m" ]; then
    echo "[warn] mirror missing: $m"
  fi
done <"$TMPLIST"

if [ "$TOTAL" -eq 0 ]; then
  echo "[warn] no orchestrator mirrors reachable"
  echo "FAIL fallback-ladder"
  exit 1
fi

bad=0

# run_case <n> <event> <mandated action> <governing sentence>
run_case() {
  n="$1"
  event="$2"
  action="$3"
  sentence="$4"
  found=0
  total=0
  missing=""
  while IFS= read -r m; do
    total=$((total + 1))
    if [ -f "$m" ] && grep -F -q -- "$sentence" "$m"; then
      found=$((found + 1))
    else
      missing="$missing $m"
    fi
  done <"$TMPLIST"
  printf '[case %s] %s -> %s [policy sentence found in %s/%s mirrors]\n' \
    "$n" "$event" "$action" "$found" "$total"
  if [ "$total" -eq 0 ] || [ "$found" -ne "$total" ]; then
    echo "[warn] case $n: governing sentence missing in:$missing"
    echo "[warn] case $n: expected sentence: $sentence"
    bad=1
  fi
}

# Case 1 — a Go-budget spawn dies on a quota refusal: one retry, same model.
run_case 1 \
  'opencode-go/deepseek-v4.1-flash spawn reports provider.quota' \
  'one retry, same model' \
  'Retry the same failure once — same model, in the same or a fresh spawn.'

# Case 2 — the retry fails identically: exactly one rotation, different model.
run_case 2 \
  'the retry fails identically' \
  'one rotation to a live-list model, not the original' \
  'make exactly ONE rotation to a different `opencode-go/*` model'

# Case 3 — the rotated spawn fails: stop and escalate with evidence.
run_case 3 \
  'the rotated spawn fails' \
  'stop; escalate with both errors and both model ids' \
  'Escalate to the user with the failure evidence: both error reports and both model ids.'

# Case 4 — a second rotation is contemplated: forbidden.
run_case 4 \
  'a second rotation is contemplated' \
  'forbidden; never a second silent rotation' \
  'Never a second silent rotation.'

# Case 5 — an xai spawn fails on credit/auth: no ladder, escalate directly.
run_case 5 \
  'xai/grok-4.7 spawn reports credit/auth error' \
  'no ladder; escalate directly' \
  'spawns get NO ladder: a cap, credit, or auth error there escalates directly to the user with the evidence.'

# Case 6 — any spawn failure: never substitute a free model.
run_case 6 \
  'any spawn failure' \
  'never substitute a free model' \
  'never substitute a free model'

if [ "$bad" -eq 0 ]; then
  echo "PASS fallback-ladder"
  exit 0
fi

echo "FAIL fallback-ladder"
exit 1
