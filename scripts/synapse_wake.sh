#!/bin/bash
# scripts/synapse_wake.sh — Wake Synapse agent with dual alert (visual + tmux)
# Phase 209.4 | MARKER_209.DUAL_WAKE
#
# Usage: synapse_wake.sh ROLE [AGENT_TYPE] [MESSAGE]
#
# ALWAYS sends macOS notification (visual alert for human operator).
# If agent is idle (> WAKE_THRESHOLD), also injects tmux text poke.
# This ensures Commander sees the alert even when mid-conversation.

set -euo pipefail

ROLE="${1:?Usage: synapse_wake.sh ROLE [AGENT_TYPE] [MESSAGE]}"
AGENT_TYPE="${2:-claude_code}"
MESSAGE="${3:-Agent $ROLE has pending notifications}"

SESSION_NAME="vetka-$ROLE"
WAKE_THRESHOLD="${SYNAPSE_WAKE_THRESHOLD:-30}"
LOG_PREFIX="[SYNAPSE-WAKE]"

# ── macOS notification (ALWAYS fires — visual interrupt) ──
# This is the critical fix: even if agent is mid-conversation,
# the human operator sees the notification banner.
_send_notification() {
    local title="$1"
    local body="$2"
    if pgrep -q WindowServer 2>/dev/null; then
        osascript -e "display notification \"$body\" with title \"$title\" sound name \"Ping\"" 2>/dev/null || true
        echo "$LOG_PREFIX macOS notification sent: $title"
    fi
}

# ── Vibe agents: signal file + notification ───────────────
if [ "$AGENT_TYPE" = "vibe" ]; then
    SIGNAL_DIR="$HOME/.vetka/signals"
    mkdir -p "$SIGNAL_DIR"
    SIGNAL_FILE="$SIGNAL_DIR/${ROLE}_wake_$(date +%s).json"
    echo "{\"role\": \"$ROLE\", \"action\": \"wake\", \"ts\": $(date +%s), \"message\": \"$MESSAGE\"}" > "$SIGNAL_FILE"
    _send_notification "SYNAPSE: $ROLE" "$MESSAGE"
    echo "$LOG_PREFIX $ROLE (vibe) wake signal + notification sent"
    exit 0
fi

# ── Validate tmux session exists ──────────────────────────
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    # Agent not running — still send notification so operator knows
    _send_notification "SYNAPSE: $ROLE OFFLINE" "$ROLE is not running — needs spawn"
    echo "$LOG_PREFIX $ROLE not running (no tmux session '$SESSION_NAME')"
    exit 1
fi

# ── ALWAYS send macOS notification ────────────────────────
_send_notification "SYNAPSE: Wake $ROLE" "$MESSAGE"

# ── Check if agent is idle for tmux poke ──────────────────
LAST_ACTIVITY=$(tmux display-message -p -t "$SESSION_NAME" '#{pane_activity}' 2>/dev/null || echo "0")
NOW=$(date +%s)
IDLE_SEC=$(( NOW - LAST_ACTIVITY ))

if [ "$IDLE_SEC" -lt "$WAKE_THRESHOLD" ]; then
    # Agent is active — notification already sent above, skip tmux poke
    # (typing into active conversation would corrupt the prompt)
    echo "$LOG_PREFIX $ROLE is active (idle ${IDLE_SEC}s) — notification sent, tmux poke skipped"
    exit 0
fi

# ── Idle agent: also inject tmux text to trigger inbox read ─
tmux send-keys -t "$SESSION_NAME" "vetka session init"
sleep 0.3  # TUI needs time to process typed text before Enter
tmux send-keys -t "$SESSION_NAME" Enter
echo "$LOG_PREFIX Woke $ROLE (idle ${IDLE_SEC}s) — notification + tmux poke sent"
