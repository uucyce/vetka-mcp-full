# PHASE 17.2: Multi-Tree Knowledge Graph - COMPLETE

**Date:** 2025-12-24
**Status:** IMPLEMENTED - Semantic DAG + Blend Slider + Procrustes Alignment

---

## Executive Summary

Transformed VETKA from single-tree (directory) to **multi-tree Knowledge Graph** with:
1. **Semantic DAG** built from embeddings + clustering
2. **Procrustes-aligned blending** between directory ↔ semantic layouts
3. **LOD system** with camera-based detail levels
4. **Real-time blend slider** (0% directory → 100% semantic)

---

## 1. Architecture Overview

```
Phase 17.1 (Previous):
├─ Single tree (directory)
├─ Y = depth (folder hierarchy)
└─ CAM operations (surprise metric)

Phase 17.2 (New):
├─ TWO independent layouts
│  ├─ Directory Layout (fan spread from root)
│  │  └─ Y = depth, X = fan angle, Z = file stack
│  │
│  └─ Semantic Layout (knowledge clusters)
│     └─ Y = knowledge_level, X = cluster, Z = sibling offset
│
├─ API returns both layouts (?mode=both)
├─ Procrustes alignment (frontend)
├─ Real-time blend slider (0-100%)
└─ LOD system (auto/cluster/dot/icon/full)
```

---

## 2. Files Created

### 2.1 `src/orchestration/semantic_dag_builder.py` (NEW)

**Classes:**
- `SemanticNode` - Dataclass for concept/file nodes
- `SemanticEdge` - Dataclass for edges (prerequisite, similarity, contains)
- `SemanticDAGBuilder` - Main builder class

**Key Methods:**
```python
def build_semantic_tree(self) -> Tuple[Dict[str, SemanticNode], List[SemanticEdge]]:
    """
    Full pipeline:
    1. Cluster embeddings (HDBSCAN or KMeans fallback)
    2. Create concept nodes (cluster centroids)
    3. Create file leaf nodes
    4. Calculate knowledge levels (hub score)
    5. Infer prerequisite edges (similarity + direction)
    """

def build_semantic_dag_from_qdrant(qdrant_client, collection_name, min_cluster_size):
    """Convenience function: fetch embeddings and build DAG in one call"""
```

**Clustering Strategy:**
- Primary: HDBSCAN (variable cluster sizes, handles noise)
- Fallback: KMeans (when sklearn HDBSCAN unavailable)
- Cosine similarity via normalized embeddings

### 2.2 `src/layout/semantic_sugiyama.py` (NEW)

**Functions:**
```python
def calculate_semantic_sugiyama_layout(nodes, edges, max_y, x_spread, z_offset):
    """
    Sugiyama layout for semantic tree:
    - Phase 1: Layer assignment (Y by knowledge_level, 0-10 buckets)
    - Phase 2: Order within layers (topological sort)
    - Phase 3: Position nodes (X spread, Z offset)
    - Phase 4: Soft repulsion (avoid overlap)
    """

def calculate_semantic_positions_for_files(semantic_nodes, semantic_edges, file_ids, max_y):
    """Map file positions based on parent concept positions"""
```

---

## 3. Files Modified

### 3.1 `src/server/routes/tree_routes.py`

**Changes:**

1. **New imports (lines 27-29):**
```python
from src.orchestration.semantic_dag_builder import build_semantic_dag_from_qdrant
from src.layout.semantic_sugiyama import calculate_semantic_positions_for_files
```

2. **Semantic cache (lines 35-41):**
```python
_semantic_cache = {
    'nodes': None,
    'edges': None,
    'positions': None,
    'stats': None
}
```

3. **Mode parameter (line 90):**
```python
mode = request.args.get('mode', 'directory')  # 'directory', 'semantic', 'both'
```

4. **STEP 6: Semantic Layout (lines 398-469):**
- Build/cache semantic DAG from Qdrant embeddings
- Calculate semantic positions for file nodes
- Build semantic_data for response

5. **STEP 7: Response with both layouts (lines 471-527):**
- Add `semantic_position` to each file node
- Include `layouts: {directory: {...}, semantic: {...}}`
- Include `semantic_data: {nodes, edges, stats}`

### 3.2 `src/visualizer/tree_renderer.py`

**Changes:**

1. **CSS for semantic blend panel (lines 274-324):**
```css
#semantic-blend-panel { position: fixed; right: 20px; ... }
#semantic-blend-slider { background: linear-gradient(to right, #8B4513, #9A4A8B); ... }
```

2. **HTML for blend slider (lines 893-900):**
```html
<div id="semantic-blend-panel">
    <span class="label label-top">Semantic</span>
    <input type="range" id="semantic-blend-slider" min="0" max="100" value="0"
           oninput="updateSemanticBlend(this.value)">
    <span class="label">Directory</span>
    <span id="semantic-blend-value">0%</span>
</div>
```

