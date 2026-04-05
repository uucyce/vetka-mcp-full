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

# ── MARKER_209.POLARIS: Model routing from registry ───────
# If SYNAPSE_MODEL_ID is set, use it. Otherwise, look up from agent_registry.yaml.
MODEL_ID="${SYNAPSE_MODEL_ID:-}"
if [ -z "$MODEL_ID" ]; then
    MODEL_ID=$(python3 -c "
import yaml, pathlib
reg = pathlib.Path('$PROJECT_ROOT/data/templates/agent_registry.yaml')
if not reg.exists():
    reg = pathlib.Path('${WORKTREE_PATH}/data/templates/agent_registry.yaml')
if reg.exists():
    data = yaml.safe_load(reg.read_text())
    for r in data.get('roles', []):
        if r.get('callsign') == '$ROLE':
            print(r.get('model_id', ''))
            break
" 2>/dev/null || echo "")
fi

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
    exit 0
fi

# ── Build spawn command per agent type ────────────────────────
case "$AGENT_TYPE" in
    claude_code)
        SPAWN_CMD="cd '$WORKTREE_PATH' && claude --dangerously-skip-permissions"
        ;;
    opencode)
        # MARKER_209.POLARIS: pass model_id if available (e.g. openrouter/qwen/qwen3-235b-a22b:free)
        if [ -n "$MODEL_ID" ]; then
            SPAWN_CMD="cd '$WORKTREE_PATH' && opencode -m '$MODEL_ID'"
        else
            SPAWN_CMD="cd '$WORKTREE_PATH' && opencode"
        fi
        ;;
    generic_cli)
        # generic_cli expects SPAWN_CMD override via env var
        SPAWN_CMD="${SYNAPSE_SPAWN_CMD:-cd '$WORKTREE_PATH' && bash}"
        ;;
    vibe)
        # Vibe = browser-based, no terminal session needed
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

# ── Register session ────────────────────────────────────────
# MARKER_207.SESSION_REGISTRY: Track spawned agents in synapse_sessions.json
_register_session() {
    local ts
    ts=$(date +%s)
    # Use python3 for atomic JSON update (jq not guaranteed)
    python3 -c "
import json, pathlib, sys
p = pathlib.Path('$REGISTRY_FILE')
data = {}
if p.exists():
    try: data = json.loads(p.read_text())
    except: pass
data['$ROLE'] = {
    'tmux_session': '$SESSION_NAME',
    'worktree': '$WORKTREE',
    'agent_type': '$AGENT_TYPE',
    'model_id': '$MODEL_ID' or None,
    'fleet': None,
    'backend': '$BACKEND',
    'spawned_at': $ts,
    'last_activity': $ts,
    'compacting': False,
}
# MARKER_209.POLARIS: detect fleet from registry
try:
    import yaml
    reg_path = __import__('pathlib').Path('$PROJECT_ROOT/data/templates/agent_registry.yaml')
    if reg_path.exists():
        reg = yaml.safe_load(reg_path.read_text())
        for r in reg.get('roles', []):
            if r.get('callsign') == '$ROLE':
                data['$ROLE']['fleet'] = r.get('fleet')
                break
except Exception:
    pass
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(data, indent=2))
" 2>/dev/null || true
}
_register_session
echo "$LOG_PREFIX Registered $ROLE in $REGISTRY_FILE"

# ── Auto-init after boot delay ──────────────────────────────
# MARKER_207.AUTO_INIT: Send init prompt after agent boots (8s delay)
if [ -n "$INIT_PROMPT" ] && [ "$AGENT_TYPE" != "vibe" ]; then
    (
        sleep 8
        if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            tmux send-keys -t "$SESSION_NAME" "$INIT_PROMPT" Enter
            echo "$LOG_PREFIX Auto-init sent to $ROLE: $INIT_PROMPT"
        fi
    ) &
    echo "$LOG_PREFIX Auto-init scheduled (background PID $!)"
fi

echo "$LOG_PREFIX To write: scripts/synapse_write.sh $ROLE 'your prompt'"
echo "$LOG_PREFIX To wake:  scripts/synapse_wake.sh $ROLE"
