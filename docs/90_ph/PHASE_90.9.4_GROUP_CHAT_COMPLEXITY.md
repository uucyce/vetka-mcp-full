# PHASE 90.9.4: Анализ сложности группового чата vs сольного чата

**Дата:** 2026-01-23
**Статус:** Исследовательский отчёт
**Язык:** Русский
**Тип:** Анализ архитектуры и зависимостей

---

## Проблема

Групповой чат имеет избыточную сложность по сравнению с рабочим сольным чатом. Требуется:

1. Идентифицировать ВСЕ файлы, вовлечённые в поток сообщений группового чата
2. Сравнить со входом сольного чата
3. Найти, где была добавлена сложность
4. Нанести на карту цепь эндпоинтов для групповых сообщений

---

## ЧАСТЬ I: Поток сольного чата (БАЗОВЫЙ/ПРОСТОЙ)

### Краткое резюме

**Вход:** POST `/api/chat` → FastAPI Route → Orchestrator → LLM
**Выход:** JSON response
**Сложность:** НИЗКАЯ (одна REST API, прямой контроль потока)

### Архитектура сольного чата

```
USER
  ↓
POST /api/chat (HTTP)
  ↓
src/api/routes/chat_routes.py::api_chat()
  ↓
Условная логика:
  - Если model_override == "mcp/*" → перенаправить в team_messages буфер
  - Если Hostess доступен → фаза маршрутизации (quick_answer/clarify/search/agent_call/chain_call)
  - Если orchestrator доступен → параллельная обработка агентов
  - Иначе → API Gateway v2 или Ollama fallback
  ↓
Memory persistence (triple_write в Weaviate + Qdrant)
  ↓
EvalAgent scoring
  ↓
Возврат response dict
```

### Основные эндпоинты сольного чата

| Эндпоинт | Файл | Назначение |
|----------|------|-----------|
| `GET /api/chat/history` | `chat_routes.py` | Получить историю для узла |
| `POST /api/chat/clear-history` | `chat_routes.py` | Очистить историю |
| **`POST /api/chat`** | `chat_routes.py` | **ГЛАВНЫЙ УНИВЕРСАЛЬНЫЙ ЭНДПОИНТ** |

### Используемые компоненты

```python
# src/api/routes/chat_routes.py
- get_memory_manager()        # Weaviate memory
- get_orchestrator()          # LLM агент оркестратор
- get_hostess()              # Маршрутизатор решений
- get_model_for_task()       # Выбор модели
- is_model_banned()          # Проверка запрета
- model_router               # Маршрутизатор моделей v2
- api_gateway                # API Gateway v2
- qdrant_manager             # Qdrant векторная БД
- EvalAgent                  # Оценка качества ответов
```

---

## ЧАСТЬ II: Поток группового чата (УСЛОЖНЁННЫЙ/МНОГОУРОВНЕВЫЙ)

### Краткое резюме

**Вход:** Socket.IO `group_message` → WebSocket event handler → Orchestrator → LLM
**Выход:** Множество Socket.IO events (stream_start, stream_end, group_message, typing, error)
**Сложность:** ОЧЕНЬ ВЫСОКАЯ (WebSocket, async event chain, multi-agent, MCP integration)

### Архитектура группового чата

```
USER
  ↓
Socket.IO: group_message event
  ↓
src/api/handlers/group_message_handler.py::handle_group_message()
  ├─ 1. Сохранить пользовательское сообщение
  ├─ 2. Транслировать сообщение в room (group_{group_id})
  ├─ 3. Парсить @mentions
  ├─ 4. Уведомить MCP агентов (browser_haiku, claude_code)
  │  └─ notify_mcp_agents() → Socket event 'mcp_mention' + debug_routes.team_messages буфер
  ├─ 5. Сохранить в chat_history (Chat History Manager)
  ├─ 6. Получить Group объект (для smart reply decay - фаза 80.28)
  ├─ 7. Выбрать отвечающих агентов:
  │  └─ manager.select_responding_agents()
  │     ├─ Проверка reply_to (фаза 80.7)
  │     ├─ Проверка @mentions
  │     ├─ Smart reply decay (фаза 80.28)
  │     ├─ /solo, /team, /round команды
  │     ├─ Ключевое слово интеллектуальный выбор
  │     └─ Значение по умолчанию (админ > первый worker)
  ├─ 8. Для КАЖДОГО агента в цепи:
  │  ├─ Эмит 'group_typing' сигнал
  │  ├─ Эмит 'group_stream_start'
  │  ├─ Получить system_prompt от role_prompts
  │  ├─ Собрать контекст из истории + previous_outputs
  │  ├─ Вызвать orchestrator.call_agent()
  │  ├─ Сохранить ответ агента
  │  ├─ Эмит 'group_stream_end'
  │  ├─ Транслировать 'group_message' в room
  │  ├─ Сохранить в chat_history
  │  ├─ Отслеживать last_responder для smart reply (фаза 80.28)
  │  ├─ Парсить @mentions в ответе агента
  │  └─ Если @mentions найдены → динамически добавить к participants_to_respond (фаза 57.8)
  │     (for loop переделан на while для этого!)
  └─ 9. [УДАЛЕНО] Было: Hostess summary (фаза 57.8.2) - слишком медленно
```

