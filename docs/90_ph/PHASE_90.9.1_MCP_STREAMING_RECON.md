# PHASE 90.9.1: MCP Streaming Truncation Issue - Investigation Report

**Дата:** 2026-01-23
**Версия:** 90.9.1
**Язык:** Русский

---

## РЕЗЮМЕ ПРОБЛЕМЫ

В групповом чате, когда MCP инструмент `vetka_call_model` (вызов LLM через VETKA) используется:
- Запрос показывается корректно
- **Ответ модели НЕ ВИДИТ** или показывается ОБРЕЗАННЫМ

## КРИТИЧЕСКИЕ МАРКЕРЫ НАЙДЕННЫЕ

### MARKER_90.4.0_START - llm_call_tool.py (строки 14-210)

**Местоположение:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/llm_call_tool.py`

```python
# MARKER_90.4.0_START: VETKA chat ID for call_model streaming
LIGHTNING_CHAT_ID = "5e2198c2-8b1a-45df-807f-5c73c5496aa8"  # "Молния" group
# MARKER_90.4.0_END

def _emit_request_to_chat(self, model: str, messages: List[Dict], temperature: float, max_tokens: int):
    """Emit LLM request to VETKA chat"""
    # Get last user message for preview
    user_messages = [m for m in messages if m.get('role') == 'user']
    last_message = user_messages[-1]['content'] if user_messages else '(no user message)'

    # MARKER_90.9.1_FOUND: TRUNCATION POINT
    # ⚠️ TRUNCATING запросы до 200 символов!
    preview = last_message[:200]
    if len(last_message) > 200:
        preview += "..."

    content = f"**[MCP call_model]** {model}\n"
    content += f"Temperature: {temperature}, Max tokens: {max_tokens}\n"
    content += f"```\n{preview}\n```"

    self._emit_to_chat('@user', content, 'system')

def _emit_response_to_chat(self, model: str, content: str, usage: Optional[Dict] = None):
    """Emit LLM response to VETKA chat"""
    # ⚠️ ЗДЕСЬ НЕТ TRUNCATION для response_content!
    # Но есть потенциальная проблема: ответ полностью отправляется в одном emit()
    response_content = content + usage_str
    self._emit_to_chat(f'@{model}', response_content, 'response')
```

**ПРОБЛЕМА:**
- Запрос правильно урезается до 200 символов (для preview)
- **Ответ отправляется ПОЛНОСТЬЮ**, но Socket.IO emit может иметь ограничения

---

## МАРШРУТ ПОТОКА ДАННЫХ

### 1. MCP Tool → VETKA Chat (llm_call_tool.py)

```
execute()
├─ _emit_request_to_chat()    ← Запрос (200 char preview) ✓
├─ call_model_v2()            ← Получить ответ от модели
└─ _emit_response_to_chat()   ← Ответ ПОЛНЫЙ (МОЖЕТ БЫТЬ ПРОБЛЕМА!)
   └─ _emit_to_chat()
      └─ socketio.emit('group_message', {}, room=room)
