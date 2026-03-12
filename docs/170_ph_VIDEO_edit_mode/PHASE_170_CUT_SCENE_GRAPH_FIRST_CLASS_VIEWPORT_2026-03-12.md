# PHASE 170 - CUT Scene Graph First-Class Viewport
**Date:** 2026-03-12
**Status:** active architectural clarification
**References:**
- `PHASE_170_CUT_SCENE_GRAPH_ARCHITECTURE_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_PRODUCT_VIEWPORT_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_MCC_ADAPTER_PLAN_2026-03-12.md`

## Decision
CUT Scene Graph is a first-class VETKA viewport.
It is not a hidden graph, not a debug-only tool, and not a secondary fallback UI.

The graph may be collapsed or closed by the user, but conceptually it remains a primary surface alongside:
- timeline
- storyboard
- selected shot / inspector

## Editorial architect layer
CUT should inherit the MCC practice where graph structure is shaped not only by manual editing but also by an architectural reasoning layer.

For CUT this means an **editorial architect layer** that can fuse:
- montage sheet structure
- timecode / waveform / meta sync
- HDBSCAN / spectral clustering
- TTR / rhythm signals
- JEPA / V-JEPA scene and visual proposals
- logging and state transitions from montage operations

Rule:
these systems enrich and organize the DAG; they do not replace it.

## Product rule
- DAG is explicit
- multiple DAG scales are allowed
- nested / fractal DAG composition is allowed
- media-native nodes are preferred over abstract boxes when useful

## Markers
- `MARKER_170.SCENE_GRAPH.FIRST_CLASS_VIEWPORT`
- `MARKER_170.SCENE_GRAPH.EDITORIAL_ARCHITECT_LAYER`
- `MARKER_170.SCENE_GRAPH.FRACTAL_DAG_MODEL`