### Основные эндпоинты группового чата

| Метод | Эндпоинт | Назначение |
|-------|----------|-----------|
| GET | `/api/groups` | Список всех групп |
| POST | `/api/groups` | Создать группу |
| GET | `/api/groups/{group_id}` | Получить группу по ID |
| POST | `/api/groups/{group_id}/participants` | Добавить участника |
| DELETE | `/api/groups/{group_id}/participants/{agent_id}` | Удалить участника |
| PATCH | `/api/groups/{group_id}/participants/{agent_id}/model` | Обновить модель участника |
| PATCH | `/api/groups/{group_id}/participants/{agent_id}/role` | Обновить роль участника |
| GET | `/api/groups/{group_id}/messages` | Получить сообщения группы |
| POST | `/api/groups/{group_id}/messages` | Отправить сообщение в группу |
| POST | `/api/groups/{group_id}/tasks` | Назначить задачу |
| POST | `/api/groups/{group_id}/models/add-direct` | Добавить модель напрямую (фаза 80.19) |

### Socket.IO события (WebSocket)

| Событие | Направление | Назначение |
|---------|-------------|-----------|
| `join_group` | Client → Server | Присоединиться к комнате группы |
| `leave_group` | Client → Server | Покинуть комнату группы |
| `group_message` | ↔️ Двустороннее | Отправить/получить сообщение |
| `group_typing` | ↔️ Двустороннее | Индикатор печатания |
| `group_stream_start` | Server → Client | Начало потока ответа от агента |
| `group_stream_end` | Server → Client | Конец потока ответа от агента |
| `group_joined_ack` | Server → Client | Подтверждение присоединения |
| `group_error` | Server → Client | Ошибка обработки |
| `mcp_mention` | Server → Client (MCP Extension) | Уведомление о @mention для MCP агентов |

### Используемые компоненты группового чата

```python
# src/api/handlers/group_message_handler.py

1. GroupChatManager (src/services/group_chat_manager.py)
   - get_group_chat_manager()
   - select_responding_agents()
   - send_message()
   - get_messages()
   - get_group()
   - get_group_object()

2. Orchestrator (src/initialization/components_init.py)
   - call_agent()

3. Chat History Manager (src/chat/chat_history_manager.py)
   - get_chat_history_manager()
   - get_or_create_chat()
   - add_message()

4. Role Prompts (src/agents/role_prompts.py)
   - get_agent_prompt()
   - PM_SYSTEM_PROMPT
   - DEV_SYSTEM_PROMPT
   - QA_SYSTEM_PROMPT
   - ARCHITECT_SYSTEM_PROMPT
   - RESEARCHER_SYSTEM_PROMPT

5. Debug Routes (src/api/routes/debug_routes.py)
   - team_messages (буфер)
   - KNOWN_AGENTS (справочник)

6. Socket.IO Server instance
   - emit()
   - enter_room()
   - leave_room()
```

---

## ЧАСТЬ III: Сравнительный анализ

### Таблица сложности

| Критерий | Сольный чат | Групповой чат | Множитель |
|----------|-----------|---------------|-----------|
| Главных эндпоинтов | 1 | 11 | 11× |
| Socket.IO событий | 0 | 8 | ∞ |
| Управляемых агентов | 1-2 | 3-10 | 5-10× |
| Слоёв обработки | 2 | 9+ | 4-5× |
| Состояния отслеживания | 0 | 3 (last_responder, decay, reply_to) | ∞ |
| Контекстных пассов | 1 | 5+ (история, previous_outputs, pinned_files, group_object, reply_context) | 5× |
| Объектов в памяти | Chat object | Group + Participants + Messages + Context | 10× |

