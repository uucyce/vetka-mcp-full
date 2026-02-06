# Phase 113.3: Labels Championship — IMPLEMENTATION PLAN v2

**Date:** 2026-02-05
**Status:** READY FOR IMPLEMENTATION (post-rollback fix)
**Commander:** Claude Opus 4.6
**Recon:** 9 Haiku scouts (2 rounds) + 3 Sonnet verifiers + Web research
**Rollback postmortem:** Applied

---

## 1. ROOT CAUSE ANALYSIS (Why v1 Failed)

| Problem | Cause | Fix in v2 |
|---------|-------|-----------|
| Labels always visible | `selectTopLabels()` called but result **not used** in FileCard | FileCard checks `selectedLabelIds.includes(id)` FIRST |
| Performance regression | `setLabelScores(Map)` in Zustand state every 200ms | Scores in `useRef(Map)`, NOT in state |
| Min threshold too low | Every folder score >= 0.25 passed visibility | Hard top-N cut: only 30 labels, period |
| Re-render cascade | New Map reference → prop change → all FileCards re-render | Pass `showLabel: boolean` prop (stable) |

---

## 2. ARCHITECTURE (v2 — Fixed)

```
┌─────────────────────────────────────────────┐
│  FrustumCulledNodes (App.tsx)                │
│  useFrame (200ms throttle)                   │
│                                              │
│  for (node of nodes) {                       │
│    if (frustum.containsPoint) {              │
│      lod = calculateAdaptiveLOD(...)         │  ← existing
│      score = computeScore(node, refs)        │  ← NEW (in-loop)
│      scoresRef.set(node.id, score)           │  ← ref, NOT state
│    }                                         │
│  }                                           │
│                                              │
│  // AFTER loop: top-N selection              │
│  top30 = sortByScore(scoresRef) → take 30   │
│  top30 += pinnedFileIds (always show)        │
│                                              │
│  // Only update store if SET changed         │
│  if (!arraysEqual(top30, prev)) {            │
│    setSelectedLabels(top30)  ← Zustand       │
│  }                                           │
└─────────────────────┬───────────────────────┘
                      │ showLabel={selectedLabelIds.has(id)}
                      ▼
┌─────────────────────────────────────────────┐
│  FileCard (memo + arePropsEqual)             │
│                                              │
│  Folder label IIFE:                          │
│    if (!showLabel && !isRoot) return null  ← HARD FILTER │
│    importance = depthScore*0.5+sizeScore*0.5 │  ← existing formula
│    labelZ = pos[2] + 1 + jitterZ(rank)       │  ← NEW anti-overlap
│    fontSize = f(importance, distance)         │  ← existing
│    render <Html>                              │
└─────────────────────────────────────────────┘
```

### Key Decisions:
1. **showLabel: boolean** prop — NOT numeric score. Prevents re-renders when score changes but visibility doesn't.
2. **selectedLabelIds** in Zustand — only updates when SET membership changes (shallow compare).
3. **Scores in useRef** — zero re-render cost. Used only for sorting + styling.
4. **Top-30 hard limit** — ~7.5% of 400 visible nodes. Google Maps shows ~5-10% of labels at any zoom.
5. **Pinned files override** — always in selected set.
6. **Root always visible** — depth === 0 bypasses filter.

---

## 3. MARKERS (Verified by Haiku + Sonnet, confirmed still valid)

### useStore.ts
| Marker | Line | Action |
|--------|------|--------|
| TreeState interface | 79-171 | Add `selectedLabelIds: string[]` after line 114 |
| Initial state | 204 | Add `selectedLabelIds: []` |
| Actions | 205 | Add `setSelectedLabels: (ids) => set({ selectedLabelIds: ids })` |
| pinnedFileIds | 111, 155-162 | Read in scoring loop for override |
| highlightedIds | 88, 124-125 | Read for search boost |

