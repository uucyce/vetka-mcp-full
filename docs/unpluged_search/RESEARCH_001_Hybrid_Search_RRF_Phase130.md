# Hybrid Search с RRF (Reciprocal Rank Fusion)

**Рекомендуемая фаза:** 130
**Статус:** Не имплементировано
**Приоритет:** ВЫСОКИЙ
**Источник:** Беседы агентов, Phase 68-70 research

## Описание

Объединение BM25 keyword-поиска с семантическим векторным поиском через Reciprocal Rank Fusion. Формула: score = Σ(1/(k+rank_i)), k=60.

## Текущее состояние

- Qdrant semantic search работает (Phase 91, 95% ready)
- BM25 keyword search НЕ реализован
- RRF fusion НЕ реализован

## Технические детали

- Weaviate BM25 для keyword search
- Qdrant dense vectors для semantic
- RRF fusion algorithm (k=60)
- Multi-source ranking
- Query decomposition для сложных запросов

## Шаги имплементации

1. Добавить BM25 индексацию при file watch
2. Реализовать RRF fusion в search pipeline
3. Интегрировать в существующий dynamic_semantic_search()
4. Добавить UI toggle для типа поиска
5. Benchmark: сравнить качество с чистым semantic search

## Ожидаемый результат

Значительное улучшение качества поиска для mixed-type запросов
