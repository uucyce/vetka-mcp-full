# PHASE 162 — P4.P5 Runtime Scenario Matrix Recon (2026-03-07)

Goal: verify MYCO guidance via executable runtime scenarios (function-level), not marker-only contracts.

## Scope
- Runtime quick-reply matrix in `src/api/routes/chat_routes.py` (`_build_myco_quick_reply`).
- High-risk regression observed by operator: fallback to generic roadmap hint while workflow context is active.

## Risk identified
1. Static tests (markers/string presence) do not prove scenario routing correctness.
2. UI context might evolve; without direct runtime tests fallback branch can silently win.

## P4.P5 plan
1. Add runtime tests that call `_build_myco_quick_reply(...)` with realistic context payloads.
2. Assert role/family-specific actions for workflow-expanded scenarios.
3. Assert roadmap generic fallback is not used in node-unfold/workflow-expanded scenarios.

## Marker
- `MARKER_162.P4.P5.MYCO.RUNTIME_SCENARIO_MATRIX_LOCK.V1`

GO token: `GO P4.P5`
