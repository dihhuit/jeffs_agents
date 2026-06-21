#!/usr/bin/env bash
# Deploy generic agent definitions to OpenCode, Grok Build, and/or Claude Code user config dirs.
#
# Usage:
#   ./deploy.sh              # dry run
#   ./deploy.sh --force      # install
#   ./deploy.sh --force --rebuild   # rebuild then install

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

DO_COPY=false
DO_REBUILD=false
for arg in "$@"; do
  case "$arg" in
    --force) DO_COPY=true ;;
    --rebuild) DO_REBUILD=true ;;
  esac
done

OPENCODE_CONFIG_DIR="${HOME}/.config/opencode"
OPENCODE_PROMPTS_DIR="${OPENCODE_CONFIG_DIR}/prompts"
OPENCODE_SKILLS_DIR="${OPENCODE_CONFIG_DIR}/skills"
GROK_AGENTS_DIR="${HOME}/.grok/agents"
GROK_SKILLS_DIR="${HOME}/.grok/skills"
CLAUDE_AGENTS_DIR="${HOME}/.claude/agents"

resolve_sources() {
  if [[ ! -f "${BUILD_DIR}/opencode.json" || "$DO_REBUILD" == true ]]; then
    if [[ "$DO_COPY" == true || "$DO_REBUILD" == true ]]; then
      log_info "building deploy sources"
      bash "${SCRIPT_DIR}/build.sh"
    elif [[ ! -f "${BUILD_DIR}/opencode.json" ]]; then
      log_warn "build/ not found; dry-run will use repo root"
      DEPLOY_ROOT="$REPO_ROOT"
      return
    fi
  fi

  if [[ -f "${BUILD_DIR}/opencode.json" ]]; then
    DEPLOY_ROOT="$BUILD_DIR"
    log_info "deploying from build/"
  else
    DEPLOY_ROOT="$REPO_ROOT"
    log_info "deploying from repo root"
  fi
}

deploy_opencode_json() {
  [[ "$HAS_OPENCODE" == true ]] || return 0
  [[ -f "${DEPLOY_ROOT}/opencode.json" ]] || return 0
  if [[ "$DO_COPY" == true ]]; then
    mkdir -p "$OPENCODE_CONFIG_DIR"
    cp "${DEPLOY_ROOT}/opencode.json" "${OPENCODE_CONFIG_DIR}/opencode.json"
    log_ok "opencode.json → ${OPENCODE_CONFIG_DIR}/"
  else
    log_info "[dry-run] opencode.json → ${OPENCODE_CONFIG_DIR}/opencode.json"
  fi
}

deploy_prompts() {
  [[ "$HAS_OPENCODE" == true ]] || return 0
  [[ -d "${DEPLOY_ROOT}/prompts" ]] || return 0
  local files=("${DEPLOY_ROOT}/prompts/"*.md)
  [[ -e "${files[0]}" ]] || return 0
  if [[ "$DO_COPY" == true ]]; then
    mkdir -p "$OPENCODE_PROMPTS_DIR"
    cp "${DEPLOY_ROOT}/prompts/"*.md "$OPENCODE_PROMPTS_DIR/"
    log_ok "${#files[@]} prompt(s) → ${OPENCODE_PROMPTS_DIR}/"
  else
    log_info "[dry-run] ${#files[@]} prompt(s) → ${OPENCODE_PROMPTS_DIR}/"
  fi
}

deploy_skills() {
  [[ -d "${DEPLOY_ROOT}/skills" ]] || return 0
  local skill_dir skill_name
  for skill_dir in "${DEPLOY_ROOT}/skills/"*/; do
    [[ -f "${skill_dir}SKILL.md" ]] || continue
    skill_name="$(basename "$skill_dir")"
    if [[ "$HAS_OPENCODE" == true ]]; then
      if [[ "$DO_COPY" == true ]]; then
        mkdir -p "$OPENCODE_SKILLS_DIR"
        cp -r "$skill_dir" "${OPENCODE_SKILLS_DIR}/"
        log_ok "skill ${skill_name}/ → opencode"
      else
        log_info "[dry-run] skill ${skill_name}/ → ${OPENCODE_SKILLS_DIR}/"
      fi
    fi
    if [[ "$HAS_GROK" == true ]]; then
      if [[ "$DO_COPY" == true ]]; then
        mkdir -p "$GROK_SKILLS_DIR"
        cp -r "$skill_dir" "${GROK_SKILLS_DIR}/"
        log_ok "skill ${skill_name}/ → grok"
      else
        log_info "[dry-run] skill ${skill_name}/ → ${GROK_SKILLS_DIR}/"
      fi
    fi
  done
}

