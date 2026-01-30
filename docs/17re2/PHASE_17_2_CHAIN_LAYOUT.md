# Phase 17.2: Prerequisite Chain Layout ("Shashlik on Skewer")

**Date:** December 25, 2025
**Status:** IMPLEMENTED
**Previous Phase:** 17.1 - Knowledge Graph Layout (COMPLETE)

---

## Overview

Phase 17.2 implements the "Shashlik on Skewer" concept for file arrangement in Knowledge Mode. Instead of all files connecting directly to their semantic tags, files form **chains** where only the chain root connects to the tag.

### Visual Concept

```
     TAG (Y=150)
       │
       └─── ROOT FILE (lowest KL, connects to tag)
              │
              └─── FILE 2 (higher KL, connects to root)
                     │
                     └─── FILE 3 (highest KL, connects to file 2)
```

---

## Key Changes from Phase 17.1

| Aspect | Phase 17.1 | Phase 17.2 |
|--------|-----------|-----------|
| File→Tag connection | ALL files connect to tag | Only CHAIN ROOTS connect to tag |
| File→File connection | None | Files connect to previous in chain |
| Stem binding at t≥0.5 | All stems → tag | Roots → tag, others → prev file |
| API response | positions only | positions + chain_edges |

---

## Architecture

### Chain Structure

```python
@dataclass
class PrerequisiteChain:
    tag_id: str           # Parent tag/cluster
    chain_index: int      # Index within tag's chains
    files: List[str]      # Ordered: root (low KL) → tip (high KL)
    root_file: str        # File that connects to tag
```

### Position Data (Enhanced)

Each file position now includes:
```python
{
    'x': float,
    'y': float,
    'z': float,
    'angle': float,
    'type': 'file',
    'knowledge_level': float,
    'parent_tag': str,
    'chain_index': int,
    'is_chain_root': bool,    # NEW: True if this file connects to tag
    'prev_in_chain': str|None # NEW: Previous file in chain (or None for roots)
}
```

### Chain Edges

New `chain_edges` array in API response:
```json
[
  {"source": "tag_0", "target": "file_1", "type": "tag_to_file", "chain_index": 0},
  {"source": "file_1", "target": "file_2", "type": "file_to_file", "chain_index": 0},
  {"source": "file_2", "target": "file_3", "type": "file_to_file", "chain_index": 0}
]
```

---

## Algorithm

### 1. Build Prerequisite Chains

```python
def build_prerequisite_chains(tag_id, file_ids, knowledge_levels, edges):
    # Build adjacency for this cluster
    children[file_id] = [files that depend on this file]
    parents[file_id] = [files this file depends on]

    # Find chain roots: files with NO parents (in_degree = 0)
    roots = [f for f in file_ids if not parents.get(f)]

    # Limit to MAX_BRANCHES_PER_NODE (5)
    if len(roots) > 5:
        roots = sorted(roots, key=lambda f: kl[f])[:5]

    # BFS from each root to build chain
    for root in roots:
        chain_files = bfs_collect(root, children, visited)
        chain_files.sort(key=lambda f: kl[f])  # Ascending KL
        chains.append(PrerequisiteChain(...))

    return chains
```

### 2. Position Files Within Chains

```python
for chain in tag_chains:
    # Calculate chain angle (fan out from tag)
    chain_angle = tag_angle - SPREAD/2 + (chain_index / (num_chains-1)) * SPREAD

    prev_file_id = None
    for file_id in chain.files:
        kl = knowledge_levels[file_id]
        y = TAG_BASE_Y + kl * MAX_KL_LAYERS * LAYER_HEIGHT
        angle = chain_angle + (kl - 0.5) * 10
        radius = FILE_BASE_RADIUS + kl * 120

        positions[file_id] = {
            ...
            'is_chain_root': file_id == chain.root_file,
            'prev_in_chain': prev_file_id
        }

        # Create chain edge
        if prev_file_id is None:
            chain_edges.append({source: tag_id, target: file_id, type: 'tag_to_file'})
        else:
            chain_edges.append({source: prev_file_id, target: file_id, type: 'file_to_file'})

        prev_file_id = file_id
```

---

## Frontend Changes

### Stem Rebinding (updateKnowledgeBlend)

```javascript
if (t >= 0.5 && knowledgePositions[childId]) {
    const fileKgPos = knowledgePositions[childId];
    const isChainRoot = fileKgPos.is_chain_root;
    const prevInChain = fileKgPos.prev_in_chain;

    if (isChainRoot && tagMeshes.has(fileKgPos.parent_tag)) {
        // Chain ROOT connects to TAG
        positions[0] = tagGroup.position.x;
        positions[1] = tagGroup.position.y;
        positions[2] = tagGroup.position.z;
    } else if (prevInChain) {
        // Non-root connects to PREVIOUS file in chain
        const prevInfo = nodeObjects.get(prevInChain);
        positions[0] = prevInfo.mesh.position.x;
        positions[1] = prevInfo.mesh.position.y;
        positions[2] = prevInfo.mesh.position.z;
    }
}
```

---

## Constants

```python
MAX_BRANCHES_PER_NODE = 5      # Maximum chains from any single tag
TAG_BASE_Y = 150               # Tags at Y=150
FILE_BASE_RADIUS = 200         # Base radius for files
LAYER_HEIGHT = 80              # Pixels per knowledge layer
MAX_KL_LAYERS = 10             # Maximum layers above tags
CHAIN_ANGLE_SPREAD = 120       # Total degrees for chains from a tag
```

---

## API Response Format

```json
{
  "status": "ok",
  "source": "computed",
  "tags": {...},
  "edges": [...],
  "chain_edges": [
    {"source": "tag_0", "target": "file_123", "type": "tag_to_file", "chain_index": 0},
    {"source": "file_123", "target": "file_456", "type": "file_to_file", "chain_index": 0}
  ],
  "positions": {
    "file_123": {
      "x": -100,
      "y": 230,
      "z": 15,
      "type": "file",
      "knowledge_level": 0.3,
      "parent_tag": "tag_0",
      "chain_index": 0,
      "is_chain_root": true,
      "prev_in_chain": null
    }
  },
  "knowledge_levels": {...}
}
```

---

## Files Modified

| File | Changes |
|------|---------|
| `src/layout/knowledge_layout.py` | Added `PrerequisiteChain`, `build_prerequisite_chains()`, updated `calculate_knowledge_positions()` |
| `src/server/routes/tree_routes.py` | Added `chain_edges` to cache and API response |
| `src/visualizer/tree_renderer.py` | Updated `updateKnowledgeBlend()` for chain stem binding |

---

## Testing Checklist

```
[ ] API returns chain_edges array
[ ] Chain roots identified correctly (lowest KL in chain)
[ ] At t=0%: All stems connect folder→file (unchanged)
[ ] At t=50%: Stems switch to chain structure
    [ ] Root files connect to TAGs
    [ ] Non-root files connect to prev file in chain
[ ] At t=100%: Full chain visualization
    [ ] Files form visual chains ("shashlik")
    [ ] Maximum 5 chains per tag
[ ] Console logs show chain statistics
```

---

## Console Output (Expected)

```
[Chains] Tag tag_0: 3 chains from 45 files
  Chain 0: 15 files, root KL=0.22
  Chain 1: 18 files, root KL=0.25
  Chain 2: 12 files, root KL=0.30
[KnowledgeLayout] Positioned 45 files in 3 chains
[KnowledgeLayout] Created 45 chain edges
[KG] Knowledge Graph built: 5 tags, 120 edges, 213 chain_edges
```

---

*Implemented: December 25, 2025*
*Author: Claude Opus 4.5*
