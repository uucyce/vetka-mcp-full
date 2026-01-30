# WATCHDOG NOT TRIGGERING - AUDIT REPORT

**Phase:** 82_ph_ui_fixes
**Issue:** Watchdog observes directory but doesn't index new files in Qdrant
**Status:** ROOT CAUSE IDENTIFIED
**Date:** 2026-01-21

---

## EXECUTIVE SUMMARY

The watchdog is **working correctly**, BUT **the file change events are not being processed for Qdrant indexing**.

When files are added to `docs/81_ph_mcp_fixes/`:
- ✅ Watchdog observes the file creation event
- ✅ VetkaFileHandler debounces the event properly
- ✅ Socket.IO events are emitted to frontend
- ❌ **NO Qdrant indexing occurs**

**Root Cause:** The `_on_file_change()` method in `VetkaFileWatcher` only emits Socket.IO events but **NEVER calls the QdrantIncrementalUpdater to index files**.

---

## INVESTIGATION FINDINGS

### 1. VetkaFileHandler - WORKS CORRECTLY

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/file_watcher.py`

Lines 54-146: The `VetkaFileHandler` class properly:
- Filters directory events (line 81-82)
- Filters ignored patterns (line 87-88)
- **Filters by supported extensions** (line 90-93)
  ```python
  SUPPORTED_EXTENSIONS = {
      '.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.yaml', '.yml',
      '.md', '.txt', '.html', '.css', '.scss', '.sql', '.sh',
      '.java', '.go', '.rs', '.rb', '.php', '.c', '.cpp', '.h',
      '.swift', '.kt', '.scala', '.vue', '.svelte'
  }
  ```
- Debounces events with 400ms default (lines 103-112)
- Coalesces multiple events properly (lines 132-142)

✅ **.md files ARE supported** - so new markdown files in docs/81_ph_mcp_fixes/ should trigger events.

### 2. VetkaFileWatcher._on_file_change() - MISSING QDRANT CONNECTION

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/file_watcher.py`

Lines 329-365: The `_on_file_change()` callback does:
```python
def _on_file_change(self, event: Dict) -> None:
    """Handle file change event from handler."""
    event_type = event['type']
    path = event['path']

    print(f"[Watcher] {event_type}: {path}")

    # Update adaptive scanner heat
    dir_path = os.path.dirname(path)
    self.adaptive_scanner.update_heat(dir_path, event_type)
    self.adaptive_scanner.maybe_decay()

    # Emit to frontend via Socket.IO
    if self.socketio:
        try:
            if event_type == 'created':
                self._emit('node_added', {'path': path, 'event': event})
            elif event_type == 'deleted':
                self._emit('node_removed', {'path': path, 'event': event})
            elif event_type == 'modified':
                self._emit('node_updated', {'path': path, 'event': event})
            # ... more events
        except Exception as e:
            print(f"[Watcher] Error emitting socket event: {e}")
```

**PROBLEM:** No Qdrant indexing! Missing:
- No call to `QdrantIncrementalUpdater.update_file()`
- No call to `handle_watcher_event()` from qdrant_updater.py

### 3. QdrantIncrementalUpdater - HAS THE RIGHT CODE

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/qdrant_updater.py`

Lines 516-553: The `handle_watcher_event()` function exists and handles:
```python
def handle_watcher_event(event: Dict[str, Any], qdrant_client: Optional[Any] = None) -> bool:
    """Handle file watcher event and update Qdrant."""
    updater = get_qdrant_updater(qdrant_client)
    event_type = event.get('type', '')
    path = event.get('path', '')

    if event_type == 'created':
        return updater.update_file(file_path)
    elif event_type == 'modified':
        return updater.update_file(file_path)
    elif event_type == 'deleted':
        return updater.soft_delete(file_path)
    # ...
```

**BUT:** This function is **NEVER CALLED** from the watcher!

### 4. Initial Scan Works Fine

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py`

Lines 73-218 (`add_watch_directory` endpoint): When adding a directory to watch:
- ✅ Walks the directory tree (line 131)
- ✅ Filters ignored directories (lines 133-134)
- ✅ Reads file content (line 149)
- ✅ Generates embeddings (line 160)
- ✅ **Upserts to Qdrant** (line 185-188)
- ✅ Emits socket event (line 200)

**This works great - initial indexing happens!** But new files added AFTER the initial watch are not indexed.

### 5. Watcher State Shows docs/81_ph_mcp_fixes IS WATCHED

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/watcher_state.json`

```json
{
  "watched_dirs": [
    "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03",
    "/Users/danilagulin/Documents/CinemaFactory/workflows",
    "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client",
    "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/81_ph_mcp_fixes",
    "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/72_ph",
    "/Users/danilagulin/Documents/adult-doc"
  ],
  "heat_scores": {},
  "saved_at": 1769012781.966613
}
```

✅ The directory IS being watched.

---

## ROOT CAUSE ANALYSIS

### The Missing Link

The architecture has a gap between:

1. **File Watcher** (works)
   - Observes files
   - Emits Socket.IO events
   - Updates heat scores

2. **Qdrant Updater** (works)
   - Can index individual files
   - Can batch update multiple files
   - Has proper embedding + upsert logic

3. **Missing Connection:**
   - `VetkaFileWatcher._on_file_change()` does NOT call `handle_watcher_event()`
   - No way to get the Qdrant client in the watcher
   - No async context to wait for embeddings

### Why This Happened

The watcher was designed to:
- Detect file changes (done)
- Update the frontend UI (done via Socket.IO)
- But incremental Qdrant updates were planned but not connected

The initial scan (in watcher_routes.py) bypasses the watcher entirely and directly indexes files. But ongoing file changes have no path to Qdrant.

---

## SUPPORTED FILE EXTENSIONS

Watchdog **WILL** trigger for these files in docs/81_ph_mcp_fixes/:

```python
SUPPORTED_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.yaml', '.yml',
    '.md', '.txt', '.html', '.css', '.scss', '.sql', '.sh',
    '.java', '.go', '.rs', '.rb', '.php', '.c', '.cpp', '.h',
    '.swift', '.kt', '.scala', '.vue', '.svelte'
}
```

✅ `.md` files ARE supported
✅ Watchdog WILL detect them
❌ But Qdrant won't index them

---

## DEBOUNCE ANALYSIS

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/file_watcher.py`

