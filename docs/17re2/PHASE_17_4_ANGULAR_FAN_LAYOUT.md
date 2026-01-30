# Phase 17.4: Angular Fan Distribution for Trees

**Date:** December 25, 2025
**Status:** IMPLEMENTED
**Previous Phase:** 17.3 - Zone-Based Layout (COMPLETE)

---

## Problem Statement

Phase 17.3 fixed zone positioning, but files grew vertically "in the sky" without angular spread. Trees lacked the natural fan-like appearance of real trees.

**Before (17.3):**
```
    📄 📄 📄 📄  (files stacked vertically)
        |
       🏷️ tag
```

**After (17.4):**
```
    📄        📄
     \      /
      \    /
       \  /
        \/
       🏷️ tag
```

---

## Solution: Angular Fan Distribution

### Key Concept

Files spread in a **FAN shape** above their parent tag:
- Low KL files (foundational) → near center, close to tag
- High KL files (advanced) → at edges, far from tag
- Radius increases with knowledge_level → creates cone shape

### Layout Constants

```python
FAN_ANGLE_SPREAD = 120  # Total degrees (-60° to +60°)
FAN_BASE_RADIUS = 50    # Radius at kl=0 (near tag)
FAN_MAX_RADIUS = 200    # Additional radius at kl=1.0
KL_HEIGHT_RANGE = 400   # Max height above tag
```

---

## Algorithm

### For Non-Chain Files (Simple Fan)

```python
# Sort files by knowledge_level
sorted_files = sorted(tag.files, key=lambda f: knowledge_levels[f])

for i, file_id in enumerate(sorted_files):
    kl = knowledge_levels[file_id]

    # Angle within fan (-60° to +60°)
    if num_files > 1:
        angle = -60 + (i / (num_files - 1)) * 120
    else:
        angle = 0

    # Y grows with KL (ABOVE tag)
    y = tag_y + (kl * 400)

    # Radius increases with KL (wider at top)
    radius = 50 + (kl * 200)

    # X from angle
    x = tag_x + sin(radians(angle)) * radius

    # Z: slight variation
    z = tag_z + ((i % 3) - 1) * 10
```

### For Chain Files (Multi-Chain Fan)

```python
# Each chain gets its own angular segment
for chain in tag_chains:
    # Chain base angle within fan
    if num_chains > 1:
        chain_base_angle = -60 + (chain.index / (num_chains - 1)) * 120
    else:
        chain_base_angle = 0

    # Sub-spread for files within chain
    chain_sub_spread = 120 / num_chains * 0.5

    for file_idx, file_id in enumerate(chain.files):
        # File angle offset within chain's segment
        if num_files > 1:
            file_offset = -chain_sub_spread/2 + (file_idx / (num_files - 1)) * chain_sub_spread
        else:
            file_offset = 0

        angle = chain_base_angle + file_offset
        # ... rest of positioning
```

---

## Visual Result

### Single Tag with 5 Files

```
                📄 (KL=0.9)
               /
              /
             /      📄 (KL=0.8)
            /      /
           /      /
          /      /
         📄     📄 (KL=0.5)
          \    /
           \  /
            \/
            🏷️ Tag (centroid of folder)
```

### Tag with 3 Chains

```
Chain 0           Chain 1           Chain 2
  📄                📄                📄
   \                |                /
    \               |               /
     📄             📄             📄
      \             |             /
       \            |            /
        \           |           /
         \__________|__________/
                   🏷️
```

---

## Position Data Structure

```json
{
  "file_123": {
    "x": 145.5,
    "y": 520.0,
    "z": 10,
    "angle": 35.0,
    "radius": 150.0,
    "type": "file",
    "knowledge_level": 0.5,
    "parent_tag": "tag_0",
    "chain_index": 1,
    "is_chain_root": false,
    "prev_in_chain": "file_122"
  }
}
```

---

## Files Modified

| File | Changes |
|------|---------|
| `src/layout/knowledge_layout.py` | Added FAN constants, updated positioning formulas |

---

## Testing Checklist

```
[ ] At 100% blend:
    [ ] Files form FAN shape above tags
    [ ] Low KL files near center
    [ ] High KL files at edges
    [ ] Radius increases with KL (cone shape)
    [ ] Multiple chains visible as separate branches
[ ] Smooth transition from 0% to 100%
[ ] No overlapping files
[ ] Z variation prevents depth issues
```

---

*Implemented: December 25, 2025*
*Author: Claude Opus 4.5*
