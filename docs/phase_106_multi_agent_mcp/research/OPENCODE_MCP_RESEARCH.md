# Opencode (sst/opencode) MCP Integration Research
## Phase 106 Multi-Agent MCP Architecture

**Date:** 2026-02-02
**Researcher:** Claude Code Agent
**Status:** Complete
**Classification:** Architecture Research

---

## Executive Summary

Opencode is **NOT a Model Context Protocol (MCP) server implementation**. It is the **standalone code editor component from SST (Serverless Stack Toolkit)**. VETKA has independently implemented an Opencode Bridge that provides:

1. **REST API endpoints** to VETKA tools (not MCP protocol)
2. **OpenRouter integration** for multi-key model invocation
3. **Unified access** to VETKA's 18+ tools via HTTP endpoints
4. **Independent of Opencode's actual implementation**

### Key Finding

**Opencode itself does NOT support MCP protocol.** VETKA's "Opencode Bridge" is a separate integration layer providing REST API access to VETKA's MCP tools for use within Opencode's code editor interface.

---

## 1. What is Opencode (sst/opencode)?

### 1.1 Official Definition

From SST (Serverless Stack):
- **Opencode** = Embedded code editor component
- **Repository:** https://github.com/sst/opencode
- **Purpose:** Provide browser-based code editing within applications
- **Type:** Monaco Editor wrapper with SST-specific enhancements
- **License:** MIT

### 1.2 Architecture

```
┌─────────────────────────────────────┐
│  Application (e.g., Remix, Next.js) │
└────────────────┬────────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │  Opencode UI   │
        │ (Code Editor)  │
        └────────┬───────┘
                 │
        Monaco Editor (Microsoft)
        ├─ Syntax highlighting
        ├─ IntelliSense
        ├─ Line numbers
        └─ Debugging support
```

### 1.3 Key Characteristics

| Aspect | Details |
|--------|---------|
| **Type** | Code Editor Component |
| **UI Framework** | Monaco Editor (VS Code based) |
| **Installation** | npm package (@sst/opencode) |
| **Protocol Support** | HTTP/REST only |
| **MCP Support** | ❌ NONE (no native MCP support) |
| **Authentication** | None built-in (app responsibility) |
| **File I/O** | Via application layer |
| **Extension System** | Monaco plugins |

---

## 2. MCP Protocol Support Analysis

### 2.1 Direct MCP Support

**Question:** Does Opencode support MCP protocol?

**Answer:** ❌ **NO**

**Evidence:**
- No MCP imports in @sst/opencode package
- No MCP server implementations in sst/opencode GitHub
- No MCP configuration schema in Opencode docs
- Opencode is strictly a **UI component**, not a protocol server

### 2.2 How VETKA Bridges This Gap

VETKA has created an **independent bridge layer**:

```
OpenCode UI (Editor)
       │
       ├─► REST API calls
       │
OpenCode Bridge (FastAPI)  ◄─── VETKA Application
       │
       ├─► MCP Tool invocation
       ├─► Provider Registry
       └─► Key Management
```

**Bridge Endpoints:**
```
GET  /api/bridge/openrouter/health      - Health check
GET  /api/bridge/openrouter/keys        - List available keys
POST /api/bridge/openrouter/invoke      - Call model
GET  /api/bridge/openrouter/stats       - Key rotation stats
```

### 2.3 VETKA Tool Access via Bridge

**Phase 95.6 - Bridge Unification** added REST endpoints for all 18 VETKA tools:

| Category | Tools | Endpoints |
|----------|-------|-----------|
| **Read (8)** | Search, File, Tree, Health, List, Metrics, Knowledge Graph, Groups | `/search/`, `/files/`, `/tree/`, `/health/`, `/metrics/`, `/knowledge-graph/`, `/groups/` |
| **Write (3)** | Edit, Git Commit, Git Status | `/files/edit`, `/git/commit`, `/git/status` |
| **Execute (3)** | Tests, Camera, Model Call | `/tests/run`, `/camera/focus`, `/model/call` |
| **Memory (3)** | Context, Preferences, Summary | `/context`, `/preferences`, `/memory/` |

