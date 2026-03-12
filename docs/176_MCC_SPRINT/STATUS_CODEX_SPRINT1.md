# STATUS_CODEX_SPRINT1

Date: 2026-03-11

- MARKER_176.15: centralized MCC API helpers are wired through `client/src/config/api.config.ts`.
- MARKER_176.7: edge labels are preserved/rendered through `client/src/utils/dagLayout.ts`.
- MARKER_176.18: `client/src/components/mcc/FirstRunView.tsx` now shows backend/network errors and retry UI.
- MARKER_176.1F: roadmap-to-task frontend bridge is wired in `client/src/store/useMCCStore.ts` and `client/src/components/mcc/MyceliumCommandCenter.tsx`.
- MARKER_176.3F: results Apply/Reject wiring is present in `client/src/store/useMCCStore.ts` and `client/src/components/mcc/MyceliumCommandCenter.tsx`.

Verification:

- `rg -n "localhost:5001" client/src/components/mcc --glob '*.tsx'` -> no matches
- `cd client && VITE_MODE=mcc npx vite build` -> passed
- `cd client && npx vite build` -> passed
- `cd client && npx tsc --noEmit` -> blocked by branch-wide TypeScript debt beyond Sprint 1 only

Scenario status:

- `MARKER_176.T8`: Vite builds pass; `tsc` blocked
- `MARKER_176.T9`: code path implemented; manual UI scenario not run
- `MARKER_176.T10`: code path implemented; manual UI scenario not run
- `MARKER_176.T11`: edge labels implemented; manual visual confirmation pending
