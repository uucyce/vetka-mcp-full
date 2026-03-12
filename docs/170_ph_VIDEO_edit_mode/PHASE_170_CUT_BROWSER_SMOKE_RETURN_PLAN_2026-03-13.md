# PHASE 170 CUT Browser Smoke Return Plan (2026-03-13)

## Scope

Prepare the return path for browser smoke once the runner lane is stable again.

## Next smoke targets

### MARKER_170.BROWSER_RETURN.NODE_CLICK
Re-enable the loaded-state node-click smoke and prove:
- DAG node click triggers `/api/cut/timeline/apply`
- `focus source` remains coherent
- `Selected Shot` keeps semantic links after click

### MARKER_170.BROWSER_RETURN.EDGE_FILTER
Covered by `cut_scene_graph_edge_filter_minicard_smoke.spec.cjs`:
- `All Edges`
- `Structural Only`
- `Overlay Only`

### MARKER_170.BROWSER_RETURN.SELECTED_SHOT_MINI_CARD
Covered by `cut_scene_graph_edge_filter_minicard_smoke.spec.cjs` in debug mode:
- poster reuse
- primary graph label
- graph summary
- graph sync/bucket chips

## Why this matters

The current code path is ahead of the browser runner stability. This note keeps the next acceptance targets explicit so we can return to smoke coverage without rediscovery.

## Current status

- Stable now: edge filter + Selected Shot mini-card smoke
- Still isolated: DAG node click round-trip
