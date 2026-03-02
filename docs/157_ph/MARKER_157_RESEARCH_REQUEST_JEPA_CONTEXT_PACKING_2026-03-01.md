# MARKER_157_RESEARCH_REQUEST_JEPA_CONTEXT_PACKING_2026-03-01

## RESEARCH REQUEST (for Grok): JEPA vs Algorithmic Context Packing for VETKA/MYCELIUM

### Контекст
Проект: `vetka_live_03`

Цель цикла:
- Пользователь может прикладывать очень большой контекст (история + pinned файлы + viewport + документы).
- Модель не захлёбывается по контексту (`context_length_exceeded`), но сохраняет качество ответа.
- В prompt попадает:
  - сжатая суть всего корпуса,
  - главный вектор/ядро темы,
  - разворот только критически важных фрагментов.

Ключевой вопрос:
- Нужна ли JEPA для этой задачи как обязательный слой,
- или достаточно алгоритмической упаковки контекста (без JEPA) с правильными лимитами/ранжированием/компрессией,
- или лучше гибрид (`if overflow-risk -> JEPA`).

---

## Предварительный разбор (Codex): за и против

Ниже не финальное решение, а стартовые гипотезы для проверки Grok.

### Вариант A: JEPA-first для preprompt упаковки
Плюсы:
- Может дать более устойчивый “семантический центр” на больших и шумных мультимодальных корпусах.
- Полезно, когда важно сохранять межмодальные связи (audio/video/text) в едином embedding-слое.

Минусы:
- Добавляет латентность и операционную сложность (runtime, health, fallback).
- Для текст/код-heavy chat может быть избыточным по cost/benefit.
- Риск: “красивый слой”, но без прироста качества относительно хорошего алгоритмического packing.

### Вариант B: Algorithmic-first (без JEPA в chat preprompt)
Плюсы:
- Проще и быстрее: ranking + ELISION + adaptive budget + progressive truncation.
- Легче дебажить и гарантировать SLO на first-token latency.
- Уже опирается на текущие рабочие слои CAM/MGC/ENGRAM/HOPE/viewport.

Минусы:
- Может хуже переносить мультимодальные и сильно разнородные корпуса.
- При экстремальном объеме контекста может теряться “глобальная семантическая ось”, если ранжирование настроено слабо.

### Вариант C: Hybrid adaptive (предпочтительная стартовая гипотеза)
Идея:
- По умолчанию algorithmic-first.
- JEPA включается только при подтвержденном overflow/entropy/modality-pressure.

Плюсы:
- Сохраняет скорость в обычных кейсах.
- Даёт запас на сложные тяжелые кейсы.
- Минимизирует риск постоянного runtime-overhead от JEPA.

Минусы:
- Нужны корректные триггеры и hysteresis, иначе будет флап режимов.
- Требуется хорошая observability, иначе трудно доказать, что switch policy оптимальна.

Рабочая гипотеза для проверки:
- Для повседневного VETKA chat (text/code) JEPA скорее `optional`.
- Для multimodal DAG/overlay/архитектурных батч-задач JEPA даёт больше ценности.

---

## Что уже подтверждено по коду (фактическая база)

1. В VETKA direct path уже есть контекстная сборка:
- `build_pinned_context` (Qdrant + CAM + Engram + Viewport + HOPE + MGC веса)
- `build_viewport_summary`
- `build_json_context` с ELISION-компрессией по умолчанию

2. Вызовы модели идут через `call_model_v2`/`call_model_v2_stream` с адаптивным `max_tokens` (на выход).
- Это защищает длину ответа, но не гарантирует, что входной prompt не переполнит окно модели.

3. ARC и часть orchestrator-memory логики path-dependent:
- в direct message path не всегда проходит полный orchestrator маршрут.

4. JEPA в проекте уже присутствует:
- MCC overlay / runtime adapter / semantic DAG hydration.
- Сейчас нет доказанного “must-have” участия JEPA именно в chat preprompt packing.

---

## Что нужно получить от Grok (обязательно)

1. **Decision framework**: JEPA vs non-JEPA vs hybrid
- Дай строгую decision matrix:
  - Когда JEPA реально приносит выигрыш в preprompt,
  - Когда JEPA только добавляет latency/сложность без окупаемости.
- Раздели по типам данных:
  - чистый текст/код,
  - мультимодал (audio/video),
  - смешанный проектный контекст.

