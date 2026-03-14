# PHASE 164 — P5.P3 Workflow Priority Over Unfold Impl Report (2026-03-09)

## Goal
Fix MYCO guidance fallback where workflow is already visible/selected but hint still shows `module unfolded` branch.

## Markers
1. `MARKER_164.P5.P3.MYCO.WORKFLOW_NODE_PRIORITY_OVER_UNFOLD.V1`
2. `MARKER_164.P5.P3.MYCO.TOP_HINT_WORKFLOW_NODE_PRIORITY_OVER_UNFOLD.V1`

## Impl
1. Updated [MiniChat.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MiniChat.tsx):
- Added `workflowNodeContext` detector (`graphKind starts workflow_` or agent with workflow id).
- Promoted workflow reply branch from `taskDrillExpanded` to `taskDrillExpanded || workflowNodeContext`.
- Result: when workflow node is selected, MYCO keeps workflow next-actions instead of module-unfold fallback.

2. Updated [MyceliumCommandCenter.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MyceliumCommandCenter.tsx):
- `isWorkflowFocused` now also includes `workflowAgentFocused`.
- Reordered top-hint branches so workflow branch runs before node-unfold branch.
- Result: top hint remains workflow-actionable on selected workflow node/agent even if roadmap unfold state is still `expanded`.

3. Added contract test:
- [test_phase164_p5_p3_workflow_priority_over_unfold_contract.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/test_phase164_p5_p3_workflow_priority_over_unfold_contract.py)

## Verify
```bash
pytest -q \
  tests/test_phase164_p5_p3_workflow_priority_over_unfold_contract.py \
  tests/test_phase164_p5_p2_task_status_propagation_contract.py \
  tests/test_phase164_p5_p1_status_aware_guidance_contract.py \
  tests/test_phase162_p4_p2_myco_guidance_matrix_contract.py
```
