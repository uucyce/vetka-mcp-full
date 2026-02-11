# ENGRAM: Внешний Модуль Памяти (DeepSeek Research)
**Рекомендуемая фаза:** 131
**Статус:** Не имплементировано (pure research)
**Приоритет:** СРЕДНИЙ
**Источник:** engram_grok_research.txt, DeepSeek paper Jan 2026

## Описание
Внешний слой памяти O(1) lookup table для статических паттернов. Offload в RAM/DRAM. Интеграция с существующей архитектурой CAM + ELISYA + Qdrant.

## Текущее состояние
- PoC code sketches в research файле
- Интеграция НЕ начата
- Архитектура аддитивная (не заменяет существующее)

## Технические детали
- Hash-table lookup для static patterns
- Интеграция с CAM surprise metrics
- JARVIS-memory: сжатие чат-взаимодействий как engrams
- Vector-to-original file tracking
- Surprise filter: только low-surprise (<0.5) в Engram

## Шаги имплементации
1. Создать EngramTable class (RAM-based hash table)
2. Реализовать O(1) lookup для частых паттернов
3. Интегрировать с CAM surprise scoring
4. Добавить JARVIS-memory compression
5. Benchmark: замерить token savings

## Ожидаемый результат
30-40% экономия токенов при работе с повторяющимися контекстами
