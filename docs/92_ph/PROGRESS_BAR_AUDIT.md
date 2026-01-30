# VETKA Phase 92: Scan Progress Bar Audit

**Date:** 2026-01-25
**Scout:** Haiku Agent
**Status:** Complete
**Phase:** 92 - Non-blocking Scan UI

---

## Executive Summary

The scan progress bar implementation is **functionally complete** with a solid event-driven architecture using Socket.IO events. However, there are **several critical gaps** between frontend progress calculation and backend emit logic that could cause inaccurate progress display.

**Key Finding:** Progress is tracked as a **percentage (0-100)** on frontend, but backend emits **absolute counts (current/indexed)** - the frontend has NO calculation logic to convert counts to percentages.

---

## Architecture Overview

```
Backend (Python)              Frontend (React)              Browser
┌─────────────────┐         ┌────────────────┐          ┌──────────┐
│ File Watcher    │         │ ScanProgress   │          │ Custom   │
│ Qdrant Updater  │─────→   │ Panel.tsx      │─────→    │ Events   │
│ Semantic Routes │ Socket  │ (listens)      │ Window   │ (DOM)    │
└─────────────────┘ .IO     └────────────────┘ dispatch └──────────┘
  emit:                        receive:               ScanProgressPanel
  - scan_progress              scan_progress        listens to:
  - scan_complete              scan_complete        - scan_progress
  - directory_scanned          directory_scanned    - scan_complete
                                                     - directory_scanned
```

---

## Backend Event Emission Analysis

### 1. Source: `/src/api/routes/semantic_routes.py`

**Event: `scan_progress` (emitted during directory scan)**

```python
# Phase 69: Emit progress every 10 files
if socketio and total_scanned % 10 == 0:
    await socketio.emit(
        "scan_progress",
        {
            "current": total_scanned,      # ⚠️ Absolute file count
            "indexed": indexed,             # ⚠️ Absolute file count
            "file": scanned_file.name,
            "path": str(scan_path),
        },
    )
```

**Issues:**
- ⚠️ **NO total count available** - Only emits `current` (files processed) and `indexed` (successful indexes)
- ⚠️ **Cannot calculate percentage** - No total files to divide by
- ⚠️ **Frequency:** Only every 10 files (sparse updates)
- ⚠️ **Missing:** No explicit progress calculation (0-100%)

**Location:** `src/api/routes/semantic_routes.py` (grep shows line with "Emit progress every 10 files")

---

### 2. Source: `/src/api/routes/watcher_routes.py`

**Event: `directory_scanned` (emitted after scan completes)**

```python
await socketio.emit('directory_scanned', {
    'path': path,
    'files_count': indexed_count,        # ⚠️ Final count, not percentage
    'root_name': os.path.basename(path)
})
```

**Issues:**
- ⚠️ **Absolute count only** - No percentage
- ⚠️ **Only on completion** - No granular progress updates
- ⚠️ **Indirect activation** - Comes from `/api/watcher/add` endpoint, not real-time scanning

**Location:** `src/api/routes/watcher_routes.py` (lines 174-180)

---

### 3. Source: `semantic_routes.py` completion event

**Event: `scan_complete` (emitted at end of scan)**

```python
if socketio:
    event_name = "scan_stopped" if stopped else "scan_complete"
    await socketio.emit(
        event_name,
        {
            "indexed": indexed,
            "skipped": skipped,
            "total": total_scanned,           # ⚠️ Only available here!
            "deleted": deleted,
            "path": str(scan_path),
            "stopped": stopped,
        },
    )
```

**Critical Finding:**
- ✅ **Total count provided** - Only in `scan_complete`, NOT in `scan_progress`
- ⚠️ **Too late for progress calculation** - Event is fired at END
- ⚠️ **Architectural gap** - Can't use `total_scanned` during progress updates

**Location:** `src/api/routes/semantic_routes.py`

---

## Frontend Implementation Analysis

### File: `/client/src/components/chat/ScanProgressPanel.tsx`

#### Progress State Management

