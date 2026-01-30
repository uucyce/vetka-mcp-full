# Scanner Chain - Quick Debug Guide

**Quick Reference for Phase 54.9 Analysis**
**How to debug in 5 minutes instead of 50**

---

## 🎯 The Problem in One Sentence

**Server directories added via `/api/watcher/add` never get indexed to Qdrant, so the tree stays empty, Hostess stays silent, and camera never flies.**

---

## 🚀 Quick Test (2 minutes)

### Step 1: Check if Tree is Empty

```bash
curl http://localhost:5001/api/tree/data?mode=directory | jq '.tree.nodes | length'
```

- **Result: ~1** → Tree empty (just root) ❌
- **Result: >10** → Tree has content ✅

### Step 2: Check What's in Qdrant

```bash
# Direct Qdrant query
curl -X POST http://localhost:6333/collections/vetka_elisya/points/search \
  -H "Content-Type: application/json" \
  -d '{"limit": 1}' | jq '.result | length'
```

- **Result: 0** → Nothing indexed ❌
- **Result: >0** → Files exist ✅

### Step 3: Test the Endpoint

```bash
# Try adding a directory
curl -X POST http://localhost:5001/api/watcher/add \
  -H "Content-Type: application/json" \
  -d '{"path": "/tmp/test", "recursive": true}'

# Check watcher status
curl http://localhost:5001/api/watcher/status | jq '.watching'
```

