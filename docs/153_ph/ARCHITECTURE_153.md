# Phase 153: Mycelium Matryoshka — Architecture

## Vision

Mycelium — система автоматического развития проектов. Пользователь едет по рельсам:
видит карту проекта, подтверждает план Архитектора, наблюдает работу агентов.
Максимум 3 действия за раз. Всё связано. Нет оторванных элементов.

---

## Grok Architecture Synthesis (2026-02-16)

MARKER_153.ARCH.GROK_SYNTHESIS.V1

Источник синтеза: ответ Grok "VETKA Architecture Map: Universal Data Nodes + Modes + MCP Extensibility"
с фокусом на связку `input_matrix_idea.txt` + `qdrant_batch_manager.py` + `artifact_scanner.py`.

### Core Position

1. Базовый VETKA должен поддерживать универсальный ingest/index/search для всех типов данных без обязательного MCP.
2. MCP используется как расширение для heavy-mode операций (глубокий видео/аудио пайплайн, 3D/GPU, live finance и т.д.).
3. Универсальная связь между узлами строится из трех источников:
   - явные зависимости (import/reference/citation),
   - временная причинность (A.created < B.created при достаточной semantic similarity),
   - ссылочные отношения (B явно ссылается на A).

### Node Modes and Y-axis

1. Directed Mode: `Y = time` (time-only, источник внизу, производные выше).
2. Knowledge Mode: `Y = f(time, knowledge_level)`.
3. Переключение режимов: через node-folder submenu / toolbar переключатель.
4. Статус для UI: Directed Mode как отдельный явный режим со статусом готовности.

### Media-Aware Node Representation

Для media-узлов акцент не на цвете, а на типовом визуале и preview:
1. video: poster/thumbnail + playback overlay, zoom -> timeline scrub.
2. audio: waveform + duration, zoom -> full waveform + transcript.
3. script/doc: page preview + structured outline/tree.
4. code: snippet preview + full editor on zoom.

### Architecture Flow (Phase 72/153 alignment)

1. Scanner layer (modular): CodeScanner, DocumentScanner, VideoScanner, AudioScanner, TemporalLinker.
2. Batch persistence/indexing: QdrantBatch (messages/artifacts) с единым ingestion contract.
3. Graph build/layout: dependency relations -> DAG/Sugiyama -> 3D canvas.
4. Agent loop: Mycelium agents предлагают рост графа, пользователь утверждает.

### Constraints Added to Phase 153

1. Anti-fragmentation: core pipeline остается единым (no separate mode backends for MVP).
2. Backward compatibility: текстовый pipeline не ломается при включении multimodal path.
3. Extraction status must be explicit in payload: `metadata_only|extracted|failed|skipped`.
4. Heavy MCP features отделяются от базового режима флагами и отдельным launcher path.

## Core Principles

1. **Matryoshka (DAG-in-DAG)** — Один canvas. Zoom раскрывает вложенный уровень.
2. **Rails (<=3 действия)** — Никогда больше 3 кнопок. Остальное — contextual popup.
3. **Architect-Led** — Самая умная модель предлагает. Пользователь подтверждает.
4. **Panel = Zoom** — Каждое окно: compact (chip/preview) <-> fullscreen (modal/tab).
5. **Everything Connected** — Нет orphans. Задачи висят на roadmap-нодах. Stats — overlay.
6. **Playground = Sandbox** — 1 на проект. Полная копия. Агенты не выходят за границы.

---

## Hierarchy (4 levels)

```
Level 0: PROJECT
  Первый запуск. Onboarding. Указать проект -> scan -> playground -> roadmap.

Level 1: ROADMAP DAG (карта проекта)
  Ноды = модули, фичи, фазы проекта.
  Root (backend/core) внизу -> Frontend/новое вверху.
  Architect анализирует проект и генерит эту карту.
  Задачи привязаны к нодам.

Level 2: TASK (конкретная задача)
  Задача внутри модуля. Имеет: описание, приоритет, статус, команду.
  Команда подбирается автоматически (или переопределяется).
  Задача = контейнер для workflow.

Level 3: WORKFLOW DAG (команда агентов)
  Scout -> Architect -> Researcher -> Coder -> Verifier
  Реальное выполнение. Стриминг прогресса. Результаты.
```

---

## User Scenario: Rails

### Step 0 — First Open (Onboarding)

