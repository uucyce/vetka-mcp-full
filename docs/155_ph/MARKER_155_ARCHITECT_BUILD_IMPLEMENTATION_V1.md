# MARKER_155 Architect Build Implementation V1

Date: 2026-02-23
Status: Implemented (narrow wave)

Markers:
- `MARKER_155.ARCHITECT_BUILD.CONTRACT.V1`
- `MARKER_155.ARCHITECT_BUILD.VERIFIER.V1`
- `MARKER_155.ARCHITECT_BUILD.JEPA_OVERLAY.V1`

## What was implemented
1. Contract document:
- `docs/155_ph/ARCHITECT_BUILD_CONTRACT_V1.md`

2. Builder service:
- `src/services/mcc_architect_builder.py`
- Builds:
  - `runtime_graph` (from condensed SCC pipeline)
  - `design_graph` (overview-first planning graph)
  - `predictive_overlay` (optional)
  - `verifier` report

3. API endpoint:
- `POST /api/mcc/graph/build-design`
- File: `src/api/routes/mcc_routes.py`

4. Tests:
- `tests/test_mcc_architect_builder.py`

## Verifier/Eval tools now included in response
- `acyclic`
- `monotonic_layers`
- `orphan_rate`
- `density`
- `avg_out_degree`
- `spectral.lambda2`
- `spectral.eigengap`
- `spectral.component_count`
- `spectral.status`
- `decision` (`pass|warn|fail`)

## Regression/validation run
1. Unit tests:
- Command: `pytest -q tests/test_mcc_architect_builder.py`
- Result: `2 passed`

2. Service smoke run on current repo:
- Command: `python -c "from src.services.mcc_architect_builder import build_design_dag; r=build_design_dag('.', max_nodes=220, use_predictive_overlay=False); print(r['verifier']['decision'], len(r['design_graph']['nodes']), len(r['design_graph']['edges']))"`
- Result: `fail 33 8` (expected possible outcome; indicates graph-quality gate working, not silent success)

## Notes for next wave
- Hook frontend MCC action to call `/api/mcc/graph/build-design` with architect problem/goal context.
- Move threshold values into explicit config for B2 freeze.
- Add visual verifier panel (decision + spectral metrics) near DAG controls.

## Wave 2 update (2026-02-23)

### MARKER_155.ARCHITECT_BUILD.DESIGN_AGGREGATION.V2
Implemented design-graph rebuild from L0 directory aggregation (instead of near-pass-through from l2_overview):
- project root + directory hierarchy nodes,
- tree connectivity edges for architectural readability,
- adaptive aggregated dependency edges,
- monotonic layer orientation in design view.

### Validation (wave 2)
- `pytest -q tests/test_mcc_architect_builder.py` -> `2 passed`
- `pytest -q tests/test_phase153_wave5.py` -> `45 passed`
- smoke:
  - `decision= pass`
  - `nodes=122 edges=233`
  - `source=l0_directory_aggregated`
  - `spectral.status=ok`, `component_count=1`

## Wave 3 update (2026-02-23)

### MARKER_155.ARCHITECT_BUILD.SPECTRAL_OBJECTIVE.V3
Implemented spectral objective in architecture layout (not only verifier):
- file: `client/src/utils/dagLayout.ts`
- laplacian smoothing pass on X coordinates for architecture mode,
- bucket-aware placement from backend metadata (`rank_bucket`),
- reduced horizontal rail effect via layer-local spectral ordering + equitable bucket spread.

### MARKER_155.ARCHITECT_BUILD.TAO_CLUSTERING.V3
Implemented Tao-style preprocessing in design graph builder:
- file: `src/services/mcc_architect_builder.py`
- vectorization of directory candidates (embedding service first, deterministic fallback),
- whitening pass before clustering (`tao_whitening`),
- HDBSCAN preference with DBSCAN/quantile fallback,
- discrepancy/equitable bucket assignment per layer (`rank_bucket`, `bucket_count` in metadata).

