# VETKA Dynamic Memory Blueprint v1.1

> Архитектурный документ: единая динамическая память для Claude Code, Codex, MCC Architects, Jarvis и VETKA Chat agents.
>
> Автор: Opus (Architect-Commander) + Danila (Product Owner) + Sonnet (Critic)
> Дата: 2026-03-16
> Статус: ARCHITECTURE REVIEW
> v1.1: Добавлена секция 11 — двухуровневая память (True Engram + Semantic), по критике Sonnet 4.6

---

## 1. Проблема

Предложенная ранее архитектура с `program.md` содержит **5 дублей из 8 компонентов**. Этот документ фиксирует результаты критического аудита и предлагает чистую архитектуру без пятых колёс.

### 1.1 Что уже существует (и работает)

| Система | Файл/Модуль | Что хранит | Когда обновляется |
|---------|-------------|-----------|-------------------|
| **project_digest.json** | `data/project_digest.json` | Фаза, achievements, pending, system status, git | Pre-commit hook + task completion + post-commit |
| **TaskBoard** | `src/orchestration/task_board.py` | Tasks + status_history + failure_history + stats + result_status | На каждое действие (claim, run, complete, fail) |
| **Resource Learnings** | `src/orchestration/resource_learnings.py` | Паттерны, подводные камни, оптимизации | После verify_and_merge в Qdrant |
| **CORTEX (REFLEX L3)** | `src/reflex/feedback.py` | Tool effectiveness per (tool_id, phase_type) | После каждого tool execution |
| **ENGRAM** | `src/memory/engram_user_memory.py` | User preferences (comm style, viewport, tools) | По user interaction |
| **REFLEX Scorer** | `src/reflex/scorer.py` | 8 memory signals → tool ranking | Каждый REFLEX trigger |
| **Claude Code Memory** | `~/.claude/projects/.../memory/` | User feedback, gotchas, patterns, architecture | Manually by Claude |
| **session_init** | `src/mcp/tools/session_tools.py` | Returns: digest + ENGRAM + tasks + REFLEX + commits | На каждый session start |

### 1.2 Что предлагалось и что из этого — дубли

| Предложение | Дублирует | Вердикт |
|-------------|-----------|---------|
| `program.md.phase` | `project_digest.json.current_phase` | ❌ Дубль |
| `program.md.focus_area` | `project_digest.json.summary.headline` | ❌ Дубль (85%) |
| `program.md.blockers` | TaskBoard: tasks со status=hold/blocked | ❌ Дубль |
| `program.md.decisions` | TaskBoard: status_history[].reason + failure_history | ❌ Дубль |
| `program.md.next_steps` | `project_digest.json.summary.pending_items` | ❌ Дубль |
| ENGRAM store on complete | `resource_learnings.py` → Qdrant | ❌ Дубль |
| CORTEX feedback loop | `src/reflex/feedback.py` (уже L3 REFLEX) | ❌ Дубль |
| `signal_program` (9th signal) | `signal phase_match` (частично) | ⚠️ Частичный дубль |
| Filtered semantic recall in session_init | **НЕ СУЩЕСТВУЕТ** | ✅ Нужно |
| MEMORY.md cleanup | **Реальная проблема** (831 строк, truncated) | ✅ Нужно |
| Agent-level context | **НЕ СУЩЕСТВУЕТ** (все агенты видят одинаковый digest) | ✅ Нужно |

### 1.3 Пять настоящих проблем

| # | Проблема | Влияние | Текущие потери |
|---|----------|---------|----------------|
| **P1** | MEMORY.md = 831 строк, truncated at 200 | Claude Code теряет 75% контекста каждую сессию | Повторяет вопросы, забывает решения |
| **P2** | session_init не делает semantic recall | Каждый разговор "с нуля" — нет связи с прошлым опытом | Нет cross-session обучения |
| **P3** | Два параллельных мира памяти | Claude пишет в `~/.claude/memory/`, VETKA — в Qdrant. Нет моста | Дублирование + рассинхрон |
| **P4** | Digest = project-level, не agent-level | Opus, Cursor, Codex видят одинаковый контекст | Нет персонализации |
| **P5** | Digest обновляется ДО коммита (pre-commit hook) | Хук может обновить digest до того как таск закрыт | Race condition с task_board |

