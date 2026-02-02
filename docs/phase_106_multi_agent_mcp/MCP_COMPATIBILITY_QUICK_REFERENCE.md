# VETKA MCP Client Compatibility - Quick Reference

**Document:** `MCP_CLIENT_COMPATIBILITY_REPORT.md`
**Full Report Size:** 1,569 lines | 36 KB
**Last Updated:** 2026-02-02

---

## One-Minute Setup Guide

### For Claude Desktop (Easiest)

1. Copy this into `~/.config/claude-desktop/config.json`:
```json
{
  "mcpServers": {
    "vetka": {
      "command": "python",
      "args": ["/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py"],
      "env": {
        "VETKA_API_URL": "http://localhost:5001",
        "PYTHONPATH": "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
      }
    }
  }
}
```

2. Restart Claude Desktop
3. Done!

---

### For VS Code (Most Flexible)

1. Start MCP server in HTTP mode:
```bash
python /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py --http --port 5002
```

2. Install "Model Context Protocol" extension in VS Code

3. Add to `.vscode/settings.json`:
```json
{
  "mcpServers": [
    {
      "name": "vetka",
      "type": "http",
      "url": "http://localhost:5002/mcp"
    }
  ]
}
```

4. Restart VS Code
5. Done!

---

### For Cursor (Native MCP Support)

1. Start MCP server (same as VS Code):
```bash
python /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py --http --port 5002
```

2. Add to `~/.config/Cursor/User/settings.json`:
```json
{
  "mcpServers": [
    {
      "name": "vetka",
      "type": "http",
      "url": "http://localhost:5002/mcp"
    }
  ]
}
```

3. Restart Cursor
4. Done!

---

## Client Support Matrix

| Client | Support | Config Location | Transport | Setup Time |
|--------|---------|-----------------|-----------|------------|
| Claude Desktop | Full | `~/.config/claude-desktop/config.json` | stdio | 2 min |
| Claude Code CLI | Full | `~/.claude/mcp.json` | stdio | 3 min |
| VS Code | Full | `.vscode/settings.json` | HTTP | 5 min |
| Cursor | Full | `~/.config/Cursor/User/settings.json` | HTTP | 5 min |
| Continue.dev | Full | `~/.continue/config.json` | HTTP | 5 min |
| Cline | Full | VS Code settings | HTTP | 5 min |
| JetBrains IDEs | Full | IDE settings | SSE | 10 min |
| Gemini | API Only | Custom proxy | HTTP | 15 min |
| Opencode | Not Yet | Planned | TBD | TBD |

---

## Configuration File Locations Quick Map

```
macOS/Linux:
  Claude Desktop:     ~/.config/claude-desktop/config.json
  Claude Code:        ~/.claude/mcp.json
  VS Code:            ~/.config/Code/User/settings.json
  Cursor:             ~/.config/Cursor/User/settings.json
  Continue:           ~/.continue/config.json
  JetBrains:          IDE Settings → Tools → MCP Servers

Windows:
  Claude Desktop:     %APPDATA%\Claude\config.json
  VS Code:            %APPDATA%\Code\User\settings.json
  Cursor:             %APPDATA%\Cursor\User\settings.json
```

---

## Transport Types Explained

### stdio (Claude Desktop/Code)
- **Best for:** Getting started, single client
- **Setup:** 2 minutes
- **Limitation:** One client at a time
- **Speed:** <100ms
- **Command:** `python vetka_mcp_bridge.py`

### HTTP (VS Code, Cursor, Continue)
- **Best for:** Multiple clients, flexibility
- **Setup:** 5 minutes
- **Advantage:** Concurrent clients
- **Speed:** 10-50ms
- **Command:** `python vetka_mcp_bridge.py --http --port 5002`

### SSE (JetBrains)
- **Best for:** IDE plugin support
- **Setup:** 10 minutes
- **Advantage:** Real-time events
- **Speed:** 50-100ms
- **Command:** `python vetka_mcp_server.py --sse --port 5003`

### WebSocket (Future/Real-time)
- **Best for:** Live agents, low latency
- **Setup:** Advanced
- **Advantage:** Bidirectional
- **Speed:** 5-20ms
- **Command:** `python vetka_mcp_bridge.py --http --ws --port 5002`

---

## Running All Clients Together

**Recommended Setup:**

Terminal 1 - Start HTTP server:
```bash
python /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py --http --port 5002
```

