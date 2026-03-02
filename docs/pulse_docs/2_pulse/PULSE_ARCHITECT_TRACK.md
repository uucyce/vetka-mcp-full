# Pulse Architect Track (Main Agent)

Date: 2026-02-27  
Owner: Architect Codex (main thread)  
Status: Active

## Mission
Довести Pulse до production-ready ядра:
- стабильный BPM/Key/Scale в live;
- связка deterministic + JEPA без деградации latency;
- персонализация через ENGRAM/CAM-контур без хардкод-долга;
- формальные quality gates по тестам и метрикам.

## Non-Negotiables
- Никаких «магических» констант без конфиг-обоснования и sweep-артефакта.
- Любая новая логика: сначала audit marker, потом implementation marker, потом test marker.
- Детектор scale/key не может silently drift без telemetry-событий.
- Любой fallback должен быть объясним и наблюдаем в teletype/log.

## Marker Protocol (обязательный)
- `MARKER_AUDIT_*` — аудит текущей реализации и рисков.
- `MARKER_IMPL_*` — что именно внедрено.
- `MARKER_TEST_*` — что проверили, какие тесты/репорты добавили.
- `MARKER_BLOCKER_*` — блокеры/зависимости от другого агента/инфры.

## Architect Scope (сложный трек)
1. Inference architecture:
- улучшение arbitration deterministic vs JEPA;
- анти-drift для scale/key;
- confidence calibration и commit policy.

2. JEPA lifecycle:
- training/eval contracts;
- bias tuning strategy;
- reproducible benchmark design.

3. VETKA integration design:
- ENGRAM/CAM/STM/ARC/HOPE контракты;
- миграционный план с local bridge на полноформатную интеграцию.

4. Final quality gates:
- метрики success/fail;
- release-readiness criteria;
- regression matrix.

## Execution Queue (Architect)
- [ ] `MARKER_AUDIT_ARCH_1` Проверка реального состояния scale arbitration в App/Resolver.
- [ ] `MARKER_IMPL_ARCH_1` Вынести commit-policy в конфиг-слой (без разброса порогов по файлам).
- [ ] `MARKER_TEST_ARCH_1` Добавить tests на commit-policy и fallback-policy.
- [ ] `MARKER_AUDIT_ARCH_2` Проверить соответствие UI-state vs audio-state (active/detected/committed).
- [ ] `MARKER_IMPL_ARCH_2` Добавить strict sync contract (source-of-truth state map).
- [ ] `MARKER_TEST_ARCH_2` Интеграционный тест: one source update -> все представления синхронны.
- [ ] `MARKER_AUDIT_ARCH_3` Проверить packaged runtime риски (python scripts / data paths).
- [ ] `MARKER_IMPL_ARCH_3` Добавить packaging-safe fallback strategy.
- [ ] `MARKER_TEST_ARCH_3` E2E smoke для packaged paths (where possible).

## Notes to Terminal Codex
- Не менять deterministic-first контракт без явного запроса от Architect.
- Любая UI/UX задача должна сохранять диагностируемость (teletype + event tags).
- Перед крупной правкой: сначала короткий audit note в shared checklist.