---

## 2. Чистая архитектура (без пятых колёс)

### 2.1 Принцип: усиливай существующее, не создавай параллельное

Вместо нового `program.md` — обогащаем существующий `project_digest.json` + `session_init`.
Вместо нового ENGRAM write — расширяем существующий `resource_learnings`.
Вместо нового CORTEX — он УЖЕ работает.

### 2.2 Архитектура в схеме

```
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT SESSION START                        │
│                                                                 │
│  session_init(agent_type="claude_code"|"codex"|"mcc_architect") │
│      │                                                          │
│      ├── 1. project_digest.json (как сейчас)                    │
│      │      phase, achievements, pending, system_status         │
│      │                                                          │
│      ├── 2. task_board_summary (как сейчас)                     │
│      │      pending tasks, in_progress, top priorities          │
│      │                                                          │
│      ├── 3. ★ NEW: semantic_recall(agent_type, task_context)    │
│      │      │                                                   │
│      │      ├── Qdrant: VetkaResourceLearnings                  │
│      │      │   query = digest.headline + top_pending_task      │
│      │      │   filter = {category: relevant_to_agent_type}     │
│      │      │   limit = 3-5 results                             │
│      │      │                                                   │
│      │      └── Qdrant: vetka_elisya (code context)             │
│      │          query = in_progress_task.title                  │
│      │          filter = {file_type: agent's domain}            │
│      │          limit = 3 results                               │
│      │                                                          │
│      ├── 4. ENGRAM user_preferences (как сейчас)                │
│      │                                                          │
│      ├── 5. REFLEX recommendations (как сейчас)                 │
│      │                                                          │
│      └── 6. ★ NEW: agent_briefing(agent_type)                   │
│             │                                                   │
│             ├── claude_code → "ты Opus, фокус: [headline],      │
│             │                  не трогай: [codex claimed files]" │
│             ├── codex → "ты Codex, фокус: [assigned tasks],     │
│             │            не трогай: [opus claimed files]"        │
│             └── mcc_architect → "ты Архитектор, фокус: [project │
│                                  roadmap], бюджет: [tier]"      │
│                                                                 │
│  RESULT: ~50 строк контекста вместо 831 строк MEMORY.md        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Поток данных: WRITE path

```
┌─────────────────────────────────────────────────────────────────┐
│                     TASK COMPLETION                              │
│                                                                 │
│  task_board.complete(task_id)                                   │
│      │                                                          │
│      ├── 1. TaskBoard: update status, status_history, stats     │
│      │      (как сейчас, ничего не меняем)                      │
│      │                                                          │
│      ├── 2. Git commit (auto, как сейчас)                       │
│      │      pre-commit hook → digest auto-sync                  │
│      │                                                          │
│      ├── 3. resource_learnings.extract_and_store()              │
│      │      (как сейчас, после verify_and_merge)                │
│      │                                                          │
│      ├── 4. CORTEX: reflex_feedback.record_outcome()            │
│      │      (как сейчас, tool effectiveness tracking)           │
│      │                                                          │
│      └── 5. ★ NEW: digest.agent_focus[agent_type] update        │
│             Только 2 поля:                                      │
│             - last_completed: task.title                         │
│             - claimed_files: [list from active tasks]            │
│                                                                 │
│  НЕТ: program.md (дубль digest)                                │
│  НЕТ: отдельный ENGRAM write (дубль resource_learnings)        │
│  НЕТ: CORTEX write (уже работает)                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Компоненты (только новое)

### 3.1 semantic_recall() — Мост между сессиями

**Зачем:** session_init сейчас возвращает digest + task summary, но не ищет в Qdrant по контексту текущей работы. Каждая сессия начинается "с нуля".

**Реализация:** Добавить в `session_tools.py._execute_async()`, после загрузки digest и task_board:

