# Phase 112: Unified Audit Report

**Date:** 2026-02-05
**Auditors:** Opus (lead), Haiku (reconnaissance), Grok (research)
**Status:** READY FOR IMPLEMENTATION

---

## Executive Summary

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| FPS | ~20 | 60+ | **3x improvement needed** |
| Draw calls | 2000+ | <100 | **20x reduction** |
| VRAM | ~2GB | <100MB | **20x reduction** |
| Re-renders | 30-50% wasted | <5% | **React.memo needed** |

---

## P0 Critical Issues (Fix First)

### 1. No Frustum Culling in App.tsx

**File:** `client/src/App.tsx:326`
**Marker:** `MARKER_111.21_FRUSTUM`
**Impact:** All 2000+ nodes rendered regardless of visibility

```tsx
// CURRENT (line 326):
{nodes.map((node) => (
  <FileCard key={node.id} ... />
))}

// FIX:
const visibleNodes = useMemo(() => {
  const frustum = new THREE.Frustum();
  const projScreenMatrix = new THREE.Matrix4();
  projScreenMatrix.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
  frustum.setFromProjectionMatrix(projScreenMatrix);

  return nodes.filter(node => {
    const point = new THREE.Vector3(node.position.x, node.position.y, node.position.z);
    return frustum.containsPoint(point);
  });
}, [nodes, camera.position, camera.quaternion]);

{visibleNodes.map((node) => (
  <FileCard key={node.id} ... />
))}
```

**Expected:** 50-80% reduction in rendered components

---

### 2. No React.memo on FileCard

**File:** `client/src/components/canvas/FileCard.tsx:1150-1155`
**Marker:** `MARKER_111.21_MEMO`
**Impact:** 30-50% unnecessary re-renders

```tsx
// CURRENT: No memoization
export function FileCard({ ... }) { ... }

// FIX (add at end of file):
export const MemoizedFileCard = React.memo(FileCard, (prev, next) => {
  return (
    prev.id === next.id &&
    prev.isSelected === next.isSelected &&
    prev.isHighlighted === next.isHighlighted &&
    prev.opacity === next.opacity &&
    prev.position[0] === next.position[0] &&
    prev.position[1] === next.position[1] &&
    prev.position[2] === next.position[2]
  );
});
```

**Expected:** 30-50% reduction in re-renders

---

### 3. No InstancedMesh

**File:** Need to create `client/src/components/canvas/InstancedFileCards.tsx`
**Reference:** `docs/112_ph/INSTANCED_MESH_IMPLEMENTATION.md`
**Impact:** 2000 draw calls instead of 1

**Expected:** 10-50x draw call reduction

---

### 4. useFrame runs per-node

**File:** `client/src/components/canvas/FileCard.tsx:234-284`
**Marker:** `MARKER_111.21_USEFRAME`
**Impact:** 2000+ distance calculations every 100ms

```tsx
// CURRENT: Each FileCard has its own useFrame
useFrame((state) => {
  if (now - lastLodUpdate.current < 0.1) return; // 100ms throttle
  // ... LOD calculation per node
});

// FIX: Move LOD calculation to parent (App.tsx) with batch processing
// See GROK_RESEARCH_ADVANCED.md #4 Foveated LOD
```

---

### 5. Texture useMemo has 14 dependencies

**File:** `client/src/components/canvas/FileCard.tsx:373-703`
**Marker:** `MARKER_111.21_TEXTURE`
**Impact:** Canvas texture recreated on every state change

```tsx
// CURRENT (line 703):
}, [name, path, type, isSelected, isHighlighted, isDragging, isHovered,
    isPinned, lodLevel, cardCategory, previewContent, metadata,
    visual_hints, artifactType, artifactStatus, artifactProgress]);

// FIX: Split into baseTexture (static) + overlayTexture (dynamic)
// Or use Texture Atlas (see INSTANCED_MESH_IMPLEMENTATION.md)
```

---

## P1 Medium Priority Issues

### 6. No frustum culling for edges

**File:** `client/src/components/canvas/TreeEdges.tsx`
**Impact:** All edges rendered even when off-screen

```tsx
// FIX: Filter edges by frustum before rendering
const visibleEdges = useMemo(() => {
  return edges.filter(edge => {
    const midpoint = new THREE.Vector3(
      (edge.start[0] + edge.end[0]) / 2,
      (edge.start[1] + edge.end[1]) / 2,
      (edge.start[2] + edge.end[2]) / 2
    );
    return frustum.containsPoint(midpoint);
  });
}, [edges, frustum]);
```

---

### 7. No React.memo on Edge components

**File:** `client/src/components/canvas/Edge.tsx`

---

## Files Requiring Changes

| Priority | File | Changes |
|----------|------|---------|
| **P0** | `App.tsx` | Add frustum culling, batch LOD |
| **P0** | `FileCard.tsx` | Add React.memo |
| **P0** | NEW `InstancedFileCards.tsx` | InstancedMesh implementation |
| **P1** | `TreeEdges.tsx` | Frustum culling for edges |
| **P1** | `Edge.tsx` | React.memo |
| **P2** | `useTreeData.ts` | WebWorker offload (>5k nodes) |

---

## Implementation Order

```
Phase 112.1: React.memo on FileCard + Edge (1 hour)
      ↓
Phase 112.2: Frustum culling in App.tsx (2 hours)
      ↓
Phase 112.3: Batch LOD in App.tsx (2 hours)
      ↓
Phase 112.4: InstancedMesh (1 day)
      ↓
Phase 112.5: Texture Atlas (1 day)
      ↓
Phase 112.6: Foveated LOD (4 hours)
```

---

## Validation Metrics

After each phase, measure:
1. FPS (React DevTools Profiler)
2. Draw calls (Three.js stats)
3. Re-render count (React Profiler)
4. Memory usage (Chrome DevTools)

**Target:** 60 FPS on 2000+ nodes

---

## Code Markers Found

| Marker | File | Line | Status |
|--------|------|------|--------|
| `MARKER_111.21_FRUSTUM` | App.tsx | 322 | PENDING |
| `MARKER_111.21_USEFRAME` | FileCard.tsx | 254 | PENDING |
| `MARKER_111.21_TEXTURE` | FileCard.tsx | 368 | PENDING |
| `MARKER_111.21_MEMO` | FileCard.tsx | 1150 | PENDING |
| `MARKER_111_FIX` | useTreeData.ts | 159 | DONE |
| `MARKER_111_DRAG` | FileCard.tsx | 749 | DONE |

---

## Related Documents

- `docs/112_ph/INSTANCED_MESH_IMPLEMENTATION.md` - InstancedMesh code
- `docs/112_ph/GROK_RESEARCH_ADVANCED.md` - Foveated LOD, Sugiyama, WebWorker
- `docs/112_ph/multylayot_vetka_grok_research.txt` - Original Grok research

---

## Approval

- [ ] P0 issues understood
- [ ] Implementation order approved
- [ ] Ready to begin Phase 112.1
