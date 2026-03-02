# MARKER_157_RESEARCH_REVIEW_JEPA_CONTEXT_PACKING_2026-03-01

Дата: 2026-03-01  
Основание: ответ Grok по `MARKER_157_RESEARCH_REQUEST_JEPA_CONTEXT_PACKING_2026-03-01.md`

## Итог
Статус: `PARTIAL_ACCEPT`  
Направление верное: **Hybrid adaptive (algorithmic-first, JEPA-conditional)**.

## Что принимаем (accept)
1. Decision: для text/code chat JEPA не mandatory, лучше conditional.
2. Правильный акцент на latency/SLO и anti-flap hysteresis.
3. Идея layered packing (`global_summary + critical_expansions + fallback`) полезна.
4. Сохранение stream/tools path без ломки — обязательное требование.

## Критичные несоответствия коду (must-fix before impl)
1. В ответе есть несуществующие API-ориентиры:
- `mcc_jepa_adapter.predict_embedding()` отсутствует.
- Фактический вход в JEPA-адаптер: `embed_texts_for_overlay(...)` в `src/services/mcc_jepa_adapter.py`.

2. Указанный “готовый runtime profile” для всех моделей в `provider_registry.py` как будто уже есть — это не так.
- Есть adaptive output budget, но нет готовой полноценной таблицы input-packing профилей в предложенном формате.

3. Заявленные численные улучшения (`+20% quality`, `95% win-rate`, точные latency-цифры) не подтверждены замерами из текущего репозитория.
- Это гипотезы, а не доказанные KPI.

4. Формула trigger/entropy требует калибровки на реальных логах проекта.
- Без этого высокий риск ложных срабатываний и режимного флапа.

## Решение по внедрению
Принимаем как архитектурный draft, но имплементацию начинаем только после адаптации к реальным контрактам кода.

## Исправленная практическая рамка (для Phase 157.1)
1. Не трогаем stream/tools маршруты.
2. Добавляем `ContextPacker` как обертку поверх существующих:
- `build_pinned_context`
- `build_viewport_summary`
- `build_json_context` (ELISION)
3. JEPA-path подключаем только через существующий `embed_texts_for_overlay(...)`.
4. Вводим trace-поля на каждый запрос:
- `packing_path` (`algo`/`hybrid-jepa`)
- `overflow_risk`
- `compression_ratio`
- `memory_layers_used`
- `jepa_provider_mode`
5. Сначала observability + A/B, потом ужесточение trigger-порогов.

## Marker verdict
- `MARKER_157.REVIEW.ACCEPT.DIRECTION`: PASS
- `MARKER_157.REVIEW.GAP.API_CONTRACTS`: FAIL
- `MARKER_157.REVIEW.GAP.METRICS_PROOF`: FAIL
- `MARKER_157.REVIEW.DECISION.HYBRID_WITH_CODE_REALITY`: PASS

