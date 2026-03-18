# RECON 189.B: Project → Task → DAG Auto-Binding
**Date:** 2026-03-18
**Phase:** 189
**Agent:** claude_code (Opus)
**Status:** COMPLETE

---

## 1. Вопрос

Когда пользователь подгружает существующий проект (например CUT) в MCC:
- Подгрузятся ли существующие таски автоматически?
- Выстроится ли DAG проекта со связями тасков → арх.доки → куски кода?
- Если нет — что нужно для этого?

---

## 2. Текущее состояние: что ЕСТЬ

### 2.1 Project Init (`/api/mcc/project/init`)
- Создаёт ProjectConfig (project_id, source_path, sandbox_path)
- Если playground → копирует проект в sandbox (без node_modules, .git)
- Регистрирует в `mcc_projects_registry.json`
- **НЕ сканирует task_board.json** в исходном проекте
- **НЕ импортирует таски** автоматически

### 2.2 Task → DAG Node Linking
Существует двойная привязка:
- `primary_node_id` — основной DAG-нод для таска
- `affected_nodes[]` — список связанных нодов
- `module` — roadmap-модуль для иерархии
- `architecture_docs[]` — привязанные арх.документы
- `recon_docs[]` — привязанные рекон-документы
- `closure_files[]` — файлы для верификации

**Endpoints:**
- `POST /api/mcc/tasks/create-attached` — создаёт таск привязанный к ноду
- `POST /api/mcc/tasks/{id}/attach-node` — привязывает существующий таск к ноду
- `_get_roadmap_node_snapshot()` — получает метаданные нода (docs, tags)

### 2.3 Import Script (ручной)
`scripts/import_taskboard_pack.py` — CLI для импорта JSON-пака тасков:
- Дедупликация по (title, workflow_family, task_origin)
- Сохраняет workflow metadata
- **НЕ интегрирован в UI/init flow**

### 2.4 TaskDAGView (визуализация)
- `client/src/components/mcc/TaskDAGView.tsx` — рендерит таски как DAG
- `GET /api/analytics/dag/tasks` — строит граф зависимостей
- Ноды показывают status, preset, phase_type, mini_stats
- Нет связей task → source code files (только через architecture_docs)

---

## 3. Текущее состояние: что НЕТ

| Отсутствующий элемент | Последствие |
|----------------------|-------------|
| Auto-scan task_board.json при project init | Таски внешнего проекта не подгружаются |
| Task → source files binding | DAG не показывает связи таск → код |
| Batch import endpoint в REST API | Нет UI для импорта |
| Roadmap auto-discovery | Roadmap.md в проекте не парсится |
| Architecture doc linking on import | Импортированные таски не привязаны к доками |

---

## 4. Пример: проект CUT

### CUT сегодня:
- **Backend:** `src/api/routes/cut_routes.py` (7818 строк, 156 функций)
- **Frontend:** `client/src/components/cut/` (26 компонентов)
- **Services:** 13 Python-модулей (cut_project_store, cut_scene_detector, etc.)
- **Arch docs:** Phase 190 (CUT_TARGET_ARCHITECTURE.md), Phase 185 (ROADMAP)
- **Contracts:** 15 JSON-схем (timeline, scene_graph, montage, etc.)
- **Фазовые таски:** Phase 185 roadmap определяет 14 тасков в 5 волнах

### Что произойдёт СЕЙЧАС при загрузке CUT:
1. ✅ Проект зарегистрируется в registry (source_path, sandbox_path)
2. ✅ Файлы скопируются в sandbox
3. ❌ Таски НЕ появятся в MiniTasks
4. ❌ DAG будет пустой — нет нодов для CUT
5. ❌ Architecture docs не привяжутся к таскам
6. ❌ Связи код ↔ таски не построятся

---

## 5. Что нужно для полной интеграции

### Level 1: Task Import (минимум)
**Цель:** При загрузке проекта — импортировать его таски

```
POST /api/mcc/project/init
  → scan source_path/data/task_board.json
  → import tasks with project_id = new_project_id
  → return imported_count in response
```

**Файлы:**
- `src/api/routes/mcc_routes.py` — добавить scan + import в init
- `scripts/import_taskboard_pack.py` — переиспользовать логику дедупликации
- Или новый сервис `src/services/project_task_import.py`

### Level 2: Roadmap Auto-Discovery
**Цель:** Найти roadmap.md → парсить → создать DAG-ноды

```
POST /api/mcc/project/init
  → scan source_path/docs/**/ROADMAP*.md
  → parse markdown → extract task titles + phases
  → create DAG nodes for each phase/section
  → attach imported tasks to matching nodes
```

**Файлы:**
- Новый сервис `src/services/roadmap_parser.py`
- `src/api/routes/mcc_routes.py` — вызов парсера после init

### Level 3: Code → Task → Doc Binding
**Цель:** Автоматические связи между файлами кода, тасками и документами

```
Source scan:
  → find MARKER_XXX comments in source code
  → match with task IDs / phase numbers
  → find architecture docs (ARCHITECTURE_*.md, RECON_*.md)
  → create edges: task → source_file, task → arch_doc
  → populate primary_node_id, affected_nodes, architecture_docs
```

**Файлы:**
- Новый сервис `src/services/project_graph_builder.py`
- Расширение `src/api/routes/mcc_routes.py`
- Frontend: расширение TaskDAGView для показа file-нодов

### Level 4: Live Sync
**Цель:** При изменении файлов проекта — обновлять DAG

```
File watcher / git hook:
  → detect changed files
  → update affected task nodes
  → re-scan MARKERs
  → push update через SocketIO
```

---

## 6. Рекомендованный план

| Этап | Scope | Effort | Зависимости |
|------|-------|--------|-------------|
| **L1: Task Import** | Scan + import task_board.json | Small | scripts/import_taskboard_pack.py |
| **L2: Roadmap Discovery** | Parse ROADMAP*.md → DAG nodes | Medium | L1 |
| **L3: Code Binding** | MARKER scan → edges | Large | L1, L2 |
| **L4: Live Sync** | File watcher + SocketIO | Large | L3 |

**Рекомендация:** Начать с L1 (task import при project init). Это даёт моментальную ценность — пользователь загружает проект и сразу видит его таски в MiniTasks. L2-L4 — следующие фазы.

---

## 7. Скриншот (user-provided)

14 тасков CUT на доске:
- Phase 0: CLEANUP (5 tasks, P1)
- Phase 1: SCRIPT SPINE (3 tasks, P2)
- Phase 2: DAG SPINE (3 tasks, P2)
- Phase 3: ROUTING (3 tasks, P2-3)

Эти таски **созданы Claude** (видно по tb_..._6 — tb_..._19 pattern). Они в task_board.json, но **не привязаны к MCC-проекту CUT** — у них нет `project_id`, поэтому сейчас видны только через ALL toggle.