### Основные источники сложности

#### 1. **WebSocket vs HTTP**
```
HTTP (сольный):
  - Request/Response простой
  - Состояние управляется клиентом
  - Нет room-based broadcasting

WebSocket (групповой):
  - Множество event types
  - Room-based messaging (group_{group_id})
  - Требуется async управление состояния
  - Требуется правильный skip_sid для избежания дублирования
```

#### 2. **Multi-Agent Chain vs Single LLM**
```
Сольный:
  - Один вызов LLM
  - Один ответ

Групповой:
  - While loop (может быть до 10 агентов)
  - Каждый агент видит previous_outputs от других
  - Агент может @mention других → динамическое добавление в цепь
  - Отслеживание last_responder для smart reply
  - Отслеживание decay counter для smart reply decay
```

#### 3. **MCP Agent Integration**
```
Групповой добавляет:
  - notify_mcp_agents() функция
  - Парсинг @mentions специально для MCP (browser_haiku, claude_code)
  - Отправка в debug_routes.team_messages буфер
  - Socket.IO 'mcp_mention' события
```

#### 4. **Persistence Layer**
```
Сольный:
  - Weaviate (triple_write)
  - Qdrant (optional)

Групповой:
  - GroupChatManager.send_message() (в памяти + JSON file)
  - ChatHistoryManager.add_message() (для каждого агента ответа)
  - Atomic JSON write (data/groups.json)
  - Потенциально: Weaviate/Qdrant (не используется в текущем flow)
```

#### 5. **Agent Selection Logic**
```
Сольный:
  - Прямой вызов одной модели
  - Или Hostess маршрутизация (но не в group flow)

Групповой select_responding_agents():
  1. Проверка reply_to (фаза 80.7)
  2. Проверка @mentions с СЛОЖНЫМ matching:
     - Model ID exact match (содержит '-', '/', '.')
     - Simple name substring match (@PM, @Dev)
     - Case-insensitive
  3. Smart reply decay (фаза 80.28):
     - Для MCP агентов: decay < 2
     - Для пользователя: decay < 1
  4. Commands: /solo, /team, /round
  5. Ключевые слова scoring (PM, Architect, Dev, QA)
  6. Default fallback
```

#### 6. **Reply Chain Context**
```
Сольный:
  - Контекст = история файла/узла

Групповой:
  previous_outputs = {}

  Каждый агент в цепи видит:
  - system_prompt (role-specific)
  - group.name
  - recent_messages (limit=5)
  - previous_outputs (от уже ответивших агентов)
  - current request

  Это позволяет цепочке: PM → Architect → Dev → QA
  где каждый видит то, что сказал предыдущий
```

---

## ЧАСТЬ IV: Где была добавлена сложность?

### Фаза-за-фазой Анализ Усложнения

| Фаза | Добавленная сложность | Файл |
|------|---------------------|------|
| **56** | GroupChatManager, Group model, Socket.IO handlers | `group_chat_manager.py`, `group_message_handler.py` |
| **56.2** | Memory management (LRU, cleanup, bounded deque) | `group_chat_manager.py` |
| **56.4** | Async locks, periodic cleanup task | `group_chat_manager.py` |
| **57.4** | Orchestrator integration (вместо direct HTTP) | `group_message_handler.py` |
| **57.7** | Intelligent agent selection (keywords, scoring) | `group_chat_manager.py::select_responding_agents()` |
| **57.8** | Hostess router (теперь УДАЛЁН - слишком медленно) | `group_message_handler.py` |
| **57.8.2** | Dynamic @mention from agent responses → while loop | `group_message_handler.py::handle_group_message()` (line 646-654) |
| **74.8** | Chat history persistence for each agent response | `group_message_handler.py` |
| **80.6** | MCP agent isolation (no auto-response cascade) | `group_chat_manager.py::select_responding_agents()` |
| **80.7** | Reply routing to original agent (reply_to_id) | `group_message_handler.py`, `group_chat_manager.py` |
| **80.11** | Pinned files context in group messages | `group_message_handler.py` |
| **80.13** | MCP @mention routing (browser_haiku, claude_code) | `group_message_handler.py::notify_mcp_agents()` |
| **80.19** | Direct model addition without role slots | `group_routes.py::add_model_direct()` |
| **80.28** | Smart reply with decay tracking (last_responder_id, decay counter) | `group_chat_manager.py`, `group_message_handler.py` |
| **80.31** | Advanced regex for full model IDs in @mentions | `group_chat_manager.py::select_responding_agents()` |
| **82** | Model reassignment and role changes post-creation | `group_message_handler.py`, `group_routes.py` |

