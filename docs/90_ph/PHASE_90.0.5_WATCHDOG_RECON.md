# MARKER_90.0.5_START: Watchdog Investigation

## Phase 90.0.5: Scanner/Watchdog Bug Reconnaissance
**Date:** 2026-01-23
**Status:** Investigation Complete
**Scope:** Scanning docs/90_ph - Watchdog Auto-Scan Failure Analysis

---

## 1. WATCHDOG STATE STATUS

### Current Configuration
- **File:** `/src/scanners/file_watcher.py` (Phase 80.20)
- **Status:** ACTIVE AND WATCHING
- **docs/90_ph Watch State:** YES - verified in watcher_state.json

### Watcher State (from data/watcher_state.json)
```
✓ docs/90_ph IS in watched_dirs list
✓ Watchdog is observing the directory
✓ State persisted correctly
```

### Watchdog Components Status
1. **VetkaFileWatcher** - Active singleton instance
2. **VetkaFileHandler** - Debounced event handler (400ms)
3. **AdaptiveScanner** - Heat score tracking (working)
4. **Emit Queue** - Phase 80.20 async fix implemented

---

## 2. RECENT CHANGES TO SCANNER FILES

### Git History
```
Recent commits:
- c83cfa2 Phase 80.38-80.40: Fix xai key detection + rotation
- 711cf45 Phase 80.37: xai fallback to openrouter
- 4d7850b Phase 80.36: Fix x-ai provider name normalization
- 6072e08 Phase 80.35: Fix Grok routing
- b6c98f1 Phase 80.30-80.33: Fix @mention dropdown
- 9b9959f Phase 83-88: Complete scanner control, UI fixes, MCP integration
```

### Uncommitted Changes (Modified Files)
1. **src/scanners/file_watcher.py** (MODIFIED)
   - Line 111: Added `del self.timers[path]` memory leak fix
   - Change: Timer reference cleanup in debounce logic
   - Status: NOT STAGED

2. **src/scanners/qdrant_updater.py** (MODIFIED)
   - Line 22: Import type annotation update (Tuple)
   - Line 130: Type hint syntax fix (tuple -> Tuple)
   - Status: NOT STAGED

**CRITICAL:** Both scanner files have uncommitted modifications that may contain fixes!

---

## 3. SUSPECTED CAUSE OF FAILURE

### Issue Chain Analysis

#### A. Silent Failure Path in Watchdog Event Handling
**File:** `src/scanners/file_watcher.py` (Lines 346-394)

```python
def _on_file_change(self, event: Dict) -> None:
    # ... event processing ...

    # Phase 80.17: Lazy fetch qdrant_client
    qdrant_client = self._get_qdrant_client()
    if qdrant_client:
        try:
            handle_watcher_event(event, qdrant_client=qdrant_client)
            print(f"[Watcher] Indexed to Qdrant: {path}")
        except Exception as e:
            print(f"[Watcher] Error updating Qdrant index: {e}")
    else:
        # Phase 80.17: Log when qdrant_client not available
        print(f"[Watcher] WARNING: qdrant_client not available...")
```

**Problem:** If Qdrant client is None during watchdog event (early startup), file changes SKIP indexing silently. No error raised - just a warning printed.

#### B. LocalScanner Silent Failures
**File:** `src/scanners/local_scanner.py` (Lines 103-105, 127-128)

```python
except Exception as e:
    self.error_count += 1
    print(f"[Scanner] Error scanning {file_path}: {e}")

# Read content
content = self._read_content(file_path)
if not content:
    return None  # Silent skip if no content
```

**Problem:** Files with read errors or empty content return None silently. No tracking of WHICH files failed.

#### C. Scanner State Changes vs Watchdog
**File:** `src/api/routes/semantic_routes.py` (Lines 585-723, trigger_rescan)

The rescan endpoint does:
1. Creates LocalScanner
2. Calls scanner.scan() (generator)
3. For each file: updater.update_file(file_path)

**Issue:** LocalScanner and handle_watcher_event use DIFFERENT code paths:
- LocalScanner reads file content itself
- Watchdog handler receives path from filesystem event

If file is created/modified in quick succession, watcher might capture it before file is fully written.

#### D. Async Emit Context Issue (Phase 80.20 Incomplete)
**File:** `src/scanners/file_watcher.py` (Lines 395-427)

The file_watcher has TWO emit modes:
- Queue-based: Uses dedicated event loop (safe for watchdog thread)
- Direct: Tries to run asyncio in sync context

**Issue:** If queue mode NOT enabled (default), direct emit attempts `asyncio.run()` in watchdog thread, which may fail or block.

---

## 4. PATH VALIDATION: docs/90_ph

### Directory Status
```
✓ Path exists: YES
✓ Is directory: YES
✓ Files present: 4 .md files + .DS_Store
  - PHASE77to90ph_ENGRAM_PROMPT.md (8.4 KB)
  - PHASE_90.0.1_GROK_BUTTON_RECON.md (6.3 KB)
  - PHASE_90.0.2_TRUNCATION_RECON.md (6.5 KB)
  - PHASE_90.0.3_FREE_MODELS_RECON.md (12.0 KB)
```

