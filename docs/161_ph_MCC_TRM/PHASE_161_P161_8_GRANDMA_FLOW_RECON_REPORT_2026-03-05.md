# PHASE 161 — P161.8 Grandma Flow Recon Report
Date: 2026-03-05
Status: Implemented (narrow)

## Recon Findings

1. Active UI had two competing creation surfaces:
- modal onboarding (`OnboardingModal`)
- in-canvas first-run (`FirstRunView`)

This created cognitive split and duplicated source-selection semantics.

2. `+ project` in tab shell still routed to modal overlay, not to in-interface flow.

3. Source-step wording (`Local Path`) was interpreted as action button, but it was only a mode toggle.

## Fixes Applied

### A) Disable modal onboarding path in MCC
- file: `client/src/components/mcc/MyceliumCommandCenter.tsx`
- removed active modal route; `+ project` now routes to `first_run` level
- marker: `MARKER_161.8.MULTIPROJECT.UI.NO_MODAL_ONBOARDING.V1`

### B) Simplify first-run source step
- file: `client/src/components/mcc/FirstRunView.tsx`
- source options reduced to two:
  - `From This Mac`
  - `From Git URL`
- selecting `From This Mac` now immediately attempts native folder picker (Tauri)
- removed extra `Describe` path from active source step
- marker: `MARKER_161.8.MULTIPROJECT.UI.GRANDMA_FLOW_SOURCE_STEP.V1`

### C) Keep step-2 sandbox picker for later stage
- file: `client/src/components/mcc/OnboardingModal.tsx`
- retained as non-active compatibility artifact while P161.8 flow stabilizes

## Tests
- `pytest -q tests/mcc/test_mcc_projects_tabs_ui_contract.py tests/mcc`
- result: `23 passed, 1 skipped`

## Notes
- Full frontend TypeScript build currently fails due unrelated pre-existing errors across the workspace.
- P161.8 changes validated via targeted MCC contract tests.
