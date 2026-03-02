# MARKER_156.S5_SOLO_VOICE_STORAGE_RECON_AUDIT

Дата: 2026-02-27  
Скоуп: backend storage для SOLO voice (`upload + storage_id + replay after reload`)

## Итог в 1 строку
Сейчас solo voice работает только как in-memory/UI-фича (локальный `blob:` URL + STT), но **backend storage цепочки нет**: нет upload-роута, нет выдачи `/api/voice/storage/{id}`, и при загрузке чата metadata voice теряется.

## Findings (по приоритету)

### F1 — Критично: нет backend endpoint для playback по `storage_id`
- UI уже пытается воспроизводить через `/api/voice/storage/{id}` при наличии `metadata.audio.storage_id`.
- Но в backend не зарегистрирован router с voice storage endpoint.

Доказательства:
- `MessageBubble` формирует URL: `'/api/voice/storage/{id}'` — `client/src/components/chat/MessageBubble.tsx:157-163`.
- В агрегаторе роутов нет voice storage router — `src/api/routes/__init__.py:19-129`.
- Поиск по `src/` не находит route `/api/voice/storage` (кроме одного `storage_id: None` в group stub).

Риск:
- после reload replay невозможен даже если когда-то появится `storage_id` в сообщении.

### F2 — Критично: `GET /api/chats/{chat_id}` выбрасывает message metadata
- История возвращает только урезанный `MessageResponse` (id/role/content/agent/model/...) без `metadata` и без message `type`.
- Поэтому даже если voice metadata сохранилась в `chat_history.json`, на фронт она не попадает.

Доказательства:
- Формирование ответа без metadata/type — `src/api/routes/chat_history_routes.py:150-161`.
- Возврат `messages` как `MessageResponse[]` — `src/api/routes/chat_history_routes.py:172-190`.

Риск:
- voice bubble не восстановится после reload (пропадут `audio.waveform/url/storage_id`, `voice.*`).

### F3 — High: фронт при загрузке solo-чата принудительно мапит все сообщения в `type: 'text'`
- Даже если backend вернёт voice type в будущем, текущий маппинг в `ChatPanel` сотрёт это.

Доказательства:
- `type: msg.role === 'user' ? 'text' : 'text'` — `client/src/components/chat/ChatPanel.tsx:1571-1578`.
- Metadata при загрузке ограничена только model/source/provider — `client/src/components/chat/ChatPanel.tsx:1579-1583`.

Риск:
- voice replay после reload не появится даже после частичного backend фикса.

### F4 — High: solo upload аудио в storage отсутствует как операция
- Текущий flow записи в solo создаёт только локальный `blob:` URL и отправляет base64 в STT socket.
- Отдельного server upload шага (с возвратом `storage_id`) нет.

Доказательства:
- `URL.createObjectURL(payload.blob)` + сохранение только `metadata.audio.url` локально — `client/src/components/chat/ChatPanel.tsx:1176-1192`.
- Дальше идет только STT через `transcribeVoiceSample(...)` — `client/src/components/chat/ChatPanel.tsx:1195-1198`.
- `sendMessage/user_message` контракт не несёт binary/media metadata — `client/src/hooks/useSocket.ts:1753-1825`, `src/api/handlers/user_message_handler.py:358-390`.

Риск:
- после перезагрузки `blob:` URL недействителен, voice user-message превращается в текст без replay.

### F5 — Medium: контур сохранения сообщений metadata технически есть, но end-to-end не используется для solo voice
- `save_chat_message` сохраняет `metadata` как есть.
- `ChatHistoryManager.add_message` также сохраняет payload без фильтра metadata.

Доказательства:
- `metadata: message.get("metadata", {})` — `src/api/handlers/handler_utils.py:261-270`.
- `messages.append(message)` без обрезки metadata — `src/chat/chat_history_manager.py:462-489`.

Вывод:
- проблема не в дисковом слое, а в том, что solo voice metadata туда почти не отправляется и не возвращается на чтении.

## Текущее состояние SOLO цепочки (как есть)
1. FE записывает audio sample, строит waveform, делает локальный voice bubble с `blob:` url.  
2. FE отправляет audio в `voice_audio` для STT.  
3. Полученный transcript отправляется как обычный `user_message` (text).  
4. Backend сохраняет текстовые user/assistant сообщения.  
5. При reload `GET /api/chats/{id}` возвращает text-only сообщения (без voice metadata/type).  
6. Replay user voice после reload невозможен.

