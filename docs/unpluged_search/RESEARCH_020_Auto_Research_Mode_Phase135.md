# Auto-Research Mode (Background Research Agent)
**Рекомендуемая фаза:** 135
**Статус:** Не имплементировано
**Приоритет:** СРЕДНИЙ
**Источник:** Беседы агентов, Phase 68-70

## Описание
Background research scheduler с мониторингом тем. Автоматический запуск research агента по расписанию.

## Текущее состояние
- Research через MCP manual (vetka_research tool)
- Автоматический scheduling НЕ существует
- Topic monitoring НЕ реализован
- Report generation manual

## Технические детали
- Research agent scheduling (cron-like)
- Topic monitoring через web search APIs
- Relevance monitoring с CAM surprise
- Auto-report generation в Qdrant
- Integration с Tavily search
- Heartbeat-triggered research tasks

## Шаги имплементации
1. Создать ResearchScheduler с cron-like API
2. Настроить topic monitoring rules
3. Интегрировать с Tavily для web search
4. Auto-save reports в Qdrant + filesystem
5. UI: настройка тем для мониторинга

## Ожидаемый результат
Автоматическое обновление knowledge base по заданным темам
