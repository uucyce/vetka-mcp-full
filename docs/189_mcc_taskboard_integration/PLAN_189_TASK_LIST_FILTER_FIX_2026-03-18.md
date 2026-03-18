# PLAN 189.D: Task List Filter & Limit Fix
**Date:** 2026-03-18
**Phase:** 189
**Agent:** claude_code (Opus)

---

## 1. Архитектура (разъяснение)

### task_board.json — ОДИН на всех

```
data/task_board.json  ← ЕДИНСТВЕННЫЙ файл
       ↑
       │  читает/пишет
       │
  src/orchestration/task_board.py  ← ЕДИНСТВЕННЫЙ класс TaskBoard (singleton)
       ↑
       │  импортирует handle_task_board()
       │
  src/mcp/tools/task_board_tools.py  ← ЕДИНСТВЕННАЯ логика CRUD
       ↑                    ↑
       │                    │
  vetka MCP bridge     mycelium MCP server
  (stdio, port 5001)   (WS, port 8082)
       ↑                    ↑
       │                    │
  "vetka_task_board"   "mycelium_task_board"
  (local fallback)     (тот же handle_task_board!)
```

**Ключевое:**
- `task_board.json` — **один файл**, не два
- `handle_task_board()` — **одна функция**, вызывается из обоих MCP серверов
- `vetka_task_board` (local fallback) = `vetka_mcp_bridge.py:1779` → `handle_task_board()`
- `mycelium_task_board` = `mycelium_mcp_server.py:639` → тот же `handle_task_board()`
- **Любой фикс в `task_board_tools.py` автоматически работает через ОБА транспорта**

### Почему агент говорит "фильтр не работает"?

Не потому что код не исправлен, а потому что:
1. **MCP schema** (`TASK_BOARD_SCHEMA`) описывает `project_id` только для `add` action
2. Агент (Claude/Cursor) читает schema → не передаёт `project_id` при `list`
3. `handle_task_board()` получает `arguments` без `project_id` → фильтр не срабатывает
4. Плюс `tasks[:20]` обрезает выдачу → CUT-таски за 20й позицией невидимы

---

## 2. Обнаруженные проблемы

### P1: Schema не объясняет project_id для list
**Файл:** `src/mcp/tools/task_board_tools.py:62-63`
**Сейчас:** `filter_status` — единственный описанный фильтр для list
**Нужно:** Добавить `filter_project_id` или расширить описание `project_id`

### P2: Жёсткий лимит [:20]
**Файл:** `src/mcp/tools/task_board_tools.py:268`
**Сейчас:** `tasks[:20]` — hardcoded, не зависит от фильтрации
**Проблема:** При 83+ тасках, project-specific таски могут быть за лимитом
**Нужно:** Увеличить лимит после фильтрации, или сделать динамическим

### P3: count vs returned mismatch
**Сейчас:** `count: len(tasks)` (все), но `tasks: tasks[:20]` (обрезанные)
**Проблема:** Агент видит `count: 83` но получает 20 — думает что все 83 пришли

---

## 3. План имплементации

### Задача A: Обновить schema + добавить filter_project_id для list
```
Файл: src/mcp/tools/task_board_tools.py
Действия:
1. Изменить description у "project_id" в TASK_BOARD_SCHEMA:
   Было:  "Logical project ID for lane-aware multitask routing"
   Стало: "Logical project ID. For add: assigns project. For list: filters by project."

2. Или добавить явный "filter_project_id":
   "filter_project_id": {
     "type": "string", 
     "description": "Filter tasks by project_id (for list action)"
   }

Рекомендация: Вариант 1 проще — project_id уже есть в schema, 
нужно только описание расширить. Код фильтрации (MARKER_189.10C) 
уже читает arguments.get("project_id").
```

### Задача B: Динамический лимит
```
Файл: src/mcp/tools/task_board_tools.py
Действия:
1. После фильтрации project_id — лимит 40 (не 20)
2. Если project_id фильтр активен — лимит 50 (проект обычно < 50 тасков)
3. Добавить "limit" param в schema для агента
4. Исправить count/returned mismatch:
   "count": len(tasks),        ← всего с фильтром
   "returned": len(tasks[:N]), ← сколько в ответе
   "truncated": len(tasks) > N ← есть ли ещё
```

### Задача C: Mycelium schema sync
```
Файл: src/mcp/mycelium_mcp_server.py:220
Проблема: Mycelium может иметь свою копию schema
Проверить: использует ли он TASK_BOARD_SCHEMA из task_board_tools.py
           или свою копию
Если копия — синхронизировать
```

---

## 4. Что НЕ нужно делать

- ❌ Менять формат task_board.json — он общий
- ❌ Создавать второй task_board — он один
- ❌ Менять логику в handle_task_board() — она уже правильная (189.10C)
- ❌ Трогать mycelium handler — он делегирует в тот же handle_task_board()

---

## 5. Порядок выполнения

1. **Задача A** — schema fix (5 мин, 1 файл)
2. **Задача B** — dynamic limit + count/returned (10 мин, 1 файл)  
3. **Задача C** — mycelium schema check (5 мин, проверка)
4. **Тест** — запустить существующие + проверить через MCP

Итого: ~20 мин, 1 основной файл (`task_board_tools.py`)
