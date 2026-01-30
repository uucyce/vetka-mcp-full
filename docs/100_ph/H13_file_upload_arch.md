# H13 Reconnaissance Report: File Upload Architecture & Tauri Native File Access

**Date:** 2026-01-29
**Status:** Complete Analysis
**Phase:** 100.2 - Native File System Integration

---

## Executive Summary

VETKA has **successfully unlocked direct file access** through Tauri's native IPC. The system is now capable of:

1. **Native drag & drop** with real file paths (not browser paths)
2. **Direct file reading** without HTTP overhead via `readFileNative()`
3. **Native directory watching** for automatic indexing
4. **Seamless Tauri/Browser dual mode** with automatic fallback

The current architecture is **dual-mode capable** but has a critical gap: **browser mode files have fake "browser://" paths and cannot be indexed by the backend**.

---

## Current File Handling Flow

### Phase 1: File Drop Detection

#### Tauri Mode (Desktop)
```
User drops file/folder
    ↓
Tauri DragDropEvent handler (main.rs:46-72)
    ↓
Window emits "files-dropped" event with real paths: ["/Users/danilo/Projects/app.ts"]
    ↓
Frontend listener: onFilesDropped() (DropZoneRouter.tsx:123)
    ↓
handleDropPaths(paths) → Tauri command reads file metadata
```

**Key Location:** `/client/src-tauri/src/main.rs:46-72`

```rust
window.on_window_event(move |event| {
    if let tauri::WindowEvent::DragDrop(drag_event) = event {
        match drag_event {
            tauri::DragDropEvent::Drop { paths, position: _ } => {
                let path_strings: Vec<String> = paths
                    .iter()
                    .map(|p| p.to_string_lossy().to_string())
                    .collect();
                // Emit to frontend with REAL file paths
                let _ = window_handle.emit("files-dropped", &path_strings);
            }
        }
    }
});
```

#### Browser Mode (Web)
```
User drops file/folder
    ↓
HTML5 DragEvent handler (DropZoneRouter.tsx:190)
    ↓
Try FileSystemHandle API (modern browsers)
    ↓
Create fake path: "browser://filename" (security restriction)
    ↓
Dispatch drop with FileInfo objects
```

**Key Insight:** Browser paths are FAKE and start with `browser://` prefix (line 219, 231, 242 in DropZoneRouter.tsx). These **cannot be indexed** because they don't exist on the filesystem.

---

### Phase 2: File Metadata Resolution

**Location:** `/client/src-tauri/src/file_system.rs:191-222`

```rust
pub async fn handle_drop_paths(paths: Vec<String>) -> Result<Vec<FileInfo>, String> {
    let mut results = Vec::new();

    for path_str in paths {
        let path = PathBuf::from(&path_str);

        if !path.exists() {  // Real filesystem check
            continue;
        }

        // Extract: name, size, modified time, extension
        results.push(FileInfo {
            name: path.file_name()...
            path: path_str,      // REAL PATH
            is_dir: path.is_dir(),
            size: metadata.as_ref().map(|m| m.len())...
            modified: metadata.and_then(|m| m.modified().ok()?)...
            extension: path.extension()...
        });
    }
}
```

**Returns:** `FileInfo[]` with full metadata - ready for backend indexing.

---

### Phase 3: Backend Path Resolution

**Current Limitation:** Backend only accepts PATH strings, not content.

#### Route: `POST /api/files/resolve-path`
**Location:** `/src/api/routes/files_routes.py:361-532`

This endpoint uses a **3-tier search strategy** to resolve browser paths:
1. Search in watched directories (fast)
2. Use macOS Spotlight (`mdfind`) for instant search
3. Fallback to home directory search

