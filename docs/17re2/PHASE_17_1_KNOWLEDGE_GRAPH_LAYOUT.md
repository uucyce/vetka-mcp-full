# Phase 17.1: Knowledge Graph Layout - CORRECTED Implementation

**Date:** December 25, 2025
**Status:** CORRECTED - Critical bugs fixed
**Previous Phase:** 17.0 - Dynamic Stem Binding (COMPLETE)

## Critical Corrections Applied

1. **Tags Y position:** Fixed from Y=0 to Y=150
2. **Files grow UPWARD:** Files now build upward from tags (foundational=near tags, advanced=high)
3. **Tag visuals:** Changed from colored spheres to subtle gray ring + white text
4. **Stem rebinding:** Now properly switches from folder→file to TAG→file at 50%
5. **Knowledge level formula:** Corrected to properly identify foundational vs advanced files

---

## Overview

Phase 17.1 implements a complete overhaul of the Semantic/Knowledge Mode in VETKA's 3D visualization. Files now group by **semantic TAGS** (clusters) instead of flying to a chaotic pile.

### Key Changes

1. **Tag-based clustering** - Files are grouped into semantic clusters using HDBSCAN
2. **New tag nodes** - Visual spheres representing each cluster
3. **Prerequisite edges** - Directed edges showing learning dependencies
4. **Smooth interpolation** - Files animate smoothly between Directory and Knowledge modes
5. **Dynamic stem rebinding** - At 50%+ blend, stems connect to tags instead of folders

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Y-BLEND SLIDER (0% → 100%)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ↓                    ↓                    ↓
    ┌─────────┐         ┌─────────┐         ┌─────────┐
    │  0-30%  │         │ 30-70%  │         │ 70-100% │
    │DIRECTORY│         │ HYBRID  │         │KNOWLEDGE│
    └────┬────┘         └────┬────┘         └────┬────┘
         │                   │                   │
         ↓                   ↓                   ↓
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ NODES: folders  │  │ NODES: folders +│  │ NODES: tags     │
│ EDGES: folder→  │  │       tags      │  │ EDGES: tag→file │
│        file     │  │ EDGES: mixed    │  │        file→file│
│ Y: depth        │  │ Y: interpolated │  │ Y: knowledge_lvl│
│ X: barycenter   │  │ X: interpolated │  │ X: cluster+angle│
│ Z: 0            │  │ Z: interpolated │  │ Z: slight offset│
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Files Modified/Created

### New Files

| File | Purpose |
|------|---------|
| `src/layout/knowledge_layout.py` | Backend: HDBSCAN clustering, edge building, position calculation |

### Modified Files

| File | Changes |
|------|---------|
| `src/server/routes/tree_routes.py` | Added `/api/tree/knowledge-graph` endpoint |
| `src/visualizer/tree_renderer.py` | Added KG globals, `loadKnowledgeGraph()`, `createTagNodes()`, `updateKnowledgeBlend()`, `updatePrerequisiteEdges()` |

---

## API Endpoints

### GET/POST `/api/tree/knowledge-graph`

Returns Knowledge Graph structure for tag-based layout.

**Query Parameters:**
- `force_refresh` (bool): Force recalculation, bypass cache
- `min_cluster_size` (int): Minimum files per cluster (default: 3)
- `similarity_threshold` (float): Minimum similarity for edges (default: 0.7)

**Response:**
```json
{
  "status": "ok",
  "source": "computed",
  "tags": {
    "tag_0": {
      "id": "tag_0",
      "name": "Topic 0",
      "files": ["file_id_1", "file_id_2"],
      "color": "#4CAF50",
      "angle": -60,
      "position": {"x": -86.6, "y": 0, "z": 15}
    }
  },
  "edges": [
    {"source": "file_1", "target": "file_2", "type": "prerequisite", "weight": 0.85}
  ],
  "positions": {
    "tag_0": {"x": -86.6, "y": 0, "z": 15, "angle": -60, "type": "tag"},
    "file_1": {"x": -100, "y": 240, "z": 10, "angle": -55, "type": "file", "knowledge_level": 0.3}
  },
  "knowledge_levels": {
    "file_1": 0.3,
    "file_2": 0.7
  }
}
```

### POST `/api/tree/clear-knowledge-cache`

Clears the Knowledge Graph cache to force recalculation.

---

## Frontend Functions

