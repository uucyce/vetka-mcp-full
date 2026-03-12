# PHASE 155 — MCC MVP Readiness Recon (2026-03-04)

Status: `RECON + markers`  
Protocol: `RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`

## 1) Purpose

Prepare next phase with one factual baseline:
1. what was planned,
2. what is actually implemented now,
3. what is still missing for MCC MVP.

## 2) Sources used

Primary phase docs:
1. `docs/155_ph/PHASE_155_RECON_FINAL_2026-03-02.md`
2. `docs/155_ph/PHASE_155E_CLOSEOUT_REPORT_2026-03-03.md`
3. `docs/155_ph/PHASE_155A_GRANDMA_MODE_RECON_MARKERS_2026-03-02.md`
4. `docs/155_ph/PHASE_155A_WAVE_D_RUNTIME_VERIFY_REPORT_2026-03-03.md`
5. `docs/155_ph/PHASE_155E_WAVE_E_RECON_MARKERS_2026-03-03.md`
6. `docs/155_ph/CODEX_UNIFIED_DAG_MASTER_PLAN.md`
7. `docs/155_ph/ARCHITECT_BUILD_CONTRACT_V1_CHECKLIST.md`

Cross-phase bug summary checked for drift:
1. `docs/159_ph_bugs/PHASE_130_160_RECON_SUMMARY_2026-03-04.md`

Code anchors checked:
1. `client/src/components/mcc/MyceliumCommandCenter.tsx`
2. `client/src/components/mcc/MiniTasks.tsx`
3. `client/src/components/mcc/MiniContext.tsx`
4. `client/src/hooks/useRoadmapDAG.ts`
5. `client/src/store/useMCCStore.ts`
6. `src/api/routes/workflow_routes.py`

## 3) Reality check by marker groups

## 3.1 MCC Grandma/UI baseline (155A)

### Confirmed implemented in current code (or functional equivalent)
1. `MARKER_155A.G21.SINGLE_CANVAS_STATE`
2. `MARKER_155A.G26.*` drilldown geometry/packing base
3. `MARKER_155A.G27.*` reserved workflow frame / orientation controls
4. `MARKER_155A.G28.*` source-scope guard and template dedirect
5. `MARKER_155A.WC.MODEL_EDIT_BIND.V2` (MiniContext model editor path)
6. `MARKER_155A.WD.WORKFLOW_RUNTIME_ONLY_TRUTH.V1` (inline workflow runtime forcing)

### Partially aligned / drifted from docs
1. `MARKER_155A.P3.STATS_CONTEXT(.V2)` — contextual behavior exists, but strict test contract is not stabilized.
2. `MARKER_155A.P3.STREAM_CONTEXT(.V2)` — behavior path exists in UI flow, but no stable green regression pack for this branch snapshot.
3. `MARKER_155A.P4.CONFLICT_POLICY(.V2)` — documented as gear-only policy; explicit tested contract is not green in current branch.

## 3.2 Wave E workflow editing/tasks/n8n (155E)

### Confirmed implemented in current code (narrow)
1. `MARKER_155E.WF.TASKS_PANEL.MINI_SCROLL_PARITY.V1`
2. `MARKER_155E.WF.TASKS_PANEL.SELECTION_SYNC_WITH_DAG.V1`
3. `MARKER_155E.WF.TASKS_PANEL.CONTEXT_ACTIONS.START_STOP.V1`
4. `MARKER_155E.WF.EXEC.HEARTBEAT_TASK_PANEL_CONTROL.V1`
5. `MARKER_155E.ROADMAP_TASK_ANCHOR_ALWAYS_VISIBLE.V1`
6. `MARKER_155E.ROADMAP_DEFAULT_TASK_ANCHOR_SELECTION.V1`

### Drift / not fully closed
1. `MARKER_155E.WE.EDGE_EDITOR_MINIPANEL.V1` — test expects explicit contract; current code path not matching expected marker/shape.
2. `MARKER_155E.WE.EDGE_PERSIST_CANONICAL.V1` — persistence contract expected by tests is not green.
3. `MARKER_155E.WE.RUNTIME_CANONICAL_ROUNDTRIP.V1` — n8n runtime mapping profile contract currently fails tests.
4. Regression marker pack (`MARKER_155E.REGRESSION.*`) is not fully in sync with current MCC code shape.

## 3.3 Canonization API layer (155B)

Critical mismatch vs historical reports:
1. `src/api/routes/workflow_routes.py` currently exposes only history/stats/details legacy routes.
2. 155B endpoints from prior reports are not present in this file state:
   - schema versions/migrate/event schema,
   - runtime/design/predict graphs,
   - drift report,
   - convert,
   - spectral endpoints,
   - input-matrix enrich endpoint.

