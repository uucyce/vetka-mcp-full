# PHASE 17.13: HIERARCHICAL TAG TREE LAYOUT

**Date:** 2025-12-26
**Status:** COMPLETED
**File:** `src/layout/knowledge_layout.py`

---

## PROBLEM STATEMENT

Previous Knowledge Mode implementations (17.10-17.12) positioned tags in a FLAT layout:
- Tags arranged horizontally in a line
- Files scattered with complex 3D positioning
- No semantic hierarchy visible
- Did not match Directory Mode's intuitive tree structure

**User Requirement:** Tags should form a HIERARCHICAL TREE like Directory Mode - parent-child relationships, not a flat line.

---

## SOLUTION ARCHITECTURE

### Core Concept: Semantic Tag Hierarchy

Instead of arranging tags flatly, we build a **tree structure** based on semantic similarity:

```
                    [ROOT TAG]  (depth=0, most general)
                    /    |    \
           [TAG A]   [TAG B]   [TAG C]  (depth=1)
              |         |
           [TAG D]   [TAG E]  (depth=2, most specific)
```

Each tag has:
- `parent_tag_id` - reference to parent (None for root)
- `depth` - level in hierarchy (0 = root)

Files fan out BELOW their parent tag, not scattered randomly.

---

## IMPLEMENTATION DETAILS

### 1. KnowledgeTag Dataclass Extension (lines 38-40)

```python
@dataclass
class KnowledgeTag:
    # ... existing fields ...
    # Phase 17.13: Hierarchical tag tree
    parent_tag_id: Optional[str] = None  # Parent tag ID (None for root)
    depth: int = 0  # Depth in tag hierarchy (0 = root)
```

### 2. New Function: `build_tag_hierarchy()` (lines 316-423)

**Algorithm:**

1. **Compute Tag Centroids**
   - For each tag, average embeddings of its files
   - This gives a "semantic center" for each tag

2. **Find Root Tag**
   - Calculate global centroid (average of all tag centroids)
   - Root = tag closest to global centroid (most general/central topic)

3. **Assign Parent-Child Relationships**
   - Process tags iteratively
   - For each unassigned tag, find best parent among assigned tags
   - Best parent = highest cosine similarity with depth penalty
   - Depth penalty: `adjusted_sim = sim - (depth * 0.05)`
   - This prefers shallower parents (more general topics)

**Code:**
```python
def build_tag_hierarchy(
    tags: Dict[str, KnowledgeTag],
    embeddings_dict: Dict[str, np.ndarray]
) -> Dict[str, KnowledgeTag]:
    """
    Build hierarchical tree of tags (like folder structure).
    """
    from sklearn.metrics.pairwise import cosine_similarity

    # Step 1: Compute tag centroids
    tag_centroids = {}
    for tag_id, tag in tags.items():
        tag_embeddings = [embeddings_dict[fid] for fid in tag.files
                          if fid in embeddings_dict]
        if tag_embeddings:
            tag_centroids[tag_id] = np.mean(tag_embeddings, axis=0)

    # Step 2: Find root (closest to global centroid)
    global_centroid = np.mean(list(tag_centroids.values()), axis=0)
    root_tag_id = min(tag_centroids.keys(),
                      key=lambda t: 1 - cosine_similarity(
                          [tag_centroids[t]], [global_centroid])[0][0])

    tags[root_tag_id].parent_tag_id = None
    tags[root_tag_id].depth = 0

    # Step 3: Assign parents based on similarity
    assigned = {root_tag_id}
    while len(assigned) < len(tags):
        for tag_id, tag in tags.items():
            if tag_id in assigned:
                continue

            # Find best parent (highest similarity with depth penalty)
            best_parent_id = root_tag_id
            best_sim = -1

            for candidate_id in assigned:
                sim = cosine_similarity(
                    [tag_centroids[tag_id]],
                    [tag_centroids[candidate_id]]
                )[0][0]

                depth_penalty = tags[candidate_id].depth * 0.05
                adjusted_sim = sim - depth_penalty

                if adjusted_sim > best_sim:
                    best_sim = adjusted_sim
                    best_parent_id = candidate_id

            tag.parent_tag_id = best_parent_id
            tag.depth = tags[best_parent_id].depth + 1
            assigned.add(tag_id)

    return tags
```

### 3. Layout Constants (lines 554-563)

```python
# Hierarchical Layout Constants
TAG_Y_BASE = 100                # Y for root tag
TAG_LAYER_HEIGHT = 250          # Vertical spacing between tag depths
TAG_SIBLING_SPREAD = 350        # Horizontal spread among sibling tags
MAX_BRANCHES_PER_NODE = 5

# File positioning under tags
FILE_FAN_SPREAD = 80            # X spread for files under tag
FILE_STEP_Y = 50                # Y step between files (going DOWN)
FILE_START_OFFSET = 60          # Y offset from tag to first file
```

### 4. Tag Positioning (lines 600-652)

Tags are positioned hierarchically:

```python
# Sort tags by depth (process parents first)
sorted_tags = sorted(tags.values(), key=lambda t: t.depth)

for tag in sorted_tags:
    depth = tag.depth
    parent_id = tag.parent_tag_id

    # Y = based on depth (root at top, children below)
    tag_y = TAG_Y_BASE + depth * TAG_LAYER_HEIGHT

    # X = fan spread from parent
    if parent_id and parent_id in positions:
        parent_pos = positions[parent_id]

        # Find siblings (same parent)
        siblings = [t for t in tags.values() if t.parent_tag_id == parent_id]
        sibling_index = siblings.index(tag)
        num_siblings = len(siblings)

        # Spread siblings horizontally around parent
        if num_siblings > 1:
            normalized = (sibling_index / (num_siblings - 1)) - 0.5
            x_offset = normalized * TAG_SIBLING_SPREAD
        else:
            x_offset = 0

        tag_x = parent_pos['x'] + x_offset
    else:
        # Root tag at center X=0
        tag_x = 0

    tag_z = 0  # ALWAYS 0!
```

