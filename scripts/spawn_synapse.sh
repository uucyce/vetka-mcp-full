#!/bin/bash
# scripts/spawn_synapse.sh — SYNAPSE: multi-backend agent spawn in real terminal windows
# Phase 206.1 | ARCH: docs/200_taskboard_forever/ROADMAP_SYNAPSE_206.md
# MARKER_206.SYNAPSE_SPAWN
#
# Usage: spawn_synapse.sh ROLE WORKTREE [AGENT_TYPE]
#   ROLE       — agent callsign (Alpha, Beta, etc.)
#   WORKTREE   — worktree directory name under .claude/worktrees/
#   AGENT_TYPE — claude_code (default) | opencode | vibe | generic_cli

set -euo pipefail

ROLE="${1:?Usage: spawn_synapse.sh ROLE WORKTREE [AGENT_TYPE]}"
WORKTREE="${2:?Usage: spawn_synapse.sh ROLE WORKTREE [AGENT_TYPE]}"
AGENT_TYPE="${3:-claude_code}"

PROJECT_ROOT="$HOME/Documents/VETKA_Project/vetka_live_03"
WORKTREE_PATH="$PROJECT_ROOT/.claude/worktrees/$WORKTREE"
SESSION_NAME="vetka-$ROLE"
LOG_PREFIX="[SYNAPSE]"

# ── Validate ──────────────────────────────────────────────────
if [ "$AGENT_TYPE" != "vibe" ] && [ ! -d "$WORKTREE_PATH" ]; then
    echo "$LOG_PREFIX ERROR: worktree not found: $WORKTREE_PATH" >&2
    exit 1
fi

# ── Duplicate guard ───────────────────────────────────────────
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "$LOG_PREFIX $ROLE already running in tmux session $SESSION_NAME"
    exit 0
fi

# ── Build spawn command per agent type ────────────────────────
case "$AGENT_TYPE" in
    claude_code)
        SPAWN_CMD="cd '$WORKTREE_PATH' && claude --dangerously-skip-permissions"
        ;;
    opencode)
        SPAWN_CMD="cd '$WORKTREE_PATH' && opencode"
        ;;
    generic_cli)
        # generic_cli expects SPAWN_CMD override via env var
        SPAWN_CMD="${SYNAPSE_SPAWN_CMD:-cd '$WORKTREE_PATH' && bash}"
        ;;
    vibe)
        # MARKER_206.VIBE_BRIDGE: Vibe = browser-based, no terminal session.
        # V1: open Chrome to vibe_url. V2 prompt injection: scripts/vibe_bridge.py
        VIBE_URL="${SYNAPSE_VIBE_URL:-}"
        if [ -z "$VIBE_URL" ]; then
            echo "$LOG_PREFIX ERROR: SYNAPSE_VIBE_URL not set for vibe agent $ROLE" >&2
            exit 1
        fi
        open -a "Google Chrome" "$VIBE_URL"
        echo "$LOG_PREFIX $ROLE (vibe) → opened Chrome to $VIBE_URL"
        echo "$LOG_PREFIX To inject prompts: python scripts/vibe_bridge.py --role $ROLE --prompt 'text'"
        exit 0
        ;;
    *)
        echo "$LOG_PREFIX ERROR: unknown agent_type '$AGENT_TYPE'" >&2
        exit 1
        ;;
esac

# ── Detect best terminal backend ─────────────────────────────
# Priority: iTerm2 (if running) > Terminal.app (GUI) > tmux headless
detect_backend() {
    # Check if we have a GUI (macOS with WindowServer)
    if ! pgrep -q WindowServer 2>/dev/null; then
        echo "tmux"
        return
    fi

    # Check SYNAPSE_TERMINAL override
    if [ -n "${SYNAPSE_TERMINAL:-}" ]; then
        echo "$SYNAPSE_TERMINAL"
        return
    fi

    # Prefer iTerm2 if it's installed
    if [ -d "/Applications/iTerm.app" ]; then
        echo "iterm2"
        return
    fi

    # Terminal.app is always available on macOS with GUI
    echo "terminal_app"
}

BACKEND=$(detect_backend)

# ── Spawn via detected backend ────────────────────────────────
# All backends create a tmux session INSIDE the window for programmatic access
TMUX_CMD="tmux new-session -s '$SESSION_NAME' \"$SPAWN_CMD\""

case "$BACKEND" in
    iterm2)
        osascript <<APPLESCRIPT
tell application "iTerm2"
    activate
    set newWindow to (create window with default profile)
    tell current session of newWindow
        write text "$TMUX_CMD"
    end tell
end tell
APPLESCRIPT
        echo "$LOG_PREFIX $ROLE spawned via iTerm2 → tmux session $SESSION_NAME"
        ;;

    terminal_app)
        osascript <<APPLESCRIPT
tell application "Terminal"
    activate
    do script "$TMUX_CMD"
end tell
APPLESCRIPT
        echo "$LOG_PREFIX $ROLE spawned via Terminal.app → tmux session $SESSION_NAME"
        ;;

    tmux)
        # Headless fallback — detached tmux session, no GUI window
        tmux new-session -d -s "$SESSION_NAME" "$SPAWN_CMD"
        echo "$LOG_PREFIX $ROLE spawned headless → tmux attach -t $SESSION_NAME"
        ;;

    *)
        echo "$LOG_PREFIX ERROR: unknown backend '$BACKEND'" >&2
        exit 1
        ;;
esac
