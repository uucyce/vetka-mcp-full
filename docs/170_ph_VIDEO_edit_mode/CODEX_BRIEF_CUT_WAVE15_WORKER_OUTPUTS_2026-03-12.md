# CODEX BRIEF — Phase 170 Wave 15 Worker Outputs

## Scope
Safe-zone only:
- `client/e2e/*.spec.cjs`
- `docs/170_ph_VIDEO_edit_mode/*.md`
- `data/task_board.json`

Do not touch shared CUT UI or backend files.

## Goal
Cover the debug-shell `Worker Outputs` card in `/cut` with a browser smoke and docs pack.

## Tasks
- `M1` smoke: add `client/e2e/cut_debug_worker_outputs_smoke.spec.cjs`
- `M2` recon: document stable selectors and representative rows
- `M3` mock matrix: define the minimum `project-state` shape and refresh behavior

## Acceptance
- smoke verifies counts for worker bundles and sync outputs
- smoke checks representative `WF`, `TX`, `SYNC`, and `TC` rows plus refresh behavior
- `cd client && npx playwright test e2e/cut_debug_worker_outputs_smoke.spec.cjs` passes
- `cd client && npx vite build` passes
