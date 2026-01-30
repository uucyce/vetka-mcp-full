# Scanner Chain - Detailed Flow Diagrams

**Visual guide to understand every step**

---

## Overview: Full System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER ACTION                                 │
│                   (Add Directory)                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                 ┌──────────┴──────────┐
                 │                     │
                 ▼                     ▼
        ┌─────────────────┐   ┌──────────────────┐
        │  API Endpoint   │   │  Browser Drop    │
        │ /add (broken)   │   │ /add-from-browser│
        └────────┬────────┘   └────────┬─────────┘
                 │                     │
        ❌ SCANNING ✅ SCANNING        ✅ SCANNING
        ❌ INDEXING ✅ INDEXING        ✅ INDEXING
        ❌ EMITTING ✅ EMITTING        ✅ EMITTING
                 │                     │
                 └──────────┬──────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  Qdrant DB    │
                    │ vetka_elisya  │
                    └───────┬───────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │   Tree Routes /api/tree/data  │
            │    (Scroll files from DB)     │
            └───────────┬───────────────────┘
                        │
                        ▼
            ┌───────────────────────────┐
            │    Layout Calculation     │
            │  (FAN layout, Sugiyama)   │
            └───────────┬───────────────┘
                        │
                        ▼
            ┌───────────────────────────┐
            │   Frontend Store Update   │
            │  (setNodesFromRecord)     │
            └───────────┬───────────────┘
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
        ┌───────────┐          ┌──────────┐
        │ Hostess   │          │  Camera  │
        │ (Message) │          │ (Fly-To) │
        └───────────┘          └──────────┘
