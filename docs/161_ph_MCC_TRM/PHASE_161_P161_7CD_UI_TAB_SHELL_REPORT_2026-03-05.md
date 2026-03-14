# PHASE 161 — P161.7.C/D UI Tab Shell Report (2026-03-05)

Protocol: `RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`
Status: `VERIFY COMPLETE`

## Scope
Implement UI tab-shell for multi-project MCC using backend registry APIs.

## Implemented

1. Store migration to active-project model:
- file: `client/src/store/useMCCStore.ts`
- added state:
  - `activeProjectId`
  - `projectTabs[]`
  - `projectTabsLoading`
- added actions:
  - `refreshProjectTabs()` -> `GET /api/mcc/projects/list`
  - `activateProjectTab(projectId)` -> `POST /api/mcc/projects/activate` + `initMCC()`
- `initMCC()` now hydrates:
  - `active_project_id`
  - `projects[]`

2. MCC tab-shell rendering:
- file: `client/src/components/mcc/MyceliumCommandCenter.tsx`
- marker:
  - `MARKER_161.7.MULTIPROJECT.UI.TAB_SHELL_RENDER.V1`
- behavior:
  - compact row of project tabs
  - active-tab highlighting
  - active tab visually connected to workspace frame (no floating-chip gap)
  - click tab -> activate project context
  - `+ project` button opens existing `OnboardingModal`

3. Monochrome UI policy applied to related modal:
- file: `client/src/components/mcc/OnboardingModal.tsx`
- switched to `NOLAN_PALETTE` tokens
- removed ad-hoc accent colors / colorful icon labels in this flow

4. UI contract tests:
- file: `tests/mcc/test_mcc_projects_tabs_ui_contract.py`
- validates store endpoints/actions and tab-shell marker presence.

## Verification

Executed:
- `pytest -q tests/mcc`

Result:
- `18 passed, 1 skipped`

## Markers touched

- `MARKER_161.7.MULTIPROJECT.UI.ACTIVE_PROJECT_STATE.V1`
- `MARKER_161.7.MULTIPROJECT.UI.INIT_ROUTE.V1`
- `MARKER_161.7.MULTIPROJECT.UI.TAB_SHELL_RENDER.V1`

## Notes

- This wave keeps existing first-run and onboarding flows, reusing them for `+ project`.
- No workflow execution semantics changed.
- Next wave can add explicit sandbox-target selection dialog (P161.7.E refinement).
