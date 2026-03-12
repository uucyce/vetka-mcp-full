# PHASE 170 — CUT Scene Graph Reverse Cross-Highlighting

## Purpose
Make `Scene Graph Surface` respond not only to direct DAG clicks, but also to existing CUT context from storyboard and timeline selection.

## Rules
- `Selected Shot` should project into the graph through `scene_graph_view.crosslinks.by_source_path`.
- Timeline selection should project into the graph through `scene_graph_view.crosslinks.by_clip_id`.
- Backend graph focus remains authoritative when present, but local CUT context can widen the visible DAG selection.
- `Selected Shot` should expose graph-linked context directly so users do not have to inspect the graph to verify linkage.

## Expected UI Signals
- `Scene Graph Surface` copy states that graph focus follows storyboard and timeline context.
- `Selected Shot` shows:
  - `graph-linked nodes:`
  - `graph primary:`
  - `graph focus source:`
- Scene Graph cards use the same derived selection set as the DAG canvas.

## Non-Goals
- No new backend route.
- No hidden graph mode.
- No replacement of the existing DAG click-to-timeline flow.
