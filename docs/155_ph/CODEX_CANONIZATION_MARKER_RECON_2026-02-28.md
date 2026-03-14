# CODEX Canonization Marker Recon (2026-02-28)

Status: Recon complete  
Scope: Marker audit for Canonization Roadmap V1.1 (`runtime/design/predict + input_matrix + multi-format`)

## 1. Protocol
1. Scanned markers in `src`, `client`, `docs/155_ph`, `docs/besedii_google_drive_docs`.
2. Compared actual marker footprint against roadmap V1.1 checklist.
3. Produced implementation map: `EXISTS`, `MISSING`, `INSERT_TARGET`.

## 2. What Already Exists (Strong Base)
1. Input-matrix and SCC backend foundation exists:
- `MARKER_155.MODE_ARCH.V11.P1`
- `MARKER_155.INPUT_MATRIX.SCANNERS.V1`
- `MARKER_155.INPUT_MATRIX.ROOT_SCORE.V1`
- `MARKER_155.INPUT_MATRIX.BACKBONE_DAG.V1`
- `MARKER_155.INPUT_MATRIX.ARCH_DIRECTION_INVERT.V1`
- `MARKER_155.INPUT_MATRIX.FOLDER_OVERVIEW.V1`
- code anchor: [mcc_scc_graph.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/mcc_scc_graph.py)
2. Single-canvas drilldown physics exists:
- `MARKER_155A.G26.*`, `MARKER_155A.G27.*`, `MARKER_155A.P2.LOD_THRESHOLDS`
- code anchors: [DAGView.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/DAGView.tsx), [MyceliumCommandCenter.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MyceliumCommandCenter.tsx)
3. New guard markers already added:
- `MARKER_155A.G28.WF_SOURCE_SCOPE_GUARD`
- `MARKER_155A.G28.WF_TEMPLATE_DEDIRECT_ARCH_CODER`
- code anchor: [MyceliumCommandCenter.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MyceliumCommandCenter.tsx)
4. Engram DAG prefs markers already present:
- `MARKER_155.MEMORY.ENGRAM_DAG_PREFS.V1`
- code anchors: [mcc_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/mcc_routes.py), [user_memory.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/user_memory.py), [useStore.ts](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/store/useStore.ts)

## 3. What Is Missing vs Roadmap V1.1
1. Runtime canonical graph endpoints are missing:
- `GET /api/workflow/runtime-graph/{task_id}`
- `GET /api/workflow/design-graph/{workflow_id}`
- `GET /api/workflow/predict-graph/{task_id}`
2. Canonical schema endpoints are missing:
- `GET /api/workflow/schema/versions`
- `POST /api/workflow/schema/migrate`
- `GET /api/workflow/event-schema`
3. Input-matrix enrichment endpoint is missing:
- `POST /api/workflow/enrich/input-matrix/{graph_id}`
4. Drift endpoint is missing:
- `GET /api/workflow/drift-report/{task_id}`
5. UI source-mode contract is missing in explicit form:
- `workflow_source_mode = runtime|design|predict` as first-class state + badge
6. Runtime event schema marker contract is missing:
- no canonical event schema marker in pipeline builder path
7. Multi-format conversion markers are missing for `xlsx/md/xml` import/export.
8. Spectral checks are partially present conceptually, but missing as canonicalization markers tied to roadmap phases.