Then use any/all of:
- Claude Desktop (via stdio, auto-configured)
- VS Code (via HTTP, see full report for config)
- Cursor (via HTTP, see full report for config)
- Continue.dev (via HTTP, see full report for config)

All work simultaneously without interference!

---

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| "MCP server not found" | Restart the client app (not terminal) |
| Tools not appearing | Wait 10 seconds, tools take time to list |
| Connection refused (5002) | Check HTTP server is running: `curl http://localhost:5002/health` |
| Timeout errors | VETKA API might be slow, check: `curl http://localhost:5001/health` |
| High CPU usage | Multiple clients congesting, add rate limiting |

---

## Performance Tips

1. **Use HTTP mode** for multiple concurrent clients (not stdio)
2. **Set unique session IDs** to prevent state collision
3. **Monitor health** with: `curl http://localhost:5001/api/metrics`
4. **Increase timeout** for long LLM calls: `export MCP_TIMEOUT=120`

---

## Port Reference

| Service | Port | Purpose |
|---------|------|---------|
| VETKA API | 5001 | Main FastAPI server (tools, search, git, etc.) |
| VETKA MCP (HTTP) | 5002 | MCP JSON-RPC endpoint (VS Code, Cursor, etc.) |
| VETKA MCP (SSE) | 5003 | SSE endpoint for JetBrains |
| VETKA UI | 5000 | Web interface (optional) |

---

## When to Use Each Client

### Use Claude Desktop When:
- You want the simplest setup (2 min)
- You work with one project at a time
- You prefer Anthropic's official tool

### Use VS Code When:
- You need to support multiple simultaneous clients
- You want a free, open-source editor
- You're comfortable with JSON configuration

### Use Cursor When:
- You want native MCP support (built-in)
- You like an AI-first IDE experience
- You need the latest MCP features

### Use Continue.dev When:
- You want an open-source alternative
- You need to work in multiple IDEs
- You prefer community-driven tools

### Use JetBrains When:
- You use PyCharm, IntelliJ, or WebStorm
- You want deep IDE integration
- You need professional Python/Java tooling

---

## Advanced Setup: Production Deployment

For production with load balancing:

```bash
# Terminal 1: HTTP server (with logging)
python src/mcp/vetka_mcp_bridge.py --http --port 5002 \
  2>&1 | tee /tmp/vetka-mcp.log

# Terminal 2: Monitor metrics
watch -n 5 'curl -s http://localhost:5001/api/metrics | jq'

# Terminal 3+: Your clients (any combination)
# - Claude Desktop
# - VS Code with settings.json
# - Cursor with settings.json
# - etc.
```

All clients work in parallel without blocking!

---

## Environment Variables Reference

```bash
# Required
VETKA_API_URL="http://localhost:5001"          # VETKA server location
PYTHONPATH="/path/to/vetka_live_03"            # Project root

# Optional (with defaults)
MCP_HTTP_MODE="false"                          # Enable HTTP (true/false)
MCP_PORT="5002"                                # HTTP port
MCP_TIMEOUT="90"                               # Tool timeout in seconds
MCP_SESSION_ID="uuid"                          # Session isolation
VETKA_LOG_LEVEL="INFO"                         # Logging level
```

---

## File Locations Summary

| What | Where |
|------|-------|
| **VETKA MCP Code** | `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/` |
| **VETKA API** | `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/` (main.py:5001) |
| **Main Config** | `.mcp.json` (project root) |
| **Full Documentation** | `/docs/phase_106_multi_agent_mcp/MCP_CLIENT_COMPATIBILITY_REPORT.md` |
| **Phase 106 Research** | `/docs/phase_106_multi_agent_mcp/PHASE_106_RESEARCH_SYNTHESIS.md` |

---

## Next Steps

1. **Choose your client** (Claude Desktop is easiest to start)
2. **Copy the configuration** from above
3. **Start VETKA server** if not already running
4. **Restart your client**
5. **Test with a simple query** like "search for authentication logic"
6. **Refer to full report** for advanced configurations

---

## Full Documentation

For detailed configuration, troubleshooting, and advanced setup:

**Read:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/phase_106_multi_agent_mcp/MCP_CLIENT_COMPATIBILITY_REPORT.md`

This Quick Reference covers the essentials. The full report (1,569 lines) includes:
- Detailed setup for each client
- Troubleshooting matrices
- Performance tuning
- Production deployment checklist
- Docker templates
- Migration guides
- Complete template configurations

---

**Last Updated:** 2026-02-02
**Status:** Production Ready (Phase 106f)
