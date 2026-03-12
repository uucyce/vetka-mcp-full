# PHASE 170 - CUT Scene Graph LOD and Clustering Plan
**Date:** 2026-03-12  
**Status:** frozen for architecture chain step C1  
**References:**
- `PHASE_170_CUT_SCENE_GRAPH_ARCHITECTURE_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_MCC_ADAPTER_PLAN_2026-03-12.md`

## Goal
Define zoom-level behavior and clustering policy so large editorial graphs stay readable without abandoning VETKA's explicit DAG philosophy.

## Principle
Clustering reduces visual load, not semantic ownership.
The user must still be able to understand what is hidden inside a cluster and why it exists.

## Zoom tiers
### Tier 1 - Far zoom
Visible units:
- scene clusters
- major narrative branches
- high-level note groups

Hidden by default:
- individual takes
- marker-group details
- low-confidence intelligence edges

### Tier 2 - Medium zoom
Visible units:
- scenes
- takes
- primary notes
- strongest semantic or rhythm overlays

Collapsed by default:
- dense note bundles
- marker-group internals
- lower-priority overlay families

### Tier 3 - Near zoom
Visible units:
- scene nodes
- take nodes
- note nodes
- marker or anchor level entities where available
- selected overlay edges and local context

## Clustering roles
### HDBSCAN
Primary role:
- semantic grouping of related nodes or subregions when density is high

Use cases:
- scene families with highly similar takes
- note clusters around one scene
- semantic motif clusters across distant scenes

### Spectral methods
Primary role:
- structure-aware partition suggestions where relation topology matters more than pure embedding density

Use cases:
- branch separation
- continuity/rhythm neighborhood grouping
- overlay-edge community detection

## Readability guardrails
- structural edges always remain legible before overlay edges
- clustering must not reorder primary narrative flow
- no cluster should hide the currently selected node
- expanding a cluster should preserve local context and current focus

## Collapse / expand rules
- collapse by density or zoom, never arbitrarily
- selected node, selected path, and inspector-focused neighborhood remain expanded
- graph should support progressive disclosure rather than all-or-nothing collapse

## MCC adapter dependency
The adapter should expose enough metadata so clustering can operate on:
- node type
- structural neighborhood
- semantic feature group
- confidence bands for overlay edges

## Anti-rules
- do not use clustering to mask unresolved taxonomy problems
- do not let JEPA/PULSE proposals become mandatory cluster boundaries
- do not replace Sugiyama structure with freeform embedding cloud layout in the default view

## Markers
- `MARKER_170.SCENE_GRAPH.LOD_PLAN_FROZEN`
- `MARKER_170.SCENE_GRAPH.HDBSCAN_CLUSTER_ROLE`
- `MARKER_170.SCENE_GRAPH.SPECTRAL_CLUSTER_ROLE`
