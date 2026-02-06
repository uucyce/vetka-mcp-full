# Labels Championship: Unified Reconnaissance Report

**Date:** 2026-02-05
**Commander:** Claude Opus 4.6
**Scouts:** 9 Haiku + 3 Sonnet verifiers
**Target:** Phase 113 Labels Championship

---

## EXECUTIVE SUMMARY

| Phase | Feature | Feasibility | Action |
|-------|---------|-------------|--------|
| **A** | Basic Scoring (type + depth + size) | NOW | IMPLEMENT |
| **C** | JitterZ + Hover Boost | NOW | IMPLEMENT |
| **B** | Semantic/Qdrant Integration | DEFER | No backend API for real-time queries |
| **D** | CAM Integration | DEFER | No per-node CAM API exists |

**Total: ~200 new lines + ~55 modified. Zero new dependencies. 4 files.**

---

## CURRENT STATE (from 9 Haiku scouts)

### Folder Labels (H1)
- FileCard.tsx:1177-1269 — floating `<Html>` labels
- Importance = depthScore*0.5 + sizeScore*0.5 (Grok formula)
- Font 14-32px, visibility threshold = importance * 8000
- Root always visible, non-root hides beyond threshold
- labelZ = position[2] + 1 (STATIC, no jitter)
- zIndexRange={[50, 0]} (shared, no inter-label sorting)

### File Names (H2)
- Canvas texture, ctx.fillText — ALWAYS visible
- LOD controls font size only (12/14/16px), never hides
- Truncation: 18 chars horizontal, 10 chars vertical
- NOT floating labels — baked into card texture

### LOD System (H3)
- 10 levels (0-9), foveated spot (center=high, edges=low)
- Phase 112.7: minLOD=1 floor, Phase 112.8: expanded radius
- Batch calc in App.tsx every 200ms (FrustumCulledNodes)

### Batch Pipeline (H4)
- FrustumCulledNodes: single loop frustum+LOD for all nodes
- 200ms throttle, 50-80% culled, ~400 visible
- **INSERTION POINT: App.tsx line 86** (after LOD calc, inside same loop)
- Props flow: lodLevel passed to FileCard

### Mouse/Hover (H5)
- hoveredId in store EXISTS but UNUSED in 3D rendering
- Each FileCard has local isHovered, 300ms debounce
- NO proximity detection (only direct pointer over)
- No screen-space distance measurement

### Z-Ordering (H6)
- All labels share zIndexRange={[50, 0]} — NO inter-label sorting
- labelZ = position[2] + 1 — STATIC offset
- No renderOrder, no layers system
- No anti-overlap logic anywhere
- JitterZ needed at 4 insertion points

### Qdrant/Semantic (H7)
- Search returns relevance: 0-1 via useSearch.ts
- highlightedIds Set ready in store
- semanticPosition stored in TreeNode but UNUSED
- No real-time Qdrant queries from frontend

### Performance (H8)
- 200ms frustum loop ideal for batch scoring
- ~28 ops per node for score calc = ~0.5ms/1000 nodes
- Texture cache (500 max), preview cache, React.memo
- Total budget: +2ms overhead (12% of 16ms frame)

### Plan Gap (H9)
- labelScoring.ts does NOT exist yet
- useHoverBoost.ts does NOT exist yet
- Phase A feasible NOW (type/depth/size scoring)
- Phase B needs backend Qdrant integration (DEFER)
- Phase C feasible NOW (JitterZ math + hover projection)
- Phase D blocked (no CAM per-node API)

---

## ARCHITECTURE DECISIONS (from 3 Sonnets)

### S1: Scoring Engine
- **Batch in App.tsx** (same 200ms loop as LOD) — NOT per-FileCard
- **LabelScore interface**: {finalScore, components: {typeBoost, depthScore, sizeScore}}
- **Weights Phase A**: typeBoost 50% + depthScore 30% + sizeScore 20%
- **TypeBoost**: folder=1.5, code(.ts/.py/.js)=1.2, assets=0.8
- **Pass as prop**: `labelScore={labelScores.get(node.id)}`
- **Performance**: 28 ops/node, ~5600 ops per 200ms cycle = negligible