```python
# NEW: Semantic recall — 3-5 relevant past learnings
async def _semantic_recall(self, context: dict) -> list:
    """Query Qdrant for learnings relevant to current work."""
    from src.orchestration.resource_learnings import ResourceLearningStore
    store = ResourceLearningStore()

    # Build query from current context
    query_parts = []

    # From digest headline
    headline = context.get("project_digest", {}).get("summary", "")
    if headline:
        query_parts.append(headline)

    # From top pending task
    top_tasks = context.get("task_board_summary", {}).get("top_pending", [])
    if top_tasks:
        query_parts.append(top_tasks[0].get("title", ""))

    # From in-progress task
    in_progress = context.get("task_board_summary", {}).get("in_progress", [])
    if in_progress:
        query_parts.append(in_progress[0].get("title", ""))

    query = " ".join(query_parts)
    if not query:
        return []

    # Search VetkaResourceLearnings
    learnings = store.get_learnings_for_architect(query, limit=5)
    return learnings
```

**Что это даёт:**
- Начинающая сессию получает релевантные уроки из прошлых запусков
- Никакого нового хранилища — используем существующий `VetkaResourceLearnings`
- Фильтрация по текущему контексту (headline + tasks), не по всему Qdrant

**Файлы для изменения:** `src/mcp/tools/session_tools.py` (~20 строк)

### 3.2 agent_briefing() — Персонализация контекста

**Зачем:** Opus, Cursor, Codex видят одинаковый digest. Opus не знает что Codex уже claimed файлы. Codex не знает решения Opus.

**Реализация:** Добавить в `session_tools.py`:

```python
async def _agent_briefing(self, agent_type: str, context: dict) -> dict:
    """Build agent-specific briefing from shared state."""
    briefing = {"agent_type": agent_type}

    # Get all tasks to find claimed files by OTHER agents
    from src.orchestration.task_board import TaskBoard, TASK_BOARD_FILE
    board = TaskBoard(TASK_BOARD_FILE)
    in_progress = board.get_queue(status="in_progress")

    my_tasks = []
    other_claimed = []
    for task in in_progress:
        assigned = task.get("assigned_to", "")
        if assigned == agent_type:
            my_tasks.append(task.get("title", "")[:60])
        elif assigned:
            # Extract files from description
            desc = task.get("description", "")
            other_claimed.append({
                "agent": assigned,
                "task": task.get("title", "")[:40],
                "files_hint": desc[:100] if desc else ""
            })

    briefing["my_tasks"] = my_tasks
    briefing["do_not_touch"] = other_claimed  # Files claimed by others

    return briefing
```

**Что это даёт:**
- Каждый агент видит: "вот твои задачи, вот что трогать нельзя (другой агент работает)"
- Решает проблему конфликтов при multi-agent работе
- Данные берутся из task_board — никакого нового хранилища

**Файлы для изменения:** `src/mcp/tools/session_tools.py` (~30 строк), параметр `agent_type` в session_init

### 3.3 MEMORY.md → Compact Index

**Зачем:** 831 строк, Claude Code видит только первые 200. 75% контекста теряется.

**Реализация:** Сжать MEMORY.md до ≤50 строк, вынести детали в topic-файлы (некоторые уже вынесены).

**Правило:** MEMORY.md = только ссылки + 1-строчные описания. Вся детальная информация — в `memory/*.md`.

**Что удалить из MEMORY.md:**
- Phase 154 details (101 checkboxes, 6 waves) — это git history, не memory
- Phase 152 details — это git history
- Numbering Convention table — это CLAUDE.md, не memory
- Wave details (Wave 0-6) — это git history
- File listings (10 new files) — это git history
- Current State details — это project_digest.json

**Что оставить:**
- Ссылки на topic-файлы (feedback, gotchas, patterns, architecture)
- Opus Architect Role (core identity)
- Task Closure Protocol (critical workflow)
- Critical rules that aren't in CLAUDE.md

**Файлы для изменения:** `~/.claude/.../memory/MEMORY.md`

### 3.4 Digest → Agent-Aware (минимальное расширение)