**Условие**: Нет `data/project_config.json`.

**Что видит пользователь**: Modal на весь экран.

```
+------------------------------------------+
|                                          |
|  Welcome to Mycelium                     |
|                                          |
|  Укажите проект:                         |
|                                          |
|  [ /path/to/project_______ ] [Browse]    |
|                                          |
|  или Git: [ git@repo_______ ] [Clone]    |
|                                          |
|               [ Scan & Start ]           |
|                                          |
+------------------------------------------+
```

**Что происходит**:
1. Копируем проект в sandbox (`data/playgrounds/{project_id}/`)
2. Индексируем в Qdrant (все файлы)
3. Architect анализирует структуру -> генерит Roadmap DAG
4. Сохраняем `data/project_config.json` + `data/roadmap_dag.json`
5. Переходим к Step 1

**Actions (<=3)**: Browse | Git URL | Scan & Start

---

### Step 0.5 — Restart (Resume)

**Условие**: Есть `data/project_config.json`.

**Что происходит**: Загружаем конфиг, восстанавливаем состояние DAG.
Architect: "Продолжим? Последняя задача: X. Следующая рекомендация: Y."

**Actions (<=3)**: Continue | New Project | Settings

---

### Step 1 — Roadmap DAG (Project Map)

**Что видит пользователь**: Полноэкранный canvas с картой проекта.

```
+-- LEFT (compact) --+---- CENTER (roadmap DAG) ----+-- RIGHT (context) --+
|                    |                               |                    |
| [Modules list]     |  [ Frontend ]                 | OVERVIEW           |
|  > Auth module     |       |                       | Total: 12 tasks    |
|  > API layer       |  [ Components ]               | Running: 1         |
|  > Database        |       |                       | Done: 8            |
|  > Frontend        |  [ API Layer ]                 |                    |
|                    |       |                       | TEAM (5)           |
|                    |  [ Database ]                  |  ARC: kimi-k2.5    |
|                    |       |                       |  RES: grok-4.1     |
|                    |  [ Core ]  <- root            |  COD: qwen3-coder  |
|                    |                               |                    |
|                    |                               | [ARCHITECT CHAT]   |
|                    |                               | "Recommend: fix    |
|                    |                               |  API auth first"   |
+--------------------+-------------------------------+--------------------+
```

**Actions (<=3)**:
1. **Click node** -> правая панель показывает задачи этого модуля
2. **Chat with Architect** -> спросить "что дальше?" / подтвердить план
3. **Settings** (gear icon) -> popup: playground, heartbeat, global team

**Architect auto-action**: При загрузке Roadmap, Architect анализирует состояние
и выводит в чат: "Рекомендую: модуль X, задача Y (priority high). Создать?"

---

### Step 2 — Module -> Tasks

**Что видит пользователь**: Кликнул на модуль. Правая панель показывает задачи.
Или: zoom-in в ноду -> вложенный DAG задач.

```
+-- LEFT (tasks) ----+---- CENTER (task sub-DAG) ----+-- RIGHT (detail) --+
|                    |                               |                    |
| <- Back to Roadmap |  [ Fix auth endpoint ]        | TASK INFO          |
|                    |       |                       | "Fix auth..."      |
| Module: API Layer  |  [ Add rate limiting ]         | Status: pending    |
|                    |       |                       | Priority: P1       |
| Tasks:             |  [ Update docs ]               | Team: auto         |
|  > Fix auth [P1]   |                               |                    |
|  > Rate limit [P2] |                               | [ARCHITECT CHAT]   |
|  > Update docs [P3]|                               | "Fix auth first,   |
|                    |                               |  then rate limit"  |
+--------------------+-------------------------------+--------------------+
```

**Actions (<=3)**:
1. **Double-click task** -> drill-down в Workflow DAG (Step 3)
2. **Accept Architect plan** -> задачи создаются / приоритеты назначаются
3. **<- Back** -> zoom-out к Roadmap

---

### Step 3 — Task -> Workflow DAG

**Что видит пользователь**: Workflow агентов для конкретной задачи.

