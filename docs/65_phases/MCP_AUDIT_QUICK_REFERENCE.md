# MCP Audit Quick Reference

## TL;DR

| Item | Value |
|------|-------|
| **Port** | 5001 ✅ |
| **Framework** | FastAPI (100% from Flask) ✅ |
| **MCP Tools** | 15 (via Socket.IO) ✅ |
| **REST Endpoints** | 59+ ✅ |
| **Socket.IO Events** | 40+ ✅ |
| **Qdrant** | Active (localhost:6333) ✅ |
| **Approval System** | Active ✅ |
| **Camera Control** | Socket.IO event ✅ |
| **Git Operations** | Via MCP tools ✅ |

---

## Critical Endpoints for Skills Config

### Server Connection
```
http://localhost:5001
ws://localhost:5001 (Socket.IO)
```

### MCP Tool Delivery
- **Protocol:** Socket.IO (WebSocket)
- **Event:** `tool_call`
- **Response:** `tool_result` event
- **No REST API for tool calls** (use Socket.IO)

### Health Check
```
GET http://localhost:5001/api/health
```

### List Models
```
GET http://localhost:5001/api/config/models
```

### List Keys
```
GET http://localhost:5001/api/keys
```

---

## MCP Tools (15)

### Read-Only (No Approval)
- `vetka_search` - File search
- `vetka_search_knowledge` - Semantic search
- `vetka_read_file` - Read file
- `vetka_list_files` - List files
- `vetka_get_tree` - Get hierarchy
- `vetka_get_node` - Get node details
- `vetka_git_status` - Git status
- `vetka_camera_focus` - 3D camera

### Write (Approval Required)
- `vetka_edit_file` - Edit/create file
- `vetka_git_commit` - Create commit
- `vetka_create_branch` - Create folder
- `vetka_run_tests` - Run tests

### Intake (Phase 22)
- `vetka_intake_url` - URL processing
- `vetka_list_intakes` - List intakes
- `vetka_get_intake` - Get intake

---

## Key Socket.IO Events

### Chat
- `user_message` - Send message
- `message_reaction` - React to message
- `mark_messages_read` - Mark read

### Groups
- `join_group`, `leave_group`
- `group_message`, `group_typing`

### Approval
- `approve_artifact`, `reject_artifact`
- `get_pending_approvals`

### Voice
- `voice_connect`, `voice_disconnect`
- `voice_start`, `voice_stop`
- `voice_audio`, `voice_pcm`

### Workflows
- `start_workflow` (namespace: `/workflow`)
- `join_workflow`, `leave_workflow`
- `get_workflow_status`, `cancel_workflow`

### Tree
- `fork_branch`, `move_to_parent`
- `select_branch`, `refactor_knowledge`

### MCP
- `tool_call` → server processes → `tool_result`

---

## Configuration Files

### Where to Update Skills
```
~/.config/mcp/servers/vetka_claude_code/
```

### Settings in main.py
- Line 815: Port from env or default 5001
- Line 816: Host from env or default 0.0.0.0
- Line 273: Socket.IO in app.state

### Environment (.env)
```
VETKA_PORT=5001
VETKA_HOST=0.0.0.0
```

---

## Common Workflows

### Tool Call (via Socket.IO)
1. Emit `tool_call` event with tool name + args
2. Server processes via `MCPServer.handle_tool_call()`
3. Checks rate limit + approval
4. Executes tool
5. Emits `tool_result` with result/error

### Approval Flow (for write operations)
1. Tool requires approval → returns `needs_approval: True`
2. Get `approval_id` from response
3. User approves via `POST /api/approval/{approval_id}/approve`
4. Re-submit tool with `_approval_id` parameter

### File Operations
- **Read:** REST `POST /api/files/read` or `vetka_read_file` tool
- **Write:** `vetka_edit_file` tool (requires approval)
- **List:** `vetka_list_files` tool or `POST /api/files/search`

### Semantic Search
- **REST:** `GET /api/search/semantic?query=...`
- **MCP:** `vetka_search_knowledge` tool
- **Backend:** Qdrant (localhost:6333)

---

## Rate Limits

- **API calls:** 60/min
- **Write operations:** 10/min
- **All calls logged** to `data/mcp_audit/`

---

## Status Indicators

### Components (from /api/health)
- ✅ metrics_engine
- ✅ model_router
- ✅ api_gateway
- ✅ qdrant
- ✅ feedback_loop
- ✅ smart_learner
- ✅ hope_enhancer
- ✅ embeddings_projector
- ✅ student_system
- ✅ learner
- ✅ elisya

---

## Files to Know

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app entry |
| `src/mcp/mcp_server.py` | MCP core |
| `src/mcp/tools/` | 15 tools (8 + 4 + 3) |
| `src/api/routes/` | 59+ REST endpoints |
| `src/api/handlers/` | 20 Socket.IO handlers |
| `src/knowledge_graph/` | Qdrant integration |
| `src/mcp/approval.py` | Approval system |
| `src/mcp/rate_limiter.py` | Rate limiting |
| `src/mcp/audit_logger.py` | Audit logs |

---

## One-Liner Tests

```bash
# Health
curl http://localhost:5001/api/health | jq .

# Models
curl http://localhost:5001/api/config/models | jq '.models[0:3]'

# Keys
curl http://localhost:5001/api/keys | jq '.providers'

# OpenAPI
curl http://localhost:5001/openapi.json | jq '.paths | keys' | head -20
```

---

## Summary

✅ **All 15 MCP tools are working**
✅ **59+ REST endpoints are active**
✅ **Socket.IO event streaming is ready**
✅ **Qdrant semantic search is connected**
✅ **Approval system protects write operations**
✅ **Rate limiting prevents abuse**
✅ **Audit logging captures all activity**

**Port 5001 is correct and production-ready!**

See `MCP_AUDIT_RESULTS.md` for full details.
