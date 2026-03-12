# CODEX BRIEF - CUT Scene Graph Impl Batch 5
**Date:** 2026-03-12
**Status:** queued
**References:**
- `PHASE_170_CUT_SCENE_GRAPH_ARCHITECTURE_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_MCC_ADAPTER_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_PRODUCT_VIEWPORT_PLAN_2026-03-12.md`
- `docs/contracts/cut_scene_graph_view_v1.schema.json`

## Goal
Make `scene_graph_view` directly usable by a future MCC-style viewport by separating base layout data from overlay/intelligence data.

## Batch tasks
1. add `structural_subgraph` with node ids and edge ids used for primary layout
2. add `overlay_edges` for intelligence-family edges that should render after layout
3. extend contract/project-state regression tests for the split payload

## Constraints
- additive only
- no CUT frontend graph rendering in this batch
- keep raw `scene_graph` and current `scene_graph_view.edges` intact for backward compatibility
