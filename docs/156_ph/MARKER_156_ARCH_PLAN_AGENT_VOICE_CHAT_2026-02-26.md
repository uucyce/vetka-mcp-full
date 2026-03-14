# MARKER_156.ARCH_PLAN_AGENT_VOICE_CHAT

Дата: 2026-02-26  
Фаза: 156 (research/architecture)

## 1) Цель
Сделать voice-first чат в VETKA (solo + team), где при включенном голосовом режиме:
- пользователь отправляет голосовые сообщения (waveform UX);
- агенты отвечают голосовыми сообщениями (как мессенджер), а не только текстом;
- у каждой модели есть свой устойчивый голос (разные характеры, без конфликтов в команде);
- поток ответа агента сразу идет в TTS (низкая задержка), затем фиксируется финальная голосовуха в истории.

## 2) Что уже есть (база для реализации)
- Group/agent стрим: `group_stream_start / group_stream_token / group_stream_end` с текстом.
  - `src/api/handlers/group_message_handler.py`
  - `client/src/hooks/useSocket.ts`
- Voice stack и fallback:
  - `src/voice/tts_engine.py` (`Qwen3TTSClient`, `TTSEngine`, fallback chain)
  - `src/voice/tts_server_manager.py` (локальный microservice на `5003`)
- Jarvis voice-поток существует отдельно (`jarvis_audio`), но не как universal output для всех агентных ответов.
  - `src/api/handlers/jarvis_handler.py`
- Тип сообщения в чате пока текстовый (`ChatMessage.type` не содержит `voice`).
  - `client/src/types/chat.ts`

## 3) Принцип активации voice режима
Единое правило:
- Если пользователь явно включил `Voice conversation mode` или отправил первое голосовое сообщение в сессии,
- то reply policy переключается в `voice_output = on` (для solo и group).

Состояния:
- `text_only`
- `voice_auto` (voice input => voice output)
- `voice_forced` (всегда голос)

Хранить в chat/session policy:
- `chat_preferences.voice_reply_mode`
- `chat_preferences.voice_autoplay`

## 4) Identity и lock голоса за моделью

### 4.1 Ключ идентичности модели
`model_identity_key = "{provider}:{model_id}"`

Примеры:
- `openai:gpt-4o-mini`
- `ollama:qwen2.5:14b`
- `xai:grok-4`

### 4.2 Реестр голосов
Новый runtime-store (позже в БД):
- `voice_assignments`:
  - `model_identity_key` (PK)
  - `voice_id`
  - `tts_provider` (`qwen3|edge|piper|browser`)
  - `persona_tag` (`calm|strict|energetic|analytical`)
  - `created_at`, `updated_at`

### 4.3 Lock semantics
При первом обращении к модели:
1. `lookup(model_identity_key)`
2. если нет записи -> `acquire_voice_lock(model_identity_key)` (CAS/atomic insert)
3. выбираем свободный `voice_id` из пула
4. сохраняем assignment
5. дальнейшие ответы модели используют только этот `voice_id`

Это убирает race condition при параллельной командной работе агентов.

## 5) Автовыбор голоса (первый вызов)

Алгоритм `AUTO_PICK_VOICE`:
1. Взять пул голосов по `tts_provider` и языку чата.
2. Исключить уже занятые голоса в текущей group-сессии (hard uniqueness per active team).
3. Если пул исчерпан: разрешить reuse с минимальной “acoustic distance” (последний fallback).
4. Детерминированный tie-break: `hash(model_identity_key) % len(candidates)`.
5. Записать assignment и `persona_tag`.

Результат:
- стабильный характер для каждой модели;
- в одной команде голоса максимально различимы.

## 6) Streaming path: агент -> TTS сразу

### 6.1 Новый оркестратор
`AgentVoiceOrchestrator` (backend service):
- получает токены/дельты ответа агента;
- режет на фразы (sentence boundary);
- сразу вызывает TTS по фразам;
- отдает аудио-чанки в socket для мгновенного playback;
- собирает финальный аудио-артефакт для истории.

### 6.2 События Socket.IO (новые)
- `group_voice_stream_start`
- `group_voice_stream_chunk`
- `group_voice_stream_end`
- `group_voice_message`

`group_voice_message` должен содержать final payload для таймлайна:
- `message_id`, `group_id`, `agent_id`
- `audio`: `{format, duration_ms, waveform, url_or_blob_id}`
- `voice`: `{voice_id, tts_provider, persona_tag}`
- `text_preview` (краткая текстовая подложка)