### MARKER_155.ARCHITECT_BUILD.JEPA_VECTOR_PREDICTOR.V3
Upgraded predictive overlay to vector-aware branch scoring:
- file: `src/services/mcc_predictive_overlay.py`
- combined score channels:
  - layer progression,
  - path token overlap,
  - embedding cosine similarity,
  - parent affinity,
  - SCC penalty.
- API contract unchanged; payload now includes `stats.vector_model`.

### Validation (wave 3)
- `pytest -q tests/test_mcc_architect_builder.py` -> `2 passed`
- `python -m py_compile src/services/mcc_architect_builder.py src/services/mcc_predictive_overlay.py` -> OK
- smoke:
  - `decision=pass`
  - design pipeline reports: whitening + clustering + equitable coloring
  - overlay reports vector channel model in `stats.vector_model`

### Remaining for next wave
- `P1` Topology default + dependency edges only on focus set (selection-driven overlay),
- `P2` Pin layout persistence on soft refresh (no auto-reset after user drag),
- `P2.1` Layout preference learning from repeated pin/drag actions (bias profile, trigger-only loop),
- `P2.2` ENGRAM shared preference bridge for MCC+VETKA (`dag_layout_profiles`, scope-bounded),
- `P3` Attach true JEPA/V-JEPA inference backend (model runtime) as predictor source instead of embedding-service channel,
- `P4` Focus persistence across zoom + shift multi-select -> architect task payload,
- `P5` optional diagnostics panel in MCC (`bucket load`, `crossing estimate`) for architect/debug.

## P2.2 implementation update (2026-02-23)

### MARKER_155.MEMORY.ENGRAM_DAG_PREFS.V1
Implemented shared DAG preference bridge (read/write) with ENGRAM as canonical intent store:
- backend:
  - `GET /api/mcc/layout/preferences`
  - `POST /api/mcc/layout/preferences`
  - file: `src/api/routes/mcc_routes.py`
- memory schema:
  - `viewport_patterns.dag_layout_profiles`
  - file: `src/memory/user_memory.py`
- frontend wiring:
  - MCC reads profile by scope and posts trigger-based pin/drag inferred bias
  - VETKA reads same profile family and applies as soft-prior in tree auto-layout
  - files:
    - `client/src/utils/dagLayoutPreferences.ts`
    - `client/src/components/mcc/MyceliumCommandCenter.tsx`
    - `client/src/components/mcc/DAGView.tsx`
    - `client/src/utils/dagLayout.ts`
    - `client/src/utils/layout.ts`
    - `client/src/hooks/useTreeData.ts`
    - `client/src/store/useStore.ts`

Contract respected:
- no raw coordinates in ENGRAM,
- explicit pins remain top-priority,
- trigger-driven updates only (no periodic retraining loop).

## P2.1 implementation note (2026-02-23)

### MARKER_155A.P2_1.LAYOUT_PREFERENCE_LEARNING
Planned narrow implementation:
- collect drag/pin deltas in architecture mode,
- aggregate into scope-bounded bias profile (`vertical`, `sibling spacing`, `compactness`),
- apply profile as soft objective in layout composer,
- keep explicit pin as highest-priority override.

### Trigger policy
- update profile on pin/drag commit events only,
- no interval retraining,
- no background periodic recompute.

### Verifier extension target
- add readability deltas pre/post profile (`crossing_estimate`, `layer_spread`, `branch_cohesion`),
- block profile promotion on verifier fail.

### Operational issue to verify
- Mycelium shutdown reliability: observed cases where process ignored normal `SIGINT` and kept websocket loop active (looked like daemonized worker remains alive).
- Action: add explicit shutdown audit (`all child workers stopped`, websocket loop closed, no orphan PID) and a deterministic fallback stop path.

## P3/P4 implementation update (2026-02-23)

### MARKER_155.P3.JEPA_RUNTIME_FOCUS_OVERLAY.V1
Implemented runtime predictive overlay with explicit focus context:
- endpoint request extended:
  - `POST /api/mcc/graph/predict` now accepts `focus_node_ids: string[]`
  - file: `src/api/routes/mcc_routes.py`
