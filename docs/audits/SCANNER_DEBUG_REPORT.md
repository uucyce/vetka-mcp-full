# Scanner Debug Report - Phase 54.9

**Date:** 2026-01-09
**Status:** Analysis only - NO FIXES APPLIED
**Purpose:** Debug chain: Scanner → Qdrant → Tree → Hostess → Camera

---

## 1. Scanner → Qdrant

### ✅ add_directory() вызывает embedding pipeline

**File:** `src/scanners/file_watcher.py:258-296`
**Status:** ДА, but WITH CAVEAT

```python
def add_directory(self, path: str, recursive: bool = True) -> bool:
    # Adds directory to watch list
    # CREATES observer with VetkaFileHandler
    # BUT: Doesn't immediately scan/embed files!
    observer.schedule(handler, path, recursive=recursive)
    observer.start()  # Only WATCHES for changes, doesn't index existing files
```

**Issue Found:**
- ✅ File changes ARE detected via watchdog
- ✅ Changes emit socket events (node_added, node_updated, etc.)
- ❌ **EXISTING files in the directory are NOT indexed automatically**
- ❌ No embedding pipeline runs when add_directory() is called

### ❌ Файлы сохраняются в Qdrant

**File:** `src/api/routes/watcher_routes.py:73-116`
**Status:** ONLY for browser files, NOT for server files

```python
@router.post("/add")
async def add_watch_directory(req: AddWatchRequest, request: Request):
    # Gets watcher singleton
    # Calls watcher.add_directory(path)
    # Returns success
    # BUT: Doesn't call Qdrant indexing!
```

**Issue Found:**
- ❌ **No Qdrant interaction in /add endpoint**
- ✅ Browser files ARE indexed in /add-from-browser endpoint (line 238-312)
- ✅ Single files ARE indexed in /index-file endpoint (line 361-484)
- ❌ **Missing: Server directory scanning → Qdrant integration**

### ⚠️ Socket emit после сканирования

**File:** `src/scanners/file_watcher.py:329-365`
**Status:** PARTIAL - only on file CHANGES, not on directory ADD

```python
def _on_file_change(self, event: Dict) -> None:
    # Emits these events:
    if event_type == 'created':
        self._emit('node_added', {'path': path, 'event': event})
    elif event_type == 'deleted':
        self._emit('node_removed', {'path': path, 'event': event})
    elif event_type == 'modified':
        self._emit('node_updated', {'path': path, 'event': event})
    elif event_type == 'bulk_update':
        self._emit('tree_bulk_update', {...})
```

**Events Found:**
- ✅ node_added
- ✅ node_removed
- ✅ node_updated
- ✅ node_moved
- ✅ tree_bulk_update (for git/npm bulk operations)
- ❌ **Missing: scan_complete or directory_indexed event**

---

## 2. Qdrant → Tree

### ❌ Новые файлы в /api/tree/data

**File:** `src/api/routes/tree_routes.py:78-420`
**Status:** НЕТ for server directories

```python
@router.get("/data")
async def get_tree_data(mode: str = Query("directory")):
    # Step 1: Fetches ALL scanned_file records from Qdrant
    # Step 2: Filters out deleted files
    # Step 3: Builds directory hierarchy
    # Step 4: Calculates FAN layout
    # Step 5: Returns nodes + edges
```

