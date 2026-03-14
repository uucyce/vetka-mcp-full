# P161.7 — Multi-Project Tabs (Backend Registry + UI Tab Shell)

Protocol: `RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`
Status: `RECON+markers complete`
Date: 2026-03-05

## Goal
Add multi-project workflow to MCC without UI clutter:
- one MCC window,
- multiple project tabs,
- each tab has isolated source/sandbox/session,
- DAG build path remains current stable builder (TRM/JEPA as optional compare/refine profiles).

## User Scenario (target)
1. User clicks `+` tab.
2. Modal A: choose existing project folder OR create new project folder.
3. Modal B: choose sandbox/playground location.
4. If new project: architect-guided bootstrap DAG.
5. If existing project: run build + compare (`baseline`, `JEPA-overlay`, `TRM profile when enabled`).

## Recon (current reality)

### Backend today
- Single project config file: `data/project_config.json`.
- Single session file: `data/session_state.json`.
- API assumes one active project globally:
  - `GET /api/mcc/init`
  - `POST /api/mcc/project/init`
  - sandbox endpoints are project-global.
- File anchors:
  - `src/services/project_config.py`
  - `src/api/routes/mcc_routes.py`

### Frontend today
- Store has singleton state:
  - `hasProject`, `projectConfig`.
- `projectScopePath` in MCC derives from singleton config and drives DAG fetch.
- Existing first-run/onboarding flow can be reused as a creation wizard.
- File anchors:
  - `client/src/store/useMCCStore.ts`
  - `client/src/components/mcc/MyceliumCommandCenter.tsx`
  - `client/src/components/mcc/OnboardingModal.tsx`
  - `client/src/components/mcc/FirstRunView.tsx`

## Marker Pack (inserted)

### Backend
1. `MARKER_161.7.MULTIPROJECT.REGISTRY.RECON.V1`
2. `MARKER_161.7.MULTIPROJECT.REGISTRY.PATHS.V1`
3. `MARKER_161.7.MULTIPROJECT.API.INIT_ACTIVE_PROJECT.V1`
4. `MARKER_161.7.MULTIPROJECT.API.PROJECT_CREATE.V1`

### Frontend
1. `MARKER_161.7.MULTIPROJECT.UI.ACTIVE_PROJECT_STATE.V1`
2. `MARKER_161.7.MULTIPROJECT.UI.INIT_ROUTE.V1`
3. `MARKER_161.7.MULTIPROJECT.UI.TAB_SCOPE_BIND.V1`
4. `MARKER_161.7.MULTIPROJECT.UI.NEW_TAB_WIZARD.V1`

## Architecture Decision
Do not fork MCC runtime.
Evolve existing single-project path into `active project context` + `registry`, with backward compatibility.

## Data Model v1 (proposed)

### Registry storage
- `data/mcc_projects_registry.json`

Shape:
- `schema_version`
- `active_project_id`
- `projects[]` with:
  - `project_id`
  - `source_type`
  - `source_path`
  - `sandbox_path`
  - `quota_gb`
  - `created_at`
  - `qdrant_collection`
  - `last_opened_at`

### Per-project session
- `data/mcc_sessions/<project_id>.session_state.json`

### Compatibility
- On first boot, if legacy single files exist, auto-import as first registry project.

## API Plan (narrow)

### Keep existing
- `GET /api/mcc/init`
- `POST /api/mcc/project/init`

### Extend safely
- `GET /api/mcc/init?project_id=...`
- `POST /api/mcc/project/init` returns created `project_id` and can set active.

### New endpoints
1. `GET /api/mcc/projects/list`
2. `POST /api/mcc/projects/activate`
3. `POST /api/mcc/projects/create`
4. `DELETE /api/mcc/projects/{project_id}` (soft delete in v1, optional hard delete flag)

## UI Plan (tab shell)

### Minimal shell
- Top bar with project tabs.
- `+` opens create/select modal.
- Active tab controls `projectScopePath` and all DAG/API calls.
- Active tab must be visually connected to the workspace frame (no floating-chip look, no visual gap).

### Reuse
- Reuse `OnboardingModal` as create-tab wizard.
- Keep current DAG canvas/layout untouched.

