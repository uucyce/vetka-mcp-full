# Activity Feed API - Quick Reference Card

**Phase 108.4 Step 5** | **Marker:** `MARKER_108_5_ACTIVITY_FEED`

---

## API Endpoints (3 total)

### 1. GET /api/activity/feed
```bash
# Get last 20 activities
curl http://localhost:5001/api/activity/feed?limit=20

# Filter by type
curl http://localhost:5001/api/activity/feed?types=chat,mcp

# Pagination
curl http://localhost:5001/api/activity/feed?limit=25&offset=50
```

### 2. GET /api/activity/stats
```bash
curl http://localhost:5001/api/activity/stats
```

### 3. POST /api/activity/emit
```bash
curl -X POST http://localhost:5001/api/activity/emit \
  -H "Content-Type: application/json" \
  -d '{"id":"test_123","type":"chat","timestamp":"2026-02-02T15:30:00Z","title":"Test","description":"Test activity","metadata":{}}'
```

---

## Activity Types

| Type | Source | Example |
|------|--------|---------|
| `chat` | ChatHistoryManager | "Message in Dev Chat" |
| `mcp` | `data/mcp_audit/*.jsonl` | "✅ MCP: vetka_search" |
| `artifact` | `staging.json` + `artifacts/` | "Artifact: feature_x.py" |
| `commit` | `git log` | "Phase 108.4 Step 1" |

---

## Socket.IO Event

**Event:** `activity_update`

**Frontend:**
```javascript
socket.on('activity_update', (activity) => {
  console.log('New activity:', activity.type, activity.title);
  activityFeed.addActivity(activity);
});
```

---

## Service Integration

### Emit Chat Activity
```python
from src.services.activity_emitter import emit_chat_activity

await emit_chat_activity(
    socketio=sio,
    chat_id="abc123",
    chat_name="Dev Chat",
    sender="user",
    content="Hello!",
    message_id="msg_123"
)
```

### Emit MCP Activity
```python
from src.services.activity_emitter import emit_mcp_activity

await emit_mcp_activity(
    socketio=sio,
    tool_name="vetka_search",
    client_id="claude-mcp",
    success=True,
    duration_ms=45.2
)
```

### Emit Artifact Activity
```python
from src.services.activity_emitter import emit_artifact_activity

await emit_artifact_activity(
    socketio=sio,
    artifact_id="art_456",
    status="approved",
    artifact_name="feature_x.py"
)
```

### Emit Git Activity
```python
from src.services.activity_emitter import emit_git_activity

await emit_git_activity(
    socketio=sio,
    commit_hash="3d329a47...",
    author="danilagulin",
    subject="Phase 108.4 Step 1"
)
```

---

## Response Format

```json
{
  "activities": [
    {
      "id": "chat_msg_123",
      "type": "chat",
      "timestamp": "2026-02-02T15:30:00Z",
      "title": "Message in Dev Chat",
      "description": "User sent message...",
      "metadata": {
        "chat_id": "abc123",
        "sender": "user"
      }
    }
  ],
  "total": 150,
  "has_more": true
}
```

---

## Testing

```bash
# Run test script
python test_activity_feed.py

# Manual tests
curl http://localhost:5001/api/activity/feed?limit=10
curl http://localhost:5001/api/activity/stats
```

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/api/routes/activity_routes.py` | 513 | API endpoints |
| `src/services/activity_emitter.py` | 232 | Helper service |
| `test_activity_feed.py` | 107 | Test script |
| `docs/ACTIVITY_FEED_API.md` | 388 | Full docs |
| `examples/activity_feed_integration.py` | 341 | Integration examples |
| **TOTAL** | **1,581** | |

---

## Data Sources (4 total)

1. **Chat:** `ChatHistoryManager` → Recent messages
2. **MCP:** `data/mcp_audit/*.jsonl` → Tool calls
3. **Artifacts:** `staging.json` + `artifacts/` → Artifact events
4. **Git:** `git log` → Commits

---

## Key Features

- ✅ Unified activity stream (4 sources)
- ✅ Real-time Socket.IO updates
- ✅ Pagination (limit, offset)
- ✅ Type filtering (comma-separated)
- ✅ Activity stats endpoint
- ✅ Helper service for easy integration
- ✅ Pydantic models (type safety)
- ✅ Error handling (graceful degradation)

---

**Status:** ✅ Production Ready | **Next:** Frontend integration
