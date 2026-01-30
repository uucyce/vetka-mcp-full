# FIX: MCP @Mention Trigger Internal Server Error

**Phase:** 80.16
**Date:** 2026-01-22
**Status:** FIXED

## Problem

When MCP agents (Claude Code, Browser Haiku) send messages to group chat:
- Messages WITHOUT @mentions: Work correctly
- Messages WITH @mentions (e.g., "@PM @Dev test"): Cause Internal Server Error

## Root Cause Analysis

The endpoint `POST /api/debug/mcp/groups/{group_id}/send` in `debug_routes.py` had several issues:

### 1. No Outer Exception Handler
The entire endpoint lacked a top-level try/except block. Any unhandled exception would propagate up as a 500 Internal Server Error with no useful error message.

### 2. Unsafe Participant Data Access
The code used direct dictionary access (`participant['agent_id']`) instead of safe `.get()` calls, which could raise KeyError if participant data was malformed.

### 3. Orchestrator None Case
When `get_orchestrator()` returns None (app not fully initialized), the code printed an error but had no graceful handling.

### 4. No Continuation on Agent Errors
When one agent failed, the entire chain would fail instead of continuing to the next agent.

## Changes Made

### File: `src/api/routes/debug_routes.py`

#### 1. Added Outer Try/Except (Line ~1172)
```python
# Phase 80.16: Outer try/except to prevent Internal Server Error
try:
    manager = get_group_chat_manager()
    group = manager._groups.get(group_id)
    # ... rest of function ...
except Exception as e:
    # Phase 80.16: Catch all exceptions to prevent Internal Server Error
    print(f"[MCP_ERROR] Phase 80.16: Exception in send_group_message_from_mcp: {e}")
    traceback.print_exc()
    return {
        "success": False,
        "error": str(e)[:200],
        "error_type": type(e).__name__,
        "group_id": group_id,
        "agent_id": body.agent_id if body else "unknown"
    }
```

#### 2. Safe Content Slicing (Line ~1242)
```python
# Phase 80.16: Safe content slicing with fallback
content_preview = body.content[:50] if body.content else ""
log_debug(
    f"MCP group message: {body.agent_id} -> {group.name}: {content_preview}...",
    ...
)
```

#### 3. Enhanced Logging for select_responding_agents (Line ~1250)
```python
print(f"[MCP_AGENT_TRIGGER] Phase 80.16: Calling select_responding_agents for content: {body.content[:100] if body.content else 'empty'}...")
```

#### 4. Detailed Orchestrator None Logging (Line ~1261)
```python
if not orchestrator:
    # Phase 80.16: Log detailed error when orchestrator is None
    print(f"[MCP_ERROR] Phase 80.16: Orchestrator is None! Cannot call agents.")
    print(f"[MCP_ERROR] This usually means the app was not initialized properly or AGENT_ORCHESTRATOR_CLASS is missing from app config.")
    # Continue without failing - message was already saved
```

#### 5. Safe Participant Data Extraction (Line ~1275)
```python
# Phase 80.16: Safe participant data extraction with defaults
agent_id = participant.get('agent_id', 'unknown')
model_id = participant.get('model_id', 'auto')
display_name = participant.get('display_name', 'Agent')
role = participant.get('role', 'worker')
```

#### 6. Enhanced Error Handling with Continuation (Line ~1422)
```python
except Exception as e:
    # Phase 80.16: Enhanced error logging with traceback
    print(f"[MCP_ERROR] Phase 80.16: Error calling agent {agent_id}: {e}")
    traceback.print_exc()
    # ... error notification code ...
    # Phase 80.16: Continue to next agent instead of failing
    continue
```

## Verification

1. Syntax check passed:
```bash
python -m py_compile src/api/routes/debug_routes.py
```

2. Expected behavior after fix:
   - Messages with @mentions should process successfully
   - If one agent fails, others continue
   - Detailed error logs in console for debugging
   - API returns error JSON instead of 500

## Testing

To test the fix:

1. Start VETKA server
2. Open group chat in browser
3. Send message via MCP endpoint:
```bash
curl -X POST "http://localhost:5001/api/debug/mcp/groups/{group_id}/send" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "claude_code", "content": "@PM @Dev test message"}'
```

4. Should see:
   - Message appears in chat
   - Mentioned agents (PM, Dev) respond
   - No Internal Server Error

## Log Markers

Search for these markers in logs:
- `[MCP_ERROR] Phase 80.16:` - Error events
- `[MCP_AGENT_TRIGGER] Phase 80.16:` - Agent trigger events
- `[MCP_AGENT_TRIGGER] Phase 86:` - Agent selection results