### Ключевые точки Усложнения

**Точка 1: WebSocket Event Handler Chain** (фаза 56)
```
Вместо простого HTTP Request/Response:
- Socket.IO emit/broadcast множество событий
- Требуется room management (group_{group_id})
- Требуется async state management
```

**Точка 2: Multi-Agent While Loop** (фаза 57.8.2)
```
Вместо:
  for participant in participants_to_respond:
    # обработать

Теперь:
  while processed_idx < len(participants_to_respond) and processed_idx < max_agents:
    # обработать
    # может добавить нового participant во время итерации!
```
Это нужно для динамического @mention от агентов, но ОЧЕНЬ усложняет отладку.

**Точка 3: Smart Reply Decay** (фаза 80.28)
```
Требуется отслеживание на Group object:
- last_responder_id
- last_responder_decay counter

Добавляет estado tracking + условная логика в select_responding_agents():
- Если MCP отправитель + no @mention + decay < 2 → reply to last_responder
- Если пользователь + no @mention + decay < 1 → reply to last_responder
```

**Точка 4: MCP Integration** (фаза 80.13)
```
notify_mcp_agents() добавляет:
- Парсинг специальных имён агентов (browser_haiku, claude_code)
- Socket.IO 'mcp_mention' события
- Буфер debug_routes.team_messages
- Метаданные контекста группы
```

---

## ЧАСТЬ V: Цепь Эндпоинтов для Группового Сообщения

### Полный Call Stack для GROUP_MESSAGE

