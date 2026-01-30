# VETKA MCP Architecture Scout Report
**Phase 89.5 | 2026-01-22**

---

## EXECUTIVE SUMMARY
VETKA has a **production-grade MCP system** supporting multiple transports and model calling. The architecture uses a REST API bridge (via HTTP) to call LLM models through the Elisya gateway.

---

## 1. MCP SERVER STRUCTURE

### Entry Points
- **Primary:** `src/mcp/vetka_mcp_bridge.py` (Phase 65.1) - Main MCP implementation
- **Universal:** `src/mcp/vetka_mcp_server.py` (Phase 65.2) - Multi-transport wrapper
- **Legacy:** `src/mcp/stdio_server.py` - Pure stdio implementation (less used)

### Protocol Support

| Transport | Port | Used For | Status |
|-----------|------|----------|--------|
| **stdio** | - | Claude Desktop/Code, Xcode | ✅ Active |
| **HTTP** | 5002 | VS Code, Cursor, Gemini CLI | ✅ Active |
| **SSE** | 5003 | JetBrains IDEs | ✅ Active |

---

## 2. ENDPOINTS & ROUTING

### [ENDPOINT:/mcp] JSON-RPC Gateway
- **Location:** `vetka_mcp_bridge.py` lines 360-612
- **Protocol:** JSON-RPC 2.0 over stdio/HTTP/SSE
- **Methods:**
  - `initialize` - Server handshake
  - `tools/list` - Enumerate available tools
  - `tools/call` - Execute tool with arguments

### [ENDPOINT:localhost:5001] VETKA FastAPI Server
- **Entry:** `main.py` lines 249-257
- **Framework:** FastAPI + Socket.IO (ASGI)
- **Health:** `GET /api/health`
- **Routes:** 13 routers, 59 endpoints (see `src/api/routes/`)

**Key MCP-Related Routes:**
- `GET /api/search/semantic` - Semantic search in Qdrant
- `GET /api/tree/data` - Project tree structure
- `POST /api/files/read` - File content
- `GET /api/tree/knowledge-graph` - Knowledge graph
- `GET /api/metrics/dashboard` - System metrics
- `GET /api/health` - Component status

---

## 3. TOOL REGISTRATION & EXECUTION

### [TOOL:Registered Tools] 13 Total
**Read-Only Tools (8):**
1. `vetka_search_semantic` - Qdrant vector search
2. `vetka_read_file` - Read project files
3. `vetka_get_tree` - Tree structure export
4. `vetka_health` - Component health check
5. `vetka_list_files` - File enumeration
6. `vetka_search_files` - Content search
7. `vetka_get_metrics` - Analytics/metrics
8. `vetka_get_knowledge_graph` - Relationship graph

**Write Tools (5):**
1. `vetka_edit_file` - Edit/create files (dry_run default)
2. `vetka_git_commit` - Git commits (dry_run default)
3. `vetka_run_tests` - Execute pytest
4. `vetka_camera_focus` - 3D UI control

### Tool Schema (OpenAI Compatible)
```json
{
  "name": "tool_name",
  "description": "...",
  "inputSchema": {
    "type": "object",
    "properties": {...},
    "required": [...]
  }
}
```

**Location:** `vetka_mcp_bridge.py` lines 79-353

---

## 4. MODEL CALLING ARCHITECTURE

### [MISSING:Direct LLM Tool] CRITICAL FINDING
**NO dedicated LLM calling tool exists in MCP.**

MCP tools are designed to:
- Search code/knowledge
- Read/write files
- Run tests
- Control UI

They do NOT directly call Claude, GPT, Grok, etc.

### [CONNECT:Via Elisya Gateway] The Actual Model Router
**Path to LLM Calls:**

```
Claude Code (via MCP)
  ↓
vetka_mcp_bridge.py (tools execution)
  ↓
VETKA FastAPI (localhost:5001)
  ↓
src/elisya/ (API Gateway + Router)
  ↓
Model Registry (Claude, GPT, Grok, Ollama, etc.)
```

**Key Files:**
- `src/elisya/api_gateway.py` - Routes model calls to providers
- `src/elisya/model_router_v2.py` - Selects best model
- `src/services/model_registry.py` - Manages available models
- `src/elisya/api_key_detector.py` - Auto-detects 45+ provider keys

### Model Calling Example
Claude Code can:
1. Call `vetka_search_semantic` to find relevant code
2. Read files with `vetka_read_file`
3. Use its own LLM capabilities (Claude Opus)
4. CANNOT directly call Grok/GPT via MCP

To call other models from MCP agents:
- Use Elisya endpoints (not exposed to MCP currently)
- Or extend MCP with `call_model` tool

---

## 5. REQUEST/RESPONSE FLOW

### HTTP MCP Call Flow
```
Client (e.g., VS Code)
  ↓ POST /mcp
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "method": "tools/call",
  "params": {
    "name": "vetka_search_semantic",
    "arguments": {"query": "auth logic", "limit": 10}
  }
}
  ↓
vetka_mcp_server.py handle_mcp() → bridge.call_tool()
  ↓
HTTP → VETKA API (localhost:5001)
  ↓
VETKA routes (e.g., /api/search/semantic)
  ↓ HTTP 200
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "result": {
    "content": [{
      "type": "text",
      "text": "...results..."
    }]
  }
}
```

