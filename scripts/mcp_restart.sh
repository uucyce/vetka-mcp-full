#!/usr/bin/env bash
# MYCELIUM-RESTART: Graceful MCP server stop/restart
# [task:tb_1775402806_44957_3]
#
# Finds all MCP-related processes, sends SIGTERM (graceful),
# waits for exit, escalates to SIGKILL if needed.
#
# Usage:
#   scripts/mcp_restart.sh           # stop all MCP processes
#   scripts/mcp_restart.sh --restart # stop then restart
#   scripts/mcp_restart.sh --status  # show running MCP processes
#   scripts/mcp_restart.sh --dry-run # show what would be killed

set -euo pipefail

LOG="/tmp/mcp_restart.log"
GRACE_TIMEOUT=3  # seconds to wait after SIGTERM before SIGKILL

# Process patterns to target (matched via pgrep -f)
PATTERNS=(
    "mycelium_mcp_server\.py"
    "vetka_mcp_bridge\.py"
    "vetka_mcp_server\.py"
    "uds_daemon\.py"
)

# --- helpers ---

log() {
    local msg
    msg="$(date '+%Y-%m-%d %H:%M:%S') $*"
    echo "$msg"
    echo "$msg" >> "$LOG"
}

find_pids() {
    # Returns PIDs matching any of our patterns, excluding this script and grep itself
    local pids=()
    for pat in "${PATTERNS[@]}"; do
        while IFS= read -r pid; do
            [[ -n "$pid" ]] && pids+=("$pid")
        done < <(pgrep -f "$pat" 2>/dev/null || true)
    done
    # Deduplicate
    printf '%s\n' "${pids[@]}" 2>/dev/null | sort -un
}

show_status() {
    local found=0
    for pat in "${PATTERNS[@]}"; do
        local pids
        pids=$(pgrep -f "$pat" 2>/dev/null || true)
        if [[ -n "$pids" ]]; then
            found=1
            while IFS= read -r pid; do
                local cmd
                cmd=$(ps -p "$pid" -o command= 2>/dev/null || echo "(unknown)")
                echo "  PID $pid: $cmd"
            done <<< "$pids"
        fi
    done
    if [[ "$found" -eq 0 ]]; then
        echo "  No MCP processes running."
    fi
}

graceful_stop() {
    local pids
    pids=$(find_pids)

    if [[ -z "$pids" ]]; then
        log "No MCP processes found — nothing to stop."
        return 0
    fi

    # Phase 1: SIGTERM
    local count=0
    while IFS= read -r pid; do
        local cmd
        cmd=$(ps -p "$pid" -o command= 2>/dev/null || echo "(unknown)")
        log "SIGTERM → PID $pid ($cmd)"
        kill -TERM "$pid" 2>/dev/null || true
        count=$((count + 1))
    done <<< "$pids"

    log "Sent SIGTERM to $count process(es). Waiting ${GRACE_TIMEOUT}s..."
    sleep "$GRACE_TIMEOUT"

    # Phase 2: Check survivors, SIGKILL if needed
    local survivors
    survivors=$(find_pids)
    if [[ -n "$survivors" ]]; then
        while IFS= read -r pid; do
            local cmd
            cmd=$(ps -p "$pid" -o command= 2>/dev/null || echo "(unknown)")
            log "SIGKILL → PID $pid (survived SIGTERM) ($cmd)"
            kill -9 "$pid" 2>/dev/null || true
        done <<< "$survivors"
        sleep 1
    fi

    # Phase 3: Final verification
    local remaining
    remaining=$(find_pids)
    if [[ -n "$remaining" ]]; then
        log "WARNING: Processes still alive after SIGKILL:"
        while IFS= read -r pid; do
            log "  PID $pid: $(ps -p "$pid" -o command= 2>/dev/null || echo '(unknown)')"
        done <<< "$remaining"
        return 1
    fi

    log "All MCP processes stopped cleanly."
    return 0
}

do_restart() {
    # Note: MCP servers are spawned by Claude Code via stdio protocol.
    # We can only kill them — Claude Code will re-spawn on next MCP tool call.
    # The uds_daemon is the only standalone process we can restart directly.
    log "NOTE: MCP servers (mycelium, vetka_bridge) are stdio children of Claude Code."
    log "They will auto-respawn on the next MCP tool call."
    log "Restarting uds_daemon if it was running..."

    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local daemon_script="$script_dir/uds_daemon.py"

    if [[ -f "$daemon_script" ]]; then
        nohup python3 "$daemon_script" >> /tmp/uds_daemon.log 2>&1 &
        log "uds_daemon started: PID $!"
    else
        log "uds_daemon.py not found at $daemon_script — skipped."
    fi
}

# --- main ---

log "=== mcp_restart.sh invoked: $* ==="

case "${1:-}" in
    --status)
        echo "MCP processes:"
        show_status
        ;;
    --dry-run)
        echo "Would stop these MCP processes:"
        show_status
        ;;
    --restart)
        graceful_stop
        do_restart
        ;;
    --help|-h)
        echo "Usage: mcp_restart.sh [--restart|--status|--dry-run|--help]"
        echo ""
        echo "  (no args)   Stop all MCP processes (graceful SIGTERM → SIGKILL)"
        echo "  --restart   Stop all, then restart uds_daemon (MCP servers auto-respawn)"
        echo "  --status    Show running MCP processes"
        echo "  --dry-run   Show what would be killed"
        echo ""
        echo "Targets: mycelium_mcp_server, vetka_mcp_bridge, vetka_mcp_server, uds_daemon"
        echo "Log: $LOG"
        ;;
    "")
        graceful_stop
        ;;
    *)
        echo "Unknown flag: $1 (use --help)" >&2
        exit 1
        ;;
esac
