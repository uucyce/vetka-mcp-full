# 🌳 PHASE 155 — Unified DAG & Spatial Navigation

**Status**: IN_PROGRESS
**Owner**: Opus (Claude Code)
**Objective**: Transition from level-switching to zoom-based unified spatial navigation. "IKEA closet in a Japanese apartment" — minimal UI, maximum context.

## 🎯 CORE TARGETS
1. **Fix React Crash**: Wrap MCC in `ReactFlowProvider` to enable `useReactFlow`.
2. **Unified DAG Canvas**: Single component instance handling multiple levels via data swapping + zoom.
3. **Smooth Zoom-Drill**: animated camera transitions (0.5x -> 1.5x -> 3.0x).
4. **Contextual Footer**: Limit to max 3 buttons, strictly aware of depth and selection.
5. **Smart Windows**: Mini-windows (Chat, Stats, Tasks) appear/disappear based on context.

## 🛠️ IMPLEMENTATION STEPS

### 1. The Foundation (Fix & Provider)
- [x] Wrap `MyceliumCommandCenter` content in `ReactFlowProvider`.
- [x] Restore `forwardRef` in `DAGView.tsx` to expose camera controls.

### 2. Spatial Logic (Zoom-Drill)
- [x] Implement `ZOOM_LEVELS` mapping (Roadmap=0, Tasks=1, Workflow=2).
- [x] Integrate double-click zoom with existing `drillDown` state updates.
- [~] Add `zoomToNode` logic in `MyceliumCommandCenter` (partially stabilized, needs final polish).

### 3. Minimalist UI (Japanese Closet)
- [x] Audit `FooterActionBar` actions per level.
- [x] Ensure only 3 primary buttons are visible.
- [x] Auto-show/hide MiniWindows based on `navLevel`.

### 4. Cleanup & Polish
- [x] Remove `TaskDAGView.tsx` (deprecated by Unified DAG).
- [~] Clean up redundant props and state (ongoing).
- [x] MARKER_155.DANGER.STUB for URL-based camera persistence.

## ✅ Progress Update (2026-02-22)

### Done Today
- Implemented P1.5 UI bind for predictive overlay (`/api/mcc/graph/predict`) with dashed edges.
- Added strict anti-spaghetti guard for predicted overlay:
  - local-to-selected-node only
  - hard limits on predicted edge count
  - higher confidence threshold
- Implemented P1.6 backend narrow:
  - input-matrix style channel aggregation (`structural`, `temporal`, `reference`, `semantic`)
  - SCC condensation from scored graph
  - extended stats (`l0_channel_hist`, explicit/reference counters)
- Added architecture root/hub strategy on frontend to reduce single-star root collapse.
- Added implementation docs and sample JSON for P1.6.

### Open Architectural Issues
- `tests/*` still appear as horizontal-derived strip in architecture view.
- `visualization/*` and similar folders are not yet promoted into dedicated semantic branch grouping.
- Need better layer/rank normalization for “derived artifacts” so they are not forced into one rail.

## 📌 Plan For Tomorrow

1. **P1.7 Scanner Split**
- Extract scanner contracts into modular services:
  - `CodeScanner`, `DocumentScanner`, `BookScanner`, `ScriptScanner`, `VideoScanner`, `AudioScanner`.
- Keep unified `SignalEdge` output schema with channel/evidence.

2. **Folder-Aware Branching**
- Introduce branch hubs for key domains (`src`, `tests`, `docs`, `tools`, `visualization`) before Sugiyama.
- Prevent `tests` from collapsing into one horizontal strip.

3. **Rank Policy Upgrade**
- Move to strict rank policy:
  - root at bottom
  - parent->child monotonic Y
  - limited same-rank edges in architecture LOD
- Add explicit “derived/test/docs” rank offsets.

4. **Verification**
- Add quick regression checks for:
  - max edge density in architecture mode
  - no single-star root explosion
  - branch coverage for `tests` and `visualization`

## 📝 MARKERS
- `MARKER_155.UNIFIED_DAG`: Implementation of the single canvas logic.
- `MARKER_155.ZOOM_DRILL`: Zoom-based navigation logic.
- `MARKER_155.MINIMAL_UI`: Footer and window management logic.
- `MARKER_155.DANGER.STUB`: Temporary placeholders for Phase 156.

---
*Created by Opus on 2026-02-21*
