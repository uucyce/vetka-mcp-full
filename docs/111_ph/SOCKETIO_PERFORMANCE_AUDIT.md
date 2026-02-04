# Socket.IO Performance Audit

**Date:** 2026-02-04
**Phase:** 111
**Auditor:** Claude Opus 4.5

## Executive Summary

This audit identifies Socket.IO performance bottlenecks in VETKA's real-time communication layer. The codebase shows **good existing optimizations** (RAF batching for stream_token, camera debounce) but several opportunities exist for reducing emit frequency and preventing UI re-renders.

---

## High-Frequency Events

| Event | Handler Location | Current Frequency | Impact | Priority |
|-------|------------------|-------------------|--------|----------|
| `stream_token` | `streaming_handler.py:79` | Per token (~100-500/response) | HIGH | **OPTIMIZED** (RAF batching in client) |
| `group_stream_token` | `group_message_handler.py` | Per token (~100-500/response) | HIGH | Needs batching |
| `group_typing` | `group_message_handler.py:1168` | Per keystroke | MEDIUM | Needs throttle |
| `chat_node_update` | `group_message_handler.py:612,960` | Per message + per agent response | MEDIUM | Potential dedup |
| `scan_progress` | `watcher_routes.py:186` | Per file scanned | MEDIUM | Consider batching |
| `node_added/updated` | `file_watcher.py:432,436` | Per file change | LOW | Has debounce (400ms) |

---

## Detailed Analysis

### 1. Token Streaming (OPTIMIZED)

**Location:** `client/src/hooks/useSocket.ts:861-871`

```typescript
// Phase 49.2: Batch token updates with requestAnimationFrame
socket.on('stream_token', (data) => {
  const current = tokenBufferRef.current.get(data.id) || '';
  tokenBufferRef.current.set(data.id, current + data.token);

  if (!rafIdRef.current) {
    rafIdRef.current = requestAnimationFrame(() => {
      flushTokenBuffer();
    });
  }
});
```

**Status:** GOOD - Already uses RAF batching to reduce React re-renders from ~500/response to ~30/response (at 60fps).

**No action needed.**

---

### 2. Group Stream Token (NEEDS OPTIMIZATION)

**Backend:** `group_message_handler.py` emits tokens individually
**Frontend:** `ChatPanel.tsx:294-306` updates state per token

```typescript
const handleGroupStreamToken = (e: CustomEvent) => {
  const data = e.detail;
  if (data.group_id !== activeGroupId) return;

  // PROBLEM: setState on EVERY token
  useStore.setState((state) => ({
    chatMessages: state.chatMessages.map((msg) =>
      msg.id === data.id
        ? { ...msg, content: msg.content + data.token }
        : msg
    ),
  }));
};
```

**Problem:** No RAF batching like solo chat. Causes excessive re-renders.

**Recommendation:** Apply same RAF pattern as solo streaming:
```typescript
// Add to ChatPanel.tsx
const groupTokenBufferRef = useRef<Map<string, string>>(new Map());

const handleGroupStreamToken = (e: CustomEvent) => {
  const data = e.detail;
  if (data.group_id !== activeGroupId) return;

  // Accumulate in buffer
  const current = groupTokenBufferRef.current.get(data.id) || '';
  groupTokenBufferRef.current.set(data.id, current + data.token);

  // Schedule flush at next frame
  if (!groupRafIdRef.current) {
    groupRafIdRef.current = requestAnimationFrame(flushGroupTokenBuffer);
  }
};
```

**Impact:** HIGH - 10-20x reduction in group chat re-renders during streaming.

---

### 3. Typing Indicator (NEEDS THROTTLE)

**Backend:** `group_message_handler.py:1168-1179`
```python
@sio.on("group_typing")
async def handle_group_typing(sid, data):
    group_id = data.get("group_id")
    agent_id = data.get("agent_id")
    if group_id and agent_id:
        await sio.emit(
            "group_typing",
            {"group_id": group_id, "agent_id": agent_id},
            room=f"group_{group_id}",
            skip_sid=sid,
        )
```

**Frontend:** `useSocket.ts:1553-1558`
```typescript
const sendTypingIndicator = useCallback((groupId: string, agentId: string) => {
  socketRef.current?.emit('group_typing', {
    group_id: groupId,
    agent_id: agentId,
  });
}, []);
```

**Problem:** No throttle on client or server. Fast typing = flood of events.

**Recommendation:** Add 500ms throttle on client:
```typescript
const lastTypingEmitRef = useRef<number>(0);
const TYPING_THROTTLE_MS = 500;

const sendTypingIndicator = useCallback((groupId: string, agentId: string) => {
  const now = Date.now();
  if (now - lastTypingEmitRef.current < TYPING_THROTTLE_MS) return;

  lastTypingEmitRef.current = now;
  socketRef.current?.emit('group_typing', {
    group_id: groupId,
    agent_id: agentId,
  });
}, []);
```

**Impact:** MEDIUM - Reduces typing events by ~10x.

---

### 4. Chat Node Updates (POTENTIAL DEDUP)

**Backend:** `group_message_handler.py:612,960`

Emits `chat_node_update` twice per conversation turn:
1. Line 612: When user sends message
2. Line 960: When agent responds

```python
# Both emit:
await sio.emit(
    "chat_node_update",
    {
        "chat_id": group_id,
        "decay_factor": 1.0,
        "last_activity": datetime.now().isoformat(),
        "message_count": len(manager.get_messages(group_id, limit=1000)),
    },
    room=f"group_{group_id}",
)
```

