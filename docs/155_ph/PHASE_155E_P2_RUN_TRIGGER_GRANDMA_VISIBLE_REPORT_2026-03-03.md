# PHASE 155E — P2 Run Trigger Grandma Visible Report (2026-03-03)

Scope: `MARKER_155E.WF.EXEC.RUN_TRIGGER_GRANDMA_VISIBLE.V1` + `MARKER_155E.WF.EXEC.RUN_TRIGGER_IN_EXISTING_PANELS.V1`.

## Implemented markers

1. `MARKER_155E.WF.EXEC.RUN_TRIGGER_GRANDMA_VISIBLE.V1`
- `FooterActionBar` is now rendered in normal grandma flow (`navLevel != first_run`), not only in `debugMode`.
- This restores visible execute path via existing level actions (`launch/execute`) without requiring keyboard-only discovery.

2. `MARKER_155E.WF.EXEC.RUN_TRIGGER_IN_EXISTING_PANELS.V1`
- Added `run wf` action directly into existing `MiniTasks` selected-task action row.
- Button appears when selected task has `workflow_id` and calls `executeWorkflow(workflow_id, preset)`.

## Files changed

1. `client/src/components/mcc/MyceliumCommandCenter.tsx`
2. `client/src/components/mcc/MiniTasks.tsx`
3. `tests/test_phase155e_p2_run_trigger_visibility.py`
4. `docs/155_ph/PHASE_155E_P2_RUN_TRIGGER_GRANDMA_VISIBLE_REPORT_2026-03-03.md`

## Verify

- `pytest -q tests/test_phase155e_p2_run_trigger_visibility.py tests/test_phase155e_p0_contract_matrix.py tests/test_phase155e_p1_p2_edge_editor_persist.py tests/test_phase155e_p2_execution_semantics.py tests/test_phase155e_p3_template_family_registry.py tests/test_phase155e_p4_n8n_landing_hardening.py`
- Result: `18 passed`.

## Notes

- Run trigger remains inside existing surfaces (footer + MiniTasks), matching no-new-window grandma constraint.
