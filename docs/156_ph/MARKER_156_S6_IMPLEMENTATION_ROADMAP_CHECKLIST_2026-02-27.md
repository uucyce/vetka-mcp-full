# MARKER_156.S6_IMPLEMENTATION_ROADMAP_CHECKLIST

Дата: 2026-02-27  
Скоуп: S6 — SOLO voice identity + auto voice replies + local emotion layer + ENGRAM memory feedback
Статус: READY FOR IMPLEMENTATION

## Hotfix Addendum (2026-02-27, S6.4.1b)

Обнаруженные регрессии после S6.4.1 и план фикса:

1. `BUG-S6-VOICE-REPLY-ROUTING`
- Симптом: voice-reply мог уйти не в target reply-модель (`replyTo`) после длительного STT.
- Root cause: routing (`replyTo/model/source`) брался из live-state после async STT, а не snapshot на момент записи.
- Fix version: `S6.4.1b`.
- Fix: snapshot маршрута в `handleVoiceRecorded` + передача в `handleSend(routeSnapshot)`.

2. `BUG-S6-STT-TIMEOUT-33S`
- Симптом: длинные voice samples (~30s+) завершались `Voice transcription timeout`.
- Root cause: фиксированный клиентский timeout 45s + отсутствие server-side timeout-контроля и явного timeout error.
- Fix version: `S6.4.1b`.
- Fix: adaptive timeout на клиенте (по duration), `timeout_ms` в socket payload, server clamp+`asyncio.wait_for`+явный `voice_error`.

3. `BUG-S6-VOICE-CONTEXT-PARITY`
- Симптом: ощущение, что voice-путь теряет контекст text pipeline (pins/viewport/chat routing).
- Root cause: следствие `BUG-S6-VOICE-REPLY-ROUTING`; после потери target route модель могла быть не той.
- Fix version: `S6.4.1b`.
- Fix: voice send использует тот же `handleSend` path, но с зафиксированным route snapshot.

### Regression Tests Added
- `tests/test_phase156_voice_s6.py::test_voice_audio_timeout_propagates_request_id`
- `tests/test_phase156_voice_s6.py::test_voice_audio_no_audio_keeps_request_id`

## Hotfix Addendum (2026-02-27, S6.4.1c)

1. `FIX-S6-QWEN-SPEAKER-NORMALIZATION`
- Симптом: в ряде сценариев `/api/voice/tts/synthesize` падал 500 с пустым detail.
- Fix: единый catalog нормализации voice_id (`src/voice/qwen_voice_catalog.py`) для routes/realtime/solo handler.
- Результат: legacy/нестабильные speaker id приводятся к валидному Qwen voice id детерминированно.

2. `FIX-S6-QWEN-SYNTH-BURST-SERIALIZATION`
- Симптом: burst из нескольких одновременных synth-запросов мог ломать локальный Qwen и давать серию 500.
- Fix: async lock в `/api/voice/tts/synthesize` + lock в solo post-pipeline synth.
- Результат: запросы к локальной Qwen генерации сериализуются, снижается частота burst-failure.

3. `FIX-S6-QWEN-ERROR-OBSERVABILITY`
- Симптом: пустая ошибка в UI/логах (`qwen synth/store failed` без причины).
- Fix: расширенный detail и structured logging в synth route (status/speaker/short upstream body).
- Результат: диагностируемая причина без гаданий по “тихим 500”.

### Regression Tests Added (S6.4.1c)
- `tests/test_phase156_voice_s6.py::test_qwen_tts_synthesize_route_normalizes_legacy_speaker`

## Hotfix Addendum (2026-02-27, S6.4.1d)

1. `BUG-S6-AUDIO-CONTAINER-MISMATCH`
- Симптом: voice bubble есть, но playback падает (`Qwen audio playback failed`).
- Root cause: часть Qwen ответов приходила как raw PCM16, но сохранялась как `.wav` без RIFF-заголовка.
- Fix: normalize payload перед storage (`normalize_qwen_audio_payload`) с auto-wrap raw PCM -> valid WAV.
- Touchpoints:
  - `src/api/routes/voice_storage_routes.py`
  - `src/api/handlers/user_message_handler.py`

2. `UX-S6-VOICE-LOCK-BADGE-REMOVED`
- Симптом: визуально мешающий зелёный badge `voice lock`.
- Fix: удалён из header чата.
- Touchpoint:
  - `client/src/components/chat/ChatPanel.tsx`

