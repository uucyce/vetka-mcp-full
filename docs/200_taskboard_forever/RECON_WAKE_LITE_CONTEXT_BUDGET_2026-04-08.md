# RECON: Wake-Lite — Lightweight Notification Wake for Context Budget
**Date:** 2026-04-08 | **Author:** Eta (Harness Engineer 2)
**Status:** APPROVED — ready for implementation
**Triggered by:** Delta context collapse after 4-5 messages (91% budget on notification wake)

---

## 1. Problem

### Наблюдение
Delta получила уведомление "задача готова к верификации", проснулась, вызвала
`vetka_session_init` — и потеряла 91% контекстного бюджета за 4-5 сообщений.

### Корневая причина

```
wake signal → агент получает "vetka session init" → вызывает session_init
                                                         ↓
                                              ~3600 токенов ответа:
                                              - project_digest (achievements, phase)
                                              - task_board_summary (1163 pending)
                                              - engram learnings (200 entries)
                                              - JEPA session lens (15 items)
                                              - agent_metrics (7-day velocity)
                                              - memory_health (Qdrant, engram)
                                              - context_hints (2 tasks)
                                              - semantic_lessons
                                              - next_steps
```

Для цели "иди верифицируй задачу `tb_xxx`" нужно **~200-400 токенов**.
Получаем ~3600. Перерасход: **9-18x**.

### Масштаб проблемы

| Агент | Задача | Токены на wake | Реальная потребность | Перерасход |
|-------|--------|---------------|---------------------|------------|
| Delta | "verify tb_xxx" | 3600 | 300 | 12x |
| Epsilon | "verify tb_xxx" | 3600 | 300 | 12x |
| Alpha | "fix tb_xxx" | 3600 | 500 | 7x |
| Beta | "claim next task" | 3600 | 600 | 6x |

При флоте 8+ агентов и активном тасктборде → каждый wake = критическая утечка бюджета.

---

## 2. Анализ компонентов

### Текущий wake-флоу

```
action=complete (done_worktree)
    → TaskBoard._auto_notify()
        → notify Delta: ntype=task_done_worktree, message="Task tb_xxx done"
            → synapse_write.sh Delta "WAKE: Task tb_xxx done_worktree. Run /inbox."
                → Delta tmux: receives "/inbox" or full prompt
                    → Delta: calls vetka_session_init  ← ВОТ ПРОБЛЕМА
```

### Что реально нужно агенту при wake

**Delta/QA wake** (ntype=task_done_worktree):
```json
{
  "task_id": "tb_xxx",
  "title": "...",
  "action": "verify",
  "branch": "claude/cut-engine",
  "allowed_paths": [...],
  "closure_tests": [...],
  "commit_hash": "abc123"
}
```
Размер: ~300-500 токенов.

**Owner wake** (ntype=task_needs_fix):
```json
{
  "task_id": "tb_xxx",
  "title": "...",
  "action": "fix",
  "qa_verdict": "fail",
  "qa_notes": "...",
  "branch": "claude/harness-eta"
}
```
Размер: ~300-500 токенов.

**Agent fresh start** (новая сессия, нет контекста):
→ нужен полный session_init (~3600 токенов) — ЭТО НОРМАЛЬНО.

---

## 3. Решение: WAKE-LITE (3 компонента)

### Компонент 1: `vetka_session_init lite=True`

Новый параметр `lite: bool = False`. При `lite=True`:

**Возвращает** (~300-500 токенов):
- `role_context` (branch, owned_paths, callsign) — обязательно
- `unread_notifications` — с task_id и action hint
- `claimed_tasks` — задачи уже в работе у этой роли
- `ps` (protocol_status) — флаги session_init/task_claimed

**Пропускает** (экономия ~3200 токенов):
- `project_digest` (achievements, phase, system)
- `el` (engram learnings — 200 entries)
- `jsl` (JEPA session lens)
- `agent_metrics` (7-day velocity)
- `memory_health`
- `context_hints`
- `semantic_lessons`
- `rr` (reflex recommendations)
- `next_steps` (генерируется из digest)

### Компонент 2: Wake-сигнал с task_id

Обновить `TaskBoard._auto_notify()` и `synapse_write.sh` wake вызовы:

Сейчас:
```bash
synapse_write.sh Delta "WAKE: task tb_xxx done. Call /inbox."
```

Новый формат:
```bash
synapse_write.sh Delta "TASK-WAKE: tb_xxx needs verify. Run: vetka_task_board action=get task_id=tb_xxx — then verify. SKIP session_init."
```

