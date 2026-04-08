#!/usr/bin/env python3
"""MCP Console - Standalone Debug UI for viewing MCP requests/responses.

Separate server on port 5002 for monitoring MCP tool calls in real-time.
Provides a web-based interface with Socket.IO for live updates.

Features:
- Real-time log streaming via WebSocket
- Request/response visualization with syntax highlighting
- Token usage and latency tracking
- Export logs to JSON files

Usage:
    python src/mcp/mcp_console_standalone.py
    Open: http://localhost:5002

@status: active
@phase: 96
@depends: fastapi, socketio, uvicorn, dataclasses
@used_by: vetka_mcp_bridge.py (archived logging), manual debugging
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import socketio
import uvicorn

# ============================================
# Data Models
# ============================================

@dataclass
class MCPLogEntry:
    id: str
    timestamp: str
    type: str  # 'request' or 'response'
    tool: str
    agent: str
    model: str
    content: str
    tokens: int = 0
    duration_ms: int = 0
    success: bool = True
    error: str = ""


# ============================================
# In-Memory Storage
# ============================================

logs: List[MCPLogEntry] = []
MAX_LOGS = 500


# ============================================
# FastAPI App + Socket.IO
# ============================================

app = FastAPI(title="MCP Console", version="1.0")
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, app)


# ============================================
# HTML Page (inline for simplicity)
# ============================================

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Console - VETKA</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
            background: #1a1a1a;
            color: #e0e0e0;
            height: 100vh;
            overflow: hidden;
        }

        .header {
            background: #252525;
            padding: 12px 20px;
            border-bottom: 1px solid #333;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            font-size: 16px;
            font-weight: 500;
            color: #4a9eff;
        }

        .header h1 span {
            color: #666;
            font-weight: 400;
        }

        .controls {
            display: flex;
            gap: 10px;
        }

        .btn {
            background: #333;
            color: #e0e0e0;
            border: 1px solid #444;
            padding: 6px 14px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
        }

        .btn:hover { background: #444; border-color: #555; }
        .btn.primary { background: #2d5a8a; border-color: #4a9eff; }
        .btn.primary:hover { background: #3d6a9a; }
        .btn.danger { border-color: #ff4a4a; }
        .btn.danger:hover { background: #4a2020; }

        .stats {
            background: #202020;
            padding: 8px 20px;
            display: flex;
            gap: 30px;
            font-size: 12px;
            border-bottom: 1px solid #333;
        }

        .stat { color: #888; }
        .stat strong { color: #4a9eff; margin-left: 5px; }

        .logs-container {
            height: calc(100vh - 100px);
            overflow-y: auto;
            padding: 15px;
        }

        .log-entry {
            background: #252525;
            border-radius: 6px;
            margin-bottom: 10px;
            border: 1px solid #333;
            overflow: hidden;
        }

        .log-header {
            padding: 10px 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
        }

        .log-entry.request .log-header {
            background: #1a2a3a;
            border-left: 3px solid #4a9eff;
        }

        .log-entry.response .log-header {
            background: #1a3a2a;
            border-left: 3px solid #4aff9e;
        }

        .log-entry.error .log-header {
            background: #3a1a1a;
            border-left: 3px solid #ff4a4a;
        }

        .log-meta {
            display: flex;
            gap: 15px;
            color: #888;
        }

        .log-meta .tool { color: #4a9eff; font-weight: 500; }
        .log-meta .model { color: #9e9eff; }
        .log-meta .agent { color: #ff9e4a; }

        .log-time { color: #666; }

        .log-content {
            padding: 12px 15px;
            background: #1e1e1e;
            font-size: 12px;
            line-height: 1.5;
            white-space: pre-wrap;
            word-break: break-word;
            max-height: 300px;
            overflow-y: auto;
        }

        .log-content.collapsed {
            max-height: 80px;
            overflow: hidden;
            position: relative;
        }

        .log-content.collapsed::after {
            content: '... (click to expand)';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(transparent, #1e1e1e);
            padding: 20px 15px 5px;
            color: #666;
            font-style: italic;
        }

        .empty-state {
            text-align: center;
            padding: 60px;
            color: #666;
        }

        .empty-state h2 { font-size: 18px; margin-bottom: 10px; color: #888; }
        .empty-state p { font-size: 13px; }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }

        .status-dot.connected { background: #4aff9e; }
        .status-dot.disconnected { background: #ff4a4a; }

        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #1a1a1a; }
        ::-webkit-scrollbar-thumb { background: #444; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #555; }
    </style>
</head>
<body>
    <div class="header">
        <h1>
            <span class="status-dot disconnected" id="statusDot"></span>
            MCP Console <span>| VETKA Debug</span>
        </h1>
        <div class="controls">
            <button class="btn" onclick="clearLogs()">Clear</button>
            <button class="btn primary" onclick="saveLogs()">Save to File</button>
        </div>
    </div>

    <div class="stats">
        <div class="stat">Requests:<strong id="statRequests">0</strong></div>
        <div class="stat">Responses:<strong id="statResponses">0</strong></div>
        <div class="stat">Tokens:<strong id="statTokens">0</strong></div>
        <div class="stat">Errors:<strong id="statErrors">0</strong></div>
    </div>

    <div class="logs-container" id="logsContainer">
        <div class="empty-state">
            <h2>Waiting for MCP activity...</h2>
            <p>Logs will appear here when Claude Code makes tool calls</p>
        </div>
    </div>

    <script>
        const socket = io('http://localhost:5002');
        let logs = [];
        let stats = { requests: 0, responses: 0, tokens: 0, errors: 0 };

        socket.on('connect', () => {
            document.getElementById('statusDot').classList.remove('disconnected');
            document.getElementById('statusDot').classList.add('connected');
            console.log('Connected to MCP Console');
        });

        socket.on('disconnect', () => {
            document.getElementById('statusDot').classList.remove('connected');
            document.getElementById('statusDot').classList.add('disconnected');
        });

        socket.on('mcp_log', (entry) => {
            logs.unshift(entry);
            if (logs.length > 500) logs.pop();

            if (entry.type === 'request') stats.requests++;
            if (entry.type === 'response') stats.responses++;
            if (entry.tokens) stats.tokens += entry.tokens;
            if (!entry.success) stats.errors++;

            renderLogs();
            updateStats();
        });

        function renderLogs() {
            const container = document.getElementById('logsContainer');

            if (logs.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <h2>Waiting for MCP activity...</h2>
                        <p>Logs will appear here when Claude Code makes tool calls</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = logs.map(log => `
                <div class="log-entry ${log.type} ${log.success ? '' : 'error'}">
                    <div class="log-header">
                        <div class="log-meta">
                            <span class="tool">${log.tool || 'unknown'}</span>
                            <span class="model">${log.model || '-'}</span>
                            <span class="agent">${log.agent || '-'}</span>
                            ${log.tokens ? `<span>${log.tokens} tokens</span>` : ''}
                            ${log.duration_ms ? `<span>${log.duration_ms}ms</span>` : ''}
                        </div>
                        <span class="log-time">${log.timestamp}</span>
                    </div>
                    <div class="log-content collapsed" onclick="this.classList.toggle('collapsed')">
${formatContent(log.content)}
                    </div>
                </div>
            `).join('');
        }

        function formatContent(content) {
            if (typeof content === 'object') {
                return JSON.stringify(content, null, 2);
            }
            return String(content || '');
        }

        function updateStats() {
            document.getElementById('statRequests').textContent = stats.requests;
            document.getElementById('statResponses').textContent = stats.responses;
            document.getElementById('statTokens').textContent = stats.tokens;
            document.getElementById('statErrors').textContent = stats.errors;
        }

        function clearLogs() {
            logs = [];
            stats = { requests: 0, responses: 0, tokens: 0, errors: 0 };
            renderLogs();
            updateStats();
            fetch('/api/clear', { method: 'POST' });
        }

        async function saveLogs() {
            const response = await fetch('/api/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ logs })
            });
            const result = await response.json();
            alert(result.message || 'Saved!');
        }

        // Load initial logs
        fetch('/api/logs')
            .then(r => r.json())
            .then(data => {
                logs = data.logs || [];
                stats = data.stats || stats;
                renderLogs();
                updateStats();
            });
    </script>
</body>
</html>
"""


