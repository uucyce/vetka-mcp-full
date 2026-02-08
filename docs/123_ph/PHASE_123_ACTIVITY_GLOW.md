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

## Glow Effect (Phase 123.8 — Radial Gradient Sprite)

**Based on Grok research:** Using Sprite with radial gradient + AdditiveBlending.

### Implementation
| Marker | File | Description |
|--------|------|-------------|
| 123.8A | FileCard.tsx | Import getWhiteGlowTexture |
| 123.8B | FileCard.tsx | Glow scale: 1.5x-2.5x card size |
| 123.8C | FileCard.tsx | Sprite with AdditiveBlending |
| 123.8D | FileCard.tsx | Clean white color for cards |

### Glow Texture (`utils/glowTexture.ts`)
- Radial gradient: bright center → transparent edges
- Gradient stops: 0→0.8α, 0.2→0.5α, 0.5→0.2α, 0.8→0.05α, 1→0α
- Cached singleton for performance
- Size: 128x128 canvas

### Visual Parameters
- **Threshold**: heatScore > 0.1 to show glow
- **Scale**: `1.5 + heatScore * 1.0` (1.5x to 2.5x card size)
- **Opacity**: `min(0.7, heatScore * 0.9)`
- **Blending**: THREE.AdditiveBlending (true glow effect)
- **Z-offset**: -0.3 (behind card)

### Performance (Grok analysis)
- **Load**: +1-3% (billboard sprites, no postprocessing)
- **Pros**: No deps, instant, works with frustum culling
- **Cons**: Not true blur (but looks good enough)

## Label Sizes (Phase 123.4C)
- BASE_FONT_SIZE: 12px (was 14)
- MAX_FONT_SIZE: 26px (was 36)
- importanceBoost: 0-10px (was 0-16)
- padding: 4-8px vertical, 8-14px horizontal (reduced)