- **Watcher started** ✅ (will be in output)
- **Files indexed** ❌ (won't happen - this is the bug)

---

## 🔍 Debug Points (By Symptom)

### Symptom: Empty Tree After Adding Directory

**Check these files in order:**

1. **Backend logs** - Does `/api/watcher/add` get called?
   ```
   Look for: [Watcher] Started watching: /path
   Missing: [Watcher] Initial scan: indexed X files
   ```
   📄 `src/api/routes/watcher_routes.py:103`

2. **Qdrant** - Are files in database?
   ```bash
   curl http://localhost:5001/api/tree/data | jq '.tree.metadata'
   ```
   Should show `"total_files": >0`
   📄 `src/api/routes/tree_routes.py:125-137`

3. **Frontend console** - Any errors?
   ```
   Should see: [Socket] tree_updated or browser_folder_added
   Missing: Any directory_scanned event
   ```
   📄 `client/src/hooks/useSocket.ts:227`

---

### Symptom: Hostess Never Speaks After Adding Directory

**Hostess integration flow:**
1. User adds directory → `/api/watcher/add`
2. Backend should emit socket event
3. Frontend listener reloads tree
4. Hostess sees event and adds message

**Debug:**
```
❌ No Hostess message?
   ├─ Check: Did socket event emit? (backend logs)
   ├─ Check: Frontend listener registered? (DevTools)
   └─ Check: ScannerPanel enabled? (Phase 54.7 disabled)
```

📄 `client/src/components/chat/ChatPanel.tsx:309-371`

---

### Symptom: Camera Doesn't Fly After Adding Directory

**Camera flow:**
1. Socket event received (e.g., `browser_folder_added`)
2. Frontend reloads tree
3. CameraController gets command with target
4. CameraController finds node by name
5. Camera animates

**Debug:**
```
❌ Camera not moving?

   → Check browser console for:
     [CameraController] Processing command: {target: ...}
     [CameraController] Found by path: ...

   If YES: Camera should move (check 3D canvas)
   If NO:
     ├─ Socket event never received? (check network tab)
     ├─ setCameraCommand never called? (check frontend logs)
     └─ Tree never reloaded? (check /api/tree/data)
```

📄 `client/src/components/canvas/CameraController.tsx:107-182`

---

## 📊 The Three Paths

### Path 1: Browser Files (WORKS) ✅

```
User drops folder from browser
  ↓
App.tsx: handleFileDrop()
  ↓
POST /api/watcher/add-from-browser
  ↓
watcher_routes.py:221    Get QdrantUpdater ✅
watcher_routes.py:246    Generate embedding ✅
watcher_routes.py:273    Upsert to Qdrant ✅
watcher_routes.py:308    Emit socket event ✅
  ↓
useSocket.ts:227    Listener receives event ✅
useSocket.ts:232    Reload tree ✅
useSocket.ts:250    Camera flies ✅
```

---

### Path 2: Server Directory (BROKEN) ❌

```
POST /api/watcher/add
  ↓
watcher_routes.py:103    Call add_directory() ✅
file_watcher.py:282      Start watchdog observer ✅
  ↓
[MISSING]               NO Qdrant updater
[MISSING]               NO embedding generation
[MISSING]               NO Qdrant upsert
[MISSING]               NO socket event
  ↓
Result: Empty tree, silent Hostess, immobile camera ❌
```

---

### Path 3: Single File (WORKS) ✅

```
POST /api/watcher/index-file
  ↓
watcher_routes.py:399    Get QdrantUpdater ✅
watcher_routes.py:416    Generate embedding ✅
watcher_routes.py:445    Upsert to Qdrant ✅
watcher_routes.py:456    Emit socket event ✅
```

---

## 🔧 Where to Add Fixes

### Fix #1: Scan Existing Files (Backend)

**File:** `src/api/routes/watcher_routes.py`
**Function:** `add_watch_directory()`
**Line:** After 103

**What to add:**
```python
# Scan existing files to Qdrant
# Copy logic from add_from_browser (lines 221-286)
# Use get_qdrant_updater() and qdrant_client.upsert()
```

**Pattern to follow:**
- Line 221: `updater = get_qdrant_updater(qdrant_client=qdrant_client)`
- Line 246: `embedding = updater._get_embedding(embed_text)`
- Line 273: `qdrant_client.upsert(collection_name=updater.collection_name, points=[point])`

---

### Fix #2: Emit Socket Event (Backend)

**File:** `src/api/routes/watcher_routes.py`
**Function:** `add_watch_directory()`
**Line:** After scanning done

**What to add:**
```python
# Emit directory_scanned event
await socketio.emit('directory_scanned', {
    'path': path,
    'files_count': indexed_count
})
```

**Pattern to follow:**
- Line 308: Same pattern as browser_folder_added emit

---

### Fix #3: Add Event Listener (Frontend)

**File:** `client/src/hooks/useSocket.ts`
**Location:** After line 261 (after browser_folder_added handler)

**What to add:**
```typescript
socket.on('directory_scanned', async (data) => {
    // Same logic as browser_folder_added listener
    // Reload tree via /api/tree/data
    // Call setCameraCommand()
})
```

**Pattern to follow:**
- Lines 227-261: Copy this entire handler as template

---

## 📍 Key Line Numbers (Copy-Paste Reference)

### Backend

| What | File | Line | Status |
|------|------|------|--------|
| API entry | watcher_routes.py | 73 | ❌ BROKEN |
| Add to watcher | watcher_routes.py | 103 | ✅ OK |
| Start watchdog | file_watcher.py | 282-285 | ✅ OK |
| **Missing scan** | watcher_routes.py | [AFTER 103] | **🔴 ADD HERE** |
| **Missing emit** | watcher_routes.py | [AFTER SCAN] | **🔴 ADD HERE** |
| Browser pattern | watcher_routes.py | 221-286 | ✅ COPY FROM HERE |
| Emit pattern | watcher_routes.py | 308 | ✅ COPY FROM HERE |

### Frontend

| What | File | Line | Status |
|------|------|------|--------|
| Event types | useSocket.ts | 15-55 | ⚠️ ADD type |
| Browser listener | useSocket.ts | 227-261 | ✅ COPY FROM HERE |
| **Missing listener** | useSocket.ts | [AFTER 261] | **🔴 ADD HERE** |
| Chat handler | ChatPanel.tsx | 309-371 | ✅ OK (unused) |
| Camera find | CameraController.tsx | 49-77 | ✅ OK |
| Camera command | CameraController.tsx | 113-182 | ✅ OK |

---

## 🧪 Validation Tests

### Test 1: Qdrant Populated

```bash
# Before fix
curl http://localhost:5001/api/tree/data | jq '.tree.nodes | length'
# Returns: 1 (just root)

# After adding directory + fix
curl http://localhost:5001/api/tree/data | jq '.tree.nodes | length'
# Returns: >10 (files + folders)
```

---

### Test 2: Socket Event Emitted

**Backend logs should show:**
```
[Watcher] Started watching: /path/to/project
[Watcher] Initial scan: indexed 25 files
[Watcher] Emitted directory_scanned: /path/to/project
```

---

### Test 3: Frontend Receives Event

**Browser DevTools Console:**
```
[Socket] directory_scanned: /path/to/project 25 files
[Socket] Tree reloaded via HTTP: 50 nodes
[CameraController] Processing command: {target: /path/to/project, ...}
[CameraController] Found by path: project
```

---

### Test 4: Camera Animates

**Visual check:**
- Camera moves to folder
- Folder is highlighted (3 seconds)
- Hostess message appears (if triggered)

---

## 💡 Common Mistakes to Avoid

1. **❌ Forgetting `await` on socketio.emit()**
   - Fix: Add `await` before emit

2. **❌ Using wrong collection name**
   - Should be: `'vetka_elisya'`
   - Not: `updater.collection_name` (wait, actually this is OK)

3. **❌ Wrong event name in listener**
   - Must match backend emit: `directory_scanned`
   - Not: `scan_complete` or `directory_indexed`

4. **❌ Forgetting to add event to TypeScript interface**
   - File: `useSocket.ts` lines 15-55
   - Add: `directory_scanned: (data: {...}) => void;`

5. **❌ Not handling case where Qdrant client is null**
   - Add: `if (!qdrant_client) return`

---

## 🎬 Step-by-Step Fix Implementation

### Step 1: Add Scan Logic (5 min)

1. Open: `src/api/routes/watcher_routes.py`
2. Go to: Line 103 (after `watcher.add_directory()`)
3. Copy: Lines 221-286 from same file (browser logic)
4. Adapt: For server files (no virtual path, real paths)

### Step 2: Add Socket Emit (2 min)

1. Stay in: `src/api/routes/watcher_routes.py`
2. After: Scanning loop completes
3. Copy: Lines 298-312 (socket emit pattern)
4. Change: Event name to `directory_scanned`

### Step 3: Add Frontend Type (1 min)

1. Open: `client/src/hooks/useSocket.ts`
2. Go to: Line 24 (in ServerToClientEvents interface)
3. Add: New line: `directory_scanned: (...) => void;`

### Step 4: Add Frontend Listener (5 min)

1. Stay in: `client/src/hooks/useSocket.ts`
2. After: Line 261 (after browser_folder_added handler)
3. Copy: Lines 227-261 (full handler)
4. Rename: Event and update logic

### Step 5: Test (5 min)

1. Restart backend
2. Add directory via API
3. Check: Qdrant populated?
4. Check: Backend logs?
5. Check: Frontend console?
6. Check: Camera moves?

**Total time: ~18 minutes**

---

## 🚨 Emergency Debug Commands

### If tree is empty:

```bash
# Check backend is running
curl http://localhost:5001/api/watcher/status

# Check Qdrant is running
curl http://localhost:6333/collections

# Manually trigger tree recalculation
curl http://localhost:5001/api/tree/clear-semantic-cache
curl http://localhost:5001/api/tree/clear-knowledge-cache
curl http://localhost:5001/api/tree/data?mode=directory | jq '.tree.metadata'
```

### If socket event not received:

```bash
# Check frontend WebSocket connection
# DevTools → Network → WS tab
# Should show: http://localhost:5001/socket.io/?transport=websocket

# Check if listener registered
# DevTools → Console
# Type: window.__socket (if exposed)
```

### If camera won't move:

```bash
# Check in DevTools console:
console.log(useStore.getState().cameraCommand)

# Should show command object
# If null: Command never set
# If object: Check CameraController logs
```

---

## 📚 Reference Documents

- **Full Technical Analysis:** `SCANNER_TECHNICAL_ANALYSIS.md`
- **Original Debug Report:** `SCANNER_DEBUG_REPORT.md`
- **Backend Source:** `src/api/routes/watcher_routes.py`
- **Frontend Source:** `client/src/hooks/useSocket.ts`

---

**Need help?** Check the detailed analysis document for full context and code examples.

**This is just the express lane to the fix!** 🚀
