#!/bin/bash
# scripts/reload_mcp.sh — hot-reload all VETKA MCP bridge processes
# Sends SIGUSR1 to trigger importlib.reload() of task_board + event_bus + tools
# MARKER_205.HOT_RELOAD

PIDS=$(pgrep -f "vetka_mcp_bridge" 2>/dev/null)

if [ -z "$PIDS" ]; then
    echo "[RELOAD] No vetka_mcp_bridge processes found"
    exit 0
fi

COUNT=0
for pid in $PIDS; do
    kill -USR1 "$pid" 2>/dev/null && COUNT=$((COUNT + 1))
done

echo "[RELOAD] Sent SIGUSR1 to $COUNT MCP bridge process(es)"