```

---

## Flow 1: Browser Files (WORKING) ✅

### Visual Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER DROPS FOLDER                            │
│                   (from browser UI)                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │ App.tsx: handleFileDrop()       │
        │ (Phase 54.7: DISABLED)         │
        │ BUT: When enabled or           │
        │      direct HTTP call works    │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │ readDirectoryRecursive()       │
        │ (Browser File System API)      │
        │ [Line 129-155]                 │
        │ Output: BrowserFile[]          │
        └────────────┬───────────────────┘
                     │ (relativePath, name, size, lastModified)
                     │
                     ▼
        ┌─────────────────────────────────────────┐
        │ POST /api/watcher/add-from-browser      │
        │ [watcher_routes.py:197-337]             │
        └────────────┬────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
    ┌─────────────────┐   ┌──────────────────┐
    │ Get Qdrant      │   │ Get Updater      │
    │ (line 210-214)  │   │ (line 221)       │
    │ client available│   │ get_qdrant_      │
    └────────┬────────┘   │ updater()        │
             │             └────────┬────────┘
             │                      │
             └──────────┬───────────┘
                        │
    ┌───────────────────┴──────────────────┐
    │ FOR EACH FILE IN files:              │
    │                                      │
    ├─ [Line 230] Create virtual_path:    │
    │   "browser://root/relative/path"    │
    │                                      │
    ├─ [Line 246] Generate embedding:     │
    │   updater._get_embedding(text)      │
    │                                      │
    ├─ [Line 250-276] Create PointStruct: │
    │   ┌──────────────────────────────┐  │
    │   │ id: uuid5(virtual_path)      │  │
    │   │ vector: embedding            │  │
    │   │ payload:                     │  │
    │   │   - type: 'scanned_file'    │  │
    │   │   - path: virtual_path       │  │
    │   │   - name: file.name          │  │
    │   │   - parent_folder: ...       │  │
    │   │   - source: browser_scanner  │  │
    │   │   - content: preview         │  │
    │   │   - timestamps               │  │
    │   └──────────────────────────────┘  │
    │                                      │
    └──────────────┬───────────────────────┘
                   │
                   ▼
        ┌──────────────────────────────────┐
        │ [Line 273] Upsert to Qdrant:     │
        │ qdrant_client.upsert(            │
        │   collection_name='vetka_elisya',│
        │   points=[point]                 │
        │ )                                │
        │ indexed_count += 1               │
        └──────────────┬───────────────────┘
                       │
                       ▼ (after all files)
        ┌──────────────────────────────────┐
        │ [Line 293-312]                   │
        │ EMIT SOCKET EVENT:               │
        │                                  │
        │ socketio.emit(                   │
        │   'browser_folder_added', {      │
        │     root_name: root_name,        │
        │     files_count: len(files),     │
        │     indexed_count: count,        │
        │     virtual_path: f"browser://  │
        │     {root_name}"                 │
        │   }                              │
        │ )                                │
        └──────────────┬───────────────────┘
                       │ [Line 308]
                       │ (async emit)
                       │
          ┌────────────┴───────────┐
          │                        │
     [Backend Done]           [Frontend Hears]
          │                        │
          │                        ▼
          │           ┌────────────────────────────┐
          │           │ [useSocket.ts:227]         │
          │           │ socket.on(                 │
          │           │   'browser_folder_added'  │
          │           │ )                          │
          │           └────────────┬───────────────┘
          │                        │
          │                        ▼
          │           ┌────────────────────────────┐
          │           │ [useSocket.ts:232]         │
          │           │ fetch('/api/tree/data')    │
          │           │ → GET tree from backend    │
          │           └────────────┬───────────────┘
          │                        │
          │                        ▼
          │           ┌────────────────────────────┐
          │           │ tree_routes.py:125-137     │
          │           │ Scroll all scanned_files   │
          │           │ from Qdrant                │
          │           │                            │
          │           │ Files found: YES ✅        │
          │           │ (browser:// files there)   │
          │           └────────────┬───────────────┘
          │                        │
          │                        ▼
          │           ┌────────────────────────────┐
          │           │ tree_routes.py:167-247     │
          │           │ BUILD HIERARCHY:           │
          │           │ - folders dict             │
          │           │ - files_by_folder dict     │
          │           │ - FAN layout positions     │
          │           │                            │
          │           │ Returns: nodes[], edges[]  │
          │           └────────────┬───────────────┘
          │                        │
          │                        ▼
          │           ┌────────────────────────────┐
          │           │ [useSocket.ts:244-245]     │
          │           │ convertApiResponse()       │
          │           │ setNodesFromRecord()       │
          │           │ → Store updated ✅         │
          │           └────────────┬───────────────┘
          │                        │
          │                        ▼
          │           ┌────────────────────────────┐
          │           │ [useSocket.ts:250]         │
          │           │ setCameraCommand({         │
          │           │   target: root_name,       │
          │           │   zoom: 'medium',          │
          │           │   highlight: true          │
          │           │ })                         │
          │           └────────────┬───────────────┘
          │                        │
          │                        ▼
          │           ┌────────────────────────────┐
          │           │ CameraController.tsx       │
          │           │ [line 113]                 │
          │           │ findNode(target)           │
          │           │ → Finds "root_name" node   │
          │           │ in store ✅                │
          │           └────────────┬───────────────┘
          │                        │
          │                        ▼
          │           ┌────────────────────────────┐
          │           │ CameraController.tsx       │
          │           │ [line 169-179]             │
          │           │ Setup animation:           │
          │           │ - startPos: current camera│
          │           │ - targetPos: node position│
          │           │ - finalDistance: 30       │
          │           │                            │
          │           │ Enable animation ✅       │
          │           └────────────┬───────────────┘
          │                        │
          │                        ▼
          │           ┌────────────────────────────┐
          │           │ useFrame() callback        │
          │           │ [line 185-236]             │
          │           │                            │
          │           │ Every frame:               │
          │           │ - Update camera position   │
          │           │ - Interpolate rotation     │
          │           │ - Progress 0→1 over 2.5s   │
          │           │                            │
          │           │ Animation complete ✅     │
          │           └────────────┬───────────────┘
          │                        │
          │                        ▼
          │           ┌────────────────────────────┐
          │           │ [ChatPanel.tsx:287-306]    │
          │           │                            │
          │           │ IF activeTab='scanner':{   │
          │           │   Hostess greeting shows   │
          │           │ }                          │
          │           │                            │
          │           │ OR if event handler fired: │
          │           │ [ChatPanel.tsx:313]        │
          │           │ handleScannerEvent({       │
          │           │   type: 'directory_added'  │
          │           │ })                         │
          │           │ → Hostess message ✅       │
          │           └────────────────────────────┘
          │
    [Result: SUCCESS ✅]
    - Tree populated
    - Camera moves
    - Hostess speaks
```

