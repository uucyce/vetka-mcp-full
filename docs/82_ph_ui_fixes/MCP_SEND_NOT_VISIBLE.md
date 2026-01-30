# АУДИТ: MCP Сообщения Не Видны в UI + @mention Не Триггерит Агентов

**Дата:** 2026-01-21
**Статус:** КРИТИЧЕСКОЕ - Разрыв между MCP и UI сообщениями
**Фаза:** 80.4 - MCP Agents in Group Chat

---

## ПРОБЛЕМА

При отправке сообщения из MCP через endpoint `POST /api/debug/mcp/groups/{group_id}/send`:
1. ✓ Сообщение успешно отправляется в group_chat_manager
2. ✓ Возвращается успешный ответ с message_id
3. ✗ Сообщение **НЕ видно** в UI группы
4. ✗ **@mention не триггерит** select_responding_agents() для вызова агентов

---

## АРХИТЕКТУРА: РАЗРЫВ В ПОТОКЕ ДАННЫХ

### Существующая система (РАБОТАЕТ):

```
UI Browser (Socket.IO)
  ↓
  emit('group_message', {group_id, sender_id, content})
  ↓
@sio.on('group_message') в group_message_handler.py (line 354)
  ↓
  1. manager.send_message() → сохраняет в group.messages deque
  2. sio.emit('group_message', user_message.to_dict()) → broadcast
  3. select_responding_agents() → парсит @mentions, вызывает агентов
  ↓
UI получает broadcast → отображает сообщение + ответы агентов
```

**КЛЮЧЕВОЙ МОМЕНТ:** Socket.IO handler `@sio.on('group_message')` содержит ВСЮ логику:
- Сохранение сообщения
- Broadcast в UI
- Вызов агентов через select_responding_agents()

### MCP система (НЕПОЛНАЯ):

```
MCP/Claude Code
  ↓
  POST /api/debug/mcp/groups/{group_id}/send
  ↓
send_group_message_from_mcp() в debug_routes.py (line 1143)
  ↓
  1. manager.send_message() → сохраняет в group.messages deque ✓
  2. socketio.emit('group_message', message.to_dict()) ✓
  3. socketio.emit('group_stream_end', ...) ✓
  ✗ НЕ ВЫЗЫВАЕТ select_responding_agents()
  ✗ НЕ ПАРСИТ @mentions
  ✗ НЕ ЗАПУСКАЕТ АГЕНТОВ
  ↓
Сообщение есть в БД, но UI не получает агентские ответы
```

---

## ДЕТАЛЬНЫЙ АНАЛИЗ

### 1. KOД: debug_routes.py (line 1142-1228)

```python
@router.post("/mcp/groups/{group_id}/send")
async def send_group_message_from_mcp(
    request: Request,
    group_id: str,
    body: MCPGroupMessageRequest
) -> Dict[str, Any]:
    """
    ❌ ПРОБЛЕМА: Эта функция НЕ вызывает select_responding_agents()
    """
    manager = get_group_chat_manager()
    group = manager._groups.get(group_id)

    # Линия 1181: Отправка сообщения
    message = await manager.send_message(
        group_id=group_id,
        sender_id=sender_id,
        content=body.content,
        message_type=body.message_type,
        metadata={...}
    )

    # Линии 1200-1212: Emit в Socket.IO
    if socketio:
        await socketio.emit('group_message', message.to_dict(), room=f'group_{group_id}')
        await socketio.emit('group_stream_end', {...}, room=f'group_{group_id}')

    # ❌ ОТСУТСТВУЕТ:
    # - await manager.select_responding_agents(...)
    # - Вызов orchestrator для агентов
    # - Parsing @mentions
```

### 2. КОНТРАСТ: group_message_handler.py (line 354-687)

Socket.IO handler ПРАВИЛЬНО делает:

