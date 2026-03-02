# MARKER_156.S6_RESEARCH_REQUEST_PROGRESSIVE_VOICE_PIPELINE

## RESEARCH REQUEST (for Grok): VETKA SOLO VOICE PROGRESSIVE DELIVERY + MODE HYGIENE

### Контекст
Проект: `vetka_live_03`

Текущее поведение (подтверждено по коду):
- SOLO ассистентское voice-сообщение приходит только финальным событием `chat_voice_message`.
- Перед этим UI ведет текстовый stream (`stream_start/token/end`) и создает text-placeholder.
- TTS endpoint отдает только готовый аудио payload целиком (не chunk stream).

Ключевые файлы:
- Backend pipeline:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/voice_storage_routes.py`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/voice_tts_server.py`
- Frontend socket + chat:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/hooks/useSocket.ts`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/MessageBubble.tsx`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/MessageInput.tsx`

Сценарий, который нужен:
1. Пользователь отправляет voice.
2. Сразу появляется assistant pending-voice bubble со статусом "записывает голосовое".
3. Аудио догружается чанками, можно слушать начало до завершения генерации.
4. Текст ответа можно показать после first-playable audio (чтобы не ломать ререндер и не плодить дубли).
5. Гигиена mode switch:
- voice mode ON только после отправки user voice;
- voice mode OFF сразу при первом текстовом вводе (typing), не после отправки.

---

## Что нужно получить в ответ

1. Архитектурное решение progressive audio для нашего стека (Socket.IO + FastAPI + web/tauri).
- 2-3 варианта с tradeoffs:
  - Socket.IO base64 chunks
  - HTTP chunked transfer
  - MSE/SourceBuffer
- Что лучше при ограничениях desktop WebView/Tauri.

2. Новый контракт событий для SOLO voice (с idempotency).
- `chat_voice_stream_start`
- `chat_voice_stream_chunk`
- `chat_voice_stream_end`
- поля dedupe: `message_id`, `generation_id`, `seq`, `is_final`, `checksum`.

3. State machine для frontend bubble.
- состояния: `thinking`, `voice_preparing`, `voice_streaming`, `voice_playable_partial`, `voice_complete`, `voice_error`.
- правила рендера текста и аудио без re-render гонок.

4. Backend pipeline design для first-playable SLA.
- Цель: first-playable <= 3-5s.
- Как делать sentence/phrase chunking для Qwen TTS.
- Как избежать дублирования генерации и повторного emit.

5. Mode hygiene FSM (обязательно).
- Event-driven схема:
  - `VOICE_SENT` -> ON
  - `TEXT_TYPED` -> OFF
  - `TEXT_CLEARED` -> без авто-ON
- Где хранить source-of-truth state.

6. Тест-пакет (must-have).
- Unit + integration + e2e сценарии:
  - no duplicate chunk playback
  - no duplicate bubble creation
  - partial playable before full completion
  - strict mode toggle by typing.

7. План миграции по этапам с rollback.
- S6.x incremental rollout без поломки текущего text stream.
- feature flags список и критерии включения.

---

## Ограничения и принципы
- Нельзя ломать provider/model routing.
- Нельзя делать fallback на чужие TTS без явного согласия.
- Нужна совместимость с текущим `voice_storage` replay после reload.
- При ошибке всегда должен оставаться корректный text fallback.

---

## Отдельный вопрос (важно)
Предложи конкретный способ устранить конфликт:
- сейчас `stream_start/token/end` создает text bubble,
- потом приходит `chat_voice_message` и иногда дает race/дубли/поздние апдейты.

Нужен deterministic merge policy для одного `message_id`.

