# MARKER_156.S4_S1_S2_AUDIT_AND_WAVE_RESEARCH

Дата: 2026-02-27  
Скоуп: Solo voice flow (пункты 1 и 2) + исследование wave UI/хранения

## Целевой сценарий (что проверялось)
1. Пользователь записывает голосовой сэмпл (не realtime streaming STT).
2. В чате появляется voice bubble пользователя с реальной волной.
3. Аудио отправляется на STT, транскрипт подставляется в это же сообщение.
4. Транскрипт уходит в стандартный chat pipeline как обычное текстовое сообщение.

## Что уже реализовано по 1 и 2

### FE: запись сэмпла + волна
- `MessageInput` переведен на sample-recording через `MediaRecorder` + `AnalyserNode`.
- Волна строится из реальных RMS-уровней микрофона во время записи.
- Стриминг `voice_pcm` для этого UX не используется.

Файл:
- `client/src/components/chat/MessageInput.tsx`

### FE: отправка сэмпла в STT как single-shot
- Добавлен `transcribeVoiceSample(...)` c `request_id` корреляцией.
- Используются события `voice_audio -> voice_transcribed/voice_error`.

Файл:
- `client/src/hooks/useSocket.ts`

### BE: корреляция request_id
- `voice_socket_handler` возвращает `request_id` и в `voice_transcribed`, и в `voice_error`.

Файл:
- `src/api/handlers/voice_socket_handler.py`

### FE: voice bubble пользователя + replay
- При остановке записи создается user-message типа `voice` с:
  - `metadata.audio.url` (локальный object URL),
  - `metadata.audio.waveform`,
  - `metadata.audio.duration_ms`.
- После STT в этом же bubble обновляется `content` (transcript).
- Отдельно отправляется transcript в стандартный pipeline (`skipLocalUserMessage=true`, без дубля user-message).
- В `MessageBubble` есть replay/wave не только для ассистента, но и для user voice bubble.

Файлы:
- `client/src/components/chat/ChatPanel.tsx`
- `client/src/components/chat/MessageBubble.tsx`

## Почему раньше в логах всплывал Gemini/OpenAI/Deepgram
Это шло из realtime voice контура (`voice_stream_start/voice_pcm`), где используется `stt_from_pcm_bytes(...)` из `voice_realtime_providers.py`.  
В single-shot контуре (`voice_audio`) вызывается `voice_handler.speech_to_text(...)`, и там провайдер берется строго из запроса/конфига (`whisper|deepgram|openai`) без цепочки Gemini fallback.

Проверенные точки:
- `src/api/handlers/voice_socket_handler.py`
- `src/api/handlers/voice_handler.py`
- `src/api/handlers/voice_realtime_providers.py`

## Исследование: как правильно визуализировать и хранить аудио в чате

### Визуализация волны (рекомендованный вариант)
- Во время записи: `AnalyserNode.getByteTimeDomainData` -> RMS -> буфер амплитуд.
- Перед сохранением: нормализовать до фиксированного количества столбцов (`32-64`).
- В bubble: рисовать bars + progress overlay при playback.

Плюсы:
- Дешевая отрисовка.
- Одинаковый вид на desktop/mobile.
- Не зависит от backend декодинга аудио.

### Хранение/проигрывание (варианты)
- Вариант A (сейчас): локальный `blob:` URL в metadata
  - подходит для мгновенного UX,
  - не переживает перезагрузку страницы.
- Вариант B (рекомендуется для persistence): backend voice storage
  - upload бинаря,
  - вернуть `storage_id` + опциональный `public/url`.
  - в сообщении хранить `metadata.audio.storage_id`, `format`, `duration_ms`, `waveform`.
- Вариант C: base64 в сообщении
  - не рекомендуется (раздувает историю/БД и websocket payload).

### Важное замечание по текущему коду
`MessageBubble` поддерживает `storage_id` и строит URL вида `/api/voice/storage/{id}`, но backend route на этот endpoint сейчас не найден в `src/api/routes`.
Это значит, что persistence через `storage_id` формально предусмотрен в контракте UI, но серверная часть хранения/выдачи аудио не доведена до end-to-end.

## Зависимые участки (аудит-маршрут)
- Input/record:
  - `client/src/components/chat/MessageInput.tsx`
- STT socket contract:
  - `client/src/hooks/useSocket.ts`
  - `src/api/handlers/voice_socket_handler.py`
- Solo send pipeline:
  - `client/src/components/chat/ChatPanel.tsx`
  - `client/src/hooks/useSocket.ts` (`sendMessage`)
- Voice bubble render/playback:
  - `client/src/components/chat/MessageBubble.tsx`
  - `client/src/types/chat.ts` (metadata.audio / metadata.voice)
- Realtime legacy contour (параллельный путь):
  - `client/src/hooks/useRealtimeVoice.ts`
  - `src/api/handlers/voice_router.py`
  - `src/api/handlers/voice_realtime_providers.py`

## Остаточные риски
1. Нет server-side storage endpoint для audio persistence в solo history.
2. В проекте остаются параллельные voice-контуры (single-shot и realtime), что может путать диагностику логов.
3. Полный `tsc` по репозиторию падает на исторических ошибках в других модулях (не в затронутых файлах voice-flow).
