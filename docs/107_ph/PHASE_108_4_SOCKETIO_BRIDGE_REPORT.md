# Phase 108.4: Real-time Socket.IO Bridge (MCP ↔ VETKA)

**Дата:** 2026-02-02
**Статус:** ✅ УЖЕ РЕАЛИЗОВАНО
**Маркер:** `MARKER_108_4`

---

## 🎯 Задание

Добавить Socket.IO интеграцию для real-time синхронизации MCP ↔ VETKA.

---

## 🔍 Исследование

### 1. Socket.IO уже настроен

**Файл:** `main.py`
**Строка:** 363-376

```python
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    ping_interval=25,
    ping_timeout=60,
    max_http_buffer_size=10 * 1024 * 1024,  # 10MB для больших артефактов
    logger=False,
    engineio_logger=False
)

# Store in app.state for handlers
app.state.socketio = sio
```

**✅ SocketIO активен и доступен через `request.app.state.socketio`**

---

### 2. MCP REST API endpoint уже эмитит события

**Файл:** `src/api/routes/debug_routes.py`
**Endpoint:** `POST /api/debug/mcp/groups/{group_id}/send`
**Строки:** 1143-1240

**Код:**
```python
# Phase 80.14: Improved MCP message emit with detailed logging
socketio = getattr(request.app.state, 'socketio', None)
room = f'group_{group_id}'

if socketio:
    try:
        # Broadcast message to all clients in group
        await socketio.emit('group_message', message.to_dict(), room=room)

        # UI consistency: stream_end event
        await socketio.emit('group_stream_end', stream_end_data, room=room)
    except Exception as e:
        print(f"[MCP] SocketIO emit error: {e}")
```

**✅ Real-time broadcasting уже работает!**

---

### 3. MCP Bridge использует этот endpoint

**Файл:** `src/mcp/vetka_mcp_bridge.py`
**Строки:** 170-184

```python
async def log_to_group_chat(message: str, msg_type: str = "system"):
    """Send log message to VETKA group chat"""
    if not MCP_LOG_ENABLED or not http_client:
        return
    try:
        await http_client.post(
            f"/api/debug/mcp/groups/{MCP_LOG_GROUP_ID}/send",
            json={
                "agent_id": "claude_mcp",
                "content": message,
                "message_type": msg_type
            }
        )
    except Exception as e:
        print(f"[MCP] Failed to log to group: {e}", file=sys.stderr)
```

**✅ MCP bridge → REST API → Socket.IO → Clients (уже реализовано)**

---

### 4. Frontend подписан на события

**Файл:** `client/src/hooks/useSocket.ts`
**Строки:** 969-975

```typescript
socket.on('group_message', (data) => {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(
      new CustomEvent('group-message', { detail: data })
    );
  }
});
```

**✅ Клиент получает MCP сообщения в реальном времени**

---

## 📊 Архитектура (текущая)

```
┌─────────────────┐
│  Claude Code    │
│  (MCP Client)   │
└────────┬────────┘
         │ stdio (MCP protocol)
         ↓
┌─────────────────────────────┐
│ vetka_mcp_bridge.py         │
│ - log_to_group_chat()       │
└────────┬────────────────────┘
         │ HTTP POST
         ↓
┌─────────────────────────────────────┐
│ /api/debug/mcp/groups/{id}/send     │
│ (debug_routes.py:1143)              │
│ - manager.send_message()            │
│ - socketio.emit('group_message')    │ ← MARKER_108_4
└────────┬────────────────────────────┘
         │ Socket.IO
         ↓
┌─────────────────────────────┐
│ VETKA UI (useSocket.ts)     │
│ - socket.on('group_message')│
│ - Live updates in chat      │
└─────────────────────────────┘
```

---

## ✅ Что уже работает

1. **MCP → REST API:** `vetka_mcp_bridge.py` отправляет сообщения через HTTP POST
2. **REST API → Socket.IO:** `debug_routes.py` эмитит `group_message` и `group_stream_end`
3. **Socket.IO → Clients:** `useSocket.ts` получает события и обновляет UI
4. **Rooms изоляция:** Каждая группа имеет свою room (`group_{group_id}`)
5. **Metadata сохранность:** `mcp_agent`, `icon`, `role` передаются в сообщении

---

## 🆕 Улучшения (Phase 108.4)

### Добавлен маркер `MARKER_108_4`

**Файл:** `src/api/routes/debug_routes.py`
**Строка:** 1211

