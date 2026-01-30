# Phase 80.13: MCP @Mention Routing Fix

**Date:** 2026-01-22
**Status:** IMPLEMENTED
**Phase:** 80.13

## Problem Statement

When a user writes a message with `@browser_haiku` or `@claude_code` in a group chat:
1. The system parses @mentions correctly
2. BUT MCP agents are NOT in the group's `participants` dictionary
3. Therefore they were never notified or triggered

MCP agents (Browser Haiku, Claude Code) are external agents that communicate via the debug API endpoints, not internal group participants.

## Solution Overview

Added a dedicated MCP @mention routing mechanism that:

1. **Detects MCP agent mentions** - After message is stored, check for MCP agent mentions
2. **Notifies via Socket.IO** - Emits `mcp_mention` event for browser extensions to receive
3. **Stores in team_messages** - Creates entry in debug_routes buffer for API polling
4. **Provides polling endpoints** - MCP agents can poll for their pending mentions

## Implementation Details

### 1. Modified Files

#### `/src/api/handlers/group_message_handler.py`

Added MCP agent registry and notification function:

```python
# Phase 80.13: MCP Agent @mention routing
MCP_AGENTS = {
    'browser_haiku': {
        'name': 'Browser Haiku',
        'endpoint': 'mcp/browser_haiku',
        'icon': 'eye',
        'role': 'Tester',
        'aliases': ['browserhaiku', 'browser', 'haiku']
    },
    'claude_code': {
        'name': 'Claude Code',
        'endpoint': 'mcp/claude_code',
        'icon': 'terminal',
        'role': 'Executor',
        'aliases': ['claudecode', 'claude', 'code']
    }
}

async def notify_mcp_agents(sio, group_id, group_name, sender_id, content, mentions, message_id):
    """
    Phase 80.13: Notify MCP agents when they are @mentioned.
    Emits socket event 'mcp_mention' and stores in team_messages buffer.
    """
```

Added integration in `handle_group_message`:

```python
# Phase 80.13: Check for MCP agent @mentions and notify them
mentions = user_message.mentions if hasattr(user_message, 'mentions') else re.findall(r'@(\w+)', content)
if mentions:
    await notify_mcp_agents(
        sio=sio,
        group_id=group_id,
        group_name=group.get('name', 'Unknown Group'),
        sender_id=sender_id,
        content=content,
        mentions=mentions,
        message_id=user_message.id
    )
```

#### `/src/api/routes/debug_routes.py`

Added new endpoints:

```python
# GET /api/debug/mcp/mentions/{agent_id}
# Poll for pending @mentions

# POST /api/debug/mcp/notify
# Manually notify MCP agent (for testing)
```

### 2. Flow Diagram

```
User types: "@browser_haiku help with tests"
         │
         ▼
┌─────────────────────────────────┐
│ group_message_handler           │
│ handle_group_message()          │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ Parse @mentions from content    │
│ mentions = ["browser_haiku"]    │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ notify_mcp_agents()             │
│ - Check if mention is MCP agent │
│ - Emit socket event             │
│ - Store in team_messages        │
└─────────────────────────────────┘
         │
         ├─────────────────────────────────────┐
         │                                     │
         ▼                                     ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│ Socket.IO Event         │     │ team_messages Buffer    │
│ 'mcp_mention'           │     │ (for API polling)       │
└─────────────────────────┘     └─────────────────────────┘
         │                                     │
         ▼                                     ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│ Browser Extension       │     │ GET /api/debug/mcp/     │
│ receives event          │     │   mentions/browser_haiku│
└─────────────────────────┘     └─────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ Browser Haiku responds via      │
│ POST /api/debug/mcp/groups/     │
│   {group_id}/send               │
└─────────────────────────────────┘
```

### 3. Socket Event Format

```javascript
// Event: 'mcp_mention'
{
    type: 'mcp_mention',
    target_agent: 'browser_haiku',
    agent_name: 'Browser Haiku',
    agent_role: 'Tester',
    group_id: '542444da-fcb1-4e26-ac00-f414e2c43591',
    group_name: 'Working Group',
    sender_id: 'user',
    content: '@browser_haiku help with tests',
    message_id: 'abc-123',
    timestamp: 1737564000.123,
    mentioned_agents: ['browser_haiku']
}
```

### 4. API Endpoints

#### GET /api/debug/mcp/mentions/{agent_id}

Poll for pending @mentions.

**Parameters:**
- `limit` (int, default 20): Max mentions to return
- `unread_only` (bool, default true): Only unread mentions
- `mark_read` (bool, default false): Mark returned as read

**Response:**
```json
{
    "agent": "browser_haiku",
    "agent_name": "Browser Haiku",
    "total_unread": 3,
    "returned": 3,
    "mentions": [
        {
            "id": "mcp_abc123_browser_haiku",
            "timestamp": 1737564000.123,
            "sender": "user",
            "to": "browser_haiku",
            "message": "@browser_haiku help with tests",
            "context": {
                "group_id": "542444da-...",
                "group_name": "Working Group",
                "type": "group_mention"
            }
        }
    ],
    "respond_endpoint": "/api/debug/mcp/groups/{group_id}/send"
}
```

#### POST /api/debug/mcp/notify

Manually notify an MCP agent (for testing).

**Body:**
```json
{
    "agent_id": "browser_haiku",
    "content": "Test notification",
    "group_id": "optional-group-id",
    "sender": "system"
}
```

## Testing

### Test 1: Socket Event

1. Open browser console on VETKA 3D page
2. Listen for events:
   ```javascript
   socket.on('mcp_mention', (data) => console.log('MCP Mention:', data));
   ```
3. Send message in group: "@browser_haiku test"
4. Verify event received in console

### Test 2: API Polling

1. Send message: "@claude_code check this"
2. Poll endpoint:
   ```bash
   curl http://localhost:5000/api/debug/mcp/mentions/claude_code
   ```
3. Verify mention appears in response

### Test 3: Manual Notify

```bash
curl -X POST http://localhost:5000/api/debug/mcp/notify \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "browser_haiku", "content": "Test notification"}'
```

## Backward Compatibility

- Does NOT break existing @mention behavior for group participants
- MCP agents receive notifications IN ADDITION to normal processing
- Internal agents continue to work as before
- No changes to existing API contracts

## Related Files

- `/src/api/handlers/group_message_handler.py` - Main handler with MCP routing
- `/src/api/routes/debug_routes.py` - API endpoints for MCP agents
- `/src/services/group_chat_manager.py` - select_responding_agents (unchanged)

## Future Improvements

1. **WebSocket subscription** - MCP agents could subscribe to specific rooms
2. **Acknowledgment system** - Track when MCP agent received/processed mention
3. **Priority mentions** - @browser_haiku! for urgent notifications
4. **Mention types** - Different handling for questions vs tasks vs info
