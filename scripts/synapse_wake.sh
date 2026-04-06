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

# ── ALWAYS inject notification check into agent ───────────
# Previous bug: idle threshold guard skipped tmux poke for "active" agents.
# But agent at idle prompt (waiting for input) counts as "active" by tmux
# pane_activity metric. Result: notifications never delivered.
# Fix: ALWAYS inject. If agent is mid-generation, text queues in tmux
# input buffer and executes when agent finishes.

# Exit tmux copy-mode if active (yellow bar blocks input).
# If not in copy-mode, 'q' goes to input buffer — harmless, gets consumed.
tmux send-keys -t "$SESSION_NAME" q
sleep 0.1

WAKE_PROMPT="Check your notifications: vetka_task_board action=notifications role=$ROLE"
tmux send-keys -t "$SESSION_NAME" "$WAKE_PROMPT"
sleep 0.3  # TUI needs time to process typed text before Enter
tmux send-keys -t "$SESSION_NAME" Enter
echo "$LOG_PREFIX Woke $ROLE — notification check injected"
