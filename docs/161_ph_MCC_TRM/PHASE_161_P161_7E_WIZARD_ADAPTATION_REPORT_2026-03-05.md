# PHASE 161 — P161.7.E Wizard Adaptation Report
Date: 2026-03-05
Status: Implemented + verified

## Scope
Adapt `OnboardingModal` for multi-project tab creation flow and wire explicit sandbox target path for project init.

## Implemented

### 1) New-project wizard behavior in UI
- File: `client/src/components/mcc/OnboardingModal.tsx`
- Implemented 2-step flow:
  - `source` step: source type + source path
  - `sandbox` step: sandbox/playground path + quota
- Kept progress states: `scanning`, `ready`, `error`.
- Added keyboard close behavior:
  - `MARKER_161.7.MULTIPROJECT.UI.ESC_CLOSE_MODAL.V1`
  - `Escape` closes modal.
- No separate `Cancel` action in UI (per UX request).

### 2) Backend contract extension for sandbox target
- File: `src/api/routes/mcc_routes.py`
  - `ProjectInitRequest` extended with optional `sandbox_path`.
  - `/api/mcc/project/init` passes `sandbox_path` to config creation.
- File: `src/services/project_config.py`
  - `ProjectConfig.create_new(...)` accepts optional `sandbox_path`.
  - If omitted: default `data/playgrounds/<project_id>` behavior remains.
  - Validation guard: `sandbox_path` must be absolute.

### 3) Roadmap updates
- File: `docs/161_ph_MCC_TRM/P161_7_MULTI_PROJECT_TABS_RECON_PLAN_2026-03-05.md`
  - Added explicit UX item: close create-project modal by `Esc` (no visible cancel button).
- File: `docs/161_ph_MCC_TRM/CODEX_PHASE_161_MCC_TRM_MASTER_PLAN.md`
  - Added W7 deliverable line for `Esc`-close behavior.

## Verification

### Automated
- Command: `pytest -q tests/mcc`
  - Result: `18 passed, 1 skipped`
- Command: `pytest -q tests/test_phase153_wave3.py tests/mcc`
  - Result: `29 passed, 1 skipped`

### Test hardening done
- Updated legacy onboarding tests for registry isolation and current multi-project behavior:
  - `tests/test_phase153_wave3.py`
- Updated MCC registry API test fixture to fully isolate registry/config paths:
  - `tests/mcc/test_mcc_projects_registry_api.py`

## Notes
- This wave changes project-init contract (optional `sandbox_path`) in backward-compatible mode.
- Existing clients that do not send `sandbox_path` continue to work unchanged.
