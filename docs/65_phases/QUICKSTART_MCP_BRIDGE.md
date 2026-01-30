# VETKA MCP Bridge — Quick Start

**Phase 65.1** | 5-minute setup

---

## 🚀 For Claude Code Users

```bash
# 1. Navigate to VETKA
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

# 2. Activate venv
source .venv/bin/activate

# 3. Add VETKA MCP server (one-time setup)
claude mcp add vetka -- python src/mcp/vetka_mcp_bridge.py

# 4. Start using!
claude
> Use vetka_health to check VETKA status
> Search VETKA for "FastAPI routes"
```

---

## 🖥️ For Claude Desktop Users

### 1. Edit Config

```bash
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Add:
```json
{
  "mcpServers": {
    "vetka": {
      "command": "python",
      "args": [
        "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py"
      ]
    }
  }
}
```

### 2. Restart Claude Desktop

```bash
killall Claude
open -a Claude
```

### 3. Test

In any project:
```
Use vetka_health tool
```

---

## 🛠️ Available Tools

| Tool | Description |
|------|-------------|
| `vetka_search_semantic` | Semantic search in VETKA knowledge base |
| `vetka_read_file` | Read file content |
| `vetka_get_tree` | Get 3D tree structure |
| `vetka_health` | Check server health |
| `vetka_list_files` | List files in directory |
| `vetka_search_files` | Search for files |
| `vetka_get_metrics` | Get metrics/analytics |
| `vetka_get_knowledge_graph` | Get knowledge graph |

---

## 🧪 Test

```bash
python tests/test_mcp_bridge.py
```

Expected: `✅ ALL TESTS PASSED!`

---

## 📖 Full Documentation

See: [`Phase_65.1_MCP_Bridge_Setup.md`](./Phase_65.1_MCP_Bridge_Setup.md)

---

## ⚠️ Prerequisites

1. **VETKA running:** `python main.py` (port 5001)
2. **MCP SDK installed:** `pip install mcp httpx` (in .venv)

---

**Status:** ✅ Production Ready
**Last Updated:** 2026-01-18
