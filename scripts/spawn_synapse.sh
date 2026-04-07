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

# ── MARKER_212.RECOLOR: --recolor-all flag to apply colors to all running sessions ──
if [ "${1:-}" = "--recolor-all" ]; then
    PROJECT_ROOT="$HOME/Documents/VETKA_Project/vetka_live_03"
    REGISTRY_YAML="$PROJECT_ROOT/data/templates/agent_registry.yaml"
    echo "[SYNAPSE] Recoloring all running vetka-* sessions from agent_registry.yaml..."
    python3 -c "
import yaml, subprocess
with open('$REGISTRY_YAML') as f:
    reg = yaml.safe_load(f)
for role in reg.get('roles', []):
    cs = role.get('callsign', '')
    color = role.get('tmux_color', '')
    session = f'vetka-{cs}'
    if not color:
        continue
    r = subprocess.run(['tmux', 'has-session', '-t', session], capture_output=True)
    if r.returncode != 0:
        continue
    subprocess.run(['tmux', 'set-option', '-t', session, 'status-style', color], capture_output=True)
    subprocess.run(['tmux', 'set-option', '-t', session, 'status-left', f' [{cs}] '], capture_output=True)
    subprocess.run(['tmux', 'set-option', '-t', session, 'status-right', ' %H:%M '], capture_output=True)
    bg = next((p.split('=')[1] for p in color.split(',') if p.startswith('bg=')), '')
    if bg:
        subprocess.run(['tmux', 'set-option', '-t', session, 'pane-active-border-style', f'fg={bg}'], capture_output=True)
    print(f'  {cs}: {color}')
"
    echo "[SYNAPSE] Done."
    exit 0
fi

ROLE="${1:?Usage: spawn_synapse.sh ROLE WORKTREE [AGENT_TYPE] [INIT_PROMPT]}"
WORKTREE="${2:?Usage: spawn_synapse.sh ROLE WORKTREE [AGENT_TYPE] [INIT_PROMPT]}"
AGENT_TYPE="${3:-claude_code}"
INIT_PROMPT="${4:-vetka session init}"

PROJECT_ROOT="$HOME/Documents/VETKA_Project/vetka_live_03"
WORKTREE_PATH="$PROJECT_ROOT/.claude/worktrees/$WORKTREE"
SESSION_NAME="vetka-$ROLE"
REGISTRY_FILE="$PROJECT_ROOT/data/synapse_sessions.json"
LOG_PREFIX="[SYNAPSE]"

# ── MARKER_209.UX: Color from agent_registry.yaml ────────────
# Each role has a tmux_color field in the registry. Fallback: grey.
REGISTRY_YAML="$PROJECT_ROOT/data/templates/agent_registry.yaml"

