# H6 Scout: MCP Mention Flow - Sequence Diagrams

## Sequence 1: Mention Detection and Notification

```
User                        Socket.IO              Group Handler          Debug Routes
  |                            |                        |                      |
  |---> "group_message" ------->|                        |                      |
  |     content:                |                        |                      |
  |     "@claude_code fix bug"  |                        |                      |
  |                             |                        |                      |
  |                             |---> handle_group_message() [line 532]        |
  |                             |     (async handler)                          |
  |                             |                        |                      |
  |                             |     [store message]    |                      |
  |                             |                        |                      |
  |                             |     [detect @mentions] |                      |
  |                             |     regex extract:     |                      |
  |                             |     mentions = ["claude_code"]               |
  |                             |                        |                      |
  |                             |---> notify_mcp_agents()|                      |
  |                             |     (lines 98-217)     |                      |
  |                             |                        |                      |
  |                             |                        |---> EMIT mcp_mention--->|
  |                             |                        |     event [line 163]   |
  |                             |                        |                        |
  |                             |                        |---> STORE in ---------->|
  |                             |                        |     team_messages      |
  |                             |                        |     buffer             |
  |                             |                        |     [lines 178-217]    |
  |                             |                        |                        |
  |<----- DONE ----------------<|<----- DONE -----------<|                        |
  |

[Note: mcp_mention event emitted to namespace "/" but no active listener yet]
```

---

## Sequence 2: MCP Agent Polling Loop

```
Claude Code                Debug Routes         In-Memory Buffer
  |                           |                      |
  |--- Poll Request ---------->|                      |
  |    GET /api/debug/mcp/     |                      |
  |    mentions/claude_code    |                      |
  |                            |                      |
  |                            |---> QUERY BUFFER --->|
  |                            |     filter:          |
  |                            |     - to == "claude_code"
  |                            |     - context.type == "group_mention"
  |                            |     - read == false
  |                            |                      |
  |                            |<---- RETURN MATCHES-<|
  |                            |      [array of msgs] |
  |                            |                      |
  |<--- Response (JSON) ------<|                      |
  |    {                       |                      |
  |      mentions: [           |                      |
  |        {                   |                      |
  |          id: "mcp_...",    |                      |
  |          sender: "user",   |                      |
  |          message: "...",   |                      |
  |          context: {        |                      |
  |            group_id: "...",|                      |
  |            type: "group_..."
  |          },                |                      |
  |          read: false       |                      |
  |        }                   |                      |
  |      ]                     |                      |
  |    }                       |                      |
  |                            |                      |
  |[Process mention locally]   |                      |
  |                            |                      |
  |--- Poll with mark_read=T ->|                      |
  |                            |---> UPDATE BUFFER ->|
  |                            |     Mark read=true   |
  |                            |                      |
  |                            |<---- ACK -----------<|
  |                            |                      |
  |[Wait 5 seconds]            |                      |
  |                            |                      |
  |--- Poll again (repeat) ---->                     |
  |
```

---

## Sequence 3: MCP Agent Response to Group

```
Claude Code          Debug Routes         Group Handler         Socket.IO        Clients
  |                     |                      |                    |              |
  |--- POST Send ------->|                      |                    |              |
  |     /mcp/groups/     |                      |                    |              |
  |     {group_id}/send  |                      |                    |              |
  |     {                |                      |                    |              |
  |       agent_id: "...",
  |       content: "...",|                      |                    |              |
  |       type: "response"|                      |                    |              |
  |     }                |                      |                    |              |
  |                      |                      |                    |              |
  |                      |---> send_group_message_from_mcp() [line 1154]          |
  |                      |                      |                    |              |
  |                      |---> Store message -->|                    |              |
  |                      |     in group        |                    |              |
  |                      |                      |                    |              |
  |                      |---> Call agents ------>|                  |              |
  |                      |     select_responding_|                  |              |
  |                      |     agents()           |                  |              |
  |                      |                        |                  |              |
  |                      |<----- Agent response -<|                  |              |
  |                      |     (if any)           |                  |              |
  |                      |                        |                  |              |
  |                      |---> Emit Socket events-|---> broadcast -->|---> update ->|
  |                      |     group_message      |    group_        |    chat UI   |
  |                      |     group_stream_end   |    {group_id}    |              |
  |                      |                        |                  |              |
  |<----- ACK ----------<|                        |                  |              |
  |     {                |                        |                  |              |
  |       success: true, |                        |                  |              |
  |       message_id: ...
  |     }                |                        |                  |              |
  |

[Agents may see MCP message and respond, creating chain]
```

