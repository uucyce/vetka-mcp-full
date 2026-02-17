# Phase 154 — Haiku Scout Reconnaissance Reports

**Date:** 2026-02-17
**Scouts:** 4 x Haiku (parallel)
**Status:** COMPLETE — all files analyzed, markers designated

---

## Critical Architectural Discovery

> **`useMCCStore.ts` already has NavLevel + drillDown() + goBack() from Phase 153 (MARKER_153.1C).**
> Creating separate `useMatryoshkaStore.ts` may be REDUNDANT.
> **Recommendation:** EXTEND `useMCCStore` with level config (labels, icons, actions) instead of new store.

**Evidence:**
- Line 52: `export type NavLevel = 'roadmap' | 'tasks' | 'workflow' | 'running' | 'results'`
- Lines 82-88: Navigation state fields (`navLevel`, `navHistory`, `navRoadmapNodeId`, `navTaskId`, `hasProject`, `projectConfig`)
- Lines 382-403: `initMCC()` — loads project config + session state from `/api/mcc/init`
- Lines 406-421: `drillDown(level, context)` — pushes history, sets new level, persists to server
- Lines 424-439: `goBack()` — pops history, restores previous level

**Impact on Roadmap:**
- Task 154.1 `useMatryoshkaStore.ts` — **CHANGE**: Add level config TO `useMCCStore` instead of creating new store
- MCCBreadcrumb already reads from `useMCCStore` — no import change needed
- RailsActionBar already has `LEVEL_ACTIONS` per NavLevel — keep as source of truth

---

## Wave 1: Layout Simplification

### Files Analyzed

| File | Size | Status | MARKER |
|------|------|--------|--------|
| `MCCBreadcrumb.tsx` | 5.2KB, 184 lines | EXISTS | MARKER_153.5A |
| `MyceliumCommandCenter.tsx` | 36KB, ~950 lines | EXISTS | MARKER_143.P2 |
| `CaptainBar.tsx` | 4.4KB | EXISTS | MARKER_153.7D |
| `WorkflowToolbar.tsx` | 4KB | EXISTS | MARKER_144.6 |
| `RailsActionBar.tsx` | 6.3KB, 211 lines | EXISTS | MARKER_153.6A |
| `useMCCStore.ts` | ~440 lines | EXISTS | MARKER_153.1C |
| `useMatryoshkaStore.ts` | — | MISSING | — |
| `FooterActionBar.tsx` | — | MISSING | — |

### MCCBreadcrumb.tsx — Current Structure

- **Lines 17-23:** `LEVEL_LABELS` — hard-coded NavLevel -> display string
- **Lines 25-31:** `LEVEL_ICONS` — hard-coded NavLevel -> emoji icon
- **Lines 33-39:** `BreadcrumbSegment` interface (typed segments)
- **Lines 50-88:** `useMemo` — builds segments from navHistory
- **Lines 107-183:** JSX — flexbox, clickable segments, "Esc" hint

**MARKER placement for 154.1:**
```
Line 14 → MARKER_154.1A: Add level config imports (from useMCCStore extension)
Line 23 → MARKER_154.1B: Remove hard-coded LEVEL_LABELS/ICONS (now in store)
Line 50 → MARKER_154.1C: Get level config from store
```

### MyceliumCommandCenter.tsx — Layout Map

```
HEADER (lines 540-673)
├── "MCC" | PresetDropdown | SandboxDropdown | HeartbeatChip | KeyDropdown
├── LIVE/OFF indicator | Stats (t/r/d) | Execute button | Panel toggles
│
BREADCRUMB (line 676) ← MCCBreadcrumb
│
WORKFLOW TOOLBAR (lines 679-701) ← REMOVE in 154.3
│
THREE-COLUMN LAYOUT (lines 704-854)
├── LEFT (220px): MCCTaskList
├── CENTER (flex):
│   ├── CaptainBar (line 728) ← REMOVE in 154.3
│   ├── Task breadcrumb (line 749)
│   ├── DAGView (line 800) ← onNodeDoubleClick already wired (MARKER_153.5D)
│   ├── RailsActionBar (line 844) ← becomes FooterActionBar
│   └── StreamPanel (line 853)
└── RIGHT (240px): MCCDetailPanel
```