### App.tsx (FrustumCulledNodes)
| Marker | Line | Action |
|--------|------|--------|
| Refs section | 55-57 | Add `scoresRef = useRef(new Map())` |
| After throttle check | 63 | Clear scoresRef for new cycle |
| Inside for loop, after LOD (line 86) | 87 | Add scoring: `scoresRef.current.set(id, score)` |
| After for loop (line 88) | 89 | Top-N selection + store update |
| FileCard props (line 127) | 128 | Add `showLabel={selectedLabelIds.has(node.id)}` |
| Component needs store selector | 49 | Add `const selectedLabelIds = useStore(...)` |

### FileCard.tsx
| Marker | Line | Action |
|--------|------|--------|
| FileCardProps interface | 212 | Add `showLabel?: boolean` |
| Component destructure | 214-233 | Add `showLabel` |
| Folder label IIFE start | 1188 | Add: `if (!showLabel && depth > 0) return null` |
| labelZ (static) | 1229 | Replace with jitterZ formula |
| arePropsEqual | 1316 | Add `showLabel` comparison before `return true` |

### lod.ts
| Marker | Line | Action |
|--------|------|--------|
| smoothstep function | 18 | Change `function` to `export function` |

### NEW: client/src/utils/labelScoring.ts (~50 lines)
- `computeLabelScore(node, depth, childCount, isPinned, isHighlighted)` → number 0-1
- `arraysEqual(a, b)` → boolean (shallow set comparison for store update guard)
- `goldenAngleJitterZ(rank, total)` → number (Z-offset for anti-overlap)

---

## 4. SCORING FORMULA (Simplified from v1)

```typescript
function computeLabelScore(
  node: TreeNode,
  depth: number,
  childCount: number,
  isPinned: boolean,
  isHighlighted: boolean
): number {
  // Pinned = always top
  if (isPinned) return 1.0;

  // Type boost: folders > code > other
  const typeBoost = node.type === 'folder' ? 1.5
    : isCodeFile(node.name) ? 1.2
    : 0.8;

  // Depth: shallower = more important
  const depthScore = 1 / Math.sqrt(depth + 1);

  // Size: more children = more important
  const sizeScore = Math.min(1, Math.sqrt(childCount) / Math.sqrt(200));

  // Search boost
  const searchBoost = isHighlighted ? 0.3 : 0;

  // Weighted combination
  return Math.min(1.0,
    typeBoost / 1.5 * 0.4 +
    depthScore * 0.3 +
    sizeScore * 0.2 +
    searchBoost * 0.1
  );
}
```

**Deliberately OMITTED from v1:**
- Activity tracking (click/hover decay) — adds complexity, defer to Phase 113.4
- Hover boost (mouse proximity) — defer to Phase 113.4
- Semantic/Qdrant scoring — needs backend API, defer to Phase 114

**Rationale:** v1 failed because of too much at once. v2 does MINIMUM viable: type + depth + size + pinned + search. Activity and hover come after core works.

---

## 5. JITTERZ FORMULA

```typescript
function goldenAngleJitterZ(rank: number, total: number): number {
  // Golden angle: 137.5° = optimal non-overlapping distribution
  const angle = (rank * 137.508) * Math.PI / 180;
  const amplitude = 0.3 + (rank / Math.max(total, 1)) * 0.5;
  return Math.sin(angle) * amplitude;
}
```

- Range: -0.8 to +0.8 units
- Higher rank (lower score) → larger amplitude → pushed further
- Golden angle ensures no two labels get same Z-offset
- Deterministic: same rank → same offset (no flicker)

---

## 6. STORE UPDATE GUARD

```typescript
function arraysEqual(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  const setA = new Set(a);
  for (const id of b) {
    if (!setA.has(id)) return false;
  }
  return true;
}
```

Called BEFORE `setSelectedLabels()`:
```typescript
const prevIds = useStore.getState().selectedLabelIds;
if (!arraysEqual(newTop30, prevIds)) {
  useStore.getState().setSelectedLabels(newTop30);
}
```

This ensures store updates ONLY when the actual label set changes — not every 200ms cycle.

---

## 7. PERFORMANCE BUDGET

