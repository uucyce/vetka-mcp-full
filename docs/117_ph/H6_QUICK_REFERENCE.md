# H6 Scout: Quick Reference Guide

## The 5-Second Version

User mentions `@claude_code` → Message stored in in-memory buffer → Claude Code polls REST API every 5 seconds → Claude Code responds via REST API → Message broadcast via Socket.IO to all clients.

---

## Key Markers

| Marker | File | Lines | What |
|--------|------|-------|------|
| **H6_MENTION_DETECT_LINE** | `group_message_handler.py` | 661-679 | Where @mentions are extracted from messages |
| **H6_MCP_MENTION_EVENT** | `group_message_handler.py` | 158-176 | Where `mcp_mention` Socket.IO event is emitted |
| **H6_TEAM_MESSAGES_DICT** | `debug_routes.py` | 52-56, 178-217 | In-memory message buffer structure |
| **H6_POLLING_ENDPOINT** | `debug_routes.py` | 1503-1581 | Main polling endpoint for MCP agents |
| **H6_ROUTING_FLOW** | Both files | See flow diagram | Complete end-to-end mention flow |

---

## Critical Files

```
src/api/handlers/
  ├── group_message_handler.py      ← Mention detection + notify_mcp_agents()
  └── mcp_socket_handler.py         ← Socket.IO namespace for MCP (different from mentions)

src/api/routes/
  └── debug_routes.py                ← Polling endpoints + team_messages buffer
```

---

## The Flow in 6 Steps

```
1. USER SENDS MESSAGE
   Message: "@claude_code fix the bug"
   Via: Socket.IO event "group_message"
   Handler: handle_group_message() [line 532]

2. DETECT MENTION
   Regex: @([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)
   Result: mentions = ["claude_code"]
   Line: 664-669

3. NOTIFY MCP AGENT
   Function: notify_mcp_agents() [lines 98-217]
   Actions:
   - Emit: mcp_mention event (line 163)
   - Store: in team_messages buffer (line 208)
   - Mark: pending=True, read=False

4. MCP AGENT POLLS
   Endpoint: GET /api/debug/mcp/mentions/claude_code
   Interval: Every 5 seconds (typical)
   Response: JSON array with mention and context

5. MCP AGENT PROCESSES
   - Reads mention content
   - Executes task (code analysis, etc.)
   - Prepares response

6. MCP AGENT RESPONDS
   Endpoint: POST /api/debug/mcp/groups/{group_id}/send
   Body: {agent_id, content, message_type}
   Effect: Broadcast to group via Socket.IO
```

---

## API Quick Start

### For Claude Code: Poll for Mentions

```bash
# Poll every 5 seconds
curl "http://localhost:5001/api/debug/mcp/mentions/claude_code?mark_read=true"

# Response:
# {
#   "agent": "claude_code",
#   "mentions": [
#     {
#       "id": "mcp_msg123_claude_code",
#       "sender": "user",
#       "message": "fix the bug",
#       "context": {
#         "group_id": "542444da-fcb1-4e26-ac00-f414e2c43591",
#         "group_name": "Сугиями рабочая группа 2",
#         "type": "group_mention"
#       }
#     }
#   ]
# }
```

### For Claude Code: Send Response

```bash
curl -X POST "http://localhost:5001/api/debug/mcp/groups/542444da-fcb1-4e26-ac00-f414e2c43591/send" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "claude_code",
    "content": "Bug fixed! The issue was in line 42.",
    "message_type": "response"
  }'
```

### For Users: Trigger a Mention

```bash
# Send message mentioning claude_code
curl -X POST "http://localhost:5001/api/debug/mcp/groups/542444da-fcb1-4e26-ac00-f414e2c43591/send" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "user",
    "content": "@claude_code please analyze this code",
    "message_type": "chat"
  }'
```

---

## Message Structure

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
  "message": "Full message content",
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

## Known MCP Agents

```python
# These are registered in MCP_AGENTS dict [line 80-95]

claude_code:
  - Aliases: ["claudecode", "claude", "code"]
  - Name: "Claude Code"
  - Role: "Executor"
  - Icon: "terminal"
  - Can modify: True

browser_haiku:
  - Aliases: ["browserhaiku", "browser", "haiku"]
  - Name: "Browser Haiku"
  - Role: "Tester"
  - Icon: "eye"
  - Can modify: False

# Usage in messages:
@claude_code          # exact match
@claude              # alias match
@claudecode          # alias match
@claude_code         # exact match (with underscore)
```

---

## Polling Patterns

### Pattern 1: Simple Polling Loop (Python)