_get_role_color() {
    local role="$1"
    local color=""
    # Parse tmux_color for matching callsign from YAML (no python dep for speed)
    if [ -f "$REGISTRY_YAML" ]; then
        color=$(python3 -c "
import yaml, sys
try:
    with open('$REGISTRY_YAML') as f:
        reg = yaml.safe_load(f)
    for r in reg.get('roles', []):
        if r.get('callsign') == '$role':
            print(r.get('tmux_color', ''))
            sys.exit(0)
except Exception:
    pass
" 2>/dev/null)
    fi
    echo "${color:-bg=colour244,fg=white}"  # fallback: grey
}

_apply_tmux_color() {
    local session="$1" role="$2"
    local style
    style=$(_get_role_color "$role")
    tmux set-option -t "$session" status-style "$style" 2>/dev/null || return 0
    tmux set-option -t "$session" status-left " [$role] " 2>/dev/null || true
    tmux set-option -t "$session" status-right " %H:%M " 2>/dev/null || true
    # Extract bg color for pane border
    local bg_color
    bg_color=$(echo "$style" | grep -o 'bg=[^,]*' | cut -d= -f2)
    if [ -n "$bg_color" ]; then
        tmux set-option -t "$session" pane-active-border-style "fg=$bg_color" 2>/dev/null || true
    fi
}

# ── MARKER_SPAWN_FIX_P0: Read model_tier from agent_registry.yaml ──
_get_model_tier() {
    local role="$1"
    local tier=""
    if [ -f "$REGISTRY_YAML" ]; then
        tier=$(python3 -c "
import yaml, sys
try:
    with open('$REGISTRY_YAML') as f:
        reg = yaml.safe_load(f)
    for r in reg.get('roles', []):
        if r.get('callsign') == '$role':
            print(r.get('model_tier', ''))
            sys.exit(0)
except Exception:
    pass
" 2>/dev/null)
    fi
    # PyYAML fallback: grep/awk (no deps)
    if [ -z "$tier" ] && [ -f "$REGISTRY_YAML" ]; then
        tier=$(grep -A10 "callsign: \"$role\"" "$REGISTRY_YAML" 2>/dev/null \
            | grep 'model_tier:' | head -1 | awk -F'"' '{print $2}')
    fi
    echo "${tier:-sonnet}"  # fallback: sonnet (NOT opus)
}

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

# ── Pre-spawn: ensure worktree has essential files ────────────
# opencode has no --dangerously-skip-permissions — reading files outside worktree
# triggers permission dialogs. Copy essential shared config into worktree beforehand.
if [ "$AGENT_TYPE" = "opencode" ] || [ "$AGENT_TYPE" = "generic_cli" ]; then
    # Ensure opencode.json with MCP config exists
    if [ ! -f "$WORKTREE_PATH/opencode.json" ] && [ -f "$PROJECT_ROOT/opencode.json" ]; then
        cp "$PROJECT_ROOT/opencode.json" "$WORKTREE_PATH/opencode.json"
        echo "$LOG_PREFIX Copied opencode.json → worktree"
    fi
    # Ensure AGENTS.md exists (opencode's system prompt file)
    if [ ! -f "$WORKTREE_PATH/AGENTS.md" ] && [ -f "$PROJECT_ROOT/AGENTS.md" ]; then
        cp "$PROJECT_ROOT/AGENTS.md" "$WORKTREE_PATH/AGENTS.md"
        echo "$LOG_PREFIX Copied AGENTS.md → worktree"
    fi
fi

# ── Resolve model tier from registry ─────────────────────────
MODEL_TIER=$(_get_model_tier "$ROLE")
echo "$LOG_PREFIX Model tier for $ROLE: $MODEL_TIER"

# ── Build spawn command per agent type ────────────────────────
case "$AGENT_TYPE" in
    claude_code)
        SPAWN_CMD="cd '$WORKTREE_PATH' && claude --dangerously-skip-permissions --model $MODEL_TIER"
        ;;
    free_code)
        # MARKER_GEMMA_FLEET: Gemma agents via free-code + litellm_gemma_bridge
        # MODEL_TIER = ollama model name (gemma4:e4b, gemma4:e2b, gemma4:26b)
        # Requires: LiteLLM on :4000 + litellm_gemma_bridge.py on :4001
        GEMMA_BRIDGE_URL="${GEMMA_BRIDGE_URL:-http://localhost:4001}"
        FREE_CODE_BIN="${FREE_CODE_BIN:-$HOME/Documents/VETKA_Project/free-code/cli-dev}"
        # --bare: skip OAuth/keychain, use ANTHROPIC_API_KEY from env strictly
        # Without --bare, Free Code ignores ANTHROPIC_BASE_URL and uses its saved credentials
        # --add-dir: re-inject CLAUDE.md (--bare disables auto-discovery)
        # CLAUDE.md contains Gemma XML tool call protocol (MARKER_GEMMA_BRIDGE_3B)
        SPAWN_CMD="cd '$WORKTREE_PATH' && ANTHROPIC_BASE_URL=$GEMMA_BRIDGE_URL ANTHROPIC_API_KEY=sk-ollama '$FREE_CODE_BIN' --bare --dangerously-skip-permissions --model $MODEL_TIER --add-dir '$WORKTREE_PATH'"
        ;;
    opencode)
        # NOTE: opencode has no auto-approve flag. Agent stays within worktree
        # in normal operation. Permission dialogs only trigger for out-of-worktree reads.
        SPAWN_CMD="cd '$WORKTREE_PATH' && opencode"
        ;;
    generic_cli)
        # generic_cli expects SPAWN_CMD override via env var
        SPAWN_CMD="${SYNAPSE_SPAWN_CMD:-cd '$WORKTREE_PATH' && bash}"
        ;;
    vibe)
        # MARKER_206.VIBE_BRIDGE: Vibe = browser-based, no terminal session.
        # V1 stub: open Chrome if URL set, otherwise graceful skip.
        # V2 (SYNAPSE-206.7): full Playwright prompt injection via vibe_bridge.py
        VIBE_URL="${SYNAPSE_VIBE_URL:-}"
        if [ -z "$VIBE_URL" ]; then
            echo "$LOG_PREFIX WARNING: vibe agent $ROLE — SYNAPSE_VIBE_URL not set, skipping (stub)" >&2
            echo "$LOG_PREFIX Vibe fleet is V1 stub. Full support in SYNAPSE-206.7." >&2
            exit 0
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

