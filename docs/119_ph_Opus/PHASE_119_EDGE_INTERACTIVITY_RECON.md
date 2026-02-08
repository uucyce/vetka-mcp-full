# Phase 119: Edge Interactivity — Recon Report

**Date:** 2026-02-08
**Status:** RECON COMPLETE
**Task:** Добавить интерактивность edges (связей) — клик, double-click, Shift+Click pin

---

## Problem Statement

Edges (связи между узлами) сейчас НЕ интерактивны — только визуальные линии.
Нужно:
1. **Расширить hitbox** для лёгкого клика по тонким линиям
2. **Double-click** на edge = zoom камеры к обоим узлам
3. **Shift+Click** на edge = pin to chat context
4. **Hover** на edge = подсветка разветвлений (killer feature для Knowledge Mode)

---

## Current Architecture

### Files Involved

| File | Purpose | Key Lines |
|------|---------|-----------|
| `client/src/components/canvas/Edge.tsx` | Рендер одного edge | 11-84 |
| `client/src/components/canvas/TreeEdges.tsx` | Рендер всех edges | 17-185 |
| `client/src/store/useStore.ts` | State management | 111, 165 |

### Current Rendering

**Edge.tsx** использует `@react-three/drei Line`:
```tsx
<Line
  points={points}
  color={color}
  lineWidth={lineWidth}
  transparent={opacity < 1}
  opacity={opacity}
/>
```

**Проблема:** `Line` компонент НЕ поддерживает raycast/click events.

---

## Key Discovery: MeshLine Already Installed!

**Package:** `meshline@3.3.1` (уже в package.json!)

MeshLine — это triangle-strip замена для THREE.Line с **built-in raycasting**.

### Преимущества:
- Поддерживает `onClick`, `onPointerOver` из коробки
- Увеличенный hitbox (triangles vs thin line)
- Работает на всех платформах (WebGL 2 compatible)
- Уже установлен — 0 новых зависимостей

---

## Markers Added (MARKER_119.x)

### Edge.tsx

| Marker | Line | Description |
|--------|------|-------------|
| `MARKER_119.1A` | ~14 | Edge component — uses drei Line (NON-INTERACTIVE) |
| `MARKER_119.1B` | ~60 | Line render — NO onClick support |

### TreeEdges.tsx

| Marker | Line | Description |
|--------|------|-------------|
| `MARKER_119.2A` | ~16 | TreeEdges — renders all edges, NON-INTERACTIVE |
| `MARKER_119.2B` | ~176 | Edge render loop — add callbacks when ready |

### useStore.ts

| Marker | Line | Description |
|--------|------|-------------|
| `MARKER_119.3A` | ~113 | TODO: pinnedEdgeIds, selectedEdgeId |
| `MARKER_119.3B` | ~168 | TODO: pinEdgeSmart(), selectEdge() |

---

## Implementation Plan

### Step 1: Replace Line with MeshLine (Edge.tsx)

```tsx
// BEFORE
import { Line } from '@react-three/drei';

// AFTER
import { MeshLineGeometry, MeshLineMaterial, raycast } from 'meshline';
import { extend } from '@react-three/fiber';

extend({ MeshLineGeometry, MeshLineMaterial });
```

### Step 2: Update EdgeProps

```tsx
interface EdgeProps {
  // Existing
  start: [number, number, number];
  end: [number, number, number];
  color?: string;
  lineWidth?: number;
  opacity?: number;

  // NEW — Phase 119
  edgeId: string;
  onClick?: (edgeId: string) => void;
  onDoubleClick?: (edgeId: string) => void;
  onShiftClick?: (edgeId: string) => void;
  onHover?: (edgeId: string | null) => void;
}
```

### Step 3: Render with MeshLine

```tsx
<mesh
  raycast={raycast}
  onClick={(e) => {
    e.stopPropagation();
    if (e.shiftKey) {
      onShiftClick?.(edgeId);
    } else {
      onClick?.(edgeId);
    }
  }}
  onDoubleClick={(e) => {
    e.stopPropagation();
    onDoubleClick?.(edgeId);
  }}
  onPointerOver={() => onHover?.(edgeId)}
  onPointerOut={() => onHover?.(null)}
>
  <meshLineGeometry points={points} />
  <meshLineMaterial
    lineWidth={lineWidth * 3}  // Wider hitbox!
    color={color}
    opacity={opacity}
    transparent={opacity < 1}
    resolution={new THREE.Vector2(width, height)}
  />
</mesh>
```

