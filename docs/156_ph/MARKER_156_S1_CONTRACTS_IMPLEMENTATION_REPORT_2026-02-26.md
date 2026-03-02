# MARKER_156.S1_CONTRACTS_IMPLEMENTATION_REPORT

Дата: 2026-02-26  
Фаза: 156 / S1 (contracts + events scaffold)

## Что реализовано

### 1) Контракт сообщения `voice` в фронте
- Добавлен тип `ChatMessage.type = 'voice'`.
- Добавлены контракты:
  - `metadata.audio` (`format`, `duration_ms`, `waveform`, `storage_id`, `url`)
  - `metadata.voice` (`voice_id`, `tts_provider`, `model_identity_key`, `persona_tag`)

**Маркер:** `MARKER_156.VOICE.S1_CONTRACT_TYPES`  
**Файл:** `client/src/types/chat.ts`

### 2) Socket-контракты voice событий
- Добавлены типы событий в `useSocket`:
  - `group_voice_stream_start`
  - `group_voice_stream_chunk`
  - `group_voice_stream_end`
  - `group_voice_message`
- Добавлена прокладка `socket.on(...) -> window CustomEvent(...)`.

**Маркер:** `MARKER_156.VOICE.S1_SOCKET_EVENTS`  
**Файл:** `client/src/hooks/useSocket.ts`

### 3) Прием `group_voice_message` в ChatPanel
- Добавлен обработчик `group-voice-message`.
- Поведение:
  - если сообщение уже есть (по `id`) -> апгрейд в `type='voice'` + metadata.audio/voice;
  - если нет -> добавление нового assistant voice-message.

**Маркер:** `MARKER_156.VOICE.S1_CHAT_VOICE_EVENT`  
**Файл:** `client/src/components/chat/ChatPanel.tsx`

### 4) Backend S1 voice-payload stub
- Добавлен helper payload-builder для voice-контракта (без реального TTS пока):
  - `_build_voice_contract_stub(...)`
  - `_emit_group_voice_contract_stub(...)`
- После `group_stream_end` сервер теперь эмитит `group_voice_message` (schema-complete stub) в основных ветках:
  - Hostess answer
  - Hostess delegate
  - Hostess summary
  - обычный agent success
  - agent error

**Маркер:** `MARKER_156.VOICE.S1_BACKEND_STUB`  
**Файл:** `src/api/handlers/group_message_handler.py`

### 5) Реестр событий stream handler
- Добавлены enum-события voice stream/message в `StreamEventType`.

**Маркер:** `MARKER_156.VOICE.S1_STREAM_ENUMS`  
**Файл:** `src/api/handlers/stream_handler.py`

## Список маркеров (единая карта)
1. `MARKER_156.VOICE.S1_CONTRACT_TYPES`
2. `MARKER_156.VOICE.S1_CONTRACT_AUDIO`
3. `MARKER_156.VOICE.S1_CONTRACT_VOICE`
4. `MARKER_156.VOICE.S1_SOCKET_EVENTS`
5. `MARKER_156.VOICE.S1_CHAT_VOICE_EVENT`
6. `MARKER_156.VOICE.S1_BACKEND_STUB`
7. `MARKER_156.VOICE.S1_STREAM_ENUMS`

## Проверка
- Python syntax check:
  - `python3 -m py_compile src/api/handlers/group_message_handler.py src/api/handlers/stream_handler.py`
  - статус: OK

## Что это дает уже сейчас
- Единый контракт `voice message` во frontend/backend согласован.
- UI может принимать voice-message payload как отдельный тип сообщения.
- Backend уже выдает `group_voice_message` рядом с текстовым `group_stream_end`.

## Что еще не закрыто (следующий этап)
- Реальный audio stream/chunk от TTS и финальный media artifact (`S3/S4`).
- Персистентный lock `provider:model_id -> voice_id` (`S2`).
- Эмоции голоса как runtime policy (`S6`).

## По research gap
Критичных пробелов для старта S1 нет.  
Остается точечный research для `S6`: подтвержденный контракт Qwen TTS по эмоциям/просодии (native params vs prompt-conditioning).