# ============================================
# Routes
# ============================================

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the MCP Console UI"""
    return HTML_PAGE


@app.get("/api/logs")
async def get_logs():
    """Get all logs"""
    return {
        "logs": [asdict(log) for log in logs],
        "stats": {
            "requests": sum(1 for l in logs if l.type == "request"),
            "responses": sum(1 for l in logs if l.type == "response"),
            "tokens": sum(l.tokens for l in logs),
            "errors": sum(1 for l in logs if not l.success)
        }
    }


@app.post("/api/log")
async def add_log(entry: Dict[str, Any]):
    """Add a log entry (called by MCP bridge)"""
    log_entry = MCPLogEntry(
        id=entry.get("id", str(len(logs))),
        timestamp=entry.get("timestamp", datetime.now().isoformat()),
        type=entry.get("type", "request"),
        tool=entry.get("tool", "unknown"),
        agent=entry.get("agent", ""),
        model=entry.get("model", ""),
        content=entry.get("content", ""),
        tokens=entry.get("tokens", 0),
        duration_ms=entry.get("duration_ms", 0),
        success=entry.get("success", True),
        error=entry.get("error", "")
    )

    logs.insert(0, log_entry)
    if len(logs) > MAX_LOGS:
        logs.pop()

    # Emit to connected clients
    await sio.emit("mcp_log", asdict(log_entry))

    return {"status": "ok"}


@app.post("/api/clear")
async def clear_logs():
    """Clear all logs"""
    logs.clear()
    return {"status": "cleared"}


@app.post("/api/save")
async def save_logs(data: Dict[str, Any]):
    """Save logs to file"""
    save_dir = Path(__file__).parent.parent.parent / "docs" / "mcp_chat"
    save_dir.mkdir(parents=True, exist_ok=True)

    filename = f"mcp_console_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = save_dir / filename

    with open(filepath, "w") as f:
        json.dump(data.get("logs", []), f, indent=2, default=str)

    return {"status": "saved", "message": f"Saved to {filename}", "path": str(filepath)}


# ============================================
# Socket.IO Events
# ============================================

@sio.event
async def connect(sid, environ):
    print(f"[MCP Console] Client connected: {sid}")


@sio.event
async def disconnect(sid):
    print(f"[MCP Console] Client disconnected: {sid}")


# ============================================
# Main
# ============================================

def main():
    print("\n" + "="*50)
    print("  MCP Console - VETKA Debug UI")
    print("="*50)
    print(f"\n  Open: http://localhost:5002\n")
    print("="*50 + "\n")

    uvicorn.run(socket_app, host="0.0.0.0", port=5002, log_level="info")


if __name__ == "__main__":
    main()
