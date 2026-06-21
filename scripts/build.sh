#!/usr/bin/env bash
# Build pipeline for the generic base layer.
# Stages a deploy-ready build/ directory from the repo source tree.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

main() {
  log_step "Building generic agent definitions"
  log_info "Source: ${REPO_ROOT}"
  log_info "Output: ${BUILD_DIR}"

  rm -rf "$BUILD_DIR"
  stage_source_tree "$REPO_ROOT" "$BUILD_DIR"

  log_step "Generating Claude Code subagents (from opencode.json + prompts)"
  python3 "${SCRIPTS_DIR}/lib/gen_claude_agents.py" "$BUILD_DIR" "${BUILD_DIR}/claude/agents"

  log_step "Validating build output"
  python3 "${SCRIPTS_DIR}/lib/validate.py" "$BUILD_DIR"

  log_ok "Build finished successfully → ${BUILD_DIR}"
}

main "$@"