# MCP Console - Quick Start Guide

**Version:** 1.0
**Phase:** 80.41
**Date:** 2026-01-22

---

## What is MCP Console?

The MCP Debug Console displays real-time AI agent communications in VETKA. It shows every MCP tool request and response, making it easy to debug, monitor, and understand what AI agents are doing.

---

## Quick Access

### Open Console
1. **Via UI:** Click the "🤖 MCP" button in the top bar
2. **Via Console:**
   ```javascript
   window.mcpConsole.show()
   ```

### Close Console
1. **Via UI:** Click the "✖️" button in console header
2. **Via Console:**
   ```javascript
   window.mcpConsole.hide()
   ```

---

## What You'll See

### Request Section (Blue Header)
```
REQUEST | 15:30:45
Agent: mcp_bridge | Tool: vetka_search_semantic | Model: claude-opus-4
{
  "query": "authentication logic",
  "limit": 10
}
```

### Response Section (Green/Red Header)
```
RESPONSE | 15:30:46 | 127ms | 1240 tokens
{
  "count": 8,
  "results": [...]
}
```

---

## Common Actions

### Save Logs
1. Click "💾 Save"
2. Enter session ID (e.g., "debug_session")
3. File saved to: `docs/mcp_chat/mcp_console_{session}_{timestamp}.json`

### Clear Logs
1. Click "🗑️ Clear"
2. Confirm deletion
3. All logs removed (saved files remain)

### View Statistics
Look at the stats bar for:
- Requests: Total request count
- Responses: Total response count
- Tokens: Total tokens used

---

## API Quick Reference

### Log a Request (from Python)
```python
import httpx
import time

async def log_request(tool_name: str, arguments: dict):
    async with httpx.AsyncClient() as client:
        await client.post("http://localhost:5001/api/mcp-console/log", json={
            "id": f"req-{uuid.uuid4().hex[:8]}",
            "type": "request",
            "timestamp": time.time(),
            "agent": "my_agent",
            "tool": tool_name,
            "arguments": arguments
        })
```

### Log a Response (from Python)
```python
async def log_response(request_id: str, result: dict, duration_ms: float):
    async with httpx.AsyncClient() as client:
        await client.post("http://localhost:5001/api/mcp-console/log", json={
            "id": request_id.replace("req-", "res-"),
            "type": "response",
            "timestamp": time.time(),
            "tool": "vetka_search_semantic",
            "result": result,
            "duration_ms": duration_ms
        })
```

### Get History (from JavaScript)
```javascript
const response = await fetch('/api/mcp-console/history?limit=100');
const data = await response.json();
console.log('Logs:', data.logs);
```

### Save Logs (from JavaScript)
```javascript
const response = await fetch('/api/mcp-console/save', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ session_id: 'my_session' })
});
const data = await response.json();
console.log('Saved to:', data.path);
```

---

## Troubleshooting

### Console Not Showing
- Check if VETKA server is running
- Check browser console for errors
- Verify Socket.IO connection

### Logs Not Appearing
- Check if MCP bridge is sending logs
- Verify `/api/mcp-console/log` endpoint is working
- Check Socket.IO connection status

### Save Failed
- Check if `docs/mcp_chat/` directory exists
- Verify write permissions
- Check browser console for error details

---

## Advanced Usage

### Filter Logs (API)
```bash
# Get only requests
curl "http://localhost:5001/api/mcp-console/history?type_filter=request&limit=50"

# Get logs from specific agent
curl "http://localhost:5001/api/mcp-console/history?agent=haiku_b&limit=50"
```

### Clear Logs (API)
```bash
curl -X DELETE "http://localhost:5001/api/mcp-console/clear"
```

### Get Statistics (API)
```bash
curl "http://localhost:5001/api/mcp-console/stats"
```

---

## Keyboard Shortcuts

Currently, no keyboard shortcuts are implemented.

**Future enhancements:**
- `Cmd/Ctrl + Shift + M` - Toggle console
- `Cmd/Ctrl + S` - Save logs
- `Cmd/Ctrl + K` - Clear logs

---

## Best Practices

1. **Save logs regularly** - They're lost on server restart
2. **Use descriptive session IDs** - Makes finding logs easier
3. **Clear logs after debugging** - Prevents memory bloat
4. **Check statistics** - Monitor token usage and performance

---

## File Locations

- **Backend API:** `src/api/routes/mcp_console_routes.py`
- **Frontend JS:** `frontend/static/js/mcp_console.js`
- **Frontend CSS:** `frontend/static/css/mcp_console.css`
- **MCP Bridge:** `src/mcp/vetka_mcp_bridge.py`
- **Saved Logs:** `docs/mcp_chat/`

---

## Need Help?

- Read full documentation: `docs/80_ph_mcp_agents/PHASE2_SONNET_C_MCP_CONSOLE.md`
- Check Haiku B's analysis: `docs/80_ph_mcp_agents/PHASE1_HAIKU_B_MCP_UI_CONTEXT.md`
- Check browser console for errors
- Verify VETKA server is running on port 5001

---

**Quick Start Complete!**

Now you can monitor and debug AI agent communications in real-time.