---

## Sequence 4: Complete Flow from Mention to Response

```
Timeline:
---------

T=0.0s   User types in group: "@claude_code refactor this function"
         └─> group_message event sent to Socket.IO

T=0.1s   Server receives event
         └─> Extracts mention "claude_code"
         └─> Stores in team_messages buffer
         └─> Emits mcp_mention event (not used currently)

T=0.2s   Response complete to user UI

T=5.0s   Claude Code polling timer fires
         └─> GET /api/debug/mcp/mentions/claude_code
         └─> Receives mention with context
         └─> Sets read=True automatically

T=5.2s   Claude Code processes request
         └─> Analyzes code
         └─> Prepares response

T=8.5s   Claude Code sends response
         └─> POST /api/debug/mcp/groups/{group_id}/send
         └─> {"agent_id": "claude_code", "content": "Here's the refactored..."}

T=8.6s   Server receives response
         └─> Stores in group messages
         └─> Calls select_responding_agents()
         └─> Emits Socket.IO events

T=8.7s   Group agents (Architect, QA) see MCP response
         └─> May choose to respond

T=8.8s   User sees response in chat
         └─> Chat UI updates in real-time
         └─> Shows "Claude Code" as sender

T=10.0s  Architect sends follow-up
         └─> group_message event

T=15.0s  Claude Code polls again
         └─> May receive Architect's follow-up
         └─> Creates conversation chain
```

---

## Sequence 5: In-Memory Buffer State

```
TEAM_MESSAGES BUFFER STATE
===========================

Initially: []

After User sends "@claude_code refactor":
[
  {
    id: "mcp_msg123_claude_code",
    timestamp: 1707300000.123,
    sender: "user",
    to: "claude_code",
    message: "refactor this function",
    context: {
      group_id: "542444da-fcb1-4e26-ac00-f414e2c43591",
      type: "group_mention"
    },
    pending: true,
    read: false
  }
]

After Claude Code polls with mark_read=true:
[
  {
    ...
    read: true,        // <-- MARKED READ
    pending: false     // <-- MARKED NOT PENDING
  }
]

After Claude Code sends response:
[
  {
    id: "mcp_msg123_claude_code",
    ...
    read: true,
    pending: false
  },
  {
    id: "mcp_resp456_claude_code",
    timestamp: 1707300008.456,
    sender: "claude_code",
    to: "user",
    message: "Here's the refactored...",
    context: {
      type: "mcp_response",
      group_id: "542444da-fcb1-4e26-ac00-f414e2c43591"
    },
    read: false
  }
]

[Buffer max 100 entries - circular, oldest dropped when exceeded]
```

---

## Data Flow: From Request to Response

```
REQUEST PATH:
=============

1. User message input
   └─> Websocket: group_message
   └─> Handler: handle_group_message() [line 532]
   └─> Extract mentions: ["claude_code"]
   └─> Call: notify_mcp_agents() [line 671]
   └─> Result: Message stored in team_messages + mcp_mention event emitted

2. Claude Code polling
   └─> HTTP GET: /api/debug/mcp/mentions/claude_code
   └─> Backend: Query team_messages buffer
   └─> Filter: to=="claude_code" AND context.type=="group_mention"
   └─> Return: JSON array of mentions
   └─> Mark: read=true, pending=false (if mark_read=true)

3. Claude Code processing
   └─> Local processing (model inference, code analysis, etc.)
   └─> Prepare response text

RESPONSE PATH:
==============

1. Claude Code sending response
   └─> HTTP POST: /api/debug/mcp/groups/{group_id}/send
   └─> Body: {agent_id: "claude_code", content: "...", message_type: "response"}
   └─> Handler: send_group_message_from_mcp() [line 1154]

2. Server processing response
   └─> Store message in group
   └─> Call select_responding_agents()
   └─> If agents match: call orchestrator.call_agent()
   └─> Generate agent responses

3. Real-time broadcast
   └─> Emit: group_stream_end [line 1401]
   └─> Emit: group_message [line 1414]
   └─> Broadcast to room: group_{group_id}
   └─> Result: All clients receive update via Socket.IO

4. User sees response
   └─> Frontend receives Socket.IO events
   └─> Updates chat UI
   └─> Displays message from "Claude Code"
```