### Regression Tests Added (S6.4.1d)
- `tests/test_phase156_voice_s6.py::test_normalize_qwen_audio_payload_wraps_raw_pcm`
- `tests/test_phase156_voice_s6.py::test_qwen_tts_synthesize_route_converts_raw_pcm_to_wav`

## Hotfix Addendum (2026-02-27, S6.4.1e) — Runtime Recon

Источники:
- `MARKER_156_S6_RUNTIME_RECON_VOICE_CHAT_FAILURE_2026-02-27.md`

1. `CONFIRM-S6-QWEN-4BIT-ACTIVE`
- Проверено runtime health:
  - `profile=4bit`
  - `model=mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-4bit`

2. `GAP-S6-LATENCY-SLA-NOT-MET`
- Текущий UX не соответствует требованию “assistant voice через 3-5 секунд”.
- Фиксируем SLA:
  - `voice_first_audio_p95 <= 5000ms`
  - degraded budget <= 8000ms с явным прогресс-статусом.

3. `GAP-S6-POST-STREAM-BLOCKING`
- Root cause class: voice synth запускается после полного text stream и может блокировать завершение цикла.
- План: вынести TTS generation в background path с немедленным UI статусом.

4. `GAP-S6-NO-CHUNKED-AUDIO-DELIVERY`
- Сейчас отправляется только финальный audio blob/storage; нет early audio.
- План: исследовать и внедрить “first phrase preview audio” + follow-up full audio.

5. `RISK-S6-PORT-5003-COLLISION`
- В кодовой базе `5003` фигурирует не только в TTS (MCP/proxy references).
- План: ввести выделенный `QWEN_TTS_PORT` + startup assertion “owner=voice_tts_server”.

### New Runtime Checks Added To Matrix
- [ ] E2E тайминг T0..T6 для solo voice (20 прогонов, p50/p95).
- [ ] Проверка порта TTS owner на старте backend.
- [ ] Проверка first-play SLA (`<=5s`) в dev smoke.
- [ ] Проверка “нет вечной генерации”: hard timeout + явный `voice_error_code`.

## Hotfix Addendum (2026-02-27, S6.4.1f) — Runtime Latency Path

1. `FIX-S6-ASYNC-POST-TTS`
- Что сделано: post-pipeline TTS больше не блокирует основной `user_message` flow.
- Реализация: `_emit_solo_voice_message` переведён в background task (`asyncio.create_task`) после `stream_end`.
- Эффект: текст ответа доходит сразу, voice bubble догружается отдельно.

2. `TRACE-S6-T0-T5-MARKERS`
- Добавлены runtime-маркеры:
  - `T0_USER_SEND`
  - `T1_LLM_STREAM_END`
  - `T2_TTS_START`
  - `T4_STORAGE_DONE`
  - `T5_UI_BUBBLE_EMIT`
- Цель: измерить реальные сегменты латентности и убрать “чёрный ящик”.

3. `TUNE-S6-VOICE-TOKEN-BUDGET`
- Ужесточён voice response budget для ускорения TTS:
  - short input: до ~90 tokens
  - longer input: до ~140 tokens

4. `CONFIRM-S6-QWEN-4BIT-RUNTIME`
- Зафиксировано health-check'ом:
  - `profile=4bit`
  - `model=mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-4bit`

## S6.4.2 Queue (next fixes)

1. `FIX-S6-QWEN-STRICT-PLAYBACK`
- Убрать browser/Edge fallback для voice bubble и text read-aloud.
- Единый путь: `/api/voice/tts/synthesize` -> local Qwen 4bit -> audio playback.
- Если Qwen недоступен: явная ошибка в bubble (без подмены на browser voice).

2. `FIX-S6-TTS-AUTOSTART`
- При запросе синтеза поднимать локальный TTS-сервер автоматически.
- Использовать health check + bounded startup wait.

3. `FIX-S6-WAVEFORM-REAL`
- Отказ от fake waveform fallback в UI.
- Генерация waveform из реальных PCM данных (WAV decode) на backend.

4. `RESEARCH-S6-TAURI-VOICE-UI`
- Исследовать библиотеку/паттерн для:
  - icon-only voice controls (white icon style),
  - realtime waveform recorder visualization в Tauri/WebView.