---

## Flow 2: Server Directories (BROKEN) ❌

### Visual Flow - WHERE IT BREAKS

```
┌─────────────────────────────────────────────────────────────────┐
│           POST /api/watcher/add                                 │
│           (Add server directory to watch)                       │
│           [watcher_routes.py:73-116]                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
        ┌─────────────────────────────────┐
        │ [Line 91-97]                    │
        │ Validate input:                 │
        │ - path exists? ✅               │
        │ - is directory? ✅              │
        │ - user expanded? ✅             │
        └────────────────┬────────────────┘
                         │
                         ▼
        ┌─────────────────────────────────┐
        │ [Line 100-101]                  │
        │ Get socketio from app state ✅  │
        │ Get watcher singleton ✅        │
        └────────────────┬────────────────┘
                         │
                         ▼
        ┌─────────────────────────────────┐
        │ [Line 103]                      │
        │ watcher.add_directory()         │
        │ [file_watcher.py:258-296]       │
        │                                 │
        ├─ [Line 270] Normalize path ✅   │
        ├─ [Line 272-274] Validate ✅     │
        ├─ [Line 282] Create observer ✅  │
        ├─ [Line 283] Create handler ✅   │
        ├─ [Line 284] Schedule observer ✅│
        ├─ [Line 285] Start observer ✅   │
        │                                 │
        │ This watches for FUTURE changes│
        │ BUT does NOT scan existing!    │
        │                                 │
        ├─ [Line 287-289] Save state ✅   │
        ├─ [Line 291] Print message ✅    │
        └────────────────┬────────────────┘
                         │
                         ▼
        ┌─────────────────────────────────────────────┐
        │ ❌ ❌ ❌ HERE IS THE BROKEN PART ❌ ❌ ❌  │
        │                                             │
        │ NO scanning of existing files!              │
        │ NO Qdrant indexing!                         │
        │ NO socket event!                            │
        │                                             │
        │ Result:                                     │
        │ - indexed_count = 0                         │
        │ - Qdrant empty                              │
        │ - No event emitted                          │
        │                                             │
        │ [MISSING CODE SHOULD BE HERE]               │
        │ [Lines 221-286 from add-from-browser]       │
        │ [Lines 308 from add-from-browser]           │
        └─────────────────┬──────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────┐
        │ [Line 105-109]                  │
        │ Return response:                │
        │ {                               │
        │   'success': True,              │
        │   'watching': [path],           │
        │   'message': 'Now watching...'  │
        │ }                               │
        │                                 │
        │ But files are NOT indexed!      │
        └────────────────┬────────────────┘
                         │
          ┌──────────────┴──────────────┐
          │                             │
    [Backend Done]              [Frontend Waits]
          │                             │
          │                             ▼
          │                 ┌───────────────────────┐
          │                 │ Waiting for event     │
          │                 │ (never comes) ❌      │
          │                 │                       │
          │                 │ Possible waits:       │
          │                 │ - socket event        │
          │                 │ - tree reload         │
          │                 │ - camera command      │
          │                 │ - Hostess message     │
          │                 │                       │
          │                 │ NONE OF THESE HAPPEN! │
          │                 └───────────────────────┘
          │                             │
          │                             ▼ (after timeout)
          │                 ┌───────────────────────┐
          │                 │ Frontend gives up     │
          │                 │ OR user tries again   │
          │                 │                       │
          │                 │ Result:               │
          │                 │ - Tree stays empty ❌ │
          │                 │ - Camera doesn't move │
          │                 │ - Hostess silent      │
          │                 │ - User frustrated 😠  │
          │                 └───────────────────────┘
          │
    [Result: FAILURE ❌]
    - Tree empty (only root)
    - Camera immobile
    - Hostess silent
    - User sees nothing happened
```

---

## Flow 3: Watchdog Monitoring (WORKS but Incomplete)

### What Actually Works