### `loadKnowledgeGraph()`
Fetches KG data from API, caches directory positions, creates tag nodes.

### `createTagNodes(tags)`
Creates Three.js sphere meshes for each semantic cluster with labels.

### `updateKnowledgeBlend(value)`
Main blend function called by slider:
1. Updates file positions (interpolation)
2. Fades in/out tags and folders
3. Rebinds stems at 50%+ blend
4. Shows/hides prerequisite edges

### `updatePrerequisiteEdges(t)`
Creates/updates prerequisite edge lines between files.

### `interpolatePosition(dirPos, kgPos, t)`
Interpolates position with shortest-path angle handling.

---

## Mathematical Model

### Knowledge Level Calculation

```python
# Based on in/out degree of similarity edges
knowledge_level = 1 - (in_degree / (in_degree + out_degree))

# Low knowledge_level (0.1) = foundational (many files depend on it)
# High knowledge_level (0.9) = advanced (depends on many others)
```

### Y-Axis (Knowledge Mode)
```
Y = knowledge_level * MAX_KL_LAYERS * LAYER_HEIGHT
Y = kl * 10 * 80 = kl * 800  // Range: 0 to 800 pixels
```

### X-Axis (Knowledge Mode)
```
angle = tag_angle + (barycenter_offset * 0.3)
radius = BASE_RADIUS + knowledge_level * 150
X = sin(angle * PI / 180) * radius
```

### Interpolation
```javascript
function interpolatePosition(dirPos, kgPos, t) {
    // Y: linear
    const y = (1 - t) * dirPos.y + t * kgPos.y;

    // Angle: shortest path
    let delta = kgPos.angle - dirPos.angle;
    if (delta > 180) delta -= 360;
    if (delta < -180) delta += 360;
    const angle = dirPos.angle + t * delta;

    // Radius: linear
    const radius = (1 - t) * dirPos.radius + t * kgPos.radius;

    // X from polar
    const x = sin(angle * PI / 180) * radius;

    return { x, y, z };
}
```

---

## Visual Behavior

| Slider Value | Folders | Tags | Stems | Prerequisite Edges |
|-------------|---------|------|-------|-------------------|
| 0% | Visible (100%) | Hidden | Connect to folders | Hidden |
| 30% | Visible (70%) | Fading in | Connect to folders | Hidden |
| 50% | Visible (50%) | Visible (30%) | Transition point | Start appearing |
| 70% | Fading out (30%) | Visible (60%) | Connect to tags | Visible (40%) |
| 100% | Hidden | Visible (90%) | Connect to tags | Visible (100%) |

---

## Testing Checklist

```
[ ] Slider 0% (Directory Mode):
    [ ] Files positioned under folders
    [ ] Stems connect folder -> file
    [ ] No tags visible
    [ ] No prerequisite edges

[ ] Slider 50% (Hybrid):
    [ ] Files animating to new positions
    [ ] Folders fading out (50% opacity)
    [ ] Tags fading in (~30% opacity)
    [ ] Stems still from folders

[ ] Slider 100% (Knowledge Mode):
    [ ] Tags VISIBLE (colored spheres with labels)
    [ ] Folders HIDDEN
    [ ] Files grouped around their tags
    [ ] Stems connect TAG -> file
    [ ] Prerequisite edges visible (green lines)
    [ ] Y = knowledge_level * 800
```

---

## Console Debugging

Expected log output:

```
[KG] Loading Knowledge Graph from API...
[KG] Loaded: { tags: 5, edges: 47, positions: 213, source: computed }
[KG] Cached 213 directory positions
[KG] Created 5 tag nodes
[KG-BLEND] Value: 50 t: 0.50
[KG-BLEND] Updated: 213 files, 213 stems, 5 tags
[KG] Rendered 47 prerequisite edges (opacity: 0.00)
```

---

## Dependencies

- sklearn.cluster.HDBSCAN (optional, falls back to KMeans)
- numpy
- Three.js (frontend)
- Qdrant (for embeddings)

---

## Future Improvements

1. **LLM-based tag naming** - Use AI to generate meaningful cluster names
2. **Interactive tag editing** - Allow users to reassign files to different tags
3. **Hierarchical tags** - Support nested tag structures
4. **Time-based animation** - Animate transition over time instead of instant

---

*Implemented: December 25, 2025*
*Author: Claude Opus 4.5*
