# Phase 80.15: Fix Watchdog Tree Update

## Summary

Fixed the `_emit()` method in `file_watcher.py` to properly emit Socket.IO events from the watchdog thread to the frontend.

## Root Cause

The original `_emit()` method (lines 382-404) was broken:

```python
# BROKEN CODE - asyncio.create_task() in lambda doesn't work
loop.call_soon_threadsafe(
    lambda: asyncio.create_task(self.socketio.emit(event_name, data))
)
# Also asyncio.run() blocks the watchdog thread
asyncio.run(self.socketio.emit(event_name, data))
```

Problems:
1. `asyncio.create_task()` inside a lambda passed to `call_soon_threadsafe()` doesn't work correctly
2. `asyncio.run()` blocks the watchdog thread and can cause issues
3. Events never reached the frontend

## Solution

### Primary Fix: Direct Emit Pattern

Used the same simple pattern that works in `components_init.py:163-171`:

```python
def _emit(self, event_name: str, data: Dict) -> None:
    """
    Phase 80.15: Thread-safe socket emit using direct call.
    """
    if not self.socketio:
        print(f"[Watcher] No socketio - cannot emit {event_name}")
        return

    try:
        # Direct emit - python-socketio handles threading internally
        self.socketio.emit(event_name, data)
        print(f"[Watcher] Emitted {event_name}: {data.get('path', 'unknown')}")
    except Exception as e:
        print(f"[Watcher] Emit error for {event_name}: {e}")
        import traceback
        traceback.print_exc()
```

**Why this works:** python-socketio's `emit()` method is internally thread-safe.

### Fallback: Queue-Based Pattern

Added optional queue-based emit for edge cases where direct emit might not work:

```python
# Enable with: get_watcher(socketio=sio, use_emit_queue=True)
```

This creates a background worker thread that processes emit events from a queue.

## Files Modified

**`/src/scanners/file_watcher.py`**

| Lines | Change |
|-------|--------|
| 5-8 | Updated phase to 80.15, lastAudit to 2026-01-22 |
| 243-269 | Added `use_emit_queue` parameter to `__init__` |
| 391-445 | New `_start_emit_worker()` and rewritten `_emit()` |
| 482-504 | Updated `stop_all()` to cleanup emit worker |
| 552-570 | Updated `get_watcher()` factory with new parameter |

## Testing

1. Start the VETKA server
2. Open the UI and add a folder to watch
3. Create/modify/delete a file in the watched folder
4. Verify console shows:
   - `[Watcher] Emitted node_added: /path/to/file`
   - `[Watcher] Emitted node_updated: /path/to/file`
   - `[Watcher] Emitted node_removed: /path/to/file`
5. Verify the 3D tree updates in the UI

## If Direct Emit Fails

If you see emit errors, enable queue mode:

```python
# In initialization code
from src.scanners.file_watcher import get_watcher
watcher = get_watcher(socketio=sio, use_emit_queue=True)
```

## Technical Notes

- python-socketio handles thread safety internally
- The watchdog library spawns events in separate threads
- Queue pattern adds minimal latency but guarantees thread safety
- Worker thread is daemon=True (won't block process exit)
- Shutdown signal `(None, None)` cleanly stops the worker

## Related Issues

- Phase 87: watchdog_fix investigation
- Scout report: identified asyncio threading issue

---
**Phase:** 80.15
**Date:** 2026-01-22
**Status:** COMPLETE
