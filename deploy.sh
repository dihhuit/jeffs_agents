#!/usr/bin/env bash
# Entry point: deploy generic agent definitions to OpenCode and Grok Build.
#
# Usage:
#   ./deploy.sh              # dry run
#   ./deploy.sh --force      # install
#   ./deploy.sh --force --rebuild
set -euo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/deploy.sh" "$@"