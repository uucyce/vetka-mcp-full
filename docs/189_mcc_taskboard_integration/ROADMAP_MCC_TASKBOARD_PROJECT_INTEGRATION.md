# MCC TaskBoard Project Integration Roadmap

**Phase:** 189  
**Status:** Draft (needs Opus 4.6 review)  
**Created:** 2026-03-17  
**Owner:** MCC integration

---

## Problem Statement

- MiniTasks in MCC shows empty because tasks don't have `project_id`
- Tasks created by MCP agents (Claude Code, Codex, Localguys) have no project binding
- Need unified view of all agent tasks in MCC command center
- Must NOT break existing task workflow

---

## Goals

1. **Preserve existing tasks** — don't break current flow
2. **Add project binding** — without manual entry
3. **Auto-suggest projects** — from registered projects
4. **Create new projects** — via MCC if needed
5. **Show in MCC** — all tasks with project labels

---

## Architecture

### Current State (DO NOT BREAK)

```
TaskBoard (no project_id) ──► MiniTasks ──► Empty (filters by project)
```

### Target State

```
TaskBoard ──► project_id ──► MiniTasks ──► Grouped by project
                  │
                  ├── Auto-complete from mcc_projects_registry.json
                  │
                  └── If no match ──► Prompt user to create in MCC
```

---

## Implementation Plan

### Phase 1: Add project_id to Task Creation

**Task:** `tb_18901_add_project_id_param`

**Files:**
- `src/api/routes/debug_routes.py` — add `project_id` param to `/task-board/add`
- `src/orchestration/task_board.py` — ensure `project_id` stored

**API Change:**
```python
# POST /api/task-board/add
{
  "title": "...",
  "project_id": "vetka_live_03",  # NEW: auto-complete from registry
  ...
}
```

### Phase 2: Auto-complete Project List

**Task:** `tb_18902_project_autocomplete`

**Files:**
- `src/api/routes/debug_routes.py` — add `/task-board/projects` endpoint
- `src/services/mcc_project_registry.py` — reuse existing

**API:**
```python
GET /api/task-board/projects
# Returns: ["vetka_live_03", "mcc_playwright_...", ...]
```

### Phase 3: MiniTasks Project Display

**Task:** `tb_18903_minitasks_show_project`

**Files:**
- `client/src/components/mcc/MiniTasks.tsx` — show project badge per task
- `client/src/store/useMCCStore.ts` — pass project_id to MiniTasks

**UI:**
```
[Claude Code] 🔵 vetka_live_03 | tb_xxx | title...
[Localguys]   � eco vetka_live_03 | tb_xxx | title...
[Codex]       ⚪ vetka_live_03 | tb_xxx | title...
```

### Phase 4: "Assign Projects" Button

**Task:** `tb_18904_assign_projects_button`

**Files:**
- `MiniTasks.tsx` — add "Assign Projects" button
- `debug_routes.py` — add batch update endpoint

**UI Flow:**
1. Click "Assign Projects"
2. Modal shows: unmapped tasks | registered projects
3. Select project → auto-assign to all
4. Or: "Create New Project" → opens MCC project creation

### Phase 5: Create Project from Task Context

**Task:** `tb_18905_create_project_from_task`

**Files:**
- `src/services/mcc_project_registry.py` — add create method
- `client/src/components/mcc/MyceliumCommandCenter.tsx` — project creation modal

**Flow:**
1. Agent tries to create task with unknown project_id
2. MCC prompts: "Project 'xyz' not found. Create?"
3. User confirms → project created with template from current repo
4. Task automatically assigned to new project

### Phase 6: All Tasks View (Toggle)

**Task:** `tb_18906_all_tasks_toggle`

**Files:**
- `useMCCStore.ts` — add `showAllProjects: boolean`
- `MiniTasks.tsx` — toggle between filtered/all

**UI:**
```
[▼ vetka_live_03] [All Projects ✓]
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Break existing tasks | Always use optional project_id, default to empty |
| TaskBoard corruption | Backup before batch updates |
| User confusion | Clear UI labels: "No project" vs "All projects" |
| Agent chaos | agent_type field already exists, use for grouping |

---

## Dependencies

- Existing: `data/mcc_projects_registry.json` ✅
- Existing: `src/services/mcc_project_registry.py` ✅
- Existing: `MiniTasks.tsx` ✅
- Existing: `task_board.py` ✅

---

## Acceptance Criteria

- [ ] Tasks without project_id still work (backward compat)
- [ ] New tasks can specify project_id
- [ ] MiniTasks shows tasks grouped by project
- [ ] "Assign Projects" button works
- [ ] Can create new project from task context
- [ ] All existing tests pass

---

## Questions for Opus 4.6 Review

1. Is this approach safe for existing TaskBoard?
2. Should we use `project_id` or `project_lane` as primary?
3. How to handle tasks from different worktrees (Codex, etc.)?
4. Should Localguys tasks have separate project or same as main?

---

## References

- Research: `docs/189_mcc_taskboard_integration/MCC_TASKBOARD_INTEGRATION_RECON_2026-03-17.md`
- Projects: `data/mcc_projects_registry.json`
- Backend: `src/orchestration/task_board.py`
- API: `src/api/routes/debug_routes.py`
- UI: `client/src/components/mcc/MiniTasks.tsx`
