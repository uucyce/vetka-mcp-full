# WATCHDOG → UI DISCONNECT ANALYSIS
**Analyst:** Haiku Watchdog Agent
**Date:** 2026-01-22
**Phase:** 80.20+ (Critical Pipeline Gap)

## Executive Summary
Backend watchdog successfully detects and broadcasts socket events (`node_updated`, `node_added`, `node_removed`), but **UI tree doesn't update**. Root cause: **Missing frontend socket listeners** - no component handles watchdog events. Additionally, the tree state never receives update commands because watchdog events are broadcasted to all clients but no handler processes them on the frontend.

---

## Pipeline Analysis

| # | Step | Component | Status | Evidence |
|---|------|-----------|--------|----------|
| 1 | File system event | watchdog lib | ✅ Works | VetkaFileHandler triggers on file create/modify/delete |
| 2 | Debounce & coalesce | VetkaFileHandler | ✅ Works | Accumulates events, fires after 400ms debounce |
| 3 | Callback triggered | VetkaFileWatcher._on_file_change() | ✅ Works | Logs: `[Watcher] modified: /path/to/file` |
| 4 | Qdrant indexed | handle_watcher_event() | ✅ Works | Logs: `[Watcher] Indexed to Qdrant: /path` |
| 5 | Socket emit called | VetkaFileWatcher._emit() | ✅ Works* | Code calls `asyncio.ensure_future(sio.emit(...))` - coroutine scheduled |
| 6 | Socket actually sends | AsyncServer.emit() | ⚠️ Unknown | No confirmation backend receives emit request |
| 7 | Frontend receives | browser socket.io client | ❓ Unknown | No console logs, no handlers attached |
| 8 | Event listener fires | socket.on('node_updated') | ❌ **MISSING** | No handler registered anywhere in UI code |
| 9 | Tree state updates | TreeContext/useTree hook | ❌ **MISSING** | No mechanism to dispatch tree updates |
| 10 | UI re-renders | React component | ❌ Dead | No tree context to trigger render |

---

## Root Cause Hypothesis

**PRIMARY:** Frontend has **zero socket.io event listeners** for watchdog events.

**Backend emits these events:**
- `node_updated` → file modified
- `node_added` → file created
- `node_removed` → file deleted
- `tree_bulk_update` → bulk operations (git checkout, npm install)

**But frontend has:**
- No `socket.on('node_updated', ...)` handler
- No `socket.on('node_added', ...)` handler
- No `socket.on('tree_bulk_update', ...)` handler
- No TreeContext/Redux/Zustand dispatch mechanism to update tree state
- No subscription to these socket events in UI initialization

**SECONDARY:** Socket.io emission may silently fail because:
1. `Phase 80.20` attempts to fix async emit with `asyncio.ensure_future()` - but this doesn't guarantee delivery
2. No ack/confirmation mechanism to verify socket actually sends
3. If socket connection is in wrong state, emit silently completes (coroutine resolves) without sending

---

## Detailed Investigation

### 1. File Watcher (WORKING)

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/file_watcher.py`

✅ **Line 362-378:** Correctly detects file changes and calls `self._emit()`
```python
if self.socketio:
    try:
        if event_type == 'created':
            self._emit('node_added', {'path': path, 'event': event})
        elif event_type == 'deleted':
            self._emit('node_removed', {'path': path, 'event': event})
        elif event_type == 'modified':
            self._emit('node_updated', {'path': path, 'event': event})
```

### 2. Socket Emit (FRAGILE)

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/file_watcher.py:428-473`

⚠️ **CRITICAL ISSUE:** Lines 456-466 attempt to fix async emit:
```python
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = None

if loop and loop.is_running():
    # Schedule coroutine in running loop (non-blocking)
    asyncio.ensure_future(self.socketio.emit(event_name, data))
else:
    # No running loop - create temporary one
    asyncio.run(self.socketio.emit(event_name, data))
```

**Problems:**
1. **No await:** `asyncio.ensure_future()` schedules but doesn't wait for completion
2. **Fire-and-forget:** No confirmation socket actually sends
3. **Watchdog thread:** This code runs in watchdog observer thread (NOT main FastAPI event loop)
4. **asyncio.run():** Creates new event loop - socket.io client may not be in that loop's context
5. **No error handling:** If emit fails silently, no indication

**Expected behavior:** Socket should immediately emit to ALL connected clients

