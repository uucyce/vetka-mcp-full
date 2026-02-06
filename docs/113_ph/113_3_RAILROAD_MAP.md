# Phase 113.3: Labels Championship — RAILROAD MAP

**Date:** 2026-02-05
**Status:** VERIFIED — READY FOR IMPLEMENTATION
**Commander:** Claude Opus 4.6
**Recon:** 9 Haiku (2 rounds) + Grok review (8 questions) + 3 Sonnet verifiers (S1-S3)

---

## METHODOLOGY RECAP

```
9 Haiku scouts → markers (line numbers)
         ↓
Grok review → 4 corrections (adaptive-N, useShallow, hysteresis, occlude=false)
         ↓
3 Sonnet verifiers → verified markers + own markers with exact code
         ↓
THIS DOCUMENT → unified railroad map
         ↓
Implementation → follow markers like train on tracks
```

---

## TRAIN ROUTE: 6 STATIONS

### Station 1: `client/src/utils/labelScoring.ts` (NEW FILE)

**Create file with 6 functions:**

| Function | Purpose | Complexity |
|----------|---------|------------|
| `isCodeFile(filename)` | Check extension for type boost | O(1) |
| `computeLabelScore(node, isPinned, isHighlighted)` | Score 0-1 per node | O(1) |
| `selectTopLabels(scores, pinned, visibleCount, zoom)` | Adaptive top-N selection | O(n log n) |
| `arraysEqual(a, b)` | Set-based array compare (store guard) | O(n) |
| `goldenAngleJitterZ(rank, total)` | Anti-overlap Z offset | O(1) |
| `applyHysteresis(current, prev, threshold)` | Score smoothing | O(n) |

**Key constants:**
- `GOLDEN_ANGLE = 2 * Math.PI * (Math.sqrt(5) - 1) / 2` (2.39996 rad)
- `CODE_EXTENSIONS = Set(['ts','tsx','js','jsx','py','go','rs','java','cpp','c','rb','php','swift','kt','cs','scala'])`

**Imports:** `smoothstep` from `./lod`, `TreeNode` type from `../store/useStore`

**Scoring formula:**
```
Pinned → 1.0 (always)
typeBoost = folder ? 1.5 : code ? 1.2 : 0.8
depthScore = 1 / sqrt(depth + 1)
sizeScore = sqrt(children.length) / sqrt(200)
searchBoost = highlighted ? 0.3 : 0.0
final = (typeBoost/1.5)*0.4 + depthScore*0.3 + sizeScore*0.2 + searchBoost*0.1
```

**Adaptive top-N (Grok correction):**
```
adaptiveMax = max(15, min(50, visibleCount * 0.075 + zoomLevel * 2))
```

**Hysteresis (Grok correction):**
```
if (newScore > prevScore * 1.1) → accept new
else → max(prevScore * 0.9, newScore)
```

---

### Station 2: `client/src/utils/lod.ts` (1 line)

| Marker | Line | Action |
|--------|------|--------|
| S3-01 | 18 | `function smoothstep` → `export function smoothstep` |

---

### Station 3: `client/src/store/useStore.ts` (+6 lines)

| Marker | Line | Action | Code |
|--------|------|--------|------|
| S1-01 | after 114 | Interface field | `selectedLabelIds: string[];` |
| S1-02 | after 162 | Interface method | `setSelectedLabels: (labelIds: string[]) => void;` |
| S1-03 | after 204 | Initial state | `selectedLabelIds: [],` |
| S1-04 | after 416 | Action impl | `setSelectedLabels: (labelIds) => set({ selectedLabelIds: labelIds }),` |

**Existing store data we READ (no changes):**
- `pinnedFileIds: string[]` (line 111) — for pinned override
- `highlightedIds: Set<string>` (line 88) — for search boost

---

### Station 4: `client/src/App.tsx` (+30 lines)

| Marker | Line | Action | Description |
|--------|------|--------|-------------|
| S1-06 | 1 | Import | Add `import { useShallow } from 'zustand/react/shallow'` |
| — | imports | Import | Add `import { computeLabelScore, selectTopLabels, arraysEqual, applyHysteresis } from './utils/labelScoring'` |
| S1-05 | after 57 | Ref | `const prevScoresRef = useRef<Map<string, number>>(new Map())` |
| S1-08 | 77-88 | Extend loop | Add `labelScores.set(node.id, score)` for folders inside frustum loop |
| S1-09 | after 88 | Post-loop | Hysteresis → selectTopLabels → arraysEqual guard → setSelectedLabels |
| S1-11 | after 151 | Selector | `const selectedLabelIds = useStore(useShallow(s => s.selectedLabelIds))` |
| S1-12 | 127 | Prop | Add `showLabel={node.type === 'folder' && selectedLabelIds.includes(node.id)}` |

