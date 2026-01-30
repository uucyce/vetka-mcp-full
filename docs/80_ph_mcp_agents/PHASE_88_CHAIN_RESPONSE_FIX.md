# Phase 88: Agent Chain Response Fix

**Дата:** 2026-01-21
**Статус:** ✅ CODE FIXED (требуется перезапуск)

## Проблема

PM упоминает агентов (@Researcher, @Dev) в ответе, но они НЕ вызываются.

Логи показывают:
```
[GROUP_DEBUG] Agent PM (Claude Opus 4.5) mentioned: ['Researcher', 'Dev', 'browser', 'Dev']
```

Но после этого нет `Added X to responders from agent @mention`.

## Root Cause

В `group_message_handler.py` строки 645-662 был код с exact match только по display_name:
```python
# БЫЛО (broken):
if pname.lower() == mentioned_name.lower():
    mentioned_participant = pdata
    break
```

Проблема: `"Researcher"` ≠ `"Researcher (Grok 4)"` - не матчилось.

## Fix Applied

Добавлены 3 стратегии matching:

```python
# Strategy 1: Exact display_name match
if pname == mentioned_lower:
    mentioned_participant = pdata
    break
# Strategy 2: Match agent_id
if agent_id == mentioned_lower:
    mentioned_participant = pdata
    break
# Strategy 3: Match display_name prefix (before parentheses)
if '(' in pname and pname.split('(')[0].strip() == mentioned_lower:
    mentioned_participant = pdata
    break
```

## Файлы изменены

| Файл | Строки | Изменение |
|------|--------|-----------|
| src/api/handlers/group_message_handler.py | 645-665 | 3 стратегии matching + debug logging |

## Тестирование

**Требуется перезапуск сервера** для применения изменений.

### Тест в чате "@mention call отладка"

1. Отправить сообщение с @PM
2. PM должен ответить и упомянуть других агентов
3. Те агенты должны автоматически ответить

### Ожидаемые логи после фикса:

```
[GROUP_DEBUG] Agent PM mentioned: ['Researcher', 'Dev']
[GROUP_DEBUG] Added Researcher to responders from agent @mention (queue size: 2)
[GROUP_DEBUG] Added Dev to responders from agent @mention (queue size: 3)
```

## Связанные фазы

- Phase 80.6: Agent isolation (предотвращение infinite loops)
- Phase 86: MCP @mention triggering
- Phase 87: Watchdog → Qdrant integration

---
*Phase 88 - Agent Chain Response Fix*