deploy_grok_agents() {
  [[ "$HAS_GROK" == true ]] || return 0
  [[ -d "${DEPLOY_ROOT}/grok/agents" ]] || return 0
  local files=("${DEPLOY_ROOT}/grok/agents/"*.md)
  [[ -e "${files[0]}" ]] || return 0
  if [[ "$DO_COPY" == true ]]; then
    mkdir -p "$GROK_AGENTS_DIR"
    cp "${DEPLOY_ROOT}/grok/agents/"*.md "$GROK_AGENTS_DIR/"
    log_ok "${#files[@]} grok agent profile(s) → ${GROK_AGENTS_DIR}/"
  else
    log_info "[dry-run] ${#files[@]} grok agent profile(s) → ${GROK_AGENTS_DIR}/"
  fi
}

deploy_claude_agents() {
  [[ "$HAS_CLAUDE" == true ]] || return 0
  [[ -d "${DEPLOY_ROOT}/claude/agents" ]] || return 0
  local files=("${DEPLOY_ROOT}/claude/agents/"*.md)
  [[ -e "${files[0]}" ]] || return 0
  if [[ "$DO_COPY" == true ]]; then
    mkdir -p "$CLAUDE_AGENTS_DIR"
    cp "${DEPLOY_ROOT}/claude/agents/"*.md "$CLAUDE_AGENTS_DIR/"
    log_ok "${#files[@]} claude subagent(s) → ${CLAUDE_AGENTS_DIR}/"
  else
    log_info "[dry-run] ${#files[@]} claude subagent(s) → ${CLAUDE_AGENTS_DIR}/"
  fi
}

validate_deployed_clis() {
  [[ "$DO_COPY" == true ]] || return 0
  log_step "Validating deployed configs with installed CLIs"
  if [[ "$HAS_OPENCODE" == true ]]; then
    opencode agent list >/dev/null 2>&1 || { log_error "opencode agent list failed"; return 1; }
    log_ok "opencode agent list succeeded"
  fi
  if [[ "$HAS_GROK" == true ]]; then
    local expected deployed
    expected="$(find "${DEPLOY_ROOT}/grok/agents" -maxdepth 1 -name '*.md' | wc -l)"
    deployed="$(find "$GROK_AGENTS_DIR" -maxdepth 1 -name '*.md' | wc -l)"
    [[ "$deployed" -ge "$expected" ]] || { log_error "grok agent count mismatch"; return 1; }
    log_ok "grok agents: ${deployed} profiles deployed"
  fi
  if [[ "$HAS_CLAUDE" == true ]]; then
    local expected deployed
    expected="$(find "${DEPLOY_ROOT}/claude/agents" -maxdepth 1 -name '*.md' | wc -l)"
    deployed="$(find "$CLAUDE_AGENTS_DIR" -maxdepth 1 -name '*.md' | wc -l)"
    [[ "$deployed" -ge "$expected" ]] || { log_error "claude agent count mismatch"; return 1; }
    log_ok "claude agents: ${deployed} subagents deployed"
  fi
}

main() {
  require_at_least_one_cli
  resolve_sources

  log_step "Generic Agent Definitions Deployer"
  log_info "Source: ${DEPLOY_ROOT}"
  [[ "$HAS_OPENCODE" == true ]] && log_info "OpenCode target: ${OPENCODE_CONFIG_DIR}"
  [[ "$HAS_GROK" == true ]] && log_info "Grok target: ${GROK_AGENTS_DIR}"
  [[ "$HAS_CLAUDE" == true ]] && log_info "Claude target: ${CLAUDE_AGENTS_DIR}"

  deploy_opencode_json
  deploy_prompts
  deploy_skills
  deploy_grok_agents
  deploy_claude_agents
  validate_deployed_clis

  echo
  if [[ "$DO_COPY" == false ]]; then
    log_info "Dry run complete. Run with --force to install."
  else
    log_ok "Deploy complete."
  fi
}

main "$@"