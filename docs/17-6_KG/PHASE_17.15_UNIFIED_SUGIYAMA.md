# PHASE 17.15: UNIFIED SUGIYAMA ENGINE

**Date:** 2025-12-26
**Status:** COMPLETED
**Author:** Claude Opus 4.5

---

## PROBLEM STATEMENT

Previous Knowledge Mode implementations (17.10-17.14) had duplicated positioning logic:
- **Directory Mode:** Used Sugiyama algorithm in `semantic_sugiyama.py`
- **Knowledge Mode:** Had custom positioning logic in `knowledge_layout.py`

This led to:
1. Inconsistent visual behavior between modes
2. Code duplication and maintenance burden
3. Different layout constants and algorithms

**User Requirement:** Treat tags like folders - reuse the SAME Sugiyama engine from Directory Mode.

---

## SOLUTION ARCHITECTURE

### Core Concept: Tags = Folders

Instead of having separate layout engines:
- **Before:** Knowledge Mode had custom tag positioning
- **After:** Knowledge Mode imports and uses Sugiyama functions from `semantic_sugiyama.py`

```
           BEFORE (Duplicated)              AFTER (Unified)
           ─────────────────────           ─────────────────────
Directory  │ semantic_sugiyama.py │   →    │ semantic_sugiyama.py │
Mode       │ (Sugiyama engine)    │        │ (SINGLE ENGINE)      │
           └─────────────────────┘        └─────────────────────┘
                                                    ↓
                                                 imports
                                                    ↓
Knowledge  │ knowledge_layout.py  │   →    │ knowledge_layout.py  │
Mode       │ (Custom positioning) │        │ (Uses Sugiyama)      │
           └─────────────────────┘        └─────────────────────┘
```

---

## IMPLEMENTATION DETAILS

### 1. Import Sugiyama Functions (lines 27-31)

```python
# Phase 17.15: Import Sugiyama engine functions
from src.layout.semantic_sugiyama import (
    calculate_semantic_sugiyama_layout,
    distribute_by_similarity,
    distribute_horizontally
)
```

### 2. Tag Positioning Using Sugiyama-Style Layout

Tags are now positioned using the same principles as Directory Mode folders:

```python
# Group tags by depth (like Sugiyama layers)
layers: Dict[int, List[str]] = {}
for tag_id, tag in tags.items():
    depth = tag.depth
    if depth not in layers:
        layers[depth] = []
    layers[depth].append(tag_id)

# Position tags layer by layer
TAG_Y_BASE = 100
TAG_LAYER_HEIGHT = 250

for depth in sorted(layers.keys()):
    layer_tags = layers[depth]
    y = TAG_Y_BASE + depth * TAG_LAYER_HEIGHT

    # X positioning: use similarity-based distribution from Sugiyama
    x_positions = distribute_by_similarity(layer_tags, tag_embeddings, X_SPREAD)

    for i, tag_id in enumerate(layer_tags):
        tag_positions[tag_id] = {'x': x_positions[i], 'y': y, 'z': 0.0}
```

### 3. File Positioning Using Sugiyama Distribution

Files are distributed below their parent tags using the same similarity-based algorithm:

```python
# Get file embeddings for similarity-based X distribution
file_embeddings = {f: embeddings_dict[f] for f in sorted_files if f in embeddings_dict}

# Calculate X positions using Sugiyama's similarity distribution
x_positions = distribute_by_similarity(sorted_files, file_embeddings, FILE_FAN_SPREAD)

# Position files in grid layout below tag
for i, file_id in enumerate(sorted_files):
    row = i // MAX_FILES_PER_ROW
    y = tag_y + FILE_START_OFFSET + (row * FILE_STEP_Y)
    x = tag_x + x_positions[i]
```

---

## KEY FUNCTIONS REUSED FROM SUGIYAMA

### `distribute_by_similarity()`

Distributes nodes horizontally by embedding similarity using 1D MDS-like projection:
- Similar nodes are placed closer together on X-axis
- Uses cosine similarity to calculate distances
- Projects to principal axis for 1D layout

```python
def distribute_by_similarity(
    node_ids: List[str],
    embeddings: Dict[str, np.ndarray],
    x_spread: float = 800
) -> List[float]:
    """
    Distribute nodes horizontally by embedding similarity.
    Returns: List of X positions (same order as node_ids)
    """
```

### `distribute_horizontally()`

Simple even distribution when embeddings aren't available:

