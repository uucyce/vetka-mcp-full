# RECON: Auto-inject docs content on claim/get for MCP agents

**Date:** 2026-03-19
**Phase:** 191+
**Priority:** P2
**Depends on:** MARKER_189.15 (dispatch docs inject — done), MARKER_191.1 (vetka_read_file fix — done)

## Problem

Pipeline agents (Dragon/Titan) получают docs content через dispatch_task() (MARKER_189.15).
Но MCP агенты (Claude Code, Desktop, Cursor) — нет. Они видят:
```json
{"architecture_docs": ["docs/190.../RECON.md"], "recon_docs": [...]}
```
Это пути-строки. Агент должен сам догадаться вызвать `vetka_read_file` для каждого файла.

## Current Flow

### claim action (task_board_tools.py:333-340)
```python
result = board.claim_task(task_id, agent_name, agent_type)
return result  # {"success": True, "task_id": ..., "assigned_to": ...}
```
Возвращает минимальный ответ без task data и без docs.

### get action (task_board_tools.py:291-298)
```python
task = board.get_task(task_id)
return {"success": True, "task": task}
```
Возвращает полный task dict, но docs — только пути.

## Proposed Solution

### For claim: return full task + docs content
```python
elif action == "claim":
    result = board.claim_task(task_id, agent_name, agent_type)
    if result.get("success"):
        task = board.get_task(task_id)
        result["task"] = task  # полный таск
        docs = _load_docs_content_sync(task)
        if docs:
            result["docs_content"] = docs
    return result
```

### For get: inject docs content
```python
elif action == "get":
    task = board.get_task(task_id)
    docs = _load_docs_content_sync(task)
    if docs:
        task["_docs_content"] = docs  # underscore = transient, не сохраняется
    return {"success": True, "task": task}
```

## Critical: Async Issue

- `handle_task_board()` — **sync** (task_board_tools.py:173)
- `_inject_docs_content()` — **async** (task_board.py:2043)
- Bridge calls sync: `result = handle_task_board(arguments)` (vetka_mcp_bridge.py:1746)

**Решение:** Написать sync версию `_load_docs_content_sync()` прямо в task_board_tools.py.
Async не нужен — чтение файлов синхронное. LLMModelRegistry budget не нужен — MCP агенты
сами управляют контекстом. Простой cap: 64KB total, 16KB per doc.

## Implementation Plan

### Файл: src/mcp/tools/task_board_tools.py

1. Добавить `_load_docs_content_sync(task, budget=65536, per_doc=16384) -> str`
   - Читает architecture_docs + recon_docs файлы
   - Per-doc cap + total budget
   - Возвращает formatted string или ""

2. Обновить claim handler (line 333-340):
   - После успешного claim: вернуть task + docs_content

3. Обновить get handler (line 291-298):
   - Добавить docs_content в task dict (transient field)

### Не трогаем:
- task_board.py (sync claim_task() остаётся как есть)
- vetka_mcp_bridge.py (handler остаётся sync)
- _inject_docs_content (async версия для dispatch — отдельно)

## Files

| File | Lines | Change |
|------|-------|--------|
| src/mcp/tools/task_board_tools.py | 173+ | Add _load_docs_content_sync() |
| src/mcp/tools/task_board_tools.py | 291-298 | get: inject docs |
| src/mcp/tools/task_board_tools.py | 333-340 | claim: return task + docs |
