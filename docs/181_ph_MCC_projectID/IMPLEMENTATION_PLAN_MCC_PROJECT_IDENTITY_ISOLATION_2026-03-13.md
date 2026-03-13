# IMPLEMENTATION PLAN — MCC Project Identity Isolation

Date: 2026-03-13  
Phase: 181  
Owner: Codex

## Problem Statement

MCC currently behaves like a multi-project UI on top of a partially global backend.

Symptoms:

- tasks from different projects still collapse into one shared stream;
- `activeProjectId` is not strict enough to serve as the canonical project boundary;
- two MCC windows can show different project sets and different effective "current project";
- roadmap/DAG, task list, and active agents can drift apart;
- some project flows still act as if there is one backend-global active project;
- playground is currently overloaded as both:
  - execution substrate;
  - project identity/container.

This creates a false multi-project model:

- UI tabs suggest isolated projects;
- backend still has global behaviors;
- agents receive context from a mixed system.

## Core Diagnosis

The system is conflating 3 different layers:

1. `Project identity`
   - what project/tab the user is currently operating in
   - what codebase/workspace/roadmap/task scope belongs to that project

2. `Execution substrate`
   - where an agent is actually running
   - playground, worktree, OAuth agent session, local repo, sandbox

3. `Shared core repo`
   - common backend/taskboard/pipeline infrastructure
   - can be reused by multiple projects without making those projects identical

Today these layers are not cleanly separated.

## Target Model

Each MCC tab must become a first-class `project session boundary`.

For every MCC project tab we need a stable object:

- `project_id`
- `project_name`
- `source_type`
- `source_path`
- `workspace_path` or `sandbox_path`
- `execution_mode`
  - `oauth_agent`
  - `playground`
  - `local_workspace`
- `roadmap_snapshot_id` or project-scoped roadmap source
- `task_scope`
- `context_packet_scope`
- `session_state`

The project tab is the source of truth.

Not:

- global active project on the server
- temporary local UI focus
- whichever playground was created first

## Architectural Decision

### 1. Project identity must be explicit on every MCC request

`project_id` should become mandatory for all MCC task/DAG/session routes that operate on project-scoped state.

No hidden fallback to:

- global active project
- random fixture project
- implicit roadmap root

### 2. Project identity must be per-window, not globally singleton

If two MCC windows are open, each window must maintain its own selected tab and selected project context.

This means:

- do not rely on one backend-global `active_project_id`;
- use request-scoped `project_id`;
- optionally introduce `window_session_id` if MCC windows need persistent independent state.

Minimum rule:

- backend may store registry of projects globally;
- backend must not resolve project-scoped operations from a single global active pointer.

### 3. Project identity must be separated from playground

Playground should be optional execution infrastructure, not the definition of a project.

Valid cases:

- OAuth Codex/Claude/Cursor works on a project without a playground;
- project still has isolated DAG, task scope, and context packet;
- playground is only used when isolated writable execution is required.

Therefore:

- project identity exists independently;
- execution mode is attached to the project, not equal to it.

### 4. Project-scoped roadmap/DAG must exist independently of task board

For each project tab:

- a roadmap/DAG snapshot is loaded or generated for that project;
- tasks overlay onto that project DAG only;
- task list in MCC shows only tasks with matching `project_id`.

This prevents:

- one project showing the DAG of another;
- tasks appearing in a "fake_project" tab with a minimal placeholder graph.

## Concrete Changes

## A. Project Identity Layer

### A1. Strengthen registry contract

Current registry is useful but too soft.

Need:

- canonical `project_id`
- canonical `display_name`
- stable `source_path`
- stable `workspace_path` / `sandbox_path`
- `execution_mode`
- `roadmap_binding`
- `created_by`
- `created_at`
- `last_opened_at`

### A2. Remove implicit global active project dependency

Refactor MCC routes so project-scoped endpoints use:

- explicit `project_id` from request

instead of:

- `_load_active_project_config()` as default resolution path

except for compatibility wrappers during migration.

### A3. Add per-window MCC state identity

Recommended:

- `window_session_id` generated per MCC window
- saved in local window storage
- sent with MCC state sync requests

This prevents two windows from fighting over:

- selected tab
- nav level
- selected roadmap node
- selected task

## B. Task Isolation

### B1. Make `project_id` mandatory on all new MCC task creation paths

Applies to:

- quick-add
- create attached task
- roadmap node -> create tasks
- task duplication
- task import from project-scoped actions

### B2. Filter all MCC task reads by `project_id`

Applies to:

- task list
- mini tasks
- active agents
- task DAG
- task stats
- captain recommendations

### B3. Keep `project_lane` as branch/workstream inside a project

Important distinction:

- `project_id` = project boundary
- `project_lane` = branch/workstream/zone inside that project

This avoids using lane as a fake substitute for project identity.

## C. DAG / Architecture Isolation

### C1. Project-scoped roadmap source

Each project tab must resolve roadmap from project-bound data, not from one shared file interpreted globally.

Options:

1. per-project roadmap files
2. one store keyed by `project_id`

Recommended:

