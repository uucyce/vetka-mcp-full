# Activity Feed API - Complete Index

**Phase 108.4 Step 5** | **Marker:** `MARKER_108_5_ACTIVITY_FEED` | **Status:** ✅ Complete

---

## Quick Links

- **Quick Reference:** [ACTIVITY_FEED_QUICK_REF.md](./ACTIVITY_FEED_QUICK_REF.md)
- **Full API Documentation:** [ACTIVITY_FEED_API.md](./ACTIVITY_FEED_API.md)
- **Implementation Summary:** [PHASE_108_4_STEP_5_SUMMARY.md](./PHASE_108_4_STEP_5_SUMMARY.md)
- **Registration Status:** [../ACTIVITY_FEED_REGISTRATION.md](../ACTIVITY_FEED_REGISTRATION.md)

---

## What is Activity Feed API?

A unified REST API that aggregates events from multiple sources (chat messages, MCP tool calls, artifact events, git commits) into a single real-time activity stream with pagination and filtering support.

**Key Benefits:**
- Single source of truth for all system activities
- Real-time Socket.IO updates
- Easy frontend integration
- Consistent activity format
- Scalable architecture

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Activity Feed API                        │
│                 /api/activity/feed                          │
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │    Chat      │ │     MCP      │ │  Artifacts   │ ...
    │ (History Mgr)│ │ (Audit Logs) │ │ (Staging +   │
    │              │ │              │ │  Disk)       │
    └──────────────┘ └──────────────┘ └──────────────┘
            │               │               │
            └───────────────┼───────────────┘
                            ▼
                    ┌──────────────┐
                    │   Merge &    │
                    │   Sort by    │
                    │  Timestamp   │
                    └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │  Paginate    │
                    │  (offset +   │
                    │   limit)     │
                    └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   Return     │
                    │  Activities  │
                    └──────────────┘
```

---

## File Structure

### Core Implementation
```
src/api/routes/
├── activity_routes.py         ← Main API endpoints (513 lines)
└── __init__.py               ← Router registration (MODIFIED)

src/services/
└── activity_emitter.py        ← Helper service (232 lines)
```

### Testing
```
test_activity_feed.py          ← Test script (107 lines)
```

### Documentation
```
docs/
├── ACTIVITY_FEED_INDEX.md          ← This file (overview)
├── ACTIVITY_FEED_API.md            ← Full API docs (388 lines)
├── ACTIVITY_FEED_QUICK_REF.md      ← Quick reference (167 lines)
└── PHASE_108_4_STEP_5_SUMMARY.md   ← Implementation summary (368 lines)
```

### Examples
```
examples/
└── activity_feed_integration.py    ← Integration examples (341 lines)
```

### Registration
```
ACTIVITY_FEED_REGISTRATION.md  ← Registration status (174 lines)
```

---

## API Endpoints Summary

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/activity/feed` | Get unified activity stream |
| `GET` | `/api/activity/stats` | Get activity statistics |
| `POST` | `/api/activity/emit` | Emit activity update (internal) |

**Total Endpoints:** 3

---

## Activity Types

| Type | Source | Count Field |
|------|--------|-------------|
| `chat` | ChatHistoryManager | Recent chats × 3 messages |
| `mcp` | `data/mcp_audit/*.jsonl` | Last 5 audit files |
| `artifact` | `staging.json` + `artifacts/` | All staged + disk |
| `commit` | `git log` | Recent commits |

---

## Socket.IO Integration

**Event:** `activity_update`

**Payload:**
```javascript
{
  id: "chat_msg_123",
  type: "chat",
  timestamp: "2026-02-02T15:30:00Z",
  title: "Message in Dev Chat",
  description: "User sent message...",
  metadata: { chat_id: "abc123", sender: "user" }
}
```

---

## Quick Start

### 1. Start Server
```bash
python main.py
# Should see: "[API] Registered 21 FastAPI routers"
```

### 2. Test Endpoints
```bash
# Get activities
curl http://localhost:5001/api/activity/feed?limit=10

# Get stats
curl http://localhost:5001/api/activity/stats

# Run tests
python test_activity_feed.py
```

