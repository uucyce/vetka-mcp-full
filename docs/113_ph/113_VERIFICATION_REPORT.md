# Phase 113.3: Labels Championship - Unified Verification Report

**Date:** 2026-02-05
**Phase:** Recon Complete -> Ready for Implementation
**Scouts:** 9 Haiku (H1-H9) | **Verifiers:** 3 Sonnet (S1-S3)

---

## Executive Summary

All 9 Haiku scouts placed markers with **100% line-number accuracy** across 7 source files. 3 Sonnet verifiers confirmed all markers and identified **1 critical architectural revision** and **3 minor adjustments**. The codebase is fully mapped and ready for implementation.

**Verdict: APPROVED WITH MODIFICATIONS**

---

## 1. Critical Architectural Revision

### activityMap: Local Ref, NOT Zustand Store

**S1 identified a critical issue:** Putting `activityMap: Map<string, ActivityData>` in the Zustand store would cause:
- **Re-render cascades:** Map reference equality always fails -> every subscriber re-renders on any activity update
- **Serialization failure:** Map is not serializable -> breaks DevTools, persistence, time-travel
- **200ms update storm:** Activity decay recalculated every cycle -> constant store mutations

**Solution:** Use `useRef(new Map())` inside `FrustumCulledNodes`:
```typescript
// In FrustumCulledNodes component
const activityRef = useRef(new Map<string, { lastClick: number; lastHover: number }>());
```

**Store changes (minimal):**
- Add `selectedLabelIds: string[]` to state (line 171) - for persistence only
- Add `setSelectedLabels(ids: string[])` action (line 416) - batch update
- NO activityMap, NO scoring data in store

---

## 2. Verified Markers (All 9 Scouts)

### H1: Store (useStore.ts) - CONFIRMED
| Marker | Line | Content | Status |
|--------|------|---------|--------|
| H1-A | 171 | End of TreeState interface | Verified |
| H1-B | 416 | After setGrabMode action | Verified |
| H1-F | - | Store uses raw set() (no immer) | Verified |
| H1-G | 175 | Only 1 cleanup (position timer) | Verified |

### H2: App.tsx (FrustumCulledNodes) - CONFIRMED
| Marker | Line | Content | Status |
|--------|------|---------|--------|
| H2-A | 77 | `for (const node of nodes)` main loop | Verified |
| H2-B | 85 | `calculateAdaptiveLODWithFloor()` call | Verified |
| H2-C | 106-108 | `visibleNodes` useMemo | Verified |
| H2-D | 112-129 | FileCard rendering (13 props) | Verified |
| H2-E | 42-47 | FrustumCulledNodesProps interface | Verified |
| H2-F | 62 | 200ms throttle check | Verified |

### H3: FileCard Folder Labels - CONFIRMED
| Marker | Line | Content | Status |
|--------|------|---------|--------|
| H3-A | 1229 | `labelZ = position[2] + 1` (static) | Verified |
| H3-B | 1232-1233 | Html position array | Verified |
| H3-C | 1240 | `zIndexRange={[50, 0]}` | Verified |
| H3-D | 1219-1225 | fontSize calculation | Verified |
| H3-G | 1243-1253 | Score-driven style object | Verified |

### H4: FileCard Props - CONFIRMED
| Marker | Line | Content | Status |
|--------|------|---------|--------|
| H4-A | 175-212 | FileCardProps interface | Verified |
| H4-B | 214 | Component function signature | Verified |
| H4-H | 1320 | `memo(FileCardComponent, arePropsEqual)` | Verified |

### H5: LOD Utils (lod.ts) - CONFIRMED
| Marker | Line | Content | Status |
|--------|------|---------|--------|
| H5-A | 29,88,139 | 3 exported functions | Verified |
| H5-C | 30-39 | Distance thresholds (LOD0-9) | Verified |
| H5-D | 100 | Screen-space projection | Verified |
| H5-F | 18-21 | smoothstep (not exported) | Verified |

### H6: useSearch Hook - CONFIRMED
| Marker | Line | Content | Status |
|--------|------|---------|--------|
| H6-C | 107 | SearchResult.relevance: number | Verified |
| H6-F | 37,74 | results: SearchResult[] return | Verified |

### H7: TreeNode Types - CONFIRMED
| Marker | Line | Content | Status |
|--------|------|---------|--------|
| H7-B | 21 | type: file/folder/chat/artifact | Verified |
| H7-C | 27 | extension?: string (optional) | Verified |
| H7-D | 85-94 | getFileCategory() in FileCard | Verified |
| H7-G | 34 | children?: string[] (optional) | Verified |

### H8: Interaction Points - CONFIRMED
| Marker | Line | Content | Status |
|--------|------|---------|--------|
| H8-A | 960 | `onPointerOver={() => setIsHovered(true)}` | Verified |
| H8-C | 942 | `onClick?.()` | Verified |

