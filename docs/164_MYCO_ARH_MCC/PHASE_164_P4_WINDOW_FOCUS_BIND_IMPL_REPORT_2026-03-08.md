# PHASE 164 — P4 Window Focus Bind Impl Report (2026-03-08)

## Scope
Bind MYCO guidance to **all mini windows** (including expanded/fullscreen state) so top-hint and quick-chat stop falling back to generic drill guidance when operator focus is on window-level actions.

User constraint captured:
1. Every mini window has fullscreen mode.
2. Fullscreen/expanded state must affect guidance priority.

## Markers
1. `MARKER_164.P4.WINDOW_FOCUS_EVENT_BIND_FRONTEND.V1`
2. `MARKER_164.P4.WINDOW_FOCUS_CONTEXT_PAYLOAD_BIND.V1`
3. `MARKER_164.P4.WINDOW_FOCUS_TOP_HINT_PRIORITY.V1`
4. `MARKER_164.P4.WINDOW_FOCUS_BACKEND_NORMALIZATION.V1`
5. `MARKER_164.P4.WINDOW_FOCUS_ROLE_PACKET_ACTIONS.V1`

## Implemented
1. Frontend focus event bind
- Source event: `mcc-miniwindow-focus` emitted from `MiniWindow`.
- Consumer: [MyceliumCommandCenter.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MyceliumCommandCenter.tsx)
- Stored state: `{ windowId, state }`, with minimize-clearing behavior.

2. Context payload enrichment
- Added `windowFocus`, `windowFocusState` to [MiniContext.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MiniContext.tsx) payload contract.
- Filled from MCC state in `miniContextPayload`.

3. Top-hint priority by focused window
- In [MyceliumCommandCenter.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MyceliumCommandCenter.tsx), window-focused branches now override generic drill hint:
1. `balance`
2. `stats`
3. `tasks`
4. `context`
5. `chat`
- Expanded/fullscreen state is reflected in wording.

4. Quick-chat payload bind
- Added `window_focus` and `window_focus_state` fields in both compact and expanded chat sends in [MiniChat.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MiniChat.tsx).

5. Backend normalization + role packet
- Extended `_normalize_guidance_context(...)` and `_build_role_aware_instruction_packet(...)` in [chat_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/chat_routes.py) with window-focus branches.
- Added window-focus fields to retrieval query enrichment.

## Verify
Command:
```bash
pytest -q tests/test_phase164_p1_role_aware_instruction_core.py tests/test_phase164_p2_trigger_matrix_contract.py tests/test_phase162_p4_p2_myco_guidance_matrix_contract.py
```

Result:
1. `12 passed`

## Notes
1. This step intentionally does not touch DEV panel behavior.
2. Next logical check: visual QA in runtime for each mini window compact/expanded/minimized transition.
