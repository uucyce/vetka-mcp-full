# PHASE 170 CUT Browser Smoke: Edge Filter + Mini Card (2026-03-13)

## Scope
- Confirm the promoted NLE `Scene Graph Surface` still works with the deterministic loaded fixture.
- Cover the explicit edge filter controls:
  - `All Edges`
  - `Structural Only`
  - `Overlay Only`
- Cover the `Selected Shot` graph mini-card in debug mode without re-entering the unstable DAG node-click lane.

## Stable lane
- Spec: `client/e2e/cut_scene_graph_edge_filter_minicard_smoke.spec.cjs`
- Fixture: `client/e2e/fixtures/cutSceneGraphLoadedFixture.cjs`
- Reserved port policy: use the main CUT review lane from `PHASE_170_CUT_LAUNCH_AND_PORT_PROTOCOL_2026-03-13.md`

## Assertions
1. NLE mode loads with `Graph Ready` and the shared Scene Graph pane.
2. Edge filter state defaults to `all`.
3. Switching to `structural` updates the visible filter state.
4. Switching to `overlay` updates the visible filter state.
5. Returning to `all` succeeds without page errors.
6. Switching to debug mode exposes `Selected Shot` graph enrichment:
   - `Primary Graph Mini Card`
   - `graph render mode`
   - `graph sync waveform`
   - `graph bucket selected_shot`
   - mini poster reuse image

## Marker
- `MARKER_170.BROWSER.SMOKE_EDGE_FILTER_MINI_CARD`

## Remaining gap
- DAG node click round-trip is still tracked separately. Keep it isolated from this smoke so runner instability does not block basic Scene Graph acceptance.
