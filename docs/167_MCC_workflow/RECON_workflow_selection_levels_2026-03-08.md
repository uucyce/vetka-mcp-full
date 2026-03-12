# RECON REPORT — MYCELIUM Workflow Selection Levels

Date: 2026-03-08
Protocol stage: RECON+markers -> REPORT (NO IMPL)

## 1) Где и на каких уровнях выбирается workflow

### Level A — MCP execution type (не template library)
- `pm_to_qa | pm_only | dev_qa` задаются как `workflow_type` в MCP tools.
- Маркеры:
  - `src/mcp/tools/workflow_tools.py:62-66` (enum workflow_type)
  - `src/mcp/tools/workflow_tools.py:332-344` (vetka_execute_workflow)
  - `src/mcp/mycelium_mcp_server.py:318-325` (mycelium_execute_workflow schema)
  - `src/mcp/mycelium_mcp_server.py:660-668` (handler passthrough)
- Вывод: это уровень маршрута исполнения оркестратора, НЕ выбор `ralph_loop/g3/...`.

### Level B — Architect template library (core шаблоны)
- Источник шаблонов: `data/templates/workflows/*.json`.
- Загрузка/выбор: `WorkflowTemplateLibrary` + `select_workflow()`.
- Маркеры:
  - `src/services/architect_prefetch.py:30-34` (WORKFLOWS_DIR)
  - `src/services/architect_prefetch.py:63-69` (описание библиотеки)
  - `src/services/architect_prefetch.py:233-289` (селектор шаблона)
  - `src/services/architect_prefetch.py:447-457` (применение выбора в prefetch context)
- Вывод: здесь выбираются семейства вроде `ralph_loop`, `g3_critic_coder`, `bmad_default`.

### Level C — MCC API поверх template library
- MCC backend отдает библиотеку и конкретный template.
- Маркеры:
  - `src/api/routes/mcc_routes.py:741-755` (`GET /api/mcc/workflows`, `GET /api/mcc/workflows/{workflow_key}`)
  - `src/api/routes/mcc_routes.py:927-957` (`POST /api/mcc/prefetch` + diagnostics.workflow_selection)
- Вывод: backend умеет отдать template и показать, что выбрал prefetch.

### Level D — User-created workflow templates (отдельный контур)
- CRUD/execute для пользовательских DAG: `/api/workflows`.
- Хранение: `data/workflows/*.json`.
- Маркеры:
  - `src/api/routes/workflow_template_routes.py:18` (router `/api/workflows`)
  - `src/api/routes/workflow_template_routes.py:316-426` (execute bridge nodes->TaskBoard)
  - `src/services/workflow_store.py:50-54`, `src/services/workflow_store.py:60-67` (storage `data/workflows`)
- Вывод: это отдельный уровень от core template library.

## 2) Может ли выбирать/настраивать Architect

- Да, Architect-path (prefetch/captain) выбирает workflow автоматически.
- Маркеры:
  - `src/services/architect_prefetch.py:233-289` (правила выбора)
  - `src/services/architect_prefetch.py:447-457` (выбор в `prepare()`)
  - `src/services/architect_captain.py:238-241` (captain тоже вызывает `select_workflow`)
- Ограничение: это rule/heuristic selection; явного UI для ручного выбора именно family (`ralph/g3/...`) со стороны architect-node не найдено.

## 3) Может ли выбирать/настраивать пользователь

### Пользователь может:
- Выбирать preset/team в MCC UI.
- Менять модели ролей (включая architect role) и prompts.
- Запускать execute для конкретного сохраненного workflow ID.

Маркеры:
- Preset selector:
  - `client/src/components/mcc/PresetDropdown.tsx:49-57`, `:168-176`
- Execute с preset:
  - `client/src/store/useMCCStore.ts:573-580`
- Настройка ролей/моделей:
  - `client/src/components/mcc/RolesConfigPanel.tsx:43-47`, `:65-72`
  - `src/api/routes/pipeline_config_routes.py:18` (prefix `/api/pipeline`)
  - `src/api/routes/pipeline_config_routes.py:89-112` (`/presets/update-role`)
- Настройка prompt:
  - `src/api/routes/pipeline_config_routes.py:256-266`, `:276-290`

### Пользователь НЕ имеет явного активного runtime UI выбора workflow family
- В `TaskEditPopup` комментарий говорит про workflow template, но реальный UI даёт только `TEAM` и `PHASE`.
- Маркеры:
  - `client/src/components/mcc/TaskEditPopup.tsx:5` (комментарий)
  - `client/src/components/mcc/TaskEditPopup.tsx:154-207` (фактические controls)
- `WorkflowToolbar` с richer workflow operations помечен deprecated/forbidden in runtime.
- Маркеры:
  - `client/src/components/mcc/WorkflowToolbar.tsx:2-6`

## 4) Где представлены шаблоны в backend и UI

### Backend
- Core library files: `data/templates/workflows/` (пример: `bmad_default.json`, `ralph_loop.json`, `g3_critic_coder.json`, ...).
- User workflows: `data/workflows/`.

### UI
- В runtime MCC шаблоны в основном как fallback/визуализация выбранной задачи:
  - `client/src/components/mcc/MyceliumCommandCenter.tsx:2098-2115` (берёт `workflow_id`, грузит `/api/mcc/workflows/{key}`, fallback `bmad_default`)
- Family inference в UI есть (для отображения/логики), но это inference, не явный chooser:
  - `client/src/components/mcc/MyceliumCommandCenter.tsx:361-372`

## 5) Статус по ключевым шаблонам из запроса

- `solo ralph-loop`:
  - Реализован как `ralph_loop`.
  - `task_types` включает `solo`.
  - Маркер: `data/templates/workflows/ralph_loop.json:11`
- `G3`:
  - Реализован как `g3_critic_coder`.
  - Маркер: `data/templates/workflows/g3_critic_coder.json:2-3`, `:11`
- `MYCELIUM-pipeline`:
  - Найден как MCP tool `mycelium_pipeline` (исполнение pipeline), но НЕ как workflow template JSON в `data/templates/workflows/`.
  - Маркеры:
    - `src/mcp/mycelium_mcp_server.py:179` (tool)
    - `data/templates/workflows` (нет `mycelium_pipeline*.json`)

## 6) Gap/риски (по RECON)

1. Термин `workflow` перегружен минимум 4 сущностями (MCP workflow_type, template library key, user workflow DAG, runtime pipeline flow).
2. UI комментарии частично расходятся с реальным контролом (TaskEditPopup заявляет template edit, но поля template нет).
3. Ручной выбор family (`ralph/g3/...`) в активном MCC runtime интерфейсе неочевиден/ограничен; выбор часто backend-driven.

## 7) Узкий scope для следующего этапа IMPL (предложение, без выполнения)

1. Добавить явный monochrome selector workflow family в MCC (используя существующий стиль/NOLAN palette).
2. Привязать selector к `/api/mcc/workflows` + сохранить выбор в task metadata/workflow_id.
3. Гарантировать при execute приоритет user-selected family над heuristic fallback.
4. Сохранить совместимость с deprecated surface lock (не возвращать WorkflowToolbar в runtime path).

