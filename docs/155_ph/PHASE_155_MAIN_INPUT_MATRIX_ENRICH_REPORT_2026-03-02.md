# PHASE 155 Main Flow — Input Matrix Enrich API Report (2026-03-02)

Status: `IMPLEMENTED + VERIFIED`

## 1) Delivered marker
1. `MARKER_155B.CANON.INPUT_MATRIX_ENRICH_API.V1`

## 2) API delivered
1. `POST /api/workflow/enrich/input-matrix/{graph_id}`

File:
1. `src/api/routes/workflow_routes.py`

## 3) Behavior
1. Resolves canonical graph package (version-backed or live-build fallback) via existing materialization path.
2. Supports `graph_mode` (`design|runtime`) and policy inputs:
   - `min_score`
   - `include_rejected`
   - `scope_path`
   - `max_nodes`
3. Applies channel scorers per edge:
   - `explicit`
   - `temporal`
   - `referential`
   - `semantic`
4. Writes edge-level enrich metadata to `edge.meta.input_matrix`:
   - `score`
   - `channel_scores`
   - `relation_kind`
   - `source_type` / `target_type`
   - `weights`
   - `accepted`
5. Returns enriched graph + aggregate channel histogram and acceptance counters.

## 4) Tests
Added:
1. `tests/test_phase155b_input_matrix_enrich_api.py`

Executed:
1. `pytest -q tests/test_phase155b_input_matrix_enrich_api.py tests/test_phase155b_p1_graph_source_routes.py tests/test_phase155b_p4_spectral_routes.py`
2. `pytest -q tests/test_phase155_p0_drilldown_markers.py -k "155"`

Result:
1. `8 passed` (input-matrix + p1 + p4 regression subset)
2. `20 passed` (phase155 marker guard pack)