---

## API Endpoints Summary

```
POLLING ENDPOINTS:
==================

1. Get mentions (Recommended for MCP agents)
   GET /api/debug/mcp/mentions/{agent_id}
   └─> Filters: to==agent_id AND context.type=="group_mention"
   └─> Response: Array of mention objects
   └─> Query params: limit, unread_only, mark_read

2. Get pending messages (General purpose)
   GET /api/debug/mcp/pending/{agent_id}
   └─> Filters: to==agent_id AND pending==true AND read==false
   └─> Response: Array of pending message objects
   └─> Query params: limit, mark_read

3. Get all team messages (Unfiltered)
   GET /api/debug/team-messages
   └─> Returns: All messages in buffer
   └─> Query params: limit, unread_only, sender_filter, to_filter, mark_read

SENDING ENDPOINTS:
==================

1. Send MCP message to group
   POST /api/debug/mcp/groups/{group_id}/send
   └─> Body: {agent_id, content, message_type}
   └─> Response: {success, message_id, timestamp}
   └─> Effect: Triggers agent responses, broadcasts via Socket.IO

2. Send team message (direct agent-to-agent)
   POST /api/debug/team-message
   └─> Body: {message, sender, to, priority, context}
   └─> Response: {success, message_id}
   └─> Effect: Stores in team_messages, emits Socket.IO event

3. MCP agent respond endpoint
   POST /api/debug/mcp/respond/{agent_id}
   └─> Body: {message_id, response, context}
   └─> Response: {success, message_id}
   └─> Effect: Stores response, emits Socket.IO event

UTILITY ENDPOINTS:
==================

1. List groups for MCP agents
   GET /api/debug/mcp/groups
   └─> Response: Array of group objects

2. Get group messages for MCP agents
   GET /api/debug/mcp/groups/{group_id}/messages
   └─> Query params: limit, since_id
   └─> Response: Array of group messages

3. List team agents
   GET /api/debug/team-agents
   └─> Response: KNOWN_AGENTS dictionary with metadata
```

---

## Key Decision Points

### Where do mentions go?

```
@claude_code message
        │
        ├─> Socket.IO event (mcp_mention) ──> [Not actively listened to]
        │                                      [For future Socket.IO push]
        │
        └─> In-memory buffer (team_messages) ─> [Polling mechanism used]
                                                [MCP agents poll regularly]
```

### How does Claude Code know to respond?

```
Option 1: POLLING (Current implementation)
  Claude Code timer fires every 5 seconds
  └─> Calls GET /api/debug/mcp/mentions/claude_code
  └─> Gets mention from buffer
  └─> Processes request
  └─> Sends response

Option 2: SOCKET.IO PUSH (Future potential)
  Server emits mcp_mention event
  └─> Browser extension/client listens
  └─> Immediately processes
  └─> Would be faster, less frequent polling
```

### Why polling instead of WebSocket push?

```
✅ Polling PROS:
  - Simple REST API (no complex Socket.IO client needed)
  - Works with any HTTP client
  - Self-recovery (failed request just retry next poll)
  - No state to maintain between polls
  - Easy for external tools to integrate

❌ Polling CONS:
  - Latency (5 second delay typical)
  - More network requests
  - Slight load on server (repeated queries)

💡 Best for MCP: Polling makes sense because
  - MCP agents are external tools
  - 5 second latency is acceptable
  - No need for real-time push notifications
  - Clean separation: REST API interface only
```

---

## State Transitions

```
Message Lifecycle:
==================

1. CREATED
   pending=true, read=false
   └─> Just stored from notify_mcp_agents()

2. POLL DETECTED
   pending=true, read=false
   └─> Agent calls GET /api/debug/mcp/mentions with mark_read=true
   └─> Server marks: read=true, pending=false
   └─> State: PROCESSED

3. PROCESSED
   pending=false, read=true
   └─> Agent won't see this again
   └─> Kept in buffer for reference

4. BUFFER FULL
   [100 messages max]
   └─> If > 100: Oldest messages dropped
   └─> team_messages[:] = team_messages[-100:]

5. FORGOTTEN
   └─> Server restart = buffer cleared
   └─> No persistent storage of mentions

Typical Flow:
  CREATED (0s) → POLL DETECTED (5s) → PROCESSED (5.1s) → FORGOTTEN (∞)
```

