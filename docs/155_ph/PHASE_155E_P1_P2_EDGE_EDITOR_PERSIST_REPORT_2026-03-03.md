# PHASE 155E — P1/P2 Edge Editor + Persist Report (2026-03-03)

Scope: remaining items from Wave E P0/P1 report and P2 persistence contract.

## Implemented markers

1. `MARKER_155E.WE.EDGE_EDITOR_MINIPANEL.V1`
- Added edge edit action in context menu (`Edit Edge`).
- Added compact edge mini-panel in MCC runtime flow:
  - editable: `type`, `relation`, `label`;
  - save/cancel actions;
  - gated to inline workflow edge context in roadmap runtime mode.

2. `MARKER_155E.WE.EDGE_PERSIST_CANONICAL.V1`
- Added persistence bridge `persistInlineWorkflowTemplate(nextEdges)`:
  - normalizes inline node/edge ids (`wf_{taskId}_*` -> inner ids),
  - writes workflow to `/api/workflows` (`POST` create or `PUT` update),
  - for newly created workflow, patches task via `/api/debug/task-board/{taskId}` with `workflow_id`.
- Persistence is invoked on inline edge add/update/delete and edge-editor save.

## Files changed

1. `client/src/components/mcc/DAGContextMenu.tsx`
2. `client/src/components/mcc/MyceliumCommandCenter.tsx`
3. `tests/test_phase155e_p1_p2_edge_editor_persist.py`
4. `docs/155_ph/PHASE_155E_P1_P2_EDGE_EDITOR_PERSIST_REPORT_2026-03-03.md`

## Verify

- `pytest -q tests/test_phase155e_p1_p2_edge_editor_persist.py`
- Result: `3 passed`.

## Notes

- Local `tsc --noEmit` still reports broad pre-existing repo type debt; no dedicated type baseline exists yet for strict MCC-only compile checks.
- This step intentionally keeps grandma UX compact (no new major window class; mini-panel only when edge edit is explicitly opened).
