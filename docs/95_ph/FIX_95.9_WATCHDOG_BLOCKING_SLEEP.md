# FIX_95.9: Watchdog Blocking Sleep Fix

**Date**: 2026-01-27
**Phase**: 95.9
**Status**: COMPLETED
**Author**: OPUS

## Problem Identified

HAIKU-6 found ROOT CAUSE at `src/scanners/file_watcher.py` line 387:

```python
# PROBLEMATIC CODE (removed):
if not qdrant_client:
    # Retry once after 2 seconds
    print(f"[Watcher] Retrying qdrant_client after 2s...")
    import time as retry_time
    retry_time.sleep(2)  # <-- BLOCKS ENTIRE WATCHDOG THREAD
    qdrant_client = self._get_qdrant_client()
```

This `time.sleep(2)` was called **inside the watchdog callback thread**, blocking ALL file event processing for 2 seconds whenever Qdrant wasn't immediately available.

## Solution Implemented

Replaced blocking sleep with non-blocking `threading.Timer` retry mechanism:

1. **Immediate return** - callback returns instantly, allowing watchdog to process next events
2. **Background retry** - `_schedule_qdrant_retry()` schedules timer-based retries
3. **Exponential backoff** - 2s → 4s → 8s retry delays
4. **Max retries** - 3 attempts before giving up
5. **Frontend notification** - emits socket event after successful retry

### New Code Flow

```
_on_file_change() called
    ├── Qdrant available? → Index immediately → Emit to frontend
    └── Qdrant unavailable? → Schedule background retry → Emit (indexed=False)
                                    └── Timer fires after 2s
                                        ├── Qdrant now available? → Index → Emit update
                                        └── Still unavailable? → Schedule retry #2 (4s)
                                                                   └── etc.
```

## Files Modified

- `/src/scanners/file_watcher.py`:
  - Added `_schedule_qdrant_retry()` method (lines 426-476)
  - Replaced blocking sleep with non-blocking retry (lines 386-391)
  - Added MARKER_WATCHDOG_001 for tracking

## Markers Added

- `FIX_95.9: MARKER_WATCHDOG_001` - Documents the blocking sleep removal

## Testing

To test watchdog is working:
1. Restart the server
2. Create a new file in a watched directory (e.g., docs/95_ph/)
3. Check logs for `[Watcher] ✅ Indexed to Qdrant` message
4. Verify file appears in tree view

## Related Issues

- HAIKU-6 investigation report identified this as ROOT CAUSE
- User reported "собака опять уснула" (watchdog fell asleep again)
- Watchdog was active (40 dirs watched) but events were being delayed/blocked

---

## FIX_95.9.2: macOS FSEvents Unreliable for 'created' Events

**Date**: 2026-01-27
**Status**: IMPLEMENTED

### Problem

After fixing blocking sleep, watchdog STILL didn't detect new `.md` files in `docs/95_ph/`.
Grok analysis identified that macOS FSEvents API can miss file creation events.

### Solution: PollingObserver Fallback

Added `USE_POLLING_OBSERVER=1` environment variable to force polling mode:

```python
# In add_directory() - reads env var dynamically
use_polling = os.environ.get('USE_POLLING_OBSERVER', '0') == '1'
if use_polling:
    observer = PollingObserver(timeout=1)  # Check every 1 second
else:
    observer = Observer()  # FSEvents on macOS
```

### How to Use

**IMPORTANT**: Must use `export` for uvicorn with `reload=True`:

```bash
# Correct way (with export):
export USE_POLLING_OBSERVER=1 && python main.py

# Or in two lines:
export USE_POLLING_OBSERVER=1
python main.py

# Incorrect (won't work with uvicorn reload):
USE_POLLING_OBSERVER=1 python main.py
```

### Verification

Look for these log messages:
- `[DEBUG] USE_POLLING_OBSERVER env = 1` (in startup banner)
- `[Watcher Module] USE_POLLING_OBSERVER = True (env: 1)` (at module load)
- `[Watcher] Using PollingObserver (slower but reliable)` (when adding directories)
- `[Watcher] Started watching (Polling): /path/...` (confirms Polling mode)

