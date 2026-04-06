#!/bin/bash
# scripts/synapse_heartbeat.sh — Free agent heartbeat monitor
# Phase 212.1 | MARKER_212.HEARTBEAT
#
# Detects when opencode/vibe agents stall (rate limit, slow internet, crash).
# On stall: sends osascript notification to Commander + auto-injects 'continue'.
#
# Usage:
#   scripts/synapse_heartbeat.sh              # run once (cron-friendly)
#   scripts/synapse_heartbeat.sh --daemon     # loop every POLL_INTERVAL
#   scripts/synapse_heartbeat.sh --status     # show agent liveness
#
# Env:
#   SYNAPSE_HB_POLL_INTERVAL  — seconds between checks (default: 60)
#   SYNAPSE_HB_STALL_THRESHOLD — seconds of no output = stall (default: 120)
#   SYNAPSE_HB_CAPTURE_LINES  — tmux pane lines to fingerprint (default: 20)
#   SYNAPSE_HB_AUTO_NUDGE     — if "true", auto-send 'continue' (default: true)
#   SYNAPSE_HB_AGENT_FILTER   — comma-separated agent_types to monitor (default: opencode,vibe)

set -euo pipefail

PROJECT_ROOT="$HOME/Documents/VETKA_Project/vetka_live_03"
REGISTRY_FILE="$PROJECT_ROOT/data/synapse_sessions.json"
STATE_DIR="$PROJECT_ROOT/data/heartbeat_state"
POLL_INTERVAL="${SYNAPSE_HB_POLL_INTERVAL:-60}"
STALL_THRESHOLD="${SYNAPSE_HB_STALL_THRESHOLD:-120}"
CAPTURE_LINES="${SYNAPSE_HB_CAPTURE_LINES:-20}"
AUTO_NUDGE="${SYNAPSE_HB_AUTO_NUDGE:-true}"
AGENT_FILTER="${SYNAPSE_HB_AGENT_FILTER:-opencode,vibe}"
LOG_PREFIX="[HEARTBEAT]"

mkdir -p "$STATE_DIR"

# ── Helper: get monitored sessions from synapse_sessions.json ─
get_monitored_sessions() {
    if [ ! -f "$REGISTRY_FILE" ]; then
        return
    fi
    python3 -c "
import json, pathlib
p = pathlib.Path('$REGISTRY_FILE')
if not p.exists():
    exit()
data = json.loads(p.read_text())
filter_types = set('$AGENT_FILTER'.split(','))
for role, info in data.items():
    if not isinstance(info, dict):
        continue
    agent_type = info.get('agent_type', 'claude_code')
    if agent_type not in filter_types:
        continue
    session = info.get('tmux_session', f'vetka-{role}')
    worktree = info.get('worktree', '')
    print(f'{role}|{session}|{worktree}|{agent_type}')
" 2>/dev/null || true
}

# ── Helper: capture pane fingerprint (hash of last N lines) ───
capture_fingerprint() {
    local session_name="$1"
    local output
    output=$(tmux capture-pane -t "$session_name" -p -S "-$CAPTURE_LINES" 2>/dev/null) || true
    if [ -z "$output" ]; then
        echo "no_session"
        return
    fi
    printf '%s' "$output" | shasum -a 256 2>/dev/null | cut -d' ' -f1 || echo "no_session"
}

# ── Helper: notify Commander via osascript ────────────────────
notify_commander() {
    local title="$1"
    local body="$2"
    if pgrep -q WindowServer 2>/dev/null; then
        osascript -e "display notification \"$body\" with title \"$title\" sound name \"Submarine\"" 2>/dev/null || true
    fi
    echo "$LOG_PREFIX NOTIFY: $title — $body"
}

# ── Helper: nudge agent (send 'continue' via tmux) ───────────
nudge_agent() {
    local role="$1"
    local session_name="$2"
    local agent_type="$3"

    if ! tmux has-session -t "$session_name" 2>/dev/null; then
        return 1
    fi

    tmux send-keys -t "$session_name" "continue"
    case "$agent_type" in
        opencode)
            # Escape exits Zen multiline input → compact mode, Enter submits
            tmux send-keys -t "$session_name" Escape
            sleep 0.3
            tmux send-keys -t "$session_name" Enter
            ;;
        *)
            tmux send-keys -t "$session_name" Enter
            ;;
    esac
    echo "$LOG_PREFIX Nudged $role ($agent_type) with 'continue'"
}

# ── Helper: update state file for a role ──────────────────────
update_state() {
    local role="$1"
    local fingerprint="$2"
    local stall_count="$3"
    local ts="${4:-$(date +%s)}"
    echo "${fingerprint}|${ts}|${stall_count}" > "$STATE_DIR/${role}.state"
}

# ── Helper: read state file ──────────────────────────────────
read_state() {
    local role="$1"
    local state_file="$STATE_DIR/${role}.state"
    if [ -f "$state_file" ]; then
        cat "$state_file"
    else
        echo "none|0|0"
    fi
}

