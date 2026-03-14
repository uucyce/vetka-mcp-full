# MARKER_156.S6_PROGRESSIVE_VOICE_ROADMAP

Дата: 2026-02-28  
Скоуп: S6 — SOLO progressive voice delivery и строгое управление voice mode  
Статус: актуализирован (все gaps закрыты, ждём ответ Grok V2 для final spec)

## 1. Что сделано (основано на коде)
- `client/src/hooks/useSocket.ts` теперь принимает `chat_voice_stream_start/chunk/end`, сортирует чанки по `seq`, дропает дубли по `checksum` и отсылает `chat_voice_stream_ack` для backpressure. Хранится стек `message_id:generation_id`, который обновляет `chatMessages` metadata в реальном времени. Маркер: `MARKER_156.S6.TECH.SOCKET_CONTRACT`.
- Centralized store `client/src/store/useVoiceModeStore.ts` управляет `voiceOnlyMode`/`realtimeVoiceEnabled`, сохраняет их в локальное хранилище и испускает события `voice_sent`/`text_typed`. `ChatPanel.tsx` и `MessageInput.tsx` используют его вместо локальных state, поэтому voice mode включается только после отправки аудио и выключается при наборе текста. Маркер: `MARKER_156.S6.TECH.HYGIENE_FSM`.
- `client/src/components/chat/MessageBubble.tsx` скрывает текст ответа до прихода первого playable chunk (`stream.chunks`), показывает placeholder с `aria-live`, а после появления chunk’а/ошибки выводит окончательный transcript и фон для Node; сейчас `message.content` появляется только если `stream` либо остановлен, либо завершился. Маркер: `MARKER_156.S6.TECH.TEXT_AFTER_AUDIO`.
- Тесты `pulse`: `npm run test:personalization`, `npm test`, `npm run build` (последние два из `pulse`), все зелёные; при первой попытке из корня `vetka_live_03` команда `npm run test:personalization` падала, потому что там нет `package.json`.

## 2. Актуальный roadmap
1. **S6.4.3c — Progressive playback + storage replay** (pending): реализовать декодирование Opus-чанков в `MessageBubble` через `AudioContext`, сбор buffer’ов и fallback на `/api/voice/storage/{id}`.  
2. **S6.4.3a — Backing service audit**: убедиться, что `progressive_tts_service.py` или эквивалент генерирует Opus-чанки с YAML/MLX, и что dispatcher обновляет `chat_voice_stream_*` с нужными метаданными (generation_id, checksum).  
3. **S6.4.3b/d — Metricisation**: добавить log-маркеры (T0–T6) и температуры (first chunk latency, ack failure rate, voice dupe count) в `user_message_handler.py`, `voice_router.py`, `useSocket.ts`.  
4. **S6.5 — Feature gating & rollout**: системные feature flags (`progressive_voice_backend`, `progressive_voice_ui`, `voice_mode_hygiene`, `voice_storage_retry`) нужно обернуть в DevPanel switch и документировать rollback.

## 3. Следующий шаг
Фокус сейчас на воспроизведение stream’а в UI (пункт 2.1) и дополнительной телеметрии (2.3). После них перекроем документацию GAPS/ROADMAP и снова прогоним `pulse`-тесты перед merge.

## 4. Проверка
- `npm run test:personalization` (pulse)  
- `npm test` (pulse)  
- `npm run build` (pulse)  
