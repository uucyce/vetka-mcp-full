# MARKER_156.S6_PROGRESSIVE_VOICE_IMPL_PLAN

Дата: 2026-02-28  
Автор: VETKA AI Agent  
Скоуп: S6 — имплементация progressive voice pipeline + hygiene FSM  
Цель: единый план внедрения с задачами, маркерами, кодовыми привязками и recon-аудитом.

## 1. Подтверждение фактов (recon audit)
- **Qwen TTS не стримит нативно** — `scripts/voice_tts_server.py` и `mlx_audio.tts()` возвращают полный waveform (подтверждение S6/104). поэтому pipeline строим на sentence-level chunking (`user_message_handler.py` + новая `progressive_tts_service.py`). Маркер: `MARKER_156.S6.TECH.QWEN_CHUNK_IMPL`.  
- **Socket.IO stream уже есть, но нужно контракт** — `useSocket.ts` обрабатывает `chat_voice_stream_*`, `MessageBubble.tsx` пока ждёт final blob; требуется ack/backpressure, seq. Маркер: `MARKER_156.S6.TECH.SOCKET_CONTRACT`.  
- **Определён формат Opus 48kHz** — `scripts/voice_tts_server.py`/`voice_storage_routes.py` работают с WAV, но в roadmap утверждён Opus chunk+storage. Маркер: `MARKER_156.S6.TECH.OPUS_48KHZ`.  
- **Merge/FSM + hygiene** — `ChatPanel.tsx`/`MessageInput.tsx` управляют voice state, но без centralized store; планируем `useVoiceModeStore`. Маркер: `MARKER_156.S6.TECH.FSM_INVARIANTS` и `MARKER_156.S6.TECH.HYGIENE_FSM`.  
- **Text-first-playable** — `MessageBubble.tsx` обновится по `state` (pending → streaming → playable), текст появляется после first chunk; fallback text on error. Маркер: `MARKER_156.S6.TECH.TEXT_AFTER_AUDIO`.

## 2. Реализация (phase-based roadmap)
1. **S6.4.3a — Progressive TTS service & chunk emission**  
   - Сделать новый `src/services/progressive_tts_service.py` (sentence splitter + Opus encode).  
   - В `user_message_handler.py` после `stream_end` или параллельно (para: first chunk) запускать `sentence_stream_tts` и emit chunk events.  
   - Маркеры: `MARKER_156.VOICE.S6_TRACE_T2_TTS_START`, `MARKER_156.VOICE.S6_TRACE_T3_TTS_DONE`, `MARKER_156.S6.TECH.QWEN_CHUNK_IMPL`.  
   - ✅ чеклист: sentence splitting + queue, Opus chunk encode, generation_id, background task, SLA first chunk <= 1500ms.  

2. **S6.4.3b — Socket.IO contract + ack/backpressure**  
   - В `useSocket.ts` обработка `chat_voice_stream_start/chunk/end` + ack emit.  
   - В backend логика `chat_voice_stream_chunk` emit c callback, ack handler, max 3 inflight, retry => failure.  
   - Маркер: `MARKER_156.S6.TECH.SOCKET_CONTRACT`.  
   - Чеклист: seq/ack map, queue size limit, reorder guard, duplicate checksum drop, ack timeout handling.  

3. **S6.4.3c — Playback Opus chunks in MessageBubble**  
   - В `MessageBubble.tsx` decode base64 Opus chunks via `AudioContext.decodeAudioData` и append to buffer; allow partial playback before storage.  
   - Использовать `audioMeta` waveform for progress; fallback on storage fetch from `/api/voice/storage/{id}` (normalize via `voice_storage_routes`).  
   - Маркер: `MARKER_156.S6.TECH.OPUS_48KHZ`.  
   - Чеклист: per-bubble chunk buffer, first chunk triggers play, second chunk append, fallback to `createdObjectUrlRef` for storage file, timer for text fallback.  

4. **S6.4.3d — Merge invariants + bubble FSM**  
   - Document and enforce eight invariants (`stream_start` before chunk, new generation resets, etc.) in `ChatPanel.tsx` + `MessageBubble`.  
   - Implement state transitions and hosts to avoid text/voice race.  
   - Маркер: `MARKER_156.S6.TECH.FSM_INVARIANTS`.  
   - Чеклист: message_id-based map, chunk sorting by seq, duplicate checksum drop, generation_id handshake, stream_end closes bubble.  

5. **S6.4.3e — Hygiene FSM store**  
   - Introduce `stores/useVoiceModeStore.ts` (Zustand) with events `VOICE_SENT`, `TEXT_TYPED`, `TEXT_CLEARED`.  
   - Backend session replicates flag for diagnostics; `ChatPanel.tsx` and `MessageInput.tsx` subscribe.  
   - Маркер: `MARKER_156.S6.TECH.HYGIENE_FSM`.  
   - Чеклист: voice mode ON only via store (trigger `VOICE_SENT`), OFF on first text input; ensure `MessageInput` references store to disable voice button when typing.  

6. **S6.4.3f — Text-after-first-playable rule**  
   - `MessageBubble` shows transcript only after chunk playing or after 5s timeout/error; include `aria-live` and fallback text.  
   - Provide indicator (“Голос генерируется”) while waiting.  
   - Маркер: `MARKER_156.S6.TECH.TEXT_AFTER_AUDIO`.  
   - Чеклист: text hidden until first chunk, timeout fallback, accessibility labels, error fallback text.

## 3. Tests & verification
- Unit: Vitest for FSM invariants (`MessageBubble` reducer, chunk dedupe, hygiene store).  
- Integration: Playwright scenario verifying first-chunk play <5s, ack/backpressure, mode toggle, text after playable.  
- Regression: ensure existing `voice_storage` replay path (S5 audit) still works after new Opus storage.  
- Observability: log markers T0–T6 in `user_message_handler.py` + new chunk ack events for metrics.

## 4. Feature flags & rollout
- `progressive_voice_backend`, `progressive_voice_ui`, `voice_mode_hygiene`, `voice_storage_alias`.  
- Rollout: start Canary 10% for backend chunk events, then enable UI FSM + hygiene, finalize after tests.  
- Rollback: disable backend flag → fallback to current `chat_voice_message` path, voice mode reverts to text.  

## 5. Next actions  
1. Завести new service + event emits as в пункте 1.  
2. Синхронизировать ack/backpressure + chunk processing (пункты 2-3).  
3. Прописать FSM/hygiene textual logic и text timing (п.4–6).  
4. Пройти тесты (unit + integration) и замерить first chunk latency.  
