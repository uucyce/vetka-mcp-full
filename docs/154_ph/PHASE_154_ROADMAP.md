# Phase 154: Mycelium Simplification — Roadmap

<!-- TODO_PHASE_154: Mycelium Simplification — DAG-в-DAG Матрёшка -->
<!-- DEPENDS_ON: Phase 152 (analytics backend), Phase 151 (UX overhaul), Phase 150 (DAG executor) -->
<!-- BLOCKS: Phase 155 (Unified Favorites + Weight Classes), Phase 156 (Project Architect) -->
<!-- SEARCH_TAGS: matryoshka, simplification, drill_down, breadcrumb, footer_actions, playground_v2 -->

**Status:** PLANNED
**Author:** Opus (architect) + Grok (research) + Codex (frontend)
**Date:** 2026-02-17
**Branch:** `phase154-mycelium-simplification`

---

## Манифест

> **Каждая сущность видна в DAG (визуально) и в списке (текстом). Нет скрытых настроек без визуализации. Нет визуализации без функции.**

---

## Цель

Превратить MCC из "20+ кнопок на экране" в "максимум 3 действия за раз". Один экран, 5 уровней вложенности (Матрёшка). Figma-like drill-down с expand animation.

## Исходные документы

| Документ | Содержание |
|----------|------------|
| `docs/152_ph/MYCELIUM_VISION.md` | Vision v3 — полная спецификация |
| `docs/154_ph/GROK_RESEARCH_154_MYCELIUM_SIMPLIFICATION.md` | Grok research — UX patterns, wireframes, button consolidation |
| `docs/154_ph/GROK_RESEARCH_PROMPT_154_MYCELIUM_SIMPLIFICATION.md` | Research prompt |
| `docs/154_ph/GROK_RESEARCH_154_MEMORY_ANALYSIS.md` | Grok Round 2: Memory audit + verdicts |
| `docs/155_ph/PHASE_155_UNIFIED_FAVORITES_AND_MODEL_WEIGHT_CLASSES.md` | Statistics/analytics → Phase 155 |

---

## Архитектура: что меняется

### Layout: Was → Will Be

```
WAS (current):
┌─ CaptainBar ─────────────────────────────────────────────┐
│ [MCC] [Team▾] [Sandbox▾] [Heartbeat▾] [Key▾] |stats| [▶]│
├─ WorkflowToolbar ─────────────────────────────────────────┤
│ [✎edit][name][New][Save][Load▾][↩↪][Validate][✦Gen][↓↑]  │
├───────────┬──────────────────────┬────────────────────────┤
│ TaskList  │    DAG Canvas        │    Detail Panel        │
│ + filters │                      │    (artifact viewer)   │
│           │                      │                        │
├───────────┴──────────────────────┴────────────────────────┤
│ RailsActionBar: [▶Execute] [✏Edit] [←Back]               │
└───────────────────────────────────────────────────────────┘

WILL BE:
┌─ BREADCRUMB ──────────────────────────────────────────────┐
│ Project > Roadmap > Task: add dark mode > Running...      │
├───────────────────────────────────────────────────────────┤
│                                                           │
│ [Compact Chat]                         [Compact Stats]    │
│   (top-left)                            (top-right)       │
│                                                           │
│                  DAG CANVAS (center, ~80%)                 │
│                                                           │
│                                                           │
│                                          [Compact Tasks]  │
│                                           (bottom-right)  │
├───────────────────────────────────────────────────────────┤
│ [Action 1]           [Action 2]           [Action 3]      │
└─ FOOTER ──────────────────────────────────────────────────┘
```

### Ключевые изменения

| Элемент | Текущее | Новое | Волна |
|---------|---------|-------|-------|
| CaptainBar + WorkflowToolbar + RailsActionBar | 3 тулбара, 20+ кнопок | 1 Breadcrumb (top) + 1 Footer (3 actions) | Wave 1 |
| Three-column layout | Tasks \| DAG \| Detail (фиксированные) | DAG Canvas (центр) + 3 floating mini-windows | Wave 2 |
| Navigation | Tabs, panels, modals | Double-click drill-down + Back button + Breadcrumb | Wave 2 |
| Task execution | Execute в 3 местах | Один "Launch" в Footer текущего уровня | Wave 3 |
| Team/Sandbox/Key selection | Header dropdowns | Auto (Architect decides) + ⚙ gear on Task level | Wave 3 |
| Playground | Multiple worktrees, random names | One per project, fixed name, quota | Wave 4 |
| Onboarding (First Run) | OnboardingOverlay (tutorial) | First Run state — select project, auto-scan | Wave 5 |

