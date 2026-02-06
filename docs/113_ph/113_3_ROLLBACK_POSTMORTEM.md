# Phase 113.3: Labels Championship - ROLLBACK POSTMORTEM

**Date:** 2026-02-05
**Status:** ROLLED BACK
**Reason:** Performance regression + labels always visible (no Google Maps effect)

---

## What Was Done

### Phase 1: Recon (9 Haiku scouts H1-H9)
Placed markers across 7 files with 100% line-number accuracy:
- H1: Store shape & activityMap (useStore.ts:171, :416)
- H2: App.tsx batch loop (lines 77, 85, 106-108, 112-129, 42-47, 62)
- H3: FileCard folder labels (lines 1229, 1240, 1219-1225, 1243-1253)
- H4: FileCard props interface (lines 175-212, 214, 1320)
- H5: LOD utils (lod.ts: 3 exports, smoothstep:18, projection:100)
- H6: useSearch hook (SearchResult.relevance, results array)
- H7: TreeNode types (type field, extension, children)
- H8: Interaction points (onPointerOver:960, onClick:942)
- H9: Performance budget (200ms throttle, 4 ops/node, GC safe)

### Phase 2: Verification (3 Sonnet verifiers S1-S3)
- S1: APPROVED WITH MODIFICATIONS - activityMap must be local ref, not Zustand
- S2: APPROVED - add children.length and labelScore to memo comparator
- S3: APPROVED - export smoothstep, adjust performance estimate 0.5ms->2-4ms

### Phase 3: Verification Report
- Written to `docs/113_ph/113_VERIFICATION_REPORT.md`

### Phase 4: Implementation (ROLLED BACK)
5 files touched, ~145 lines:

1. **`client/src/utils/lod.ts`** (+1 line)
   - `function smoothstep` -> `export function smoothstep`

2. **`client/src/utils/labelScoring.ts`** (NEW, ~120 lines)
   - `computeLabelScore(input, now)` - 5-factor weighted scoring
   - `goldenAngleJitterZ(rank, count)` - golden angle Z-offset
   - `scoreToZIndex(score)` - dynamic zIndexRange by score
   - `selectTopLabels(scores, maxLabels, minScore)` - top-N selection
   - Weights: Type 25% + Activity 25% + Depth/Size 20% + Search 15% + Pinned 15%
   - Decay: `e^(-t/30000)` for click (67%) and hover (33%)

3. **`client/src/store/useStore.ts`** (+8 lines)
   - Added `selectedLabelIds: string[]` to TreeState interface (line 171)
   - Added `setSelectedLabels(ids)` action (line 424)
   - Added initial state `selectedLabelIds: []` (line 213)

4. **`client/src/App.tsx`** (+42 lines)
   - Imported `computeLabelScore`, `selectTopLabels`, `ActivityData`
   - Added `activityRef = useRef(new Map<string, ActivityData>())` in FrustumCulledNodes
   - Added `labelScores` state + store selectors (pinnedFileIds, highlightedIds, setSelectedLabels)
   - Added scoring loop inside 200ms useFrame: scored all visible folders
   - Added `updateActivity` callback (click/hover -> local Map)
   - Passed `labelScore` and `updateActivity` as new props to FileCard

5. **`client/src/components/canvas/FileCard.tsx`** (+79/-69 lines)
   - Added `labelScore?: number` and `updateActivity?` to FileCardProps
   - Added them to destructuring
   - Imported `goldenAngleJitterZ`, `scoreToZIndex` from labelScoring
   - Added `hoverThrottleRef` for 200ms hover throttle
   - Changed `onPointerOver` from one-liner to block with throttled activity tracking
   - Added `updateActivity('click', id)` after `onClick?.()`
   - Replaced entire folder label IIFE:
     - `importance` now uses `labelScore ?? legacy_formula`
     - `labelZ` uses `position[2] + 1 + goldenAngleJitterZ(depth, childCount + 1)`
     - `zIndexRange` uses `scoreToZIndex(importance)` instead of static `[50, 0]`
   - Added `labelScore` + `children.length` to `arePropsEqual`

---

## What Went Wrong

### Root Cause: Labels always visible, no Google Maps culling
The `computeLabelScore()` function computed scores for ALL visible folders, but the score was used as `importance` inside FileCard's label IIFE which ONLY controlled:
- `visibilityThreshold = importance * MAX_DISTANCE`
- Font size and styling

The problem: **Every folder with `labelScore > 0` still passed the visibility check** because:
```typescript
// This check is too permissive:
if (!isRoot && distToCamera > visibilityThreshold) return null;
// With importance = 0.25 (minimum for any folder), threshold = 0.25 * 8000 = 2000
// Most camera distances are < 2000, so almost EVERYTHING renders
```

The original code had the same issue but with a simpler formula. The Championship scoring made it **worse** by giving every folder a minimum score of ~0.25 (because `typeScore = 1.0 * 0.25 = 0.25` for all folders).

### Missing: Top-N selection enforcement
`selectTopLabels()` was called and stored `selectedLabelIds` in Zustand, but **nothing used it to actually hide labels**. The FileCard never checked if its ID was in the selected set. The score was passed as a hint, not as a filter.

### Performance regression
- Scoring loop runs for ALL visible folders every 200ms
- `setLabelScores(scores)` creates new Map -> new state -> triggers re-render of FrustumCulledNodes
- Every `labelScore` map lookup produces a new `undefined | number` -> `arePropsEqual` sees change -> FileCard re-renders
- Net effect: MORE re-renders than before, not fewer

### Not following markers
The user's instruction was clear: work from the markers placed by scouts. Instead of carefully following the marker-based plan that was verified, I implemented too much too fast without validating the core logic:
- Markers were correct (verified by Sonnets)
- But the implementation deviated from the plan's intent
- The scoring formula was applied but the **selection/culling** step was missing
- `selectTopLabels` result wasn't wired back to FileCard visibility

---

## What Should Have Been Done

### Correct approach:
1. FileCard should check `selectedLabelIds.includes(id)` to decide if label renders at all
2. Only top-N folders (e.g., 30) should have visible labels
3. Score should control prominence (font size, opacity, z-index) of SHOWN labels
4. Non-selected folders should return `null` from the label IIFE immediately

### Implementation fix (for next attempt):
```typescript
// In FileCard label IIFE, FIRST line:
const selectedLabelIds = useStore((s) => s.selectedLabelIds);
if (!selectedLabelIds.includes(id) && depth > 0) return null;
// THEN apply importance-based styling for those that remain
```

### Performance fix:
- Don't pass `labelScores` Map as state (causes re-renders)
- Use `useRef` for scores too, pass boolean `showLabel` prop instead of number
- Or use Zustand `selectedLabelIds` directly in FileCard (subscribe once)

---

## Files After Rollback
All 4 modified files restored to pre-Phase-113.3 state via `git checkout`.
New file `labelScoring.ts` deleted.
Verification report (`113_VERIFICATION_REPORT.md`) preserved for next attempt.

---

## Lessons
1. **Test the core logic before building the full pipeline.** The culling check (`distToCamera > threshold`) should have been validated with console.log first.
2. **Follow the markers literally.** The scout markers identified exact insertion points. I should have made minimal changes at each marker, tested, then moved to the next.
3. **Selection must enforce visibility.** Computing scores means nothing if the render path doesn't use the selection result to hide/show.
4. **State updates in useFrame are dangerous.** `setLabelScores()` every 200ms triggers cascading re-renders. Should use refs.
