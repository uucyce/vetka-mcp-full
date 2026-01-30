# MCP Debug Console - Build Summary

**Created:** 2026-01-23
**Location:** `/mcp_console/`
**Status:** Complete & Ready to Use

---

## What Was Built

A **simple, standalone MCP Debug Console** for real-time monitoring of MCP requests/responses.

### Tech Stack
- **Backend:** FastAPI on port 5002 (171 lines)
- **Frontend:** React + TypeScript + Vite
- **Real-time:** Socket.IO
- **JSON Display:** react-json-view package
- **Theme:** Dark (VS Code style), monospace font

### Design Compliance
✅ Dark theme (#1a1a1a background, #e0e0e0 text)
✅ Monospace font (SF Mono, Monaco, Consolas)
✅ NO gradients, NO fancy animations
✅ Minimal: header + logs list only
✅ Accent color: #4a9eff (blue)
✅ Under 300 lines for server.py (171 lines actual)
✅ Uses existing npm packages (react-json-view)
✅ Tauri-compatible (no Electron)
✅ Separate /mcp_console/ folder (not in /src/)

---

## File Structure

```
/mcp_console/
├── server.py              # FastAPI + Socket.IO (171 lines)
├── requirements.txt       # Python dependencies (4 packages)
├── test_client.py         # Test with sample logs
├── setup.sh              # One-line setup script
├── .gitignore            # Git ignore rules
├── .env.example          # Configuration template
├── README.md             # Full documentation
├── QUICKSTART.md         # Quick start guide
├── ARCHITECTURE.md       # System architecture
└── frontend/
    ├── package.json      # Node dependencies (6 packages)
    ├── vite.config.ts    # Vite build config
    ├── tsconfig.json     # TypeScript config
    ├── tsconfig.node.json
    ├── index.html        # HTML entry point
    └── src/
        ├── main.tsx      # React entry
        ├── App.tsx       # Main component (~200 lines)
        ├── App.css       # Styles (~200 lines)
        └── index.css     # Global styles
```

**Total:** 17 files, ~670 lines of code (excluding dependencies)

---

## Features Implemented

✅ Show MCP requests (tool name, arguments)
✅ Show MCP responses (content, tokens, timing)
✅ Real-time updates via Socket.IO
✅ Save logs to `/docs/mcp_chat/`
✅ Clear logs button
✅ Collapsible JSON viewer
✅ Auto-scroll to latest log
✅ Connection status indicator
✅ Log count display
✅ Color-coded log types
✅ Timestamp display
✅ Copy-to-clipboard for JSON

---

## Quick Start

### 1. Setup (One Command)
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/mcp_console
./setup.sh
```

### 2. Run Server
```bash
python server.py
```

Open: **http://localhost:5002**

### 3. Test It
```bash
python test_client.py
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Serve React frontend |
| GET | `/api/logs` | Get all logs |
| POST | `/api/log` | Add new log entry |
| POST | `/api/clear` | Clear all logs |
| POST | `/api/save` | Save logs to file |
| GET | `/api/health` | Health check |

---

## Integration Example

```python
import requests

MCP_CONSOLE = "http://localhost:5002"

def log_mcp(log_type, tool_name, **kwargs):
    try:
        requests.post(f"{MCP_CONSOLE}/api/log",
                     json={'type': log_type, 'tool': tool_name, **kwargs},
                     timeout=1)
    except:
        pass  # Silent fail if console not running

# Usage:
log_mcp('request', 'vetka_search_semantic',
        arguments={'query': 'test', 'limit': 5})

result = do_search('test', limit=5)

log_mcp('response', 'vetka_search_semantic',
        content={'results': result},
        tokens=120,
        timing=450)
```

---

## Log Entry Schema

```typescript
interface LogEntry {
  id: number           // Auto-generated
  timestamp: string    // ISO 8601
  type: 'request' | 'response' | 'error' | 'info'
  tool?: string        // MCP tool name
  arguments?: any      // Request arguments
  content?: any        // Response content
  tokens?: number      // Token count
  timing?: number      // Execution time (ms)
  message?: string     // Error/info message
}
```

---

## Dependencies

### Python (requirements.txt)
```
fastapi==0.115.5
uvicorn[standard]==0.34.0
python-socketio==5.11.4
aiofiles==24.1.0
```

### Node (package.json)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "socket.io-client": "^4.7.2",
    "react-json-view": "^1.21.3"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.3.3",
    "vite": "^5.0.11"
  }
}
```

---

## Architecture

```
┌──────────────────┐         ┌──────────────────┐
│   MCP Tools      │         │   Web Browser    │
│                  │         │                  │
│  POST /api/log   │────────▶│  React Frontend  │
│                  │         │  + Socket.IO     │
└──────────────────┘         └────────┬─────────┘
                                      │
                                      │ WebSocket
                                      ▼
                            ┌─────────────────────┐
                            │  FastAPI (5002)     │
                            │  + Socket.IO        │
                            │  + In-Memory Store  │
                            └──────────┬──────────┘
                                       │
                                       │ Save
                                       ▼
                            ┌─────────────────────┐
                            │  /docs/mcp_chat/    │
                            │  mcp_debug_*.json   │
                            └─────────────────────┘
