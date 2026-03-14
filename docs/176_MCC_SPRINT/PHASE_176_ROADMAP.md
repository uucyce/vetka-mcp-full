# Phase 176 — MCC Sprint: Close All Gaps

> **Source:** `docs/175_MCC_APP/SCOUT_MCC_AUDIT_2026-03-11.md` (14 gaps) + Opus recon (10 new gaps)
> **Total:** 24 gaps, ~1770 lines, 3 sprints
> **Methodology:** Parallel execution with markers. Tests at every sprint boundary.

---

## ⚠️ CRITICAL: Command Structure (corrected 2026-03-11)

**MCC CANNOT BUILD ITSELF.** Dragons/Ralph/G3 run inside `agent_pipeline.py` — the same
code we're fixing. Using pipeline to fix pipeline = circular dependency.

| Unit | Tool | Sprint 1 Role | When to Use |
|------|------|---------------|-------------|
| **Haiku Scouts** | Agent(Explore) | Recon, markers, task board audit | Always safe, read-only |
| **Sonnet Engineers** | Agent(general-purpose) | Backend code changes (GAP 1B,2,3B,4,5,6) | Surgical edits with context |
| **Codex** | External worktree | Frontend (GAP 7,15,18,1F,3F) | UI components, store |
| **Grok** | vetka_call_model direct | Research questions, divergent analysis | No pipeline needed |
| **Opus** | Architecture + review | Briefs, memory, synthesis, final review | Conserve context |
| **Dragons/Ralph/G3** | mycelium_pipeline | **ONLY in sandbox** for external projects | After MCC is stable |

### Future: MCC Self-Improvement via Sandbox
When MCC is stable → `mycelium_playground_create` → Dragons build "MCC 2.0" in
isolated worktree → tests pass → merge to main. Never direct self-modification.

---

## Dependency Graph

```
SPRINT 1A (Backend — Sonnet engineers)           SPRINT 1B (Frontend — Codex, parallel)
┌─────────────────────────────────────┐          ┌──────────────────────────────────────┐
│ GAP_2:  Prefetch Wire        (80L)  │          │ GAP_15: API_BASE Config       (30L)  │
│ GAP_4:  TRM → DAG            (60L)  │          │ GAP_7:  Edge Labels           (80L)  │
│ GAP_5:  JEPA → Roadmap      (100L)  │          │ GAP_18: FirstRunView Errors   (50L)  │
│ GAP_6:  Group→MCC Sync       (30L)  │          │ GAP_1F: Roadmap→Task UI       (80L)  │
│ GAP_1B: Roadmap→Task Backend (70L)  │          │ GAP_3F: Apply/Reject UI       (40L)  │
│ GAP_3B: Apply/Reject Backend (30L)  │          └──────────────────────────────────────┘
└─────────────────────────────────────┘                        │
              │                                                │
              ▼                                                ▼
         SPRINT 1 TESTS (Backend pytest + Frontend build + User Scenario Tests)
              │
              ▼
SPRINT 2A (Backend — Sonnet engineer)            SPRINT 2B (Frontend — Codex)
┌─────────────────────────────────────┐          ┌──────────────────────────────────────┐
│ GAP_8:  DAG Execution       (200L)  │          │ GAP_9:  MYCO Proactive       (100L)  │
│   depends on: GAP_2, GAP_4          │          │ GAP_10: TaskDAGView          (310L)  │
└─────────────────────────────────────┘          │ GAP_16: MiniStats Real Data   (40L)  │
                                                 │ GAP_19: MiniChat Contract     (30L)  │
                                                 └──────────────────────────────────────┘
              │                                                │
              ▼                                                ▼
         SPRINT 2 TESTS (Integration + E2E User Scenarios)
              │
              ▼
SPRINT 3 (Polish — Codex + Low-priority Dragons)
┌─────────────────────────────────────────────────────────────────┐
│ GAP_11: Role Icons (9 surfaces)                          (90L) │
│ GAP_12: Canonical Roles                                  (20L) │
│ GAP_13: Task Drag-Reorder                                (60L) │
│ GAP_14: Cost Estimation                                  (40L) │
│ GAP_17: PipelineResultsViewer Retry                      (60L) │
│ GAP_21: Offline State Detection                          (80L) │
│ GAP_22: MiniWindow Namespace                             (20L) │
│ GAP_23: DAGView Test Data Guard                          (15L) │
│ GAP_24: MiniChat "/" Shortcut                            (25L) │
└─────────────────────────────────────────────────────────────────┘
```

---

## Sprint 1: Critical Path (Parallel)

**Goal:** User can: create tasks from roadmap → dispatch with prefetch → see results → apply/reject.

### Sprint 1A — Backend (Dragons, 6 parallel tasks)