---

## Error Handling

```
IF mention detection fails:
  └─> Exception caught, logged
  └─> Message stored anyway (safe)
  └─> Agent doesn't know about mention
  └─> Agent should poll anyway (poll gives all messages)

IF buffer storage fails:
  └─> Logged in try/except [lines 214-217]
  └─> notify_mcp_agents continues
  └─> Mention stored only in Socket.IO event (lost if agent offline)

IF agent doesn't poll:
  └─> Mention sits in buffer
  └─> If 100+ mentions: older ones dropped
  └─> Agent misses mention forever

IF send_group_message fails:
  └─> Caught in try/except [lines 1183-1495]
  └─> Error logged
  └─> Returns success=false to MCP agent
  └─> Message not stored, not broadcast

IF group doesn't exist:
  └─> Returns {error: "Group not found"}
  └─> HTTP 400 status
  └─> MCP agent sees error, can retry different group
```

---

## Performance Characteristics

```
LATENCY:
  User sends message → Socket.IO event:     ~10ms
  Event processed → Stored in buffer:       ~50ms
  Agent polls:                              ~5000ms (interval)
  Agent processes:                          ~1000ms (typical)
  Agent sends response:                     ~100ms
  Response broadcast:                       ~10ms
  ─────────────────────────────────────────────────
  TOTAL:                                    ~6170ms (typical)

THROUGHPUT:
  Buffer size:                              100 messages max
  Poll rate (agent):                        1 request per 5 seconds
  Broadcast rate:                           1 event per response
  Server capacity:                          ~1000 req/sec (FastAPI)

STORAGE:
  Per message:                              ~500 bytes (JSON)
  Buffer capacity:                          100 messages = ~50KB
  Memory usage:                             Negligible for server
```

---

## Integration Checklist for MCP Agents

```
✅ Connect to VETKA chat group
   - Base URL: http://localhost:5001
   - Group ID: 542444da-fcb1-4e26-ac00-f414e2c43591
   - Agent ID: claude_code (or browser_haiku)

✅ Implement polling loop
   - Endpoint: GET /api/debug/mcp/mentions/{agent_id}
   - Interval: 5 seconds recommended
   - mark_read=true to auto-acknowledge

✅ Process mentions
   - Extract context (group_id, group_name)
   - Read message content
   - Perform task (code analysis, browser control, etc.)

✅ Send response
   - Endpoint: POST /api/debug/mcp/groups/{group_id}/send
   - Include: agent_id, content, message_type
   - Handle: success/error response

✅ Handle errors
   - Network errors: retry logic
   - Buffer full: just skip
   - Agent not found: check group first

✅ Optional: Listen for Socket.IO events
   - Event: mcp_mention (namespace "/")
   - Benefit: Real-time notification instead of polling
   - Current: Not actively used, future enhancement
```

---

## Debug Commands

```bash
# Check if server is running
curl http://localhost:5001/api/debug/agent-info

# Get all agents
curl http://localhost:5001/api/debug/team-agents

# List available groups
curl http://localhost:5001/api/debug/mcp/groups

# Check for mentions (as Claude Code)
curl http://localhost:5001/api/debug/mcp/mentions/claude_code

# View all team messages
curl http://localhost:5001/api/debug/team-messages?limit=10

# Send test mention (as user)
curl -X POST http://localhost:5001/api/debug/mcp/groups/542444da-fcb1-4e26-ac00-f414e2c43591/send \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "user", "content": "@claude_code test", "message_type": "chat"}'

# Send response (as Claude Code)
curl -X POST http://localhost:5001/api/debug/mcp/groups/542444da-fcb1-4e26-ac00-f414e2c43591/send \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "claude_code", "content": "Response", "message_type": "response"}'

# Check pending messages
curl http://localhost:5001/api/debug/mcp/pending/claude_code

# View team messages (all)
curl http://localhost:5001/api/debug/team-messages
```

---

This document provides complete visibility into how @mentions flow from group chat to MCP agent execution.