### H9: Performance - CONFIRMED WITH REVISION
| Marker | Content | Status |
|--------|---------|--------|
| H9-A | 200ms throttle at line 62 | Verified |
| H9-B | 4 operations per visible node | Verified |
| H9-F | 0.5-1ms estimate | **Revised to 2-4ms** |
| H9-I | Fresh Map/Set each cycle (no leak) | Verified |

---

## 3. Sonnet Verifier Findings

### S1: Store + App.tsx Architecture
- **Verdict:** APPROVED WITH MODIFICATIONS
- **Critical:** activityMap must be local ref, not Zustand state
- **Risk:** Map reference equality + serialization issues
- **Solution:** `useRef(new Map())` in FrustumCulledNodes

### S2: FileCard Markers
- **Verdict:** APPROVED WITH MINOR ADJUSTMENTS
- **Missing:** `children.length` comparison in `arePropsEqual` (line 1279)
- **Required:** Add `labelScore` prop to interface + comparator
- **Note:** Throttle hover activity updates (100-300ms debounce)

### S3: Utils + Performance
- **Verdict:** APPROVED WITH MINOR REVISIONS
- **Required:** Export `smoothstep` from lod.ts (1 line)
- **Revised:** Performance estimate 0.5-1ms -> 2-4ms (still acceptable)
- **Suggested:** Adjust scoring formula weights

---

## 4. Final Scoring Formula

### Original Plan
```
Type 30% + Depth/Size 20% + Activity 25% + Search 15% + Pinned 10%
```

### Revised (Post-Verification)
```
score = (
  typeWeight    * 0.25 +   // Semantic relevance (folder type priority)
  activityWeight * 0.25 +  // Recency: e^(-t/30) decay
  depthSizeWeight * 0.20 + // Hierarchy depth + child count
  searchWeight   * 0.15 +  // Search result relevance boost
  pinnedWeight   * 0.15    // Manual pin override
)
```

**Rationale:** Balanced 5-factor formula. Activity and Type equally weighted as primary signals. Pinned kept meaningful at 15% (user intent matters). Hover proximity handled separately via JitterZ visual boost, not formula integration.

---

## 5. Implementation Plan (Post-Report)

### Files to Modify (3)
1. **`client/src/store/useStore.ts`** (~8 lines)
   - Add `selectedLabelIds: string[]` to TreeState (line 171)
   - Add `setSelectedLabels()` action (line 416)

2. **`client/src/App.tsx`** (~30 lines)
   - Add `activityRef = useRef(new Map())` in FrustumCulledNodes
   - Add scoring loop inside 200ms batch cycle (after line 85)
   - Pass `labelScore` prop to FileCard (line 112-129)

3. **`client/src/components/canvas/FileCard.tsx`** (~25 lines)
   - Add `labelScore?: number` to FileCardProps (line 211)
   - Add `labelScore` to arePropsEqual (line 1313)
   - Add `children.length` to arePropsEqual (line 1295)
   - Replace static `labelZ` with JitterZ (line 1229)
   - Use `labelScore` in importance calculation (line 1208)
   - Add activity tracking calls at click/hover (lines 942, 960)

### Files to Create (1)
4. **`client/src/utils/labelScoring.ts`** (~80 lines)
   - `computeLabelScore(node, activityData, searchResults, pinnedIds)`
   - `goldenAngleJitterZ(index, count)` - anti-overlap Z-offset
   - Import `smoothstep` from lod.ts (after exporting it)

### Files to Touch (1)
5. **`client/src/utils/lod.ts`** (~1 line)
   - Export `smoothstep` function

### Total: ~145 lines across 5 files

---

## 6. Risk Matrix

| Risk | Level | Mitigation |
|------|-------|------------|
| Store re-render cascade | ELIMINATED | activityMap as local ref |
| Hover event spam | LOW | Throttle in onPointerOver (200ms) |
| Performance regression | LOW | 2-4ms in 200ms budget (98% headroom) |
| Memo comparator miss | FIXED | Add children.length + labelScore |
| undefined children | LOW | Use `node.children ?? []` pattern |
| Large tree (>2000 nodes) | MEDIUM | Monitor, increase throttle if needed |

---

## 7. Research Notes (Web Search Fallback)

Grok API was unavailable (400 errors). Web search provided:
- **Three.js Html overlap:** drei `<Html>` uses CSS z-index, controllable via `zIndexRange`
- **Golden angle spiral:** 137.5 degrees produces optimal non-overlapping distribution
- **Exponential decay:** `e^(-t/tau)` with tau=30s gives natural recency falloff
- **smoothstep:** Hermite interpolation `3t^2 - 2t^3`, already in lod.ts

---

**STATUS: REPORT COMPLETE. READY FOR IMPLEMENTATION.**
