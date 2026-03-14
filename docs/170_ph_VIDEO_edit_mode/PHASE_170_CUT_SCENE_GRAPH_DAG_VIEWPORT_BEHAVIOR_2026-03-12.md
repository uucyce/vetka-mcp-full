# PHASE 170 - CUT Scene Graph DAG Viewport Behavior
**Date:** 2026-03-12
**Status:** first implementation behavior doc
**References:**
- `PHASE_170_CUT_SCENE_GRAPH_FIRST_CLASS_VIEWPORT_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_VIEWPORT_SURFACE_CONTRACT_2026-03-12.md`
- `CODEX_BRIEF_CUT_SCENE_GRAPH_FIRST_CLASS_VIEWPORT_BATCH3_2026-03-12.md`

## Goal
Define how the first explicit DAG viewport coexists with cards and inspector in CUT.

## Behavior
- DAG viewport is visible inside Scene Graph Surface
- graph cards remain below it as media-native summaries
- Scene Graph Inspector remains visible as a textual reasoning surface
- graph navigation does not replace timeline or storyboard; it complements them

## Open / close semantics
- the graph surface may later be collapsible
- the graph surface is not conceptually hidden
- cards + inspector may remain visible even when graph canvas is collapsed

## Cross-highlighting expectation
- selected CUT state should continue feeding graph focus
- future timeline/storyboard clicks should update DAG selection directly
- future DAG clicks should focus related Selected Shot / timeline context

## Markers
- `MARKER_170.SCENE_GRAPH.DAG_VIEWPORT_BEHAVIOR`
- `MARKER_170.SCENE_GRAPH.GRAPH_CARDS_INSPECTOR_COHABITATION`
