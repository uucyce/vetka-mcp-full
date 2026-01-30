# HAIKU-6 Investigation Index

**Phase:** 95.9
**Investigation Date:** 2026-01-27
**Status:** COMPLETE - ROOT CAUSE IDENTIFIED

---

## Investigation Goal

Determine why Watchdog does not react to new files in scanned folders (appears to be "sleeping").

## Result

ROOT CAUSE IDENTIFIED with 95% confidence: **Blocking `time.sleep(2)` in callback handler** (line 387 of `src/scanners/file_watcher.py`)

---

## Documentation Files

### 1. HAIKU_TEST_6_WATCHDOG_ASYNC.md (Primary Report)
**Size:** 16 KB, 528 lines
**Purpose:** Complete technical investigation with evidence

**Contents:**
- Executive summary
- Detailed findings for each component
- Root cause breakdown
- Timeline analysis
- Markers placed for implementation
- Recommended fixes
- Code evidence appendix

**Key Sections:**
- WATCHDOG OBSERVER - PROPERLY CONFIGURED ✓
- EVENT HANDLER - PARTIALLY CORRECT ✓
- DEBOUNCE/TIMER - WORKING ✓
- CALLBACK EXECUTION - CRITICAL ISSUE ✗
- ASYNC EMIT - SECONDARY ISSUE ⚠
- ROOT CAUSE BREAKDOWN
- RECOMMENDED FIXES

### 2. HAIKU_6_QUICKREF.md (Executive Summary)
**Size:** 4.2 KB
**Purpose:** Quick reference for busy developers

**Contents:**
- One-line summary
- The bug (with code)
- Impact analysis (timeline)
- Why it's critical
- Three supporting issues
- Fix options
- Markers placed
- Next steps

**Best For:** Quick understanding of the problem and fix

### 3. HAIKU_6_INDEX.md (This File)
**Purpose:** Navigation and overview

---

## Quick Summary

### The Bug

**File:** `src/scanners/file_watcher.py`
**Line:** 387
**Code:** `time.sleep(2)`
**Context:** Called from callback handler in timer thread

### The Problem

When Qdrant is unavailable during a file event, the handler calls `time.sleep(2)` which blocks the watchdog timer thread for 2 seconds. During this time:

- New file events are detected but CANNOT be processed
- Debounce timers cannot fire
- The system appears frozen or "sleeping"
- After the 2-second sleep, files are processed with cascading delays

### The Impact

**Expected:** 3 files → processed in 700ms
**Actual:** 3 files → processed with 3-5 second delays and cascading effects

### The Fix

**Primary (Recommended):** Remove the 2-second sleep
- Qdrant will be available on the next file event
- No blocking means responsive watchdog
- Risk: Very low (just removing defensive code)

**Secondary:** Use queue-based emit
- Force `use_emit_queue=True` by default
- Prevents async/sync mixing in timer thread

**Tertiary:** Non-blocking retry flag
- Log warning once, don't sleep
- Try again on next event

---

## Markers Placed

For tracking implementation:

| Marker | Location | Issue | Fix |
|--------|----------|-------|-----|
| MARKER_WATCHDOG_001 | Line 387 | Blocking sleep | Remove sleep |
| MARKER_WATCHDOG_002 | Lines 483-504 | Async emit from sync | Use queue |
| MARKER_WATCHDOG_003 | Lines 356-423 | Direct emit | Queue emit |

Search for `TODO_95.9: MARKER_WATCHDOG` in codebase to find all locations.

---

## Key Findings

### What's Working ✓

1. **Observer Start** - `observer.start()` correctly called
2. **Event Detection** - Watchdog properly detects file events
3. **Debounce Timer** - 400ms debounce works correctly
4. **Extension Filtering** - Proper extension checks
5. **State Persistence** - Watched dirs saved and restored
6. **Singleton Pattern** - Properly maintains instance
7. **Emit Worker Thread** - Correct queue-based pattern exists

### What's Broken ✗

1. **Blocking Sleep** - CRITICAL: `time.sleep(2)` in callback (line 387)
2. **Async Emit** - Creating event loops from timer thread (lines 483-504)
3. **Queue Usage** - emit_worker exists but not used consistently

### Root Cause Chain

```
File created
  ↓
watchdog.Observer detects event
  ↓
VetkaFileHandler.on_any_event() queues event
  ↓
threading.Timer fires at 400ms
  ↓
_process_batch() → _on_file_change() (RUNS IN TIMER THREAD)
  ↓
time.sleep(2) ← BLOCKS TIMER THREAD HERE
  ↓
Events detected while sleeping CANNOT be processed
  ↓
After sleep: cascading delays in processing
```

---

## Testing the Bug

To verify the bug exists:

1. Start VETKA with debug logging enabled
2. Add a directory to watch
3. Rapidly create 5-10 files in that directory
4. Check console for:
   - `[Watcher] Retrying qdrant_client after 2s` → Bug present
   - Delayed processing of subsequent files → Bug present

---

## Architecture Recommendations

**Current (Problematic):**
```
Watchdog thread
  ├─ on_any_event() [responsive]
  └─ _on_file_change() [blocks on sleep]
     └─ _emit() [creates temp event loops]
```

**Recommended:**
```
Watchdog thread
  ├─ on_any_event() [responsive]
  └─ _on_file_change() [fast, queues]
     └─ _emit_queue.put()

Emit worker thread
  └─ async socketio.emit() [safe, dedicated]
```

---

## Files Analyzed

| File | Lines | Status | Finding |
|------|-------|--------|---------|
| src/scanners/file_watcher.py | 718 | REVIEWED | BUG FOUND (line 387) |
| src/api/routes/watcher_routes.py | 763 | REVIEWED | Uses watcher correctly |
| src/scanners/qdrant_updater.py | 850+ | SPOT-CHECKED | OK |
| src/initialization/components_init.py | QUERIED | OK | Watcher initialized |

---

## Confidence Levels

| Aspect | Confidence | Reasoning |
|--------|-----------|-----------|
| Root cause identified | 95% | Direct code inspection |
| Bug severity | 90% | Clear timing analysis |
| Fix effectiveness | 95% | Simple removal of blocker |
| Overall assessment | 95% | Code is clear evidence |

---

## Implementation Priority

**Priority:** HIGH
**Complexity:** LOW
**Risk:** LOW
**Effort:** <1 hour

The fix is straightforward: remove one blocking sleep statement. The rest of the architecture is sound.

---

## References

**Primary Investigation:**
- Full report: `HAIKU_TEST_6_WATCHDOG_ASYNC.md` (528 lines)
- Quick ref: `HAIKU_6_QUICKREF.md` (4.2 KB)

**Source Code:**
- Main: `src/scanners/file_watcher.py` (lines 356-504)
- Routes: `src/api/routes/watcher_routes.py` (lines 73-264)

**Related Documents:**
- Phase 90.3: Qdrant retry logic
- Phase 80.20: Async emit fixes
- Phase 80.15: Queue-based emit

---

## Next Actions

1. **Review** - Read HAIKU_TEST_6_WATCHDOG_ASYNC.md
2. **Decide** - Choose fix option (A, B, or C)
3. **Implement** - Apply fix following markers
4. **Test** - Verify with rapid file creation
5. **Commit** - Document changes with marker reference

---

**Investigation Completed By:** HAIKU-6 Agent
**Investigation Date:** 2026-01-27
**Report Status:** READY FOR IMPLEMENTATION
