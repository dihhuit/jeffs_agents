#!/usr/bin/env bash
# Entry point: stage generic agent definitions into build/.
set -euo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/build.sh" "$@"