# RECON 189.C: Full Chain Audit — Project → Tasks → DAG
**Date:** 2026-03-18
**Phase:** 189
**Agent:** claude_code (Opus)
**Status:** COMPLETE — CRITICAL GAPS FOUND

---

## Сценарий

Пользователь создаёт проект CUT в MCC (указывает папку vetka_live_03).
Ожидает: таски с `project_id: "cut"` появятся в MiniTasks, DAG покажет структуру.

---

## 1. Полная цепочка (текущее состояние)

```
USER: Создаёт проект в FirstRunView
  │
  ├─[1] POST /api/mcc/project/init
  │     source_path, execution_mode, project_name
  │     ├─ execution_mode = "playground" → shutil.copytree() в sandbox
  │     ├─ execution_mode = "local_workspace" → НЕ копирует, работает in-place
  │     ├─ ProjectConfig.create_new() → project_id (UUID)
  │     ├─ upsert_project(config, set_active=True) → registry
  │     └─ ❌ НЕ сканирует task_board.json
  │
  ├─[2] Frontend: initMCC(project_id)
  │     ├─ GET /api/mcc/init → project_config, session_state
  │     ├─ set activeProjectId = project_id
  │     └─ set navLevel = 'roadmap'
  │
  ├─[3] Frontend: refreshProjectTabs()
  │     ├─ GET /api/mcc/projects/list → tab list
  │     └─ Tab CUT появляется в UI ✅
  │
  ├─[4] Frontend: drillDown('roadmap')
  │     └─ Переход на roadmap level
  │
  ├─[5] useRoadmapDAG(scopePath, projectId) → DAG
  │     ├─ Пробует: build-design → condensed L2 → tree → legacy roadmap
  │     ├─ Если нет дизайн-графа → fallback на file tree
  │     └─ DAG показывает файловую структуру или пустой граф
  │
  ├─[6] MiniTasks mount → fetchTasks()
  │     ├─ GET /api/debug/task-board?project_id=<cut>
  │     ├─ Backend: фильтрует task.project_id == "cut" OR пустой
  │     └─ Возвращает таски с project_id="cut" + unassigned
  │
  └─[7] TaskDAGView (если открыт)
        ├─ GET /api/analytics/dag/tasks?limit=50
        ├─ ❌ НЕ передаёт project_id
        └─ Показывает ВСЕ таски, не только CUT
```

---

## 2. Найденные разрывы (CRITICAL)

### BUG 1: fetchTasks не вызывается при смене проекта
**Файл:** `useMCCStore.ts:1045-1063` (activateProjectTab)
**Проблема:** `activateProjectTab()` НЕ вызывает `fetchTasks()` после смены activeProjectId.
**Эффект:** Пользователь переключает tab → видит старые таски до ручного refresh.
**Фикс:** Добавить `await get().fetchTasks()` после initMCC.

### BUG 2: TaskDAGView не фильтрует по project_id
**Файл:** `analytics_routes.py:262` + `TaskDAGView.tsx:99`
**Проблема:** `/api/analytics/dag/tasks` не принимает `project_id` → показывает ВСЕ таски.
**Эффект:** DAG тасков показывает все проекты смешанно.
**Фикс:** Добавить `project_id` param в endpoint + передавать из frontend.

### BUG 3: MCP tool не фильтрует по project_id
**Файл:** `task_board_tools.py:242-261`
**Проблема:** `vetka_task_board action=list` возвращает все таски без project filter.
**Эффект:** Localguys видят таски всех проектов, могут взять чужой.
**Фикс:** Добавить `project_id` param в MCP list action.

### GAP 4: Architecture docs не показываются на DAG
**Проблема:** `architecture_docs` — это metadata в таске, не отдельные ноды на DAG.
**Эффект:** Нет визуальных связей task → doc → code.
**Статус:** Design decision — может быть OK для первой версии.

### GAP 5: Нет auto-import тасков при project init
**Проблема:** Project init не сканирует task_board.json.
**Эффект:** Новый проект всегда пустой — таски нужно создавать вручную.
**Для CUT:** Не актуально — таски уже в общем task_board.json с project_id="cut".

---

## 3. Playground vs Direct Mode

### execution_mode = "playground" (default)
```
source_path ──copy──→ sandbox_path (playground/{project_id}/)
                       ↑ code changes here
                       ↑ worktree для каждого агента
                       ↑ verifier merge gate
```
- ✅ Безопасно: оригинал не трогается
- ✅ Worktree isolation для агентов
- ✅ Merge через верификатора
- ❌ task_board.json НЕ копируется (в .gitignore → shutil тоже пропускает data/)

### execution_mode = "local_workspace"
```
source_path ← работаем in-place
              ↑ code changes directly
              ↑ нет sandbox
```
- ✅ Без копирования — быстро
- ⚠️ Изменения напрямую в проекте
- ✅ task_board.json доступен если в source_path/data/
- ❌ Нет worktree isolation (опасно для multi-agent)

### В ОБОИХ случаях:
- ✅ Проект регистрируется в registry
- ✅ Tab появляется
- ✅ Таски с matching project_id видны
- ❌ task_board.json НЕ сканируется
- ❌ DAG тасков не фильтруется по проекту

---

## 4. Что для CUT-проекта работает УЖЕ

Поскольку 28 тасков уже в общем `data/task_board.json` с `project_id: "cut"`:

| Шаг | Работает? | Примечание |
|-----|-----------|------------|
| Создать проект CUT в MCC | ✅ | project/init, sandbox или direct |
| Tab CUT появится | ✅ | refreshProjectTabs |
| Таски CUT в MiniTasks | ⚠️ | Только после ручного open MiniTasks (BUG 1) |
| All toggle показывает все | ✅ | MARKER_189.6A |
| Project badge на тасках | ✅ | MARKER_189.3A |
| Agent badge | ✅ | MARKER_189.3B |
| DAG тасков scoped по CUT | ❌ | BUG 2 — не фильтрует |
| Roadmap DAG | ⚠️ | Зависит от наличия build-design графа |
| Localguys берут CUT таски | ❌ | BUG 3 — MCP не фильтрует |

---

## 5. План исправлений (приоритет)

### P0: BUG 1 — fetchTasks after project switch
```
Файл: useMCCStore.ts (activateProjectTab)
Добавить: await get().fetchTasks() после initMCC
Effort: 1 line
```

### P0: BUG 2 — TaskDAG project filter
```
Файл: analytics_routes.py (dag/tasks endpoint)
Добавить: project_id param + filter
Файл: TaskDAGView.tsx
Добавить: передать activeProjectId в запрос
Effort: ~10 lines
```

### P1: BUG 3 — MCP project filter
```
Файл: task_board_tools.py (list action)
Добавить: project_id filter param
Effort: ~5 lines
```

### P2: Architecture docs on DAG
```
Отдельная фаза — дизайн-решение нужно
```

---

## 6. Вывод

**CUT в MCC будет работать** после трёх багфиксов (BUG 1-3). Таски уже есть, project_id уже назначен. Основные разрывы — в frontend refresh при смене проекта и отсутствии project filter в TaskDAG и MCP.

**Для будущих пользователей (сценарий "чёрный ящик"):**
- Создают проект → tab появляется
- Если таски есть с правильным project_id → видят сразу
- Если тасков нет → создают через UI или MCP с auto-project_id
- DAG строится из тасков + их зависимостей
- Localguys берут таски через MCP с project filter
