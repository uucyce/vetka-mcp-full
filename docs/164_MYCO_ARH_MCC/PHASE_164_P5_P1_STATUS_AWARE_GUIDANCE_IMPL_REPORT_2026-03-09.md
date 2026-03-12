# PHASE 164 — P5.P1 Status-Aware Workflow Guidance Impl Report (2026-03-09)

## Goal
Improve MYCO proactive quality after drill/workflow open so guidance reflects **current task status** (`pending/running/done/failed`) instead of generic run/retry text.

## Markers
1. `MARKER_164.P5.P1.MYCO.CHAT_STATUS_AWARE_NEXT_ACTIONS.V1`
2. `MARKER_164.P5.P1.MYCO.TOP_HINT_STATUS_AWARE_WORKFLOW_ACTIONS.V1`

## Impl
1. Updated compact/expanded MYCO quick-reply matrix in [MiniChat.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MiniChat.tsx):
- Added `statusAction` branch by `context.status`.
- Applied it to workflow-open role paths (`architect/coder/verifier/eval/other`).

2. Updated top hint workflow branch in [MyceliumCommandCenter.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MyceliumCommandCenter.tsx):
- Added `statusHintTail` from `selectedTaskMeta.status`.
- Workflow-open hints now end with state-specific action tail.

3. Added contract test:
- [test_phase164_p5_p1_status_aware_guidance_contract.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/test_phase164_p5_p1_status_aware_guidance_contract.py)

## Verify
```bash
pytest -q tests/test_phase164_p5_p1_status_aware_guidance_contract.py \
  tests/test_phase164_p4_top_hint_ticker_contract.py \
  tests/test_phase164_p2_trigger_matrix_contract.py
```

Expected:
1. Both P5.P1 markers present.
2. Status branches `running/done/failed` present in chat + top hint logic.
3. Existing P4/P2 contracts still pass.
