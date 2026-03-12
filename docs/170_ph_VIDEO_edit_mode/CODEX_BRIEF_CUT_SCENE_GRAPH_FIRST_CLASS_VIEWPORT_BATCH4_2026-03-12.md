# CODEX BRIEF - CUT Scene Graph First-Class Viewport Batch 4
**Date:** 2026-03-12
**Status:** active
**References:**
- `PHASE_170_CUT_SCENE_GRAPH_FIRST_CLASS_VIEWPORT_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_DAG_VIEWPORT_BEHAVIOR_2026-03-12.md`
- `docs/contracts/cut_scene_graph_view_v1.schema.json`

## Goal
Make graph selection live by wiring first cross-highlighting between the DAG viewport, storyboard selection, and timeline selection.

## Tasks
1. wire DAG node selection into CUT Selected Shot / storyboard focus
2. wire DAG node selection into timeline selection when clip ids are available
3. extend shell contract docs/tests for explicit cross-highlighting behavior
