# H6 Scout: Chat-to-MCP Mention Routing Flow

**Project:** VETKA Live 03
**Phase:** 80.13 - MCP Agent @mention Routing
**Status:** ACTIVE
**Last Updated:** 2026-02-07

---

## Overview

When a user @mentions an MCP agent (like `@claude_code` or `@browser_haiku`) in a group chat, this document traces the complete flow from mention detection through to MCP execution.

**Key Finding:** VETKA uses a **polling-based architecture** rather than WebSocket push. MCP agents must periodically check for mentions via REST API.

---

## Architecture Diagram

```
USER INPUT
    ↓
    ├─ @claude_code do something
    │
    ↓
SOCKET.IO EVENT: group_message
    ↓
    ├─ handler: handle_group_message() @ line 532
    │  (group_message_handler.py)
    │
    ├─ MENTION DETECTION @ lines 664-669
    │  └─ regex: @([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)
    │  └─ extracts: mentions = ["claude_code", ...]
    │
    ↓
NOTIFY MCP AGENTS @ line 671
    ↓
    ├─ notify_mcp_agents(sio, group_id, mentions, ...)
    │  (Lines 98-217, group_message_handler.py)
    │
    ├─ FOR EACH MENTION:
    │  │
    │  ├─ EMIT SOCKET EVENT @ line 163
    │  │  └─ Event: mcp_mention
    │  │  └─ Namespace: / (root)
    │  │  └─ Data includes: group_id, content, sender_id, timestamp
    │  │
    │  └─ STORE IN TEAM_MESSAGES @ lines 178-217
    │     └─ Buffer: debug_routes.team_messages
    │     └─ Structure: JSON with id, timestamp, sender, to, message, context
    │     └─ Max 100 messages (circular buffer)
    │
    ↓
MCP AGENT POLLING (Claude Code / Browser Haiku)
    ↓
    ├─ OPTION 1: Poll via REST API (Recommended)
    │  │
    │  ├─ Endpoint: GET /api/debug/mcp/mentions/{agent_id}
    │  │  (Lines 1503-1581, debug_routes.py)
    │  │
    │  ├─ Returns: List of pending mentions with context
    │  │  └─ Filters: to == agent_id, context.type == "group_mention"
    │  │  └─ Marked as: pending=True, read=False (initially)
    │  │
    │  ├─ Agent processes mention and responds
    │  │
    │  └─ Optional: mark_read=True to mark mention as processed
    │
    ├─ OPTION 2: Socket.IO mcp_mention Event (Not Yet Fully Implemented)
    │  │
    │  ├─ Event: "mcp_mention" emitted at line 164
    │  ├─ Namespace: "/" (root)
    │  ├─ Data: Full mention context
    │  └─ NOTE: Browser extensions/tabs would need to listen for this
    │     (No active listener currently implemented)
    │
    ├─ OPTION 3: Team Messages Buffer (Direct Access)
    │  │
    │  ├─ Endpoint: GET /api/debug/team-messages
    │  │  (Lines 813-872, debug_routes.py)
    │  │
    │  ├─ Returns: All team messages (not filtered to agent)
    │  └─ Agent must filter for messages to them
    │
    └─ OPTION 4: Pending Messages Buffer
       │
       ├─ Endpoint: GET /api/debug/mcp/pending/{agent_id}
       │  (Lines 898-954, debug_routes.py)
       │
       └─ Returns: Pending messages, filters: pending=True, read=False

    ↓
MCP AGENT EXECUTION
    ↓
    ├─ Claude Code reads mention via API
    │
    ├─ Processes the task
    │
    ├─ SEND RESPONSE @ line 1153
    │  └─ Endpoint: POST /api/debug/mcp/groups/{group_id}/send
    │  └─ Sends MCP agent message to group chat
    │
    ├─ Response triggers select_responding_agents()
    │  (Lines 1266-1272, debug_routes.py)
    │
    ├─ Group agents respond to MCP message
    │  └─ Creates agent chain: MCP → Agents → User
    │
    └─ DONE

```

---

## Key Files and Markers

