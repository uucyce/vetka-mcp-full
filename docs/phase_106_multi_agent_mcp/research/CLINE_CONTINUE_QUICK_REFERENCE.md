# Cline & Continue MCP Support - Quick Reference
**Phase 106 Integration Summary**

---

## 1. At a Glance

| Aspect | Cline | Continue |
|--------|-------|----------|
| **MCP Ready** | ✅ Production | ⚠️ Experimental |
| **STDIO Support** | Excellent | Good |
| **Config Format** | JSON (simple) | Python (flexible) |
| **Recommendation** | PRIMARY | Secondary |

---

## 2. Quick Setup - Cline

### Create `.cline/cline_mcp_config.json`:
```json
{
  "mcpServers": [{
    "name": "vetka-live-mcp",
    "type": "stdio",
    "command": "python",
    "args": [
      "/path/to/vetka_live_03/src/mcp/vetka_mcp_server.py",
      "--stdio"
    ],
    "env": {
      "VETKA_HOME": "/path/to/vetka_live_03",
      "PYTHONPATH": "/path/to/vetka_live_03/src"
    },
    "autoConnect": true
  }]
}
```

### Or in VS Code `.vscode/settings.json`:
```json
{
  "cline.mcp.servers": {
    "vetka": {
      "command": "python",
      "args": ["${workspaceFolder}/src/mcp/vetka_mcp_server.py", "--stdio"],
      "env": {
        "VETKA_HOME": "${workspaceFolder}",
        "PYTHONPATH": "${workspaceFolder}/src"
      }
    }
  }
}
```

---

## 3. Quick Setup - Continue

### Create `~/.continue/config.py`:
```python
from continuedev.core.config import Config
from continuedev.core.mcp import MCPServer
import os

VETKA = os.path.expanduser("~/Documents/VETKA_Project/vetka_live_03")

config = Config(
    models=[{"provider": "anthropic", "model": "claude-3-5-sonnet-20241022"}],
    mcp_servers={
        "vetka": MCPServer(
            command="python",
            args=[f"{VETKA}/src/mcp/vetka_mcp_server.py", "--stdio"],
            env={"VETKA_HOME": VETKA, "PYTHONPATH": f"{VETKA}/src"},
            type="stdio"
        )
    }
)
```

---

## 4. Key Differences

### Cline
- Mature, production-ready
- Simpler configuration
- Better error recovery
- Larger community

### Continue
- Community-driven, open-source
- More flexible Python config
- Evolving API (breaking changes possible)
- Good for experimentation

---

## 5. Compatibility Checklist

- ✅ VETKA STDIO server already compatible
- ✅ JSON-RPC protocol supported by both
- ✅ Tool registration works
- ✅ Environment variables supported
- ⚠️ Resource streaming (Continue: partial)
- ⚠️ Prompt templates (Continue: not yet)

---

## 6. Testing

```bash
# Test STDIO directly
python src/mcp/vetka_mcp_server.py --stdio

# With environment
VETKA_HOME=/path/to/vetka_live_03 \
PYTHONPATH=/path/to/vetka_live_03/src \
python src/mcp/vetka_mcp_server.py --stdio
```

---

## 7. Common Issues

| Issue | Solution |
|-------|----------|
| "MCP server failed to start" | Check Python path, verify PYTHONPATH, check stderr |
| "Tool invocation timeout" | Increase timeout in config, check for blocking ops |
| "JSON-RPC parse errors" | Verify UTF-8 encoding, check newlines (LF only) |
| "Tools not discovered" | Verify server initialization, check tool registration |

---

## 8. Recommendation for VETKA

1. **Now:** Implement Cline integration (production-ready)
2. **Soon:** Test Continue when API stabilizes
3. **Later:** Support both with unified MCP interface

**Timeline:** Cline integration in Phase 106.1 (1-2 days)

---

See `CLINE_CONTINUE_MCP_RESEARCH.md` for detailed analysis.
