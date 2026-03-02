# PHASE 155 RECON — VERIFIED VS CODEBASE (2026-03-01)

**Scope:** Marker audit verification against actual codebase  
**Status:** Verified

---

## ✅ VERIFIED DONE — Found in Code

### MCC Drilldown G26 (6 markers)
- `MARKER_155A.G26.WF_CANONICAL_LAYOUT` — DAGView.tsx:60 ✅
- `MARKER_155A.G26.WF_CANONICAL_PACKING` — DAGView.tsx:153 ✅
- `MARKER_155A.G26.WF_EDGE_PRUNE_CANONICAL` — DAGView.tsx ✅
- `MARKER_155A.G26.WF_MINI_SCALE_MICRO` — MyceliumCommandCenter.tsx:689 ✅
- `MARKER_155A.G26.WF_ANCHOR_ROOT_LOCK` — DAGView.tsx:541 ✅
- `MARKER_155A.G26.NODE_DRILL_RICHER_PATH_FALLBACK` — MyceliumCommandCenter.tsx:857 ✅

### MCC Drilldown G27 (6 markers)
- `MARKER_155A.G27.RESERVED_WORKFLOW_FRAME` — DAGView.tsx:529 ✅
- `MARKER_155A.G27.PIN_SANITIZE_INLINE` — DAGView.tsx:325 ✅
- `MARKER_155A.G27.NODE_DRILL_PRIORITY` — MyceliumCommandCenter.tsx:2538 ✅
- `MARKER_155A.G27.MICRO_HANDLE_DOWNSCALE` — DAGView.tsx:1212 ✅
- `MARKER_155A.G27.GLOBAL_HANDLE_FLOW` — DAGView.tsx:735 ✅
- `MARKER_155A.G27.WF_BOTTOM_UP_ORIENTATION` — DAGView.tsx:186 ✅

### MCC Drilldown G28 (2 markers)
- `MARKER_155A.G28.WF_SOURCE_SCOPE_GUARD` — MyceliumCommandCenter.tsx:1127 ✅
- `MARKER_155A.G28.WF_TEMPLATE_DEDIRECT_ARCH_CODER` — MyceliumCommandCenter.tsx:1097 ✅

### MCC G25 Deprecated + Thresholds (7 markers)
- `MARKER_155A.G25.DEPRECATED_SURFACE_LOCK` — TaskDAGView.tsx, MCCTaskList.tsx ✅
- `MARKER_155A.G25.DEPRECATED_UI_RUNTIME_GUARD` — MyceliumCommandCenter.tsx:15 ✅
- `MARKER_155A.G25.MINITASKS_EXPANDED_V2` — MiniTasks.tsx:126 ✅
- `MARKER_155A.G25.NODE_DRILL_THRESHOLDS` — MyceliumCommandCenter.tsx:816 ✅
- `MARKER_155A.G25.NODE_DRILL_OVERFLOW_BADGE` — MyceliumCommandCenter.tsx:958 ✅
- `MARKER_155A.G25.LAZY_UNFOLD_STATE_CLEANUP` — MyceliumCommandCenter.tsx:2117 ✅
- `MARKER_155A.G25.INCREMENTAL_STRESS_TUNE` — DAGView.tsx:365 ✅

### Input Matrix / SCC (8 markers)
- `MARKER_155.INPUT_MATRIX.SCANNERS.V1` — mcc_scc_graph.py:1394 ✅
- `MARKER_155.INPUT_MATRIX.ROOT_SCORE.V1` — mcc_scc_graph.py:728 ✅
- `MARKER_155.INPUT_MATRIX.BACKBONE_DAG.V1` — mcc_scc_graph.py:891 ✅
- `MARKER_155.INPUT_MATRIX.ARCH_DIRECTION_INVERT.V1` — mcc_scc_graph.py:1286 ✅
- `MARKER_155.INPUT_MATRIX.FOLDER_OVERVIEW.V1` — mcc_scc_graph.py:1326 ✅
- `MARKER_155.INPUT_MATRIX.ROOT_COALESCE.V1` — mcc_scc_graph.py:837 ✅
- `MARKER_155.INPUT_MATRIX.LAYER_FROM_FULL_DAG.V1` — mcc_scc_graph.py:1302 ✅
- `MARKER_155.INPUT_MATRIX.OVERVIEW_EDGE_BUDGET.V1` — mcc_scc_graph.py:1323 ✅

### Engram Memory (1 marker)
- `MARKER_155.MEMORY.ENGRAM_DAG_PREFS.V1` — mcc_routes.py:936, user_memory.py:43 ✅

### Canonization P0 (3 markers)
- `MARKER_155B.CANON.SCHEMA_LOCK.V1` — workflow_canonical_schema.py:2 ✅
- `MARKER_155B.CANON.SCHEMA_VERSIONING.V1` — workflow_canonical_schema.py:3 ✅
- `MARKER_155B.CANON.EVENT_SCHEMA.V1` — workflow_canonical_schema.py:4 ✅

### Tests
- `tests/test_phase155_p0_drilldown_markers.py` — EXISTS (20 tests) ✅

---

## ❌ NOT FOUND — Requires Implementation

### API Endpoints (5)
- `MARKER_155B.CANON.RUNTIME_GRAPH_API.V1` — workflow_routes.py ❌
- `MARKER_155B.CANON.DESIGN_GRAPH_API.V1` — workflow_routes.py ❌
- `MARKER_155B.CANON.PREDICT_GRAPH_API.V1` — workflow_routes.py ❌
- `MARKER_155B.CANON.INPUT_MATRIX_ENRICH_API.V1` — workflow_routes.py ❌
- `MARKER_155B.CANON.DRIFT_REPORT_API.V1` — mcc_dag_compare.py ❌

### UI Components (2)
- `MARKER_155B.CANON.UI_SOURCE_MODE.V1` — useMCCStore.ts ❌
- `MARKER_155B.CANON.UI_SOURCE_BADGE.V1` — MyceliumCommandCenter.tsx ❌

### Converters (4)
- `MARKER_155B.CANON.XLSX_CONVERTER.V1` ❌
- `MARKER_155B.CANON.MD_CONVERTER.V1` ❌
- `MARKER_155B.CANON.XML_CONVERTER.V1` ❌
- `MARKER_155B.CANON.CONVERT_API.V1` ❌

### Spectral / Diagnostics (2)
- `MARKER_155B.CANON.SPECTRAL_LAYOUT_QA.V1` ❌
- `MARKER_155B.CANON.SPECTRAL_ANOMALY.V1` ❌

---

## 📊 Summary
| Category | Verified | Missing |
|----------|----------|---------|
| MCC/G25 | 21 | 0 |
| Input Matrix | 8 | 0 |
| Canonization P0 | 3 | 0 |
| API/UI/Converters | 0 | 11 |
| **Total** | **32** | **11** |

---

## 🎯 Verified Next Steps

1. **Immediate:** Add API endpoints in `workflow_routes.py` with markers:
   - `MARKER_155B.CANON.RUNTIME_GRAPH_API.V1`
   - `MARKER_155B.CANON.DESIGN_GRAPH_API.V1`
   - `MARKER_155B.CANON.PREDICT_GRAPH_API.V1`

2. **Then:** Add UI source mode switch:
   - `MARKER_155B.CANON.UI_SOURCE_MODE.V1` in useMCCStore.ts
   - `MARKER_155B.CANON.UI_SOURCE_BADGE.V1` in MyceliumCommandCenter.tsx

3. **Then:** Converters (P3)