---

## Waves

### Wave 0: Grok Research ✅ DONE

- UX pattern research (7 products analyzed) → Figma-like drill-down
- Button consolidation table (5 states × 3 actions)
- Wireframe layout
- Playground implementation details
- Transition animation recommendation (expand, 300ms)
- **Docs:** `GROK_RESEARCH_154_MYCELIUM_SIMPLIFICATION.md`

---

### Wave 1: Layout Simplification (Opus + Codex)

**Goal:** Remove 3 toolbars → 1 Breadcrumb + 1 Footer. Clean canvas.

#### 154.1 — Breadcrumb Navigation (Opus backend + Codex frontend)
**Files:**
- `client/src/components/mcc/MCCBreadcrumb.tsx` — REWRITE (currently 5.2K, simple path)
  - State-aware: shows current Matryoshka level
  - Clickable segments: navigate to any parent level
  - Level indicator: `Project > Roadmap > Task: {name} > Running...`
  - Connected to new `useMatryoshkaStore` (see 154.3)
- `client/src/store/useMatryoshkaStore.ts` — NEW
  - `level: 'first_run' | 'roadmap' | 'task' | 'execution' | 'result'`
  - `breadcrumb: [{label, level, id?}]`
  - `drillDown(nodeId)` / `goBack()` / `goToLevel(level)`
  - `currentTaskId`, `currentWorkflowId`

**MARKERs:** `MARKER_154.1A` (breadcrumb), `MARKER_154.1B` (store)

#### 154.2 — Footer Action Bar (Codex)
**Files:**
- `client/src/components/mcc/FooterActionBar.tsx` — NEW (~150 lines)
  - 3 buttons, change per level (from Grok research table)
  - Keyboard shortcuts: `1/2/3` or `Enter/E/Esc`
  - ⚙ gear icon → context-specific popup (hidden actions per level)
  - Connects to `useMatryoshkaStore.level`

**Action map:**

| Level | Action 1 (primary) | Action 2 | Action 3 | ⚙ Gear popup |
|-------|-------------------|----------|----------|--------------|
| FIRST_RUN | Select Folder | Enter URL | Describe Text | API keys |
| ROADMAP | Launch Recommended | Ask Architect | Add Task | Filters, Stats, Edit DAG |
| TASK | Launch | Edit | Back | Team, Validate |
| EXECUTION | Pause | Cancel | Back | Log export |
| RESULT | Accept | Redo | Back | Diff export, Verifier details |

**MARKERs:** `MARKER_154.2A` (footer), `MARKER_154.2B` (action map)

#### 154.3 — Remove Old Toolbars (Codex)
**Files to modify:**
- `client/src/components/mcc/MyceliumCommandCenter.tsx` — Remove CaptainBar, WorkflowToolbar, RailsActionBar imports. Add Breadcrumb (top) + FooterActionBar (bottom). Keep DAGView center.
- `client/src/components/mcc/CaptainBar.tsx` — DEPRECATE (keep file, remove from layout)
- `client/src/components/mcc/WorkflowToolbar.tsx` — DEPRECATE
- `client/src/components/mcc/RailsActionBar.tsx` — DEPRECATE
- `client/src/components/panels/TaskFilterBar.tsx` — Move into gear popup / expanded Tasks mini-window

**MARKERs:** `MARKER_154.3A` (layout cleanup)

**Tests (Wave 1):**
- Breadcrumb renders correct path for each level
- Footer shows correct 3 actions per level
- Gear popup opens with correct hidden actions
- Old toolbars removed from render tree
- Keyboard shortcuts 1/2/3 trigger correct actions

---

### Wave 2: Matryoshka Navigation (Opus + Codex)

**Goal:** Implement drill-down navigation. Double-click node → enter. Back → exit.

#### 154.4 — DAGView Drill-Down (Codex)
**Files:**
- `client/src/components/mcc/DAGView.tsx` — MODIFY
  - `onNodeDoubleClick` → `matryoshkaStore.drillDown(nodeId)`
  - Different node rendering per level:
    - Roadmap level: task nodes (colored by status)
    - Task level: agent workflow nodes (Scout → Researcher → Architect → Coder → Verifier)
    - Execution level: same workflow nodes, animated (pulse/glow)
    - Result level: static workflow nodes + result badges
  - Level-specific edge styles