| # | GAP | Marker | Files | Lines | Dragon Tier | Parallel? |
|---|-----|--------|-------|-------|-------------|-----------|
| 1 | GAP_1B | `MARKER_176.1B` | `mcc_routes.py`, `roadmap_generator.py` | 70 | Silver | ✅ Yes |
| 2 | GAP_2 | `MARKER_176.2` | `agent_pipeline.py`, `architect_prefetch.py` | 80 | Silver | ✅ Yes |
| 3 | GAP_3B | `MARKER_176.3B` | `mcc_routes.py`, `task_board.py` | 30 | Bronze | ✅ Yes |
| 4 | GAP_4 | `MARKER_176.4` | `mcc_trm_adapter.py`, design DAG builder | 60 | Silver | ✅ Yes |
| 5 | GAP_5 | `MARKER_176.5` | `mcc_jepa_adapter.py`, `roadmap_generator.py` | 100 | Silver | ✅ Yes |
| 6 | GAP_6 | `MARKER_176.6` | `group_message_handler.py` | 30 | Bronze | ✅ Yes |

**Total Sprint 1A:** 370 lines, ALL parallel (different files, no conflicts).

**Dragon dispatch strategy:**
- GAP_4 + GAP_5 → Dragon Silver (intelligence layer, medium complexity)
- GAP_2 → Dragon Silver (pipeline wiring, needs understanding of flow)
- GAP_1B + GAP_3B + GAP_6 → Dragon Bronze (simple endpoint additions)

### Sprint 1B — Frontend (Codex, 5 parallel tasks)

| # | GAP | Marker | Files | Lines | Parallel? |
|---|-----|--------|-------|-------|-----------|
| 1 | GAP_15 | `MARKER_176.15` | NEW `api.config.ts` + 10 imports | 30 | ✅ Yes |
| 2 | GAP_7 | `MARKER_176.7` | `DAGView.tsx`, edge components | 80 | ✅ Yes |
| 3 | GAP_18 | `MARKER_176.18` | `FirstRunView.tsx` | 50 | ✅ Yes |
| 4 | GAP_1F | `MARKER_176.1F` | `RoadmapTaskNode.tsx`, `useMCCStore.ts` | 80 | ⚠️ After GAP_1B API ready |
| 5 | GAP_3F | `MARKER_176.3F` | `MyceliumCommandCenter.tsx` | 40 | ⚠️ After GAP_3B API ready |

**Total Sprint 1B:** 280 lines. GAP_15/7/18 start immediately. GAP_1F/3F wait for backend APIs.

### Sprint 1 Tests

```
# Backend (pytest)
MARKER_176.T1: test_roadmap_create_tasks — POST /api/mcc/roadmap/{node_id}/create-tasks
MARKER_176.T2: test_prefetch_called_before_dispatch — dispatchTask() → prefetch → pipeline
MARKER_176.T3: test_apply_updates_task_status — POST /api/mcc/tasks/{id}/apply
MARKER_176.T4: test_reject_requeues_task — POST /api/mcc/tasks/{id}/reject
MARKER_176.T5: test_trm_policy_in_dag — TRM output used in build_design_dag()
MARKER_176.T6: test_jepa_clustering_in_roadmap — JEPA embeddings in roadmap generation
MARKER_176.T7: test_group_task_appears_in_mcc — @dragon task → task_board.json

# Frontend (build + user scenarios)
MARKER_176.T8: Vite build passes (both VETKA + MCC targets)
MARKER_176.T9: User Scenario — "Create project → see roadmap → click node → create tasks"
MARKER_176.T10: User Scenario — "Edit task → select workflow → dispatch → apply result"
MARKER_176.T11: Edge labels visible on DAG with correct type names
```

---

## Sprint 2: Intelligence + UX (After Sprint 1)

### Sprint 2A — Backend (Sonnet engineer, 1 major task)

| # | GAP | Marker | Files | Lines | Depends on |
|---|-----|--------|-------|-------|------------|
| 1 | GAP_8 | `MARKER_176.8` | `agent_pipeline.py`, `workflow_executor.py` (NEW) | 200 | GAP_2, GAP_4 |

**Why Sonnet?** DAG Execution modifies `agent_pipeline.py` — the core of MCC pipeline. Using Dragons to edit this file = circular dependency. Sonnet engineer reads full context, makes surgical changes with markers. Brief: `docs/176_MCC_SPRINT/DRAGON_GOLD_BRIEF_SPRINT2.md` (renamed but spec still valid for Sonnet).

### Sprint 2B — Frontend (Codex, 4 tasks)

| # | GAP | Marker | Files | Lines | Depends on |
|---|-----|--------|-------|-------|------------|
| 1 | GAP_9 | `MARKER_176.9` | `MycoHints.tsx` (NEW), `useMCCStore.ts` | 100 | None |
| 2 | GAP_10 | `MARKER_176.10` | `TaskDAGView.tsx` (NEW) | 310 | GAP_7 edge labels |
| 3 | GAP_16 | `MARKER_176.16` | `MiniStats.tsx` | 40 | None |
| 4 | GAP_19 | `MARKER_176.19` | `MiniChat.tsx` | 30 | None |

**Total Sprint 2:** 680 lines. Backend (200) + Frontend (480).

### Sprint 2 Tests

