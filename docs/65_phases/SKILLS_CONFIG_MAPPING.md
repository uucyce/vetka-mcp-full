# MCP Skills Config Mapping

## Skills-to-Endpoints Reference

This document maps each MCP tool to its actual implementation location and how to call it.

---

## 1. Read-Only Tools (Safe)

### vetka_search
**Purpose:** Search files by name or content
**Status:** ✅ Production
**Transport:** Socket.IO
**Approval:** ❌ Not required

**Call:**
```json
{
  "id": "123",
  "name": "vetka_search",
  "arguments": {
    "query": "search term",
    "search_type": "name"  // or "content"
  }
}
```

**Handler:** `src/mcp/tools/search_tool.py`
**Line:** Class `SearchTool`

**Response Example:**
```json
{
  "jsonrpc": "2.0",
  "id": "123",
  "result": {
    "success": true,
    "files": [
      {
        "path": "/path/to/file.py",
        "name": "file.py",
        "matched": true
      }
    ]
  }
}
```

---

### vetka_search_knowledge
**Purpose:** Semantic search with embeddings (Qdrant)
**Status:** ✅ Production
**Transport:** Socket.IO
**Approval:** ❌ Not required

**Call:**
```json
{
  "id": "124",
  "name": "vetka_search_knowledge",
  "arguments": {
    "query": "authentication system",
    "limit": 10,
    "threshold": 0.5
  }
}
```

**Handler:** `src/mcp/tools/search_knowledge_tool.py`
**Backend:** Qdrant (localhost:6333)
**REST Alternative:** `GET /api/search/semantic?query=...`

**Response Example:**
```json
{
  "jsonrpc": "2.0",
  "id": "124",
  "result": {
    "success": true,
    "results": [
      {
        "file_id": "12345",
        "path": "/src/auth/login.py",
        "relevance": 0.92,
        "content_snippet": "..."
      }
    ]
  }
}
```

---

### vetka_read_file
**Purpose:** Read file content
**Status:** ✅ Production
**Transport:** Socket.IO
**Approval:** ❌ Not required

**Call:**
```json
{
  "id": "125",
  "name": "vetka_read_file",
  "arguments": {
    "file_path": "/path/to/file.py",
    "encoding": "utf-8"
  }
}
```

**Handler:** `src/mcp/tools/read_file_tool.py`
**REST Alternative:** `POST /api/files/read` with `{"file_path": "..."}`

**Response Example:**
```json
{
  "jsonrpc": "2.0",
  "id": "125",
  "result": {
    "success": true,
    "content": "import os\nprint('hello')",
    "lines": 2,
    "encoding": "utf-8"
  }
}
```

---

### vetka_list_files
**Purpose:** List directory contents
**Status:** ✅ Production
**Transport:** Socket.IO
**Approval:** ❌ Not required

**Call:**
```json
{
  "id": "126",
  "name": "vetka_list_files",
  "arguments": {
    "path": "/src",
    "recursive": false,
    "include_hidden": false
  }
}
```

**Handler:** `src/mcp/tools/list_files_tool.py`

**Response Example:**
```json
{
  "jsonrpc": "2.0",
  "id": "126",
  "result": {
    "success": true,
    "files": [
      {"name": "main.py", "type": "file", "size": 1024},
      {"name": "config", "type": "dir", "size": 4096}
    ]
  }
}
```

---

### vetka_get_tree
**Purpose:** Get folder/file hierarchy
**Status:** ✅ Production
**Transport:** Socket.IO
**Approval:** ❌ Not required

**Call:**
```json
{
  "id": "127",
  "name": "vetka_get_tree",
  "arguments": {
    "root_path": "/",
    "depth": 3,
    "include_content": false
  }
}
```

**Handler:** `src/mcp/tools/tree_tool.py` - Class `GetTreeTool`
**REST Alternative:** `GET /api/tree/data`

