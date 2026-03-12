# CODEX BRIEF — Phase 170 Wave 18 Scene Graph Surface

## Scope
Safe-zone only:
- `client/e2e/*.spec.cjs`
- `docs/170_ph_VIDEO_edit_mode/*.md`
- `data/task_board.json`

Do not touch shared CUT UI or backend files.

## Goal
Cover the debug-shell `Scene Graph Surface` card in `/cut` with a browser smoke and docs pack.

## Tasks
- `P1` smoke: add `client/e2e/cut_debug_scene_graph_surface_smoke.spec.cjs`
- `P2` recon: document stable selectors, node anchors, and refresh behavior
- `P3` mock matrix: define the minimum `project-state` shape and refresh sequence

## Acceptance
- smoke verifies `Scene graph not ready.` empty state
- smoke verifies hydrated scene graph nodes after refresh
- `cd client && npx playwright test e2e/cut_debug_scene_graph_surface_smoke.spec.cjs` passes
- `cd client && npx vite build` passes