```python
import requests
import time

BASE_URL = "http://localhost:5001"
AGENT_ID = "claude_code"

while True:
    # Poll for mentions
    response = requests.get(
        f"{BASE_URL}/api/debug/mcp/mentions/{AGENT_ID}",
        params={"mark_read": True}
    )

    mentions = response.json().get("mentions", [])

    if mentions:
        for mention in mentions:
            # Process mention
            task = mention["message"]
            group_id = mention["context"]["group_id"]

            # Do work...
            result = process_task(task)

            # Send response
            requests.post(
                f"{BASE_URL}/api/debug/mcp/groups/{group_id}/send",
                json={
                    "agent_id": AGENT_ID,
                    "content": result,
                    "message_type": "response"
                }
            )

    time.sleep(5)  # Poll every 5 seconds
```

### Pattern 2: JavaScript Polling Loop

```javascript
const BASE_URL = "http://localhost:5001";
const AGENT_ID = "claude_code";

async function pollAndRespond() {
  while (true) {
    try {
      // Poll for mentions
      const response = await fetch(
        `${BASE_URL}/api/debug/mcp/mentions/${AGENT_ID}?mark_read=true`
      );
      const data = await response.json();

      for (const mention of data.mentions || []) {
        // Process mention
        const task = mention.message;
        const groupId = mention.context.group_id;

        // Do work...
        const result = await processTask(task);

        // Send response
        await fetch(
          `${BASE_URL}/api/debug/mcp/groups/${groupId}/send`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              agent_id: AGENT_ID,
              content: result,
              message_type: "response"
            })
          }
        );
      }

      await new Promise(resolve => setTimeout(resolve, 5000));
    } catch (error) {
      console.error("Poll error:", error);
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
  }
}

pollAndRespond();
```

---

## Debugging Checklist

```
✓ Is server running on :5001?
  curl http://localhost:5001/api/debug/agent-info

✓ Does agent exist in KNOWN_AGENTS?
  curl http://localhost:5001/api/debug/team-agents | grep claude_code

✓ Is group accessible?
  curl http://localhost:5001/api/debug/mcp/groups | grep "542444da"

✓ Are there any pending mentions?
  curl http://localhost:5001/api/debug/mcp/mentions/claude_code

✓ Can I send a test mention?
  [See API Quick Start section]

✓ Can agent respond to test mention?
  [See API Quick Start section]

✓ Are mentions reaching the buffer?
  curl http://localhost:5001/api/debug/team-messages | grep claude_code

✓ Is Socket.IO working?
  Browser console should show Socket.IO connected
  Check Network tab for socket.io frames
```

---

## Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Mention not detected | Typo in @mention | Check exact agent ID: `@claude_code` not `@code` |
| Agent doesn't receive mention | Not polling | Implement polling loop (every 5 seconds) |
| Polling returns empty | Mention already marked read | Set `mark_read=false` to see all |
| Response not broadcast | Wrong group_id | Extract from mention context |
| Buffer overflow | >100 messages without clearing | Oldest automatically dropped |
| Agent offline | No polling happening | Implement health check, retry on failure |

---

## Important Notes

1. **In-Memory Only**
   - Buffer lost on server restart
   - Max 100 messages
   - No persistent storage

2. **Polling Pattern**
   - 5 second interval recommended
   - Automatic mark_read available
   - No real-time push (Socket.IO push available but not used)

3. **Group Context**
   - Always include group_id from mention context when responding
   - Enables proper routing and threading
   - Required for send response endpoint

4. **Agent Identity**
   - Use lowercase agent_id in API calls
   - Aliases work in @mentions (e.g., @claude matches claude_code)
   - Must match KNOWN_AGENTS or MCP_AGENTS dict

5. **Error Handling**
   - Network errors: implement retry logic
   - Missing agent: returns 400 with error message
   - Invalid group: returns {error: "Group not found"}

---

## Phase Information

- **Phase 80.13:** Original @mention routing implementation
- **Phase 80.14:** Improved MCP message emit with logging
- **Phase 80.16:** Enhanced error handling
- **Phase 80.28:** Smart reply decay for chains

---

## Related Reading

- Full specification: `H6_MCP_MENTION_ROUTING_FLOW.md`
- Sequence diagrams: `H6_MENTION_FLOW_SEQUENCE.md`
- MCP Config: `.claude-mcp-config.md`
- Group chat manager: `src/services/group_chat_manager.py`

---

## TL;DR Summary

**What:** VETKA system allows MCP agents (@claude_code, @browser_haiku) to receive and respond to @mentions in group chats.

**How:** Mentions → in-memory buffer → polling REST API → MCP agent processes → sends response → broadcast via Socket.IO.

**Where:** User sends message in group → stored in `/api/debug/mcp/mentions/{agent_id}` → agent polls every 5s → agent responds via `/api/debug/mcp/groups/{group_id}/send`.

**When:** Instant storage (10ms), delayed delivery (5s polling interval), instant broadcast.

**Why:** Enables seamless agent collaboration in group chats without complex infrastructure.