**Response Example:**
```json
{
  "jsonrpc": "2.0",
  "id": "127",
  "result": {
    "success": true,
    "tree": {
      "root": "/",
      "children": [
        {
          "name": "src",
          "type": "dir",
          "children": [...]
        }
      ]
    }
  }
}
```

---

### vetka_get_node
**Purpose:** Get details about a specific node
**Status:** ✅ Production
**Transport:** Socket.IO
**Approval:** ❌ Not required

**Call:**
```json
{
  "id": "128",
  "name": "vetka_get_node",
  "arguments": {
    "node_id": "file_or_folder_id",
    "include_stats": true,
    "include_content": false
  }
}
```

**Handler:** `src/mcp/tools/tree_tool.py` - Class `GetNodeTool`

**Response Example:**
```json
{
  "jsonrpc": "2.0",
  "id": "128",
  "result": {
    "success": true,
    "node": {
      "id": "...",
      "name": "file.py",
      "type": "file",
      "size": 1024,
      "modified": "2026-01-18T00:00:00"
    }
  }
}
```

---

### vetka_git_status
**Purpose:** Get git status
**Status:** ✅ Production
**Transport:** Socket.IO
**Approval:** ❌ Not required

**Call:**
```json
{
  "id": "129",
  "name": "vetka_git_status",
  "arguments": {
    "repo_path": "/path/to/repo"
  }
}
```

**Handler:** `src/mcp/tools/git_tool.py` - Class `GitStatusTool`

**Response Example:**
```json
{
  "jsonrpc": "2.0",
  "id": "129",
  "result": {
    "success": true,
    "status": {
      "branch": "main",
      "modified_files": 2,
      "untracked_files": 1,
      "staged_files": 0
    }
  }
}
```

---

### vetka_camera_focus
**Purpose:** Control 3D camera to focus on specific nodes
**Status:** ✅ Production
**Transport:** Socket.IO
**Approval:** ❌ Not required
**Note:** Only works with active UI session

**Call:**
```json
{
  "id": "130",
  "name": "vetka_camera_focus",
  "arguments": {
    "target": "file_or_folder_name",
    "focus_type": "single"  // or "overview"
  }
}
```

**Handler:** `src/mcp/tools/camera_tool.py` - Class `CameraControlTool`
**Frontend Event:** `camera_control` emitted to WebGL viewer

**Response Example:**
```json
{
  "jsonrpc": "2.0",
  "id": "130",
  "result": {
    "success": true,
    "message": "Camera moved to 'main.py'"
  }
}
```

---

## 2. Write Tools (Require Approval)

### vetka_edit_file
**Purpose:** Edit or create file
**Status:** ✅ Production
**Transport:** Socket.IO
**Approval:** ✅ **REQUIRED**
**Dry-run:** Default (safe)

**Call (Dry-run - Always Safe):**
```json
{
  "id": "200",
  "name": "vetka_edit_file",
  "arguments": {
    "file_path": "/path/to/file.py",
    "content": "new content here",
    "create_if_missing": true,
    "dry_run": true
  }
}
```

**Response (Dry-run):**
```json
{
  "jsonrpc": "2.0",
  "id": "200",
  "result": {
    "success": true,
    "message": "DRY RUN: Would write 50 bytes to file.py",
    "preview": "new content here"
  }
}
```

**Call (Real Write - Needs Approval):**
```json
{
  "id": "201",
  "name": "vetka_edit_file",
  "arguments": {
    "file_path": "/path/to/file.py",
    "content": "new content here",
    "create_if_missing": true,
    "dry_run": false
  }
}
```

**Response (Approval Required):**
```json
{
  "jsonrpc": "2.0",
  "id": "201",
  "result": {
    "needs_approval": true,
    "approval_id": "550e8400-e29b-41d4-a716-446655440000",
    "expires_at": "2026-01-19T01:14:00",
    "message": "This operation requires approval. Use _approval_id='550e8400-e29b-41d4-a716-446655440000' after approval."
  }
}
```

