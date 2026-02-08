# Phase 123: Activity Glow System

## Summary
Unified activity tracking with visual glow feedback on file operations.

## Components

### 123.0 - ActivityHub (Backend)
**File:** `src/services/activity_hub.py`

Central singleton for activity tracking:
- `emit_glow()` / `emit_glow_sync()` - emit glow events
- Lazy decay: `intensity * (0.98 ^ seconds_elapsed)` - no background loop!
- LRU eviction at 100 nodes max

### 123.1 - Activity Sources (Backend)
All sources emit to ActivityHub:

| Marker | File | Reason | Intensity |
|--------|------|--------|-----------|
| 123.1A | file_watcher.py | `watcher:created/modified/deleted` | 0.5-0.9 |
| 123.1B | edit_file_tool.py | `mcp:edit_write/append` | 0.9 |
| 123.1C | read_file_tool.py | `mcp:read` | 0.4 |
| 123.1D | agent_pipeline.py | `vetka_out:created` | 1.0 |
| 123.1E | qdrant_updater.py | `scanner:indexed` | 0.6 |
| 123.1F | disk_artifact_service.py | `artifact:created` | 1.0 |

### 123.2 - Frontend Glow
| Marker | File | Function |
|--------|------|----------|
| 123.2A | useSocket.ts | `activity_glow` event listener |
| 123.2B | useStore.ts | `setNodeHeatScore(nodeId, intensity)` |
| 123.2C | FileCard.tsx | Heat-based color tint (#c8e4f4) |

### 123.4 - Label Fixes
| Marker | File | Change |
|--------|------|--------|
| 123.4A | labelScoring.ts | Hardcode for "vetka" root → score 0.99 |
| 123.4B | labelScoring.ts | Min 5 labels at LOD 0 (was 1) |
| 123.4C | FileCard.tsx | Smaller label sizes (font 12-26, less padding) |

## Data Flow
```
Source → ActivityHub.emit_glow_sync()
       → Socket.IO 'activity_glow'
       → useStore.setNodeHeatScore()
       → FileCard heatScore prop
       → color tint + label boost
```

## Color Scheme
Scanner Panel gradient: `#5c8aaa → #7ab3d4`
- `heatScore > 0.5` → `#c8e4f4` (subtle cold blue)
- `heatScore > 0.2` → `#e8f4fc` (very subtle blue)
- No activity → `#ffffff` (white)

## Label Sizes (Phase 123.4C)
- BASE_FONT_SIZE: 12px (was 14)
- MAX_FONT_SIZE: 26px (was 36)
- importanceBoost: 0-10px (was 0-16)
- padding: 4-8px vertical, 8-14px horizontal (reduced)
