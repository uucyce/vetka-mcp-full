# Phase 80.20: Fix Socket Async Emit

**Date:** 2026-01-22
**Status:** FIXED
**File:** `src/scanners/file_watcher.py`

---

## Problem

The `file_watcher.py` was calling `self.socketio.emit()` without `await`, but `self.socketio` is a `socketio.AsyncServer` where `emit()` is a coroutine method.

```python
# Line 439 (BEFORE - BROKEN)
self.socketio.emit(event_name, data)  # Creates coroutine object, never executes!
```

### Symptoms
- Backend logs showed "Emitted" messages
- Frontend never received socket events from file watcher
- File changes were detected but not propagated to UI
- Tree view didn't update on file create/modify/delete

### Root Cause
- `emit()` on `AsyncServer` returns a coroutine
- Calling without `await` creates a coroutine object
- Python garbage collects the unawaited coroutine
- No error is raised, making debugging difficult

---

## Solution

### Direct Emit Mode (Default)

Properly schedule the coroutine from sync context:

```python
def _emit(self, event_name: str, data: Dict) -> None:
    if not self.socketio:
        return

    try:
        import asyncio

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

        print(f"[Watcher] Emitted {event_name}: {data.get('path', 'unknown')}")

    except Exception as e:
        print(f"[Watcher] Emit error for {event_name}: {e}")
```

### Queue Mode (Fallback)

For thread safety, the queue worker now creates its own event loop:

```python
def worker():
    # Create dedicated event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        event_name, data = self._emit_queue.get()
        if event_name is None:  # Shutdown signal
            break
        if self.socketio:
            # Run coroutine in thread's event loop
            loop.run_until_complete(self.socketio.emit(event_name, data))

    loop.close()
```

---

## Alternative: Use Queue Mode by Default

If direct emit still has issues, enable queue mode in `get_watcher()`:

```python
# In components_init.py or wherever watcher is created
watcher = get_watcher(socketio=sio, use_emit_queue=True)
```

Queue mode is more reliable because:
1. Dedicated thread with its own event loop
2. No race conditions between watchdog thread and main async loop
3. Events are processed sequentially

---

## Verification

1. Start VETKA backend
2. Make a file change in watched directory
3. Check backend logs for: `[Watcher] Emitted node_updated: /path/to/file`
4. Check browser console for socket events: `node_updated`, `node_added`, `node_removed`
5. Tree view should update automatically

---

## Files Modified

- `src/scanners/file_watcher.py`
  - Updated `_emit()` method to handle async coroutine
  - Updated `_start_emit_worker()` with dedicated event loop
  - Updated header docstring with Phase 80.20

---

## Related Issues

- Phase 80.15: Initial queue-based emit (had same async bug)
- Phase 80.17: Lazy Qdrant client fetch (separate issue)

---

## Lesson Learned

When using `python-socketio` AsyncServer from synchronous code:
- Always use `asyncio.ensure_future()` or `asyncio.run()` to execute coroutines
- Backend "success" logs don't mean emit actually happened
- Test by checking frontend receives events, not just backend logs
