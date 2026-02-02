# Cursor IDE MCP Integration Research
**Date:** 2026-02-02
**Status:** Complete Research
**Focus:** Native MCP support, configuration, and Python stdio compatibility

---

## Executive Summary

Cursor IDE has **native MCP protocol support** through the `anysphere.cursor-mcp` extension, but it operates differently from Claude Desktop. Cursor can configure MCP servers to extend AI agent capabilities with custom tools and resources.

**Key Finding:** Cursor supports MCP servers but does NOT automatically read from Claude Desktop config. Cursor requires its own MCP server configuration in extension-specific settings files.

---

## 1. Does Cursor Support MCP Protocol Natively?

### Answer: YES ✅

**Evidence:**
- Cursor has built-in extension `anysphere.cursor-mcp` that provides MCP protocol support
- Located in logs: `/Library/Application Support/Cursor/logs/*/window*/exthost/anysphere.cursor-mcp`
- Cursor processes MCP connections through agent implementations (Roo-Cline, Kilo-Code)

### MCP Support Details

| Feature | Status | Details |
|---------|--------|---------|
| **MCP Server Support** | ✅ Native | Can connect to stdio and HTTP MCP servers |
| **Multiple Agents** | ✅ Yes | Roo-Cline and Kilo-Code both have MCP configs |
| **WebSocket Transport** | ⚠️ Limited | No native WebSocket MCP support (different from Claude Desktop) |
| **stdio Transport** | ✅ Yes | Primary transport method |
| **HTTP Transport** | ✅ Yes | Can use HTTP-based MCP servers |

---

## 2. How to Configure Custom MCP Servers in Cursor

### Configuration Location

Cursor stores MCP server configurations in **agent-specific settings**:

```
/Library/Application Support/Cursor/User/globalStorage/[AGENT_ID]/settings/mcp_settings.json
```

**Known Agent IDs:**
- `kilocode.kilo-code` - Kilo-Code agent
- `rooveterinaryinc.roo-cline` - Roo-Cline agent

### Configuration File Format

**Current Format (Empty):**
```json
{
  "mcpServers": {
  }
}
```

**Standard MCP Server Configuration:**
```json
{
  "mcpServers": {
    "server-name": {
      "command": "/path/to/python3",
      "args": ["/path/to/mcp_server.py"]
    }
  }
}
```

---

## 3. Configuration File Location and Format

### 3.1 Primary Configuration Paths

| Location | Purpose | Agent |
|----------|---------|-------|
| `~/.config/claude-desktop/config.json` | Claude Desktop MCP config | Claude Desktop |
| `~/Library/Application Support/Cursor/User/globalStorage/kilocode.kilo-code/settings/mcp_settings.json` | Kilo-Code MCP | Cursor (Kilo-Code) |
| `~/Library/Application Support/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json` | Roo-Cline MCP | Cursor (Roo-Cline) |

### 3.2 Configuration Format Details

**Cursor MCP Settings Structure:**
```json
{
  "mcpServers": {
    "unique-server-id": {
      "command": "/absolute/path/to/executable",
      "args": ["arg1", "arg2", "arg3"],
      "env": {
        "CUSTOM_VAR": "value"
      }
    }
  }
}
```

**Key Requirements:**
- `command`: Absolute path to Python executable or shell command
- `args`: Array of command arguments (typically path to MCP server script)
- `env` (optional): Environment variables for the process
- Server ID: Unique identifier for the MCP server

### 3.3 Current System Configuration (Your Setup)

**Claude Desktop Config:**
```json
{
  "mcpServers": {
    "openmemory-multi-project": {
      "command": "/opt/homebrew/bin/python3",
      "args": ["/Users/danilagulin/Documents/VETKA_Project/mcp_wrapper/mcp_wrapper_multi_project.py"]
    }
  }
}
```

**Cursor Config (Both Agents):**
```json
{
  "mcpServers": {}
}
```

**Current Status:** Cursor MCP servers are **not configured** in your system.

---

## 4. Known Issues and Limitations with Python stdio MCP Servers

### 4.1 Python stdio MCP Compatibility

