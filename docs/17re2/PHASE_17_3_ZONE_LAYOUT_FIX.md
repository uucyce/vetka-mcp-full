# Phase 17.3: CRITICAL FIX - Zone-Based Layout

**Date:** December 25, 2025
**Status:** IMPLEMENTED
**Previous Phase:** 17.2 - Prerequisite Chain Layout (COMPLETE)

---

## Problem Statement

Phase 17.1/17.2 had critical issues:

1. **Files collapsed to a single point** - All files flew to Y=0 instead of staying in zones
2. **Tags at Y=0** - Tags were placed at fixed positions instead of folder positions
3. **Green spider web** - Prerequisite edges rendered as separate green lines
4. **Reset broken** - Reset View didn't restore directory positions
5. **Cross-tree connections** - Multiple trees (VETKA + Reels) weren't kept separate

---

## Solution: Zone-Based Layout

### Key Principle: Tags REPLACE Folders

```
Directory Mode:                 Knowledge Mode:
/src/api (X=-100, Y=300)  ->   "API" tag (X=-100, Y=300)
/src     (X=0, Y=200)     ->   "Backend" tag (X=0, Y=200)

Tags appear AT FOLDER POSITIONS, not at origin!
```

### Key Principle: Files Stay in Zones

```
Directory Mode:                 Knowledge Mode:
file under /src/api       ->   file near "API" tag
                                 Y = TAG_Y + (knowledge_level * 400)
                                 X = same zone (+/- 50px from tag X)

Files DO NOT fly across the screen!
Files grow UPWARD from their parent tag!
```

---

## Implementation Changes

### Backend (`src/layout/knowledge_layout.py`)

**Before (WRONG):**
```python
TAG_BASE_Y = 150  # Fixed Y for all tags
for tag in tags:
    angle = (i / num_tags) * 360
    x = sin(angle) * TAG_RADIUS
    # All tags at same Y, spread in circle at origin
```

**After (CORRECT):**
```python
def calculate_knowledge_positions(tags, knowledge_levels, edges,
                                   file_directory_positions=None):
    # Tags inherit positions from file centroids!
    for tag_id, tag in tags.items():
        # Calculate centroid of files in this tag
        for file_id in tag.files:
            if file_id in file_dir_pos:
                file_x_sum += pos.x
                file_y_sum += pos.y

        # TAG at centroid of its files
        tag_x = file_x_sum / count
        tag_y = file_y_sum / count

    # Files: Y = tag_Y + knowledge_level * 400
    # Files: X stays near directory position
```

### Frontend (`src/visualizer/tree_renderer.py`)

**1. Send file positions to API:**
```javascript
async function loadKnowledgeGraph() {
    cacheDirectoryPositions();

    const filePositions = {};
    Object.entries(directoryPositions).forEach(([nodeId, pos]) => {
        filePositions[nodeId] = { x: pos.x, y: pos.y, z: pos.z };
    });

    const response = await fetch('/api/tree/knowledge-graph', {
        method: 'POST',
        body: JSON.stringify({ file_positions: filePositions })
    });
}
```

**2. Disable green spider web:**
```javascript
function updatePrerequisiteEdges(t) {
    // DISABLED - No green spider web!
    // Chains are shown via STEMS, not separate lines.
    prerequisiteLines.forEach(line => scene.remove(line));
    prerequisiteLines = [];
}
```

**3. Reset View restores directory positions:**
```javascript
function resetToDirectoryMode() {
    yBlendValue = 0;

    // Restore all file positions
    Object.entries(directoryPositions).forEach(([nodeId, dirPos]) => {
        const nodeInfo = nodeObjects.get(nodeId);
        if (nodeInfo?.mesh) {
            nodeInfo.mesh.position.set(dirPos.x, dirPos.y, dirPos.z);
        }
    });

    // Hide tags, show folders
    tagMeshes.forEach(group => group.visible = false);
    // ... restore folder visibility ...
}
```

---

## API Changes

### POST `/api/tree/knowledge-graph`

**New Request Body:**
```json
{
  "file_positions": {
    "file_123": {"x": -100, "y": 350, "z": 0},
    "file_456": {"x": -80, "y": 280, "z": 0}
  },
  "force_refresh": true
}
```

Backend uses `file_positions` to:
1. Calculate tag positions as centroids of their files
2. Position files relative to their tag (Y = tag_Y + kl * 400)

---

## Layout Constants

```python
KL_HEIGHT_RANGE = 400   # Files grow up to 400px above tag
FILE_SPREAD_X = 50      # +/- 50px horizontal spread from tag
```

---

## Visual Result

### At 0% (Directory Mode):
```
      /src
       |
    /src/api
    /  |  \
  file1 file2 file3

Files under folders, normal tree structure.
```

### At 100% (Knowledge Mode):
```
    file3 (KL=0.9)
      |
    file2 (KL=0.5)
      |
    file1 (KL=0.2)
      |
    [API] tag (at folder position)

Files form chains, growing UPWARD from tags.
Tags appear WHERE folders were.
```

---

## Testing Checklist

```
[ ] Slider 0% -> 3%: Files move SLIGHTLY (not collapse!)
[ ] Slider 50%: Files animate smoothly to new positions
[ ] Slider 100%:
    [ ] Tags visible at FOLDER positions (not Y=0)
    [ ] Files ABOVE their tags (Y = tag_Y + kl * 400)
    [ ] Files near their directory X position
    [ ] NO green spider web
    [ ] Stems show chains (blue lines from file to file)
[ ] Reset View:
    [ ] Slider returns to 0%
    [ ] Files return to directory positions
    [ ] Tags hidden
    [ ] Folders visible
[ ] Two separate trees remain separate
```

---

## Files Modified

| File | Changes |
|------|---------|
| `src/layout/knowledge_layout.py` | Tag positions from file centroids, files stay in zones |
| `src/server/routes/tree_routes.py` | Accept `file_positions` from frontend |
| `src/visualizer/tree_renderer.py` | Send positions, disable spider web, reset fix |

---

*Implemented: December 25, 2025*
*Author: Claude Opus 4.5*
