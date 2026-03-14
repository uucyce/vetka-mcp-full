# CODEX BRIEF - CUT Scene Graph Impl Batch 3
**Date:** 2026-03-12
**Status:** queued
**References:**
- `PHASE_170_CUT_SCENE_GRAPH_ARCHITECTURE_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_MCC_ADAPTER_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_PRODUCT_VIEWPORT_PLAN_2026-03-12.md`
- `docs/contracts/cut_scene_graph_view_v1.schema.json`

## Goal
Add the first product-facing projection hints to `scene_graph_view` so future MCC viewport work can focus and rank nodes without re-deriving editorial intent from raw graph state.

## Batch tasks
1. add focus anchors derived from timeline selection and selected scene ids
2. add layout hint block that separates structural vs overlay edge families
3. cover the new adapter hints with focused project-state tests

## Constraints
- keep the payload additive and backward-compatible
- do not add frontend CUT graph UI yet
- no new node or edge taxonomy in this batch
