# TaskBoard Architecture Bible — Phase 200
## SINGLE SOURCE OF TRUTH
**MARKER_200.TB_BIBLE**

Дата создания: 2026-03-27
Последнее обновление: 2026-03-27
Автор: Epsilon (QA Engineer 2) — Claude Opus 4.6
Источник: `src/orchestration/task_board.py` (3167 строк), `src/mcp/tools/task_board_tools.py` (1138 строк)
Подпись: Agent Epsilon, claude/cut-qa-2, session 2026-03-27

Любое изменение TaskBoard ОБЯЗАНО пройти QA через этот документ.

---

## S1. НАЗНАЧЕНИЕ

TaskBoard — центральная очередь задач для координации мультиагентной разработки в экосистеме VETKA. Это единственная система, через которую все агенты (Claude Code, Cursor, Mycelium Pipeline, Grok, human) получают, исполняют и закрывают задачи.

### Роль в экосистеме

```
MCP VETKA (stdio, :5001) ──┐
                            ├──→ handle_task_board() ──→ TaskBoard (singleton)
MCP Mycelium (WS, :8082) ──┤                                    │
                            │                              SQLite (WAL)
REST API (:5001) ───────────┘                              data/task_board.db
```

- **MCP VETKA** — основной транспорт для Claude Code агентов (Alpha, Beta, Gamma, Delta, Epsilon)
- **MCP Mycelium** — транспорт для расширенных операций (search_fts, batch_merge, stale_check)
- **REST API** — UI доступ из MCC (Mission Control Center)
- **TaskBoard singleton** — единственный объект, управляющий очередью

### Почему критичен

14 MCP процессов одновременно обращаются к TaskBoard. Вся координация — кто что делает, где код, какие зависимости — проходит через эту единственную точку. Сбой TaskBoard = полная остановка мультиагентной разработки.

---

## S2. АРХИТЕКТУРА ДАННЫХ

### SQLite схема

Три таблицы: `tasks`, `settings`, `meta`.

#### Таблица `tasks`

| Колонка | Тип | Default | Описание |
|---------|-----|---------|----------|
| `id` | TEXT PRIMARY KEY | — | Формат: `tb_{unix_timestamp}_{counter}` |
| `title` | TEXT NOT NULL | — | Короткое название задачи |
| `description` | TEXT | `''` | Детальное описание |
| `priority` | INTEGER | `3` | 1=critical, 2=high, 3=medium, 4=low, 5=someday |
| `status` | TEXT | `'pending'` | Текущий статус (см. S6) |
| `phase_type` | TEXT | `'build'` | `build` / `fix` / `research` / `test` |
| `complexity` | TEXT | `'medium'` | `low` / `medium` / `high` |
| `project_id` | TEXT | `''` | Логический проект (e.g. `CUT`) |
| `assigned_to` | TEXT | `''` | Имя агента: `opus`, `cursor`, `dragon` |
| `agent_type` | TEXT | `''` | Тип: `claude_code`, `cursor`, `mycelium`, `grok`, `human` |
| `assigned_at` | TEXT | `''` | ISO timestamp назначения |
| `created_by` | TEXT | `''` | Кто создал: `claude-code`, `heartbeat` |
| `created_at` | TEXT NOT NULL | — | ISO timestamp создания |
| `started_at` | TEXT | `''` | ISO timestamp начала работы |
| `completed_at` | TEXT | `''` | ISO timestamp завершения |
| `closed_at` | TEXT | `''` | ISO timestamp закрытия |
| `commit_hash` | TEXT | `''` | Git commit, закрывший задачу |
| `commit_message` | TEXT | `''` | Первая строка commit message |
| `updated_at` | TEXT | `''` | Последнее обновление |
| `extra` | TEXT | `'{}'` | JSON blob для всех остальных полей |

#### Индексы

| Индекс | Колонка | Назначение |
|--------|---------|------------|
| `idx_tasks_status` | `status` | Фильтрация по статусу (get_queue, list) |
| `idx_tasks_priority` | `priority` | Сортировка по приоритету |
| `idx_tasks_project` | `project_id` | Фильтрация по проекту |
| `idx_tasks_assigned` | `assigned_to` | Поиск задач агента |

#### Таблица `settings`

