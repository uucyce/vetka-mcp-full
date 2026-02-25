# MARKER_155 Implementation Map (Single Source of Truth)

Date: 2026-02-22  
Status: active  
Goal: full-picture marker map without semantic duplicates

## Core Contracts

1. `MARKER_155.MODE_ARCH.V11.P1`
- File: `src/services/mcc_scc_graph.py`
- Meaning: backend `L0 -> L1(SCC) -> L2(view)` graph package.

2. `MARKER_155.INPUT_MATRIX.SCANNERS.V1`
- Files:
  - `docs/155_ph/MARKER_155_INPUT_MATRIX_SCANNER_CONTRACT.md`
  - `src/services/mcc_scc_graph.py`
- Meaning: typed relation channels + scanner contract.

3. `MARKER_155.ALGORITHMIC_DAG_FORMULAS.V1`
- File: `docs/155_ph/MARKER_155_ALGORITHMIC_DAG_FORMULAS_V1.md`
- Meaning: no-hardcode DAG formulas, computed root, backbone, KL.

4. `MARKER_155.INPUT_MATRIX.ROOT_SCORE.V1`
- File: `src/services/mcc_scc_graph.py`
- Meaning: algorithmic root scoring (graph/time/reference signals).

5. `MARKER_155.INPUT_MATRIX.BACKBONE_DAG.V1`
- File: `src/services/mcc_scc_graph.py`
- Meaning: default readable architecture graph = backbone edges.

6. `MARKER_155.INPUT_MATRIX.ROOT_COALESCE.V1`
- File: `src/services/mcc_scc_graph.py`
- Meaning: algorithmic root-count control for readability (no folder hardcode).

## Overlay Layer (Predictive)

7. `MARKER_155.MODE_ARCH.V11.P15`
- Files:
  - `docs/155_ph/MARKER_155_P15_JEPA_OVERLAY_SPEC.md`
  - `src/services/mcc_predictive_overlay.py`
- Meaning: JEPA/predictive edges as overlay, not base truth.

## UI-Side Transitional Markers

8. `MARKER_155A.G22.VETKA_TREE_ARCH`
- File: `client/src/hooks/useRoadmapDAG.ts`
- Meaning: fallback tree mapping and interim readability controls.

9. `MARKER_155.P15.UI_BIND`
- Files:
  - `client/src/components/mcc/MyceliumCommandCenter.tsx`
  - `client/src/hooks/useRoadmapDAG.ts`
- Meaning: client binding for predictive/condensed endpoints.

## Duplicate/Conflict Policy

- No duplicate marker should define conflicting behavior.
- Normative priority:
  1. `MARKER_155.ALGORITHMIC_DAG_FORMULAS.V1`
  2. `MARKER_155.MODE_ARCH.V11.P1`
  3. UI transitional markers (`155A.*`, `P15.UI_BIND`)

If conflict appears, formulas/backend contract wins and UI marker must be updated.

## Current Snapshot (Post P1.6+)

- Base graph uses SCC condensation and input-matrix channel aggregation.
- Roots and backbone are computed algorithmically in backend.
- L2 default edges are backbone-first.
- Cross-links preserved in L1 payload and can be shown as optional overlay.

## Tomorrow Focus

1. P1.7 scanner split by modality (Code/Doc/Video/Audio/Book/Script) with same `SignalEdge` schema.
2. Expose KL and root metrics in UI mini-panel for explainability.
3. Add `show_cross_links` toggle in MCC architecture view.