**MARKER placement for 154.3:**
```
Line 21  → MARKER_154.3A: Remove WorkflowToolbar import
Line 679 → MARKER_154.3B: Remove WorkflowToolbar JSX block
Line 728 → MARKER_154.3C: Remove CaptainBar (recommendation moved to Breadcrumb area)
Line 844 → MARKER_154.3D: Replace RailsActionBar with FooterActionBar
```

### RailsActionBar.tsx — Action Definitions (KEEP as reference)

- **Lines 29-55:** `LEVEL_ACTIONS` — 5 levels, 3 actions each:
  - `roadmap:` Drill (primary), Regenerate, Settings
  - `tasks:` Open (primary), Add Task, Back
  - `workflow:` Execute (primary), Edit, Back
  - `running:` Stop (primary), Stream, Back
  - `results:` Apply (primary), Reject, Back
- **Lines 88-130:** Action handler switch statement
- **Lines 149-200:** Nolan styling (rgba bg, blur, shortcut hints)

### WorkflowToolbar.tsx — DEPRECATE

- **Lines 42-49:** Button style (Nolan: transparent, borderDim, 9px font)
- **Props:** workflowId, isDirty, canUndo, canRedo, editMode, onNew/Save/Load/Validate/Undo/Redo/Generate/Import
- **Decision:** Save/Load/Validate move to gear popup. Undo/Redo stay as keyboard shortcuts.

### CaptainBar.tsx — DEPRECATE

- Only renders at `navLevel === 'roadmap'` (line 37)
- Shows "Next: [task]. [reason]. [Accept] [Skip]"
- **Decision:** Recommendation logic moves to Breadcrumb subtitle or MiniChat prompt

---

## Wave 2: Matryoshka Navigation

### Files Analyzed

| File | Size | Status | MARKER |
|------|------|--------|--------|
| `DAGView.tsx` | 13.8KB | EXISTS | MARKER_153.5D |
| `useDAGEditor.ts` | ~360 lines | EXISTS | — |
| `nodes/` (10 types) | ~80-150 lines each | EXISTS | — |
| `MatryoshkaTransition.tsx` | — | MISSING | — |
| `nodes/RoadmapTaskNode.tsx` | — | MISSING | — |

### DAGView.tsx — Drill-Down Infrastructure

- **Lines 44-54:** 9 custom node types: TaskNode, AgentNode, SubtaskNode, ProposalNode, ConditionNode, ParallelNode, LoopNode, TransformNode, GroupNode
- **Lines 210-221:** `handleNodeClick` — single-click toggle selection
- **Lines 223-229:** `handleNodeDoubleClick` — **ALREADY IMPLEMENTED**
  ```typescript
  const handleNodeDoubleClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeDoubleClick?.(node.id);
    },
    [onNodeDoubleClick]
  );
  ```
- **Line 303:** Wired: `onNodeDoubleClick={onNodeDoubleClick ? handleNodeDoubleClick : undefined}`
- **Lines 297-328:** ReactFlow config: fitView, minZoom 0.2, maxZoom 3, Sugiyama BT layout

**MARKER placement for 154.4-154.6:**
```
Line 77  → MARKER_154.4A: Extend DAGViewProps with `level` prop
Line 109 → MARKER_154.4B: Level-aware node selection (getNodesForLevel)
Line 287 → MARKER_154.5A: MatryoshkaTransition animation wrapper
Line 303 → MARKER_154.4A: drillDown integration via matryoshkaStore
```

### useDAGEditor.ts — Level Extension Needed

- **Methods:** addNode, removeNode, updateNodeData, addEdge, handleConnect, removeEdge, undo, redo, save, load, listWorkflows, validate
- **Line 112:** Each DAGNode has `layer: 0` (placeholder, unused)
- **No hierarchy concept** — all nodes flat list
- **Missing:** `getNodesForLevel(level, taskId?)` method

