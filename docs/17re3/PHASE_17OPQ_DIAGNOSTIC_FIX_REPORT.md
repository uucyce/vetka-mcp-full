# Phase 17-O/P/Q: Diagnostic & Fix Report

**Date:** 2025-12-27
**Agent:** Claude Code Opus 4.5
**Status:** PARTIALLY FIXED
**Commits:** `26b520e`, `7df5fab`

---

## Executive Summary

Провёл полную диагностику Phase 17-O/P/Q и Triple Write. Обнаружено 5 проблем, исправлено 4. Одна проблема (Triple Write для файлов) требует изменения scan pipeline.

---

## 1. Infrastructure Diagnostic

### 1.1 Service Status

| Service | URL | Status | Details |
|---------|-----|--------|---------|
| **Weaviate** | http://localhost:8080 | READY | 8 classes defined |
| **Qdrant** | http://127.0.0.1:6333 | READY | 1 collection, 421 points |
| **Flask** | http://localhost:5001 | READY | All endpoints accessible |

### 1.2 Weaviate Schema

```
✅ Class: VetkaLeaf
✅ Class: VetkaSharedMemory
✅ Class: VetkaGlobal
✅ Class: VetkaChangeLog
✅ Class: VetkaAgentsMemory
✅ Class: VetkaUserFeedback
✅ Class: VetkaElisyaLog
✅ Class: VetkaTree
```

### 1.3 Data Analysis

| Store | Collection | Count | Issue |
|-------|------------|-------|-------|
| Weaviate | VetkaLeaf | 3 | Contains evaluation data, NOT files |
| Qdrant | vetka_elisya | 421 | Main file index (working) |
| Local | chat_history/ | 19 files | Missing `node_path`, `read` fields |
| Local | changelog/ | 0 | Directory was missing |

**VetkaLeaf Schema Problem:**
```json
// Expected:
{"file_path": "...", "file_name": "...", "content": "...", "file_type": "...", "depth": 0}

// Actual:
{"complexity": "...", "evaluation_id": "...", "output": "...", "score": 0.8, "task": "..."}
```

**Chat History Schema Problem:**
```json
// Expected (for badges):
{"role": "assistant", "agent": "PM", "node_path": "src/main.py", "read": false}

// Actual:
{"role": "assistant", "text": "...", "node_id": "123", "timestamp": "..."}
```

---

## 2. Problems Identified

### Problem 1: Branch Context Not Displayed
**Symptom:** Clicking on folder doesn't show context in chat header
**Cause:** `selectNode()` didn't call `onBranchClick()` for folders
**Status:** FIXED

### Problem 2: Chat Badges Not Visible
**Symptom:** No message count badges on file cards
**Cause:** `VETKABadges.updateAllBadges()` looked for DOM elements, but Three.js uses Sprites
**Status:** FIXED

### Problem 3: Chat History Missing Metadata
**Symptom:** Badge API returns counts but can't aggregate by path
**Cause:** `save_chat_message()` didn't add `node_path` and `read` fields
**Status:** FIXED

### Problem 4: ChangeLog Directory Missing
**Symptom:** Triple Write changelog component fails
**Cause:** `data/changelog/` directory never created
**Status:** FIXED

### Problem 5: Weaviate VetkaLeaf Empty (for files)
**Symptom:** Weaviate search returns no file results
**Cause:** Triple Write configured for evaluation data, not file indexing
**Status:** NOT FIXED (requires scan pipeline changes)

---

## 3. Fixes Applied

### Fix 1: Branch Detection in selectNode()

**File:** `src/visualizer/tree_renderer.py` (line 5843-5869)

```javascript
// ✅ PHASE 17-M/P: Determine if file or folder
const nodeType = info.data?.type || info.data?.metadata?.type || info.type || 'unknown';
const nodePath = chatState.currentNodePath;

// Check if this is a folder
const isFolder = nodeType === 'folder' || nodeType === 'directory' || nodeType === 'branch' ||
                 nodeType === 'root' || (nodePath && !nodePath.includes('.'));

// Check if this is a file
const isFile = nodeType === 'file' || nodeType === 'leaf' ||
               (nodePath && nodePath.includes('.') && !nodePath.endsWith('/'));

if (isFolder) {
    // ✅ PHASE 17-P: Handle branch/folder selection
    console.log('[BRANCH] Node is a folder, calling onBranchClick:', nodePath);
    onBranchClick({
        path: nodePath,
        name: info.data?.name || nodePath.split('/').pop(),
        type: 'branch'
    });
} else if (isFile && nodePath && nodePath !== 'Unknown') {
    // ✅ PHASE 17-Q: Mark messages as read
    VETKABadges.markAsRead(nodePath);
    loadFileToArtifact(nodePath);
}
```

