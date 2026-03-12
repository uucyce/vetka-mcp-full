# PHASE 168 — W9.F Runtime Trigger Switching Report

Date: 2026-03-11
Status: implemented
Protocol stage: IMPL NARROW -> VERIFY TEST

## Goal

Make compact MCC surfaces react to live workflow/runtime events without violating the role-placement policy:

- top MYCO stays MYCO
- compact `Chat` shows role avatars only in explicit role mode
- compact `Stats` may pulse workflow/task roles for the currently selected task only

## Implemented

### 1. Compact Stats trigger-aware role pulses

File:
- `client/src/components/mcc/MiniStats.tsx`

Added:
- workflow-selection pulse on `mcc-workflow-selected`
- task lifecycle pulse on `task-board-updated`
- task-scope guard to avoid cross-task leakage

Markers:
- `MARKER_168.MYCO.RUNTIME.MINI_STATS_WORKFLOW_SELECTED_TRANSITION.V1`
- `MARKER_168.MYCO.RUNTIME.MINI_STATS_TASK_BOARD_TRANSITION.V1`

### 2. Compact Chat safe model-selected transition

File:
- `client/src/components/mcc/MiniChat.tsx`

Added:
- role pulse on `mcc-model-updated` only in role-specific architect mode
- helper-mode reset so MYCO never re-enters with stale architect/coder/scout visuals

Markers:
- `MARKER_168.MYCO.RUNTIME.MINI_CHAT_MODEL_SELECTED_TRANSITION.V1`
- `MARKER_168.MYCO.RUNTIME.MINI_CHAT_TRIGGER_RESET_ON_HELPER.V1`
- `MARKER_168.MYCO.RUNTIME.MINI_CHAT_COMPACT_HELPER_STAYS_MYCO.V1`

## Result

`W9.F` now provides deterministic compact-surface trigger switching:

- explicit workflow choice pulses the workflow lead role in compact `Stats`
- task lifecycle may pulse coder/verifier in compact `Stats`
- role-model updates may pulse the current role in compact `Chat`
- helper-mode MYCO remains canonical and does not inherit role visuals

## Verification

Tests:
- `tests/phase168/test_myco_runtime_role_preview_contract.py`
- `tests/phase168/test_myco_runtime_trigger_switching_contract.py`

Expected runtime outcome:
- top helper click keeps compact `Chat` on MYCO
- architect/task mode keeps architect avatar in compact `Chat`
- compact `Stats` reflects live task/workflow transitions without affecting unrelated tasks
