# Task C1: Code Snippets for Implementation

**File to modify:** `/src/api/routes/tree_routes.py`
**Lines to replace:** 520-627 (chat node building section)

---

## 1. Add Import (at top of file)

```python
from src.layout.knowledge_layout import calculate_chat_positions
```

---

## 2. Build File Positions Mapping (after line 537)

**Location:** After `file_path_to_node_id` dict is built

```python
# ═══════════════════════════════════════════════════════════════════
# MARKER_108_TIMELINE_DECAY: Phase 108.2 - Temporal chat positioning
# ═══════════════════════════════════════════════════════════════════

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

print(f"[CHAT_VIZ] Extracted {len(file_positions)} file positions for temporal layout")
```

---

## 3. Prepare Chats for Positioning (replace lines 538-581)

**Replace:** Current loop that creates chat nodes one by one
**With:** Data collection phase

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

    # Skip chats without associated files (orphaned chats)
    if not associated_file_id:
        print(f"[CHAT_VIZ] Skipping chat {chat_id[:8]} - no associated file (path: {file_path})")
        continue

    # Parse timestamp to datetime object
    from datetime import datetime, timezone
    if updated_at_str:
        try:
            last_activity = datetime.fromisoformat(updated_at_str.replace("Z", ""))
            if last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=timezone.utc)
        except Exception as e:
            print(f"[CHAT_VIZ] Failed to parse timestamp for {chat_id[:8]}: {e}, using now")
            last_activity = datetime.now(timezone.utc)
    else:
        last_activity = datetime.now(timezone.utc)

    # Extract participants
    participants = extract_participants(chat)

    # Determine chat name
    chat_name = chat.get("display_name") or chat.get("file_name") or f"Chat #{chat_id[:8]}"

    # Add to positioning list
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

print(f"[CHAT_VIZ] Prepared {len(chats_to_position)} chats for temporal positioning")
```

---

## 4. Calculate Temporal Positions (new code)

**Add after:** chats_to_position is built

```python
# Calculate positions with temporal Y-axis ordering
# Older chats → lower Y, newer chats → higher Y
positioned_chats = calculate_chat_positions(
    chats=chats_to_position,
    file_positions=file_positions,
    time_range=None,  # Auto-compute from chat timestamps
    y_min=0,
    y_max=500
)

print(f"[CHAT_VIZ] Positioned {len(positioned_chats)} chats with temporal Y-axis")

# Log temporal range for debugging
if positioned_chats:
    y_coords = [c['position']['y'] for c in positioned_chats]
    print(f"[CHAT_VIZ] Y-axis range: {min(y_coords):.1f} to {max(y_coords):.1f}")
```

---

## 5. Create Chat Nodes from Positions (replace lines 583-624)

**Replace:** Current chat node creation
**With:** Loop over positioned_chats

```python
# Create chat nodes from positioned chats
for chat in positioned_chats:
    chat_id = chat['id']
    position = chat['position']

    # Extract position data (now with temporal Y-axis!)
    chat_x = position['x']
    chat_y = position['y']  # ← Temporally ordered: older = lower, newer = higher
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
            "opacity": 0.7 + (decay_factor * 0.3)  # Opacity based on decay (0.7-1.0)
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

---

## Complete Replacement Code

**Replace lines 520-627 in tree_routes.py with:**

