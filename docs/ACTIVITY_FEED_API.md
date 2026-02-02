# Activity Feed API - Phase 108.4 Step 5

**Status:** ✅ COMPLETE
**Created:** 2026-02-02
**Marker:** `MARKER_108_5_ACTIVITY_FEED`

## Overview

Unified activity stream API that aggregates events from multiple sources:
- **Chat messages** (from ChatHistoryManager)
- **MCP tool calls** (from `data/mcp_audit/*.jsonl`)
- **Artifact events** (from `staging.json` + `artifacts/` directory)
- **Git commits** (from `git log`)

All activities are merged, sorted by timestamp (most recent first), and returned with pagination support.

## API Endpoints

### 1. GET /api/activity/feed

Get unified activity stream with pagination and filtering.

**Query Parameters:**
- `limit` (int, default: 50, max: 200) - Max activities to return
- `offset` (int, default: 0) - Skip first N activities
- `types` (string, optional) - Comma-separated activity types to include
  - Valid types: `chat`, `mcp`, `artifact`, `commit`
  - Example: `types=chat,mcp`

**Response:**
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
        "sender": "user",
        "agent": null,
        "model": null
      }
    },
    {
      "id": "mcp_2026-02-02T15:25:00_vetka_search",
      "type": "mcp",
      "timestamp": "2026-02-02T15:25:00Z",
      "title": "✅ MCP: vetka_search",
      "description": "Client: claude-mcp",
      "metadata": {
        "tool": "vetka_search",
        "client_id": "claude-mcp",
        "success": true,
        "duration_ms": 45.2
      }
    },
    {
      "id": "artifact_art_456",
      "type": "artifact",
      "timestamp": "2026-02-02T15:20:00Z",
      "title": "Artifact: feature_x.py",
      "description": "Status: approved",
      "metadata": {
        "artifact_id": "art_456",
        "status": "approved"
      }
    },
    {
      "id": "commit_3d329a47",
      "type": "commit",
      "timestamp": "2026-02-02T14:00:00Z",
      "title": "Phase 108.4 Step 1: Dev/QA Artifact Tools",
      "description": "By danilagulin",
      "metadata": {
        "commit_hash": "3d329a47...",
        "short_hash": "3d329a47",
        "author": "danilagulin",
        "subject": "Phase 108.4 Step 1: Dev/QA Artifact Tools"
      }
    }
  ],
  "total": 150,
  "has_more": true
}
```

**Examples:**
```bash
# Get last 20 activities (all types)
curl http://localhost:5001/api/activity/feed?limit=20

# Get only chat and MCP activities
curl http://localhost:5001/api/activity/feed?types=chat,mcp

# Get activities with pagination (offset 50, limit 25)
curl http://localhost:5001/api/activity/feed?limit=25&offset=50
```

### 2. GET /api/activity/stats

Get activity statistics (counts by type, sources).

**Response:**
```json
{
  "total": 150,
  "by_type": {
    "chat": 45,
    "mcp": 78,
    "artifact": 12,
    "commit": 15
  },
  "sources": {
    "chat_history_manager": 45,
    "mcp_audit_logs": 78,
    "disk_artifacts": 12,
    "git_log": 15
  }
}
```

**Example:**
```bash
curl http://localhost:5001/api/activity/stats
```

### 3. POST /api/activity/emit

Emit `activity_update` Socket.IO event for real-time updates.

**Internal endpoint** - called by services to broadcast new activities to connected clients.

**Request Body:**
```json
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
```

**Response:**
```json
{
  "success": true,
  "message": "Activity update emitted",
  "activity_id": "chat_msg_123"
}
```

## Socket.IO Events

### Event: `activity_update`

Emitted when new activity occurs in the system. Frontend can listen to this event for real-time feed updates.

**Payload:**
```javascript
{
  id: "chat_msg_123",
  type: "chat",
  timestamp: "2026-02-02T15:30:00Z",
  title: "Message in Dev Chat",
  description: "User sent message...",
  metadata: { ... }
}
```

**Frontend Usage:**
```javascript
socket.on('activity_update', (activity) => {
  console.log('New activity:', activity);
  // Add to feed UI
  activityFeed.addActivity(activity);
});
```

## Service Integration

### ActivityEmitter Service

Helper service for emitting activity updates from other services.

**Location:** `src/services/activity_emitter.py`

**Usage:**

```python
from src.services.activity_emitter import emit_activity_update

# Generic activity
await emit_activity_update(
    socketio=sio,
    activity_type="chat",
    title="New message in Dev Chat",
    description="User sent a message",
    metadata={"chat_id": "abc123", "sender": "user"}
)
```

**Helper Functions:**

```python
from src.services.activity_emitter import (
    emit_chat_activity,
    emit_mcp_activity,
    emit_artifact_activity,
    emit_git_activity
)