```
MARKER_176.T12: test_dag_execution_follows_topology — workflow template → agent dispatch order
MARKER_176.T13: test_dag_parallel_fork_join — parallel nodes dispatched concurrently
MARKER_176.T14: User Scenario — "MYCO shows hint when entering roadmap level"
MARKER_176.T15: User Scenario — "TaskDAGView shows task dependencies with edge labels"
MARKER_176.T16: User Scenario — "Custom workflow dispatches in correct topology order"
MARKER_176.T17: MiniStats shows real data (not placeholders) or "No data" state
```

---

## Sprint 3: Polish (After Sprint 2)

### Sprint 3A — Frontend (Codex)

| # | GAP | Marker | Files | Lines |
|---|-----|--------|-------|-------|
| 1 | GAP_11 | `MARKER_176.11` | 9 MCC surfaces | 90 |
| 2 | GAP_12 | `MARKER_176.12` | `mycoRolePreview.ts` | 20 |
| 3 | GAP_13 | `MARKER_176.13` | `MCCTaskList.tsx` | 60 |
| 4 | GAP_17 | `MARKER_176.17` | `PipelineResultsViewer.tsx` | 60 |
| 5 | GAP_21 | `MARKER_176.21` | `useOnlineStatus.ts` (NEW) + 3 components | 80 |
| 6 | GAP_22 | `MARKER_176.22` | `MiniWindow.tsx` | 20 |
| 7 | GAP_23 | `MARKER_176.23` | `DAGView.tsx` | 15 |
| 8 | GAP_24 | `MARKER_176.24` | Global keydown listener | 25 |

### Sprint 3B — Backend (Sonnet engineer)

| # | GAP | Marker | Files | Lines |
|---|-----|--------|-------|-------|
| 1 | GAP_14 | `MARKER_176.14` | `architect_prefetch.py` | 40 |

**Total Sprint 3:** 410 lines polish.

### Sprint 3 Tests

```
MARKER_176.T18: Role icons visible on all 13 MCC surfaces
MARKER_176.T19: "/" shortcut opens MiniChat focus
MARKER_176.T20: Offline banner appears when navigator.onLine = false
MARKER_176.T21: MiniWindow positions scoped per project_id
MARKER_176.T22: Full E2E — Create project → roadmap → tasks → dispatch → apply → done
```

---

## Summary

| Sprint | Backend | Frontend | Total Lines | Time Est |
|--------|---------|----------|-------------|----------|
| **1** | 370 (6 Sonnet tasks) | 280 (5 Codex tasks) | **650** | 4-6h |
| **2** | 200 (1 Sonnet major) | 480 (4 Codex tasks) | **680** | 6-8h |
| **3** | 40 (1 Sonnet) | 370 (8 Codex tasks) | **410** | 3-4h |
| **Total** | **610** | **1130** | **1740** | ~16h |

## Agent Assignment (Corrected 2026-03-11)

| Agent | Role | Sprint 1 | Sprint 2 | Sprint 3 |
|-------|------|----------|----------|----------|
| **Opus** | Architect | Briefs, review, memory, test design | Review Sonnet output, architecture | Final integration |
| **Codex** | Frontend | GAP 15,7,18,1F,3F | GAP 9,10,16,19 | GAP 11-13,17,21-24 |
| **Sonnet Engineers** | Backend | GAP 1B,2,3B,4,5,6 (surgical edits) | GAP 8 (major) | GAP 14 |
| **Haiku Scouts** | Recon | Task board audit, file checks | Verify Sprint 1 markers | Regression checks |
| **Grok** | Research | Direct call for divergent questions | Architecture analysis | — |
| **Dragons/Ralph/G3** | **RESERVED** | — (not used on MCC self) | — | Future: sandbox only |

### Why NOT Dragons for MCC?
Dragons execute via `agent_pipeline.py` — the same file we're patching (GAP_2, GAP_8).
Using the pipeline to fix the pipeline = circular dependency. When MCC has a sandbox
(playground worktree with test harness), Dragons CAN build "MCC 2.0" there.

## File Coordination (No Conflicts)

| File | Sprint 1A (Sonnet) | Sprint 1B (Codex) | Sprint 2 |
|------|--------------------|--------------------|----------|
| `mcc_routes.py` | GAP_1B, GAP_3B | — | — |
| `agent_pipeline.py` | GAP_2 | — | GAP_8 (sequential) |
| `roadmap_generator.py` | GAP_1B, GAP_5 | — | — |
| `group_message_handler.py` | GAP_6 | — | — |
| `mcc_trm_adapter.py` | GAP_4 | — | — |
| `mcc_jepa_adapter.py` | GAP_5 | — | — |
| `DAGView.tsx` | — | GAP_7 | — |
| `MyceliumCommandCenter.tsx` | — | GAP_3F | — |
| `FirstRunView.tsx` | — | GAP_18 | — |
| `useMCCStore.ts` | — | GAP_1F | GAP_9 (sequential) |

**Conflict avoidance:** Sprint 1A backend and Sprint 1B frontend touch ZERO shared files.
Sprint 2A (GAP_8 touches agent_pipeline.py) runs AFTER Sprint 1A GAP_2 is complete.