```
Directory is watching (started by add_directory())
                │
    ┌───────────┴───────────┬─────────────┬──────────────┐
    │                       │             │              │
    ▼                       ▼             ▼              ▼
 FILE CREATED        FILE MODIFIED    FILE DELETED   FILE MOVED
    │                       │             │              │
    ├─ watchdog detects     ├─ detected   ├─ detected   ├─ detected
    │   event                │             │              │
    │                        │             │              │
    └────────┬──────────────┬┴────────────┬┴──────────────┘
             │              │             │
             ▼              ▼             ▼
    ┌──────────────────────────────────────────┐
    │ VetkaFileHandler._on_file_change()       │
    │ [file_watcher.py:329-365]                │
    │                                          │
    ├─ Coalesce rapid events                   │
    ├─ Detect bulk operations                  │
    └──────────────┬───────────────────────────┘
                   │
    ┌──────────────┴──────────────┐
    │                             │
    ▼                             ▼
created       deleted      modified    moved     bulk_update
event         event        event       event     event
    │             │            │         │          │
    ├─────────────┴────────────┴────────┬┴─────────┤
    │                                   │          │
    ▼                                   ▼          ▼
emit('node_added')              emit('node_updated')
emit('node_removed')            emit('tree_bulk_update')
emit('node_moved')

    ▼
[Frontend receives individual node updates]

These work for monitoring CHANGES
But NOT for initial directory scan!
```

---

## Flow 4: What SHOULD Happen (Proposed Fix)

### Fixed Flow - Server Directories

```
┌─────────────────────────────────────────────────────────────────┐
│           POST /api/watcher/add                                 │
│           (Add server directory to watch)                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
        ┌─────────────────────────────────┐
        │ [Line 103] add_directory() ✅    │
        │ Starts watchdog observer         │
        └────────────────┬────────────────┘
                         │
        ┌────────────────┴─────────────────────────────┐
        │                                              │
        │ ✨ ✨ ✨ NEW CODE SHOULD GO HERE ✨ ✨ ✨ │
        │                                              │
        ▼                                              ▼
  ┌──────────────────────┐                  ┌──────────────────────┐
  │ Add to watchdog      │                  │ Scan existing files  │
  │ (DONE)               │                  │ (NEW)                │
  │                      │                  │                      │
  │ Watches for:         │                  │ [NEW lines ~110-150] │
  │ - created ✅         │                  │                      │
  │ - deleted ✅         │                  │ FOR EACH FILE:       │
  │ - modified ✅        │                  │ ├─ Check supported   │
  └──────────────────────┘                  │   extension          │
                         │                  │ ├─ Read content      │
                         │                  │ ├─ Generate embedding│
                         │                  │ ├─ Create point      │
                         │                  │ └─ Upsert to Qdrant  │
                         │                  │                      │
                         │                  │ indexed_count++      │
                         │                  │                      │
                         │                  └──────────────┬───────┘
                         │                                 │
                         └─────────────────┬───────────────┘
                                           │
                                           ▼
                          ┌────────────────────────────────┐
                          │ [NEW lines ~155-165]           │
                          │ EMIT SOCKET EVENT              │
                          │                                │
                          │ socketio.emit(                 │
                          │   'directory_scanned',         │
                          │   {                            │
                          │     path: directory_path,      │
                          │     files_count: indexed_count,│
                          │     indexed_at: timestamp      │
                          │   }                            │
                          │ )                              │
                          └────────────┬───────────────────┘
                                       │
                   ┌───────────────────┴────────────────┐
                   │                                    │
        ┌──────────┴──────────┐            ┌───────────┴──────────┐
        │                     │            │                      │
   [Backend Done]        [Waiting]    [Frontend Listens]    [Files in DB]
        │                     │            │                      │
        │                     │            ▼                      ▼
        │                     │  ┌──────────────────────────┐      │
        │                     │  │ socket.on(               │      │
        │                     │  │   'directory_scanned'    │      │
        │                     │  │ )                        │      │
        │                     │  └────────┬─────────────────┘      │
        │                     │           │                        │
        │                     │           ▼                        │
        │                     │  ┌──────────────────────────┐      │
        │                     │  │ fetch('/api/tree/data')  │      │
        │                     │  └────────┬─────────────────┘      │
        │                     │           │                        │
        │                     │           ▼                        │
        │                     │  ┌──────────────────────────┐      │
        │                     │  │ tree_routes.py:125-137   │      │
        │                     │  │ Scroll from Qdrant       │      │
        │                     │  │ Files found: YES ✅      │──────┘
        │                     │  │ (indexed_count files)    │
        │                     │  └────────┬─────────────────┘
        │                     │           │
        │                     │           ▼
        │                     │  ┌──────────────────────────┐
        │                     │  │ Build tree structure ✅  │
        │                     │  │ Generate positions ✅    │
        │                     │  │ Create nodes/edges ✅    │
        │                     │  └────────┬─────────────────┘
        │                     │           │
        │                     │           ▼
        │                     │  ┌──────────────────────────┐
        │                     │  │ updateStore()            │
        │                     │  │ setNodesFromRecord()     │
        │                     │  └────────┬─────────────────┘
        │                     │           │
        │                     │           ▼
        │                     │  ┌──────────────────────────┐
        │                     │  │ setCameraCommand({       │
        │                     │  │   target: path,          │
        │                     │  │   zoom: 'medium'         │
        │                     │  │ })                       │
        │                     │  └────────┬─────────────────┘
        │                     │           │
        │                     │           ▼
        │                     │  ┌──────────────────────────┐
        │                     │  │ CameraController         │
        │                     │  │ finds node ✅            │
        │                     │  │ animates ✅              │
        │                     │  └────────┬─────────────────┘
        │                     │           │
        │                     │           ▼
        │                     │  ┌──────────────────────────┐
        │                     │  │ [Optional]               │
        │                     │  │ Hostess receives update  │
        │                     │  │ Adds message ✅          │
        │                     │  └────────────────────────┘
        │
    [Result: SUCCESS ✅]
    - Tree populated with 25+ nodes
    - Camera smoothly animates
    - Hostess greets user (if enabled)
    - Everything works!
```