| Issue | Severity | Impact | Workaround |
|-------|----------|--------|-----------|
| **Argument Parsing** | 🔴 High | MCP SDK expects `--help` but `parse_args()` may fail | Use `parse_known_args()` |
| **Stderr Buffering** | 🟡 Medium | Logging to stderr pollutes MCP protocol | Redirect logging to files |
| **stdio Stream Blocking** | 🔴 High | One client per stdio connection (no multiplexing) | Use HTTP transport instead |
| **Signal Handling** | 🟡 Medium | SIGTERM/SIGINT may not propagate | Implement signal handlers |
| **Process Isolation** | 🟡 Medium | No timeout enforcement in stdio transport | Implement per-call timeouts |

### 4.2 VETKA-Specific Findings

**Your Current MCP Server:**
- Location: `/Users/danilagulin/.config/mcp/servers/vetka_claude_code/vetka_claude_bridge_simple.py`
- Transport: **stdio only**
- Status: Tested and working with Claude Code

**Identified Issues:**

1. **Single stdio bottleneck**
   ```python
   # Line 155-159 (BOTTLENECK)
   async with stdio_server() as (read_stream, write_stream):
       await server.run(read_stream, write_stream, ...)
       # ^ Blocks all other clients
   ```
   - Only one Cursor agent can use this server at a time
   - Sequential tool execution (no parallelism)
   - 90-second timeout blocks the entire bridge

2. **Global httpx client**
   ```python
   # Line 76-89 (POTENTIAL RACE CONDITIONS)
   result = subprocess.run(
       ['claude', command],
       cwd=project_path,
       env=env,
       capture_output=True
   )
   ```
   - No connection pooling limits configured
   - Could exhaust system resources with high concurrency

3. **No error recovery**
   - Failed subprocess calls kill the MCP server
   - No retry logic or graceful degradation

### 4.3 Cursor-Specific Limitations

**Cursor does NOT support:**
- ❌ WebSocket MCP servers (use HTTP instead)
- ❌ Direct reading of Claude Desktop config
- ❌ Automatic MCP server discovery
- ❌ GUI for MCP configuration (manual JSON editing required)

**Cursor DOES support:**
- ✅ stdio-based MCP servers
- ✅ HTTP-based MCP servers
- ✅ Environment variable injection
- ✅ Multiple agents with separate MCP configs

---

## 5. Practical Configuration Example for VETKA MCP Server

### 5.1 Configuration for Cursor Kilo-Code Agent

**File:** `~/Library/Application Support/Cursor/User/globalStorage/kilocode.kilo-code/settings/mcp_settings.json`

```json
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
```

### 5.2 Configuration for Cursor Roo-Cline Agent

**File:** `~/Library/Application Support/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json`

```json
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
```

### 5.3 Setup Instructions

**Step 1: Verify venv is working**
```bash
/opt/homebrew/bin/python3 /Users/danilagulin/.config/mcp/servers/vetka_claude_code/venv/bin/python --version
```

**Step 2: Test MCP server startup**
```bash
cd /Users/danilagulin/.config/mcp/servers/vetka_claude_code
./venv/bin/python vetka_claude_bridge_simple.py
```

**Step 3: Edit Cursor settings files**
- Kilo-Code: `~/Library/Application Support/Cursor/User/globalStorage/kilocode.kilo-code/settings/mcp_settings.json`
- Roo-Cline: `~/Library/Application Support/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json`

**Step 4: Restart Cursor to activate**

### 5.4 Using the MCP Server in Cursor

Once configured, the VETKA MCP server provides these tools to Cursor agents:

1. **call_claude_code**
   ```
   Command: Claude Code CLI command
   Example: "edit src/main.ts"
   Returns: Execution result and stdout/stderr
   ```

2. **get_vetka_status**
   ```
   No parameters required
   Returns: JSON status of VETKA system
   Example output:
   {
     "system": "VETKA Spatial Intelligence",
     "mcp_integration": "working",
     "dual_ai_coding": "operational"
   }
   ```

3. **debug_websocket**
   ```
   Parameter: server_file (optional, default: vetka_websocket_server.py)
   Returns: Diagnostics about WebSocket server
   ```

