# Phase 154 — Checklist 🚂

> **Каждая сущность видна в DAG и в списке. Нет скрытых настроек. Нет визуализации без функции.**

---

## Wave 0: Grok Research ✅

- [x] UX pattern research → Figma-like drill-down
- [x] Button consolidation table (5 states × 3 actions)
- [x] Wireframe layout template
- [x] Playground design (one per project, quota)
- [x] Transition animation → expand 300ms
- [x] Memory audit (10,876 строк production — ничего не потеряно)

---

## Wave 1: Layout Simplification ✅

**Цель:** 3 тулбара → 1 Breadcrumb (top) + 1 Footer (3 actions). Чистый canvas.

### 154.1 — Extend useMCCStore + Breadcrumb Rewrite
**Agent:** Opus (store) → Codex (UI)

> **Scout Discovery:** `useMCCStore.ts` already has NavLevel, drillDown(), goBack() from MARKER_153.1C.
> **Decision:** EXTEND `useMCCStore` instead of creating separate `useMatryoshkaStore.ts`.

- [x] Расширить `client/src/store/useMCCStore.ts` (НЕ создавать новый store) ✅ Opus
  - [x] Добавить `LEVEL_CONFIG`: labels, icons, actions per level (6 levels × 3 actions)
  - [x] Добавить `first_run` в NavLevel type: `'first_run' | 'roadmap' | 'tasks' | 'workflow' | 'running' | 'results'`
  - [x] Добавить `goToLevel(level)` action (jump, not drill — trims history)
  - [x] Existing drillDown/goBack from MARKER_153.1C — kept as-is
  - [x] MARKER_154.1B в коде (NavLevel, LEVEL_CONFIG, goToLevel, initMCC first_run)
  - [x] `ActionDef` + `LevelConfig` types exported
  - [x] `initMCC()` → sets `first_run` when no project
- [x] Переписать `client/src/components/mcc/MCCBreadcrumb.tsx` ✅ Opus
  - [x] Убрать hard-coded LEVEL_LABELS/LEVEL_ICONS (lines 17-31)
  - [x] Читать config из `LEVEL_CONFIG` (imported from useMCCStore)
  - [x] Кликабельные сегменты → `goToLevel()` (direct jump, not multiple goBack)
  - [x] Формат: `🗺 Roadmap > 📋 Tasks (auth-module) > ⚙ Workflow`
  - [x] MARKER_154.1A в коде
  - [x] Hidden at first_run level
- [ ] 154.1C — async Qdrant query при `drillDown()` (memory-aware) → Wave 2
  - [ ] Не блокирует UI, loading indicator
  - [ ] MARKER_154.1C в коде

### 154.2 — FooterActionBar
**Agent:** Codex

- [x] Создать `client/src/components/mcc/FooterActionBar.tsx` ✅ Opus (~230 lines)
  - [x] 3 кнопки, меняются по `useMCCStore.navLevel` (reads LEVEL_CONFIG)
  - [x] Action map:
    - [x] FIRST_RUN: Folder / URL / Text
    - [x] ROADMAP: Launch / Ask / Add
    - [x] TASK: Launch / Edit / Back
    - [x] RUNNING: Pause / Cancel / Back
    - [x] RESULTS: Accept / Redo / Back
  - [x] ⚙ gear icon → popup with GEAR_ACTIONS per level
  - [x] Keyboard shortcuts: `1/2/3` for primary actions, Esc for back
  - [x] MARKER_154.2A (bar), MARKER_154.2B (gear actions) в коде
  - [x] `disabledActions` prop for conditional disable
  - [x] Glass-morphism + Nolan dark style

### 154.3 — Убрать старые тулбары
**Agent:** Codex

- [x] `MyceliumCommandCenter.tsx` — убрать WorkflowToolbar, RailsActionBar из render tree ✅ Opus
- [x] Добавить: Breadcrumb (top) + DAGView (center) + FooterActionBar (bottom)
- [ ] `CaptainBar.tsx` — оставлен (пока используется, уберётся в Wave 4 → MiniChat)
- [x] `WorkflowToolbar.tsx` — убран из layout (import закомментирован, файл оставлен)
- [x] `RailsActionBar.tsx` — убран из layout (import закомментирован, файл оставлен, first_run добавлен)
- [ ] `TaskFilterBar.tsx` — перенести в gear popup / MiniTasks expanded → Wave 4
- [x] MARKER_154.3A в коде (3 places: imports, toolbar block, footer replacement)
- [x] FooterActionBar `onAction` dispatcher wired (17 action handlers)
- [x] `useKeyboardShortcuts.ts` — added `first_run: {}` entry
- [x] 0 new TS errors (verified with `npx tsc --noEmit`)

