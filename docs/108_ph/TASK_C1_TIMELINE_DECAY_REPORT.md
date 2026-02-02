# Task C1: Timeline Decay Visualization - Verification Report

**Phase:** 108.2
**Date:** 2026-02-02
**Status:** PARTIAL IMPLEMENTATION - NEEDS FIX

---

## Summary

The timeline decay visualization system is **partially implemented**:
- ✅ Backend decay calculation works correctly
- ✅ Opacity flows from backend to frontend
- ❌ **CRITICAL:** Temporal Y-axis ordering is NOT implemented in production code
- ✅ Frontend correctly applies opacity from visual_hints

---

## 1. Decay Factor Implementation

### Backend: knowledge_layout.py (Lines 2239-2265)

**Status:** ✅ CORRECT

```python
def calculate_decay_factor(last_activity: datetime) -> float:
    """
    Calculate decay factor for chat node opacity based on recency.

    MARKER_108_CHAT_DECAY: Phase 108.2 - Chat node temporal decay

    Returns:
        float: Decay factor in range [0, 1] where 1 = most recent, 0 = oldest
               Formula: max(0, 1 - hours_since_activity / 168)
               168 hours = 1 week, so chats older than 1 week have 0 decay
    """
    now = datetime.now(timezone.utc)

    # Ensure last_activity is timezone-aware
    if last_activity.tzinfo is None:
        last_activity = last_activity.replace(tzinfo=timezone.utc)

    delta = now - last_activity
    hours_since = delta.total_seconds() / 3600

    # Decay over 1 week (168 hours)
    decay = max(0.0, 1.0 - (hours_since / 168.0))

    return decay
```

**Verification:**
- ✅ Timezone handling is correct
- ✅ Formula is correct: `max(0, 1 - hours_since_activity / 168)`
- ✅ Returns range [0, 1]
- ✅ Marked with `MARKER_108_CHAT_DECAY`

**Test Cases:**
- Now: decay ≈ 1.0 (fully visible)
- 3.5 days (84 hours): decay = 0.5 (semi-transparent)
- 7 days (168 hours): decay = 0.0 (nearly invisible)
- 14+ days: decay = 0.0 (clamped)

---

## 2. Opacity Mapping (Backend → Frontend)

### API: tree_routes.py (Line 606)

**Status:** ✅ CORRECT

```python
"visual_hints": {
    "layout_hint": {
        "expected_x": chat_x,
        "expected_y": chat_y,
        "expected_z": chat_z
    },
    "color": "#4a9eff",  # Blue for chat nodes
    "opacity": 0.7 + (decay_factor * 0.3)  # More opaque for recent chats
}
```

**Opacity Formula:** `opacity = 0.7 + (decay * 0.3)`

**Verification:**
- ✅ Recent chat (decay=1.0): opacity = 1.0 (fully opaque)
- ✅ Mid-age chat (decay=0.5): opacity = 0.85 (semi-transparent)
- ✅ Old chat (decay=0.0): opacity = 0.7 (minimum visibility)

**Note:** Opacity is clamped to minimum 0.7 to ensure all chats remain visible.

---

## 3. Frontend Rendering

### FileCard.tsx (Lines 345-357)

**Status:** ✅ CORRECT

```typescript
// MARKER_108_CHAT_CARD: Phase 108.2 - Chat node rendering
if (type === 'chat') {
  // Chat node rendering with blue theme
  const chatOpacity = visual_hints?.opacity ?? 1.0;
  const bgColor = isSelected ? '#3a7acc' : isHovered ? '#4a88dd' : '#4a9eff';

  // Background with rounded corners
  ctx.fillStyle = bgColor;
  ctx.globalAlpha = chatOpacity;  // ← Applies decay-based opacity
  ctx.beginPath();
  ctx.roundRect(0, 0, w, h, 8);
  ctx.fill();
  ctx.globalAlpha = 1.0;
  // ... rest of rendering
}
```

