# MARKER_156.RECON_TTS_AGENT_VOICE_CHAT
# Phase 156 Recon: TTS, Agent Voice, Voice Models in VETKA Chat

Date: 2026-02-26
Workspace: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03`

## 1. Scope
Recon по документации + кодовой базе с фокусом на:
- что уже есть по TTS/STT/voice;
- как это связано с агентами;
- как голосовые модели участвуют в чате;
- что нужно для режима "агенты отвечают голосовыми сообщениями как в мессенджерах".

## 2. Что уже есть (код, подтверждено)

### 2.1 Backend voice pipeline (generic realtime)
- Активный realtime voice state machine: `voice_stream_start -> voice_pcm -> voice_utterance_end -> STT -> LLM stream -> TTS chunks`.
- Файл: `src/api/handlers/voice_router.py` (Phase 60.5.1).
- Файл: `src/api/handlers/voice_socket_handler.py` (legacy + realtime events).
- Провайдеры realtime: `src/api/handlers/voice_realtime_providers.py`.

Что делает:
- STT: fallback chain (`gemini/openai/deepgram/whisper local`).
- LLM streaming: XAI/OpenRouter.
- TTS: ElevenLabs -> Piper -> browser fallback.
- Поддерживает interrupt (перебивание) во время ответа.

### 2.2 Jarvis voice pipeline (отдельный контур)
- Отдельные socket events `jarvis_*` + свой lifecycle.
- Файл: `src/api/handlers/jarvis_handler.py`.
- Frontend hook: `client/src/hooks/useJarvis.ts`.

Что делает:
- принимает PCM chunks от микрофона;
- строит ответ (LLM);
- синтезирует аудио (`FastTTS` edge или `Qwen3TTSClient`);
- отдает `jarvis_audio` (base64 + format).

### 2.3 TTS microservice и автозапуск
- В `main.py` есть автозапуск TTS сервера на старте (Phase 104).
- Менеджер процесса: `src/voice/tts_server_manager.py`.
- Скрипт сервиса: `scripts/voice_tts_server.py`.
- По API ожидается `http://127.0.0.1:5003/health` и `/tts/generate`.

### 2.4 Voice model discovery для UI
- `/api/models/autodetect` детектит voice capability и состояние local qwen_tts.
- Файл: `src/api/routes/model_routes.py` (MARKER_138.S2_5_MODEL_AUTODETECT).
- Реестр моделей содержит `ModelType.VOICE`: `src/services/model_registry.py`.

### 2.5 Frontend chat voice UX (ввод)
- ChatPanel грузит voice-модели и передает в MessageInput.
- MessageInput включает mic/realtime mode если выбран/упомянут voice model.
- Файлы:
  - `client/src/components/chat/ChatPanel.tsx`
  - `client/src/components/chat/MessageInput.tsx`
  - `client/src/hooks/useRealtimeVoice.ts`

Итог: в чате уже есть голосовой ввод + realtime цикл, но это не равно голосовым сообщениям агентов в истории чата.

### 2.6 MessageBubble TTS (локальный read-aloud)
- `MessageBubble.tsx` использует `useTTS` (Web Speech API) чтобы озвучить текст пузыря.
- Это клиентский read-aloud текста, не сохраненное голосовое сообщение от агента.

## 3. Что в документации (план/намерение)

### 3.1 Стратегический план
- `docs/VETKA_STRATEGIC_PLAN_2026.md`:
  - S2.3: streaming TTS pipeline;
  - S2.4: voice mode in unified search;
  - S2.6: persistent agent voice IDs + voice messages in chat.
- В документе есть целевая модель: agent voice identity + waveform bubbles.

### 3.2 Фаза 104
- `docs/104_ph/PHASE_104_JARVIS_VOICE.md`: Jarvis как отдельный voice interface над чатом.
- Архитектура и socket-контракты описаны, часть уже реализована в коде.

## 4. Runtime snapshot (в этом окружении)
- `5001` backend слушает.
- `5003` TTS microservice сейчас НЕ слушает.
- `/api/models/autodetect` возвращает `qwen_tts.running=false`.
- Категории из autodetect: `voice=16` (в основном облачные voice-capable модели + registry).

Вывод: voice stack в целом активен, но локальный Qwen TTS сейчас не поднят.

## 5. Как это сейчас работает с агентами