```

### 2. Socket.IO Broadcast (group_message_handler.py)

**Строка 768-778 (group_message_handler.py):**

```python
# Emit stream end with full response
await sio.emit('group_stream_end', {
    'id': msg_id,
    'group_id': group_id,
    'agent_id': agent_id,
    'full_message': response_text,  # ← ПОЛНЫЙ ответ
    'metadata': {
        'model': model_id,
        'agent_type': agent_type
    }
}, room=f'group_{group_id}')
```

### 3. Frontend Reception (ChatPanel.tsx)

**Строка 265-283 (ChatPanel.tsx):**

```typescript
const handleGroupStreamEnd = (e: CustomEvent) => {
    const data = e.detail;
    if (data.group_id !== activeGroupId) return;

    setIsTyping(false);

    // Финализация потокового сообщения
    useStore.setState((state) => ({
        chatMessages: state.chatMessages.map((msg) =>
            msg.id === data.id
                ? {
                    ...msg,
                    content: data.full_message,  // ← ИСПОЛЬЗУЕТСЯ ПОЛНЫЙ ОТВЕТ
                    metadata: { ...msg.metadata, isStreaming: false },
                }
                : msg
        ),
    }));
};
```

---

## НАЙДЕННЫЕ ПРОБЛЕМЫ

### ПРОБЛЕМА #1: Socket.IO Emit для MCP Tool Response
**MARKER_90.9.1_ISSUE_1**

**Локация:** `src/mcp/tools/llm_call_tool.py:125-177`

**Код:**
```python
async def _emit_to_chat(self, sender_id: str, content: str, message_type: str = "chat"):
    try:
        socketio = get_socketio()
        if not socketio:
            logger.debug("[LLM_CALL_TOOL] SocketIO not available, skipping chat emit")
            return

        message_data = {
            'group_id': LIGHTNING_CHAT_ID,
            'sender_id': sender_id,
            'content': content,
            'message_type': message_type,
            'timestamp': datetime.now().isoformat(),
            'metadata': {
                'source': 'vetka_call_model',
                'mcp_tool': True
            }
        }

        # ⚠️ ПРОБЛЕМА: Async emit без await!
        async def emit_async():
            await socketio.emit('group_message', message_data, room=room)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Задачи не имеют гарантии доставки
                asyncio.create_task(emit_async())
            else:
                asyncio.run(emit_async())
        except Exception as e:
            logger.debug(f"[LLM_CALL_TOOL] Could not emit to chat (no event loop): {e}")
```

**ПРИЧИНЫ ОБРЕЗАНИЯ:**
1. `asyncio.create_task()` создает задачу БЕЗ ожидания доставки
2. Нет гарантии, что emit завершился перед возвратом
3. Большие сообщения могут быть потеряны или урезаны на уровне транспорта

---

### ПРОБЛЕМА #2: Нет Stream Token Events для MCP Response
**MARKER_90.9.1_ISSUE_2**

**Локация:** `src/mcp/tools/llm_call_tool.py:197-209`

**Код:**
```python
def _emit_response_to_chat(self, model: str, content: str, usage: Optional[Dict] = None):
    """Emit LLM response to VETKA chat"""
    response_content = content + usage_str
    # ⚠️ ОТПРАВЛЯЕМ ВЕСЬ ОТВЕТ В ОДНОМ EMIT!
    # Нет streaming tokens, just a big blob
    self._emit_to_chat(f'@{model}', response_content, 'response')
```

**ПРОБЛЕМА:**
- Обычный chat handler использует `group_stream_token` для progressивного ввода
- MCP tool использует один большой `_emit_to_chat()`
- Socket.IO может иметь ограничение на размер сообщения (обычно 100KB-1MB)

---

### ПРОБЛЕМА #3: Нет Handling для `group_stream_token` Events
**MARKER_90.9.1_ISSUE_3**

**Локация:** Frontend `ChatPanel.tsx:251-263`

```typescript
const handleGroupStreamToken = (e: CustomEvent) => {
    const data = e.detail;
    if (data.group_id !== activeGroupId) return;

    // Append token to streaming message
    useStore.setState((state) => ({
        chatMessages: state.chatMessages.map((msg) =>
            msg.id === data.id
                ? { ...msg, content: msg.content + data.token }  // ✓ Есть поддержка
                : msg
        ),
    }));
};
```

**РЕШЕНИЕ:** MCP tool должен использовать `group_stream_token` вместо одного большого emit.

---

### ПРОБЛЕМА #4: Request Truncation
**MARKER_90.9.1_ISSUE_4**

**Локация:** `src/mcp/tools/llm_call_tool.py:186-188`

```python
# Truncate long messages
preview = last_message[:200]  # ← ЗАЧЕМ 200?
if len(last_message) > 200:
    preview += "..."
```

**СЛЕДСТВИЕ:** Длинные запросы показываются только первые 200 символов. Это может скрывать важный контекст.

---

## ВРЕМЕННАЯ ШКАЛА ДОСТАВКИ

```
MCP Tool Request → _emit_request_to_chat()
  └─ emit('group_message') [200 char preview] → Frontend [ВИДИТ ✓]

LLM Call → call_model_v2()
  └─ Response (может быть 5000+ символов)

Response → _emit_response_to_chat()
  └─ _emit_to_chat() [ПОЛНЫЙ ответ]
     ├─ asyncio.create_task(emit_async())  [НЕ ЖДЕТ!]
     └─ return

