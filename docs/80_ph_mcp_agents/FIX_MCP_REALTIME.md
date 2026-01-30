# Phase 80.14: Fix MCP Real-time Message Updates

## Date: 2026-01-22

## Problem Summary

MCP (Model Context Protocol) agent messages were not appearing in real-time in the chat panel. Messages were being stored correctly in the database but not broadcast to connected clients via SocketIO.

## Root Cause Analysis

Based on the Scout report (SCOUT_MCP_REALTIME.md), the following issues were identified:

1. **Silent SocketIO failures**: The emit code had basic error handling but no logging to diagnose issues
2. **Potential room issues**: No verification that clients were properly joined to the room
3. **Missing fallback**: If SocketIO failed, users had to refresh to see messages

## Changes Made

### 1. Backend: Enhanced SocketIO Emit Logging (debug_routes.py)

**File**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/debug_routes.py`

**Lines**: ~1202-1230

**Changes**:
- Added detailed logging before each emit
- Added success confirmation logging after emit
- Added traceback logging on error
- Added warning when SocketIO is not available

```python
# Phase 80.14: Improved MCP message emit with detailed logging
socketio = getattr(request.app.state, 'socketio', None)
room = f'group_{group_id}'
print(f"[MCP] Phase 80.14: Sending message to group {group_id}, socketio={'present' if socketio else 'None'}")

if socketio:
    try:
        print(f"[MCP] Emitting 'group_message' to room {room}")
        await socketio.emit('group_message', message.to_dict(), room=room)
        # ... stream_end emit ...
        print(f"[MCP] Phase 80.14: Emit successful for message {message.id}")
    except Exception as e:
        print(f"[MCP] Phase 80.14: SocketIO emit error: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"[MCP] Phase 80.14: SocketIO not available - message stored but not broadcast")
```

### 2. Frontend: HTTP Polling Fallback (ChatPanel.tsx)

**File**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`

**Lines**: ~284-347

**Changes**:
Added a polling mechanism as fallback for when SocketIO messages don't arrive:

```typescript
// Phase 80.14: HTTP Polling fallback for MCP messages
useEffect(() => {
  if (!activeGroupId) return;

  let lastPollTime = Date.now() / 1000;

  const pollMessages = async () => {
    // Fetch recent messages from API
    const response = await fetch(
      `/api/debug/mcp/groups/${activeGroupId}/messages?limit=10`
    );
    // Check for new messages and add if not duplicates
    // Uses timestamp and ID-based deduplication
  };

  // Poll every 3 seconds as fallback
  const interval = setInterval(pollMessages, 3000);
  return () => clearInterval(interval);
}, [activeGroupId, chatMessages, addChatMessage]);
```

**Key Features**:
- Polls every 3 seconds only when in a group chat
- Deduplicates by message ID to avoid duplicates
- Only adds messages newer than last poll
- Silent failure (doesn't spam console)

### 3. SocketIO Setup Verification

**Verified in**:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/main.py` (line 291): `app.state.socketio = sio`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/initialization/components_init.py`: `_socketio` global and `get_socketio()` function
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`: Room joining with `enter_room(sid, f'group_{group_id}')`

**Conclusion**: SocketIO setup is correct. The issue is likely in room membership or async timing.

## Debugging Steps

When MCP messages don't appear in real-time:

1. **Check server logs for**:
   - `[MCP] Phase 80.14: Sending message to group...` - Confirms emit is triggered
   - `[MCP] Phase 80.14: Emit successful...` - Confirms no exception
   - `[GROUP] Client ... joined group room:` - Confirms client is in room

2. **Check browser console for**:
   - `[Poll] Phase 80.14: Added ... new messages via polling` - Confirms fallback is working
   - Socket connection events

3. **If socketio is None**:
   - Check that `app.state.socketio` is set in main.py
   - Check that request.app is the correct FastAPI app instance

## Testing

1. Start the server and observe startup logs
2. Create a group chat in the UI
3. Send a message via MCP endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/debug/mcp/groups/{group_id}/messages \
     -H "Content-Type: application/json" \
     -d '{"agent_id": "test-agent", "content": "Hello from MCP"}'
   ```
4. Check server logs for emit messages
5. Verify message appears in UI (either via socket or polling within 3 seconds)

## Future Improvements

1. Add room membership debug endpoint to verify clients are in rooms
2. Consider WebSocket heartbeat for connection health
3. Add client-side reconnection logic
4. Consider Server-Sent Events (SSE) as alternative fallback

## Related Files

- `src/api/routes/debug_routes.py` - MCP send endpoint
- `client/src/components/chat/ChatPanel.tsx` - Chat UI
- `client/src/hooks/useSocket.ts` - Socket hook
- `src/api/handlers/group_message_handler.py` - Socket event handlers
- `main.py` - SocketIO initialization