```
1. CLIENT (Browser/WebSocket)
   └─ socket.emit('group_message', {group_id, sender_id, content, reply_to, pinned_files})

2. SOCKET.IO SERVER
   └─ src/api/handlers/group_message_handler.py::handle_group_message()

      2.1 Валидация и восстановление
          └─ manager.get_group(group_id)
          └─ manager.get_group_object(group_id)  [фаза 80.28]

      2.2 Сохранить пользовательское сообщение
          └─ manager.send_message(group_id, sender_id='user', content, metadata)
             └─ GroupChatManager.send_message() [LOCK]
                ├─ parse_mentions(content)
                ├─ GroupMessage(id, group_id, sender_id, content, mentions, type)
                ├─ deque.append(message)
                ├─ group.last_activity = now
                ├─ save_to_json() [ATOMIC WRITE to data/groups.json]
                └─ return GroupMessage

      2.3 Транслировать пользовательское сообщение
          └─ sio.emit('group_message', user_message.to_dict(), room=f'group_{group_id}')

      2.4 Increment decay (если sender_id == 'user')
          └─ group_object.last_responder_decay += 1 [фаза 80.28]

      2.5 Парсить @mentions и уведомить MCP агентов
          └─ notify_mcp_agents() [фаза 80.13]
             ├─ Парсить @mentions из content
             ├─ Найти MCP agents (browser_haiku, claude_code)
             ├─ sio.emit('mcp_mention', {...}, namespace='/')
             └─ Добавить в team_messages буфер [для debug_routes]

      2.6 Сохранить в Chat History
          └─ chat_history.get_or_create_chat(display_name=group_name, context_type='group')
          └─ chat_history.add_message(chat_id, {role, content, agent, metadata})

      2.7 Получить Orchestrator
          └─ orchestrator = get_orchestrator()

      2.8 Найти оригинального агента (если reply_to)
          └─ Если reply_to_id:
             └─ Поиск в manager.get_messages() для sender_id
             └─ reply_to_agent = sender_id (если начинается с '@')

      2.9 Выбрать отвечающих агентов
          └─ manager.select_responding_agents(
               content=content,
               participants=group.participants,
               sender_id=sender_id,
               reply_to_agent=reply_to_agent,  [фаза 80.7]
               group=group_object  [фаза 80.28]
             )

             2.9.1 Логика выбора:
                   ├─ Если reply_to_agent: вернуть [agent]
                   ├─ Если @mentions: найти participant по display_name/agent_id/model_id
                   │  (Сложное matching: model IDs exact, names substring) [фаза 80.31]
                   ├─ Если @mentions но НЕ найден: вернуть [] (возможно MCP)
                   ├─ Если sender - MCP + decay < 2: вернуть [last_responder]
                   ├─ Если sender - user + decay < 1: вернуть [last_responder]
                   ├─ Если sender - agent без @mention: вернуть [] (no cascade)
                   ├─ /solo, /team, /round команды
                   ├─ Ключевое слово scoring
                   └─ Default: admin или first_worker

      2.10 While loop: обработать каждого агента в цепи (может расти!)

           while processed_idx < len(participants_to_respond) && processed_idx < 10:
               participant = participants_to_respond[processed_idx]

               2.10.1 Эмит typing indicator
                      └─ sio.emit('group_typing', {group_id, agent_id}, room=f'group_{group_id}')

               2.10.2 Эмит stream start
                      └─ sio.emit('group_stream_start', {id, group_id, agent_id, model}, room)

               2.10.3 Получить system_prompt
                      └─ get_agent_prompt(agent_type)  [PM, Dev, QA, Architect, Researcher]

               2.10.4 Собрать контекст
                      ├─ recent_messages = manager.get_messages(group_id, limit=5)
                      ├─ Построить prompt с:
                      │  ├─ system_prompt (role-specific)
                      │  ├─ group.name
                      │  ├─ recent_messages
                      │  ├─ previous_outputs (from earlier agents in chain)
                      │  └─ current request

               2.10.5 Вызвать Orchestrator
                      └─ result = await orchestrator.call_agent(
                            agent_type=agent_type,
                            model_id=model_id,
                            prompt=prompt,
                            context={group_id, group_name, agent_id, display_name}
                         )
                         [TIMEOUT: 120s]

               2.10.6 Сохранить ответ агента
                      └─ agent_message = manager.send_message(
                            group_id, sender_id=agent_id, content=response_text,
                            message_type='response', metadata={'in_reply_to': user_message.id}
                         )
                         └─ (also save_to_json(), LRU tracking)

               2.10.7 Эмит stream end
                      └─ sio.emit('group_stream_end', {id, group_id, agent_id, full_message, metadata}, room)

               2.10.8 Транслировать агентское сообщение
                      └─ sio.emit('group_message', agent_message.to_dict(), room=f'group_{group_id}')

               2.10.9 Отслеживать last_responder (фаза 80.28)
                      └─ group_object.last_responder_id = agent_id
                      └─ group_object.last_responder_decay = 0 (reset)

               2.10.10 Сохранить в Chat History
                       └─ chat_history.add_message(chat_id, {role: 'assistant', content, agent, model})

               2.10.11 ДИНАМИЧЕСКОЕ РАСШИРЕНИЕ ЦЕПИ (фаза 57.8.2)
                       └─ Парсить @mentions из response
                       └─ Для каждого mentioned_name:
                          ├─ Если self-mention или уже ответил: skip
                          ├─ Найти mentioned_participant в group.participants
                          │  (match by display_name, agent_id, или display_name prefix)
                          └─ Если найден и не observer:
                             └─ Если уже в queue: skip
                             └─ Иначе: participants_to_respond.append(mentioned_participant)

               2.10.12 Error handling
                       └─ Catch исключения
                       └─ Эмит 'group_stream_end' с error
                       └─ Сохранить error message

               processed_idx += 1

      2.11 [УДАЛЕНО] post_hostess_summary() - фаза 57.8.2
           (была слишком медленная, теперь только passive context)

3. RESPONSE
   └─ Клиент получает multiple Socket.IO события:
      ├─ group_message (пользовательское сообщение)
      ├─ group_typing (индикатор)
      ├─ group_stream_start
      ├─ group_message (для каждого агента в цепи)
      ├─ group_stream_end
      └─ (Возможно) mcp_mention (для MCP агентов)
```

### REST API эндпоинты (для управления группами)