Status:
1. `MARKER_155B.CANON.SCHEMA_*` service-layer artifacts exist in docs/history.
2. Route-layer closure for 155B in current branch snapshot: `NOT DONE`.

## 3.4 JEPA architect bootstrap (155C)

Current branch test evidence indicates contract drift:
1. expected helper functions/signatures in `architect_chat_routes.py` are missing,
2. expected JEPA bootstrap trace/force-flow contracts are not present in tested form,
3. build-design spectral autowire contract currently not satisfying test expectation.

Status:
1. 155C docs claim closure in prior iteration,
2. current branch snapshot for strict test contract: `NOT VERIFIED / DRIFTED`.

## 4) Test-grounded verification snapshot (today)

Executed:
1. `pytest -q tests/test_phase155b_p0_1_schema_routes.py tests/test_phase155b_p1_graph_source_routes.py tests/test_phase155b_p2_ui_source_mode_markers.py tests/test_phase155b_p3_convert_api.py tests/test_phase155b_p4_spectral_routes.py tests/test_phase155e_p0_contract_matrix.py tests/test_phase155e_p1_p2_edge_editor_persist.py tests/test_phase155e_p2_execution_semantics.py tests/test_phase155e_p2_run_trigger_visibility.py tests/test_phase155e_p3_template_family_registry.py tests/test_phase155e_p4_n8n_landing_hardening.py tests/test_phase155e_regression_graph_edges_and_context_menu.py tests/test_phase155e_task_anchor_and_source_mode_guards.py`
2. `pytest -q tests/test_phase155c_architect_jepa_bootstrap.py tests/test_phase155c_build_design_spectral_autowire.py`

Result summary:
1. 155B/155C/part of 155E contract packs: mostly failing in current branch snapshot.
2. `tests/test_phase155e_task_anchor_and_source_mode_guards.py`: `5 passed`.

## 5) Semantically close MCC TODO/readiness docs

Recommended working set for next phase planning:
1. `docs/155_ph/PHASE_155_RECON_FINAL_2026-03-02.md`
2. `docs/155_ph/PHASE_155_RECON_SUMMARY_2026-03-01.md`
3. `docs/155_ph/PHASE_155A_GRANDMA_MODE_ROADMAP_2026-03-02.md`
4. `docs/155_ph/PHASE_155E_WAVE_E_RECON_MARKERS_2026-03-03.md`
5. `docs/155_ph/PHASE_155E_CLOSEOUT_REPORT_2026-03-03.md`
6. `docs/155_ph/PHASE_155E_REGRESSION_RECON_CONTEXT_MENU_EDGES_2026-03-04.md`
7. `docs/155_ph/ARCHITECT_BUILD_CONTRACT_V1_CHECKLIST.md`
8. `docs/155_ph/MCC_RELEASE_GATE_V1.md`
9. `docs/155_ph/CODEX_UNIFIED_DAG_MASTER_PLAN.md`
10. `docs/159_ph_bugs/PHASE_130_160_RECON_SUMMARY_2026-03-04.md` (as historical snapshot, not source-of-truth)

## 6) MVP readiness verdict (MCC)

Verdict: `NO-GO for MVP release` (current branch snapshot).

Reason:
1. Route/API contract layer for 155B is not actually closed in live code snapshot.
2. 155C JEPA bootstrap contracts are not green by current tests.
3. 155E edge/persist/roundtrip contracts are only partially aligned.
4. UI is usable in core grandma flow, but backend/API + contract drift blocks MVP gate.

## 7) Next phase (narrow, execution-first)

Recommended next slice order:
1. `P0-RESTORE-CONTRACT`: restore 155B route layer (schema/graph/convert/spectral/enrich) in real router path used by app.
2. `P1-REBASE-TESTS`: align/repair 155E regression tests to actual intended contract where marker IDs were renamed; keep strict behavior assertions.
3. `P2-JEPA-BOOTSTRAP`: restore 155C helper/trace contracts in `architect_chat_routes.py` and spectral autowire payload field.
4. `P3-MVP-GATE-RUN`: run focused gate pack + manual grandma checklist from `ARCHITECT_BUILD_CONTRACT_V1_CHECKLIST.md` and `MCC_RELEASE_GATE_V1.md`.

## 8) Marker pack for next recon/implementation cycle

1. `MARKER_155F.RESTORE.WORKFLOW_ROUTES_CONTRACT.V1`
2. `MARKER_155F.RESTORE.WAVE_E_EDGE_PERSIST_CONTRACT.V1`
3. `MARKER_155F.RESTORE.JEPA_BOOTSTRAP_CONTRACT.V1`
4. `MARKER_155F.GATE.MVP_CHECKLIST_EXECUTION.V1`
5. `MARKER_155F.GATE.MVP_READY_VERDICT.V1`