```python
@sio.on('group_message')
async def handle_group_message(sid, data):
    """Полная обработка с agentами"""

    # Линия 390: Сохранение сообщения
    user_message = await manager.send_message(...)

    # Линия 404: Broadcast в UI
    await sio.emit('group_message', user_message.to_dict(), room=f'group_{group_id}')

    # Линии 449-454: ✓ ЗДЕСЬ ПРОИСХОДИТ МАГИЯ
    participants_to_respond = await manager.select_responding_agents(
        content=content,  # Парсит @mentions
        participants=group.get('participants', {}),
        sender_id=sender_id,
        reply_to_agent=reply_to_agent  # Phase 80.7
    )

    # Линии 478-681: Вызов каждого агента через orchestrator
    while processed_idx < len(participants_to_respond):
        # orchestrator.call_agent()
        # emit('group_stream_end') с ответом
        # manager.send_message() для ответа агента
```

### 3. ФАЗА 80.6 - ИЗОЛЯЦИЯ MCP АГЕНТОВ

В group_chat_manager.py (line 199-223):

```python
async def select_responding_agents(
    self,
    content: str,
    participants: Dict[str, Any],
    sender_id: str,
    reply_to_agent: str = None
) -> List[Any]:
    """
    Phase 80.6: MCP agent isolation - no auto-response cascade.
    """

    # Линия 202: Проверка, отправляет ли АГЕНТ (начинается с @)
    is_agent_sender = sender_id.startswith('@')

    # Линия 221-223: ВАЖНО!
    if is_agent_sender:
        logger.info(f"[GroupChat] Phase 80.6: Agent sender '{sender_id}' without @mention - no auto-response")
        return []  # ❌ АГЕНТ БЕЗ @mention не триггерит ответы
```

**ВЫВОД:** Когда MCP отправляет как '@Claude Code', без явной @mention в сообщении:
- select_responding_agents() возвращает пустой список
- Ни один агент не вызывается
- Это по дизайну (Phase 80.6), но нужна документация

---

## ПОТОК СООБЩЕНИЙ: ГДЕ ОНИ НАХОДЯТСЯ?

### Сценарий 1: UI отправляет (РАБОТАЕТ)

```
UI emit('group_message', {group_id, sender_id: 'user', content: 'Hello'})
  ↓
Socket.IO server (группа подписана на room)
  ↓
Сообщение попадает:
  ✓ group.messages deque (GroupChatManager)
  ✓ chat_history.json (ChatHistoryManager) - линия 411-421
  ✓ Real-time UI через emit('group_message')
  ✓ Agents видят в контексте
```

### Сценарий 2: MCP отправляет (НЕПОЛНЫЙ)

```
MCP: POST /api/debug/mcp/groups/{group_id}/send
  ↓
debug_routes.send_group_message_from_mcp()
  ↓
Сообщение попадает:
  ✓ group.messages deque (GroupChatManager)
  ✓ chat_history.json (через manager.save_to_json() на линии 337, 372, 467)
  ✓ Real-time emit('group_message') на линии 1200
  ✓ Agents видят в контексте (через manager.get_messages())

  ✗ agents НЕ получают response flow (select_responding_agents не вызывается)
```

---

## ЧТО СЛУЧИЛОСЬ С @MENTIONS

### Логика select_responding_agents():

**Линия 205-216:**
```python
# 1. Проверяем @mentions в сообщении
mentioned = re.findall(r'@(\w+)', content)  # Ищет @word
if mentioned:
    selected = []
    for pid, p in participants.items():
        display = p.get('display_name', '').lower()
        agent_id = p.get('agent_id', '').lower().lstrip('@')
        if any(m.lower() in display or m.lower() == agent_id for m in mentioned):
            if p.get('role') != 'observer':
                selected.append(p)
    if selected:
        logger.info(f"[GroupChat] Selected by @mention: ...")
        return selected  # ✓ Возвращает агентов
```

### ПО ЧТО МЕ ВИДНЫ @mentions?

**Когда MCP отправляет:**
```
sender_id = "@Claude Code"  (начинается с @)
is_agent_sender = True
```

**Если в сообщении НЕТ явной @mention (e.g., "@Architect"):**
```
content = "Please help me with this task"
mentioned = []  # regex не нашел @word
```

**Результат - линия 221-223:**
```python
if is_agent_sender and not mentioned:
    return []  # Агент отправляет без @mention → никто не отвечает
```

---

## РЕШЕНИЕ 1: ДОПОЛНИТЬ MCP ENDPOINT

