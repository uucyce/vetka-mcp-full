# Task C1: Implementation Checklist

**Phase:** 108.2 - Timeline Decay Visualization
**Date:** 2026-02-02

---

## Pre-Implementation

- [x] Verify decay calculation works (`calculate_decay_factor`)
- [x] Verify opacity mapping works (0.7 + decay * 0.3)
- [x] Verify frontend rendering works (ctx.globalAlpha)
- [x] Identify issue: temporal Y-axis NOT implemented
- [x] Document current state
- [x] Write verification report

---

## Implementation Steps

### Step 1: Import Required Function
**File:** `src/api/routes/tree_routes.py`
**Location:** Top of file (imports section)

- [ ] Add import:
```python
from src.layout.knowledge_layout import calculate_chat_positions
```

**Verify:**
- [ ] No import errors
- [ ] Function is accessible

---

### Step 2: Build File Positions Mapping
**File:** `src/api/routes/tree_routes.py`
**Location:** After line 537 (before chat loop)

- [ ] Add code to extract file positions:
```python
# MARKER_108_TIMELINE_DECAY: Phase 108.2 - Temporal chat positioning
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

print(f"[CHAT_VIZ] Extracted {len(file_positions)} file positions")
```

**Verify:**
- [ ] `file_positions` dict is created
- [ ] Contains entries for all file nodes
- [ ] Each entry has x, y, z coordinates

---

### Step 3: Prepare Chats List
**File:** `src/api/routes/tree_routes.py`
**Location:** Replace lines 538-581 (current chat loop)

- [ ] Collect chats with timestamps:
```python
# Prepare chats for temporal positioning
chats_to_position = []

for chat in all_chats:
    # Skip chats with no messages
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

    # Skip chats without associated files
    if not associated_file_id:
        print(f"[CHAT_VIZ] Skipping chat {chat_id[:8]} - no associated file")
        continue

    # Parse timestamp
    from datetime import datetime, timezone
    if updated_at_str:
        try:
            last_activity = datetime.fromisoformat(updated_at_str.replace("Z", ""))
            if last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=timezone.utc)
        except Exception as e:
            print(f"[CHAT_VIZ] Failed to parse timestamp for {chat_id[:8]}: {e}")
            last_activity = datetime.now(timezone.utc)
    else:
        last_activity = datetime.now(timezone.utc)

    # Extract participants
    participants = extract_participants(chat)

    # Determine chat name
    chat_name = chat.get("display_name") or chat.get("file_name") or f"Chat #{chat_id[:8]}"

    # Add to list
    chats_to_position.append({
        'id': chat_id,
        'parentId': associated_file_id,
        'lastActivity': last_activity,
        'name': chat_name,
        'message_count': message_count,
        'participants': participants,
        'file_path': file_path,
        'context_type': chat.get("context_type", "file"),
        'display_name': chat.get("display_name")
    })

print(f"[CHAT_VIZ] Prepared {len(chats_to_position)} chats for positioning")
```

**Verify:**
- [ ] `chats_to_position` list is created
- [ ] All chats have required fields: id, parentId, lastActivity
- [ ] Timestamps are datetime objects
- [ ] Only chats with associated files are included

---

### Step 4: Call Positioning Function
**File:** `src/api/routes/tree_routes.py`
**Location:** After chats_to_position is built

- [ ] Call `calculate_chat_positions`:
```python
# Calculate temporal positions with Y-axis timeline
positioned_chats = calculate_chat_positions(
    chats=chats_to_position,
    file_positions=file_positions,
    time_range=None,  # Auto-compute from timestamps
    y_min=0,
    y_max=500
)

print(f"[CHAT_VIZ] Positioned {len(positioned_chats)} chats with temporal Y-axis")
```

**Verify:**
- [ ] `positioned_chats` list returned
- [ ] Each chat has 'position' key
- [ ] Position contains x, y, z, decay_factor
- [ ] Y values differ based on timestamp (older = lower)

---

### Step 5: Create Chat Nodes from Positions
**File:** `src/api/routes/tree_routes.py`
**Location:** Replace lines 583-624 (current chat node creation)

- [ ] Build chat nodes using positioned data:
```python
# Create chat nodes from positioned chats
for chat in positioned_chats:
    chat_id = chat['id']
    position = chat['position']

    # Extract position data
    chat_x = position['x']
    chat_y = position['y']  # ← Temporally ordered Y-axis!
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
            "color": "#4a9eff",  # Blue for chat nodes
            "opacity": 0.7 + (decay_factor * 0.3)  # More opaque for recent chats
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

print(f"[CHAT_VIZ] Built {len(chat_nodes)} chat nodes, {len(chat_edges)} chat edges")
```

**Verify:**
- [ ] Chat nodes created successfully
- [ ] Each node has correct visual_hints
- [ ] Opacity still uses decay formula (0.7 + decay * 0.3)
- [ ] Y coordinates differ based on timestamp
- [ ] Chat edges created for all nodes

