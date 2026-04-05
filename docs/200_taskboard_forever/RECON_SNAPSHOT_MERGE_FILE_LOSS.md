# RECON: Snapshot Merge Loses Files Outside allowed_paths
# Phase 205 — Merge Strategy Audit

**Date:** 2026-04-04
**Author:** Eta (Harness Engineer 2)
**Status:** RECON — problem identified, solution pending
**Task:** tb_1775312xxx (see task board)

---

## 1. Problem Statement

`strategy=snapshot` в `merge_request` копирует **только файлы из `allowed_paths` задачи** в main.
Если коммит в ветке трогал файлы вне `allowed_paths` — они молча теряются.

**Реальный инцидент (2026-04-04):**
- Zeta реализовала `NOTIFY_BUS` fix в `task_board.py` + новый `event_bus.py`
- `allowed_paths` задачи = `["src/orchestration/task_board.py"]`
- snapshot взял только `task_board.py`, `event_bus.py` пропал
- Результат: 3 cherry-pick конфликта, 2 часа debug, однословный баг `source → source_agent` потребовал full investigation
- `event_bus.py` не попал в main

---

## 2. Code: Как работает snapshot сейчас

```python
# src/orchestration/task_board.py — MARKER_201.SNAPSHOT
if strategy == "snapshot":
    for fpath in allowed_paths:
        rc, _, err = await _git("checkout", branch, "--", fpath)
        # Только allowed_paths — всё остальное МОЛЧА ТЕРЯЕТСЯ
    await _git("add", "-A")
    await _git("commit", "-m", f"Snapshot merge {branch} ...")
```

`allowed_paths` — это **охранный список (ownership guard)** задачи, не инвентарь всех файлов коммита.
Snapshot использует его как фильтр для checkout — это семантическая ошибка.

---

## 3. История попыток: что пробовали и почему плохо

| Стратегия | Когда использовалась | Проблема | Почему отказались |
|-----------|---------------------|----------|-------------------|
| **cherry-pick** (default) | Phase 195–204, каждый день | Конфликт когда ветки разошлись >3 коммитов; `7c3f69500` блокирует весь pipeline | Не авто-восстанавливается, требует ручного `--abort` + retry |
| **merge --no-ff** | Phase 195 early | Тянет всю историю ветки в main, merge commits замусоривают лог | Abandoned — history pollution |
| **squash** | Phase 196–197 | Теряет attribution (кто что написал); один fat commit сложно ревьюить | Частично используется для мелких задач |
| **snapshot** | Phase 201+ (introduced MARKER_201.SNAPSHOT) | **Теряет файлы вне allowed_paths** — это текущая проблема | Всё ещё используется как fallback для конфликтных cherry-pick |
| **cherry-pick + skip ancestors** | MARKER_200.IS_ANCESTOR | Лучше чем pure cherry-pick, но конфликт на shared файлах (task_board.py) всё ещё ломает | Частичное улучшение |
| **batch_merge** | Phase 198+ | Накопление 40+ `done_worktree` задач — Commander bottleneck | Организационная, не техническая проблема |
| **ручной git merge** (запрещён) | Попытки в кризис | Пропускает task promotion pipeline, статусы ломаются | **ЗАПРЕЩЕНО** (feedback_merge_via_taskboard.md) |

---

## 4. Корневые причины конфликтов (все известные)

### 4.1 Snapshot теряет файлы (текущий баг)
- `allowed_paths` = ownership guard, не file manifest
- `event_bus.py`, `srcsrv/notify_bus.py` и другие sidecar-файлы из задачи не попадают в main

### 4.2 Cherry-pick конфликты на shared файлах
- `task_board.py` — shared zone между Eta и Zeta
- Каждый агент коммитит туда независимо → diverged history → cherry-pick conflict
- `7c3f69500` (ROLE_MEMORY recon) — пример commit который блокирует pipeline Eta

### 4.3 Worktree branches долго живут без rebase
- harness-eta отстаёт от main на N коммитов
- Чем дольше ветка живёт — тем хуже конфликты

### 4.4 allowed_paths не отражает реальный footprint задачи
- Агент создаёт sidecar файлы (тесты, конфиги, новые модули) вне `allowed_paths`
- task_board не знает об этих файлах при merge

---

## 5. Варианты решения (для исследования)

### Option A: snapshot берёт все файлы изменённые в коммитах (не только allowed_paths)
- `git diff main..branch --name-only` → список всех изменённых файлов
- snapshot checkouts всё это, не только allowed_paths
- **Риск:** может тянуть файлы других агентов если ветка shared

### Option B: closure_files как явный merge manifest
- Агент при `action=complete` указывает `closure_files=[...]` — исчерпывающий список
- merge_request использует closure_files вместо allowed_paths для snapshot
- **Риск:** агент может забыть указать файл

### Option C: snapshot + git diff auto-detection
- При strategy=snapshot, если `allowed_paths` не покрывает все изменённые файлы — warning + auto-expand
- Логика: `actual_changed = git diff main..branch --name-only`, `missing = actual_changed - allowed_paths`
- Если `missing` не пустой — либо добавить в snapshot, либо вернуть error

### Option D: cherry-pick с auto-fallback на squash (не snapshot)
- cherry-pick сначала
- При конфликте — auto-abort + retry через squash (не snapshot)
- squash не теряет файлы, но теряет attribution
- **Проблема:** squash тоже может конфликтовать на shared файлах

### Option E: Per-agent merge branches (pre-integration layer)
- Не мержить напрямую worktree → main
- Сначала мержить в `integration/agent-name` ветку
- Тестировать integration branch → потом fast-forward main
- **Риск:** усложняет pipeline, больше веток

### Option F: File manifest в задаче (расширение task schema)
- Новое поле `merge_manifest: [files]` — явный список файлов для merge
- Агент обновляет при каждом коммите
- merge_request использует manifest вместо allowed_paths
- Самое чистое но требует изменения протокола

---

## 6. Что нужно исследовать у Grok

1. Какой паттерн merge для multi-agent worktree workflow рекомендуется в production?
2. Есть ли Git-native способ "взять все файлы изменённые в commits X..Y, но только если они не конфликтуют с main"?
3. Как решить проблему sidecar files в snapshot strategy без изменения task schema?
4. Есть ли паттерн "merge manifest" в существующих CI/CD системах?

---

## 7. Рекомендация для таска

**Приоритет:** P1 (блокирует надёжность всего pipeline)
**Домен:** harness (task_board.py)
**Тип:** research → fix
**Предварительный выбор:** Option C (snapshot + git diff auto-detection) как наименее инвазивный