**Problem:** `get_messages(group_id, limit=1000)` is called just for count. Expensive query.

**Recommendation:**
1. Track message count in Group object (increment on add)
2. Debounce chat_node_update to 1 second
3. Batch multiple updates into single emit

```python
# In Group class:
class Group:
    message_count: int = 0

    def add_message(self, msg):
        self.messages.append(msg)
        self.message_count += 1
```

**Impact:** MEDIUM - Reduces Qdrant queries and duplicate emits.

---

### 5. Scan Progress Events

**Backend:** `watcher_routes.py:186`

```python
await socketio.emit('scan_progress', {
    'progress': ...,
    'current': current_count,
    'total': total_count,
    'file_path': file_path,
})
```

**Frontend:** `useSocket.ts:668-687` dispatches to window.

**Current state:** Emits per file during scan. Large projects = thousands of events.

**Recommendation:** Batch to emit every 100 files or 500ms:
```python
# Accumulate in buffer
scan_buffer = []
last_emit_time = 0

async def emit_scan_progress(file_path):
    global scan_buffer, last_emit_time

    scan_buffer.append(file_path)
    now = time.time()

    # Emit every 100 files or every 500ms
    if len(scan_buffer) >= 100 or (now - last_emit_time) > 0.5:
        await socketio.emit('scan_progress', {
            'files': scan_buffer,
            'count': len(scan_buffer),
        })
        scan_buffer = []
        last_emit_time = now
```

**Impact:** LOW-MEDIUM - Reduces scan events by ~100x for large projects.

---

### 6. Broadcast vs Room-Specific

**Current patterns found:**

| Pattern | Usage | Status |
|---------|-------|--------|
| `to=sid` | Individual client events | GOOD |
| `room=f"group_{group_id}"` | Group-specific events | GOOD |
| No `to=` parameter | Broadcast to all | Needs review |

**Broadcast events found:**
- `tree_handlers.py:68,100,147` - `branch_forked`, `node_moved`, `knowledge_refactored`
- `chat_handlers.py:130` - `message_counts_updated`

**Recommendation:** Review if these truly need broadcast or can be room-scoped.

---

### 7. Payload Size Analysis

**Large payloads identified:**

| Event | Payload Size | Issue |
|-------|--------------|-------|
| `group_stream_end` | full_message (potentially 10KB+) | Acceptable - needed for persistence |
| `chat_history_loaded` | All messages array | Could paginate |
| `tree_updated` | Full tree nodes | Consider delta updates |

**Recommendation:** For `tree_updated`, consider delta updates:
```python
# Instead of full tree:
await sio.emit('tree_updated', {'nodes': all_nodes})  # BAD

# Send only changes:
await sio.emit('tree_delta', {
    'added': [new_node],
    'removed': [deleted_id],
    'modified': [changed_node],
})
```

---

## Recommended Throttle/Debounce Settings

| Event | Current | Recommended | Rationale |
|-------|---------|-------------|-----------|
| `stream_token` | RAF batching | Keep as-is | Already optimized |
| `group_stream_token` | None | RAF batching | Match solo chat |
| `group_typing` | None | 500ms throttle | Standard UX |
| `chat_node_update` | None | 1000ms debounce | Batch activity updates |
| `scan_progress` | Per file | 500ms or 100 files | Reduce flood |
| `node_added` | 400ms debounce | Keep as-is | Already optimized |
| Camera focus | 2000ms debounce | Keep as-is | Already optimized |

---

## Implementation Priority

### High Priority (Do First)
1. **Group token batching** - Copy RAF pattern from solo chat
2. **Typing throttle** - Simple 500ms throttle

### Medium Priority
3. **Chat node update dedup** - Track count in object, debounce emit
4. **Scan progress batching** - 100-file or 500ms batches

### Low Priority (Future)
5. **Tree delta updates** - Requires significant refactor
6. **Broadcast review** - Audit all no-`to=` emits

---

## Existing Optimizations (Already Good)

1. **Camera debounce** (`useSocket.ts:27-33`): 2000ms debounce prevents camera chaos
2. **Token RAF batching** (`useSocket.ts:431-451`): Reduces re-renders significantly
3. **Room-based routing**: Most group events use `room=f"group_{id}"`
4. **File watcher debounce** (`file_watcher.py`): 400ms debounce for file events
5. **HTTP polling fallback** (`ChatPanel.tsx:356-421`): 3-second poll, not aggressive

---

## Metrics to Monitor

After implementing optimizations:
- WebSocket messages/second during streaming
- React render count during group chat
- CPU usage during large file scans
- Time-to-interactive after receiving events

---

## Files to Modify

| File | Changes |
|------|---------|
| `client/src/components/chat/ChatPanel.tsx` | Add RAF batching for group_stream_token |
| `client/src/hooks/useSocket.ts` | Add throttle to sendTypingIndicator |
| `src/api/handlers/group_message_handler.py` | Debounce chat_node_update, cache message count |
| `src/api/routes/watcher_routes.py` | Batch scan_progress events |

---

## Conclusion

VETKA's Socket.IO layer shows thoughtful existing optimizations (RAF batching, camera debounce) but has gaps in group chat streaming and typing indicators. Implementing the recommended throttle/debounce patterns will reduce UI lag and server load, particularly during active group conversations.

**Estimated effort:** 2-4 hours for high-priority items.
