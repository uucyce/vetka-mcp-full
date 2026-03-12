# PHASE 164 — P5.P4 Workflow Guidance Depth Impl Report (2026-03-11)

Status: `IMPL NARROW + VERIFY TEST`

## Goal
Make MYCO workflow guidance equally deep in the top hint and in chat once workflow is already open, so the helper stops collapsing to generic "workflow open" advice and instead explains the next action by role/gate/status.

## Markers
1. `MARKER_164.P5.P4.MYCO.WORKFLOW_ROLE_STATUS_DEPTH_MATRIX.V1`
2. `MARKER_164.P5.P4.MYCO.TOP_HINT_ROLE_STATUS_DEPTH_MATRIX.V1`
3. `MARKER_164.P5.P4.MYCO.WORKFLOW_OPEN_NO_GENERIC_ROADMAP_FALLBACK.V1`

## Implemented
1. Added shared top-hint workflow status branching:
- `running` -> monitor Stats/stream and wait for verifier/eval
- `done` -> inspect artifacts/result and pick the next queued task
- `failed` -> inspect failure cause and retry with corrected model/prompt
- fallback -> start from Tasks and iterate

2. Added top-hint role/gate guidance matrix for:
- `architect`
- `scout`
- `researcher`
- `coder`
- `verifier`
- `eval`
- `quality gate`
- `approval gate`
- `deploy`
- `measure`

3. Applied the same role-aware workflow guidance in both workflow focus paths:
- task workflow already expanded
- workflow node/agent selected while remaining in roadmap shell

4. Locked out generic roadmap/module-unfold fallback when workflow focus is already established.

## Files
- [MyceliumCommandCenter.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MyceliumCommandCenter.tsx)
- [MiniChat.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MiniChat.tsx)
- [test_phase164_p5_p4_workflow_guidance_depth_contract.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/test_phase164_p5_p4_workflow_guidance_depth_contract.py)

## Verification
Run:

```bash
pytest -q \
  tests/test_phase164_p5_p4_workflow_guidance_depth_contract.py \
  tests/test_phase164_p5_p3_workflow_priority_over_unfold_contract.py \
  tests/test_phase164_p5_p2_task_status_propagation_contract.py \
  tests/test_phase164_p5_p1_status_aware_guidance_contract.py
```

Expected:
- P5.P4 markers present
- top hint contains role-specific workflow copy
- top hint uses role-guidance helper in both workflow branches
- no regression in P5.P1/P5.P2/P5.P3 contracts

## Outcome
Top hint now describes the actual next operator action inside workflow, not only the fact that workflow is open.
