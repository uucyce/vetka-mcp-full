# Artifact Scanner Quick Reference

**Phase:** 108.3
**Marker:** `MARKER_108_3_ARTIFACT_SCAN`
**Status:** ✅ Active

## Quick Import

```python
from src.services.artifact_scanner import (
    scan_artifacts,
    build_artifact_edges,
    update_artifact_positions
)
```

## Usage Pattern

```python
# Step 1: Scan artifacts
artifact_nodes = scan_artifacts()
# Returns: List[Dict] of artifact nodes

# Step 2: Build edges (requires chat_nodes)
artifact_edges = build_artifact_edges(artifact_nodes, chat_nodes)
# Returns: List[Dict] of edges from chats to artifacts

# Step 3: Update positions (modifies artifact_nodes in-place)
update_artifact_positions(artifact_nodes, chat_nodes)
# Positions artifacts relative to parent chats
```

## Artifact Node Quick View

```python
{
    "id": "artifact_{hash}",           # Stable ID from filename hash
    "type": "artifact",                 # Always "artifact"
    "name": "config.py",                # Filename
    "parent_id": "chat_{id}",          # Source chat (None if not linked)
    "metadata": {
        "file_path": "data/artifacts/...",
        "artifact_type": "code|document|data|image",
        "language": "python|markdown|json|...",
        "size_bytes": 1234,
        "created_at": "ISO8601",
        "modified_at": "ISO8601",
        "source_message_id": "msg_xxx",  # From staging.json
        "source_chat_id": "chat_xxx",    # From staging.json
        "status": "done|streaming|error",
        "extension": ".py"
    },
    "visual_hints": {
        "layout_hint": {"expected_x": 120, "expected_y": 300, "expected_z": 0},
        "color": "#10b981",  # Type-based color
        "opacity": 1.0
    }
}
```

## Type Colors

| Type | Color | Hex |
|------|-------|-----|
| code | Green | `#10b981` |
| document | Blue | `#3b82f6` |
| data | Amber | `#f59e0b` |
| image | Pink | `#ec4899` |

## File Type Mapping

**Code:** `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.java`, `.cpp`, `.c`, `.go`, `.rs`, `.rb`, `.php`, `.swift`, `.kt`

**Document:** `.md`, `.txt`, `.rst`, `.adoc`, `.tex`, `.pdf`, `.docx`

**Data:** `.json`, `.yaml`, `.yml`, `.xml`, `.csv`, `.tsv`, `.toml`, `.ini`, `.env`

**Image:** `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp`, `.bmp`, `.ico`

## Position Calculation

**With parent chat:**
- Offset: `(x + 3 + index*2, y - 2 - row*2, z)`
- Creates cluster around parent
- Max 3 per row

**Without parent:**
- Position: `(100 + index*5, -50 - row*5, 0)`
- Artifact cluster area (bottom-right)

## Staging.json Link Format

**New format:**
```json
{
  "artifacts": {
    "art_1": {
      "filename": "config.py",
      "source_message_id": "msg_123",
      "source_chat_id": "chat_abc",
      "status": "done"
    }
  }
}
```

**Old format:**
```json
{
  "items": [
    {
      "filename": "config.py",
      "source_message_id": "msg_123",
      "group_id": "group_xyz",
      "status": "done"
    }
  ]
}
```

## API Response

```python
# GET /api/tree/data response
{
  "tree": {...},
  "chat_nodes": [...],
  "chat_edges": [...],
  "artifact_nodes": [...],  # NEW: Phase 108.3
  "artifact_edges": [...]   # NEW: Phase 108.3
}
```

## Test Command

```bash
python test_artifact_scan.py
```

## Common Operations

**Count artifacts by type:**
```python
type_counts = {}
for artifact in artifact_nodes:
    art_type = artifact['metadata']['artifact_type']
    type_counts[art_type] = type_counts.get(art_type, 0) + 1
```

**Find artifacts by chat:**
```python
chat_artifacts = [
    a for a in artifact_nodes
    if a['parent_id'] == f"chat_{chat_id}"
]
```

**Get orphaned artifacts (no parent):**
```python
orphaned = [a for a in artifact_nodes if a['parent_id'] is None]
```

**Filter by type:**
```python
code_artifacts = [
    a for a in artifact_nodes
    if a['metadata']['artifact_type'] == 'code'
]
```

## Error Handling

All scanner functions are wrapped in try/except blocks:

```python
try:
    artifact_nodes = scan_artifacts()
except Exception as e:
    print(f"[ARTIFACT_SCAN] Error: {e}")
    artifact_nodes = []  # Fallback to empty list
```

## Performance

- **Scan time:** ~10ms for 25 artifacts
- **Memory:** ~1KB per artifact node
- **Disk I/O:** Single read of staging.json + stat() per artifact

## Debugging

Enable debug output:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Look for:
- `[ARTIFACT_SCAN] Loaded N staging links`
- `[ARTIFACT_SCAN] Scanned N artifacts from data/artifacts`
- `[ARTIFACT_SCAN] Built N artifact nodes, N artifact edges`
- `[ARTIFACT_SCAN] Updated positions for N artifacts`

## Integration Checklist

- ✅ Import scanner functions
- ✅ Call `scan_artifacts()` after chat nodes
- ✅ Call `update_artifact_positions()` with chat_nodes
- ✅ Call `build_artifact_edges()` with both node lists
- ✅ Add to API response: `artifact_nodes`, `artifact_edges`
- ✅ Handle errors gracefully (empty lists on failure)

## Files

**Scanner:** `src/services/artifact_scanner.py`
**Integration:** `src/api/routes/tree_routes.py`
**Test:** `test_artifact_scan.py`
**Data:** `data/artifacts/` (scanned directory)
**Links:** `data/staging.json` (artifact metadata)