### 5.1 Group/Solo агентные ответы
- Агентные ответы в group flow эмитятся как текст (`group_stream_end.full_message`) и сохраняются как текстовые assistant messages.
- Файл: `src/api/handlers/group_message_handler.py`.
- Структура сообщения в фронте (`ChatMessage`) не содержит audio payload/voice metadata.
- Файл: `client/src/types/chat.ts`.

### 5.2 Jarvis
- Jarvis может отдать аудио (`jarvis_audio`) и проигрываться в клиенте.
- Но это отдельный voice-интерфейс; не universal audio output для всех чат-агентов PM/Dev/QA/Architect.

## 6. Как это сейчас работает с voice models в чате
- Voice models используются для переключения режима ввода/микрофона в MessageInput.
- Ответы при этом не материализуются в persisted voice messages в chat timeline.
- Текущий UX ближе к "voice interaction mode", а не к "голосовые сообщения агентов как Telegram/WhatsApp".

## 7. Главные разрывы до целевой фичи

1. Нет chat message type для voice.
2. Нет backend-шага "сгенерировать аудио для каждого агентного ответа" в group/solo pipelines.
3. Нет persist-слоя для audio artifacts (путь/длительность/waveform hash).
4. Нет agent->voice mapping в runtime (в коде), только в strategy doc.
5. Нет единого playback UX в MessageList/MessageBubble как у voice messages.
6. Нет SLA-режимов latency (fast first audio / quality full audio) для agent chat.

## 8. Важные техриски

1. Формат аудио: `scripts/voice_tts_server.py` возвращает base64 raw PCM bytes, но помечает `format="wav"`.
2. Расхождение путей TTS:
   - realtime voice router использует `voice_realtime_providers` (ElevenLabs/Piper/browser),
   - Jarvis quality mode использует Qwen3TTSClient,
   - group agent pipeline TTS не использует вообще.
3. При отсутствии 5003 (qwen_tts down) поведение должно оставаться graceful и предсказуемым.

## 9. Предложение для Phase 156 (цель пользователя)

### MARKER_156.S1_DATA_CONTRACT
- Расширить `ChatMessage`:
  - `type: 'voice'`;
  - `metadata.audio = {format, duration_ms, waveform[], tts_provider, voice_id, path_or_id}`;
  - `metadata.source_text`.

### MARKER_156.S2_AGENT_VOICE_PROFILE
- Ввести `data/agent_voice_config.json` (runtime reading + defaults):
  - `PM/Dev/QA/Architect/Hostess/Jarvis -> voice_id, provider, speed, language`.

### MARKER_156.S3_TTS_POSTPROCESS_AGENT_REPLY
- После генерации agent text в solo/group:
  - if `voice_response_mode=true` для чата/сессии,
  - синтезировать audio через unified TTS service,
  - эмитить `group_voice_message` (или унифицированный message event),
  - сохранять как voice message в history.

### MARKER_156.S4_CHAT_UI_VOICE_BUBBLE
- В `MessageBubble/MessageList` добавить voice bubble:
  - waveform, duration, play/pause, playback progress;
  - autoplay опционально при `voice conversation mode`.

### MARKER_156.S5_MODE_SWITCH
- Явный переключатель в ChatPanel:
  - `Text replies` | `Voice replies` | `Auto (voice input => voice output)`.

### MARKER_156.S6_LOCAL_FIRST_LATENCY
- Двухконтурная стратегия:
  - fast mode (edge/browser/local lightweight) для first chunk;
  - optional quality finalize (qwen3/premium) если доступно.
- Цели:
  - first audio < 1.5-2.5s;
  - fallback без silent failures.

## 10. Минимальный MVP (практичный порядок)
1. `S1_DATA_CONTRACT`
2. `S2_AGENT_VOICE_PROFILE`
3. `S3_TTS_POSTPROCESS_AGENT_REPLY` (без waveform, просто playable audio)
4. `S4_CHAT_UI_VOICE_BUBBLE` (basic player)
5. `S5_MODE_SWITCH`

## 11. Acceptance criteria для фичи
- При включенном voice mode ответы PM/Dev/QA/Architect появляются как voice bubbles в чате.
- После перезагрузки история содержит playable voice messages.
- При недоступном TTS провайдере: fallback + системное уведомление, без зависания ответа.
- На локальной машине UX остается плавным: нет длинной "мертвой паузы" после user input.