| Колонка | Тип | Описание |
|---------|-----|----------|
| `key` | TEXT PRIMARY KEY | Ключ настройки |
| `value` | TEXT | JSON-сериализованное значение |

Текущие настройки: `max_concurrent` (default: 2), `auto_dispatch` (default: true), `default_preset` (default: `dragon_silver`).

#### Таблица `meta`

| Колонка | Тип | Описание |
|---------|-----|----------|
| `key` | TEXT PRIMARY KEY | Ключ метаданных |
| `value` | TEXT | Значение |

Используется для версионирования миграций и системных флагов.

### Extra JSON blob

Все поля задачи, не входящие в `INDEXED_COLUMNS`, хранятся в `extra` как JSON blob. Ключевые поля в extra:

| Поле | Тип | Описание |
|------|-----|----------|
| `tags` | `list[str]` | Теги для категоризации |
| `dependencies` | `list[str]` | ID задач-зависимостей |
| `allowed_paths` | `list[str]` | Файлы/директории, которые агент может менять |
| `blocked_paths` | `list[str]` | Файлы, запрещенные для агента |
| `completion_contract` | `list[str]` | Checklist приемочных критериев |
| `implementation_hints` | `str` | Подсказки для реализации |
| `architecture_docs` | `list[str]` | Ссылки на архитектурные документы |
| `recon_docs` | `list[str]` | Ссылки на recon-документы |
| `closure_tests` | `list[str]` | Shell-команды для closure proof |
| `closure_files` | `list[str]` | Файлы для scoped auto-commit |
| `role` | `str` | Callsign агента (Alpha, Beta, Gamma, Delta, Epsilon, Commander) |
| `domain` | `str` | Домен задачи (engine, media, ux, qa, architect) |
| `execution_mode` | `str` | `pipeline` (полная верификация) / `manual` (commit_hash only) |
| `status_history` | `list[dict]` | Лог всех переходов статуса (max 50 записей) |
| `failure_history` | `list[dict]` | История неудачных попыток (max 5) |
| `branch_name` | `str` | Git branch (e.g. `claude/cut-engine`) |
| `merge_result` | `dict` | Результат merge_request |
| `closure_proof` | `dict` | Доказательство закрытия (commit_hash, tests, verifier) |
| `module` | `str` | Auto-assigned roadmap module |
| `source` | `str` | Откуда создана: `mcp`, `manual`, `imported` |
| `protocol_version` | `str` | Default: `multitask_mcp_v1` |

---

## S3. SINGLETON + КЭШИРОВАНИЕ

### Паттерн

```
SQLite = durable storage (authoritative)
self.tasks: Dict[str, dict] = read cache (performance)
```

TaskBoard — singleton через `get_task_board()`. Один инстанс на весь MCP-процесс.

### `__init__` последовательность

```python
def __init__(self, board_file=None):
    1. self.db = self._connect()          # SQLite с WAL + busy_timeout=5000
    2. self._ensure_schema()              # CREATE TABLE IF NOT EXISTS (идемпотент)
    3. self._migrate_json_to_sqlite()     # Одноразовая миграция из JSON (если DB пустая)
    4. self.settings = self._load_settings()  # SELECT * FROM settings
    5. self.tasks = self._load_all_tasks()    # SELECT * FROM tasks → dict cache
    # _backfill_modules() УБРАН из init (Phase 200 fix) → action=backfill_modules
```

**ПРАВИЛО: `__init__` НИКОГДА не делает bulk writes.** ТОЛЬКО reads. POSTMORTEM Phase 199: `_backfill_fts()` в `__init__` вызвал DB lock storm с 14 MCP процессами. `_backfill_modules()` вызывал ту же проблему — перенесен в `action=backfill_modules`.

### Cache coherence

Каждая запись обновляет обе стороны:
- `_save_task(task)` → INSERT OR REPLACE в SQLite + обновление `self.tasks[id]` + FTS5 index
- `get_task(id)` → SELECT из SQLite → обновляет `self.tasks[id]`
- `get_queue()` → читает из кэша `self.tasks` (Phase 200 fix Зеты), сортирует по `(priority, created_at)`

---

## S4. CONCURRENCY MODEL

### WAL mode

```python
conn.execute("PRAGMA journal_mode=WAL")
```

WAL (Write-Ahead Logging) позволяет параллельное чтение и запись. Readers не блокируют writers, writers не блокируют readers. Только writer-writer конфликты ждут busy_timeout.