### H6_MENTION_DETECT_LINE
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`
**Lines:** 661-679

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

**What it does:**
- Extracts @mentions from user message using regex
- Calls `notify_mcp_agents()` if mentions found
- Supports hyphenated model names (e.g., `@openai/gpt-5.2`)

---

### H6_MCP_MENTION_EVENT
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`
**Lines:** 158-176

```python
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

**What it does:**
- Emits `mcp_mention` Socket.IO event
- Sends to root namespace "/" (not MCP-specific namespace)
- Includes agent metadata (name, role)
- **Current Status:** Event is emitted but no active listener exists in MCP code

---

### H6_TEAM_MESSAGES_DICT
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/debug_routes.py`
**Lines:** 52-56, 178-217

```python
# Global message buffer for agent-to-agent communication
team_messages: List[Dict[str, Any]] = []
_max_team_messages = 100

# In notify_mcp_agents():
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
```

**What it does:**
- Stores mentions in global in-memory buffer
- Each message has: id, timestamp, sender, to, message content, context
- Marked with `pending=True, read=False`
- Context includes group_id, group_name, message_id, type="group_mention"
- Circular buffer (max 100 messages)

**Message Structure:**
```json
{
  "id": "mcp_<message_id>_<agent_id>",
  "timestamp": 1707300000.123,
  "sender": "user_id",
  "sender_info": {
    "name": "user_id",
    "icon": "user",
    "role": "User"
  },
  "to": "claude_code",
  "to_info": {
    "name": "Claude Code",
    "icon": "terminal",
    "role": "Executor"
  },
  "message": "Full message content from group chat",
  "priority": "normal",
  "context": {
    "group_id": "542444da-fcb1-4e26-ac00-f414e2c43591",
    "group_name": "Сугиями рабочая группа 2",
    "message_id": "<original_message_id>",
    "type": "group_mention"
  },
  "pending": true,
  "read": false
}
```

---

### H6_POLLING_ENDPOINT
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/debug_routes.py`

#### Primary Endpoint: `/api/debug/mcp/mentions/{agent_id}`
**Lines:** 1503-1581

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
    """
```

**Query Parameters:**
- `limit` (default: 20) - Max mentions to return
- `unread_only` (default: True) - Only unread mentions
- `mark_read` (default: False) - Mark as processed

**Response:**
```json
{
  "agent": "claude_code",
  "agent_name": "Claude Code",
  "total_unread": 3,
  "returned": 2,
  "mentions": [
    {
      "id": "mcp_msg123_claude_code",
      "timestamp": 1707300000.123,
      "sender": "user",
      "message": "Full message content",
      "context": {
        "group_id": "542444da-fcb1-4e26-ac00-f414e2c43591",
        "group_name": "Сугиями рабочая группа 2",
        "message_id": "msg123",
        "type": "group_mention"
      },
      "read": false
    },
    ...
  ],
  "respond_endpoint": "/api/debug/mcp/groups/{group_id}/send",
  "tip": "Use the respond_endpoint with group_id from mention context to reply"
}
```

#### Secondary Endpoint: `/api/debug/mcp/pending/{agent_id}`
**Lines:** 898-954

Similar to above but filters for `pending=True, read=False`.

#### Tertiary Endpoint: `/api/debug/team-messages`
**Lines:** 813-872

Returns all team messages (not filtered by agent). Agent must parse response.

---

### H6_ROUTING_FLOW
**Complete end-to-end flow:**

1. **User sends message with @mention in group chat**
   - Message sent via Socket.IO: `group_message` event
   - Handler: `handle_group_message()` at line 532

2. **Mention detection (lines 661-679)**
   - Regex extracts @mentions: `@([\w\-\.]+...)`
   - Supports: `@claude_code`, `@browser_haiku`, `@openai/gpt-5.2`, etc.

3. **Notification phase (lines 98-217, `notify_mcp_agents()`)**
   - Matches mentions to MCP_AGENTS dict (lines 80-95)
   - Emits `mcp_mention` Socket.IO event (line 163)
   - Stores in `team_messages` buffer (lines 178-217)
   - Sets metadata: `pending=True, read=False`