**Issue Found:**
- ✅ Files appear IF they're in Qdrant with type='scanned_file'
- ✅ Browser files appear (browser:// prefix works, lines 152-227)
- ✅ /api/tree/data properly filters browser:// virtual paths
- ❌ **Server directories added via /add never get indexed to Qdrant**
- ❌ **Result: Empty tree after adding server directory**

### ⚠️ Координаты правильные

**File:** `src/api/routes/tree_routes.py:266-283`
**Status:** DEPENDS ON SOURCE

For browser files:
- ✅ Uses FAN layout: `calculate_directory_fan_layout()`
- ✅ Returns positions with x, y, z coordinates
- ✅ Parent folder hierarchy works (browser://root/folder structure)

For potential server files:
- ✅ Would use same FAN layout
- ❓ NO TEST - because server files never reach Qdrant

### ✅ parent_folder есть

**File:** `src/api/routes/tree_routes.py:177-245`
**Status:** ДА

```python
for point in all_files:
    parent_folder = p.get('parent_folder', '')
    if not parent_folder and file_path:
        parent_folder = '/'.join(file_path.split('/')[:-1])
    if not parent_folder:
        parent_folder = 'root'
```

- ✅ parent_folder stored in Qdrant payload
- ✅ Sugiyama layout uses parent_folder for tree structure
- ✅ Hierarchy is properly reconstructed

---

## 3. Scanner → Hostess

### ✅ Socket event для Hostess

**Events Found:**
- Browser files: `browser_folder_added` (from /add-from-browser endpoint)
- File changes: Individual node events (node_added, node_updated, etc.)
- ❌ **Missing: scan_complete or initial_scan_done**

### ✅ Backend отправляет browser_folder_added

**File:** `src/api/routes/watcher_routes.py:314-329`
**Status:** ДА - but ONLY for browser files

```python
if socketio:
    try:
        event_data = {
            'root_name': root_name,
            'files_count': len(files),
            'indexed_count': indexed_count,
            'virtual_path': f"browser://{root_name}"
        }
        await socketio.emit('browser_folder_added', event_data)
        print(f"[Watcher] Emitted browser_folder_added: {root_name}")
    except Exception as e:
        print(f"[Watcher] Socket emit error: {e}")
```

- ✅ Emits for browser files (virtual path)
- ❌ **No emit for server directories (/add endpoint)**

### ✅ Frontend слушает browser_folder_added

**File:** `client/src/hooks/useSocket.ts:226-261`
**Status:** ДА

```typescript
socket.on('browser_folder_added', async (data) => {
    console.log('[Socket] browser_folder_added:', data.root_name, data.files_count, 'files');

    // Fetches fresh tree data via HTTP
    const response = await fetch('/api/tree/data');
    if (response.ok) {
        const treeData = await response.json();
        // Updates store with new nodes/edges
        setNodesFromRecord(convertedNodes);
        setEdges(edges);

        // Camera fly-to after tree is loaded
        setTimeout(() => {
            setCameraCommand({
                target: data.root_name,
                zoom: 'medium',
                highlight: true,
            });
        }, 300);
    }
});
```

- ✅ Listener installed
- ✅ Reloads tree via HTTP
- ✅ Triggers camera fly-to

### ❌ Hostess сообщение НЕ добавляется

**File:** `client/src/components/chat/ChatPanel.tsx:309-371`
**Status:** PARTIAL - only for ScannerPanel events

```typescript
const handleScannerEvent = useCallback((event: ScannerEvent) => {
    let hostessMessage = '';

    switch (event.type) {
        case 'directory_added':
            hostessMessage = `${event.filesCount} files from "${event.path}"...`;
            break;
        case 'scan_complete':
            hostessMessage = 'Scan complete! Your tree is ready.';
            break;
        case 'files_dropped':
            hostessMessage = `Dropped ${event.filesCount} files from "${event.path}"`;
            break;
    }

    if (hostessMessage) {
        addChatMessage({
            id: crypto.randomUUID(),
            role: 'assistant',
            agent: 'Hostess',
            content: hostessMessage,
            type: 'text',
            timestamp: new Date().toISOString(),
        });
    }
}, [addChatMessage]);
```

- ✅ handleScannerEvent exists
- ✅ Processes directory_added, scan_complete, files_dropped
- ❌ **ScannerPanel.tsx is DISABLED (Phase 54.7 - drag & drop disabled)**
- ❌ **onEvent callback never called → Hostess message never added**

**Evidence:**
- `client/src/components/scanner/ScannerPanel.tsx:157` - `export const ScannerPanel`
- `client/src/components/chat/ChatPanel.tsx:475-500` - ScannerPanel rendered but disabled
- `client/src/components/scanner/ScannerPanel.tsx:335-400` - ALL drag/drop handlers commented out

---

## 4. Scanner → Camera

### ❌ Camera event НЕ отправляется для server directories

**Current Events:**
- ✅ `browser_folder_added` triggers camera fly
- ❌ **No equivalent for server directories**

**File:** `client/src/components/canvas/CameraController.tsx:79-105`
**Status:** НЕТ server directory event handler

```typescript
// Only listens for 'camera-fly-to-folder' custom event
window.addEventListener('camera-fly-to-folder', handleFlyToFolder as EventListener);

// Never triggered by backend server directory add!
```

### ❓ Координаты откуда

**When Event IS Triggered (browser files):**
- `data.root_name` used as target
- CameraController finds node by name match
- Uses node.position from store

**Issue:**
- ❌ If node not in tree yet, camera has nowhere to fly
- ⚠️ Timing issue: tree might not be loaded when camera tries to fly

### ❌ Триггер после scan НЕ работает для server directories

**Flow for browser files:**
1. Browser drops folder → `/api/watcher/add-from-browser`
2. Qdrant indexed
3. Socket: `browser_folder_added` emitted
4. Frontend: Reloads tree via `/api/tree/data`
5. Frontend: Calls `setCameraCommand({target: root_name, ...})`
6. Camera flies to folder

**Flow for server directories (BROKEN):**
1. Server folder added via `/api/watcher/add` endpoint
2. ❌ Watcher starts monitoring (no indexing!)
3. ❌ No socket event emitted
4. ❌ Frontend never knows files were added
5. ❌ Camera never flies
6. ❌ Hostess never speaks

---

## 5. Что сломано

### 🔴 PRIMARY ISSUE: Missing integration between Server Directory Watcher and Qdrant

**Root Cause:**
- `/api/watcher/add` endpoint only starts file watching via watchdog
- It does NOT index existing files to Qdrant
- It does NOT emit any socket event to notify frontend

**Evidence Chain:**
1. `watcher_routes.py:110` - calls `watcher.add_directory(path)` ✅
2. `file_watcher.py:258-296` - only starts observer, doesn't index ✅
3. No Qdrant client used in /add endpoint ✅
4. No socket event emitted after directory added ✅
5. Frontend never knows about new files ✅

### 🟡 SECONDARY ISSUE: Phase 54.7 - Drag & Drop Disabled

**Status:** All drop handlers commented out in `App.tsx:277-318`

```typescript
/* const handleFileDrop = useCallback(async (e: DragEvent, zone: DropZone) => {
    // ... entire handler disabled
}, [isChatOpen, resolveFilePath, addFileToTree]); */
```

**Impact:**
- ❌ ScannerPanel.tsx never receives drop events
- ❌ onEvent callback chain broken
- ❌ Hostess messages for server files never added
- ❌ Manual scanner UI unavailable

### 🟡 TERTIARY ISSUE: No scan_complete Event for Server Directories

**Currently:**
- Only individual file change events (created, modified, deleted)
- No aggregate "directory scan complete" event
- No way to know when all existing files in a directory have been indexed

---

## 6. Рекомендации (Fix Strategy)

### Phase 1: Server Directory Scanning → Qdrant Integration

**Missing endpoint or modify `/add` endpoint:**

Option A: Add `POST /api/watcher/scan-directory`
```python
# Scan existing files in directory (after adding to watch)
# Call Qdrant updater to index all files
# Emit 'directory_scanned' socket event
```

Option B: Modify `POST /api/watcher/add` to:
```python
# 1. Add to watcher (start monitoring changes)
# 2. Scan existing files immediately
# 3. Index files to Qdrant
# 4. Emit socket event: 'directory_scanned' with file count
```

### Phase 2: Socket Event Chain

**Add backend event:**
```python
# After directory scanned to Qdrant
await socketio.emit('directory_scanned', {
    'path': directory_path,
    'files_count': indexed_count,
    'indexed_at': time.time()
})
```

**Frontend listens (useSocket.ts):**
```typescript
socket.on('directory_scanned', async (data) => {
    // Reload tree via /api/tree/data
    // Trigger camera fly-to
    // Update store
});
```

### Phase 3: Re-enable Phase 54.7 Features (Optional)

**If using Tauri migration:**
- Un-comment drag/drop handlers in App.tsx
- Un-comment ScannerPanel handlers
- Restore Hostess integration

**Or keep disabled if using only `/add` endpoint approach**

### Phase 4: QdrantIncrementalUpdater Integration

**Use existing updater (already used in watcher_routes.py):**
```python
from src.scanners.qdrant_updater import get_qdrant_updater

updater = get_qdrant_updater(qdrant_client=qdrant_client)
# updater already has .update_from_directory(path) or similar
```

---

## 7. Timing Flow Diagram

### Current (BROKEN) - Server Directory:
```
User: POST /api/watcher/add → /path/to/project
│
└─> watcher.add_directory(path)
    └─> starts watchdog observer
    └─> waits for file CHANGES
    │
    └─> (NOTHING happens for existing files)
    └─> (no socket event)
    └─> (no tree update)
    └─> (camera doesn't fly)
    └─> (Hostess silent)
```

### Current (WORKING) - Browser Directory:
```
User: Drops folder from browser
│
└─> App.tsx: handleFileDrop()
    └─> readDirectoryRecursive(handle)
    └─> POST /api/watcher/add-from-browser
        └─> Indexes files to Qdrant ✅
        └─> Emits 'browser_folder_added' ✅
        │
        └─> useSocket: browser_folder_added listener
            └─> Reloads tree via /api/tree/data ✅
            └─> setCameraCommand({target: root_name}) ✅
            │
            └─> CameraController: finds node
                └─> Camera flies ✅
                └─> Hostess speaks ✅
```

### Proposed (FIXED) - Server Directory:
```
User: POST /api/watcher/add → /path/to/project
│
└─> watcher.add_directory(path)
    └─> starts watchdog observer ✅
    │
    └─> [NEW] scan_directory(path)
        └─> read all existing files
        └─> get_qdrant_updater().update_from_directory()
        └─> index to Qdrant ✅
        │
        └─> Emit 'directory_scanned' ✅
            │
            └─> useSocket: directory_scanned listener
                └─> Reload tree via /api/tree/data ✅
                └─> setCameraCommand({target: directory_name}) ✅
                │
                └─> CameraController: finds node
                    └─> Camera flies ✅
                    └─> Hostess speaks ✅
```

---

## Summary Table

| Component | Status | Issue | Priority |
|-----------|--------|-------|----------|
| Scanner → Watchdog | ✅ | None | N/A |
| Watchdog → Qdrant | ❌ | No integration | 🔴 CRITICAL |
| Qdrant → Tree | ✅ | Only if in Qdrant | N/A |
| Tree → Hostess | ✅ | Missing event source | Blocked by above |
| Hostess → Camera | ✅ | No trigger for server files | Blocked by above |
| Socket Events | ⚠️ | browser_folder_added only | 🟡 MEDIUM |
| Drag & Drop UI | ❌ | Phase 54.7 disabled | 🟡 OPTIONAL |

---

## Conclusion

The scanner-to-camera pipeline is **functionally incomplete** for server directories:

1. **Root cause:** Server directories are watched but never indexed to Qdrant
2. **Impact:** Empty tree, silent Hostess, immobile camera
3. **Solution:** Add Qdrant scanning step + socket event to watcher/add endpoint
4. **Effort:** ~1-2 hours to implement Phase 1-2
5. **Testing:** Verify event chain: add → scan → emit → reload → fly

**NEXT STEP:** Proceed with fixes after approval of this analysis.
