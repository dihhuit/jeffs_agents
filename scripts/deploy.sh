#!/usr/bin/env bash
# Deploy generic agent definitions to OpenCode, Grok Build, and/or Claude Code user config dirs.
#
# Usage:
#   ./deploy.sh                          # dry run (paid tier)
#   ./deploy.sh --force                  # install the single paid config
#   ./deploy.sh --force --rebuild        # rebuild then install
#   ./deploy.sh --force --tier=paid      # same as the default (paid == go)
#
# MDU-40 retired the Zen tier and the two-file parked layout: there is exactly
# one config (opencode.json, every agent on a paid model) and it installs to
# ~/.config/opencode/opencode.json. Rollback is a git operation:
#   git revert <mdu-40-commit> && ./build.sh && ./deploy.sh --force
#
# A model-health probe gate (scripts/lib/probe_models.py --gate --config) runs
# before the copy. In this public base repo it is ADVISORY: a missing report or
# no `opencode` CLI only prints, never aborts. Overlays run the same gate hard.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

DO_COPY=false
DO_REBUILD=false
TIER="paid"
ARGS=("$@")
for ((i = 0; i < ${#ARGS[@]}; i++)); do
  case "${ARGS[$i]}" in
    --force) DO_COPY=true ;;
    --rebuild) DO_REBUILD=true ;;
    --tier=*) TIER="${ARGS[$i]#--tier=}" ;;
    --tier)
      i=$((i + 1))
      TIER="${ARGS[$i]:-}"
      ;;
    *) log_warn "ignoring unknown argument: ${ARGS[$i]}" ;;
  esac
done
case "$TIER" in
  paid | go) TIER="paid" ;;
  zen)
    log_error "zen tier retired in MDU-40; use paid (single config)"
    log_error "rollback instead: git revert <mdu-40-commit> && ./build.sh && ./deploy.sh --force"
    exit 2
    ;;
  *)
    log_error "--tier must be 'paid' (alias 'go'); got '${TIER}'"
    exit 2
    ;;
esac

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

# Model-health probe gate (MDU-38, single config per MDU-40), advisory in the
# public base repo. A stranger with no probe report or no `opencode` CLI must
# still be able to deploy, so every outcome prints and returns 0. The overlay
# deploy.sh runs this hard.
probe_gate_advisory() {
  local report="${REPO_ROOT}/config/model-probe-report.json"
  local active="${DEPLOY_ROOT}/opencode.json"
  local output="" rc=0
  log_step "Model-health probe gate (advisory)"
  output="$(python3 "${SCRIPT_DIR}/lib/probe_models.py" --gate \
    --report "$report" \
    --config "$active" 2>&1)" || rc=$?
  if [[ "$rc" -eq 0 ]]; then
    log_ok "model-health probe gate: green"
  elif [[ "$rc" -eq 2 ]]; then
    log_info "[gate] model-health probe not evaluable here (no CLI, report or config); advisory only in the base repo"
    log_info "  bootstrap: python3 scripts/lib/probe_models.py --refresh --gate --config '$active'"
  else
    log_warn "[gate] model-health probe RED — advisory only in the base repo, deploy continues"
    printf '%s\n' "$output" >&2
    log_warn "  bootstrap: python3 scripts/lib/probe_models.py --refresh --gate --config '$active'"
  fi
  return 0
}

# Grok-xai hard rule check (MDU-42): every grok-named agent (grok-*,
# grokestrator, grok-plan) in a config must resolve to an xai/* model. Unlike
# the probe gate this is a hard failure in the base repo too: delegating a
# grok-named agent to a free or Go-substituted opencode model is never
# allowed, so a named failure aborts before any copy.
grok_xai_gate() {
  local active="$1"
  local output rc=0
  log_step "Grok-xai hard-rule gate (${active})"
  output="$(python3 "${SCRIPT_DIR}/lib/model_registry.py" --grok-xai-check "$active" 2>&1)" || rc=$?
  if [[ "$rc" -eq 0 ]]; then
    log_ok "grok-xai hard-rule gate: green"
    return 0
  fi
  log_error "grok-named agent(s) must use xai/* account models"
  printf '%s\n' "$output" >&2
  return 1
}

deploy_opencode_json() {
  [[ "$HAS_OPENCODE" == true ]] || return 0
  local active="${DEPLOY_ROOT}/opencode.json"
  if [[ ! -f "$active" ]]; then
    if [[ "$DO_COPY" == true ]]; then
      log_error "paid config not found: ${active}"
      log_error "run ./build.sh first (or ./deploy.sh --force --rebuild)"
      return 1
    fi
    log_warn "paid config not found: ${active} (run ./build.sh)"
    return 0
  fi

  # MDU-42: the grok-xai hard rule runs once, on the single active config,
  # before any copy. The advisory probe gate in main() already measures the
  # xai/* targets; this gate is what actually aborts on a downgrade.
  grok_xai_gate "$active"

  if [[ "$DO_COPY" == true ]]; then
    mkdir -p "$OPENCODE_CONFIG_DIR"
    cp "$active" "${OPENCODE_CONFIG_DIR}/opencode.json"
    log_ok "opencode.json (paid) → ${OPENCODE_CONFIG_DIR}/opencode.json"
  else
    log_info "[dry-run] opencode.json (paid) → ${OPENCODE_CONFIG_DIR}/opencode.json"
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
    # V2 dropped `opencode agent list`. `debug agents` prints the loaded registry.
    opencode debug agents >/dev/null 2>&1 || { log_error "opencode debug agents failed"; return 1; }
    log_ok "opencode debug agents succeeded"
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
  log_info "Tier: ${TIER} (single config: opencode.json)"
  [[ "$HAS_OPENCODE" == true ]] && log_info "OpenCode target: ${OPENCODE_CONFIG_DIR}"
  [[ "$HAS_GROK" == true ]] && log_info "Grok target: ${GROK_AGENTS_DIR}"
  [[ "$HAS_CLAUDE" == true ]] && log_info "Claude target: ${CLAUDE_AGENTS_DIR}"

  probe_gate_advisory
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