3. **API call with mode=both (line 1328):**
```javascript
const response = await fetch('/api/tree/data?mode=both');
```

4. **Store semantic positions on file cards (lines 2897-2910):**
```javascript
if (file.semantic_position) {
    card.userData.semanticPosition = { x, y, z, knowledge_level };
    card.userData.directoryPosition = { x, y, z };
}
```

5. **Semantic blend function (lines 6149-6314):**
```javascript
function updateSemanticBlend(value) {
    // Interpolate positions between directory and semantic
    nodeObjects.forEach((info, nodeId) => {
        const dirPos = userData.directoryPosition;
        const semPos = userData.semanticPosition;
        mesh.position.set(
            dirPos.x + (semPos.x - dirPos.x) * eased,
            dirPos.y + (semPos.y - dirPos.y) * eased,
            dirPos.z + (semPos.z - dirPos.z) * eased
        );
    });
}

function alignSemanticToDirectory(dirPositions, semPositions) {
    // Simplified Procrustes: translate + scale to match centroids
}
```

---

## 4. API Response Format

### Request: `GET /api/tree/data?mode=both`

### Response:
```json
{
  "format": "vetka-v1.4",
  "source": "qdrant",
  "mode": "both",
  "tree": {
    "nodes": [
      {
        "id": "file_123",
        "type": "leaf",
        "name": "example.py",
        "visual_hints": { "layout_hint": { "expected_x": 100, "expected_y": 50 } },
        "semantic_position": { "x": 200, "y": 300, "z": 0, "knowledge_level": 0.7 },
        "cam": { "surprise_metric": 0.45, "operation": "append" }
      }
    ],
    "edges": [...]
  },
  "layouts": {
    "directory": { "file_123": { "x": 100, "y": 50, "z": 0 }, ... },
    "semantic": { "file_123": { "x": 200, "y": 300, "z": 0 }, ... }
  },
  "semantic_data": {
    "nodes": [
      { "id": "concept_0", "type": "concept", "label": "Topic_0", "knowledge_level": 0.3, "children": [...] }
    ],
    "edges": [
      { "source": "concept_0", "target": "file_123", "type": "contains", "weight": 1.0 }
    ],
    "stats": { "total_nodes": 50, "concept_count": 5, "file_count": 45, ... }
  }
}
```

---

## 5. Blend Slider Behavior

| Slider Value | Visualization |
|--------------|---------------|
| 0% | Directory layout (fan from root) |
| 25% | Nodes start moving toward semantic positions |
| 50% | Midpoint transition |
| 75% | Nodes mostly in semantic positions |
| 100% | Full semantic layout (knowledge clusters) |

**Animation Features:**
- Eased transitions (easeOutQuad)
- Stems follow file cards dynamically
- Edge opacity fades (directory→semantic)

---

## 6. Knowledge Level Calculation

```python
# Hub score = out_degree / (in_degree + out_degree)
# Knowledge level = hub_score (0.0 = foundational, 1.0 = advanced)

# If no edges, use embedding complexity:
complexity = np.linalg.norm(node.embedding) / 100
node.knowledge_level = clamp(complexity, 0.1, 0.9)
```

---

## 7. Procrustes Alignment

Frontend function `alignSemanticToDirectory()`:
1. Calculate centroids of both layouts
2. Calculate scale factor: `sqrt(dir_variance / sem_variance)`
3. Apply transformation: translate + scale semantic to match directory bounds

This minimizes visual "jump" when switching between layouts.

---

## 8. Testing Results

```bash
# Import tests
python -c "from src.orchestration.semantic_dag_builder import *"  # OK
python -c "from src.layout.semantic_sugiyama import *"  # OK
python -c "from src.server.routes.tree_routes import bp"  # OK

# API test
curl 'http://localhost:5001/api/tree/data?mode=both' | jq '.mode'
# Expected: "both"
```

---

## 9. Integration with Phase 17.1

Phase 17.2 builds on Phase 17.1 (CAM):
- CAM metrics (`surprise_metric`, `cam_operation`) still included in nodes
- Border colors from Phase 17.1 still applied
- Semantic positions added alongside existing data

---

## 10. Files Summary

| File | Status | Lines Changed |
|------|--------|---------------|
| `src/orchestration/semantic_dag_builder.py` | NEW | 280+ lines |
| `src/layout/semantic_sugiyama.py` | NEW | 150+ lines |
| `src/server/routes/tree_routes.py` | MODIFIED | +100 lines (STEP 6, 7) |
| `src/visualizer/tree_renderer.py` | MODIFIED | +200 lines (blend, UI) |

---

## 11. Next Steps (Phase 17.3)

1. **Edge bundling** - Group parallel edges for cleaner visualization
2. **Semantic edge coloring** - Different colors for prerequisite vs contains
3. **Cluster labels** - Show concept names in semantic mode
4. **Animated transitions** - Smoother camera movement during blend

---

*Completed: 2025-12-24*
*Author: Claude Opus 4.5*
