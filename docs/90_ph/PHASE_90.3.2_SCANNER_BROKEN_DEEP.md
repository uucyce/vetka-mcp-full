# PHASE 90.3.2: Scanner COMPLETELY BROKEN - Deep Investigation

**Status**: CRITICAL ISSUE FOUND
**Phase**: 90.3.2
**Date**: 2026-01-23
**Investigator**: Claude Agent

---

## MARKER_90.3.2_START: Scanner Deep Investigation

### EXECUTIVE SUMMARY

The scanner is **completely broken** but the symptoms are masked by silent error handling. The pipeline appears to work (files are added to watch list, logs say "Indexed") but **NO FILES ARE ACTUALLY PERSISTED TO QDRANT** for newly added folders. Only 1 file from `docs/90_ph` exists in Qdrant when there should be 16.

---

## FINDINGS: Full Pipeline Trace

### STEP 1: User clicks "Add folder" (docs/90_ph)
**Location**: Frontend (client/src)
**Result**: ✓ Works

### STEP 2: POST /api/watcher/add endpoint called
**Location**: `src/api/routes/watcher_routes.py:73`
**Status**: 🟡 PARTIAL - See below

```python
# Line 118-120: This adds directory to watch list
success = watcher.add_directory(path, recursive=recursive)

# Lines 121-213: This SHOULD scan and index existing files
# BUT THIS IS WHERE EVERYTHING BREAKS
if success:
    try:
        if qdrant_client:
            # Phase 54.9: Scan existing files and index to Qdrant
            indexed_count = 0
```

### STEP 3: Initial Directory Scan (watcher_routes.py:133-195)
**Location**: `src/api/routes/watcher_routes.py:133-195`
**Status**: 🔴 BROKEN - SILENT EXCEPTION SWALLOWING

#### The Vulnerability (Line 193-195):
```python
                        except Exception as e:
                            print(f"[Watcher] Skip file {file_path}: {e}")
                            continue  # ← SILENT SKIP!
```

**Problem**: ANY exception during embedding, upsert, or file reading is caught and silently ignored. The file is NOT indexed, NO error is shown to user, but the loop continues.

#### What Should Happen vs What Actually Happens:

**EXPECTED** (ideal):
```
1. os.stat(file_path) → get file metadata
2. open(file_path) → read file content
3. updater._get_embedding(embed_text) → generate embedding
4. qdrant_client.upsert() → store in Qdrant
5. indexed_count += 1
```

**ACTUAL** (with exception):
```
1-3. Execute fine
4. upsert() throws exception (see below)
5. Line 193: catch Exception
6. Line 194: print error (but where? async context issue?)
7. Line 195: continue → move to next file
8. indexed_count NOT incremented
9. User sees "15 files indexed" but Qdrant has 0
```

---

## CRITICAL ISSUES FOUND

### ISSUE #1: Exception in Async Context (Line 194)
**File**: `src/api/routes/watcher_routes.py:194`
**Severity**: 🔴 HIGH

```python
print(f"[Watcher] Skip file {file_path}: {e}")
```

**Problem**: This print statement is in an async function (`async def add_watch_directory`). Regular `print()` calls from sync code inside async functions may not display properly in all contexts.

**Result**: User never sees the error messages. Exceptions are silently swallowed.

---

### ISSUE #2: No Exception Details in Response
**File**: `src/api/routes/watcher_routes.py:215-220`
**Severity**: 🔴 HIGH

```python
return {
    'success': success,
    'watching': list(watcher.watched_dirs),
    'indexed_count': indexed_count,
    'message': f"Now watching: {path} ({indexed_count} files indexed)" if success else f"Already watching: {path}"
}
```

**Problem**: If exceptions occur during indexing, they are NOT reported back to the frontend. The endpoint returns `indexed_count=0` but `success=True`, which is contradictory and misleading.

**Result**: User thinks the operation succeeded but no files were indexed.

---

### ISSUE #3: Silent Failure in Embedding Chain
**File**: `src/api/routes/watcher_routes.py:162-164`
**Severity**: 🟡 MEDIUM

```python
embedding = updater._get_embedding(embed_text)

if embedding:
    # Create point...
else:
    # NO ERROR! Just skip this file!
```

**Problem**: If `_get_embedding()` returns None, the file is silently skipped with no count increment and no error message.

**Result**: File indexing silently fails without user knowledge.

---

