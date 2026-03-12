# PHASE 170 - CUT Scene Graph Product Viewport Plan
**Date:** 2026-03-12  
**Status:** frozen for architecture chain step D1  
**References:**
- `PHASE_170_CUT_SCENE_GRAPH_ARCHITECTURE_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_MCC_ADAPTER_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_LOD_CLUSTERING_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_INTEL_OVERLAYS_2026-03-12.md`

## Goal
Define the promotion path from current debug-shell `Scene Graph Surface` to a product-grade CUT viewport that feels native to VETKA.

## Current state
- debug-shell list rendering
- contract and hydration validation
- no real DAG viewport yet

## Target state
A CUT scene graph viewport that:
- uses MCC DAG grammar and Sugiyama BT layout
- highlights editorial structure
- cross-links storyboard, timeline, selected shot, and inspector
- exposes overlays only when they improve editorial reasoning

## Required surface behaviors
### Cross-highlighting
- selecting a storyboard card highlights the related take/scene node
- selecting a timeline clip highlights the corresponding graph path
- selecting a graph node can focus the selected-shot or inspector context

### Inspector behavior
Right inspector should show:
- node summary
- related takes/assets/notes
- relevant sync or marker context
- optional intelligence overlay reasons

### Viewport behavior
- default: structural view first
- medium zoom: scene/take relationships
- near zoom: local anchors and note/marker context
- overlay filters for semantic/rhythm/context layers

## Delivery stages
### Stage 1
Debug-shell contract and smoke coverage.

### Stage 2
MCC adapter prototype with editorial node/edge styling.

### Stage 3
Cross-highlighting between storyboard/timeline and scene graph.

### Stage 4
LOD clustering and overlay filters.

### Stage 5
Promotion into the main CUT NLE shell as a first-class viewport.

## Exit rule
The product viewport is considered real only when:
- it is not just a debug list
- it uses DAG semantics consistent with MCC
- it cooperates with storyboard, timeline, and inspector
- overlay families remain optional and explainable

## Markers
- `MARKER_170.SCENE_GRAPH.PRODUCT_VIEWPORT_PLAN_FROZEN`
- `MARKER_170.SCENE_GRAPH.CROSS_HIGHLIGHTING_REQUIRED`
- `MARKER_170.SCENE_GRAPH.MAIN_CUT_VIEWPORT_PATH`
