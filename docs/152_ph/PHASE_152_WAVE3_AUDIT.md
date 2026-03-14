# Phase 152 Wave 3 — MCC UX Audit + Task Plan

**Date:** 2026-02-16
**Agents:** Opus (architecture + backend), Codex (frontend)
**Status:** READY FOR EXECUTION

---

## Part 1: Gap Analysis (Current State vs Grok Design)

### 🔴 Critical Gaps

| # | Grok Rule | Current State | Gap |
|---|-----------|--------------|-----|
| G1 | **Panel = Zoom**: every panel has compact (in right column) + expanded (as DevPanel tab). Same component, `mode` prop, shared Zustand state | ArchitectChat ✅ works (compact in MCCDetailPanel, expanded in DevPanel ARCHITECT tab, ↗/↙ button). PipelineStats ✅ works (compact in MCCDetailPanel, expanded via StatsDashboard). **BUT**: PipelineStats compact and StatsDashboard expanded are DIFFERENT components with DIFFERENT data paths (client-side vs server REST API) | **PipelineStats/StatsDashboard are TWO separate components** — violates "same component, mode prop" rule. Need to unify or accept the split |
| G2 | **Dual DAG**: Task DAG (roadmap) + Workflow DAG (per-task). Click task node → drill into workflow | Only Workflow DAG exists. No Task DAG view. Backend ready (`/api/analytics/dag/tasks` + mini_stats) but **zero frontend** | **152.10-152.11 not built**. Codex task |
| G3 | **No unnecessary buttons**: every control answers WHO/WHERE/WHEN. If it doesn't → remove | WorkflowToolbar has 11 buttons always visible in edit mode. **Validate** shows on empty workflows. **Generate** can overwrite loaded workflow. **Save/Generate** use browser `prompt()` dialog breaking Nolan aesthetic | Toolbar needs contextual visibility + custom inputs |
| G4 | **Execute always visible** in header even with no workflow loaded | Execute button clickable with no workflow → shows error message reactively instead of preventing | Should disable or grey out when no workflow |

### 🟡 Medium Gaps