### File Support
- Extension: `.md` - SUPPORTED by LocalScanner (line 42-46 in local_scanner.py)
- Content: Text UTF-8 - READABLE

### .gitignore Analysis
- No exclude for docs/ or 90_ph
- docs/ directory NOT in .gitignore
- Files are tracked and should be scanned

---

## 5. ERROR HANDLING GAPS

### Gap 1: Watchdog Silent Failures
**Location:** `file_watcher.py:383-394`
- Lazy fetch returns None? → WARNING printed, NO indexing, NO error
- Perfect place for files to vanish from Qdrant

### Gap 2: Scanner Exception Swallowing
**Location:** `local_scanner.py:103-105`
- Exception in _scan_file? → Printed, error_count++, NOTHING indexed
- User never sees which file caused problem

### Gap 3: Async Emit Blocking
**Location:** `file_watcher.py:452-467`
- Direct emit mode calls asyncio.run() in sync watchdog thread
- Can cause: deadlock, exception, or complete socket failure
- NO fallback to queue mode if direct fails

### Gap 4: Path Parameter Ignored in Watcher
**Location:** `file_watcher.py:385-394`
- handle_watcher_event() called but never checks if path should be watched
- Watcher ADDS the directory but no per-file path filtering

---

## 6. WATCHDOG vs SCAN MISMATCH

### How Files Get Into Qdrant

**Path A: Watchdog (Real-time)**
```
File created/modified → Watchdog observes
  → VetkaFileHandler.on_any_event()
  → Debounced 400ms
  → _on_file_change()
  → handle_watcher_event(event, qdrant_client)
  → Problem: qdrant_client might be None
```

**Path B: Manual Scan (Triggered)**
```
POST /api/semantic/scanner/rescan?path=/path/to/90_ph
  → LocalScanner(str(scan_path))
  → scanner.scan() generator
  → updater.update_file(file_path) for each file
  → Success: 4 files scanned
```

**Problem:** Path A (watchdog) silently skips indexing if qdrant_client is None
But Path B (manual scan) WORKS because it doesn't have lazy fetch dependency

---

## 7. ROOT CAUSE HYPOTHESIS

### Most Likely Culprit: Lazy Qdrant Fetch in Watchdog

**Evidence:**
1. Watchdog is WATCHING docs/90_ph ✓
2. Manual scan WORKS ✓
3. But watchdog auto-scan FAILS ✓
4. Code path has: `if qdrant_client: ... else: print(WARNING)`

**Scenario:**
1. Server starts, watcher initialized BEFORE Qdrant connects
2. Phase 80.17 tries lazy fetch: `get_qdrant_manager()`
3. If components_init fails OR manager.client is still None → WARNING printed
4. File creation events captured but NOT indexed
5. Manual scan works because POST endpoint checks Qdrant explicitly

### Secondary Issues
- Async emit mode might be blocking watchdog thread
- Scanner exception handling hides real errors
- No per-file error tracking in watchdog path

---

## 8. UNCOMMITTED CHANGES AS CLUES

### Change 1: Timer Cleanup (file_watcher.py:111)
```python
+ del self.timers[path]  # Fix: Clear reference to prevent memory leak
```
**Implication:** Recent memory leak fix suggests watchdog was causing problems before

### Change 2: Type Hint Fix (qdrant_updater.py:130)
```python
- def _file_changed(...) -> tuple[bool, Optional[Dict]]:
+ def _file_changed(...) -> Tuple[bool, Optional[Dict]]:
```
**Implication:** Type compatibility issue that might cause runtime errors

**Status:** These changes NOT committed - might be pending fixes!

---

## 9. PHASE 80.20 INCOMPLETE IMPLEMENTATION

The file_watcher.py shows Phase 80.20 async fixes were added but:

1. **Queue mode optional** (use_emit_queue parameter defaults to False)
2. **Direct async.run() in watchdog thread** - problematic on macOS
3. **No retry logic** if emit fails
4. **No fallback to queue mode** if direct fails

Result: Watchdog might experience deadlock/blocking on file change events

---

## SUMMARY: WATCHDOG BROKEN - 3 ROOT CAUSES

| # | Issue | File | Impact | Severity |
|---|-------|------|--------|----------|
| 1 | Lazy qdrant_client fetch returns None | file_watcher.py:383-394 | Files indexed 0x, silently skipped | CRITICAL |
| 2 | Async emit in sync thread (Phase 80.20 incomplete) | file_watcher.py:452-467 | Watchdog blocks/deadlocks | HIGH |
| 3 | Exception swallowing in LocalScanner | local_scanner.py:103-128 | Errors hidden from user | MEDIUM |

---

## MARKER_90.0.5_END
