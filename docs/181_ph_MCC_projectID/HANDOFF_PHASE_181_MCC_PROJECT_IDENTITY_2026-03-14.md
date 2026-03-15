# HANDOFF: Phase 181 MCC Project Identity Isolation

Date: 2026-03-14  
Phase: 181  
Owner: Codex

## Scope Completed

This handoff captures the current state of MCC multi-project isolation after implementing the next roadmap slices from:

- `IMPLEMENTATION_PLAN_MCC_PROJECT_IDENTITY_ISOLATION_2026-03-13.md`

Delivered in this phase:

1. Project identity is explicit on key MCC routes and store flows (`project_id`, `window_session_id`).
2. Registry is now a stronger source of truth with per-project snapshot persistence (`data/mcc_projects/<project_id>/project_config.json`).
3. Canonical workspace/context scope fields are present (`workspace_path`, `context_scope_path`).
4. Cross-window project-tab sync is now event-driven (`storage` sync key) in addition to focus/poll.
5. Project classification is introduced (`project_kind` + `tab_visibility`) so fixture/temp/legacy projects are hidden from default tab shell.

## Key Implementation Notes

## 1) Canonical project scope and snapshot persistence

- `src/services/project_config.py`
  - Added `resolved_workspace_path()` and `resolved_context_scope_path()`.
  - Added `project_kind: user|fixture|temp|legacy`.

- `src/services/mcc_project_registry.py`
  - Added snapshot directory: `PROJECTS_DIR = data/mcc_projects`.
  - Added per-project snapshot IO helpers and bootstrap reconciliation from snapshots.
  - `list_projects()` now returns:
    - `updated_at`
    - `workspace_path`
    - `context_scope_path`
    - `project_kind`
    - `tab_visibility`
    - `hidden_count`
  - Default listing hides non-user projects unless `include_hidden=True`.

## 2) API contract updates

- `src/api/routes/mcc_routes.py`
  - `InitResponse` now includes `updated_at` and `hidden_count`.
  - `ProjectInitRequest` includes `project_kind`.
  - `ProjectInitResponse` includes `project_kind`.
  - `GET /api/mcc/projects/list` now supports `include_hidden` query flag.
  - `mcc/init` uses `always_include_project_id` for requested project so direct-open by `project_id` still works for hidden projects.

## 3) MCC frontend tab/session behavior

- `client/src/store/useMCCStore.ts`
  - Added `project_kind`, `tab_visibility` to tab model.
  - Added `projectTabsHiddenCount`.
  - Added local storage sync channel:
    - `MCC_PROJECT_REGISTRY_SYNC_KEY`
    - `announceProjectRegistryChanged(...)`

- `client/src/components/mcc/MyceliumCommandCenter.tsx`
  - Listens to `storage` events and refreshes tabs on cross-window project changes.
  - Shows `+N hidden` hint in tab row.

- `client/src/components/mcc/FirstRunView.tsx`
- `client/src/components/mcc/OnboardingModal.tsx`
  - After project create, broadcast registry-change event to other windows.

## 4) Fixture flow hardening

- `scripts/mcc_seed_playwright_fixture.py`
  - Uses `projects/list?include_hidden=1` for fixture lookup.
  - Creates fixture projects with `"project_kind": "fixture"`.

## Validation Executed

Primary regression pack:

```bash
pytest -q tests/mcc/test_mcc_projects_registry_api.py \
  tests/mcc/test_mcc_projects_tabs_ui_contract.py \
  tests/test_phase177_mcc_playwright_seed_contract.py
```

Result: `17 passed`

Syntax checks:

```bash
python -m py_compile src/services/project_config.py \
  src/services/mcc_project_registry.py \
  src/api/routes/mcc_routes.py \
  scripts/mcc_seed_playwright_fixture.py
```

Result: OK

## Known Gaps / Risks

1. Legacy playground folders (`data/playgrounds/fake_project_*`) still exist and are not automatically elevated to user projects.
2. Hidden-project behavior now prevents tab pollution, but there is no explicit UI for "import legacy playground as real project".
3. Global/legacy fallback paths still exist in parts of MCC stack; they should continue shrinking as project-registry flows become fully canonical.

## Recommended Next Slice (First Task In Next Chat)

Implement a controlled legacy import/reconcile flow:

1. Add endpoint to scan candidate legacy playgrounds and return import preview.
2. Add explicit import action that creates proper `ProjectConfig` + `project_kind=user` with normalized `display_name`.
3. Add MCC UI action for "Import legacy playground" (separate from normal `+ project` path).
4. Keep automatic hiding for non-user projects; imported ones become visible tabs.

## Files Touched In This Slice

- `src/services/project_config.py`
- `src/services/mcc_project_registry.py`
- `src/api/routes/mcc_routes.py`
- `client/src/store/useMCCStore.ts`
- `client/src/components/mcc/MyceliumCommandCenter.tsx`
- `client/src/components/mcc/FirstRunView.tsx`
- `client/src/components/mcc/OnboardingModal.tsx`
- `scripts/mcc_seed_playwright_fixture.py`
- `tests/mcc/test_mcc_projects_registry_api.py`
- `tests/mcc/test_mcc_projects_tabs_ui_contract.py`
- `tests/test_phase177_mcc_playwright_seed_contract.py`

