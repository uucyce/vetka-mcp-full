# Phase 90.3: Watchdog Scanner Fix - Qdrant Retry Logic

**Date:** 2026-01-23
**Status:** ✅ COMPLETE
**Priority:** CRITICAL

## Executive Summary

Fixed silent file skipping in watchdog auto-scan when Qdrant client not immediately available. Added retry logic with 2-second delay to handle race condition where watcher starts before Qdrant connects.

## Root Cause Analysis

### Issue 1: Silent Qdrant Unavailability (CRITICAL)

**Location:** `src/scanners/file_watcher.py:383-394`

**Before (Broken):**
```python
qdrant_client = self._get_qdrant_client()
if qdrant_client:
    # ... index file
else:
    print(f"[Watcher] WARNING: qdrant_client not available...")  # SILENT FAIL
```

**Problem:**
- If Qdrant not ready during file event, files silently skipped
- Only printed WARNING (easy to miss in logs)
- User never notified which files were skipped
- Race condition: watcher starts before Qdrant connects

### Issue 2: Async Emit in Sync Thread (HIGH)

**Location:** `src/scanners/file_watcher.py:452-467`

**Status:** Already fixed in Phase 80.20
- Queue mode optional (disabled by default)
- Direct mode uses proper async handling
- Fix verified present in codebase

### Issue 3: Exception Swallowing (MEDIUM)

**Location:** `src/scanners/local_scanner.py:103-128`

**Status:** Not addressed in this phase
- Errors printed but not tracked
- Left as-is (low priority)

## Changes Made

### 1. Qdrant Retry Logic (MARKER_90.3)

**File:** `src/scanners/file_watcher.py:383-401`

**After (Fixed):**
```python
# MARKER_90.3_START: Fix qdrant client retry
qdrant_client = self._get_qdrant_client()
if not qdrant_client:
    # Retry once after 2 seconds
    import time as retry_time
    retry_time.sleep(2)
    qdrant_client = self._get_qdrant_client()

if qdrant_client:
    try:
        handle_watcher_event(event, qdrant_client=qdrant_client)
        print(f"[Watcher] ✅ Indexed to Qdrant: {path}")
    except Exception as e:
        print(f"[Watcher] ❌ Error updating Qdrant: {e}")
else:
    print(f"[Watcher] ⚠️ SKIPPED (Qdrant unavailable after retry): {path}")
    # TODO Phase 90.4: Queue for later retry
# MARKER_90.3_END
```

**Key Improvements:**
1. **Retry Logic:** 2-second delay + retry if first fetch returns None
2. **Clear Status:** Emoji prefixes (✅ ❌ ⚠️) for visual scanning
3. **User Notification:** Explicit SKIPPED message instead of generic WARNING
4. **Future-Ready:** TODO marker for Phase 90.4 queue system

### 2. Updated File Header

**File:** `src/scanners/file_watcher.py:1-18`

```python
@phase Phase 90.3
@lastAudit 2026-01-23
...
- Phase 90.3: Qdrant retry logic (2s delay, prevents silent skip)
```

## Uncommitted Fixes Included

### Timer Cleanup (Line 112)

**Status:** Already present in codebase
```python
del self.timers[path]  # Fix: Clear reference to prevent memory leak
```

### Type Hint (qdrant_updater.py:130)

**Status:** Already correct in codebase
```python
def _file_changed(self, file_path: Path) -> Tuple[bool, Optional[Dict]]:
```

## Testing Notes

### Manual Testing Required

1. **Test Race Condition:**
   ```bash
   # Start VETKA with Qdrant disabled
   # Watch docs/90_ph
   # Create new file
   # Enable Qdrant within 2 seconds
   # Verify file gets indexed
   ```

2. **Test Skip Scenario:**
   ```bash
   # Start VETKA with Qdrant permanently disabled
   # Create new file in watched directory
   # Verify clear ⚠️ SKIPPED message appears
   ```

3. **Test Normal Operation:**
   ```bash
   # Start VETKA with Qdrant enabled
   # Create/modify file
   # Verify ✅ Indexed message appears
   ```

### Expected Behavior

| Scenario | Before | After |
|----------|--------|-------|
| Qdrant ready | ✅ Index | ✅ Index |
| Qdrant delayed 1s | ⚠️ Silent skip | ✅ Index (retry) |
| Qdrant unavailable | ⚠️ Silent skip | ⚠️ Clear SKIPPED warning |
| Qdrant error | ❌ Logs error | ❌ Logs error |

## Future Work (Phase 90.4)

### Queue-Based Retry System

Instead of blocking for 2 seconds, implement queue:

```python
def _queue_for_retry(self, path: str) -> None:
    """Queue file for retry when Qdrant becomes available."""
    if not hasattr(self, '_retry_queue'):
        self._retry_queue = []

    self._retry_queue.append({
        'path': path,
        'queued_at': time.time()
    })

    print(f"[Watcher] Queued for retry: {path}")

def _process_retry_queue(self) -> None:
    """Process queued files when Qdrant available."""
    if not hasattr(self, '_retry_queue'):
        return

    qdrant_client = self._get_qdrant_client()
    if not qdrant_client:
        return

    while self._retry_queue:
        item = self._retry_queue.pop(0)
        # ... process item
```

**Benefits:**
- Non-blocking (no 2s delay)
- Handles multiple files
- Processes queue when Qdrant connects

### Enable Queue Mode by Default

**Current:** `use_emit_queue=False` (default)
**Proposed:** `use_emit_queue=True` (default)

**Location:** `src/scanners/file_watcher.py:246`

**Requires Testing:**
- Verify no deadlock on macOS
- Benchmark performance impact
- Test with high-frequency events

## Impact Assessment

### Critical Fix ✅
- Prevents silent data loss (files not indexed)
- Clear user feedback on failures
- Handles startup race condition

### Low Risk ⚠️
- 2-second blocking delay (only on first fetch failure)
- No breaking changes to API
- Backward compatible

### Migration Notes
- No migration required
- Existing watched directories unaffected
- Drop-in replacement

## Code Markers

All changes marked with `MARKER_90.3_START` / `MARKER_90.3_END` for easy tracking:

```bash
# Find all Phase 90.3 changes
grep -r "MARKER_90.3" src/
```

## Related Documentation

- `docs/80_ph/HAIKU_A_INDEX.md` - Haiku recon report (identified issue)
- `src/scanners/file_watcher.py` - Main implementation
- `src/scanners/qdrant_updater.py` - Qdrant integration

## Sign-Off

**Implemented By:** Claude Opus 4.5
**Reviewed By:** [Pending]
**Deployed:** [Pending]
**Verified:** [Pending]

---

**Next Steps:**
1. Test retry logic with real Qdrant startup sequence
2. Verify docs/90_ph auto-scan works
3. Monitor for 2-second delays in logs
4. Plan Phase 90.4 queue-based retry