## 7) Новый формат chat message
Расширение `ChatMessage`:
- `type: 'text' | 'code' | 'plan' | 'compound' | 'voice'`
- `metadata.audio`:
  - `format`
  - `duration_ms`
  - `waveform: number[]`
  - `storage_id` / `url`
- `metadata.voice`:
  - `voice_id`
  - `tts_provider`
  - `model_identity_key`
  - `persona_tag`

UI:
- voice bubble (play/pause, progress, waveform, speed 1x/1.5x/2x)
- опциональный autoplay в `voice_auto`/`voice_forced`.

## 8) CAM + эмоции голоса

### 8.1 Реалистичный минимум (Phase 1)
Сначала сделать независимый слой:
- `emotion_hint` вычисляется из текста ответа + role/persona.
- mapping в TTS style params (`neutral`, `warm`, `confident`, `urgent`).

### 8.2 CAM-интеграция (Phase 2)
Через CAM event pipeline добавить enrichment:
- событие `voice_emotion_requested`
- CAM дает `context_emotion_hint` (напр. calm/tense/excited)
- оркестратор подмешивает это в TTS request.

Важно: текущий CAM в коде ориентирован на memory/activation, не на prosody API. Поэтому эмоции голоса надо вводить отдельным контрактом, а CAM использовать как дополнительный сигнал.

## 9) Qwen TTS эмоции: исследовательский статус
На текущем этапе в репозитории нет подтвержденного контракта Qwen TTS для явных emotion tokens/prosody controls.

Решение в архитектуре:
- абстракция `VoiceStyleParams` (vendor-agnostic)
- адаптер провайдера:
  - если Qwen поддерживает style-параметры -> передаем нативно
  - если нет -> делаем prompt-style preconditioning/пост-обработку
  - fallback -> neutral

## 10) Отказоустойчивость и деградация
Порядок провайдеров:
1. `qwen3` (локально, порт `5003`)
2. `edge`
3. `piper`
4. text fallback (если все упало)

Политика:
- если voice режим включен, но TTS недоступен -> показывать текст + badge `voice_failed`;
- не блокировать основной чат-пайплайн.

## 11) Пошаговый план внедрения

### MARKER_156.VOICE.S1_CONTRACTS
- Ввести `ChatMessage.type='voice'` и `metadata.audio/voice`.
- Ввести новые socket events для voice stream и final voice message.

### MARKER_156.VOICE.S2_VOICE_REGISTRY
- Реализовать `voice_assignments` (in-memory + persistence).
- Реализовать `model_identity_key` и atomic lock при первом назначении.

### MARKER_156.VOICE.S3_AGENT_TTS_STREAM
- Встроить `AgentVoiceOrchestrator` в group/solo ответный pipeline.
- Подключить sentence-chunked TTS выдачу в реальном времени.

### MARKER_156.VOICE.S4_CHAT_UI_WAVEFORM
- Voice bubble в `MessageBubble/MessageList`.
- Автовоспроизведение и ручные controls.

### MARKER_156.VOICE.S5_MODE_POLICY
- Переключатель режимов `text_only | voice_auto | voice_forced`.
- Auto-rule: первое голосовое сообщение пользователя включает `voice_auto`.

### MARKER_156.VOICE.S6_EMOTION_LAYER
- `VoiceStyleParams` + emotion mapper.
- CAM enrichment hook.

### MARKER_156.VOICE.S7_METRICS
- Метрики: `time_to_first_audio`, `voice_success_rate`, `fallback_rate`, `avg_duration_ms`.

## 12) Что проверить через Grok/интернет (точечно)
1. Поддерживает ли используемый Qwen TTS endpoint явные параметры эмоций/просодии (официальный API-контракт).
2. Поддерживает ли потоковую генерацию аудио chunk-by-chunk (не только full wav/base64).
3. Какие voice IDs/спикеры реально доступны и как стабильно закреплять их между перезапусками.
4. Лучший формат для мессенджерного UX в web/tauri: `opus/webm` vs `wav` для latency/размера.

## 13) Критерии готовности
- В group chat несколько агентов отвечают голосом, с разными устойчивыми голосами.
- После перезапуска приложения `provider:model_id -> voice_id` сохраняется.
- При первом voice input у пользователя ответы автоматически становятся voice messages.
- История чата содержит воспроизводимые waveform voice bubbles.
- При падении `5003` чат не ломается: работает fallback/degrade path.
