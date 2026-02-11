# MGC: Многоуровневая Иерархическая Память
**Рекомендуемая фаза:** 131
**Статус:** Не имплементировано (design ready)
**Приоритет:** ВЫСОКИЙ
**Источник:** Phase 99, беседы агентов

## Описание
Каскадная репликация: Primary (RAM) → Intermediate (Qdrant) → Cold (JSON disk). GenerationalCache class с MemoryProxy rate-limiting.

## Текущее состояние
- Phase 99 design documents готовы
- STMBuffer, MGCEntry dataclasses определены
- MemoryProxy design sketched
- Реализация НЕ начата

## Технические детали
- Gen 0: RAM (768D vectors, hot data)
- Gen 1: Qdrant (384D, warm data)
- Gen 2: JSON disk (256D, cold data)
- Gen 3: Archive (64D, historical)
- Rate limiting: 50 req/min через MemoryProxy
- Materialized Graph Cache для 3D viewport по zoom level

## Шаги имплементации
1. Реализовать GenerationalCache class
2. Создать MemoryProxy с rate limiting
3. Настроить cascade promotion/demotion rules
4. Интегрировать с viewport zoom levels
5. Добавить disk persistence (gzip after 7 days)

## Ожидаемый результат
Эффективное управление памятью для 10k+ файлов
