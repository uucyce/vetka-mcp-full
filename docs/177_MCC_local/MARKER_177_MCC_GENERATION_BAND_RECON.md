# MARKER_177 - MCC generation-band recon

Date: 2026-03-13

## Recon + markers

- `MARKER_177.GEN_BAND.SHARED_RENDER_LAYER`
  - Code-scope descendants still flow through one visual component family in `client/src/components/mcc/nodes/RoadmapTaskNode.tsx`.
  - This is why lowering floors for grandchildren also improved daughters.

- `MARKER_177.GEN_BAND.CUMULATIVE_DEPTH_PRESENT`
  - The graph already carries cumulative fractal depth through `rd_depth_total`.
  - The chain builder in `client/src/components/mcc/MyceliumCommandCenter.tsx` writes cumulative depth for remapped nodes and inline edges.

- `MARKER_177.GEN_BAND.POLICY_SPLIT_REQUIRED`
  - The remaining gap is not "more global shrinking".
  - The remaining gap is a generation-aware policy split:
    - `depth1`
    - `depth2`
    - `depth3+`
  - Each band needs separate floors for node size, font, border, handles, and edges.

- `MARKER_177.GEN_BAND.GEOMETRY_SPLIT_REQUIRED`
  - Visual size alone is not enough.
  - The inline layout in `client/src/components/mcc/DAGView.tsx` also needs generation-aware `xGap/yGap`, or the hierarchy still reads as flat.

- `MARKER_177.GEN_BAND.PLAYWRIGHT_PATH`
  - Local MCC dev server can be started on `http://127.0.0.1:3002`.
  - Browser automation is available, but a fresh browser session currently opens with no hydrated project context, so graph inspection still needs either seeded state or a replay fixture.

## Decision

Apply the fractal rule as a generation-band policy, not one shared mini-layer clamp.

- `depth1` keeps current daughter readability
- `depth2` shrinks more aggressively
- `depth3+` shrinks again with stricter floors
- layout spacing follows the same split so generations read as nested

## Next verification

1. Contract tests for generation-band policy and spacing
2. Browser-side verification against a seeded MCC graph state
3. If the browser path still opens "no project context yet", add a replay/fixture path for Playwright-driven graph inspection
4. Prefer a reusable seeded fixture over ad-hoc browser state so repeated visual checks stay deterministic
