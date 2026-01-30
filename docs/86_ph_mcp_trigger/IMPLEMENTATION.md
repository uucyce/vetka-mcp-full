# Phase 86: MCP @mention Agent Trigger

**Date:** 2026-01-21
**Status:** COMPLETED
**Author:** Claude Code (MCP)

---

## Problem

MCP endpoint `POST /api/debug/mcp/groups/{group_id}/send` was NOT triggering agents when @mentions were present in the message content.

**Root Cause:** The `select_responding_agents()` call was disabled (set to empty list) in Phase 80.8 for debugging, and never re-enabled.

---

## Solution

Re-enabled the agent trigger logic in `send_group_message_from_mcp()`.

### Changes Made

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/debug_routes.py`

#### 1. Fixed Imports (lines 1162-1165)

**Before:**
```python
from src.services.group_chat_manager import get_group_chat_manager
# Phase 80.9: Removed broken imports - orchestrator doesn't exist
# from src.agents.orchestrator import get_orchestrator
# from src.agents.role_prompts import get_agent_prompt
```

**After:**
```python
from src.services.group_chat_manager import get_group_chat_manager
# Phase 86: Re-enabled imports - orchestrator exists in components_init
from src.initialization.components_init import get_orchestrator
from src.agents.role_prompts import get_agent_prompt
```

#### 2. Enabled select_responding_agents() (lines 1228-1237)

**Before:**
```python
# Phase 80.8: Agent trigger temporarily disabled - needs debugging
# TODO: Fix agent trigger logic
participants_to_respond = []  # Disabled for now

# Original code (disabled):
# participants_to_respond = await manager.select_responding_agents(...)
```

**After:**
```python
# Phase 86: Re-enabled agent trigger for @mentions
# select_responding_agents() will parse @mentions and return agents to call
participants_to_respond = await manager.select_responding_agents(
    content=body.content,
    participants=group.participants,
    sender_id=sender_id,
    reply_to_agent=None  # MCP messages don't have reply context
)

print(f"[MCP_AGENT_TRIGGER] Phase 86: select_responding_agents returned {len(participants_to_respond)} agents")
```

---

## How It Works Now

### Message Flow with @mentions:

```
MCP/Claude Code sends:
  POST /api/debug/mcp/groups/{group_id}/send
  body: {"agent_id": "claude_code", "content": "@Architect please review this"}
    |
    v
send_group_message_from_mcp()
    |
    v
1. manager.send_message() -> stores in group.messages
2. socketio.emit('group_message') -> broadcasts to UI
3. manager.select_responding_agents(content="@Architect please review this")
   -> Parses @Architect mention
   -> Returns [Architect participant]
    |
    v
4. If participants_to_respond:
   - get_orchestrator()
   - orchestrator.call_agent(agent_type='Architect', ...)
   - Store agent response via manager.send_message()
   - Broadcast via socketio.emit('group_message')
```

### Phase 80.6 Isolation (Still Active)

When MCP sends AS an agent (sender_id starts with @):
- If content has NO explicit @mention -> `select_responding_agents()` returns empty list
- This prevents infinite agent-to-agent loops
- Example: `@Claude Code` sends "help" -> nobody responds
- Example: `@Claude Code` sends "@Architect help" -> @Architect responds

---

## Testing

### Test 1: MCP sends with @mention

```bash
curl -X POST http://localhost:8000/api/debug/mcp/groups/{group_id}/send \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "claude_code",
    "content": "@Architect please review this architecture",
    "message_type": "chat"
  }'
```

**Expected:**
- Message saved in group
- UI receives `group_message` event
- @Architect agent is called
- Agent response saved and broadcasted

### Test 2: MCP sends without @mention

```bash
curl -X POST http://localhost:8000/api/debug/mcp/groups/{group_id}/send \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "claude_code",
    "content": "Just sharing some information",
    "message_type": "chat"
  }'
```

**Expected:**
- Message saved in group
- UI receives `group_message` event
- No agents respond (Phase 80.6 isolation)

---

## Files Modified

1. `/src/api/routes/debug_routes.py` - lines 1162-1237
2. `/docs/82_ph_ui_fixes/MCP_SEND_NOT_VISIBLE.md` - updated status

---

## Related Phases

- **Phase 57.7:** Original `select_responding_agents()` implementation
- **Phase 80.4:** MCP agents in group chat - added REST endpoints
- **Phase 80.6:** MCP agent isolation - no auto-response cascade
- **Phase 80.8:** Disabled agent trigger for debugging
- **Phase 86:** Re-enabled agent trigger (this phase)
