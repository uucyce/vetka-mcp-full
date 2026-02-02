# Phase 108.3: Artifact Scanning Implementation

**Status:** ✅ Complete
**Date:** 2026-02-02
**Marker:** `MARKER_108_3_ARTIFACT_SCAN`

## Overview

Phase 108.3 implements artifact scanning from the `data/artifacts/` directory, allowing artifacts to appear as nodes in the 3D VETKA tree visualization. Artifacts are linked to their source chats via `staging.json` metadata.

## Files Created

### 1. `src/services/artifact_scanner.py` (NEW)

Main artifact scanning service with the following functions:

#### Core Functions

- **`scan_artifacts() -> List[Dict]`**
  - Scans `data/artifacts/` directory
  - Parses artifact metadata (filename, type, size, timestamps)
  - Links to source chat via `staging.json` (source_message_id, source_chat_id)
  - Returns list of artifact node dictionaries

- **`build_artifact_edges(artifact_nodes, chat_nodes) -> List[Dict]`**
  - Builds edges from chat nodes to artifact nodes
  - Only creates edges where parent_id exists and matches a chat node
  - Returns list of edge dictionaries

- **`update_artifact_positions(artifact_nodes, chat_nodes) -> None`**
  - Updates artifact positions based on parent chat node positions
  - Offsets artifacts from parent chat in a cluster pattern
  - Modifies artifact_nodes in-place

#### Helper Functions

- `_load_staging_links()`: Loads staging.json metadata
- `_get_artifact_type_and_language(file_path)`: Determines artifact type from extension
- `_generate_artifact_id(filename)`: Generates stable artifact ID
- `_calculate_artifact_position(parent_position, index)`: Calculates artifact position

### 2. Test Files

- **`test_artifact_scan.py`** (NEW): Test script for artifact scanner
- **`data/artifact_sample_node.json`** (Generated): Sample artifact node JSON

## Files Modified

### 1. `src/api/routes/tree_routes.py`

**Changes:**

1. **Header Documentation Updated:**
   - Updated `@phase` to Phase 108.3
   - Updated `@lastAudit` to 2026-02-02
   - Added Phase 108.3 to phase history

2. **New Step 4.7: Artifact Scanning** (after chat nodes, before response):
   ```python
   # STEP 4.7: Build artifact nodes and edges
   # MARKER_108_3_ARTIFACT_SCAN: Phase 108.3 - Artifact nodes in tree API
   artifact_nodes = []
   artifact_edges = []

   try:
       from src.services.artifact_scanner import (
           scan_artifacts,
           build_artifact_edges,
           update_artifact_positions
       )

       # Scan artifacts directory
       artifact_nodes = scan_artifacts()

       # Update artifact positions based on parent chat positions
       update_artifact_positions(artifact_nodes, chat_nodes)

       # Build edges from chats to artifacts
       artifact_edges = build_artifact_edges(artifact_nodes, chat_nodes)

       print(f"[ARTIFACT_SCAN] Built {len(artifact_nodes)} artifact nodes, {len(artifact_edges)} artifact edges")

   except Exception as artifact_err:
       print(f"[ARTIFACT_SCAN] Warning: Could not build artifact nodes: {artifact_err}")
       import traceback
       traceback.print_exc()
   ```

3. **Response Updated:**
   ```python
   response = {
       'format': 'vetka-v1.4',
       'source': 'qdrant',
       'mode': mode,
       'tree': {
           'id': root_id,
           'name': 'VETKA',
           'nodes': nodes,
           'edges': edges,
           ...
       },
       'chat_nodes': chat_nodes,
       'chat_edges': chat_edges,
       # NEW: Phase 108.3
       'artifact_nodes': artifact_nodes,
       'artifact_edges': artifact_edges
   }
   ```

## Artifact Node Structure

```python
{
    "id": "artifact_c9e6f153",
    "type": "artifact",
    "name": "config.py",
    "parent_id": "chat_{source_chat_id}",  # Link to source chat
    "metadata": {
        "file_path": "data/artifacts/config_20260202.py",
        "artifact_type": "code",  # code, document, data, image
        "language": "python",
        "size_bytes": 1234,
        "created_at": "2026-02-02T10:30:00Z",
        "modified_at": "2026-02-02T10:35:00Z",
        "source_message_id": "msg_xxx",  # From staging.json
        "source_chat_id": "chat_xxx",    # From staging.json
        "status": "done",  # done, streaming, error
        "extension": ".py"
    },
    "visual_hints": {
        "layout_hint": {
            "expected_x": 120,
            "expected_y": 300,
            "expected_z": 0
        },
        "color": "#10b981",  # Green for code artifacts
        "opacity": 1.0
    }
}
```

## Artifact Types & Colors

