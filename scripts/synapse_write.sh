#!/bin/bash
# scripts/synapse_write.sh — Inject prompt text into running Synapse agent
# Phase 209 | MARKER_209.SYNAPSE_WRITE
#
# Usage: synapse_write.sh ROLE 'prompt text' [AGENT_TYPE]
#   echo "multi-line prompt" | synapse_write.sh ROLE - [AGENT_TYPE]
#
# Works WITHOUT window focus — uses tmux send-keys for programmatic access.

set -euo pipefail

ROLE="${1:?Usage: synapse_write.sh ROLE 'prompt text' [AGENT_TYPE]}"
PROMPT="${2:?Usage: synapse_write.sh ROLE 'prompt text' [AGENT_TYPE]}"
AGENT_TYPE="${3:-claude_code}"

SESSION_NAME="vetka-$ROLE"
LOG_PREFIX="[SYNAPSE-WRITE]"

# ── Validate session exists ────────────────────────────────
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "$LOG_PREFIX ERROR: no tmux session '$SESSION_NAME' — agent not running" >&2
    exit 1
fi

# ── Read from stdin if PROMPT is "-" ───────────────────────
if [ "$PROMPT" = "-" ]; then
    PROMPT=$(cat)
fi

if [ -z "$PROMPT" ]; then
    echo "$LOG_PREFIX ERROR: empty prompt" >&2
    exit 1
fi

# ── Vibe agents: signal file mechanism (no tmux) ──────────
if [ "$AGENT_TYPE" = "vibe" ]; then
    SIGNAL_DIR="$HOME/.vetka/signals"
    mkdir -p "$SIGNAL_DIR"
    SIGNAL_FILE="$SIGNAL_DIR/${ROLE}_write_$(date +%s).json"
    python3 -c "
import json, sys
json.dump({'role': '$ROLE', 'prompt': sys.stdin.read(), 'ts': $(date +%s)}, open('$SIGNAL_FILE', 'w'))
" <<< "$PROMPT"
    echo "$LOG_PREFIX $ROLE (vibe) signal written to $SIGNAL_FILE"
    exit 0
fi

# ── MARKER_212.SUBMIT_KEY: Per-agent-type submit timing ───
# opencode Bubble Tea TUI needs a delay between paste/type and Enter.
# Without delay, Enter arrives before TUI processes the text and gets
# swallowed or treated as newline. 0.3s is enough for TUI event loop.
# Verified: Commander tested bare Enter on Polaris — works WITH delay.
SUBMIT_DELAY="${SYNAPSE_SUBMIT_DELAY:-0.3}"

# ── Detect single-line vs multi-line ──────────────────────
NEWLINE_COUNT=$(echo "$PROMPT" | wc -l | tr -d ' ')

if [ "$NEWLINE_COUNT" -le 1 ]; then
    # Single-line: type text, wait for TUI, then Enter
    tmux send-keys -t "$SESSION_NAME" "$PROMPT"
    sleep "$SUBMIT_DELAY"
    tmux send-keys -t "$SESSION_NAME" Enter
    echo "$LOG_PREFIX Sent to $ROLE ($AGENT_TYPE): ${PROMPT:0:80}..."
else
    # Multi-line: use tmux load-buffer + paste, wait for TUI, then Enter
    TMPFILE=$(mktemp /tmp/synapse_write_XXXXXX.txt)
    echo "$PROMPT" > "$TMPFILE"
    tmux load-buffer -b synapse_write_buf "$TMPFILE"
    tmux paste-buffer -b synapse_write_buf -t "$SESSION_NAME"
    sleep "$SUBMIT_DELAY"
    tmux send-keys -t "$SESSION_NAME" Enter
    rm -f "$TMPFILE"
    echo "$LOG_PREFIX Pasted multi-line to $ROLE ($AGENT_TYPE, ${NEWLINE_COUNT} lines)"
fi
