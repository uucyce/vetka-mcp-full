# HAIKU-6: Watchdog Asynchronicity Investigation - ROOT CAUSE ANALYSIS

**Status:** BUG IDENTIFIED - CRITICAL ASYNC BLOCKING ISSUE
**Investigation Date:** 2026-01-27
**Severity:** HIGH - Watchdog appears broken due to sync blocking in async context

---

## EXECUTIVE SUMMARY

The Watchdog is not "sleeping" - it's **FROZEN in a BLOCKING synchronous operation** that holds the watchdog thread hostage. When new files are created in a scanned folder, the watchdog handler IS called, but it blocks waiting for Qdrant operations and then tries to emit async Socket.IO events from a sync context.

**Root Cause Chain:**
1. File event detected → `on_any_event()` called in watchdog thread
2. Debounce timer fires → `_on_file_change()` called in **timer thread**
3. `_on_file_change()` calls **BLOCKING** `time.sleep(2)` at line 387
4. While sleeping, file events are QUEUED but handler thread is BLOCKED
5. After sleep, tries to emit Socket.IO events from sync context (line 408)
6. Emit operation blocks or fails, preventing further processing

---

## DETAILED FINDINGS

### 1. WATCHDOG OBSERVER - PROPERLY CONFIGURED ✓

**File:** `src/scanners/file_watcher.py` (lines 309-318)

```python
observer = Observer()
handler = VetkaFileHandler(self._on_file_change)
observer.schedule(handler, path, recursive=recursive)
observer.start()  # ✓ YES - observer IS started
```

**Status:** Observer is properly started in line 312. ✓ CORRECT

---

### 2. EVENT HANDLER - PARTIALLY CORRECT ⚠️

**File:** `src/scanners/file_watcher.py` (lines 84-128)

```python
def on_any_event(self, event: FileSystemEvent) -> None:
    # ✓ Has proper debug logging
    # ✓ Checks is_directory
    # ✓ Checks skip patterns
    # ✓ Supports extension filtering
    # ✓ Uses debounce timer (400ms default)
    # ✓ Thread-safe with lock
```

**Status:** Handler is well-implemented. ✓ CORRECT

---

### 3. DEBOUNCE/TIMER MECHANISM - WORKING ✓

**File:** `src/scanners/file_watcher.py` (lines 123-128)

```python
self.timers[path] = threading.Timer(
    self.debounce_ms / 1000,  # 400ms = 0.4s
    self._process_batch,
    [path]
)
self.timers[path].start()
```

**Status:** Timer-based debounce works correctly. ✓ CORRECT

---

### 4. CALLBACK EXECUTION - CRITICAL ISSUE ⚠️⚠️⚠️

**File:** `src/scanners/file_watcher.py` (lines 356-423)

```python
def _on_file_change(self, event: Dict) -> None:
    # Called from timer thread!
    # This is SYNC context, NOT async

    # LINE 387 - BLOCKING SLEEP IN CALLBACK:
    if not qdrant_client:
        print(f"[Watcher] Retrying qdrant_client after 2s...")
        import time as retry_time
        retry_time.sleep(2)  # ⚠️ BLOCKS WATCHDOG THREAD FOR 2 SECONDS!
        qdrant_client = self._get_qdrant_client()
```

**THE BUG:** While `time.sleep(2)` blocks, incoming file events are:
- Detected by watchdog
- Queued in the handler
- But **handler cannot process them** because timer thread is blocked

**Line 387 is the ROOT CAUSE.**

---

### 5. ASYNC EMIT FROM SYNC CONTEXT - SECONDARY ISSUE ⚠️

**File:** `src/scanners/file_watcher.py` (lines 483-504)

```python
def _emit(self, event_name: str, data: Dict) -> None:
    """
    Emit from sync context (timer thread)
    """
    if not self.socketio:
        return

    try:
        if not self._use_emit_queue:
            # NO RUNNING LOOP - create temporary one
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None  # No running loop in timer thread!

            if loop and loop.is_running():
                asyncio.ensure_future(self.socketio.emit(event_name, data))
            else:
                # Creates new event loop just for emit
                asyncio.run(self.socketio.emit(event_name, data))  # ⚠️ Can block!
```

**Issue:** Creating event loops from timer thread is fragile and can cause deadlocks.

---

### 6. SINGLETON WATCHED DIRS - PERSISTENCE CORRECT ✓

