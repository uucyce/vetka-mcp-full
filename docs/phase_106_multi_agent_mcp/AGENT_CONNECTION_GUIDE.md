# VETKA MCP Agent Connection Guide

## Quick Start

### Prerequisites
```bash
# Ensure VETKA API is running
curl http://localhost:5001/api/health

# Start MCP HTTP server
python src/mcp/vetka_mcp_server.py --http --port 5002
```

---

## Cursor IDE Connection

### Option 1: Kilo-Code Extension (Recommended)

1. Install Kilo-Code extension in Cursor
2. Create/edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "vetka": {
      "command": "python",
      "args": [
        "/Users/YOUR_USER/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py"
      ],
      "env": {
        "VETKA_BASE_URL": "http://localhost:5001"
      }
    }
  }
}
```

### Option 2: HTTP Transport

```json
{
  "mcpServers": {
    "vetka-http": {
      "url": "http://localhost:5002/mcp",
      "transport": "http"
    }
  }
}
```

### Option 3: Roo-Cline Extension

1. Install Roo-Cline in Cursor
2. Settings → MCP Servers → Add:
   - Name: `vetka`
   - Command: `python`
   - Args: `src/mcp/vetka_mcp_bridge.py`
   - Working Dir: `/path/to/vetka_live_03`

---

## Opencode Connection

### Method 1: Direct stdio

```bash
# Run opencode with VETKA MCP
opencode --mcp-server "python src/mcp/vetka_mcp_bridge.py"
```

### Method 2: HTTP Proxy (Recommended)

1. Start OpenCode proxy:
```bash
python src/mcp/opencode_proxy.py
```

2. Configure opencode:
```json
{
  "mcp": {
    "servers": {
      "vetka": {
        "url": "http://localhost:5003",
        "type": "http"
      }
    }
  }
}
```

### Method 3: Environment Config

```bash
export OPENCODE_MCP_SERVERS='{"vetka":{"command":"python","args":["src/mcp/vetka_mcp_bridge.py"]}}'
opencode
```

---

## Claude CLI Connection

Already configured in `~/.claude.json`:

```json
{
  "mcpServers": {
    "vetka": {
      "command": "python",
      "args": ["/path/to/vetka_live_03/src/mcp/vetka_mcp_bridge.py"]
    }
  }
}
```

---

## Available Tools

| Tool | Description |
|------|-------------|
| `vetka_health` | Check system health |
| `vetka_get_tree` | Get 3D tree structure |
| `vetka_search_semantic` | Vector search in knowledge base |
| `vetka_read_file` | Read file content |
| `vetka_list_files` | List files by pattern |
| `vetka_edit_file` | Edit files (dry_run default) |
| `vetka_git_commit` | Create git commits |
| `vetka_run_tests` | Run pytest |
| `vetka_session_init` | Initialize session with context |
| `vetka_call_model` | Call any LLM model |
| `vetka_spawn_pipeline` | Launch agent pipeline |
| `vetka_execute_workflow` | Execute full workflow |

---

## Troubleshooting

### Connection Issues

```bash
# Check MCP server health
curl http://localhost:5002/health

# Run doctor
python src/mcp/tools/doctor_tool.py --level standard
```

### Permission Denied

For background agents, some tools require explicit permission.
Use HTTP transport with session headers for multi-agent scenarios.

### Session Isolation

Each client gets isolated session via `X-Session-ID` header:
```bash
curl -X POST http://localhost:5002/mcp \
  -H "X-Session-ID: my-cursor-session" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

---

## Generate Cursor Config

```bash
python src/mcp/tools/cursor_config_generator.py --client kilo-code
python src/mcp/tools/cursor_config_generator.py --client roo-cline
```

---

*Phase 106g - Multi-Agent MCP Architecture*