```typescript
const [progress, setProgress] = useState(0);        // 0-100%
const [totalFiles, setTotalFiles] = useState(0);    // For display only
const [isScanning, setIsScanning] = useState(false);
const [scannedFiles, setScannedFiles] = useState<ScannedFile[]>([]);
```

#### Event Listeners

**1. `scan_progress` listener (line 63-80):**

```typescript
const handleScanProgress = (event: CustomEvent<{
  progress: number;      // ← EXPECTED: 0-100
  status?: string;
  file_path?: string;
}>) => {
  setProgress(event.detail.progress);  // ⚠️ Uses progress directly
  setIsScanning(true);

  // File tracking logic
  if (event.detail.file_path) {
    setScannedFiles(prev => {
      const newFile: ScannedFile = {
        path: event.detail.file_path!,
        timestamp: Date.now()
      };
      return [newFile, ...prev].slice(0, 10);
    });
  }
};
```

**⚠️ CRITICAL ISSUE:**
- Expects `progress: number` (0-100 percentage)
- Backend emits `current` and `indexed` (absolute counts)
- **TYPE MISMATCH**: Frontend will receive `undefined` for `progress` field
- Result: Progress bar stuck at 0%

---

**2. `scan_complete` listener (line 82-95):**

```typescript
const handleScanComplete = (event: CustomEvent<{
  filesCount?: number;
  nodes_count?: number;
}>) => {
  setIsScanning(false);
  setProgress(100);  // ✅ Set to 100 on completion

  const count = event.detail?.filesCount || event.detail?.nodes_count || 0;
  setTotalFiles(count);  // Display total in header

  // Reset after 3 seconds
  setTimeout(() => {
    setProgress(0);
    setScannedFiles([]);
    setTotalFiles(0);
  }, 3000);
};
```

**Good:**
- ✅ Sets progress to 100% on completion
- ✅ Extracts file count for display
- ✅ Cleans up state after scan

**Issues:**
- ⚠️ Resets too aggressively (3 seconds)
- ⚠️ No progressive loading - jumps 0% → 100%

---

**3. `directory_scanned` listener (line 97-109):**

```typescript
const handleDirectoryScanned = (event: CustomEvent<{
  path: string;
  files_count?: number;
}>) => {
  if (event.detail.path) {
    setScannedFiles(prev => {
      const newFile: ScannedFile = {
        path: event.detail.path,
        timestamp: Date.now()
      };
      return [newFile, ...prev].slice(0, 10);
    });
  }
};
```

**Issues:**
- ⚠️ Only adds directory to file list (cosmetic)
- ⚠️ Never updates progress percentage
- ⚠️ Treats directory as a file (misleading)

---

#### Progress Bar Rendering

```typescript
<div className="scan-progress-bar">
  <div
    className="scan-progress-fill"
    style={{ width: `${progress}%` }}  // ← Uses progress state
  />
</div>
```

**Status:**
- ✅ Simple, clean implementation
- ⚠️ But `progress` is always 0 or 100 (no intermediate values)

---

## Socket.IO Event Flow Analysis

### Socket Listener in `/client/src/hooks/useSocket.ts`

**Lines 537-543:**

```typescript
socket.on('scan_progress', (data) => {
  // console.log('[Socket] scan_progress:', data.progress, '%');
  // ✅ Receives event, but does nothing with it!
});

socket.on('scan_complete', (data) => {
  // console.log('[Socket] scan_complete:', data.nodes_count, 'nodes');
  // ✅ Receives event, but does nothing with it!
});
```

**Critical Finding:**
- ✅ Socket.IO receives and acknowledges events
- ⚠️ **Does NOT dispatch to window** (unlike other events like `group-message`)
- ⚠️ **ScanProgressPanel never sees these events!**
- ⚠️ Only `directory_scanned` is implicitly handled (tree reload)

**Pattern Mismatch:**
Most events in useSocket.ts dispatch to window:
```typescript
window.dispatchEvent(new CustomEvent('group-message', { detail: data }));
```