### Wave 1 Tests
- [ ] Breadcrumb рендерит правильный путь для каждого уровня
- [ ] Footer показывает 3 правильных действия по уровню
- [ ] Gear popup открывается с правильными hidden actions
- [ ] Старые тулбары не рендерятся
- [ ] Shortcuts 1/2/3 работают

### Wave 1 ✅ Commit
- [ ] `git commit` через `vetka_git_commit`
- [ ] Обновить MEMORY.md

---

## Wave 2: Matryoshka Navigation ✅

**Цель:** Double-click на ноду = вход внутрь. Back = выход. Expand animation.

### 154.4 — DAGView Drill-Down
**Agent:** Opus

- [x] `DAGView.tsx` — `onNodeDoubleClick` already existed (MARKER_153.5D) ✅
- [x] Разный рендеринг нод по уровню:
  - [x] Roadmap: `roadmap_task` node type (RoadmapTaskNode) with team badge + progress ✅ Opus
  - [ ] Task: workflow nodes (Scout→Researcher→Architect→Coder→Verifier) → Wave 3
  - [ ] Execution: workflow nodes + анимация (pulse/glow) → Wave 3
  - [ ] Result: workflow nodes + badges результатов → Wave 3
- [x] `DAGView.tsx` — registered `roadmap_task` in nodeTypes ✅ Opus
- [x] `types/dag.ts` — added `'roadmap_task'` to DAGNodeType union ✅ Opus
- [x] `types/dag.ts` — added `'dependency'` to EdgeType union ✅ Opus
- [x] `dagLayout.ts` — added `roadmap_task` to NODE_DIMENSIONS ✅ Opus
- [x] `dagLayout.ts` — added `description` to data pass-through ✅ Opus
- [ ] `useDAGEditor.ts` — метод `getNodesForLevel(level, taskId?)` → deferred to Wave 3
- [x] MARKER_154.4A (DAGView node type), MARKER_154.6A (RoadmapTaskNode) в коде

### 154.5 — Expand Transition Animation
**Agent:** Opus

- [x] Создать `client/src/components/mcc/MatryoshkaTransition.tsx` ✅ Opus (~92 lines)
  - [x] Direction auto-detected from LEVEL_DEPTH map (first_run=0 → results=5)
  - [x] Drill-down: scale 0.85→1 + blur 4px→0px (300ms)
  - [x] Go-back: scale 1.15→1 + blur 4px→0px (300ms)
  - [x] `cubic-bezier(0.4, 0, 0.2, 1)` easing ✅
- [x] Framer Motion integration в `MyceliumCommandCenter.tsx` ✅ Opus
  - [x] `<MatryoshkaTransition navLevel={navLevel}>` wraps DAGView canvas section
  - [x] AnimatePresence mode="wait" for clean entry/exit
- [x] MARKER_154.5A в коде

### 154.6 — Level-Specific Content
**Agent:** Opus

