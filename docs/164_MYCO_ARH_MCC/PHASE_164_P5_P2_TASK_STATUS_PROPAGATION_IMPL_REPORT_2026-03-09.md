# PHASE 164 — P5.P2 Task Status Propagation Impl Report (2026-03-09)

## Goal
Fix real status-aware behavior for MYCO top hints after workflow open by propagating task status from active task metadata, then tighten `done/failed` next actions.

## Marker
1. `MARKER_164.P5.P2.MYCO.TASK_STATUS_PROPAGATION_FROM_ACTIVE_TASK.V1`

## Impl
1. Updated [MyceliumCommandCenter.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MyceliumCommandCenter.tsx):
- Added canonical `status` extraction inside `selectedTaskMeta`.
- Included `status` in returned meta object (used by top-hint status tail).
- Strengthened `done/failed` tails:
  - `done`: review artifacts and pick next queued/pending task in Tasks.
  - `failed`: inspect Context and retry with corrected model/prompt.

2. Updated [MiniChat.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MiniChat.tsx):
- Aligned `done` status action with explicit next-task move in Tasks.

3. Added contract test:
- [test_phase164_p5_p2_task_status_propagation_contract.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/test_phase164_p5_p2_task_status_propagation_contract.py)

## Verify
```bash
pytest -q \
  tests/test_phase164_p5_p2_task_status_propagation_contract.py \
  tests/test_phase164_p5_p1_status_aware_guidance_contract.py \
  tests/test_phase164_p4_top_hint_ticker_contract.py
```