- predictor updated:
  - focus-aware scoring (`focus_bonus`) and local overlay restriction in focus mode
  - overlay cache key includes focus set
  - file: `src/services/mcc_predictive_overlay.py`
- MCC runtime bind:
  - predictive fetch uses single or multi focus ids
  - edge budget adapts by current LOD (`architecture/tasks/workflow`)
  - file: `client/src/components/mcc/MyceliumCommandCenter.tsx`

### MARKER_155.P4.FOCUS_ACROSS_ZOOM_MULTISELECT.V1
Implemented shift multi-select + focus persistence across zoom/drill:
- DAG view API:
  - `selectedNodeIds` + `onNodeSelectWithMode(additive)` support
  - shift-click in canvas toggles nodes into focus set
  - file: `client/src/components/mcc/DAGView.tsx`
- focus rendering:
  - highlight engine now supports focus-set (not single node only)
  - roadmap overlay filtering uses focused set for dependency/predicted edges
  - files:
    - `client/src/components/mcc/DAGView.tsx`
    - `client/src/components/mcc/MyceliumCommandCenter.tsx`
- cross-zoom behavior:
  - focus set is preserved; stale ids pruned only when node set changes
  - file: `client/src/components/mcc/MyceliumCommandCenter.tsx`
- multi-select action:
  - `Shift+Enter` sends focused node context to Architect chat prefill
  - files:
    - `client/src/components/mcc/MyceliumCommandCenter.tsx`
    - `client/src/components/mcc/MiniChat.tsx`

### Remaining after this wave
- replace heuristic/vector predictor channel with real JEPA/V-JEPA model runtime adapter,
- add accept/reject feedback loop for predicted edges (online ranking refinement),
- expose selected focus-set action in explicit footer button (in addition to `Shift+Enter`).

### Smoke report reference
- `docs/155_ph/P3_P4_SMOKE_REPORT_2026-02-23.md`
  - P3 service/API path: `GO`
  - P4 wiring path: `GO`
  - P4 manual runtime confirmation: `PENDING`

### MARKER_155.P3_4.STATS_DIAGNOSTICS_WORKSPACE.V1

Status: `DONE (UI wiring)`

What changed:
- Unified Stats tab into one workspace with internal modes:
  - `Ops` (user-facing metrics),
  - `Diagnostics` (graph verifier/spectral, JEPA runtime health, trigger log).
- Kept main MCC user surface clean (no extra primary buttons).
- Added compact diagnostics summary in `MiniStats`:
  - graph decision + runtime up/down + shortcut to diagnostics mode.

Files:
- `client/src/components/panels/StatsWorkspace.tsx`
- `client/src/hooks/useMCCDiagnostics.ts`
- `client/src/components/panels/DevPanel.tsx`
- `client/src/components/mcc/MiniStats.tsx`
- `client/src/store/useDevPanelStore.ts`

## P3.1 implementation update (2026-02-23)

### MARKER_155.P3_1.JEPA_ADAPTER.V1
Implemented JEPA runtime adapter landing layer with provider switch + safe fallback chain:
- new adapter service:
  - file: `src/services/mcc_jepa_adapter.py`
  - provider policy:
    - `runtime` -> dynamic runtime module (`MCC_JEPA_RUNTIME_MODULE` or request override)
    - `embedding` -> `src.utils.embedding_service.get_embedding`
    - fallback -> deterministic vectors
- predictive overlay integration:
  - file: `src/services/mcc_predictive_overlay.py`
  - new params:
    - `jepa_provider`
    - `jepa_runtime_module`
  - cache key now includes provider/runtime module
  - response stats now expose:
    - `predictor_mode`
    - `predictor_detail`
  - each predicted edge now includes:
    - `prediction_mode`
- API extension:
  - file: `src/api/routes/mcc_routes.py`
  - `POST /api/mcc/graph/predict` request now accepts:
    - `jepa_provider` (`auto|runtime|embedding|deterministic`)
    - `jepa_runtime_module` (optional module path)

### P3.1 smoke (service-level)
- `python3 -m py_compile` for:
  - `src/services/mcc_jepa_adapter.py`
  - `src/services/mcc_predictive_overlay.py`
  - `src/api/routes/mcc_routes.py`
