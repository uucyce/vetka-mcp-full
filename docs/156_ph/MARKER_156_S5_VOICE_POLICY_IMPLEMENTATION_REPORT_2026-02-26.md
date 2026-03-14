# MARKER_156.S5_VOICE_POLICY_IMPLEMENTATION_REPORT

Дата: 2026-02-26  
Фаза: 156 / S5 (mode policy switch)

## Что реализовано

### 1) UI policy switch в Group Chat
В ChatPanel добавлен пользовательский переключатель режимов:
- `Text` -> `text_only`
- `Auto` -> `voice_auto`
- `Voice` -> `voice_forced`

Сохранение в localStorage:
- key: `vetka_voice_reply_mode`

**Маркер:** `MARKER_156.VOICE.S5_UI_POLICY`  
**Файл:** `client/src/components/chat/ChatPanel.tsx`

### 2) Передача policy в backend через socket
`sendGroupMessage(...)` теперь отправляет:
- `voice_reply_mode`
- `voice_input`
- `reply_to_id`

**Маркер:** `MARKER_156.VOICE.S5_SOCKET_POLICY`  
**Файл:** `client/src/hooks/useSocket.ts`

### 3) Backend policy resolution
В group handler добавлен resolver:
- принимает `voice_reply_mode` + `voice_input`;
- хранит состояние в `group.shared_context`;
- вычисляет `should_emit_voice`.

Логика:
- `text_only` -> voice emit OFF
- `voice_forced` -> voice emit ON
- `voice_auto` -> включается после первого `voice_input=true` и держится в сессии группы

**Маркер:** `MARKER_156.VOICE.S5_POLICY_BACKEND`  
**Файл:** `src/api/handlers/group_message_handler.py`

### 4) Применение policy в S3 emitter path
Эмит `group_voice_*` и `group_voice_message` в основном group-pipeline теперь происходит только если `should_emit_voice=True`.

### 5) Доп. совместимость
Backend принимает reply target из обоих полей:
- `reply_to_id` (новое)
- `reply_to` (legacy)

## Маркеры S5
1. `MARKER_156.VOICE.S5_UI_POLICY`
2. `MARKER_156.VOICE.S5_SOCKET_POLICY`
3. `MARKER_156.VOICE.S5_POLICY_BACKEND`

## Проверка
- `python3 -m py_compile src/api/handlers/group_message_handler.py` -> OK

## Результат
Теперь voice-ответы агентов не всегда-on, а управляются политикой пользователя и сценарием voice input first.
