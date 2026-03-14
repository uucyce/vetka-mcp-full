# PHASE 155 RECON — Canonization + MCC Drilldown Status
**Created:** 2026-03-01  
**Scope:** Marker audit summary for Phase 155 (MCC drilldown + DAG Canonization)

---

## ✅ СДЕЛАНО (DONE)

### MCC Drilldown — G26/G27/G28 Stabilization
| Marker | Status | Description |
|--------|--------|-------------|
| `MARKER_155A.G26.WF_CANONICAL_LAYOUT` | ✅ DONE | Канонический layout inline workflow |
| `MARKER_155A.G26.WF_CANONICAL_PACKING` | ✅ DONE | Анти-spaghetti фильтрация рёбер |
| `MARKER_155A.G26.WF_EDGE_PRUNE_CANONICAL` | ✅ DONE | Пакование без коллизий |
| `MARKER_155A.G26.WF_MINI_SCALE_MICRO` | ✅ DONE | Micro-scale rendering |
| `MARKER_155A.G26.WF_ANCHOR_ROOT_LOCK` | ✅ DONE | Root lock к выбранной task |
| `MARKER_155A.G26.NODE_DRILL_RICHER_PATH_FALLBACK` | ✅ DONE | Richer path fallback |
| `MARKER_155A.G27.RESERVED_WORKFLOW_FRAME` | ✅ DONE | Reserved frame для inline workflow |
| `MARKER_155A.G27.PIN_SANITIZE_INLINE` | ✅ DONE | Pin sanitization для временных узлов |
| `MARKER_155A.G27.NODE_DRILL_PRIORITY` | ✅ DONE | Node-drill priority fixed |
| `MARKER_155A.G27.MICRO_HANDLE_DOWNSCALE` | ✅ DONE | Уменьшенные handles |
| `MARKER_155A.G27.GLOBAL_HANDLE_FLOW` | ✅ DONE | Top-output / bottom-input geometry |
| `MARKER_155A.G27.WF_BOTTOM_UP_ORIENTATION` | ✅ DONE | Bottom-up orientation |
| `MARKER_155A.G28.WF_SOURCE_SCOPE_GUARD` | ✅ DONE | Workflow source guard |
| `MARKER_155A.G28.WF_TEMPLATE_DEDIRECT_ARCH_CODER` | ✅ DONE | Template dedirect arch |

**Commits:** 10 key commits (4e2aa6d6 → 206e20c7)  
**Tests:** `tests/test_phase155_p0_drilldown_markers.py` — 20 passed

### Input Matrix / SCC Backend Foundation
| Marker | Status | Description |
|--------|--------|-------------|
| `MARKER_155.MODE_ARCH.V11.P1` | ✅ DONE | Mode architecture V11 |
| `MARKER_155.INPUT_MATRIX.SCANNERS.V1` | ✅ DONE | Input matrix scanners |
| `MARKER_155.INPUT_MATRIX.ROOT_SCORE.V1` | ✅ DONE | Root score calculation |
| `MARKER_155.INPUT_MATRIX.BACKBONE_DAG.V1` | ✅ DONE | Backbone DAG |
| `MARKER_155.INPUT_MATRIX.ARCH_DIRECTION_INVERT.V1` | ✅ DONE | Direction inversion |
| `MARKER_155.INPUT_MATRIX.FOLDER_OVERVIEW.V1` | ✅ DONE | Folder overview |
| `MARKER_155.MEMORY.ENGRAM_DAG_PREFS.V1` | ✅ DONE | Engram DAG preferences |

**Code anchor:** `src/services/mcc_scc_graph.py`

### Canonization P0 — Schema Lock
| Marker | Status | Description |
|--------|--------|-------------|
| `MARKER_155B.CANON.SCHEMA_LOCK.V1` | ✅ DONE | Canonical schema locked |
| `MARKER_155B.CANON.SCHEMA_VERSIONING.V1` | ✅ DONE | Semver policy + migration |
| `MARKER_155B.CANON.EVENT_SCHEMA.V1` | ✅ DONE | Event schema defined |

**Code anchor:** `src/services/workflow_canonical_schema.py` (NEW)

