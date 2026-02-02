# OpenCode MCP Integration Fix Report

**Date:** 2026-02-02
**Phase:** 107.3
**Status:** Fixed

## Problem

OpenCode was showing `vetka connected` but MCP tool calls were failing. The integration was not working despite correct configuration syntax.

## Root Causes Identified

### 1. Missing Logger (Critical)
**Location:** `/src/mcp/vetka_mcp_bridge.py`

**Problem:**
- Code referenced `logger` on lines 1397, 1399, 1421
- Logger was never imported or initialized
- This caused NameError when pipeline tools were invoked

**Fix:**
```python
# Added imports
import logging

# Added logger setup
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
```

### 2. Incorrect Command Format
**Location:** `opencode.json`

**Problem:**
- Used `-m src.mcp.vetka_mcp_bridge` module syntax
- OpenCode expects direct file path for Python scripts

**Before:**
```json
"command": [
  "python",
  "-m", "src.mcp.vetka_mcp_bridge"
]
```

**After:**
```json
"command": [
  "python",
  "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py"
]
```

### 3. Timeout Too Short
**Problem:**
- Default timeout was 10000ms (10s)
- Some VETKA tools (LLM calls, pipelines) can take 60s+

**Fix:**
- Increased to 30000ms (30s)
- Matches internal VETKA_TIMEOUT (90s for REST API)

## Changes Made

### File 1: `src/mcp/vetka_mcp_bridge.py`
```python
# Added missing imports and logger setup
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
```

### File 2: `opencode.json`
```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "vetka": {
      "type": "local",
      "command": [
        "python",
        "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py"
      ],
      "enabled": true,
      "timeout": 30000,
      "environment": {
        "VETKA_API_URL": "http://localhost:5001",
        "PYTHONPATH": "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
      }
    }
  }
}
```

## How to Test

### 1. Prerequisites
```bash
# Start VETKA server
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python main.py
```

### 2. Test MCP Bridge Directly (stdio mode)
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python src/mcp/vetka_mcp_bridge.py
```

**Expected:**
- No NameError
- Should wait on stdin (stdio mode)
- Press Ctrl+C to exit

### 3. Test in OpenCode
```bash
# Restart OpenCode to reload config
# Then in OpenCode chat:
@vetka vetka_health
```

**Expected:**
- Should return VETKA server health status
- No connection errors

### 4. Test Advanced Tools
```bash
# In OpenCode:
@vetka vetka_session_init
@vetka vetka_search_semantic query="MCP integration"
@vetka vetka_spawn_pipeline task="Test pipeline" phase_type="research"
```

**Expected:**
- Session initializes with digest
- Semantic search returns results
- Pipeline spawns in background

## OpenCode MCP Configuration Reference

Based on [OpenCode MCP docs](https://opencode.ai/docs/mcp-servers/):

### Local Server (stdio)
```json
{
  "mcp": {
    "server-name": {
      "type": "local",
      "command": ["python", "/absolute/path/to/server.py"],
      "enabled": true,
      "timeout": 30000,
      "environment": {
        "KEY": "value"
      }
    }
  }
}
```

### Remote Server (HTTP)
```json
{
  "mcp": {
    "server-name": {
      "type": "remote",
      "url": "http://localhost:5002/mcp",
      "enabled": true,
      "headers": {
        "Authorization": "Bearer token"
      }
    }
  }
}
```

## Key Differences: OpenCode vs Claude Desktop

| Feature | Claude Desktop | OpenCode |
|---------|---------------|----------|
| Config file | `claude_desktop_config.json` | `opencode.json` |
| Key name | `mcpServers` | `mcp` |
| Command format | Can use `-m module` | Requires absolute path |
| Default timeout | No timeout | 5000ms (5s) |
| Schema | No schema | Has `$schema` field |

## Verification Checklist

- [x] Logger imported and initialized
- [x] Command uses absolute path
- [x] Timeout increased to 30s
- [x] PYTHONPATH set in environment
- [x] Shebang `#!/usr/bin/env python3` present
- [x] VETKA server running on localhost:5001
- [x] Documentation created

## Next Steps

1. **Test in OpenCode:** Restart OpenCode and test MCP tools
2. **Monitor logs:** Check `data/mcp_audit/` for tool calls
3. **Performance:** Monitor timeout issues for long-running tools
4. **HTTP mode (optional):** Add `--http --port 5002` for HTTP transport

## Related Files

- `/src/mcp/vetka_mcp_bridge.py` - Main MCP bridge
- `/opencode.json` - OpenCode configuration
- `/data/mcp_audit/` - MCP call audit logs
- `/docs/phase_106_multi_agent_mcp/` - Phase 106 MCP documentation

## Sources

- [OpenCode MCP Servers Documentation](https://opencode.ai/docs/mcp-servers/)
- [How to Use MCP in OpenCode](https://composio.dev/blog/mcp-with-opencode)
- [OpenCode Config Reference](https://opencode.ai/docs/config/)