```

---

## Design Preview

```
┌────────────────────────────────────────────────────────────┐
│ 🔍 MCP Debug Console     ● Connected    42 logs  💾  🗑️  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  → REQUEST  vetka_search_semantic         12:34:56        │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Arguments:                                           │ │
│  │  {                                                   │ │
│  │    "query": "test spatial intelligence",            │ │
│  │    "limit": 5                                       │ │
│  │  }                                                   │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ← RESPONSE  vetka_search_semantic   120 tokens  450ms    │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Content:                                             │ │
│  │  {                                                   │ │
│  │    "results": [...]                                 │ │
│  │  }                                                   │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ✕ ERROR  vetka_read_file                  12:34:58      │
│  File not found: /nonexistent/path.py                     │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

1. **In-Memory Storage**
   - Fast access
   - Max 1000 logs (FIFO)
   - Optional save to disk

2. **Socket.IO for Real-Time**
   - No polling overhead
   - Instant updates
   - Connection status tracking

3. **React + Vite**
   - Fast development
   - Hot module reload
   - Production build optimization

4. **react-json-view Package**
   - Don't reinvent the wheel
   - Collapsible JSON
   - Copy-to-clipboard
   - Dark theme support

5. **Separate /mcp_console/ Folder**
   - Not in /src/ (clean separation)
   - Can be run independently
   - Easy to deploy/share

6. **Tauri Compatible**
   - No Electron dependencies
   - Pure React build
   - Can be embedded later

---

## Testing

Test script provided: `test_client.py`

Sends 6 sample logs:
1. Request log (semantic search)
2. Response log (with results, tokens, timing)
3. Error log (file not found)
4. Info log (server started)
5. Complex request (model call)
6. Large response (model output)

```bash
python test_client.py
```

---

## Next Steps (Optional)

### Integration with VETKA MCP
Add logging to existing MCP tools in `/src/mcp/tools/`:
- `vetka_search_semantic`
- `vetka_read_file`
- `vetka_call_model`
- etc.

### Example Integration:
```python
# Add to src/mcp/tools/search_tool.py

import requests

def log_to_console(log_type, tool_name, **kwargs):
    try:
        requests.post('http://localhost:5002/api/log',
                     json={'type': log_type, 'tool': tool_name, **kwargs},
                     timeout=1)
    except:
        pass

# In search function:
log_to_console('request', 'vetka_search_semantic', arguments=params)
result = search_qdrant(query, limit)
log_to_console('response', 'vetka_search_semantic', content=result)
```

### Future Enhancements (Not Implemented)
- [ ] Filter logs by type/tool
- [ ] Search in log content
- [ ] Export to CSV
- [ ] Log statistics dashboard
- [ ] Persistent storage (SQLite)
- [ ] Authentication (if needed)
- [ ] Multiple log streams
- [ ] Log replay/playback

---

## Summary

✅ **COMPLETE** - Fully functional MCP Debug Console
✅ **SIMPLE** - 171 lines for backend, ~670 total
✅ **FAST** - Real-time Socket.IO updates
✅ **CLEAN** - Dark theme, no clutter
✅ **READY** - Setup script, test script, docs
✅ **FLEXIBLE** - Easy to integrate with any MCP tool

**Start using it:**
```bash
cd mcp_console && ./setup.sh && python server.py
```

**View at:** http://localhost:5002