**MARKER placement:**
```
Line 72  → MARKER_154.4B: Add getNodesForLevel() method
Line 355 → MARKER_154.6A: Level-specific node data fetching
```

### Node Types — Usage Per Level

| Level | Primary Node | Secondary |
|-------|-------------|-----------|
| **Roadmap** | TaskNode / RoadmapTaskNode (NEW) | TaskDAGNode (stats variant) |
| **Task** | AgentNode (Scout->Architect->Researcher->Coder->Verifier) | ConditionNode |
| **Execution** | AgentNode (animated pulse) | — |
| **Result** | ProposalNode + AgentNode (static) | — |

### Dependencies Verified

- `framer-motion: ^11.18.2` — line 29 in package.json
- `@xyflow/react: ^12.10.0` — line 27
- `zustand: ^4.5.2` — line 44
- **No npm install needed**

---

## Wave 3: Actions Per Level

### Files Analyzed

| File | Status | Wave Task |
|------|--------|-----------|
| `FooterActionBar.tsx` | MISSING | 154.7-154.10 |
| `TaskEditPopup.tsx` | MISSING | 154.8B |
| `RedoFeedbackInput.tsx` | MISSING | 154.10B |

### Backend Endpoints (All Verified Existing)

| Endpoint | File | Line | Used By |
|----------|------|------|---------|
| `POST /api/debug/task-board/dispatch` | debug_routes.py | 2147 | 154.7 Launch, 154.8 Task Launch |
| `POST /api/debug/task-board/cancel` | debug_routes.py | 2238 | 154.9 Pause/Cancel |
| `PATCH /api/debug/task-board/{id}` | debug_routes.py | — | 154.8 Edit, 154.10 Redo |
| `POST /api/debug/task-board/add` | debug_routes.py | — | 154.7 Add Task |
| `GET /api/analytics/summary` | analytics_routes.py | 31 | 154.14 MiniStats |
| `GET /api/analytics/task/{id}` | analytics_routes.py | 46 | Task drill-down |
| `GET /api/analytics/agents` | analytics_routes.py | 65 | Agent efficiency |

### Action Map (from RailsActionBar + Grok Research)

| Level | Action 1 (Primary) | Action 2 | Action 3 | Gear Popup |
|-------|-------------------|----------|----------|------------|
| FIRST_RUN | Select Folder | Enter URL | Describe Text | API keys |
| ROADMAP | Launch Recommended | Ask Architect | Add Task | Filters, Stats, Edit DAG |
| TASK | Launch | Edit | Back | Team, Validate |
| EXECUTION | Pause | Cancel | Back | Log export |
| RESULT | Accept | Redo | Back | Diff export, Verifier details |

### New Components Needed

**TaskEditPopup.tsx** (~200 lines):
- Team dropdown (Bronze/Silver/Gold)
- Workflow template selector
- Description textarea
- File list (from Scout report, read-only)
- API: PATCH `/api/debug/task-board/{id}`

**RedoFeedbackInput.tsx** (~60 lines):
- Textarea: "What went wrong?"
- Submit → PATCH task + re-dispatch with feedback
- Cancel button

### MARKER Placement

```
FooterActionBar.tsx (NEW):
  MARKER_154.7A  — Launch action (dispatch recommended task)
  MARKER_154.7B  — Add Task action (inline quick-add)
  MARKER_154.8A  — Task Launch action
  MARKER_154.8B  — Task Edit popup trigger
  MARKER_154.9A  — Execution Pause/Cancel actions
  MARKER_154.10A — Result Accept action
  MARKER_154.10B — Result Redo with feedback

TaskEditPopup.tsx (NEW):
  MARKER_154.8B  — Team + workflow + description editor

RedoFeedbackInput.tsx (NEW):
  MARKER_154.10B — Feedback text + re-dispatch
```

---

