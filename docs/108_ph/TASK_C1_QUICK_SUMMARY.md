# Task C1: Timeline Decay - Quick Summary

**Phase:** 108.2
**Status:** ⚠️ PARTIAL - Needs Fix
**Date:** 2026-02-02

---

## TL;DR

✅ **WORKING:**
- Backend decay calculation
- Opacity mapping (0.7 → 1.0 based on age)
- Frontend opacity rendering

❌ **BROKEN:**
- **Temporal Y-axis ordering NOT implemented in production**
- Tree routes uses static Y offset instead of time-based positioning
- `calculate_chat_positions()` exists but is NOT called

---

## What Works

### 1. Decay Calculation
```python
# knowledge_layout.py:2239
decay = max(0, 1 - hours_since_activity / 168)
```
- Recent (< 1 day): decay ≈ 1.0
- Mid (3.5 days): decay = 0.5
- Old (7+ days): decay = 0.0

### 2. Opacity Mapping
```python
# tree_routes.py:606
opacity = 0.7 + (decay_factor * 0.3)
```
- Recent: opacity = 1.0 (fully opaque)
- Old: opacity = 0.7 (dimmed)

### 3. Frontend Rendering
```typescript
// FileCard.tsx:348
const chatOpacity = visual_hints?.opacity ?? 1.0;
ctx.globalAlpha = chatOpacity;  // ✅ Works!
```

---

## What's Broken

### Current Implementation (tree_routes.py:572-575)
```python
chat_x = parent_pos.get('expected_x', 0) + 8
chat_y = parent_pos.get('expected_y', 0) - 5  # ❌ STATIC OFFSET
chat_z = parent_pos.get('expected_z', 0)
```

**Problem:** All chats get same Y offset (-5), no temporal ordering.

---

## The Fix

### Step 1: Import the function
```python
from src.layout.knowledge_layout import calculate_chat_positions
```

### Step 2: Prepare data
```python
# Build file_positions dict
file_positions = {
    node_id: {'x': x, 'y': y, 'z': z}
    for node in nodes if node.type in ['leaf', 'file']
}

# Prepare chats with timestamps
chats_to_position = [
    {
        'id': chat_id,
        'parentId': associated_file_id,
        'lastActivity': datetime.fromisoformat(updated_at),
        'name': chat_name,
        ...
    }
    for chat in all_chats
]
```

### Step 3: Call positioning function
```python
# MARKER_108_TIMELINE_DECAY
positioned_chats = calculate_chat_positions(
    chats=chats_to_position,
    file_positions=file_positions,
    y_min=0,
    y_max=500
)
```

### Step 4: Use positioned data
```python
for chat in positioned_chats:
    position = chat['position']
    chat_x = position['x']
    chat_y = position['y']  # ← Now temporally ordered!
    chat_z = position['z']
    decay_factor = position['decay_factor']

    # Create chat_node with these positions...
```

---

## Expected Result

### Before Fix
```
File Node
   │
   ├─ Chat 1 (new)  ━━━  Y=-5 (static)
   ├─ Chat 2 (mid)  ━━   Y=-5 (static)
   └─ Chat 3 (old)  ──   Y=-5 (static)
```

### After Fix
```
File Node
   │
   ├─ Chat 1 (new)  ━━━  Y=450 (high)
   │
   ├─ Chat 2 (mid)  ━━   Y=300 (medium)
   │
   └─ Chat 3 (old)  ──   Y=150 (low)

Y-axis = Timeline:
↑ Higher Y = Newer (brighter)
↓ Lower Y  = Older (dimmer)
```

---

## Files to Modify

1. **src/api/routes/tree_routes.py** (lines 520-627)
   - Replace static positioning with `calculate_chat_positions()`
   - Add `MARKER_108_TIMELINE_DECAY`

---

## Test Checklist

- [ ] Import `calculate_chat_positions` successfully
- [ ] Build `file_positions` dict correctly
- [ ] Parse chat timestamps to datetime objects
- [ ] Call `calculate_chat_positions()` without errors
- [ ] Verify `positioned_chats` have temporal Y-axis
- [ ] Verify older chats have lower Y coordinates
- [ ] Verify newer chats have higher Y coordinates
- [ ] Verify opacity still works (0.7 - 1.0)
- [ ] Verify multiple chats are staggered in X-axis
- [ ] Visual test: chats appear in temporal order

---

## References

- Full Report: `/docs/108_ph/TASK_C1_TIMELINE_DECAY_REPORT.md`
- Flow Diagram: `/docs/108_ph/TIMELINE_DECAY_FLOW_DIAGRAM.txt`
- Usage Guide: `/docs/108_ph/CHAT_POSITIONING_USAGE.md`

---

## Markers

**Existing:**
- `MARKER_108_CHAT_DECAY` - knowledge_layout.py:2243
- `MARKER_108_CHAT_POSITION` - knowledge_layout.py:2278
- `MARKER_108_CHAT_CARD` - FileCard.tsx:345

**Missing:**
- `MARKER_108_TIMELINE_DECAY` - tree_routes.py (add when fix is applied)

---

**Next Action:** Apply fix to tree_routes.py

**Estimated Time:** 1-2 hours