```
+-- LEFT (subtasks) -+---- CENTER (workflow DAG) ----+-- RIGHT (detail) --+
|                    |                               |                    |
| <- Back to Tasks   |      [ @verifier ]            | TASK               |
|                    |           |                   | "Fix auth..."      |
| Task: Fix auth     |    [ @coder ]                  | Status: ready      |
|                    |      /    \                   |                    |
| Subtasks:          | [@scout] [@researcher]         | Team: dragon_silver|
|  > Scan codebase   |      \    /                   |  ARC: kimi-k2.5    |
|  > Plan changes    |   [ @architect ]               |  COD: qwen3-coder  |
|  > Implement       |                               |                    |
|  > Verify          |                               | [ >> Execute ]     |
|                    |                               | [ Edit team... ]   |
+--------------------+-------------------------------+--------------------+
```

**Actions (<=3)**:
1. **>> Execute** -> запустить pipeline, перейти к Step 4
2. **Edit team** -> popup для смены модели/пресета ЭТОЙ задачи
3. **<- Back** -> zoom-out к Tasks

---

### Step 4 — Execution -> Results

**Что видит пользователь**: Стриминг выполнения.

```
+-- LEFT (progress) -+---- CENTER (live DAG) --------+-- RIGHT (stream) --+
|                    |                               |                    |
| <- Back            |      [ @verifier ] ○          | LIVE STREAM        |
|                    |           |                   |                    |
| Task: Fix auth     |    [ @coder ] ● RUNNING       | @scout: found 3    |
| Status: RUNNING    |      /    \                   |   files matching   |
|                    | [@scout]✓ [@researcher]✓       |                    |
| Progress:          |      \    /                   | @architect: plan   |
| ████████░░ 75%     |   [ @architect ] ✓             |   3 subtasks       |
|                    |                               |                    |
| Duration: 45s      |                               | @coder: writing    |
| Tokens: 12.4k      |                               |   auth_handler.py  |
+--------------------+-------------------------------+--------------------+
```

**Actions (<=3)**:
1. **Stop** -> остановить pipeline
2. **View result** (когда done) -> код/diff/apply
3. **<- Back** -> к Workflow

### Step 4.5 — Results Review

**Actions (<=3)**:
1. **Apply** -> применить к playground
2. **Reject** -> rework loop
3. **<- Back** -> к Workflow

---

## Panel = Zoom Architecture

Каждый компонент существует в двух режимах. Один React-компонент, prop `mode`.

| Component | Compact (chip/preview) | Fullscreen (tab/modal) |
|-----------|----------------------|----------------------|
| **Architect Chat** | Последние 3 сообщения в правой колонке | Полный чат с историей |
| **Stats** | 4 числа (runs/success/weak/adjusted) | Recharts dashboard |
| **Task List** | Список задач текущего уровня | Полный TaskBoard с фильтрами |
| **Stream** | Последние 5 событий | Полный ActivityLog |
| **Results** | Статус + confidence | DiffViewer + code + apply |

**Переключение**: Кнопка ↗ в заголовке compact-панели -> открывает fullscreen.
Кнопка ↙ в fullscreen -> возвращает к compact.
Shared state через Zustand store.

---

## Architect: The Captain

Architect — не просто LLM для планирования subtask-ов внутри pipeline.
Architect — **командир всей системы**.

### Architect responsibilities:

1. **Analyze project** -> генерит Roadmap DAG при первом запуске
2. **Recommend next** -> при каждом входе предлагает следующую задачу
3. **Plan tasks** -> разбивает модули на задачи с приоритетами
4. **Select team** -> подбирает пресет (bronze/silver/gold) под сложность
5. **Review results** -> оценивает результаты pipeline, предлагает rework
6. **Update roadmap** -> после выполнения задач обновляет карту
7. **Select workflow** -> подбирает готовый workflow-шаблон или собирает из блоков
8. **Prefetch tools** -> заранее собирает нужный контекст (файлы, доки, паттерны)

### Architect = Гроссмейстер, не новичок

Ключевой принцип: Architect НЕ строит workflow с нуля каждый раз.
Он оперирует **готовыми комбинациями** — как гроссмейстер в шахматах оперирует
дебютами, а не думает каждый ход с чистого листа.

```
Новичок:   "Что делать?" -> думает с нуля -> слабый план -> плохой результат
Гроссмейстер: "Тип задачи?" -> выбирает дебют -> адаптирует -> сильный план
```

### Workflow Template Library (Дебюты)

Набор проверенных workflow-шаблонов в `data/templates/workflows/`:

| Template | When to use | Nodes | Origin |
|----------|-------------|-------|--------|
| `bmad_default.json` | Полный цикл: build + verify + deploy | 11 nodes | VETKA (Phase 150) |
| `quick_fix.json` | Баг-фикс: scout → coder → verify | 4 nodes | Built-in |
| `research_first.json` | Неизвестная библиотека: researcher → architect → coder | 5 nodes | Built-in |
| `refactor.json` | Рефакторинг: scout deep → architect → coder parallel → verify | 6 nodes | Built-in |
| `test_only.json` | Написать тесты: scout → coder (test-mode) → verify | 4 nodes | Built-in |
| `docs_update.json` | Обновить документацию: scout → coder (docs-mode) | 3 nodes | Built-in |
| `n8n_import/` | Импортированные n8n workflows | varies | n8n import |
| `comfyui_import/` | Импортированные ComfyUI workflows | varies | ComfyUI import |

Architect выбирает шаблон на основе:
1. **Тип задачи** (build/fix/refactor/test/docs/research)
2. **Сложность** (simple → quick_fix, complex → bmad_default)
3. **Контекст** (новая библиотека → research_first, знакомый код → quick_fix)
4. **История** (этот тип задач раньше лучше работал с X шаблоном)

### Prefetch: Контекст заранее

Не просто "один инструмент — молоток". Одна кнопка вызывает **цепочку**:

```
User clicks [Execute] на задаче "Fix auth endpoint"
  ↓
Architect Prefetch Pipeline (автоматически, ДО основного pipeline):
  1. prefetch_files:    Qdrant semantic search "auth endpoint" → top 5 файлов
  2. prefetch_markers:  ripgrep MARKER_* в найденных файлах
  3. prefetch_docs:     Context7 → FastAPI auth docs (если в стеке)
  4. prefetch_history:  pipeline_history.json → как решали похожие задачи
  5. prefetch_workflow:  выбрать шаблон (quick_fix vs bmad_default)
  ↓
Всё это подаётся на вход Scout/Architect/Coder как ГОТОВЫЙ контекст.
Агенты не тратят свои FC turns на поиск — всё уже найдено.
```

### Architect Memory (CAM + ARC + HOPE)

Architect помнит прошлые решения через 3 системы:

| System | What it remembers | How it helps |
|--------|-------------------|--------------|
| **CAM** (Context-Aware Memory) | Активные ноды в Qdrant — файлы, паттерны, hot spots | Prefetch знает какие файлы "горячие" |
| **ARC** (Adaptive Reasoning Context) | Граф решений — что работало, что нет | Architect выбирает workflow на основе прошлого опыта |
| **HOPE** (pipeline_history + feedback) | Результаты пайплайнов: success rate, weak links | "Qwen3-coder плохо справляется с React → использовать research_first" |

Связка:
```
Задача: "Add dark mode toggle"
  → CAM: горячие файлы = useStore.ts, App.tsx, tokens.css
  → ARC: похожая задача "Add bookmark toggle" → использовали quick_fix → success
  → HOPE: Dragon Silver verifier_avg_confidence=0.9 для UI задач
  → Architect решение: quick_fix.json + dragon_silver + prefetch [useStore.ts, tokens.css]
```

### One Button = One Chain

Философия: пользователь нажимает ОДНУ кнопку → запускается ЦЕПОЧКА.

```
[Execute] = prefetch → select_workflow → select_team → dispatch → stream → verify → apply
[Accept Plan] = architect_plan → create_tasks → dispatch_first → navigate_to_running
[Fix This] = scout_error → quick_fix_workflow → coder_with_context → verify → apply
```

Никогда: "выбери workflow" → "настрой команду" → "запусти" → "проверь" → "применить".
Всегда: одна кнопка → всё автоматически → результат.

### Architect chat:

- Compact: 3 последних сообщения в правой колонке (всегда видны)
- Fullscreen: полный чат через DevPanel tab ARCHITECT
- Один чат, один store (`useArchitectStore`), два режима отображения
- Architect отвечает в контексте текущего уровня (roadmap/task/workflow)

---

## Playground v2

### What it is:
Изолированная копия проекта. Агенты работают ТОЛЬКО внутри.
Оригинал не трогается. Безопасность + свобода.

### Spec:

```
data/project_config.json:
{
  "project_id": "vetka_live_03",
  "source": {
    "type": "local",                    // "local" | "git"
    "path": "/Users/user/my-project"    // или "git@github.com:user/repo.git"
  },
  "sandbox": {
    "path": "/data/playgrounds/vetka_live_03/",
    "quota_gb": 10,
    "created_at": "2026-02-16T10:00:00Z"
  },
  "qdrant_collection": "vetka_live_03",
  "agents_boundary": true,              // agents chroot to sandbox
  "deletable": true
}
```

### Rules:
- **1 playground per project** (не массив рандомных worktree)
- **Полная копия** (cp -r для local, git clone --depth=1 для git)
- **Quota** (backend проверяет du -sh, предупреждает при >80%)
- **Delete & recreate** (пользователь может удалить и пересоздать)
- **Agents boundary** (cwd = sandbox path, no ../ escape)
- **Без Git не проблема** (cp -r работает для любого проекта)
- **Remote support** (будущее: указать URL сервера, ssh/rsync)

### What changes from current:
- Убрать: рандомные имена (pg_d8291162), множественные worktree
- Добавить: привязка к проекту, quota, delete
- Сохранить: git worktree как опция (если проект с git)
- Упростить UI: одна кнопка "Playground" вместо SandboxDropdown списка

---

## Persistence

### What we save (survives server restart):

| File | Content | When saved |
|------|---------|------------|
| `data/project_config.json` | Project source, sandbox path, quota | On project init |
| `data/roadmap_dag.json` | Roadmap DAG nodes + edges | On Architect update |
| `data/session_state.json` | Current level, selected task, zoom | On every navigation |
| `data/task_board.json` | All tasks with statuses | Already exists, on every change |
| `data/pipeline_history.json` | Pipeline execution logs | Already exists |
| `data/heartbeat_config.json` | Heartbeat settings | Already exists |

### What we load on restart:

```
Server startup:
  1. Read project_config.json -> know project path, sandbox
  2. Read session_state.json -> know where user was

Frontend mount (MyceliumCommandCenter):
  1. GET /api/mcc/init -> returns project_config + session_state
  2. If no config -> show Onboarding modal
  3. If config exists -> restore DAG level + selection
  4. Architect: "Продолжим? Последняя задача: X"
```

---

## What We Keep (from old Mycelium)

### Keep as-is (working, valuable):

| Component | Lines | Why keep |
|-----------|-------|----------|
| `agent_pipeline.py` | 3858 | Core pipeline, battle-tested (Phases 122-127) |
| `task_board.py` | 1064 | JSON-backed queue, dependency resolution |
| `pipeline_analytics.py` | 920 | 9 aggregation functions (Phase 152) |
| `analytics_routes.py` | 309 | 9 REST endpoints for stats |
| `dag_executor.py` | 993 | DAG execution engine with topological sort |
| `PipelineStats.tsx` | 257 | Per-agent stats bars |
| `StatsDashboard.tsx` | 348 | Recharts dashboard |
| `TaskDrillDown.tsx` | 353 | Task detail modal |
| `ArchitectChat.tsx` | 284 | Chat with compact/expanded modes |
| `ActivityLog.tsx` | 630 | Event ring buffer |
| `DiffViewer.tsx` | 160 | Code diff display |
| `PipelineResultsViewer.tsx` | 325 | Result viewer with apply/reject |
| `KeyDropdown.tsx` | 234 | API key management |
| `BalancesPanel.tsx` | 332 | Balance display |
| `HeartbeatChip.tsx` | 250 | Countdown timer |
| `useSocket.ts` | 1858 | Socket.IO event hub |
| `useDAGEditor.ts` | 381 | DAG manipulation |
| `useMCCStore.ts` | 339 | Central state hub |
| `model_presets.json` | - | 6 tier definitions |
| `pipeline_prompts.json` | - | 5 role prompts |

### Refactor (keep logic, change UI integration):

| Component | What changes |
|-----------|-------------|
| `MyceliumCommandCenter.tsx` (846) | Matryoshka navigation: zoom levels instead of static 3-column |
| `MCCTaskList.tsx` (449) | Becomes context-aware: shows tasks of current level |
| `MCCDetailPanel.tsx` (474) | Becomes context-aware: shows detail of current selection |
| `WorkflowToolbar.tsx` (575) | Slim to <=3 buttons + contextual popup |
| `DAGView.tsx` (417) | Add zoom-level awareness (roadmap / task-sub / workflow) |
| `OnboardingOverlay.tsx` (153) | Replace 5-step tips with project-init modal |
| `SandboxDropdown.tsx` (208) | Single playground button instead of list |
| `PlaygroundBadge.tsx` (183) | Show project sandbox status |