**Verification:**
- ✅ Reads `visual_hints.opacity` from API
- ✅ Applies to canvas context via `ctx.globalAlpha`
- ✅ Marked with `MARKER_108_CHAT_CARD`
- ✅ Properly resets alpha to 1.0 after background

---

## 4. Temporal Y-Axis Ordering

### ISSUE: NOT IMPLEMENTED IN PRODUCTION

**Status:** ❌ BROKEN

### Current Implementation: tree_routes.py (Lines 572-575)

```python
# Offset chat node from file: +8 in x, -5 in y
chat_x = parent_pos.get('expected_x', 0) + 8
chat_y = parent_pos.get('expected_y', 0) - 5  # ← STATIC OFFSET, NO TEMPORAL ORDERING
chat_z = parent_pos.get('expected_z', 0)
```

**Problem:** All chats are positioned at the same Y offset (-5) from their parent file, regardless of timestamp.

### Expected Implementation: knowledge_layout.py (Lines 2268-2417)

The `calculate_chat_positions()` function EXISTS and is CORRECT, but is **NOT BEING CALLED** by tree_routes.py.

```python
def calculate_chat_positions(
    chats: List[Dict],
    file_positions: Dict[str, Dict],
    time_range: Optional[Tuple[datetime, datetime]] = None,
    y_min: float = 0,
    y_max: float = 500
) -> List[Dict]:
    """
    MARKER_108_CHAT_POSITION: Phase 108.2 - Chat node positioning

    Positioning rules:
    - X: offset from parent file (+8-12 units to the right, staggered if multiple chats)
    - Y: temporal axis (older chats at bottom, newer at top)  # ← THIS IS THE MISSING PIECE
      Formula: base_y + (normalized_time * height_range)
      normalized_time = (chat_timestamp - min_timestamp) / (max_timestamp - min_timestamp)
    - Z: same as parent file (keep in same "depth plane")
    - decay_factor: affects opacity (recent chats = brighter)
    """
```

**Key Features of calculate_chat_positions:**
- ✅ Temporal Y sorting: `y = y_min + (normalized_time * height_range)`
- ✅ X-axis staggering for multiple chats: `x = parent.x + 10 + (idx % 3) * 2`
- ✅ Z-plane alignment with parent
- ✅ Decay factor calculation
- ✅ Marked with `MARKER_108_CHAT_POSITION`

---

## 5. Required Fix

### File: src/api/routes/tree_routes.py

**Location:** Lines 520-627 (chat node building section)

**Current Flow:**
```
1. Get all chats from chat_manager
2. For each chat:
   - Calculate decay_factor ✅
   - Find parent file position
   - Apply STATIC offset (+8, -5) ❌ NO TEMPORAL ORDERING
   - Create chat node with visual_hints
```

**Required Flow:**
```
1. Get all chats from chat_manager
2. Prepare chats list with parentId, lastActivity
3. Extract file_positions from existing nodes
4. Call calculate_chat_positions(chats, file_positions, y_min=0, y_max=500) ✅
5. Use returned positions with temporal Y-axis ✅
6. Create chat nodes with visual_hints
```

### Implementation Steps:

1. **Import the function** (add to imports section):
```python
from src.layout.knowledge_layout import calculate_chat_positions
```

2. **Build file_positions dict** (before chat loop):
```python
# Build file_positions mapping for calculate_chat_positions
file_positions = {}
for node in nodes:
    if node.get('type') in ['leaf', 'file']:
        node_id = node['id']
        layout_hint = node.get('visual_hints', {}).get('layout_hint', {})
        file_positions[node_id] = {
            'x': layout_hint.get('expected_x', 0),
            'y': layout_hint.get('expected_y', 0),
            'z': layout_hint.get('expected_z', 0)
        }
```

