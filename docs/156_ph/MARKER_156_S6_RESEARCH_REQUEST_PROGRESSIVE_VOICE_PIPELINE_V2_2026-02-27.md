# MARKER_156.S6_RESEARCH_REQUEST_PROGRESSIVE_VOICE_PIPELINE_V2

## Follow-up RESEARCH REQUEST (precision pass)

Контекст:
- Первый ответ принят частично (`PARTIAL_ACCEPT`).
- Нужны implementation-grade ответы по спорным зонам.

Ссылки на код:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/voice_tts_server.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/voice_storage_routes.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/hooks/useSocket.ts`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/MessageBubble.tsx`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/MessageInput.tsx`

## Нужны точные ответы

1) Qwen true streaming feasibility (обязательно)
- Может ли наш `mlx_audio`/Qwen стек отдавать audio incrementally без полного завершения synth?
- Если да: конкретный API-level способ (какие объекты/итераторы, формат чанков).
- Если нет: best alternative architecture с first-playable <=5s (например sentence pre-synth + staged publish).

2) Протокол доставки с backpressure/ack
- Опиши точный контракт socket-событий с полями:
  - `message_id`, `generation_id`, `seq`, `chunk_ms`, `checksum`, `sent_at`.
- Добавь механизм ack:
  - FE -> BE `chat_voice_stream_ack{message_id,generation_id,seq}`.
- Политика повторов/таймаутов/дропа/duplicate handling.

3) Формат аудио для Tauri/WebView (single choice)
- Дай один рекомендованный формат для production:
  - PCM/WAV chunks или OGG/Opus chunks.
- Обоснуй по CPU, latency, decode stability в WKWebView/Tauri.

4) Deterministic merge invariants (формально)
- Таблица правил для всех race cases:
  - `stream_end` раньше `voice_stream_start`;
  - новый `generation_id` при уже открытом bubble;
  - duplicate seq same checksum;
  - duplicate seq different checksum;
  - missing seq gap.
- Для каждого кейса: expected state transition + UI behavior.

5) Hygiene FSM integration plan (точно по текущему коду)
- Кто source-of-truth: `ChatPanel` store или backend session?
- Где и как эмитить события:
  - `VOICE_SENT`, `TEXT_TYPED`, `TEXT_SENT`, `VOICE_REPLY_FAIL`.
- Как мигрировать без регресса для текущих hotkeys/mention logic в `MessageInput.tsx`.

6) Текстовая видимость и accessibility
- Нужна policy для режима "показывать текст после first-playable audio":
  - когда показывать text при timeout;
  - когда показывать text при voice error;
  - screen-reader доступность.

7) Конкретные acceptance tests
- 10 обязательных тестов с Given/When/Then и измеримыми критериями:
  - first-playable <=5s (p95),
  - duplicate-playback=0,
  - duplicate-bubble=0,
  - mode hygiene strict (`VOICE_SENT`/`TEXT_TYPED`).

## Неподвижное правило (must preserve)
- Voice mode ON только после `VOICE_SENT`.
- Voice mode OFF при первом `TEXT_TYPED`.
- `TEXT_CLEARED` не включает voice обратно.

