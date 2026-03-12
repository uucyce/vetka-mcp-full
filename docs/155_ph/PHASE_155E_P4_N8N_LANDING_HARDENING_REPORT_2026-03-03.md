# PHASE 155E — P4 n8n Landing Hardening Report (2026-03-03)

Scope: `P4` from `PHASE_155E_WAVE_E_RECON_MARKERS_2026-03-03.md`.

## Implemented markers

1. `MARKER_155E.WE.N8N_RUNTIME_LANDING.V1`
- Added explicit deterministic profile marker in metadata:
  - import: `workflow.metadata.runtime_mapping_profile = "n8n->canonical->runtime.v1"`
  - export: `meta.runtime_mapping_profile = "n8n->canonical->runtime.v1"`

2. `MARKER_155E.WE.N8N_TYPE_PRESERVE_ASSERT.V1`
- n8n import now preserves exact connection slot metadata per edge:
  - `output_type`
  - `output_index`
  - `target_type`
  - `target_index`
- Stored under: `edge.data.n8n_connection`.

3. `MARKER_155E.WE.RUNTIME_CANONICAL_ROUNDTRIP.V1`
- n8n export now prefers preserved edge slot metadata for deterministic reconstruction.
- Fallback remains backward compatible for legacy workflows without `n8n_connection` metadata.
- Added API-level roundtrip assertion (`/api/workflows/import` -> `/api/workflows/{id}/export`) to verify profile + slot preservation through endpoint path.

## Files changed

1. `src/services/converters/n8n_converter.py`
2. `tests/test_phase155e_p4_n8n_landing_hardening.py`
3. `docs/155_ph/PHASE_155E_P4_N8N_LANDING_HARDENING_REPORT_2026-03-03.md`

## Verify

- `pytest -q tests/test_phase155e_p4_n8n_landing_hardening.py`
- Result: `3 passed`.

## Notes

- This implementation hardens import/export determinism for n8n connection structure without changing existing workflow UX.
- Additional end-to-end checks via `/api/workflows/import` + `/api/workflows/{id}/export` can be added as follow-up integration harness.
