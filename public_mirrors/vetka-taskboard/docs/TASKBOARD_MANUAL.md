# TaskBoard Manual — Phase 200
## Operator's Guide for VETKA Multi-Agent Task System
**MARKER_200.TB_MANUAL**

Дата создания: 2026-03-27
Автор: Epsilon (QA Engineer 2)
Companion to: `ARCHITECTURE_TASKBOARD_BIBLE.md` (Zeta) и `TASKBOARD_ARCHITECTURE_BIBLE.md` (Epsilon)

Этот документ — инструкция по эксплуатации TaskBoard для агентов и Commander.
Architecture Bible описывает КАК устроено. Этот мануал описывает КАК ПОЛЬЗОВАТЬСЯ.

---

## 1. Architecture Overview

TaskBoard — SQLite-based priority queue, единственный координатор для 14 MCP процессов (6 VETKA + 6 Mycelium + Flask API + heartbeat). Каждый агент (Alpha через Epsilon + Zeta + Commander) читает и пишет задачи через один общий файл `data/task_board.db`.

### Три ключевых свойства

1. **Singleton per process** — один `TaskBoard()` объект на MCP-процесс, доступ через `get_task_board()`
2. **Write-through cache** — пишем в SQL, потом обновляем кэш `self.tasks`; читаем из кэша (быстро)
3. **WAL mode** — параллельные чтения не блокируют запись, запись <1ms per row

### Компоненты

```
data/task_board.db          ← SQLite WAL, 3 таблицы (tasks, settings, meta) + FTS5
src/orchestration/task_board.py  ← TaskBoard class (3167 строк)
src/mcp/tools/task_board_tools.py ← MCP handler handle_task_board() (1138 строк)
```

---

## 2. Data Model

### Indexed Columns vs Extra JSON

TaskBoard использует гибридную схему: 19 колонок с SQL-индексами для быстрого WHERE/ORDER BY, и один `extra TEXT` столбец для JSON blob со всеми остальными полями.

**Правило:** Если поле используется в SQL WHERE/ORDER BY — оно живет в SQL колонке. Все остальное — в `extra`.

### Indexed Columns (19)

`id`, `title`, `description`, `priority`, `status`, `phase_type`, `complexity`, `project_id`, `assigned_to`, `agent_type`, `assigned_at`, `created_by`, `created_at`, `started_at`, `completed_at`, `closed_at`, `commit_hash`, `commit_message`, `updated_at`

### Ключевые поля в Extra

`tags`, `dependencies`, `allowed_paths`, `blocked_paths`, `completion_contract`, `implementation_hints`, `architecture_docs`, `recon_docs`, `closure_tests`, `closure_files`, `role`, `domain`, `execution_mode`, `status_history`, `failure_history`, `branch_name`, `merge_result`, `closure_proof`, `module`, `source`, `protocol_version`

### Task Lifecycle Statuses

```
pending → claimed → done_worktree → verified → done_main
                        │                 │
                        → need_qa ────────┘
                        │
                    needs_fix → claimed (re-claim)

pending → queued (max_concurrent reached) → claimed
claimed → running (pipeline dispatch)
running → done_main | failed → pending (retry)
any → cancelled
```

**14 валидных статусов:** `pending`, `queued`, `claimed`, `running`, `done`, `done_worktree`, `done_main`, `failed`, `cancelled`, `hold`, `pending_user_approval`, `verified`, `needs_fix`, `need_qa`

---

## 3. Read Path

### `get_queue(status)` — Bulk read

Читает из in-memory кэша `self.tasks`. Сортирует по `(priority, created_at)`.

- Вызывается 7+ раз в `session_init` (по одному на каждый status bucket)
- 450 задач из кэша = <1ms
- **НИКОГДА через SQL** — это красная линия (см. Architecture Bible S12)

### `get_task(task_id)` — Point read

Читает из SQL (`SELECT WHERE id=?`), обновляет кэш. Используется перед claim/complete для свежести.

### `search_fts(query)` — Full-text search

FTS5 запрос по `tasks_fts` virtual table. Поддерживает:
- `fix AND crash` — оба слова
- `"database lock"` — точная фраза
- `task*` — prefix match

### `get_board_summary()` — Aggregate

SQL `SELECT status, COUNT(*) GROUP BY status` + preview следующей задачи.

---

## 4. Write Path

### `_save_task(task)` — Atomic write

Единственный метод записи в SQL. `INSERT OR REPLACE` одной строки. <1ms.

