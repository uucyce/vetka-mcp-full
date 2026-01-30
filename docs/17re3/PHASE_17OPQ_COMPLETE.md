# Phase 17-O/P/Q: Weaviate Search + Branch Context + Chat Badges

**Date:** 2025-12-27
**Status:** COMPLETED
**Agent:** Claude Code Opus 4.5

---

## Summary

Implemented three interconnected features for VETKA visualization system:

| Phase | Feature | Status |
|-------|---------|--------|
| **17-O** | Weaviate Semantic Search | Completed |
| **17-P** | Branch Context for Agents | Completed |
| **17-Q** | Chat Message Badges | Completed |

---

## Phase 17-O: Weaviate Semantic Search

### API Endpoint

```
POST /api/search/weaviate
```

**Request:**
```json
{
  "query": "search text",
  "limit": 15,
  "filters": {}
}
```

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "id": "uuid",
      "path": "src/file.py",
      "name": "file.py",
      "type": "py",
      "distance": 0.2,
      "certainty": 0.8,
      "snippet": "first 200 chars...",
      "source": "weaviate"
    }
  ],
  "total": 15,
  "query": "search text",
  "source": "weaviate"
}
```

### Features

- **Hybrid Search:** Uses Weaviate's hybrid search (alpha=0.7) combining keyword + vector similarity
- **Fallback:** Automatically falls back to Qdrant semantic search if Weaviate unavailable
- **Security:** Query sanitization, length limits (max 50 results)

### Frontend: Cmd+K Search

- **Shortcut:** `Cmd+K` (macOS) / `Ctrl+K` (Windows/Linux) opens search bar
- **Debounce:** 300ms delay before sending requests
- **Results:** Show file name, path, snippet, match score, and source
- **Actions:** Click result to focus node in 3D tree + open in artifact panel

### Files Modified

- `main.py`: Added `/api/search/weaviate` endpoint (lines 5514-5642)
- `src/visualizer/tree_renderer.py`:
  - CSS: `.vetka-search-bar` styles (lines 772-897)
  - HTML: Search bar element (lines 1700-1706)
  - JS: `VETKASearch` object (lines 9272-9440)

---

## Phase 17-P: Branch Context for Agents

### API Endpoint

```
POST /api/branch/context
```

**Request:**
```json
{
  "path": "src/agents",
  "depth": 2,
  "include_content": false
}
```

**Response:**
```json
{
  "success": true,
  "context": {
    "branch_path": "src/agents",
    "branch_name": "agents",
    "full_path": "/full/path/src/agents",
    "total_files": 25,
    "total_size": 125000,
    "total_size_human": "122.1 KB",
    "total_lines": 3500,
    "file_types": {"py": 20, "md": 5},
    "max_depth_scanned": 2,
    "structure_preview": ["path1", "path2", ...]
  },
  "files": [
    {"path": "...", "name": "...", "size": 1234, "ext": "py", "mtime": 1735300000}
  ]
}
```

### Features

- **Deep Scanning:** Configurable depth (max 5 levels)
- **Content Inclusion:** Optional file content for text files (<30KB)
- **Smart Filtering:** Skips `.git`, `node_modules`, `__pycache__`, binary files
- **File Type Stats:** Aggregates counts by extension

### Socket.IO Events

- **`select_branch`:** Client emits when branch is clicked
- **`branch_selected`:** Server confirms branch selection

### Files Modified

- `main.py`:
  - Added `/api/branch/context` endpoint (lines 5645-5762)
  - Added `select_branch` Socket.IO handler (lines 5901-5917)
- `src/visualizer/tree_renderer.py`:
  - CSS: `.chat-context-display` styles (lines 937-966)
  - JS: `onBranchClick()`, `updateChatContextDisplay()` functions (lines 9582-9629)

---

## Phase 17-Q: Chat Message Badges

### API Endpoint

```
GET /api/messages/counts
```

**Response:**
```json
{
  "success": true,
  "counts": {
    "src/file.py": {"total": 5, "unread": 2},
    "src": {"total": 12, "unread": 3}
  }
}
```

### Badge Logic

```
PRIORITY:
├─ If unread from agents > 0 → GREEN badge with unread count
└─ Else if total > 0 → GRAY badge with total count

COLORS (subtle/muted):
├─ Green (unread): rgba(76, 175, 80, 0.4)
└─ Gray (total): rgba(120, 120, 120, 0.5)

AGGREGATION:
└─ Parent branches sum all child file counts
```

### Socket.IO Events

- **`mark_messages_read`:** Client emits when file is opened
- **`message_counts_updated`:** Server broadcasts updated counts to all clients

### Features

- **Real-time Updates:** Via Socket.IO broadcast
- **Auto-refresh:** Every 30 seconds
- **Aggregation:** Branch badges sum all child file counts
- **Subtle Design:** Muted colors to not distract

### Files Modified

- `main.py`:
  - Added `/api/messages/counts` endpoint (lines 5765-5839)
  - Added `mark_messages_read` Socket.IO handler (lines 5842-5898)
- `src/visualizer/tree_renderer.py`:
  - CSS: `.node-badge` styles (lines 899-935)
  - JS: `VETKABadges` object (lines 9442-9580)

---

## Testing Checklist

### Weaviate Search (17-O)

- [x] `Cmd+K` opens search bar
- [x] Typing triggers debounced search (300ms)
- [x] Results show with name, path, snippet
- [x] Click result closes search
- [x] Escape closes search
- [x] Fallback to Qdrant works

### Branch Context (17-P)

- [x] Click on folder emits `select_branch`
- [x] API returns file list and summary
- [x] Content inclusion works for text files
- [x] Depth limiting works

### Chat Badges (17-Q)

- [x] Badges load on page init
- [x] Green badge for unread messages
- [x] Gray badge for total messages
- [x] Real-time updates via Socket.IO
- [x] Mark as read when file opened

---

## Technical Details

### Dependencies

- **Weaviate:** `http://localhost:8080` (optional, falls back to Qdrant)
- **Qdrant:** `http://127.0.0.1:6333` (fallback for search)
- **Socket.IO:** Real-time badge updates

### Security

- Path traversal prevention (`..` rejected)
- Query length limits
- File size limits for content inclusion
- Directory skip patterns for sensitive folders

### Performance

- Debounced search (300ms)
- Badge refresh every 30 seconds
- Max 50 search results
- Max 100 files in branch context response

---

## Lines of Code Added

| File | Lines Added |
|------|-------------|
| `main.py` | ~400 lines |
| `src/visualizer/tree_renderer.py` | ~600 lines |
| **Total** | ~1000 lines |

---

## Future Improvements

From Danila's requirements (not implemented yet):

1. **Chat Y-axis sync:** Align chat messages Y-position with tree Y-position
2. **Chat branching:** Sugiyama layout for chat stems
3. **Chat direction:** Input at top, messages flow down

---

## Commit

```bash
git add main.py src/visualizer/tree_renderer.py docs/17re3/

git commit -m "Phase 17-O/P/Q: Weaviate Search + Branch Context + Chat Badges

Features:
- 17-O: Semantic search via Weaviate (Cmd+K), Qdrant fallback
- 17-P: Branch context API for agents (folder metadata)
- 17-Q: Chat message badges on tree nodes (unread priority)

API Endpoints:
- POST /api/search/weaviate - Hybrid search
- POST /api/branch/context - Folder context
- GET /api/messages/counts - Badge counts

Socket.IO:
- select_branch, branch_selected
- mark_messages_read, message_counts_updated

UI:
- Search bar with Cmd+K shortcut
- Subtle green/gray badges
- Branch context display

Generated with Claude Code
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```
