# HAIKU-6: Watchdog Async Investigation - Quick Reference

**Date:** 2026-01-27
**Status:** ROOT CAUSE IDENTIFIED
**Confidence:** 95%

---

## ONE-LINE SUMMARY

Watchdog is not "sleeping" - it's **BLOCKED by a 2-second sleep** in the callback handler that prevents processing subsequent file events.

---

## THE BUG

**File:** `src/scanners/file_watcher.py`
**Line:** 387
**Code:** `time.sleep(2)`

```python
def _on_file_change(self, event: Dict) -> None:
    # Called from timer thread
    
    qdrant_client = self._get_qdrant_client()
    
    if not qdrant_client:
        # ⚠️ THIS BLOCKS THE WATCHDOG THREAD FOR 2 SECONDS
        time.sleep(2)
        qdrant_client = self._get_qdrant_client()
```

---

## IMPACT

When files are created rapidly:
1. Watchdog detects file1 → queues it → starts 400ms debounce timer
2. Watchdog detects file2, file3 → queues them
3. Timer fires at 400ms → handler runs
4. Handler blocks on `time.sleep(2)` → **watchdog thread FROZEN**
5. While frozen, file2/file3 events accumulate
6. After 2s, handler resumes, processes file1
7. file2/file3 processed separately with additional delays

**Result:** 3-5 second cascading delays instead of <1 second response time

---

## WHY IT'S CRITICAL

- Timer callbacks run in **thread pool threads**, not the async event loop
- Blocking a thread pool thread prevents watchdog from processing new events
- This creates a "dead zone" where files added during the sleep are not immediately indexed
- Can cause race conditions where frontend requests data before indexing completes

---

## THREE SUPPORTING ISSUES

### Issue #2: Async Emit from Sync Context
**Location:** `src/scanners/file_watcher.py:483-504`

Timer thread tries to emit Socket.IO events without an event loop, creating fragile `asyncio.run()` calls.

### Issue #3: Inconsistent Queue Usage
**Location:** `src/scanners/file_watcher.py:356-423`

The emit_worker thread (lines 425-457) exists and works correctly, but `_on_file_change()` doesn't use it consistently.

---

## THE FIX (One of three approaches)

### Option A: Remove the Sleep (RECOMMENDED)
```python
if not qdrant_client:
    # Skip retry - Qdrant will be available on next event
    print(f"[Watcher] ⚠️ Qdrant unavailable: {path}")
    # No sleep, no retry
```

### Option B: Use Non-Blocking State Flag
```python
if not qdrant_client and not hasattr(self, '_logged_qdrant_warning'):
    # Only log warning once per burst
    print(f"[Watcher] ⚠️ Qdrant unavailable, continuing without indexing")
    self._logged_qdrant_warning = True
```

### Option C: Route Through Emit Queue
```python
# Always use queue-based emit
self._use_emit_queue = True  # Force in __init__
self._emit_queue.put(('file_changed', event_data))
```

---

## MARKERS PLACED

```
TODO_95.9: MARKER_WATCHDOG_001 - BLOCKING SLEEP (Line 387)
TODO_95.9: MARKER_WATCHDOG_002 - ASYNC EMIT SAFETY (Lines 483-504)
TODO_95.9: MARKER_WATCHDOG_003 - QUEUE INTEGRATION (Lines 356-423)
```

---

## VERIFICATION

To see the bug in action:
1. Start VETKA
2. Watch a directory
3. Rapidly create 5-10 files in that directory
4. Look at console:
   - If you see `[Watcher] Retrying qdrant_client after 2s` → BUG CONFIRMED
   - If subsequent files have delays → BUG CONFIRMED

---

## ARCHITECTURE

**Current (Broken):**
```
watchdog thread ─────┬─ handler: on_any_event() [SYNC]
                     └─ timer: _on_file_change() [BLOCKS on sleep(2)]
                        └─ emit: socketio.emit() [creates temp event loops]
```

**Better (Recommended):**
```
watchdog thread ──┬─ handler: on_any_event() [SYNC, responsive]
                  └─ timer: _on_file_change() [fast, queues emit]
                     └─ emit_queue.put()

emit_worker thread ─ async: socketio.emit() [dedicated loop, safe]
```

---

## FILES MODIFIED

None yet - this is just investigation. Markers added for future fixes.

---

## NEXT STEPS

1. Remove the 2-second sleep (Option A)
2. Ensure `_use_emit_queue=True` by default
3. Test with rapid file creation
4. Verify no cascading delays

---

## REFERENCE

Full report: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/95_ph/HAIKU_TEST_6_WATCHDOG_ASYNC.md` (528 lines, 16KB)

Key code: `src/scanners/file_watcher.py` lines 356-504