4. **MCP Agent Polling (3 mechanisms)**

   **Mechanism A: Mention-specific polling** (Recommended)
   - Endpoint: `GET /api/debug/mcp/mentions/{agent_id}`
   - Filters: `to == agent_id AND context.type == "group_mention"`
   - Response includes full context and group_id

   **Mechanism B: Pending messages polling**
   - Endpoint: `GET /api/debug/mcp/pending/{agent_id}`
   - Filters: `to == agent_id AND pending == True AND read == False`
   - General-purpose, not mention-specific

   **Mechanism C: All team messages**
   - Endpoint: `GET /api/debug/team-messages`
   - Returns all messages, agent must filter
   - Less efficient but available

5. **MCP Agent Response**
   - Claude Code reads mention from API response
   - Processes the request
   - Sends response via: `POST /api/debug/mcp/groups/{group_id}/send`
   - Request body:
     ```json
     {
       "agent_id": "claude_code",
       "content": "Response message",
       "message_type": "response"
     }
     ```

6. **Agent Chain Trigger**
   - When MCP agent sends message, system calls `select_responding_agents()`
   - Group agents may respond to MCP message
   - Creates chain: User → MCP Agent → Group Agents → User

7. **Real-time Broadcast**
   - MCP response emitted via Socket.IO: `group_stream_end`
   - Broadcast to room: `group_{group_id}`
   - Frontend updates chat UI in real-time

---

## MCP Agent Configuration

### Known MCP Agents
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/debug_routes.py`
**Lines:** 61-108

```python
KNOWN_AGENTS = {
    "browser_haiku": {
        "name": "Browser Haiku",
        "icon": "eye",
        "role": "Tester",
        "description": "QA/Observer in Chrome Console",
        "can_modify": False,
        "capabilities": ["testing", "chat", "vision"],
        "model_id": "mcp/browser_haiku"
    },
    "claude_code": {
        "name": "Claude Code",
        "icon": "terminal",
        "role": "Executor",
        "description": "Code executor with MCP access",
        "can_modify": True,
        "capabilities": ["code", "reasoning", "execute"],
        "model_id": "mcp/claude_code"
    },
    ...
}
```

### MCP_AGENTS Dictionary
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`
**Lines:** 80-95

Defines agent aliases for mention matching:
```python
MCP_AGENTS = {
    "browser_haiku": {
        "name": "Browser Haiku",
        "endpoint": "mcp/browser_haiku",
        "icon": "eye",
        "role": "Tester",
        "aliases": ["browserhaiku", "browser", "haiku"],
    },
    "claude_code": {
        "name": "Claude Code",
        "endpoint": "mcp/claude_code",
        "icon": "terminal",
        "role": "Executor",
        "aliases": ["claudecode", "claude", "code"],
    },
}
```

---

## Socket.IO Event Details

### mcp_mention Event
**Emitted from:** `notify_mcp_agents()` at line 163
**Namespace:** "/" (root)
**Payload:**

```json
{
  "type": "mcp_mention",
  "group_id": "542444da-fcb1-4e26-ac00-f414e2c43591",
  "group_name": "Сугиября рабочая группа 2",
  "sender_id": "user_id",
  "content": "Full message from user",
  "message_id": "msg_uuid",
  "timestamp": 1707300000.123,
  "mentioned_agents": ["claude_code"],
  "target_agent": "claude_code",
  "agent_name": "Claude Code",
  "agent_role": "Executor"
}
```

**Current Status:**
- ✅ Event is emitted
- ⚠️ No active listener in MCP code
- 💡 Browser extensions could listen if needed

---

## Implementation Example: Claude Code Polling

Here's how Claude Code should implement mention checking:

```python
import requests
import time

class MCPMentionPoller:
    def __init__(self, agent_id="claude_code", base_url="http://localhost:5001"):
        self.agent_id = agent_id
        self.base_url = base_url
        self.poll_interval = 5  # seconds

    def check_mentions(self, limit=20, unread_only=True):
        """Poll for pending mentions."""
        endpoint = f"{self.base_url}/api/debug/mcp/mentions/{self.agent_id}"
        params = {
            "limit": limit,
            "unread_only": unread_only,
            "mark_read": True  # Auto-mark as read
        }

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to fetch mentions: {e}")
            return None

    def respond_to_mention(self, mention, response_text):
        """Send response to group chat."""
        group_id = mention["context"]["group_id"]
        endpoint = f"{self.base_url}/api/debug/mcp/groups/{group_id}/send"

        payload = {
            "agent_id": self.agent_id,
            "content": response_text,
            "message_type": "response"
        }

        try:
            response = requests.post(endpoint, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to send response: {e}")
            return None

    def poll_continuously(self):
        """Continuously poll for mentions."""
        while True:
            data = self.check_mentions()
            if data and data.get("returned", 0) > 0:
                print(f"Found {data['returned']} mentions!")
                for mention in data["mentions"]:
                    print(f"From {mention['sender']}: {mention['message']}")
                    # Process mention...
                    response = self.respond_to_mention(
                        mention,
                        "Acknowledgement: I received your message"
                    )
                    print(f"Sent response: {response}")

            time.sleep(self.poll_interval)

# Usage
poller = MCPMentionPoller()
poller.poll_continuously()
```

---

## Testing the Flow

### 1. Trigger a mention in group chat

```bash
curl -X POST http://localhost:5001/api/debug/mcp/groups/542444da-fcb1-4e26-ac00-f414e2c43591/send \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "user",
    "content": "@claude_code please analyze this code",
    "message_type": "chat"
  }'
```

### 2. Poll for mentions as Claude Code

```bash
curl http://localhost:5001/api/debug/mcp/mentions/claude_code
```

### 3. Respond as Claude Code

```bash
curl -X POST http://localhost:5001/api/debug/mcp/groups/542444da-fcb1-4e26-ac00-f414e2c43591/send \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "claude_code",
    "content": "Analysis complete: The code is well-structured",
    "message_type": "response"
  }'
```

---

## Important Notes

1. **In-Memory Buffer:** `team_messages` is stored in-memory, not persistent
   - Survives server restarts? No
   - Max capacity: 100 messages
   - Circular buffer: oldest messages dropped when limit exceeded

2. **Polling vs Push:**
   - Current: Polling-based (agent checks periodically)
   - Future: Could use Socket.IO push for real-time notification
   - Current implementation of `mcp_mention` event not actively used

3. **Agent Identification:**
   - Agents matched by ID in MCP_AGENTS dict
   - Supports aliases (e.g., "claude" matches "claude_code")
   - Case-insensitive matching

4. **Context Preservation:**
   - group_id, group_name, message_id preserved in context
   - Allows agent to respond to specific group/message
   - Enables traceability and reply threading

5. **State Management:**
   - Messages: `pending=True` initially
   - After polling: auto-marked `read=True` (if mark_read=True)
   - No deletion, just circular buffer overflow

---

## Phase History

- **Phase 80.13:** MCP @mention routing introduced
- **Phase 80.2:** Agent-to-agent team messaging
- **Phase 80.3:** Monochrome design with Lucide icons
- **Phase 80.14:** Improved MCP message emit with logging
- **Phase 80.16:** Enhanced error logging for group_message_from_mcp

---

## Related Documentation

- MCP Config: `.claude-mcp-config.md`
- Group Chat Manager: `src/services/group_chat_manager.py`
- Message Handler: `src/api/handlers/group_message_handler.py`
- Debug Routes: `src/api/routes/debug_routes.py`
- Socket Manager: `src/api/handlers/mcp_socket_handler.py`

---

## Summary

**How @mentions get from chat to MCP:**

1. User types: `@claude_code do something`
2. Message sent via Socket.IO `group_message` event
3. Mention detected via regex: `@([\w\-\.]+...)`
4. Mention stored in global `team_messages` buffer with metadata
5. `mcp_mention` Socket.IO event emitted (for future use)
6. Claude Code polls `/api/debug/mcp/mentions/claude_code` periodically
7. Claude Code receives mention with full context (group_id, content, etc.)
8. Claude Code processes and responds via `POST /api/debug/mcp/groups/{group_id}/send`
9. Response broadcast to group chat in real-time

**Key Takeaway:** VETKA uses **polling-based** mention delivery with **in-memory buffering** and **Socket.IO broadcasting** for real-time responses. MCP agents are first-class participants in group chats, not external tools.
