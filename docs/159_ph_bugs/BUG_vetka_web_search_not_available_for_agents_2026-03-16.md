# BUG: vetka_web_search не доступен агентам в чате VETKA

**Дата:** 2026-03-16  
**Статус:** Open  
**Приоритет:** High  
**Тэги:** `bug`, `phase159`, `search`, `tools`, `agent-permissions`

## Описание

Модели, вызываемые в чате VETKA (сольный чат и командный чат), **не имеют доступа** к `vetka_web_search` (Tavily) через function calling, хотя:
1. Unified Search UI (Cmd+K) корректно использует Tavily
2. Backend `WebSearchTool` работает и использует `UnifiedKeyManager`

## Симптомы

- Агенты в чате (Default, PM, Dev, QA, Architect, Researcher) не могут выполнять web search
- Researcher, который должен делать research, не имеет доступа к поиску по интернету
- Ошибок в логах нет — просто tools не передаются в LLM

## Root Cause

Две системы tool permissions:

1. **SAFE_FUNCTION_CALLING_TOOLS** (`src/mcp/tools/llm_call_tool.py:46-74`)
   - Содержит `vetka_web_search` в allowlist
   - Используется для фильтрации unsafe tools при FC

2. **AGENT_TOOL_PERMISSIONS** (`src/agents/tools.py:1462-1565`)
   - Определяет какие tools получают конкретные агенты
   - **`vetka_web_search` НЕ добавлен ни в одну роль**

## Архитектурные документы

- `docs/172_vetka_tools/REFLEX_ROADMAP_CHECKLIST_2026-03-10.md` — REFLEX архитектура, связь с AGENT_TOOL_PERMISSIONS
- `docs/172_vetka_tools/REFLEX_ARCHITECTURE_BLUEPRINT_2026-03-10.md` — Section 5.3: AGENT_TOOL_PERMISSIONS
- `docs/114_ph/SCOUT_114.4_MCP_TOOLS_INVENTORY.md` — Section "Issue #1: Missing Tools in AGENT_TOOL_PERMISSIONS"
- `docs/118_ph/PHASE_118_COMPLETION_AND_MYCELIUM_AUDIT.md:263` — "Tavily API key support registered but NOT wired to pipeline agents"
- `docs/unpluged_search/PH123_Pipeline_Function_Calling.md:210` — "Choose tools per agent — give coder web search"
- `src/mcp/tools/llm_call_tool.py:46-74` — SAFE_FUNCTION_CALLING_TOOLS
- `src/agents/tools.py:1462-1565` — AGENT_TOOL_PERMISSIONS (место where bug is)

## Решение

Добавить `vetka_web_search` в `AGENT_TOOL_PERMISSIONS` для ролей:
- `Researcher` — primary (основная роль для research)
- `Architect` — для архитектурного research
- `Dev` — для поиска документации
- `Default` — fallback для неизвестных моделей

Также добавить:
- `vetka_library_docs` — для поиска документации библиотек

## Связанные задачи

- `tb_1771092080_6` — C-149.2: Unified Search wire Tavily web provider (queued)