| Operation | Ops/node | 400 nodes | Time |
|-----------|----------|-----------|------|
| Score computation | 6 | 2400 | ~0.3ms |
| Sort top-30 | - | 1 sort | ~0.1ms |
| Array comparison | - | 30 items | ~0.01ms |
| Store update | - | conditional | ~0ms (usually) |
| **TOTAL** | | | **~0.4ms** |

Well within 2ms budget. The key: NO state updates in the hot path.

---

## 8. FileCard CONSUMERS (useShallow)

```typescript
// In FrustumCulledNodes or parent:
const selectedLabelIds = useStore(
  useShallow((state) => state.selectedLabelIds)
);
```

Per [Zustand docs](https://zustand.docs.pmnd.rs/guides/prevent-rerenders-with-use-shallow): `useShallow` does shallow comparison on arrays, preventing re-renders when array contents haven't changed.

Alternatively, convert to Set for O(1) lookup:
```typescript
const selectedLabelSet = useMemo(
  () => new Set(selectedLabelIds),
  [selectedLabelIds]
);
// Then: showLabel={selectedLabelSet.has(node.id)}
```

---

## 9. IMPLEMENTATION ORDER

### Step 1: labelScoring.ts (NEW file, ~50 lines)
- `computeLabelScore()`
- `goldenAngleJitterZ()`
- `arraysEqual()`
- `isCodeFile()` helper

### Step 2: lod.ts (1 line change)
- Export `smoothstep`

### Step 3: useStore.ts (+6 lines)
- `selectedLabelIds: string[]` in interface + initial state
- `setSelectedLabels()` action

### Step 4: App.tsx (+25 lines)
- `scoresRef`
- Scoring inside for loop
- Top-N selection after loop
- Store update with guard
- `showLabel` prop to FileCard

### Step 5: FileCard.tsx (+5 lines, ~2 modified)
- `showLabel` in props interface
- `showLabel` in destructuring
- `if (!showLabel && depth > 0) return null` at IIFE start
- JitterZ on labelZ line
- `showLabel` in arePropsEqual

### Step 6: Test
- Verify only 30 labels visible at overview zoom
- Verify pinned files always have labels
- Verify root always visible
- Verify no performance regression (60fps)
- Verify labels don't flicker on camera move

---

## 10. RISK MATRIX

| Risk | Level | Mitigation |
|------|-------|------------|
| Store churn on fast camera | LOW | arraysEqual guard + top-N rarely changes |
| children undefined | LOW | `node.children?.length ?? 0` |
| Flicker on threshold | LOW | Top-30 is stable — only edges of set flicker |
| Hysteresis (edge labels) | LOW | Accept for v2, add in v2.1 if needed |
| arePropsEqual miss | ELIMINATED | Boolean showLabel, trivial comparison |

---

## 11. NOT DOING (Deferred)

- Activity tracking (click/hover decay) → Phase 113.4
- Hover proximity boost → Phase 113.4
- Semantic/Qdrant scoring → Phase 114
- CAM integration → Phase 114
- useHoverBoost.ts → Phase 113.4
- Hysteresis (label edge stability) → Phase 113.3.1 if needed

---

## 12. WEB RESEARCH FINDINGS

### drei Html at scale
Per [R3F Discussion #3130](https://github.com/pmndrs/react-three-fiber/discussions/3130): Html component is NOT performant for large numbers. **Top-N selection is the correct approach** — render only what matters.

### Label anti-overlap
Per [Three.js manual](https://threejs.org/manual/en/align-html-elements-to-3d.html): HTML elements positioned to match 3D scene. Z-offset via position prop. Golden angle provides mathematically optimal non-repeating distribution.

### Zustand array comparison
Per [Zustand docs](https://zustand.docs.pmnd.rs/guides/prevent-rerenders-with-use-shallow): `useShallow` wraps selectors returning arrays/objects. Prevents re-renders when contents haven't changed.

---

**STATUS: PLAN COMPLETE. MARKERS VALIDATED. READY FOR IMPLEMENTATION.**

*Total changes: ~50 new lines (labelScoring.ts) + ~35 modified lines across 4 files.*
*Zero new dependencies. Minimum viable approach.*
