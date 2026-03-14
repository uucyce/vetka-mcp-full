# MARKER_156.S6_RUNTIME_RECON_PROGRESSIVE_VOICE_PIPELINE

Дата: 2026-02-27
Скоуп: SOLO voice-first UX (voice input -> assistant voice output)

## Требуемый сценарий (target)
1. Пользователь отправляет voice message.
2. В чате сразу появляется статус ассистента: "записывает голосовое" (не просто generic thinking).
3. Ассистентский voice bubble создается сразу в pending-состоянии.
4. Аудио докидывается чанками (как progressive download), play доступен до полной догрузки.
5. Транскрипт ассистента показывается после готовности/первого playable аудио (чтобы убрать re-render race).
6. Voice mode hygiene:
- включается только после отправки voice-сообщения;
- выключается на первом текстовом вводе пользователя.

## Что есть в коде сейчас (confirmed)

### C1. Текущий SOLO assistant voice event финальный, не потоковый
- Backend эмитит только финальный `chat_voice_message` после полного synth+storage:
  - `src/api/handlers/user_message_handler.py` (emit `chat_voice_message`).
- Frontend принимает `chat_voice_message` и постфактум конвертирует placeholder в `type='voice'`:
  - `client/src/hooks/useSocket.ts`.

Маркер: `MARKER_156.RECON.C1_FINAL_ONLY_SOLO_EVENT`

### C2. Текстовый stream создаёт text-placeholder заранее
- На `stream_start` всегда создается `type='text'` сообщение, затем `stream_token`, `stream_end`:
  - `client/src/hooks/useSocket.ts`.

Маркер: `MARKER_156.RECON.C2_TEXT_PLACEHOLDER_FIRST`

### C3. Нет solo audio chunk events в сокет-контракте
- В типах сокета есть chunk events для group (`group_voice_stream_chunk`),
  но в backend нет emit этих group chunk событий, и для solo аналогов нет.
- В `user_message_handler.py` найден только `chat_voice_message` (final).

Маркер: `MARKER_156.RECON.C3_NO_SOLO_AUDIO_CHUNK_EVENTS`

### C4. TTS endpoint возвращает только готовый аудио payload
- `POST /api/voice/tts/synthesize` вызывает `5003/tts/generate`, ждёт полный ответ,
  потом сохраняет и возвращает `audio_b64 + storage_id + url`.
- Потокового ответа/чанков нет.
  - `src/api/routes/voice_storage_routes.py`
  - `scripts/voice_tts_server.py`

Маркер: `MARKER_156.RECON.C4_TTS_FULL_PAYLOAD_ONLY`

### C5. Playback storage уже поддерживает partial content на уровне HTTP
- Route `GET /api/voice/storage/{id}` отдает `FileResponse`; в runtime-логах наблюдается `206 Partial Content`.
- Это помогает только после появления файла целиком, но не решает live generation chunking.

Маркер: `MARKER_156.RECON.C5_STORAGE_RANGE_OK_BUT_POSTFACTUM`

### C6. Hygiene режима частично реализована, но не строго по бизнес-правилу
- В `MessageInput.tsx` есть `useEffect`: если `hasText`, то `onVoiceOnlyModeChange(false)`.
- Но в `ChatPanel.tsx` voice mode включается автоматически после успешного voice roundtrip:
  - `setVoiceOnlyMode(true); setRealtimeVoiceEnabled(true);`
- Нет явного единого state-machine с событиями `VOICE_SENT`, `TEXT_TYPED`.

Маркер: `MARKER_156.RECON.C6_MODE_HYGIENE_PARTIAL`

## Ключевые гэпы относительно target

1. `GAP-PV-1` Нет pending voice bubble ассистента сразу после `stream_start`.
2. `GAP-PV-2` Нет progressive socket delivery аудио чанков для solo.
3. `GAP-PV-3` Нет backend pipeline "first playable chunk <= 3-5s".
4. `GAP-PV-4` Нет контракта "текст ассистента показывать после first-playable audio".
5. `GAP-PV-5` Voice mode hygiene разбросана по нескольким хукам, нет централизованной FSM.

## Вероятная причина наблюдаемого "долго и странно"
- Система сейчас архитектурно ждёт полный LLM text + полный TTS synth,
  и только потом эмитит финальный voice bubble.
- Любая задержка в LLM/TTS превращается в долгий "ничего не происходит".
- Редкие дубли/гонки проявляются как multiple generation/play attempts в одном bubble.

Маркер: `MARKER_156.RECON.HYPOTHESIS.POSTFACTUM_AUDIO_PIPELINE`

## Что нужно проектно (без имплементации в этом документе)
1. Новый SOLO сокет-контракт:
- `chat_voice_stream_start`
- `chat_voice_stream_chunk`
- `chat_voice_stream_end`
2. Pending assistant bubble типа `voice_pending` на `stream_start`.
3. Progressive аудио буфер на фронте (MSE/SourceBuffer или append Blob strategy).
4. Разделить текст и аудио таймлайн отображения (text-after-audio policy).
5. Centralized voice-mode FSM:
- Events: `VOICE_SENT`, `TEXT_TYPED`, `TEXT_SENT`, `VOICE_REPLY_DONE`, `VOICE_REPLY_FAIL`.

