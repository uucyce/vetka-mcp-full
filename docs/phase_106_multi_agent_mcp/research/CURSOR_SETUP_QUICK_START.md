# Cursor MCP Setup - Quick Start Guide
**For VETKA Integration in Phase 106**

---

## TL;DR

Cursor supports MCP natively. To enable VETKA MCP server in Cursor:

1. Add JSON config to both agent settings files
2. Restart Cursor
3. Test with agent

---

## One-Command Setup

```bash
# Create/update Kilo-Code MCP config
cat > ~/Library/Application\ Support/Cursor/User/globalStorage/kilocode.kilo-code/settings/mcp_settings.json << 'EOF'
{
  "mcpServers": {
    "vetka-claude-bridge": {
      "command": "/opt/homebrew/bin/python3",
      "args": ["/Users/danilagulin/.config/mcp/servers/vetka_claude_code/vetka_claude_bridge_simple.py"],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "VETKA_PROJECT_PATH": "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
      }
    }
  }
}
EOF

# Create/update Roo-Cline MCP config
cat > ~/Library/Application\ Support/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json << 'EOF'
{
  "mcpServers": {
    "vetka-claude-bridge": {
      "command": "/opt/homebrew/bin/python3",
      "args": ["/Users/danilagulin/.config/mcp/servers/vetka_claude_code/vetka_claude_bridge_simple.py"],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "VETKA_PROJECT_PATH": "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
      }
    }
  }
}
EOF

echo "✅ Cursor MCP configs updated"
```

---

## Verification Steps

### 1. Check Files Were Created
```bash
cat ~/Library/Application\ Support/Cursor/User/globalStorage/kilocode.kilo-code/settings/mcp_settings.json
cat ~/Library/Application\ Support/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json
```

### 2. Verify Python Path Works
```bash
/opt/homebrew/bin/python3 --version
```

### 3. Test MCP Server Startup
```bash
cd /Users/danilagulin/.config/mcp/servers/vetka_claude_code
./venv/bin/python vetka_claude_bridge_simple.py < /dev/null
# Should run without errors (Ctrl+C to stop)
```

### 4. Restart Cursor and Test
- Close all Cursor windows
- Reopen Cursor
- Open VETKA project
- Try using Kilo-Code agent (Cmd+K)
- Look for "VETKA MCP tools" in agent context

---

## Configuration Details

### File Locations

**Kilo-Code MCP:**
```
~/Library/Application Support/Cursor/User/globalStorage/kilocode.kilo-code/settings/mcp_settings.json
```

**Roo-Cline MCP:**
```
~/Library/Application Support/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json
```

### Configuration Format

```json
{
  "mcpServers": {
    "unique-id": {
      "command": "/path/to/python",
      "args": ["/path/to/server.py"],
      "env": {
        "VAR_NAME": "value"
      }
    }
  }
}
```

**Key Points:**
- `command`: Absolute path to Python executable
- `args`: Array with script path
- `env`: Optional environment variables
- Must use absolute paths (no `~`)

---

## Available Tools After Setup

### get_vetka_status
Returns system status
```json
{
  "system": "VETKA Spatial Intelligence",
  "mcp_integration": "working",
  "claude_code_integration": "testing",
  "dual_ai_coding": "operational"
}
```

### call_claude_code
Execute Claude Code commands
```
Command: "edit src/main.ts"
Returns: Execution result with stdout/stderr
```

### debug_websocket
Diagnose WebSocket server
```
Parameter: server_file (optional)
Returns: Diagnostic information
```

---

## Troubleshooting

### MCP Tools Don't Appear in Agent

**Symptoms:** Agent context menu doesn't show VETKA tools

**Solutions:**
1. Check JSON syntax with: `python -m json.tool ~/Library/Application\ Support/Cursor/User/globalStorage/kilocode.kilo-code/settings/mcp_settings.json`
2. Verify paths are absolute (no `~`)
3. Ensure Python executable exists: `/opt/homebrew/bin/python3 --version`
4. Restart Cursor completely (not just window)
5. Check logs: `~/Library/Application Support/Cursor/logs/*/exthost/anysphere.cursor-mcp`

### MCP Server Crashes

**Symptoms:** Tool calls fail or hang

**Solutions:**
1. Test manually: `cd /Users/danilagulin/.config/mcp/servers/vetka_claude_code && ./venv/bin/python vetka_claude_bridge_simple.py < /dev/null`
2. Add stderr redirect: Add `"env": {"PYTHONUNBUFFERED": "1"}` (already in config)
3. Check VETKA project exists at configured path
4. Review Claude Code bridge logs in project directory

### Python Environment Issues

**Symptoms:** "Python not found" or module errors

**Solutions:**
1. Verify path: `which python3` (should include `/opt/homebrew/`)
2. Check venv: `/Users/danilagulin/.config/mcp/servers/vetka_claude_code/venv/bin/python --version`
3. Update requirements: `cd /Users/danilagulin/.config/mcp/servers/vetka_claude_code && ./venv/bin/pip install -r requirements.txt`

---

## Performance Considerations

### Limitations
- **Single stdio connection per agent**
  - Kilo-Code and Roo-Cline each get separate connection
  - Only one tool call at a time per agent
  - ~2-5 second latency per call

- **Future optimization**
  - HTTP transport available at port 5002
  - Would eliminate stdio bottleneck
  - Requires config change: use `--http` flag in VETKA server

### Expected Performance
- Tool invocation: 1-2 seconds
- Status queries: <100ms
- Claude Code execution: 5-30 seconds (depending on command)

---

## Next Steps

### Phase 106 Implementation
1. ✅ Research (this document)
2. → Apply configurations
3. → Test with both agents
4. → Monitor for issues
5. → Consider HTTP transport upgrade

### Advanced: HTTP Transport (Optional)

If stdio bottleneck becomes issue:
```json
{
  "mcpServers": {
    "vetka-http": {
      "command": "/opt/homebrew/bin/python3",
      "args": [
        "/Users/danilagulin/.config/mcp/servers/vetka_claude_code/vetka_mcp_server.py",
        "--http",
        "--port", "5002"
      ]
    }
  }
}
```

Benefits: True concurrent tool calls, lower latency
Drawback: More complex debugging

---

## Questions?

Check:
1. Full research: `docs/phase_106_multi_agent_mcp/research/CURSOR_MCP_RESEARCH.md`
2. VETKA bridge: `/Users/danilagulin/.config/mcp/servers/vetka_claude_code/`
3. Phase 106 synthesis: `docs/phase_106_multi_agent_mcp/PHASE_106_RESEARCH_SYNTHESIS.md`

---

**Version:** 1.0
**Created:** 2026-02-02
**Status:** Ready for Implementation