3. **Prepare chats for positioning** (collect all chats first):
```python
# Prepare chats for positioning
chats_to_position = []
for chat in all_chats:
    message_count = len(chat.get("messages", []))
    if message_count == 0:
        continue

    chat_id = chat.get("id")
    file_path = chat.get("file_path", "")
    updated_at_str = chat.get("updated_at")

    # Find associated file node id
    associated_file_id = None
    if file_path and file_path not in ('unknown', 'root', ''):
        associated_file_id = file_path_to_node_id.get(file_path)

    # Skip chats without associated files (or handle separately)
    if not associated_file_id:
        continue

    # Parse timestamp
    from datetime import datetime, timezone
    if updated_at_str:
        try:
            last_activity = datetime.fromisoformat(updated_at_str.replace("Z", ""))
            if last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=timezone.utc)
        except:
            last_activity = datetime.now(timezone.utc)
    else:
        last_activity = datetime.now(timezone.utc)

    chats_to_position.append({
        'id': chat_id,
        'parentId': associated_file_id,
        'lastActivity': last_activity,
        'name': chat.get("display_name") or chat.get("file_name") or f"Chat #{chat_id[:8]}",
        'message_count': message_count,
        'participants': extract_participants(chat),
        'file_path': file_path,
        'context_type': chat.get("context_type", "file"),
        'display_name': chat.get("display_name")
    })
```

4. **Call calculate_chat_positions**:
```python
# MARKER_108_TIMELINE_DECAY: Calculate temporal positions
positioned_chats = calculate_chat_positions(
    chats=chats_to_position,
    file_positions=file_positions,
    time_range=None,  # Auto-compute from timestamps
    y_min=0,
    y_max=500
)
```

5. **Create chat nodes from positioned chats**:
```python
for chat in positioned_chats:
    chat_id = chat['id']
    position = chat['position']

    # Extract position data
    chat_x = position['x']
    chat_y = position['y']  # ← Now temporally ordered!
    chat_z = position['z']
    decay_factor = position['decay_factor']

    # Create chat node
    chat_node = {
        "id": f"chat_{chat_id}",
        "type": "chat",
        "name": chat['name'],
        "parent_id": chat['parentId'],
        "metadata": {
            "chat_id": chat_id,
            "file_path": chat['file_path'],
            "last_activity": chat['lastActivity'].isoformat(),
            "message_count": chat['message_count'],
            "participants": chat['participants'],
            "decay_factor": decay_factor,
            "context_type": chat['context_type'],
            "display_name": chat['display_name']
        },
        "visual_hints": {
            "layout_hint": {
                "expected_x": chat_x,
                "expected_y": chat_y,
                "expected_z": chat_z
            },
            "color": "#4a9eff",
            "opacity": 0.7 + (decay_factor * 0.3)
        }
    }

    chat_nodes.append(chat_node)

    # Create edge from file to chat
    chat_edge = {
        "from": chat['parentId'],
        "to": f"chat_{chat_id}",
        "semantics": "chat",
        "metadata": {
            "type": "chat",
            "color": "#4a9eff",
            "opacity": 0.3
        }
    }
    chat_edges.append(chat_edge)
```

---

## 6. Visual Decay Legend (Optional Enhancement)

**Status:** NOT IMPLEMENTED

**Proposal:** Add a legend/indicator showing what opacity levels mean:
- Recent (opacity 1.0): "Active" - fully visible, bright blue
- Mid-age (opacity 0.85): "Recent" - semi-transparent
- Old (opacity 0.7): "Archive" - dimmed, nearly invisible

**Implementation Location:** Could be added to:
- Client UI overlay (ChatSidebar.tsx)
- Canvas overlay (Canvas3D.tsx)
- Help tooltip/info panel

**Example Legend:**
```
Chat Timeline Legend:
━━━━━━━━━━━━━━━━━━━
🔵 Bright: < 1 day old
🔷 Medium: 1-4 days old
🔹 Dim: 4-7 days old
◽️ Faded: > 7 days old
```

---

## 7. Test Cases

### Backend Tests (Recommended)

**File:** `tests/test_chat_positioning.py`

