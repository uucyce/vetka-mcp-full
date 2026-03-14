# CODEX BRIEF — Phase 170 Wave 17 Timeline Surface

## Scope
Safe-zone only:
- `client/e2e/*.spec.cjs`
- `docs/170_ph_VIDEO_edit_mode/*.md`
- `data/task_board.json`

Do not touch shared CUT UI or backend files.

## Goal
Cover the debug-shell `Timeline Surface` card in `/cut` with a browser smoke and docs pack.

## Tasks
- `O1` smoke: add `client/e2e/cut_debug_timeline_surface_smoke.spec.cjs`
- `O2` recon: document stable selectors, lane anchors, and selection behavior
- `O3` mock matrix: define the minimum `project-state` shape and `/cut/timeline/apply` refresh sequence

## Acceptance
- smoke verifies `Timeline not ready. Run scene assembly.` empty state
- smoke verifies hydrated lanes/clips after refresh
- smoke clicks `Select First Clip` and confirms the selected clip re-renders as `timeline selected`
- `cd client && npx playwright test e2e/cut_debug_timeline_surface_smoke.spec.cjs` passes
- `cd client && npx vite build` passes
