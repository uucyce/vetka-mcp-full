# H6 Scout Report Summary

**Task:** Investigate how @mentions route from group chat to MCP tool execution
**Status:** COMPLETE
**Date:** 2026-02-07

---

## What Was Discovered

The VETKA system uses a **polling-based mention routing architecture**:

1. User @mentions MCP agent in group chat (e.g., `@claude_code`)
2. System detects mention via regex and stores it in in-memory buffer
3. MCP agent polls REST API every 5 seconds for mentions
4. MCP agent processes mention and responds via REST API
5. Response broadcast to group via Socket.IO in real-time

**Key Finding:** No WebSocket push mechanism for mentions. MCP agents must implement polling.

---

## Documents Created

### 1. **H6_MCP_MENTION_ROUTING_FLOW.md** (Complete Specification)
**What:** Full architectural documentation with code references and markers
**Contains:**
- Architecture diagram
- Key markers (H6_MENTION_DETECT_LINE, H6_MCP_MENTION_EVENT, etc.)
- Complete API endpoint documentation
- Socket.IO event details
- Message structure and metadata
- MCP agent configuration
- Testing procedures
- Implementation examples

**Best For:** Understanding the complete system design

### 2. **H6_MENTION_FLOW_SEQUENCE.md** (Visual Sequence Diagrams)
**What:** ASCII sequence diagrams showing message flow over time
**Contains:**
- 5 detailed sequence diagrams
- Data flow visualization
- Memory state transitions
- API endpoint summary
- Timeline example
- Integration checklist
- Debug commands

**Best For:** Visual learners and implementers

### 3. **H6_QUICK_REFERENCE.md** (Cheat Sheet)
**What:** Quick lookup guide for developers
**Contains:**
- 5-second summary
- Key marker locations
- 6-step flow overview
- API quick start examples
- Message structure template
- Known MCP agents
- Polling patterns (Python & JavaScript)
- Debugging checklist
- Common issues and solutions

**Best For:** Developers implementing MCP agents

### 4. **H6_CODE_WALKTHROUGH.md** (Line-by-Line Analysis)
**What:** In-depth code analysis with examples
**Contains:**
- Mention detection code (lines 661-679)
- notify_mcp_agents() function (lines 98-217)
- Global buffer definition (lines 52-56)
- Polling endpoint implementation (lines 1503-1581)
- Response endpoint implementation (lines 1153-1496)
- Complete call stack example
- Memory state evolution
- Design decision rationale
- Error handling paths

**Best For:** Code review and deep understanding

---

## Key Markers Identified

| Marker | Location | Purpose |
|--------|----------|---------|
| **H6_MENTION_DETECT_LINE** | group_message_handler.py:661-679 | Where @mentions extracted from messages |
| **H6_MCP_MENTION_EVENT** | group_message_handler.py:158-176 | Where `mcp_mention` Socket.IO event emitted |
| **H6_TEAM_MESSAGES_DICT** | debug_routes.py:52-56, 178-217 | Global in-memory message buffer |
| **H6_POLLING_ENDPOINT** | debug_routes.py:1503-1581 | Main polling endpoint for MCP agents |
| **H6_ROUTING_FLOW** | Both files | Complete end-to-end mention routing |

---

## The Complete Flow (30-Second Version)

```
User: @claude_code fix the bug
  ↓
Socket.IO: group_message event
  ↓
Regex detect: mentions = ["claude_code"]
  ↓
notify_mcp_agents():
  - Emit "mcp_mention" Socket.IO event (namespace="/")
  - Store in team_messages buffer with: {to: "claude_code", pending: true, read: false}
  ↓
Claude Code polls (every 5s):
  GET /api/debug/mcp/mentions/claude_code?mark_read=true
  ↓
Claude Code receives mention with context:
  {id, sender, message, context: {group_id, type: "group_mention"}}
  ↓
Claude Code processes and responds:
  POST /api/debug/mcp/groups/{group_id}/send
  {agent_id: "claude_code", content: "Fixed!", message_type: "response"}
  ↓
Server broadcasts response:
  Emit group_message + group_stream_end via Socket.IO
  ↓
User sees response in chat UI (real-time)
```

---

## Critical Code Locations

```
src/api/handlers/group_message_handler.py
  ├─ Line 532: handle_group_message() - entry point
  ├─ Line 664-669: Mention detection (regex extraction)
  ├─ Line 671: Call notify_mcp_agents()
  ├─ Lines 80-95: MCP_AGENTS dict definition
  ├─ Lines 98-217: notify_mcp_agents() function
  │   ├─ Lines 122-140: Agent matching
  │   ├─ Lines 147-176: Socket.IO emit
  │   └─ Lines 178-217: Buffer storage
  └─ Lines 1191-1250: Agent response chain trigger

src/api/routes/debug_routes.py
  ├─ Lines 52-56: team_messages buffer definition
  ├─ Lines 61-108: KNOWN_AGENTS registry
  ├─ Lines 1503-1581: GET /api/debug/mcp/mentions/{agent_id}
  └─ Lines 1153-1496: POST /api/debug/mcp/groups/{group_id}/send
```

---

## API Endpoints Reference

### For MCP Agents (Polling)

```
GET /api/debug/mcp/mentions/{agent_id}
  └─ Returns: Pending @mentions for this agent
  └─ Params: limit=20, unread_only=true, mark_read=true
  └─ Response: {agent, mentions: [...], total_unread, ...}
```