If you see `(FSEvents)` instead of `(Polling)`, the env var is not being picked up.

### Markers

- `MARKER_WATCHDOG_002` - PollingObserver fallback implementation

---

## FIX_95.9.3: Infinite Loop - Changelog Triggers Watchdog

**Date**: 2026-01-27
**Status**: FIXED
**Root Cause**: Grok analysis

### Problem

After enabling TripleWrite, watchdog entered infinite loop:
1. Watchdog detects file change
2. `handle_watcher_event()` calls TripleWrite
3. TripleWrite writes to `data/changelog/changelog_*.json`
4. Watchdog detects changelog change (`.json` is in SUPPORTED_EXTENSIONS)
5. GOTO step 2 → infinite loop

Logs showed repeated delete/create cycles for `changelog_2026-01-27.json` every 2-3 seconds.

### Solution

Added TripleWrite output files to SKIP_PATTERNS:

```python
SKIP_PATTERNS = [
    # ... existing patterns ...
    # FIX_95.9.3: Prevent infinite loop
    'data/changelog', 'changelog_',  # Skip changelog directory and files
    'watcher_state.json',  # Skip watcher's own state file
    'models_cache.json', 'groups.json', 'chat_history.json'  # Skip other data files
]
```

### Why This Works

`_should_skip()` checks `if pattern in path`, so:
- `/path/to/data/changelog/changelog_2026-01-27.json` matches `'data/changelog'`
- Files like `changelog_*.json` anywhere match `'changelog_'`

### Verification

After restart, you should NOT see:
- Repeated `[DEBUG_WATCHER] Raw event: type=deleted, path=.../changelog_*.json`
- Repeated `[DEBUG_WATCHER] Raw event: type=created, path=.../changelog_*.json`

You SHOULD see:
- `[DEBUG_WATCHER] SKIP: matches skip pattern -> .../changelog_2026-01-27.json`

---

## FIX_95.9.4: Camera Not Focusing on New Files

**Date**: 2026-01-27
**Status**: FIXED
**Root Cause**: Grok analysis

### Problem

After watchdog detected new file and emitted `node_added`:
1. Backend correctly indexed file to Qdrant ✅
2. Frontend received `node_added` event ✅
3. Tree reloaded via HTTP ✅
4. **BUT camera didn't fly to new file** ❌

### Root Cause

300ms `setTimeout` was not enough time for React to update `nodes` state after `reloadTreeFromHttp()`. When `setCameraCommand` fired, the new node wasn't in the store yet, so `findNode()` returned null and camera command was silently ignored.

### Solution

Replaced fixed 300ms timeout with retry-based approach:

```javascript
const attemptCameraFocus = (attempt = 0, maxAttempts = 5) => {
  const currentNodes = useStore.getState().nodes;
  const nodeExists = Object.values(currentNodes).some(
    n => n.name === fileName || n.path === data.path
  );

  if (nodeExists) {
    setCameraCommand({ target: fileName, zoom: 'medium', highlight: true });
  } else if (attempt < maxAttempts) {
    setTimeout(() => attemptCameraFocus(attempt + 1), 500);
  }
};

setTimeout(() => attemptCameraFocus(0, 5), 500);
```

### Files Modified

- `client/src/hooks/useSocket.ts` - Retry-based camera focus in `node_added` handler
- `client/src/components/canvas/CameraController.tsx` - Enabled debug logging

### Verification

After creating a new file, browser console should show:
- `[Socket] node_added received: { path: "...", indexed: true }`
- `[Socket] ✅ Camera focusing on new file: filename.md (attempt N)`
- `[CameraController] Processing command: { target: "filename.md", zoom: "medium" }`

If camera still doesn't move, check for:
- `[Socket] ⚠️ Node still not found after 5 attempts` - node not in tree response
- `[CameraController] Node not found: filename.md` - findNode() failure