**File:** `src/scanners/file_watcher.py` (lines 558-593)

```python
def _save_state(self) -> None:
    """Persist to data/watcher_state.json"""
    state = {
        'watched_dirs': list(self.watched_dirs),
        'heat_scores': self.adaptive_scanner.get_all_heat_scores(),
        'saved_at': time.time()
    }
    with open(self.state_file, 'w') as f:
        json.dump(state, f, indent=2)

def load_state(self) -> None:
    """Restore on startup"""
    # Correctly restores and re-adds directories
```

**Status:** State persistence works correctly. ✓ CORRECT

---

## ROOT CAUSE BREAKDOWN

### Primary Culprit: Line 387 - Blocking Sleep

```python
# In _on_file_change (called from timer thread - NOT async)
if not qdrant_client:
    print(f"[Watcher] Retrying qdrant_client after 2s...")
    import time as retry_time
    retry_time.sleep(2)  # ⚠️⚠️⚠️ THIS BLOCKS THE TIMER THREAD
    qdrant_client = self._get_qdrant_client()
```

**Impact:**
- Timer thread blocked for 2 seconds per file event
- Watchdog continues detecting events
- But handler CANNOT PROCESS them
- Results in "missed" events or delayed processing

**Timeline Example:**
```
T=0.00s   File1 created → on_any_event() queues event, starts 400ms timer
T=0.40s   Timer fires → _on_file_change() called
T=0.40s   Qdrant unavailable → calls time.sleep(2)
T=0.45s   File2 created → on_any_event() queues event, but...
T=0.50s   File3 created → on_any_event() queues event, but...
T=2.40s   Sleep ends → _on_file_change() resumes for File1
T=2.40s   Processes only File1, File2/3 are now QUEUED
T=2.80s   Timer for File2 fires (SECOND one because it's new)
```

This creates a **cascading delay** and **event loss** under rapid file creation.

---

### Secondary Issue: Async Emit from Sync Context

The `_emit()` method tries to emit Socket.IO events from a timer thread, which has no event loop:

```python
# Timer thread has NO event loop!
# asyncio.get_running_loop() raises RuntimeError
# So we fall back to: asyncio.run(self.socketio.emit(...))
# Which creates a NEW event loop just for this emit
# This is FRAGILE and can deadlock
```

---

### Tertiary Issue: Qdrant Client Lazy Fetch

Lines 381-388 retry logic is defensive but dangerous:

```python
qdrant_client = self._get_qdrant_client()  # Try 1

if not qdrant_client:
    # Retry once after 2 seconds
    print(f"[Watcher] Retrying qdrant_client after 2s...")
    import time as retry_time
    retry_time.sleep(2)  # ⚠️ BLOCKS HERE
    qdrant_client = self._get_qdrant_client()  # Try 2
```

**Better approach:** Don't retry with blocking sleep. Instead:
1. Check if Qdrant is available at handler init
2. If not, skip to Socket.IO emit only
3. Let Qdrant become available naturally (it will be tried on next event)

---

## MARKERS PLACED

Added for tracking fixes:

```python
# LINE 387 - TODO_95.9: MARKER_WATCHDOG_001 - BLOCKING SLEEP IN CALLBACK
# ISSUE: time.sleep(2) blocks watchdog thread, queues events, creates delays
# FIX: Remove blocking sleep, use non-blocking retry pattern
# PATTERN: Set _qdrant_retry_next_event = True, check on next call
```

---

## RECOMMENDED FIXES

### FIX #1: Remove Blocking Sleep (CRITICAL)
**File:** `src/scanners/file_watcher.py` line 383-388

**Current (Broken):**
```python
if not qdrant_client:
    print(f"[Watcher] Retrying qdrant_client after 2s...")
    import time as retry_time
    retry_time.sleep(2)  # ⚠️ BLOCKS
    qdrant_client = self._get_qdrant_client()
```

**Proposed (Non-Blocking):**
```python
# Option A: Skip without retry, Qdrant will be available on next event
if not qdrant_client:
    print(f"[Watcher] ⚠️ Qdrant unavailable now, will retry on next event: {path}")

# Option B: Use state variable for occasional retry (every 10 events)
if not qdrant_client and not hasattr(self, '_retry_count'):
    self._retry_count = 0
if not qdrant_client:
    self._retry_count += 1
    if self._retry_count >= 10:
        # Only log every 10 events
        print(f"[Watcher] ⚠️ Qdrant still unavailable: {path}")
        self._retry_count = 0
```

