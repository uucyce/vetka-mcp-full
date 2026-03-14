# MCC Full Audit — 5 Haiku Scouts (2026-03-11)

## MARKER_175B.AUDIT — Consolidated Report

### Scout Coverage
| Scout | Scope | Key Finding |
|-------|-------|-------------|
| Scout 1 | Phases 120-135 | DAG foundation solid, edge labels NOT rendered, no Vetka→MCC sync |
| Scout 2 | Phases 136-150 | TRM coded but NOT integrated, JEPA coded but NOT used, roadmap = static heuristic only |
| Scout 3 | Phases 151-155 | 152.10-11 TaskDAGView NOT built, MYCO reactive only, onboarding incomplete |
| Scout 4 | Phases 156-170 | Role icons on 4/13 surfaces, all 10 templates have roles, stub roles non-canonical |
| Scout 5 | E2E flow | Roadmap→Task bridge BROKEN, Prefetch DISCONNECTED, Apply/Reject NO-OP |

---

## TIER 1 — CRITICAL GAPS (user can't complete basic workflow)

### GAP_1: Roadmap → Task Bridge BROKEN
- **Problem:** RoadmapDAG nodes are directory-structure nodes, NOT tasks
- **Evidence:** `drillDown('tasks', { roadmapNodeId })` stores navRoadmapNodeId but MCCTaskList ignores it
- **Impact:** User sees roadmap but can't create tasks FROM it
- **Fix:** Add "Create Tasks" action on roadmap node → generate subtasks for that module
- **Effort:** ~150 lines (backend + frontend)
- **MARKER:** MARKER_176.ROADMAP_TASK_BRIDGE

### GAP_2: Architect Prefetch DISCONNECTED from dispatch
- **Problem:** `ArchitectPrefetch.prepare()` exists (prefetch_files, prefetch_markers, select_workflow, select_team) but NEVER called before pipeline dispatch
- **Evidence:** `useMCCStore.dispatchTask()` → POST /dispatch → pipeline starts WITHOUT prefetch context
- **Impact:** Architect sees raw task description, no file context, no markers, no history
- **Fix:** Wire prefetch into dispatch chain: dispatchTask → prefetch → inject → pipeline
- **Effort:** ~80 lines (backend wire + frontend pre-dispatch UI)
- **MARKER:** MARKER_176.PREFETCH_WIRE

### GAP_3: Results Apply/Reject handlers are NO-OP
- **Problem:** RailsActionBar at `results` level has Apply/Reject buttons but handlers do nothing
- **Evidence:** MyceliumCommandCenter.tsx — `onApply()` and `onReject()` callbacks not wired
- **Impact:** User can't approve or reject pipeline results
- **Fix:** Wire apply → update task.result_status + save to sandbox; reject → requeue with feedback
- **Effort:** ~60 lines
- **MARKER:** MARKER_176.RESULT_HANDLERS

### GAP_4: TRM NOT integrated into DAG builder
- **Problem:** `mcc_trm_config.py` + `mcc_trm_adapter.py` coded (Phase 161) but output IGNORED
- **Evidence:** `resolve_trm_policy()` returns policy → policy NOT passed to `build_design_dag()`
- **Impact:** DAG is always baseline, never TRM-refined
- **Fix:** Call `mcc_trm_adapter.adapt_candidates()` in build_design_dag, add source badge
- **Effort:** ~40 lines backend + ~20 lines UI badge
- **MARKER:** MARKER_176.TRM_INTEGRATION

### GAP_5: JEPA NOT participating in project creation
- **Problem:** `mcc_jepa_adapter.py` (Phase 155) coded but NO usage site
- **Evidence:** Adapter provides embeddings for similarity, but roadmap_generator.py is pure heuristic
- **Impact:** Roadmap generation misses logical architecture (auth across api+middleware)
- **Fix:** After static scan, call JEPA for semantic clustering → refine roadmap
- **Effort:** ~100 lines
- **MARKER:** MARKER_176.JEPA_ROADMAP

---

## TIER 2 — HIGH (system works but UX broken)

