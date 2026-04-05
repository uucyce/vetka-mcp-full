#!/bin/bash
# scripts/synapse_write.sh — SYNAPSE: inject prompt into a running agent's session
# Phase 206.4 | ARCH: docs/200_taskboard_forever/ROADMAP_SYNAPSE_206.md
# MARKER_206.SYNAPSE_WRITE
#
# Usage:
#   synapse_write.sh ROLE 'prompt text' [AGENT_TYPE]
#   echo -e "line1\nline2" | synapse_write.sh ROLE - [AGENT_TYPE]
#
#   ROLE        — agent callsign (Alpha, Beta, Eta, ...)
#   PROMPT      — text to inject, or '-' to read from stdin (multi-line)
#   AGENT_TYPE  — claude_code (default) | opencode | vibe | generic_cli

set -euo pipefail

ROLE="${1:?Usage: synapse_write.sh ROLE PROMPT [AGENT_TYPE]}"
PROMPT_ARG="${2:?Usage: synapse_write.sh ROLE PROMPT [AGENT_TYPE]}"
AGENT_TYPE="${3:-claude_code}"

SESSION_NAME="vetka-$ROLE"
LOG_PREFIX="[SYNAPSE.WRITE]"
TMPFILE=""
BUFFER_NAME="synapse_${ROLE}_write"

cleanup() {
    [ -n "$TMPFILE" ] && [ -f "$TMPFILE" ] && rm -f "$TMPFILE"
    tmux delete-buffer -b "$BUFFER_NAME" 2>/dev/null || true
}
trap cleanup EXIT

# ── Vibe stub (Playwright bridge not yet implemented — SYNAPSE-206.7) ─────────
if [ "$AGENT_TYPE" = "vibe" ]; then
    echo "$LOG_PREFIX WARNING: vibe agent_type not supported yet" >&2
    echo "$LOG_PREFIX Playwright bridge will be wired in SYNAPSE-206.7. Role=$ROLE skipped." >&2
    exit 0
fi

# ── Validate session exists ───────────────────────────────────────────────────
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "$LOG_PREFIX ERROR: tmux session '$SESSION_NAME' not found for role $ROLE" >&2
    echo "$LOG_PREFIX Hint: spawn first with:  spawn_synapse.sh $ROLE <worktree> $AGENT_TYPE" >&2
    exit 1
fi

# ── Resolve prompt ────────────────────────────────────────────────────────────
TMPFILE=$(mktemp /tmp/synapse_write_XXXXXX.txt)

if [ "$PROMPT_ARG" = "-" ]; then
    # Read from stdin (multi-line heredoc / pipe)
    cat > "$TMPFILE"
else
    printf '%s' "$PROMPT_ARG" > "$TMPFILE"
fi

if [ ! -s "$TMPFILE" ]; then
    echo "$LOG_PREFIX ERROR: prompt is empty" >&2
    exit 1
fi

LINE_COUNT=$(wc -l < "$TMPFILE")

# ── Send prompt ───────────────────────────────────────────────────────────────
if [ "$LINE_COUNT" -le 1 ]; then
    # Single-line: send-keys directly (clean, no buffer overhead)
    PROMPT_TEXT=$(cat "$TMPFILE")
    tmux send-keys -t "$SESSION_NAME" "$PROMPT_TEXT" Enter
    PREVIEW="${PROMPT_TEXT:0:80}"
    [ "${#PROMPT_TEXT}" -gt 80 ] && PREVIEW="${PREVIEW}..."
    echo "$LOG_PREFIX $ROLE ← \"$PREVIEW\""
else
    # Multi-line: load into tmux paste buffer, then paste + Enter
    tmux load-buffer -b "$BUFFER_NAME" "$TMPFILE"
    tmux paste-buffer -b "$BUFFER_NAME" -t "$SESSION_NAME"
    tmux send-keys -t "$SESSION_NAME" "" Enter
    echo "$LOG_PREFIX $ROLE ← multi-line prompt injected (${LINE_COUNT} lines)"
fi
