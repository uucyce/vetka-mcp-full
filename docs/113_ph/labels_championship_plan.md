# Phase 112.8+ / 113: Labels Championship

## Status: TODO (Planned)
**Prepared by:** Grok + Claude collaboration
**Date:** 2026-02-05
**Depends on:** Phase 112.6-112.8 (Adaptive Foveated Spot) - COMPLETED

---

## Problem Statement

Labels (file names, folder names) compete for visibility when:
1. Multiple nodes are close together
2. User zooms out (overview mode)
3. Camera moves (labels flicker/overlap)

Current behavior: All labels render at same priority, causing visual chaos.

---

## Solution: Semantic Scoring + Priority System

### Core Idea
Each label gets a **semantic score** (0-1) based on:
- Qdrant similarity to current context
- CAM (Context-Aware Memory) activations
- User attention patterns (mouse proximity, recent clicks)
- File type importance (folders > files, code > assets)

Higher score = higher rendering priority (larger font, no transparency, survives culling).

---

## Architecture

### 1. Semantic Scoring Engine

```typescript
// client/src/utils/labelScoring.ts

interface LabelScore {
  nodeId: string;
  score: number;        // 0-1 final score
  components: {
    semantic: number;   // Qdrant similarity
    cam: number;        // CAM activation level
    attention: number;  // Mouse proximity + recency
    typeBoost: number;  // Folder/file type multiplier
  };
}

export function calculateLabelScore(
  node: TreeNode,
  context: {
    qdrantSimilarity: number;  // From MCP vetka_search_semantic
    camActivation: number;     // From MCP vetka_get_memory_summary
    mouseDistance: number;     // Screen-space distance to cursor
    lastInteraction: number;   // Timestamp of last click/hover
    currentTime: number;
  }
): LabelScore {
  const semantic = context.qdrantSimilarity;  // 0-1
  const cam = context.camActivation;          // 0-1

  // Attention decays over time (half-life: 30 seconds)
  const timeSinceInteraction = (context.currentTime - context.lastInteraction) / 1000;
  const recencyFactor = Math.exp(-timeSinceInteraction / 30);

  // Mouse proximity (inverse distance, capped)
  const proximityFactor = Math.max(0, 1 - context.mouseDistance / 200);

  const attention = Math.max(recencyFactor, proximityFactor);

  // Type boost: folders=1.5x, code=1.2x, assets=0.8x
  const typeBoost = node.type === 'folder' ? 1.5 :
                    ['ts', 'tsx', 'py', 'js'].includes(node.extension || '') ? 1.2 : 0.8;

  // Weighted combination
  const score = Math.min(1, (
    semantic * 0.35 +
    cam * 0.25 +
    attention * 0.25 +
    (typeBoost - 1) * 0.15  // Normalized boost
  ));

  return {
    nodeId: node.id,
    score,
    components: { semantic, cam, attention, typeBoost }
  };
}
```

### 2. JitterZ Anti-Overlap

Prevent labels from z-fighting by assigning unique Z offsets based on score rank:

```typescript
// In FileCard.tsx or new LabelRenderer.tsx

function calculateJitterZ(
  scoreRank: number,    // 0 = highest score, 1 = second, etc.
  totalLabels: number,
  baseZ: number
): number {
  // Higher ranked labels get closer to camera
  const zOffset = (scoreRank / totalLabels) * 5;  // 0-5 units spread
  return baseZ - zOffset;  // Negative = closer to camera
}
```

### 3. Mouse Hover Boost

Immediate score boost when mouse is near a node:

```typescript
// In App.tsx or dedicated hook

function useHoverBoost(nodes: TreeNode[], mousePosition: Vector2) {
  const [boostedNodes, setBoostedNodes] = useState<Set<string>>(new Set());

  useFrame(() => {
    const nearbyNodes = nodes.filter(node => {
      const screenPos = projectToScreen(node.position, camera);
      const dist = screenPos.distanceTo(mousePosition);
      return dist < 50;  // 50px radius
    });

    setBoostedNodes(new Set(nearbyNodes.map(n => n.id)));
  });

  return boostedNodes;
}
```

### 4. Label LOD System

Different label rendering based on score + distance:

| LOD Level | Score Range | Rendering |
|-----------|-------------|-----------|
| 3 (Full)  | 0.8-1.0     | Full name, bold, no fade |
| 2 (Medium)| 0.5-0.8     | Full name, normal, slight fade |
| 1 (Mini)  | 0.2-0.5     | Truncated (8 chars), small |
| 0 (Hidden)| 0-0.2       | No label (icon only) |

```typescript
function getLabelLOD(score: number, distanceLOD: number): number {
  // Combine semantic score with distance LOD
  const combined = (score * 0.6 + distanceLOD / 9 * 0.4);

  if (combined >= 0.7) return 3;
  if (combined >= 0.4) return 2;
  if (combined >= 0.15) return 1;
  return 0;
}
```

---

## Integration Points

### Backend (MCP Tools)

1. **vetka_search_semantic** - Get Qdrant similarity scores
2. **vetka_get_memory_summary** - Get CAM activations
3. **vetka_get_user_preferences** - Personalization weights

### Frontend Files

| File | Changes |
|------|---------|
| `client/src/utils/labelScoring.ts` | NEW - Scoring engine |
| `client/src/components/canvas/FileCard.tsx` | Label LOD integration |
| `client/src/App.tsx` | Batch score calculation |
| `client/src/hooks/useHoverBoost.ts` | NEW - Mouse proximity hook |

---

## Implementation Phases

### Phase A: Basic Scoring (1-2 hours)
1. Create `labelScoring.ts` with type boost only
2. Integrate with FileCard.tsx label rendering
3. Test: Folders should always show labels before files

### Phase B: Semantic Integration (2-4 hours)
1. Add MCP calls for Qdrant similarity
2. Batch scoring in App.tsx (throttled, 500ms)
3. Test: Search-relevant nodes highlight

### Phase C: JitterZ + Hover (1-2 hours)
1. Implement Z-offset calculation
2. Add mouse proximity detection
3. Test: No label overlaps, hover reveals labels

### Phase D: CAM Integration (2-4 hours)
1. Connect to CAM activations from MCP
2. Add recency decay
3. Test: Recently viewed nodes stay visible

---

## Performance Considerations

1. **Batch scoring**: Calculate all scores every 500ms, not per-frame
2. **Spatial indexing**: Use octree/BVH for mouse proximity checks
3. **Score caching**: Only recalculate on camera move or context change
4. **Async MCP calls**: Don't block render for Qdrant/CAM data

---

## Testing Checklist

- [ ] Folders always show labels before files at same distance
- [ ] Search results highlight their labels
- [ ] Mouse hover reveals nearby labels immediately
- [ ] No label z-fighting or overlap
- [ ] Labels fade smoothly (no popping)
- [ ] Performance: 60 FPS with 2000+ nodes
- [ ] Works on mobile (larger touch zones)

---

## Related Files

- `docs/112_ph/multylayot_vetka_grok_research.txt` - Original Grok audit
- `client/src/utils/lod.ts` - Adaptive Foveated LOD (Phase 112.6-112.8)
- `docs/113_ph/113_ph_roadmap_grok.txt` - Main Phase 113 roadmap

---

## Notes from Grok

> "Labels Championship - это не просто визуальная оптимизация, а **семантический UI**.
> Qdrant + CAM дают контекст, который label система использует для **умного приоритизирования**.
> Результат: пользователь видит важное, даже не осознавая что система решает за него."

---

*Prepared for Phase 113 implementation. Continue in new chat session.*