### GAP_6: Group Chat → MCC Task Board sync incomplete
- **Problem:** @dragon commands in VETKA group chat DON'T appear in MCC task board
- **Evidence:** `_dispatch_system_command()` creates mycelium pipeline task but doesn't add to task_board.json
- **Impact:** Tasks from Vetka group chat invisible in MCC
- **Fix:** Add `board.add_task()` call in group_message_handler with source_chat_id
- **Effort:** ~30 lines
- **MARKER:** MARKER_176.GROUP_SYNC

### GAP_7: DAG edge labels NOT rendered
- **Problem:** Edge types defined (structural, dataflow, temporal, conditional, etc.) but NO visual labels
- **Evidence:** dagre `g.setEdge(source, target)` with empty label; no label component in ReactFlow
- **Impact:** User can't see input/output matrix connections between nodes
- **Fix:** Add edge label renderer + input_matrix data on edges
- **Effort:** ~80 lines
- **MARKER:** MARKER_176.EDGE_LABELS

### GAP_8: DAG execution NOT wired to user workflows
- **Problem:** User can create/edit workflow DAGs but execution still uses hard-coded sequential pipeline
- **Evidence:** Phase 144 DAG editor creates visual structure; pipeline ignores it, runs Scout→Architect→Coder→Verifier
- **Impact:** Custom workflows are visual-only, can't execute
- **Fix:** Parse workflow template → dispatch agents per node topology
- **Effort:** ~200 lines (major feature)
- **MARKER:** MARKER_176.DAG_EXECUTION

### GAP_9: MYCO has NO proactive guidance
- **Problem:** MYCO only responds to explicit `/myco` trigger; doesn't suggest help unprompted
- **Evidence:** `isMycoTrigger(message)` checks for `/myco`, `/help myco`, `?` prefixes only
- **Impact:** New users don't get contextual guidance at each navigation level
- **Fix:** Add level-specific hints system: roadmap→"click node to drill", tasks→"select or add", etc.
- **Effort:** ~100 lines
- **MARKER:** MARKER_176.MYCO_PROACTIVE

### GAP_10: 152.10-11 TaskDAGView NOT built
- **Problem:** Backend `/api/analytics/dag/tasks` endpoint exists, frontend component MISSING
- **Evidence:** No TaskDAGView.tsx in codebase
- **Impact:** Users can't see task dependency graph (only see individual workflow DAGs)
- **Fix:** Build TaskDAGView.tsx (~250 lines) + dual DAG toggle (~60 lines)
- **Effort:** ~310 lines
- **MARKER:** MARKER_176.TASK_DAG_VIEW

---

## TIER 3 — MEDIUM (polish & consistency)

### GAP_11: Role icons on 4/13 MCC surfaces
| Surface | Icons? | Priority |
|---------|--------|----------|
| AgentNode | ✅ | — |
| PipelineStats | ✅ | — |
| StatsDashboard | ✅ | — |
| TaskDrillDown | ✅ | — |
| NodeStreamView | ❌ | Medium |
| MiniTasks | ❌ | Low |
| RoadmapTaskNode | ❌ | Medium (show lead role) |
| CaptainBar | ❌ | Low (action bar) |
| FooterActionBar | ❌ | Low (action bar) |
| TaskEditPopup | ❌ | Low |

### GAP_12: Stub workflow templates use non-canonical roles
- openhands_collab_stub: "critic", "deploy", "approval" not in MycoRolePreviewRole
- pulse_scheduler_stub: "planner", "scheduler" not in MycoRolePreviewRole
- **Fix:** Expand MycoRolePreviewRole or map to canonical roles
- **Effort:** ~20 lines
- **MARKER:** MARKER_176.CANONICAL_ROLES

### GAP_13: No task drag-reorder in UI
- `changePriority()` exists in store but no drag UI
- **Effort:** ~60 lines with react-dnd or xyflow drag

### GAP_14: No pre-dispatch cost estimation
- prefetch context should estimate tokens/cost before launch
- **Effort:** ~40 lines

---

