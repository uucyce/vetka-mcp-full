# VETKA MCP Bridge Setup Guide

**Phase 65.1** | **Status:** Production Ready
**Date:** 2026-01-18

## 📋 Overview

The VETKA MCP Bridge allows Claude Desktop and Claude Code to interact with VETKA tools through the standard Model Context Protocol (MCP).

### Architecture

```
┌─────────────────┐
│ Claude Desktop  │
│ Claude Code     │
└────────┬────────┘
         │ MCP stdio
         │ (JSON-RPC)
         ↓
┌─────────────────┐
│ vetka_mcp_bridge│
└────────┬────────┘
         │ HTTP/REST
         ↓
┌─────────────────┐
│ VETKA FastAPI   │
│ localhost:5001  │
└─────────────────┘
```

### Features

- **8 VETKA tools** exposed via MCP
- **Standard stdio transport** (JSON-RPC over stdin/stdout)
- **REST API client** to VETKA FastAPI server
- **Auto-reconnect** on connection errors
- **Pretty formatting** for search results, health checks, etc.

---

## 🛠️ Installation

### Prerequisites

1. **VETKA server running:**
   ```bash
   cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
   python main.py
   ```

2. **MCP SDK installed:**
   ```bash
   source .venv/bin/activate
   pip install mcp httpx
   ```

---

## 🔌 Claude Code Setup

### Register MCP Server

```bash
# Navigate to VETKA project
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

# Activate venv
source .venv/bin/activate

# Add VETKA MCP server
claude mcp add vetka -- python src/mcp/vetka_mcp_bridge.py

# Verify registration
claude mcp list
```

Expected output:
```
vetka  python src/mcp/vetka_mcp_bridge.py
```

### Test in Claude Code

Start a new Claude Code session:

```bash
claude
```

In the chat, try:
```
Use vetka_health tool to check VETKA server status
```

---

## 🖥️ Claude Desktop Setup

### Edit Config File

Location: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "vetka": {
      "command": "python",
      "args": [
        "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py"
      ],
      "env": {
        "PYTHONPATH": "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
      }
    }
  }
}
```

### Restart Claude Desktop

```bash
# Quit Claude Desktop completely
killall Claude

# Reopen Claude Desktop
open -a Claude
```

### Test in Claude Desktop

Create a new project or chat, then try:
```
Use vetka_health to check server status
```

---

## 🧪 Available Tools

### 1. `vetka_search_semantic`

Semantic search using Qdrant vector database.

**Parameters:**
- `query` (required): Search query
- `limit` (optional): Max results (default: 10, max: 50)

**Example:**
```
Search VETKA knowledge base for "FastAPI routes implementation"
```

---

### 2. `vetka_read_file`

Read file content with line numbers.

**Parameters:**
- `file_path` (required): Relative path from project root

**Example:**
```
Read src/mcp/vetka_mcp_bridge.py
```

---

### 3. `vetka_get_tree`

Get VETKA 3D tree structure.

**Parameters:**
- `format` (optional): "summary" (default) or "tree"

**Example:**
```
Show VETKA tree summary
```

---

### 4. `vetka_health`

Check VETKA server health and component status.

**Example:**
```
Check VETKA health status
```

**Sample Output:**
```
VETKA Health Status
===================
Status: healthy
Version: 2.0.0
Phase: 39.8

Components:
  ✅ metrics_engine
  ✅ model_router
  ✅ api_gateway
  ✅ qdrant
  ✅ feedback_loop
  ...
```

---

### 5. `vetka_list_files`

List files in directory or matching pattern.

**Parameters:**
- `path` (optional): Directory path (default: ".")
- `pattern` (optional): Glob pattern (e.g., "*.py")
- `recursive` (optional): Recursive listing (default: false)

**Example:**
```
List all Python files in src/mcp/
```

---

### 6. `vetka_search_files`

Fast file search by name or content.

**Parameters:**
- `query` (required): Search query
- `search_type` (optional): "filename", "content", or "both" (default)
- `limit` (optional): Max results (default: 20)

**Example:**
```
Search for files containing "Socket.IO"
```

---

### 7. `vetka_get_metrics`

Get VETKA metrics and analytics.

**Parameters:**
- `metric_type` (optional): "dashboard", "agents", or "all" (default: "dashboard")

**Example:**
```
Show VETKA dashboard metrics
```

---

### 8. `vetka_get_knowledge_graph`

Get knowledge graph structure.

**Parameters:**
- `format` (optional): "summary" (default) or "json"

**Example:**
```
Show VETKA knowledge graph summary
```

---

## 🧪 Testing

### Run Automated Tests

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
source .venv/bin/activate
python tests/test_mcp_bridge.py
```