- `client/src/hooks/useDAGEditor.ts` — MODIFY
  - Add `getNodesForLevel(level, taskId?)` method
  - Roadmap: nodes from `task_board.json` (task list)
  - Task: nodes from workflow template (BMAD or custom)
  - Execution: same nodes with live status updates
  - Result: same nodes with completion badges

**MARKERs:** `MARKER_154.4A` (drill-down), `MARKER_154.4B` (level nodes)

#### 154.5 — Expand Transition Animation (Codex)
**Files:**
- `client/src/components/mcc/DAGView.tsx` — MODIFY
  - On drill-down: target node bounds → full canvas animation (300ms)
  - Framer Motion: `animate={{ scale, x, y, opacity }}`
  - Fade out surrounding nodes, expand target
  - Reverse on "Back" (shrink back to node position)
- `client/src/components/mcc/MatryoshkaTransition.tsx` — NEW (~80 lines)
  - Wrapper component: handles enter/exit animations
  - Props: `fromBounds: Rect`, `direction: 'in' | 'out'`
  - CSS: `transition: all 300ms cubic-bezier(0.4, 0, 0.2, 1)`

**Dependency:** `framer-motion` (already in project for OnboardingOverlay)

**MARKERs:** `MARKER_154.5A` (animation)

#### 154.6 — Level-Specific Canvas Content (Opus backend + Codex frontend)
**Files:**
- Backend: No new endpoints needed. Uses existing:
  - `/api/debug/task-board` → Roadmap nodes
  - `/api/analytics/task/{id}` → Task details
  - SocketIO `pipeline_activity` → Execution updates
  - `/api/debug/task-board/{id}/results` → Result data
- Frontend:
  - `client/src/store/useMCCStore.ts` — Add `roadmapNodes`, `taskWorkflowNodes` computed
  - `client/src/components/mcc/nodes/` — Existing node types suffice. May add:
    - `RoadmapTaskNode.tsx` — NEW: task node for roadmap level (status color, title, team badge)

**MARKERs:** `MARKER_154.6A` (roadmap nodes), `MARKER_154.6B` (task workflow nodes)

**Tests (Wave 2):**
- Double-click on roadmap node → level changes to 'task'
- Back button → level changes back to 'roadmap'
- Breadcrumb click on 'Roadmap' → returns to roadmap level
- Animation plays on transition (mock timing)
- Correct nodes rendered per level
- Execution level shows live pulse on active node

---

### Wave 3: Actions Per Level (Opus + Codex)

**Goal:** Wire Footer actions to real functionality per level.

#### 154.7 — Roadmap Actions (Opus backend + Codex frontend)
**Actions:**
1. **Launch** → Dispatch recommended task (`POST /api/debug/task-board/dispatch`)
2. **Ask Architect** → Open compact Chat mini-window (ArchitectChat)
3. **Add Task** → Inline add (quick input, auto-assign priority + team)

**Files:**
- `client/src/components/mcc/FooterActionBar.tsx` — Wire actions
- `client/src/store/useMCCStore.ts` — `recommendedTaskId` from Captain logic
- Backend: Existing endpoints suffice

**MARKERs:** `MARKER_154.7A` (launch), `MARKER_154.7B` (add task)

#### 154.8 — Task Actions (Codex)
**Actions:**
1. **Launch** → Start pipeline for this task (`POST /api/debug/task-board/dispatch?task_id=X`)
2. **Edit** → Open gear popup with: team selector, workflow template, description edit
3. **Back** → `matryoshkaStore.goBack()`

**Files:**
- `client/src/components/mcc/FooterActionBar.tsx` — Wire task actions
- `client/src/components/mcc/TaskEditPopup.tsx` — NEW (~200 lines)
  - Team dropdown (Bronze/Silver/Gold)
  - Workflow template selector
  - Description textarea
  - File list (from Scout)

**MARKERs:** `MARKER_154.8A` (task launch), `MARKER_154.8B` (task edit popup)

#### 154.9 — Execution Actions (Codex)
**Actions:**
1. **Pause** → `POST /api/debug/task-board/cancel/{id}` (existing)
2. **Cancel** → Cancel + go back
3. **Back** → Go to Roadmap (pipeline continues in background)

