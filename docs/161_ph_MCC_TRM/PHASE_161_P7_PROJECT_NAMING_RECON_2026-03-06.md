# PHASE 161 — P7 Project Naming Recon (2026-03-06)

Protocol: `RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`  
Scope: harmonized project naming in first-run flow and all dependent layers

Markers:
- `MARKER_161.9.PROJECT_NAMING.RECON.V1`
- `MARKER_161.9.PROJECT_NAMING.UI_INPUT.V1`
- `MARKER_161.9.PROJECT_NAMING.API_CONTRACT.V1`
- `MARKER_161.9.PROJECT_NAMING.REGISTRY_PERSIST.V1`
- `MARKER_161.9.PROJECT_NAMING.UI_TAB_LABEL.V1`

---

## 1) Problem statement

Current gap:
- user can create a new tab project, but explicit project name is not captured as first-class value.
- tab label is derived heuristically from `source_path`/`sandbox_path` basename.
- for `source_type=empty`, `source_path` is temporary folder, so naming may be unstable/non-human.

Desired behavior:
1. user defines project name at creation step (or derives it predictably),
2. project name becomes:
   - tab label in MCC,
   - canonical playground folder name,
   - persisted metadata in registry/config,
3. fallback remains backward-compatible for old records.

---

## 2) What exists now (fact-based)

## 2.1 UI first-run
File:
- `client/src/components/mcc/FirstRunView.tsx`

Facts:
- only `workspacePath` is editable at final step.
- payload to `/api/mcc/project/init` includes:
  - `source_type`
  - `source_path`
  - `sandbox_path`
  - `quota_gb`
- no explicit `project_name`.

## 2.2 API create project
File:
- `src/api/routes/mcc_routes.py`

Facts:
- `ProjectInitRequest` has no `project_name`.
- `ProjectConfig.create_new(...)` derives `project_id` from source path + random suffix.
- for `empty` source path, backend creates temp source folder and treats as local source.

Impact:
- name quality depends on path heuristics, not user intent.

## 2.3 Persistence and registry
Files:
- `src/services/project_config.py`
- `src/services/mcc_project_registry.py`

Facts:
- `ProjectConfig` has no `display_name`.
- registry records contain:
  - `project_id`, `source_type`, `source_path`, `sandbox_path`, ...
- tabs receive registry data from `/api/mcc/projects/list`.

## 2.4 Tab shell label
File:
- `client/src/components/mcc/MyceliumCommandCenter.tsx`

Facts:
- tab text currently:
  - basename(`source_path || sandbox_path || project_id`)
- no dedicated display name field.

---

## 3) Answer to UX proposal (`name_project` in Workspace path placeholder)

Your idea is good and harmonizes with current minimal UI.

Recommended UX:
1. keep single workspace input (no extra bulky field),
2. use placeholder with explicit naming cue:
   - `/.../playgrounds/name_project`
3. add subtle helper text:
   - `Folder name becomes project name and tab title`

This keeps UI minimal and grandma-friendly, while making naming logic obvious.

---

## 4) Recon: dependent places to register project name

## 4.1 UI layer (input)
1. `FirstRunView.tsx`
   - derive `project_name` from workspace basename by default
   - optional explicit name field (compact), or hidden derivation if no extra controls desired
   - send `project_name` in `project/init` payload

## 4.2 API contract
2. `ProjectInitRequest` in `mcc_routes.py`
   - add optional `project_name: str = ""`
3. `ProjectInitResponse`
   - add `project_name: str = ""` for immediate UI hydration/debug

## 4.3 Core config model
4. `ProjectConfig` in `project_config.py`
   - add `display_name: str = ""`
5. `ProjectConfig.create_new(...)`
   - accept `project_name`
   - normalize to slug-safe folder stem
   - generate:
     - `display_name` = human-friendly name
     - `project_id` = deterministic slug + short suffix (internal key)

## 4.4 Registry persistence
6. `_project_to_record`/`_record_to_project` in `mcc_project_registry.py`
   - persist `display_name`
7. `list_projects()`
   - return `display_name`
   - if missing (legacy records), derive fallback from sandbox/source basename

## 4.5 UI tab rendering
8. `MCCProjectTab` type in `useMCCStore.ts`
   - add `display_name?: string`
9. `MyceliumCommandCenter.tsx` tab render
   - label priority:
     1) `display_name`
     2) basename(sandbox_path)
     3) basename(source_path)
     4) project_id

## 4.6 Downstream compatibility
10. services relying on `project_id` (sessions, dag versions, myco memory bridge) remain unchanged.
- no migration of identity key needed.
- only display layer and metadata enrich.

---

## 5) Migration and backward compatibility

No breaking migration needed.

Strategy:
1. add optional `display_name` to schema/records,
2. on read:
   - if absent -> fallback derivation,
3. on write:
   - always persist explicit `display_name`.

Legacy projects continue to work unchanged.

---

## 6) Risk analysis

## R1: Name collisions in tabs
- same `display_name` possible.
- Mitigation: keep internal `project_id` unique; tabs keyed by `project_id`.

## R2: Invalid filesystem chars
- Mitigation: sanitize for folder slug when used in path construction.

## R3: Empty-source naming from temp path
- Mitigation: ignore temp source basename when `source_type=empty`; prioritize:
  - explicit `project_name`, else
  - workspace basename.

## R4: UI clutter
- Mitigation: keep one input field and one subtle hint text.

---

## 7) Suggested implementation order (narrow)

1. API/model:
   - `ProjectInitRequest/Response` + `ProjectConfig.display_name`
2. Registry:
   - persist/list `display_name` with legacy fallback
3. UI:
   - workspace placeholder + helper hint
   - include `project_name` in init payload
   - tab label preference to `display_name`
4. Tests:
   - API init naming contract
   - registry list contains `display_name`
   - tab shell uses `display_name` first

---

## 8) Test matrix (minimum)

1. `tests/mcc/test_mcc_project_init_naming_contract.py`
   - init with `project_name`, verify response + config
2. `tests/mcc/test_mcc_projects_registry_api.py`
   - list returns `display_name` for new and legacy records
3. `tests/mcc/test_mcc_projects_tabs_ui_contract.py`
   - tab label derives from `display_name` first
4. run:
   - `pytest -q tests/mcc`

---

## 9) GO/NO-GO criteria

GO if:
1. new project name appears consistently in:
   - tab
   - registry
   - config
2. empty-source flow no longer leaks temp folder naming into tab title.
3. full `tests/mcc` stays green.

NO-GO if:
1. any project switch/session persistence regresses,
2. tab labels become unstable across restart.