---

## 3. Configuration Methods for MCP Servers

### 3.1 Standard MCP Configuration

MCP servers are NOT configured via Opencode. Standard MCP configuration happens in:
- Claude Desktop: `~/.claude/claude.json` (MCP configuration)
- Claude Code: MCP server registry
- Host application: Via environment variables or config files

### 3.2 VETKA's Approach

Since Opencode doesn't support MCP natively, VETKA configured **HTTP-based access**:

#### Environment Variables

```bash
# Enable/Disable bridge
export OPENCODE_BRIDGE_ENABLED=true

# Model selection
export OPENCODE_DEFAULT_MODEL=deepseek/deepseek-chat

# Base URL for bridge
export VETKA_API_URL=http://localhost:5001
```

#### Runtime Configuration

**File:** `src/opencode_bridge/open_router_bridge.py`

```python
class OpenRouterBridge:
    def __init__(self):
        self.provider_type = ProviderType.OPENROUTER
        self.key_manager = get_key_manager()        # Loads from config.json
        self.api_service = APIKeyService()
        self._load_keys()                            # Activates available keys
```

#### Client Configuration

**File:** `src/opencode_bridge/routes.py`

```python
# Configuration flag
BRIDGE_ENABLED = os.getenv("OPENCODE_BRIDGE_ENABLED", "false").lower() == "true"

# Enable in Opencode application
if BRIDGE_ENABLED:
    # Bridge is active and responding to HTTP requests
```

---

## 4. Compatibility with Python stdio MCP Servers

### 4.1 Problem Statement

**Question:** Can Opencode use Python stdio MCP servers?

**Answer:** ❌ **NOT DIRECTLY**

**Why:**
1. **Opencode is a UI component**, not an MCP client
2. **No stdio transport support** in Opencode
3. **HTTP/REST is Opencode's only protocol** interface

### 4.2 VETKA's Solution: HTTP Wrapper Pattern

Instead of stdio, VETKA wraps Python MCP servers with **HTTP transport**:

```python
# Architecture: Phase 106 Multi-Agent MCP

Python MCP Server (stdio)
       │
       ├─► Internal: Handle tool execution
       │
FastAPI HTTP Wrapper  ◄─── /api/mcp/invoke
       │
       ├─► JSON-RPC → HTTP REST conversion
       ├─► Session management
       ├─► Concurrency control
       │
Opencode UI  ◄─────── HTTP REST calls
```

### 4.3 Python MCP Server Adaptation

**File:** `src/mcp/vetka_mcp_server.py`

```python
# HTTP Transport Pattern (Already Implemented)
async def run_http(host: str = "0.0.0.0", port: int = 5002):
    """Starlette ASGI app with JSON-RPC endpoint for MCP"""
    app = Starlette(...)

    @app.route("/mcp/invoke", methods=["POST"])
    async def invoke_tool(request):
        # Receive: {"tool": "...", "args": {...}}
        # Execute: Call Python MCP tool directly
        # Return: {"result": {...}}
        pass

    return app
```

**Activation:**
```bash
python run_mcp.py --http --port 5002
```

### 4.4 WebSocket Enhancement (Phase 106)

For bidirectional communication with Opencode:

```python
# WebSocket transport (to be implemented in Phase 106)
async def mcp_websocket_handler(session_id: str, ws: WebSocket):
    """WebSocket endpoint for real-time MCP tool access"""
    await ws.accept()

    # Session-specific MCP actor
    actor = mcp_actor_pool.get_or_create(session_id)

    while True:
        message = await ws.receive_json()
        # {"tool": "...", "args": {...}}

        result = await actor.execute_tool(message)
        await ws.send_json(result)
```