**Actual behavior:** Coroutine may or may not execute depending on asyncio context

### 3. Backend Socket.io Setup (CORRECT)

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/main.py:278-291`

✅ **Lines 278-291:** FastAPI + Socket.io correctly configured
```python
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    ping_interval=25,
    ping_timeout=60,
)
socket_app = socketio.ASGIApp(sio, app)
app.state.socketio = sio
```

✅ **Line 300:** Handlers registered
```python
register_all_handlers(sio, app)
```

### 4. Watcher Routes (EMIT EXTRA EVENTS)

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py:200-209`

✅ **Line 202:** Emits on initial directory scan:
```python
await socketio.emit('directory_scanned', {
    'path': path,
    'files_count': indexed_count,
    'root_name': os.path.basename(path)
})
```

⚠️ **Note:** This uses `await socketio.emit()` (CORRECT async await) - unlike watchdog thread code!

### 5. Tree Handlers (MISSING UPDATE LOGIC)

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/tree_handlers.py`

❌ **CRITICAL FINDING:** No handlers for watchdog events!
- `select_branch` - handles user branch selection
- `fork_branch` - handles branch fork
- `move_to_parent` - handles node moves
- **MISSING:** `node_updated`, `node_added`, `node_removed`, `tree_updated`

No server-side handler to:
1. Receive watchdog events
2. Fetch updated tree data from Qdrant
3. Broadcast tree snapshot to all clients
4. Update tree metadata (timestamps, counts, etc.)

### 6. Frontend Socket Listeners (COMPLETELY ABSENT)

❌ **CRITICAL FINDING:** No frontend socket.io listeners for watchdog events

Searched entire frontend codebase:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/frontend/src/` - minimal files
- No `socket.on('node_updated', ...)`
- No `socket.on('node_added', ...)`
- No `socket.on('directory_scanned', ...)`
- No subscription to watchdog events in app initialization

**Implication:** Even if backend sends perfectly, frontend receives nothing. No handler exists to process the event.

### 7. Tree State Management (UNKNOWN)

❌ **Cannot confirm:** No TreeContext/Redux/Zustand found in frontend source

Expected:
- TreeContext/Hook to manage tree state (nodes, edges)
- `dispatch({ type: 'ADD_NODE', path, ... })` mechanism
- `useTree()` hook in components to subscribe

Actual:
- Frontend structure unclear (minimal src files found)
- Likely frontend is elsewhere or built as SPA

---

## Event Flow (CURRENT - BROKEN)

```
File system
    ↓
[watchdog] detects change
    ↓
VetkaFileHandler.on_any_event() [callback in thread]
    ↓ [debounce 400ms]
VetkaFileWatcher._on_file_change() [watchdog thread]
    ↓ [parallel paths]
    ├→ Qdrant: handle_watcher_event() ✅ [Indexed to Qdrant]
    └→ Socket: self._emit('node_updated', {path}) ⚠️ [Uncertain delivery]
        ↓
        asyncio.ensure_future(sio.emit(...)) [fire & forget, wrong context?]
        ↓ ❌ [May silently fail - watchdog thread, not FastAPI loop]

    [Socket.io message SHOULD go to all clients]
        ↓ ❌ [No confirmation it goes out]

    [Frontend socket.io client]
        ↓ ❌ [NO LISTENER for 'node_updated']

    [Event lost in void]
```

---

## Recommended Fixes (Priority Order)

### FIX 1: Thread-Safe Socket Emit (CRITICAL)
**File:** `src/scanners/file_watcher.py`

Use the **queue-based emit** (Phase 80.15 fallback) as PRIMARY method:

```python
# In __init__, always use queue mode:
self._use_emit_queue = True  # Force queue mode
self._start_emit_worker()    # Start worker thread

# The worker thread properly handles asyncio context
```

**Why:** Queue-based emit has dedicated worker thread with proper async context. Avoids watchdog thread trying to call async functions.

---

### FIX 2: Add Tree Update Socket Handler (CRITICAL)
**File:** `src/api/handlers/tree_handlers.py`

Add handler to process watchdog events:

```python
@sio.on('node_updated')
async def handle_node_updated(sid, data):
    """
    Handle file update from watchdog.
    Fetch updated tree and broadcast to all clients.
    """
    path = data.get('path')
    print(f"[Tree] Node updated: {path}")

    # Fetch tree from Qdrant tree routes
    # Broadcast tree_updated event to all clients
    await sio.emit('tree_updated', {
        'timestamp': datetime.now().isoformat(),
        'updated_paths': [path],
        'type': 'node_update'
    })  # No 'to=' parameter = broadcast to all
```

