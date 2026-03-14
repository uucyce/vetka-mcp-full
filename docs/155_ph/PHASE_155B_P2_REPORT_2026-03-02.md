# PHASE 155B-P2 REPORT (2026-03-02)

Protocol stage: `REPORT` after `IMPL NARROW -> VERIFY`.

## Scope
Implement MCC UI source mode and source badge:
1. persistent `workflow_source_mode = runtime|design|predict`
2. source-mode requests bound to canonical workflow graph APIs
3. visible source badge in MCC canvas

## Marker Contract
1. `MARKER_155B.CANON.UI_SOURCE_MODE.V1`
2. `MARKER_155B.CANON.UI_SOURCE_BADGE.V1`

## Implementation Notes
1. Added persistent source mode in MCC Zustand store (`localStorage` key: `mcc_workflow_source_mode_v1`).
2. Added source-mode switch in `MyceliumCommandCenter` and bound API endpoint routing:
   - `runtime -> /api/workflow/runtime-graph/{task_id}`
   - `design -> /api/workflow/design-graph/{task_id}`
   - `predict -> /api/workflow/predict-graph/{task_id}`
3. Added source badge showing active mode + backend graph source (`version` or `live_build`).
4. Added mode-aware graph adaptation for roadmap rendering with fallback to existing design roadmap graph.

## Implementation Anchors
1. [useMCCStore.ts](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/store/useMCCStore.ts)
2. [MyceliumCommandCenter.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MyceliumCommandCenter.tsx)
3. [test_phase155b_p2_ui_source_mode_markers.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/test_phase155b_p2_ui_source_mode_markers.py)

## Verification
1. `pytest -q tests/test_phase155b_p2_ui_source_mode_markers.py` -> `2 passed`
2. `pytest -q tests/test_phase155b_p1_graph_source_routes.py tests/test_phase155b_p0_1_schema_routes.py tests/test_phase155_p0_drilldown_markers.py` -> `29 passed`

## DoD Status
1. Mode switch persists in store: Done.
2. Mode reflected in requests and UI labels: Done.
3. Manual one-canvas flow check: Pending manual UI smoke (automated marker verification is green).

## Forward Plan Note
Template library stage is now explicitly tracked for post-converter readiness (`155B-P3.5`), to minimize Architect token spend and avoid from-scratch workflow generation.

## Next Protocol Gate
`WAIT GO` before starting `155B-P3`.
