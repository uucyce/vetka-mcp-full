# H13 Quick Reference: File Handling in VETKA

## Files to Know (Reading Order)

```
START HERE:
├─ H13_FINDINGS.md              ← Key discoveries & insights
├─ H13_file_upload_arch.md      ← Detailed technical architecture
├─ H13_file_handling_flow.txt   ← Visual diagrams & flowcharts
└─ This file (quick reference)
```

---

## The 30-Second Version

**How files get into VETKA:**

1. User drags file from Finder/Explorer
2. Tauri detects native drop → real path: `/Users/danilo/app.ts`
3. Frontend routes to DropZoneRouter
4. ScanPanel processes: separate dirs from files
5. POST `/api/watcher/add` with real path
6. Watchdog observer starts monitoring
7. Files indexed to Qdrant (semantic embeddings)
8. File appears in 3D tree

**Browser mode (same but slower):**
- Browser drop → `browser://app.ts` (fake path)
- Backend searches via Spotlight (mdfind)
- Resolves to real path or error
- Rest is the same

---

## File Handling Status

| Component | Status | File | Line |
|-----------|--------|------|------|
| Tauri native file read | ✅ Done | `src-tauri/src/file_system.rs` | 29-52 |
| Tauri native file write | ✅ Done | `src-tauri/src/file_system.rs` | 141-173 |
| Native drag & drop | ✅ Done | `src-tauri/src/main.rs` | 46-72 |
| Frontend drop routing | ✅ Done | `client/src/components/DropZoneRouter.tsx` | 1-379 |
| File scanning | ✅ Done | `client/src/components/scanner/ScanPanel.tsx` | 286-370 |
| Path resolution | ✅ Done | `src/api/routes/files_routes.py` | 361-532 |
| Watcher integration | ✅ Done | `src/api/routes/watcher_routes.py` | 13-150 |
| Qdrant indexing | ✅ Done | `src/scanners/qdrant_updater.py` | Variable |
| 3D visualization | ✅ Done | `client/src/components/canvas/Scene.tsx` | Variable |

---

## Critical Code Paths

### Tauri Path (Real Files)
```
User drops file
    ↓
main.rs:46-72 (DragDropEvent handler)
    ↓
"files-dropped" event emitted
    ↓
DropZoneRouter.tsx:115-148 (onFilesDropped listener)
    ↓
file_system.rs:192-222 (handleDropPaths command)
    ↓
ScanPanel.tsx:286-370 (process dropped files)
    ↓
POST /api/watcher/add (add to watchdog)
    ↓
qdrant_updater.py (index files)
    ↓
File in 3D tree ✅
```

### Browser Path (Fake Files)
```
User drops file
    ↓
DropZoneRouter.tsx:150-283 (HTML5 drag handlers)
    ↓
Create "browser://filename" path
    ↓
ScanPanel.tsx:286-370 (process dropped files)
    ↓
POST /api/files/resolve-path (search for file)
    ↓
Backend search: watched dirs → mdfind → home dir
    ↓
IF FOUND: return real path
IF NOT FOUND: error
    ↓
POST /api/watcher/add (if path found)
    ↓
qdrant_updater.py (index files)
    ↓
File in 3D tree ✅
```

---

## Key APIs

### Tauri Commands (Desktop)
```typescript
// Read file
await readFileNative("/Users/danilo/app.ts")
// Returns: {path, content, size, encoding}

// Write file
await writeFileNative("/Users/danilo/app.ts", "new content")
// Returns: {path, size, confirmation}

// List directory
await listDirectoryNative("/Users/danilo/Projects")
// Returns: FileInfo[] (sorted: dirs first, then alphabetical)

// Handle dropped files
await handleDropPaths(["/Users/danilo/app.ts"])
// Returns: FileInfo[] with metadata

// Watch directory
await watchDirectory("/Users/danilo/Projects")
// Returns: watch ID, emits "file-change" events
```

### Tauri Events (Desktop)
```typescript
// Listen for file drops
const unlisten = await onFilesDropped((paths: string[]) => {
  console.log("Files dropped:", paths);
});

// Listen for file changes
const unlisten = await onFileChange((event: FileChangeEvent) => {
  console.log("File changed:", event.paths);
});

// Listen for heartbeat
const unlisten = await onHeartbeat((payload: HeartbeatPayload) => {
  console.log("Heartbeat:", payload);
});
```

### Backend Endpoints