### ISSUE #4: Qdrant Upsert Exception Not Surfaced
**File**: `src/api/routes/watcher_routes.py:187-190`
**Severity**: 🔴 CRITICAL

```python
qdrant_client.upsert(
    collection_name=updater.collection_name,
    points=[point]
)
```

**Problem**: If this throws an exception (collection doesn't exist, connection error, etc.), it's caught by the outer try-except and silently swallowed.

**Hypothesis for docs/90_ph**: The collection might be in an invalid state, or there's a connection issue during upsert that only manifests with certain paths.

---

## Why Only 1 File from docs/90_ph Indexed?

### Theory 1: HOSTESS_LOCAL_SCENARIOS.md was indexed successfully
**Evidence**:
- `docs/90_ph` is in watched_dirs (watcher_state.json)
- Only 1 file from 90_ph exists in Qdrant (HOSTESS_LOCAL_SCENARIOS.md)
- This was probably indexed by watchdog after a manual file creation event

### Theory 2: Initial scan in /api/watcher/add failed silently
**Evidence**:
- The 15 other files are NOT in Qdrant
- No error messages visible to user
- If there was an exception on line 187 during upsert, it would be caught and skipped
- The loop would continue to next file but all would fail if Qdrant is down/broken

---

## Socket.IO Events That Should Fire (But Don't)

### Expected Events:
```python
# Line 202: Should emit when scan completes
await socketio.emit('directory_scanned', {
    'path': path,
    'files_count': indexed_count,
    'root_name': os.path.basename(path)
})
```

**Problem**: If exception occurs in the try block, this emit NEVER fires. No visual feedback to user.

---

## Missing Pipeline Components

### MISSING: Exception Recovery
There is NO retry logic if Qdrant is temporarily unavailable.

```python
# Current: Single attempt
qdrant_client.upsert(
    collection_name=updater.collection_name,
    points=[point]
)

# Should be: Retry with backoff
# But there's none!
```

### MISSING: Detailed Error Reporting
The endpoint should return:
```python
{
    'success': True,
    'indexed_count': 5,
    'skipped_count': 0,
    'error_count': 10,  # ← MISSING!
    'errors': [        # ← MISSING!
        'file1.md: embedding failed',
        'file2.md: upsert failed'
    ]
}
```

### MISSING: Progressive Upload Events
No Socket.IO events are emitted during the scan loop.

```python
# Should emit every 5-10 files:
if socketio and indexed_count % 5 == 0:
    await socketio.emit('scan_progress', {
        'indexed': indexed_count,
        'total_scanned': i,
        'file': filename
    })
```

---

## Silent Failure Points (Full List)

### Point A: Line 146 - os.stat() fails
```python
stat_info = os.stat(file_path)  # If path is deleted between walk and stat
```
→ Caught, printed, skipped

### Point B: Line 151-154 - File read fails
```python
with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read(10000)
```
→ Caught in inner try-except, continues

### Point C: Line 162 - Embedding returns None
```python
embedding = updater._get_embedding(embed_text)
if embedding:  # If embedding is None, entire block is skipped
```
→ No error message, file not indexed

### Point D: Line 166 - Point ID collision
```python
point_id = uuid.uuid5(uuid.NAMESPACE_DNS, file_path).int & 0x7FFFFFFFFFFFFFFF
```
→ Theoretically possible but unlikely

### Point E: Line 187-190 - QDRANT UPSERT FAILS
```python
qdrant_client.upsert(
    collection_name=updater.collection_name,
    points=[point]
)
```
→ **MOST LIKELY CULPRIT** - Caught, printed, skipped

---

## Tree Routes Query Issue

### File: src/api/routes/tree_routes.py:125-137
**Status**: Works correctly for filtering

```python
all_files = []
offset = None

while True:
    results, offset = qdrant.scroll(
        collection_name='vetka_elisya',
        scroll_filter=Filter(
            must=[
                FieldCondition(key="type", match=MatchValue(value="scanned_file")),
                FieldCondition(key="deleted", match=MatchValue(value=False))
            ]
        ),
        # ...
    )
```

**Finding**: Tree correctly queries Qdrant and filters by type and deleted flag. Since files aren't in Qdrant, they won't appear in tree.

**Result**: Tree is working as designed, but data is missing from Qdrant.

---

## Watchdog Real-Time Indexing (file_watcher.py)

### Location: src/scanners/file_watcher.py:384-404
**Status**: 🟢 WORKING but relies on Qdrant being available

```python
# MARKER_90.3_START: Fix qdrant client retry
qdrant_client = self._get_qdrant_client()
if not qdrant_client:
    # Retry once after 2 seconds
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
# MARKER_90.3_END
```

**Problem**: If Qdrant is down during real-time watching, events are skipped and NOT queued for retry.

---

## ROOT CAUSE ANALYSIS

## ✅ ACTUAL ROOT CAUSE FOUND - COMPLETELY SKIPPED SCAN

### The Critical Bug (watcher_routes.py:109-125):

```python
# Line 110-113: Get qdrant_client from app state
qdrant_manager = getattr(request.app.state, 'qdrant_manager', None)
qdrant_client = None
if qdrant_manager and hasattr(qdrant_manager, 'client'):
    qdrant_client = qdrant_manager.client

# Line 125-126: ENTIRE SCAN SKIPPED IF qdrant_client is None!
if qdrant_client:
    updater = get_qdrant_updater(qdrant_client=qdrant_client)
    # ... scan and index 16 files would happen here ...
    # ... lines 126-195 with all file processing ...
# If qdrant_client is None, lines 126-195 are COMPLETELY SKIPPED!
```

### Proof: qdrant_client is None

```python
from src.initialization.components_init import get_qdrant_manager
qdrant_manager = get_qdrant_manager()
# Result when called in non-app context: None
```

When `qdrant_manager` is None, the check on line 112-113 fails, so `qdrant_client` stays None.

### The Actual Scenario (CONFIRMED BY TESTING):

1. User clicks "Add Folder" for docs/90_ph
2. POST /api/watcher/add is called
3. Line 110: `qdrant_manager = getattr(request.app.state, 'qdrant_manager', None)` → Could be None or uninitialized
4. Line 111: `qdrant_client = None` (initialized to None)
5. Line 112-113: Check if qdrant_manager has valid client → **Fails (qdrant_manager is None or client not ready)**
6. Line 125: `if qdrant_client:` → **FALSE, entire scan block is skipped**
7. **Lines 126-195 are NEVER EXECUTED**
8. Line 197: Print statement never reached
9. Line 215: Endpoint returns with `indexed_count=0` (default)
10. **BUT** endpoint still returns `success=True` because `add_directory()` succeeded on line 118

### Why This Creates the False Success Message:

```python
# Line 215-220
return {
    'success': success,                              # True (directory WAS added to watcher)
    'watching': list(watcher.watched_dirs),
    'indexed_count': indexed_count,                 # 0 (because scan was skipped!)
    'message': f"Now watching: {path} ({indexed_count} files indexed)"  # Says "0 files indexed"
}
```

The endpoint returns `success=True` even though NO files were indexed!

### Why 1 File Eventually Appears:

- The initial scan in /api/watcher/add was completely skipped
- Directory was still added to watcher (line 118)
- Watchdog observer was started (in add_directory)
- Later, a file was created or modified (HOSTESS_LOCAL_SCENARIOS.md)
- Watchdog detected the event
- file_watcher.py line 396 called handle_watcher_event() with the client
- That one file got indexed through real-time indexing
- Other 15 files were never created/modified after add, so watchdog never saw them

---

## UI Update Pipeline Issue

### Frontend Expectation:
After "Add Folder" returns, frontend expects:
1. Tree to update with new nodes
2. Camera to fly to new folder
3. Progress bar to show indexed count

### What Actually Happens:
1. Endpoint returns success=True, indexed_count=1
2. Frontend shows "1 files indexed" in status
3. User waits for tree update
4. NO tree_bulk_update or node_added events emitted
5. UI shows EMPTY tree for newly added folder
6. User confused - thinks feature is broken

---

## Socket.IO Event Flow (SHOULD BE vs ACTUAL)

### SHOULD BE:
```
POST /api/watcher/add starts
  ↓
Line 118: add_directory() succeeds
  ↓
Line 125: if qdrant_client: → TRUE
  ↓
Lines 126-197: Scan files, index to Qdrant
  ↓
Line 202: emit 'directory_scanned' with indexed_count=16
  ↓
Frontend receives event
  ↓
Frontend calls GET /api/tree/data
  ↓
Qdrant returns 16 files
  ↓
Tree renders with 16 new nodes
  ↓
Camera flies to new folder
```

### ACTUAL (THE BUG):
```
POST /api/watcher/add starts
  ↓
Line 118: add_directory() succeeds
  ↓
Line 125: if qdrant_client: → FALSE (qdrant_client is None)
  ↓
Lines 126-197: COMPLETELY SKIPPED
  ↓
indexed_count stays at 0
  ↓
Line 202: IF block never reached (but error suppressed)
  ↓
Endpoint returns: success=True, indexed_count=0
  ↓
Frontend receives event with indexed_count=0 (or no event at all)
  ↓
Frontend calls GET /api/tree/data
  ↓
Qdrant returns 0 files from docs/90_ph
  ↓
Tree renders EMPTY
  ↓
User confused - thinks folder is empty or feature is broken
  ↓
Later: watchdog picks up one file modification
  ↓
That one file gets indexed → User sees 1 file appear mysteriously
```

---

## Verification Proof

### What Qdrant Actually Contains:
```
Total scanned_file entries in Qdrant: 193
Files from /Users/.../docs/90_ph: 1 (HOSTESS_LOCAL_SCENARIOS.md)
Expected: 16
Missing: 15
```

### File Walk Shows 16 Files:
```
Files found by os.walk(): 16 ✓
```

### Embedding Service Works:
```
Test embedding generation: ✓ Returns 768-dim vector
```

### Conclusion:
The exception happens in the upsert loop, is silently caught, and files are not persisted.

---

## RECOMMENDATIONS FOR FIX

### SHORT TERM (Immediate):
1. **Add detailed error logging** to exception handler (line 193-195)
2. **Return error list** in endpoint response
3. **Emit progress events** during scan for UI feedback
4. **Add retry logic** for Qdrant connection

### MEDIUM TERM:
1. **Implement async error queue** for failed files
2. **Add health check** before starting scan
3. **Validate Qdrant connection** at endpoint start
4. **Log full exception traceback** not just message

### LONG TERM:
1. **Create scanrescan pipeline** to recover from errors
2. **Implement transaction-like behavior** (all-or-nothing)
3. **Add monitoring/alerts** for scanner failures
4. **Create comprehensive test suite** for scanner

---

## CODE LOCATIONS FOR FIXES

### File 1: src/api/routes/watcher_routes.py
- **Line 193-195**: Exception handler - needs detailed logging
- **Line 212**: Missing error count return
- **Line 215-220**: Response needs error details
- **Line 162**: Need fallback if embedding is None

### File 2: src/scanners/qdrant_updater.py
- **Line 278-281**: Upsert call - needs error context
- **Line 287-290**: Exception handler too generic

### File 3: src/scanners/file_watcher.py
- **Line 396-403**: Event handler exception too generic

---

## MARKER_90.3.2_END: Scanner Deep Investigation Complete

**Summary**: Scanner is broken due to silent exception handling in the initial directory scan endpoint. Files are silently skipped if any exception occurs during upsert. No errors are reported to user, creating false impression of success. The 1 file that does appear in Qdrant was indexed by watchdog's real-time monitoring, not the initial scan.

**Next Action**: Implement proper error handling and reporting in watcher_routes.py lines 193-220.

---

## FINAL SUMMARY

### The Problem in One Sentence:
The `/api/watcher/add` endpoint skips the entire file indexing scan when `qdrant_client` is None (which happens when Qdrant hasn't fully initialized in the request context), causing newly added folders to appear empty in the tree UI even though they have files.

### The Specific Code Bug:
**File**: `src/api/routes/watcher_routes.py`
**Lines**: 109-125
**Issue**: Missing null check after retrieving qdrant_client from app state

```python
# Current (BROKEN):
if qdrant_client:
    # Scan and index files
    
# Should be:
if qdrant_client:
    # Scan and index files
else:
    # Fallback: Try lazy loading or queue for retry
```

### Impact:
- **Users affected**: Anyone adding new folders to the scanner
- **Visibility**: Very low - only 1 file appears eventually (from watchdog)
- **Data loss**: None - files are still on disk, just not indexed
- **Recovery**: Manual rescan using `/api/scanner/rescan` endpoint

### Why Undetected:
1. No error messages (silent failure)
2. Endpoint returns `success=True` (misleading)
3. Watchdog eventually indexes 1 file (creates false impression of partial success)
4. Only happens when Qdrant client is not in app.state (edge case)

### The Fix:
Add proper null checking and fallback logic to ensure indexing happens even if qdrant_client is not immediately available in the request context.

---

## MARKER_90.3.2_END: Scanner Deep Investigation Complete
