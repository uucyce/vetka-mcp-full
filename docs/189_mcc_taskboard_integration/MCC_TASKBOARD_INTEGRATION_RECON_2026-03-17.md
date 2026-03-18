# MCC ↔ TaskBoard Integration Research (2026-03-17)

## Current State

### 1. Projects System — ✅ EXISTS
- **Registry:** `data/mcc_projects_registry.json`
- **Current projects:**
  - `vetka_live_03` (active)
  - `mcc_playwright_graph_fixture_fee6f866`
  - `temp_4b58ad29`
- **Backend:** `src/services/mcc_project_registry.py`

### 2. TaskBoard — ✅ EXISTS
- **Backend:** `src/orchestration/task_board.py`
- **API:** `src/api/routes/debug_routes.py:1803+`
- **Fields per task:**
  - `project_id` (optional)
  - `project_lane` (optional)
  - `roadmap_id`, `roadmap_node_id`, `roadmap_lane`
  - `assigned_to`, `agent_type`

### 3. Task Filtering — ✅ WORKS
- `GET /api/debug/task-board?project_id=xxx` filters by:
  - `project_id` OR `roadmap_id`
- If no `project_id` → returns ALL tasks

### 4. Frontend — MiniTasks ⚠️
- **Component:** `MiniTasks.tsx` (renders in MCC)
- **Fetching:** `fetchTasks()` calls `/api/debug/task-board?project_id=...`
- **Issue:** Empty because tasks don't have `project_id`

### 5. Task Creation — ❌ GAP
Tasks created by MCP (via `vetka_task_board` tool) **don't assign project_id**.

**How tasks are created:**
1. Via MCP tool `mycelium_task_board action=add`
2. Via API `/api/task-board/add`
3. Via heartbeat (`mycelium_heartbeat.py`)

**Problem:** `add_task_api` (debug_routes.py:2212) doesn't pass `project_id` to board.add_task().

---

## The Gap

### Issue 1: Tasks Have No Project
- Tasks created by agents (Claude Code, MCP, etc.) have no `project_id`
- MiniTasks filters by active project → returns empty
- We need to **assign existing tasks to projects**

### Issue 2: No Global View
- With project filter → only tasks for that project
- Without filter → ALL tasks (but UI doesn't support this well)

### Issue 3: Multi-Agent Context
- Claude Code: works in worktree, creates tasks
- Opus (Codex): same
- MCP agents: create tasks via heartbeat
- Localguys: will create tasks
- **Need unified view of ALL agents' tasks**

---

## Proposed Solutions

### Option A: Auto-assign project_id to existing tasks
1. Add batch endpoint to assign `project_id` to existing tasks
2. Map: `roadmap_id` → `project_id`
3. Example: "MCC" roadmap → `vetka_live_03` project

### Option B: Create "All Tasks" view in MCC
1. Add toggle: "Show all projects" in MiniTasks
2. When activeProjectId is empty → fetch without filter

### Option C: Task Creation + Project Binding
1. When creating task from MCC → auto-assign activeProjectId
2. When creating from MCP → extract project from context

### Option D: Agent-based grouping
1. Group by `assigned_to` or `agent_type` instead of project
2. Show: "Claude Code tasks", "MCP tasks", "Localguys tasks"

---

## Key Questions for Grok

1. What's the best way to group tasks in MCC?
   - By project (current)
   - By agent (assigned_to)
   - By roadmap
   - By phase/type

2. How should we handle tasks created by different agents?
   - Auto-assign based on agent type?
   - Let user manually assign?

3. Should we have "All Tasks" view + per-project views?

4. How to map existing tasks to projects?
   - Use roadmap_id as hint
   - Use tags
   - Manual assignment

---

## Files to Touch

| File | Change |
|------|--------|
| `src/api/routes/debug_routes.py` | Add project_id to add_task |
| `client/src/store/useMCCStore.ts` | Add "all projects" toggle |
| `client/src/components/mcc/MiniTasks.tsx` | Show project label per task |
| `src/orchestration/task_board.py` | Add batch update method |

---

## References

- Projects registry: `data/mcc_projects_registry.json`
- TaskBoard: `src/orchestration/task_board.py:611+`
- API: `src/api/routes/debug_routes.py:1803+`
- Frontend fetch: `useMCCStore.ts:615+`
- MiniTasks: `MiniTasks.tsx:177+`