### Security Layers
- **Rate Limiting:** 60/min API, 10/min writes (`src/mcp/rate_limiter.py`)
- **Approval Flow:** Non-dry-run writes need human approval (`src/mcp/approval.py`)
- **Audit Logging:** All calls logged to `data/mcp_audit/` (`src/mcp/audit_logger.py`)

---

## 6. TOOL IMPLEMENTATION DETAILS

### Base Tool Class
```python
class BaseMCPTool:
  def __init__(self):
    self.name = "tool_name"

  def execute(args: dict) -> dict:
    """Main logic, returns {"success": bool, "result": any, "error": str}"""

  def safe_execute(args: dict) -> dict:
    """Wraps execute with validation, error handling, rate limiting"""

  def validate_arguments(args: dict) -> str | None:
    """Returns error message if validation fails, None if valid"""
```

**Location:** `src/mcp/tools/base_tool.py`

### Implemented Tools
| Tool | File | Lines | Status |
|------|------|-------|--------|
| SearchTool | `search_tool.py` | - | ✅ |
| ReadFileTool | `read_file_tool.py` | - | ✅ |
| EditFileTool | `edit_file_tool.py` | - | ✅ |
| GitCommitTool | `git_tool.py` | - | ✅ |
| RunTestsTool | `run_tests_tool.py` | - | ✅ |
| SearchKnowledgeTool | `search_knowledge_tool.py` | - | ✅ |
| CameraControlTool | `camera_tool.py` | - | ✅ |

---

## 7. EXTERNAL CLIENT INTEGRATION

### [CONNECT:Claude Desktop]
Register in `~/.config/claude/claude.json`:
```json
{
  "mcpServers": {
    "vetka": {
      "command": "python",
      "args": ["/path/to/vetka_mcp_bridge.py"]
    }
  }
}
```

### [CONNECT:Claude Code]
```bash
claude mcp add vetka -- python /path/to/vetka_mcp_bridge.py
```

### [CONNECT:VS Code (HTTP)]
```bash
python src/mcp/vetka_mcp_server.py --http --port 5002
```

Then configure VS Code to use HTTP MCP at `http://localhost:5002/mcp`

### [CONNECT:JetBrains (SSE)]
```bash
python src/mcp/vetka_mcp_server.py --sse --port 5003
```

---

## 8. MODEL CALLING CAPABILITY ANALYSIS

### Current State
- ✅ MCP can access VETKA tools (search, read, write)
- ✅ VETKA has Elisya gateway for model routing
- ✅ 45+ model providers supported (via `api_key_detector.py`)
- ❌ MCP has NO built-in LLM calling tool

### To Add Model Calling to MCP

**Option 1: Create `call_model` MCP Tool**
```python
# src/mcp/tools/llm_call_tool.py
class LLMCallTool(BaseMCPTool):
  name = "vetka_call_model"

  def execute(self, args):
    model = args["model"]  # "claude-opus-4-5", "grok-2", etc.
    prompt = args["prompt"]
    # Call via VETKA Elisya gateway
    response = await http_client.post(
      f"/api/models/{model}/call",
      json={"prompt": prompt}
    )
    return response
```

**Option 2: Extend via Custom Bridge**
Create wrapper that Claude Code directly calls:
```bash
python src/mcp/vetka_mcp_bridge.py --with-llm-tools
```

**Option 3: Use Elisya Direct (No MCP)**
Claude Code uses `https://localhost:5001/api/models/call` directly

---

## 9. SOCKET.IO FOR REAL-TIME FEATURES

### Real-Time Capabilities
- ✅ Group chat with orchestrator agents
- ✅ Chat-as-tree node creation
- ✅ Approval workflow (UI → backend)
- ✅ Hostess memory visualization
- ❌ MCP support (stdio, HTTP/SSE don't use sockets)

**Event Handlers:** `src/api/handlers/` (18 events)

---

## 10. VETKA STARTUP SEQUENCE

```bash
# Start main FastAPI server
python main.py
# OR
uvicorn main:socket_app --host 0.0.0.0 --port 5001

# In separate terminal: Start MCP server (HTTP)
python src/mcp/vetka_mcp_server.py --http --port 5002

# OR for stdio (Claude Desktop)
python src/mcp/vetka_mcp_bridge.py
```

---

## RECOMMENDATIONS

### For Claude Code Model Calling

1. **Keep current approach:** Claude Code uses its own LLM (Opus), MCP is for code tools
2. **Add LLM tool if needed:** Create `vetka_call_model` tool in `src/mcp/tools/`
3. **Use Elisya directly:** Claude Code can call `http://localhost:5001/api/models/call` via HTTP (outside MCP)

### For Team Collaboration

1. HTTP MCP (port 5002) is better than stdio for multi-client scenarios
2. Socket.IO for real-time features requires dedicated UI client
3. Group chat already orchestrates agents via VETKA Elisya

---

## PHASE REFERENCE
- **Phase 39.8:** Flask → FastAPI migration (complete)
- **Phase 65.1:** MCP stdio bridge
- **Phase 65.2:** MCP universal (HTTP/SSE/stdio)
- **Phase 89.5:** This architecture audit

---

**Scout Report Complete**
Total MCP Tools: **13** | FastAPI Routes: **59** | Supported Models: **45+**