# ── Main: check one cycle ─────────────────────────────────────
check_heartbeats() {
    local sessions
    sessions=$(get_monitored_sessions)

    if [ -z "$sessions" ]; then
        return
    fi

    local now
    now=$(date +%s)

    while IFS='|' read -r role session_name worktree agent_type; do
        [ -z "$role" ] && continue

        # Skip if tmux session doesn't exist
        if ! tmux has-session -t "$session_name" 2>/dev/null; then
            continue
        fi

        # Capture current fingerprint
        local current_fp
        current_fp=$(capture_fingerprint "$session_name")

        if [ "$current_fp" = "no_session" ]; then
            continue
        fi

        # Read previous state
        local prev_state prev_fp prev_ts prev_stall_count
        prev_state=$(read_state "$role")
        prev_fp=$(echo "$prev_state" | cut -d'|' -f1)
        prev_ts=$(echo "$prev_state" | cut -d'|' -f2)
        prev_stall_count=$(echo "$prev_state" | cut -d'|' -f3)

        if [ "$current_fp" != "$prev_fp" ]; then
            # Output changed — agent is alive
            if [ "$prev_stall_count" -gt 0 ] 2>/dev/null; then
                echo "$LOG_PREFIX $role recovered (was stalled for $prev_stall_count cycles)"
            fi
            update_state "$role" "$current_fp" "0"
            continue
        fi

        # Output unchanged — check how long
        local elapsed=0
        if [ "$prev_ts" -gt 0 ] 2>/dev/null; then
            elapsed=$(( now - prev_ts ))
        else
            # First time seeing this fingerprint
            update_state "$role" "$current_fp" "0"
            continue
        fi

        local new_stall_count=$(( prev_stall_count + 1 ))

        if [ "$elapsed" -ge "$STALL_THRESHOLD" ]; then
            echo "$LOG_PREFIX $role STALLED: no output change for ${elapsed}s (threshold: ${STALL_THRESHOLD}s)"

            # Notify Commander
            notify_commander "HEARTBEAT: $role stalled" "$role ($agent_type) no output for ${elapsed}s — cycle $new_stall_count"

            # Auto-nudge if enabled (only on first detection, then every 3 cycles)
            if [ "$AUTO_NUDGE" = "true" ]; then
                if [ "$new_stall_count" -le 1 ] || [ $(( new_stall_count % 3 )) -eq 0 ]; then
                    nudge_agent "$role" "$session_name" "$agent_type"
                fi
            fi

            update_state "$role" "$current_fp" "$new_stall_count" "$prev_ts"
        else
            # Not yet at threshold, just update stall count (preserve original timestamp)
            update_state "$role" "$prev_fp" "$new_stall_count" "$prev_ts"
        fi
    done <<< "$sessions"
}

# ── Status command ────────────────────────────────────────────
show_status() {
    echo "$LOG_PREFIX Heartbeat Monitor Status"
    echo "──────────────────────────────────────────"
    echo "  Poll: ${POLL_INTERVAL}s | Stall threshold: ${STALL_THRESHOLD}s | Filter: $AGENT_FILTER"
    echo ""

    local sessions
    sessions=$(get_monitored_sessions)

    if [ -z "$sessions" ]; then
        echo "  No monitored agents in $REGISTRY_FILE"
        return
    fi

    local now
    now=$(date +%s)

    printf "  %-12s %-15s %-10s %-8s %s\n" "ROLE" "SESSION" "TYPE" "STATUS" "DETAIL"
    printf "  %-12s %-15s %-10s %-8s %s\n" "────" "───────" "────" "──────" "──────"

    while IFS='|' read -r role session_name worktree agent_type; do
        [ -z "$role" ] && continue

        local status="UNKNOWN"
        local detail=""

        if ! tmux has-session -t "$session_name" 2>/dev/null; then
            status="OFFLINE"
        else
            local prev_state prev_fp prev_ts prev_stall_count
            prev_state=$(read_state "$role")
            prev_fp=$(echo "$prev_state" | cut -d'|' -f1)
            prev_ts=$(echo "$prev_state" | cut -d'|' -f2)
            prev_stall_count=$(echo "$prev_state" | cut -d'|' -f3)

            if [ "$prev_fp" = "none" ]; then
                status="NEW"
                detail="no data yet"
            elif [ "$prev_stall_count" -gt 0 ] 2>/dev/null; then
                local elapsed=0
                [ "$prev_ts" -gt 0 ] 2>/dev/null && elapsed=$(( now - prev_ts ))
                status="STALL"
                detail="no change ${elapsed}s, nudge#${prev_stall_count}"
            else
                local idle=0
                [ "$prev_ts" -gt 0 ] 2>/dev/null && idle=$(( now - prev_ts ))
                status="ALIVE"
                detail="last change ${idle}s ago"
            fi
        fi

        printf "  %-12s %-15s %-10s %-8s %s\n" "$role" "$session_name" "$agent_type" "$status" "$detail"
    done <<< "$sessions"
}

# ── Entry point ───────────────────────────────────────────────
case "${1:-}" in
    --status)
        show_status
        ;;
    --daemon)
        echo "$LOG_PREFIX Starting daemon (poll: ${POLL_INTERVAL}s, stall: ${STALL_THRESHOLD}s, filter: $AGENT_FILTER)"
        while true; do
            check_heartbeats
            sleep "$POLL_INTERVAL"
        done
        ;;
    *)
        # Single run (cron-friendly)
        check_heartbeats
        ;;
esac
