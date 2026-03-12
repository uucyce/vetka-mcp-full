# CODEX BRIEF - CUT Scene Graph Impl Batch 4
**Date:** 2026-03-12
**Status:** queued
**References:**
- `PHASE_170_CUT_SCENE_GRAPH_ARCHITECTURE_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_MCC_ADAPTER_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_PRODUCT_VIEWPORT_PLAN_2026-03-12.md`
- `docs/contracts/cut_scene_graph_view_v1.schema.json`

## Goal
Add cross-surface binding data to `scene_graph_view` so future timeline/storyboard selection can jump into the MCC DAG viewport without UI-side graph searching.

## Batch tasks
1. add crosslink block for clip ids, scene ids, and source paths
2. expose per-node related clip/source references for fast selection bridging
3. extend project-state regression tests for the new crosslinks

## Constraints
- additive only
- no frontend CUT graph implementation yet
- keep raw scene_graph untouched