**Файл:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/debug_routes.py`

**Строки 1142-1228:** Функция `send_group_message_from_mcp()`

**Добавить после line 1181 (после manager.send_message()):**

```python
# ✓ ДОБАВИТЬ: Вызов select_responding_agents + orchestrator
from src.initialization.components_init import get_orchestrator

# ... existing code ...

message = await manager.send_message(
    group_id=group_id,
    sender_id=sender_id,
    content=body.content,
    message_type=body.message_type,
    metadata={...}
)

# ✓✓✓ ДОБАВИТЬ ЭТОТ БЛОК ✓✓✓
if message:
    # Determine which agents should respond
    participants_to_respond = await manager.select_responding_agents(
        content=body.content,
        participants=group.participants,
        sender_id=sender_id,
        reply_to_agent=None  # No reply context for MCP
    )

    print(f"[MCP] Group message: {len(participants_to_respond)} agents to respond")

    # Route to agents if any @mentions or agent selection
    if participants_to_respond:
        orchestrator = get_orchestrator()
        if orchestrator:
            for participant in participants_to_respond:
                try:
                    # Call agent via orchestrator
                    result = await asyncio.wait_for(
                        orchestrator.call_agent(
                            agent_type=participant.get('display_name', 'Dev'),
                            model_id=participant.get('model_id'),
                            prompt=body.content,
                            context={'group_id': group_id}
                        ),
                        timeout=120.0
                    )

                    # Store agent response
                    response_text = result.get('output', '') if isinstance(result, dict) else str(result)

                    agent_msg = await manager.send_message(
                        group_id=group_id,
                        sender_id=participant.get('agent_id'),
                        content=response_text,
                        message_type='response'
                    )

                    # Emit agent response
                    if socketio and agent_msg:
                        await socketio.emit('group_message', agent_msg.to_dict(), room=f'group_{group_id}')

                except Exception as e:
                    print(f"[MCP] Error calling agent {participant.get('agent_id')}: {e}")
```

---

## РЕШЕНИЕ 2: ДОКУМЕНТИРОВАТЬ ПОВЕДЕНИЕ PHASE 80.6

**Файл:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/group_chat_manager.py`

**Добавить в docstring select_responding_agents (line 159-186):**

```python
"""
Phase 80.7: Intelligent agent selection.
Phase 80.6: MCP agent isolation - no auto-response cascade.

WICHTIG - AGENT-TO-AGENT COMMUNICATION RULES:
==============================================

1. USER sends WITHOUT @mention:
   - select_responding_agents() uses SMART keyword selection
   - Default: first non-observer agent
   - Example: "Please help" → @Architect responds

2. AGENT sends WITHOUT @mention (sender_id.startswith('@')):
   - Returns empty list (Phase 80.6 isolation)
   - No auto-response cascade (prevents agent loops)
   - This is INTENTIONAL to prevent infinite loops
   - Example: "@Claude Code" sends "help" → NOBODY responds

3. ANY sender WITH explicit @mention (in content):
   - Routes to ONLY mentioned agents, regardless of sender
   - Example: "@Claude Code" sends "help @Architect" → @Architect responds
   - Example: "user" sends "@Architect" → @Architect responds

APPLIES TO: Socket.IO handler + REST endpoint + MCP endpoint
"""
```

---

## РЕШЕНИЕ 3: UI ЗАГРУЗИТЬ СООБЩЕНИЯ ПРИ ОТКРЫТИИ

**Файл:** Frontend (не найден в этом аудите)

Когда UI открывает группу, он должен:
1. Socket.IO join_group
2. **GET /api/debug/mcp/groups/{group_id}/messages** или **GET /api/groups/{group_id}/messages**
3. Отобразить все existing сообщения
4. Subscribe на real-time updates

**Текущие endpoints:**
- `GET /api/groups/{group_id}/messages` (line 121-127 в group_routes.py)
- `GET /api/debug/mcp/groups/{group_id}/messages` (line 1076-1132 в debug_routes.py)

Оба должны возвращать одинаковые сообщения из `group.messages` deque.

---

## ТЕСТИРОВАНИЕ

### Тест 1: MCP отправляет с @mention

