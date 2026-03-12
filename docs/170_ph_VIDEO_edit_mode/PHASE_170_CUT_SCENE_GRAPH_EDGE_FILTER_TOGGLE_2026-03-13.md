# PHASE 170 CUT Scene Graph Edge Filter Toggle (2026-03-13)

## Scope

Add a low-friction edge filter directly to the promoted NLE Scene Graph pane.

## Added controls

### MARKER_170.NLE_GRAPH.EDGE_FILTER
Three explicit filters are now surfaced in the NLE Scene Graph pane:
- `All Edges`
- `Structural Only`
- `Overlay Only`

The pane also shows a compact `edge filter:` status line so the active view is always visible.

## Expected behavior

- `All Edges` keeps the full promoted graph view.
- `Structural Only` keeps the layout-driving subgraph visible.
- `Overlay Only` keeps intelligence edges visible without the full structural clutter.

## Why this matters

This is the first user-facing step toward LOD/overlay discipline in CUT. It gives the graph pane a real editorial control, not just a static visualization.