## Wave 4: Mini-Windows

### Files Analyzed

| File | Size | Status | Mode Prop |
|------|------|--------|-----------|
| `ArchitectChat.tsx` | ~200 lines | EXISTS | `mode?: 'compact' \| 'expanded'` (line 32) |
| `StatsDashboard.tsx` | ~300 lines | EXISTS | `mode?: 'compact' \| 'expanded'` (line 16) |
| `PipelineStats.tsx` | ~200 lines | EXISTS | `mode?: 'compact' \| 'expanded'` (line 10) |
| `MCCTaskList.tsx` | 17.5KB | EXISTS | No mode prop yet |
| `MiniWindow.tsx` | — | MISSING | — |
| `MiniChat.tsx` | — | MISSING | — |
| `MiniTasks.tsx` | — | MISSING | — |
| `MiniStats.tsx` | — | MISSING | — |

### ArchitectChat.tsx — Ready for Wrapping

- **Line 32:** `mode?: 'compact' | 'expanded'` prop confirmed
- **Line 51-54:** `visibleMessages` — compact shows last 5, expanded shows all
- **Uses:** `useArchitectStore` for shared state
- **NO changes needed** — MiniChat wraps it directly

### StatsDashboard.tsx — Ready for Wrapping

- **Line 16:** `mode?: 'compact' | 'expanded'` prop confirmed
- **API:** `GET /api/analytics/summary` (endpoint verified, line 21)
- **Charts:** Recharts (LineChart, BarChart)
- **NO changes needed** — MiniStats wraps it directly

### MCCTaskList.tsx — Needs Mode Prop

- **Line 41-47:** Reads from `useMCCStore`
- **Line 14:** Has `TaskFilterBar` component
- **Line 16:** Has `TaskDrillDown` component
- **Missing:** `mode` prop for compact rendering (hide filters, limit to 5 tasks)

### New Components Needed

**MiniWindow.tsx** (~120 lines) — Base framework:
```typescript
interface MiniWindowProps {
  position: 'top-left' | 'top-right' | 'bottom-right';
  title: string;
  children: ReactNode;
  initialState?: 'compact' | 'expanded';
}
// States: compact (200x150, corner) | expanded (80% viewport, centered overlay)
// Style: glass-morphism, backdrop-filter: blur(10px), Nolan dark
// Animation: 300ms ease on expand/collapse
```

**MiniChat.tsx** (~100 lines) — Position: top-left
- Compact: one-line input + last response summary
- Expanded: full ArchitectChat mode="expanded"

**MiniTasks.tsx** (~100 lines) — Position: bottom-right
- Compact: 5 tasks, status badges, no filters
- Expanded: full MCCTaskList with filters

**MiniStats.tsx** (~80 lines) — Position: top-right
- Compact: 4 stat boxes (Runs | Success% | Avg Duration | Total Cost)
- Expanded: full StatsDashboard overlay

### MARKER Placement

```
MiniWindow.tsx (NEW):  MARKER_154.11A — Mini-window framework
MiniChat.tsx (NEW):    MARKER_154.12A — Chat wrapper
MiniTasks.tsx (NEW):   MARKER_154.13A — Tasks wrapper
MiniStats.tsx (NEW):   MARKER_154.14A — Stats wrapper
```

### Layout Integration (in MyceliumCommandCenter.tsx)

```
MCC Canvas (after Wave 4):
+-- Breadcrumb (top full-width) ---------------------+
|                                                     |
| [MiniChat]                           [MiniStats]    |
|  (top-left)                          (top-right)    |
|                                                     |
|              DAGView (center, ~70%)                 |
|                                                     |
|                                    [MiniTasks]      |
|                                    (bottom-right)   |
|                                                     |
+-- FooterActionBar (3 buttons) ---------------------+
```

---

## Wave 5: Playground v2 + First Run

### Files Analyzed

