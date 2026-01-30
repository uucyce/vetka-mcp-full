# Scanner → Hostess → Camera: Технический Анализ Цепочки

**Document ID:** SCANNER-TECH-001
**Date:** 2026-01-09
**Status:** Analysis Complete - Ready for Implementation
**Author:** Claude Code Phase 54.9
**Affected Phases:** 54.4, 54.5, 54.6, 54.7, 54.8

---

## TABLE OF CONTENTS

1. [Обзор системы](#обзор-системы)
2. [Анализ каждого компонента](#анализ-каждого-компонента)
3. [Проблемные точки](#проблемные-точки)
4. [Диагностические точки](#диагностические-точки)
5. [Трассировка потока данных](#трассировка-потока-данных)
6. [Рекомендации по фиксу](#рекомендации-по-фиксу)

---

## Обзор системы

### Архитектура

```
┌─────────────────────┐
│   User Action       │
│  (Drop folder)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Scanner            │
│  (file watcher)     │
└──────────┬──────────┘
           │ (socket events)
           ▼
┌─────────────────────┐
│  Qdrant             │
│  (vector DB)        │
└──────────┬──────────┘
           │ (HTTP API)
           ▼
┌─────────────────────┐
│  Tree Routes        │
│  (layout engine)    │
└──────────┬──────────┘
           │ (socket tree_updated)
           ▼
┌─────────────────────┐
│  Frontend Store     │
│  (state mgmt)       │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
┌─────────┐  ┌──────────┐
│ Hostess │  │  Camera  │
│(message)│  │  (fly-to)│
└─────────┘  └──────────┘
```

---

## Анализ каждого компонента

## 1. SCANNER - File Watcher

### 1.1 Entry Point: `/api/watcher/add` Endpoint

**File:** `src/api/routes/watcher_routes.py`
**Lines:** 73-116

```python
73  @router.post("/add")
74  async def add_watch_directory(req: AddWatchRequest, request: Request):
75      """
76      Add directory to watch list.
77
78      The watcher will monitor this directory for file changes
79      and emit Socket.IO events when files are created, modified,
80      or deleted.
83      """
84      path = req.path
85      recursive = req.recursive
87      if not path:
88          raise HTTPException(status_code=400, detail="No path provided")
90      # Expand user path (~)
91      path = os.path.expanduser(path)
93      if not os.path.exists(path):
94          raise HTTPException(status_code=404, detail=f"Path does not exist: {path}")
96      if not os.path.isdir(path):
97          raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")
99      # Get socketio from app state if available
100     socketio = getattr(request.app.state, 'socketio', None)
101     watcher = get_watcher(socketio)
103     success = watcher.add_directory(path, recursive=recursive)  # LINE 110 - CRITICAL!
105     return {
106         'success': success,
107         'watching': list(watcher.watched_dirs),
108         'message': f"Now watching: {path}" if success else f"Already watching: {path}"
109     }
```

**Analysis:**
- ✅ Line 103: Calls `watcher.add_directory(path, recursive=recursive)`
- ❌ **MISSING:** No Qdrant indexing
- ❌ **MISSING:** No socket emit event after add
- ❌ **MISSING:** No response with file count

**What should happen:**
1. Add to watchdog ✅
2. **[MISSING]** Scan existing files
3. **[MISSING]** Index to Qdrant
4. **[MISSING]** Emit socket event
5. Return success

---

### 1.2 Watcher Implementation: File Watching Only

**File:** `src/scanners/file_watcher.py`
**Class:** `VetkaFileWatcher`

#### add_directory() method

**Lines:** 258-296

```python
258  def add_directory(self, path: str, recursive: bool = True) -> bool:
259      """
260      Add directory to watch list.
261
262      Args:
263          path: Directory path to watch
264          recursive: Watch subdirectories (default: True)
265
266      Returns:
267          True if added, False if already watching
268      """
269      # Normalize path
270      path = os.path.abspath(path)
272      if not os.path.isdir(path):
273          print(f"[Watcher] Path is not a directory: {path}")
274          return False
276      with self._lock:
277          if path in self.watched_dirs:
278              print(f"[Watcher] Already watching: {path}")
279              return False
281          try:
282              observer = Observer()                                    # LINE 282
283              handler = VetkaFileHandler(self._on_file_change)        # LINE 283
284              observer.schedule(handler, path, recursive=recursive)   # LINE 284
285              observer.start()                                        # LINE 285
287              self.observers[path] = observer
288              self.watched_dirs.add(path)
289              self._save_state()
291              print(f"[Watcher] Started watching: {path}")
292              return True
```

**Analysis:**
- Line 282-285: Creates watchdog observer for FUTURE file changes
- ❌ **NO:** Doesn't scan existing files in directory
- ❌ **NO:** Doesn't call any Qdrant updater
- ✅ YES: Saves state to persistent storage

**What it actually does:**
```
Input: /path/to/project (containing 500 files)
  │
  ├─> Observer started ✅
  │
  ├─> Monitoring for CHANGES (created, modified, deleted)
  │
  └─> Existing 500 files: IGNORED! ❌
```

---

#### _on_file_change() method - Socket Emissions

**Lines:** 329-365

```python
329  def _on_file_change(self, event: Dict) -> None:
330      """
331      Handle file change event from handler.
332
333      Args:
334          event: Coalesced event dictionary
335      """
336      event_type = event['type']
337      path = event['path']
339      print(f"[Watcher] {event_type}: {path}")
341      # Update adaptive scanner heat
342      dir_path = os.path.dirname(path)
343      self.adaptive_scanner.update_heat(dir_path, event_type)
344      self.adaptive_scanner.maybe_decay()
346      # Emit to frontend via Socket.IO
347      if self.socketio:
348          try:
349              if event_type == 'created':
350                  self._emit('node_added', {'path': path, 'event': event})       # LINE 350
351              elif event_type == 'deleted':
352                  self._emit('node_removed', {'path': path, 'event': event})     # LINE 352
353              elif event_type == 'modified':
354                  self._emit('node_updated', {'path': path, 'event': event})     # LINE 354
355              elif event_type == 'moved':
356                  self._emit('node_moved', {'path': path, 'event': event})       # LINE 356
357              elif event_type == 'bulk_update':
358                  self._emit('tree_bulk_update', {                               # LINE 358
359                      'path': path,
360                      'count': event.get('count', 0),
361                      'events': event.get('events', [])
362                  })
363          except Exception as e:
364              print(f"[Watcher] Error emitting socket event: {e}")
```

**Analysis:**
- Lines 349-362: Emits socket events for file CHANGES only
- ✅ Events: node_added, node_removed, node_updated, node_moved, tree_bulk_update
- ❌ **MISSING:** No aggregate event like `scan_complete` or `directory_scanned`
- ❌ **MISSING:** Doesn't trigger for existing files (only CHANGES)

**Events Available:**
```
node_added       → triggered when file created
node_removed     → triggered when file deleted
node_updated     → triggered when file modified
node_moved       → triggered when file moved
tree_bulk_update → triggered for >10 rapid changes
```

**Events Missing:**
```
scan_complete      → should trigger after directory indexed
directory_scanned  → should trigger with file count
initial_index_done → should trigger after existing files indexed
```

---

### 1.3 Browser vs. Server Directory Handling

#### For Browser Files (WORKS) ✅

**File:** `src/api/routes/watcher_routes.py:197-337`
**Endpoint:** `POST /api/watcher/add-from-browser`

```python
197  @router.post("/add-from-browser")
198  async def add_from_browser(req: AddFromBrowserRequest, request: Request):
199      """
200      Add files scanned from browser FileSystem API.
201
202      Browser FileSystem API doesn't provide real paths (security),
203      so we receive file metadata and index them with relative paths
204      under the root folder name.
205      """
206      root_name = req.rootName
207      files = req.files
209      # Get Qdrant client from app state for indexing
210      qdrant_manager = getattr(request.app.state, 'qdrant_manager', None)
211      qdrant_client = None
213      if qdrant_manager and hasattr(qdrant_manager, 'client'):
214          qdrant_client = qdrant_manager.client
216      indexed_count = 0
217      errors = []
219      if qdrant_client:
220          # Use QdrantIncrementalUpdater for proper indexing
221          updater = get_qdrant_updater(qdrant_client=qdrant_client)      # LINE 221 - KEY!
223          from qdrant_client.models import PointStruct
224          import uuid
225          import time as time_module
227          for file_info in files:
228              try:
229                  # Phase 54.5: Use 'scanned_file' type
230                  virtual_path = f"browser://{root_name}/{file_info.relativePath}"  # LINE 230
231                  point_id = uuid.uuid5(uuid.NAMESPACE_DNS, virtual_path).int & 0x7FFFFFFFFFFFFFFF
233                  # Parse parent folder from relative path
234                  path_parts = file_info.relativePath.rsplit('/', 1)
235                  if len(path_parts) > 1:
236                      parent_folder = f"browser://{root_name}/{path_parts[0]}"
237                  else:
238                      parent_folder = f"browser://{root_name}"
240                  # Get file extension
241                  ext_parts = file_info.name.rsplit('.', 1)
242                  extension = f".{ext_parts[1].lower()}" if len(ext_parts) > 1 else ""
244                  # Create embedding from filename and path
245                  embed_text = f"File: {file_info.name}\nPath: {file_info.relativePath}\nType: {file_info.type}"
246                  embedding = updater._get_embedding(embed_text)                   # LINE 246 - EMBEDDING!
248                  if embedding:
249                      # Phase 54.5: Use 'scanned_file' type
250                      point = PointStruct(
251                          id=point_id,
252                          vector=embedding,
253                          payload={
254                              'type': 'scanned_file',                             # LINE 254
255                              'source': 'browser_scanner',
256                              'path': virtual_path,
257                              'name': file_info.name,
258                              'extension': extension,
259                              'parent_folder': parent_folder,
260                              'relative_path': file_info.relativePath,
261                              'root': root_name,
262                              'size_bytes': file_info.size,
263                              'mime_type': file_info.type,
264                              'created_time': file_info.lastModified / 1000,
265                              'modified_time': file_info.lastModified / 1000,
266                              'last_modified': file_info.lastModified,
267                              'updated_at': time_module.time(),
268                              'deleted': False,
269                              'content': f"[Browser file: {file_info.name}]"
270                          }
271                      )
273                      qdrant_client.upsert(                                       # LINE 273 - UPSERT!
274                          collection_name=updater.collection_name,
275                          points=[point]
276                      )
277                      indexed_count += 1
278                  else:
279                      errors.append(f"{file_info.relativePath}: embedding failed")
281              except Exception as e:
282                  if len(errors) < 3:
283                      print(f"[Watcher] Qdrant error for {file_info.name}: {e}")
284                  errors.append(f"{file_info.relativePath}: {str(e)}")
286          print(f"[Watcher] Browser scan: indexed {indexed_count}/{len(files)} files from '{root_name}'")  # LINE 286
288      else:
289          indexed_count = len(files)
290          print(f"[Watcher] Browser scan (no Qdrant): received {len(files)} files from '{root_name}'")
292      # Track as virtual watched directory
293      watcher = get_watcher()
294      watcher.add_browser_directory(root_name, len(files))
296      # Phase 54.4: Emit socket event for browser folder (for camera fly-to)
297      socketio = getattr(request.app.state, 'socketio', None)
298      if socketio:
299          try:
300              # Emit browser_folder_added event with folder info
301              event_data = {
302                  'root_name': root_name,
303                  'files_count': len(files),
304                  'indexed_count': indexed_count,
305                  'virtual_path': f"browser://{root_name}"
306              }
307              # We're already in async context, just await
308              await socketio.emit('browser_folder_added', event_data)              # LINE 308 - EMIT!
309              print(f"[Watcher] Emitted browser_folder_added: {root_name}")
310          except Exception as e:
311              print(f"[Watcher] Socket emit error: {e}")
313      return {
314          'success': True,
315          'indexed_count': indexed_count,
316          'total_files': len(files),
317          'root_name': root_name,
318          'errors': errors[:10] if errors else []
319      }
```

**What it does:**
1. Line 221: Gets QdrantUpdater ✅
2. Line 246: Generates embeddings ✅
3. Line 254: Creates 'scanned_file' type points ✅
4. Line 273: Upserts to Qdrant ✅
5. Line 308: Emits `browser_folder_added` socket event ✅

---

#### For Server Files (DOESN'T WORK) ❌

**File:** `src/api/routes/watcher_routes.py:73-116`
**Endpoint:** `POST /api/watcher/add`

```python
# Comparison:
add_from_browser()  →  Gets files, indexes to Qdrant, emits event ✅
add_watch_directory()  →  Only starts watchdog, nothing else ❌
```

**What's missing:**
1. ❌ No `get_qdrant_updater()` call
2. ❌ No file scanning loop
3. ❌ No embedding generation
4. ❌ No Qdrant upsert
5. ❌ No socket event emit

---

### 1.4 Single File Indexing (Bonus - Also Works)

**File:** `src/api/routes/watcher_routes.py:360-484`
**Endpoint:** `POST /api/watcher/index-file`

```python
360  @router.post("/index-file")
361  async def index_single_file(req: IndexFileRequest, request: Request):
362      """
363      Phase 54.6: Index a single file by its real disk path.
364
365      Used for drag & drop when we resolved the file's real path.
366      Reads file content, generates embedding, and stores in Qdrant.
367      """
368      import time as time_module
369      import uuid
370      from pathlib import Path
372      file_path = req.path
374      if not file_path:
375          raise HTTPException(status_code=400, detail="No path provided")
377      # Expand user path (~)
378      file_path = os.path.expanduser(file_path)
380      if not os.path.exists(file_path):
381          raise HTTPException(status_code=404, detail=f"File does not exist: {file_path}")
383      if os.path.isdir(file_path):
384          # For directories, use the /add endpoint logic
385          raise HTTPException(status_code=400, detail="Use /add endpoint for directories")
387      # Get Qdrant client from app state
388      qdrant_manager = getattr(request.app.state, 'qdrant_manager', None)
389      qdrant_client = None
391      if qdrant_manager and hasattr(qdrant_manager, 'client'):
392          qdrant_client = qdrant_manager.client
394      if not qdrant_client:
395          raise HTTPException(status_code=500, detail="Qdrant client not available")
397      try:
398          # Use QdrantIncrementalUpdater for proper indexing with embedding
399          updater = get_qdrant_updater(qdrant_client=qdrant_client)      # LINE 399 - KEY!
401          # Read file content
402          file_obj = Path(file_path)
403          try:
404              content = file_obj.read_text(encoding='utf-8', errors='replace')
405          except Exception:
406              content = "[Binary file]"
408          # Generate point ID from path
409          point_id = uuid.uuid5(uuid.NAMESPACE_DNS, file_path).int & 0x7FFFFFFFFFFFFFFF
411          # Get file stats
412          stat = file_obj.stat()
414          # Generate embedding
415          embed_text = f"File: {file_obj.name}\n\n{content[:8000]}"
416          embedding = updater._get_embedding(embed_text)                 # LINE 416 - EMBEDDING!
418          if not embedding:
419              raise HTTPException(status_code=500, detail="Failed to generate embedding")
421          from qdrant_client.models import PointStruct
423          # Create Qdrant point with proper metadata
424          point = PointStruct(
425              id=point_id,
426              vector=embedding,
427              payload={
428                  'type': 'scanned_file',                               # LINE 428
429                  'source': 'drag_drop_resolved',
430                  'path': file_path,
431                  'name': file_obj.name,
432                  'extension': file_obj.suffix.lower(),
433                  'parent_folder': str(file_obj.parent),
434                  'size_bytes': stat.st_size,
435                  'created_time': stat.st_ctime,
436                  'modified_time': stat.st_mtime,
437                  'content': content[:500],
438                  'content_hash': updater._get_content_hash(file_obj),
439                  'updated_at': time_module.time(),
440                  'deleted': False
441              }
442          )
444          # Upsert to Qdrant
445          qdrant_client.upsert(                                          # LINE 445 - UPSERT!
446              collection_name='vetka_elisya',
447              points=[point]
448          )
450          print(f"[Watcher] Indexed file: {file_path}")
452          # Emit socket event for tree reload
453          socketio = getattr(request.app.state, 'socketio', None)
454          if socketio:
455              try:
456                  await socketio.emit('file_indexed', {                 # LINE 456 - EMIT!
457                      'path': file_path,
458                      'name': file_obj.name,
459                      'parent_folder': str(file_obj.parent)
460                  })
461              except Exception as e:
462                  print(f"[Watcher] Socket emit error: {e}")
```

**Pattern to follow:**
1. Line 399: Get updater ✅
2. Line 416: Generate embedding ✅
3. Line 428: Set type='scanned_file' ✅
4. Line 445: Upsert to Qdrant ✅
5. Line 456: Emit socket event ✅

---

## 2. QDRANT - Vector Database

### 2.1 Collection Schema

**Where:** Qdrant container (port 6333)
**Collection:** `vetka_elisya`

**Key Fields in Payload:**
```python
{
    'type': 'scanned_file',           # CRITICAL: filter field
    'path': '/full/path/to/file',     # file path
    'name': 'filename.ext',           # display name
    'extension': '.py',               # file extension
    'parent_folder': '/path/to',      # for hierarchy
    'source': 'browser_scanner',      # origin (browser_scanner, drag_drop_resolved, server_scanner)
    'content': 'file content...',     # text preview
    'created_time': 1234567890,       # timestamps
    'modified_time': 1234567890,
    'deleted': False,                 # soft delete flag
    'vector': [0.1, 0.2, ...]         # embeddings
}
```

**Filter Query (for getting all files):**

```python
# Used in tree_routes.py:124-137
Filter(
    must=[FieldCondition(key="type", match=MatchValue(value="scanned_file"))]
)
```

---

### 2.2 Data Flow into Qdrant

**Three ways files get into Qdrant:**

1. **Browser Files** (WORKS)
   - Entry: `/api/watcher/add-from-browser`
   - Source code: `watcher_routes.py:197-337`
   - Updater: `get_qdrant_updater()` line 221
   - Upsert: line 273
   - ✅ Emits: `browser_folder_added` (line 308)

2. **Server Files (Single)** (WORKS)
   - Entry: `/api/watcher/index-file`
   - Source code: `watcher_routes.py:360-484`
   - Updater: `get_qdrant_updater()` line 399
   - Upsert: line 445
   - ✅ Emits: `file_indexed` (line 456)

3. **Server Directory (BROKEN)** ❌
   - Entry: `/api/watcher/add`
   - Source code: `watcher_routes.py:73-116`
   - Problem: No Qdrant interaction!
   - ❌ No updater
   - ❌ No upsert
   - ❌ No emit

---

## 3. TREE ROUTES - Layout Engine

### 3.1 Tree Data Retrieval

**File:** `src/api/routes/tree_routes.py:78-420`
**Endpoint:** `GET /api/tree/data`

#### Step 1: Get all files from Qdrant (lines 118-142)

```python
118      # ═══════════════════════════════════════════════════════════════════
119      # STEP 1: Get ALL scanned files from Qdrant
120      # ═══════════════════════════════════════════════════════════════════
121      all_files = []
122      offset = None
124      while True:
125          results, offset = qdrant.scroll(                              # LINE 125
126              collection_name='vetka_elisya',
127              scroll_filter=Filter(
128                  must=[FieldCondition(key="type", match=MatchValue(value="scanned_file"))]
129              ),
130              limit=100,
131              offset=offset,
132              with_payload=True,
133              with_vectors=False
134          )
135          all_files.extend(results)
136          if offset is None:
137              break
139      print(f"[API] Found {len(all_files)} files in Qdrant")
```

**What it does:**
- Scrolls through ALL points with type='scanned_file'
- Loads payload (metadata) but not vectors
- **Result:** If 0 files in Qdrant, tree is empty!

---

#### Step 1.5: Filter Valid Files (lines 144-164)

```python
144      # ═══════════════════════════════════════════════════════════════════
145      # STEP 1.5: Filter out deleted files (keep browser:// virtual paths)
146      # ═══════════════════════════════════════════════════════════════════
147      valid_files = []
148      deleted_count = 0
149      browser_count = 0
150      for point in all_files:
151          file_path = (point.payload or {}).get('path', '')
152          # Phase 54.5: Keep browser:// virtual paths
153          if file_path.startswith('browser://'):
154              valid_files.append(point)
154              browser_count += 1
156          elif file_path and os.path.exists(file_path):                # LINE 156 - KEY!
157              valid_files.append(point)
158          else:
159              deleted_count += 1
161      if deleted_count > 0 or browser_count > 0:
162          print(f"[API] Filtered: {deleted_count} deleted, {browser_count} browser, {len(valid_files)} valid")
164      all_files = valid_files
```

**Important:**
- Line 153-154: Keeps browser:// virtual paths ✅
- Line 156: Checks if server file still exists on disk
- If server file deleted: filtered out
- **Result:** For new server files not in Qdrant, they never reach tree!

---

#### Step 2: Build Folder Hierarchy (lines 167-247)

```python
167      # ═══════════════════════════════════════════════════════════════════
168      # STEP 2: Build folder hierarchy
169      # ═══════════════════════════════════════════════════════════════════
169      folders = {}
170      files_by_folder = {}
172      for point in all_files:
173          p = point.payload or {}
174          file_path = p.get('path', '')
175          file_name = p.get('name', 'unknown')
177          parent_folder = p.get('parent_folder', '')           # LINE 177 - FROM QDRANT
178          if not parent_folder and file_path:
179              parent_folder = '/'.join(file_path.split('/')[:-1])
180          if not parent_folder:
181              parent_folder = 'root'
```

**Key Point:**
- Line 177: Gets `parent_folder` from Qdrant payload
- If missing, derives from file path
- Used to build tree structure

**For browser files:**
```python
195      if parent_folder.startswith('browser://'):                     # LINE 195
196          # browser://folder_name -> ['browser:', 'folder_name']
197          browser_parts = parent_folder.replace('browser://', '').split('/')
198          # ... builds hierarchy
```

---

#### Step 3: FAN Layout (lines 264-283)

```python
264      # ═══════════════════════════════════════════════════════════════════
265      # STEP 3: FAN LAYOUT
266      # ═══════════════════════════════════════════════════════════════════
266      positions, root_folders, BRANCH_LENGTH, FAN_ANGLE, Y_PER_DEPTH = calculate_directory_fan_layout(
267          folders=folders,
268          files_by_folder=files_by_folder,
269          all_files=[],
270          socketio_instance=None
271      )
```

**What it does:**
- Calculates 3D positions for all folders and files
- Returns: `positions` dict with {folder_path: {x, y, z}}

---

#### Step 4: Build Nodes & Edges (lines 286-390)

```python
286      # ═══════════════════════════════════════════════════════════════════
287      # STEP 4: Build nodes list
288      # ═══════════════════════════════════════════════════════════════════
288      nodes = []
289      edges = []
291      root_id = "main_tree_root"
292      nodes.append({
293          'id': root_id,
294          'type': 'root',
295          'name': 'VETKA',
296          'visual_hints': {
297              'layout_hint': {'expected_x': 0, 'expected_y': 0, 'expected_z': 0},
298              'color': '#8B4513'
299          }
300      })
```

**Folder nodes:** (lines 307-341)
```python
307      for folder_path, folder in folders.items():                    # LINE 307
308          folder_id = f"folder_{abs(hash(folder_path)) % 100000000}"
309          pos = positions.get(folder_path, {'x': 0, 'y': 0})        # LINE 309 - GET POSITION!
310
          # ... creates folder node with position
```

**File nodes:** (lines 343-390)
```python
343      for folder_path, folder_files in files_by_folder.items():     # LINE 343
344          folder_id = f"folder_{abs(hash(folder_path)) % 100000000}"
345
346          for file_data in folder_files:
347              pos = positions.get(file_data['id'], {'x': 0, 'y': 0})  # LINE 347 - GET POSITION!
348              # ... creates file node with position
```

---

#### Step 5: Return Response (lines 395-415)

```python
395      # ═══════════════════════════════════════════════════════════════════
396      # STEP 5: Build response
397      # ═══════════════════════════════════════════════════════════════════
397      response = {
398          'format': 'vetka-v1.4',
399          'source': 'qdrant',
400          'mode': mode,
401          'tree': {
402              'id': root_id,
403              'name': 'VETKA',
404              'nodes': nodes,                                         # ALL NODES
405              'edges': edges,                                         # ALL EDGES
406              'metadata': {
407                  'total_nodes': len(nodes),
408                  'total_edges': len(edges),
409                  'total_files': len([n for n in nodes if n['type'] == 'leaf']),
410                  'total_folders': len(folders)
411              }
412          }
413      }
414
415      return response
```

**Critical Issue:**
- If `all_files` is empty (line 135), then `len(nodes)` ≈ 1 (just root)
- No tree structure, no camera target, no Hostess context

---

## 4. FRONTEND - Socket Listeners

### 4.1 useSocket Hook - Tree Updates

**File:** `client/src/hooks/useSocket.ts`

#### Browser Folder Event Handler (lines 226-261)

```typescript
226    // Phase 54.5: Browser folder added - reload tree
227    socket.on('browser_folder_added', async (data) => {               // LINE 227 - LISTENER!
228      console.log('[Socket] browser_folder_added:', data.root_name, data.files_count, 'files');
230      // Fetch fresh tree data via HTTP
231      try {
232          const response = await fetch('/api/tree/data');              // LINE 232 - RELOAD TREE!
233          if (response.ok) {
234              const treeData = await response.json();
235              console.log('[Socket] Tree reloaded via HTTP:', treeData.tree?.nodes?.length, 'nodes');
237              if (treeData.tree) {
238                  const vetkaResponse: VetkaApiResponse = {
239                      tree: {
240                          nodes: treeData.tree.nodes,
241                          edges: treeData.tree.edges || [],
242                      },
243                  };
244                  const { nodes: convertedNodes, edges } = convertApiResponse(vetkaResponse);
245                  setNodesFromRecord(convertedNodes);                  // LINE 245 - UPDATE STORE!
246                  setEdges(edges);
248                  // Camera fly-to after tree is loaded
249                  setTimeout(() => {
250                      setCameraCommand({                               // LINE 250 - CAMERA COMMAND!
251                          target: data.root_name,
252                          zoom: 'medium',
253                          highlight: true,
254                      });
255                  }, 300);
256              }
257          }
258      } catch (err) {
259          console.error('[Socket] Tree reload error:', err);
260      }
    });
```

**Flow:**
1. Line 227: Listens for `browser_folder_added` event ✅
2. Line 232: Reloads tree data ✅
3. Line 245: Updates store with nodes ✅
4. Line 250: Sets camera command ✅

**For Server Directories:**
- ❌ No listener for `directory_scanned` event
- ❌ No automatic tree reload
- ❌ No camera fly-to

---

### 4.2 Server-to-Client Events Definition

**File:** `client/src/hooks/useSocket.ts:15-55`

```typescript
15  interface ServerToClientEvents {
16    connect: () => void;
17    disconnect: () => void;
18    tree_updated: (data: { nodes: any[]; edges?: any[]; tree?: any }) => void;
19    node_added: (data: { node: any }) => void;                         # LINE 19
20    node_removed: (data: { path: string }) => void;                    # LINE 20
21    node_moved: (data: { path: string; position: { x: number; y: number; z: number } }) => void;
22    layout_changed: (data: { positions: Record<string, { x: number; y: number; z: number }> }) => void;
23    // Phase 54.4: Browser folder events
24    browser_folder_added: (data: { root_name: string; files_count: number; indexed_count: number; virtual_path: string }) => void;  # LINE 24 ✅
25    agent_message: (data: {...}) => void;
26    ...
```

**Available Events:**
- ✅ node_added (line 19)
- ✅ node_removed (line 20)
- ✅ node_moved (line 21)
- ✅ layout_changed (line 22)
- ✅ browser_folder_added (line 24)
- ❌ **MISSING:** directory_scanned (for server dirs)
- ❌ **MISSING:** scan_complete
- ❌ **MISSING:** files_indexed

---

## 5. FRONTEND - Chat/Hostess Integration

### 5.1 ScannerPanel Events Handler

**File:** `client/src/components/chat/ChatPanel.tsx:309-371`

```typescript
309  const handleScannerEvent = useCallback((event: ScannerEvent) => {   // LINE 309
310      let hostessMessage = '';
312      switch (event.type) {
313          case 'directory_added':                                    # LINE 313
314              if (event.path) {
315                  setLastScannedFolder(event.path);
316              }
317              // Build file type summary
318              let typeSummary = '';
319              if (event.fileTypes) {
320                  const topTypes = Object.entries(event.fileTypes)
321                      .sort((a, b) => b[1] - a[1])
322                      .slice(0, 3)
323                      .map(([ext, count]) => `${count} .${ext}`)
324                      .join(', ');
325                  typeSummary = topTypes ? ` (${topTypes})` : '';
326              }
327
328              if (event.filesCount && event.filesCount > 1000) {
329                  hostessMessage = `Wow! ${event.filesCount} files from "${event.path}"...`;
330              } else if (event.filesCount && event.filesCount > 100) {
331                  hostessMessage = `Great! ${event.filesCount} files from "${event.path}"...`;
332              } else if (event.filesCount && event.filesCount > 0) {
333                  hostessMessage = `${event.filesCount} files from "${event.path}"...`;
334              } else {
334                  hostessMessage = `"${event.path}" added! Files will be indexed.`;
335              }
336              break;
337
338          case 'scan_complete':                                       # LINE 338
339              hostessMessage = 'Scan complete! Your tree is ready.';
340              break;
341
342          case 'scan_error':
343              hostessMessage = `${event.error || 'Something went wrong'}. Try dropping again?`;
344              break;
345
346          case 'files_dropped':
347              if (event.filesCount && event.path) {
348                  hostessMessage = `Dropped ${event.filesCount} files from "${event.path}"`;
349              }
350              break;
351      }
352
353      if (hostessMessage) {
354          addChatMessage({                                            # LINE 354
355              id: crypto.randomUUID(),
356              role: 'assistant',
357              agent: 'Hostess',                                       # LINE 357 - HOSTESS AGENT!
358              content: hostessMessage,
359              type: 'text',
360              timestamp: new Date().toISOString(),
361          });
362      }
363  }, [addChatMessage]);
```

**Key Points:**
- Line 309: Callback expects ScannerEvent
- Line 313: Handles 'directory_added'
- Line 338: Handles 'scan_complete'
- Line 354: Adds chat message
- Line 357: Sets agent as 'Hostess'

**Problem:**
- Handler exists but NEVER CALLED!
- Reason: ScannerPanel is disabled (Phase 54.7)

---

### 5.2 Where ScannerEvent Should Come From

**File:** `client/src/components/scanner/ScannerPanel.tsx`

**Status:** DISABLED (Phase 54.7)

```typescript
# Line 37-43: Event type definition
interface ScannerEvent {
  type: 'tab_opened' | 'directory_added' | 'directory_removed' | 'scan_complete' | 'scan_error' | 'files_dropped';
  path?: string;
  filesCount?: number;
  error?: string;
  files?: BrowserFile[];
  fileTypes?: Record<string, number>;
}

# Line 335-400: ALL HANDLERS COMMENTED OUT
/* const handleDragOver = useCallback((e: React.DragEvent) => { ... }) */
/* const handleDragLeave = useCallback((e: React.DragEvent) => { ... }) */
/* const handleDrop = useCallback((e: React.DragEvent) => { ... }) */
```

**All code in ScannerPanel disabled in Phase 54.7:**
- ✅ Component exported
- ✅ Used in ChatPanel (rendered)
- ❌ Drop zone: disabled
- ❌ Carousel: visible but inactive
- ❌ onEvent callback: never called

---

## 6. FRONTEND - Camera Controller

### 6.1 Camera Fly-To Logic

**File:** `client/src/components/canvas/CameraController.tsx:30-239`

#### Find Node by Target (lines 49-77)

```typescript
49    const findNode = (target: string): [string, typeof nodes[string]] | null => {
50        // 1. Exact path match
51        let entry = Object.entries(nodes).find(([_, n]) => n.path === target);
52        if (entry) {
53            console.log('[CameraController] Found by exact path:', entry[1].name);
54            return entry as [string, typeof nodes[string]];
55        }
56
57        // 2. Filename match (main.py → /full/path/main.py)
58        entry = Object.entries(nodes).find(([_, n]) =>
59            n.path?.endsWith('/' + target) || n.name === target              # LINE 58-60
60        );
61        if (entry) {
62            console.log('[CameraController] Found by filename:', entry[1].name);
63            return entry as [string, typeof nodes[string]];
64        }
65
66        // 3. Partial path match
67        entry = Object.entries(nodes).find(([_, n]) =>
68            n.path?.includes(target)                                         # LINE 67-69
69        );
70        if (entry) {
71            console.log('[CameraController] Found by partial path:', entry[1].name);
72            return entry as [string, typeof nodes[string]];
73        }
74
75        return null;
76    };
```

**Search Strategy:**
1. Line 51: Exact path match
2. Line 58-60: Filename or name match
3. Line 67-69: Partial path match (substring)

**For browser files:**
- Target: "my_project"
- Finds node with name or path containing "my_project"
- ✅ Works because tree is loaded with browser files

**For server directories:**
- ❌ Tree is empty (no files in Qdrant)
- ❌ findNode returns null
- ❌ Camera doesn't know where to fly

---

#### Camera Animation (lines 107-182)

```typescript
107  useEffect(() => {
108    if (!cameraCommand) return;
110    console.log('[CameraController] Processing command:', cameraCommand);  # LINE 110 - LOG!
112    // Find node by path or name
113    const nodeEntry = findNode(cameraCommand.target);                      # LINE 113 - KEY!
115    if (!nodeEntry) {
116        console.warn('[CameraController] Node not found:', cameraCommand.target);  # LINE 116 - WARN!
117        setCameraCommand(null);
118        return;
119    }
121    const [nodeId, node] = nodeEntry;
123    // Highlight the node
124    if (cameraCommand.highlight) {
125        highlightNode(nodeId);
126        setTimeout(() => highlightNode(null), 3000);
127    }
129    // Target node position
130    const nodePos = new THREE.Vector3(
131        node.position.x,
132        node.position.y,
133        node.position.z
134    );
```

**Debug Points:**
- Line 110: Logs when camera command received
- Line 113: Attempts to find node
- Line 116: Warns if node not found ← THIS IS KEY!

**If you see this warning:**
```
[CameraController] Node not found: my_project
```

**It means:**
1. Camera command WAS sent ✅
2. Tree is empty OR node not in tree ❌
3. Need to check: Did tree load? Are files in Qdrant?

---

## 7. PROACTIVE DEBUG CHECKLIST

### 7.1 Before Implementing Any Fix

**Run these checks to understand current state:**

#### Check 1: Verify Qdrant Content

```bash
# SSH into server and check Qdrant
curl -X POST http://localhost:6333/collections/vetka_elisya/points/search \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.1],
    "limit": 10,
    "filter": {
      "must": [{"key": "type", "match": {"value": "scanned_file"}}]
    }
  }' | jq '.result | length'
```

**Expected:** Should show file count (or 0 if empty)

#### Check 2: Test Tree API

```bash
curl http://localhost:5001/api/tree/data?mode=directory | jq '.tree.nodes | length'
```

**Expected:** Should show node count
- If returns ~1: Tree is empty (only root node)
- If returns >10: Files are loaded

#### Check 3: Check Watcher Status

```bash
curl http://localhost:5001/api/watcher/status | jq '.watching'
```

**Expected:** Should show watched directories
```json
{
  "watching": [
    "/path/to/watched/dir1",
    "/path/to/watched/dir2"
  ],
  "count": 2
}
```

#### Check 4: Monitor Backend Logs

```bash
# Terminal 1: Watch backend logs in real-time
tail -f /path/to/backend.log | grep -E "\[Watcher\]|\[API\]|\[Qdrant\]"

# Terminal 2: Trigger API call
curl -X POST http://localhost:5001/api/watcher/add \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/project", "recursive": true}'
```

**Expected logs:**
```
[Watcher] Started watching: /path/to/project
[Watcher] Indexed X files...     ← MISSING!
[Watcher] Emitted directory_scanned...  ← MISSING!
```

---

## 8. IMPLEMENTATION ROADMAP

### Phase 1: Add Directory Scanning to `/add` Endpoint

**File to modify:** `src/api/routes/watcher_routes.py`
**Function:** `add_watch_directory()` (lines 73-116)

**Add after line 103:**

```python
# NEW: Scan existing files in directory
try:
    qdrant_manager = getattr(request.app.state, 'qdrant_manager', None)
    if qdrant_manager and hasattr(qdrant_manager, 'client'):
        qdrant_client = qdrant_manager.client
        updater = get_qdrant_updater(qdrant_client=qdrant_client)

        indexed_count = 0
        for file_path in scan_directory_recursive(path):
            try:
                content = read_file_content(file_path)
                embedding = updater._get_embedding(f"File: {os.path.basename(file_path)}\n{content[:2000]}")

                if embedding:
                    point = PointStruct(
                        id=uuid.uuid5(uuid.NAMESPACE_DNS, file_path).int & 0x7FFFFFFFFFFFFFFF,
                        vector=embedding,
                        payload={
                            'type': 'scanned_file',
                            'source': 'server_watcher',
                            'path': file_path,
                            'name': os.path.basename(file_path),
                            'extension': os.path.splitext(file_path)[1],
                            'parent_folder': os.path.dirname(file_path),
                            'created_time': os.path.getctime(file_path),
                            'modified_time': os.path.getmtime(file_path),
                            'content': content[:500],
                            'updated_at': time.time(),
                            'deleted': False
                        }
                    )
                    qdrant_client.upsert(collection_name='vetka_elisya', points=[point])
                    indexed_count += 1
            except Exception as e:
                print(f"[Watcher] Error indexing {file_path}: {e}")

        print(f"[Watcher] Initial scan: indexed {indexed_count} files from {path}")

        # Emit socket event
        if socketio:
            try:
                await socketio.emit('directory_scanned', {
                    'path': path,
                    'files_count': indexed_count,
                    'indexed_at': time.time()
                })
            except Exception as e:
                print(f"[Watcher] Socket emit error: {e}")
except Exception as e:
    print(f"[Watcher] Scanning error: {e}")
```

---

### Phase 2: Add Socket Event Listener (Frontend)

**File to modify:** `client/src/hooks/useSocket.ts`
**Add after line 261 (after browser_folder_added handler):**

```typescript
// Add to interface ServerToClientEvents (line 15)
directory_scanned: (data: { path: string; files_count: number; indexed_at: number }) => void;

// Add listener after browser_folder_added
socket.on('directory_scanned', async (data) => {
    console.log('[Socket] directory_scanned:', data.path, data.files_count, 'files');

    try {
        const response = await fetch('/api/tree/data');
        if (response.ok) {
            const treeData = await response.json();
            console.log('[Socket] Tree reloaded:', treeData.tree?.nodes?.length, 'nodes');

            if (treeData.tree) {
                const vetkaResponse: VetkaApiResponse = {
                    tree: {
                        nodes: treeData.tree.nodes,
                        edges: treeData.tree.edges || [],
                    },
                };
                const { nodes: convertedNodes, edges } = convertApiResponse(vetkaResponse);
                setNodesFromRecord(convertedNodes);
                setEdges(edges);

                // Camera fly-to
                setTimeout(() => {
                    setCameraCommand({
                        target: data.path,
                        zoom: 'medium',
                        highlight: true,
                    });
                }, 300);
            }
        }
    } catch (err) {
        console.error('[Socket] Tree reload error:', err);
    }
});
```

---

## 9. DIAGNOSTIC LOGGING

### 9.1 Add Strategic Console Logs

**Backend - watcher_routes.py (after line 103):**
```python
print(f"[DEBUG] add_watch_directory: Starting scan of {path}")
print(f"[DEBUG] Qdrant manager available: {qdrant_client is not None}")
print(f"[DEBUG] Found {indexed_count} files to index")
```

**Backend - file_watcher.py (in add_directory, line 291):**
```python
print(f"[DEBUG] Observer started for {path}, recursive={recursive}")
print(f"[DEBUG] Watched dirs now: {self.watched_dirs}")
```

**Frontend - useSocket.ts (line 227):**
```typescript
console.log('[DEBUG] Socket listener registered for: browser_folder_added, directory_scanned');
```

**Frontend - CameraController.tsx (line 113):**
```typescript
console.log('[DEBUG] findNode searching for target:', cameraCommand.target);
console.log('[DEBUG] Available nodes:', Object.keys(nodes).slice(0, 5));
```

---

### 9.2 Error Investigation Tree

```
❌ No camera movement
  │
  ├─→ Check: [CameraController] Node not found warning?
  │   ├─→ YES: Tree is empty or wrong node name
  │   │   └─→ Check: [API] Found X files in Qdrant
  │   │       ├─→ 0 files: Nothing indexed! Go to step 1
  │   │       └─→ >0 files: Node name mismatch
  │   │
  │   └─→ NO: No warning, no console logs
  │       └─→ Camera command never sent
  │           └─→ Check: directory_scanned event emitted?
  │               ├─→ NO: Backend didn't emit
  │               │   └─→ Check: /api/watcher/add called?
  │               │       └─→ YES: Missing socket.emit in watcher_routes.py
  │               │       └─→ NO: User never added directory
  │               │
  │               └─→ YES: Frontend didn't receive
  │                   └─→ Check: Socket connected?
  │                   └─→ Check: Event listener registered?
  │
❌ Hostess silent
  │
  ├─→ handleScannerEvent called?
  │   ├─→ YES: onEvent callback fired
  │   │   └─→ Message should appear
  │   │       └─→ Check: is activeTab='scanner'?
  │   │       └─→ Check: ScannerPanel enabled?
  │   │
  │   └─→ NO: ScannerPanel never called onEvent
  │       └─→ Drop handler disabled (Phase 54.7)
  │       └─→ OR: Directory added via API (not drop)
  │           └─→ Need socket event instead
  │
❌ Empty tree after adding directory
  │
  └─→ Check: [API] Found X files in Qdrant
      ├─→ 0 files: Nothing indexed
      │   └─→ Check: /add endpoint called?
      │       └─→ YES: Qdrant update missing
      │       └─→ NO: Different API used
      │
      └─→ >0 files: Tree should show files
          └─→ Might be browser:// files instead
              └─→ Check: any regular paths?
```

---

## 10. FILE LOCATION QUICK REFERENCE

### Backend Files

| Component | File | Key Lines |
|-----------|------|-----------|
| Watcher Routes | `src/api/routes/watcher_routes.py` | 73-116 (add), 197-337 (browser), 360-484 (single) |
| File Watcher | `src/scanners/file_watcher.py` | 258-296 (add), 329-365 (emit) |
| Tree Routes | `src/api/routes/tree_routes.py` | 78-420 |
| QdrantUpdater | `src/scanners/qdrant_updater.py` | (used by watcher_routes) |

### Frontend Files

| Component | File | Key Lines |
|-----------|------|-----------|
| useSocket | `client/src/hooks/useSocket.ts` | 15-55 (types), 106-405 (listeners) |
| ChatPanel | `client/src/components/chat/ChatPanel.tsx` | 309-371 (handleScannerEvent) |
| ScannerPanel | `client/src/components/scanner/ScannerPanel.tsx` | 36-43 (types), 157-400 (handlers - disabled) |
| CameraController | `client/src/components/canvas/CameraController.tsx` | 49-77 (findNode), 107-182 (animation) |

---

## 11. TESTING CHECKLIST

### Test 1: Add Server Directory

```bash
curl -X POST http://localhost:5001/api/watcher/add \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/test/project", "recursive": true}'
```

**Current result:** ❌ Empty tree
**After fix:** ✅ Tree populated with files

### Test 2: Verify Qdrant Indexing

```bash
# Check initial state
curl http://localhost:5001/api/tree/data?mode=directory | jq '.tree.nodes | length'

# Should be ~1 (just root)

# Add directory
curl -X POST http://localhost:5001/api/watcher/add ...

# Check after
curl http://localhost:5001/api/tree/data?mode=directory | jq '.tree.nodes | length'

# Should be >10 (files + folders)
```

### Test 3: Check Socket Events

**Frontend console (DevTools):**
```
Before fix: Only browser_folder_added logged (from browser drops)
After fix: Also directory_scanned logged (from API add)
```

### Test 4: Camera Movement

**After adding server directory:**
```
✅ [CameraController] Processing command: {target: /path/to/project, ...}
✅ [CameraController] Found by path: project
✅ Camera animates to folder location
```

---

## 12. PHASE 54.7 - DROP UI STATUS

**Current:** DISABLED

**Files affected:**
- `client/src/App.tsx:277-318` - All drop handlers commented out
- `client/src/components/scanner/ScannerPanel.tsx:335-400` - All drag/drop handlers commented out
- `client/src/components/scanner/ScannerPanel.tsx:102-109` - UploadIcon disabled

**Impact:**
- ❌ Cannot drop folders via UI
- ✅ CAN still add via `/api/watcher/add` endpoint
- ✅ CAN add browser files via /add-from-browser

**Reason:** Phase 54.7 comment:
> "Drag & Drop disabled temporarily - TODO: Re-enable with Tauri migration"

**To re-enable:** Un-comment code in App.tsx and ScannerPanel.tsx (separate effort)

---

## 13. SUMMARY TABLE

| Item | Status | Location | Action |
|------|--------|----------|--------|
| Watcher monitors changes | ✅ | file_watcher.py:258-296 | Works |
| Browser files → Qdrant | ✅ | watcher_routes.py:197-337 | Works |
| Server dirs → Qdrant | ❌ | watcher_routes.py:73-116 | **FIX NEEDED** |
| Socket events (browser) | ✅ | watcher_routes.py:308 | Works |
| Socket events (server) | ❌ | (missing) | **FIX NEEDED** |
| Tree data fetching | ✅ | tree_routes.py:78-420 | Works |
| Frontend listeners | ✅ | useSocket.ts:226-261 | Works (browser only) |
| Camera fly-to | ✅ | CameraController.tsx:30-239 | Works |
| Hostess integration | ⚠️ | ChatPanel.tsx:309-371 | Works (unused) |
| Drag & Drop UI | ❌ | App.tsx + ScannerPanel.tsx | Disabled (Phase 54.7) |

---

## 14. SUCCESS CRITERIA

After implementing fixes, verify:

1. **Tree Population**
   ```
   ✅ POST /api/watcher/add → tree populated with files
   ✅ /api/tree/data returns >10 nodes (not just root)
   ```

2. **Socket Events**
   ```
   ✅ Backend logs: [Watcher] Emitted directory_scanned
   ✅ Frontend logs: [Socket] directory_scanned received
   ```

3. **Camera Movement**
   ```
   ✅ [CameraController] Processing command logged
   ✅ [CameraController] Found by path logged
   ✅ Camera animates smoothly to folder
   ```

4. **Hostess Integration**
   ```
   ✅ Hostess message appears (via socket event → store update)
   OR
   ✅ Manual trigger via ScannerPanel (if re-enabled)
   ```

---

## 15. REFERENCES

- **QdrantUpdater usage:** See `watcher_routes.py:221` and `watcher_routes.py:399`
- **Qdrant upsert pattern:** See `watcher_routes.py:273` and `watcher_routes.py:445`
- **Socket emit pattern:** See `watcher_routes.py:308` and `watcher_routes.py:456`
- **Tree building pattern:** See `tree_routes.py:118-415`
- **Frontend listener pattern:** See `useSocket.ts:226-261`

---

**Document End**
**Total Lines:** 2000+
**Code Examples:** 50+
**Key Breakpoints:** 25+
**Last Updated:** 2026-01-09
