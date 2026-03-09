# PHASE 170 CutProjectStore Implementation
**Date:** 2026-03-09  
**Status:** narrow implementation draft  
**Scope:** file-based persistence service for `cut_project_v1` and bootstrap-adjacent state

## Goal
`CutProjectStore` is the first persistence service for standalone `VETKA CUT`.

It should provide a minimal, reliable file-backed API for:
1. loading the active `cut_project_v1`,
2. saving the active `cut_project_v1`,
3. loading/saving bootstrap state,
4. validating reopen flow for `POST /api/cut/bootstrap`.

## Marker
- `MARKER_170.STORE.CUT_PROJECT_STORE_V1`

## Why a dedicated store
Do not wire first CUT persistence directly into MCC registry or generic project config.

Reasons:
1. CUT sandbox must remain standalone,
2. file layout is CUT-specific,
3. bootstrap/open logic should stay local and testable,
4. future bridge to main VETKA can wrap this store later.

## Canonical files
1. `config/cut_project.json`
2. `config/cut_bootstrap_state.json`
3. optional `config/cut_projects_index.json`

## Minimal API
### `load_project(sandbox_root) -> dict | None`
Loads `cut_project_v1` from `config/cut_project.json`.

### `save_project(sandbox_root, project) -> None`
Atomically writes `cut_project_v1`.

### `load_bootstrap_state(sandbox_root) -> dict | None`
Loads last bootstrap summary.

### `save_bootstrap_state(sandbox_root, state) -> None`
Writes last bootstrap summary.

### `resolve_create_or_open(sandbox_root, source_path) -> (mode, project | None)`
Used by `POST /api/cut/bootstrap` to decide whether to reopen or create.

## Validation rules
### On load
1. file exists,
2. JSON parses,
3. `schema_version` matches,
4. required roots are absolute,
5. `sandbox_root` matches actual request sandbox.

### On save
1. parent directory exists,
2. payload schema is valid enough for persistence,
3. write is atomic (`tmp -> rename`),
4. timestamps updated consistently.

## Reopen policy
`create_or_open` should reopen only if:
1. project file exists,
2. `source_path` matches requested source,
3. `sandbox_root` matches requested sandbox,
4. persisted roots are coherent.

Else:
- create a new project and overwrite stale bootstrap state.

## Bootstrap state shape
Bootstrap state is intentionally not the same as `cut_project_v1`.

Recommended contents:
1. `schema_version`
2. `project_id`
3. `last_bootstrap_mode`
4. `last_source_path`
5. `last_stats`
6. `last_degraded_reason`
7. `last_job_id`
8. `updated_at`

## First implementation split
1. `CutProjectPaths`
2. `CutProjectStore`
3. `CutBootstrapStateStore` or bootstrap methods on same class

## Pseudo-flow
```text
route -> CutBootstrapService
      -> CutProjectStore.resolve_create_or_open(...)
      -> CutProjectStore.save_project(...)
      -> CutProjectStore.save_bootstrap_state(...)
```

## Non-goals for V1
1. no database backend
2. no multi-sandbox global registry
3. no timeline state persistence in same file
4. no worker job queue logic in project store

## Testing targets
1. load missing file -> None
2. save then load roundtrip
3. stale source path prevents reopen
4. invalid schema_version rejected
5. bootstrap state saved independently from project record