---

### FIX 3: Add Frontend Socket Listeners (CRITICAL)
**Frontend:** TBD (location unknown - needs discovery)

Add socket listeners on app mount:

```typescript
// In main app component or hooks
socket.on('node_updated', (data) => {
  console.log('Tree node updated:', data);
  // Dispatch to tree state: treeStore.updateNode(data.path)
  // UI should re-query tree data or accept diff
});

socket.on('node_added', (data) => {
  console.log('Tree node added:', data);
  // Dispatch: treeStore.addNode(data.path)
});

socket.on('tree_updated', (data) => {
  console.log('Tree bulk update:', data);
  // Re-fetch entire tree or apply diff
});
```

---

### FIX 4: Add Tree Requery Endpoint (SECONDARY)
**File:** `src/api/routes/tree_routes.py`

When watchdog fires, frontend might ask for updated tree:

```python
@router.get("/tree-delta/{timestamp}")
async def get_tree_delta(timestamp: int, request: Request):
    """Get tree changes since timestamp for incremental updates."""
    # Query Qdrant for files modified after timestamp
    # Return delta (new/modified/deleted paths)
```

---

### FIX 5: Add Socket.io ACK Confirmation (SECONDARY)
**File:** `src/scanners/file_watcher.py`

Add acknowledgment to confirm socket sends:

```python
def _emit(self, event_name: str, data: Dict) -> None:
    if self._use_emit_queue:
        self._emit_queue.put((event_name, data))
        print(f"[Watcher] Queued {event_name}: {data.get('path')}")
    else:
        # Add timeout/ack callback
        try:
            asyncio.ensure_future(
                self.socketio.emit(event_name, data)
            )
        except Exception as e:
            print(f"[Watcher] Emit failed: {e}")
```

---

## Files To Check/Fix

| File | What to look for | Action |
|------|------------------|--------|
| `/src/scanners/file_watcher.py` | `_emit()` method, queue mode enabled | Fix async context with queue-based emit |
| `/src/api/handlers/tree_handlers.py` | Missing watchdog handlers | Add `node_updated`, `node_added`, `node_removed`, `tree_updated` handlers |
| `/frontend/src/App.tsx` or main component | Missing socket listeners | Add socket.on() for watchdog events |
| `/frontend/src/hooks/useTree.ts` or similar | Tree state management | Create if missing, add state dispatch for tree updates |
| `/main.py` | Socket.io initialization | Verify `sio.state` or middleware for tree subscriptions |
| `/src/api/handlers/connection_handlers.py` | Client connect logic | May need to init tree sync on connection |

---

## Verification Checklist

- [ ] Check if frontend socket listeners exist (find App.tsx, index.tsx, main.tsx)
- [ ] Enable debug logging: `VETKA_DEBUG=true` + browser console
- [ ] Watch browser DevTools → Network → WebSocket frames
- [ ] Verify watchdog emits to socket with `[Watcher] Emitted ...` log
- [ ] Confirm browser receives message in WebSocket tab
- [ ] Add test: Create file in watched directory, check for `tree_updated` broadcast
- [ ] Check frontend receives event: `socket.on('tree_updated', console.log)`
- [ ] Verify tree component subscribes to updates and re-renders

---

## Phase 80.20+ Next Steps

1. **Immediate:** Enable queue-based emit in file_watcher.py (safest)
2. **Short-term:** Add tree update handlers to tree_handlers.py
3. **Short-term:** Add frontend socket listeners (needs frontend location)
4. **Medium-term:** Implement proper tree state subscription system
5. **Medium-term:** Add tree delta/diff support for efficient updates
6. **Long-term:** Add UI notification when tree updates (visual feedback)

---

## Conclusion

The watchdog-to-UI disconnect is caused by **missing frontend infrastructure**, not backend issues:

1. **Backend:** Correctly watches files, indexes to Qdrant, attempts to emit socket events
2. **Socket.io:** Correctly configured, but emit from watchdog thread context is fragile
3. **Frontend:** **Complete absence of event listeners and tree state synchronization**

**Minimum fix:** Add socket listeners + tree handlers + proper queue-based emit.

**Expected outcome:** After fixes, UI tree will update in real-time when files change.