- Результат: shortlist 2-3 вариантов + latency/CPU tradeoffs + integration plan.

5. `BUG-S6-QWEN-SYNTH-TEXT-ONLY`
- Симптом: после voice input модель отвечает текстом, но `chat_voice_message` не приходит.
- Лог: `[SOLO_VOICE_S6_2] qwen synth/store failed`.
- Root cause hypothesis: холодный старт Qwen TTS + timeout/одноразовая попытка.
- Fix: увеличить startup window, retry synth, явный error telemetry в UI metadata.

6. `BUG-S6-VOICE-ASSIGNMENT-FILE-WATCHER-NOISE`
- Симптом: в логах `Watcher deleted data/agent_voice_assignments.json` + `node_removed`.
- Риск: визуально выглядит как потеря реестра voice identity.
- Root cause hypothesis: atomic/triple-write rename sequence даёт ложный delete event.
- Fix: watcher should classify atomic replace as update, not remove, for assignment registry path.

7. `BUG-S6-VOICE-POLICY-NO-AUDIO-BUBBLE`
- Симптом: voice mode активен, но при TTS fail нет assistant voice bubble fallback-contract.
- Fix: в metadata ответа писать `voice_error_code` + показывать badge "Qwen TTS failed", чтобы пользователь видел причину.

### New Test Cases To Add
- [ ] `voice_input -> stream_end -> chat_voice_message` (happy path, provider=polza/grok).
- [ ] cold-start TTS: first request may take >45s, second request should pass.
- [ ] watcher atomic replace on `agent_voice_assignments.json` emits update, not remove.
- [ ] live waveform during recording correlates with microphone amplitude (non-flat bars).

## Цель S6
Сделать для solo-чата production-контур:
- voice input -> text generation (selected model/provider) -> Qwen TTS voice output,
- детерминированный `provider:model_id -> voice_id` (9 голосов),
- эмоциональная окраска локально (без токенов LLM),
- ENGRAM feedback loop для устойчивого поведения/тона.

---

## Feature Flags (обязательно)
1. `VOICE_S6_SOLO_AUTOREPLY_ENABLED` (default: off)
2. `VOICE_S6_ASSIGNMENT_V2_ENABLED` (default: off)
3. `VOICE_S6_EMOTION_LOCAL_ENABLED` (default: off)
4. `VOICE_S6_ENGRAM_FEEDBACK_ENABLED` (default: off)
5. `VOICE_S6_STRICT_PROVIDER_LOCK` (default: on)

Rollback: любой флаг -> `off` возвращает на текстовый baseline без ломки storage/history.

---

## Этапы внедрения

## Phase S6.1 — Solo Voice Reply Contract
**Задача:** ввести финальный контракт голосового ответа для solo.

### Impl
- Добавить socket event `chat_voice_message` (или эквивалент) с payload:
  - `id`, `chat_id`, `role='assistant'`, `content`,
  - `message_type='voice'`,
  - `metadata.audio{storage_id,format,duration_ms,waveform}`,
  - `metadata.voice{voice_id,tts_provider,model_identity_key,persona_tag}`,
  - `metadata.model{model,model_source,model_provider}`.
- Не ломать `chat_response`; оставить как fallback/text path.

### Checklist
- [ ] Event schema зафиксирован в TS + Python.
- [ ] `chat_response` не дублирует голосовой bubble.
- [ ] Ошибки TTS не валят text response.

### DoD
- При voice input в solo ассистент приходит как `type='voice'` bubble с playable audio.

---

## Phase S6.2 — Deterministic Voice Assignment V2
**Задача:** стабильный `provider:model_id -> voice_id` (pool из 9 Qwen голосов).

### Impl
- Расширить `voice_assignment_registry`:
  - поля: `assigned_at`, `last_used_at`, `usage_count`, `status`.
  - глобальный маркер `last_free_voice_cursor`.
- Политика выдачи:
  - сначала `free`, затем `least-used`, затем `LRU` среди `active` (по конфигу).
- Всегда использовать `model_identity_key = f"{provider}:{model_id}"`.

### Checklist
- [ ] Межчатовая стабильность подтверждена.
- [ ] Нет коллизий при параллельных assign (lock/atomic write).
- [ ] Видно, какой моделью занят голос.

### DoD
- Одна и та же модель в разных чатах получает одинаковый `voice_id`.

---

