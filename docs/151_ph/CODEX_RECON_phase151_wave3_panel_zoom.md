# CODEX RECON — Phase 151 Wave 3 (Panel Zoom)

Date: 2026-02-15
Scope: frontend only

## MARKER_151.8_RECON
Before changes:
- ARCHITECT tab used `client/src/components/panels/ArchitectChat.tsx`.
- MCC area used different chat components (`client/src/components/mcc/ArchitectChat.tsx`) with separate local state.
- Result: compact and expanded were not zoom states of one source of truth.

Fix applied:
- `client/src/components/panels/ArchitectChat.tsx` now supports `mode: 'compact' | 'expanded'`.
- Shared chat state moved to Zustand store (`client/src/store/useArchitectStore.ts`) for messages/model/loading.
- Compact mode uses same data, shows recent messages + minimal input + expand button.
- Expanded mode keeps full UI and has collapse button.

## MARKER_151.9_RECON
Before changes:
- `PipelineStats` had only one expanded view.
- No compact preview in MCC detail panel.

Fix applied:
- `client/src/components/panels/PipelineStats.tsx` now supports `mode: 'compact' | 'expanded'`.
- Compact mode: 2x2 summary + expand button.
- Expanded mode: existing full stats + collapse button.
- `client/src/components/mcc/MCCDetailPanel.tsx` now embeds compact stats.

## MARKER_151.10_RECON
Before changes:
- `KeyDropdown` lacked direct path to full BALANCE tab.

Fix applied:
- `client/src/components/mcc/KeyDropdown.tsx` now has `View all ->` action to open BALANCE tab.

## MARKER_151.8_151.9_TAB_ROUTING
Before changes:
- DevPanel active tab lived only in local `useState`.
- Compact widgets could not switch tabs.

Fix applied:
- Added `client/src/store/useDevPanelStore.ts`.
- `client/src/components/panels/DevPanel.tsx` now uses shared tab store.
- Compact/expanded widgets switch tabs through the same store.