```bash
# Add directory to watch
POST /api/watcher/add
{
  "path": "/Users/danilo/Projects",
  "recursive": true
}

# Resolve browser drop path
POST /api/files/resolve-path
{
  "filename": "app.ts",
  "relativePath": "src/app.ts",
  "contentHash": "abc123...",
  "fileSize": 2048
}

# Get watcher status
GET /api/watcher/status
# Returns: {watching: ["/path1", "/path2", ...]}

# Read file content
POST /api/files/read
{
  "path": "/Users/danilo/app.ts"
}
# Returns: {content, encoding, mimeType, size, path}

# Save file content
POST /api/files/save
{
  "path": "/Users/danilo/app.ts",
  "content": "new content"
}
# Returns: {success, path, size}

# Open file in Finder
POST /api/files/open-in-finder
{
  "path": "/Users/danilo/app.ts"
}
```

---

## File Path Rules

### Allowed Paths (Tauri Write)
```
✅ /Users/danilo/...       ($HOME)
✅ /tmp/...                (system temp)
✅ /var/folders/...        (macOS temp)

❌ /System/...             (system protected)
❌ /Applications/...       (system protected)
❌ /private/var/db/...     (system protected)
```

### Path Resolution (Backend)
```
/artifact/xxx.md    → data/artifacts/xxx.md (artifacts special)
/absolute/path      → /absolute/path (used directly)
relative/path       → PROJECT_ROOT/relative/path (normalized)

All paths validated with os.path.realpath() (prevents traversal)
All paths checked with os.path.exists() (must exist)
```

---

## File Type Support

### Text Files (Indexed & Searchable)
```
Code:  .py, .js, .ts, .tsx, .jsx, .json, .yaml, .yaml, .xml, .html, .css, .sql, .sh, .java, .go, .rs, .rb, .php, .swift, .kt, .scala, .vue, .svelte, .md, .txt
```

### Binary Files (Metadata Only)
```
Images:   .png, .jpg, .jpeg, .gif, .bmp, .ico, .svg, .webp, .tiff
Video:    .mp4, .avi, .mov, .mkv, .webm, .flv
Audio:    .mp3, .wav, .ogg, .flac, .aac
Fonts:    .ttf, .otf, .woff, .woff2, .eot
Archives: .zip, .tar, .gz, .rar, .7z
Binary:   .exe, .dll, .so, .dylib, .bin, .db, .sqlite, .pyc, .class
```

---

## File Size Limits

| Operation | Limit | Source |
|-----------|-------|--------|
| Tauri Read | 10 MB | `file_system.rs:39` |
| Tauri Write | 10 MB | `file_system.rs:153` |
| HTTP POST | Unlimited | FastAPI default |
| Content Preview | 50 KB | Frontend truncation |
| Qdrant Vector | Unlimited | Semantic embedding |

---

## Common Patterns

### Pattern 1: User Drops Folder
```
User drags /Users/danilo/Projects (folder)
    ↓
handleDropPaths() detects is_dir: true
    ↓
ScanPanel separates into "directories" array
    ↓
POST /api/watcher/add (with path)
    ↓
Watchdog starts monitoring subdirectories
    ↓
All files in folder auto-indexed
```

### Pattern 2: User Drops File
```
User drags /Users/danilo/app.ts (file)
    ↓
handleDropPaths() detects is_dir: false
    ↓
ScanPanel adds to "scannedFiles" (recent list)
    ↓
Frontend shows in recent files, NOT in tree yet
    ↓
User must also drop parent folder OR use /api/watcher/add
```

### Pattern 3: User Adds Path via Input
```
User clicks "Add Directory" in ScanPanel
    ↓
openFolderDialog() (Tauri) or manual input (Browser)
    ↓
User selects /Users/danilo/Projects
    ↓
POST /api/watcher/add (same as drop)
    ↓
Watchdog starts monitoring
```

### Pattern 4: File Gets Edited
```
File changed on disk
    ↓
watchdog detects FileModifiedEvent
    ↓
VetkaFileHandler.on_any_event() triggered
    ↓
Debounce 400ms (coalescence)
    ↓
qdrant_updater.handle_watcher_event()
    ↓
Re-read file + update embeddings in Qdrant
    ↓
Socket.IO emit to frontend
    ↓
3D node updates (glow effect, etc.)
```

---

## Troubleshooting

### Files Don't Appear in Tree
```
Step 1: Check if path was added to watcher
GET /api/watcher/status

Step 2: If not, add manually
POST /api/watcher/add
{
  "path": "/Users/danilo/Projects",
  "recursive": true
}

Step 3: Check if files are being indexed
Monitor qdrant_updater logs for index events

Step 4: Verify files are searchable
Try semantic search in chat panel
```