### Deprecated Surfaces Policy
| Marker | Status | Description |
|--------|--------|-------------|
| `MARKER_155A.G25.DEPRECATED_SURFACE_LOCK` | ✅ DONE | Lock policy active |
| `MARKER_155A.G25.DEPRECATED_UI_RUNTIME_GUARD` | ✅ DONE | Runtime guard |
| `MARKER_155A.G25.MINITASKS_EXPANDED_V2` | ✅ DONE | MiniTasks V2 |

**Files locked:** MCCTaskList.tsx, MCCDetailPanel.tsx, WorkflowToolbar.tsx, RailsActionBar.tsx, TaskDAGView.tsx

---

## ⏳ В ПРОЦЕССЕ (IN PROGRESS)

| Area | Marker | Status | Description |
|------|--------|--------|-------------|
| P0 API endpoints | `MARKER_155B.CANON.*_API.V1` | 🔄 PENDING | Требуется интеграция в workflow_routes.py |

---

## ❌ НЕ СДЕЛАНО (TODO)

### Canonization — P1-P5 Roadmap

| Priority | Marker Area | Status | Description |
|----------|------------|--------|-------------|
| P1 | `RUNTIME_GRAPH_API.V1` | ❌ TODO | Endpoint `/api/workflow/runtime-graph/{task_id}` |
| P1 | `EVENT_SCHEMA` integration | ❌ TODO | Event -> graph builder из pipeline events |
| P1 | Conditional edges | ❌ TODO | `on_fail`, `on_pass`, `on_major_fail` в runtime |
| P2 | `UI_SOURCE_MODE.V1` | ❌ TODO | `workflow_source_mode = runtime\|design\|predict` в MCC |
| P2 | `UI_SOURCE_BADGE.V1` | ❌ TODO | Source badge в UI |
| P2 | `SPECTRAL_LAYOUT_QA.V1` | ❌ TODO | Discrepancy-based balanced layering |
| P3 | `XLSX_CONVERTER.V1` | ❌ TODO | XLSX importer/exporter |
| P3 | `MD_CONVERTER.V1` | ❌ TODO | Markdown importer/exporter |
| P3 | `XML_CONVERTER.V1` | ❌ TODO | XML importer/exporter |
| P4 | `INPUT_MATRIX_ENRICH_API.V1` | ❌ TODO | Channel scorers endpoint |
| P4 | UI filters | ❌ TODO | Filters by channel + threshold |
| P5 | `PREDICT_GRAPH_API.V1` | ❌ TODO | JEPA overlay (dashed) |
| P5 | `DRIFT_REPORT_API.V1` | ❌ TODO | G_design vs G_runtime drift |
| P5 | `SPECTRAL_ANOMALY.V1` | ❌ TODO | Laplacian eigengap diagnostics |

### Endpoint Checklist (из roadmap V1.1)
```
DONE:
  ✅ GET /api/workflow/schema/versions
  ✅ POST /api/workflow/schema/migrate
  ✅ GET /api/workflow/event-schema

TODO:
  ⬜ GET /api/workflow/runtime-graph/{task_id}
  ⬜ GET /api/workflow/design-graph/{workflow_id}
  ⬜ GET /api/workflow/predict-graph/{task_id}
  ⬜ POST /api/workflow/convert
  ⬜ POST /api/workflow/export/{format}
  ⬜ POST /api/workflow/enrich/input-matrix/{graph_id}
  ⬜ GET /api/workflow/drift-report/{task_id}
```

### Post-V1 Dependencies (вне V1.1 scope)
- Approval flow / audit trail для G_design
- Engram memory integration
- Scale strategy для >10K nodes
- Performance benchmarks / SLOs

---

## 📊 Summary

| Category | Done | In Progress | Todo |
|----------|------|-------------|------|
| MCC Drilldown (G26/G27/G28) | 14 markers | 0 | 0 |
| Input Matrix / SCC | 7 markers | 0 | 0 |
| Canonization P0 (Schema) | 3 markers | 0 | 0 |
| Canonization P1-P5 | 0 markers | 1 | 14 markers |
| **Total Phase 155** | **24 markers** | **1** | **14 markers** |

---

## 🎯 Next Step Recommendation

**Immediate:** P0 API endpoints integration — подключить маркеры 155B.CANON.* к workflow_routes.py

**Then:** P1 Runtime Builder — event → graph builder pipeline