```python
from datetime import datetime, timedelta, timezone
from src.layout.knowledge_layout import calculate_decay_factor, calculate_chat_positions

def test_decay_factor():
    now = datetime.now(timezone.utc)

    # Test recent chat
    recent = now - timedelta(hours=1)
    assert calculate_decay_factor(recent) > 0.99

    # Test mid-age chat
    mid = now - timedelta(hours=84)  # 3.5 days
    assert abs(calculate_decay_factor(mid) - 0.5) < 0.01

    # Test old chat
    old = now - timedelta(days=7)
    assert calculate_decay_factor(old) == 0.0

    # Test very old chat
    very_old = now - timedelta(days=14)
    assert calculate_decay_factor(very_old) == 0.0

def test_temporal_ordering():
    now = datetime.now(timezone.utc)

    chats = [
        {'id': 'chat1', 'parentId': 'file1', 'lastActivity': now - timedelta(days=1)},
        {'id': 'chat2', 'parentId': 'file1', 'lastActivity': now - timedelta(days=5)},
        {'id': 'chat3', 'parentId': 'file1', 'lastActivity': now - timedelta(hours=1)},
    ]

    file_positions = {
        'file1': {'x': 100, 'y': 200, 'z': 50}
    }

    positioned = calculate_chat_positions(chats, file_positions, y_min=0, y_max=500)

    # Extract Y positions
    y_positions = {chat['id']: chat['position']['y'] for chat in positioned}

    # Verify temporal ordering: older (chat2) < middle (chat1) < newer (chat3)
    assert y_positions['chat2'] < y_positions['chat1'] < y_positions['chat3']
```

### Frontend Visual Tests

1. **Manual Test:**
   - Open VETKA with multiple chats of different ages
   - Verify older chats appear lower (smaller Y)
   - Verify newer chats appear higher (larger Y)
   - Verify opacity decreases with age

2. **Visual Inspection:**
   - Recent chat (< 1 day): fully opaque, high Y position
   - Week-old chat (7 days): dim opacity (0.7), low Y position

---

## 8. Current Markers

**Existing Markers:**
- ✅ `MARKER_108_CHAT_DECAY` - knowledge_layout.py:2243 (decay calculation)
- ✅ `MARKER_108_CHAT_POSITION` - knowledge_layout.py:2278 (positioning function)
- ✅ `MARKER_108_CHAT_CARD` - FileCard.tsx:345 (chat rendering)

**Missing Marker:**
- ❌ `MARKER_108_TIMELINE_DECAY` - Should be added to tree_routes.py where calculate_chat_positions is called

---

## 9. Summary of Findings

### ✅ WORKING Components:
1. Backend decay calculation (calculate_decay_factor)
2. Opacity mapping (0.7 + decay * 0.3)
3. Frontend opacity rendering (ctx.globalAlpha)
4. Decay factor flow from backend to frontend

### ❌ BROKEN Components:
1. **Temporal Y-axis ordering NOT implemented in production**
   - Function exists but is not called
   - Tree routes uses static Y offset (-5)
   - No temporal sorting of chats by timestamp

### 🔧 Required Fix:
- Integrate `calculate_chat_positions()` into `tree_routes.py`
- Replace static positioning with temporal Y-axis
- Add `MARKER_108_TIMELINE_DECAY` marker

---

## 10. Deliverable

**Status:** PARTIAL - Requires fix before marking as complete.

**Next Steps:**
1. Apply the fix to tree_routes.py as outlined in Section 5
2. Add marker `MARKER_108_TIMELINE_DECAY`
3. Test temporal ordering visually
4. Verify opacity decay works with new positioning
5. Optionally add decay legend to UI

**Estimated Time:** 1-2 hours to implement fix and test.

---

## References

- Backend implementation: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/layout/knowledge_layout.py` (lines 2239-2417)
- API implementation: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/tree_routes.py` (lines 520-627)
- Frontend rendering: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/FileCard.tsx` (lines 345-410)
- Documentation: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/108_ph/CHAT_POSITIONING_USAGE.md`

---

**Report Generated:** 2026-02-02
**Task:** C1 - Timeline Decay Visualization
**Phase:** 108.2
**Status:** NEEDS FIX - Temporal ordering not integrated
