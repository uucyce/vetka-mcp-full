# PHASE 170 CUT Scene Graph Node-Click Stabilization (2026-03-13)

## Scope
Stabilize the isolated loaded-state smoke that clicks a DAG node and expects a `/api/cut/timeline/apply` round-trip.

## Hardening already applied
- Added stable DAG node label hooks in shared MCC node renderers:
  - `data-testid="dag-node-label"`
  - `data-node-label`
  - `data-node-task-id`
- Moved the loaded review spec to use exact `data-node-label="Take A"` targeting instead of text-only lookup.
- Converted the loaded-review server cleanup to an awaited async shutdown path.

## Current status
- The new edge-filter + mini-card smoke is stable and passing.
- The node-click loaded smoke still hangs after launch in the Playwright runner lane.
- The failure is now isolated from selector ambiguity; the remaining problem is runner/round-trip stability, not basic visibility.

## Next steps
1. Split node-click smoke into a narrower dedicated spec with no extra loaded assertions.
2. Add request counters / explicit status assertions around `Graph focus -> timeline:`.
3. If the hang persists, capture request timeline from the mocked routes and compare with the passing edge-filter smoke harness.

## Markers
- `MARKER_170.BROWSER_RETURN.NODE_CLICK`
- `MARKER_170.SCENE_GRAPH.NODE_CLICK.STABILIZATION`