| File | Size | Status | MARKER |
|------|------|--------|--------|
| `playground_manager.py` | 943 lines | EXISTS | MARKER_146.PLAYGROUND |
| `playground_routes.py` | — | MISSING | — |
| `data/project_config.json` | ~10 lines | EXISTS | — |
| `FirstRunView.tsx` | — | MISSING | — |
| `OnboardingOverlay.tsx` | 4.6KB | EXISTS | — |
| `OnboardingModal.tsx` | 11.4KB | EXISTS | — |
| `useOnboarding.ts` | 80 lines | EXISTS | — |

### playground_manager.py — Current API

```python
class PlaygroundManager:
    create(task_description, preset, source_branch, auto_write) → PlaygroundConfig
    get_playground_root(playground_id) → Optional[Path]
    list_playgrounds(include_inactive=False) → List[PlaygroundConfig]
    validate_path(playground_id, file_path) → bool       # path traversal prevention
    scope_path(playground_id, relative_path) → Optional[Path]
    destroy(playground_id) → bool
    cleanup_expired() → int                               # TTL=4 hours
    record_pipeline_run(playground_id, files_created)
    get_diff(playground_id) → Optional[str]
    review(playground_id) → Optional[Dict]
    promote(playground_id, strategy="cherry-pick") → Optional[str]
    reject(playground_id) → bool
```

**Current config:** `PlaygroundConfig` with `playground_id`, `branch_name`, `worktree_path`, etc.
**Current naming:** Random `pg_<8-hex>` IDs
**Current quota:** MAX_PLAYGROUNDS=5, TTL=4 hours

**Changes needed for 154.15:**
- Fixed naming: `{project_name}-playground` instead of `pg_<random>`
- One per project: `get_or_create()` method, error if exists
- Quota: `_check_quota()` with size check (`git count-objects --all --size`)
- Simplified REST: GET/POST/DELETE `/api/playground` (no multi-playground CRUD)

### OnboardingOverlay.tsx — Extensible for FirstRun

- 4-step guided tour: key -> team -> sandbox -> architect chat
- Targets DOM elements via `data-onboarding` attribute
- Reusable pattern for FirstRun flow

### project_config.json — Current Schema

```json
{
  "project_id": "fake_project_b9c3cf3d",
  "source_type": "local",
  "source_path": "/path/to/source",
  "sandbox_path": "/Users/.../playgrounds/...",
  "quota_gb": 10,
  "created_at": "2026-02-16T18:45:46.770162+00:00",
  "qdrant_collection": "fake_project_b9c3cf3d"
}
```

**Extensions needed:**
- `first_run: boolean` — true on creation, false after first Execute
- `playground.path`, `playground.size_limit_gb`, `playground.created_at`
- `roadmap_file: "data/roadmap.json"`

### MARKER Placement

```
playground_manager.py:
  MARKER_154.15A — Single playground (fixed naming, one per project)
  MARKER_154.15B — Quota system (soft 80% warn, hard 100% block)

project_config.json schema:
  MARKER_154.15C — Extended schema (playground, first_run)

FirstRunView.tsx (NEW):
  MARKER_154.16A — First run onboarding flow

data/project_config.json:
  MARKER_154.17A — Session persistence (nav state, playground)
  MARKER_154.17B — Qdrant fallback for corrupt config
```

---

## Wave 6: Polish + Integration

### Files Analyzed

| File | Size | Status | MARKER |
|------|------|--------|--------|
| `useKeyboardShortcuts.ts` | 103 lines | EXISTS | MARKER_153.6B |
| `useOnboarding.ts` | 80 lines | EXISTS | — |

### useKeyboardShortcuts.ts — Current Shortcuts

```typescript
const SHORTCUTS = {
  roadmap:  { Enter: 'onDrillNode' },
  tasks:    { Enter: 'onDrillTask', a: 'onAddTask' },
  workflow: { Enter: 'onExecute', e: 'onToggleEdit' },
  running:  { ' ': 'onStop', v: 'onExpandStream' },
  results:  { Enter: 'onApply', r: 'onReject' }
}
```

