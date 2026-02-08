# H6 Scout: Complete Code Walkthrough

## File 1: group_message_handler.py - Mention Detection

### Location: Lines 661-679

```python
# Phase 80.13: Check for MCP agent @mentions and notify them
# MCP agents (browser_haiku, claude_code) are not in participants
# but can be @mentioned and notified via socket events
mentions = (
    user_message.mentions
    if hasattr(user_message, "mentions")
    # MARKER_108_ROUTING_FIX_4: Support hyphenated model names
    else re.findall(r"@([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)", content)
)
if mentions:
    await notify_mcp_agents(
        sio=sio,
        group_id=group_id,
        group_name=group.get("name", "Unknown Group"),
        sender_id=sender_id,
        content=content,
        mentions=mentions,
        message_id=user_message.id,
    )
```

**What happens:**
1. Check if user_message object has mentions attribute
2. If not, use regex to extract @mentions from content
3. Regex supports: `@word`, `@word/subword`, `@word:tag`
4. Call notify_mcp_agents() with list of extracted mentions

**Regex breakdown:**
```
@([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)
 │ │           │                 │            │
 │ │           │                 │            └─ Optional :tag
 │ │           │                 └─ Optional /subword
 │ │           └─ Main agent name (word, dash, dot)
 │ └─ Capture group (returns text after @)
 └─ Literal @ symbol

Examples that match:
  @claude_code        → "claude_code"
  @gpt4              → "gpt4"
  @openai/gpt-5.2    → "openai/gpt-5.2"
  @claude:main       → "claude:main"
  @browse_haiku      → "browse_haiku"
```

---

## File 2: group_message_handler.py - notify_mcp_agents Function

### Location: Lines 98-217

#### Part A: Match mentions to registered agents (Lines 122-140)

```python
def notify_mcp_agents(
    sio,
    group_id: str,
    group_name: str,
    sender_id: str,
    content: str,
    mentions: list,
    message_id: str,
):
    """
    Phase 80.13: Notify MCP agents when they are @mentioned.
    """
    # Find which MCP agents are mentioned
    mentioned_mcp_agents = []

    for mention in mentions:
        mention_lower = mention.lower()

        # Check direct match
        if mention_lower in MCP_AGENTS:
            mentioned_mcp_agents.append(mention_lower)
            continue

        # Check aliases
        for agent_id, agent_info in MCP_AGENTS.items():
            if mention_lower in agent_info.get("aliases", []):
                mentioned_mcp_agents.append(agent_id)
                break

    if not mentioned_mcp_agents:
        return
```

**What happens:**
1. For each mention in the list:
   - Convert to lowercase
   - Check if it's a direct agent ID match
   - If not, check aliases
   - Add matched agent to mentioned_mcp_agents list
2. If no matches, return early

**Example:**
```
mentions = ["claude_code", "haiku"]

First iteration: mention = "claude_code"
  → mention_lower = "claude_code"
  → Check: "claude_code" in MCP_AGENTS? YES
  → mentioned_mcp_agents = ["claude_code"]

Second iteration: mention = "haiku"
  → mention_lower = "haiku"
  → Check: "haiku" in MCP_AGENTS? NO
  → Check aliases for "haiku"...
  → Find "browser_haiku" has alias "haiku"
  → mentioned_mcp_agents = ["claude_code", "browser_haiku"]

Result: mentioned_mcp_agents = ["claude_code", "browser_haiku"]
```

#### Part B: Build and emit Socket.IO event (Lines 147-176)

```python
# Build notification payload
notification = {
    "type": "mcp_mention",
    "group_id": group_id,
    "group_name": group_name,
    "sender_id": sender_id,
    "content": content,
    "message_id": message_id,
    "timestamp": time.time(),
    "mentioned_agents": mentioned_mcp_agents,
}

# Emit socket event for each mentioned MCP agent
for agent_id in mentioned_mcp_agents:
    agent_info = MCP_AGENTS[agent_id]

    # Emit targeted event
    await sio.emit(
        "mcp_mention",
        {
            **notification,
            "target_agent": agent_id,
            "agent_name": agent_info["name"],
            "agent_role": agent_info["role"],
        },
        namespace="/",
    )

    print(
        f"[MCP_MENTION] Notified {agent_info['name']} of @mention in {group_name}"
    )
```

**What happens:**
1. Build notification object with group context
2. For each matched agent:
   - Add target_agent, agent_name, agent_role
   - Emit "mcp_mention" Socket.IO event to root namespace "/"
   - Print log message