---

## 6. Recommended Implementation Strategy for Phase 106

### 6.1 Current Status
- ✅ Cursor has native MCP support
- ✅ VETKA MCP server (stdio) exists and works
- ❌ Cursor not configured to use VETKA MCP
- ⚠️ stdio bottleneck limits concurrent agents

### 6.2 Recommended Steps

**Phase 1: Enable Current Configuration**
1. Add MCP server config to both Cursor agents
2. Test with Kilo-Code first (simpler)
3. Test with Roo-Cline
4. Verify tools appear in agent context menu

**Phase 2: Upgrade to HTTP Transport (Optional)**
- Current: `vetka_mcp_server.py` has HTTP support at port 5002
- Benefit: No stdio bottleneck, true concurrent agents
- Configuration:
  ```json
  {
    "mcpServers": {
      "vetka-http": {
        "command": "/opt/homebrew/bin/python3",
        "args": [
          "-m", "http.server",
          "--bind", "127.0.0.1",
          "--port", "5002"
        ]
      }
    }
  }
  ```

**Phase 3: WebSocket Support (Advanced)**
- MCP SDK does NOT have native WebSocket transport
- Must implement custom WebSocket-to-stdio bridge
- Reference: Claude Desktop uses custom WebSocket implementation

### 6.3 Testing Checklist

- [ ] MCP config files created for both agents
- [ ] Cursor restarted
- [ ] Agent has access to VETKA tools
- [ ] Tool execution returns proper results
- [ ] No stdio conflicts with other MCP servers
- [ ] Logging properly isolated from protocol stream
- [ ] Performance acceptable for concurrent usage

---

## 7. Key Differences: Cursor vs Claude Desktop

| Aspect | Cursor | Claude Desktop |
|--------|--------|----------------|
| **Config File** | Per-agent settings | Global config.json |
| **Transport** | stdio, HTTP | stdio, HTTP, WebSocket |
| **GUI Setup** | Manual JSON editing | Settings UI |
| **Agent Support** | Per-agent MCP | Single global MCP pool |
| **Python Compatibility** | stdio works well | Requires parse_known_args |
| **Logging** | Must redirect to file | Handled by system |
| **Startup** | On-demand when agent runs | At desktop launch |

---

## 8. References and Sources

### Cursor Configuration
- Cursor application data: `~/Library/Application Support/Cursor/`
- Extension logs: `~/Library/Application Support/Cursor/logs/*/exthost/anysphere.cursor-mcp`
- Settings structure: Agent-specific storage in `globalStorage/[agent-id]/settings/`

### VETKA MCP Implementation
- Bridge location: `/Users/danilagulin/.config/mcp/servers/vetka_claude_code/`
- Current servers: `vetka_claude_bridge_simple.py` (stdio)
- HTTP transport: `vetka_mcp_server.py` (existing but not configured)
- Phase 106 research: `docs/phase_106_multi_agent_mcp/PHASE_106_RESEARCH_SYNTHESIS.md`

### MCP Protocol Documentation
- MCP Server SDK: Uses `mcp.server.stdio` for transport
- Python compatibility: `parse_known_args()` required for argument handling
- Connection patterns: `async with stdio_server()` context manager

---

## 9. Conclusion

**Cursor IDE DOES support MCP natively** and can be configured to use the VETKA MCP server. However, configuration is:
- Manual JSON editing (not automatic)
- Per-agent rather than global
- Limited to stdio and HTTP transports (no WebSocket)
- Currently unconfigured in your system

**Immediate Next Steps:**
1. Copy provided JSON configs to Cursor's MCP settings files
2. Restart Cursor
3. Test agent access to VETKA tools
4. Monitor for stdio bottleneck issues if multiple agents run concurrently

**Long-term Optimization:**
- Migrate to HTTP transport to eliminate stdio bottleneck
- Implement proper logging isolation
- Consider connection pooling for httpx client
- Add retry logic and error recovery

---

**Document Version:** 1.0
**Last Updated:** 2026-02-02
**Next Review:** After Cursor MCP implementation
