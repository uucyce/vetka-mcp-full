# CODEX BRIEF - CUT Scene Graph First-Class Viewport Batch 2
**Date:** 2026-03-12
**Status:** active
**References:**
- `PHASE_170_CUT_SCENE_GRAPH_FIRST_CLASS_VIEWPORT_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_EDITORIAL_ARCHITECT_LAYER_2026-03-12.md`
- `docs/contracts/cut_scene_graph_view_v1.schema.json`

## Goal
Move from backend-first Scene Graph payloads into the first explicit CUT viewport adapter and prototype wiring.

## Tasks
1. client adapter helper for `scene_graph_view.dag_projection`
2. viewport surface contract doc
3. first non-default viewport prototype wiring in CUT

## Rules
- Scene Graph remains a first-class viewport
- do not describe it as hidden
- timeline and storyboard remain present; graph joins them as an explicit surface