### busy_timeout=5000

```python
conn.execute("PRAGMA busy_timeout=5000")
```

5 секунд достаточно потому что:
- 14 процессов * <1ms per write = 14ms worst-case queue time
- Каждый write = 1 INSERT OR REPLACE (атомарный, <1ms)
- Нет транзакций длиннее одной строки в hot path

### Правила concurrency

1. **Никаких bulk writes в hot path** (`__init__`, `session_init`, `get_queue`)
2. **busy_timeout = 5000** (5s), не больше
3. **timeout в `sqlite3.connect()` = default** (не 30)
4. **Каждый write = одна строка** (`_save_task` = один INSERT OR REPLACE)
5. **WAL mode обязателен** — без WAL 14 процессов deadlock за секунды
6. **`check_same_thread=False`** — MCP handler может вызвать из любого потока

---

## S5. API — ВСЕ ACTIONS

Обработчик: `handle_task_board(arguments)` в `task_board_tools.py:274`.
Сигнатура: `arguments: Dict[str, Any]` → `Dict[str, Any]`.

### `add`

Создает новую задачу.

| Параметр | Тип | Обязательный | Описание |
|----------|-----|-------------|----------|
| `title` | str | да | Название задачи |
| `description` | str | нет | Детальное описание |
| `priority` | int | нет | 1-5 (default: 3) |
| `phase_type` | str | нет | `build`/`fix`/`research`/`test` |
| `complexity` | str | нет | `low`/`medium`/`high` |
| `project_id` | str | нет | Проект (`CUT`, `PARALLAX`) |
| `tags` | list[str] | нет | Теги |
| `role` | str | нет | Callsign агента |
| `domain` | str | нет | Домен задачи |
| `architecture_docs` | list[str] | нет* | Архитектурные документы |
| `recon_docs` | list[str] | нет* | Recon-документы |
| `allowed_paths` | list[str] | нет | Разрешенные файлы |
| `completion_contract` | list[str] | нет | Критерии приемки |
| `implementation_hints` | str | нет | Подсказки |
| `force_no_docs` | bool | нет | Bypass DOC_GATE |

*DOC_GATE: `build`/`fix` задачи обязаны иметь хотя бы один doc. `research`/`test` авто-exempt.

**Что делает:**
1. DOC_GATE validation (suggest docs если нет)
2. `apply_task_profile_defaults()` если profile=p6
3. `board.add_task()` → генерирует ID, нормализует поля, пишет в SQLite + кэш
4. Emits SocketIO event `added`

**Возвращает:** `{success, task_id, message}`

### `list`

Список задач с фильтрацией.

| Параметр | Тип | Описание |
|----------|-----|----------|
| `filter_status` | str | Фильтр по статусу |
| `project_id` | str | Smart filter (case-insensitive, RU layout fix, prefix match) |
| `limit` | int | Max записей (default: 40, max: 100) |

**Что делает:** `board.get_queue(status)` → SQL SELECT с ORDER BY priority, created_at. Smart project_id resolution: `СГЕ` → `CUT`, `c` → `CUT`.

**Возвращает:** `{success, count, returned, truncated, tasks: [{id, title, priority, status, ...}]}`

### `get`

Получить одну задачу с полным содержимым + docs.

| Параметр | Тип | Обязательный |
|----------|-----|-------------|
| `task_id` | str | да |

**Что делает:** `board.get_task(id)` → SQL SELECT + `_load_docs_content_sync()` для чтения architecture_docs/recon_docs файлов.

**Возвращает:** `{success, task: {full task dict}, docs_content: "..."}`

### `update`

Обновить поля задачи.

| Параметр | Тип | Обязательный |
|----------|-----|-------------|
| `task_id` | str | да |
| любое поле | any | нет |

Обновляемые поля: `title`, `description`, `priority`, `phase_type`, `complexity`, `preset`, `status`, `tags`, `dependencies`, `project_id`, `project_lane`, `architecture_docs`, `recon_docs`, `closure_tests`, `closure_files`, `allowed_paths`, `completion_contract`, `implementation_hints`, `role`, `domain`, `branch_name`.

**Что делает:** `board.update_task(id, **updates)`. Validates status, normalizes protocol fields, appends history entry.

**Возвращает:** `{success, updated_fields}`

### `remove`