**Зачем:** Решить P4 (все агенты видят одинаковый digest) и P5 (race condition с pre-commit hook).

**Реализация:** Добавить секцию `agent_focus` в digest:

```json
{
  "agent_focus": {
    "claude_code": {
      "last_completed": "186.1: Playwright config + reflex tool",
      "claimed_files": ["src/reflex/scorer.py", "tests/test_reflex.py"]
    },
    "codex": {
      "last_completed": "152.7: Task Editor inline editing",
      "claimed_files": ["client/src/components/TaskCard.tsx"]
    }
  }
}
```

**Обновление:** В `task_tracker._update_digest_with_task()` добавить запись в `agent_focus[source]`.

**Файлы для изменения:** `src/services/task_tracker.py` (~10 строк), `scripts/update_project_digest.py` (~5 строк для schema)

### 3.5 P5 Fix: Digest hook order

**Зачем:** Pre-commit hook обновляет digest ДО коммита. Если task_board.complete() тоже обновляет digest через task_tracker, получается race.

**Решение:** Перенести digest auto-sync из pre-commit в **post-commit hook**:

```
СЕЙЧАС:
  pre-commit → update_digest → git commit → post-commit → push
  task_board.complete() → update_digest → ... → conflict

ПОСЛЕ:
  pre-commit → (только lint/tests)
  git commit
  post-commit → update_digest + push

  task_board.complete() → triggers git commit → post-commit updates digest
```

**Файлы для изменения:** `.git/hooks/pre-commit` (удалить вызов update_digest), `.git/hooks/post-commit` (добавить вызов update_digest)

---

## 4. Что НЕ делаем (и почему)

| Компонент | Почему НЕ делаем |
|-----------|-----------------|
| `program.md` | 70% дублирует digest. Поля focus_area и confidence можно добавить в digest.agent_focus, а не в отдельный файл |
| Новый ENGRAM collection | resource_learnings уже хранят уроки в Qdrant. Не нужна вторая коллекция для того же |
| signal_program (9th signal) | phase_match уже делает 80% этого. Если нужна гранулярность — расширить phase_match, а не добавлять 9-й сигнал |
| Новый CORTEX write path | CORTEX = REFLEX Layer 3, уже пишет после каждого tool call. Не нужен второй write |
| Автоматический Qdrant recall при каждом tool call | Слишком дорого. Recall нужен только на session_init, не на каждый запрос |

---

## 5. Потребители памяти — кто что получает

### 5.1 Матрица: агент × источник