```
Управление группами:
  GET    /api/groups
  POST   /api/groups                          [CreateGroupRequest]
  GET    /api/groups/{group_id}
  DELETE /api/groups/{group_id}               [если реализовано]

Управление участниками:
  POST   /api/groups/{group_id}/participants
           └─ [AddParticipantRequest]
  DELETE /api/groups/{group_id}/participants/{agent_id}
  PATCH  /api/groups/{group_id}/participants/{agent_id}/model
           └─ [UpdateParticipantModelRequest]
  PATCH  /api/groups/{group_id}/participants/{agent_id}/role
           └─ [UpdateParticipantRoleRequest]

Сообщения:
  GET    /api/groups/{group_id}/messages
  POST   /api/groups/{group_id}/messages      [SendMessageRequest]

Задачи:
  POST   /api/groups/{group_id}/tasks        [AssignTaskRequest]

Модели (фаза 80.19):
  POST   /api/groups/{group_id}/models/add-direct
           └─ [AddModelDirectRequest]
```

---

## ЧАСТЬ VI: Зависимости и Граф Файлов

### Слои архитектуры

```
┌─────────────────────────────────────────────────────────┐
│ PRESENTATION LAYER                                      │
├─────────────────────────────────────────────────────────┤
│ - Socket.IO Event Handlers (group_message_handler.py)  │
│ - FastAPI Routes (group_routes.py)                     │
│ - Debug Routes (debug_routes.py - team_messages)       │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ BUSINESS LOGIC LAYER                                    │
├─────────────────────────────────────────────────────────┤
│ - GroupChatManager (group_chat_manager.py)             │
│ - Agent Selection (select_responding_agents)           │
│ - Persistence (save_to_json, load_from_json)           │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ ORCHESTRATION & INTEGRATION LAYER                       │
├─────────────────────────────────────────────────────────┤
│ - Orchestrator (orchestration/orchestrator.py)         │
│ - Hostess Router (agents/hostess_agent.py)             │
│ - Chat History Manager (chat/chat_history_manager.py)  │
│ - Role Prompts (agents/role_prompts.py)               │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ DATA MODELS & ENTITIES LAYER                            │
├─────────────────────────────────────────────────────────┤
│ - Group, GroupMessage, GroupParticipant (dataclasses) │
│ - GroupRole (enum)                                      │
│ - GroupChatManager state (_groups, _agent_groups)      │
└─────────────────────────────────────────────────────────┘
```

### Зависимости по файлам

#### Основные (CORE)

```
src/services/group_chat_manager.py
├── Используется:
│   ├─ src/api/handlers/group_message_handler.py (основной)
│   ├─ src/api/routes/group_routes.py (REST API)
│   ├─ src/api/routes/debug_routes.py (для инспекции)
│   └─ main.py (инициализация singleton)
├── Зависит от:
│   ├─ asyncio (async locks, tasks)
│   ├─ dataclasses (Group, GroupMessage, GroupParticipant, GroupRole)
│   ├─ enum (GroupRole)
│   ├─ deque (bounded message history)
│   ├─ pathlib (JSON file I/O)
│   └─ json (persistence)
└── Экспортирует:
    ├─ GroupChatManager (singleton)
    ├─ Group, GroupMessage, GroupParticipant, GroupRole
    └─ get_group_chat_manager()
```

#### Handler (WebSocket Events)

```
src/api/handlers/group_message_handler.py
├── Используется:
│   └─ src/api/handlers/__init__.py::register_all_handlers()
│      └─ main.py::setup() → app.state.sio
├── Зависит от:
│   ├─ asyncio
│   ├─ uuid (message IDs)
│   ├─ time (timestamps)
│   ├─ logging
│   ├─ json
│   ├─ re (regex for @mentions)
│   ├─ src/services/group_chat_manager (GroupChatManager)
│   ├─ src/initialization/components_init (get_orchestrator)
│   ├─ src/chat/chat_history_manager (get_chat_history_manager)
│   ├─ src/agents/role_prompts (get_agent_prompt, *_SYSTEM_PROMPT)
│   └─ src/api/routes/debug_routes (team_messages buffer, KNOWN_AGENTS)
└── Экспортирует:
    ├─ register_group_message_handler()
    ├─ notify_mcp_agents()
    ├─ route_through_hostess() [фаза 57.8, используется ли?]
    ├─ post_hostess_summary() [фаза 57.8, используется ли?]
    ├─ set_socketio()
    └─ get_socketio()
```

