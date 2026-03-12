# CODEX BRIEF - CUT Scene Graph Impl Batch 6
**Date:** 2026-03-12
**Status:** queued
**References:**
- `PHASE_170_CUT_SCENE_GRAPH_ARCHITECTURE_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_MCC_ADAPTER_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_PRODUCT_VIEWPORT_PLAN_2026-03-12.md`
- `docs/contracts/cut_scene_graph_view_v1.schema.json`

## Goal
Prepare `scene_graph_view` for first MCC-side consumption by shipping a lightweight DAG projection payload directly from backend.

## Batch tasks
1. add additive `dag_projection` block to `cut_scene_graph_view_v1`
2. map scene-graph nodes/edges into MCC-friendly DAG projection fields
3. extend contract and project-state regression tests for the new projection

## Constraints
- additive only
- keep existing `scene_graph_view` fields unchanged
- no frontend graph rendering in this batch