| Extension | Type | Language | Color |
|-----------|------|----------|-------|
| `.py`, `.js`, `.ts`, etc. | `code` | `python`, `javascript`, etc. | `#10b981` (green) |
| `.md`, `.txt`, `.pdf`, etc. | `document` | `markdown`, `text`, etc. | `#3b82f6` (blue) |
| `.json`, `.yaml`, `.csv`, etc. | `data` | `json`, `yaml`, etc. | `#f59e0b` (amber) |
| `.png`, `.jpg`, `.svg`, etc. | `image` | `image`, `svg` | `#ec4899` (pink) |

## Artifact Edge Structure

```python
{
    "from": "chat_{source_chat_id}",
    "to": "artifact_c9e6f153",
    "semantics": "artifact",
    "metadata": {
        "type": "artifact",
        "color": "#10b981",  # Matches artifact type color
        "opacity": 0.5
    }
}
```

## Position Strategy

Artifacts are positioned relative to their parent chat nodes:

1. **With Parent Chat:**
   - Offset from parent: `x + (3 + index*2)`, `y - (2 + row*2)`
   - Creates small cluster around parent chat
   - Max 3 artifacts per row

2. **Without Parent:**
   - Bottom-right quadrant: `x=100+index*5`, `y=-50-row*5`
   - Artifact cluster area for orphaned artifacts

## Staging.json Integration

The scanner reads `data/staging.json` to link artifacts to source chats:

### Supported Formats

**New Format (artifacts dict):**
```json
{
  "version": "1.0",
  "artifacts": {
    "art_1": {
      "id": "art_1",
      "filename": "config.py",
      "source_message_id": "msg_123",
      "source_chat_id": "chat_abc",
      "group_id": "group_xyz",
      "status": "done"
    }
  },
  "spawn": {}
}
```

**Old Format (items array):**
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

## Testing

Run the test script:

```bash
python test_artifact_scan.py
```

**Expected Output:**
```
ARTIFACT SCANNER TEST - Phase 108.3
[1] Scanning artifacts directory...
    Found 22 artifacts

[2] Sample artifact nodes:
    Artifact 1:
      ID: artifact_c9e6f153
      Name: QA_1767071710856_fe7ab690.md
      Type: document
      Language: markdown
      Size: 61 bytes
      Parent: None
      Source Chat: None
      Status: done
      Color: #3b82f6
      Position: x=105, y=-50
...

Summary:
  Total artifacts: 22
  Total edges: 0
  Artifact types: 1
```

## API Response Changes

The `/api/tree/data` endpoint now returns:

```json
{
  "format": "vetka-v1.4",
  "source": "qdrant",
  "mode": "directory",
  "tree": {
    "nodes": [...],
    "edges": [...]
  },
  "chat_nodes": [...],
  "chat_edges": [...],
  "artifact_nodes": [
    {
      "id": "artifact_c9e6f153",
      "type": "artifact",
      "name": "config.py",
      ...
    }
  ],
  "artifact_edges": [
    {
      "from": "chat_abc",
      "to": "artifact_c9e6f153",
      "semantics": "artifact",
      ...
    }
  ]
}
```

## Frontend Integration (TODO)

**Next Steps for Frontend:**

1. **useTreeData.ts:**
   - Parse `artifact_nodes` and `artifact_edges` from API response
   - Convert to `TreeNode[]` and `TreeEdge[]`
   - Merge with existing nodes/edges

2. **FileCard.tsx:**
   - Add rendering for `type='artifact'`
   - Show artifact type badge (code/document/data/image)
   - Display artifact status (done/streaming/error)
   - Use artifact type color

3. **TreeEdges.tsx:**
   - Render artifact edges with artifact type color
   - Lower opacity (0.5) for artifact edges
   - Dashed line style for artifact edges

4. **Interaction:**
   - Click artifact → show artifact preview/editor
   - Shift+click → pin artifact
   - Hover → show artifact metadata tooltip

## Statistics

- **Total Artifacts Scanned:** 22
- **Artifact Types:** 1 (document)
- **Linked Artifacts:** 0 (no staging.json links yet)
- **Orphaned Artifacts:** 22 (placed in artifact cluster area)

## Markers

All changes are marked with: `MARKER_108_3_ARTIFACT_SCAN`

**File Markers:**
- `src/services/artifact_scanner.py` (header)
- `src/api/routes/tree_routes.py` (Step 4.7, response)

## Related Phases

- **Phase 108.2:** Chat node visualization (parent feature)
- **Phase 108.4:** Artifact editor/preview (planned)
- **Phase 108.5:** Artifact status streaming (planned)

## Success Criteria

- ✅ Artifact scanner service created
- ✅ Artifact nodes returned in `/api/tree/data`
- ✅ Artifact edges created for linked artifacts
- ✅ Position calculation based on parent chat
- ✅ Test script verifies functionality
- ✅ Documentation complete

## Next Steps

1. Update `staging.json` format to include artifact metadata
2. Implement frontend rendering for artifact nodes
3. Add artifact preview/editor modal
4. Implement artifact status streaming (done → streaming → error)
5. Add artifact search/filter in UI