2. **Архитектура “Context Packing Engine” для VETKA**
- Предложи production-схему из стадий:
  1) intake,
  2) dedupe,
  3) salience ranking,
  4) compression,
  5) layered assembly,
  6) overflow guard,
  7) provider/model-specific final budget.
- Дай формат выхода:
  - `global_summary`,
  - `semantic_core_vector/descriptor`,
  - `critical_expansions[]`,
  - `fallback_slices[]`.

3. **Overflow-safe strategy (без хардкода)**
- Нужна формула budgeting:
  - вход + выход <= context window,
  - динамический reserve,
  - per-model profile.
- Нужны правила деградации:
  - что выбрасывать первым,
  - что никогда не выбрасывать,
  - как избегать “потери смысла”.

4. **JEPA as conditional accelerator**
- Предложи конкретный `if/when` контракт:
  - `if documents_count / modality_mix / entropy / token_pressure > threshold -> JEPA path`.
- Дай анти-флап hysteresis (чтобы режим не прыгал on/off на каждом сообщении).

5. **Latency budget and SLO**
- Целевые бюджеты:
  - preprompt assembly p50/p95,
  - first-token latency p50/p95,
  - degradation budget under overload.
- Дай рекомендации, как не убить stream UX и tool selection.

6. **Интеграция с текущей memory системой (mandatory)**
- CAM/ARC/STM/MGC/ENGRAM/ELISION/ELISYA должны остаться “в игре”.
- Определи, кто “source of truth” на каждом шаге упаковки.
- Предложи trace-маркеры для каждого запроса:
  - `path`, `memory_layers_used`, `compression_ratio`, `overflow_risk`, `jepa_mode`.

7. **Тестовый план и acceptance**
- Unit + integration + load:
  - no context overflow under stress,
  - stable quality under compression,
  - no latency explosion.
- Минимум 5 тест-сценариев с метриками pass/fail.

---

## Важные ограничения

- Нельзя ломать:
  - streaming,
  - tool selection/approval path,
  - текущий memory-aware ranking.
- Нельзя делать “one-size-fits-all” хардкод бюджетов.
- Решение должно быть provider/model-agnostic, но с per-model профилями.
- Нужен план rollout по фазам + rollback.

---

## Специальный вопрос (критичный)

Дай прямой ответ в формате:
1. `JEPA required` / `JEPA optional` / `JEPA not recommended` для chat preprompt packing (text/code heavy).
2. Обоснование на архитектурном и performance уровне.
3. Если `optional` — точный adaptive trigger policy.

---

## Формат ответа Grok

Просим вернуть:
1. `Executive decision` (1-2 абзаца)
2. `Target architecture` (блок-схема и этапы)
3. `Algorithm details` (формулы + thresholds)
4. `Integration map` (куда встраивать в текущий код)
5. `Experiment plan` (A/B + KPI)
6. `Rollout plan` (Phase 157.x)
7. `Risks + mitigations`

---

## Зависимые файлы для исследования (обязательный контекст)

### Документы (концепция и терминология)
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/besedii_google_drive_docs/VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/besedii_google_drive_docs/Convolutional_neural_network_GROK.txt`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/103_ph/MEMORY_INTEGRATION_ANALYSIS.md`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/93_ph/MEMORY_SYSTEMS_SUMMARY.md`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/150_ph/stream_GROK.txt`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/157_ph/MARKER_157_MEMORY_FLOW_AUDIT_2026-03-01.md`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/157_ph/MARKER_157_ABBREVIATIONS_RUNTIME_MAP_2026-03-01.md`

### VETKA context assembly and prompt path
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/message_utils.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/chat_handler.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/provider_registry.py`

### Memory/orchestration
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/memory_manager.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/orchestrator_with_elisya.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/elision.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/engram_user_memory.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/mgc_cache.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/spiral_context_generator.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/cam_engine.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/arc_gap_detector.py`

### JEPA/MCC paths
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/mcc_jepa_adapter.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/jepa_runtime.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/jepa_http_server.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/mcc_predictive_overlay.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/semantic_dag_builder.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/knowledge_graph/jepa_integrator.py`

---

## Отдельно попросить Grok

Сформировать:
- `Phase 157 implementation checklist`
- `Performance guardrails` (hard fail conditions)
- `No-regression contract` для stream + tools + memory layers.
