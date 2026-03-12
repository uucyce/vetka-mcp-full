# CODEX BRIEF - CUT Scene Graph Impl Batch 2
**Date:** 2026-03-12
**Status:** active
**References:**
- `PHASE_170_CUT_SCENE_GRAPH_ARCHITECTURE_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_MCC_ADAPTER_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_PRODUCT_VIEWPORT_PLAN_2026-03-12.md`

## Goal
Move from raw `cut_scene_graph_v1` storage toward a product-usable adapter/read-model for future MCC DAG projection.

## Batch tasks
1. freeze `cut_scene_graph_view_v1` as a lightweight adapter payload contract
2. expose `scene_graph_view` from `/api/cut/project-state`
3. validate the adapter payload with focused regression tests

## Constraints
- reuse frozen taxonomy docs; do not invent new node or edge types
- keep `scene_graph` raw payload intact; adapter is additive
- keep implementation backend/read-model only; no CUT UI changes in this batch

## Markers
- `MARKER_170.SCENE_GRAPH.IMPL_BATCH2_ACTIVE`
- `MARKER_170.SCENE_GRAPH.ADAPTER_PAYLOAD_V1`
- `MARKER_170.SCENE_GRAPH.PROJECT_STATE_VIEW_BINDING`