### Guardrails
- No new side panels.
- No duplicated DAG state per tab in memory unless active.
- Cache last DAG payload per tab id (small cap, LRU 3-5 tabs).
- Visual policy (hard):
  - monochrome only: black/white/gray;
  - no ad-hoc colors, no random icon palette;
  - use only existing project palette tokens (exact values);
  - use only existing project fonts/typography tokens;
  - no ready-made colorful icons in tab strip or popovers.
- Asset policy for Tauri:
  - prefer white SVG source assets;
  - generate PNG derivatives only via project pipeline/tooling (no manual color edits);
  - popover/tab assets follow the same monochrome rule.

## Implementation Steps

### P161.7.A — Registry backend skeleton
- Add registry service (list/create/activate).
- Add legacy migration read-path.
- Keep old `ProjectConfig.load()` functional for fallback.

### P161.7.B — API bind
- Wire new `/projects/*` routes.
- Extend `/init` with optional `project_id` selection.

### P161.7.C — Store migration
- Add `projectTabs[]`, `activeProjectId` to `useMCCStore`.
- Keep `projectConfig` alias for active tab only (compat layer).

### P161.7.D — UI tab shell
- Add tabs row + `+` action in MCC header.
- Bind `projectScopePath` to active tab.
- Apply active-tab-to-frame visual connection rule and monochrome design constraints.

### P161.7.E — Wizard adaptation
- Reuse `OnboardingModal` as “new tab project” flow.
- Add two-step source/sandbox input.
- Enforce palette/typography/icon constraints in modal and popovers from day one.
- Close modal via `Esc` (keyboard-first); no dedicated Cancel button in UI.

### P161.7.F — Verify
- API tests for list/create/activate.
- UI contract tests for tab switching scope.
- No regressions in existing `tests/mcc` pack.

### P161.8 — In-Interface Grandma Flow (no modal onboarding)
- Remove modal onboarding from active path; use only in-canvas `first_run`.
- `+ project` always routes to `first_run` creation surface.
- First show empty draft tab canvas (no DAG), then show source/setup overlay with slight delay.
- Draft tab canvas keeps default mini-window placeholders so user sees target workspace context.
- Source step should be explicit and minimal:
  - `From Disk` (opens picker immediately),
  - `From Git`,
  - `Skip for now` (returns to previous workspace state).
- Reduce control count on source step (single primary next action, no duplicate browse controls).
- Keep strict monochrome style and existing palette tokens.

Markers:
- `MARKER_161.8.MULTIPROJECT.UI.NO_MODAL_ONBOARDING.V1`
- `MARKER_161.8.MULTIPROJECT.UI.GRANDMA_FLOW_SOURCE_STEP.V1`
- `MARKER_161.8.MULTIPROJECT.UI.DRAFT_TAB_EMPTY_CANVAS.V1`
- `MARKER_161.8.MULTIPROJECT.UI.DRAFT_TAB_MINI_DEFAULTS.V1`
- `MARKER_161.8.MULTIPROJECT.UI.DRAFT_TAB_DELAYED_OVERLAY.V1`

Acceptance:
- No modal overlay is required to create a project tab.
- User can start project creation from the main interface with one click (`+ project`).
- Draft tab starts as empty workspace context first, then setup dialog appears over it.
- Source selection language is self-explanatory for non-technical users.

## Test Plan (must before behavior-heavy rollout)

1. `tests/mcc/test_mcc_projects_registry_api.py`
   - list/create/activate contract
2. `tests/mcc/test_mcc_init_active_project.py`
   - `/init` respects active project
3. `tests/mcc/test_mcc_tab_scope_binding_contract.py`
   - roadmap scope follows active tab
4. run existing:
   - `pytest -q tests/mcc`

## Risks and mitigations

1. Risk: breaking current single-project startup.
   - Mitigation: compatibility layer + migration import + fallback path.
2. Risk: DAG source mix between tabs.
   - Mitigation: strict scope binding (`activeProjectId` in every DAG fetch).
3. Risk: user confusion from too many controls.
   - Mitigation: one new element only (`tabs row` + `+`), no extra panels.

## Definition of Done

1. User can open multiple project tabs and switch without restarting MCC.
2. Each tab has its own source/sandbox/session context.
3. DAG load/build/compare operates against active tab scope only.
4. Existing single-project flow still works (legacy compatibility).