### Step 4: Store Additions (useStore.ts)

```typescript
// State
pinnedEdgeIds: string[];
selectedEdgeId: string | null;
hoveredEdgeId: string | null;

// Actions
selectEdge: (edgeId: string | null) => void;
pinEdgeSmart: (edgeId: string) => void;
togglePinEdge: (edgeId: string) => void;
clearPinnedEdges: () => void;
```

### Step 5: Pin Logic

```typescript
pinEdgeSmart: (edgeId) => set((state) => {
  const edge = state.edges.find(e => e.id === edgeId);
  if (!edge) return state;

  // Pin both connected nodes
  const newPinned = new Set(state.pinnedFileIds);

  // Add source node
  const sourceNode = state.nodes[edge.source];
  if (sourceNode?.type === 'file') {
    newPinned.add(edge.source);
  }

  // Add target node
  const targetNode = state.nodes[edge.target];
  if (targetNode?.type === 'file') {
    newPinned.add(edge.target);
  }

  // Also pin edge itself
  const newPinnedEdges = new Set(state.pinnedEdgeIds);
  newPinnedEdges.add(edgeId);

  return {
    pinnedFileIds: [...newPinned],
    pinnedEdgeIds: [...newPinnedEdges]
  };
}),
```

### Step 6: Highlight Branches on Hover

```typescript
// When edge is hovered, highlight all connected branches
highlightBranch: (edgeId) => set((state) => {
  const edge = state.edges.find(e => e.id === edgeId);
  if (!edge) return state;

  // Find all edges in the same branch (recursive)
  const branchEdgeIds = new Set<string>();
  const findBranch = (nodeId: string) => {
    state.edges.forEach(e => {
      if (e.source === nodeId || e.target === nodeId) {
        if (!branchEdgeIds.has(e.id)) {
          branchEdgeIds.add(e.id);
          // Recurse to find full branch
          findBranch(e.source === nodeId ? e.target : e.source);
        }
      }
    });
  };

  findBranch(edge.source);
  findBranch(edge.target);

  return { highlightedEdgeIds: [...branchEdgeIds] };
}),
```

---

## Target Interactions

| Action | Target | Result |
|--------|--------|--------|
| **Click** | Edge | Select edge (highlight) |
| **Double-click** | Edge | Zoom camera to show both nodes |
| **Shift+Click** | Edge | Pin edge + both nodes to chat |
| **Hover** | Edge | Highlight all connected branches |

---

## Complexity Assessment

| Aspect | Level | Notes |
|--------|-------|-------|
| Code changes | MEDIUM | 3-4 files, ~150 lines |
| Risk | LOW | MeshLine already installed |
| Performance | WATCH | Test with 100+ edges |
| Testing | Manual | Hover, click, double-click, shift+click |

---

## Files to Modify

1. **Edge.tsx**
   - Replace @react-three/drei Line with meshline
   - Add click handlers

2. **TreeEdges.tsx**
   - Pass edge ID and callbacks to Edge
   - Handle hover state for branch highlighting

3. **useStore.ts**
   - Add pinnedEdgeIds, selectedEdgeId, hoveredEdgeId
   - Add pinEdgeSmart, selectEdge, highlightBranch

4. **useSocket.ts** (later)
   - Send pinned edges to chat context

---

## Search Commands for Verification

```bash
# Find all markers
grep -rn "MARKER_119" client/src/

# Check meshline installation
cat client/package.json | grep meshline

# Find Edge usages
grep -rn "import.*Edge" client/src/
```

---

## Killer Feature: Branch Highlighting

При hover на edge подсвечиваются ВСЕ связанные ветки — это будет основа для:
- **Knowledge Mode** — граф связей внутри папки
- **Dependency visualization** — кто от кого зависит
- **Navigation** — "покажи мне эту ветку целиком"

---

## Next Steps

1. User approval of plan
2. Implement MeshLine replacement (Edge.tsx)
3. Add store state for edges
4. Test with real tree (100+ edges)
5. Add branch highlighting on hover

---

**Report generated by:** Opus 4.5 (Recon Phase)
**Haiku scouts:** 3 parallel agents
**Duration:** ~3 minutes