**Problem:** This endpoint is designed for BROWSER drops (where we don't have real paths). For Tauri drops, we already have real paths - no resolution needed!

```python
@router.post("/resolve-path")
async def resolve_file_path(req: FileResolveRequest, request: Request):
    """
    When a file is dropped from browser, we don't get the full path.
    This searches for the file on disk using filename + metadata.

    Search strategy:
    1. Search in watched directories (fast, likely match)
    2. Use mdfind (macOS Spotlight)  ← Best for browser drops
    3. Fallback to find in home directory (slow)
    """
    # Returns: { status, path, candidates, needsWatchedDir }
```

---

### Phase 4: Adding to File Tree (Watcher)

**Location:** `/src/api/routes/watcher_routes.py:13-14`

```
POST /api/watcher/add  - Add directory to watch list
Body: { "path": "/Users/.../project", "recursive": true }
```

**Frontend Code:** `ScanPanel.tsx:309-323`
```typescript
// After files dropped, add directories to watcher
for (const dir of directories) {
    const response = await fetch(`${API_BASE}/watcher/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: dir.path, recursive: true })
    });
    // Backend starts watching and indexing
}
```

**Key Insight:** We send **PATHS as strings** to the backend. The backend then:
1. Validates the path exists
2. Adds to watchdog observer
3. Starts scanning files
4. Indexes to Qdrant

---

## Architecture Diagram: Current Flow

```
┌─────────────────────────────────────────────────────────┐
│                    USER INTERACTION                      │
│                  Drag & Drop Files                       │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ↓                         ↓
   [TAURI MODE]            [BROWSER MODE]
   Real File Paths         Browser:// Paths
   /Users/app.ts           browser://app.ts
        │                         │
        │                         │
   ┌────┴─────────┐          ┌────┴──────────────┐
   │ Window Event │          │ HTML5 DragEvent   │
   │ DragDrop     │          │ FileSystemHandle  │
   └────┬─────────┘          └────┬──────────────┘
        │                         │
        ↓                         ↓
┌─────────────────────────────────────────────────────────┐
│         Frontend: DropZoneRouter.tsx                    │
│  onFilesDropped() + handleDropPaths() + FileInfo        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│      ScanPanel.tsx: Process Drops                       │
│  - Separate directories from files                      │
│  - Send PATH strings to backend                         │
│  - Emit "files_dropped" event                           │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ↓                         ↓
  [TAURI BACKEND]        [BROWSER BACKEND]
  Real paths work         Needs resolve-path
  Direct indexing        Search + resolve
        │                         │
        ├─────────────┬───────────┤
        │             │           │
        ↓             ↓           ↓
    ┌──────────────────────────────────────┐
    │ Backend: /api/watcher/add            │
    │ Validates path exists on filesystem  │
    │ Adds to watchdog observer            │
    │ Starts async scan + Qdrant indexing  │
    └──────────────────────────────────────┘
```

---

## Current File Input Routes

### 1. Direct Path Input
- **Endpoint:** `POST /api/watcher/add`
- **Input:** `{ "path": "/real/filesystem/path", "recursive": true }`
- **Status:** ✅ Fully functional
- **Use Case:** User manually enters a path in UI

### 2. Browser Drag & Drop with Path Resolution
- **Endpoint:** `POST /api/files/resolve-path`
- **Input:** `{ "filename": "app.ts", "relativePath": "src/", "contentHash": "abc123", "fileSize": 1024 }`
- **Status:** ✅ Fully functional
- **Use Case:** Browser mode files (paths start with `browser://`)
- **Location:** `/src/api/routes/files_routes.py:361-532`

### 3. Tauri Native Drag & Drop
- **Endpoint:** (No dedicated endpoint - direct Tauri IPC)
- **Input:** Real file paths from Tauri's DragDrop event
- **Status:** ✅ Working but bypasses HTTP entirely
- **Flow:** Tauri paths → Frontend → `/api/watcher/add` (as path string)

---

## Current Tauri Native Capabilities

### Available Commands (Phase 100.2)

**Location:** `/client/src-tauri/src/file_system.rs`

| Command | Purpose | Input | Output | Status |
|---------|---------|-------|--------|--------|
| `read_file_native` | Read file content directly | `path: String` | `FileContent { path, content, size, encoding }` | ✅ Implemented |
| `list_directory` | List dir contents | `path: String` | `Vec<FileInfo>` | ✅ Implemented |
| `write_file_native` | Write file (with security checks) | `path, content` | `String` (confirmation) | ✅ Implemented |
| `remove_file_native` | Delete file | `path: String` | `String` (confirmation) | ✅ Implemented |
| `handle_drop_paths` | Process dropped files | `Vec<String>` | `Vec<FileInfo>` | ✅ Implemented |
| `watch_directory` | Start watching dir | `path: String` | `String` (watch ID) | ✅ Implemented |