- provider-mode smoke run:
  - `auto` -> `jepa_runtime_module` (`src.services.jepa_runtime`)
  - `runtime` -> `jepa_runtime_module` (`src.services.jepa_runtime`)
  - `runtime` with nonexistent module -> deterministic fallback + explicit reason
  - `embedding` without embedding service -> deterministic fallback + explicit reason
  - deterministic mode -> deterministic fallback

Verdict: `GO` for adapter contract and fallback behavior.  
Runtime provider module has been added:
- `src/services/jepa_runtime.py`
  - batch embedding path
  - Tao-style whitening pass
  - normalized vectors + bounded cache
  - deterministic local fallback if Ollama embedding call is unavailable

Remaining next step:
- replace surrogate runtime provider internals with true JEPA/V-JEPA model inference backend.

### MARKER_155.P3_1.JEPA_HTTP_RUNTIME_BRIDGE.V1
Added direct runtime bridge contract for external JEPA service:
- file: `src/services/jepa_runtime.py`
- env controls:
  - `MCC_JEPA_HTTP_ENABLE=1`
  - `MCC_JEPA_HTTP_URL=http://127.0.0.1:8099/embed_texts`
  - `MCC_JEPA_HTTP_TIMEOUT_SEC=2.5`
- expected endpoint contract:
  - request: `{"texts":[...], "dim":128}`
  - response: `{"vectors":[[...], ...], "model":"<name>"}`

If HTTP JEPA endpoint is unavailable, runtime falls back to local embedding path and preserves predictor continuity.

### MARKER_2026_JEPA_INTEGRATION_FULL (landing in KG pipeline)
Implemented media JEPA integration scaffolding with safe runtime behavior:
- added:
  - `src/knowledge_graph/jepa_integrator.py`
  - `src/knowledge_graph/jepa_to_qdrant.py`
- integrated into semantic DAG build pipeline:
  - `src/orchestration/semantic_dag_builder.py`
  - new pre-cluster step: `_hydrate_multimodal_embeddings_from_jepa()`
    - hydrates missing embeddings for metadata entries marked as `type=video|audio`
    - uses JEPA integrator with HTTP-runtime-first strategy and deterministic fallback
    - tags metadata with `jepa_extracted=true` when hydrated
- dependency policy:
  - no hard crash if OpenCV/Whisper/JEPA runtime endpoint is unavailable
  - fallback path preserves DAG build continuity

Runtime notes:
- optional requirements annotated in `requirements.txt`:
  - `opencv-python`, `mlx`, `mlx-lm`
- local env still requires explicit JEPA runtime service for true V-JEPA inference.

### MARKER_155.P3_1.JEPA_UI_DEFAULT_RUNTIME_ARCH.V1
MCC UI bind updated to default JEPA runtime provider on architecture LOD:
- file: `client/src/components/mcc/MyceliumCommandCenter.tsx`
- `/api/mcc/graph/predict` request now sends:
  - `jepa_provider = "runtime"` when `cameraLOD === "architecture"`
  - `jepa_provider = "auto"` for other LODs
  - `jepa_runtime_module` from `VITE_MCC_JEPA_RUNTIME_MODULE` or fallback `src.services.jepa_runtime`

### MARKER_155.P3_4.JEPA_RUNTIME_HEALTH_ROUTE.V1
Operational runtime handshake and diagnostics landed:
- `src/services/jepa_runtime.py`
  - added `runtime_health(force: bool)` and trigger-based `/health` probe cache
  - strict/live path now has explicit health evidence in backend detail
- `src/api/routes/mcc_routes.py`
  - added `GET /api/mcc/graph/predict/runtime-health`
  - supports `runtime_module` override and forced probe

Smoke summary:
- local stub runtime (`/health`, `/embed_texts`) verifies:
  - `runtime_health(force=True) -> ok=true`
  - strict adapter path reports `|jepa_http_runtime|`
- route execution smoke in current shell is environment-blocked (missing `fastapi` in direct test process), but compile gate passes.