**Files:**
- `client/src/components/mcc/FooterActionBar.tsx` — Wire execution actions
- Existing cancel endpoint in `debug_routes.py` works

**MARKERs:** `MARKER_154.9A` (execution actions)

#### 154.10 — Result Actions (Codex)
**Actions:**
1. **Accept** → Apply code + mark task complete
2. **Redo** → Show feedback input → retry pipeline with feedback
3. **Back** → Return to Roadmap (result stays saved)

**Files:**
- `client/src/components/mcc/FooterActionBar.tsx` — Wire result actions
- `client/src/components/mcc/RedoFeedbackInput.tsx` — NEW (~60 lines)
  - Text input: "What's wrong?"
  - Submit → PATCH task status to pending + re-dispatch with feedback
- Backend: Existing endpoints (task-board update + dispatch)

**MARKERs:** `MARKER_154.10A` (accept), `MARKER_154.10B` (redo feedback)

**Tests (Wave 3):**
- Launch dispatches correct task
- Edit popup shows team/workflow/description
- Pause/Cancel call correct endpoints
- Accept marks task done + node turns green in roadmap
- Redo adds feedback to task + re-dispatches
- Back navigates up one level

---

### Wave 4: Mini-Windows (Codex)

**Goal:** 3 floating mini-windows — compact in corners, expandable to overlay.

#### 154.11 — Mini-Window Framework (Codex)
**Files:**
- `client/src/components/mcc/MiniWindow.tsx` — NEW (~120 lines)
  - Props: `position: 'top-left' | 'top-right' | 'bottom-right'`
  - States: `compact | expanded`
  - Compact: small (200×150), draggable, in corner
  - Expanded: overlay (80% screen), centered, z-index above DAG
  - Toggle: click header to expand, X or click outside to compact
  - CSS: glass-morphism background, Nolan dark style

**MARKERs:** `MARKER_154.11A` (mini-window)

#### 154.12 — Chat Mini-Window (Codex)
**Files:**
- `client/src/components/mcc/MiniChat.tsx` — NEW (~100 lines)
  - Compact: one-line input + last response (summary)
  - Expanded: full ArchitectChat with history
  - Wraps existing `ArchitectChat.tsx` (already has `mode: 'compact' | 'expanded'`)
  - Position: top-left

**MARKERs:** `MARKER_154.12A` (mini chat)

#### 154.13 — Tasks Mini-Window (Codex)
**Files:**
- `client/src/components/mcc/MiniTasks.tsx` — NEW (~100 lines)
  - Compact: 5 tasks, status badges, no filters
  - Expanded: full task list with filters + search (reuses MCCTaskList internals)
  - Position: bottom-right

**MARKERs:** `MARKER_154.13A` (mini tasks)

#### 154.14 — Stats Mini-Window (Codex)
**Files:**
- `client/src/components/mcc/MiniStats.tsx` — NEW (~80 lines)
  - Compact: 4 stat boxes (runs, success%, avg duration, total cost)
  - Expanded: StatsDashboard overlay (existing component)
  - Position: top-right
  - Data: `/api/analytics/summary` endpoint (Phase 152)

**MARKERs:** `MARKER_154.14A` (mini stats)

**Tests (Wave 4):**
- Mini-windows render at correct positions
- Compact → click → expanded overlay
- Expanded → X → back to compact
- Chat sends message, shows response
- Tasks list updates on pipeline activity
- Stats shows correct numbers from API

---

### Wave 5: Playground v2 + First Run (Opus backend + Codex frontend)

**Goal:** One playground per project. First Run onboarding flow.

#### 154.15 — Playground Simplification (Opus backend)
**Files:**
- `src/orchestration/playground_manager.py` — MODIFY
  - `create()` → fixed name: `{project_name}-playground`
  - Only one playground per project (error if exists)
  - `get_or_create()` method for auto-creation
  - Quota: `_check_quota()` before agent writes
    - Soft warning at 80% of user limit
    - Hard block at 100%
    - Size check: `git count-objects --all --size` (fast, ~10ms)
  - `delete()` → `git worktree remove` + `git branch -d` + prune
- `src/api/routes/playground_routes.py` — MODIFY
  - Remove multi-playground CRUD, simplify to:
    - `GET /api/playground` → get current playground status
    - `POST /api/playground` → create (if not exists)
    - `DELETE /api/playground` → delete with confirmation
    - `GET /api/playground/quota` → size + limit + usage%