**Socket.IO Event Payload Example:**
```json
{
  "type": "mcp_mention",
  "group_id": "542444da-fcb1-4e26-ac00-f414e2c43591",
  "group_name": "Сугиями рабочая группа 2",
  "sender_id": "user_123",
  "content": "@claude_code please fix the bug",
  "message_id": "msg_789",
  "timestamp": 1707300000.123,
  "mentioned_agents": ["claude_code"],
  "target_agent": "claude_code",
  "agent_name": "Claude Code",
  "agent_role": "Executor"
}
```

**Note:** Socket.IO event is emitted to namespace "/" (root), not to specific MCP namespace. Currently no active listener for this event.

#### Part C: Store in team_messages buffer (Lines 178-217)

```python
# Store in team_messages buffer for API access
try:
    from src.api.routes.debug_routes import team_messages, KNOWN_AGENTS

    for agent_id in mentioned_mcp_agents:
        agent_info = MCP_AGENTS[agent_id]

        msg = {
            "id": f"mcp_{message_id}_{agent_id}",
            "timestamp": time.time(),
            "sender": sender_id,
            "sender_info": {"name": sender_id, "icon": "user", "role": "User"},
            "to": agent_id,
            "to_info": {
                "name": agent_info["name"],
                "icon": agent_info["icon"],
                "role": agent_info["role"],
            },
            "message": content,
            "priority": "normal",
            "context": {
                "group_id": group_id,
                "group_name": group_name,
                "message_id": message_id,
                "type": "group_mention",
            },
            "pending": True,
            "read": False,
        }

        team_messages.append(msg)

        # Keep buffer limited (max 100)
        if len(team_messages) > 100:
            team_messages[:] = team_messages[-100:]

except ImportError as e:
    print(f"[MCP_MENTION] Could not import debug_routes: {e}")
except Exception as e:
    print(f"[MCP_MENTION] Error storing message: {e}")
```

**What happens:**
1. Import global team_messages list from debug_routes
2. For each mentioned agent:
   - Create message object with full context
   - Set pending=True, read=False
   - Append to team_messages list
   - If list exceeds 100 items, keep only last 100 (circular buffer)

**Message Structure:**
```python
msg = {
    "id": "mcp_msg123_claude_code",     # Unique ID
    "timestamp": 1707300000.123,         # When created
    "sender": "user_id",                 # Who sent
    "sender_info": {                     # Sender metadata
        "name": "user_id",
        "icon": "user",
        "role": "User"
    },
    "to": "claude_code",                 # Target agent
    "to_info": {                         # Target metadata
        "name": "Claude Code",
        "icon": "terminal",
        "role": "Executor"
    },
    "message": "@claude_code fix bug",   # Full message
    "priority": "normal",                # Priority level
    "context": {                         # Group context
        "group_id": "542444da-...",
        "group_name": "Сугиября...",
        "message_id": "msg123",
        "type": "group_mention"          # Always "group_mention"
    },
    "pending": True,                     # Not yet processed
    "read": False                        # Not yet read by agent
}
```

**Buffer Management:**
```python
if len(team_messages) > 100:
    team_messages[:] = team_messages[-100:]
    # Keeps only last 100 messages
    # Oldest messages discarded
```

---

## File 3: debug_routes.py - Global Buffer

### Location: Lines 52-56

```python
# ============================================================
# PHASE 80.2: AGENT-TO-AGENT TEAM CHAT
# ============================================================
# Simple in-memory message buffer for browser agents to communicate
# with Claude Code (MCP) through VETKA

team_messages: List[Dict[str, Any]] = []
_max_team_messages = 100

# Alias for backward compatibility
_team_messages = team_messages
```

**What it is:**
- Global list that persists for lifetime of Python process
- Lost on server restart
- No database backing
- Simple but sufficient for 5-second polling interval

---

## File 4: debug_routes.py - Polling Endpoint

### Location: Lines 1503-1581

#### Part A: Function Definition

```python
@router.get("/mcp/mentions/{agent_id}")
async def get_mcp_mentions(
    agent_id: str,
    limit: int = Query(20, description="Number of mentions to return"),
    unread_only: bool = Query(True, description="Only return unread mentions"),
    mark_read: bool = Query(False, description="Mark returned mentions as read")
) -> Dict[str, Any]:
    """
    Phase 80.13: Get pending @mentions for an MCP agent.

    When users @mention browser_haiku or claude_code in group chat,
    the mention is stored in team_messages with context type 'group_mention'.

    This endpoint allows MCP agents to poll for mentions.
    """
    global _team_messages
```