```python
def distribute_horizontally(count: int, x_spread: float) -> List[float]:
    """
    Distribute N nodes evenly across X range [-x_spread/2, x_spread/2]
    """
```

---

## LAYOUT CONSTANTS

```python
# Tag Layout (aligned with Sugiyama)
TAG_Y_BASE = 100           # Y for root tag
TAG_LAYER_HEIGHT = 250     # Vertical spacing between tag depths
X_SPREAD = 800             # X-axis spread for tags

# File Layout
FILE_FAN_SPREAD = 300      # X spread for files under tag
FILE_STEP_Y = 35           # Y step between file rows
FILE_START_OFFSET = 60     # Y offset from tag to first file row
MAX_FILES_PER_ROW = 8      # Max files per row (grid layout)
```

---

## VISUAL RESULT

```
Y=100:                    [Root Tag]
                         /    |    \
                        /     |     \
Y=350:            [Tag A]  [Tag B]  [Tag C]
                     |        |        |
Y=410-480:      [files]   [files]   [files]
                 (grid)    (grid)    (grid)
```

X positions are determined by semantic similarity:
- Tags with similar centroids are placed closer together
- Files within a tag cluster by content similarity

---

## TEST RESULTS

```
============================================================
PHASE 17.15: UNIFIED SUGIYAMA ENGINE TEST
============================================================

📌 TAG POSITIONS:
  tag_0 (Root Topic): X=0.0, Y=100.0, depth=0
  tag_1 (Web APIs): X=-200.0, Y=350.0, depth=1
  tag_2 (Database): X=200.0, Y=350.0, depth=1

📄 FILE POSITIONS:
  file_1: X=-39.9, Y=160.0, tag=tag_0
  file_4: X=-228.7, Y=410.0, tag=tag_1
  file_8: X=125.0, Y=410.0, tag=tag_2

📊 POSITION RANGES:
  Tags X: -200 to 200
  Tags Y: 100 to 350
  Files X: -293 to 275
  Files Y: 160 to 410

✅ VALIDATION:
  Root tag Y = 100.0 (expected ~100) ✓
  Child tag Y = 350.0 (expected ~350) ✓
  Layer gap = 250.0 (expected 250) ✓

✓ Test PASSED!
```

---

## FILES MODIFIED

| File | Changes |
|------|---------|
| `src/layout/knowledge_layout.py` | Added imports from `semantic_sugiyama.py`; Rewrote `calculate_knowledge_positions()` to use Sugiyama-style layout; Added `embeddings_dict` parameter for similarity-based file placement |

---

## BENEFITS

1. **Code Reuse:** No more duplicated positioning logic
2. **Consistency:** Tags behave like folders in both modes
3. **Maintainability:** Single source of truth for layout algorithms
4. **Semantic Layout:** Files cluster by similarity within tags
5. **Predictable Coordinates:** Y = depth × 250, X = similarity-based

---

## COMPARISON: BEFORE vs AFTER

### Before (Phase 17.14 - Custom Logic)
```python
# Custom tag positioning
tag_y = TAG_Y_BASE + depth * TAG_LAYER_HEIGHT
# Custom sibling spread
normalized = (sibling_index / (num_siblings - 1)) - 0.5
x_offset = normalized * TAG_SIBLING_SPREAD
```

### After (Phase 17.15 - Unified Sugiyama)
```python
# Use Sugiyama distribution functions
x_positions = distribute_by_similarity(layer_tags, tag_embeddings, X_SPREAD)
# OR
x_positions = distribute_horizontally(n_tags, X_SPREAD)
```

---

## FUNCTION SIGNATURE CHANGE

```python
# Before (Phase 17.14):
def calculate_knowledge_positions(
    tags: Dict[str, KnowledgeTag],
    knowledge_levels: Dict[str, float],
    edges: List[KnowledgeEdge],
    file_directory_positions: Optional[Dict[str, Dict[str, float]]] = None
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:

# After (Phase 17.15):
def calculate_knowledge_positions(
    tags: Dict[str, KnowledgeTag],
    knowledge_levels: Dict[str, float],
    edges: List[KnowledgeEdge],
    file_directory_positions: Optional[Dict[str, Dict[str, float]]] = None,
    embeddings_dict: Optional[Dict[str, np.ndarray]] = None  # NEW!
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
```

---

## NEXT STEPS

1. Frontend integration - ensure Three.js renderer uses new positions correctly
2. Mode transition animation testing
3. Performance profiling with large file counts
4. Consider adding edge rendering between parent-child tags (like Directory Mode)