## Phase S6.3 — Solo Post-Pipeline TTS Bridge
**Задача:** после текстового ответа модели обязательно генерировать Qwen TTS (при voice mode).

### Impl
- В `user_message_handler` после финального текста (stream end) запускать TTS bridge:
  - вход: `assistant_text`, `model`, `model_source`, `chat_id`.
  - resolve voice assignment.
  - synthesize в Qwen TTS.
  - сохранить audio в `voice_storage` -> `storage_id`.
  - эмитить `chat_voice_message`.
- Provider routing LLM не менять (strict lock).

### Checklist
- [ ] Нет подмены модели/провайдера.
- [ ] При TTS fail текст всё равно доставляется.
- [ ] latency overhead контролируемый (метрики ниже).

### DoD
- Solo voice режим всегда отвечает голосом (если TTS доступен), иначе корректный text fallback.

---

## Phase S6.4 — Local Emotion/Prosody Layer (No Tokens)
**Задача:** локально вычислять эмо-контекст и маппить в параметры TTS.

### Impl
- Добавить `emotion_controller` (локальный, rule-based + light semantic scoring):
  - вход: user_text, assistant_text, dialog_state.
  - выход: `emotion_snapshot`:
    - `sentiment[-1..1]`, `arousal[0..1]`, `urgency[0..1]`, `confidence[0..1]`, `politeness[0..1]`.
- Маппинг в prosody:
  - `speed`, `pitch`, `pause_profile`, `energy`.
- Smoothing:
  - clamp delta между соседними репликами,
  - анти-overacting лимиты.

### Checklist
- [ ] Нет резких скачков тона между соседними ответами.
- [ ] Профиль эмоции не требует LLM токенов.
- [ ] Значения логируются для аудита.

### DoD
- Голос звучит вариативно, но стабильно и без «переигрывания».

---

## Phase S6.5 — ENGRAM Feedback Loop
**Задача:** адаптировать стиль/тон через память агента и обратную связь.

### Impl
- ENGRAM state per model identity:
  - stable formality,
  - style bias,
  - rolling emotional baseline,
  - last feedback outcomes.
- Источники feedback:
  - implicit (перебивание, повтор, replay skip, response correction),
  - explicit (user reaction / thumbs).
- Коррекция только control-plane (prosody/style knobs), без смены model routing.

### Checklist
- [ ] ENGRAM не увеличивает prompt tokens в базовом контуре.
- [ ] State обновляется атомарно и изолированно per identity.
- [ ] Можно выключить флагом без потери core voice flow.

### DoD
- Через несколько реплик голос/тон стабилизируется под стиль диалога.

---

## Phase S6.6 — Observability + Guardrails
**Задача:** измеримость и безопасность контура.

### Metrics
- `voice_identity_stability_rate` (target >= 99.5%)
- `voice_reply_latency_ms_p50/p95`
- `tts_failure_rate`
- `voice_model_mismatch_rate` (target ~0)
- `emotion_jitter_score` (межрепликовый drift)

### Guardrails
- При любой ошибке: text response не теряется.
- При missing storage: bubble остается, UI показывает playback error без краша.
- При provider key fail: no cross-provider fallback.

### Checklist
- [ ] Метрики в логах/дашборде.
- [ ] Трассировка `chat_id + model_identity_key + voice_id` в каждом voice reply.
- [ ] Алерт на mismatch > порога.

### DoD
- Инциденты диагностируются по логам за 1-2 минуты.

---

## Test Matrix

### Functional
- [ ] Solo: voice input -> assistant voice reply.
- [ ] Solo reload: replay user+assistant voice сообщений работает.
- [ ] Same model across chats -> same voice_id.
- [ ] Different models -> распределение по пулу 9 голосов.

### Routing/Provider
- [ ] `model_source=polza` не уходит в openrouter/xai fallback.
- [ ] `grok-*` direct vs `x-ai/...` via aggregator маршрутизируются корректно.

### Failure
- [ ] TTS недоступен -> text fallback, no crash.
- [ ] Storage 404 -> graceful playback error.
- [ ] STT пустой -> корректный UX без зависания кнопок.

### Performance
- [ ] p95 latency voice reply в допустимом бюджете.
- [ ] Нет деградации UI responsiveness при записи/stop/send.

---

