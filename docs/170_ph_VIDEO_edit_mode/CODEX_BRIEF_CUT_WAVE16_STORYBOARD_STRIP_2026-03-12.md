# CODEX BRIEF — Phase 170 Wave 16 Storyboard Strip

## Scope
Safe-zone only:
- `client/e2e/*.spec.cjs`
- `docs/170_ph_VIDEO_edit_mode/*.md`
- `data/task_board.json`

Do not touch shared CUT UI or backend files.

## Goal
Cover the debug-shell `Storyboard Strip` card in `/cut` with a browser smoke and docs pack.

## Tasks
- `N1` smoke: add `client/e2e/cut_debug_storyboard_strip_smoke.spec.cjs`
- `N2` recon: document stable selectors and thumbnail-card anchors
- `N3` mock matrix: define the minimum `project-state` shape and refresh behavior

## Acceptance
- smoke verifies empty-state text, thumbnail cards, and `Select Clip` behavior after hydration
- smoke checks refresh behavior against a changed thumbnail bundle
- `cd client && npx playwright test e2e/cut_debug_storyboard_strip_smoke.spec.cjs` passes
- `cd client && npx vite build` passes
