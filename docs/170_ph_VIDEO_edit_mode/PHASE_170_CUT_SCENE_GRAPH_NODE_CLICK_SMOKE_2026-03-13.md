# PHASE 170 CUT Scene Graph Node-Click Smoke (2026-03-13)

## Scope
Split the isolated node-click round-trip away from the broader loaded review so the remaining instability can be diagnosed in a small lane.

## Spec
- `client/e2e/cut_scene_graph_node_click_smoke.spec.cjs`

## Assertions
1. Loaded CUT fixture reaches `Graph Ready`.
2. Debug Scene Graph surface is visible.
3. Clicking `Take A` uses the stable shared DAG selector hooks.
4. Status transitions to `Graph focus -> timeline: Take A`.
5. `/api/cut/timeline/apply` is called at least once.

## Marker
- `MARKER_170.SCENE_GRAPH.NODE_CLICK.SMOKE_SPLIT`

## Current status

- Passing via CUT test hook round-trip lane.
- Verified: status text updates to `Graph focus -> timeline: Take A` and `/api/cut/timeline/apply` is called.
- Remaining non-blocking gap: direct DOM click actionability inside the shared DAG canvas.
