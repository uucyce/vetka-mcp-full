# 3D Performance Audit - VETKA UI

**Date:** 2026-02-04
**Problem:** UI lags with 2000+ nodes
**Auditor:** Claude Opus 4.5

---

## Executive Summary

The VETKA 3D interface has several performance bottlenecks that cause lag with large node counts (2000+). The main issues are:

1. **No instancing** - Each FileCard creates its own geometry/material
2. **No virtualization** - All nodes render regardless of visibility
3. **Heavy texture regeneration** - Canvas textures recreate on many state changes
4. **Store subscription pattern** - Components subscribe to entire objects, causing re-renders
5. **No React.memo** - FileCard and Edge components are not memoized

---

## Critical Issues (HIGH Impact)

| File | Line | Problem | Fix |
|------|------|---------|-----|
| `App.tsx` | 310-326 | All nodes rendered via `.map()` without virtualization or frustum culling | Implement view frustum culling - only render visible nodes |
| `FileCard.tsx` | 362-692 | **useMemo texture regeneration** has 14+ dependencies - recreates canvas on nearly every state change | Split into smaller useMemo blocks, cache canvas textures globally |
| `FileCard.tsx` | 233-278 | **useFrame** runs every frame for ALL 2000+ nodes - calculates distance + LOD | Throttle to every N frames, use spatial hashing for batched LOD |
| `FileCard.tsx` | 830-832 | No `React.memo` - component re-renders when parent re-renders | Wrap export with `React.memo` and custom comparator |
| `TreeEdges.tsx` | 16-19 | Subscribes to entire `nodes` and `edges` objects - any change triggers recalculation | Use selector functions to only subscribe to needed fields |
| `Edge.tsx` | 39-52 | Creates new THREE.Vector3, CatmullRomCurve3 on every render | No React.memo, geometry not reused |

---

## Medium Issues

| File | Line | Problem | Fix |
|------|------|---------|-----|
| `FileCard.tsx` | 281-294 | **useEffect for hover debounce** runs on `isHovered` and `type` change, but also clears content on every unhover | Keep preview content cached, only clear on unmount |
| `FileCard.tsx` | 300-345 | **useEffect for content loading** has 6 dependencies - may trigger unnecessary fetches | Reduce dependencies, move fetch logic outside effect |
| `CameraController.tsx` | 200-251 | useFrame animation runs even when no animation is active | Early return is present but still subscribed to frame loop |
| `useStore.ts` | 231-239 | `updateNodePosition` creates new objects on every update | Use immer or shallow merge for position updates |
| `useSocket.ts` | 432-451 | Token buffer flush uses `setState` which may cause cascading re-renders | Batch with `unstable_batchedUpdates` or use ref-based state |
| `MessageList.tsx` | 30-34 | `getMessageById` recreated on every render - passed as prop to all MessageBubbles | Wrap in useCallback or move to store |
| `MessageBubble.tsx` | 51 | No React.memo - each message re-renders when any message changes | Add React.memo with shallow comparison |
| `ChatPanel.tsx` | 129-144 | **soloModels useMemo** iterates all chatMessages on every render | Add early return if activeGroupId exists |
| `chatTreeStore.ts` | 64-80 | Uses immer `produce` for every update - overhead for simple updates | Consider shallow updates for hot paths |

---

## Low Issues

| File | Line | Problem | Fix |
|------|------|---------|-----|
| `FileCard.tsx` | 36-50 | Global style injection runs on every module load | Move to CSS file or check document.head existence |
| `FileCard.tsx` | 854-901 | Html component for hover preview renders even when not hovered (controlled by conditional) | Move inside memo or add key for proper mounting |
| `TreeEdges.tsx` | 81-119 | Edge color/lineWidth calculated inline for every edge | Pre-compute style objects in useMemo |
| `layout.ts` | 22-29 | Sorting inside layout calculation - O(n log n) per depth level | Pre-sort once if data is mostly static |

---

## Recommendations

### 1. Implement InstancedMesh for FileCards (HIGH PRIORITY)

```typescript
// Instead of 2000+ individual meshes:
<InstancedMesh ref={meshRef} args={[geometry, material, count]}>
  // Update matrix for each instance
</InstancedMesh>
```

**Expected improvement:** 10-50x reduction in draw calls

