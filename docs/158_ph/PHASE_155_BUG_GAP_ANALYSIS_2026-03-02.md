# PHASE 155 — Bug/Gap Analysis + Grandma Mode Research
**Created:** 2026-03-02

---

## 1. Phase 155 Documents Analysis

### 1.1 PHASE_155_RECON_FINAL_2026-03-02.md — Status

| Section | Status | Issues |
|---------|--------|--------|
| MCC G26/G27/G28 | ✅ DONE | Verified in code |
| Input Matrix/SCC | ✅ DONE | Verified in code |
| Engram Memory | ✅ DONE | Verified |
| Canonization P0 (Schema) | ✅ DONE | Service exists |
| 155B-P0.1 Schema API | ✅ DONE | Endpoints verified |
| 155B-P1 Graph APIs | ✅ DONE | Runtime/design/predict/drift |
| 155B-P2 UI Mode | ✅ DONE | Source badge + mode |
| 155B-P3 Converters | ✅ DONE | XLSX/MD/XML |
| 155B-P4 Spectral | ✅ DONE | QA + anomaly |
| 155C JEPA | ✅ DONE | Bootstrap + fallback |
| Input Matrix Enrich API | ✅ DONE | Implemented |

**Critical Finding:** This doc claims ALL items are DONE. Need verification.

---

## 1.2 Verification — What Actually Exists in Codebase

### API Endpoints Check
| Claimed Endpoint | File | Verified |
|-----------------|------|----------|
| `/api/workflow/schema/versions` | workflow_routes.py:783 | ✅ EXISTS |
| `/api/workflow/schema/migrate` | workflow_routes.py:794 | ✅ EXISTS |
| `/api/workflow/event-schema` | workflow_routes.py:822 | ✅ EXISTS |
| `/api/workflow/runtime-graph/{task_id}` | workflow_routes.py:833 | ✅ EXISTS |
| `/api/workflow/design-graph/{task_id}` | workflow_routes.py:871 | ✅ EXISTS |
| `/api/workflow/predict-graph/{task_id}` | workflow_routes.py:909 | ✅ EXISTS |
| `/api/workflow/drift-report/{task_id}` | workflow_routes.py:978 | ✅ EXISTS |
| `/api/workflow/spectral-layout-qa/{task_id}` | workflow_routes.py:1013 | ✅ EXISTS |
| `/api/workflow/spectral-anomaly/{task_id}` | workflow_routes.py:1052 | ✅ EXISTS |
| `/api/workflow/convert` | workflow_routes.py:1091 | ✅ EXISTS |
| `/api/workflow/enrich/input-matrix/{graph_id}` | workflow_routes.py:585 | ✅ EXISTS |

**All claimed endpoints verified in code.**

### Test Files Check
| Claimed Test | Status |
|--------------|--------|
| test_phase155_p0_drilldown_markers.py | ✅ EXISTS (20 tests) |
| test_phase155b_p0_1_schema_routes.py | ❓ Need verify |
| test_phase155b_p1_graph_source_routes.py | ❓ Need verify |
| test_phase155b_p2_ui_source_mode_markers.py | ❓ Need verify |
| test_phase155b_p3_convert_api.py | ❓ Need verify |
| test_phase155b_p4_spectral_routes.py | ❓ Need verify |

---

## 2. Logical Gaps + Bugs Identified

### Gap #1: Mini-Windows — Node Context Window NOT Implemented
| Item | Status |
|------|--------|
| `MARKER_155A.P3.NODE_CONTEXT_WINDOW` | ❌ NOT DONE |
| Goal | Clicking node opens one context mini-window |
| Current State | No node-specific mini-window on click |
| Risk | Duplicate panels, conflicting interactions |

**Evidence:**
- `MiniWindow.tsx` exists (MiniTasks, MiniStats, MiniChat, MiniBalance)
- No node-context mini-window in MyceliumCommandCenter.tsx at lines 548-559

### Gap #2: Model Edit Bind NOT Implemented
| Item | Status |
|------|--------|
| `MARKER_155A.P3.MODEL_EDIT_BIND` | ❌ NOT DONE |
| Goal | Model can be viewed/changed from selected node context |
| Current State | MCCDetailPanel is deprecated, no replacement |

### Gap #3: Stats Context NOT Fully Contextual
| Item | Status |
|------|--------|
| `MARKER_155A.P3.STATS_CONTEXT` | ⚠️ PARTIAL |
| Goal | Selected node changes stats scope instantly |
| Current State | MiniStats exists but may not respond to node selection |