### For MCP Agents (Responding)

```
POST /api/debug/mcp/groups/{group_id}/send
  └─ Sends message to group as MCP agent
  └─ Body: {agent_id, content, message_type}
  └─ Response: {success, message_id, timestamp}
  └─ Effect: Triggers agent responses, broadcasts via Socket.IO
```

### For Debugging

```
GET /api/debug/team-messages
  └─ Returns all team messages (unfiltered)

GET /api/debug/team-agents
  └─ Returns list of known agents

GET /api/debug/agent-info
  └─ Returns API documentation
```

---

## Architecture Characteristics

### ✅ Strengths
- **Simple:** Polling is straightforward to implement
- **Robust:** No connection state to maintain
- **Universal:** Works with any HTTP client
- **Firewall-friendly:** No incoming connections needed
- **Stateless:** Easy to scale horizontally

### ⚠️ Limitations
- **Latency:** 5-second delay typical
- **In-memory:** Lost on server restart
- **Max 100 messages:** Buffer overflow drops oldest
- **No persistence:** No historical record
- **No real-time:** Must poll to detect mentions

### 💡 Optimal For
- External MCP agents
- 5+ second latency tolerance
- Occasional mention frequency
- Simple HTTP-only integration

---

## Integration Checklist

**For Claude Code or other MCP agents:**

- [ ] Implement polling loop: `GET /api/debug/mcp/mentions/{agent_id}`
- [ ] Poll every 5 seconds (or less frequently)
- [ ] Use `mark_read=true` to acknowledge mentions
- [ ] Extract `group_id` from mention context
- [ ] Process mention task
- [ ] Implement response: `POST /api/debug/mcp/groups/{group_id}/send`
- [ ] Include: `{agent_id, content, message_type}`
- [ ] Handle errors: network retries, missing group, etc.
- [ ] Log polling activity for debugging

---

## Known Issues & Gotchas

1. **mcp_mention Socket.IO event is emitted but not used**
   - Event sent to namespace "/" (root)
   - No active listener in MCP code
   - Kept for future enhancement
   - Current: Use polling API instead

2. **Buffer is in-memory only**
   - Lost on server restart
   - Max 100 messages
   - Oldest dropped on overflow
   - Acceptable for current use case

3. **Polling interval trade-off**
   - 5 seconds: Good latency/load balance
   - Shorter: More responsive but more load
   - Longer: Less responsive, less load
   - No dynamic adjustment

4. **Group context must be preserved**
   - Response must include group_id from mention
   - Without it: message routing fails
   - Always extract from mention context

---

## Future Enhancements

1. **WebSocket push for real-time notification**
   - Use existing `mcp_mention` event
   - Implement listener in MCP client
   - Eliminates polling latency

2. **Persistent message store**
   - Add database backing
   - Survive server restarts
   - Historical audit trail

3. **Smart buffer management**
   - Per-agent message queue
   - Configurable limits
   - Automatic cleanup

4. **Priority queue**
   - Urgent mentions get priority
   - FIFO ordering for same priority
   - Agent can choose processing order

---

## Testing

### Manual Test Flow

```bash
# 1. Trigger mention from user
curl -X POST http://localhost:5001/api/debug/mcp/groups/542444da-fcb1-4e26-ac00-f414e2c43591/send \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "user", "content": "@claude_code test", "message_type": "chat"}'

# 2. Poll as Claude Code
curl http://localhost:5001/api/debug/mcp/mentions/claude_code

# 3. Verify mention in response
# Should see: mentions: [{id: "mcp_...", to: "claude_code", message: "..."}]

# 4. Send response as Claude Code
curl -X POST http://localhost:5001/api/debug/mcp/groups/542444da-fcb1-4e26-ac00-f414e2c43591/send \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "claude_code", "content": "Response", "message_type": "response"}'

# 5. Verify response broadcast
# Check browser console for Socket.IO events: group_message, group_stream_end
```

---

## Files Analyzed

### Main Code
- `/src/api/handlers/group_message_handler.py` (1297 lines)
- `/src/api/routes/debug_routes.py` (1672 lines)
- `/src/api/handlers/mcp_socket_handler.py` (179 lines)

### Configuration
- `/.claude-mcp-config.md` (306 lines)

### Total Code Reviewed
- ~3500 lines of Python
- ~300 lines of documentation
- Complete flow coverage

---

## Conclusion

**VETKA's MCP mention routing is a clean, simple polling-based architecture** that:

1. Detects @mentions via regex in group messages
2. Stores mentions in a global in-memory buffer with full context
3. Provides REST API endpoints for MCP agents to poll and respond
4. Broadcasts responses in real-time via Socket.IO
5. Creates agent chains when group agents respond to MCP messages

The architecture prioritizes simplicity and robustness over real-time latency, making it ideal for external MCP agents that need HTTP-only integration without maintaining WebSocket connections.

**All 5 H6 markers successfully identified and documented.**

---

## Document Locations

All documentation stored in:
```
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/
  ├─ H6_MCP_MENTION_ROUTING_FLOW.md    (Complete specification)
  ├─ H6_MENTION_FLOW_SEQUENCE.md       (Sequence diagrams)
  ├─ H6_QUICK_REFERENCE.md             (Quick lookup)
  ├─ H6_CODE_WALKTHROUGH.md            (Code analysis)
  └─ H6_SUMMARY.md                     (This file)
```

Each document is self-contained and cross-references the others.