```bash
curl -X POST http://localhost:8000/api/debug/mcp/groups/c9dd0a3a-ab2c-49f2-b248-9d0a4d27b487/send \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "claude_code",
    "content": "@Architect please review this architecture",
    "message_type": "chat"
  }'
```

**Ожидается:**
- Message сохранена в group.messages ✓
- @Architect получит запрос (если Solution 1 реализовано)
- UI получит message broadcast ✓

### Тест 2: Проверить наличие сообщение

```bash
curl http://localhost:8000/api/debug/mcp/groups/c9dd0a3a-ab2c-49f2-b248-9d0a4d27b487/messages \
  -H "Content-Type: application/json"
```

**Ожидается:**
- Все сообщения от MCP и UI видны в одном списке

### Тест 3: UI должна загрузить историю

```javascript
// На frontend при открытии группы
fetch(`/api/groups/${groupId}/messages?limit=100`)
  .then(r => r.json())
  .then(data => {
    data.messages.forEach(msg => {
      renderMessage(msg);  // Render all existing
    });

    // ТОГДА subscribe на real-time
    socket.emit('join_group', {group_id: groupId});
    socket.on('group_message', msg => renderMessage(msg));
  });
```

---

## КОРНЕВЫЕ ПРИЧИНЫ

| Проблема | Причина | Слой |
|----------|---------|------|
| MCP сообщение не вызывает агентов | `select_responding_agents()` не вызывается в `send_group_message_from_mcp()` | REST API |
| @mention не работает | Phase 80.6: Агенты без @mention не триггерят ответы (по дизайну) | Бизнес-логика |
| UI не видит сообщения | Frontend не загружает историю при открытии группы | UI |
| Socket.IO broadcast работает | Эмит срабатывает правильно | Socket.IO ✓ |

---

## ФАЗЫ И ИСТОРИЯ

- **Phase 56:** Group Chat Manager создана
- **Phase 57.7:** select_responding_agents() с smart selection + @mentions
- **Phase 80.4:** MCP agents in group chat - добавлены REST endpoints
- **Phase 80.6:** MCP agent isolation - агенты без @mention не отвечают
- **Phase 80.7:** Reply routing - поддержка reply_to_agent

**ПРОБЛЕМА:** Phase 80.4 добавил REST endpoint, но не полностью интегрировал с Phase 80.6 логикой.

---

## СТАТУС ИСПРАВЛЕНИЯ

- [x] Реализовать Solution 1: Вызов select_responding_agents() в MCP endpoint (Phase 86 - DONE)
- [ ] Реализовать Solution 2: Документировать Phase 80.6 поведение
- [ ] Реализовать Solution 3: Frontend загрузить history на открытии
- [ ] Тестирование с curl и UI
- [ ] Update docs/START_HERE с примерами MCP messaging

### Phase 86 Implementation Details (2026-01-21)

**Fixed:** MCP endpoint now calls `select_responding_agents()` and triggers agents on @mentions.

**Changes in `/src/api/routes/debug_routes.py`:**
1. Re-enabled imports: `get_orchestrator` from `components_init`, `get_agent_prompt` from `role_prompts`
2. Removed disabled code block, now calls `select_responding_agents()` directly
3. Agent calling logic was already present and working - just needed the trigger enabled

**Note:** Phase 80.6 isolation still applies - if MCP sends AS an agent (sender_id starts with @) WITHOUT explicit @mention in content, no agents will respond. This is intentional to prevent infinite loops.

---

## ФАЙЛЫ ЗАТРОНУТЫ

1. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/debug_routes.py` (1142-1228)
2. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/group_chat_manager.py` (159-186)
3. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py` (354-687)
4. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/group_routes.py` (121-127)
5. Frontend code (неизвестно, нужно найти)

---

## ВЫВОДЫ

**MCP messaging архитектура неполная:**
- ✓ Сохранение в БД работает
- ✓ Socket.IO broadcast работает
- ✓ Логика выбора агентов написана
- ✗ Связь между MCP endpoint и логикой агентов разорвана
- ✗ Phase 80.6 изоляция документирована в коде но не очевидна

**Solution:** Скопировать логику из `handle_group_message()` Socket.IO handler в `send_group_message_from_mcp()` REST endpoint.
