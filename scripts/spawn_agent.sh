#!/bin/bash
# scripts/spawn_agent.sh — spawn Claude Code agent in detached tmux session
# Phase 205.1 | ARCH: docs/200_taskboard_forever/ARCH_AGENT_AUTOSPAWN_205.md

set -euo pipefail

ROLE="${1:?Usage: spawn_agent.sh ROLE WORKTREE}"
WORKTREE="${2:?Usage: spawn_agent.sh ROLE WORKTREE}"
PROJECT_ROOT="$HOME/Documents/VETKA_Project/vetka_live_03"
WORKTREE_PATH="$PROJECT_ROOT/.claude/worktrees/$WORKTREE"
SESSION_NAME="vetka-$ROLE"

# Validate worktree exists
if [ ! -d "$WORKTREE_PATH" ]; then
    echo "[SPAWN] ERROR: worktree not found: $WORKTREE_PATH" >&2
    exit 1
fi

# Guard: don't duplicate
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "[SPAWN] $ROLE already running in tmux session $SESSION_NAME"
    exit 0
fi

# Spawn detached tmux session with claude
# --dangerously-skip-permissions shows a confirmation prompt (Down=Yes, Enter=confirm)
# We auto-accept by sending keystrokes after a short delay
tmux new-session -d -s "$SESSION_NAME" \
    "cd '$WORKTREE_PATH' && claude --dangerously-skip-permissions"

# Auto-accept bypass permissions prompt
(sleep 2 && tmux send-keys -t "$SESSION_NAME" Down 2>/dev/null && \
 sleep 0.3 && tmux send-keys -t "$SESSION_NAME" Enter 2>/dev/null) &

echo "[SPAWN] $ROLE spawned in $WORKTREE → tmux attach -t $SESSION_NAME"