- `data/project_config.json` — NEW schema
  ```json
  {
    "project_path": "/path/to/project",
    "project_name": "vetka",
    "playground": {
      "path": "/path/to/vetka-playground",
      "size_limit_gb": 2,
      "created_at": "2026-02-17T..."
    },
    "roadmap_file": "data/roadmap.json"
  }
  ```

**MARKERs:** `MARKER_154.15A` (single playground), `MARKER_154.15B` (quota), `MARKER_154.15C` (project config)

#### 154.16 — First Run State (Opus backend + Codex frontend)
**Files:**
- Backend:
  - `src/api/routes/project_routes.py` — NEW (~100 lines)
    - `GET /api/project` → project config (or null if no project)
    - `POST /api/project/init` → set project path, trigger scan + roadmap generation
    - `POST /api/project/init/url` → git clone + init
    - `POST /api/project/init/text` → create from text description
  - `data/project_config.json` — created on init
- Frontend:
  - `client/src/components/mcc/FirstRunView.tsx` — NEW (~150 lines)
    - Clean screen, one question: "Какой проект развиваем?"
    - 3 options: Folder picker, URL input, Text area
    - Progress: scanning → building roadmap → creating playground
    - Auto-transitions to Roadmap level when done
  - `client/src/store/useMatryoshkaStore.ts` — ADD
    - `isFirstRun` flag from `/api/project` response
    - On init: if no project → level = 'first_run'

**MARKERs:** `MARKER_154.16A` (first run backend), `MARKER_154.16B` (first run frontend)

#### 154.17 — Persistence Between Sessions (Opus backend)
**Files:**
- `src/api/routes/project_routes.py` — ADD
  - On startup: load `project_config.json` → restore level
  - Roadmap: saved in `data/roadmap.json` (task_board.json already persists)
  - Last viewed task: save in project_config
  - Mini-window positions: save in localStorage
- `data/roadmap.json` — NEW (auto-generated by Project Architect)
  ```json
  {
    "nodes": [
      {"id": "task_001", "title": "Add dark mode", "status": "ready", "deps": []},
      {"id": "task_002", "title": "Fix auth bug", "status": "blocked", "deps": ["task_001"]}
    ],
    "edges": [
      {"from": "task_001", "to": "task_002"}
    ],
    "recommended": "task_001",
    "generated_at": "2026-02-17T..."
  }
  ```

**MARKERs:** `MARKER_154.17A` (persistence)

**Tests (Wave 5):**
- Playground creates with correct name (`{project}-playground`)
- Quota check blocks writes over limit
- First Run shows 3 options
- Folder selection → scan → roadmap generated
- Closing + reopening → same state restored
- Only one playground per project (second create → error)

---

### Wave 6: Polish + Integration Tests (Opus + Codex)

#### 154.18 — Dead Code Cleanup (Codex)
Remove deprecated components from render tree (keep files for reference):
- `CaptainBar.tsx` — removed from layout
- `WorkflowToolbar.tsx` — removed from layout
- `RailsActionBar.tsx` — removed from layout
- `FilterBar.tsx` — moved into MiniTasks expanded view
- `SandboxDropdown.tsx` — replaced by auto-playground
- Unused header dropdowns (Team, Key) → auto or ⚙ gear

#### 154.19 — Keyboard Shortcuts (Codex)
- `1/2/3` → Footer actions
- `Enter` → Action 1 (primary)
- `Escape` → Back (Action 3 where applicable)
- `Ctrl+D` → Verifier details (Result level)
- `Ctrl+V` → Validate (Task level)
- `/` → Open compact Chat

#### 154.20 — Playwright E2E Tests (Codex)
- Full flow: First Run → Roadmap → click task → Launch → Result → Accept
- Back navigation at every level
- Mini-window open/close
- Keyboard shortcuts

---

## Agent Assignments

| Wave | Tasks | Agent | Effort |
|------|-------|-------|--------|
| 0 | Grok Research | Grok | ✅ DONE |
| 1 | 154.1-154.3 — Layout simplification | Opus (store/backend) + Codex (frontend) | 1-2 days |
| 2 | 154.4-154.6 — Matryoshka navigation | Codex (primary) + Opus (review) | 2-3 days |
| 3 | 154.7-154.10 — Actions per level | Codex (frontend) + Opus (backend wiring) | 1-2 days |
| 4 | 154.11-154.14 — Mini-windows | Codex | 1-2 days |
| 5 | 154.15-154.17 — Playground v2 + First Run | Opus (backend) + Codex (frontend) | 2-3 days |
| 6 | 154.18-154.20 — Polish + E2E | Codex | 1-2 days |

