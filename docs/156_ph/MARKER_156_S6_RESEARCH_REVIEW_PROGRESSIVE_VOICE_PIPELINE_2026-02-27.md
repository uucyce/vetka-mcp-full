# MARKER_156.S6_RESEARCH_REVIEW_PROGRESSIVE_VOICE_PIPELINE

Дата: 2026-02-27
Основание: ответ Grok `MARKER_156.S6_RESEARCH_RESPONSE_PROGRESSIVE_VOICE_PIPELINE`

## Итог по качеству ответа
Статус: `PARTIAL_ACCEPT` (можно брать как направление, но не как финальный blueprint для имплементации).

## Что ответил хорошо (accept)
1. Правильно попал в главную проблему: текущий solo flow final-only и поэтому UX ждёт слишком долго.
2. Предложил правильный класс решения: `chat_voice_stream_start/chunk/end` + pending bubble.
3. Дал верную идею idempotency: `message_id + generation_id + seq + checksum`.
4. Отдельно выделил merge-race между `stream_*` и `chat_voice_message`.
5. Поддержал ваш hygiene-контракт: mode ON по `VOICE_SENT`, OFF по `TEXT_TYPED`.

Маркер: `MARKER_156.REVIEW.ACCEPT.CORE_DIRECTION`

## Критичные пробелы / риски (must clarify)

1. Не доказано, что Qwen backend реально умеет true streaming chunks
- В текущей кодовой базе `scripts/voice_tts_server.py` возвращает только полный payload.
- Ответ предлагает chunking, но не даёт конкретного механизма для нашего `mlx_audio` API (какие именно yield-данные, формат, границы).

Маркер: `MARKER_156.REVIEW.GAP.QWEN_TRUE_STREAM_UNPROVEN`

2. Base64-chunk через Socket.IO описан, но без backpressure/window control
- Нет политики `max_inflight_chunks`, `ack`, `retry`, `drop`, `reorder handling`.
- Без этого легко получить те же дубли/гонки в одном bubble.

Маркер: `MARKER_156.REVIEW.GAP.BACKPRESSURE_ACK_MISSING`

3. Недоопределён audio format strategy
- Предложены одновременно `WAV/Opus` и MSE/WebAudio пути, но нет единого решения для Tauri/WebView.
- Нет ответа по компромиссу: latency vs CPU vs стабильность decode на WKWebView.

Маркер: `MARKER_156.REVIEW.GAP.FORMAT_DECISION_MISSING`

4. Merge policy не доведена до строгих правил порядка
- Нужны формальные инварианты:
  - что делать, если `stream_end` пришёл раньше `voice_stream_start`;
  - что делать при `generation_id` смене;
  - что делать при дубликате `seq` с разным checksum;
  - когда финально "закрывать" bubble.

Маркер: `MARKER_156.REVIEW.GAP.ORDERING_INVARIANTS_MISSING`

5. Hygiene FSM описан концептуально, но без точек интеграции в текущий код
- Сейчас состояние размазано между:
  - `ChatPanel.tsx` (`setVoiceOnlyMode(true)` после voice path),
  - `MessageInput.tsx` (off при `hasText`).
- Нужна точная migration-схема: кто владелец state, кто publisher событий, кто consumer.

Маркер: `MARKER_156.REVIEW.GAP.HYGIENE_OWNERSHIP_MISSING`

6. Нет строгого ответа по "текст показываем только после first-playable audio"
- Не определены edge-cases для accessibility/timeout/error.

Маркер: `MARKER_156.REVIEW.GAP.TEXT_VISIBILITY_POLICY_INCOMPLETE`

## Решение по приему
- Принимаем ответ Grok как `архитектурный draft`.
- Не начинаем full implementation S6.4.3, пока не закрыты GAP выше.
- Требуется второй research-итератор с код-ориентированными решениями.

Маркер: `MARKER_156.REVIEW.DECISION.NEED_FOLLOWUP_V2`

## Неподвижное бизнес-правило (hygiene lock)
Обязательно фиксируем в impl/тестах:
- voice mode включается только событием `VOICE_SENT`.
- voice mode выключается на первом `TEXT_TYPED`.
- `TEXT_CLEARED` не включает voice обратно автоматически.

Маркер: `MARKER_156.REVIEW.HYGIENE_LOCK`