Expected output:
```
============================================================
  VETKA MCP BRIDGE TESTS - Phase 65.1
============================================================

[TEST] Bridge initialization...
✅ Bridge initializes successfully

[TEST] Listing tools...
Found 8 tools:
  - vetka_search_semantic
  - vetka_read_file
  - vetka_get_tree
  - vetka_health
  - vetka_list_files
  - vetka_search_files
  - vetka_get_metrics
  - vetka_get_knowledge_graph
✅ All expected tools present

...

✅ ALL TESTS PASSED!
```

### Manual Testing

```bash
# Start bridge manually
python src/mcp/vetka_mcp_bridge.py

# Send JSON-RPC request (in another terminal)
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | python src/mcp/vetka_mcp_bridge.py
```

---

## 🔧 Troubleshooting

### Error: "Cannot connect to VETKA server"

**Solution:** Ensure VETKA is running:
```bash
curl http://localhost:5001/api/health
```

If not running:
```bash
python main.py
```

---

### Error: "Module 'mcp' not found"

**Solution:** Install MCP SDK:
```bash
source .venv/bin/activate
pip install mcp httpx
```

---

### Error: "Memory manager not available" (semantic search)

**Cause:** Qdrant vector database not initialized or not running.

**Solution:**
1. Check Qdrant status in health check:
   ```
   Use vetka_health
   ```

2. Initialize Qdrant collections if needed:
   ```bash
   # TODO: Add Qdrant init script
   ```

---

### Bridge not showing in Claude Code

**Solution:** Re-register MCP server:
```bash
# Remove old registration
claude mcp remove vetka

# Add again with full path
claude mcp add vetka -- python /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py

# Verify
claude mcp list
```

---

### Bridge not showing in Claude Desktop

**Solution:**
1. Check config file syntax:
   ```bash
   cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | python -m json.tool
   ```

2. Ensure Python path is correct:
   ```bash
   which python
   # Should output: /usr/local/bin/python3 or similar
   ```

3. Restart Claude Desktop completely:
   ```bash
   killall Claude
   open -a Claude
   ```

---

## 📊 REST API Mapping

| MCP Tool | REST Endpoint | Method |
|----------|---------------|--------|
| `vetka_search_semantic` | `/api/search/semantic?q=...` | GET |
| `vetka_read_file` | `/api/files/read` | POST |
| `vetka_get_tree` | `/api/tree/data` | GET |
| `vetka_health` | `/api/health` | GET |
| `vetka_list_files` | `/api/tree/data` (filtered) | GET |
| `vetka_search_files` | `/api/search/semantic` | GET |
| `vetka_get_metrics` | `/api/metrics/dashboard` or `/api/metrics/agents` | GET |
| `vetka_get_knowledge_graph` | `/api/tree/knowledge-graph` | GET |

---

## 🔄 Future Enhancements

### Planned for Phase 65.2

- [ ] Add write operations (edit_file, git_commit) with approval flow
- [ ] Add camera control via Socket.IO bridge
- [ ] Add file watching/hot reload
- [ ] Add batch operations support
- [ ] Improve error messages with actionable suggestions
- [ ] Add rate limiting awareness (show remaining quota)
- [ ] Add caching for frequently accessed data

---

## 📝 Notes

- **Transport:** MCP Bridge uses **stdio** (stdin/stdout JSON-RPC), not HTTP
- **Security:** Bridge runs locally, no authentication needed
- **Performance:** REST calls to localhost:5001 are fast (<10ms typically)
- **Compatibility:** Works with MCP SDK v1.19.0+

---

## 🆘 Support

For issues or questions:

1. Check this guide
2. Run tests: `python tests/test_mcp_bridge.py`
3. Check VETKA server logs: `tail -f logs/vetka.log`
4. Check Claude Code logs: `~/.claude/logs/`

---

**Last Updated:** 2026-01-18
**Author:** Phase 65.1 Team
**Status:** ✅ Production Ready