Удалить задачу.

| Параметр | Тип | Обязательный |
|----------|-----|-------------|
| `task_id` | str | да |

**Что делает:** `board.remove_task(id)` → DELETE FROM tasks + remove from cache.

**Возвращает:** `{success, message}`

### `summary`

Сводка по доске.

**Что делает:** SQL `SELECT status, COUNT(*) GROUP BY status` + `get_next_task()`.

**Возвращает:** `{success, total, by_status: {pending: N, ...}, next_task: {id, title, priority}}`

### `claim`

Агент берет задачу в работу.

| Параметр | Тип | Обязательный |
|----------|-----|-------------|
| `task_id` | str | да |
| `assigned_to` | str | нет | auto from session |
| `agent_type` | str | нет | auto from session |

**Что делает:**
1. Валидация: статус должен быть `pending`, `queued`, или `needs_fix`
2. Устанавливает `status=claimed`, `assigned_to`, `agent_type`, `assigned_at`
3. Auto-infer `execution_mode` (claude_code/cursor → manual, mycelium → pipeline)
4. Domain validation через AgentRegistry (warn mode)
5. Emits SocketIO event `task_claimed`
6. Возвращает full task + docs content

**Возвращает:** `{success, task_id, assigned_to, task: {...}, docs_content: "..."}`

### `complete`

Закрыть задачу с commit.

| Параметр | Тип | Обязательный |
|----------|-----|-------------|
| `task_id` | str | да |
| `commit_hash` | str | нет | Если есть — Case A |
| `commit_message` | str | нет | |
| `branch` | str | нет | auto-detect |
| `worktree_path` | str | нет | auto-infer from branch |
| `closure_files` | list[str] | нет | override task.closure_files |
| `q1_bugs` | str | нет | Debrief Q1 |
| `q2_worked` | str | нет | Debrief Q2 |
| `q3_idea` | str | нет | Debrief Q3 |

**Три пути закрытия:**

- **Case A** (commit_hash provided): `board.complete_task()` напрямую
- **Case B** (run_id exists): Verifier merge через `AgentPipeline.verify_and_merge()`
- **Case C** (no commit): `_try_auto_commit()` — stage files, commit, then close

**Auto-commit scoped staging** (приоритет):
1. `override_closure_files` (из MCP arguments)
2. `task.closure_files`
3. `task.allowed_paths` (фильтрует dirty files)
4. Все dirty files (fallback, с warning)

**Side effects:**
- Branch detection → `done_worktree` (non-main) или `done_main` (main)
- Ownership validation (warn mode)
- Debrief injection (Q1/Q2/Q3)
- Passive experience report creation
- SocketIO event `task_completed`

**Возвращает:** `{success, task_id, commit_hash, status, auto_commit: {...}, debrief_requested}`

### `active_agents`

Список агентов с активными задачами.

**Что делает:** SQL SELECT WHERE status IN ('claimed', 'running').

**Возвращает:** `{success, agents: [{agent_name, agent_type, task_id, task_title, elapsed_seconds}], count}`

### `merge_request`

Merge worktree branch → main.

| Параметр | Тип | Обязательный |
|----------|-----|-------------|
| `task_id` | str | да |

**Что делает:**
1. Validate task has `branch_name` (auto-infer from role if missing)
2. Validate branch exists (`git rev-parse --verify`)
3. Get commits ahead of main (`git log main..{branch}`)
4. Run `closure_tests` if defined
5. Execute merge (strategy: cherry-pick/merge/squash)
6. Count tests before/after (eval_delta)
7. Log to ActionRegistry
8. Set status → `done_main`

**Merge strategies:**
- `cherry-pick` (default): per-commit, safest
- `merge`: `git merge --no-ff`
- `squash`: `git merge --squash` + single commit

**Возвращает:** `{success, task_id, status, merge_result, eval_delta}`

### `promote_to_main`

Подтвердить что merge произошел, установить `done_main`.

| Параметр | Тип | Обязательный |
|----------|-----|-------------|
| `task_id` | str | да |
| `commit_hash` | str | **да** | Must be on main |

**Что делает:**
1. Validates commit is on main (`git merge-base --is-ancestor`)
2. Sets status → `done_main`

**ПРАВИЛО:** Без `commit_hash` — ERROR. Нет бумажных promotions.

**Возвращает:** `{success, task_id, status}`