**Extensions needed for 154.19:**
- Add footer shortcuts: `1/2/3` for 3 footer actions
- Add `Esc` = Back at all levels
- Add `first_run` level shortcuts

### MARKER Placement

```
useKeyboardShortcuts.ts:
  MARKER_154.19A — Footer action shortcuts (1/2/3, Esc=Back)

Dead code cleanup:
  MARKER_154.18A — Remove deprecated toolbars from imports
  MARKER_154.18B — Clean up unused store fields

E2E tests:
  MARKER_154.20A — Playwright test scenarios
```

---

## Complete MARKER Registry

| Marker | Wave | File | Purpose |
|--------|------|------|---------|
| MARKER_154.1A | 1 | MCCBreadcrumb.tsx:14 | Level config imports |
| MARKER_154.1B | 1 | MCCBreadcrumb.tsx:23 | Remove hard-coded level config |
| MARKER_154.1C | 1 | MCCBreadcrumb.tsx:50 | Get config from store |
| MARKER_154.2A | 1 | FooterActionBar.tsx (NEW) | Footer component |
| MARKER_154.2B | 1 | FooterActionBar.tsx (NEW) | Action map per level |
| MARKER_154.3A | 1 | MyceliumCommandCenter.tsx:21 | Remove WorkflowToolbar import |
| MARKER_154.3B | 1 | MyceliumCommandCenter.tsx:679 | Remove WorkflowToolbar JSX |
| MARKER_154.3C | 1 | MyceliumCommandCenter.tsx:728 | Remove CaptainBar |
| MARKER_154.3D | 1 | MyceliumCommandCenter.tsx:844 | Replace RailsActionBar -> FooterActionBar |
| MARKER_154.4A | 2 | DAGView.tsx:77,303 | Drill-down integration |
| MARKER_154.4B | 2 | DAGView.tsx:109, useDAGEditor.ts:72 | Level-aware node selection |
| MARKER_154.5A | 2 | MatryoshkaTransition.tsx (NEW), DAGView.tsx:287 | Animation wrapper |
| MARKER_154.6A | 2 | useDAGEditor.ts:355 | Roadmap node data fetching |
| MARKER_154.6B | 2 | RoadmapTaskNode.tsx (NEW) | Task node with team badge |
| MARKER_154.7A | 3 | FooterActionBar.tsx | Launch recommended task |
| MARKER_154.7B | 3 | FooterActionBar.tsx | Add Task inline |
| MARKER_154.8A | 3 | FooterActionBar.tsx | Task Launch |
| MARKER_154.8B | 3 | TaskEditPopup.tsx (NEW) | Team/workflow/description editor |
| MARKER_154.9A | 3 | FooterActionBar.tsx | Execution Pause/Cancel |
| MARKER_154.10A | 3 | FooterActionBar.tsx | Result Accept |
| MARKER_154.10B | 3 | RedoFeedbackInput.tsx (NEW) | Redo with feedback |
| MARKER_154.11A | 4 | MiniWindow.tsx (NEW) | Mini-window framework |
| MARKER_154.12A | 4 | MiniChat.tsx (NEW) | Chat wrapper |
| MARKER_154.12B | 4 | MiniChat.tsx | Engram history integration |
| MARKER_154.13A | 4 | MiniTasks.tsx (NEW) | Tasks wrapper |
| MARKER_154.14A | 4 | MiniStats.tsx (NEW) | Stats wrapper |
| MARKER_154.15A | 5 | playground_manager.py | Single playground per project |
| MARKER_154.15B | 5 | playground_manager.py | Quota system |
| MARKER_154.15C | 5 | project_config.json | Extended schema |
| MARKER_154.16A | 5 | FirstRunView.tsx (NEW) | First run flow |
| MARKER_154.17A | 5 | project_config.json | Session persistence |
| MARKER_154.17B | 5 | project_config.json | Qdrant fallback |
| MARKER_154.1C_MEM | 5 | useMCCStore.ts | Memory-aware drill-down |
| MARKER_154.18A | 6 | MyceliumCommandCenter.tsx | Dead code cleanup |
| MARKER_154.18B | 6 | useMCCStore.ts | Unused store fields |
| MARKER_154.19A | 6 | useKeyboardShortcuts.ts | Footer shortcuts |
| MARKER_154.20A | 6 | e2e/phase154.spec.ts (NEW) | E2E test scenarios |

