# Multi-Model Council Pattern
**Рекомендуемая фаза:** 131
**Статус:** Частично (routing exists, council нет)
**Приоритет:** СРЕДНИЙ
**Источник:** Беседы агентов

## Описание
Маршрутизация задач к специализированным моделям: Grok → research, DeepSeek → math/code, Claude → synthesis, Gemini → multimodal.

## Текущее состояние
- ModelProvider enum реализован (Phase 64)
- Provider routing работает
- Council decision-making НЕ реализован
- Автоматический выбор модели по типу задачи НЕ работает

## Технические детали
- LangGraph state dispatch по типу задачи
- API key rotation между провайдерами
- Latency target: <200ms
- Silence Council Mode: 10-sec pause → 6-8 моделей параллельно
- Haiku summary результатов council

## Шаги имплементации
1. Создать task type classifier (research/code/synthesis/multimodal)
2. Реализовать auto-routing по классификации
3. Добавить parallel execution для council mode
4. Haiku-агрегация результатов
5. Метрики: tracking accuracy per model per task type

## Ожидаемый результат
Оптимальное использование сильных сторон каждой модели