### `verify`

QA gate для done_worktree задач.

| Параметр | Тип | Обязательный |
|----------|-----|-------------|
| `task_id` | str | да |
| `verdict` | str | да | `pass` или `fail` |
| `notes` | str | нет | Заметки верификации (max 300 chars) |
| `verified_by` | str | нет | Агент-верификатор (default: Delta) |

**Что делает:**
- `pass` → status = `verified`
- `fail` → status = `needs_fix`, emits `task_needs_fix` event

**Допустимый входной статус:** только `done_worktree`.

**Возвращает:** `{success, task_id, status, verdict}`

### `close` / `bulk_close`

Закрыть задачу(и) без commit (для obsolete/duplicate/cancelled).

| Параметр | Тип | Описание |
|----------|-----|----------|
| `task_id` / `task_ids` | str / list | ID задач(и) |
| `reason` | str | `already_implemented`, `duplicate`, `obsolete`, `research_done`, `cancelled` |

Обрабатывается через Mycelium transport.

### `stale_check`

Проверка устаревших задач.

| Параметр | Тип | Описание |
|----------|-----|----------|
| `auto_close` | bool | Если true, авто-закрыть задачи со score >= 0.8 |

### `search_fts`

Полнотекстовый поиск FTS5.

| Параметр | Тип | Описание |
|----------|-----|----------|
| `query` | str | FTS5 синтаксис: AND, OR, "phrase", prefix* |

### `batch_merge`

Пакетный merge нескольких задач из worktree.

### `debrief_skipped`

Список задач, закрытых без debrief Q1-Q3.

### `context_packet`

Генерация контекстного пакета для MCC.

---

## S6. LIFECYCLE ЗАДАЧИ

### Диаграмма статусов

```
                           ┌─────────────────────────────┐
                           v                             │
pending ──→ claimed ──→ done_worktree ──→ verified ──→ done_main
  ^            │              │                │
  │            │              v                │
  │            │          need_qa ─────────────┘
  │            │              │
  │            v              v
  │         running       needs_fix ──→ claimed (re-claim)
  │            │
  │            v
  │         done_main (if on main branch)
  │            │
  │            v
  └──────── failed (timeout/error → reset to pending)
```

### Все валидные статусы

`pending`, `queued`, `claimed`, `running`, `done`, `done_worktree`, `done_main`, `failed`, `cancelled`, `hold`, `pending_user_approval`, `verified`, `needs_fix`

### Transition rules

| Из | В | Кто может | Обязательные поля |
|----|---|-----------|-------------------|
| `pending` | `claimed` | Любой агент | `assigned_to`, `agent_type` |
| `pending` | `queued` | dispatch (max_concurrent reached) | — |
| `queued` | `claimed` | Любой агент | `assigned_to`, `agent_type` |
| `claimed` | `running` | dispatch | `started_at` |
| `claimed` | `done_worktree` | complete (non-main branch) | `commit_hash` (manual mode) |
| `claimed` | `done_main` | complete (main branch) | `commit_hash` |
| `running` | `done` | pipeline dispatch | `completed_at` |
| `running` | `failed` | pipeline error / stale timeout | `result_summary` |
| `done_worktree` | `verified` | verify (verdict=pass) | `verification_agent` |
| `done_worktree` | `needs_fix` | verify (verdict=fail) | `notes` |
| `done_worktree` | `done_main` | promote_to_main / merge_request | `commit_hash` (on main) |
| `verified` | `done_main` | promote_to_main | `commit_hash` (on main) |
| `needs_fix` | `claimed` | re-claim | `assigned_to` |
| `failed` | `pending` | record_failure (auto-reset) | — |
| any | `cancelled` | cancel_task | — |

### Stale cleanup

- `running` > 10 min → `failed`
- `claimed` > 5 min → reset to `pending` (release claim)

---

## S7. ТРАНСПОРТЫ

### Принцип: один handler, три транспорта

```python
# src/mcp/tools/task_board_tools.py:274
def handle_task_board(arguments: Dict[str, Any]) -> Dict[str, Any]:
    board = get_task_board()
    action = arguments["action"]
    # ... switch on action
```

### MCP VETKA (stdio, порт 5001)