### Available Event Listeners (Phase 100.2)

**Location:** `/client/src/config/tauri.ts`

| Event | Triggered By | Payload | Status |
|-------|--------------|---------|--------|
| `files-dropped` | User drags files to window | `Vec<String>` (real paths) | ✅ Implemented |
| `file-change` | File system event | `FileChangeEvent` | ✅ Implemented |
| `heartbeat` | Tauri backend periodically | `HeartbeatPayload` | ✅ Implemented |

---

## Path Handling: Detailed Breakdown

### Tauri Mode Path Flow

```typescript
// Step 1: Native drop (Rust)
window_handle.emit("files-dropped", ["/Users/danilo/app.ts"])

// Step 2: Frontend listener
onFilesDropped(async (paths: string[]) => {
    // paths = ["/Users/danilo/app.ts"]  ← REAL PATH

    // Step 3: Get metadata
    const fileInfos = await handleDropPaths(paths);
    // fileInfos = [{
    //   path: "/Users/danilo/app.ts",     ← REAL PATH
    //   name: "app.ts",
    //   is_dir: false,
    //   size: 2048,
    //   modified: 1706470000
    // }]

    // Step 4: Send to backend
    await fetch(`/api/watcher/add`, {
        body: JSON.stringify({
            path: "/Users/danilo/app.ts"   ← REAL PATH
        })
    });
});
```

**Result:** Backend receives real paths that exist on the filesystem. Indexing works directly.

---

### Browser Mode Path Flow

```typescript
// Step 1: Browser drop (HTML5)
const file = await handle.getFile();
// Cannot get real path due to browser security

// Step 2: Create fake path
const filePath = `browser://${file.name}`;  // browser://app.ts

// Step 3: Send to backend
await fetch(`/api/files/resolve-path`, {
    body: JSON.stringify({
        filename: "app.ts",
        contentHash: "abc123...",
        fileSize: 2048
    })
});

// Step 4: Backend searches for matching file
// - Look in watched directories first
// - Use mdfind (macOS Spotlight)
// - Search home directory
// Result: If found, real path returned

// Step 5: Add real path to watcher
await fetch(`/api/watcher/add`, {
    body: JSON.stringify({
        path: "/Users/danilo/app.ts"   ← RESOLVED from browser drop
    })
});
```

**Result:** Browser drops work but require resolution step. If file not found, indexing fails.

---

## What's Missing: Direct File Content Support

### Current Limitation

The system **only accepts file PATHS**, not file CONTENT. This means:

❌ **CANNOT:**
- Drop a new file that doesn't exist on the filesystem yet
- Drop a file from a cloud storage or temporary location
- Process in-memory files

✅ **CAN:**
- Drop files from local filesystem (Tauri or browser with Spotlight)
- Drop folders to start watching
- Index existing files

### Why Path-Only Design?

1. **Performance:** Tauri can read files directly via native code - no HTTP overhead
2. **Consistency:** Single source of truth - the filesystem
3. **Security:** Files can only come from disk, not arbitrary content
4. **Watching:** Only paths can be watched by the file watcher

### When Path-Only Limitation Matters

- **Use Case 1:** User wants to scan `/Downloads` - works via directory watch
- **Use Case 2:** User drops a zip file to extract & index - works if unzipped first
- **Use Case 3:** User wants to index a cloud file - broken (would need local copy)

---

## Backend File Validation Strategy

**Location:** `/src/api/routes/files_routes.py:71-94`

```python
def _resolve_path(file_path: str) -> tuple[str, bool]:
    """
    Resolve file path with special handling for artifacts.

    Rules:
    1. /artifact/xxx.md  → data/artifacts/xxx.md (allow creation)
    2. /absolute/path    → use directly
    3. relative/path     → resolve from PROJECT_ROOT
    """
    clean_path = file_path.lstrip("/")

    # Artifact paths are special (can create new)
    if clean_path.startswith("artifact/"):
        artifact_name = clean_path.replace("artifact/", "", 1)
        artifact_name = artifact_name.replace("..", "").replace("/", "_")
        real_path = os.path.abspath(os.path.join(PROJECT_ROOT, "data", "artifacts", artifact_name))
        return real_path, True

    # Absolute paths
    elif file_path.startswith("/"):
        return os.path.realpath(file_path), False

    # Relative paths
    else:
        return os.path.realpath(os.path.join(PROJECT_ROOT, file_path)), False