---

## File Inventory

### NEW Files (14)

| File | Wave | Lines Est. | Agent |
|------|------|-----------|-------|
| `FooterActionBar.tsx` | 1 | ~150 | Codex |
| `MatryoshkaTransition.tsx` | 2 | ~80 | Codex |
| `nodes/RoadmapTaskNode.tsx` | 2 | ~100 | Codex |
| `TaskEditPopup.tsx` | 3 | ~200 | Codex |
| `RedoFeedbackInput.tsx` | 3 | ~60 | Codex |
| `MiniWindow.tsx` | 4 | ~120 | Codex |
| `MiniChat.tsx` | 4 | ~100 | Codex |
| `MiniTasks.tsx` | 4 | ~100 | Codex |
| `MiniStats.tsx` | 4 | ~80 | Codex |
| `FirstRunView.tsx` | 5 | ~150 | Codex |
| `playground_routes.py` | 5 | ~200 | Opus |
| `e2e/phase154.spec.ts` | 6 | ~300 | Codex |
| *(useMatryoshkaStore.ts)* | — | CANCELLED | — |
| **Total** | | **~1640** | |

### MODIFY Files (7)

| File | Wave | Changes |
|------|------|---------|
| `MCCBreadcrumb.tsx` | 1 | Rewrite level config source |
| `MyceliumCommandCenter.tsx` | 1-4 | Remove 3 toolbars, add Footer + MiniWindows |
| `DAGView.tsx` | 2 | Level prop, drill-down store integration |
| `useDAGEditor.ts` | 2 | Add `getNodesForLevel()` |
| `useMCCStore.ts` | 1,5 | Add level config + session persistence |
| `playground_manager.py` | 5 | Single playground, quota, fixed naming |
| `useKeyboardShortcuts.ts` | 6 | Footer shortcuts (1/2/3, Esc) |

### DEPRECATE Files (5)

| File | Wave | Replacement |
|------|------|------------|
| `WorkflowToolbar.tsx` | 1 | FooterActionBar gear popup |
| `CaptainBar.tsx` | 1 | Breadcrumb subtitle / MiniChat |
| `RailsActionBar.tsx` | 1 | FooterActionBar (absorbs action config) |
| `TaskFilterBar.tsx` | 4 | MiniTasks expanded mode |
| DevPanel tabs (partial) | 4 | MiniWindows replace Stats/Architect tabs |

---

## Data Flow Summary

```
App Boot:
  useMCCStore.initMCC() → GET /api/mcc/init
    → hasProject=false → FIRST_RUN level (FirstRunView)
    → hasProject=true  → ROADMAP level (DAGView with task nodes)

Navigation:
  Double-click node → drillDown(level, {taskId})
    → navLevel updates → DAGView re-renders with getNodesForLevel()
    → Breadcrumb updates → FooterActionBar shows level actions
    → MatryoshkaTransition animates (300ms expand)

  Back button / Esc → goBack()
    → navHistory.pop() → restore previous level
    → MatryoshkaTransition animates (300ms shrink)

Actions:
  FooterActionBar button click → handler per level
    → Launch: POST /api/debug/task-board/dispatch
    → Edit: TaskEditPopup overlay
    → Accept: PATCH task status=done
    → Redo: RedoFeedbackInput → PATCH + dispatch

Mini-Windows:
  Compact (corner) → click header → Expanded (overlay)
    → MiniChat: ArchitectChat mode='compact'|'expanded'
    → MiniTasks: MCCTaskList with/without filters
    → MiniStats: StatsDashboard with/without charts
```

---

**All scouts complete. Ready for implementation.**