**Flow inside useFrame (200ms):**
```
1. for (node of nodes) {
     frustum check → LOD calc → score calc (folders only)
   }
2. applyHysteresis(newScores, prevScoresRef)
3. selectTopLabels(smoothed, pinnedIds, visibleCount, zoom)
4. if (!arraysEqual(topLabels, currentLabels)) setSelectedLabels(topLabels)
```

**Zoom level calculation:**
```typescript
const zoomLevel = Math.max(0, Math.min(4, Math.log2(camera.zoom || 1) + 2));
```

---

### Station 5: `client/src/components/canvas/FileCard.tsx` (+10 lines, ~5 modified)

| Marker | Line | Action | Description |
|--------|------|--------|-------------|
| S2-01 | after 211 | Props | `showLabel?: boolean;` |
| S2-02 | 232 | Destructure | Add `showLabel,` |
| S2-03 | 1217 | **CRITICAL** | `if (!showLabel && depth > 0) return null;` **BEFORE** distance check |
| S2-10 | 1229 | Replace | Static `labelZ` → golden angle jitter Z |
| S2-05 | 1240 | Replace | `zIndexRange={[100 + Math.floor(importance * 100) * 2, 50]}` |
| S2-07 | before 1316 | arePropsEqual | `if (prev.showLabel !== next.showLabel) return false;` |

**The critical fix (why v1 failed):**
```typescript
// Line 1217 — FIRST check in label IIFE
// This is the Google Maps culling: if not in top-N, don't render
if (!showLabel && depth > 0) return null;

// Then existing distance check
if (!isRoot && distToCamera > visibilityThreshold) return null;
```

**JitterZ (replaces static `position[2] + 1`):**
```typescript
const GOLDEN_ANGLE_DEG = 137.508;
const pseudoRank = Math.floor(importance * 100);
const jitterZ = Math.sin(pseudoRank * GOLDEN_ANGLE_DEG * Math.PI / 180) * (0.3 + pseudoRank / 100 * 0.5);
const labelZ = position[2] + 1 + jitterZ;
```

---

### Station 6: TEST

- [ ] Only ~15-50 labels visible (depending on zoom)
- [ ] Pinned files always have labels
- [ ] Root always visible
- [ ] Labels don't flicker on camera pan
- [ ] 60fps maintained (profile: labels overhead < 1ms)
- [ ] Search results boost label visibility
- [ ] Golden angle prevents z-fighting

---

## EXECUTION ORDER (CRITICAL)

```
1. labelScoring.ts  (NEW — no deps on other changes)
2. lod.ts           (1 line — export smoothstep)
3. useStore.ts      (4 insertions — state + action)
4. App.tsx           (scoring loop + selector + prop)
5. FileCard.tsx      (filter + jitter + arePropsEqual)
6. TEST
```

Each station is independent of the next in terms of compilation — you can build after each station. Station 4 imports from 1+2+3. Station 5 uses props from 4.

---

## GROK CORRECTIONS APPLIED

| # | Correction | Where Applied |
|---|-----------|---------------|
| 1 | Adaptive top-N (not fixed 30) | labelScoring.ts `selectTopLabels()` |
| 2 | useShallow mandatory | App.tsx selector S1-11 |
| 3 | Hysteresis on camera move | labelScoring.ts `applyHysteresis()` + App.tsx S1-09 |
| 4 | occlude=false, manual top-N | Architecture decision (no occlude prop) |

---

## WHAT WE'RE NOT DOING (Deferred)

- Activity tracking (click/hover decay) → Phase 113.4
- Hover proximity boost (useHoverBoost.ts) → Phase 113.4
- Semantic/Qdrant scoring → Phase 114
- CAM integration → Phase 114
- labelRank prop (S2-08, S2-09) → Phase 113.4
- Troika 3D Text migration → Future

---

## TOTAL CHANGES

| File | New Lines | Modified Lines |
|------|-----------|----------------|
| labelScoring.ts (NEW) | ~120 | - |
| lod.ts | - | 1 |
| useStore.ts | 6 | 0 |
| App.tsx | ~30 | 2 |
| FileCard.tsx | ~10 | ~5 |
| **TOTAL** | **~166** | **~8** |

Zero new dependencies. Zero new npm packages.

---

**STATUS: RAILROAD COMPLETE. ALL MARKERS VERIFIED. READY FOR IMPLEMENTATION.**