**Route details:**
- Method: GET
- Path: /api/debug/mcp/mentions/{agent_id}
- Example: GET /api/debug/mcp/mentions/claude_code
- Query params: limit, unread_only, mark_read

#### Part B: Filter Mentions

```python
# Get messages for this agent
pending = [
    m for m in _team_messages
    if (m.get("to") == agent_id or m.get("to") == "all")
    and m.get("context", {}).get("type") == "group_mention"
]

# Sort newest first
pending = sorted(pending, key=lambda x: x.get("timestamp", 0), reverse=True)
```

**Filtering logic:**
1. From all team_messages
2. Keep messages where:
   - to == agent_id (addressed to this agent)
   - OR to == "all" (broadcast to all)
   - AND context.type == "group_mention" (is a mention)
3. Sort by timestamp descending (newest first)

**Example:**
```
team_messages = [
  {id: 1, to: "claude_code", context: {type: "group_mention"}},     ✓
  {id: 2, to: "browser_haiku", context: {type: "group_mention"}},   ✗
  {id: 3, to: "all", context: {type: "group_mention"}},             ✓
  {id: 4, to: "claude_code", context: {type: "response"}},          ✗
  {id: 5, to: "claude_code", context: {type: "group_mention"}},     ✓
]

For agent_id = "claude_code":
  Returns: [id:5, id:1, id:3] (newest first)
```

#### Part C: Apply Limits

```python
# Apply limit
mentions = mentions[:limit]

# Mark as read if requested
if mark_read and mentions:
    msg_ids = {m.get("id") for m in mentions}
    for m in _team_messages:
        if m.get("id") in msg_ids:
            m["read"] = True
            m["pending"] = False
```

**Behavior:**
1. Keep only first 'limit' mentions
2. If mark_read=True:
   - Find all message IDs returned
   - Find those messages in buffer
   - Set read=True, pending=False
   - In-place modification (affects buffer)

**Important:** mark_read modifies the global buffer! Next poll will not return these messages.

#### Part D: Return Response

```python
agent_info = KNOWN_AGENTS.get(agent_id, {"name": agent_id})

return {
    "agent": agent_id,
    "agent_name": agent_info.get("name", agent_id),
    "total_unread": total_unread,
    "returned": len(mentions),
    "mentions": mentions,
    "respond_endpoint": f"/api/debug/mcp/groups/{{group_id}}/send",
    "tip": "Use the respond_endpoint with group_id from mention context to reply"
}
```

**Response structure:**
```json
{
  "agent": "claude_code",
  "agent_name": "Claude Code",
  "total_unread": 3,
  "returned": 1,
  "mentions": [
    {
      "id": "mcp_msg123_claude_code",
      "timestamp": 1707300000.123,
      "sender": "user_id",
      "sender_info": {...},
      "to": "claude_code",
      "to_info": {...},
      "message": "@claude_code fix bug",
      "context": {
        "group_id": "542444da-...",
        "type": "group_mention"
      },
      "read": false,
      "pending": true
    }
  ],
  "respond_endpoint": "/api/debug/mcp/groups/{group_id}/send",
  "tip": "Use the respond_endpoint..."
}
```

---

## File 5: debug_routes.py - Response Endpoint

### Location: Lines 1153-1496 (send_group_message_from_mcp)

#### Part A: Receive and Store Response

```python
@router.post("/mcp/groups/{group_id}/send")
async def send_group_message_from_mcp(
    request: Request,
    group_id: str,
    body: MCPGroupMessageRequest
) -> Dict[str, Any]:
    """
    Send a message to group chat as MCP agent.
    """
    manager = get_group_chat_manager()
    group = manager._groups.get(group_id)

    if not group:
        return {"error": f"Group not found: {group_id}"}

    agent_info = KNOWN_AGENTS.get(body.agent_id, {
        "name": body.agent_id,
        "icon": "bot",
        "role": "MCP Agent"
    })

    # Format sender_id with @ prefix like other agents
    sender_id = f"@{agent_info.get('name', body.agent_id)}"

    # Send message through manager
    message = await manager.send_message(
        group_id=group_id,
        sender_id=sender_id,
        content=body.content,
        message_type=body.message_type,
        metadata={
            "mcp_agent": body.agent_id,
            "icon": agent_info.get("icon"),
            "role": agent_info.get("role")
        }
    )
```

