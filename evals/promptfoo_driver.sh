#!/bin/sh
# promptfoo exec-provider dispatcher (MDU-09).
# promptfoo runs the provider with cwd = the config's directory (evals/), so
# relative paths are resolved from evals/.
set -u

task="${1:-}"
if [ -z "$task" ]; then
  echo "FAIL promptfoo-driver (no task given)"
  exit 1
fi

driver="tasks/${task##*/}/driver.sh"
if [ ! -f "$driver" ]; then
  echo "FAIL promptfoo-driver (no driver for $task)"
  exit 1
fi

bash "$driver"