#### REST API (HTTP Endpoints)

```
src/api/routes/group_routes.py
├── Используется:
│   └─ main.py::app.include_router(router) [в setup()]
├── Зависит от:
│   ├─ fastapi
│   ├─ pydantic (BaseModel)
│   ├─ src/services/group_chat_manager (get_group_chat_manager, GroupParticipant, GroupRole)
├── Определяет:
│   ├─ CreateGroupRequest
│   ├─ AddParticipantRequest
│   ├─ SendMessageRequest
│   ├─ AssignTaskRequest
│   ├─ UpdateParticipantModelRequest
│   ├─ UpdateParticipantRoleRequest
│   └─ AddModelDirectRequest
└── Экспортирует:
    └─ router (APIRouter для /api/groups)
```

#### Debug/Inspection

```
src/api/routes/debug_routes.py
├── Глобальные переменные:
│   ├─ team_messages = []  [буфер для MCP @mentions]
│   └─ KNOWN_AGENTS = {...}
├── Использует:
│   └─ src/services/group_chat_manager (для инспекции групп)
└── Используется:
    ├─ src/api/handlers/group_message_handler (write to team_messages)
    └─ src/api/routes/chat_routes (write to team_messages)
```

#### Integration Points

```
src/agents/role_prompts.py
├─ Используется:
│  └─ src/api/handlers/group_message_handler (get_agent_prompt, *_SYSTEM_PROMPT)
└─ Определяет system prompts для:
   ├─ PM_SYSTEM_PROMPT
   ├─ DEV_SYSTEM_PROMPT
   ├─ QA_SYSTEM_PROMPT
   ├─ ARCHITECT_SYSTEM_PROMPT
   └─ RESEARCHER_SYSTEM_PROMPT

src/chat/chat_history_manager.py
├─ Используется:
│  └─ src/api/handlers/group_message_handler (get_chat_history_manager, add_message)
└─ Управляет persistence chat history

src/initialization/components_init.py
├─ Используется:
│  └─ src/api/handlers/group_message_handler (get_orchestrator)
└─ Инициализирует Orchestrator instance

src/api/handlers/__init__.py
├─ Используется:
│  └─ main.py (register_all_handlers)
└─ Координирует регистрацию всех handlers
   └─ register_group_message_handler(sio, app)
```

---

## ЧАСТЬ VII: Список ВСЕХ Зависимых Файлов

### Прямые зависимости (импортируют групповой код)

```
1. /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/main.py
   - Инициализирует GroupChatManager
   - Регистрирует handlers
   - Управляет жизненным циклом

2. /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/__init__.py
   - Регистрирует group_message_handler

3. /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/debug_routes.py
   - Использует GroupChatManager для инспекции
   - Содержит team_messages буфер

4. /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/agents/tools.py
   - Импортирует get_socketio из group_message_handler
   - Может эмитить Socket.IO события

5. /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py
   - Возможно использует group события для MCP интеграции
```

### Косвенные зависимости (используются основным кодом группового чата)

```
6. /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/group_chat_manager.py
   [CORE - основной сервис]

7. /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py
   [CORE - WebSocket handlers]

8. /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/group_routes.py
   [REST API endpoints]

9. /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/agents/role_prompts.py
   - get_agent_prompt()
   - System prompts для каждой роли

10. /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/chat/chat_history_manager.py
    - Сохранение истории каждого ответа группы

11. /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/initialization/components_init.py
    - get_orchestrator()

12. /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/orchestrator.py
    - call_agent()
    - LLM orchestration

13. /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/agents/hostess_agent.py
    - [Потенциально используется в route_through_hostess - но УДАЛЁН в фаза 57.8.2]
```

---

## ВЫВОДЫ И РЕКОМЕНДАЦИИ

### Почему группой чат НАМНОГО сложнее

1. **WebSocket Event Model** вместо простого Request/Response
   - Требуется async state management
   - Требуется room-based broadcasting
   - Требуется правильное управление sid

2. **Multi-Agent While Loop** с динамическим расширением цепи
   - Один агент может @mention другого
   - While loop может расти во время итерации
   - Нужна максимум 10 агентов для безопасности

