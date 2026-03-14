# ARCHITECT_BUILD_CONTRACT_V1

Status: Implemented baseline (code-aligned)
Date: 2026-02-25
Owner: MCC Architect Pipeline

Markers:
- `MARKER_155.ARCHITECT_BUILD.CONTRACT.V1`
- `MARKER_155.ARCHITECT_BUILD.VERIFIER.V1`
- `MARKER_155.ARCHITECT_BUILD.JEPA_OVERLAY.V1`
- `MARKER_155.MEMORY.SHARED_DAG_POLICY.V1`

Source of truth (current implementation):
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/mcc_architect_builder.py`

## 1. Goal
Build architecture-first Design DAG from selected project scope, suitable for one-canvas MCC flow:
- rooted and acyclic backbone,
- readable overview,
- deterministic runtime facts separated from predictive hints,
- ready for task placement and drill.

Pipeline intent:
`Research -> Design -> Plan -> Implement -> Verifier/Eval`

## 2. Inputs (API Contract)
Endpoint build input fields:
- `scope_path` (optional; resolved scope root)
- `max_nodes` (overview budget)
- `include_artifacts` (bool)
- `problem_statement` (string)
- `target_outcome` (string)
- `use_predictive_overlay` (bool)
- `max_predicted_edges`
- `min_confidence`

Runtime clamps (implemented):
- `max_nodes`: `50..5000`
- `max_predicted_edges`: `0..2000`
- `min_confidence`: `0.0..0.99`

## 3. Implementation Order (actual v1)
1. `build_condensed_graph(...)` -> runtime graph basis
2. `_embed_texts(...)` -> semantic vectors
3. `_whiten_vectors(...)` -> Tao-style eigen whitening
4. `_cluster_vectors(...)` -> HDBSCAN/DBSCAN/quantile fallback
5. `_build_design_graph(...)` -> architecture topology + scoped cross edges
6. `build_predictive_overlay(...)` (optional)
7. `_verifier_report(...)` + `_spectral_metrics(...)`

## 4. Step Details and Parameters
### 4.1 Embedding
- Primary: `src.utils.embedding_service.get_embedding`
- Fallback: deterministic stable hashing vector
- Working dimension target: `128`
- L2 normalization applied

### 4.2 Whitening
- Covariance eigen whitening
- Keep principal components up to ~95% variance
- Component bounds: `min 4`, `max 96`
- Safe fallback if numeric conditions are not met

### 4.3 Clustering
Priority chain:
1. `HDBSCAN`
   - `min_cluster_size = max(2, round(sqrt(n)))`
   - `min_samples = 1`
   - `metric = euclidean`
2. `DBSCAN` fallback
   - `eps = 1.25`
   - `min_samples = 2`
3. Deterministic quantile bins fallback

### 4.4 Design Graph Budgeting
- `total_budget = clamp(0.9 * max_nodes, 24..260)`
- `max_top_dirs = clamp(round(total_budget**0.42), 5..14)`
- `lvl2_per_branch = clamp(sqrt(total_budget / branch_count) + 1, 2..10)`
- `lvl3_per_lvl2 = clamp(sqrt(lvl2_per_branch) + 1, 1..5)`

Directory importance score (implemented):
- `importance = file_count + 0.9 * flow_degree`

### 4.5 Edge Policy
- Base topology: structural tree edges only
- Dependency cross edges: limited (focus-safe)
  - per source cap: `clamp(sqrt(k), 1..3)`
  - default confidence around `0.68`

## 5. Outputs (Build Result Contract)
Top-level response fields:
- `scope_root`
- `architect_context`
- `runtime_graph`
- `design_graph`
- `predictive_overlay`
- `verifier`
- `markers`

Layer semantics:
1. `runtime_graph`: deterministic scanner/runtime truth
2. `design_graph`: architecture view for planning/drill
3. `predictive_overlay`: candidate edges only, non-authoritative

## 6. DAG Invariants
Required for PASS path:
- Acyclic structural backbone
- Layer monotonicity (`source_layer < target_layer` for base edges)
- Explicit cycle handling via SCC/runtime trace (no silent dropping)
- Explainable edge channels/evidence

## 7. Verifier / Eval Contract
Verifier fields:
- `acyclic`
- `monotonic_layers`
- `orphan_rate`
- `density`
- `avg_out_degree`
- `spectral`:
  - `lambda2`
  - `eigengap`
  - `component_count`
  - `status` = `ok|warn|fail`
- `decision` = `pass|warn|fail`

Decision policy (implemented):
- `fail` if: not acyclic OR not monotonic OR spectral fail
- `warn` if: `orphan_rate > 0.35` OR spectral warn
- `pass` otherwise

Spectral sampling cap (implemented):
- max nodes analyzed in spectral block: `220`

## 8. JEPA Role (v1 vs future)
Current v1:
- JEPA does **not** mutate base architecture topology
- predictive layer is overlay-only (candidate links)

Future gated evolution (v2 intent):
- JEPA candidates may be promoted only after verifier + explicit policy gate

## 9. Runtime Budget and Degradation
Current v1 behavior:
- Budgeting limits prevent unbounded node explosion in overview
- Spectral analysis capped to fixed sample size
- Fallback chain keeps builder deterministic under dependency/model failures

Planned hardening:
- expose budget profile presets (`small/medium/large`) in API
- explicit timeout and fallback reason codes in response

## 9A. Array Core (implemented)
Markers:
- `MARKER_155.ARCHITECT_BUILD.ARRAY_CORE.V1`
- `MARKER_155.ARCHITECT_BUILD.ARRAY_RUNTIME_BRIDGE.V1`
- `MARKER_155.ARCHITECT_BUILD.ARRAY_INFER_EDGES.V1`
- `MARKER_155.ARCHITECT_BUILD.ARRAY_API.V1`

Implemented:
- generic algorithmic-offload path for arbitrary arrays:
  - `records[]` (required)
  - `relations[]` (optional)
- runtime bridge normalizes records into L0 module-like graph.
- deterministic edge inference is applied when relations are missing.
- output package stays contract-compatible with regular `build_design_dag`.

API:
- `POST /api/mcc/graph/build-design/from-array`
  - request: `scope_name, records, relations, max_nodes, use_predictive_overlay, max_predicted_edges, min_confidence`
  - response: standard architect build package (`runtime_graph, design_graph, predictive_overlay, verifier, markers`)

## 10. Rollback Policy
If build quality degrades:
1. disable predictive overlay
2. fallback to deterministic runtime->design baseline
3. keep verifier visible and return reason

No destructive automatic rewrite of user-pinned layout state.

## 11. Interaction Contract (UI)
- Topology default: clean architecture backbone
- Dependency edges on focus (not global noise)
- Focus persistence across zoom
- Shift multi-select merges dependency overlay
- Pin/drag persistence must survive soft refresh

## 12. Shared Memory Policy (MCC <-> VETKA)
- Shared preference intent in ENGRAM for DAG layout habits
- Store coefficients/preferences, not absolute x/y as canonical truth
- Local surfaces may keep local coordinates
- Scope isolation key: `project_root + graph_type + nav_level`
- Explicit user pin overrides learned preference

## 13. Acceptance Criteria (v1)
- Deterministic output for same scope/signature
- Verifier always present
- Base graph remains acyclic/layer-monotonic under PASS
- Overlay visibly and contractually separated
- Result directly usable for architect task placement

## 14. Known Gaps (tracked)
- Full JEPA runtime model path is prepared but not authoritative yet
- Some projects still require better topology readability heuristics at high density
- Shutdown blockers in Mycelium process lifecycle require separate diagnostics hardening
