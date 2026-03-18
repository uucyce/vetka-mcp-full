# RECON: Schema-as-Documentation + Structured Task Fields

**Date:** 2026-03-18
**Phase:** 191 (DEBUG session)
**Priority:** 3 (enhancement, not bug)

---

## Part 1: Schema-as-Documentation

### Problem
MCP schema descriptions — единственная документация которую агент реально читает при tool discovery.
Сейчас нет автоматической генерации human-readable docs из schema.

### Current State

**Schema определены в 3 местах:**
1. `src/mcp/vetka_mcp_bridge.py:327+` — 40 tools inline через `Tool()` конструктор
2. `src/mcp/mycelium_mcp_server.py:179+` — 24 tools, `MYCELIUM_TOOLS` list
3. `src/mcp/tools/task_board_tools.py:29-76` — `TASK_BOARD_SCHEMA` (single source of truth для task board)

**Каждый tool имеет:**
- Tool-level `description` (string)
- Property-level `description` для каждого параметра
- Constraints: `enum`, `minimum`, `maximum`, `default`

**Уже есть catalog generator:**
- `scripts/generate_reflex_catalog.py` (502 lines)
- Генерирует `data/reflex/tool_catalog.json` (94 tools, 79KB)
- Включает: namespace, kind, intent_tags, trigger_patterns, cost, permission
- **НЕ включает:** property-level descriptions, parameter details, примеры вызовов

**Существующие доки:**
- `docs/172_vetka_tools/TOOLS_SKILLS_CATALOG_2026-03-09.json` (33KB)
- `docs/172_vetka_tools/TOOLS_SKILLS_CATALOG_2026-03-09.csv`

### Proposal: Schema → Docs Generator

Расширить `generate_reflex_catalog.py` (или создать отдельный скрипт) чтобы:

1. **Парсить полные inputSchema** — не только tool name/description, но и все properties
2. **Генерировать Markdown reference** — один файл на namespace (vetka, mycelium)
3. **Включать:**
   - Tool name + description
   - Parameters table: name, type, required, default, description
   - Enum values где есть
   - Примеры вызовов (можно генерировать из defaults)
4. **Выходной формат:** `docs/api/VETKA_MCP_REFERENCE.md`, `docs/api/MYCELIUM_MCP_REFERENCE.md`

### Effort Estimate
- Скрипт: ~100 lines Python (парсинг schema + markdown generation)
- Интеграция: добавить в pre-commit или CI
- Разовый запуск: 2-3 секунды

### Affected Files
| File | Role |
|------|------|
| `scripts/generate_reflex_catalog.py` | Существующий catalog generator |
| `src/mcp/vetka_mcp_bridge.py` | Source: 40 tool schemas |
| `src/mcp/mycelium_mcp_server.py` | Source: 24 tool schemas |
| `src/mcp/tools/task_board_tools.py` | Source: TASK_BOARD_SCHEMA |
| `docs/api/` (new) | Output: generated reference docs |

---

## Part 2: Structured Task Fields

### Problem
Вся информация (target files, acceptance criteria, algorithm hints) валится в free-text `description`.
Агенты не могут структурированно читать эти данные.

### Current State — 65 полей, но нет target_files/acceptance_criteria

**УЖЕ СУЩЕСТВУЮТ близкие поля:**

| Поле | Тип | Назначение | Использование |
|------|-----|-----------|---------------|
| `completion_contract` | list | Человекочитаемые acceptance criteria | Мало используется |
| `allowed_paths` | list | Файлы которые агент МОЖЕТ менять | Ownership guard |
| `closure_files` | list | Файлы в scoped auto-commit | Commit scope |
| `closure_tests` | list | Команды для проверки | Verification |

**Проблема:** `completion_contract` и `allowed_paths` существуют, но:
- Не заполняются при создании тасков через MCP (не в schema "add" action)
- Агенты не знают о них (description в schema не указывает на них)
- UI не показывает их prominently

### Решение: НЕ добавлять новые поля, а активировать существующие

Вместо `target_files` + `acceptance_criteria` (ещё 2 поля в schema с 65):

1. **Промотировать `completion_contract`** — переименовать description в schema:
   ```
   "completion_contract": {
     "type": "array",
     "items": {"type": "string"},
     "description": "Acceptance criteria checklist. Each item = one verifiable condition. Example: ['API returns 200', 'tests pass', 'no console errors']"
   }
   ```

2. **Промотировать `allowed_paths`** как target_files:
   ```
   "allowed_paths": {
     "type": "array",
     "items": {"type": "string"},
     "description": "Target files/directories this task should modify. Also serves as ownership guard — agent won't touch files outside this list."
   }
   ```

3. **Добавить `implementation_hints`** (единственное НОВОЕ поле) — свободный текст для algorithm/approach:
   ```
   "implementation_hints": {
     "type": "string",
     "description": "Algorithm hints, approach notes, or technical guidance for the implementing agent"
   }
   ```

### Change Surface (Minimal)

**Backend (3 files):**

| File | Lines | Change |
|------|-------|--------|
| `src/mcp/tools/task_board_tools.py:29-76` | Schema | Обновить descriptions для `completion_contract`, `allowed_paths`; добавить `implementation_hints` |
| `src/mcp/tools/task_board_tools.py:216-238` | Handler | Пробросить `implementation_hints` в add action |
| `src/orchestration/task_board.py:622-672` | add_task() | Добавить param `implementation_hints` |
| `src/orchestration/task_board.py:704-797` | payload | Добавить `"implementation_hints": implementation_hints or ""` |
| `src/orchestration/task_board.py:910-924` | ADDABLE_FIELDS | Добавить `"implementation_hints"` |

**Frontend (optional, phase 2):**

| File | Change |
|------|--------|
| `client/src/components/panels/TaskCard.tsx` | Show `completion_contract` + `allowed_paths` |
| `client/src/components/panels/TaskEditor.tsx` | Edit `implementation_hints` |

### Backward Compatibility
- `implementation_hints` defaults to `""` — existing tasks unaffected
- `completion_contract`/`allowed_paths` already exist — just better descriptions
- No migration needed
