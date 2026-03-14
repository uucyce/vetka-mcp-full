# CODEX BRIEF — Phase 170 Wave 14 CAM Ready

## Scope
Safe-zone only:
- `client/e2e/*.spec.cjs`
- `docs/170_ph_VIDEO_edit_mode/*.md`
- `data/task_board.json`

Do not touch shared CUT UI or backend files.

## Goal
Cover the debug-shell `CAM Ready` card in `/cut` with a browser smoke and docs pack.

## Tasks
- `L1` smoke: add `client/e2e/cut_debug_cam_ready_smoke.spec.cjs`
- `L2` recon: document stable selectors and visible anchors
- `L3` mock matrix: define the minimum `project-state` shape and refresh behavior

## Acceptance
- smoke proves `CAM Ready` renders an empty state for the selected shot, then hydrates after refresh
- smoke verifies selected-shot anchor, CAM marker count, status text, and representative `cam_payload` row
- `cd client && npx playwright test e2e/cut_debug_cam_ready_smoke.spec.cjs` passes
- `cd client && npx vite build` passes
