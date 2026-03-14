# MARKER_155 P1.6 Implementation (IMPL NARROW)

Date: 2026-02-22  
Status: implemented (narrow), verified locally by service call

## Scope

Implemented backend upgrade for `L0 -> SCC -> L2` with input-matrix style channel aggregation:
- structural
- temporal
- reference
- semantic

Kept API shape compatible for `/api/mcc/graph/condensed`.

## Files Changed

- `src/services/mcc_scc_graph.py`
- `client/src/hooks/useRoadmapDAG.ts`
- `docs/155_ph/MARKER_155_INPUT_MATRIX_SCANNER_CONTRACT.md`
- `docs/155_ph/P1_6_CONDENSED_SAMPLE.json`

## Backend Changes

### 1) Channelized L0 edge scoring

Added:
- pair-weight matrix by source/target type
- sigmoid aggregation
- channel evidence preservation
- non-structural gate for temporal/semantic/reference promotion

Result edge fields now include:
- `type` / `relation_kind`
- `score` / `confidence`
- `channels`
- `pair_types`
- `evidence`

### 2) SCC condensation from scored graph

`L1` is now built from aggregated accepted edges (not only explicit imports), while preserving acyclicity through SCC condensation.

### 3) Stats extension

`stats` now includes:
- `l0_explicit_edges`
- `l0_reference_edges`
- `l0_channel_hist`

## UI Anti-Spaghetti Guard

In `useRoadmapDAG`:
- added virtual architecture root for multi-root L2
- hardened edge thinning with global budget and near-tree incoming constraints

This reduces cross-canvas over-connection in architecture LOD.

## Verification Snapshot

Local run (`build_condensed_graph(..., max_nodes=180)`):
- `l0_nodes`: 821
- `l0_edges`: 2017
- `l0_channel_hist`: `{"structural": 1569, "semantic": 19, "temporal": 429}`
- `l1_scc_nodes`: 671
- `l2_nodes`: 180
- `l2_edges`: 439

Sample output saved to:
- `docs/155_ph/P1_6_CONDENSED_SAMPLE.json`

## Limitations (Known)

- Scanner family is not yet split into dedicated classes (`CodeScanner/VideoScanner/...`): this is planned for P1.7.
- Media/book/audio/script channels are contract-defined but not fully extracted in code yet.
- Endpoint wiring depends on active runtime app/router registration.

## Markers

- `MARKER_155.INPUT_MATRIX.SCANNERS.V1`
- `MARKER_155.MODE_ARCH.V11.P1`