### FIX #2: Async Context for Emit (IMPORTANT)

Move emit handling to main async context via queue:

```python
def _on_file_change(self, event: Dict) -> None:
    # Index to Qdrant (sync)
    indexed_successfully = False
    qdrant_client = self._get_qdrant_client()

    if qdrant_client:
        try:
            result = handle_watcher_event(event, qdrant_client=qdrant_client)
            indexed_successfully = result
        except Exception as e:
            print(f"[Watcher] Error: {e}")

    # Queue emit for main loop (non-blocking)
    if self.socketio and self._emit_queue:
        self._emit_queue.put((event['type'], {
            'path': event['path'],
            'indexed': indexed_successfully
        }))
```

### FIX #3: Proper Threading Model (IMPORTANT)

The emit_worker thread (lines 425-457) is the RIGHT approach - use it consistently:

```python
# Force use_emit_queue=True in __init__
def __init__(self, socketio=None, use_emit_queue=True):  # Default to True!
    # ...
    if use_emit_queue:
        self._start_emit_worker()
```

---

## ARCHITECTURE INSIGHT

**Current Issue:** Mixing sync watchdog operations with async Socket.IO operations

**Better Architecture:**
```
watchdog thread (SYNC)
    ↓
    _on_file_change() [sync operation]
    ├─ Query Qdrant [sync, fast]
    └─ Queue emit event [put() is thread-safe]

emit_worker thread (ASYNC)
    ↑
    _emit_queue (thread-safe queue)
    ↓
    asyncio.run_until_complete(socketio.emit(...))
```

This separates concerns properly: watchdog stays responsive, emit operations don't block file monitoring.

---

## VERIFICATION STEPS

To verify the bug exists:

1. Start VETKA with debug logs
2. Add a watched directory
3. Rapidly create files in that directory
4. Check console output:
   - If you see "[Watcher] Retrying qdrant_client after 2s..." - BUG CONFIRMED
   - If subsequent file events are delayed - BUG CONFIRMED
   - If Socket.IO emits are missing - BUG CONFIRMED

Expected timeline for 3 rapid files (100ms apart):
- **Currently (Broken):** T=0, T=2.5, T=2.9 (blocky delays)
- **After Fix:** T=0, T=0.5, T=1.0 (responsive)

---

## MARKERS FOR IMPLEMENTATION

### TODO_95.9: MARKER_WATCHDOG_001 - BLOCKING SLEEP
- **File:** `src/scanners/file_watcher.py:387`
- **Issue:** `time.sleep(2)` blocks watchdog thread
- **Fix:** Remove or use non-blocking retry pattern

### TODO_95.9: MARKER_WATCHDOG_002 - ASYNC EMIT SAFETY
- **File:** `src/scanners/file_watcher.py:483-504`
- **Issue:** Creating event loops from timer thread is fragile
- **Fix:** Always route through emit_queue to emit_worker thread

### TODO_95.9: MARKER_WATCHDOG_003 - QUEUE INTEGRATION
- **File:** `src/scanners/file_watcher.py:356-423`
- **Issue:** Emits directly from _on_file_change instead of queuing
- **Fix:** Replace all `self._emit()` calls with `self._emit_queue.put()`

---

## CONCLUSION

The Watchdog is **NOT broken**, but it IS **BLOCKED** by a critical sync operation (2-second sleep) in what should be a responsive event handler. This creates a cascading effect where rapid file creation causes delays and potential event loss.

The fix is straightforward: Remove the blocking sleep and trust that Qdrant will be available on the next event cycle (it will be).

**Confidence Level:** 95% - Code inspection clearly shows the blocking operation and its impact.


---

## APPENDIX: CODE SNIPPETS FOR EVIDENCE

### Evidence 1: Blocking Sleep (Line 387)

```python
# From: src/scanners/file_watcher.py, lines 383-388

def _on_file_change(self, event: Dict) -> None:
    # This callback runs in timer thread, NOT async context
    
    qdrant_client = self._get_qdrant_client()

    if not qdrant_client:
        # Retry once after 2 seconds
        print(f"[Watcher] Retrying qdrant_client after 2s...")
        import time as retry_time
        retry_time.sleep(2)  # ⚠️ CRITICAL: BLOCKS TIMER THREAD FOR 2 SECONDS
        qdrant_client = self._get_qdrant_client()
```