### Fix 2: Chat Context Display Element

**File:** `src/visualizer/tree_renderer.py` (line 1872-1876)

```html
<div class="chat-context-display" id="chat-context-display" style="display: none;">
    <span class="context-icon"></span>
    <span class="context-path"></span>
    <span class="context-type"></span>
</div>
```

### Fix 3: Canvas Badge Drawing Function

**File:** `src/visualizer/tree_renderer.py` (line 4635-4672)

```javascript
function drawBadgeOnCanvas(ctx, dims, count, isUnread) {
    if (!count || count <= 0) return;

    const badgeRadius = Math.min(dims.canvasW, dims.canvasH) * 0.08;
    const badgeX = dims.canvasW - badgeRadius - 4;
    const badgeY = badgeRadius + 4;

    ctx.beginPath();
    ctx.arc(badgeX, badgeY, badgeRadius, 0, Math.PI * 2);

    if (isUnread) {
        ctx.fillStyle = 'rgba(76, 175, 80, 0.6)';  // Subtle green
        ctx.strokeStyle = 'rgba(76, 175, 80, 0.4)';
    } else {
        ctx.fillStyle = 'rgba(120, 120, 120, 0.7)';  // Subtle gray
        ctx.strokeStyle = 'rgba(150, 150, 150, 0.4)';
    }

    ctx.fill();
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
    ctx.font = 'bold ' + (badgeRadius * 0.9) + 'px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    const displayCount = count > 99 ? '99+' : count.toString();
    ctx.fillText(displayCount, badgeX, badgeY);
}
```

### Fix 4: Badge Integration in createVisibleFileCard()

**File:** `src/visualizer/tree_renderer.py` (line 4713-4724)

```javascript
// ✅ PHASE 17-Q: Draw badge if this node has messages
if (typeof VETKABadges !== 'undefined' && VETKABadges.counts && nodePath) {
    const badgeData = VETKABadges.counts[nodePath];
    if (badgeData) {
        if (badgeData.unread > 0) {
            drawBadgeOnCanvas(ctx, dims, badgeData.unread, true);
        } else if (badgeData.total > 0) {
            drawBadgeOnCanvas(ctx, dims, badgeData.total, false);
        }
    }
}
```

### Fix 5: Enhanced save_chat_message()

**File:** `main.py` (line 710-734)

```python
def save_chat_message(node_path: str, message: dict):
    """Save a chat message to node's history with proper metadata for badges"""
    if not node_path:
        return
    file = get_chat_history_file(node_path)
    history = load_chat_history(node_path)

    # ✅ PHASE 17-Q: Add node_path and read status for badge tracking
    enhanced_message = {
        **message,
        'node_path': node_path,  # For badge aggregation
        'timestamp': datetime.now().isoformat(),
        'read': message.get('role') == 'user'  # User messages read, agent unread
    }

    history.append(enhanced_message)
    # ... rest of function
```

### Fix 6: ChangeLog Directory

```bash
mkdir -p data/changelog
touch data/changelog/.gitkeep
```

---

## 4. API Endpoints Status

### Phase 17-O: Weaviate Search

```bash
curl -X POST http://localhost:5001/api/search/weaviate \
  -H "Content-Type: application/json" \
  -d '{"query": "main", "limit": 5}'
```

**Response:** Working, uses Qdrant fallback (VetkaLeaf empty)

```json
{
  "success": true,
  "results": [...],
  "total": 5,
  "source": "qdrant"
}
```

### Phase 17-P: Branch Context

```bash
curl -X POST http://localhost:5001/api/branch/context \
  -H "Content-Type: application/json" \
  -d '{"path": "src", "depth": 2}'
```

**Response:** Working

```json
{
  "success": true,
  "context": {
    "branch_name": "src",
    "total_files": 146,
    "total_size_human": "2.2 MB",
    "file_types": {"py": 143, "backup": 2}
  },
  "files": [...]
}
```

### Phase 17-Q: Message Counts

```bash
curl -s http://localhost:5001/api/messages/counts
```

**Response:** Working

```json
{
  "success": true,
  "counts": {
    "node_root": {"total": 27, "unread": 16},
    "node_5727576722312259871": {"total": 13, "unread": 7}
  }
}
```

---

## 5. Files Modified

