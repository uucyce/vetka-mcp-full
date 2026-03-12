# PHASE 155A — Wave C / Architect Key Scope Guard (2026-03-03)

Protocol stage: `IMPL NARROW -> VERIFY`

## Marker
- `MARKER_155A.WC.ARCH_MODEL_BIND_SELECTED_BALANCE_KEY.V1`

## Scope implemented
1. Added strict UI guard in `MiniContext` model editor for `architect` role:
   - when key is selected in `MiniBalance`, architect model save is blocked if model is out of selected provider scope.
2. Added contextual hint when current architect model is out of scope.
3. Added one-click action `align to key` to pick first in-scope model and proceed with save.

## File changed
- `client/src/components/mcc/MiniContext.tsx`

## Behavior
1. `role !== architect`:
   - no strict scope block.
2. `role === architect` + no selected key:
   - no scope block (auto/all mode).
3. `role === architect` + selected key:
   - save disabled for out-of-scope model,
   - hint + align action shown.

## Verify status
- UI-level verify pending manual check in running MCC session.
