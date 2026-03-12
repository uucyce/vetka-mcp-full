# PHASE 170 - CUT Scene Graph Editorial Architect Layer
**Date:** 2026-03-12
**Status:** active planning step
**References:**
- `PHASE_170_CUT_SCENE_GRAPH_FIRST_CLASS_VIEWPORT_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_ARCHITECTURE_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_INTEL_OVERLAYS_2026-03-12.md`

## Goal
Define how CUT Scene Graph structure can be shaped by intelligence and synchronization systems while remaining explicit, inspectable, and editor-first.

## Inputs to the architect layer
### Structural inputs
- montage sheet / project records
- timeline clip membership
- scene assembly payloads
- notes / markers / comments

### Sync inputs
- timecode sync
- waveform sync
- meta sync
- pause/silence slices

### Intelligence inputs
- HDBSCAN / spectral cluster proposals
- TTR rhythm groups
- JEPA / V-JEPA semantic and visual anchors
- continuity and motif proposals

## Output classes
- cluster proposals for scene/take grouping
- candidate overlay edges
- focus hints / attention routing
- viewport collapse/expand suggestions
- inspector summaries and rationale blocks

## Hard rules
- no opaque graph mutation without inspectable provenance
- no model-only node or edge families outside approved taxonomy
- sync and intelligence may shape the graph, but structural identities stay stable
- montage-sheet logging remains the source of truth for editorial actions

## Suggested implementation order
1. provenance fields for architect suggestions
2. cluster proposal payloads
3. rationale text for overlay edges
4. viewport filters for architect-suggested layers

## Markers
- `MARKER_170.SCENE_GRAPH.EDITORIAL_ARCHITECT_INPUTS`
- `MARKER_170.SCENE_GRAPH.EDITORIAL_ARCHITECT_OUTPUTS`
- `MARKER_170.SCENE_GRAPH.PROVENANCE_REQUIRED`