But `scan_progress` and `scan_complete` are ignored!

---

## Issues Found

### 🔴 CRITICAL (Blocks functionality)

1. **Missing Window Events Dispatch (Line 537-543)**
   - `scan_progress` and `scan_complete` Socket.IO events are received but not dispatched to window
   - `ScanProgressPanel` listens to window events but never receives them
   - **Result:** Progress bar never updates
   - **Fix:** Add `window.dispatchEvent()` calls in useSocket.ts for these events

2. **Type Mismatch: Backend vs Frontend (Line 63-64)**
   - Backend emits `{current, indexed, file, path}` for `scan_progress`
   - Frontend expects `{progress: number, status?: string, file_path?: string}`
   - `progress` field will be `undefined` - progress bar stays at 0%
   - **Fix:** Backend must emit `progress` as calculated percentage

3. **No Total Count During Progress (semantic_routes.py)**
   - `scan_progress` emitted without total file count
   - `total_scanned` only available in `scan_complete` event
   - Frontend cannot calculate percentage (current/total*100)
   - **Fix:** Add total count to `scan_progress` event payload

### 🟡 MAJOR (Degrades UX)

4. **Progress Not Per-File (semantic_routes.py)**
   - Only emitted "every 10 files" (sparse updates)
   - Progress bar appears to hang for seconds
   - **Fix:** Emit progress on EVERY file or use batch counts

5. **Progress Calculation Logic Missing (ScanProgressPanel.tsx)**
   - No code to calculate percentage from counts
   - Frontend assumes backend sends percentage
   - **Fix:** Add explicit calculation: `(current / total * 100).toFixed(0)`

6. **Event Timing Issues (ScanProgressPanel.tsx line 90-94)**
   - Reset after 3 seconds is too aggressive
   - Users don't see final count
   - **Fix:** Increase to 5-10 seconds or add user dismiss button

7. **Directory vs File Confusion (ScanProgressPanel.tsx line 97-109)**
   - `directory_scanned` treated as "file" in UI
   - Shows folder icon + folder path in file list
   - **Fix:** Separate folder handling or different visual indicator

### 🟠 MINOR (Polish)

8. **No Pause/Cancel UI**
   - Progress bar shows 0-100% but user can't stop scan
   - Backend has `stop_scan_all` endpoint but no UI button
   - **Fix:** Add stop button or pause control

9. **No Error State**
   - If scan fails, progress bar just disappears
   - User doesn't know if scan succeeded or failed
   - **Fix:** Add error state with red progress bar

10. **Accessibility Missing**
    - No aria-labels on progress bar
    - `width: ${progress}%` not announced to screen readers
    - **Fix:** Add `aria-valuenow`, `aria-valuemin`, `aria-valuemax`

---

## Progress Tracking Verification

### Is Progress Per-File or Per-Folder?

**Backend Answer:** Per-file (counts individual files during scan)

```python
for total_scanned % 10 == 0:  # Every 10 files processed
    emit("scan_progress", {"current": total_scanned, "indexed": indexed})
```

**Frontend Interpretation:** Assumes per-file updates via `file_path` field

```typescript
if (event.detail.file_path) {
  // Track individual file
  setScannedFiles(prev => [newFile, ...prev].slice(0, 10));
}
```

**Verdict:** ✅ Consistent (per-file tracking), but frequency is too sparse

---

## Total Count Calculation

### Where Does Total Come From?

**In `scan_progress` events:** ⚠️ MISSING
- Only has `current` (files processed so far)
- No way to know final total

**In `scan_complete` event:** ✅ Available
- `total_scanned` field provided
- But it's too late - scan already finished

**In `directory_scanned` event:** ⚠️ Only file count
- `files_count` provided
- Not total scanned (only final count for directory)

### How Frontend Calculates Percentage

Currently: ❌ Doesn't
- Assumes backend sends `progress: number` (0-100)
- Backend sends `current: number` (absolute count)
- Result: `progress` is always `undefined`

**Should be:**
```javascript
const percentage = (current / total * 100).toFixed(0);
```