Инвариант: после SQL write ОБЯЗАТЕЛЬНО обновляет `self.tasks[id]` и вызывает `_index_task_fts(task)`.

### Цепочка вызовов

| Операция | Вызывает | SQL | Кэш |
|----------|----------|-----|------|
| `add_task()` | `_save_task()` | INSERT | `self.tasks[id] = task` |
| `update_task()` | `_save_task()` | REPLACE | modifies `self.tasks[id]` |
| `claim_task()` | `update_task()` | REPLACE | через `update_task()` |
| `complete_task()` | `update_task()` | REPLACE | через `update_task()` |
| `verify_task()` | `update_task()` | REPLACE | через `update_task()` |
| `remove_task()` | `_delete_task()` | DELETE | `del self.tasks[id]` |

---

## 5. Init Sequence

```
__init__(board_file=None)
    1. self.db = self._connect()           # WAL + busy_timeout=5000
    2. self._ensure_schema()                # CREATE TABLE IF NOT EXISTS
    3. self._migrate_json_to_sqlite()       # One-time migration (if DB empty)
    4. self.settings = self._load_settings() # SELECT * FROM settings
    5. self.tasks = self._load_all_tasks()   # SELECT * FROM tasks → cache
    6. self._backfill_modules()              # Auto-assign module (per-task writes)
```

### Что НЕЛЬЗЯ добавлять в init

- **Bulk writes** (INSERT/UPDATE loops) — 14 процессов стартуют одновременно
- **FTS backfill** — уже перенесен в `action=backfill_fts`
- **WAL checkpoint** — WAL самоуправляется
- **Любая операция > 100ms**

POSTMORTEM Phase 199: `_backfill_fts()` в init вызвал DB lock storm с 14 MCP процессами. Каждый пытался переиндексировать 400+ задач. Результат: 60+ секунд session_init.

---

## 6. Concurrency Contract

### WAL mode

```python
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=5000")
```

- Readers не блокируют writers
- Writers очередь: <1ms per write, 14 writers = 14ms worst case
- 5000ms busy_timeout = 350x safety margin

### Безопасные операции

| Паттерн | Почему безопасен |
|---------|-----------------|
| Single-row INSERT OR REPLACE | <1ms, атомарный |
| SELECT без транзакции | WAL readers не блокируют |
| `_load_all_tasks()` в init | Read-only |
| `_ensure_schema()` с DDL fast-path | Идемпотентный |

### Опасные операции (ЗАПРЕЩЕНЫ)

| Anti-pattern | Проблема |
|-------------|----------|
| Bulk writes в `__init__` | N processes x M writes = lock storm |
| `timeout=30` в connect() | 30s hang вместо fail-fast |
| `busy_timeout=30000` | Маскирует проблему |
| `_execute_with_retry` с sleep | Добавляет latency поверх busy_timeout |
| `isolation_level=None` | Каждый INSERT auto-commits (50x медленнее) |

---

## 7. Integration Points

### MCP Tools — `task_board_tools.py`

Основной entry point: `handle_task_board(arguments)`. Все транспорты вызывают эту функцию.

```
MCP VETKA (stdio, :5001) ──┐
MCP Mycelium (WS, :8082) ──┼──→ handle_task_board() ──→ TaskBoard singleton
REST API (:5001) ───────────┘
```

### session_init

Вызывает `get_queue()` 7+ раз (по status bucket), `get_active_agents()`, `get_board_summary()`. Все через кэш. Target: <2s total.

### protocol_guard

Проверяет `task_claimed` flag в session state. Вызывается на каждый Edit/Write tool call.

### git_tool

`auto_complete_by_commit()` — после commit ищет `[task:tb_xxxx]` в commit message и авто-закрывает совпадающие задачи.

### smart_debrief

Debrief Q1-Q3 инжектируется в `action=complete` через `_inject_debrief()`.

### heartbeat

`get_queue()` каждые 30-60 секунд. Использует кэш.

---

## 8. Performance Invariants

| Метрика | Target | Метод проверки |
|---------|--------|---------------|
| `session_init` total | <2s | End-to-end timing |
| `claim_task()` | <100ms | Single claim с concurrent load |
| `get_queue()` | <10ms | Из кэша, без SQL |
| `_save_task()` | <5ms | Single INSERT OR REPLACE |
| 14 concurrent inits | <5s total | 14 threads, каждый создает TaskBoard |
| `__init__` single | <500ms | С 500 задачами в DB |
| `search_fts()` | <50ms | FTS5 query на 500 задачах |

---

## 9. NEVER DO List