- keep a single store only if every entry is namespaced by `project_id`
- otherwise use per-project roadmap files

### C2. Auto-open new tab with isolated DAG on project creation

Desired UX:

1. user creates project `CUT`
2. MCC registry creates `project_id`
3. UI opens a new tab immediately
4. project-scoped roadmap/DAG is loaded or generated
5. empty task list is shown for that project only
6. agents created from this tab inherit that project context

### C3. Attach tasks only to visible DAG in the same project

No task should be attachable to a node that belongs to another project tab.

If user is in project `CUT`:

- only CUT DAG nodes are valid attach targets;
- only CUT tasks overlay there.

## D. Agent Context Model

### D1. Context packet must be project-scoped first

Agent packet must always include:

- `project_id`
- `project_name`
- `source_path`
- `execution_mode`
- `roadmap_binding`
- `docs`
- `task_scope`
- `lane`

### D2. OAuth agents should not require playground

For OAuth agents:

- project context packet is enough for read/plan/reason flows;
- playground/worktree only needed for isolated write execution.

### D3. Explicit ownership/provenance in UI

Show in MCC:

- `assigned_to`
- `agent_type`
- `closed_by`
- `source`
- `project_id`
- `project_lane`

This makes cross-agent coordination visible immediately.

## E. Hard Guardrails

### E1. TaskBoard mutation path policy

Policy:

- `task_board.json` is runtime-owned
- agents must not mutate it directly
- all writes go through API/MCP/TaskBoard methods

### E2. Direct-write detection

Keep current integrity signature mechanism and extend it:

- visible MCC warning banner
- analytics/audit log entry
- optional "quarantine mode" for suspicious writes

### E3. Future stronger option

Possible next step:

- move task board storage from ad-hoc JSON file semantics to an append-log or DB-backed service

This is not required immediately, but JSON should stop being treated as an editable coordination surface.

## Migration Plan

## Phase 1. Make project identity explicit everywhere

Deliverables:

- require `project_id` in MCC task/DAG routes
- stop resolving project-scoped reads from global active project
- pass `project_id` from all UI task fetch/create/update paths

Success criteria:

- opening project A does not show project B tasks
- tasks no longer fall into fixture/fake project by default

## Phase 2. Split per-window state from global registry

Deliverables:

- add `window_session_id`
- save selected tab/navigation per window
- stop cross-window tab drift

Success criteria:

- two MCC windows can remain on different project tabs without overwriting each other

## Phase 3. Project-scoped roadmap/DAG storage

Deliverables:

- roadmap source isolated per `project_id`
- auto-generate/load DAG on project creation
- task overlay always uses matching project graph

Success criteria:

- new project opens with its own DAG, not a shared/global one

## Phase 4. Separate execution mode from project identity

Deliverables:

- add `execution_mode` to project config
- allow `oauth_agent` projects without playground
- keep playground only for isolated writable/sandboxed runs

Success criteria:

- OAuth agents can participate in project context without forced playground dependency

## Phase 5. Strong coordination and attribution

Deliverables:

- hard guard against direct task board mutation
- visible attribution fields in MCC
- visible integrity warnings in UI

Success criteria:

- Claude/Codex/Cursor can see who owns what
- out-of-band board writes are detectable and surfaced

## Recommended Data Model

```json
{
  "project_id": "cut_abc123",
  "project_name": "CUT",
  "source_type": "local",
  "source_path": "/repo/cut",
  "workspace_path": "/repo/cut",
  "sandbox_path": "/data/playgrounds/cut_abc123",
  "execution_mode": "oauth_agent",
  "roadmap_id": "roadmap_cut_2026_03_13",
  "context_scope": {
    "docs": ["..."],
    "dag_version": "v12",
    "default_lane": "cut_core"
  }
}
```

Task model:

```json
{
  "id": "tb_...",
  "project_id": "cut_abc123",
  "project_lane": "cut_montage_engine",
  "roadmap_node_id": "cut_montage_engine",
  "primary_node_id": "node_...",
  "assigned_to": "codex_a",
  "agent_type": "oauth_codex",
  "closed_by": "codex_a",
  "source": "mcc_attached"
}
```

## Risks

### Risk 1. Partial migration leaves mixed behavior

If some routes remain global and others become project-scoped, confusion gets worse.

Rule:

- migrate whole read/write surfaces per slice, not one route at a time without contract update.

### Risk 2. Lane/project confusion persists

If `project_lane` continues to be used as a substitute for `project_id`, isolation will remain fragile.

Rule:

- project boundary first, lane second.

### Risk 3. Playground assumptions leak back in

If project creation still assumes playground creation, OAuth projects remain artificially constrained.

Rule:

- create project first
- choose execution mode second

## Recommended Immediate Next Task

Implement the first strict contract slice:

1. Make `project_id` mandatory in MCC task/DAG fetch routes.
2. Stop using backend-global active project as default for project-scoped reads.
3. Add per-window MCC session identity.
4. Add visible MCC banner when `integrity_warning` is present.

This is the smallest change set that turns the system from "multi-project illusion" into "actual isolated project sessions".
