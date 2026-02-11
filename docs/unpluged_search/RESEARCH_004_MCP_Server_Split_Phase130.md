# MCP Server Split Architecture (3 сервера)

**Рекомендуемая фаза:** 130
**Статус:** Research done, implementation pending
**Приоритет:** ВЫСОКИЙ
**Источник:** Phase 128 Grok Research, Phase 129.3

## Описание

Разделение 35+ инструментов на 3 MCP сервера: MCP-UI, MCP-Pipeline, MCP-Files для лучшей изоляции и масштабирования.

## Текущее состояние

- 1 MCP сервер с 15+ tools
- Bottleneck при параллельных запросах
- Grok research (Phase 128) завершён
- Phase 129.3 — P1 priority

## Технические детали

- MCP-UI: viewport, camera, UI-related tools
- MCP-Pipeline: workflow, task board, agent tools
- MCP-Files: file search, edit, git operations
- HTTP transport для каждого
- Shared state через Qdrant + filesystem

## Шаги имплементации

1. Категоризировать текущие tools по группам
2. Создать 3 отдельных FastMCP сервера
3. Обновить .mcp.json конфигурацию
4. Тестировать изоляцию и параллелизм
5. Мигрировать клиентов (Claude Code, Cursor)

## Ожидаемый результат

Устранение bottleneck, возможность параллельного использования tools