**Total: ~8-14 days** (depends on parallelization)

---

## MARKERs

```
MARKER_154.1A    — Breadcrumb state-aware navigation
MARKER_154.1B    — useMatryoshkaStore (level, breadcrumb, drillDown/goBack)
MARKER_154.2A    — FooterActionBar (3 actions per level)
MARKER_154.2B    — Action map configuration
MARKER_154.3A    — Old toolbar removal from layout
MARKER_154.4A    — DAGView drill-down (onNodeDoubleClick)
MARKER_154.4B    — Level-specific node rendering
MARKER_154.5A    — Expand transition animation (300ms, Framer Motion)
MARKER_154.6A    — Roadmap task nodes from task_board
MARKER_154.6B    — Task workflow nodes from template
MARKER_154.7A    — Launch recommended task
MARKER_154.7B    — Add task inline
MARKER_154.8A    — Task launch dispatch
MARKER_154.8B    — Task edit popup (team, workflow, description)
MARKER_154.9A    — Execution pause/cancel/back
MARKER_154.10A   — Accept result (apply + complete)
MARKER_154.10B   — Redo with feedback input
MARKER_154.11A   — MiniWindow framework (compact/expanded)
MARKER_154.12A   — MiniChat (ArchitectChat wrapper)
MARKER_154.13A   — MiniTasks (task list wrapper)
MARKER_154.14A   — MiniStats (analytics summary wrapper)
MARKER_154.15A   — Single playground per project
MARKER_154.15B   — Playground quota (soft warn 80%, hard block 100%)
MARKER_154.15C   — project_config.json schema
MARKER_154.16A   — First Run backend (project init endpoints)
MARKER_154.16B   — First Run frontend (3 options UI)
MARKER_154.17A   — Session persistence (project_config + roadmap)
MARKER_154.17B   — Qdrant fallback for corrupt config
MARKER_154.1C    — Memory-aware drill-down (Qdrant context on level change)
MARKER_154.12B   — Architect Chat Engram history integration
```

---

## Риски и mitigation

| Риск | Impact | Mitigation |
|------|--------|------------|
| ReactFlow не поддерживает smooth expand animation | Переход без анимации | CSS transform на wrapper div, не на ReactFlow |
| Потеря функциональности при удалении тулбаров | Пользователь не найдёт фичу | Всё в ⚙ gear popup + keyboard shortcuts |
| Roadmap generation (Project Architect) — сложная задача | Неточный roadmap | Phase 154 = UI only. Project Architect intelligence → Phase 156 |
| First Run git clone может быть медленным | UX тормоз | Progress bar + async clone в фоне |
| Mini-windows загромождают canvas | Опять 20 кнопок | Compact по умолчанию, прозрачный фон, auto-hide при маленьком экране |

---

## Grok Research Round 2: Memory Architecture Analysis

Grok провёл 3 документа по теме "не потеряем ли мы VETKA memory в Phase 154". Opus провёл аудит кодовой базы. Результат:

### Что уже есть (production, ~10,876 строк memory-кода):

| Компонент | Файл | Статус |
|-----------|------|--------|
| STM Buffer (Short-Term Memory) | `src/memory/stm_buffer.py` | ✅ В pipeline (agent_pipeline.py:1702-1854) |
| ELISION Compression (23-43%) | `src/memory/elision.py` | ✅ В pipeline (context injection) |
| MGC Cache (Gen 0-3: RAM→Qdrant→JSON→Archive) | `src/memory/mgc_cache.py` | ✅ Production |
| Engram User Memory (RAM hot + Qdrant cold) | `src/memory/engram_user_memory.py` | ✅ User prefs, temporal decay |
| Qdrant Client + Batch Manager | `src/memory/qdrant_client.py` | ✅ Full CRUD |
| Surprise Detector (CAM) | `src/memory/surprise_detector.py` | ✅ Novelty scoring |
| ModelRouter v2 | `src/elisya/model_router_v2.py` | ✅ Task-type routing |
| LLM Model Registry (speed/context profiles) | `src/elisya/llm_model_registry.py` | ✅ 20+ models, Artificial Analysis API |
| Provider Registry (7 providers) | `src/elisya/provider_registry.py` | ✅ FC support, key rotation |
| Capability Matrix | `src/elisya/capability_matrix.py` | ✅ Stream/FC mode detection |

