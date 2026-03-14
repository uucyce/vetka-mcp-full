# MARKER_156.S6_RESEARCH_REQUEST_ENGRAM_VOICE_EMOTION

Дата: 2026-02-27  
Статус: REQUEST PREPARED + CODEBASE REALITY CHECK

## RESEARCH REQUEST: VETKA SOLO VOICE IDENTITY + EMOTION LAYER + AGENT MEMORY (ENGRAM)

### Контекст (текущее состояние)
- В solo voice уже есть запись/отправка пользовательского voice sample, STT и voice bubble.
- Авто-voice-ответ модели пока не включается как обязательный post-pipeline шаг.
- Нужна стабильная привязка голоса к identity модели (`model_id + provider`).
- Нужен локальный (без токенов LLM) механизм эмоциональной окраски TTS.
- Нужен аудит: можно ли завязать это на ENGRAM как слой памяти/поведения агента с обратной связью.

### Цель исследования
Спроектировать production-механику:
1. deterministic voice assignment для всех моделей,
2. локальный emotion/prosody controller для Qwen TTS (без роста token cost),
3. ENGRAM-driven память агента (индивидуальная + контекстная) для устойчивого стиля/поведения.

### Обязательные требования

#### 1) Voice ID mapping
- Ключ: `provider:model_id` (например `openrouter:upstage/solar-pro-3:free`).
- При первом появлении: выдача одного из 9 Qwen voice IDs.
- Межчатовая стабильность: та же модель в любом чате получает тот же voice_id.
- Реестр должен хранить:
  - `model_identity_key`
  - `voice_id`
  - `assigned_at`
  - `last_used_at`
  - `usage_count`
  - `status` (`active|free|archived`)
- Нужен маркер «последний свободный голос» и политика распределения (LRU/least-used/role-aware).

#### 2) Voice reply pipeline
- После voice input в solo: стандартный текстовый pipeline модели -> Qwen TTS -> голосовой ответ.
- Без подмены модели/провайдера.
- В metadata ответа фиксировать:
  - `voice.voice_id`
  - `voice.model_identity_key`
  - `voice.tts_provider=qwen`
  - `audio.storage_id|format|duration_ms|waveform`

#### 3) Emotion layer (без токенов)
- Локальная оценка эмоционального контекста на входе/выходе (sentiment, arousal, urgency, confidence, politeness).
- Маппинг эмоций в prosody-параметры Qwen TTS:
  - speed, pitch, pause profile, energy/intensity.
- Запрет на «переигрывание»: лимиты амплитуды изменений, smoothing между репликами.

#### 4) ENGRAM integration
- Индивидуальная память агента:
  - стиль ответа,
  - устойчивый уровень формальности,
  - предыдущее эмоциональное состояние диалога.
- Контур обратной связи:
  - оценка релевантности/естественности voice-ответа,
  - корректировка будущих prosody-параметров без изменения model routing.
- Никаких обязательных дополнительных токенов в prompt для базового цикла.

### Что выдать на выходе
1. Архитектурная схема (components + data flow + failure modes).
2. Контракт данных (JSON schema) для:
  - voice assignment registry
  - emotion state snapshot
  - response voice metadata
3. Политика выбора голоса (алгоритм + edge cases).
4. Алгоритм emotion inference (локально) и таблица mapping в prosody.
5. План внедрения по этапам (S6/S7/...) с rollback-стратегией.
6. Метрики качества:
  - стабильность voice identity
  - latency overhead
  - MOS-like субъективная оценка естественности
  - частота mismatch «модель ↔ голос»
7. Риски и защита:
  - коллизии voice_id,
  - деградация при пустой/шумной семантике,
  - конфликт между role-voice и model-voice.

---

## Reality Check (сверка с актуальной кодовой базой)

### Что уже есть
- Solo voice storage/replay контракт и backend endpoints:
  - `POST /api/voice/storage`
  - `GET /api/voice/storage/{storage_id}`
  - `src/api/routes/voice_storage_routes.py`
- Сохранение `message_type` + `metadata` в chat history и возврат через `GET /api/chats/{id}`.
- Hydration в `ChatPanel` для `voice`-типов после reload.
- Базовый voice assignment registry уже присутствует:
  - `src/voice/voice_assignment_registry.py`
  - есть storage в `data/agent_voice_assignments.json` и role map.

### Что еще не реализовано (гепы к S6)
1. Auto voice response в SOLO как обязательный post-pipeline шаг (сейчас ответы приходят текстом через `chat_response`/stream).
2. Единый solo event-contract для голосового ответа модели (`type='voice'` + `metadata.audio/voice`), аналогичный group voice message.
3. Полный lifecycle менеджер 9 Qwen voice IDs с явным `last_free_voice_cursor` и статусами `active/free/archived`.
4. Локальный emotion/prosody controller (не зависящий от токенов LLM).
5. ENGRAM feedback loop для корректировки поведения/эмоций на уровне TTS control plane.

---

## Grok/provider sanity check (по коду)

### Проверено
- В `provider_registry`:
  - source-aware routing включен (`detect_provider(model, source=...)`),
  - запрещен автоматический fallback между провайдерами,
  - поддержка агрегаторов (`poe`, `polza`, etc.) через openai-compatible провайдер.
- В `user_message_handler`:
  - в direct/stream ветках явно зафиксировано `NO FALLBACK` при exhausted xAI keys.
- В realtime `voice_realtime_providers`:
  - LLM path strict mode; для raw `grok-*` без префикса используется xAI,
  - для provider/model формата используется выбранная модель/путь без подмены на локалку.

### Вывод
Критичных глюков уровня «подмена провайдера на случайный fallback» по текущим проверенным веткам не обнаружено.

---

## Рекомендованный старт S6
1. Сначала утвердить solo voice response event-contract (`chat_voice_message` или расширение `stream_end`).
2. Затем подключить deterministic assignment registry в solo path (provider:model -> voice_id).
3. Потом добавить локальный emotion layer (rule-based + smoothing), и только после — ENGRAM feedback adaptation.