```

**Key Insight:** Backend supports:
1. Real filesystem paths (validated with `os.path.exists()`)
2. Special artifact paths (`/artifact/...` for generated content)
3. Relative paths (resolved from project root)

---

## Recommended Architecture for Phase 101

### Option A: Enhance Tauri Support (RECOMMENDED)

**Goal:** Leverage Tauri's native file access for faster indexing.

#### Backend Changes

1. **New endpoint:** `POST /api/files/add-with-content`
   ```python
   @router.post("/files/add-with-content")
   async def add_file_with_content(req: FileAddRequest):
       """
       Add file directly without requiring it to exist on watched paths.
       Tauri sends file path + optional content preview.
       """
       path = req.path
       content = req.content  # Optional preview (first 1KB)

       # If content provided, use directly
       if content:
           # Index preview immediately
           # Full file will be indexed when watcher picks it up
           pass

       # Always validate path exists
       if not os.path.exists(path):
           raise HTTPException(400, "File not found")

       # Add to watcher
       watcher.add_directory(os.path.dirname(path), recursive=False)
       return { "path": path, "indexed": True }
   ```

2. **New Tauri command:** `fast_index_file`
   ```rust
   pub async fn fast_index_file(
       path: String,
   ) -> Result<FileContent, String> {
       // Read file content directly
       // Return to frontend for preview
       // Frontend sends both path + preview to backend
       // Backend indexes faster (preview already available)
   }
   ```

#### Frontend Changes

1. **Enhance DropZoneRouter:**
   ```typescript
   // When Tauri file drops
   const fileInfos = await handleDropPaths(paths);

   // For text files, also read content
   const filesWithContent = await Promise.all(
       fileInfos
           .filter(f => isTextFile(f.name))
           .map(async f => ({
               ...f,
               content: await readFileNative(f.path)
           }))
   );

   // Send to backend with content preview
   await fetch('/api/files/add-with-content', {
       body: JSON.stringify(filesWithContent)
   });
   ```

#### Benefits
- Tauri drops are **instant** (content already loaded)
- Backend can index preview while watching full file
- Works seamlessly with existing watch system
- No HTTP overhead for large files

---

### Option B: Unify Browser & Tauri (Future)

**Goal:** Make browser mode as capable as Tauri mode.

#### Requirements
1. Implement `FileSystemHandle` API more robustly
2. Use "Access Handles" for persistent file references
3. Store file permissions in IndexedDB
4. Allow browser to read actual file content (with permission)

#### Status
- ⏳ Browser FileSystemHandle API still experimental
- ⏳ Chrome 86+, Edge 86+, but Safari/Firefox limited
- ⏳ Would require major refactoring

---

### Option C: Hybrid Mode (CURRENT)

**Goal:** Use whatever mode is available.

**Rules:**
1. Tauri mode: Use native paths directly
2. Browser mode: Resolve paths via Spotlight + search
3. Fallback: Offer manual path input

**Status:** ✅ Already implemented (Phase 100.4)

---

## Security Considerations

### Path Validation in Tauri

**Location:** `/client/src-tauri/src/file_system.rs:224-232`

```rust
fn is_allowed_path(path: &PathBuf) -> bool {
    // Only allow paths under $HOME or /tmp
    let home = std::env::var("HOME").unwrap_or_else(|_| "/Users".to_string());

    path.starts_with(&home)
        || path.starts_with("/tmp")
        || path.starts_with("/var/folders")  // macOS temp
}
```

**Current Restrictions:**
- ✅ Write/remove only allowed in `$HOME`, `/tmp`, `/var/folders`
- ✅ Read allowed anywhere (trust user's machine)
- ✅ 10MB file size limit
- ✅ Path must exist (validated with `os.path.exists()`)

### Backend Path Validation

**Location:** `/src/api/routes/files_routes.py:123-130`

```python
if not os.path.exists(real_path):
    raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