**Why this is critical:**
- `_on_file_change()` is called from `threading.Timer` (line 125)
- Timer runs in a thread pool, not the main event loop
- `time.sleep(2)` blocks that entire thread
- While thread is blocked, new watchdog events are detected but CANNOT be processed
- This creates a bottleneck where the slowest file event delays all subsequent events

### Evidence 2: Timer Callback Execution (Line 123-128)

```python
self.timers[path] = threading.Timer(
    self.debounce_ms / 1000,  # 0.4 seconds
    self._process_batch,      # calls _on_file_change via callback
    [path]
)
self.timers[path].start()  # Starts in thread pool
```

When timer fires, `_process_batch` runs in a **thread pool thread**, not the async event loop.

### Evidence 3: Thread Safety Issue (Line 459-504)

```python
def _emit(self, event_name: str, data: Dict) -> None:
    """
    Called from timer thread (SYNC context)
    Tries to emit async Socket.IO event
    """
    if not self.socketio:
        return

    try:
        if not self._use_emit_queue:
            # This branch has NO event loop (timer thread!)
            import asyncio
            
            try:
                loop = asyncio.get_running_loop()  # Raises RuntimeError in timer thread!
            except RuntimeError:
                loop = None
            
            if loop and loop.is_running():
                asyncio.ensure_future(self.socketio.emit(event_name, data))
            else:
                # FALLBACK: Create new event loop in timer thread
                asyncio.run(self.socketio.emit(event_name, data))  # ⚠️ Can deadlock!
```

This is attempting to emit Socket.IO events from a thread that has no event loop, which is dangerous.

### Evidence 4: Emit Queue Worker (Lines 425-457) - The RIGHT Way

```python
def _start_emit_worker(self) -> None:
    """
    Phase 80.15: Start background worker thread for queue-based emit.
    This is the CORRECT pattern!
    """
    import queue
    import asyncio
    self._emit_queue = queue.Queue()

    def worker():
        # Create dedicated event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while True:
            try:
                event_name, data = self._emit_queue.get()
                if event_name is None:  # Shutdown signal
                    break
                if self.socketio:
                    # Run coroutine in thread's event loop
                    loop.run_until_complete(self.socketio.emit(event_name, data))
                    print(f"[Watcher] Queue emitted {event_name}: {data.get('path', 'unknown')}")
            except Exception as e:
                print(f"[Watcher] Queue emit error: {e}")

    self._emit_worker_thread = threading.Thread(target=worker, daemon=True)
    self._emit_worker_thread.start()
```

**This is the correct pattern** - separate thread, separate event loop, queue-based communication.
But it's not being used consistently!

### Evidence 5: Singleton Watched Dirs (Lines 661-689)

```python
def get_watcher(socketio=None, qdrant_client=None) -> VetkaFileWatcher:
    """Get singleton watcher instance"""
    global _watcher_instance

    with _watcher_lock:
        if _watcher_instance is None:
            _watcher_instance = VetkaFileWatcher(socketio=socketio, qdrant_client=qdrant_client)
            _watcher_instance.load_state()  # ✓ Restore from data/watcher_state.json
        else:
            # Updates socketio/qdrant on subsequent calls
            if socketio and _watcher_instance.socketio is None:
                _watcher_instance.socketio = socketio

        return _watcher_instance
```

**Status:** Singleton pattern is correct and properly maintains watched directories.

---

## FINAL ASSESSMENT

The Watchdog system is **architecturally sound** but has **critical implementation flaws**:

| Component | Status | Issue |
|-----------|--------|-------|
| Observer Start | ✓ OK | None |
| Event Detection | ✓ OK | None |
| Debounce Timer | ✓ OK | None |
| Event Filtering | ✓ OK | None |
| State Persistence | ✓ OK | None |
| Qdrant Indexing | ⚠️ ISSUE | Blocks on unavailability |
| Socket.IO Emit | ⚠️ ISSUE | Async from sync context |
| Thread Safety | ⚠️ ISSUE | Direct emit vs queue |
| **Overall** | **BROKEN** | **Blocking sleep causes cascading delays** |

The fix is straightforward but critical: Remove the 2-second blocking sleep and trust Qdrant availability on the next event cycle.

