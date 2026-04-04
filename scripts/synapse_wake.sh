#!/bin/bash
# scripts/synapse_wake.sh — SYNAPSE: force idle agent to read its notification inbox
# Phase 206.5 | ARCH: docs/200_taskboard_forever/ROADMAP_SYNAPSE_206.md
# MARKER_206.SYNAPSE_WAKE
#
# Usage: synapse_wake.sh ROLE [AGENT_TYPE]
#   ROLE        — agent callsign (Alpha, Beta, Eta, ...)
#   AGENT_TYPE  — claude_code (default) | opencode | vibe | generic_cli
#
# How it works:
#   Phase 204 already writes a signal file on notify(). If the agent is idle
#   (no tool calls happening), the PreToolUse hook never fires, so the signal
#   is never read. synapse_wake.sh nudges the agent by injecting "/inbox" into
#   its tmux session, which forces a tool call → hook fires → signal read.
#
# No-op conditions (safe to skip wake):
#   - Session does not exist (agent offline)
#   - Agent was recently active (pane activity within ACTIVE_THRESHOLD_SECS)

set -euo pipefail

ROLE="${1:?Usage: synapse_wake.sh ROLE [AGENT_TYPE]}"
AGENT_TYPE="${2:-claude_code}"

SESSION_NAME="vetka-$ROLE"
LOG_PREFIX="[SYNAPSE.WAKE]"

# How recently (seconds) a pane must have been active to be considered busy.
# tmux #{pane_activity} is updated on every byte of output — tool calls produce output.
ACTIVE_THRESHOLD_SECS="${SYNAPSE_WAKE_THRESHOLD:-30}"

# ── Vibe stub ─────────────────────────────────────────────────────────────────
if [ "$AGENT_TYPE" = "vibe" ]; then
    echo "$LOG_PREFIX WARNING: vibe agent wake not implemented — Playwright bridge in 206.7" >&2
    echo "$LOG_PREFIX Role=$ROLE skipped." >&2
    exit 0
fi

# ── Session exists? ───────────────────────────────────────────────────────────
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "$LOG_PREFIX $ROLE: no session '$SESSION_NAME' — agent offline, nothing to wake" >&2
    exit 0
fi

# ── Activity check — no-op if recently active ─────────────────────────────────
LAST_ACTIVITY=$(tmux display-message -p -t "$SESSION_NAME" '#{pane_activity}' 2>/dev/null || echo "0")
NOW=$(date +%s)
DIFF=$((NOW - LAST_ACTIVITY))

if [ "$LAST_ACTIVITY" != "0" ] && [ "$DIFF" -lt "$ACTIVE_THRESHOLD_SECS" ]; then
    echo "$LOG_PREFIX $ROLE is active (pane activity ${DIFF}s ago, threshold=${ACTIVE_THRESHOLD_SECS}s) — no-op"
    exit 0
fi

# ── Send inbox wake trigger ───────────────────────────────────────────────────
tmux send-keys -t "$SESSION_NAME" "vetka session init" Enter
echo "$LOG_PREFIX $ROLE ← woken (sent inbox trigger, last activity was ${DIFF}s ago)"
