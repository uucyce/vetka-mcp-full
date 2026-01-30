# VETKA MCP Tools Reference

## Read-Only Tools

### vetka_search
Search files by name or content.
```json
{"name": "vetka_search", "arguments": {"query": "camera", "type": "filename|content|all", "limit": 20}}
```

### vetka_search_knowledge
Semantic search using Qdrant embeddings.
```json
{"name": "vetka_search_knowledge", "arguments": {"query": "how does camera control work", "limit": 10}}
```

### vetka_list_files
List directory contents with pattern.
```json
{"name": "vetka_list_files", "arguments": {"path": "src/mcp/tools", "pattern": "*.py"}}
```

### vetka_read_file
Read file content with optional line range.
```json
{"name": "vetka_read_file", "arguments": {"path": "main.py", "start_line": 1, "end_line": 100}}
```

### vetka_get_tree
Get folder/file hierarchy.
```json
{"name": "vetka_get_tree", "arguments": {"path": "src/agents", "depth": 3}}
```

### vetka_get_node
Get details about specific node.
```json
{"name": "vetka_get_node", "arguments": {"path": "src/agents/tools.py"}}
```

### vetka_git_status
Get git status.
```json
{"name": "vetka_git_status", "arguments": {}}
```

### vetka_camera_focus
Control 3D camera to show user specific nodes.
```json
{"name": "vetka_camera_focus", "arguments": {"target": "src/agents/tools.py", "zoom": "close", "highlight": true, "animate": true}}
```

| Parameter | Type | Default | Options |
|-----------|------|---------|---------|
| target | string | required | File path or "overview" |
| zoom | enum | "medium" | "close", "medium", "far" |
| highlight | bool | true | Highlight target node |
| animate | bool | true | Smooth camera animation |

## Write Tools (dry_run=true default)

### vetka_edit_file
Edit or create file. Always preview first.
```json
{"name": "vetka_edit_file", "arguments": {"path": "src/new_file.py", "content": "# New content", "dry_run": true}}
```

### vetka_create_branch
Create a new folder.
```json
{"name": "vetka_create_branch", "arguments": {"path": "src/new_feature", "dry_run": true}}
```

### vetka_git_commit
Create git commit.
```json
{"name": "vetka_git_commit", "arguments": {"message": "feat: add new feature", "files": ["src/new_file.py"], "dry_run": true}}
```

### vetka_run_tests
Run pytest tests.
```json
{"name": "vetka_run_tests", "arguments": {"path": "tests/", "pattern": "test_*.py"}}
```

## Intake Tools

### vetka_intake_url
Process URL content (YouTube transcripts, webpages).
```json
{"name": "vetka_intake_url", "arguments": {"url": "https://youtube.com/watch?v=...", "type": "youtube|webpage"}}
```

### vetka_list_intakes
List all processed content.
```json
{"name": "vetka_list_intakes", "arguments": {}}
```

### vetka_get_intake
Get intake content by ID.
```json
{"name": "vetka_get_intake", "arguments": {"id": "intake_123"}}
```

## Python Client

```python
import socketio

# Socket.IO client (primary method)
sio = socketio.Client()
sio.connect('http://localhost:5001')

def vetka_tool(name, **args):
    """Call MCP tool via Socket.IO"""
    import uuid
    call_id = str(uuid.uuid4())

    result = {}

    @sio.on('tool_result')
    def handle_result(data):
        if data.get('id') == call_id:
            result['data'] = data

    sio.emit('tool_call', {
        'id': call_id,
        'name': name,
        'arguments': args
    })

    # Wait for result (simplified)
    import time
    time.sleep(1)
    return result.get('data', {})

# REST alternatives for some tools
import requests

def vetka_search_semantic(query):
    """REST alternative for semantic search"""
    return requests.get(
        f"http://localhost:5001/api/search/semantic",
        params={"query": query}
    ).json()

def vetka_read_file(path):
    """REST alternative for file read"""
    return requests.post(
        "http://localhost:5001/api/files/read",
        json={"file_path": path}
    ).json()

def vetka_get_tree():
    """REST alternative for tree data"""
    return requests.get(
        "http://localhost:5001/api/tree/data"
    ).json()
```

## Approval Flow (Write Operations)

Write operations (`vetka_edit_file`, `vetka_git_commit`, etc.) require approval:

### Step 1: Submit with dry_run=false
```json
{
  "id": "123",
  "name": "vetka_edit_file",
  "arguments": {
    "path": "file.py",
    "content": "new content",
    "dry_run": false
  }
}
```

### Step 2: Receive approval_id
```json
{
  "needs_approval": true,
  "approval_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "This operation requires approval"
}
```

### Step 3: Approve via REST
```bash
curl -X POST http://localhost:5001/api/approval/550e8400-e29b-41d4-a716-446655440000/approve
```

### Step 4: Re-submit with approval_id
```json
{
  "id": "124",
  "name": "vetka_edit_file",
  "arguments": {
    "path": "file.py",
    "content": "new content",
    "dry_run": false,
    "_approval_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Step 5: Tool executes
```json
{
  "success": true,
  "result": {"bytes_written": 123}
}
```

## REST Alternatives

Some tools have REST endpoints (no Socket.IO needed):

| Tool | REST Endpoint | Method |
|------|---------------|--------|
| `vetka_read_file` | `/api/files/read` | POST |
| `vetka_search_knowledge` | `/api/search/semantic?query=...` | GET |
| `vetka_get_tree` | `/api/tree/data` | GET |
| `vetka_edit_file` | `/api/files/save` | POST |

### Examples:
```bash
# Read file
curl -X POST http://localhost:5001/api/files/read \
  -H "Content-Type: application/json" \
  -d '{"file_path": "main.py"}'

# Semantic search
curl "http://localhost:5001/api/search/semantic?query=authentication"

# Get tree
curl http://localhost:5001/api/tree/data

# Health check
curl http://localhost:5001/api/health
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Server not responding | `curl http://localhost:5001/api/health` |
| Check available tools | See `/docs` endpoint (FastAPI auto-docs) |
| Permission denied | Check path within project root, no `..` |
| Rate limited | Wait 60 seconds, check `retry_after` in error |
| Approval required | Use approval flow (see above) |
