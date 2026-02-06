# Phase 113.4: Label Championship — Implementation Report

**Date:** 2025-02-06
**Status:** Implemented + Hotfix Applied
**Files Changed:** `App.tsx`, `labelScoring.ts`, `FileCard.tsx`, `useStore.ts`, `DevPanel.tsx`

---

## 1. Summary

Phase 113.4 connected the previously unconnected `labelScoring.ts` (216 lines, written in Phase 113.3 but never imported) into the rendering pipeline. The system implements Google Maps-style adaptive label visibility for 3D folder nodes — fewer labels at overview, more when zoomed in.

**Key metric:** 2275 nodes, ~400 visible at overview. Labels should scale from 1 (overview) to 25 (close-up).

---

## 2. Architecture

```
useFrame (every 200ms, inside FrustumCulledNodes)
  ├── Frustum culling → visible Set
  ├── LOD calculation → lodLevels Map
  └── Phase 113.4: Label Championship
      ├── computeLabelScore() for each visible folder → scoresRef Map
      ├── applyHysteresis(current, prev) → smoothed Map
      ├── zoomLevel from camera ↔ OrbitControls.target distance
      ├── selectTopLabels(smoothed, pinned, visibleCount, zoom) → string[]
      ├── Set comparison (labelsChanged?)
      └── IF changed: labelSetRef = newSet, setLabelGeneration++

React render:
  ├── currentLabelSet = useMemo(() => labelSetRef.current, [labelGeneration])
  └── FileCard showLabel={currentLabelSet.has(node.id)}
      └── arePropsEqual checks showLabel → only changed cards re-render
```

---

## 3. The Formula Search — Detailed Journey

### 3.1 Initial Approach: Approach A vs B

**Approach A (Nth-Label skipFactor):** Grok's original proposal. Show every Nth label based on siblings index.
- Requires `indexInSiblings` — data NOT available in frontend
- Requires sorting siblings — O(N log N) per group
- Position-dependent — breaks on camera movement

**Approach B (Score-based from labelScoring.ts):** Already written, 216 lines, just needs connecting.
- Uses `computeLabelScore()` with weighted formula
- Adaptive top-N selection via `selectTopLabels()`
- Hysteresis anti-flicker via `applyHysteresis()`
- **Chosen by 3 Sonnet verifiers unanimously**

### 3.2 The Performance Disaster (v1)

First implementation caused **severe lag** ("жутко тормозит"). Root causes found:

| Bug | Complexity | Impact |
|-----|-----------|--------|
| `selectedLabelIds.includes(node.id)` in render | O(N) per node = O(N²) total | ~400 nodes × ~20 labels = 8000 comparisons per frame |
| `useStore(s => s.selectedLabelIds)` subscription | Re-render trigger | ALL 400+ FileCards re-rendered every 200ms |
| `pinnedFileIds.includes(node.id)` in scoring | O(N) per folder | ~100 folders × ~5 pinned = 500 comparisons per tick |
| `camera.position.length()` for zoom | Wrong metric | Distance to origin, not to look-at target |
| Linear top-N formula | Too generous | 16-23 labels at overview instead of 1-5 |

### 3.3 Performance Fix (v2)

| Fix | Before | After |
|-----|--------|-------|
| Label lookup | `array.includes()` O(N) | `Set.has()` O(1) via `useMemo` |
| Store subscription | `useStore(s => s.selectedLabelIds)` → full re-render | `labelSetRef` + `labelGeneration` counter → minimal re-render |
| Pinned lookup | `pinnedFileIds.includes()` O(N) | `new Set(pinnedFileIds)` O(1) |
| Zoom calculation | `camera.position.length()` (distance to origin) | `camera.position.distanceTo(orbitControls.target)` |
| Re-render scope | ALL FileCards on every label change | Only FileCards whose `showLabel` actually changed (via `arePropsEqual`) |

### 3.4 The Root Chain Problem

After performance fix, labels still stacked at overview. Root cause: the filesystem path chain `VETKA → Users → danilagulin → Documents → VETKA_Project → vetka_live_03` all had depth 0-5 with high `depthScore`.

**Original formula** (v1):
```
score = (typeBoost/1.5)*0.4 + depthScore*0.3 + sizeScore*0.2 + searchBoost*0.1
```

For VETKA (depth=0, 1 child): `1.0*0.4 + 1.0*0.3 + 0.07*0.2 + 0 = 0.71` — very high!

The root chain got high scores because depthScore dominated and they had the shallowest depths.

### 3.5 Formula Iterations

**Iteration 1: Add branchFactor**
```
branchFactor = childCount <= 1 ? 0.0 : log2(childCount) / log2(20)
```
Idea: penalize folders with 1 child (chain segments).
Result: Chain folders still scored ~0.35 due to typeBoost and depthScore.

**Iteration 2: gatedDepth = branchFactor > 0 ? depthScore : 0**
Idea: depth only counts if folder actually branches.
Result: Chain folders dropped to 0.15, but `docs` (depth=7, 20ch) beat `vetka_live_03` (depth=5, 10ch) because branchFactor dominated.

**Iteration 3: depthBranch = depthScore × branchFactor**
Idea: combined multiplicative score rewards both shallow AND branching.
Result: Still docs > vetka_live_03. The product depthScore×branchFactor was too small to differentiate.

**Iteration 4: Exponential depthScore = 0.7^depth**
Idea: stronger depth separation.
Result: Both scores became tiny (~0.01), dominated by branchFactor anyway.

