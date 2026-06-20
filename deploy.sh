#!/usr/bin/env bash
set -euo pipefail

# deploy.sh — Generic deploy for open agent definitions (OpenCode + Grok Build)
#
# Usage:
#   ./deploy.sh          # dry run
#   ./deploy.sh --force  # install to default locations for grok-build and opencode on ubuntu/linux

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

OPENCODE_CONFIG_DIR="${HOME}/.config/opencode"
OPENCODE_PROMPTS_DIR="${OPENCODE_CONFIG_DIR}/prompts"
OPENCODE_SKILLS_DIR="${OPENCODE_CONFIG_DIR}/skills"

GROK_AGENTS_DIR="${HOME}/.grok/agents"
GROK_SKILLS_DIR="${HOME}/.grok/skills"

DO_COPY=false
if [[ "${1:-}" == "--force" ]]; then
    DO_COPY=true
fi

# Determine which tools are available (at least one is required)
HAS_OPENCODE=false
HAS_GROK=false
if command -v opencode >/dev/null 2>&1; then
    HAS_OPENCODE=true
fi
if command -v grok >/dev/null 2>&1; then
    HAS_GROK=true
fi

if [ "$HAS_OPENCODE" = false ] && [ "$HAS_GROK" = false ]; then
    echo "Error: Neither opencode nor grok was found in PATH."
    echo "This deploy script requires at least one of OpenCode or Grok Build CLI to be installed."
    echo "Install at least one of them and try again."
    exit 1
fi

TARGETS=""
if [ "$HAS_OPENCODE" = true ]; then
    TARGETS="OpenCode ~/.config/opencode/"
fi
if [ "$HAS_GROK" = true ]; then
    if [ -n "$TARGETS" ]; then
        TARGETS="${TARGETS} , "
    fi
    TARGETS="${TARGETS}Grok ~/.grok/"
fi

echo "==> Generic Agent Definitions Deployer"
echo "    Source: ${SCRIPT_DIR}"
echo "    Targets: ${TARGETS}"
echo ""

# opencode.json (OpenCode only)
if [ "$HAS_OPENCODE" = true ]; then
    if [ -f "${SCRIPT_DIR}/opencode.json" ]; then
        if [ "$DO_COPY" = true ]; then
            mkdir -p "${OPENCODE_CONFIG_DIR}"
            cp "${SCRIPT_DIR}/opencode.json" "${OPENCODE_CONFIG_DIR}/opencode.json"
            echo "  [copied]  opencode.json"
        else
            echo "  [dry-run] opencode.json → ${OPENCODE_CONFIG_DIR}/opencode.json"
        fi
    else
        echo "  [SKIP]    opencode.json not found"
    fi
fi

# prompts/*.md (OpenCode only)
if [ "$HAS_OPENCODE" = true ]; then
    if ls "${SCRIPT_DIR}/prompts/"*.md &>/dev/null 2>&1; then
        if [ "$DO_COPY" = true ]; then
            mkdir -p "${OPENCODE_PROMPTS_DIR}"
            cp "${SCRIPT_DIR}/prompts/"*.md "${OPENCODE_PROMPTS_DIR}/"
            count="$(ls -1 "${OPENCODE_PROMPTS_DIR}"/*.md 2>/dev/null | wc -l)"
            echo "  [copied]  ${count} prompt file(s)"
        else
            count="$(ls -1 "${SCRIPT_DIR}/prompts/"*.md 2>/dev/null | wc -l)"
            echo "  [dry-run] ${count} prompt file(s) → ${OPENCODE_PROMPTS_DIR}/"
        fi
    else
        echo "  [SKIP]    no prompt files found in prompts/"
    fi
fi

# skills/* (to OpenCode and/or Grok depending on availability)
if [ -d "${SCRIPT_DIR}/skills" ] && ls "${SCRIPT_DIR}/skills/"*/SKILL.md &>/dev/null 2>&1; then
    if [ "$DO_COPY" = true ]; then
        if [ "$HAS_OPENCODE" = true ]; then
            mkdir -p "${OPENCODE_SKILLS_DIR}"
            for skill_dir in "${SCRIPT_DIR}/skills/"*/; do
                skill_name="$(basename "${skill_dir}")"
                cp -r "${skill_dir}" "${OPENCODE_SKILLS_DIR}/"
                echo "  [copied]  skill: ${skill_name}/ (opencode)"
            done
        fi
        if [ "$HAS_GROK" = true ]; then
            mkdir -p "${GROK_SKILLS_DIR}"
            for skill_dir in "${SCRIPT_DIR}/skills/"*/; do
                skill_name="$(basename "${skill_dir}")"
                cp -r "${skill_dir}" "${GROK_SKILLS_DIR}/"
                echo "  [copied]  skill: ${skill_name}/ (grok)"
            done
        fi
    else
        for skill_dir in "${SCRIPT_DIR}/skills/"*/; do
            skill_name="$(basename "${skill_dir}")"
            if [ "$HAS_OPENCODE" = true ]; then
                echo "  [dry-run] skill: ${skill_name}/ → ${OPENCODE_SKILLS_DIR}/${skill_name}/ (opencode)"
            fi
            if [ "$HAS_GROK" = true ]; then
                echo "  [dry-run] skill: ${skill_name}/ → ${GROK_SKILLS_DIR}/${skill_name}/ (grok)"
            fi
        done
    fi
else
    echo "  [SKIP]    no skills found in skills/"
fi

# grok/agents/*.md (Grok only)
if [ "$HAS_GROK" = true ]; then
    if ls "${SCRIPT_DIR}/grok/agents/"*.md &>/dev/null 2>&1; then
        if [ "$DO_COPY" = true ]; then
            mkdir -p "${GROK_AGENTS_DIR}"
            count=0
            for agent_file in "${SCRIPT_DIR}/grok/agents/"*.md; do
                agent_name="$(basename "${agent_file}")"
                cp "${agent_file}" "${GROK_AGENTS_DIR}/${agent_name}"
                echo "  [copied]  grok agent profile: ${agent_name}"
                count=$((count + 1))
            done
            echo "  [copied]  ${count} Grok agent profile(s) to ${GROK_AGENTS_DIR}"
        else
            count="$(ls -1 "${SCRIPT_DIR}/grok/agents/"*.md 2>/dev/null | wc -l)"
            echo "  [dry-run] ${count} grok agent profile(s) → ${GROK_AGENTS_DIR}/"
        fi
    else
        echo "  [SKIP]    no agent profiles found in grok/agents/"
    fi
fi

echo ""
if [ "$DO_COPY" = false ]; then
    echo "Dry run complete. Run with --force to actually copy files."
else
    DEPLOYED_TO=""
    if [ "$HAS_OPENCODE" = true ]; then
        DEPLOYED_TO="OpenCode"
    fi
    if [ "$HAS_GROK" = true ]; then
        if [ -n "$DEPLOYED_TO" ]; then
            DEPLOYED_TO="${DEPLOYED_TO} and "
        fi
        DEPLOYED_TO="${DEPLOYED_TO}Grok"
    fi
    echo "Done. Generic agents deployed to ${DEPLOYED_TO} locations."
fi
