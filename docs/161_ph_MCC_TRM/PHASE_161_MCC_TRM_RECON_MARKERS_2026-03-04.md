# PHASE 161 — MCC TRM Recon + Markers (2026-03-04)

Protocol: `RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`
Status: `REPORT`
Scope: TRM integration planning for Algorithmic Offload in MCC/VETKA DAG pipeline.

---

## 1) Recon Summary (fact-based from current code)

Current production DAG path is already algorithmic and split into stable stages:

1. API entry:
   - `POST /api/mcc/graph/build-design`
   - `POST /api/mcc/graph/build-design/from-array`
   - file: `src/api/routes/mcc_routes.py`
2. Builder core:
   - `build_design_dag(...)`
   - `build_design_dag_from_arrays(...)`
   - file: `src/services/mcc_architect_builder.py`
3. Runtime graph substrate:
   - `build_condensed_graph(...)`
   - file: `src/services/mcc_scc_graph.py`
4. Variant exploration:
   - `run_dag_auto_compare(...)`
   - file: `src/services/mcc_dag_compare.py`
5. Version registry:
   - `create_dag_version/list/get/set_primary`
   - file: `src/services/mcc_dag_versions.py`
6. Frontend source arbitration for roadmap canvas:
   - hook `useRoadmapDAG` (build-design -> condensed -> tree -> legacy fallback)
   - file: `client/src/hooks/useRoadmapDAG.ts`

Key constraint already enforced in code: architectural backbone is deterministic and verifier-gated; predictive layer (JEPA) is overlay-oriented.

---

## 2) Why TRM here (and what not to do)

TRM is suitable as an **algorithmic offload module** for structured graph-shaping heuristics under fixed budgets, but should not directly replace backbone DAG generation in v1.

Recommended role in MCC pipeline:
- not `backbone replacement`
- yes `candidate scorer / recursive refiner` over:
  - root selection
  - branch packing
  - cross-edge arbitration
  - compare score enrichment

This keeps current stable SCC+Design pipeline and introduces TRM as gated optimization.

---

## 3) Code Entry/Exit Marker Map (for Phase 161)

### A. API entry markers
- `src/api/routes/mcc_routes.py`
  - `MARKER_161.TRM.API.BUILD_DESIGN_INPUT.V1`
    - entry point for TRM policy/config in `BuildDesignGraphRequest`
  - `MARKER_161.TRM.API.BUILD_FROM_ARRAY_INPUT.V1`
    - entry point for array-schema TRM adapters
  - `MARKER_161.TRM.API.AUTO_COMPARE_INPUT.V1`
    - variant-level TRM toggles in compare runs

### B. Builder core markers
- `src/services/mcc_architect_builder.py`
  - `MARKER_161.TRM.BUILDER.ENTRY.V1`
    - gateway before design graph assembly
  - `MARKER_161.TRM.BUILDER.ARRAY_BRIDGE.V1`
    - arbitrary records/relations normalization to TRM-ready tensor/features
  - `MARKER_161.TRM.BUILDER.REFINE_GATE.V1`
    - apply TRM suggestions only under verifier-safe policy
  - `MARKER_161.TRM.BUILDER.EXIT_PAYLOAD.V1`
    - expose TRM diagnostics in response markers/stats

### C. Compare and scoring markers
- `src/services/mcc_dag_compare.py`
  - `MARKER_161.TRM.COMPARE.SCORECARD_EXT.V1`
    - add readability/topology terms derived from TRM refinement logs
  - `MARKER_161.TRM.COMPARE.VARIANT_POLICY.V1`
    - standard variant profiles with/without TRM

### D. Frontend source/render markers
- `client/src/hooks/useRoadmapDAG.ts`
  - `MARKER_161.TRM.UI.SOURCE_BADGE.V1`
    - expose `graph_source = design|condensed|tree|trm_refined`
  - `MARKER_161.TRM.UI.RENDER_GUARD.V1`
    - prevent client-side rewiring from destroying backend topology

### E. Versioning markers
- `src/services/mcc_dag_versions.py`
  - `MARKER_161.TRM.VERSION_META.V1`
    - persist TRM config/refinement stats per DAG version

---

## 4) Gaps identified now

1. No explicit `graph_source` contract in build-design response for TRM lineage.
2. No config object for algorithmic-policy packs (hardcoded defaults dominate).
3. No golden datasets for non-code array inputs to measure DAG quality drift.
4. No TRM-specific verifier gate (currently generic verifier only).
5. No deterministic replay artifact for compare runs (seed/config snapshot is partial).

---

## 5) Test baseline present vs missing

Already present in `tests/mcc`:
- auto-compare ranking (service/API)
- dag-versions list/create path
- UI contract presence for auto-compare endpoint

Missing for Phase 161:
- TRM policy schema validation tests
- TRM-off vs TRM-on deterministic replay tests
- quality regression tests on fixed “golden” inputs
- response contract tests for TRM diagnostics/markers

---

## 6) External TRM evidence used for planning

Primary sources checked:
- GitHub repo: `SamsungSAILMontreal/TinyRecursiveModels`
- paper: `Less is More: Recursive Reasoning with Tiny Networks` (arXiv:2510.04871)

Planning inference:
- TRM strengths are iterative refinement and compute-depth tradeoff;
- this aligns with MCC compare/refine loop, not with immediate full replacement of deterministic DAG backbone.

---

## 7) Recon conclusion

Phase 161 should start as **TRM-assisted refinement layer** behind strict verifier gates and reproducible compare harness.

Do not migrate MCC DAG backbone to TRM directly in first iteration.
