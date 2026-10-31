#!/usr/bin/env bash
# MDU-48 connectivity probe — prints neutral environment facts for the three
# symptoms. It does NOT judge PASS/FAIL: the test phase interprets the values.
# Exit code is always 0 so callers can read the facts even when a gap exists.
# Stdout only; no writes.

set -uo pipefail

DEPLOYED_CONFIG="${HOME}/.config/opencode/opencode.json"

# Symptom 3, part 1: is the Blender APPLICATION running (exact process name)?
# `pgrep -f blender` is NOT used: it matches the `uvx mcp-for-blender` launcher
# processes, which say nothing about the app or its addon socket.
if timeout 5 pgrep -x blender >/dev/null 2>&1; then
    APP_RUNNING=yes
else
    APP_RUNNING=no
fi
echo "APP_RUNNING=${APP_RUNNING}"

# Symptom 3, part 2: how many `mcp-for-blender` launcher processes exist?
# Info only — accumulated idle launchers are a leak signal, not a health signal.
LAUNCHER_COUNT=$(timeout 5 pgrep -fc mcp-for-blender 2>/dev/null || true)
LAUNCHER_COUNT=${LAUNCHER_COUNT:-0}
echo "LAUNCHER_COUNT=${LAUNCHER_COUNT}"

# Symptom 2, part 1: Google Chrome stable at the Playwright default path?
if [ -e /opt/google/chrome/chrome ]; then
    CHROME_PATH_FOUND=yes
else
    CHROME_PATH_FOUND=no
fi
echo "CHROME_PATH_FOUND=${CHROME_PATH_FOUND}"

# Symptom 2, part 2: deployed Playwright MCP args (channel default when
# `--browser` is absent).
if [ -r "$DEPLOYED_CONFIG" ]; then
    if timeout 5 grep -q '"--caps=devtools,network,testing"' "$DEPLOYED_CONFIG"; then
        if timeout 5 grep -q '"--browser"' "$DEPLOYED_CONFIG"; then
            echo "MCP_ARGS=caps=devtools,network,testing browser=<set>"
        else
            echo "MCP_ARGS=caps=devtools,network,testing browser=<absent:channel default chrome>"
        fi
    else
        echo "MCP_ARGS=<caps flag not found in ${DEPLOYED_CONFIG}>"
    fi
else
    echo "MCP_ARGS=<config unreadable: ${DEPLOYED_CONFIG}>"
fi

exit 0
