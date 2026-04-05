#!/bin/bash
# MARKER_204.UDS_START: Start VETKA UDS Event Daemon if not already running.
# Usage: ./scripts/start_uds_daemon.sh [--stop|--status]
#
# The daemon fans out TaskBoard events to connected MCP server processes.
# Zero CPU when idle — kernel manages wake-up via kqueue/epoll.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DAEMON_SCRIPT="$SCRIPT_DIR/uds_daemon.py"
PYTHON="${VETKA_PYTHON:-$(dirname "$SCRIPT_DIR")/.venv/bin/python3}"
SOCKET_PATH="/tmp/vetka-events.uds"
PID_FILE="/tmp/vetka-events-daemon.pid"

# Pass through --stop / --status to daemon script
if [[ "${1:-}" == "--stop" ]]; then
    "$PYTHON" "$DAEMON_SCRIPT" --stop
    exit $?
fi

if [[ "${1:-}" == "--status" ]]; then
    "$PYTHON" "$DAEMON_SCRIPT" --status
    exit $?
fi

# Check if already running
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "[UDS] Daemon already running (PID $PID, socket $SOCKET_PATH)"
        exit 0
    else
        echo "[UDS] Stale PID file (process $PID dead), removing..."
        rm -f "$PID_FILE"
    fi
fi

# Kill orphaned MCP bridge zombies (detached from any terminal)
ZOMBIES=$(ps aux | grep vetka_mcp_bridge | grep -v grep | awk '$7 == "??" {print $2}' | wc -l | tr -d ' ')
if [[ "$ZOMBIES" -gt 0 ]]; then
    echo "[UDS] Killing $ZOMBIES orphaned MCP bridge processes..."
    ps aux | grep vetka_mcp_bridge | grep -v grep | awk '$7 == "??" {print $2}' | xargs kill -9 2>/dev/null || true
fi

# Clean stale socket
rm -f "$SOCKET_PATH"

# Start daemon in background
echo "[UDS] Starting VETKA Event Daemon..."
"$PYTHON" "$DAEMON_SCRIPT" --daemon

# Verify startup (wait up to 3sec)
for i in 1 2 3; do
    sleep 1
    if [[ -S "$SOCKET_PATH" ]]; then
        echo "[UDS] Daemon running (socket $SOCKET_PATH)"
        if [[ -f "$PID_FILE" ]]; then
            echo "[UDS] PID: $(cat "$PID_FILE")"
        fi
        exit 0
    fi
done

echo "[UDS] ERROR: Daemon failed to start (no socket after 3s)"
exit 1
