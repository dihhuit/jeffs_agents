#!/usr/bin/env bash
# Shared helpers for the generic (base) build and deploy pipelines.

set -euo pipefail

if [[ -z "${REPO_ROOT:-}" ]]; then
  REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi

BUILD_DIR="${REPO_ROOT}/build"
SCRIPTS_DIR="${REPO_ROOT}/scripts"

log_info()  { printf '  [info]  %s\n' "$*"; }
log_step()  { printf '==> %s\n' "$*"; }
log_ok()    { printf '  [ok]    %s\n' "$*"; }
log_warn()  { printf '  [warn]  %s\n' "$*" >&2; }
log_error() { printf '  [error] %s\n' "$*" >&2; }

detect_cli_tools() {
  HAS_OPENCODE=false
  HAS_GROK=false
  command -v opencode >/dev/null 2>&1 && HAS_OPENCODE=true
  command -v grok >/dev/null 2>&1 && HAS_GROK=true
  export HAS_OPENCODE HAS_GROK
}

require_at_least_one_cli() {
  detect_cli_tools
  if [[ "$HAS_OPENCODE" == false && "$HAS_GROK" == false ]]; then
    log_error "Neither opencode nor grok found in PATH."
    log_error "Install at least one CLI before deploying."
    exit 1
  fi
}

stage_source_tree() {
  local src="$1" dest="$2"
  mkdir -p "$dest/prompts" "$dest/grok/agents" "$dest/skills"
  cp "$src/opencode.json" "$dest/opencode.json"
  cp "$src/prompts/"*.md "$dest/prompts/"
  if [[ -d "$src/grok/agents" ]]; then
    cp "$src/grok/agents/"*.md "$dest/grok/agents/" 2>/dev/null || true
  fi
  if [[ -d "$src/skills" ]]; then
    cp -a "$src/skills/." "$dest/skills/"
  fi
}