## GAP matrix (должно vs есть)
- Upload endpoint: **должно быть** `POST /api/voice/storage` → `storage_id`; **сейчас нет**.
- Binary persistence: **должно быть** disk/object storage; **сейчас нет**.
- Read endpoint: **должно быть** `GET /api/voice/storage/{id}`; **сейчас нет**.
- Message contract: **должно быть** `type='voice' + metadata.audio/voice`; **сейчас в solo read-path теряется**.
- Chat reload mapping: **должно быть** сохранить `type` и `metadata`; **сейчас принудительно text-only**.

## Status после фиксов (2026-02-27, update)
- ✅ Добавлен backend storage API:
  - `POST /api/voice/storage`
  - `GET /api/voice/storage/{storage_id}`
  - Файл: `src/api/routes/voice_storage_routes.py`
- ✅ Роут зарегистрирован в API агрегаторе:
  - Файл: `src/api/routes/__init__.py`
- ✅ В socket `user_message` добавлен контракт:
  - `message_type`, `message_metadata`
  - Файлы: `client/src/hooks/useSocket.ts`, `src/api/handlers/user_message_handler.py`
- ✅ `save_chat_message` теперь сохраняет `message_type`:
  - Файл: `src/api/handlers/handler_utils.py`
- ✅ `GET /api/chats/{chat_id}` возвращает `message_type + metadata`:
  - Файл: `src/api/routes/chat_history_routes.py`
- ✅ `ChatPanel` при reload учитывает `msg.message_type/msg.metadata` (не форсит только text):
  - Файл: `client/src/components/chat/ChatPanel.tsx`
- ✅ Solo voice send теперь загружает аудио в backend storage и сохраняет `storage_id` в metadata перед отправкой transcript.

### Остаточные риски после фиксов
1. Если upload в storage не удался, сообщение остается с локальным `blob:` URL (в рамках текущей сессии playable, после reload — нет).
2. `duration_ms` для не-WAV форматов может быть `null` (это допустимо, UI добирает длительность из `audio` metadata при playback).
3. Для upload endpoint нужен пакет `python-multipart` (если в окружении отсутствует, FastAPI multipart route не поднимется).

## Минимальный план закрытия (без хардкода провайдера)

### Step 1 (backend storage API)
- Добавить `src/api/routes/voice_storage_routes.py`:
  - `POST /api/voice/storage` (multipart/file): сохранить файл, вернуть `{storage_id, format, duration_ms}`.
  - `GET /api/voice/storage/{storage_id}`: отдать файл с корректным `Content-Type`, `ETag`, `Cache-Control`.
  - Опционально `HEAD` для preflight playback.
- Зарегистрировать router в `src/api/routes/__init__.py`.

### Step 2 (message persistence contract)
- Расширить solo message write-path:
  - при voice send сохранять `type='voice'` и `metadata.audio.{storage_id, format, duration_ms, waveform}`.
- `save_chat_message` уже умеет metadata; нужно передавать ее из UI/API контракта.

### Step 3 (chat history read-path)
- В `GET /api/chats/{chat_id}` вернуть raw message fields:
  - `type`, `metadata`, `model_source/model_provider` и т.д.
- Не терять `metadata.audio/voice` в `MessageResponse`.

### Step 4 (frontend hydration)
- В `ChatPanel.handleSelectChat` использовать `msg.type` (не форсить `text`).
- Пробрасывать `msg.metadata` целиком в `addChatMessage`.

### Step 5 (garbage collection)
- Добавить job удаления orphaned voice файлов:
  - либо reference-count по chat_history,
  - либо TTL + access log.

## Тест-критерии приёмки
1. Записать solo voice, отправить, увидеть waveform + transcript + replay.  
2. Перезапустить сервер/клиент, открыть тот же чат: voice bubble восстановлен, replay работает.  
3. `metadata.voice.voice_id` и `tts_provider` сохраняются и возвращаются.  
4. 404/invalid storage_id обрабатывается UI-ошибкой без падения чата.

## Доп. замечание
`chat_response` и текущий socket-хендлинг по умолчанию создают `type: 'text'` (`client/src/hooks/useSocket.ts:1033-1053`).  
Для полноценных voice-ответов ассистента в solo потребуется отдельный финальный message-contract (например `chat_voice_message`) либо расширение stream_end/chat_response payload до `type+metadata.audio`.
