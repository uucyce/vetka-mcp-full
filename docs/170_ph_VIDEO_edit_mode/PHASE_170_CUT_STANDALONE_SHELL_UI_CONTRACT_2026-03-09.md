# PHASE 170 CUT Standalone Shell UI Contract
**Date:** 2026-03-09  
**Status:** first runtime-facing UI contract  
**Scope:** minimal standalone `VETKA CUT` shell bound only to `CUT MCP`

## Goal
Freeze the first UI-facing contract so standalone CUT can be built without coupling to main VETKA UI internals.

This contract assumes:
1. standalone shell,
2. CUT MCP only,
3. timeline-first editing,
4. optional scene graph panel.

## Marker
- `MARKER_170.UI.STANDALONE_SHELL_CONTRACT_V1`
- `MARKER_170.UI.MCP_ONLY_BINDING`
- `MARKER_170.UI.TIMELINE_BOOTSTRAP`
- `MARKER_170.UI.SCENE_GRAPH_OPTIONAL`

## Shell surfaces (V1)
1. `Launch / Open`
2. `Project Overview`
3. `Timeline Surface`
4. `Scene Graph Surface`
5. `Inspector / Questions`

## Required MCP reads
### 1. Bootstrap
- `POST /api/cut/bootstrap`
- `POST /api/cut/bootstrap-async`
- `GET /api/cut/bootstrap-job/{job_id}`

Purpose:
- create/open project,
- quick-scan folder,
- return fallback questions,
- expose initial degraded state.

### 2. Project state hydrate
- `GET /api/cut/project-state`

Purpose:
- hydrate shell from persisted sandbox state,
- recover after reload,
- decide whether timeline/graph panes should mount.

Expected UI mapping:
1. `project` -> topbar/project header
2. `bootstrap_state` -> recovery/status lane
3. `timeline_state` -> timeline surface
4. `scene_graph` -> graph surface
5. `runtime_ready` -> timeline enabled gate
6. `graph_ready` -> graph pane gate

## Required MCP writes
### 1. Timeline edit
- `POST /api/cut/timeline/apply`

V1 operations currently supported:
1. `set_selection`
2. `set_view`
3. `move_clip`
4. `trim_clip`

### 2. Scene graph edit
- `POST /api/cut/scene-graph/apply`

V1 operations currently supported:
1. `rename_node`
2. `add_note`
3. `add_edge`

## UI state model
The shell should keep a thin client state:
1. `project_state` from `GET /api/cut/project-state`
2. optimistic local selection/view state only if easily reversible
3. no duplicate source of truth for persisted timeline/graph

Rule:
server snapshot is canonical; UI cache is disposable.

## Minimal shell flow
### A. Open folder
1. user selects folder + sandbox
2. shell calls bootstrap
3. if success, shell stores `project_id`
4. shell hydrates `GET /api/cut/project-state`
5. if `runtime_ready=false`, show `Start Scene Assembly`

### B. Start assembly
1. shell calls `POST /api/cut/scene-assembly-async`
2. shell polls `GET /api/cut/job/{job_id}`
3. on `done`, shell refreshes `GET /api/cut/project-state`

### C. Edit timeline
1. drag/select/trim in UI
2. shell sends narrow `timeline/apply` op batch
3. shell replaces local timeline snapshot with returned `timeline_state`

### D. Edit graph
1. rename scene or add note/link
2. shell sends narrow `scene-graph/apply` op batch
3. shell replaces local graph snapshot with returned `scene_graph`

## V1 layout recommendation
1. left rail: project/files/questions
2. center: timeline
3. right panel: inspector
4. optional bottom/right tab: scene graph

Important:
scene graph stays secondary in V1.
Timeline is the primary editorial surface.

## V1 non-goals
1. no direct binding to main `client/src/App.tsx`
2. no coupling to current VETKA chat panes
3. no rich multiplayer state
4. no embedded worker controls beyond job status
5. no mandatory node-graph-first UX

## Failure behavior
1. if `project-state` fails, shell falls back to bootstrap/open screen
2. if `timeline/apply` fails, keep previous timeline snapshot and surface error toast/panel
3. if `scene-graph/apply` fails, keep previous graph snapshot and surface error
4. if job poll fails, show retry action without resetting project

## Next follow-up
After this contract:
1. freeze schema docs for `cut_project_state_v1`, `cut_timeline_apply_v1`, `cut_scene_graph_apply_v1`
2. update roadmap markers
3. build first standalone shell skeleton outside main VETKA UI