### Что Грок предложил → наш вердикт:

| Предложение | Вердикт | Причина |
|-------------|---------|---------|
| `agent_memory_hook.py` — unified access | ⚠️ Phase 156+ | Хорошая идея, но STM/ELISION/MGC уже напрямую в pipeline |
| `model_catalog.json` | ❌ Дубликат | = `llm_model_registry.py` (20+ моделей) |
| `compression_pipeline.py` + QIM | ⚠️ Phase 155+ | `compression.py` (17K) уже есть. QIM = research Phase 137 |
| `engram_integration.py` | ❌ Дубликат | = `engram_user_memory.py` (production) |
| OpenClaw синергия | ❌ Шум | Простой vector DB. У нас 4-tier MGC + graph |
| Agent-scoped memory (Project/Task/Role) | ✅ Phase 156 | Хорошая идея, связана с Project Architect |
| MCP duality | ❌ Путаница | MCP = Model Context Protocol (server), не Memory Compression |
| Persistence fallback: config corrupt → Qdrant restore | ✅ Добавлено | Ниже в 154.17 |

### Что берём в Phase 154 (3 пункта):

**154.17B — Qdrant Fallback для Persistence:**
- If `project_config.json` corrupt → attempt restore from Qdrant `project_state` collection
- If Qdrant unavailable → create fresh config from directory scan
- UI: "Config damaged. Restoring from memory..." progress bar

**154.1C — Memory-Aware Drill-Down:**
- `useMatryoshkaStore.drillDown(nodeId)` при переходе на уровень Task:
  - Async query Qdrant для контекста задачи (related files, past attempts, feedback)
  - Inject в DAGView как enriched node metadata
  - Не блокирует UI (async, с loading indicator)

**154.12B — Architect Chat Memory:**
- MiniChat (154.12) при expand → load chat history из Engram
- Project Architect "помнит" предыдущие разговоры через `engram_user_memory` → `communication_style` + `topics`
- Полная реализация Architect intelligence → Phase 156, но UI-хук готовим сейчас

**MARKERs:**
```
MARKER_154.17B   — Qdrant fallback for corrupt config
MARKER_154.1C    — Memory-aware drill-down (Qdrant context on level change)
MARKER_154.12B   — Architect Chat Engram history integration
```

---

## Что НЕ входит в Phase 154

| Тема | Почему | Куда |
|------|--------|------|
| Project Architect intelligence (auto-roadmap) | Сложная LLM задача, отдельная фаза | Phase 156 |
| Unified Favorites + Weight Classes | Отдельная архитектура | Phase 155 |
| Dynamic team assembly | Зависит от weight classes | Phase 155 |
| DAG Executor integration (BMAD loop) | Уже работает (Phase 150) | Переиспользуем as-is |
| QIM compression (70-80%) | Research Phase 137, не для UI фазы | Phase 155+ (after ELISION proven) |
| Agent-scoped memory (Project/Task/Role) | Связана с Project Architect intelligence | Phase 156 |
| Multi-Model Council (parallel voting) | Research Phase 131, routing v2 достаточен | Phase 157+ |
| Mobile responsive | Desktop only | Not planned |
| Multi-project | Один проект | Not planned |

---

## Dependencies

```
Phase 150 (DAG Executor)        → BMAD workflow templates for task level
Phase 151 (UX Overhaul)         → Mini-window patterns (compact/expanded)
Phase 152 (Pipeline Analytics)  → /api/analytics/* endpoints for MiniStats
Phase 126.0 (Pipeline Stats)    → Pipeline stats data for Result level
Phase 124.2 (Task Board REST)   → /api/debug/task-board/* for Roadmap actions
Phase 122 (Feedback Loops)      → Retry/escalation for Redo action
```

## Post-154 Path

```
Phase 154 — Mycelium Simplification (UI architecture)
    ↓
Phase 155 — Unified Favorites + Model Weight Classes (intelligence data layer)
    ↓
Phase 156 — Project Architect (auto-roadmap, auto-team, auto-recommend)
    ↓
Phase 157 — Structured Agent Streaming (agent_stream events, WS control panel)
```
