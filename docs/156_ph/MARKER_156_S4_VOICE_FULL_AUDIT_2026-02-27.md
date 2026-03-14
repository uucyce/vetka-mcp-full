# MARKER_156 — Full Voice Audit (2026-02-27)

## Scope
Audit of end-to-end voice path for Chat (solo + group):
- recording UX (real wave + replay)
- audio message contract
- STT moment (post-record, not realtime dictation)
- model routing identity (model + provider/source)
- reply voice mode and TTS provider (Qwen TTS expected)

## Target behavior (as requested)
1. User records voice sample (MediaRecorder-like), sees real waveform.
2. Recorded audio is sent as voice message object into chat timeline.
3. STT runs after stop/send (not live dictation loop while speaking).
4. Voice chat mode activates:
- solo: selected called model replies by text generation + Qwen TTS voice.
- group: team replies by text generation + Qwen TTS voices, each stable voice_id.
5. No hidden provider/model fallback; strict model + source identity.

---

## Findings (Critical)

### A1. Chat input mic is wired to realtime PCM/VAD pipeline, not to recorded-audio message flow
- `client/src/components/chat/MessageInput.tsx:154-169`
- `client/src/hooks/useRealtimeVoice.ts:272-325`
- `src/api/handlers/voice_socket_handler.py:225-276`
- `src/api/handlers/voice_router.py:239-275`

What happens now:
- Mic opens `useRealtimeVoice` -> sends `voice_pcm` frames continuously.
- Backend STT is executed on utterance end (`voice_utterance_end`) and returns transcript (`voice_final`).
- Frontend writes transcript into text input and auto-sends text (`onChange` + `onSend`).

Impact:
- This is exactly live dictation path (realtime STT), not “record sample -> send audio message”.

### A2. No solo audio-message transport contract in chat send path
- `client/src/hooks/useSocket.ts:1793-1808`

What happens now:
- `user_message` emit sends only `text`, no audio payload (`blob/base64/storage_id/mime/duration/waveform`).

Impact:
- Voice from user cannot be represented/stored/sent as first-class voice message in solo pipeline.

### A3. Solo assistant messages are forced to `type: 'text'`
- `client/src/hooks/useSocket.ts:1028-1037`

What happens now:
- `chat_response` is always mapped to `type: 'text'`.

Impact:
- Even if backend wanted to send voice metadata, current mapping drops voice typing for solo assistant path.

### A4. Realtime TTS provider for voice router is not Qwen TTS
- `src/api/handlers/voice_realtime_providers.py:558-578`
- `src/api/handlers/voice_realtime_providers.py:526-555`

What happens now:
- TTS order = ElevenLabs -> Piper -> browser TTS fallback.
- Qwen TTS is not used in this realtime router path.

Impact:
- Contradicts requirement “all models answer through our Qwen TTS”.

### A5. Realtime voice defaults enforce local Whisper STT and Grok model in session config
- `src/api/handlers/voice_router.py:54-57`
- `src/api/handlers/voice_router.py:250-265`
- `src/api/handlers/voice_realtime_providers.py:268-289`

What happens now:
- Default STT provider is `whisper`.
- Router performs STT in realtime path by design.

Impact:
- Explains your logs (`whisper/transcribe.py`, FP32 warnings) and “дикое распознавание”.

### A6. Group voice stream chunks are emitted, but frontend has no consumer for playback stream events
- Emitters: `src/api/handlers/group_message_handler.py:323-372` (`group_voice_stream_*`)
- Forwarding: `client/src/hooks/useSocket.ts:1237-1261`
- No listeners/players in ChatPanel/voice UI for `group-voice-stream-*` custom events.

Impact:
- Audio chunks are produced but effectively unused in UI realtime playback path.

### A7. Voice bubble playback URL contract is incomplete for persisted playback
- Bubble expects `metadata.audio.url` or `storage_id`:
  - `client/src/components/chat/MessageBubble.tsx:157-163`
- Group payload currently sets `storage_id=None`, `url=None` by default:
  - `src/api/handlers/group_message_handler.py:236-242`

