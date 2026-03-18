# RECON: Task Auto-Close False Positives

**Date:** 2026-03-18
**Severity:** CRITICAL
**Phase:** 191 (DEBUG session)

## Problem Statement

Post-commit hook закрывает таски, которые **не были explicitly claimed** текущим агентом.
Таск помечается "done" без реального выполнения = **ложная уверенность** что работа сделана.

## Root Cause Chain

```
git commit → git_tool.py:commit() → _auto_complete_tasks()
  → task_board.py:auto_complete_by_commit() → complete_task()
```

### Bug #1: Agent identity не передается при auto-close

**File:** `src/mcp/tools/git_tool.py`, line 264
```python
self._auto_complete_tasks(commit_hash, message)
```
Не передается `agent_id` — невозможно проверить, что коммитящий агент = owner таска.

### Bug #2: Claimed/running таски включены в eligible без проверки owner

**File:** `src/orchestration/task_board.py`, lines 1402-1405
```python
eligible = [
    t for t in self.tasks.values()
    if not t.get("require_closure_proof")
    and t["status"] in ("pending", "queued", "claimed", "running")
]
```
**Проблема:** `claimed` и `running` таски могут быть закрыты ЛЮБЫМ агентом.
Нет проверки `task.assigned_to == current_agent`.

### Bug #3: Агрессивный keyword matching

**File:** `src/orchestration/task_board.py`, lines 1429-1473

Matching правила (ANY из них триггерит auto-close):
1. **Direct ID mention:** `if task_id in commit_msg: return True` (line 1451)
2. **Tag match:** `if tag in commit_msg: return True` (lines 1454-1457)
3. **Title keyword match:** 3+ слов совпало = close (lines 1459-1464)
4. **Phase/MARKER patterns** (lines 1466-1471)

Title keyword matching особенно опасен — коммит "fix: update task scheduling" может совпасть с 5+ тасками.

### Bug #4: activating_agent фальсифицирован

**File:** `src/orchestration/task_board.py`, lines 1419-1421
```python
"activating_agent": str(task.get("assigned_to") or "git"),
```
Записывается `assigned_to` таска, а не реальный коммитер. Ложная атрибуция.

### Bug #5: Post-merge hook без проверки authority

**File:** `.git/hooks/post-merge`, line 57
- Извлекает task ID из merged коммитов
- Вызывает `promote_to_main()` без проверки ownership
- `promote_to_main()` (task_board.py:1174-1197) не проверяет кто делает merge

## Danger Scenarios

| Сценарий | Результат |
|----------|-----------|
| Agent A claim Task X, Agent B коммитит "fix task X" | Task закрыт под именем Agent A |
| Общий коммит "fix: update task scheduling" | 5+ тасков закрыты одним коммитом |
| Merge ветки с `[task:tb_xxxx]` в коммите | Post-merge promotes без authority check |
| `MARKER_136.AUTO_CLOSE_COMMIT` enabled | Даже pending/queued таски (не claimed) закрываются |

## Fix Strategy

### Minimal Fix (must-have)
1. **Передавать `agent_id` в `_auto_complete_tasks()`** из git_tool
2. **Исключить `claimed`/`running` таски из eligible** если `assigned_to != current_agent`
3. **Запретить auto-close для `pending`/`queued` тасков** (никто не claim = нельзя закрыть)

### Defensive Fix (should-have)
4. **Ужесточить matching:** требовать exact task_id match ИЛИ explicit `[task:ID]` tag
5. **Убрать title keyword matching** — слишком много false positives
6. **Добавить `closed_by_agent` field** с реальным ID коммитера
7. **Post-merge: проверять ownership** перед promote_to_main

### Audit Fix (nice-to-have)
8. **Добавить dry-run mode** для auto-close (log без закрытия)
9. **Audit log** всех auto-close с diff between claimed_by vs closed_by

## Affected Files

| File | Lines | Role |
|------|-------|------|
| `src/mcp/tools/git_tool.py` | 264, 336-353 | Entry point: _auto_complete_tasks |
| `src/orchestration/task_board.py` | 1381-1427 | auto_complete_by_commit() |
| `src/orchestration/task_board.py` | 1429-1473 | _commit_matches_task() |
| `src/orchestration/task_board.py` | 1079-1172 | complete_task() |
| `src/orchestration/task_board.py` | 1174-1197 | promote_to_main() |
| `.git/hooks/post-commit` | 1-34 | Hook entry |
| `.git/hooks/post-merge` | 1-65 | Merge auto-promote |
