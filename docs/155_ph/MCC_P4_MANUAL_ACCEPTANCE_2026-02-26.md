# MCC P4 Manual Acceptance (2026-02-26)

Date: 2026-02-26  
Scope: `MARKER_155.P4_1.FOCUS_ACTION_PARITY.V1`, `MARKER_155.P4_2.FOCUS_MEMORY.V1`, `MARKER_155.P4_3.FOCUS_DISPLAY_MODES.V1`  
Owner: MCC UX/Runtime

## Goal

Close G1 with a fresh manual acceptance run for P4 UX behavior:
- focus persistence across zoom/drill,
- Architect prefill behavior,
- focus display mode stability.

## Preconditions

- App running with MCC UI.
- Roadmap DAG loaded for a real project scope.
- MiniChat visible.

## Checklist

1. Shift-click multi-select in DAG:
- Select 2+ nodes with Shift.
- Expected: focus set grows additively, no reset on each click.

2. Focus display mode behavior:
- Switch between `all`, `selected+deps`, `selected-only`.
- Expected: filtering behavior matches mode semantics, no stale hidden nodes after mode change.

3. Zoom/drill persistence:
- With active focus set, perform zoom in/out and drill transitions.
- Expected: valid focused ids are preserved, stale ids are pruned safely.

4. Architect prefill parity:
- Trigger `Shift+Enter` from focused selection.
- Trigger "Ask Architect" button from same focus context.
- Expected: both actions prefill MiniChat with equivalent selected scope payload.

5. Regression check:
- Clear focus.
- Recreate focus set.
- Repeat steps 2-4.
- Expected: no stuck state, no empty prefill on non-empty focus set.

## Result (current run)

Status: `PENDING MANUAL IN TARGET RUNTIME`

Notes:
- This artifact defines acceptance contract and evidence format.
- Manual runtime execution must be completed in local Mycelium desktop/runtime environment.

## Evidence to attach on completion

- Short screen capture or 3 screenshots:
  - multi-select state,
  - zoom/drill return with preserved focus,
  - MiniChat prefill from Shift+Enter/Ask Architect.
- Final verdict line:
  - `P4 manual UX confirmation: GO` or
  - `P4 manual UX confirmation: NO-GO` (+ blocker list).