### Browser Drop Doesn't Work
```
Cause 1: File not indexed by Spotlight
Solution: Add parent folder to watcher manually

Cause 2: mdfind disabled or slow
Solution: Use Tauri mode (native file access)

Cause 3: File is in excluded path
Solution: Check SKIP_PATTERNS in file_watcher.py
```

### Tauri Read Fails
```
Cause 1: File too large (>10MB)
Solution: Increase limit in file_system.rs:39 or read in chunks

Cause 2: File locked by another process
Solution: Wait for process to release file

Cause 3: Permission denied
Solution: Run Tauri app with appropriate permissions
```

---

## Performance Tips

### Tip 1: Watch Specific Folders, Not Root
```
❌ Bad: Watch /Users (too broad, many changes)
✅ Good: Watch /Users/danilo/Projects (specific)
```

### Tip 2: Use Exclude Patterns
```python
# In file_watcher.py SKIP_PATTERNS
# Prevents indexing unneeded directories
SKIP_PATTERNS = [
    'node_modules', '.git', '__pycache__',  # Common
    '.venv', '.env', '.DS_Store',           # Cruft
    'data/changelog', 'watcher_state.json'  # System
]
```

### Tip 3: Batch Operations on Disk
```
When doing bulk edits:
1. Stop watcher temporarily (reduce noise)
2. Do bulk operation (git checkout, npm install)
3. Restart watcher (re-scan everything)

This prevents massive event coalescence.
```

### Tip 4: Use ReadFileNative for Previews
```typescript
// In Tauri mode, read file content directly
// Don't make HTTP request to /api/files/read
// This avoids network roundtrip

const content = await readFileNative(path);
// Much faster than: fetch('/api/files/read', {body: path})
```

---

## Next Steps (Phase 101)

### High Priority
1. **Faster Tauri Indexing** - Send content preview with path
2. **Performance Metrics** - Track index speed improvements
3. **User Documentation** - Tutorial for adding files

### Medium Priority
1. **Artifact Auto-Indexing** - Auto-watch data/artifacts folder
2. **FileSystemHandle Enhancement** - Better browser support
3. **Incremental Indexing** - Track file changes incrementally

### Low Priority
1. **Cloud Storage Mounting** - Google Drive, Dropbox integration
2. **Network File Support** - NFS, SMB mounts
3. **Advanced Filters** - Custom exclusion patterns

---

## Key Contacts in Code

**Tauri IPC:**
- `client/src/config/tauri.ts` - Runtime detection & dynamic imports
- `client/src-tauri/src/main.rs` - DragDrop event handler
- `client/src-tauri/src/file_system.rs` - File operations

**Frontend:**
- `client/src/components/DropZoneRouter.tsx` - Drop zone routing
- `client/src/components/scanner/ScanPanel.tsx` - File processing
- `client/src/components/canvas/Scene.tsx` - 3D visualization

**Backend:**
- `src/api/routes/files_routes.py` - File read/write/resolve
- `src/api/routes/watcher_routes.py` - Watch directory add/remove
- `src/scanners/file_watcher.py` - File system monitoring
- `src/scanners/qdrant_updater.py` - Semantic indexing

---

## Checklists

### Adding New File Type Support
```
[ ] Add extension to SUPPORTED_EXTENSIONS in file_watcher.py
[ ] Add mime type detection in files_routes.py
[ ] Add preview renderer in FileCard.tsx LOD levels
[ ] Test drag & drop with new file type
[ ] Test semantic search indexing
[ ] Document in H13_file_handling_flow.txt
```

### Debugging File Indexing
```
[ ] Check path in /api/watcher/status
[ ] Check file exists: os.path.exists(path)
[ ] Check file not excluded: SKIP_PATTERNS
[ ] Monitor qdrant_updater logs
[ ] Check Qdrant collection for file metadata
[ ] Verify embedding generated successfully
[ ] Test semantic search in chat
```

### Optimizing Watch Performance
```
[ ] Review watched directories (GET /api/watcher/status)
[ ] Check for overly broad watches (e.g., /)
[ ] Verify SKIP_PATTERNS is complete
[ ] Monitor debounce events (400ms coalescence)
[ ] Check for file lock loops
[ ] Review socket.IO emission frequency
```

---

## References

- **Architecture Diagram:** `H13_file_handling_flow.txt` (comprehensive ASCII diagrams)
- **Detailed Analysis:** `H13_file_upload_arch.md` (full technical breakdown)
- **Key Findings:** `H13_FINDINGS.md` (insights & opportunities)
- **This Document:** `H13_QUICK_REFERENCE.md` (quick lookup)

---

**Last Updated:** January 29, 2026
**Status:** Complete & verified
**Next Review:** Phase 101 enhancements
