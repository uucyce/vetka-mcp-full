# PHASE 170 CUT Project Persistence Layout
**Date:** 2026-03-09  
**Status:** narrow persistence draft  
**Scope:** where `cut_project_v1` and adjacent bootstrap state live inside sandbox

## Goal
Зафиксировать предсказуемую persistence layout для standalone `VETKA CUT`, чтобы bootstrap/open/reopen flows не зависели от случайных файлов и не смешивались с MCC/VETKA global project files.

## Marker
- `MARKER_170.CONTRACT.CUT_PROJECT_PERSISTENCE_V1`

## Design rule
CUT project persistence is local to the CUT sandbox first.

Why:
1. sandbox must remain standalone,
2. CUT should not depend on global MCC registry for first launch,
3. future reintegration can map or import these files later.

## Recommended layout
```text
<VETKA_CUT_SANDBOX>/
├─ config/
│  ├─ cut.env.example
│  ├─ cut_core_mirror_manifest.json
│  ├─ cut_project.json
│  ├─ cut_bootstrap_state.json
│  └─ cut_projects_index.json
├─ cut_runtime/
│  ├─ jobs/
│  ├─ logs/
│  ├─ cache/
│  └─ state/
│     ├─ timeline_state.latest.json
│     ├─ scene_graph.latest.json
│     └─ bootstrap_job.latest.json
└─ cut_storage/
```

## File roles
### `config/cut_project.json`
Canonical persisted `cut_project_v1` for the sandbox's active project.

### `config/cut_bootstrap_state.json`
Last bootstrap summary:
1. last source path,
2. last bootstrap mode,
3. last quick-scan stats,
4. last degraded reason,
5. optional last bootstrap job id.

### `config/cut_projects_index.json`
Optional local index if one sandbox stores multiple CUT projects.

### `cut_runtime/state/timeline_state.latest.json`
Latest `cut_timeline_state_v1` snapshot.

### `cut_runtime/state/scene_graph.latest.json`
Latest `cut_scene_graph_v1` snapshot.

### `cut_runtime/state/bootstrap_job.latest.json`
Pointer or snapshot of most recent async bootstrap job.

## V1 rule
For first implementation:
1. `cut_project.json` is required,
2. `cut_bootstrap_state.json` is recommended,
3. `cut_projects_index.json` can stay optional,
4. runtime state files can appear later as timeline/scene contracts land.

## Relation to existing VETKA persistence
Existing patterns in `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/project_config.py:48` and `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/mcc_project_registry.py:23` are useful references, but CUT should not write into those files by default.

Rule:
- standalone CUT persists locally in sandbox,
- future bridge/import into main VETKA can be implemented separately.

## Reopen policy
`POST /api/cut/bootstrap` in `create_or_open` mode should:
1. inspect `config/cut_project.json`,
2. verify `source_path` and `sandbox_root` match request intent,
3. reopen existing project when safe,
4. create new one only when no valid persisted project exists.

## Persistence safety rules
1. never persist volatile worker progress into `cut_project.json`
2. keep bootstrap summary separate from canonical project record
3. write JSON atomically where possible
4. use absolute paths only
5. isolate by sandbox, not by repo-global singleton