## Dependencies / Owners
1. Backend socket+pipeline (S6.1/S6.3) — API handlers.
2. Voice registry (S6.2) — `src/voice/voice_assignment_registry.py`.
3. Emotion controller (S6.4) — новый модуль `src/voice/emotion_controller.py`.
4. ENGRAM feedback (S6.5) — ENGRAM/storage интеграция.
5. Frontend contract/hydration — `useSocket`, `ChatPanel`, `MessageBubble`.

---

## Release Plan
1. Canary с `VOICE_S6_SOLO_AUTOREPLY_ENABLED=on` только для dev профиля.
2. Включить assignment v2.
3. Включить emotion layer (10%/50%/100%).
4. Включить ENGRAM feedback последним.
5. Freeze + regression audit по чек-листу.

---

## Final Go/No-Go
Release S6 возможен, если одновременно выполнено:
- [ ] Voice identity stability >= 99.5%
- [ ] mismatch rate == 0 (или < agreed threshold)
- [ ] нет блокирующих regression в text pipeline
- [ ] rollback флаги проверены в боевом окружении

## Hotfix Addendum (2026-02-27, S6.4.2b) — Progressive Voice UX + Mode Hygiene

Источники:
- `MARKER_156_S6_RUNTIME_RECON_PROGRESSIVE_VOICE_PIPELINE_2026-02-27.md`
- `MARKER_156_S6_RESEARCH_REQUEST_PROGRESSIVE_VOICE_PIPELINE_2026-02-27.md`

1. `GAP-S6-SOLO-FINAL-ONLY-VOICE-EVENT`
- Сейчас solo voice приходит только финальным `chat_voice_message`.
- Нет `chat_voice_stream_*` для раннего воспроизведения.

2. `GAP-S6-NO-PENDING-VOICE-BUBBLE`
- На `stream_start` создается только text placeholder.
- Нужен pending voice bubble со статусом "модель записывает голосовое".

3. `GAP-S6-NO-PROGRESSIVE-AUDIO-DELIVERY`
- `/tts/generate` и `/api/voice/tts/synthesize` возвращают готовый payload целиком.
- Нужна progressive догрузка и first-play до full completion.

4. `GAP-S6-TEXT-VOICE-MERGE-RACE`
- Текущий merge path (`stream_end` + поздний `chat_voice_message`) подвержен гонкам обновления одного `message_id`.
- Нужна deterministic merge policy через `generation_id + seq`.

5. `GAP-S6-MODE-HYGIENE-FSM-MISSING`
- Бизнес-правило: voice-mode ON только после `VOICE_SENT`, OFF на `TEXT_TYPED`.
- Сейчас логика размазана по `ChatPanel`/`MessageInput`, нет единой FSM.

### New S6.4.3 Work Items
- [ ] `S6.4.3a` SOLO `chat_voice_stream_start/chunk/end` contract.
- [ ] `S6.4.3b` Pending voice bubble + status states.
- [ ] `S6.4.3c` Progressive audio buffer/playback in `MessageBubble`.
- [ ] `S6.4.3d` Deterministic merge policy for text/voice updates.
- [ ] `S6.4.3e` Centralized mode hygiene FSM (`VOICE_SENT`, `TEXT_TYPED`).


## Hotfix Addendum (2026-02-27, S6.4.2c) — Review of Research Response

Источники:
- `MARKER_156_S6_RESEARCH_REVIEW_PROGRESSIVE_VOICE_PIPELINE_2026-02-27.md`
- `MARKER_156_S6_RESEARCH_REQUEST_PROGRESSIVE_VOICE_PIPELINE_V2_2026-02-27.md`

1. `REVIEW-S6-PARTIAL-ACCEPT`
- Первый research-ответ принят частично как архитектурный draft.
- Full implementation откладывается до precision-pass V2.

2. `GAP-S6-TRUE-STREAM-UNPROVEN`
- Не подтвержден true incremental stream из текущего Qwen/MLX стека.
- Нужен точный ответ по API feasibility.

3. `GAP-S6-PROTOCOL-BACKPRESSURE`
- Требуется формальный протокол ack/retry/reorder для chunk delivery.

4. `GAP-S6-FORMAT-DECISION`
- Нужен единый production формат аудио под Tauri/WebView.

5. `LOCK-S6-HYGIENE-RULE`
- Блокирующее бизнес-правило:
  - ON только `VOICE_SENT`;
  - OFF по `TEXT_TYPED`;
  - no auto-ON on `TEXT_CLEARED`.