---

## Testing

### Unit Tests

- [ ] Test decay calculation:
```python
from datetime import datetime, timedelta, timezone
from src.layout.knowledge_layout import calculate_decay_factor

now = datetime.now(timezone.utc)

# Recent (1 hour ago)
recent = calculate_decay_factor(now - timedelta(hours=1))
assert recent > 0.99, f"Recent decay should be ~1.0, got {recent}"

# Mid (3.5 days ago)
mid = calculate_decay_factor(now - timedelta(hours=84))
assert abs(mid - 0.5) < 0.01, f"Mid decay should be ~0.5, got {mid}"

# Old (7 days ago)
old = calculate_decay_factor(now - timedelta(days=7))
assert old == 0.0, f"Old decay should be 0.0, got {old}"
```

- [ ] Test temporal ordering:
```python
from src.layout.knowledge_layout import calculate_chat_positions

chats = [
    {'id': 'c1', 'parentId': 'f1', 'lastActivity': now - timedelta(days=1)},
    {'id': 'c2', 'parentId': 'f1', 'lastActivity': now - timedelta(days=5)},
    {'id': 'c3', 'parentId': 'f1', 'lastActivity': now - timedelta(hours=1)},
]

file_positions = {'f1': {'x': 100, 'y': 200, 'z': 50}}

positioned = calculate_chat_positions(chats, file_positions)
y_values = {c['id']: c['position']['y'] for c in positioned}

# Older chats should have lower Y
assert y_values['c2'] < y_values['c1'] < y_values['c3'], \
    f"Y ordering wrong: {y_values}"
```

---

### Integration Tests

- [ ] Start server
- [ ] Call `/api/tree/data`
- [ ] Verify response contains chat_nodes
- [ ] Check that chat_nodes have:
  - [ ] Different Y values based on timestamp
  - [ ] Opacity values in range [0.7, 1.0]
  - [ ] Expected_x, expected_y, expected_z in visual_hints
- [ ] Verify older chats have lower Y than newer chats

---

### Visual Tests

- [ ] Open VETKA UI
- [ ] Navigate to 3D canvas
- [ ] Verify chat nodes appear
- [ ] Check visual order:
  - [ ] Older chats appear lower (smaller Y coordinate)
  - [ ] Newer chats appear higher (larger Y coordinate)
- [ ] Check opacity:
  - [ ] Recent chats are bright (fully opaque)
  - [ ] Old chats are dim (70% opacity)
- [ ] Verify multiple chats from same file:
  - [ ] Staggered horizontally (X-axis)
  - [ ] Ordered vertically by timestamp (Y-axis)

---

## Verification

### Code Review

- [ ] `calculate_chat_positions` imported correctly
- [ ] `file_positions` dict built from nodes
- [ ] `chats_to_position` list prepared with timestamps
- [ ] `positioned_chats` calculated using function
- [ ] Chat nodes use positioned data
- [ ] Marker `MARKER_108_TIMELINE_DECAY` added
- [ ] No hardcoded Y offsets remain

### Output Verification

- [ ] API returns chat nodes with temporal Y-axis
- [ ] Y coordinates vary based on timestamp
- [ ] Opacity values in range [0.7, 1.0]
- [ ] Decay factor matches opacity
- [ ] Frontend receives correct data

### Visual Verification

- [ ] Chats appear in correct temporal order
- [ ] Opacity reflects age
- [ ] Multiple chats stagger correctly
- [ ] No positioning errors or overlaps

---

## Cleanup

- [ ] Remove old static positioning code
- [ ] Remove unused variables
- [ ] Add comments explaining temporal logic
- [ ] Update markers
- [ ] Commit changes with message:
```
Phase 108.2: Implement temporal Y-axis for chat nodes

- Integrate calculate_chat_positions() into tree_routes.py
- Replace static Y offset with time-based positioning
- Older chats appear lower, newer chats appear higher
- Opacity decay already working (0.7-1.0 based on age)
- Add MARKER_108_TIMELINE_DECAY

Fixes: Task C1 timeline decay visualization
```

---

## Documentation

- [ ] Update TASK_C1_TIMELINE_DECAY_REPORT.md with "FIXED" status
- [ ] Update TASK_C1_QUICK_SUMMARY.md
- [ ] Add screenshots to docs (if applicable)
- [ ] Update PHASE_108_RECON_REPORT.md progress

---

## Success Criteria

✅ Task is complete when:

1. `calculate_chat_positions()` is called in tree_routes.py
2. Chat nodes use temporal Y-axis positioning
3. Older chats have lower Y coordinates
4. Newer chats have higher Y coordinates
5. Opacity decay still works (0.7-1.0)
6. Visual tests confirm correct ordering
7. No regression in chat rendering
8. Marker `MARKER_108_TIMELINE_DECAY` added

---

**Status:** Ready for implementation

**Estimated Time:** 1-2 hours

**Priority:** P1 (Task C1, Phase 108.2)