### Remove (deprecated / replaced):

| Component | Reason |
|-----------|--------|
| `orchestrator_with_elisya.py` (2861) | Old parallel orchestrator |
| `agent_orchestrator_parallel.py` (388) | Replaced by AgentPipeline |
| `agent_orchestrator.py` (264) | Replaced by AgentPipeline |
| `langgraph_nodes.py` (1120) | Old workflow system |
| `langgraph_builder.py` (425) | Old workflow system |
| `autogen_extension.py` (284) | Old multi-agent |
| `simpo_training_loop.py` (471) | Future feature, not used |

**Total removable**: ~5,813 lines of dead code

---

## New Components Needed

| Component | Purpose | Estimated lines |
|-----------|---------|----------------|
| `OnboardingModal.tsx` | First-open project picker (replaces OnboardingOverlay) | ~150 |
| `RoadmapDAG.tsx` | Level 1 project map visualization | ~200 |
| `MatryoshkaNavigator.tsx` | Zoom-level state machine (L1->L2->L3->L4) | ~120 |
| `RailsActionBar.tsx` | Bottom bar with <=3 contextual actions | ~100 |
| `mcc_handler.py` | Backend: /api/mcc/init, /api/project/init | ~200 |
| `roadmap_generator.py` | Architect generates Roadmap DAG from project scan | ~300 |
| `project_config.py` | Config model + persistence | ~100 |
| **Total new** | | **~1,170 lines** |

---

## API Changes

### New endpoints:

```
POST /api/project/init          — First open: copy project, index, generate roadmap
GET  /api/mcc/init              — Load project_config + session_state + roadmap
POST /api/mcc/state             — Save session state (level, selection)
GET  /api/roadmap               — Get roadmap DAG
POST /api/roadmap/generate      — Architect generates/updates roadmap
GET  /api/roadmap/{node}/tasks  — Tasks of a specific module
POST /api/playground/init       — Create single project playground
DELETE /api/playground           — Delete playground (recreatable)
GET  /api/playground/status      — Quota usage, health
```

### Keep existing:
- All analytics endpoints (152.2)
- Task board CRUD
- Pipeline execution
- Chat endpoints
- Config endpoints

---

## State Machine: Navigation Levels

```
                    +--------+
                    | ONBOARD|  (no config)
                    +---+----+
                        |
                        v
                 +------+------+
          +----->|  L1 ROADMAP |<-----+
          |      +------+------+      |
          |             |             |
          |   click     | click       |
          |   node      | node        |
          |             v             |
          |      +------+------+      |
          +------+  L2 TASKS  +------+
          back   +------+------+ back
                        |
              dbl-click | task
                        v
                 +------+------+
          +------+ L3 WORKFLOW +------+
          | back +------+------+ back |
          |             |             |
          |    execute  |             |
          |             v             |
          |      +------+------+      |
          +------+ L4 RUNNING  +------+
                 +------+------+
                        |
                  done  |
                        v
                 +------+------+
                 | L4.5 RESULT |
                 +-------------+
                   apply/reject
                        |
                        v
                   back to L2/L3
```

Each level stores its state in `session_state.json`.
On restart, user returns to exact position.

---

## DAGExecutor Bridge (BMAD Integration)

Phase 150 built `dag_executor.py` (993 lines) — Kahn's BFS topological sort engine.
It already knows how to execute DAG nodes (parallel, condition, feedback edges).

### How Matryoshka connects to DAGExecutor:

```
Level 1 (Roadmap DAG):
  Nodes = modules/phases. NOT executable. Static map.
  Generated by Architect LLM. Saved as roadmap_dag.json.
  Purpose: navigation only.

Level 2 (Tasks):
  Nodes = tasks. Managed by TaskBoard (task_board.py).
  Each task has: title, description, priority, team preset.
  Dispatched to agent_pipeline.py for execution.

Level 3 (Workflow DAG):
  Nodes = agent roles (Scout, Architect, Coder, Verifier).
  THIS is where DAGExecutor runs.
  BMAD template (data/templates/bmad_workflow.json) defines the flow.
  DAGExecutor.execute() walks the graph, calls agent_pipeline methods.

Connection:
  TaskBoard.dispatch_task(task_id)
    -> agent_pipeline.execute(task, preset)
      -> DAGExecutor.execute(bmad_template, task_context)
        -> Each node runs its agent (Scout, Architect, etc.)
```