3. **Smart Reply Decay Tracking** (фаза 80.28)
   - Отслеживание last_responder_id
   - Отслеживание decay counter
   - Условная логика для MCP vs User messages

4. **MCP Integration**
   - Специальная обработка browser_haiku, claude_code
   - Отправка в team_messages буфер
   - Socket.IO 'mcp_mention' события

5. **Context Multiplexing**
   - Каждый агент видит previous_outputs от других
   - Требуется сборка контекста для каждого агента
   - Поддержка pinned_files, reply_to, metadata

### Рекомендации по упрощению

1. **Рассмотреть unified message gateway вместо двух путей (REST + WebSocket)**
   - Текущий сольный чат использует REST /api/chat
   - Групповой использует WebSocket group_message
   - Можно обобщить?

2. **Упростить agent selection logic**
   - Текущий select_responding_agents() очень сложный (80+ строк)
   - Может быть декомпозирован на отдельные функции per-strategy

3. **Удалить неиспользуемый код**
   - route_through_hostess() - используется ли?
   - post_hostess_summary() - был удалён в 57.8.2

4. **Извлечь MCP handling в отдельный модуль**
   - notify_mcp_agents() могла бы быть отдельным файлом
   - Это упростит основной handler

5. **Рассмотреть Event Sourcing паттерн**
   - Вместо множества вызовов save_to_json()
   - Сохранять события в event log
   - Воспроизводить состояние при необходимости

---

## ПРИЛОЖЕНИЕ: Полный Список Файлов Зависимостей

### **CORE ГРУППОВОГО ЧАТА (ОБЯЗАТЕЛЬНЫЕ)**

```
✓ /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/group_chat_manager.py
  - GroupChatManager (singleton)
  - Group, GroupMessage, GroupParticipant (dataclasses)
  - GroupRole (enum)

✓ /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py
  - handle_group_message (main WebSocket handler)
  - handle_join_group, handle_leave_group
  - handle_group_typing
  - notify_mcp_agents()
  - route_through_hostess()
  - post_hostess_summary()
  - register_group_message_handler()

✓ /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/group_routes.py
  - list_groups, create_group, get_group
  - add_participant, remove_participant
  - update_participant_model, update_participant_role
  - get_messages, send_message
  - assign_task
  - add_model_direct
  - router (FastAPI)
```

### **ИНТЕГРАЦИЯ И КООРДИНАЦИЯ**

```
✓ /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/main.py
  - GroupChatManager initialization
  - Lifecycle management (startup/shutdown)
  - Cleanup task scheduling

✓ /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/__init__.py
  - register_group_message_handler() call
  - Handler coordination

✓ /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/initialization/components_init.py
  - get_orchestrator()
  - Component initialization

✓ /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/orchestrator.py
  - Orchestrator class
  - call_agent() method
```

### **ПОДДЕРЖКА И ИНТЕГРАЦИЯ**

```
✓ /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/agents/role_prompts.py
  - get_agent_prompt(agent_type)
  - PM_SYSTEM_PROMPT, DEV_SYSTEM_PROMPT, QA_SYSTEM_PROMPT
  - ARCHITECT_SYSTEM_PROMPT, RESEARCHER_SYSTEM_PROMPT

✓ /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/chat/chat_history_manager.py
  - get_chat_history_manager()
  - get_or_create_chat()
  - add_message()

✓ /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/debug_routes.py
  - team_messages (global buffer)
  - KNOWN_AGENTS (registry)
  - MCP inspection endpoints

✓ /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/agents/tools.py
  - get_socketio() import (for artifact emission)
```

### **MCP И ВНЕШНИЕ АГЕНТЫ**

```
✓ /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py
  - MCP agent communication
  - Возможная интеграция с group events

✓ /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/llm_call_tool.py
  - LLM calling through MCP
```

### **ДАННЫЕ И СОСТОЯНИЕ**

```
✓ /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/groups.json
  - Persistence file (atomic write)
  - Сохраняется после каждой операции:
    - create_group(), add_participant(), remove_participant()
    - update_participant_model(), update_participant_role()
    - send_message()

✓ /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/chat_history.json
  - Chat history storage
  - Parallel persistence with GroupChatManager
```

---

**ДОКУМЕНТ ЗАВЕРШЁН**

Дата создания: 2026-01-23
Версия: 1.0
Язык: Русский
Статус: Завершено