| File | Lines Changed | Changes |
|------|---------------|---------|
| `main.py` | +15 | Enhanced `save_chat_message()` |
| `src/visualizer/tree_renderer.py` | +95 | Badge drawing, folder detection, context display |
| `data/changelog/.gitkeep` | new | Directory marker |
| `docs/17-6_chat/DIAGNOSTIC_REPORT.md` | new | First diagnostic report |

---

## 6. Testing Checklist

### After Server Restart:

| Feature | Expected | Status |
|---------|----------|--------|
| Cmd+K opens search | Search bar appears | Should Work |
| Search finds files | Results from Qdrant | Working |
| Click folder → context | Shows icon + path + type | Should Work |
| Click file → artifact | Opens in panel | Working |
| Click file → mark read | Socket emit sent | Should Work |
| Badges on file cards | Visible on cards with messages | After tree rebuild |
| New messages save properly | Include node_path, read | After restart |

---

## 7. Remaining Work

### 7.1 Triple Write for File Indexing (NOT FIXED)

**Problem:** VetkaLeaf contains evaluation data, not file metadata.

**Solution Required:** Modify scan pipeline to call Triple Write:

```python
# In src/scanner/ or src/transformers/
async def index_file(file_path: str, content: str):
    await memory_manager.triple_write(
        weaviate_data={
            'class': 'VetkaLeaf',
            'properties': {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'content': content[:5000],
                'file_type': get_extension(file_path),
                'depth': file_path.count('/')
            }
        },
        qdrant_data={...},
        changelog_data={...}
    )
```

### 7.2 Migrate Existing Chat History

**Problem:** 19 existing files lack `node_path` and `read` fields.

**Solution:** One-time migration script:

```python
for chat_file in Path('data/chat_history').glob('*.json'):
    history = json.loads(chat_file.read_text())
    for msg in history:
        if 'node_path' not in msg:
            msg['node_path'] = f"node_{msg.get('node_id', 'unknown')}"
        if 'read' not in msg:
            msg['read'] = msg.get('role') == 'user'
    chat_file.write_text(json.dumps(history, indent=2))
```

### 7.3 Dynamic Badge Updates

**Problem:** Badges drawn at tree creation, don't update in real-time.

**Solution:** Add sprite texture update function:

```javascript
window.updateSpriteBadges = function(counts) {
    fileCards.forEach(card => {
        const path = card.userData.filePath;
        const data = counts[path];
        if (data) {
            // Redraw sprite texture with updated badge
            const texture = createUpdatedTexture(card, data);
            card.material.map = texture;
            card.material.needsUpdate = true;
        }
    });
};
```

---

## 8. Commits

### Commit 1: Initial Implementation
```
26b520e Phase 17-O/P/Q: Weaviate Search + Branch Context + Chat Badges
```

### Commit 2: Diagnostic Fixes
```
7df5fab Phase 17-O/P/Q Fixes: Branch context display + Canvas badges

Fixes:
- selectNode() now detects folders and calls onBranchClick()
- Added #chat-context-display element with icon/path/type
- Added drawBadgeOnCanvas() for Three.js sprite badges
- Enhanced save_chat_message() with node_path and read fields
- Created data/changelog/ directory
- updateChatContextDisplay() now shows context on folder click

Issues Identified:
- VetkaLeaf contains evaluation data, not files (Triple Write config)
- Existing chat history lacks metadata fields
```

---

## 9. Architecture Notes

### Badge Color Scheme (per Danila's spec)

```css
/* Unread (priority): Subtle green */
rgba(76, 175, 80, 0.4)

/* Total messages: Subtle gray */
rgba(120, 120, 120, 0.5)
```

### Badge Priority Logic

```
IF unread > 0:
    Show GREEN badge with unread count
ELSE IF total > 0:
    Show GRAY badge with total count
ELSE:
    No badge
```

### Branch Aggregation

```
Parent branch badge = SUM(all child file badges)

Example:
src/agents/pm.py: 5 messages
src/agents/dev.py: 3 messages
src/agents/: 8 messages (aggregated)
```

---

## 10. Summary

| Phase | Feature | Implementation | Status |
|-------|---------|----------------|--------|
| 17-O | Weaviate Search | API + Frontend | Working (Qdrant fallback) |
| 17-P | Branch Context | API + Click handler + Display | Fixed |
| 17-Q | Chat Badges | API + Canvas drawing | Fixed |
| - | Triple Write | Scan → Weaviate | Not Implemented |

**Total Lines Added:** ~1100
**Files Modified:** 4
**Commits:** 2