Агент видит task_id прямо в промпте → `action=get task_id=tb_xxx` (~400 токенов) вместо session_init (~3600 токенов). **Экономия: 3200 токенов.**

### Компонент 3: CLAUDE.md template — разделить "start" vs "wake"

Сейчас в CLAUDE.md у всех агентов в Init:
```
1. mcp__vetka__vetka_session_init
```

Новый протокол:
```
## Init (новая сессия)
1. mcp__vetka__vetka_session_init [полный, только при старте]

## Wake (получен TASK-WAKE сигнал)
1. vetka_task_board action=get task_id=<id из сигнала>
2. Выполнить action (verify/fix/claim)
3. НЕ вызывать session_init — он не нужен при wake
```

---

## 4. Экономия

| Сценарий | До | После | Экономия |
|---------|----|-------|---------|
| Wake Delta на verify | 3600 | 400 | **3200 токенов (89%)** |
| Wake owner на fix | 3600 | 400 | **3200 токенов (89%)** |
| Новая сессия агента | 3600 | 3600 | 0 (норма) |
| Wake + lite session_init | 3600 | 500 | **3100 токенов (86%)** |

Delta с 128k контекстом: вместо 1 задачи до "critical" → **30+ задач** в одной сессии.

---

## 5. Задачи

### WAKE-LITE-1: lite mode для vetka_session_init
**File:** `src/mcp/tools/session_tools.py`
**Owner:** Eta
**What:** Add `lite: bool = False` parameter. When `lite=True`: skip digest, el, jsl, metrics, memory_health. Return only role_context + notifications + claimed_tasks + ps.
**Acceptance:** `session_init lite=True` returns ≤600 tokens, ≥300 tokens less than full.

### WAKE-LITE-2: Task-id в wake-сигнале
**File:** `src/orchestration/task_board.py` (метод `_auto_notify` / wake dispatch)
**Owner:** Eta (shared zone с Zeta — разные секции)
**What:** When auto-notifying Delta/Epsilon (ntype=task_done_worktree) or owner (task_needs_fix), include `task_id=<id>` and `action=verify|fix` in the wake message. Template:
`"TASK-WAKE tb_{id}: {action}. vetka_task_board action=get task_id=tb_{id}. SKIP session_init."`
**Acceptance:** wake message contains task_id and action; agent can act without session_init.

### WAKE-LITE-3: CLAUDE.md template — wake protocol
**File:** `data/templates/claude_md_template.j2`
**Owner:** Eta
**What:** Add "## Wake Protocol" section distinct from "## Init":
- Init (первый запуск/fresh session): session_init полный
- Wake (получен TASK-WAKE): action=get task_id=X → act → skip session_init
**Acceptance:** Every role CLAUDE.md regenerated with wake protocol section.

### WAKE-LITE-4: Тест lite mode + wake signal
**File:** `tests/test_wake_lite.py`
**Owner:** Delta (QA)
**What:**
1. Call session_init lite=True → verify response ≤600 tokens, contains role_context + notifications
2. Call action=notify ntype=task_done_worktree → verify wake message contains task_id
3. Simulate wake: parse task_id from message → call action=get → verify task data returned
**Acceptance:** 3 tests pass

---

## 6. Зависимости

```
WAKE-LITE-1 (session_tools.py lite mode) ─────┐
                                               ├── WAKE-LITE-4 (Delta test)
WAKE-LITE-2 (task_board.py wake message) ─────┘

WAKE-LITE-3 (claude_md_template.j2) ── independent (can ship separately)
```

Параллельно: WAKE-LITE-1 || WAKE-LITE-2 || WAKE-LITE-3 → затем WAKE-LITE-4.

---

## 7. Что НЕ меняем

- `vetka_session_init` без параметров — остаётся полным (для первого старта)
- Формат notifications (action=notifications) — не трогаем
- SQLite schema — не трогаем
- Существующие task_board actions — не трогаем
- Обратная совместимость: агенты без wake-protocol в CLAUDE.md работают как раньше

---

## 8. Маркеры

- `MARKER_WAKE_LITE.LITE_MODE` — session_tools.py lite parameter
- `MARKER_WAKE_LITE.TASK_ID_SIGNAL` — task_board.py wake message format
- `MARKER_WAKE_LITE.CLAUDE_PROTOCOL` — claude_md_template.j2 wake section
