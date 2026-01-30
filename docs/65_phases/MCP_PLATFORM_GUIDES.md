# VETKA MCP - Platform Setup Guides

**Phase 65.2 | January 2026**

VETKA MCP Server supports multiple transports for maximum AI platform compatibility.

## Overview

| Platform | Transport | Port | Status |
|----------|-----------|------|--------|
| Claude Desktop/Code | stdio | - | ✅ Production |
| VS Code / Copilot | HTTP | 5002 | ✅ Production |
| Cursor IDE | HTTP | 5002 | ✅ Production |
| JetBrains | SSE | 5003 | ✅ Production |
| Google Gemini CLI | HTTP | 5002 | ✅ Production |
| Xcode | stdio | - | ✅ Should work |
| GitHub Copilot CLI | HTTP | 5002 | ✅ Production |

## Available Tools (13 total)

### Read-Only Tools (8)
| Tool | Description |
|------|-------------|
| `vetka_health` | Check VETKA server health and components |
| `vetka_search_semantic` | Semantic search in knowledge base |
| `vetka_read_file` | Read file content |
| `vetka_list_files` | List files in directory |
| `vetka_search_files` | Search for files |
| `vetka_get_tree` | Get 3D tree structure |
| `vetka_get_knowledge_graph` | Get knowledge graph |
| `vetka_get_metrics` | Get system metrics |

### Write Tools (5)
| Tool | Description | Safety |
|------|-------------|--------|
| `vetka_edit_file` | Edit/create files | dry_run=true by default |
| `vetka_git_commit` | Create git commits | dry_run=true by default |
| `vetka_git_status` | Get git status | Read-only |
| `vetka_run_tests` | Run pytest tests | Controlled execution |
| `vetka_camera_focus` | Focus 3D camera | Requires UI |

---

## Claude Desktop / Claude Code (stdio)

### Quick Setup

```bash
# Register VETKA MCP server
claude mcp add vetka -- python /path/to/vetka_live_03/src/mcp/vetka_mcp_server.py

# Verify
claude mcp list
```

### Manual Setup (claude_desktop_config.json)

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "vetka": {
      "command": "python",
      "args": ["/path/to/vetka_live_03/src/mcp/vetka_mcp_server.py"]
    }
  }
}
```

### Verify Connection

In Claude Desktop, you should see the VETKA tools icon. Try:
```
Use vetka_health to check the server status
```

---

## VS Code / Cursor (HTTP)

### Step 1: Start HTTP Server

```bash
cd /path/to/vetka_live_03
source .venv/bin/activate
python src/mcp/vetka_mcp_server.py --http --port 5002
```

### Step 2: Configure VS Code

Add to `.vscode/settings.json`:

```json
{
  "mcp.servers": {
    "vetka": {
      "url": "http://localhost:5002/mcp",
      "transport": "http"
    }
  }
}
```

### Step 3: Verify

```bash
# Test endpoint
curl http://localhost:5002/health

# List tools
curl -X POST http://localhost:5002/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

---

## JetBrains IDEs (SSE)

### Step 1: Start SSE Server

```bash
cd /path/to/vetka_live_03
source .venv/bin/activate
python src/mcp/vetka_mcp_server.py --sse --port 5003
```

### Step 2: Configure JetBrains

In IDE Settings → AI Assistant → MCP Servers:

```
Server URL: http://localhost:5003/sse
Transport: SSE
```

### Step 3: Verify

```bash
# Health check
curl http://localhost:5003/health

# Test SSE stream
curl http://localhost:5003/sse
# Should see: event: connected, event: capabilities
```

---

## Google Gemini CLI (HTTP)

### Step 1: Start HTTP Server

```bash
python src/mcp/vetka_mcp_server.py --http --port 5002
```

### Step 2: Configure Gemini

```bash
# Add to Gemini config
gemini config set mcp.vetka.url http://localhost:5002/mcp
gemini config set mcp.vetka.transport http
```

### Step 3: Use

```bash
gemini chat --mcp vetka
> Use vetka_health to check status
```

---

## Running as a Service (Production)

### Using systemd (Linux)

Create `/etc/systemd/system/vetka-mcp.service`:

```ini
[Unit]
Description=VETKA MCP HTTP Server
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/vetka_live_03
ExecStart=/path/to/.venv/bin/python src/mcp/vetka_mcp_server.py --http --port 5002
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable vetka-mcp
sudo systemctl start vetka-mcp
```

### Using launchd (macOS)

Create `~/Library/LaunchAgents/com.vetka.mcp.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.vetka.mcp</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/.venv/bin/python</string>
        <string>/path/to/vetka_live_03/src/mcp/vetka_mcp_server.py</string>
        <string>--http</string>
        <string>--port</string>
        <string>5002</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.vetka.mcp.plist
```

---

## Troubleshooting

### Connection Refused

1. Check VETKA server is running: `curl http://localhost:5001/api/health`
2. Check MCP server is running: `curl http://localhost:5002/health`

### Import Errors

```bash
# Ensure dependencies
pip install mcp httpx starlette uvicorn sse-starlette
```

### Port Already in Use

```bash
# Find what's using the port
lsof -i :5002

# Use different port
python src/mcp/vetka_mcp_server.py --http --port 5004
```

### Write Tools Return "DRY RUN"

This is expected! Write tools default to `dry_run=true` for safety.
Set `dry_run=false` to actually execute the operation:

```
vetka_edit_file(path="test.txt", content="hello", dry_run=false)
```

---

## API Reference

### JSON-RPC Methods

| Method | Description |
|--------|-------------|
| `initialize` | Initialize MCP session |
| `tools/list` | List available tools |
| `tools/call` | Execute a tool |

### Example Request

```bash
curl -X POST http://localhost:5002/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "vetka_search_semantic",
      "arguments": {
        "query": "authentication",
        "limit": 5
      }
    }
  }'
```

---

## Security Notes

1. **Write tools use dry_run by default** - No accidental changes
2. **Git commits require explicit confirmation** - Safe by design
3. **File edits create backups** - In `.vetka_backups/`
4. **Tests run with timeout** - Max 300 seconds

---

**Phase 65.2 Complete** | 13 Tools | 3 Transports | Production Ready