### 2. Add Frustum Culling / Virtualization

```typescript
// Only render nodes within camera view
const visibleNodes = useMemo(() => {
  const frustum = new THREE.Frustum();
  frustum.setFromProjectionMatrix(
    camera.projectionMatrix.clone().multiply(camera.matrixWorldInverse)
  );
  return nodes.filter(node => {
    const point = new THREE.Vector3(node.position.x, node.position.y, node.position.z);
    return frustum.containsPoint(point);
  });
}, [nodes, camera.position, camera.rotation]);
```

**Expected improvement:** 50-80% reduction in rendered components

### 3. Memoize FileCard Component

```typescript
export const FileCard = React.memo(function FileCard({ ... }: FileCardProps) {
  // component body
}, (prevProps, nextProps) => {
  // Custom comparison - only re-render if visual props changed
  return prevProps.id === nextProps.id &&
         prevProps.isSelected === nextProps.isSelected &&
         prevProps.isHighlighted === nextProps.isHighlighted &&
         prevProps.opacity === nextProps.opacity;
});
```

**Expected improvement:** 30-50% reduction in re-renders

### 4. Throttle LOD Updates in useFrame

```typescript
// Current: runs every frame for every node
useFrame((state) => {
  const now = state.clock.elapsedTime;
  if (now - lastLodUpdate.current < 0.1) return; // Already throttled to 100ms
  // ... but still runs for ALL nodes
});

// Better: Use spatial partitioning
// Batch LOD updates by region, not per-node
```

### 5. Optimize Store Subscriptions

```typescript
// Current (bad):
const nodes = useStore((state) => state.nodes);

// Better:
const nodeCount = useStore((state) => Object.keys(state.nodes).length);
const selectedNode = useStore((state) => state.selectedId ? state.nodes[state.selectedId] : null);
```

### 6. Split Heavy useMemo in FileCard.texture

```typescript
// Current: 14+ dependencies cause frequent recalculation
const texture = useMemo(() => { ... }, [name, path, type, isSelected, ...12 more]);

// Better: Split into layers
const baseTexture = useMemo(() => createBaseTexture(type, cardCategory), [type, cardCategory]);
const overlayTexture = useMemo(() => createOverlay(isSelected, isPinned), [isSelected, isPinned]);
```

### 7. Use React-Window for MessageList (if needed)

```typescript
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={containerHeight}
  itemCount={messages.length}
  itemSize={80}
>
  {({ index, style }) => (
    <MessageBubble key={messages[index].id} message={messages[index]} style={style} />
  )}
</FixedSizeList>
```

---

## Performance Metrics to Monitor

1. **FPS** - Target: 60fps, Current: likely <30fps with 2000+ nodes
2. **Draw calls** - Target: <100, Current: likely 2000+ (one per node)
3. **Re-renders** - Use React DevTools Profiler to track
4. **Memory** - Canvas textures consume ~1MB each at 256x128

---

## Implementation Priority

1. **Week 1:** Add React.memo to FileCard, Edge, MessageBubble
2. **Week 2:** Implement frustum culling in App.tsx
3. **Week 3:** Convert FileCard to InstancedMesh for geometry
4. **Week 4:** Optimize store subscriptions across components

---

## Files to Modify

| Priority | File | Changes |
|----------|------|---------|
| P0 | `client/src/components/canvas/FileCard.tsx` | Add React.memo, split texture useMemo, throttle useFrame |
| P0 | `client/src/App.tsx` | Add frustum culling before nodes.map() |
| P1 | `client/src/components/canvas/Edge.tsx` | Add React.memo, reuse geometry |
| P1 | `client/src/components/canvas/TreeEdges.tsx` | Optimize store subscriptions |
| P1 | `client/src/components/chat/MessageBubble.tsx` | Add React.memo |
| P2 | `client/src/hooks/useSocket.ts` | Batch token flush updates |
| P2 | `client/src/store/useStore.ts` | Optimize updateNodePosition |

---

## References

- Three.js Performance: https://threejs.org/docs/#manual/en/introduction/How-to-update-things
- R3F Performance: https://docs.pmnd.rs/react-three-fiber/advanced/scaling-performance
- React.memo: https://react.dev/reference/react/memo
- Zustand Selectors: https://docs.pmnd.rs/zustand/guides/auto-generating-selectors
