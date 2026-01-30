---
name: vetka-mcp
description: VETKA MCP Server integration for AI agents. Provides 15 tools for file search, semantic knowledge search, directory navigation, file editing, git operations, test running, 3D camera control, and content intake (YouTube/web). Use when user mentions "VETKA", "Ветка" (in context of knowledge system, not tree branches), or needs to search/edit/commit files through VETKA system. Server runs on localhost:5001.
---

# VETKA MCP Integration

**Vision:** "VETKA — workshop for agents, spacesuit for humans"

## Quick Start

```bash
# Check health
curl http://localhost:5001/api/health

# MCP tools use Socket.IO (not REST)
# Use socket.io-client or Python socketio library

# REST alternatives for common operations:
curl http://localhost:5001/api/search/semantic?query=...
curl -X POST http://localhost:5001/api/files/read -d '{"file_path": "main.py"}'
curl http://localhost:5001/api/tree/data
```

## Transport Protocol

**MCP tools use Socket.IO, not REST!**

### Socket.IO Connection
```javascript
const io = require('socket.io-client');
const socket = io('http://localhost:5001');

// Send tool call
socket.emit('tool_call', {
  id: 'unique-id',
  name: 'vetka_search',
  arguments: { query: 'search term' }
});

// Receive result
socket.on('tool_result', (response) => {
  console.log(response.result);
});
```

### Python Socket.IO
```python
import socketio

sio = socketio.Client()
sio.connect('http://localhost:5001')

sio.emit('tool_call', {
    'id': '123',
    'name': 'vetka_search',
    'arguments': {'query': 'search term'}
})

@sio.on('tool_result')
def on_result(data):
    print(data)
```

## Tools Overview (15 total)

### Read-Only (Safe)
| Tool | Purpose | Transport |
|------|---------|-----------|
| `vetka_search` | Search files by name/content | Socket.IO |
| `vetka_search_knowledge` | Semantic search (Qdrant) | Socket.IO / REST* |
| `vetka_get_tree` | Folder/file hierarchy | Socket.IO / REST* |
| `vetka_get_node` | File/folder details | Socket.IO |
| `vetka_list_files` | Directory contents | Socket.IO |
| `vetka_read_file` | Read file content | Socket.IO / REST* |
| `vetka_git_status` | Git status | Socket.IO |
| `vetka_camera_focus` | Control 3D camera | Socket.IO only |

*REST alternatives available (see references/tools.md)

### Write Operations (Approval Required)
| Tool | Purpose | Transport |
|------|---------|-----------|
| `vetka_edit_file` | Edit/create file | Socket.IO |
| `vetka_git_commit` | Git commit | Socket.IO |
| `vetka_create_branch` | Create folder | Socket.IO |
| `vetka_run_tests` | Run pytest | Socket.IO |

### Intake Tools
| Tool | Purpose | Transport |
|------|---------|-----------|
| `vetka_intake_url` | Process YouTube/web | Socket.IO |
| `vetka_list_intakes` | List processed content | Socket.IO |
| `vetka_get_intake` | Get intake by ID | Socket.IO |

## Camera Control

Navigate 3D visualization with agents. Supports EN/RU commands:
- `"focus on X"`, `"show me X"`, `"zoom to X"`
- `"подлети к X"`, `"покажи X"`, `"перейди к X"`

```json
{"name": "vetka_camera_focus", "arguments": {"target": "main.py", "zoom": "close", "highlight": true}}
```

## Safety & Limits

- **Rate limiting:** 60 API calls/min, 10 write ops/min
- **Approval system:** Write operations require explicit approval
- **Dry-run default:** Write tools default to dry_run=true
- **Audit log:** All calls logged to `data/mcp_audit/`
- **Backups:** Edit operations backup to `.vetka_backups/`
- **No `..` in paths** — path traversal blocked

## Response Format

```json
{"success": true, "result": {...}, "error": null}
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Server not responding | `curl http://localhost:5001/api/health` |
| Check available tools | See `/docs` endpoint (FastAPI auto-docs) |
| Rate limited | Wait 60 seconds, check `retry_after` in error |
| Approval required | Use approval flow (see references/tools.md) |

## Detailed Reference

See [references/tools.md](references/tools.md) for all tool parameters and examples.