**What happens:**
1. Get group from manager
2. Get agent info from KNOWN_AGENTS
3. Format sender_id with @ prefix (e.g., "@Claude Code")
4. Store message in group via manager
5. Include agent metadata

#### Part B: Trigger Agent Responses

```python
# Phase 80.16: Safe participant data extraction with defaults
participants_to_respond = await manager.select_responding_agents(
    content=body.content,
    participants=group.participants,
    sender_id=sender_id,
    reply_to_agent=None,
    group=group
)

print(f"[MCP_AGENT_TRIGGER] {len(participants_to_respond)} agents to respond")

if participants_to_respond:
    orchestrator = get_orchestrator()
    if not orchestrator:
        print(f"[MCP_ERROR] Orchestrator is None!")
    else:
        # Track previous outputs for chain context
        previous_outputs = {}

        # Process agents sequentially
        for participant in participants_to_respond:
            # Extract participant data
            agent_id = getattr(participant, 'agent_id', 'unknown')
            model_id = getattr(participant, 'model_id', 'auto')
            display_name = getattr(participant, 'display_name', 'Agent')
            role = getattr(participant, 'role', 'worker')

            # Map to orchestrator agent type
            agent_type_map = {
                'PM': 'PM', 'pm': 'PM',
                'Dev': 'Dev', 'dev': 'Dev',
                ...
            }
            agent_type = agent_type_map.get(display_name, 'Dev')

            # Call agent via orchestrator
            result = await asyncio.wait_for(
                orchestrator.call_agent(
                    agent_type=agent_type,
                    model_id=model_id,
                    prompt=prompt,
                    context={...}
                ),
                timeout=120.0
            )
```

**What happens:**
1. Call select_responding_agents() to determine who should respond
2. If orchestrator available:
   - For each responding agent:
     - Map role to agent type
     - Call orchestrator.call_agent()
     - Get response
     - Store in group
     - Emit Socket.IO events

#### Part C: Broadcast Response

```python
# Emit stream end with full response
if socketio:
    await socketio.emit('group_stream_end', {
        'id': msg_id,
        'group_id': group_id,
        'agent_id': agent_id,
        'full_message': response_text,
        'metadata': {
            'model': model_id,
            'agent_type': agent_type
        }
    }, room=f'group_{group_id}')

# Broadcast agent response
if agent_message and socketio:
    await socketio.emit('group_message', agent_message.to_dict(), room=f'group_{group_id}')
```

**Socket.IO Events:**
1. `group_stream_end`: Full response with metadata
2. `group_message`: Complete message object
3. Both broadcast to room `group_{group_id}`
4. All connected clients receive update in real-time

**Result:** Chat UI updates, user sees response from Claude Code and any group agent responses.

---

## Complete Call Stack Example

```
USER SENDS: "@claude_code fix the bug"
  │
  ├─ Socket.IO Event: "group_message"
  │  └─> handle_group_message() [line 532]
  │
  ├─ Extract mentions [line 664-669]
  │  └─ regex.findall() → ["claude_code"]
  │
  ├─ notify_mcp_agents() [line 671]
  │  ├─ Match mentions to MCP_AGENTS [line 122-140]
  │  │  └─ "claude_code" → mentioned_mcp_agents = ["claude_code"]
  │  │
  │  ├─ Emit Socket.IO event [line 163]
  │  │  └─ await sio.emit("mcp_mention", {...}, namespace="/")
  │  │
  │  └─ Store in buffer [line 208]
  │     └─ team_messages.append({...})
  │
  ├─ return (handle_group_message complete)
  │
  ├─ [5 second wait...]
  │
  ├─ CLAUDE CODE POLLS
  │  └─ GET /api/debug/mcp/mentions/claude_code?mark_read=true
  │     │
  │     ├─ get_mcp_mentions() [line 1503]
  │     ├─ Filter team_messages [line 1539-1543]
  │     ├─ Sort by timestamp [line 1550]
  │     ├─ Mark as read [line 1556-1561]
  │     └─ Return JSON with mention
  │
  ├─ CLAUDE CODE PROCESSES
  │  └─ Local processing (model inference, etc.)
  │
  ├─ CLAUDE CODE RESPONDS
  │  └─ POST /api/debug/mcp/groups/{group_id}/send
  │     │
  │     ├─ send_group_message_from_mcp() [line 1154]
  │     ├─ Store message in group [line 1201]
  │     ├─ Call select_responding_agents() [line 1266]
  │     ├─ If agents respond:
  │     │  ├─ Call orchestrator.call_agent() [line 1362]
  │     │  ├─ Store agent responses [line 1391]
  │     │  └─ Emit Socket.IO events [line 1401]
  │     │
  │     ├─ Emit group_message event [line 1232]
  │     └─ Emit group_stream_end event [line 1246]
  │
  └─ USER SEES RESPONSE
     └─ Chat UI receives Socket.IO events
        └─ Updates display with "Claude Code" response
```