## WHAT'S ACTUALLY DONE ✅

| Feature | Status | Phase |
|---------|--------|-------|
| DAG Visualization (grayscale, Sugiyama layout) | ✅ | 135 |
| 9 Node Types (task, agent, subtask, condition, parallel, loop, transform, group, proposal) | ✅ | 135-144 |
| 7 Edge Types (structural, dataflow, temporal, conditional, parallel_fork/join, feedback) | ✅ | 135-144 |
| Workflow Editor (CRUD, undo/redo, validation) | ✅ | 144 |
| Matryoshka Navigation (6 levels) | ✅ | 154 |
| Task Board (CRUD, dispatch, status) | ✅ | 153 |
| MCC Backend Routes (project init, roadmap, state, sandbox) | ✅ | 153 |
| Roadmap Generator (static heuristic) | ✅ | 153-155 |
| Per-Agent Stats (backend + frontend) | ✅ | 151 |
| Stats Dashboard (Recharts) | ✅ | 152 |
| Task Drill-Down Modal | ✅ | 152 |
| Workflow Family Selector | ✅ | 175B |
| Role Avatars (4 surfaces) | ✅ | 175 |
| Asset Compression (28x WebP) | ✅ | 175 |
| showReflexInsight Toggle | ✅ | 174 |
| 10 Workflow Templates (all with roles) | ✅ | 153-155 |
| MiniWindows (Chat, Tasks, Stats, Balance) | ✅ | 154 |
| FirstRunView (3 options) | ✅ | 154 |
| Onboarding (4-step spotlight) | ✅ | 151 |
| TRM Config + Adapter (coded, not integrated) | ⚠️ | 161 |
| JEPA Adapter (coded, not integrated) | ⚠️ | 155 |

---

## Priority Roadmap for Phase 176 MCC

### Sprint 1 (Critical Path — 4-6 hours)
1. **Roadmap→Task Bridge** (GAP_1) — 150 lines
2. **Prefetch Wire** (GAP_2) — 80 lines
3. **Result Apply/Reject** (GAP_3) — 60 lines

### Sprint 2 (Intelligence Layer — 4-6 hours)
4. **TRM Integration** (GAP_4) — 60 lines
5. **Group→MCC Sync** (GAP_6) — 30 lines
6. **Edge Labels** (GAP_7) — 80 lines

### Sprint 3 (UX Complete — 6-8 hours)
7. **JEPA Roadmap** (GAP_5) — 100 lines
8. **MYCO Proactive** (GAP_9) — 100 lines
9. **TaskDAGView** (GAP_10) — 310 lines
10. **DAG Execution** (GAP_8) — 200 lines (major)

### Deferred
- Role icons on remaining surfaces (GAP_11)
- Canonical roles for stubs (GAP_12)
- Task drag-reorder (GAP_13)
- Cost estimation (GAP_14)
- Tauri packaging (Phase 176 packaging)

## Codex B Observations

- `NavLevel` now enumerates six levels (`first_run` → `roadmap` → `tasks` → `workflow` → `running` → `results`) inside `client/src/store/useMCCStore.ts`, but on the MCC surface we presently observe only the aggregated roadmap view and the modal task drill-down; the deeper node-by-node connections that are claimed in the audit still need a node-specific context pane.
- When a roadmap node is clicked, the current UI surfaces only the shared high-level DAG (`MyceliumCommandCenter` / `TaskDrillDown` show general stats) instead of exposing the full JEPA+LLM+TRM connections for that node; `client/src/components/analytics/TaskDrillDown.tsx` already fetches per-task analytics, so the missing step is wiring the task selector to pass the clicked node's task_id along with the contextual breadcrumbs.
- The expectation to see "maximum necessary connections" per node is partially met: clicking a task already opens the drill-down modal, but it renders the same edge set that the overall DAG already shows (`client/src/components/mcc/TaskDAGView.tsx` does not yet exist), so we need to augment that modal with the additional context (TRM policy outputs, JEPA cluster hints, and related files from the prefetch matrix) rather than trying to create a new standalone view.