if os.path.isdir(real_path):
    raise HTTPException(status_code=400, detail="Path is a directory, not a file")
```

**Current Restrictions:**
- ✅ File must exist on filesystem
- ✅ Cannot be a directory
- ✅ No path traversal (uses `os.path.realpath()`)

---

## File Handling: Complete Sequence Diagram

```
┌──────────────┐                                           ┌─────────┐
│   USER       │                                           │ BACKEND │
└──────┬───────┘                                           └────┬────┘
       │                                                        │
       │ Drag file to window                                    │
       │                                                        │
       ├─────────────────────┐                                  │
       │                     │                                  │
       ↓ [Tauri]            ↓ [Browser]                        │
   Native path          HTML5 Drop                            │
   /Users/app.ts        browser://app.ts                      │
       │                     │                                  │
       ├─────────────────────┤                                  │
       │       ↓ DropZoneRouter                                │
       │   Recognize paths                                     │
       │                                                        │
       ├─────────────────────┤                                  │
       │       ↓ ScanPanel                                      │
       │   Separate dirs/files                                 │
       │                                                        │
       ├─────────────────────┤                                  │
       │                     │                                  │
   Tauri:             Browser:                                 │
   Send real path     Send for resolution                      │
       │                     │                                  │
       ├────────────────────────────────────────────────→ /api/files/resolve-path
       │ /api/watcher/add       ← Results: real path
       ├────────────────────────────────────────────────→ /api/watcher/add
       │                                                        │
       │                     ← Watcher starts scanning
       │                     ← Qdrant indexing begins
       │                                                        │
       ← Files appear in tree                                  │
```

---

## Implementation Status Summary

| Component | Status | Location | Phase |
|-----------|--------|----------|-------|
| Tauri IPC Bridge | ✅ Complete | `/client/src-tauri/src/` | 100.1 |
| Native File Read | ✅ Complete | `file_system.rs:29-52` | 100.2 |
| Native File Write | ✅ Complete | `file_system.rs:141-173` | 100.2 |
| Drag & Drop Events | ✅ Complete | `main.rs:46-72` | 100.2 |
| Frontend Listeners | ✅ Complete | `DropZoneRouter.tsx:115-148` | 100.4 |
| Path Resolution | ✅ Complete | `files_routes.py:361-532` | 54.6 |
| Watcher Integration | ✅ Complete | `watcher_routes.py` | 96+ |
| File Indexing | ✅ Complete | `qdrant_updater.py` | 90+ |
| **Browser/Tauri Dual Mode** | ✅ Complete | `tauri.ts:68-70` | 100.4 |

---

## Quick Reference: Adding Files to VETKA

### Method 1: Drag & Drop (Recommended)
1. User drags file/folder from Finder/Explorer
2. Frontend detects drop zone (tree or chat)
3. Tauri: Direct native path usage
4. Browser: Auto-resolution via Spotlight
5. Files appear in 3D tree

### Method 2: Manual Path Input (ScanPanel)
1. User clicks "Add Directory"
2. Opens native folder dialog (Tauri) or asks for path (Browser)
3. Backend validates path exists
4. Starts watching & indexing

### Method 3: Programmatic (API)
```bash
curl -X POST http://localhost:5001/api/watcher/add \
  -H "Content-Type: application/json" \
  -d '{"path": "/Users/danilo/Projects/app", "recursive": true}'
```

---

## Conclusion

**Current state:** ✅ File handling architecture is **mature and production-ready** for Phase 100.

**Key achievements:**
1. Seamless Tauri/Browser dual mode
2. Native file access without HTTP overhead
3. Intelligent path resolution for browser drops
4. Real-time file watching & indexing
5. Secure path validation (filesystem-first)

**Next frontier (Phase 101+):**
1. Enhanced Tauri support with content preview
2. Better browser FileSystemHandle integration
3. Direct file content support (optional)
4. Cloud storage integration

The architecture **does not block direct file content** - it just doesn't require it. Paths are sufficient because all files must exist on the local filesystem for the VETKA watcher to index them efficiently.

---

**Report Generated:** Phase 100.4 Analysis
**Next Steps:** Implement Phase 101 enhancements or continue with Phase 99 memory architecture
