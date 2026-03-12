# PHASE 170 — CUT Scene Graph Shared DAG Pane In NLE

## Goal
Use the same Scene Graph DAG bridge inside the NLE pane that already powers the shell viewport, so NLE promotion does not duplicate graph logic.

## Rules
- NLE pane reuses `scene_graph_view` adapter output.
- NLE pane mounts shared `DAGView` instead of a placeholder when `sceneGraphSurfaceMode = nle_ready`.
- Node selection behavior remains shared with shell wiring.

## Visible Signals
- `Shared DAG viewport mounted inside NLE pane.`
- `NLE pane now reuses the shared DAG viewport bridge.`
- Selection and graph identity stay explicit.