### What this means for Phase 153:

- Roadmap DAG: NEW (generated by Architect, navigational only)
- Task dispatch: EXISTS (TaskBoard + agent_pipeline, battle-tested)
- Workflow DAG execution: EXISTS (DAGExecutor + BMAD, Phase 150)
- We just need to CONNECT them: Roadmap node -> task list -> dispatch -> BMAD execute

---

## Playground v2: Source Types

### Local project (no git):
```
source_type: "local"
source_path: "/Users/user/my-project"
copy_method: shutil.copytree() or rsync (if available)
```

### Git project:
```
source_type: "git"
source_path: "git@github.com:user/repo.git"
copy_method: git clone --depth=1
```

### Remote project (Phase 154+):
```
source_type: "remote"
source_path: "ssh://user@server:/path/to/project"
copy_method: rsync -az --progress
agent_execution: on remote server OR local sandbox
```

Remote support is Phase 154 because it needs:
- SSH key management
- Network error handling
- Sync direction (push results back?)
- Agent execution location decision

For Phase 153: local + git only. Remote is documented but not implemented.

---

## Keyboard Shortcuts

Every level has shortcuts matching the 3 actions:

| Level | Key 1 | Key 2 | Key 3 |
|-------|-------|-------|-------|
| Roadmap | Enter = drill node | C = chat | S = settings |
| Tasks | Enter = drill task | A = accept plan | Esc = back |
| Workflow | Enter = execute | E = edit team | Esc = back |
| Running | Space = stop | V = view stream | Esc = back |
| Results | Enter = apply | R = reject | Esc = back |

Global:
- Esc = go back one level (always)
- F = expand current panel to fullscreen
- ? = show shortcuts overlay

---

## Error Handling

### LLM failures (Roadmap generation, Architect):
```
Try LLM call (3 retries with exponential backoff)
  -> Success: parse JSON, validate structure
  -> Failure: show toast "Architect unavailable"
  -> Fallback: "Manual mode" — user can create roadmap nodes manually
     (same as current workflow editor, but for roadmap)
```

### Playground creation failures:
```
Try copy project
  -> Success: index in Qdrant
  -> Failure (disk space): show quota error, suggest cleanup
  -> Failure (permissions): show permission error, suggest path
  -> Failure (git clone): show network error, suggest local path
```

### Pipeline execution failures:
```
Already handled by agent_pipeline.py (Phases 122-127):
  - Verifier retry loop (max 2 retries)
  - Tier upgrade (bronze -> silver -> gold)
  - Architect escalation (re-plan on major failures)
  - Graceful degradation (verifier errors default to pass)
```

---

## Frontend Tech Decisions (from Grok Research)

### React Flow zoom (R1):
Use `useReactFlow().setViewport()` with `{ duration: 300 }` for animated transitions.
NO GSAP dependency — React Flow handles animation natively.
For nested DAG: swap node/edge data, call fitView() after data change.

### Zustand persistence (R2):
```ts
// Custom storage that syncs to server
const serverStorage = {
  getItem: async () => (await fetch('/api/mcc/state')).json(),
  setItem: debounce(async (_, value) => {
    fetch('/api/mcc/state', { method: 'POST', body: JSON.stringify(value) });
  }, 500),
};
// localStorage as offline fallback
```

### Tauri file dialog (R4):
```ts
import { open } from '@tauri-apps/api/dialog';
// Fallback: <input type="file" webkitdirectory> for non-Tauri
```

### Architect prompts (R5):
Few-shot examples in prompt. Strict JSON output format.
Post-LLM validation: check nodes array, edges array, valid references.

---

## Future (Phase 154+)

These are documented but NOT part of Phase 153:

1. **Multi-project support** — ProjectsManager, project switcher dropdown
2. **Remote projects** — SSH/rsync source type, remote agent execution
3. **Collaborative editing** — Multiple users on same Roadmap DAG
4. **AI model marketplace** — User can add custom models for team roles
5. **Template library** — Pre-built BMAD workflows for common tasks
6. **VETKA extrapolation** — Matryoshka DAG-in-DAG reused in VETKA 3D chat
7. **Localization** — Russian/English UI toggle
