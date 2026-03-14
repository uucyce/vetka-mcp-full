# CODEX RECON — Phase 152 Codex Entry

Date: 2026-02-16
Protocol status: `RECON -> REPORT` complete. `IMPL` not started.

## Context Read
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/152_ph/PHASE_152_ROADMAP.md`

## Codex Scope (from roadmap)
Priority start (independent from backend API readiness):
- **152.7 Task Editor** (moderate, independent)
- **152.8 Task Filtering & Search** (moderate, independent)

Deferred until Opus backend readiness:
- 152.5 Stats Dashboard (needs 152.2)
- 152.6 Task Drill-Down (needs 152.2 + 152.4)
- 152.10/152.11 Dual DAG (needs 152.9)

## Current Code Reality (for narrow, safe implementation)
- Active task list UI is in `client/src/components/mcc/MCCTaskList.tsx`.
- Task updates supported by backend endpoint:
  - `PATCH /api/debug/task-board/{task_id}`
  - allowed fields: `title, description, priority, phase_type, preset, status, tags`.
- Existing `useDevPanelStore` currently stores only `activeTab`; can safely extend for filter persistence.
- Task `source` values currently seen in board data: `dragon_todo`, `titan_todo`, `mcp`, `heartbeat_titan`.

## TAKEN (reserved by Codex)
- **152.7 Task Editor**
- **152.8 Task Filtering & Search**

## Narrow Implementation Plan (after GO)
1. Add `client/src/components/panels/TaskEditor.tsx`:
   - inline edit form for `title, description, priority, tags`;
   - save via `PATCH /api/debug/task-board/{id}`;
   - source badge mapper.
2. Add `client/src/components/panels/TaskFilterBar.tsx`:
   - source/status/preset filters + keyword search + sort + show completed toggle.
3. Extend `client/src/store/useDevPanelStore.ts` for persistent filter state.
4. Integrate editor + filter pipeline into `client/src/components/mcc/MCCTaskList.tsx` (current active task list surface).
5. Verify with targeted TypeScript check on changed files.

## Explicit non-actions (per protocol)
- No code edits executed yet.
- No backend files touched.
- Waiting for user `GO` before `IMPL NARROW`.