```python
# MARKER_108_4: Real-time MCP ↔ VETKA bridge via Socket.IO
# Phase 80.14: Improved MCP message emit with detailed logging
# MCP agents (Claude Code, Browser Haiku) send messages via REST API
# This endpoint broadcasts them to all clients in real-time via Socket.IO
```

**Цель:** Явно обозначить место интеграции для будущих разработчиков.

---

## 📋 События Socket.IO

### 1. `group_message`

**Эмитится:** При получении сообщения от MCP агента
**Payload:**
```json
{
  "id": "uuid",
  "group_id": "group_uuid",
  "sender_id": "@Claude MCP",
  "content": "Message text",
  "message_type": "chat",
  "timestamp": "2026-02-02T12:34:56.789Z",
  "metadata": {
    "mcp_agent": "claude_mcp",
    "icon": "terminal",
    "role": "MCP Agent"
  }
}
```

### 2. `group_stream_end`

**Эмитится:** После завершения отправки сообщения
**Payload:**
```json
{
  "id": "uuid",
  "group_id": "group_uuid",
  "agent_id": "@Claude MCP",
  "full_message": "Complete message text",
  "metadata": {
    "mcp_agent": "claude_mcp",
    "agent_type": "MCP"
  }
}
```

---

## 🧪 Тестирование

### Проверить работу Socket.IO:

```bash
# 1. Запустить VETKA сервер
python main.py

# 2. В другом терминале - запустить MCP bridge
cd src/mcp
python vetka_mcp_bridge.py

# 3. В Claude Code выполнить:
vetka_read_group_messages(group_id="5e2198c2-8b1a-45df-807f-5c73c5496aa8")

# 4. Проверить в браузере (открыть DevTools):
# Должны появиться события 'group_message' в реальном времени
```

### Пример лога (успешная работа):

```
[MCP] Phase 80.14: Sending message to group 5e2198c2-8b1a-45df-807f-5c73c5496aa8, socketio=present
[MCP] Emitting 'group_message' to room group_5e2198c2-8b1a-45df-807f-5c73c5496aa8
[MCP] Emitting 'group_stream_end' to room group_5e2198c2-8b1a-45df-807f-5c73c5496aa8
[MCP] Phase 80.14: Emit successful for message abc123
```

---

## 📝 Выводы

### ✅ Реализация уже завершена

**Phase 80.14** (автор: вероятно Haiku или Architect) добавил:
- Socket.IO broadcast в MCP endpoint
- Детальное логирование для отладки
- Поддержку `group_stream_end` для UI консистентности

**Phase 108.4** добавил:
- **Маркер** `MARKER_108_4` для навигации
- **Документацию** (этот файл)
- **Комментарии** в коде для будущих разработчиков

### 🔄 Следующие шаги (опционально)

Если нужно улучшить интеграцию:

1. **Добавить событие `mcp_typing`:**
   - Эмитить когда MCP агент начинает генерировать ответ
   - Показывать индикатор "typing..." в UI

2. **Добавить событие `mcp_error`:**
   - Эмитить при ошибках MCP агента
   - Показывать user-friendly уведомления

3. **Поддержка приоритетов:**
   - Важные сообщения от MCP могут иметь `priority: high`
   - UI может показывать их с анимацией/звуком

---

## 🎓 Для разработчиков

### Как добавить новое событие Socket.IO для MCP?

**Шаг 1:** Добавить emit в `debug_routes.py`

```python
# После существующих emit
await socketio.emit('mcp_custom_event', {
    'data': 'your_data',
    'timestamp': datetime.now().isoformat()
}, room=f'group_{group_id}')
```

**Шаг 2:** Добавить listener в `useSocket.ts`

```typescript
socket.on('mcp_custom_event', (data) => {
  console.log('[MCP] Custom event received:', data);
  // Handle event
});
```

**Шаг 3:** Задокументировать в этом файле.

---

## 📚 Связанные файлы

- `main.py:363` - Socket.IO initialization
- `src/api/routes/debug_routes.py:1143` - MCP group message endpoint (MARKER_108_4)
- `src/mcp/vetka_mcp_bridge.py:170` - MCP bridge log function
- `client/src/hooks/useSocket.ts:969` - Frontend listener
- `src/api/handlers/group_message_handler.py` - Group message Socket.IO handlers

---

## 🏁 Итог

**Phase 108.4 завершена:**
✅ Socket.IO интеграция уже работает
✅ Маркер `MARKER_108_4` добавлен
✅ Документация создана

**Real-time синхронизация MCP ↔ VETKA полностью функциональна!**