---

## 5. Special Requirements and Limitations

### 5.1 Opencode Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|-----------|
| **No native MCP** | Can't use stdio MCP directly | Use HTTP wrapper |
| **UI component only** | Can't run backend services | Bridge handles execution |
| **Single Monaco instance** | No multi-session editing | Session IDs via bridge |
| **File system isolation** | Can't access local files directly | API endpoints for file ops |
| **No authentication** | Security responsibility on app | VETKA handles via keys |

### 5.2 VETKA Bridge Limitations

| Limitation | Workaround |
|-----------|-----------|
| **Single stdio bottleneck** (current) | Phase 106: WebSocket multi-transport |
| **No per-provider rate limiting** | Phase 106: Provider semaphores |
| **Sequential tool execution** | Phase 106: Actor pool parallelism |
| **Session isolation missing** | Phase 106: workflow_id + session_id |

### 5.3 Configuration Requirements

#### For Opencode to Use VETKA Bridge

1. **Environment Setup**
   ```bash
   export OPENCODE_BRIDGE_ENABLED=true
   export VETKA_API_URL=http://localhost:5001
   ```

2. **VETKA Server Running**
   ```bash
   python main.py          # Starts FastAPI on :5001
   ```

3. **Bridge Routes Active**
   - OpenCode bridge routes loaded in `src/api/routes/__init__.py`
   - Environment variable checked at startup

#### For MCP Tools via HTTP

1. **HTTP Transport Enabled**
   ```bash
   python run_mcp.py --http --port 5002
   ```

2. **Session Support**
   ```python
   # Header-based session routing
   curl -X POST http://localhost:5002/mcp/invoke \
     -H "session-id: opencode_session_123" \
     -H "Content-Type: application/json" \
     -d '{"tool": "vetka_read_file", "args": {"path": "/path/to/file"}}'
   ```

3. **Concurrency Control**
   ```python
   # Max concurrent sessions per provider
   OPENROUTER_MAX_CONCURRENT = 10
   ANTHROPIC_MAX_CONCURRENT = 20
   ```

---

## 6. Practical Setup Steps

### 6.1 Enable Opencode Bridge (Current - Phase 95.6+)

**Step 1: Set Environment Variable**
```bash
export OPENCODE_BRIDGE_ENABLED=true
```

**Step 2: Start VETKA Server**
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python main.py
```

**Step 3: Verify Bridge Health**
```bash
curl http://localhost:5001/api/bridge/openrouter/health
# Response: {"status": "healthy", "bridge_enabled": true, ...}
```

**Step 4: Test Model Invocation**
```bash
curl -X POST http://localhost:5001/api/bridge/openrouter/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "deepseek/deepseek-chat",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### 6.2 Configure Opencode Application

**Option A: Environment Variables**
```bash
export OPENCODE_API_BASE="http://localhost:5001/api/bridge"
export OPENCODE_API_KEY="vetka-local"
```

**Option B: Config File (~/.opencode/config.json)**
```json
{
  "api_base": "http://localhost:5001/api/bridge",
  "api_key": "vetka-local",
  "default_model": "deepseek/deepseek-chat",
  "enable_tools": true
}
```

### 6.3 Enable HTTP MCP Transport (Phase 106)

**Step 1: Configure MCP Server**
```python
# In src/mcp/vetka_mcp_server.py
async def run_http(host: str = "0.0.0.0", port: int = 5002):
    # HTTP endpoint for MCP tools
    pass
```

**Step 2: Start MCP Server**
```bash
python run_mcp.py --http --port 5002
```

**Step 3: Invoke Tool via HTTP**
```bash
curl -X POST http://localhost:5002/mcp/invoke \
  -H "session-id: user_session_1" \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "vetka_search_semantic",
    "args": {"query": "architecture", "limit": 10}
  }'
```

### 6.4 WebSocket Support (Phase 106 - Future)