### Gap #4: Stream Context NOT Implemented
| Item | Status |
|------|--------|
| `MARKER_155A.P3.STREAM_CONTEXT` | ❌ NOT DONE |
| Goal | Focused task shows filtered live events |
| Current State | Stream shows all events, not filtered by context |

### Gap #5: Primary Actions Still Exceed 3
| Item | Status |
|------|--------|
| Goal | Primary button count remains <=3 in all states |
| Current State | Unknown - needs verification in FooterActionBar |

---

## 3. Grandma Mode — Mini-Windows Research

### Philosophy: "Even grandma can use it" — max 3 actions, one view, progressive disclosure

### Current Implementation (154/155 Phases)
| Mini-Window | Component | Status |
|-------------|-----------|--------|
| Tasks | MiniTasks.tsx | ✅ DONE |
| Stats | MiniStats.tsx | ✅ DONE |
| Chat | MiniChat.tsx | ✅ DONE |
| Balance | MiniBalance.tsx | ✅ DONE |

### NOT Implemented (Grandma Mode Gaps)
| Feature | Phase | Status | Research Document |
|---------|-------|--------|-------------------|
| Node Context Mini-Window | P3 | ❌ NOT DONE | CODEX_UNIFIED_DAG_RECON_MAP.md:39 |
| Model Edit Bind | P3 | ❌ NOT DONE | CODEX_UNIFIED_DAG_RECON_MAP.md:40 |
| Stats Context (node-aware) | P3 | ⚠️ PARTIAL | CODEX_UNIFIED_DAG_RECON_MAP.md:41 |
| Stream Context (filtered) | P3 | ❌ NOT DONE | CODEX_UNIFIED_DAG_RECON_MAP.md:42 |
| Conflict Policy (gear only) | P4 | ❌ NOT DONE | CODEX_UNIFIED_DAG_RECON_MAP.md:44 |

### Key Research Documents for Continuation
| Document | Relevance |
|----------|-----------|
| `docs/154_ph/MARKER_155_MCC_ARCHITECTURE_REDUX.md` | Core grandma philosophy (line 18) |
| `docs/155_ph/CODEX_UNIFIED_DAG_RECON_MAP.md` | P3 marker map with gaps |
| `docs/155_ph/CODEX_UNIFIED_DAG_MASTER_PLAN.md` | Master plan |
| `docs/155_ph/MCC_DRILLDOWN_ARCHITECTURE_PLAN_2026-02-26.md` | Mini-window specs |
| `docs/154_ph/PHASE_154_ROADMAP.md` | Wave 1-4 mini-windows |

### From MARKER_155_MCC_ARCHITECTURE_REDUX.md (Line 18)
> **Philosophy:** "Even grandma can use it" — max 3 actions, one view, progressive disclosure

### From PHASE_154_ROADMAP.md (Line 78)
> **Goal:** 3 floating mini-windows — compact in corners, expandable to overlay.

---

## 4. Summary of What Works vs What's Broken

### ✅ Working (Verified)
1. Single-canvas DAG (no window switching)
2. Mini-windows framework (draggable, floating)
3. Workflow source mode (runtime/design/predict)
4. Schema APIs + Graph APIs
5. Converters (XLSX/MD/XML)
6. Spectral QA
7. Input Matrix Enrich

### ❌ Not Working / Incomplete
1. Node click → mini-window (P)
2. Model3 gap edit from node context (P3 gap)
3. Stats respond to selected node (P3 gap)
4. Stream filtered by context (P3 gap)
5. Conflict actions in gear only (P4 gap)

---

## 5. Recommended Next Steps for MCC

### Priority 1: Close P3 Gaps
1. Implement `MARKER_155A.P3.NODE_CONTEXT_WINDOW` 
   - Click node → open context mini-window with node details
   
2. Implement `MARKER_155A.P3.STATS_CONTEXT`
   - MiniStats should update when node selected
   
3. Implement `MARKER_155A.P3.STREAM_CONTEXT`
   - Filter live events by focused task/agent

### Priority 2: Close P4 Gaps
1. Implement `MARKER_155A.P4.CONFLICT_POLICY`
   - Conflict actions only in gear/secondary

### Priority 3: Grandma Mode Polish
1. Ensure max 3 primary actions always
2. Progressive disclosure for complexity

---

## 6. Related Documents
- `docs/155_ph/PHASE_155_RECON_FINAL_2026-03-02.md` — Main reference
- `docs/155_ph/CODEX_UNIFIED_DAG_RECON_MAP.md` — Marker map with gaps
- `docs/154_ph/MARKER_155_MCC_ARCHITECTURE_REDUX.md` — Philosophy
- `docs/154_ph/PHASE_154_ROADMAP.md` — Mini-windows roadmap
