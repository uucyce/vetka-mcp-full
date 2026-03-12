# Phase 170 CUT Wave 9 Marker Archive and Focus

## Goal
Keep the CUT browser roadmap moving in safe-zone only, focusing on archive/focus flows that already exist in the debug shell marker UI.

## Safe edit zone
- `client/e2e/*.spec.cjs`
- `docs/170_ph_VIDEO_edit_mode/*.md`
- `data/task_board.json`

## Do not touch
- `client/src/CutStandalone.tsx`
- `client/src/components/cut/TimelineTrackView.tsx`
- `client/src/components/cut/TransportBar.tsx`
- `client/src/components/cut/CutEditorLayout.tsx`
- backend CUT routes/store

## Part G — Marker archive/focus lane

### G1
Create `client/e2e/cut_debug_marker_archive_focus_smoke.spec.cjs`.
- Toggle into debug shell.
- Mock selected-shot marker groups plus global markers.
- Verify `Focus Marker In Timeline`, `Archive Marker`, and `Show All Global Markers` / `Show Active Global Only`.
- Verify `/api/cut/timeline/apply` and `/api/cut/time-markers/apply` payloads and post-refresh visibility changes.

### G2
Write `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_DEBUG_MARKER_ARCHIVE_FOCUS_RECON_2026-03-12.md`.
- Stable selectors and anchor texts for selected/global marker cards.
- Expected status texts for focus/archive flows.

### G3
Write `docs/170_ph_VIDEO_edit_mode/PHASE_170_CUT_DEBUG_MARKER_ARCHIVE_FOCUS_MOCK_MATRIX_2026-03-12.md`.
- Minimum marker bundle shape.
- Required timeline/time-marker apply mocks.
- Which routes can remain unmocked.