# ── Set window title: [VETKA] Role — worktree ────────────────
WINDOW_TITLE="[VETKA] ${ROLE} — ${WORKTREE}"
case "$BACKEND" in
    terminal_app)
        osascript -e "tell application \"Terminal\" to set custom title of front window to \"$WINDOW_TITLE\""
        ;;
    iterm2)
        osascript -e "tell application \"iTerm2\" to tell current session of current window to set name to \"$WINDOW_TITLE\""
        ;;
esac
# Also set tmux window name (visible in tmux status bar / tmux ls)
sleep 0.3
tmux rename-window -t "$SESSION_NAME" "$WINDOW_TITLE" 2>/dev/null || true
echo "$LOG_PREFIX Window title set: $WINDOW_TITLE"

# ── MARKER_209.UX: Apply role color to tmux status bar ───────
_apply_tmux_color "$SESSION_NAME" "$ROLE"
echo "$LOG_PREFIX Color applied: $ROLE → $(_get_role_color "$ROLE")"

# ── Update session registry ──────────────────────────────────
mkdir -p "$(dirname "$REGISTRY_FILE")"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

python3 -c "
import json
try:
    with open('$REGISTRY_FILE') as f:
        reg = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
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

echo "$LOG_PREFIX Registry updated: $REGISTRY_FILE"

# ── Auto-init: wait for agent to boot, then send init prompt ──
# FIX: was claude_code only — now supports all CLI agent types (opencode, generic_cli)
# Uses synapse_write.sh which handles agent-type-aware submit (bug #1 fix)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -n "$INIT_PROMPT" ] && [ "$AGENT_TYPE" != "vibe" ]; then
    # Boot time varies by agent type
    case "$AGENT_TYPE" in
        claude_code) BOOT_WAIT=8 ;;
        opencode)    BOOT_WAIT=5 ;;
        *)           BOOT_WAIT=3 ;;
    esac
    echo "$LOG_PREFIX Waiting ${BOOT_WAIT}s for $AGENT_TYPE to boot..."
    (
        sleep "$BOOT_WAIT"
        if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            "$SCRIPT_DIR/synapse_write.sh" "$ROLE" "$INIT_PROMPT" "$AGENT_TYPE"
            echo "$LOG_PREFIX Auto-init sent: '$INIT_PROMPT' → $SESSION_NAME ($AGENT_TYPE)"
        else
            echo "$LOG_PREFIX WARNING: tmux session $SESSION_NAME gone before auto-init"
        fi
    ) &
    echo "$LOG_PREFIX Auto-init scheduled (background PID $!)"
fi

echo "$LOG_PREFIX To write: scripts/synapse_write.sh $ROLE 'your prompt' $AGENT_TYPE"
echo "$LOG_PREFIX To wake:  scripts/synapse_wake.sh $ROLE"

# ── MARKER_209.UX: Recolor all running vetka-* sessions ──────
# Apply colors to any already-running sessions that may lack them
for existing_session in $(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep '^vetka-'); do
    existing_role="${existing_session#vetka-}"
    _apply_tmux_color "$existing_session" "$existing_role"
done
echo "$LOG_PREFIX Recolor pass complete for all vetka-* sessions"
