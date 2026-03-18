# RECON 189: MCC TaskBoard ↔ Project Integration
**Date:** 2026-03-18
**Phase:** 189
**Agent:** claude_code (Opus)
**Status:** COMPLETE

---

## 1. Scope

Привязка задач TaskBoard к проектам MCC. Старые таски закрываются по текущей схеме, новые — через project binding с загрузкой зависимых файлов на DAG нового проекта.

**Принципы:**
- backward compatible — `project_id` опциональный
- auto-complete из зарегистрированных проектов
- если проект не найден — предложить создать в MCC
- показать `agent_type` (claude_code, localguys, etc.)

---

## 2. Обследованные файлы

### Backend

| Файл | Роль | Состояние `project_id` |
|------|------|------------------------|
| `src/orchestration/task_board.py` | Core task storage (JSON) | ✅ Хранит `project_id`, `project_lane` в каждом таске |
| `src/api/routes/taskboard_routes.py` | REST API `/api/taskboard/*` | ✅ `project_id` в `_CREATE_FIELDS` (line 48) |
| `src/orchestration/taskboard_adapters.py` | Adapter layer | ✅ Пробрасывает все поля через `board.add_task()` |
| `src/services/mcc_project_registry.py` | Project registry | ✅ `_load_registry()`, `active_project_id`, массив `projects[]` |
| `src/api/routes/mcc_routes.py` | MCC API | ✅ `/api/mcc/projects/list` уже работает |

### Frontend

| Файл | Роль | Состояние |
|------|------|-----------|
| `client/src/components/panels/TaskCard.tsx` | `TaskData` interface | ⚠️ Есть `agent_type?` (line 54), НЕТ `project_id` |
| `client/src/components/mcc/MiniTasks.tsx` | Compact task list | ❌ Нет project badge, нет agent_type icon, нет project filter |
| `client/src/store/useMCCStore.ts` | Store | Нужно проверить — может уже тянет project_id из API |

### Tests

| Файл | Покрытие |
|------|----------|
| `tests/mcc/test_mcc_projects_registry_api.py` | Registry CRUD + list (line 76: `/api/mcc/projects/list`) |
| `tests/test_phase121_task_board.py` | Task board core |

---

## 3. Находки

### 3.1 Backend: project_id уже пробрасывается

`task_board.py` и `taskboard_routes.py` уже принимают и хранят `project_id`. При создании таска через MCP (`vetka_task_board action=add project_id=vetka`) — поле сохраняется корректно. Подтверждено GET на все 6 тасков фазы 189.

**Вывод:** Backend-часть 189.1 фактически готова. Нужна только фронтовая интеграция.

### 3.2 Registry endpoint уже существует

`/api/mcc/projects/list` — возвращает список проектов с `project_id`, `display_name`, `source_path` etc. Тест `test_mcc_projects_registry_api.py` подтверждает.

**Вывод:** Для 189.2 не нужен новый эндпоинт. Фронт может использовать существующий.

### 3.3 TaskData не знает о project_id

`TaskCard.tsx:TaskData` interface (line 35-70):
- ✅ `agent_type?: string` — есть
- ✅ `assigned_to?: string` — есть
- ❌ `project_id` — НЕТ
- ❌ `project_lane` — НЕТ

Backend возвращает эти поля, но TypeScript их не типизирует → фронт их игнорирует.

### 3.4 MiniTasks рендерит минимум

`MiniTasks.tsx` рендерит на каждый таск:
```
[status dot] [title] [assigned_to] [status text]
```

Нет: project badge, agent_type icon, project filter toggle.

### 3.5 Миграция: старые vs новые таски

Текущие 56 pending тасков не имеют `project_id` (или имеют `project_id: "vetka"` по умолчанию). Стратегия:
- **Старые таски** → закрываются по текущей схеме, без обязательного project binding
- **Новые таски** → при создании должны привязываться к проекту, загружать зависимые файлы на DAG проекта

---

## 4. Зависимости между тасками

```
189.1 (project_id в TaskData)
  ↓
189.3 (badges в MiniTasks)  ←──── 189.2 (auto-complete из registry)
  ↓
189.6 (All Projects toggle)
  ↓
189.4 (Assign Projects button)
  ↓
189.5 (Create project from task)
```

### Рекомендованный порядок

1. **189.1** — TypeScript: добавить `project_id`, `project_lane` в `TaskData`
2. **189.3** — UI: project badge + agent_type icon в MiniTasks
3. **189.2** — Autocomplete: подключить `/api/mcc/projects/list` к task creation
4. **189.6** — Toggle: фильтр "All Projects" / active project
5. **189.4** — Batch assign: modal для unmapped тасков
6. **189.5** — Create project: prompt при unknown project_id

---

## 5. Точки входа для имплементации

### MARKER_189.1: TaskData project fields
- **Файл:** `client/src/components/panels/TaskCard.tsx`
- **Действие:** Добавить `project_id?: string`, `project_lane?: string` в `TaskData`
- **Риск:** Нулевой — опциональные поля

### MARKER_189.3A: MiniTasks project badge
- **Файл:** `client/src/components/mcc/MiniTasks.tsx`
- **Действие:** Рендерить project badge (цветной тег) рядом с title
- **Зависимость:** 189.1

### MARKER_189.3B: MiniTasks agent_type icon
- **Файл:** `client/src/components/mcc/MiniTasks.tsx`
- **Действие:** Иконка agent_type (claude_code=C, cursor=Cu, grok=G, etc.)
- **Зависимость:** `agent_type` уже в TaskData

### MARKER_189.2A: Project autocomplete endpoint wiring
- **Файл:** `client/src/store/useMCCStore.ts` (или новый хук)
- **Действие:** Fetch `/api/mcc/projects/list`, кеш в store
- **Зависимость:** endpoint уже работает

### MARKER_189.6A: MiniTasks project filter toggle
- **Файл:** `client/src/components/mcc/MiniTasks.tsx`
- **Действие:** Toggle "All" vs "Active project", filter по `project_id`
- **Зависимость:** 189.1, 189.3

### MARKER_189.4A: Assign Projects modal
- **Файл:** `client/src/components/mcc/MiniTasks.tsx` (или отдельный компонент)
- **Действие:** Modal: unmapped tasks + project selector + batch PATCH
- **Зависимость:** 189.2, 189.3

### MARKER_189.5A: Create project from task context
- **Файл:** `src/api/routes/taskboard_routes.py` + frontend
- **Действие:** При unknown project_id → suggest create → call `/api/mcc/project/init`
- **Зависимость:** 189.2

---

## 6. Стратегия миграции

```
OLD tasks (project_id empty or "vetka"):
  → close normally via task_board action=complete
  → no project_id validation required
  → gradual assignment via 189.4 batch modal (optional)

NEW tasks (created after 189.1 deployed):
  → project_id auto-suggested from registry
  → dependent files loaded to project DAG
  → project badge visible in MiniTasks
  → filtered by active project (189.6)
```

**Критерий:** `project_id` остаётся OPTIONAL. Таски без project_id продолжают работать как раньше. Новый функционал — additive only.
