# Phase 80.18: Socket Room Join Acknowledgment Fix

## Problem

MCP messages were not appearing in real-time due to a race condition:
1. `joinGroup(groupId)` - async socket emit
2. `setActiveGroupId(groupId)` - sync state update
3. MCP emit happens before the client has actually joined the room

The socket.io `enter_room()` on the backend is async, but the frontend wasn't waiting for confirmation before setting up message listeners.

## Solution

### Backend (Already Implemented)
The backend already emits `group_joined_ack` after joining the room:

**File:** `src/api/handlers/group_message_handler.py`
```python
@sio.on('join_group')
async def handle_join_group(sid, data):
    """Handle client joining a group room."""
    group_id = data.get('group_id')
    if group_id:
        # Join Socket.IO room for this group
        await sio.enter_room(sid, f'group_{group_id}')
        print(f"[GROUP] Client {sid[:8]} joined group room: {group_id}")
        # Phase 80.18: Send acknowledgment
        await sio.emit('group_joined_ack', {'group_id': group_id}, to=sid)
```

### Frontend Changes

#### 1. useSocket.ts - Add Event Type and Listener

**Added interface:**
```typescript
// Phase 80.18: Socket room join acknowledgment
group_joined_ack: (data: {
  group_id: string;
  room?: string;
}) => void;
```

**Added listener:**
```typescript
// Phase 80.18: Socket room join acknowledgment - fixes race condition
socket.on('group_joined_ack', (data) => {
  console.log('[Socket] group_joined_ack:', data.group_id);
  if (typeof window !== 'undefined') {
    window.dispatchEvent(
      new CustomEvent('group_joined_ack', { detail: data })
    );
  }
});
```

#### 2. ChatPanel.tsx - Wait for Acknowledgment

Updated both `handleCreateGroup` and `handleSelectChat` to wait for the ack:

```typescript
// Phase 80.18: Wait for room join acknowledgment before setting active
const waitForJoin = new Promise<void>((resolve) => {
  const handler = (e: CustomEvent) => {
    if (e.detail.group_id === groupId) {
      window.removeEventListener('group_joined_ack', handler as EventListener);
      console.log('[ChatPanel] Phase 80.18: Room join confirmed for', groupId);
      resolve();
    }
  };
  window.addEventListener('group_joined_ack', handler as EventListener);
  // Timeout fallback after 2 seconds
  setTimeout(() => {
    window.removeEventListener('group_joined_ack', handler as EventListener);
    console.log('[ChatPanel] Phase 80.18: Join ack timeout, proceeding anyway');
    resolve();
  }, 2000);
});

joinGroup(groupId);
await waitForJoin;
setActiveGroupId(groupId);
```

## Files Modified

1. `src/api/handlers/group_message_handler.py` - Backend already had the fix
2. `client/src/hooks/useSocket.ts` - Added type and listener for `group_joined_ack`
3. `client/src/components/chat/ChatPanel.tsx` - Wait for ack in `handleCreateGroup` and `handleSelectChat`

## Testing

1. Create a new group - messages should appear immediately
2. Select an existing group chat from history - messages should load and real-time updates work
3. If acknowledgment times out (2 sec), the system falls back gracefully

## Alternative Approach (Not Implemented)

A simpler but less reliable fix would be to reduce polling interval from 3 sec to 1 sec for faster fallback. The acknowledgment approach is more robust.