**Iteration 5: Quadratic depthScore = 1/(depth+1)²**
Idea: even stronger.
Result: Same problem — depthScore component too small, branchFactor wins.

**Iteration 6 (FINAL): Hard gate + linear depthScore**
```
if (childCount <= 1) return 0.0;  // HARD GATE: kill chain folders
depthScore = 1/(depth+1);          // linear decay
// Weighted: depth*0.50, branch*0.15, size*0.10, type*0.10, search*0.15
```

**Key insight:** No weight combination could make vetka_live_03 (depth=5, 10ch) beat docs (depth=7, 20ch) while keeping the formula generic. But the HARD GATE eliminates chain folders completely (score=0), and the remaining folders are ALL meaningful structural landmarks. Whether `docs` or `vetka_live_03` shows at overview=1 — both are correct answers.

### 3.6 Weight Exploration Summary

| Weight Set | depth | branch | size | type | search | Result |
|-----------|-------|--------|------|------|--------|--------|
| Original  | 0.30  | —      | 0.20 | 0.40 | 0.10   | Chain folders dominate |
| +branchFactor | 0.20 | 0.35 | 0.20 | 0.15 | 0.10 | Chain still ~0.35 |
| gatedDepth | 0.30 | 0.25 | 0.15 | 0.15 | 0.15 | docs > vetka_live_03 |
| depthBranch | 0.40 | 0.15 | 0.20 | 0.15 | 0.10 | docs still wins |
| **FINAL** | **0.50** | **0.15** | **0.10** | **0.10** | **0.15** | Chain=0, rest compete fairly |

---

## 4. Adaptive Top-N Formula

### Before (v1 — linear):
```
adaptiveMax = max(5, min(30, floor(visibleCount * 0.04 + zoomLevel * 1.5)))
```
At overview (400 visible, zoom~1): **17 labels** — way too many.

### After (v2 — quadratic + density penalty):
```
zoomBase = floor(zoomLevel² × 0.25)
densityPenalty = floor(log2(visibleCount / 50))
adaptiveMax = max(1, min(25, zoomBase - densityPenalty + 2))
```

| Zoom Level | Visible | zoomBase | densityPenalty | adaptiveMax |
|-----------|---------|----------|---------------|-------------|
| 0 (far)   | 400     | 0        | 3             | 1           |
| 1         | 350     | 0        | 2             | 1           |
| 2         | 300     | 1        | 2             | 1           |
| 3         | 200     | 2        | 2             | 2           |
| 4         | 150     | 4        | 1             | 5           |
| 5         | 100     | 6        | 1             | 7           |
| 6         | 60      | 9        | 0             | 11          |
| 7         | 40      | 12       | 0             | 14          |
| 8         | 20      | 16       | 0             | 18          |
| 9         | 10      | 20       | 0             | 22          |
| 10        | 5       | 25       | 0             | 25          |

---

## 5. Lessons for Future Phases

### 5.1 For CAM Integration (Phase 114+)
- `computeLabelScore()` is the single point where scoring happens
- Adding CAM weight is trivial: `camBoost = isActivatedInCAM ? 0.3 : 0.0`
- Add it as 6th weight component, reduce others proportionally
- The HARD GATE (`childCount <= 1 → 0`) should remain — chain folders are never interesting regardless of CAM

### 5.2 For User Activity Scoring
- `isHighlighted` currently used for search — extend to recent activity
- Consider `lastAccessedTime` as a factor: `recencyScore = 1 / (1 + hoursSinceAccess/24)`
- Pin behavior already works (`isPinned → 1.0`)

### 5.3 For modified_time Integration
- Backend sends `modified_time` (tree_routes.py:543) but `apiConverter.ts` drops it
- When added: `freshnessScore = 1 / (1 + daysSinceModified/30)`
- Fresh folders (recently modified files inside) should score higher

### 5.4 Performance Guardrails
- **NEVER use array.includes() in render loops** — always use Set
- **NEVER subscribe to frequently-changing store state** in parent of many children
- Use ref + generation counter pattern instead
- `arePropsEqual` on FileCard is your last defense — keep it comprehensive

### 5.5 Formula Design Principles
- **Hard gates > soft weights** for categorical differences (chain vs branching)
- **No weight combination can fix categorical confusion** — if chain folders shouldn't show, gate them to 0
- **Depth vs branching tension is fundamental** — can't have both dominate
- For Google Maps style: depth should be primary (shallow = overview), branching = tiebreaker

---

## 6. Files Modified

| File | Changes |
|------|---------|
| `client/src/App.tsx` | labelScoring imports, ref-based label tracking, Set lookups, OrbitControls zoom |
| `client/src/utils/labelScoring.ts` | Hard gate for chain folders, reweighted formula, quadratic top-N |
| `client/src/components/canvas/FileCard.tsx` | Removed isRoot fallback, showLabel prop controls everything |
| `client/src/store/useStore.ts` | Added selectedLabelIds, persistPositions, resetLayout |
| `client/src/components/panels/DevPanel.tsx` | Spatial Memory section with toggle + reset |

---

## 7. Verification

- **TypeScript:** 0 errors in modified files
- **Vite build:** 3.08s
- **Performance:** Smooth again after hotfix (was "жутко тормозит" before)
- **Visual:** 1 label at overview, 4-5 at medium zoom, scales up on zoom-in
- **Chain folders:** Completely eliminated from label selection