- Transport: stdio (stdin/stdout JSON-RPC)
- Tool name: `vetka_task_board`
- Actions: `add`, `list`, `get`, `update`, `remove`, `summary`, `claim`, `complete`, `active_agents`, `merge_request`, `promote_to_main`, `verify`
- Handler: `handle_task_board()` в `task_board_tools.py`

### MCP Mycelium (WebSocket, порт 8082)

- Transport: WebSocket JSON-RPC
- Tool name: `mycelium_task_board`
- Actions: все actions из VETKA + расширенные: `close`, `bulk_close`, `stale_check`, `batch_merge`, `search_fts`, `backfill_fts`, `debrief_skipped`, `context_packet`
- Handler: тот же `handle_task_board()` + расширения в Mycelium server

### REST API (порт 5001)

Полная карта REST endpoints, вызывающих TaskBoard:

#### `task_routes.py` — основной CRUD API для MCC devpanel (17 вызовов)

| Endpoint | Method | TaskBoard call |
|----------|--------|---------------|
| `/api/tasks` | GET | `get_queue()` |
| `/api/tasks/{id}` | GET | `get_task()` |
| `/api/tasks` | POST | `add_task()` |
| `/api/tasks/{id}` | PUT | `update_task()` |
| `/api/tasks/{id}` | DELETE | `remove_task()` |
| `/api/tasks/{id}/claim` | POST | `claim_task()` |
| `/api/tasks/{id}/complete` | POST | `complete_task()` |
| `/api/tasks/{id}/merge` | POST | `merge_request()` |
| `/api/tasks/summary` | GET | `get_board_summary()` |

#### `mcc_routes.py` — MCC context overlay

| Endpoint | Method | TaskBoard call |
|----------|--------|---------------|
| `/api/mcc/tasks/{id}/context-packet` | GET | `get_context_packet()` — read-only |

#### `debug_routes.py` — debug/admin

| Endpoint | Method | TaskBoard call |
|----------|--------|---------------|
| `/api/debug/task-board` | GET/POST | Various CRUD |
| `/api/debug/task-board/notify` | POST | SocketIO emit (no DB write) |

### Внешние callers (не REST)

#### `group_message_handler.py` — Telegram doctor triage

- Создает задачи через `add_task()`
- Управляет через `update_task()`
- **COUPLING CONCERN:** строка ~821 использует `board.tasks.get(task_id)` — прямой доступ к dict кэша, минуя `get_task()`. Это обходит SQL refresh и может читать stale данные из кэша другого процесса. Рекомендация: заменить на `board.get_task(task_id)`.

#### `agent_pipeline.py` — pipeline lifecycle

- `update_task()` для checkpoint saves во время pipeline execution
- `record_pipeline_stats()` для финальных метрик
- `list_tasks()` (alias `get_queue()`) для team performance summary — полный скан, идет из кэша

#### `mycelium_heartbeat.py` — periodic task checks

- `get_queue()` на каждый tick (30-60s) — ДОЛЖЕН идти из кэша (не SQL)
- `add_task()` для heartbeat-detected tasks

### ПРАВИЛО: один `handle_task_board()`, три транспорта

Все MCP транспорты вызывают одну и ту же функцию. REST API вызывает TaskBoard методы напрямую. Нет дублирования логики.

---

## S8. ЗАВИСИМОСТИ

### Кто вызывает TaskBoard

```
session_init ──→ board.get_board_summary()     (count by status)
              ──→ board.get_queue(pending)       (top_pending preview)
              ──→ board.get_active_agents()      (claimed/running tasks)

protocol_guard ──→ checks task_claimed flag     (session_tracker state)

smart_debrief ──→ Q1-Q3 через action=complete  (debrief injection)

reflex_integration ──→ reads task meta          (tool scoring context)

agent_registry ──→ domain/ownership validation  (claim/complete)

GitCommitTool ──→ auto_complete_by_commit()     (post-commit hook)

experience_report ──→ auto-created on complete  (passive metrics)

failure_feedback ──→ record_failure()           (retry learning)

action_registry ──→ merge_request logs          (ActionRegistry)
```

### Диаграмма зависимостей (текстовая)

```
               ┌──── session_tools.py (session_init)
               │
               ├──── protocol_guard.py (task_claimed check)
               │
TaskBoard ─────├──── smart_debrief.py (Q1-Q3 on complete)
               │
               ├──── reflex_integration.py (scoring context)
               │
               ├──── agent_registry.py (domain/ownership)
               │
               ├──── git_tool.py (auto-complete by commit)
               │
               ├──── experience_report.py (passive metrics)
               │
               ├──── failure_feedback.py (retry learning)
               │
               └──── action_registry.py (merge logging)
```

