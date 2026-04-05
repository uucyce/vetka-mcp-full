#!/bin/bash
# scripts/synapse_wake.sh — Wake idle Synapse agent to read notification inbox
# Phase 209 | MARKER_209.SYNAPSE_WAKE
#
# Usage: synapse_wake.sh ROLE [AGENT_TYPE]
#
# Checks if agent has been idle for WAKE_THRESHOLD seconds (default 30).
# If idle, injects "vetka session init" to trigger context reload + inbox check.

set -euo pipefail

ROLE="${1:?Usage: synapse_wake.sh ROLE [AGENT_TYPE]}"
AGENT_TYPE="${2:-claude_code}"

SESSION_NAME="vetka-$ROLE"
WAKE_THRESHOLD="${SYNAPSE_WAKE_THRESHOLD:-30}"
LOG_PREFIX="[SYNAPSE-WAKE]"

# ── Validate session exists ────────────────────────────────
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "$LOG_PREFIX $ROLE not running (no tmux session '$SESSION_NAME')"
    exit 1
fi

# ── Vibe agents: signal file mechanism ────────────────────
if [ "$AGENT_TYPE" = "vibe" ]; then
    SIGNAL_DIR="$HOME/.vetka/signals"
    mkdir -p "$SIGNAL_DIR"
    SIGNAL_FILE="$SIGNAL_DIR/${ROLE}_wake_$(date +%s).json"
    echo "{\"role\": \"$ROLE\", \"action\": \"wake\", \"ts\": $(date +%s)}" > "$SIGNAL_FILE"
    echo "$LOG_PREFIX $ROLE (vibe) wake signal written to $SIGNAL_FILE"
    exit 0
fi

# ── Check if agent is idle ────────────────────────────────
LAST_ACTIVITY=$(tmux display-message -p -t "$SESSION_NAME" '#{pane_activity}' 2>/dev/null || echo "0")
NOW=$(date +%s)
IDLE_SEC=$(( NOW - LAST_ACTIVITY ))

if [ "$IDLE_SEC" -lt "$WAKE_THRESHOLD" ]; then
    echo "$LOG_PREFIX $ROLE is active (idle ${IDLE_SEC}s < threshold ${WAKE_THRESHOLD}s) — skipping"
    exit 0
fi

# ── Wake: inject session init to reload context ───────────
tmux send-keys -t "$SESSION_NAME" "vetka session init" Enter
echo "$LOG_PREFIX Woke $ROLE (was idle ${IDLE_SEC}s) — sent 'vetka session init'"