# Chat activity
await emit_chat_activity(
    socketio=sio,
    chat_id="abc123",
    chat_name="Dev Chat",
    sender="user",
    content="Hello world!",
    message_id="msg_123"
)

# MCP activity
await emit_mcp_activity(
    socketio=sio,
    tool_name="vetka_search",
    client_id="claude-mcp",
    success=True,
    duration_ms=45.2
)

# Artifact activity
await emit_artifact_activity(
    socketio=sio,
    artifact_id="art_456",
    status="approved",
    artifact_name="feature_x.py"
)

# Git activity
await emit_git_activity(
    socketio=sio,
    commit_hash="3d329a47...",
    author="danilagulin",
    subject="Phase 108.4 Step 1",
    timestamp="2026-02-02T14:00:00Z"
)
```

## Data Sources

### 1. Chat Messages
- **Source:** `ChatHistoryManager` (`src/chat/chat_history_manager.py`)
- **Format:** Recent chats with last 3 messages per chat
- **Timestamp:** Message `timestamp` field

### 2. MCP Tool Calls
- **Source:** `data/mcp_audit/*.jsonl` files
- **Format:** One JSON line per tool call
- **Timestamp:** `timestamp` field
- **Fields:** `tool`, `client_id`, `success`, `duration_ms`, `error`

### 3. Artifact Events
- **Source 1:** `data/staging.json` (staged artifacts)
- **Source 2:** `artifacts/` directory (disk artifacts)
- **Timestamp:** File modification time for disk artifacts
- **Fields:** `artifact_id`, `status`, `file_name`, `size_bytes`

### 4. Git Commits
- **Source:** `git log` command
- **Format:** Parsed from git log output
- **Timestamp:** Commit timestamp (ISO 8601)
- **Fields:** `commit_hash`, `author`, `subject`

## Testing

### Test Script

Run the test script to verify all endpoints:

```bash
python test_activity_feed.py
```

**Test Cases:**
1. Get activity feed (all types)
2. Get activity feed (filtered by type)
3. Get activity stats
4. Pagination test

### Manual Testing

```bash
# Start VETKA server
python main.py

# In another terminal, test endpoints
curl http://localhost:5001/api/activity/feed?limit=10
curl http://localhost:5001/api/activity/stats
curl http://localhost:5001/api/activity/feed?types=chat,mcp&limit=5
```

## Implementation Details

### File Structure

```
src/api/routes/activity_routes.py    # API endpoints
src/services/activity_emitter.py     # Helper service for emitting events
test_activity_feed.py                # Test script
docs/ACTIVITY_FEED_API.md            # This documentation
```

### Router Registration

Located in `src/api/routes/__init__.py`:

```python
from .activity_routes import router as activity_router

def get_all_routers() -> List[APIRouter]:
    return [
        # ... other routers
        activity_router,  # /api/activity/* (Phase 108.4 Step 5)
    ]
```

### Activity Aggregation

Activities are merged and sorted by timestamp (most recent first):

1. Fetch from all sources (chat, MCP, artifacts, git)
2. Combine into single list
3. Sort by ISO 8601 timestamp (descending)
4. Apply pagination (offset + limit)
5. Return paginated results

### Performance Considerations

- **Caching:** Consider implementing Redis cache for frequent queries
- **Limits:** Each source fetches `limit * 2` to ensure enough activities after merge
- **Pagination:** Frontend should use offset-based pagination for large feeds
- **Real-time:** Socket.IO events provide instant updates without polling

## Future Enhancements

### Phase 108.5+

1. **Activity Filtering:**
   - Filter by date range
   - Filter by user/agent
   - Filter by chat/project

2. **Activity Search:**
   - Full-text search across activities
   - Semantic search integration

3. **Activity Grouping:**
   - Group related activities (e.g., MCP calls for same task)
   - Thread view for chat messages

4. **Activity Reactions:**
   - Allow users to react to activities
   - Track activity engagement

5. **Activity Export:**
   - Export activity feed as JSON/CSV
   - Activity report generation

## Related Documentation

- **Phase 108.4 Step 1:** Dev/QA Artifact Tools + Approval UI
- **Phase 108.3:** Real-time chat nodes + artifact scanning in 3D tree
- **Chat History API:** `src/api/routes/chat_history_routes.py`
- **MCP Audit Logs:** `data/mcp_audit/`
- **Artifact Service:** `src/services/disk_artifact_service.py`

---

**Status:** ✅ Production Ready
**Next Steps:** Frontend integration + Socket.IO event handling
