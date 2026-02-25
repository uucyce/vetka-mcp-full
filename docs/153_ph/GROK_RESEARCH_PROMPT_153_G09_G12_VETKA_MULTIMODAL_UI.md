# Grok Research Prompt — Phase 153: VETKA Multimodal UI (G09/G12 Closure)

**Для:** `@x-ai/grok-4.1-fast`  
**PROTOCOL:** `RECON + markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`  
**Фокус:** только VETKA (не MCC/Mycelium UI), мультимедиа импорт/сканирование/граф  
**Цель:** получить максимально подробный research (20k+ знаков), который можно напрямую переводить в имплементацию без цикла правок.

---

## 0) Важно: Режим исследования

Ты работаешь в режиме **code-aware архитектурного research**:
- не фантазировать про несуществующие роуты/файлы;
- опираться на указанные файлы и их текущие контракты;
- если чего-то не хватает, явно отмечать `UNVERIFIED` + что именно нужно проверить;
- предлагать решения только с учетом существующей архитектуры VETKA.

---

## 1) Контекст задачи

Мы уже сделали backend-цепочку для мультимедиа в VETKA:

1. Ingest:
- policy gate (`mime_policy`)  
- watcher index-file с OCR/STT fallback  
- triple-write multimodal reindex  

2. Storage:
- `media_chunks` пишутся в Qdrant (`vetka_elisya`) как `point_type=media_chunk`  

3. Retrieval:
- endpoint поиска chunk’ов (`/api/triple-write/media-chunks/search`)  

4. Graph payload:
- chunk nodes/edges уже прокидываются в `/api/tree/data` через `artifact_scanner`  

**Проблема:** нужен frontend UX слой и UX-архитектура для полного закрытия `G09/G12` в VETKA: как пользователю работать с chunk-узлами, фильтрами, переходами по таймкодам, плотностью графа, и как не убить производительность/читаемость.

---

## 2) Обязательные файлы контекста (прочитать и учитывать)

### 2.1 Основной отчёт гэпов
- `docs/153_ph/CODEX_RECON_phase153_gap_closure_independent_report.md`

### 2.2 Новый capability/stream документ (для event-контрактов)
- `docs/152_ph/CAPABILITY_MATRIX_UNIFIED_STREAM_TOOLS_SPEC.md`

### 2.3 Backend routes и payload
- `src/api/routes/tree_routes.py`
- `src/api/routes/triple_write_routes.py`
- `src/api/routes/watcher_routes.py`
- `src/api/routes/artifact_routes.py`

### 2.4 Multimodal/scanner layer
- `src/services/artifact_scanner.py`
- `src/scanners/embedding_pipeline.py`
- `src/scanners/mime_policy.py`
- `src/scanners/qdrant_updater.py`

### 2.5 Storage/orchestration
- `src/orchestration/triple_write_manager.py`

### 2.6 Frontend (VETKA UI, мультимедиа/артефакты/граф)
Сначала найди актуальные файлы, связанные с:
- tree graph rendering,
- artifact panel/media viewer,
- edge styling/legend,
- node interaction/click handlers,
- socket/tree data adapters.

Если точный файл не найден — верни список кандидатов + уровень уверенности.

---

## 3) Технические маркеры (используй в ответе)

Используй эти маркеры в отчёте Grok:
- `MARKER_153.RESEARCH.G09G12.UI_STATE_MODEL`
- `MARKER_153.RESEARCH.G09G12.GRAPH_DENSITY_POLICY`
- `MARKER_153.RESEARCH.G09G12.CHUNK_INTERACTION`
- `MARKER_153.RESEARCH.G09G12.TIMECODE_NAV`
- `MARKER_153.RESEARCH.G09G12.SEARCH_UX`
- `MARKER_153.RESEARCH.G09G12.PERF_BUDGET`
- `MARKER_153.RESEARCH.G09G12.ACCESSIBILITY`
- `MARKER_153.RESEARCH.G09G12.MOBILE_POLICY`
- `MARKER_153.RESEARCH.G09G12.API_CONTRACT_PATCHES`
- `MARKER_153.RESEARCH.G09G12.TEST_PLAN`
- `MARKER_153.RESEARCH.G09G12.ROLL_OUT_FLAGS`
- `MARKER_153.RESEARCH.G09G12.RISKS_AND_ROLLBACK`

---

