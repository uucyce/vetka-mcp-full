# PHASE 170 CUT Selected Shot Graph Enrichment (2026-03-12)

## Scope

Enrich the `Selected Shot` panel with graph-native information so the user does not need to look back to the graph pane for basic semantic context.

## Added fields

### MARKER_170.SELECTED_SHOT.GRAPH_RENDER_MODE
Expose the primary graph card render hints directly in `Selected Shot`:
- `graph render mode`
- modality pairing from graph hints

### MARKER_170.SELECTED_SHOT.GRAPH_SUMMARY
Expose the primary graph card summary directly in `Selected Shot`:
- `graph summary`

### MARKER_170.SELECTED_SHOT.GRAPH_CHIPS
Expose compact graph chips directly in `Selected Shot`:
- sync chips like `graph sync waveform`
- bucket chips like `graph bucket selected_shot`
- fallback `no graph sync chips`

## Why this matters

`Selected Shot` is already the main editorial inspector. Moving a compact slice of graph semantics into that panel reduces ping-pong between the right inspector and the graph pane while keeping the first-class graph surface intact.
