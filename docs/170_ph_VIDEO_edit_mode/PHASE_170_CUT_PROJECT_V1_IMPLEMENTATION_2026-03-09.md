# PHASE 170 cut_project_v1 Implementation
**Date:** 2026-03-09  
**Status:** first implementation draft  
**Scope:** canonical CUT project object for standalone sandbox boot and future edit-mode reintegration

## Goal
`cut_project_v1` is the canonical project record for `VETKA CUT`.

It should be simple enough to create during bootstrap, but strong enough to anchor:
1. sandbox location,
2. source media location,
3. runtime profile,
4. storage namespace,
5. linkage to shared VETKA contracts.

## Marker
- `MARKER_170.CONTRACT.CUT_PROJECT_V1`

## Why not reuse existing ProjectConfig directly
Existing `ProjectConfig` in `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/project_config.py:48` is useful as precedent, but it is MCC/VETKA-oriented and not specific enough for CUT editorial runtime.

`cut_project_v1` should:
1. stay compatible with core sandbox/project ideas,
2. add CUT-specific fields,
3. avoid dragging unrelated MCC assumptions into CUT.

## Required fields
1. `schema_version`
2. `project_id`
3. `display_name`
4. `source_path`
5. `sandbox_root`
6. `core_mirror_root`
7. `runtime_root`
8. `storage_root`
9. `qdrant_namespace`
10. `created_at`
11. `bootstrap_profile`
12. `state`

## Recommended fields
1. `source_type` (`local`, `git`, `archive`)
2. `edit_mode_target` (`standalone`, `future_vetka_embed`)
3. `contracts`
4. `memory_policy`
5. `worker_topology`
6. `import_defaults`
7. `last_opened_at`
8. `notes`

## State enum
- `bootstrapping`
- `ready`
- `indexing`
- `degraded`
- `archived`

## Proposed shape
```json
{
  "schema_version": "cut_project_v1",
  "project_id": "cut_demo_1234abcd",
  "display_name": "Demo Cut",
  "source_type": "local",
  "source_path": "/absolute/path/to/source_media",
  "sandbox_root": "/absolute/path/to/VETKA_CUT_SANDBOX",
  "core_mirror_root": "/absolute/path/to/VETKA_CUT_SANDBOX/core_mirror",
  "runtime_root": "/absolute/path/to/VETKA_CUT_SANDBOX/cut_runtime",
  "storage_root": "/absolute/path/to/VETKA_CUT_SANDBOX/cut_storage",
  "qdrant_namespace": "cut_demo_1234abcd",
  "bootstrap_profile": "default",
  "edit_mode_target": "standalone",
  "state": "ready",
  "contracts": {
    "media_chunks": "media_chunks_v1",
    "montage_sheet": "vetka_montage_sheet_v1",
    "bootstrap": "cut_bootstrap_v1"
  },
  "memory_policy": {
    "engram_enabled": true,
    "cam_enabled": true,
    "elision_enabled": true,
    "namespace_mode": "sandbox_project"
  },
  "worker_topology": {
    "cut_mcp": "enabled",
    "media_worker_mcp": "enabled"
  },
  "import_defaults": {
    "quick_scan_limit": 5000,
    "use_core_mirror": true
  },
  "created_at": "2026-03-09T12:00:00Z",
  "last_opened_at": "2026-03-09T12:00:00Z",
  "notes": ""
}
```

## Mapping notes
### Maps from sandbox bootstrap
1. `sandbox_root` <- sandbox bootstrap root
2. `core_mirror_root` <- `<sandbox_root>/core_mirror`
3. `runtime_root` <- `<sandbox_root>/cut_runtime`
4. `storage_root` <- `<sandbox_root>/cut_storage`

### Maps from source selection
1. `source_type`
2. `source_path`
3. `display_name`

### Maps to shared VETKA runtime
1. `contracts.media_chunks` -> `media_chunks_v1`
2. `contracts.montage_sheet` -> `vetka_montage_sheet_v1`
3. `qdrant_namespace` -> isolated CUT collection prefix/namespace

## Narrow implementation rule
For the first code path, `cut_project_v1` should be created during `POST /api/cut/bootstrap` before advanced ingest jobs begin.

This means:
1. bootstrap can return a project immediately,
2. heavy analysis can happen after project creation,
3. project persistence is separated from worker success/failure.

## Non-goals for this version
1. no full timeline state inside `cut_project_v1`
2. no scene graph inside `cut_project_v1`
3. no embedded media_chunks payloads inside `cut_project_v1`
4. no direct storage of volatile worker progress here

## Next follow-up
After this draft:
1. freeze a JSON schema for `cut_project_v1`,
2. define persistence location,
3. define `cut_timeline_state_v1` separately,
4. define `cut_scene_graph_v1` separately.
