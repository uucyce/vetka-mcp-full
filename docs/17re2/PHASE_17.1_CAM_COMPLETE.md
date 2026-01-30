# PHASE 17.1: CAM Operations - COMPLETE

**Date:** 2025-12-24
**Status:** IMPLEMENTED - Surprise metric + visual colors

---

## Executive Summary

Implemented **Constructivist Agentic Memory (CAM)** from NeurIPS 2025 paper:
- File novelty detection via cosine similarity with sibling embeddings
- Surprise metric (0.0-1.0) for each file
- CAM operations: `branch`, `append`, `merge`
- Visual color coding on file card borders

---

## 1. Surprise Metric Calculation

**Formula:**
```
surprise = 1 - cosine_similarity(file_embedding, avg_sibling_embeddings)
```

**Thresholds (per NeurIPS 2025 CAM paper):**
| Surprise Range | Operation | Meaning |
|----------------|-----------|---------|
| > 0.65 | `branch` | Novel content - create new memory branch |
| 0.30 - 0.65 | `append` | Related content - add to existing memory |
| < 0.30 | `merge` | Redundant content - consolidate with existing |

---

## 2. Code Changes

### Backend: `src/orchestration/cam_engine.py`

**Added functions (lines 696-853):**

```python
def calculate_surprise_for_file(
    self,
    file_embedding: np.ndarray,
    sibling_embeddings: List[np.ndarray]
) -> float:
    """
    surprise = 1 - cosine_similarity(file_embedding, avg_sibling_embeddings)
    Returns: 0.0 (identical) to 1.0 (completely novel)
    """
    if file_embedding is None or len(sibling_embeddings) == 0:
        return 0.5  # Neutral surprise

    avg_sibling = np.mean(sibling_embeddings, axis=0)
    # ... cosine similarity calculation ...
    surprise = max(0.0, min(1.0, 1.0 - similarity))
    return surprise

def decide_cam_operation_for_file(self, surprise: float) -> str:
    if surprise > 0.65:
        return 'branch'
    elif surprise > 0.30:
        return 'append'
    else:
        return 'merge'
```

**Standalone function for API integration:**
```python
def calculate_surprise_metrics_for_tree(
    files_by_folder: Dict[str, List[Dict]],
    qdrant_client,
    collection_name: str = "vetka_elisya"
) -> Dict[str, Dict[str, Any]]:
    """
    Returns: Dict mapping file_id -> {surprise_metric, cam_operation}
    """
```

### API: `src/server/routes/tree_routes.py`

**Added import:**
```python
from src.orchestration.cam_engine import calculate_surprise_metrics_for_tree
```

**Added STEP 2.5 (lines 182-196):**
```python
# STEP 2.5: CAM SURPRISE METRICS (Phase 17.1)
cam_metrics = {}
try:
    cam_metrics = calculate_surprise_metrics_for_tree(
        files_by_folder=files_by_folder,
        qdrant_client=qdrant,
        collection_name='vetka_elisya'
    )
    print(f"[CAM] Calculated surprise metrics for {len(cam_metrics)} files")
except Exception as cam_err:
    print(f"[CAM] Warning: Could not calculate surprise metrics: {cam_err}")
```

**Added CAM data to file nodes (lines 326-368):**
```python
# Phase 17.1: Get CAM metrics for this file
file_cam = cam_metrics.get(file_data['id'], {})
surprise_metric = file_cam.get('surprise_metric', 0.5)
cam_operation = file_cam.get('cam_operation', 'append')

nodes.append({
    ...
    'cam': {
        'surprise_metric': surprise_metric,  # 0.0-1.0
        'operation': cam_operation  # 'branch', 'append', 'merge'
    }
})
```

### Frontend: `src/visualizer/tree_renderer.py`

**Added CAM color function (lines 3079-3113):**
```javascript
function getCamBorderColor(node) {
    const cam = node.cam || {};
    const operation = cam.operation || 'append';
    const surprise = cam.surprise_metric || 0.5;

    switch(operation) {
        case 'branch':
            // High surprise = Magenta/Pink (novel content)
            return `rgb(180-255, 50-80, 140-200)`;

        case 'merge':
            // Low surprise = Muted Gray (redundant)
            return `rgb(60-90, 60-90, 70-100)`;

        case 'append':
        default:
            // Normal range = Cyan/Teal
            return `rgb(50-70, 140-180, 160-200)`;
    }
}
```

**Updated all card drawing functions:**
- `drawTextFileCard()` - lines 3142-3145
- `drawSystemFileCard()` - lines 3211-3214
- `drawVideoFileCard()` - lines 3266-3271
- `drawAudioFileCard()` - lines 3308-3311
- `drawImageFileCard()` - lines 3356-3359

---

## 3. Visual Color Scheme

| CAM Operation | Color | RGB Range | Visual |
|---------------|-------|-----------|--------|
| `branch` | Magenta/Pink | (180-255, 50-80, 140-200) | Novel/surprising |
| `append` | Cyan/Teal | (50-70, 140-180, 160-200) | Normal/expected |
| `merge` | Gray | (60-90, 60-90, 70-100) | Redundant |

Colors interpolate based on actual surprise value within each range.

---

## 4. Data Flow

```
1. API Request: GET /api/tree/data
   │
2. Qdrant Query: Fetch all scanned files
   │
3. Build files_by_folder: Group files by parent folder
   │
4. CAM Calculation:
   ├─ For each folder:
   │   ├─ Get all sibling embeddings from Qdrant
   │   ├─ For each file in folder:
   │   │   ├─ Get file embedding
   │   │   ├─ Calculate average sibling embedding
   │   │   ├─ surprise = 1 - cosine_similarity
   │   │   └─ Decide operation based on thresholds
   │   └─ Store {file_id: {surprise_metric, cam_operation}}
   │
5. Build nodes list: Add 'cam' field to each file node
   │
6. API Response: JSON with nodes containing 'cam' data
   │
7. Frontend Rendering:
   ├─ getCamBorderColor(node) returns color
   └─ File cards drawn with colored borders
```

---

## 5. Console Output (Expected)

```
[CAM] Calculated surprise metrics for 213 files
[API] Tree built: 242 nodes, 241 edges (structural only)
```

---

## 6. Testing Verification

```bash
# Test imports
python -c "from src.orchestration.cam_engine import calculate_surprise_metrics_for_tree; print('OK')"
python -c "from src.server.routes.tree_routes import bp; print('OK')"

# Both pass without errors
```

---

## 7. Files Modified

| File | Lines | Change |
|------|-------|--------|
| `src/orchestration/cam_engine.py` | 696-853 | Added surprise metric functions |
| `src/server/routes/tree_routes.py` | 25, 182-196, 326-368 | CAM integration |
| `src/visualizer/tree_renderer.py` | 3074-3113, 3142-3145, 3211-3214, 3266-3271, 3308-3311, 3356-3359 | CAM colors |

---

## 8. Graceful Degradation

If CAM calculation fails (Qdrant error, missing embeddings):
- Warning logged to console
- Files default to `surprise_metric: 0.5`, `operation: 'append'`
- Visualization continues with cyan/teal borders
- No crash, no broken UI

---

## 9. Future Extensions

1. **CAM Legend** - Add legend showing color meanings
2. **Hover Tooltip** - Show exact surprise value on hover
3. **Filter by CAM** - Filter tree to show only `branch` files
4. **CAM Timeline** - Track how surprise changes over time
5. **Auto-organize** - Suggest folder reorganization based on CAM

---

*Completed: 2025-12-24*
*Author: Claude Opus 4.5*