## 4. Marker Gap Matrix (Exists / Missing / Where to Integrate)
| Area | Status | Marker (existing or proposed) | Insert target |
|---|---|---|---|
| Runtime graph source of truth | Partial | `MARKER_155A.G28.WF_SOURCE_SCOPE_GUARD` exists; need runtime builder marker | [agent_pipeline.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/agent_pipeline.py), new builder module |
| Canonical schema lock | Missing | `MARKER_155B.CANON.SCHEMA_LOCK.V1` | new `src/services/workflow_canonical_schema.py` |
| Schema versioning protocol | Missing | `MARKER_155B.CANON.SCHEMA_VERSIONING.V1` | [workflow_store.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/workflow_store.py) + new schema service |
| Runtime event schema | Missing | `MARKER_155B.CANON.EVENT_SCHEMA.V1` | [agent_pipeline.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/agent_pipeline.py) |
| Runtime graph endpoint | Missing | `MARKER_155B.CANON.RUNTIME_GRAPH_API.V1` | [workflow_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/workflow_routes.py) or new route module |
| Design graph endpoint | Missing | `MARKER_155B.CANON.DESIGN_GRAPH_API.V1` | same as above |
| Predict graph endpoint | Missing | `MARKER_155B.CANON.PREDICT_GRAPH_API.V1` | same as above + [mcc_predictive_overlay.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/mcc_predictive_overlay.py) |
| Input-matrix enrich endpoint | Missing | `MARKER_155B.CANON.INPUT_MATRIX_ENRICH_API.V1` | [workflow_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/workflow_routes.py) |
| Drift report endpoint | Missing | `MARKER_155B.CANON.DRIFT_REPORT_API.V1` | [mcc_dag_compare.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/mcc_dag_compare.py) + route |
| Source mode in MCC | Missing | `MARKER_155B.CANON.UI_SOURCE_MODE.V1` | [useMCCStore.ts](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/store/useMCCStore.ts), [MyceliumCommandCenter.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MyceliumCommandCenter.tsx) |
| Source badge | Missing | `MARKER_155B.CANON.UI_SOURCE_BADGE.V1` | [MyceliumCommandCenter.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MyceliumCommandCenter.tsx) |
| Multi-format convert API | Missing | `MARKER_155B.CANON.CONVERT_API.V1` | new converter service + route |
| XLSX importer/exporter | Missing | `MARKER_155B.CANON.XLSX_CONVERTER.V1` | new `src/services/workflow_convert_xlsx.py` |
| Markdown importer/exporter | Missing | `MARKER_155B.CANON.MD_CONVERTER.V1` | new `src/services/workflow_convert_md.py` |
| XML importer/exporter | Missing | `MARKER_155B.CANON.XML_CONVERTER.V1` | new `src/services/workflow_convert_xml.py` |
| Spectral layout quality gate | Missing | `MARKER_155B.CANON.SPECTRAL_LAYOUT_QA.V1` | [dagLayout.ts](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/utils/dagLayout.ts) + backend diagnostics route |
| Spectral anomaly diagnostics | Missing | `MARKER_155B.CANON.SPECTRAL_ANOMALY.V1` | backend diagnostics service + API |
| Storage contract | Missing | `MARKER_155B.CANON.STORAGE_CONTRACT.V1` | schema service + persistence layer |
| Approval/audit for G_design | Missing | `MARKER_155B.CANON.DESIGN_APPROVAL_AUDIT.V1` | workflow store/routes |
| Scale strategy >10K | Missing | `MARKER_155B.CANON.SCALE_POLICY.V1` | layout service + UI drill strategy |

## 5. Recommended Marker Namespace for Canonization
To avoid collisions with old 155A drill markers:
1. Use `MARKER_155B.CANON.*` for all V1.1 canonization work.
2. Keep `MARKER_155A.G26/G27/G28` for already shipped drilldown behavior.
3. Keep `MARKER_155.INPUT_MATRIX.*` for existing SCC/input_matrix engine markers.

## 6. Unified Implementation Order (Marker-First)
1. `MARKER_155B.CANON.SCHEMA_LOCK.V1`
2. `MARKER_155B.CANON.SCHEMA_VERSIONING.V1`
3. `MARKER_155B.CANON.EVENT_SCHEMA.V1`
4. `MARKER_155B.CANON.RUNTIME_GRAPH_API.V1`
5. `MARKER_155B.CANON.UI_SOURCE_MODE.V1`
6. `MARKER_155B.CANON.UI_SOURCE_BADGE.V1`
7. `MARKER_155B.CANON.INPUT_MATRIX_ENRICH_API.V1`
8. `MARKER_155B.CANON.XLSX_CONVERTER.V1`
9. `MARKER_155B.CANON.MD_CONVERTER.V1`
10. `MARKER_155B.CANON.XML_CONVERTER.V1`
11. `MARKER_155B.CANON.DRIFT_REPORT_API.V1`
12. `MARKER_155B.CANON.SPECTRAL_LAYOUT_QA.V1`
13. `MARKER_155B.CANON.SPECTRAL_ANOMALY.V1`

## 7. Direct Answer (Delegation / Cost)
1. In this terminal flow I cannot directly invoke a separate “Codex mini 5.1 team” runtime as an internal sub-agent switch.
2. Fast/cheap recon is still achieved here via marker-grep + focused mapping (done in this report).
3. If needed, we can script this audit into a repeatable `marker_recon` command for daily cheap checks.