## 4) Что именно исследовать (подробно)

### A. UX-модель взаимодействия с media chunks в графе VETKA
Нужен полный state model:
- default view: что видно сразу;
- когда/как появляются chunk nodes;
- какие edge types показывать по умолчанию (`artifact`, `reference`, `temporal`, `media_chunk`, `temporal_chunk`);
- как переключать уровни детализации.

Сделай:
1. state diagram (текстом/таблицей)  
2. события переходов  
3. пользовательские сценарии (минимум 8)

---

### B. Политика плотности графа (anti-overload)
Исследуй и предложи:
- лимит chunk-узлов на артефакт (динамический по zoom/LOD);
- глобальные лимиты по viewport;
- алгоритм progressive reveal;
- fallback при перегрузке (cluster node, sampled mode, edge thinning).

Нужны:
1. конкретные формулы/эвристики  
2. числовые дефолты  
3. trade-offs

---

### C. Timecode UX (клик по chunk -> media jump)
Нужна точная спецификация:
- как клик по chunk ведёт в панель артефакта;
- как передается `start_sec`/`end_sec`;
- как синхронизируется выделение в графе и плеере;
- что делать для audio/video и для transcription-only режима.

Дай:
1. API/UI контракт поля  
2. пример payload  
3. обработка ошибок (нет media source, поврежден файл, таймкод вне диапазона)

---

### D. Search UX для chunk-поиска
Мы уже имеем backend endpoint `POST /api/triple-write/media-chunks/search`.
Исследуй frontend стратегию:
- быстрый поиск по фразе;
- фильтры (modality, confidence, parent file, time range);
- группировка результатов по артефакту;
- “найти на графе” + “прыжок к таймкоду”.

Нужно:
1. UX flow  
2. ranking hints на UI (почему этот результат выше)  
3. debounce/caching стратегия

---

### E. Производительность и лимиты
Сформируй бюджет:
- latency budgets (поиск, рендер, переход);
- max nodes/edges before degradation;
- влияние на FPS при открытом графе;
- telemetry набор для наблюдаемости.

Выдай:
1. таблицу бюджетов (desktop/mobile отдельно)  
2. метрики для трекинга деградации  
3. recommended feature flags rollout

---

### F. Accessibility и Mobile policy
Нужна pragmatic версия:
- keyboard navigation;
- reduced motion;
- цвет/контраст для новых edge типов;
- mobile-режим (collapsed chunks / list-first / timeline drawer).

---

## 5) Что нужно отдать в ответе (формат)

Ответ должен включать:

1. **Executive summary** (5–10 bullets)  
2. **Code-anchored findings** (с привязкой к файлам из контекста)  
3. **UI architecture proposal** (state model + data flow)  
4. **Concrete patch map** (какие файлы и что менять)  
5. **API contract deltas** (если нужно расширение)  
6. **Performance/telemetry plan**  
7. **Test plan** (unit + integration + e2e + acceptance)  
8. **Rollout plan** (feature flags + rollback)  
9. **Open questions** (если останутся)  

---

## 6) Жесткие требования к качеству ответа

- Никаких общих слов “можно сделать лучше” без конкретики.
- Каждый большой тезис должен иметь:
  - где в коде это связано,
  - что именно изменить,
  - ожидаемый эффект.
- Если предлагается новый endpoint/поле — показать backward compatibility.
- Указывать риски и anti-regression действия.

---

## 7) Вопросы, на которые нужен прямой ответ (чеклист)

Ответь явно `YES/NO + explanation`:

1. Достаточно ли текущей backend цепочки для production UX без новых backend endpoints?
2. Нужен ли отдельный endpoint для “chunk neighbors by artifact/time window”?
3. Нужен ли отдельный client-side store для chunk graph layer?
4. Нужен ли режим “hide all chunk nodes” по умолчанию?
5. Нужно ли разделять edge legend на advanced/basic mode?
6. Можно ли сделать mobile-first fallback без потери core функциональности?
7. Какие 3 самых рискованных места дадут регресс первыми?

---

## 8) Целевой результат этого research

После твоего ответа команда должна иметь:
- готовый blueprint для реализации frontend UX части `G09/G12`;
- минимум неопределенностей;
- список конкретных файлов и шагов внедрения;
- понятный план тестирования и rollout.

---

MARKER_153.RESEARCH.G09G12.PROMPT_READY