| Источник | Claude Code (Opus) | Codex (worktree) | MCC Architect | Chat Agent | Jarvis |
|----------|-------------------|-------------------|---------------|------------|--------|
| project_digest.json | ✅ via session_init | ✅ via session_init | ✅ via pipeline context | ✅ via session_init | ✅ direct read |
| task_board_summary | ✅ pending + in_progress | ✅ only assigned to me | ✅ roadmap view | ❌ not needed | ✅ full view |
| **semantic_recall** | ✅ 5 learnings | ✅ 3 learnings (filtered to frontend) | ✅ 5 learnings (filtered to architecture) | ❌ not needed | ✅ 5 learnings |
| **agent_briefing** | ✅ my tasks + don't touch | ✅ my tasks + don't touch | ✅ project scope | ❌ chat is ephemeral | ✅ global view |
| ENGRAM preferences | ✅ comm style | ❌ uses own config | ❌ pipeline agent | ✅ comm style | ✅ comm style |
| REFLEX recommendations | ✅ tool suggestions | ❌ Codex has own tools | ✅ tool selection | ✅ tool routing | ❌ not needed |
| Claude Code memory | ✅ reads `~/.claude/memory/` | ❌ separate agent | ❌ separate agent | ❌ separate agent | ❌ separate agent |
| CORTEX feedback | ✅ via REFLEX signal | ✅ via REFLEX signal | ✅ via tool ranking | ✅ via REFLEX | ❌ not needed |
| resource_learnings | ✅ via semantic_recall | ✅ via semantic_recall | ✅ architect context injection | ❌ | ✅ via recall |
| failure_history | ❌ (Opus plans, doesn't code) | ✅ injected into coder prompt | ✅ injected into coder prompt | ❌ | ❌ |

### 5.2 Разница по агентам

**Claude Code (Opus):** Получает полный контекст + semantic recall + "не трогай файлы Codex". Пишет архитектурные решения в task descriptions. Memory = `~/.claude/memory/` (read/write) + Qdrant (read via recall).

**Codex:** Получает узкий контекст: только свои задачи + failure_history + "не трогай файлы Opus". Не видит MEMORY.md Claude. Пишет результаты через task_board.complete().

**MCC Architect:** Получает проектный контекст: roadmap + resource_learnings + tier budget. Пишет в task_board (creates subtasks) + resource_learnings (после verify).

**Chat Agent (VETKA UI):** Получает digest + ENGRAM (как общаться с user) + REFLEX (какие tools предложить). Не пишет в долговременную память.

**Jarvis:** Получает ВСЁ. Orchestrates across agents. Пишет в digest.agent_focus.

---

## 6. Мост Claude Memory ↔ VETKA Memory

### 6.1 Проблема двух миров

Claude Code пишет в `~/.claude/projects/.../memory/` — файлы `feedback_no_preview.md`, `gotchas.md`, `patterns.md`. Эти файлы **невидимы** для VETKA Chat agents и MCC.

VETKA пишет в Qdrant (`VetkaResourceLearnings`) и `feedback_log.jsonl`. Эти данные **невидимы** для Claude Code.

### 6.2 Решение: однонаправленный мост (VETKA → Claude)

Не пытаемся синхронизировать два мира (сложно, fragile). Вместо этого:

1. **Claude Code memory остаётся как есть** — это "личная память" агента Claude. Feedback, user preferences, gotchas. Автоматически загружается Claude Code при старте.

2. **VETKA memory (Qdrant) приходит через semantic_recall** — 3-5 релевантных learnings при session_init. Claude Code получает "коллективный опыт" без дублирования.

3. **Мост не нужен** — это не два хранилища одного и того же. Это два разных типа памяти:
   - Claude memory = **personal** (как я работаю с этим юзером, какие ошибки я делал)
   - VETKA memory = **collective** (что вся система узнала о кодовой базе)

```
Claude Code Memory          VETKA Memory (Qdrant)
─────────────────          ──────────────────────
"Don't use Preview         "Files scorer.py and
 for CUT" (feedback)        feedback.py always
                             change together" (pattern)
"User prefers Russian"     "Verifier fails on
 (user preference)           missing type annotations"
                             (pitfall)
"Always close tasks via    "dragon_silver optimal for
 MCP" (workflow rule)        frontend tasks" (optimization)
```

Разные данные, разные цели, разные потребители. Мост = semantic_recall в session_init.

---

## 7. Реализация: что менять

### 7.1 Приоритеты

| # | Задача | Файлы | Строк кода | Зависимости | Приоритет |
|---|--------|-------|------------|-------------|-----------|
| 1 | **MEMORY.md cleanup** | `~/.claude/.../memory/MEMORY.md` | -700 строк | Нет | 🔴 Критично |
| 2 | **semantic_recall в session_init (L2)** | `session_tools.py` | +20 | resource_learnings.py | 🔴 Критично |
| 3 | **agent_briefing в session_init** | `session_tools.py` | +30 | task_board.py | 🟡 Важно |
| 4 | **agent_focus в digest** | `task_tracker.py` + `update_project_digest.py` | +15 | digest schema | 🟡 Важно |
| 5 | **Digest hook order fix** | `.git/hooks/pre-commit` + `post-commit` | ±10 | git hooks | 🟢 Nice to have |
| 6 | **True Engram L1 cache** | new: `src/memory/engram_cache.py` + `data/engram_cache.json` | +80 | semantic_recall (задача 2) | 🟢 После L2 стабилизации |

### 7.2 Что НЕ трогаем

- `task_board.py` — работает, не ломаем
- `resource_learnings.py` — работает, только читаем из session_init
- `reflex/feedback.py` — работает, CORTEX уже пишет
- `reflex/scorer.py` — 8 сигналов достаточно, не добавляем 9-й
- `engram_user_memory.py` — работает, user preferences уже приходят

---

## 8. Валидация: контрольные вопросы

### Q: program.md нужен?
**A: Нет.** Его задачи покрываются:
- `digest.current_phase` + `digest.summary.headline` = phase + focus
- `task_board.get_queue(status="hold")` = blockers
- `task_board.status_history` = decisions
- `digest.summary.pending_items` = next_steps
- `digest.agent_focus[agent_type]` (NEW) = agent-specific state

### Q: Нужна ли новая Qdrant коллекция?
**A: Нет.** `VetkaResourceLearnings` уже хранит уроки. Просто начинаем читать из неё при session_init.

### Q: Нужен ли 9-й сигнал в REFLEX?
**A: Нет.** `phase_match` (signal #6) уже выравнивает инструменты по фазе. Если нужна гранулярность по focus_area — лучше расширить phase_match, используя `digest.summary.headline` как дополнительный фильтр.

### Q: Как Claude Code узнает про прошлые решения?
**A: Через semantic_recall.** При session_init ищем в `VetkaResourceLearnings` по текущему контексту. 3-5 релевантных уроков. Не 831 строк хронологии.

### Q: А что если Qdrant упал?
**A: resource_learnings.py уже имеет fallback** на `data/resource_learnings.json`. semantic_recall просто вернёт пустой список. Агент продолжит работать с digest + task_board (как сейчас).

### Q: Работает ли это для Jarvis?
**A: Да.** Jarvis вызывает session_init с `agent_type="jarvis"`, получает полный контекст + semantic_recall + global agent_briefing. Jarvis — единственный, кто видит ВСЕ agent_focus записи.

---

## 9. Метрики успеха

| Метрика | Сейчас | Цель |
|---------|--------|------|
| MEMORY.md размер | 831 строк (truncated at 200) | ≤50 строк |
| Context relevance при session_init | 0% semantic recall | 3-5 targeted learnings |
| Agent conflict (файловые коллизии) | Случайные, нет видимости | 0 (agent_briefing.do_not_touch) |
| Новые файлы/системы | — | 0 (всё в существующих модулях) |
| Новые Qdrant коллекции | — | 0 |
| Строк нового кода | — | ~75 (session_tools.py + task_tracker.py) |

---

## 10. Следующий шаг

1. Ревью этого документа (Danila)
2. Если ОК — создать таски на task_board:
   - `187.1: MEMORY.md cleanup (831→50 строк)`
   - `187.2: semantic_recall in session_init`
   - `187.3: agent_briefing + agent_type param in session_init`
   - `187.4: digest.agent_focus in task_tracker`
   - `187.5: True Engram — deterministic cache layer`
3. Реализация в порядке приоритетов (1→2→3→4→5)

---

## 11. True Engram: двухуровневая память (v1.1, по критике Sonnet)

### 11.1 Проблема: мы неправильно назвали вещи

Наш `engram_user_memory.py` — это **user preferences store** с RAM кэшем. Он хранит `communication_style`, `viewport_patterns`, `tool_usage_patterns` и отдаёт их по `user_id`. Это полезный модуль, но к DeepSeek Engram он не имеет отношения.

| | DeepSeek Engram (оригинал) | Наш "ENGRAM" |
|--|---------------------------|-------------|
| **Что** | N-граммная адресация внутри forward pass модели | Dict[str, UserPreferences] + Qdrant |
| **Как** | O(1) детерминированный lookup по паттерну | Семантический поиск (cosine similarity) |
| **Где** | Внутри весов/архитектуры LLM | Снаружи, как внешний инструмент |
| **Цель** | Освободить ранние слои от паттерн-реконструкции | Хранить user preferences между сессиями |

**Вывод:** Модуль `engram_user_memory.py` работает корректно для своей задачи (user preferences). Но имя вводит в заблуждение — планируем переименование:

- `EngramUserMemory` → `UserPreferenceStore`
- `engram_user_memory.py` → `user_preference_store.py`
- `enhanced_engram_lookup()` (levels 2-5) → удалить (~200 строк мёртвого placeholder кода)
- Слово "Engram" зарезервировано для настоящего детерминированного L1 кэша

Подробный план: `docs/186_memory/RENAME_ENGRAM_PLAN.md`

### 11.2 Ключевая идея: детерминированный lookup vs семантический поиск

Сейчас ВСЯ наша память работает через семантический поиск (Qdrant cosine similarity):

```
Запрос: "как работает pipeline timeout?"
  → Qdrant embedding → cosine similarity → top-K results
  → Результат ЗАВИСИТ от: модели эмбеддингов, порога, данных в коллекции
  → Недетерминировано, ~200ms
```

Настоящий Engram-подход добавляет **первый уровень** — детерминированный кэш:

```
Запрос: "как работает pipeline timeout?"
  → hash("pipeline" + "timeout") → dict lookup → точный ответ
  → Результат ВСЕГДА один и тот же
  → Детерминировано, <1ms
```

### 11.3 Двухуровневая архитектура

```
┌─────────────────────────────────────────────────┐
│              MEMORY QUERY                        │
│                                                  │
│  Level 1: DETERMINISTIC CACHE (True Engram)      │
│  ┌──────────────────────────────────────────┐    │
│  │ Key: (agent_type, file_path, action)     │    │
│  │ Value: конкретный урок / контекст        │    │
│  │                                          │    │
│  │ Примеры:                                 │    │
│  │ ("opus", "session_tools.py", "edit")     │    │
│  │   → "JSON namespace bug, use _json"      │    │
│  │                                          │    │
│  │ ("codex", "TaskCard.tsx", "edit")         │    │
│  │   → "inline editing uses contentEditable"│    │
│  │                                          │    │
│  │ ("*", "agent_pipeline.py", "modify")     │    │
│  │   → "DANGER: self-modification, use      │    │
│  │      sandbox worktree"                   │    │
│  │                                          │    │
│  │ O(1), детерминированный, <1ms            │    │
│  │ Источник: auto-populated from            │    │
│  │   resource_learnings + failure_history    │    │
│  └────────────────────┬─────────────────────┘    │
│                       │                          │
│          HIT? ────────┤                          │
│          │            │                          │
│         YES          NO                          │
│          │            │                          │
│          ▼            ▼                          │
│   Return cached   Level 2: SEMANTIC SEARCH       │
│   answer          ┌───────────────────────────┐  │
│                   │ Qdrant: VetkaResource-    │  │
│                   │   Learnings (existing)    │  │
│                   │                           │  │
│                   │ query = task context       │  │
│                   │ cosine similarity, top-5   │  │
│                   │ ~200ms                     │  │
│                   └───────────────────────────┘  │
│                                                  │
│  Level 1 = частые повторяющиеся паттерны         │
│  Level 2 = новые/уникальные ситуации             │
└──────────────────────────────────────────────────┘
```

### 11.4 Как наполняется Level 1 (auto-populate)

Level 1 — не ручной кэш. Он **автоматически растёт** из существующих данных:

```python
# Источник 1: resource_learnings (после verify_and_merge)
# Если один и тот же урок match-ится > 3 раз → promote to L1 cache

# Источник 2: failure_history (после провалов)
# Файл, который вызвал failure > 2 раз → auto-cache предупреждение

# Источник 3: CORTEX feedback (tool effectiveness)
# Если tool X для phase_type Y имеет success_rate > 0.9
#   → cache: ("*", phase_type_Y, "tool_select") → tool_X

# Пример auto-populate pipeline:
def _maybe_promote_to_engram(learning: dict, match_count: int):
    """Promote frequently-matched learning to L1 deterministic cache."""
    if match_count < 3:
        return  # Not yet frequent enough

    # Build deterministic key from learning metadata
    files = learning.get("files", [])
    category = learning.get("category", "pattern")

    for file_path in files:
        key = _engram_key("*", file_path, category)
        ENGRAM_CACHE[key] = {
            "text": learning["text"],
            "source": f"promoted from L2 (matched {match_count}x)",
            "promoted_at": time.time(),
        }
```

### 11.5 Структура данных Level 1

```python
# Простой dict в RAM + JSON fallback на диске
# Файл: data/engram_cache.json (~50-200 entries max)

ENGRAM_CACHE: Dict[str, dict] = {}

def _engram_key(agent: str, file_path: str, action: str) -> str:
    """Deterministic key from context N-gram."""
    # Normalize: strip path to filename, lowercase action
    filename = Path(file_path).name if file_path else "*"
    return f"{agent}::{filename}::{action}"

def engram_lookup(agent: str, file_path: str, action: str) -> Optional[str]:
    """O(1) deterministic lookup. Returns cached lesson or None."""
    # Try exact match
    key = _engram_key(agent, file_path, action)
    if key in ENGRAM_CACHE:
        return ENGRAM_CACHE[key]["text"]

    # Try wildcard agent
    key_wild = _engram_key("*", file_path, action)
    if key_wild in ENGRAM_CACHE:
        return ENGRAM_CACHE[key_wild]["text"]

    return None  # → fall through to Level 2 (Qdrant semantic search)
```

### 11.6 Где вызывается

**В session_init (новый semantic_recall):**
```python
# BEFORE Qdrant search, try L1 cache
in_progress = context.get("task_board_summary", {}).get("in_progress", [])
for task in in_progress:
    # Check if we have cached knowledge about files in this task
    cached = engram_lookup(agent_type, task.get("files_hint", ""), "edit")
    if cached:
        context["engram_hits"].append(cached)
        # Skip Qdrant for this — we already know the answer

# Only go to Qdrant (L2) for uncached queries
if not context.get("engram_hits"):
    learnings = store.get_learnings_for_architect(query, limit=5)
```

**В pipeline (architect planning):**
```python
# Before asking LLM for plan, check if we have cached patterns
for file in task.changed_files:
    cached = engram_lookup("mcc_architect", file, "pattern")
    if cached:
        architect_context += f"\nKnown pattern for {file}: {cached}"
```

### 11.7 Что это даёт

| Аспект | Только Qdrant (сейчас) | + Level 1 Engram |
|--------|----------------------|-----------------|
| Latency для частых паттернов | ~200ms (embedding + cosine) | <1ms (dict lookup) |
| Детерминированность | Нет (зависит от embeddings) | Да для cached patterns |
| Стоимость | Embedding API call | 0 (RAM) |
| Для новых ситуаций | Работает | Fallback к Qdrant (L2) |

### 11.8 Границы

| Level 1 (Engram Cache) | Level 2 (Qdrant Semantic) |
|------------------------|--------------------------|
| Файл X всегда ломается так-то | Незнакомая ошибка, похожая на прошлый опыт |
| Tool Y лучший для phase Z | Какой tool подойдёт для новой задачи? |
| Агент A не должен трогать файл B | Кто работал над похожей задачей раньше? |
| Конкретный gotcha для конкретного модуля | Абстрактный урок из другого проекта |

### 11.9 Размер и lifecycle

- **Max entries:** 200 (LRU eviction)
- **Promotion threshold:** learning matched ≥3 times
- **Eviction:** LRU + temporal decay (не использовался 30 дней → evict)
- **Persistence:** `data/engram_cache.json` (загружается при старте)
- **Не путать с:** `engram_user_memory.py` (user preferences, отдельная система)

### 11.10 Приоритет реализации

Level 1 Engram cache — это **P3 (после semantic_recall и agent_briefing)**:

1. Сначала запускаем semantic_recall (Level 2 уже работает через resource_learnings)
2. Собираем статистику: какие learnings match-атся чаще всего
3. Когда видим повторяющиеся паттерны — добавляем Level 1 cache
4. Auto-promote из Level 2 → Level 1 при match_count ≥ 3

Без Level 2 (semantic_recall) нет данных для auto-populate Level 1. Поэтому порядок: L2 first → L1 grows organically.