```python
# ═══════════════════════════════════════════════════════════════════
# STEP 4.5: Build chat nodes and edges with temporal positioning
# MARKER_108_TIMELINE_DECAY: Phase 108.2 - Chat nodes with Y-axis timeline
# ═══════════════════════════════════════════════════════════════════
chat_nodes = []
chat_edges = []

try:
    from src.chat.chat_history_manager import get_chat_history_manager

    chat_manager = get_chat_history_manager()
    all_chats = chat_manager.get_all_chats(limit=100, load_from_end=True)

    # Create a mapping from file_path to file node id
    file_path_to_node_id = {}
    for node in nodes:
        if node.get('type') in ['leaf', 'file']:
            node_path = node.get('metadata', {}).get('path')
            if node_path:
                file_path_to_node_id[node_path] = node['id']

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

    print(f"[CHAT_VIZ] Extracted {len(file_positions)} file positions for temporal layout")

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
            print(f"[CHAT_VIZ] Skipping chat {chat_id[:8]} - no associated file (path: {file_path})")
            continue

        # Parse timestamp to datetime object
        from datetime import datetime, timezone
        if updated_at_str:
            try:
                last_activity = datetime.fromisoformat(updated_at_str.replace("Z", ""))
                if last_activity.tzinfo is None:
                    last_activity = last_activity.replace(tzinfo=timezone.utc)
            except Exception as e:
                print(f"[CHAT_VIZ] Failed to parse timestamp for {chat_id[:8]}: {e}, using now")
                last_activity = datetime.now(timezone.utc)
        else:
            last_activity = datetime.now(timezone.utc)

        # Extract participants
        participants = extract_participants(chat)

        # Determine chat name
        chat_name = chat.get("display_name") or chat.get("file_name") or f"Chat #{chat_id[:8]}"

        # Add to positioning list
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

    print(f"[CHAT_VIZ] Prepared {len(chats_to_position)} chats for temporal positioning")

    # Calculate positions with temporal Y-axis ordering
    # Older chats → lower Y, newer chats → higher Y
    positioned_chats = calculate_chat_positions(
        chats=chats_to_position,
        file_positions=file_positions,
        time_range=None,  # Auto-compute from chat timestamps
        y_min=0,
        y_max=500
    )

    print(f"[CHAT_VIZ] Positioned {len(positioned_chats)} chats with temporal Y-axis")

    # Log temporal range for debugging
    if positioned_chats:
        y_coords = [c['position']['y'] for c in positioned_chats]
        print(f"[CHAT_VIZ] Y-axis range: {min(y_coords):.1f} to {max(y_coords):.1f}")

    # Create chat nodes from positioned chats
    for chat in positioned_chats:
        chat_id = chat['id']
        position = chat['position']

        # Extract position data (now with temporal Y-axis!)
        chat_x = position['x']
        chat_y = position['y']  # ← Temporally ordered: older = lower, newer = higher
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
                "opacity": 0.7 + (decay_factor * 0.3)  # Opacity based on decay (0.7-1.0)
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

except Exception as chat_err:
    print(f"[CHAT_VIZ] Warning: Could not build chat nodes: {chat_err}")
    import traceback
    traceback.print_exc()
```

---

## Testing Snippet

**Run in Python console or test file:**

```python
from datetime import datetime, timedelta, timezone
from src.layout.knowledge_layout import calculate_decay_factor, calculate_chat_positions

# Test decay factor
now = datetime.now(timezone.utc)
print("Testing decay factor:")
print(f"  Recent (1h ago):  {calculate_decay_factor(now - timedelta(hours=1)):.3f} (expect ~1.0)")
print(f"  Mid (3.5d ago):   {calculate_decay_factor(now - timedelta(hours=84)):.3f} (expect ~0.5)")
print(f"  Old (7d ago):     {calculate_decay_factor(now - timedelta(days=7)):.3f} (expect 0.0)")

# Test temporal ordering
chats = [
    {'id': 'chat1', 'parentId': 'file1', 'lastActivity': now - timedelta(days=1)},
    {'id': 'chat2', 'parentId': 'file1', 'lastActivity': now - timedelta(days=5)},
    {'id': 'chat3', 'parentId': 'file1', 'lastActivity': now - timedelta(hours=1)},
]

file_positions = {'file1': {'x': 100, 'y': 200, 'z': 50}}

positioned = calculate_chat_positions(chats, file_positions, y_min=0, y_max=500)

print("\nTesting temporal ordering:")
for chat in positioned:
    pos = chat['position']
    print(f"  {chat['id']}: Y={pos['y']:.1f}, decay={pos['decay_factor']:.2f}")

# Verify ordering
y_values = [c['position']['y'] for c in positioned]
print(f"\nY ordering check: chat2 < chat1 < chat3")
print(f"  Actual: {positioned[1]['id']} ({y_values[1]:.1f}) < {positioned[0]['id']} ({y_values[0]:.1f}) < {positioned[2]['id']} ({y_values[2]:.1f})")
```

---

## Quick Verification

**After implementation, verify with:**

```bash
# 1. Check syntax
python3 -m py_compile src/api/routes/tree_routes.py

# 2. Start server
python3 src/server.py

# 3. Check API response
curl http://localhost:8000/api/tree/data | jq '.chat_nodes[] | {id, y: .visual_hints.layout_hint.expected_y, opacity: .visual_hints.opacity}'
```

**Expected output:** Chat nodes with varying Y values and opacity values

---

## Rollback (if needed)

**If something breaks, revert to static positioning:**

```python
# Fallback to static positioning (OLD CODE)
chat_x = parent_pos.get('expected_x', 0) + 8
chat_y = parent_pos.get('expected_y', 0) - 5  # Static offset
chat_z = parent_pos.get('expected_z', 0)
decay_factor = calculate_decay(updated_at)
```

---

**End of Code Snippets**

Use this file as a direct reference during implementation. Copy-paste the complete replacement code or individual snippets as needed.