But requires total in every `scan_progress` event.

---

## Event Lifecycle

```
User adds folder via UI
    ↓
POST /api/watcher/add
    ↓
get_watcher() + scan_directory()
    ↓
For each file:
  - emit scan_progress [every 10 files] ⚠️ SPARSE
  - update counts (current, indexed, skipped)
    ↓
Scan complete:
  - emit scan_complete [final event]
  - includes total_scanned ✅
    ↓
Socket.IO server receives both events
    ↓
useSocket.ts receives both events
    ↓
⚠️ NOT dispatched to window ⚠️
    ↓
ScanProgressPanel never sees them ❌
    ↓
Progress bar stays at 0% ❌
```

---

## Recommendations

### Phase 92 Fixes (Priority)

**MUST FIX (P0):**

1. **Update useSocket.ts (lines 537-543):**
   ```typescript
   socket.on('scan_progress', (data) => {
     if (typeof window !== 'undefined') {
       window.dispatchEvent(new CustomEvent('scan_progress', { detail: data }));
     }
   });

   socket.on('scan_complete', (data) => {
     if (typeof window !== 'undefined') {
       window.dispatchEvent(new CustomEvent('scan_complete', { detail: data }));
     }
   });
   ```

2. **Update backend event payload (semantic_routes.py):**
   ```python
   # Calculate progress percentage upfront
   progress_pct = int((total_scanned / estimated_total) * 100) if estimated_total else 0

   await socketio.emit('scan_progress', {
       'progress': progress_pct,      # ← NEW: percentage
       'current': total_scanned,
       'indexed': indexed,
       'total': estimated_total,      # ← NEW: total count
       'file': scanned_file.name,
       'path': str(scan_path),
   })
   ```

3. **Fix ScanProgressPanel listener (line 63):**
   ```typescript
   const handleScanProgress = (event: CustomEvent<{
     progress: number;     // ← Now guaranteed
     current?: number;
     indexed?: number;
     total?: number;
     file_path?: string;
   }>) => {
     setProgress(Math.min(99, event.detail.progress));  // Cap at 99% until complete
     setIsScanning(true);
     // ... rest of logic
   };
   ```

**SHOULD FIX (P1):**

4. Increase emit frequency: Every file instead of every 10
5. Add estimated total calculation on backend
6. Fix 3-second reset timeout (increase to 8 seconds)
7. Add pause/stop button in UI
8. Add error state handling
9. Add accessibility attributes

---

## Files Involved

| File | Status | Issue Type |
|------|--------|-----------|
| `/client/src/hooks/useSocket.ts` | ⚠️ Missing dispatch | Critical |
| `/client/src/components/chat/ScanProgressPanel.tsx` | ⚠️ Type mismatch | Critical |
| `/src/api/routes/semantic_routes.py` | ⚠️ Missing fields | Critical |
| `/src/api/routes/watcher_routes.py` | ✅ OK | Info only |
| `/client/src/components/chat/ScanProgressPanel.css` | ✅ OK | No changes needed |

---

## Testing Checklist

- [ ] Add folder and watch progress bar update in real-time
- [ ] Verify percentage goes 0 → 100 (not jump 0 → 100)
- [ ] Verify final count displays correctly
- [ ] Check file list shows last 10 scanned files
- [ ] Verify panel collapses/expands correctly
- [ ] Test with large directory (>1000 files)
- [ ] Test with deeply nested folders
- [ ] Check animation smoothness
- [ ] Verify cleanup after scan completes

---

## Summary

The progress bar UI component is **well-designed** but **disconnected from data flow**. The Socket.IO events exist and contain useful data, but they never reach the component because `useSocket.ts` doesn't dispatch them to the window.

Additionally, there's a **type contract mismatch** between what the backend emits (`current`, `indexed`, absolute counts) and what the frontend expects (`progress` percentage).

**Estimated Fix Time:** 30 minutes (wire up events + add percentage calculation)

---

**Audit Complete** ✓
Scout: Haiku 4.5
Phase: 92
