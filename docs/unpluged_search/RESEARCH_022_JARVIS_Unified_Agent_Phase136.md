# JARVIS: Единый Агент-Фасад
**Рекомендуемая фаза:** 136
**Статус:** Частично спланировано
**Приоритет:** СРЕДНИЙ
**Источник:** Беседы агентов

## Описание
Единый фасад агента, который прозрачно переключается между LLM моделями. Personality persistence, model rotation, provider abstraction.

## Текущее состояние
- LearnerArchitecture с pluggable LLMs существует
- JARVIS как unified facade НЕ реализован
- Auto model rotation НЕ работает
- Personality persistence НЕ реализована

## Технические детали
- Single agent persona (JARVIS)
- Auto model switching по типу задачи
- Provider abstraction layer
- Personality persistence across model switches
- Chat-First Settings: настройка через естественный язык
- Integration с Hostess role

## Шаги имплементации
1. Создать JarvisAgent facade class
2. Реализовать auto-routing по task type
3. Добавить personality persistence layer
4. Chat-based settings parser
5. UI: единый чат-интерфейс JARVIS

## Ожидаемый результат
Бесшовный UX без видимого переключения моделей
