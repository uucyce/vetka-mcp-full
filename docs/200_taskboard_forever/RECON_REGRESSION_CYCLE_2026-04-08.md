# RECON: Regression Cycle — needs_fix Tasks Merged Without Fixes
**Date:** 2026-04-08 | **Author:** Eta (Harness Engineer 2)
**Status:** APPROVED — ready for implementation
**Triggered by:** Commander question "куда смотрит наш guard?"

---

## 1. Problem

### Наблюдение
Задачи с статусом `needs_fix` (QA отклонил) попадают в main без исправлений.
Результат: один и тот же баг всплывает снова и снова в следующих итерациях QA.

### Корневая причина

```
verify_task(verdict=fail)
    → status = needs_fix
    → notify owner: "fix needed"
        → owner sees notification
        → but: action=merge_request is still callable with status=needs_fix!
            ↓
            merge_request() → MARKER_201.QA_WARN:
                _qa_skipped = task.get("status") != "verified"
                if _qa_skipped:
                    logger.warning("QA gate skipped by Commander")
                    # ← ONLY LOGS. DOES NOT RETURN. DOES NOT BLOCK.
                # → continues to git merge!
```

### Два вектора атаки

**Вектор A: Прямой merge с needs_fix статусом**
- Commander вызывает `action=merge_request task_id=tb_xxx` когда статус = `needs_fix`
- Guard видит это, логирует warning, продолжает merge
- Задача с незафиксированным багом попадает в main

**Вектор B: Отсутствие structured notes при needs_fix**
- QA вызывает `verify_task(verdict=fail, notes="bad")`
- `notes` — только 3 слова, без root_cause, без failing tests
- Owner получает уведомление с бесполезным описанием
- Не знает что именно фиксить → делает случайные изменения → снова fails QA

---

## 2. Код: где именно дыры

### Дыра 1: merge_request() — MARKER_201.QA_WARN (строки 4713-4732)

```python
# src/orchestration/task_board.py, строки 4713-4732
_qa_skipped = task.get("status") != "verified"
if _qa_skipped:
    self._append_history(task, event="qa_skipped_warning", ...)
    self._save_task(task)
    logger.warning("[MergeRequest] Task %s status='%s', not verified. QA gate skipped by Commander.", ...)
# ← НЕТУ return {"success": False, "error": "..."}
# Продолжает выполнение до git merge
```

**Что нужно:** вернуть `{"success": False, "error": "..."}` если статус == `needs_fix`.
Commander-override должен быть явным (`force=True` параметр), а не молчаливым.

### Дыра 2: verify_task() — нет валидации notes (строки 3681-3720)

```python
# src/orchestration/task_board.py, строки ~3695-3700
elif verdict == "fail":
    new_status = "needs_fix"
# нет проверки len(notes) > 50
# нет проверки наличия root_cause
# notes обрезается до 300 символов — это единственная валидация
```

**Что нужно:** при `verdict=fail` требовать `notes` ≥ 50 символов. Рекомендовать структуру.

### Нет дыры (проверено): branch-level check

Проверил весь `merge_request()` — branch-level проверки других `needs_fix` задач на той же ветке **нет**.
Но это менее критично: один task_id = один контракт. Блокировки per-task достаточно.

---

## 3. Масштаб проблемы

| Метрика | Значение |
|---------|---------|
| Текущих `needs_fix` задач | 2 (tb_1774648952, tb_1774649270, оба PARALLAX) |
| Блокирует ли guard merge? | **НЕТ** — только логирует warning |
| Требует ли QA structured notes? | **НЕТ** — notes≥1 символ проходит |
| Можно ли смерджить needs_fix прямо сейчас? | **ДА** — через action=merge_request |

---

## 4. Решение: MERGE-GUARD (2 компонента)

### Компонент 1: Hard block в merge_request()

**Файл:** `src/orchestration/task_board.py`, метод `merge_request()`

**Сейчас** (MARKER_201.QA_WARN):
```python
_qa_skipped = task.get("status") != "verified"
if _qa_skipped:
    logger.warning("QA gate skipped by Commander.")
    # → продолжает
```

**После:**
```python
# MARKER_MERGE_GUARD.HARD_BLOCK
_status = task.get("status", "")
if _status == "needs_fix":
    return {
        "success": False,
        "error": (
            f"Task {task_id} is in needs_fix status — merge blocked. "
            "Fix the QA issues and re-verify before merging. "
            "Commander override: add force=True to bypass (logged)."
        ),
        "task_status": _status,
        "hint": "vetka_task_board action=verify task_id=<id> verdict=pass",
    }
elif _status != "verified":
    # warn-only for other non-verified statuses (done_worktree, pending, etc.)
    logger.warning("[MergeGuard] Task %s status='%s', not verified. Proceeding with warning.", ...)
```

Добавить параметр `force: bool = False` в сигнатуру. При `force=True` и `needs_fix`:
- Логировать с severity ERROR (не warning)
- Добавить в history `event="force_merge_override"` с reason
- Продолжить merge

### Компонент 2: Structured notes guard в verify_task()

**(уже есть как отдельный таск tb_1775670715 QA-GUARD)**

Смотри `RECON_WAKE_LITE_CONTEXT_BUDGET_2026-04-08.md` для аналогии.

При `verdict=fail` и `len(notes.strip()) < 50`:
```python
return {
    "success": False,
    "error": "Verdict 'fail' requires notes ≥ 50 chars. Include: root_cause, failing_tests.",
    "hint": "notes='root_cause: X. failing_tests: test_foo. steps: Y'",
}
```

---

## 5. Задачи

### MERGE-GUARD-1: Hard block needs_fix в merge_request()
**File:** `src/orchestration/task_board.py`, метод `merge_request()`
**Owner:** Eta
**What:**
- Изменить MARKER_201.QA_WARN: добавить hard block если status == "needs_fix"
- Добавить параметр `force: bool = False` для Commander override с ERROR logging
- Сохранить warn-only для других non-verified статусов (не ломаем Commander workflow)
**Acceptance:**
- `action=merge_request task_id=<needs_fix_task>` → `{"success": False, "error": "merge blocked"}`
- `action=merge_request task_id=<needs_fix_task> force=True` → merge proceeds, ERROR logged
- `action=merge_request task_id=<done_worktree_task>` → warning logged, merge proceeds (unchanged)

---

## 6. Зависимости

```
MERGE-GUARD-1 (merge_request hard block) ─── независимый
QA-GUARD      (verify_task notes guard)  ─── tb_1775670715, независимый

Оба можно делать параллельно.
```

---

## 7. Что НЕ меняем

- Commander workflow для non-needs_fix статусов — остаётся warn-only
- `verify_task()` logic кроме notes validation (tb_1775670715)
- SQLite schema — не трогаем
- Нотификации — не трогаем
- MARKER_201.QA_WARN комментарий обновится → MARKER_MERGE_GUARD.HARD_BLOCK

---

## 8. Маркеры

- `MARKER_MERGE_GUARD.HARD_BLOCK` — merge_request() block для needs_fix
- `MARKER_MERGE_GUARD.FORCE_OVERRIDE` — force=True Commander escape hatch
- `MARKER_QA_GUARD.NOTES_MIN` — verify_task() notes validation (tb_1775670715)