---

## Memory State During Flow

```
T=0.0s - User sends "@claude_code fix bug"

team_messages = []

T=0.1s - Message received and processed

team_messages = [
  {
    id: "mcp_msg1_claude_code",
    to: "claude_code",
    context: {type: "group_mention"},
    pending: true,
    read: false
  }
]

T=5.0s - Claude Code polls

// GET /api/debug/mcp/mentions/claude_code?mark_read=true

Query filters:
  - to == "claude_code" ✓
  - context.type == "group_mention" ✓

Returns message to Claude Code
Updates buffer: read=true, pending=false

team_messages = [
  {
    id: "mcp_msg1_claude_code",
    to: "claude_code",
    context: {type: "group_mention"},
    pending: false,     // CHANGED
    read: true          // CHANGED
  }
]

T=8.5s - Claude Code sends response

// POST /api/debug/mcp/groups/{group_id}/send

team_messages = [
  {old message, read=true},
  {
    id: "mcp_resp1_claude_code",
    to: "user",
    message: "Here's the fix...",
    context: {type: "mcp_response"},
    pending: true,
    read: false
  }
]

T=10.0s - Next poll cycle

Claude Code polls again for new mentions
Buffer now has response message (but it's type="mcp_response", not "group_mention")
Claude Code filter won't match response message
No mentions returned

team_messages state unchanged
```

---

## Key Design Decisions Explained

### 1. Why Polling Instead of Push?

**Polling:**
- Simple HTTP GET requests
- No connection state needed
- Self-healing (failed request retries next poll)
- Easy for external tools
- Works through firewalls/NAT

**Push:**
- Real-time notification
- Lower latency
- Requires WebSocket connection
- More complex state management
- Harder for external tools

**Current choice:** Polling because MCP agents are external tools needing simple HTTP API.

### 2. Why In-Memory Buffer?

**In-Memory:**
- Fast (no database)
- Simple implementation
- Good for 5-second polling
- Lost on restart (acceptable)

**Persistent:**
- Survives restarts
- Better for long polling
- More complex
- Overkill for mention routing

**Current choice:** In-memory buffer is sufficient for real-time mention delivery.

### 3. Why Circular Buffer (Max 100)?

**100 message limit:**
- Prevent unbounded memory growth
- Typical group has <5 active agents
- 5 second polling means <20 unread at once
- Old messages discarded automatically

**If buffer overflows:**
- Oldest message dropped
- New message added
- Agent never knows about dropped message
- Acceptable tradeoff for simplicity

### 4. Why Socket.IO Event Not Used?

**mcp_mention Socket.IO event is emitted but:**
- No active listener in MCP code
- Would require WebSocket client in agent
- Polling simpler and works with any HTTP client
- Socket.IO event kept for future enhancement

---

## Error Handling Paths

```
SCENARIO 1: Mention detection fails
  notify_mcp_agents() called with mentions=[]
  └─ Early return (line 139)
  └─ Message stored but no notification
  └─ Agent won't see it in polling

SCENARIO 2: Buffer storage fails
  Exception caught [lines 214-217]
  └─ Logged to console
  └─ notify_mcp_agents continues
  └─ Agent won't see mention in buffer
  └─ But Socket.IO event was emitted

SCENARIO 3: Polling endpoint fails
  HTTP 400 if agent_id not in KNOWN_AGENTS [lines 1532-1536]
  └─ Agent gets error response
  └─ Agent should retry/check KNOWN_AGENTS

SCENARIO 4: Buffer overflow
  > 100 messages in buffer
  └─ Oldest message(s) discarded
  └─ Agent never knows it existed
  └─ Simple but lossy

SCENARIO 5: Send response fails
  Group not found [line 1188]
  └─ Returns {error: "Group not found"}
  └─ HTTP 400
  └─ Agent knows to retry/check group_id

SCENARIO 6: Orchestrator not available
  orchestrator == None [lines 1279-1285]
  └─ Message stored in group
  └─ No agents called
  └─ Socket.IO events emitted
  └─ Graceful degradation
```

---

This walkthrough explains every step of the mention flow at the code level.