| # | Grok Rule | Current State | Gap |
|---|-----------|--------------|-----|
| G5 | **ArchitectChat compact** should be contextual — not forced into every detail mode | MCCDetailPanel ALWAYS renders compact ArchitectChat at bottom (230-320px), even in dag_node stream view or task results. This squeezes the actual content panel severely in 240px column | Chat should hide when irrelevant (dag_node stream, task_results) OR be collapsible |
| G6 | **PipelineStats compact** same problem | MCCDetailPanel ALWAYS renders compact PipelineStats at bottom regardless of mode | Same fix — contextual or collapsible |
| G7 | **Unified header was designed**: `[MCC] [Team▾] [Sandbox▾] [Heartbeat▾] [Key▾] ●LIVE stats [Execute]` | Header exists and has all components ✅ | Header works but is crowded on narrow screens (no flexWrap). Minor. |
| G8 | **Stats must be Recharts** (full charts), not CSS bars | StatsDashboard.tsx uses Recharts ✅. PipelineStats.tsx uses CSS-only bars for some metrics | PipelineStats compact could stay CSS (it's a preview). Expanded should be Recharts via StatsDashboard. This is acceptable. |

### 🟢 Satisfied Rules

| Rule | Status |
|------|--------|
| Nolan palette (#111/#222/#e0e0e0, teal accent) | ✅ Everywhere |
| Monospace font | ✅ Everywhere |
| 3-column layout (left/center/right) | ✅ |
| Bottom-to-Top DAG flow | ✅ |
| Edge type: step (orthogonal) | ✅ |
| HeartbeatChip with presets (10m-1w) | ✅ |
| KeyDropdown with balance | ✅ |
| SandboxDropdown with create/destroy | ✅ |
| PresetDropdown with search + grouping | ✅ |
| Onboarding overlay (4 steps, non-modal) | ✅ |
| Tooltips with useLimitedTooltip (3 max shows) | ✅ |
| Task provenance (source_chat_id) | ✅ backend |
| Adjusted stats (0.7 verifier + 0.3 user) | ✅ backend |
| Architect reads team performance | ✅ backend |
| Playground auto-create on first Execute | ✅ |
| NodePicker (ComfyUI-style double-click) | ✅ |
| TaskEditor inline editing | ✅ |
| TaskFilterBar (status/source/preset/search) | ✅ |
| TaskDrillDown modal | ✅ |

---

## Part 2: Task Plan

### CODEX Tasks (Frontend Only)

#### C1. Task DAG View — `TaskDAGView.tsx` (NEW, ~300 lines)
**Priority: P0 — this is the 152.10 deliverable**

Create `client/src/components/mcc/TaskDAGView.tsx` + `nodes/TaskDAGNode.tsx`:
- Separate ReactFlow instance rendering tasks from `GET /api/analytics/dag/tasks?limit=50`
- Custom node `TaskDAGNode`: title, preset+phase_type, mini-stats badge (duration, confidence%, retries)
- Status coloring: done=green border, failed=red, running=pulse animation, pending=dashed gray, hold=yellow dashed
- dagre layout TB (top-to-bottom), `ranksep: 80, nodesep: 40`
- Single-click → `onTaskSelect(id)`, Double-click → `onTaskDrillDown(id)`
- MiniMap with status coloring
- READ-ONLY (no drag, no editing)

**Existing brief:** `docs/152_ph/CODEX_BRIEF_WAVE3_DUAL_DAG.md` section 152.10

#### C2. Dual DAG Navigation — MCC center column toggle (152.11)
**Priority: P0 — paired with C1**

Modify `MyceliumCommandCenter.tsx`:
- Add `dagViewMode: 'tasks' | 'workflow'` state (local useState)
- Add tab toggle bar between toolbar and DAG: `[📋 Tasks] [⚙ Workflow]`
- Default view = "tasks" → `<TaskDAGView />`
- Double-click task node → switch to "workflow" + select task in store
- Breadcrumb in workflow mode: `← Back to Tasks | Task: {title}`
- Import `TaskDAGView`

**Existing brief:** `docs/152_ph/CODEX_BRIEF_WAVE3_DUAL_DAG.md` section 152.11

#### C3. WorkflowToolbar Cleanup — Contextual Buttons
**Priority: P1**

Modify `client/src/components/mcc/WorkflowToolbar.tsx`:
1. **Validate button**: hide when workflow has 0 nodes (`dagNodes.length === 0`)
2. **Generate button**: hide when workflow has unsaved changes (dirty indicator `*`)
3. **Save dialog**: replace `prompt()` with inline input (styled Nolan monochrome). Show input field inside toolbar when Save clicked and workflow is "Untitled"
4. **Generate dialog**: replace `prompt()` with inline text input in toolbar
5. **Export button**: already correctly disabled when no workflowId ✅ (no change)

Props needed from MCC: `nodeCount: number`, `isDirty: boolean`

#### C4. Right Column Context Awareness — Collapsible Bottom Panels
**Priority: P1**

Modify `MCCDetailPanel.tsx`:
- When mode = `dag_node` (node selected) AND `dagNodeTab = 'stream'`: **hide** ArchitectChat compact and PipelineStats compact (stream needs full height)
- When mode = `dag_node` AND `dagNodeTab = 'info'` OR `edit`: **show** PipelineStats compact only (no chat — irrelevant when inspecting a node)
- When mode = `task_results` or `task_running`: **show** PipelineStats compact only (chat irrelevant when viewing results)
- When mode = `task_info` or `overview`: **show both** ArchitectChat compact + PipelineStats compact (this is where chat makes sense — user is thinking about tasks)
- Add collapse toggle `▼`/`▲` on each bottom panel header so user can manually hide

This recovers ~300px of vertical space in the right column when viewing node details or results.

#### C5. Execute Button Adaptive State
**Priority: P2**

Modify `MyceliumCommandCenter.tsx` header:
- Execute button: `disabled` + grayed out when no workflow loaded (no nodes in DAG AND no workflowId)
- Tooltip on disabled: "Load or create a workflow first"

---

### OPUS Tasks (Backend + Architecture)

#### O1. Update Project Digest to Phase 152
**Priority: P0**

Update `data/project_digest.json` — currently says Phase 150, should say Phase 152.

#### O2. Verify Analytics API Endpoints
**Priority: P0 — prerequisite for C1**

Run backend server and test:
```
GET /api/analytics/dag/tasks?limit=50
GET /api/analytics/summary
GET /api/analytics/task/{task_id}
```
Ensure they return data in expected format for Codex frontend work.

#### O3. Clean Up Deleted mcc/ArchitectChat.tsx References
**Priority: P1**

Already done ✅:
- Removed import from MCCTaskList ✅
- Removed `onAcceptArchitectChanges` prop from MCC ✅
- Deleted `mcc/ArchitectChat.tsx` ✅
- `panels/ArchitectChat.tsx` compact restored in MCCDetailPanel ✅

Verify: `npx tsc --noEmit` passes (only pre-existing NodeInspector error).

---

### GROK Research Needed?

**Currently: NO.** The existing Grok research (Phase 151 + 152) covers the UX philosophy thoroughly. All tasks above derive directly from the research.

**IF we need Grok later**, send these files for review:
1. `client/src/components/mcc/WorkflowToolbar.tsx` — toolbar button audit
2. `client/src/components/mcc/MyceliumCommandCenter.tsx` — header + layout
3. `client/src/components/mcc/MCCDetailPanel.tsx` — right column modes
4. This audit document (`PHASE_152_WAVE3_AUDIT.md`)

---

## Part 3: Execution Order

```
Phase 1 (Opus, now):
  O1. Update digest
  O2. Verify API endpoints
  O3. Verify cleanup (already done)

Phase 2 (Codex, session 1):
  C1. TaskDAGView.tsx (NEW)        — ~300 lines
  C2. Dual DAG Navigation           — ~60 lines modify MCC

Phase 3 (Codex, session 2):
  C3. WorkflowToolbar cleanup       — ~80 lines modify
  C4. Right column context awareness — ~40 lines modify MCCDetailPanel
  C5. Execute button adaptive        — ~10 lines modify MCC
```

Codex session 1 = Wave 3 core (Task DAG).
Codex session 2 = Wave 3 polish (toolbar + right column).

---

## Part 4: Files Summary

| Action | File | Agent | Est. Lines |
|--------|------|-------|-----------|
| **CREATE** | `client/src/components/mcc/TaskDAGView.tsx` | Codex | ~250 |
| **CREATE** | `client/src/components/mcc/nodes/TaskDAGNode.tsx` | Codex | ~120 |
| **MODIFY** | `client/src/components/mcc/MyceliumCommandCenter.tsx` | Codex | +60, -10 |
| **MODIFY** | `client/src/components/mcc/WorkflowToolbar.tsx` | Codex | +40, -20 |
| **MODIFY** | `client/src/components/mcc/MCCDetailPanel.tsx` | Codex | +20, -5 |
| **MODIFY** | `data/project_digest.json` | Opus | ~5 |
| **DELETED** | `client/src/components/mcc/ArchitectChat.tsx` | Opus | done ✅ |

**Total new: ~370 lines. Total modified: ~120 lines.**

---

## Part 5: DO NOT

1. ❌ Do NOT touch backend Python files (all analytics ready)
2. ❌ Do NOT modify `DAGView.tsx` (workflow DAG stays as-is)
3. ❌ Do NOT modify `panels/ArchitectChat.tsx` or `panels/PipelineStats.tsx` (they work correctly)
4. ❌ Do NOT install new npm packages
5. ❌ Do NOT create `.ts` files for components with JSX — always `.tsx`
6. ❌ Do NOT modify stores (`useMCCStore`, `useDevPanelStore`, `useArchitectStore`)
7. ❌ Do NOT add framer-motion animations (deferred to Phase 153)
8. ❌ Do NOT add split-view for >1920px (deferred to Phase 153)
9. ❌ Do NOT delete or modify the existing Dual DAG brief (`CODEX_BRIEF_WAVE3_DUAL_DAG.md`)

## Part 6: DO

1. ✅ Follow Nolan palette (`NOLAN_PALETTE` from `dagLayout.ts`)
2. ✅ Use monospace font everywhere
3. ✅ Use `@xyflow/react` v12 (already installed)
4. ✅ Use `dagre` (already installed)
5. ✅ Use MARKER_152.10 / MARKER_152.11 / MARKER_152.W3 in code comments
6. ✅ Run `npx tsc --noEmit` before committing
7. ✅ Panel = Zoom: compact in DAG, expanded as tab. Same component, mode prop.
8. ✅ Every button answers WHO/WHERE/WHEN or is contextual to current action
