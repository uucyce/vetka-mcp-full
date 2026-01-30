# VETKA MCP Tools Reference

**Version:** Phase 22
**Date:** 2025-12-30

## Overview

VETKA exposes 15 MCP tools that any AI agent can use via REST API or MCP protocol.

## REST API Endpoints

```
POST /api/mcp/call     - Execute any tool
GET  /api/mcp/tools    - List all tools with schemas
```

## Available Tools

### Read-Only Tools (Safe)

#### 1. vetka_search
Search files by name or content.
```json
{
  "name": "vetka_search",
  "arguments": {
    "query": "camera",
    "type": "filename|content|all",
    "limit": 20
  }
}
```

#### 2. vetka_search_knowledge
Semantic search using embeddings (Qdrant).
```json
{
  "name": "vetka_search_knowledge",
  "arguments": {
    "query": "how does camera control work",
    "limit": 10
  }
}
```

#### 3. vetka_get_tree
Get folder/file hierarchy.
```json
{
  "name": "vetka_get_tree",
  "arguments": {
    "path": "src/agents",
    "depth": 3
  }
}
```

#### 4. vetka_get_node
Get details about specific node.
```json
{
  "name": "vetka_get_node",
  "arguments": {
    "path": "src/agents/tools.py"
  }
}
```

#### 5. vetka_list_files
List directory contents.
```json
{
  "name": "vetka_list_files",
  "arguments": {
    "path": "src/mcp/tools",
    "pattern": "*.py"
  }
}
```

#### 6. vetka_read_file
Read file content.
```json
{
  "name": "vetka_read_file",
  "arguments": {
    "path": "main.py",
    "start_line": 1,
    "end_line": 100
  }
}
```

#### 7. vetka_git_status
Get git status.
```json
{
  "name": "vetka_git_status",
  "arguments": {}
}
```

#### 8. vetka_camera_focus
Control 3D camera to show user specific nodes.
```json
{
  "name": "vetka_camera_focus",
  "arguments": {
    "target": "src/agents/tools.py",
    "zoom": "close",
    "highlight": true,
    "animate": true
  }
}
```

### Write Operations (Require Approval)

#### 9. vetka_create_branch
Create a new folder.
```json
{
  "name": "vetka_create_branch",
  "arguments": {
    "path": "src/new_feature",
    "dry_run": true
  }
}
```

#### 10. vetka_edit_file
Edit or create file.
```json
{
  "name": "vetka_edit_file",
  "arguments": {
    "path": "src/new_file.py",
    "content": "# New file content",
    "dry_run": true
  }
}
```

#### 11. vetka_git_commit
Create git commit.
```json
{
  "name": "vetka_git_commit",
  "arguments": {
    "message": "feat: add new feature",
    "files": ["src/new_file.py"],
    "dry_run": true
  }
}
```

#### 12. vetka_run_tests
Run pytest tests.
```json
{
  "name": "vetka_run_tests",
  "arguments": {
    "path": "tests/",
    "pattern": "test_*.py"
  }
}
```

### Intake Tools

#### 13. vetka_intake_url
Process URL content (YouTube, web).
```json
{
  "name": "vetka_intake_url",
  "arguments": {
    "url": "https://youtube.com/watch?v=...",
    "type": "youtube|webpage"
  }
}
```

#### 14. vetka_list_intakes
List processed content.
```json
{
  "name": "vetka_list_intakes",
  "arguments": {}
}
```

#### 15. vetka_get_intake
Get intake content.
```json
{
  "name": "vetka_get_intake",
  "arguments": {
    "id": "intake_123"
  }
}
```

## Usage Examples

### cURL
```bash
# Search for files
curl -X POST http://localhost:5001/api/mcp/call \
  -H "Content-Type: application/json" \
  -d '{"name": "vetka_search", "arguments": {"query": "camera"}}'

# Move camera
curl -X POST http://localhost:5001/api/mcp/call \
  -H "Content-Type: application/json" \
  -d '{"name": "vetka_camera_focus", "arguments": {"target": "main.py"}}'

# List all tools
curl http://localhost:5001/api/mcp/tools
```

### Python
```python
import requests

def vetka_tool(name, **args):
    return requests.post(
        "http://localhost:5001/api/mcp/call",
        json={"name": name, "arguments": args}
    ).json()

# Search
result = vetka_tool("vetka_search", query="camera")

# Focus camera
vetka_tool("vetka_camera_focus", target="main.py", zoom="close")
```

### Claude Desktop (MCP)
Tools are automatically available when VETKA MCP server is configured.

## Security

- **Rate Limiting**: 100 API calls/minute, 10 write ops/minute
- **Dry Run**: Write operations default to `dry_run: true`
- **Audit Log**: All tool calls logged to `data/mcp_audit/`
- **Approval**: Write operations require user approval

## Response Format

All tools return:
```json
{
  "success": true|false,
  "result": {...},
  "error": "error message if failed"
}
```

---

*VETKA MCP Tools - AI agents navigating and modifying codebases*