### 3. Check API Docs
```bash
open http://localhost:5001/docs
# Look for "/api/activity" section
```

---

## Integration Examples

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

**More examples:** [examples/activity_feed_integration.py](../examples/activity_feed_integration.py)

---

## Documentation Map

### For API Users (Frontend Developers)
1. **Start here:** [ACTIVITY_FEED_QUICK_REF.md](./ACTIVITY_FEED_QUICK_REF.md)
2. **Full details:** [ACTIVITY_FEED_API.md](./ACTIVITY_FEED_API.md)

### For Backend Developers (Integration)
1. **Start here:** [examples/activity_feed_integration.py](../examples/activity_feed_integration.py)
2. **Implementation:** [PHASE_108_4_STEP_5_SUMMARY.md](./PHASE_108_4_STEP_5_SUMMARY.md)

### For DevOps (Deployment)
1. **Start here:** [ACTIVITY_FEED_REGISTRATION.md](../ACTIVITY_FEED_REGISTRATION.md)
2. **Testing:** [../test_activity_feed.py](../test_activity_feed.py)

---

## Statistics

| Metric | Count |
|--------|-------|
| **Files Created** | 8 |
| **Files Modified** | 1 |
| **Total Lines** | 1,581+ |
| **API Endpoints** | 3 |
| **Activity Types** | 4 |
| **Data Sources** | 4 |
| **Test Cases** | 4 |
| **Documentation Pages** | 5 |

---

## Key Features

- ✅ Unified activity stream (4 sources)
- ✅ Real-time Socket.IO updates
- ✅ Pagination (limit, offset)
- ✅ Type filtering
- ✅ Activity statistics
- ✅ Helper service for easy integration
- ✅ Pydantic models (type safety)
- ✅ Error handling
- ✅ Comprehensive documentation
- ✅ Test script
- ✅ Integration examples

---

## Next Steps

### Phase 108.5: Frontend Integration
- [ ] Create ActivityFeed React component
- [ ] Subscribe to `activity_update` Socket.IO event
- [ ] Implement infinite scroll pagination
- [ ] Add type filter UI

### Phase 108.6: Service Integration
- [ ] ChatHistoryManager → emit chat activities
- [ ] MCP Server → emit tool call activities
- [ ] Approval Service → emit artifact activities
- [ ] Git operations → emit commit activities

### Phase 108.7: Performance & Features
- [ ] Redis caching for frequent queries
- [ ] Activity search (full-text + semantic)
- [ ] Activity grouping (threads)
- [ ] Activity reactions (emoji)
- [ ] Activity export (JSON/CSV)

---

## Support & Troubleshooting

### Documentation
- **Quick Ref:** [ACTIVITY_FEED_QUICK_REF.md](./ACTIVITY_FEED_QUICK_REF.md)
- **Full API:** [ACTIVITY_FEED_API.md](./ACTIVITY_FEED_API.md)

### Testing
```bash
python test_activity_feed.py
```

### Debugging
```bash
# Check router registration
grep -n "activity_router" src/api/routes/__init__.py

# Check markers
grep -rn "MARKER_108_5_ACTIVITY_FEED" src/

# Check server logs
tail -f logs/vetka.log
```

---

## Related Phases

- **Phase 108.4 Step 1:** Dev/QA Artifact Tools + Approval UI
- **Phase 108.3:** Real-time chat nodes + artifact scanning
- **Phase 108.2:** Chat Visualization in 3D VETKA Tree
- **Phase 107:** Git Auto-Push + Cleanup
- **Phase 103:** Artifact Staging + Chat Persistence

---

## Markers

**Primary Marker:** `MARKER_108_5_ACTIVITY_FEED`

**Locations:**
- `src/api/routes/activity_routes.py` (lines 10, 370, 440)
- `src/services/activity_emitter.py` (lines 12, 47)
- `src/api/routes/__init__.py` (line 50)

---

**Status:** ✅ Complete and Production Ready

**Last Updated:** 2026-02-02

**Author:** Claude Code (Sonnet 4.5)

**Review:** Ready for code review and frontend integration
