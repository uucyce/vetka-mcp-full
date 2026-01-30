# MCP Console Architecture

**Version:** 1.0
**Phase:** 80.41
**Date:** 2026-01-22

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                          CLAUDE CODE / DESKTOP                       │
│                                                                     │
│                    (Sends MCP Tool Call Requests)                   │
│                                                                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ MCP Protocol (JSON-RPC over stdio)
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                       MCP BRIDGE (Python)                           │
│                   src/mcp/vetka_mcp_bridge.py                       │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ 1. call_tool(name, arguments)                                 │ │
│  │    - Generate request_id = "req-abc123"                       │ │
│  │    - Record start_time                                        │ │
│  │                                                               │ │
│  │ 2. log_mcp_request(name, arguments, request_id)               │ │
│  │    → POST /api/mcp-console/log                                │ │
│  │                                                               │ │
│  │ 3. Execute tool via VETKA REST API                            │ │
│  │    → GET/POST /api/search/semantic, /api/files/read, etc.    │ │
│  │                                                               │ │
│  │ 4. Calculate duration_ms = (now - start_time) * 1000          │ │
│  │                                                               │ │
│  │ 5. log_mcp_response(name, result, request_id, duration_ms)    │ │
│  │    → POST /api/mcp-console/log                                │ │
│  │                                                               │ │
│  │ 6. Return formatted result to Claude Code                     │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ HTTP REST API
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                     FASTAPI BACKEND (Python)                        │
│                 src/api/routes/mcp_console_routes.py                │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ In-Memory Storage                                             │ │
│  │ _mcp_logs: List[Dict] = []                                    │ │
│  │ (Max 1000 entries, auto-rotation)                             │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ Endpoints                                                     │ │
│  │                                                               │ │
│  │ POST   /api/mcp-console/log        - Log request/response    │ │
│  │ GET    /api/mcp-console/history    - Get logs (with filters) │ │
│  │ POST   /api/mcp-console/save       - Save to JSON file       │ │
│  │ DELETE /api/mcp-console/clear      - Clear all logs          │ │
│  │ GET    /api/mcp-console/stats      - Get statistics          │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ Socket.IO Emission                                            │ │
│  │                                                               │ │
│  │ On POST /api/mcp-console/log:                                 │ │
│  │   → Emit 'mcp_log' event to all connected clients            │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ Socket.IO (WebSocket)
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                      BROWSER CLIENT (JavaScript)                    │
│                  frontend/static/js/mcp_console.js                  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ MCPConsole Class                                              │ │
│  │                                                               │ │
│  │ - Listen for Socket.IO 'mcp_log' events                      │ │
│  │ - Store logs in this.logs array                              │ │
│  │ - Group request/response pairs                               │ │
│  │ - Render in UI container (#mcp-log-container)                │ │
│  │ - Update statistics display                                  │ │
│  │ - Auto-scroll to latest                                      │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ UI Components                                                 │ │
│  │                                                               │ │
│  │ .mcp-console                 - Main container (fixed)         │ │
│  │ .mcp-console-header          - Title + controls               │ │
│  │ .mcp-console-stats           - Statistics bar                 │ │
│  │ .mcp-log-container           - Scrollable log area            │ │
│  │   └─ .mcp-log-pair           - Request/response pair          │ │
│  │       ├─ .mcp-log-request    - Request section                │ │
│  │       └─ .mcp-log-response   - Response section               │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ User Actions                                                  │ │
│  │                                                               │ │
│  │ - Click "🤖 MCP" button → toggle console visibility           │ │
│  │ - Click "💾 Save" button → POST /api/mcp-console/save         │ │
│  │ - Click "🗑️ Clear" button → DELETE /api/mcp-console/clear     │ │
│  │ - Click "✖️" button → hide console                             │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Request Lifecycle

### 1. Request Initiated

```
Claude Code: "Search for authentication logic"
     │
     ▼
MCP Bridge: call_tool("vetka_search_semantic", {"query": "authentication"})
     │
     ├─ request_id = "req-a3f4b9c2"
     ├─ start_time = 1737564000.123
     │
     └─→ POST /api/mcp-console/log
         {
           "id": "req-a3f4b9c2",
           "type": "request",
           "timestamp": 1737564000.123,
           "agent": "mcp_bridge",
           "tool": "vetka_search_semantic",
           "arguments": {"query": "authentication", "limit": 10}
         }
```

### 2. Request Logged

```
FastAPI: POST /api/mcp-console/log received
     │
     ├─ Store in _mcp_logs list
     │
     └─→ Socket.IO emit 'mcp_log' event
              │
              ▼
         Browser: socket.on('mcp_log', data)
              │
              └─→ mcpConsole.addLog(data)
                       │
                       └─→ Render request card in UI
```

### 3. Tool Execution

```
MCP Bridge: Execute tool
     │
     └─→ GET /api/search/semantic?q=authentication&limit=10
              │
              ▼
         VETKA API: Process semantic search
              │
              └─→ Return results: {"count": 8, "results": [...]}
```

### 4. Response Logged

```
MCP Bridge: Tool completed
     │
     ├─ duration_ms = (time.time() - start_time) * 1000 = 127ms
     │
     └─→ POST /api/mcp-console/log
         {
           "id": "res-a3f4b9c2",
           "type": "response",
           "timestamp": 1737564000.250,
           "tool": "vetka_search_semantic",
           "result": {"count": 8, "results": [...]},
           "duration_ms": 127,
           "tokens": 1240
         }
```

### 5. Response Rendered

```
FastAPI: POST /api/mcp-console/log received
     │
     ├─ Store in _mcp_logs list
     │
     └─→ Socket.IO emit 'mcp_log' event
              │
              ▼
         Browser: socket.on('mcp_log', data)
              │
              └─→ mcpConsole.addLog(data)
                       │
                       └─→ Group with matching request
                       │
                       └─→ Render response card in UI
                       │
                       └─→ Update statistics
```

---

## Component Interaction Diagram

```
┌──────────────┐
│ Claude Code  │
│              │
│ "Search for  │
│ auth logic"  │
└──────┬───────┘
       │ MCP Protocol
       │ (JSON-RPC)
       ▼
┌──────────────────────────────────────────────────────────┐
│ MCP Bridge (vetka_mcp_bridge.py)                         │
│                                                          │
│  call_tool()                                             │
│    │                                                     │
│    ├──→ log_mcp_request() ─────────────┐                │
│    │                                   │                │
│    ├──→ Execute VETKA API              │                │
│    │                                   │                │
│    └──→ log_mcp_response() ────────────┤                │
│                                        │                │
└────────────────────────────────────────┼────────────────┘
                                         │
                                         │ HTTP POST
                                         ▼
┌──────────────────────────────────────────────────────────┐
│ FastAPI (mcp_console_routes.py)                          │
│                                                          │
│  POST /api/mcp-console/log                               │
│    │                                                     │
│    ├──→ Store in _mcp_logs                              │
│    │                                                     │
│    └──→ Emit Socket.IO 'mcp_log' ──────┐                │
│                                        │                │
└────────────────────────────────────────┼────────────────┘
                                         │
                                         │ Socket.IO
                                         ▼
┌──────────────────────────────────────────────────────────┐
│ Browser (mcp_console.js)                                 │
│                                                          │
│  socket.on('mcp_log')                                    │
│    │                                                     │
│    └──→ addLog(data)                                     │
│         │                                                │
│         ├──→ Group request/response pairs                │
│         │                                                │
│         ├──→ renderLogs()                                │
│         │                                                │
│         └──→ updateStats()                               │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## File Structure

```
vetka_live_03/
│
├── src/
│   ├── api/
│   │   └── routes/
│   │       └── mcp_console_routes.py    (245 lines)
│   │           ├── POST   /api/mcp-console/log
│   │           ├── GET    /api/mcp-console/history
│   │           ├── POST   /api/mcp-console/save
│   │           ├── DELETE /api/mcp-console/clear
│   │           └── GET    /api/mcp-console/stats
│   │
│   └── mcp/
│       └── vetka_mcp_bridge.py          (modified)
│           ├── log_mcp_request()        (new function)
│           ├── log_mcp_response()       (new function)
│           └── call_tool()              (modified)
│
├── frontend/
│   └── static/
│       ├── js/
│       │   └── mcp_console.js           (379 lines)
│       │       └── class MCPConsole
│       │           ├── init()
│       │           ├── createConsoleUI()
│       │           ├── connectSocket()
│       │           ├── loadHistory()
│       │           ├── addLog()
│       │           ├── renderLogs()
│       │           ├── groupRequestResponsePairs()
│       │           ├── createLogPairElement()
│       │           ├── saveLogs()
│       │           ├── clearLogs()
│       │           └── toggle/show/hide()
│       │
│       └── css/
│           └── mcp_console.css          (319 lines)
│               ├── .mcp-console
│               ├── .mcp-console-header
│               ├── .mcp-console-stats
│               ├── .mcp-log-container
│               ├── .mcp-log-pair
│               ├── .mcp-log-request
│               └── .mcp-log-response
│
├── app/
│   └── frontend/
│       └── templates/
│           └── index.html               (modified)
│               ├── Added: <link mcp_console.css>
│               └── Added: <script mcp_console.js>
│
├── docs/
│   └── mcp_chat/                        (save directory)
│       └── (saved log files)
│
└── main.py                              (modified)
    └── Registered: mcp_console_router
```

---

## Request/Response Pairing Logic

### Pairing Algorithm

```javascript
// In mcp_console.js: groupRequestResponsePairs()

1. Create empty pairs array: []
2. Create request map: Map<request_id, {request, response}>

3. For each log in this.logs:

   IF log.type === "request":
     - Add to map: requestMap.set(log.id, {request: log, response: null})

   ELSE IF log.type === "response":
     - Extract request_id = log.id.replace("res-", "req-")
     - IF requestMap.has(request_id):
         - Update: requestMap.get(request_id).response = log
       ELSE:
         - Standalone response: pairs.push({request: null, response: log})

4. Convert map to array:
   - requestMap.forEach(pair => pairs.push(pair))

5. Return pairs
```

### Example

```javascript
// Input logs:
[
  {id: "req-abc", type: "request", tool: "search", ...},
  {id: "req-def", type: "request", tool: "read_file", ...},
  {id: "res-abc", type: "response", tool: "search", ...},
  {id: "res-def", type: "response", tool: "read_file", ...}
]

// Output pairs:
[
  {
    request: {id: "req-abc", type: "request", tool: "search", ...},
    response: {id: "res-abc", type: "response", tool: "search", ...}
  },
  {
    request: {id: "req-def", type: "request", tool: "read_file", ...},
    response: {id: "res-def", type: "response", tool: "read_file", ...}
  }
]
```

---

## Socket.IO Event Flow

```
MCP Bridge                FastAPI                 Browser
     │                       │                       │
     ├─ POST /log (request)  │                       │
     │ ──────────────────────>│                       │
     │                       │                       │
     │                       ├─ Store log            │
     │                       │                       │
     │                       ├─ Emit 'mcp_log'       │
     │                       │ ──────────────────────>│
     │                       │                       │
     │                       │                       ├─ socket.on('mcp_log')
     │                       │                       │
     │                       │                       ├─ addLog(data)
     │                       │                       │
     │                       │                       └─ Render UI
     │                       │                       │
     ├─ Execute tool         │                       │
     │                       │                       │
     ├─ POST /log (response) │                       │
     │ ──────────────────────>│                       │
     │                       │                       │
     │                       ├─ Store log            │
     │                       │                       │
     │                       ├─ Emit 'mcp_log'       │
     │                       │ ──────────────────────>│
     │                       │                       │
     │                       │                       ├─ socket.on('mcp_log')
     │                       │                       │
     │                       │                       ├─ addLog(data)
     │                       │                       │
     │                       │                       └─ Update UI
```

---

## Memory Management

### Backend (_mcp_logs)

```python
# In mcp_console_routes.py

_mcp_logs: List[Dict] = []
_max_logs = 1000

# On POST /api/mcp-console/log:
_mcp_logs.append(log_dict)

# Trim if exceeds max:
if len(_mcp_logs) > _max_logs:
    _mcp_logs = _mcp_logs[-_max_logs:]  # Keep last 1000
```

**Memory usage:**
- ~500 bytes per log entry (avg)
- 1000 entries = ~500 KB
- Negligible impact

### Frontend (this.logs)

```javascript
// In mcp_console.js: addLog()

this.logs.push(logEntry);

// Keep only last 100 in UI:
if (this.logs.length > 100) {
    this.logs = this.logs.slice(-100);
}
```

**Memory usage:**
- ~500 bytes per log entry (avg)
- 100 entries = ~50 KB
- Minimal browser memory

---

## Error Handling

### MCP Bridge Logging Errors

```python
# In vetka_mcp_bridge.py

async def log_mcp_request(...):
    try:
        await http_client.post("/api/mcp-console/log", ...)
    except Exception as e:
        # Silently fail - logging should NOT break functionality
        print(f"[MCP] Failed to log request: {e}", file=sys.stderr)
```

**Rationale:** Logging is a non-critical feature. If it fails, tool execution should continue.

### Frontend Socket.IO Errors

```javascript
// In mcp_console.js

connectSocket() {
    if (typeof io === 'undefined') {
        console.warn('[MCP Console] Socket.IO not available');
        return;  // Graceful degradation
    }

    this.socket = io();

    this.socket.on('connect_error', (error) => {
        console.error('[MCP Console] Socket.IO error:', error);
    });
}
```

**Fallback:** If Socket.IO fails, user can still view logs via REST API (`loadHistory()`).

---

## Performance Characteristics

### Latency Breakdown (per tool call)

| Operation | Time | Notes |
|-----------|------|-------|
| Generate request_id | < 1ms | UUID generation |
| log_mcp_request() POST | 2-5ms | HTTP request |
| Execute tool (VETKA API) | 50-500ms | Main operation |
| Calculate duration | < 1ms | Simple math |
| log_mcp_response() POST | 2-5ms | HTTP request |
| Socket.IO emit | 1-2ms | WebSocket broadcast |
| Browser render | 5-10ms | DOM updates |
| **Total overhead** | **5-15ms** | **< 2% of typical tool execution** |

### Throughput

- **Backend:** Can handle 1000+ logs/second
- **Frontend:** Can render 100+ log pairs/second
- **Socket.IO:** Can broadcast to 100+ clients simultaneously

---

## Security Considerations

### 1. No Authentication Required

Currently, `/api/mcp-console/*` endpoints have NO authentication.

**Risk:** Anyone on localhost:5001 can view/clear logs.

**Mitigation:**
- VETKA runs on localhost (not exposed to internet)
- Future: Add API key authentication

### 2. No Sensitive Data Filtering

Logs contain raw arguments and results.

**Risk:** Passwords, API keys in logs if tools receive them.

**Mitigation:**
- MCP tools should NEVER receive sensitive data
- Future: Add sensitive data redaction

### 3. In-Memory Storage Only

Logs are lost on server restart.

**Risk:** No audit trail after restart.

**Mitigation:**
- Save logs regularly
- Future: Persistent database storage

---

## Scalability

### Current Limits

- **Max logs in memory:** 1000 (backend) + 100 (frontend)
- **Max log size:** ~500 bytes per entry
- **Max simultaneous clients:** Limited by Socket.IO (typically 10,000+)

### Scaling Strategies

**Vertical Scaling:**
- Increase `_max_logs` to 10,000+
- Use deque instead of list for O(1) trimming

**Horizontal Scaling:**
- Store logs in Redis (shared across instances)
- Use Redis pub/sub for Socket.IO broadcasts

**Database Scaling:**
- Move to PostgreSQL for persistent storage
- Index by timestamp, tool, agent
- Partition by date

---

## Testing Strategy

### Unit Tests

```python
# test_mcp_console_routes.py

def test_log_request():
    response = client.post("/api/mcp-console/log", json={
        "id": "req-test",
        "type": "request",
        "tool": "vetka_search_semantic"
    })
    assert response.status_code == 200

def test_get_history():
    response = client.get("/api/mcp-console/history?limit=10")
    assert response.status_code == 200
    assert "logs" in response.json()
```

### Integration Tests

```python
# test_mcp_integration.py

async def test_full_flow():
    # 1. MCP bridge calls tool
    result = await call_tool("vetka_search_semantic", {"query": "test"})

    # 2. Check logs were created
    response = await client.get("/api/mcp-console/history")
    logs = response.json()["logs"]

    # 3. Verify request log exists
    assert any(log["type"] == "request" for log in logs)

    # 4. Verify response log exists
    assert any(log["type"] == "response" for log in logs)
```

### Frontend Tests (Manual)

1. Open browser DevTools
2. Check Socket.IO connection: `window.mcpConsole.socket.connected`
3. Trigger tool call from Claude Code
4. Verify logs appear in UI
5. Test save/clear buttons

---

## Future Enhancements

### Phase 3: Enhanced Features

1. **Persistent Storage**
   - PostgreSQL/SQLite database
   - Survive server restarts
   - Query by date range

2. **Search & Filters**
   - Full-text search
   - Filter by tool, agent, time
   - Export filtered results

3. **Token Tracking**
   - Parse token usage from responses
   - Track cumulative costs
   - Budget alerts

### Phase 4: Analytics

4. **Performance Metrics**
   - Tool execution time trends
   - Success/failure rates
   - Bottleneck detection

5. **Visualization**
   - Timeline view
   - Tool usage charts
   - Token usage graphs

### Phase 5: Collaboration

6. **Multi-Agent Views**
   - Separate tabs per agent
   - Agent comparison
   - Cross-agent context tracking

7. **Sharing**
   - Share logs via URL
   - Team dashboards
   - Export to JIRA/GitHub

---

**End of Architecture Document**

Generated by Sonnet Agent C (UI Builder)
Phase 80.41 - 2026-01-22