- [ ] `useMCCStore.ts` — добавить `roadmapNodes`, `taskWorkflowNodes` computed → Wave 3
- [x] Создать `RoadmapTaskNode.tsx` — нода для roadmap (статус, title, team badge) ✅ Opus (~226 lines)
  - [x] Team badge: Bronze(B/#cd7f32), Silver(S/#c0c0c0), Gold(G/#ffd700)
  - [x] Subtask progress bar (done/total)
  - [x] Description snippet (ellipsis, title tooltip)
  - [x] Status-aware border + glow for running
  - [x] Double-click hint on hover via CSS
- [x] `useRoadmapDAG.ts` — all node types → `roadmap_task`, added taskId, strength ✅ Opus
- [x] `DAGView.tsx` — `.roadmap-node-hint` hover CSS ✅ Opus
- [ ] Backend: используем существующие endpoints → Wire in Wave 3
- [x] MARKER_154.6A в коде (6 files)

### Wave 2 Tests
- [ ] Double-click на roadmap node → level = 'task'
- [ ] Back → level = 'roadmap'
- [ ] Breadcrumb click на 'Roadmap' → возврат
- [ ] Анимация expand/collapse работает
- [ ] Правильные ноды на каждом уровне
- [ ] Execution level показывает pulse на активной ноде

### Wave 2 ✅ Commit
- [ ] `git commit` через `vetka_git_commit`
- [ ] Обновить MEMORY.md

---

## Wave 3: Actions Per Level ✅

**Цель:** Footer actions подключены к реальным функциям.

### 154.7 — Roadmap Actions
**Agent:** Opus

- [x] Launch → drill into selected node (handleRoadmapNodeDrill) or dispatch (handleExecute) ✅ Wave 1
- [ ] Ask Architect → open MiniChat → deferred to Wave 4 (MiniChat component)
- [x] Add Task → focuses quick-add input in MCCTaskList ✅ Wave 1
- [ ] `useMCCStore.ts` — `recommendedTaskId` → deferred (Captain already selects)
- [x] Actions wired in FooterActionBar onAction switch ✅

### 154.8 — Task Actions
**Agent:** Opus

- [x] Launch → `dispatchTask(taskId)` via useMCCStore ✅ Wave 1
- [x] Edit → TaskEditPopup ✅ Opus
- [x] Создать `client/src/components/mcc/TaskEditPopup.tsx` ✅ Opus (~210 lines)
  - [x] Team buttons (Bronze/Silver/Gold) with descriptions
  - [x] Phase type buttons (Build/Fix/Research)
  - [x] Description textarea
  - [x] Save + Save & Launch buttons
  - [x] Escape/overlay-click to close
- [x] Back → handled by FooterActionBar internally (goBack) ✅
- [x] MARKER_154.8A в коде

### 154.9 — Execution Actions
**Agent:** Opus

- [x] Pause → `cancelTask(runningTaskId)` ✅ Wave 1
- [x] Cancel → cancel + goBack() ✅ Wave 1
- [x] Back → goBack() (pipeline продолжает в фоне) ✅ FooterActionBar
- [x] Actions wired in FooterActionBar onAction switch ✅

### 154.10 — Result Actions
**Agent:** Opus

- [x] Accept → PATCH task done + result_status=applied + goBack() ✅ Opus
- [x] Redo → RedoFeedbackInput ✅ Opus
- [x] Создать `client/src/components/mcc/RedoFeedbackInput.tsx` ✅ Opus (~130 lines)
  - [x] Textarea: "What needs to be fixed?"
  - [x] Cmd+Enter to submit
  - [x] Submit → PATCH task pending + result_status=rework + re-dispatch with feedback
- [x] Back → goBack() (результат сохраняется) ✅ FooterActionBar
- [x] MARKER_154.10A, MARKER_154.10B в коде

### Wave 3 Tests
- [ ] Launch диспатчит правильную задачу
- [ ] Edit popup показывает team/workflow/description
- [ ] Pause/Cancel вызывают правильные endpoints
- [ ] Accept → нода зеленеет в roadmap
- [ ] Redo → feedback добавляется к задаче + re-dispatch
- [ ] Back → навигация вверх на один уровень

### Wave 3 ✅ Commit
- [ ] `git commit` через `vetka_git_commit`
- [ ] Обновить MEMORY.md

---

## Wave 4: Mini-Windows

**Цель:** 3 floating окна — compact в углах, expanded как overlay.

### 154.11 — MiniWindow Framework
**Agent:** Codex

- [ ] Создать `client/src/components/mcc/MiniWindow.tsx`
  - [ ] Props: `position`, `children`, `title`
  - [ ] States: `compact | expanded`
  - [ ] Compact: 200×150, в углу
  - [ ] Expanded: 80% screen, overlay, z-index above DAG
  - [ ] Toggle: click header ↔ expand/compact
  - [ ] X или click outside → compact
  - [ ] Glass-morphism, Nolan dark style
- [ ] MARKER_154.11A в коде

### 154.12 — MiniChat
**Agent:** Codex

- [ ] Создать `client/src/components/mcc/MiniChat.tsx`
  - [ ] Compact: одна строка ввода + последний ответ
  - [ ] Expanded: полный ArchitectChat с историей
  - [ ] Wraps `ArchitectChat.tsx` (у него уже есть mode prop)
  - [ ] Position: top-left
- [ ] 154.12B — Engram history при expand
  - [ ] Load chat history из `engram_user_memory`
  - [ ] MARKER_154.12B в коде
- [ ] MARKER_154.12A в коде

### 154.13 — MiniTasks
**Agent:** Codex

- [ ] Создать `client/src/components/mcc/MiniTasks.tsx`
  - [ ] Compact: 5 задач со статусами
  - [ ] Expanded: полный список + фильтры (reuse MCCTaskList)
  - [ ] Position: bottom-right
- [ ] MARKER_154.13A в коде

### 154.14 — MiniStats
**Agent:** Codex

- [ ] Создать `client/src/components/mcc/MiniStats.tsx`
  - [ ] Compact: 4 числа (runs, success%, duration, cost)
  - [ ] Expanded: StatsDashboard overlay
  - [ ] Position: top-right
  - [ ] Data: `/api/analytics/summary`
- [ ] MARKER_154.14A в коде

### Wave 4 Tests
- [ ] Mini-windows рендерятся на правильных позициях
- [ ] Compact → click → expanded overlay
- [ ] Expanded → X → compact
- [ ] Chat отправляет сообщение, показывает ответ
- [ ] Tasks обновляется при pipeline activity
- [ ] Stats показывает правильные числа с API

### Wave 4 ✅ Commit
- [ ] `git commit` через `vetka_git_commit`
- [ ] Обновить MEMORY.md

---

## Wave 5: Playground v2 + First Run + Persistence

**Цель:** Один playground на проект. First Run. Всё сохраняется между сессиями.

### 154.15 — Playground Simplification
**Agent:** Opus (backend)

- [ ] `playground_manager.py` — MODIFY
  - [ ] Fixed name: `{project_name}-playground`
  - [ ] Один на проект (error если уже есть)
  - [ ] `get_or_create()` метод
  - [ ] `_check_quota()`: soft 80% warn, hard 100% block
  - [ ] Size: `git count-objects --all --size`
  - [ ] `delete()`: `git worktree remove` + prune
- [ ] `playground_routes.py` — SIMPLIFY
  - [ ] `GET /api/playground` — status
  - [ ] `POST /api/playground` — create
  - [ ] `DELETE /api/playground` — delete
  - [ ] `GET /api/playground/quota` — size info
- [ ] MARKER_154.15A, MARKER_154.15B в коде

### 154.16 — First Run
**Agent:** Opus (backend) + Codex (frontend)

- [ ] Backend: `src/api/routes/project_routes.py` — NEW
  - [ ] `GET /api/project` → config или null
  - [ ] `POST /api/project/init` → path + scan + roadmap
  - [ ] `POST /api/project/init/url` → git clone + init
  - [ ] `POST /api/project/init/text` → from text
- [ ] Frontend: `client/src/components/mcc/FirstRunView.tsx` — NEW
  - [ ] Чистый экран: "Какой проект развиваем?"
  - [ ] 3 опции: Folder / URL / Text
  - [ ] Progress: scanning → roadmap → playground
  - [ ] Auto-transition → Roadmap level
- [ ] `useMCCStore.ts` — `isFirstRun` flag (extend existing)
- [ ] `data/project_config.json` — schema
- [ ] MARKER_154.16A, MARKER_154.16B в коде

### 154.17 — Persistence + Fallback
**Agent:** Opus (backend)

- [ ] On startup: load `project_config.json` → restore level
- [ ] Save: last viewed task, mini-window positions (localStorage)
- [ ] `data/roadmap.json` — auto-save roadmap graph
- [ ] 154.17B — Qdrant fallback
  - [ ] Config corrupt → restore из Qdrant
  - [ ] Qdrant unavailable → fresh scan
  - [ ] UI: "Restoring from memory..." progress
  - [ ] MARKER_154.17B в коде
- [ ] MARKER_154.15C, MARKER_154.17A в коде

### Wave 5 Tests
- [ ] Playground создаётся с правильным именем
- [ ] Quota блокирует при превышении
- [ ] First Run показывает 3 опции
- [ ] Folder selection → scan → roadmap
- [ ] Close → open → state restored
- [ ] Один playground на проект (второй create → error)
- [ ] Corrupt config → Qdrant restore

### Wave 5 ✅ Commit
- [ ] `git commit` через `vetka_git_commit`
- [ ] Обновить MEMORY.md

---

## Wave 6: Polish + E2E

**Цель:** Cleanup, shortcuts, end-to-end тесты.

### 154.18 — Dead Code Cleanup
**Agent:** Codex

- [ ] Убрать из render tree (файлы оставить):
  - [ ] `CaptainBar.tsx`
  - [ ] `WorkflowToolbar.tsx`
  - [ ] `RailsActionBar.tsx`
  - [ ] `FilterBar.tsx` (→ в MiniTasks expanded)
  - [ ] `SandboxDropdown.tsx` (→ auto-playground)
  - [ ] Неиспользуемые header dropdowns

### 154.19 — Keyboard Shortcuts
**Agent:** Codex

- [ ] `1/2/3` → Footer actions
- [ ] `Enter` → Action 1 (primary)
- [ ] `Escape` → Back
- [ ] `Ctrl+D` → Verifier details (Result level)
- [ ] `/` → Open compact Chat

### 154.20 — Playwright E2E Tests
**Agent:** Codex

- [ ] Full flow: First Run → Roadmap → click task → Launch → Result → Accept
- [ ] Back navigation на каждом уровне
- [ ] Mini-window open/close
- [ ] Keyboard shortcuts
- [ ] Persistence: reload → same state

### Wave 6 ✅ Commit
- [ ] `git commit` через `vetka_git_commit`
- [ ] Обновить MEMORY.md
- [ ] Обновить Phase в MEMORY.md: `Phase 154 ✅ COMPLETE`

---

## Quick Reference: File Map

### NEW Files (создать)
```
client/src/components/mcc/FooterActionBar.tsx    — Wave 1 (154.2)
client/src/components/mcc/MatryoshkaTransition.tsx — Wave 2 (154.5)
client/src/components/mcc/nodes/RoadmapTaskNode.tsx — Wave 2 (154.6)
client/src/components/mcc/TaskEditPopup.tsx      — Wave 3 (154.8)
client/src/components/mcc/RedoFeedbackInput.tsx  — Wave 3 (154.10)
client/src/components/mcc/MiniWindow.tsx          — Wave 4 (154.11)
client/src/components/mcc/MiniChat.tsx            — Wave 4 (154.12)
client/src/components/mcc/MiniTasks.tsx           — Wave 4 (154.13)
client/src/components/mcc/MiniStats.tsx           — Wave 4 (154.14)
client/src/components/mcc/FirstRunView.tsx        — Wave 5 (154.16)
src/api/routes/project_routes.py                 — Wave 5 (154.16)
data/project_config.json                         — Wave 5 (154.15)
data/roadmap.json                                — Wave 5 (154.17)
```

### MODIFY Files (изменить)
```
client/src/store/useMCCStore.ts                  — Wave 1 (154.1) + Wave 5 (154.17) EXTEND
client/src/components/mcc/MCCBreadcrumb.tsx      — Wave 1 (154.1) REWRITE
client/src/components/mcc/MyceliumCommandCenter.tsx — Wave 1 (154.3) layout + Wave 4 mini-windows
client/src/components/mcc/DAGView.tsx            — Wave 2 (154.4, 154.5)
client/src/hooks/useDAGEditor.ts                 — Wave 2 (154.4)
src/orchestration/playground_manager.py          — Wave 5 (154.15)
src/api/routes/playground_routes.py              — Wave 5 (154.15)
```

### DEPRECATE (убрать из layout, файлы оставить)
```
client/src/components/mcc/CaptainBar.tsx         — Wave 1 (154.3)
client/src/components/mcc/WorkflowToolbar.tsx    — Wave 1 (154.3)
client/src/components/mcc/RailsActionBar.tsx     — Wave 1 (154.3)
client/src/components/panels/TaskFilterBar.tsx   — Wave 1 (154.3) → MiniTasks
client/src/components/mcc/SandboxDropdown.tsx    — Wave 6 (154.18)
```

---

## Progress Tracker

| Wave | Status | Tasks | Done | Commit |
|------|--------|-------|------|--------|
| 0 | ✅ | 6 | 6 | — |
| 1 | ✅ | 154.1, 154.2, 154.3 + TS fixes | ~20/~20 | pending |
| 2 | ✅ | 154.4, 154.5, 154.6 (visual) + TS fixes | ~15/~15 | 898f22f7 |
| 3 | ✅ | 154.7, 154.8, 154.9, 154.10 | ~15/~18 | pending |
| 4 | ⬜ | 154.11, 154.12, 154.13, 154.14 + tests | 0/~16 | — |
| 5 | ⬜ | 154.15, 154.16, 154.17 + tests | 0/~20 | — |
| 6 | ⬜ | 154.18, 154.19, 154.20 | 0/~12 | — |

**Total: ~101 checkboxes. Поехали.** 🚂