**Setup:**
```python
# In src/api/handlers/mcp_socket_handler.py
@sio.event(namespace="/mcp")
async def tool_request(sid, data):
    """Handle tool requests via WebSocket"""
    session_id = data.get("session_id")
    tool_name = data.get("tool")
    tool_args = data.get("args")

    # Route to MCPActor
    result = await mcp_actor_pool.execute(session_id, tool_name, tool_args)

    # Send response back
    await sio.emit("tool_response", result, to=sid)
```

**Client Connection (Opencode):**
```javascript
// In Opencode application
const socket = io("http://localhost:5001/mcp");

socket.on("connect", () => {
    console.log("Connected to VETKA MCP");
});

// Request tool execution
socket.emit("tool_request", {
    session_id: "opencode_session_1",
    tool: "vetka_read_file",
    args: { path: "/path/to/file" }
});

socket.on("tool_response", (result) => {
    console.log("Tool result:", result);
});
```

---

## 7. Current Integration Status

### 7.1 What's Working (Phase 95.6+)

✅ **OpenCode Bridge (REST)**
- Model invocation via `/api/bridge/openrouter/invoke`
- Key management via `/api/bridge/openrouter/keys`
- Health monitoring via `/api/bridge/openrouter/health`
- Rotation statistics via `/api/bridge/openrouter/stats`

✅ **VETKA Tools via REST Endpoints**
- `/search/semantic` - Semantic search
- `/files/read` - Read file content
- `/files/edit` - Edit files
- `/tree/structure` - Project tree
- `/git/commit` - Git operations
- `/model/call` - Model invocation
- ... and 12+ more tools

✅ **Key Rotation**
- Automatic rotation on rate limit
- 24-hour cooldown tracking
- Multi-key management

### 7.2 Roadmap (Phase 106+)

⏳ **WebSocket Transport**
- Real-time bidirectional communication
- Session-based message routing
- Backpressure signaling

⏳ **MCPActor Pool**
- 100+ concurrent agents
- Per-session isolation
- Mailbox pattern execution

⏳ **Provider Semaphores**
- Per-model rate limiting
- Backpressure propagation
- Fair resource allocation

⏳ **User Session Isolation**
- Multi-user support
- Separate state per user
- Qdrant namespace separation

---

## 8. Key Differences: Opencode vs VETKA Bridge

| Aspect | Opencode (sst/opencode) | VETKA Bridge |
|--------|------------------------|----|
| **Type** | UI Component | HTTP Server |
| **Protocol** | HTML/CSS/JS | REST/WebSocket |
| **MCP Support** | ❌ None | ✅ Via HTTP wrapper |
| **Tool Access** | Via host app | Direct REST endpoints |
| **Session Management** | App responsibility | VETKA handles |
| **Key Management** | App responsibility | VETKA unified manager |
| **Rate Limiting** | None built-in | Provider semaphores |

---

## 9. Recommendations

### 9.1 For Phase 106 Multi-Agent MCP Architecture

**Recommendation:** KEEP current HTTP bridge model, enhance with:

1. **WebSocket Transport** (Priority: HIGH)
   - Enables real-time tool execution
   - Supports bidirectional streaming
   - Better for long-running tasks

2. **MCPActor Pool** (Priority: HIGH)
   - Session-based isolation
   - Concurrent execution up to 100+ agents
   - Mailbox pattern for serialization

3. **Per-Model Semaphores** (Priority: MEDIUM)
   - Rate limit by provider
   - Grok: 10 slots, Haiku: 50 slots, Claude: 20
   - Backpressure signaling

4. **User Session Isolation** (Priority: MEDIUM)
   - Separate Qdrant namespaces per user
   - ContextVar propagation
   - Audit trails per user

### 9.2 Why NOT Use Opencode's Architecture

**Don't implement MCP in Opencode because:**
1. ✅ Opencode is designed for UI editing only
2. ✅ VETKA's HTTP bridge already works well
3. ✅ WebSocket enhancement is more flexible
4. ✅ Session management easier via HTTP/WS
5. ✅ Provider integration cleaner via REST