---

## Component Interactions Map

### Qdrant Client References

```
watcher_routes.py
├─ Line 210-214: Get client (add-from-browser)
├─ Line 226: Get from request.app.state.qdrant_manager
├─ Line 230: Check hasattr(qdrant_manager, 'client')
│
└─ Line 273: upsert() call
   └─ collection_name='vetka_elisya'
   └─ points=[PointStruct(...)]

tree_routes.py
├─ Line 100: Get from memory.qdrant
│
└─ Line 125: scroll() call
   ├─ collection_name='vetka_elisya'
   ├─ filter: type='scanned_file'
   └─ Returns: Points with payload
```

### Socket Events Flow

```
Backend (emits) ──────────────────→ Frontend (listens)

watcher_routes.py:308              useSocket.ts:227
"browser_folder_added"             socket.on('browser_folder_added', ...)
{
  root_name,
  files_count,
  indexed_count,
  virtual_path
}

─ MISSING ─              ─ MISSING ─
"directory_scanned"                socket.on('directory_scanned', ...)
{
  path,
  files_count,
  indexed_at
}
```

---

## State Update Chain

```
Backend Qdrant Update
    │
    ├─→ files inserted with type='scanned_file'
    │
Frontend Socket Event (NEW)
    │
    ├─→ directory_scanned event received
    │
HTTP /api/tree/data Request
    │
    ├─→ Scroll all scanned_file points
    ├─→ Build hierarchy
    ├─→ Calculate positions
    ├─→ Create nodes/edges
    │
React Store Update
    │
    ├─→ setNodesFromRecord(nodes)
    │   └─→ Store.nodes updated
    │
    ├─→ setCameraCommand(command)
    │   └─→ Store.cameraCommand updated
    │
Component Re-render Chain
    │
    ├─→ Canvas Re-renders
    │   ├─→ FileCard components show files
    │   └─→ TreeEdges show connections
    │
    ├─→ CameraController Re-renders
    │   ├─→ Detects cameraCommand change
    │   ├─→ Animates camera
    │   └─→ Updates OrbitControls
    │
    └─→ ChatPanel Re-renders
        └─→ Optionally shows Hostess message
```

---