---

## S9. FTS5 ПОИСК

### Схема tasks_fts

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts
USING fts5(id, title, description, tags, content='tasks', content_rowid='rowid');
```

FTS5 таблица индексирует `id`, `title`, `description`, `tags` для полнотекстового поиска.

### Инкрементальная индексация

Каждый `_save_task()` вызывает `_index_task_fts(task)` для обновления FTS индекса. Индексация per-task, не batch.

### search_fts() — синтаксис запросов

FTS5 синтаксис через Mycelium transport:
- `fix AND crash` — оба слова
- `"database lock"` — точная фраза
- `fix OR bug` — любое из слов
- `task*` — prefix match
- `title: crash` — поиск по конкретной колонке

### backfill_fts

Ленивый бэкфил FTS индекса. Вызывается ЯВНО через `action=backfill_fts`, **НИКОГДА в `__init__`**.

POSTMORTEM Phase 199: `_backfill_fts()` в `__init__` вызвал DB lock storm. 14 MCP процессов стартовали одновременно, каждый пытался переиндексировать 400+ задач. Fix: инкрементальный FTS + DDL fast path.

---

## S10. МИГРАЦИИ

### _run_migrations()

Версионированные, идемпотентные миграции. Каждая миграция проверяет `meta` таблицу перед выполнением.

### DDL_FAST — sqlite_master check перед DDL

```python
# Проверка через sqlite_master ПЕРЕД ALTER TABLE / CREATE INDEX
cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks_fts'")
if cursor.fetchone() is None:
    db.execute("CREATE VIRTUAL TABLE ...")
```

DDL операции (ALTER TABLE, CREATE INDEX) идемпотентны — используют `IF NOT EXISTS` или проверку `sqlite_master`. Это позволяет 14 процессам безопасно стартовать одновременно.

### Как добавить новую миграцию

```python
# Шаблон миграции:
def _migration_NNN(self):
    """Description of what this migration does."""
    # 1. Check if already applied
    cursor = self.db.execute("SELECT value FROM meta WHERE key = 'migration_NNN'")
    if cursor.fetchone():
        return  # Already applied

    # 2. Execute DDL/DML (idempotent)
    with self.db:
        # DDL_FAST: check sqlite_master first
        existing = self.db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_new_index'"
        ).fetchone()
        if not existing:
            self.db.execute("CREATE INDEX idx_new_index ON tasks(new_column)")

        # Mark as applied
        self.db.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("migration_NNN", datetime.now().isoformat()),
        )
```

**ПРАВИЛО: Новые данные → `extra` JSON blob, не новые колонки в `tasks`.**

---

## S11. КРАСНЫЕ ЛИНИИ — НЕЛЬЗЯ НИКОГДА

1. **Bulk writes в `__init__`** — 14 процессов стартуют одновременно, bulk = DB lock storm
2. **`get_queue()` через SQL** — БЫЛО сделано через SQL для корректности, кэш может быть stale. Но query ДОЛЖЕН быть быстрым (indexed columns only)
3. **`busy_timeout` > 5000** — увеличение timeout маскирует проблему, не решает
4. **`timeout` > 5 в `sqlite3.connect()`** — та же причина
5. **`_execute_with_retry` или любой retry на writes** — retry на locked DB = amplification, каждый retry создает еще один writer в очереди
6. **Новые колонки в `tasks` таблице** — используй `extra` JSON blob. Новая колонка = ALTER TABLE + INDEX + миграция всех 14 процессов
7. **Синхронные bulk операции в `session_init`** — session_init вызывается при каждом старте агента, должен быть <100ms

---

## S12. ЧИСТЫЙ РЕСТАРТ

### Пошаговая инструкция перезагрузки MCP серверов

**1. Остановка всех процессов**

```bash
# Найти все MCP процессы, держащие task_board.db
fuser data/task_board.db

# Или через lsof
lsof data/task_board.db

# Остановить MCP серверы (зависит от конфигурации запуска)
# НЕ kill -9 — это может оставить WAL в inconsistent state
```

**2. Проверка целостности БД**

```bash
# Проверить integrity
sqlite3 data/task_board.db "PRAGMA integrity_check;"
# Ожидаемый ответ: "ok"

