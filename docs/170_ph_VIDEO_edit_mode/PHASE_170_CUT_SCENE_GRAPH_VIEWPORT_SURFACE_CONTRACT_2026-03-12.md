# PHASE 170 - CUT Scene Graph Viewport Surface Contract
**Date:** 2026-03-12
**Status:** first explicit surface contract
**References:**
- `PHASE_170_CUT_SCENE_GRAPH_FIRST_CLASS_VIEWPORT_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_PRODUCT_VIEWPORT_PLAN_2026-03-12.md`
- `docs/contracts/cut_scene_graph_view_v1.schema.json`

## Goal
Define the first explicit product contract for the CUT Scene Graph viewport as a first-class surface.

## Surface rule
Scene Graph is openable/closable, but never conceptually hidden.
It remains a primary surface alongside timeline and storyboard.

## Required behaviors
### Open / close
- viewport may be collapsed
- viewport may be closed
- reopening must preserve graph focus derived from current CUT state

### Cross-highlighting
- timeline selection highlights matching graph path
- storyboard selection highlights matching scene/take/asset nodes
- graph focus exposes inspector content without replacing Selected Shot

### Media-native node rendering
- scene nodes may render as structural cards
- take and asset nodes may render with poster, modality, duration, sync badge, marker density
- note nodes remain compact and annotation-first

### Inspector contract
- focused graph nodes must expose short summaries
- inspector must be able to show related clip ids and source paths
- architect-layer rationale may be additive later

## Initial non-goals
- no requirement that graph is the default visible surface on first load
- no forced replacement of timeline-centric editing
- no opaque model-generated graph mutations

## Markers
- `MARKER_170.SCENE_GRAPH.VIEWPORT_SURFACE_CONTRACT`
- `MARKER_170.SCENE_GRAPH.OPEN_CLOSE_ALLOWED`
- `MARKER_170.SCENE_GRAPH.MEDIA_NATIVE_NODE_RENDERING`
