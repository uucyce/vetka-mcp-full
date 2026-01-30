# Phase 17.6: Sugiyama-Only Coordinate System

**Date:** December 25, 2025
**Status:** IMPLEMENTED
**Previous Phase:** 17.5 - Mode Toggle (COMPLETE)

---

## Problem Statement

The codebase mixed multiple coordinate systems:

1. **Sugiyama positions** - Calculated in JS frontend
2. **Backend layout_hint** - `visual_hints.layout_hint.expected_x/y` from Python
3. **semantic_position** - Blend target from API
4. **y_time / y_semantic** - Legacy Y-blend values

This mixing caused:
- Files appearing in wrong places
- Coordinate mismatch between modes
- Complex, hard-to-debug positioning logic

---

## Solution: Single Source of Truth

### Directory Mode
- Uses Sugiyama layout (calculated in buildTree)
- Positions cached in `directoryPositions`

### Knowledge Mode
- Positions come from `/api/tree/knowledge-graph` endpoint
- Stored in `knowledgePositions`

### No Mixing
- `switchToDirectoryMode()` uses ONLY `directoryPositions`
- `switchToKnowledgeMode()` uses ONLY `knowledgePositions`

---

## Changes Made

### Removed Backend Layout Hints

**Before:**
```javascript
if (useSugiyama) {
    // Sugiyama coords
} else {
    const hint = file.visual_hints?.layout_hint;
    if (hint) {
        x = hint.expected_x + treeOffset;  // MIXED!
    }
}
```

**After:**
```javascript
// Always Sugiyama for Directory Mode
if (sugiyamaPositions && sugiyamaPositions[file.id]) {
    const sp = sugiyamaPositions[file.id];
    x = sp.x + treeOffset;
    y = sp.y;
}
```

### Removed Blend Values

**Before:**
```javascript
nodeObjects.set(file.id, {
    mesh: card,
    data: file,
    type: 'leaf',
    position: position,
    y_time: y_time,           // REMOVED
    y_semantic: y_semantic,   // REMOVED
    semanticPosition: file.semantic_position  // REMOVED
});
```

**After:**
```javascript
nodeObjects.set(file.id, {
    mesh: card,
    data: file,
    type: 'leaf',
    position: position
});
```

### Simplified Card Creation

**Before:**
```javascript
card.userData.y_time = y_time || position.y;
card.userData.y_semantic = y_semantic || position.y;
card.userData.isKGNode = true;

if (file.semantic_position) {
    card.userData.semanticPosition = { ... };
    card.userData.directoryPosition = { ... };
}
```

**After:**
```javascript
card.userData.directoryPosition = {
    x: position.x,
    y: position.y,
    z: position.z || 0
};
```

---

## Dead Code Identified

These functions are now unused (legacy blend logic):
- `updateSemanticBlend(value)`
- `updateYBlend(value)`
- `updateStemsForSemanticBlend()`
- `updateEdgeOpacityForSemanticBlend()`

Consider removing in a future cleanup phase.

---

## New Architecture

```
Directory Mode                    Knowledge Mode
    │                                   │
    ▼                                   ▼
Sugiyama Layout               /api/tree/knowledge-graph
    │                                   │
    ▼                                   ▼
sugiyamaPositions                knowledgePositions
    │                                   │
    └──────────► Mode Toggle ◄──────────┘
                    │
                    ▼
              Single Position
              Applied to Mesh
```

---

## Files Modified

| File | Changes |
|------|---------|
| `src/visualizer/tree_renderer.py` | Removed layout_hint, y_time, y_semantic, semantic_position |

---

## Testing Checklist

```
[ ] Files appear at correct Sugiyama positions on load
[ ] No console errors about missing layout_hint
[ ] Mode toggle still works (Directory ↔ Knowledge)
[ ] Reset View returns files to Sugiyama positions
[ ] No coordinate drift between mode switches
```

---

*Implemented: December 25, 2025*
*Author: Claude Opus 4.5*