**After Approval:**
1. Call: `POST /api/approval/550e8400-e29b-41d4-a716-446655440000/approve`
2. Re-submit with approval_id:
```json
{
  "id": "202",
  "name": "vetka_edit_file",
  "arguments": {
    "file_path": "/path/to/file.py",
    "content": "new content here",
    "dry_run": false,
    "_approval_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Handler:** `src/mcp/tools/edit_file_tool.py` - Class `EditFileTool`
**REST Alternative:** `POST /api/files/save` (but still needs approval flow)

---

### vetka_git_commit
**Purpose:** Create git commit
**Status:** ✅ Production
**Transport:** Socket.IO
**Approval:** ✅ **REQUIRED**
**Dry-run:** Default (safe)

**Call (Dry-run):**
```json
{
  "id": "210",
  "name": "vetka_git_commit",
  "arguments": {
    "repo_path": "/path/to/repo",
    "message": "Fix: update auth system",
    "files": ["src/auth/login.py", "src/auth/logout.py"],
    "dry_run": true
  }
}
```

**Handler:** `src/mcp/tools/git_tool.py` - Class `GitCommitTool`

---

### vetka_create_branch
**Purpose:** Create a new folder/branch
**Status:** ✅ Production
**Transport:** Socket.IO
**Approval:** ✅ **REQUIRED**

**Call (Dry-run):**
```json
{
  "id": "220",
  "name": "vetka_create_branch",
  "arguments": {
    "parent_path": "/src",
    "branch_name": "new_module",
    "dry_run": true
  }
}
```

**Handler:** `src/mcp/tools/branch_tool.py` - Class `CreateBranchTool`

---

### vetka_run_tests
**Purpose:** Run pytest tests
**Status:** ✅ Production
**Transport:** Socket.IO
**Approval:** ✅ **REQUIRED**

**Call (Dry-run):**
```json
{
  "id": "230",
  "name": "vetka_run_tests",
  "arguments": {
    "test_path": "tests/",
    "pattern": "test_*.py",
    "dry_run": true
  }
}
```

**Handler:** `src/mcp/tools/run_tests_tool.py` - Class `RunTestsTool`

---

## 3. Intake Tools (Phase 22)

### vetka_intake_url
**Purpose:** Process URL content (YouTube, web pages)
**Status:** ✅ Production
**Transport:** Socket.IO
**Approval:** ❌ Not required

**Call:**
```json
{
  "id": "300",
  "name": "vetka_intake_url",
  "arguments": {
    "url": "https://example.com/article",
    "content_type": "web"  // or "youtube"
  }
}
```

**Handler:** `src/intake/tools.py` - Class `IntakeURLTool`

---

### vetka_list_intakes
**Purpose:** List processed intake content
**Status:** ✅ Production
**Transport:** Socket.IO
**Approval:** ❌ Not required

**Call:**
```json
{
  "id": "301",
  "name": "vetka_list_intakes",
  "arguments": {
    "limit": 10,
    "offset": 0
  }
}
```

**Handler:** `src/intake/tools.py` - Class `ListIntakesTool`

---

### vetka_get_intake
**Purpose:** Get specific intake content
**Status:** ✅ Production
**Transport:** Socket.IO
**Approval:** ❌ Not required

**Call:**
```json
{
  "id": "302",
  "name": "vetka_get_intake",
  "arguments": {
    "intake_id": "intake_id_here"
  }
}
```

**Handler:** `src/intake/tools.py` - Class `GetIntakeTool`

---

## Implementation Details

### Socket.IO Event Flow

1. **Client sends** → `tool_call` event with tool name + arguments
2. **Server receives** → `MCPServer.handle_tool_call()` in `src/mcp/mcp_server.py`
3. **Security checks:**
   - Rate limiting (60/min for API, 10/min for writes)
   - Approval check (if write operation + not dry-run)
   - Tool validation
4. **Execution** → Tool's `safe_execute()` method runs
5. **Response** → `tool_result` event with result or error
6. **Audit logging** → All calls logged to `data/mcp_audit/`

### Approval Flow

For operations requiring approval:

```
1. Submit tool with dry_run=false
   ↓