## Error States and Recovery

```
ERROR STATE 1: Empty Tree After Adding Directory
│
├─ Root cause: No files in Qdrant
├─ Why: /add endpoint doesn't scan
├─ Evidence:
│   └─ curl /api/tree/data shows only 1 node (root)
├─ Fix: Add scan loop + Qdrant upsert
└─ Verify: /api/tree/data shows >10 nodes

ERROR STATE 2: Camera Doesn't Move
│
├─ Root cause 2a: No socket event emitted
│   ├─ Why: /add endpoint doesn't emit
│   ├─ Evidence: No backend logs
│   └─ Fix: Add socketio.emit('directory_scanned')
│
├─ Root cause 2b: Frontend listener missing
│   ├─ Why: Listener not registered
│   ├─ Evidence: No frontend console logs
│   └─ Fix: Add socket.on('directory_scanned', ...)
│
├─ Root cause 2c: Node not found
│   ├─ Why: Tree is empty
│   ├─ Evidence: [CameraController] Node not found warning
│   └─ Fix: Ensure files in tree first
│
└─ Root cause 2d: Animation disabled
    ├─ Why: OrbitControls issue
    ├─ Evidence: Camera command logged but no movement
    └─ Fix: Check CameraController.tsx enablement

ERROR STATE 3: Hostess Silent
│
├─ Root cause 3a: ScannerPanel disabled (Phase 54.7)
│   ├─ Why: Drop UI disabled temporarily
│   ├─ Evidence: No drop handlers in App.tsx
│   └─ Fix: Re-enable drop handlers (separate task)
│
├─ Root cause 3b: Socket event doesn't trigger handler
│   ├─ Why: No 'directory_scanned' listener
│   ├─ Evidence: No frontend console logs
│   └─ Fix: Add event listener for directory_scanned
│
└─ Root cause 3c: Event received but no message
    ├─ Why: Handler logic issue
    ├─ Evidence: Event logged but no Hostess message
    └─ Fix: Debug ChatPanel handler
```

---

## Debug Breakpoints Map

### Backend Breakpoints

```
src/api/routes/watcher_routes.py
├─ Line 91: path = req.path               [INPUT]
├─ Line 103: watcher.add_directory()      [FUNCTION CALL]
├─ Line 105-109: Return response          [OUTPUT]
│
│ [SHOULD ADD BREAKPOINTS HERE]
│ ├─ Line ~110: Get Qdrant client
│ ├─ Line ~115: Start scanning loop
│ ├─ Line ~120: For each file
│ ├─ Line ~130: Generate embedding
│ ├─ Line ~140: Upsert to Qdrant
│ └─ Line ~150: Emit socket event
│
└─ Check logs:
   └─ grep '[Watcher] Started watching'
   └─ grep '[Watcher] Initial scan'
   └─ grep '[Watcher] Emitted'

src/api/routes/tree_routes.py
├─ Line 125: qdrant.scroll()              [QDRANT ACCESS]
├─ Line 139: print(Found X files)         [DEBUG LOG]
├─ Line 156: os.path.exists(file_path)    [FILTER]
└─ Line 404: return response              [OUTPUT]
```

### Frontend Breakpoints

```
client/src/hooks/useSocket.ts
├─ Line 227: socket.on('browser_folder_added')  [EXISTING]
│ [SHOULD ADD NEW LISTENER AFTER THIS]
│
├─ Line 232: fetch('/api/tree/data')      [TREE RELOAD]
├─ Line 245: setNodesFromRecord()         [STORE UPDATE]
└─ Line 250: setCameraCommand()           [CAMERA TRIGGER]

client/src/components/canvas/CameraController.tsx
├─ Line 110: console.log(cameraCommand)   [INPUT]
├─ Line 113: findNode(target)             [SEARCH]
├─ Line 116: warn if not found            [ERROR]
└─ Line 185: useFrame() callback          [ANIMATION]

DevTools Console Check:
├─ [Socket] event names logged?
├─ [CameraController] messages visible?
└─ Camera position values printed?
```

---

**End of Flow Diagrams**

*Use alongside SCANNER_TECHNICAL_ANALYSIS.md for complete understanding*
