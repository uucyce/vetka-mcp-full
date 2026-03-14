# PHASE 155 RECON — FINAL VERIFIED BASELINE (2026-03-02)

**Purpose:** final, execution-ready baseline for Phase 155 continuation (canonization + MCC drilldown), after re-checking `PHASE_155_RECON_VERIFIED_2026-03-01.md` against the current codebase.

---

## 1) Audit Method

Verification performed on **2026-03-02** by direct code scan:
- marker presence in `src/`, `client/`, `tests/`
- endpoint presence in route modules
- file existence for claimed artifacts/tests

Primary docs cross-checked:
- `docs/155_ph/PHASE_155_RECON_VERIFIED_2026-03-01.md`
- `docs/155_ph/PHASE_155_RECON_SUMMARY_2026-03-01.md`
- `docs/155_ph/CODEX_CANONIZATION_MARKER_RECON_2026-02-28.md`

---

## 2) What Is Verified As Implemented

### A. MCC Drilldown markers (G26/G27/G28 + G25 policy)
Status: **Implemented and present**.

Key anchors:
- `client/src/components/mcc/DAGView.tsx`
- `client/src/components/mcc/MyceliumCommandCenter.tsx`
- `client/src/components/mcc/MiniTasks.tsx`
- deprecated locks in `MCCTaskList.tsx`, `TaskDAGView.tsx`, etc.

### B. Input Matrix / SCC markers
Status: **Implemented and present**.

Key anchor:
- `src/services/mcc_scc_graph.py`

### C. Engram memory marker
Status: **Implemented and present**.

Key anchors:
- `src/api/routes/mcc_routes.py`
- `src/memory/user_memory.py`

### D. Canonization P0 schema service markers
Status: **Implemented in service layer**.

Key anchor:
- `src/services/workflow_canonical_schema.py`
  - `MARKER_155B.CANON.SCHEMA_LOCK.V1`
  - `MARKER_155B.CANON.SCHEMA_VERSIONING.V1`
  - `MARKER_155B.CANON.EVENT_SCHEMA.V1`

### E. Test artifact claimed in recon
Status: **exists and contains 20 tests**.

Key anchor:
- `tests/test_phase155_p0_drilldown_markers.py`

---

## 3) Critical Corrections To Previous Recon Docs

### Correction #1: P0 API checklist was overstated
`PHASE_155_RECON_SUMMARY_2026-03-01.md` lists as DONE:
- `GET /api/workflow/schema/versions`
- `POST /api/workflow/schema/migrate`
- `GET /api/workflow/event-schema`

**Actual state (verified):** these endpoints are **not exposed** in routes yet.
- `src/api/routes/workflow_routes.py` currently serves only:
  - `/history`
  - `/stats`
  - `/{workflow_id}`

### Correction #2: Missing-count arithmetic mismatch
`PHASE_155_RECON_VERIFIED_2026-03-01.md` shows “API/UI/Converters = 11 missing”, while listed items are:
- API: 5
- UI: 2
- Converters: 4
- Spectral/Diagnostics: 2

Total listed missing scope = **13**, not 11.

### Correction #3: Marker verification line for tests
Line `tests/test_phase155_p0_drilldown_markers.py — EXISTS (20 tests)` is valid as existence info, but it is **not a marker assertion** and should not be counted as marker-verified row.

---

## 4) Final Missing Scope (Implementation Backlog)

## 4.1 API (not implemented)
1. `MARKER_155B.CANON.RUNTIME_GRAPH_API.V1`
2. `MARKER_155B.CANON.DESIGN_GRAPH_API.V1`
3. `MARKER_155B.CANON.PREDICT_GRAPH_API.V1`
4. `MARKER_155B.CANON.INPUT_MATRIX_ENRICH_API.V1`
5. `MARKER_155B.CANON.DRIFT_REPORT_API.V1`

## 4.2 UI mode/source visibility (not implemented)
1. `MARKER_155B.CANON.UI_SOURCE_MODE.V1`
2. `MARKER_155B.CANON.UI_SOURCE_BADGE.V1`

## 4.3 Converters (not implemented)
1. `MARKER_155B.CANON.XLSX_CONVERTER.V1`
2. `MARKER_155B.CANON.MD_CONVERTER.V1`
3. `MARKER_155B.CANON.XML_CONVERTER.V1`
4. `MARKER_155B.CANON.CONVERT_API.V1`

## 4.4 Spectral canon QA markers (not implemented)
1. `MARKER_155B.CANON.SPECTRAL_LAYOUT_QA.V1`
2. `MARKER_155B.CANON.SPECTRAL_ANOMALY.V1`

---

## 5) Execution Plan To Close Tails (Ready For Next Stage)

### Stage 155B-P0.1 (must-do first)
Expose schema service through API routes:
- add endpoints (or separate `workflow_canon_routes.py`) for:
  - `GET /api/workflow/schema/versions`
  - `POST /api/workflow/schema/migrate`
  - `GET /api/workflow/event-schema`

DoD:
- endpoints wired in router registry
- response includes canonical marker IDs
- route tests added and green

### Stage 155B-P1
Implement graph source APIs:
- runtime graph
- design graph
- predict graph
- drift report

DoD:
- each endpoint has marker + payload contract
- no placeholder/stub response in default path
- integration tests cover happy path + empty data path

### Stage 155B-P2
UI source mode + source badge in MCC:
- `workflow_source_mode = runtime|design|predict`
- visible source badge in `MyceliumCommandCenter`

DoD:
- mode switch persists in store
- mode reflected in requests and UI labels
- manual check in one-canvas flow passes

### Stage 155B-P3
Converters and convert/export API:
- XLSX/MD/XML converters
- unified convert endpoint

DoD:
- conversion roundtrip tests
- schema validation performed after import

### Stage 155B-P4
Spectral QA and anomaly diagnostics:
- implement spectral markers and diagnostics surface

DoD:
- metrics returned in API
- quality thresholds documented

---

## 6) Final Go/No-Go For Next Implementation Wave

**GO** with this baseline, under one condition:
- treat prior 2026-03-01 recon docs as historical context,
- use this file as the **single source of truth** for what is actually implemented vs pending.

---

## 7) Suggested Tracking Rule

For every new 155B deliverable:
- marker in code
- endpoint/UI anchor in code
- test for behavior (not only marker string)
- update this file’s section 4/5 status in the same PR

