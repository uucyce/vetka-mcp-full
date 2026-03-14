# PHASE 170 - CUT Scene Graph Cross-Highlighting
**Date:** 2026-03-12
**Status:** first live cross-highlighting step
**References:**
- `PHASE_170_CUT_SCENE_GRAPH_DAG_VIEWPORT_BEHAVIOR_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_VIEWPORT_SURFACE_CONTRACT_2026-03-12.md`
- `CODEX_BRIEF_CUT_SCENE_GRAPH_FIRST_CLASS_VIEWPORT_BATCH4_2026-03-12.md`

## Goal
Lock the first live behavior where Scene Graph selection influences other CUT surfaces.

## Implemented step
- DAG node selection can update Selected Shot / storyboard focus through `selection_refs.source_paths`
- DAG node selection can update timeline selection through `selection_refs.clip_ids`
- graph focus remains explicit and visible in the viewport while other surfaces synchronize

## Rules
- graph focus should not hide timeline or storyboard
- graph focus may lead timeline selection when clip ids are available
- node selection without clip ids may still update Selected Shot / graph status text

## Markers
- `MARKER_170.SCENE_GRAPH.CROSS_HIGHLIGHTING_LIVE`
- `MARKER_170.SCENE_GRAPH.DAG_TO_TIMELINE_SELECTION`
- `MARKER_170.SCENE_GRAPH.DAG_TO_SHOT_FOCUS`