2. Server returns: needs_approval=true + approval_id
   ↓
3. POST /api/approval/{approval_id}/approve
   ↓
4. Resubmit tool with _approval_id parameter
   ↓
5. Tool executes with real changes
```

### REST Alternatives

Some tools have REST endpoints:

| Tool | REST Endpoint |
|------|---------------|
| `vetka_read_file` | `POST /api/files/read` |
| `vetka_list_files` | `GET /api/search` (via query) |
| `vetka_get_tree` | `GET /api/tree/data` |
| `vetka_search_knowledge` | `GET /api/search/semantic` |
| `vetka_camera_focus` | Socket.IO only |
| `vetka_edit_file` | `POST /api/files/save` |
| `vetka_git_*` | Socket.IO only |

---

## Configuration for Skills

When setting up MCP skills, use:

```json
{
  "name": "vetka_search",
  "type": "socket.io",
  "url": "http://localhost:5001",
  "event": "tool_call",
  "handler": "MCPServer",
  "requires_approval": false,
  "dry_run_default": false
}
```

For write operations:

```json
{
  "name": "vetka_edit_file",
  "type": "socket.io",
  "url": "http://localhost:5001",
  "event": "tool_call",
  "handler": "MCPServer",
  "requires_approval": true,
  "dry_run_default": true,
  "approval_endpoint": "POST /api/approval/{id}/approve"
}
```

---

## Error Handling

### Rate Limited
```json
{
  "jsonrpc": "2.0",
  "id": "123",
  "error": {
    "code": -32000,
    "message": "Rate limited. Retry after 60 seconds",
    "data": {"retry_after": 60}
  }
}
```

### Tool Not Found
```json
{
  "jsonrpc": "2.0",
  "id": "123",
  "error": {
    "code": -32601,
    "message": "Method not found",
    "data": "Unknown tool: vetka_invalid_tool"
  }
}
```

### Approval Required
```json
{
  "jsonrpc": "2.0",
  "id": "123",
  "error": {
    "code": -32001,
    "message": "Invalid or expired approval: approval_id_here"
  }
}
```

### Execution Error
```json
{
  "jsonrpc": "2.0",
  "id": "123",
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": "File not found: /nonexistent/file.py"
  }
}
```

---

## Testing Tools

### Using curl (REST alternatives)

```bash
# Read file
curl -X POST http://localhost:5001/api/files/read \
  -H "Content-Type: application/json" \
  -d '{"file_path": "main.py"}'

# Search semantic
curl "http://localhost:5001/api/search/semantic?query=auth"

# Get tree
curl http://localhost:5001/api/tree/data
```

### Using socket.io-client (Node.js)

```javascript
const io = require('socket.io-client');
const socket = io('http://localhost:5001');

socket.on('connect', () => {
  socket.emit('tool_call', {
    id: '123',
    name: 'vetka_search',
    arguments: { query: 'main' }
  });
});

socket.on('tool_result', (response) => {
  console.log('Tool result:', response);
});
```

---

## Production Checklist

- ✅ Port 5001 is active
- ✅ FastAPI is serving requests
- ✅ Socket.IO is connected
- ✅ Qdrant is accessible at localhost:6333
- ✅ All 15 tools are registered
- ✅ Approval system is active
- ✅ Rate limiting is enforced
- ✅ Audit logging is enabled
- ✅ 59+ REST endpoints are available
- ✅ 40+ Socket.IO events are mapped

**Status:** 🚀 **READY FOR PRODUCTION**

---

## Resources

- **Full Audit:** `MCP_AUDIT_RESULTS.md`
- **Quick Ref:** `MCP_AUDIT_QUICK_REFERENCE.md`
- **Main Server:** `main.py`
- **MCP Core:** `src/mcp/mcp_server.py`
- **Tools:** `src/mcp/tools/`
- **Routes:** `src/api/routes/`