Impact:
- Voice bubble often falls back to browser TTS for replay instead of real generated audio file URL.

---

## Findings (Major)

### B1. Legacy record-and-send component exists but is disconnected from chat input
- `client/src/components/voice/VoiceButton.tsx:165-215`
- usage search: only declaration/export; no integration in chat input flow.

What it does:
- Uses `MediaRecorder`, builds blob, sends `voice_audio` after stop.

Impact:
- The code that matches your desired “record sample then send” exists but is currently not wired into `MessageInput`/`ChatPanel`.

### B2. Two parallel voice stacks increase interception risk
1) Legacy stack:
- `voice_start`, `voice_audio`, `voice_stop`, `tts_request` in `voice_socket_handler.py`
- provider impl in `voice_handler.py`

2) Realtime stack:
- `voice_stream_start`, `voice_pcm`, `voice_utterance_end`, ...
- provider impl in `voice_realtime_providers.py` + `voice_router.py`

Handler registry confirms both active:
- `src/api/handlers/__init__.py:119-121`

Impact:
- Duplicate logic and mismatched expectations; behavior depends on which frontend path is wired.

### B3. `MessageInput` button path ignores `realtimeVoiceEnabled` flag in main click route
- `client/src/components/chat/MessageInput.tsx:487-494`

What happens:
- For voice mode button, it always calls `realtimeVoice.startListening()`.

Impact:
- Even if UI state suggests another mode, mic path stays realtime PCM/VAD.

---

## Findings (What is already correct)

### C1. Provider identity routing (`model + source`) is now preserved in key solo/group paths
- Solo stream/direct:
  - `src/api/handlers/user_message_handler.py:823`
  - `src/api/handlers/user_message_handler.py:1329,1342`
- Group:
  - `src/api/handlers/group_message_handler.py:1749-1751`
- Provider detector bug for `provider/model:tag` vs ollama fixed in registry.

### C2. Group voice policy and role voice-id lock are implemented
- Policy resolver:
  - `src/api/handlers/group_message_handler.py:413-444`
- Role voice lock:
  - `src/api/handlers/group_message_handler.py:182-205,277-294`
  - `src/voice/voice_assignment_registry.py` (stable assignments)

---

## Dependency map (where to change for requested behavior)

### D1. Frontend recording mode (must switch from realtime dictation to sample recording)
- `client/src/components/chat/MessageInput.tsx`
- `client/src/components/voice/VoiceButton.tsx` (candidate to reuse)
- `client/src/hooks/useSocket.ts` (new `user_voice_message` emit contract)

### D2. Backend user voice message ingest
- `src/api/handlers/voice_socket_handler.py` (or dedicated event in `user_message_handler.py`)
- `src/api/handlers/user_message_handler.py` (persist + route + emit timeline event)

### D3. Solo voice response contract
- `src/api/handlers/user_message_handler.py` (emit voice metadata/event for solo)
- `client/src/hooks/useSocket.ts` (`chat_response` mapping to voice type when payload contains voice metadata)
- `client/src/components/chat/ChatPanel.tsx` (handle solo voice event similarly to group)

### D4. TTS unification to Qwen
- Replace realtime router TTS in:
  - `src/api/handlers/voice_realtime_providers.py` (`tts_sentence_to_base64`)
- Reuse path already used in group:
  - `src.voice.tts_engine.get_tts_engine(primary='qwen3', ...)`

### D5. Audio storage/replay
- Implement persistent audio storage + retrieval route (currently missing):
  - expected by bubble at `/api/voice/storage/{storage_id}`
  - no matching route found in `src/api/routes/*`

---

## Bottom line
Current production path in chat is realtime STT dictation (PCM+VAD+Whisper-like), then text send.
This is why you see garbled transcript and no true user audio-message behavior.

To match required scenario, chat input must be rewired to a **recorded sample message contract** (audio first-class), and solo response path must emit **voice message metadata + Qwen TTS audio** (as already partially done in group).
