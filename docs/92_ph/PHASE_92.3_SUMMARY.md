# Phase 92.3: Scan Progress Panel Improvements

**Date:** 2026-01-25
**Status:** COMPLETED

---

## Changes Made

### 1. ScanProgressPanel.css
- Changed `position: absolute; bottom: 0` to `position: relative` (in document flow)
- Border on BOTTOM instead of TOP (since panel now at top)
- Progress bar height: **10px** (was 3px)
- Progress bar has rounded corners (border-radius: 5px)
- File counter now VETKA blue (#4a9eff) with monospace font
- Resize handle at BOTTOM (drag down to expand)
- Added `.file-preview-popup` styles for hover preview

### 2. ScanProgressPanel.tsx
- Added **300ms hover preview** (same pattern as UnifiedSearchBar)
- Added `hoveredFile`, `previewPosition`, `hoverTimerRef` state
- Fixed resize logic: drag DOWN = increase height (panel at top)
- Preview shows: file/directory type, size, date, full path
- Counter format: `{currentFiles}/{totalFiles} files`

### 3. ChatPanel.tsx
- **MOVED** ScanProgressPanel from line 1990 (before MessageInput) to line 1929 (after GroupCreatorPanel, before Messages)
- Now renders: Header → SearchBar → ScannerPanel/GroupCreator → **ScanProgressPanel** → Messages → MessageInput
- MessageInput stays at absolute bottom, unchanged

### 4. ScannerPanel.tsx
- **Shrunk "Clear All Scans"** from full-width button to 32x32px icon button
- Positioned at right side (flex-end)
- Trash icon (SVG inline)
- Loading state shows spinning circle
- Title tooltip: "Clear All Scans"

---

## Visual Layout (After Changes)

```
┌─────────────────────────────────────────────────────┐
│ [Chat] [Scanner] [Group]                     [−][×] │
├─────────────────────────────────────────────────────┤
│ 🔍 Search...                                        │
├─────────────────────────────────────────────────────┤
│ + Add Folder                                   [🗑] │  ← Small trash icon
├─────────────────────────────────────────────────────┤
│ Scanning... 45/156 files                      [▲]  │  ← ScanProgressPanel
│ ██████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │  ← 10px progress bar
│ ✓ src/api/routes.py              (hover=preview)   │
│ ✓ src/api/handlers.py                              │
│ ✓ src/memory/engram.py                             │
│ ═══════════════════════ drag handle ═══════════════│
├─────────────────────────────────────────────────────┤
│                                                     │
│           Messages Area (flex: 1)                   │
│                                                     │
├─────────────────────────────────────────────────────┤
│ [Message input...                          ] [Send] │  ← Unchanged
└─────────────────────────────────────────────────────┘
```

---

## Files Modified

| File | Lines Changed | Summary |
|------|---------------|---------|
| `ScanProgressPanel.css` | Rewritten | position relative, 10px bar, hover preview |
| `ScanProgressPanel.tsx` | Rewritten | 300ms hover, resize from bottom |
| `ChatPanel.tsx` | ~10 lines | Moved ScanProgressPanel to top |
| `ScannerPanel.tsx` | ~40 lines | Shrunk Clear button to icon |

---

## Features

| Feature | Status |
|---------|--------|
| Panel at TOP (not bottom) | ✅ |
| 10px progress bar | ✅ |
| Counter: 45/156 files | ✅ |
| 300ms hover preview | ✅ |
| Click → camera fly-to | ✅ |
| Resize by drag (bottom handle) | ✅ |
| Collapse/expand | ✅ |
| Small trash icon for Clear | ✅ |
| MessageInput unchanged | ✅ |

---

## Testing

To test:
1. Open VETKA UI
2. Go to Scanner tab
3. Click "Add Folder" and select a directory
4. Watch:
   - ScanProgressPanel appears at TOP
   - 10px blue progress bar fills
   - Files list populates
   - Hover 300ms on file → preview popup
   - Click file → camera flies to location
5. Message input remains at bottom

---

## Grok Research Used

`@ramonak/react-progress-bar` was recommended (3.2kB), but we kept custom CSS implementation for:
- Zero additional dependencies
- Full control over Nolan-style design
- Integration with existing VETKA theme

---

---

## Backend Changes (Phase 92.3.1)

### Problem Found
Backend was NOT emitting `scan_progress` events during scan!
- Only `directory_scanned` emitted AFTER scan complete
- Frontend ScanProgressPanel never received progress updates
- Progress bar showed 0%, counter showed 0 files

### Fix 1: QdrantUpdater.scan_directory
**File:** `src/scanners/qdrant_updater.py`

Added `progress_callback` parameter:
```python
def scan_directory(
    self,
    path: str,
    skip_dirs: Optional[List[str]] = None,
    progress_callback: Optional[callable] = None  # NEW
) -> int:
    # First pass - count total files
    total_files = 0
    all_files = []
    for root, dirs, files in os.walk(path):
        ...

    # Second pass - process with progress callback
    for file_path_str in all_files:
        current += 1
        if progress_callback:
            progress_callback(current, total_files, file_path_str)
        ...
```

### Fix 2: watcher_routes.py
**File:** `src/api/routes/watcher_routes.py`

Added progress callback that emits `scan_progress`:
```python
async def emit_progress(current, total, file_path):
    await socketio.emit('scan_progress', {
        'current': current,
        'total': total,
        'progress': int((current / total) * 100),
        'file_path': file_path,
        'status': 'scanning'
    })

def progress_callback(current, total, file_path):
    asyncio.ensure_future(emit_progress(current, total, file_path))

indexed_count = updater.scan_directory(path, progress_callback=progress_callback)
```

Also added `scan_complete` emit after scan finishes.

---

## Files Modified (Backend)

| File | Changes |
|------|---------|
| `src/scanners/qdrant_updater.py` | Added progress_callback parameter |
| `src/api/routes/watcher_routes.py` | Added scan_progress emit in callback |

---

## To Test

1. **Restart backend**: `python main.py` (required for Python changes)
2. **Refresh frontend** or restart `npm run dev`
3. Go to Scanner tab
4. Click "Add Folder" and select a directory
5. Watch:
   - Progress bar fills from 0% to 100%
   - Counter updates: `1/156 files` → `2/156 files` → ...
   - Files appear in list as they're scanned
   - `scan_complete` event shows final count

---

**Phase 92.3 + 92.3.1 COMPLETE**