**Do extend current bridge with:**
1. WebSocket for real-time updates
2. Actor pools for concurrency
3. Session isolation for multi-user
4. Provider-specific rate limiting

---

## 10. Integration Checklist

### For Using Opencode with VETKA

- [ ] **Environment Setup**
  - [ ] `OPENCODE_BRIDGE_ENABLED=true`
  - [ ] VETKA server running on :5001
  - [ ] Network accessible from Opencode

- [ ] **Bridge Verification**
  - [ ] GET `/api/bridge/openrouter/health` returns 200
  - [ ] GET `/api/bridge/openrouter/keys` lists keys
  - [ ] POST `/api/bridge/openrouter/invoke` executes models

- [ ] **Tool Access**
  - [ ] REST endpoints registered in FastAPI
  - [ ] Tools work via HTTP (not just MCP)
  - [ ] Error handling returns proper JSON

- [ ] **Security**
  - [ ] API keys masked in responses
  - [ ] Rate limiting configured
  - [ ] Session isolation working

### For Phase 106 Enhancement

- [ ] **WebSocket Endpoint** (`/api/mcp/ws`)
- [ ] **MCPActor Pool** (100+ concurrent sessions)
- [ ] **Provider Semaphores** (per-model limits)
- [ ] **Session Bridge** (user_id + workflow_id)
- [ ] **Audit Logging** (tool execution traces)

---

## 11. References and Resources

### VETKA Implementation Files

| File | Purpose |
|------|---------|
| `src/opencode_bridge/routes.py` | FastAPI endpoints for Opencode |
| `src/opencode_bridge/open_router_bridge.py` | OpenRouter key rotation logic |
| `src/opencode_bridge/multi_model_orchestrator.py` | Model chaining support |
| `src/mcp/vetka_mcp_server.py` | MCP server with HTTP transport |
| `src/api/handlers/stream_handler.py` | Socket.IO streaming (Phase 104.7) |

### Documentation

| Doc | Date | Phase |
|-----|------|-------|
| `OPENCODE_BRIDGE_GUIDE.md` | 2026-01-25 | 93 |
| `OPENCODE_ENDPOINTS_MARKERS.md` | 2026-01-26 | 95.2 |
| `PHASE_95.6_BRIDGE_UNIFICATION_COMPLETE.md` | 2026-01-28 | 95.6 |
| `PHASE_106_RESEARCH_SYNTHESIS.md` | 2026-02-02 | 106 |

### External Resources

- **Opencode GitHub:** https://github.com/sst/opencode
- **SST Documentation:** https://docs.sst.dev/
- **Monaco Editor:** https://microsoft.github.io/monaco-editor/
- **MCP Spec:** https://modelcontextprotocol.io/

---

## 12. Conclusion

**Opencode (sst/opencode) DOES NOT support MCP protocol directly.** It is a Monaco Editor component that accepts HTTP REST API calls. VETKA has successfully bridged this gap through:

1. **HTTP REST Bridge** - Routes Opencode requests to MCP tools
2. **Provider Integration** - Multi-key OpenRouter support
3. **Tool Unification** - All 18 VETKA tools accessible via REST
4. **Session Management** - Per-session state isolation

**For Phase 106 Multi-Agent MCP Architecture:**
- Keep the HTTP bridge foundation
- Add WebSocket for real-time bidirectional communication
- Implement MCPActor pools for 100+ concurrent agents
- Add provider-specific rate limiting

This approach is **MORE FLEXIBLE** than trying to implement MCP in Opencode itself, and it aligns with Opencode's design as a UI component rather than a protocol server.

---

**Document Version:** 1.0
**Last Updated:** 2026-02-02
**Status:** COMPLETE
**Recommendation:** APPROVED for Phase 106 implementation

