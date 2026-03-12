# PHASE 165 — MCC Context Search Recon + Markers (2026-03-07)

Protocol: `RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY TEST -> find better idea/or bag -> check guides -> RECON+markers -> REPORT+markers -> WAIT GO`
Status: `RECON DONE / WAIT GO`

## 1) Goal
Embed search directly into MCC `Context` window:
- input lives inside Context panel,
- results render in same panel,
- selecting result highlights/focuses matching DAG node.

Constraint:
- reuse VETKA search methods, but do not blindly copy;
- keep strict monochrome MCC style;
- preserve project isolation (`sandbox-first`, no cross-project leakage).

## 2) Code Recon (fact-based)

### 2.1 Context window insertion point
- Context panel implementation:
  - `client/src/components/mcc/MiniContext.tsx`
- Current state:
  - no search input and no callback to select node from inside Context.
  - compact/expanded view already structured and extensible.

### 2.2 Node focus/highlight mechanism already exists
- Node selection pipeline:
  - `handleLevelAwareNodeSelect(...)` in `client/src/components/mcc/MyceliumCommandCenter.tsx`
- DAG highlighting depends on selected ids:
  - `selectedNodeIds` and edge highlight logic in `client/src/components/mcc/DAGView.tsx`
- Good news:
  - we already have robust path normalization and node-path lookup primitives (`normalizePathKey`, task anchor resolving logic) that can be reused for search hit -> node id mapping.

### 2.3 VETKA search methods available for reuse
- Unified routes:
  - `src/api/routes/unified_search_routes.py`
  - `/api/search/unified`
  - `/api/search/file`
- Unified handler:
  - `src/api/handlers/unified_search.py`
- File search engine:
  - `src/search/file_search_service.py`
- Hybrid engine:
  - `src/search/hybrid_search.py`

## 3) Critical Gaps / Bugs (for MCC isolated mode)

1. Scope leak risk (major):
- Current file search roots in `file_search_service` can include `home/cwd/parent` and Spotlight fallback (macOS), i.e. broader than active MCC project.
- `unified_search` also uses broad defaults and `Path.cwd()` fallback.
- This conflicts with MCC multi-project isolation intent.

2. Missing scoped API contract:
- `/api/search/file` and `/api/search/unified` do not carry strict `scope_root` for MCC use path.

3. Context panel lacks search-to-focus bridge:
- `MiniContext` cannot request node selection in graph yet.

4. Potential UX noise risk:
- if we dump full global search UI into Context, it will overload panel.

## 4) Proposed Safe Architecture (narrow)

### 4.1 Search strategy (better idea)
Use 2-tier search in Context:
- Tier A (instant, local): graph-local search over currently rendered DAG nodes (label/path/id/metadata).
- Tier B (optional fallback): backend scoped file search in active project sandbox only.

Why:
- fast and deterministic highlighting,
- no leakage across projects,
- keeps UX lightweight in Context panel,
- still reuses VETKA file search methods as fallback engine.

### 4.2 Backend hardening before UI binding
Add scoped file search contract:
- new MCC-specific route (recommended):
  - `POST /api/mcc/search/file`
- request fields:
  - `query`, `limit`, `mode`, `scope_path?`
- effective scope resolution:
  - default = active project `sandbox_path` (fallback to `source_path` only if sandbox unavailable)
- filter result paths to be within effective scope.

### 4.3 UI integration
- Add compact search row to `MiniContext` expanded view.
- Render top N results with source badges (`local` / `scoped-file`).
- On result click:
  - call new prop from `MiniContext` -> `MyceliumCommandCenter`
  - invoke existing `handleLevelAwareNodeSelect(nodeId)`.

## 5) Marker Plan

### Backend markers
- `MARKER_165.MCC.CONTEXT_SEARCH.API_SCOPED_FILE_ROUTE.V1`
- `MARKER_165.MCC.CONTEXT_SEARCH.SCOPE_GUARD.V1`
- `MARKER_165.MCC.CONTEXT_SEARCH.PATH_FILTER.V1`

### Frontend markers
- `MARKER_165.MCC.CONTEXT_SEARCH.UI_INPUT.V1`
- `MARKER_165.MCC.CONTEXT_SEARCH.UI_RESULTS.V1`
- `MARKER_165.MCC.CONTEXT_SEARCH.NODE_FOCUS_BRIDGE.V1`

### Tests markers
- `MARKER_165.MCC.CONTEXT_SEARCH.TEST_API_SCOPE.V1`
- `MARKER_165.MCC.CONTEXT_SEARCH.TEST_UI_CONTRACT.V1`
- `MARKER_165.MCC.CONTEXT_SEARCH.TEST_NODE_HIGHLIGHT_BRIDGE.V1`

## 6) Test Plan (before/after)

1. API scope tests:
- route rejects invalid scope,
- default uses active sandbox,
- returned paths never escape scope root.

2. UI contract tests:
- `MiniContext` contains search input + results section markers,
- no color/icon deviation from MCC palette constraints.

3. Bridge tests:
- result click triggers node-focus callback,
- callback uses existing select/highlight path (no new highlight mechanism).

4. Regression tests:
- existing `tests/mcc` full subset remains green.

## 7) Implementation Slices (narrow)

- P165.A: backend scoped route + tests.
- P165.B: Context input/results shell + tests.
- P165.C: focus bridge wiring + tests.
- P165.D: optional fallback quality tuning + audit.

## 8) GO Decision Request
Ready for `IMPL NARROW` with P165.A first.
