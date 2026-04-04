#!/bin/bash
# scripts/spawn_synapse.sh — SYNAPSE v2: multi-backend agent spawn with auto-init
# Phase 206.1+ | ARCH: docs/200_taskboard_forever/ROADMAP_SYNAPSE_206.md
# MARKER_206.SYNAPSE_SPAWN_V2
#
# Usage: spawn_synapse.sh ROLE WORKTREE [AGENT_TYPE] [INIT_PROMPT]
#   ROLE         — agent callsign (Alpha, Beta, Zeta, etc.)
#   WORKTREE     — worktree directory name under .claude/worktrees/
#   AGENT_TYPE   — claude_code (default) | opencode | vibe | generic_cli
#   INIT_PROMPT  — auto-sent after boot (default: "vetka session init")

set -euo pipefail

ROLE="${1:?Usage: spawn_synapse.sh ROLE WORKTREE [AGENT_TYPE] [INIT_PROMPT]}"
WORKTREE="${2:?Usage: spawn_synapse.sh ROLE WORKTREE [AGENT_TYPE] [INIT_PROMPT]}"
AGENT_TYPE="${3:-claude_code}"
INIT_PROMPT="${4:-vetka session init}"

PROJECT_ROOT="$HOME/Documents/VETKA_Project/vetka_live_03"
WORKTREE_PATH="$PROJECT_ROOT/.claude/worktrees/$WORKTREE"
SESSION_NAME="vetka-$ROLE"
REGISTRY_FILE="$PROJECT_ROOT/data/synapse_sessions.json"
LOG_PREFIX="[SYNAPSE]"

# ── Validate ──────────────────────────────────────────────────
if [ "$AGENT_TYPE" != "vibe" ] && [ ! -d "$WORKTREE_PATH" ]; then
    echo "$LOG_PREFIX ERROR: worktree not found: $WORKTREE_PATH" >&2
    exit 1
fi

# ── Duplicate guard ───────────────────────────────────────────
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "$LOG_PREFIX $ROLE already running in tmux session $SESSION_NAME"
    echo "$LOG_PREFIX To write: scripts/synapse_write.sh $ROLE 'your prompt'"
    exit 0
fi

# ── Build spawn command per agent type ────────────────────────
case "$AGENT_TYPE" in
    claude_code)
        # Start claude without prompt — init sent later via tmux send-keys
        SPAWN_CMD="cd '${WORKTREE_PATH}' && claude --dangerously-skip-permissions"
        ;;
    opencode)
        SPAWN_CMD="cd '${WORKTREE_PATH}' && opencode"
        ;;
    generic_cli)
        SPAWN_CMD="${SYNAPSE_SPAWN_CMD:-cd '${WORKTREE_PATH}' && bash}"
        ;;
    vibe)
        VIBE_URL="${SYNAPSE_VIBE_URL:-}"
        if [ -z "$VIBE_URL" ]; then
            echo "$LOG_PREFIX ERROR: SYNAPSE_VIBE_URL not set for vibe agent $ROLE" >&2
            exit 1
        fi
        open -a "Google Chrome" "$VIBE_URL"
        echo "$LOG_PREFIX $ROLE (vibe) → opened Chrome to $VIBE_URL"
        exit 0
        ;;
    *)
        echo "$LOG_PREFIX ERROR: unknown agent_type '$AGENT_TYPE'" >&2
        exit 1
        ;;
esac

# ── Detect best terminal backend ─────────────────────────────
detect_backend() {
    if ! pgrep -q WindowServer 2>/dev/null; then
        echo "tmux"
        return
    fi
    if [ -n "${SYNAPSE_TERMINAL:-}" ]; then
        echo "$SYNAPSE_TERMINAL"
        return
    fi
    # Always use Terminal.app — iTerm2 AppleScript is unreliable
    echo "terminal_app"
}

BACKEND=$(detect_backend)

# ── Spawn via detected backend ────────────────────────────────
# tmux inside terminal window = programmatic send-keys access without focus
TMUX_INNER="tmux new-session -s ${SESSION_NAME} '${SPAWN_CMD}'"

case "$BACKEND" in
    terminal_app)
        # do script without target = always creates NEW window
        WINDOW_ID=$(osascript <<EOF
tell application "Terminal"
    activate
    do script "${TMUX_INNER}"
    return id of front window
end tell
EOF
)
        echo "$LOG_PREFIX $ROLE spawned via Terminal.app (window $WINDOW_ID) → tmux $SESSION_NAME"
        ;;

    iterm2)
        osascript <<EOF
tell application "iTerm2"
    activate
    set newWindow to (create window with default profile)
    tell current session of newWindow
        write text "${TMUX_INNER}"
    end tell
end tell
EOF
        WINDOW_ID="iterm2-$$"
        echo "$LOG_PREFIX $ROLE spawned via iTerm2 → tmux $SESSION_NAME"
        ;;

    tmux)
        eval "tmux new-session -d -s '${SESSION_NAME}' '${SPAWN_CMD}'"
        WINDOW_ID="headless"
        echo "$LOG_PREFIX $ROLE spawned headless → tmux attach -t $SESSION_NAME"
        ;;

    *)
        echo "$LOG_PREFIX ERROR: unknown backend '$BACKEND'" >&2
        exit 1
        ;;
esac

# ── Update session registry ──────────────────────────────────
mkdir -p "$(dirname "$REGISTRY_FILE")"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Create or update registry JSON
if [ -f "$REGISTRY_FILE" ]; then
    # Use python to safely update JSON
    python3 -c "
import json, sys
try:
    with open('$REGISTRY_FILE') as f:
        reg = json.load(f)
except:
    reg = {}
reg['$ROLE'] = {
    'tmux_session': '$SESSION_NAME',
    'window_id': '$WINDOW_ID',
    'worktree': '$WORKTREE',
    'agent_type': '$AGENT_TYPE',
    'started_at': '$TIMESTAMP',
    'pid': $$
}
with open('$REGISTRY_FILE', 'w') as f:
    json.dump(reg, f, indent=2)
"
else
    python3 -c "
import json
reg = {'$ROLE': {
    'tmux_session': '$SESSION_NAME',
    'window_id': '$WINDOW_ID',
    'worktree': '$WORKTREE',
    'agent_type': '$AGENT_TYPE',
    'started_at': '$TIMESTAMP',
    'pid': $$
}}
with open('$REGISTRY_FILE', 'w') as f:
    json.dump(reg, f, indent=2)
"
fi

echo "$LOG_PREFIX Registry updated: $REGISTRY_FILE"

# ── Auto-init: wait for Claude Code to boot, then send init prompt ──
if [ -n "$INIT_PROMPT" ] && [ "$AGENT_TYPE" = "claude_code" ]; then
    echo "$LOG_PREFIX Waiting 8s for Claude Code to boot..."
    (
        sleep 8
        if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            tmux send-keys -t "$SESSION_NAME" "$INIT_PROMPT" Enter
            echo "$LOG_PREFIX Auto-init sent: '$INIT_PROMPT' → $SESSION_NAME"
        else
            echo "$LOG_PREFIX WARNING: tmux session $SESSION_NAME gone before auto-init"
        fi
    ) &
    echo "$LOG_PREFIX Auto-init scheduled (background PID $!)"
fi

echo "$LOG_PREFIX To write: scripts/synapse_write.sh $ROLE 'your prompt'"
echo "$LOG_PREFIX To wake:  scripts/synapse_wake.sh $ROLE"