Frontend: Событие 'group_message' с ответом [МОЖЕТ НЕ ПРИЙТИ или ОБРЕЗАН]
```

---

## РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ

### ИСПРАВЛЕНИЕ #1: Использовать Streaming Events
**Приоритет:** HIGH

Вместо одного большого emit:
```python
def _emit_response_to_chat(self, model: str, content: str, usage: Optional[Dict] = None):
    # Отправить STREAM START
    self._emit_to_chat_stream_start(model)

    # Отправить CHUNKS по 500-1000 символов
    for i in range(0, len(content), 500):
        chunk = content[i:i+500]
        self._emit_to_chat_stream_token(model, chunk)

    # Отправить STREAM END с полным контентом
    self._emit_to_chat_stream_end(model, content, usage)
```

### ИСПРАВЛЕНИЕ #2: Гарантированная Доставка
**Приоритет:** HIGH

```python
async def _emit_to_chat(self, ...):
    # Убедиться, что await завершен
    try:
        socketio = get_socketio()
        if not socketio:
            return

        room = f'group_{LIGHTNING_CHAT_ID}'

        # ✓ Прямой await без create_task
        await socketio.emit('group_message', message_data, room=room)
        logger.info(f"[LLM_CALL_TOOL] Emitted to {room}")

    except Exception as e:
        logger.error(f"[LLM_CALL_TOOL] Failed to emit: {e}")
```

### ИСПРАВЛЕНИЕ #3: Увеличить Preview для Requests
**Приоритет:** MEDIUM

```python
# ВМЕСТО:
preview = last_message[:200]

# ИСПОЛЬЗОВАТЬ:
preview = last_message[:800]  # Или полный текст, если < 1000
if len(last_message) > 800:
    preview += "..."
```

---

## ТЕСТОВЫЙ СЦЕНАРИЙ ВЕРИФИКАЦИИ

```python
# Test: Long MCP Response
1. Открыть групповой чат "Молния"
2. Отправить: @grok-4 Напиши 2000 символов про историю VETKA
3. ПРОВЕРИТЬ:
   ✓ Запрос видим (200+ символов preview)
   ✓ Ответ ПОЛНЫЙ (не обрезан)
   ✓ Streaming показывает прогресс
   ✓ Нет ошибок в консоли

# Test: Очень длинный ответ (>10000 символов)
1. @claude-opus-4-5 Объясни полный цикл разработки в VETKA
2. ПРОВЕРИТЬ: Ответ полностью виден, не обрезан в UI
```

---

## ФАЙЛЫ ДЛЯ МОДИФИКАЦИИ

1. **`src/mcp/tools/llm_call_tool.py`** (ГЛАВНЫЙ)
   - Добавить `_emit_to_chat_stream_start()`
   - Добавить `_emit_to_chat_stream_token()`
   - Добавить `_emit_to_chat_stream_end()`
   - Изменить `_emit_response_to_chat()` для использования streaming
   - Увеличить preview для requests

2. **`src/api/handlers/group_message_handler.py`** (ПРОВЕРИТЬ)
   - Убедиться что `group_stream_token` events регистрируются
   - Проверить room broadcasting

3. **`client/src/components/chat/ChatPanel.tsx`** (ПРОВЕРИТЬ)
   - Убедиться что `handleGroupStreamToken` корректно работает

---

## СТАТИСТИКА ПРОБЛЕМЫ

- **Файлы с проблемой:** 3 (llm_call_tool.py, group_message_handler.py, ChatPanel.tsx)
- **Строк кода затронуто:** ~100
- **Граница потока:** Socket.IO emit → Frontend reception
- **Максимальный размер сообщения:** Socket.IO default 100KB (может быть меньше)
- **Текущее ограничение preview:** 200 символов (запрос), НЕТУ (ответ)

---

## СВЯЗАННЫЕ ISSUES

- Phase 90.4.0: Added streaming to VETKA chat "Молния"
- Phase 80.13: MCP Agent @mention Routing
- Phase 56: GROUP CHAT MANAGER

---

**ВЕРСИЯ ДОКУМЕНТА:** 1.0
**СТАТУС:** INVESTIGATION COMPLETE
**АВТОР:** Claude Code Agent
**ДАТА СОЗДАНИЯ:** 2026-01-23
