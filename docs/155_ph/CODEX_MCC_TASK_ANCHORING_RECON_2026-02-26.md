# MCC Task Anchoring Recon — 2026-02-26

Scope: task-to-code anchoring and minimal task UX in MCC roadmap/tasks flow.

## Marker Checklist

- `MARKER_155.G1.TASK_ANCHORING_CONTRACT_V1`
  - Added explicit anchor metadata flow end-to-end:
    - frontend create: `module`, `primary_node_id`, `affected_nodes`, `workflow_id`, `team_profile`, `task_origin`
    - backend persist/update in task board.

- `MARKER_155.2A` (module assignment continuity)
  - Preserved auto-assign behavior.
  - Added explicit module override for anchored task creation from roadmap node.

- `MARKER_144.3` (context menu)
  - Extended context menu to support `Create Task Here` on roadmap node right-click.
  - Preserved edit-mode node/edge operations for workflow levels.

- `MARKER_155A.G21.SINGLE_CANVAS_STATE`
  - Roadmap remains clean: only anchored overlay tasks are rendered.
  - Unplaced tasks are hidden from overlay until anchored.

- `MARKER_152.8` (task filters)
  - Added `minimal` mode usage for expanded mini Tasks panel.
  - Team-first filtering retained, noisy controls reduced.

## UX Changes Implemented

1. Expanded Tasks panel cleanup:
   - removed `Add & Run`,
   - keep single `+` queue add,
   - minimal filter bar (search + team + statuses).
2. Roadmap right-click:
   - `Create Task Here` on node.
3. Task anchor persistence:
   - stored in `task_board.json` schema via TaskBoard fields and debug routes.
4. Suggested anchors flow (roadmap):
   - tasks without explicit anchors get one inferred `suggested` anchor (when match found),
   - suggested task nodes are rendered semi-transparent with dashed outline,
   - right-click suggested task node -> `Approve Suggested Anchor` persists `primary_node_id/affected_nodes/module`.
5. Fractal workflow reveal:
   - in roadmap (single canvas), when a task is selected and camera LOD reaches workflow zoom,
   - selected task workflow nodes/edges are overlaid inline (prefixed IDs, bridge edge from task overlay),
   - no forced navigation to separate workflow screen for basic drill.

## Verification Notes

- Python compile: OK for touched backend files.
- Frontend full `npm run build` currently fails due unrelated pre-existing TS errors in other modules; no new blocker-specific compile signal available from full build.