**Visual Result:**
```
Y=100:                    [Root Tag]
                         /    |    \
Y=350:            [Tag A]  [Tag B]  [Tag C]
                     |
Y=600:            [Tag D]
```

### 5. File Positioning (lines 664-763)

Files fan out BELOW their parent tag:

```python
for tag_id, tag in tags.items():
    tag_pos = positions[tag_id]
    tag_y = tag_pos['y']
    tag_x = tag_pos['x']

    sorted_files = sorted(tag.files,
                          key=lambda f: knowledge_levels.get(f, 0.5))

    for i, file_id in enumerate(sorted_files):
        # Y = tag_y + offset + stacking (going DOWN)
        y = tag_y + FILE_START_OFFSET + (i * FILE_STEP_Y)

        # X = small fan spread around tag center
        if num_files > 1:
            normalized = (i / (num_files - 1)) - 0.5
            x_offset = normalized * FILE_FAN_SPREAD
        else:
            x_offset = 0

        x = tag_x + x_offset
        z = 0  # ALWAYS flat!
```

**Visual Result:**
```
                [Tag A] (Y=350)
                   |
    file1 ----file2----file3  (Y=410, 460, 510...)
                   |
                   V (stacking down)
```

### 6. Pipeline Integration (lines 894-896)

Added hierarchy building step to main pipeline:

```python
# 2. Cluster files into tags
tags = cluster_files_to_tags(embeddings_dict, file_metadata, min_cluster_size)

# 2.5 Phase 17.13: Build tag hierarchy (parent-child relationships)
tags = build_tag_hierarchy(tags, embeddings_dict)
logger.info(f"[KnowledgeLayout] Tag hierarchy built with {len(tags)} tags")

# 3. Build prerequisite edges
# ... rest of pipeline
```

### 7. API Response Extension (lines 917-919)

Added hierarchy data to JSON response:

```python
'tags': {
    tag_id: {
        'id': tag.id,
        'name': tag.name,
        'files': tag.files,
        'color': tag.color,
        'angle': tag.angle,
        'position': tag.position,
        # Phase 17.13: Hierarchical tag tree data
        'parent_tag_id': tag.parent_tag_id,
        'depth': tag.depth
    }
    for tag_id, tag in tags.items()
}
```

---

## COORDINATE SYSTEM

```
        Y axis (hierarchy)
        ^
        |
        |    [Root] Y=100
        |       |
        |    [Children] Y=350
        |       |
        |    [Grandchildren] Y=600
        |       |
        |    [Files below each tag]
        |
        +-------------------------> X axis (semantic spread)
       (0,0)

        Z = 0 ALWAYS (flat 2D tree)
```

---

## LOGGING OUTPUT

Expected console output:
```
[TagHierarchy] Built hierarchy with 8 tags
[TagHierarchy] Depth distribution: {0: 1, 1: 4, 2: 3}
[TagHierarchy] Root tag: Python Core

[KnowledgeLayout] Tag 'Python Core' depth=0 at (0, 100) - 45 files
[KnowledgeLayout] Tag 'Web Development' depth=1 at (-175, 350) - 32 files
[KnowledgeLayout] Tag 'Data Science' depth=1 at (0, 350) - 28 files
[KnowledgeLayout] Tag 'DevOps' depth=1 at (175, 350) - 15 files
...
```

---

## COMPARISON: BEFORE vs AFTER

### Before (Phase 17.12 - Flat Layout)
```
[Tag1] [Tag2] [Tag3] [Tag4] [Tag5] [Tag6] [Tag7] [Tag8]  <- All at Y=150
  |      |      |      |      |      |      |      |
files  files  files  files  files  files  files  files
```

### After (Phase 17.13 - Hierarchical Tree)
```
                        [Root Tag]
                       /    |    \
               [Child1] [Child2] [Child3]
                  |        |
           [Grandchild1] [Grandchild2]
                |           |
             files        files
```

---

## FILES MODIFIED

| File | Changes |
|------|---------|
| `src/layout/knowledge_layout.py` | Added `parent_tag_id`, `depth` to dataclass; New `build_tag_hierarchy()` function; Rewrote tag positioning; Rewrote file positioning; Pipeline integration; API response extension |

---

## TESTING

Verification command:
```bash
.venv/bin/python -c "from src.layout.knowledge_layout import build_knowledge_graph_from_qdrant, build_tag_hierarchy, calculate_knowledge_positions; print('✓ All imports successful')"
```

**Result:** ✓ All imports successful

---

## NEXT STEPS

1. Visual testing in browser - verify tree structure appears correctly
2. Adjust constants if spacing is too tight/wide:
   - `TAG_LAYER_HEIGHT` - vertical gap between tag levels
   - `TAG_SIBLING_SPREAD` - horizontal spread of siblings
   - `FILE_FAN_SPREAD` - horizontal spread of files under tag
   - `FILE_STEP_Y` - vertical gap between files

3. Consider adding:
   - Edge rendering between parent-child tags (like Directory Mode)
   - Collapse/expand functionality for tag subtrees
   - Dynamic spacing based on number of children
