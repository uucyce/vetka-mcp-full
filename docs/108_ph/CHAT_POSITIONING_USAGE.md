# Chat Node Positioning - Usage Guide

**Phase 108.2: Chat Visualization**
**File:** `src/layout/knowledge_layout.py`

## Overview

Two new functions have been added to `knowledge_layout.py` for positioning chat nodes in 3D space relative to their parent files:

1. `calculate_decay_factor(last_activity: datetime) -> float`
2. `calculate_chat_positions(chats, file_positions, ...) -> List[Dict]`

## Function Details

### `calculate_decay_factor(last_activity: datetime) -> float`

**MARKER:** `MARKER_108_CHAT_DECAY`

Calculates opacity decay based on chat recency.

**Formula:** `max(0, 1 - hours_since_activity / 168)`
- 168 hours = 1 week
- Chats older than 1 week have decay factor of 0
- Recent chats have decay factor approaching 1

**Example:**
```python
from datetime import datetime, timezone, timedelta
from src.layout.knowledge_layout import calculate_decay_factor

# Recent chat (1 hour ago)
recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
decay = calculate_decay_factor(recent_time)
# decay ≈ 0.994 (very bright)

# Week-old chat
old_time = datetime.now(timezone.utc) - timedelta(days=7)
decay = calculate_decay_factor(old_time)
# decay ≈ 0.0 (nearly invisible)
```

---

### `calculate_chat_positions(chats, file_positions, ...) -> List[Dict]`

**MARKER:** `MARKER_108_CHAT_POSITION`

Main positioning function for chat nodes.

**Positioning Rules:**
- **X-axis:** Parent file X + 10 units (base offset) + stagger (0-4 units for multiple chats)
- **Y-axis:** Temporal timeline (older = lower, newer = higher)
  - Normalized between `y_min` and `y_max`
  - Formula: `y_min + (normalized_time * height_range)`
- **Z-axis:** Same as parent file (keeps chat in same depth plane)
- **Decay factor:** Calculated via `calculate_decay_factor()`

**Parameters:**
```python
def calculate_chat_positions(
    chats: List[Dict],              # Chat objects with id, parentId, lastActivity
    file_positions: Dict[str, Dict], # file_id -> {x, y, z}
    time_range: Optional[Tuple[datetime, datetime]] = None,  # Auto-computed if None
    y_min: float = 0,               # Min Y coordinate
    y_max: float = 500              # Max Y coordinate
) -> List[Dict]:
```

**Input Chat Format:**
```python
chat = {
    'id': 'chat-uuid-123',
    'parentId': 'file-uuid-456',  # Associated file
    'lastActivity': datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc),
    'name': 'Chat about X'  # Optional
}
```

**Output Format:**
```python
positioned_chat = {
    'id': 'chat-uuid-123',
    'parentId': 'file-uuid-456',
    'lastActivity': datetime(...),
    'name': 'Chat about X',
    'position': {
        'x': 110.0,        # Parent X + offset
        'y': 350.0,        # Timeline position
        'z': 50.0,         # Same as parent
        'decay_factor': 0.85  # Opacity factor
    }
}
```

## Usage Example

```python
from datetime import datetime, timezone, timedelta
from src.layout.knowledge_layout import calculate_chat_positions

# File positions from existing layout
file_positions = {
    'file-1': {'x': 100, 'y': 200, 'z': 50},
    'file-2': {'x': 150, 'y': 300, 'z': 50},
}

# Sample chats
chats = [
    {
        'id': 'chat-1',
        'parentId': 'file-1',
        'lastActivity': datetime.now(timezone.utc) - timedelta(days=1),
        'name': 'Recent discussion'
    },
    {
        'id': 'chat-2',
        'parentId': 'file-1',
        'lastActivity': datetime.now(timezone.utc) - timedelta(days=5),
        'name': 'Older discussion'
    },
    {
        'id': 'chat-3',
        'parentId': 'file-2',
        'lastActivity': datetime.now(timezone.utc) - timedelta(hours=2),
        'name': 'Very recent chat'
    },
]

# Calculate positions
positioned_chats = calculate_chat_positions(
    chats=chats,
    file_positions=file_positions,
    y_min=0,
    y_max=500
)

# Result:
# chat-1: x=110 (file-1.x + 10), y=high (recent), z=50, decay=high
# chat-2: x=112 (file-1.x + 12, staggered), y=medium (older), z=50, decay=medium
# chat-3: x=160 (file-2.x + 10), y=very_high (newest), z=50, decay=very_high
```

## Integration Points

### 1. Tree Routes (`src/api/routes/tree_routes.py`)

Add chat positioning to tree data endpoint:

```python
from src.layout.knowledge_layout import calculate_chat_positions

# After computing file positions
positioned_chats = calculate_chat_positions(
    chats=chat_data,
    file_positions=positions,
    y_min=0,
    y_max=500
)

# Add to response
return {
    'nodes': file_nodes,
    'edges': edges,
    'chats': positioned_chats  # Include positioned chats
}
```

### 2. Frontend Integration

TypeScript interface for positioned chat:

```typescript
interface PositionedChat {
  id: string;
  parentId: string;
  lastActivity: string;  // ISO datetime
  name?: string;
  position: {
    x: number;
    y: number;
    z: number;
    decay_factor: number;  // 0-1 for opacity
  };
}
```

Render with Three.js:

```typescript
chats.forEach(chat => {
  const opacity = chat.position.decay_factor;
  const material = new THREE.MeshBasicMaterial({
    color: 0x00ff00,
    transparent: true,
    opacity: opacity
  });

  const geometry = new THREE.SphereGeometry(2);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(
    chat.position.x,
    chat.position.y,
    chat.position.z
  );

  scene.add(mesh);
});
```

## Testing

```python
# Test decay calculation
from datetime import datetime, timezone, timedelta
from src.layout.knowledge_layout import calculate_decay_factor

# Test cases
now = datetime.now(timezone.utc)
test_cases = [
    (now, 1.0),                           # Just now = full brightness
    (now - timedelta(hours=84), 0.5),     # 3.5 days = 50% decay
    (now - timedelta(days=7), 0.0),       # 1 week = invisible
    (now - timedelta(days=14), 0.0),      # 2 weeks = still invisible
]

for timestamp, expected_decay in test_cases:
    actual = calculate_decay_factor(timestamp)
    assert abs(actual - expected_decay) < 0.01, f"Expected {expected_decay}, got {actual}"
```

## Markers

All code is marked with Phase 108.2 markers:

- `MARKER_108_CHAT_DECAY` - Decay factor calculation
- `MARKER_108_CHAT_POSITION` - Main positioning function

Search for these markers to find all related code:

```bash
grep -r "MARKER_108_CHAT" src/
```

## Next Steps

1. **A3:** Integrate with tree routes to include positioned chats in API response
2. **A4:** Add frontend rendering for chat nodes with decay-based opacity
3. **A5:** Add chat-to-file edge rendering (connecting lines)

---

**Status:** ✅ Complete
**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/layout/knowledge_layout.py`
**Lines:** 2239-2400 (approx)