# Проверить WAL checkpoint
sqlite3 data/task_board.db "PRAGMA wal_checkpoint(TRUNCATE);"
# Это flush-ит WAL в основной файл

# Проверить размер
ls -la data/task_board.db data/task_board.db-wal data/task_board.db-shm
# WAL файл должен быть <1MB после checkpoint

# Проверить количество задач
sqlite3 data/task_board.db "SELECT status, COUNT(*) FROM tasks GROUP BY status;"
```

**3. Запуск**

```bash
# MCP серверы запускаются через .mcp.json конфигурацию
# При старте каждый процесс создает TaskBoard singleton:
# 1. _connect() → WAL mode + busy_timeout=5000
# 2. _ensure_schema() → CREATE TABLE IF NOT EXISTS (идемпотент)
# 3. _load_all_tasks() → заполнение кэша
```

**4. Верификация**

```bash
# Проверить что TaskBoard доступен через MCP
# (через любой агент)
vetka_task_board action=summary

# Проверить количество процессов
fuser data/task_board.db
# Должно быть по 2 процесса на каждый MCP сервер (основной + watchdog)

# Проверить WAL mode
sqlite3 data/task_board.db "PRAGMA journal_mode;"
# Ответ: "wal"
```

### Экстренное восстановление (если DB locked permanently)

```bash
# 1. Остановить ВСЕ процессы
pkill -f "vetka.*mcp"  # осторожно!

# 2. Checkpoint + vacuum
sqlite3 data/task_board.db "PRAGMA wal_checkpoint(TRUNCATE); VACUUM;"

# 3. Удалить WAL/SHM если checkpoint не помог
rm -f data/task_board.db-wal data/task_board.db-shm

# 4. Перезапуск
# (через .mcp.json)
```

---

## APPENDIX A: Singleton Pattern

```python
# src/orchestration/task_board.py:3145-3167
_board_instance: Optional[TaskBoard] = None

def get_task_board() -> TaskBoard:
    global _board_instance
    if _board_instance is None:
        _board_instance = TaskBoard()
    return _board_instance

def reset_task_board() -> None:
    """Close SQLite connection and reset singleton.
    Call before importlib.reload()."""
    global _board_instance
    if _board_instance is not None:
        try:
            _board_instance.db.close()
        except Exception:
            pass
    _board_instance = None
```

## APPENDIX B: ID Generation

```python
def _generate_task_id() -> str:
    global _task_counter
    _task_counter += 1
    return f"tb_{int(time.time())}_{_task_counter}"
```

Формат: `tb_{unix_seconds}_{per_process_counter}`. Уникальность гарантируется временем + per-process counter. При перезапуске counter сбрасывается, но timestamp обеспечивает уникальность.

## APPENDIX C: Project ID Smart Resolution

TaskBoard поддерживает smart matching для `project_id`:

1. **Exact match:** `CUT` → `CUT`
2. **Case-insensitive:** `cut` → `CUT`
3. **RU layout fix:** `СГЕ` (русская раскладка) → `CUT`
4. **Prefix match:** `c` → `CUT` (если единственный кандидат)
5. **Prefix ambiguous:** `v` → candidates: `[vetka, vetka_pulse]` (возвращает все)

## APPENDIX D: execution_mode

Два режима закрытия задач:

| Mode | Agents | Proof Required |
|------|--------|---------------|
| `pipeline` | mycelium, dragon | pipeline_success + verifier_confidence >= 0.75 + closure_tests pass + commit_hash |
| `manual` | claude_code, cursor, human, grok, codex | commit_hash only (closure_tests if defined) |

Auto-inferred from `agent_type` at claim time. Manual agents (CLI tools) commit directly — they don't go through verifier pipeline.

## APPENDIX E: DOC_GATE

Все `build`/`fix` задачи обязаны иметь хотя бы один `architecture_doc` или `recon_doc`.

- `research`/`test` — auto-exempt (они создают документы, а не потребляют)
- `force_no_docs=true` — bypass, но REJECTED если >= 2 relevant docs найдены (strict mode)
- Docs suggestions: `_suggest_docs_for_title()` ищет через REST `vetka_search_semantic` + glob fallback