Lines 63-112: VetkaFileHandler initialization:
```python
def __init__(self, on_change_callback: Callable[[Dict], None], debounce_ms: int = 400):
    self.debounce_ms = debounce_ms  # Default: 400ms
    self.pending: Dict[str, List[Dict]] = defaultdict(list)
    self.timers: Dict[str, threading.Timer] = {}
    # ...
```

The debounce mechanism:
- Collects events in `self.pending` (line 96-101)
- Creates a timer for each file (line 107-111)
- Cancels and restarts timer on new events (line 104-105)
- Fires callback after 400ms of inactivity (line 109)

✅ **Debounce is working correctly**
❌ **But the callback doesn't do anything with Qdrant**

---

## EVENT FLOW

When a file is created in `docs/81_ph_mcp_fixes/`:

```
1. watchdog.observers detects file creation
2. VetkaFileHandler.on_any_event() called
3. Checks: is_directory? No
4. Checks: should_skip()? No
5. Checks: extension supported? YES (.md is supported)
6. Adds to pending events
7. Starts 400ms debounce timer
8. After 400ms, calls callback(_process_batch)
9. Coalesces events
10. Calls VetkaFileWatcher._on_file_change()
11. ❌ STOPS HERE - only emits Socket.IO event
12. ❌ Never calls handle_watcher_event()
13. ❌ Never indexes in Qdrant
```

---

## COMPARISON: How Initial Scan Works

When you call `/api/watcher/add` with docs/81_ph_mcp_fixes/:

```
1. API receives request with path
2. add_watch_directory() starts watching with observer
3. IMMEDIATELY walks directory (line 131)
4. For each file:
   - Reads content
   - Generates embedding (via updater._get_embedding)
   - Creates PointStruct
   - Upserts to Qdrant
5. Emits socket event
```

This works because it **directly interfaces with Qdrant**, not through the watcher callback.

---

## VERIFICATION

To verify the issue, check logs for:

### What You'll See (Working)
```
[Watcher] created: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/81_ph_mcp_fixes/NEW_FILE.md
[Watcher] Emitted node_added: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/81_ph_mcp_fixes/NEW_FILE.md
```

### What You Won't See (Missing)
```
[QdrantUpdater] Updated: NEW_FILE.md
[QdrantUpdater] Batch updated: 1 files
```

---

## FIX STRATEGY

To fix this, connect the watcher to Qdrant:

### Option A: Direct Integration (Recommended)
Modify `VetkaFileWatcher._on_file_change()` to:
1. Get Qdrant client from app state
2. Call `handle_watcher_event(event, qdrant_client)`
3. Log the result

### Option B: Socket.IO Trigger
Emit a special Socket.IO event that the backend processes to index in Qdrant.

### Option C: Async Task Queue
Add Qdrant indexing task to a queue (Redis, RabbitMQ, etc.)

### Requirements for Fix
- Must have access to Qdrant client (from app state)
- Must handle embedding errors gracefully
- Must not block the watcher callback (use async)
- Must log success/failure

---

## SUMMARY TABLE

| Component | Status | Issue |
|-----------|--------|-------|
| watchdog.observers | ✅ Working | - |
| VetkaFileHandler.on_any_event() | ✅ Working | - |
| Extension filtering (.md) | ✅ Working | - |
| Debounce (400ms) | ✅ Working | - |
| Coalesce events | ✅ Working | - |
| VetkaFileWatcher._on_file_change() | ⚠️ Partial | No Qdrant call |
| Socket.IO emit | ✅ Working | - |
| QdrantIncrementalUpdater | ✅ Working | Never called from watcher |
| handle_watcher_event() | ✅ Ready | Never called |
| Initial scan (/api/watcher/add) | ✅ Working | - |

---

## FILES INVOLVED

- **File Watcher:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/file_watcher.py` (526 lines)
- **Qdrant Updater:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/qdrant_updater.py` (554 lines)
- **Watcher Routes:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py` (630 lines)
- **Watcher State:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/watcher_state.json`

---

## CONCLUSION

The watchdog is **NOT failing to trigger** - it's working correctly. The real issue is a **missing integration** between the watcher's file change callbacks and the Qdrant indexing system.

**Priority:** Medium-High (affects real-time knowledge graph updates)
**Complexity:** Low (straightforward function call addition)
**Impact:** High (enables live indexing of new files)

The fix is simple: make `VetkaFileWatcher._on_file_change()` call Qdrant indexing logic after emitting Socket.IO events.
