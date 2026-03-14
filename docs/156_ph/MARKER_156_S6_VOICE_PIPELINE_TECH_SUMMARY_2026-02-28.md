# MARKER_156.S6_VOICE_PIPELINE_TECH_SUMMARY

Дата: 2026-02-28  
Автор: VETKA AI Agent  
Скоуп: S6 — solo progressive voice pipeline  
Цель: объединить и зафиксировать ответы Grok на шесть критичных вопросов; привязать к текущим маркерам и файлам.

## 1. Native streaming отсутствует → sentence-level async pipeline  
- `scripts/voice_tts_server.py` и `mlx_audio.tts()` действительно возвращают полный `np.ndarray`, никакого `yield` не поддерживают → `MARKER_156.REVIEW.GAP.QWEN_TRUE_STREAM_UNPROVEN` закрывается путем сегментации текста на предложения в `src/api/handlers/user_message_handler.py` и генерации отдельного chunk (каждое предложение) через новый progressive TTS service.  
- План: `sentence_stream_tts` отдаёт Opus chunk, backend эмитит `chat_voice_stream_chunk` с `message_id`/`generation_id`/`seq`/`checksum`. Нужно ещё реализовать сервис (pending).  

## 2. Socket.IO контракт chunk/ack/backpressure  
- Grok описал события `chat_voice_stream_start/chunk/end`, имя/seq/checksum, и ack (`chat_voice_stream_ack`).  
- Софт: `useSocket.ts` должен поддерживать queue map, лимит 3 inflight, ack timeout 500 ms, reorder drop, duplication guard. Эта логика запланирована в `MARKER_156_S6_RESEARCH_RESPONSE_VOICE_PIPELINE_TECHNICAL_SPECS`.  
- В настоящее время `user_message_handler.py` уже эмитит `chat_voice_stream_*`; необходимо добавить обработку ack на backend.  

## 3. Формат Opus 48kHz для Tauri/WKWebView  
- Выбор Opus 48 кГц (20 ms, 1 канал) обоснован: низкая задержка, встроенная поддержка в Safari/Chromium (используется в `MessageBubble.tsx` через `AudioContext`), и нет проблем с лицензией.  
- Альтернативы WAV/PCM/AAC либо «жируют», либо нестабильны в WKWebView.  
- Маркер: `MARKER_156.REVIEW.GAP.FORMAT_DECISION_MISSING` → закрыт.  

## 4. Merge policy и FSM  
- Предложены 8 инвариантов, охватывающих `stream_start`, `chunk`/`seq`, `generation_id` switch, `stream_end` и таймауты; эти правила фиксируются в новом FSM `MessageBubble.tsx`/`ChatPanel.tsx`.  
- Инварианты и состояния `thinking → voice_streaming → voice_playable_partial → voice_complete/error` описаны в `MARKER_156.S6.RESEARCH_RESPONSE…` (раздел 4).  

## 5. Hygiene FSM integration  
- Владелец состояния: фронтендовый Zustand store (`useVoiceModeStore`), backend поддерживает session flag `voice_mode`.  
- События: `VOICE_SENT` (после успешного отправления voice) включают режим, `TEXT_TYPED` отключают.  
- `ChatPanel.tsx` и `MessageInput.tsx` подписываются на store → единое поведение.  
- Маркер: `MARKER_156.REVIEW.GAP.HYGIENE_OWNERSHIP_MISSING` закрыт, новая store-структура в roadmap.  

## 6. Текст после первого playable  
- Text появляется только после первого chunk, либо после timeout/error (ARIA label/timeout=5s).  
- Доступность: `aria-live="polite"` и fallback text (если audio не стартовал).  
- Ведётся контроль `state === 'voice_playable_partial'` в `MessageBubble.tsx`.  
- Маркер: `MARKER_156.REVIEW.GAP.TEXT_VISIBILITY_POLICY_INCOMPLETE` закрыт.

## Заключение  
Все шесть базовых вопросов получили конкретные технические ответы с привязками к текущим файлам и маркерам. Следующий шаг — воплотить эти предложения в roadmap и реализацию (S6.4.3), а затем перейти к S6.5. Если надо, подкину final spec (с кодом и тестами) на основе этого резюме.