Правила навечно. Каждое выучено на ошибке.

1. **Bulk writes в `__init__`** — Phase 199: 14-process deadlock
2. **`timeout > 5` в `sqlite3.connect()`** — Phase 199: 60s session_init
3. **`busy_timeout > 5000`** — маскирует проблему
4. **Retry loops с `time.sleep()`** — Phase 199: `_execute_with_retry()` добавляло 3.1s per write
5. **`get_queue()` через SQL когда кэш есть** — Phase 199/200: 3150 json.loads per session_init
6. **SQL WHERE на полях из `extra` JSON** — `module`, `domain`, `role` не SQL колонки
7. **`isolation_level=None`** — ломает batch transactions
8. **WAL checkpoint TRUNCATE в close() с concurrent readers** — requires exclusive lock
9. **Новые колонки в `tasks`** — используй `extra` JSON blob

---

## 10. FTS5 Search

### Схема

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
    task_id, title, description, tags, project_id,
    content='', contentless_delete=1
);
```

### Incremental indexing

Каждый `_save_task()` вызывает `_index_task_fts(task)` — один INSERT в FTS5 таблицу.
Каждый `_delete_task()` вызывает `_remove_task_fts(task_id)`.

### Manual backfill

`action=backfill_fts` — полный реиндекс. Вызывается ВРУЧНУЮ, **НИКОГДА в init**.

### Query sanitization

`search_fts()` strips special FTS5 characters перед запросом: `()`, `*`, `"`, `:`.

### Синтаксис запросов

| Запрос | Описание |
|--------|----------|
| `fix crash` | Содержит оба слова |
| `"database lock"` | Точная фраза |
| `fix OR bug` | Любое из слов |
| `task*` | Prefix match |

---

## Appendix A: Quick Reference — Common Operations

### Для агента: стандартный workflow

```
1. session_init(role="Alpha")        # Получить контекст
2. task_board action=list project_id=cut filter_status=pending  # Найти задачу
3. task_board action=claim task_id=tb_xxx  # Взять в работу
4. ... работа ...
5. task_board action=complete task_id=tb_xxx  # Закрыть с commit
   commit_message="fix: ..." q1_bugs="..." q2_worked="..." q3_idea="..."
```

### Для Commander: merge workflow

```
1. task_board action=list filter_status=done_worktree  # Найти готовые задачи
2. task_board action=verify task_id=tb_xxx verdict=pass  # QA gate
3. task_board action=merge_request task_id=tb_xxx  # Cherry-pick to main
   # или
   task_board action=batch_merge  # Merge все verified
```

### Для Commander: создание задачи

```
task_board action=add
  title="ALPHA-P1: Fix rendering pipeline"
  description="..."
  priority=2
  phase_type=fix
  project_id=CUT
  role=Alpha
  domain=engine
  architecture_docs=["docs/190.../RECON_xxx.md"]
  allowed_paths=["src/services/cut_render_engine.py"]
  completion_contract=["Render completes without error", "Tests pass"]
  implementation_hints="Check _build_filter_chain for the broken pipe"
```

### Для QA (Delta/Epsilon): верификация

```
task_board action=list filter_status=done_worktree  # QA queue
task_board action=get task_id=tb_xxx  # Полный контекст + docs
task_board action=verify task_id=tb_xxx verdict=pass notes="Diff reviewed, tests pass"
# или
task_board action=verify task_id=tb_xxx verdict=fail notes="Missing data-testid on button"
```

## Appendix B: DOC_GATE

Все `build`/`fix` задачи обязаны иметь `architecture_docs` или `recon_docs`.

- `research`/`test` — auto-exempt
- `force_no_docs=true` — bypass (rejected если >= 2 relevant docs найдены)
- Suggestions: `_suggest_docs_for_title()` ищет через `vetka_search_semantic` + glob

## Appendix C: execution_mode

| Mode | Agents | Что нужно для closure |
|------|--------|----------------------|
| `pipeline` | mycelium, dragon | pipeline_success + verifier >= 0.75 + tests pass + commit_hash |
| `manual` | claude_code, cursor, human, grok | commit_hash only |

Auto-inferred from `agent_type` at claim time.

## Appendix D: Project ID Smart Resolution

1. **Exact:** `CUT` → `CUT`
2. **Case-insensitive:** `cut` → `CUT`
3. **RU layout:** `СГЕ` → `CUT`
4. **Prefix:** `c` → `CUT`
5. **Ambiguous prefix:** `v` → `[vetka, vetka_pulse]`