### S2: JitterZ + Hover
- **JitterZ in 3D space** (labelZ offset), NOT HTML zIndexRange
- **Golden angle hash**: deterministic, no flicker, Fibonacci-optimal distribution
- **Range**: ±0.3 to ±0.8 units (bounded, score-ranked)
- **Hover boost**: screen-space projection (reuse LOD projection pattern)
- **Radius**: 80px base (mobile 120px, 4K 100px), zoom-adaptive
- **Smoothstep falloff**: 0 outside radius, 1.0 at cursor
- **Performance**: +0.5ms/frame (projections already done for LOD)

### S3: Scope & Architecture
- **NEW**: `utils/labelScoring.ts` (80 lines) — pure scoring engine
- **NEW**: `hooks/useHoverBoost.ts` (60 lines) — mouse proximity
- **MODIFY**: `App.tsx` (+45 lines) — batch scoring in frustum loop
- **MODIFY**: `FileCard.tsx` (+15, ~50 modified) — score-based label rendering
- **Plug-in design**: semantic/CAM can be added later with ONE line each
- **File names**: Keep on texture (stable), don't modify

---

## IMPLEMENTATION PLAN

### Files

| # | File | Action | Lines |
|---|------|--------|-------|
| 1 | `client/src/utils/labelScoring.ts` | NEW | ~80 |
| 2 | `client/src/hooks/useHoverBoost.ts` | NEW | ~60 |
| 3 | `client/src/App.tsx` | MODIFY (FrustumCulledNodes) | +45 |
| 4 | `client/src/components/canvas/FileCard.tsx` | MODIFY (folder labels) | +15, ~50 mod |

### Label LOD Table (score + distance)

| Score | Rendering | Font | Opacity |
|-------|-----------|------|---------|
| 0.8-1.0 | Full name, bold | 26-32px | 1.0 |
| 0.5-0.8 | Full name | 18-26px | 0.9 |
| 0.3-0.5 | Full name, smaller | 14-18px | 0.8 |
| 0.15-0.3 | Truncated (10 chars) | 12-14px | 0.7 |
| 0-0.15 | Hidden (icon only) | — | 0 |

### Scoring Formula (Phase A)

```
typeBoost = folder ? 1.5 : code ? 1.2 : 0.8
depthScore = 1 / sqrt(depth + 1)
sizeScore = sqrt(childCount) / sqrt(maxChildren)

finalScore = normalize(typeBoost) * 0.5 + depthScore * 0.3 + sizeScore * 0.2
```

### JitterZ Formula

```
hash = hashNodeId(id) % 360
rankOffset = (rank / totalVisible) * 0.5
jitterZ = sin((hash + rank * 137.5) * PI / 180) * (0.3 + rankOffset)
```

### Hover Boost

```
Project node to screen → measure pixel distance from mouse
if (dist < 80px) → boost = smoothstep(1 - dist/radius)
Apply: score += 0.3 * boost
Visual: scale(1 + boost * 0.1), opacity boost
```

---

## NOT DOING

- Phase B Semantic (no backend API for real-time Qdrant)
- Phase D CAM (no per-node API)
- File name texture changes (stable, don't touch)
- New npm dependencies (zero)
- Feature flags (overkill for this scope)

---

## GROK REVIEW PROMPT

Questions for Grok to verify:
1. Golden angle (137.5 deg) for JitterZ distribution — optimal for label packing?
2. Hover radius 80px — too small/large for VETKA's 1700 nodes?
3. Score weights (type 50%, depth 30%, size 20%) — balanced?
4. Should hover boost use useThree pointer or window mousemove?
5. Any Three.js tricks for Html label anti-overlap we're missing?

---

*Report compiled from 9 Haiku scouts + 3 Sonnet verifiers.*
*Ready for Grok review, then implementation.*
