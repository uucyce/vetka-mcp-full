# EDGE BINDING ANALYSIS

**Date:** 2025-12-24
**Status:** YES - Edges are ALREADY DYNAMIC!

---

## Executive Summary

**EDGES ARE DYNAMICALLY BOUND TO NODE IDs, NOT POSITIONS.**

The VETKA visualization already has full dynamic edge binding:
1. Edges stored as `(from_node_id, to_node_id)` pairs
2. Edge positions recalculated on Y-blend slider change
3. Function `updateEdgeGeometry()` rebuilds curves each time

**Grok research NOT NEEDED for edge binding.**

---

## 1. Current Edge Structure (from API)

```bash
curl 'http://localhost:5001/api/tree/data?mode=directory' | jq '.tree.edges[0:5]'
```

**Result:**
```json
[
  {"from": "main_tree_root", "semantics": "contains", "to": "folder_68947568"},
  {"from": "folder_68947568", "semantics": "contains", "to": "folder_56895548"},
  {"from": "folder_56895548", "semantics": "contains", "to": "folder_34630634"},
  {"from": "folder_34630634", "semantics": "contains", "to": "folder_39009684"},
  {"from": "folder_39009684", "semantics": "contains", "to": "folder_73273315"}
]
```

**Analysis:**
- Edges contain `from` and `to` as **node IDs** (strings)
- NO position data stored in edges
- Semantics field indicates relationship type (`contains`, `similar_to`, `depends_on`)

---

## 2. How Edges Are Created (Layout Code)

**File:** `src/layout/fan_layout.py`

The layout code **does NOT create edges** - it only calculates positions.

Edges come from:
1. **Directory hierarchy:** `contains` edges from parent folder to children
2. **Semantic relationships:** `similar_to`, `depends_on` from vector similarity (Qdrant)

**Layout only provides:**
```python
positions[node_id] = {
    'x': folder_x,
    'y': folder_y,
    'angle': parent_angle
}
```

Edges are constructed from the folder hierarchy (`parent_path` relationships) in `main.py` or API layer, NOT in `fan_layout.py`.

---

## 3. How Edges Are Rendered (Frontend)

**File:** `src/visualizer/tree_renderer.py`

### Edge Creation (Lines 2973-2994):
```javascript
semanticEdges.forEach(edge => {
    const fromInfo = nodeObjects.get(edge.from);
    const toInfo = nodeObjects.get(edge.to);

    if (fromInfo?.mesh && toInfo?.mesh) {
        const fromPos = fromInfo.mesh.position;  // DYNAMIC lookup!
        const toPos = toInfo.mesh.position;      // DYNAMIC lookup!

        // ... safety checks ...

        const edgeLine = createSemanticEdge(fromPos, toPos, color, edge.weight, edge.from, edge.to);
        edgeLine.userData = { source: edge.from, target: edge.to };  // Store IDs!
        scene.add(edgeLine);
        semanticEdgeMeshes.push(edgeLine);
    }
});
```

### Dynamic Update (Lines 6039-6071):
```javascript
function updateEdgeGeometry(edge) {
    if (!edge.userData || !edge.userData.source || !edge.userData.target) return;

    const sourceInfo = nodeObjects.get(String(edge.userData.source));  // ID lookup
    const targetInfo = nodeObjects.get(String(edge.userData.target));  // ID lookup

    if (sourceInfo?.mesh && targetInfo?.mesh) {
        const fromPos = sourceInfo.mesh.position;  // Current position
        const toPos = targetInfo.mesh.position;    // Current position

        // Rebuild Bezier curve with new positions
        const curve = new THREE.QuadraticBezierCurve3(
            fromPos.clone(),
            midPoint,
            toPos.clone()
        );
        const points = curve.getPoints(20);
        edge.geometry.setFromPoints(points);  // Update geometry!
    }
}
```

### Called When:
```javascript
// Lines 6074-6077
knowledgeGraphEdges.forEach(updateEdgeGeometry);
semanticEdgeMeshes.forEach(updateEdgeGeometry);
```

This is triggered by the Y-blend slider (`updateYBlend(value)`).

---

## 4. Can Edges Be Dynamic?

### Answer: **YES - ALREADY IMPLEMENTED!**

| Requirement | Status |
|-------------|--------|
| Edges stored as (from_id, to_id) | **YES** - `edge.from`, `edge.to` |
| Edge positions recalculated each frame | **YES** - `updateEdgeGeometry()` |
| Edges switch source between modes | **PARTIAL** - Needs mode switching |

### Currently Working:
1. Y-blend slider moves nodes
2. `updateEdgeGeometry()` is called
3. Edges are rebuilt with new node positions
4. Both `knowledgeGraphEdges` and `semanticEdgeMeshes` are updated

### What's Missing for Full Dynamic Switching:
- **Mode switching** (Directory -> Knowledge -> Time) doesn't rebuild edges
- Need to call `updateEdgeGeometry()` when mode changes
- Or better: animate edges during mode transition

---

## 5. What Needs to Change?

### Option A: Nothing (Current System Works)
If nodes stay the same and only Y positions change:
- Already works via Y-blend slider
- No changes needed

### Option B: Mode Transition Animation
If switching between Directory/Knowledge/Time modes:
```javascript
function animateModeTransition(fromMode, toMode, duration = 1000) {
    // 1. Get new positions from API for target mode
    // 2. Animate node positions
    // 3. Call updateEdgeGeometry() each frame during animation
}
```

**Estimate:** Easy fix (add animation loop calling existing function)

### Option C: Edge Source Switching
If edge sources change between modes (folder -> tag):
```javascript
// Edges need new from/to IDs
// Requires rebuilding edge list, not just updating positions
```

**Estimate:** Medium (needs edge regeneration logic)

---

## 6. Diagram: Current Edge Flow

```
API Response:
edges: [{ from: "folder_A", to: "file_1" }, ...]

                    ↓

Frontend Creates Edges:
for each edge:
    fromMesh = nodeObjects.get(edge.from)  ← ID lookup
    toMesh = nodeObjects.get(edge.to)      ← ID lookup
    line = createLine(fromMesh.position, toMesh.position)
    line.userData = { source: edge.from, target: edge.to }

                    ↓

Y-Blend Slider Changes:
updateYBlend(value):
    1. Update node Y positions
    2. semanticEdgeMeshes.forEach(updateEdgeGeometry)
       → Each edge looks up source/target by ID
       → Gets CURRENT mesh.position
       → Rebuilds curve geometry

                    ↓

Edges Follow Nodes Automatically!
```

---

## 7. Conclusion

**DYNAMIC EDGE BINDING: ALREADY WORKING**

| Question | Answer |
|----------|--------|
| Are edges stored as (from_id, to_id)? | **YES** |
| Are edge positions recalculated each frame? | **YES** (on slider change) |
| Can edges switch source? | **Partially** (same IDs, different Y) |
| What needs to change? | **Nothing for Phase 17.1 (CAM)** |
| Grok research needed? | **NO** |

**Proceed directly to Phase 17.1** - the edge binding infrastructure is already in place.

---

## Appendix: Key Code Locations

| Component | File | Lines |
|-----------|------|-------|
| Edge creation | `tree_renderer.py` | 2973-2994 |
| Edge update function | `tree_renderer.py` | 6039-6071 |
| Y-blend trigger | `tree_renderer.py` | 6014-6080 |
| Edge storage | `semanticEdgeMeshes[]` | Line 1366 |
| Node ID storage | `edge.userData.source/target` | Line 3038 |

---

*Generated: 2025-12-24*
*Auditor: Claude Opus 4.5*
