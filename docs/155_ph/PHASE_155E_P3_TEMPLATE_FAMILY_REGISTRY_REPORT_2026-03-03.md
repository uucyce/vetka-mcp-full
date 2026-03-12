# PHASE 155E — P3 Template Family Registry Report (2026-03-03)

Scope: `P3` from `PHASE_155E_WAVE_E_RECON_MARKERS_2026-03-03.md`.

## Implemented markers

1. `MARKER_155E.WF.FAMILY.REGISTRY.V1`
- Added normalized workflow family contract in `WorkflowTemplateLibrary`:
  - required keys: `family`, `version`, `roles`, `policy`
  - auto-normalization on `load_all()` for legacy templates.
- Added API endpoint `GET /api/mcc/workflow-families`.

2. `MARKER_155E.WF.FAMILY.BMAD_G3_RALPH_BIND.V1`
- Bound `bmad_default`, `g3_critic_coder`, `ralph_loop` to one family contract (`core_library`, `v1`).
- Added strict default policy normalization for role/edge semantics.

3. `MARKER_155E.WF.FAMILY.OPENHANDS_PULSE_STUBS.V1`
- Added template stubs:
  - `data/templates/workflows/openhands_collab_stub.json`
  - `data/templates/workflows/pulse_scheduler_stub.json`
- Added selector routing for `openhands` and `pulse` task types/descriptions.

## Files changed

1. `src/services/architect_prefetch.py`
2. `src/api/routes/mcc_routes.py`
3. `data/templates/workflows/openhands_collab_stub.json`
4. `data/templates/workflows/pulse_scheduler_stub.json`
5. `tests/test_phase155e_p3_template_family_registry.py`
6. `docs/155_ph/PHASE_155E_P3_TEMPLATE_FAMILY_REGISTRY_REPORT_2026-03-03.md`

## Verify

- Run targeted test file:
  - `pytest -q tests/test_phase155e_p3_template_family_registry.py`
- The registry, core-family binding, and OpenHands/Pulse selection are covered.

## Notes

- Runtime execution remains default BMAD-compatible; OpenHands/Pulse are currently governance stubs with strict family metadata.
- Deep pipeline behavior tuning for these families remains deferred to next phase (already tracked in prior roadmap TODOs).
