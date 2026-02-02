# Аудит Routing Phase 108 - Срочный Audit Групповых Чатов

**Дата:** 2026-02-02
**Автор:** Claude Code Audit
**Статус:** Не исправляется - маркеры и отчет для Sonnet

---

## 1. FALLBACK ПРОБЛЕМЫ

### Fallback на ChatGPT/OpenRouter (ОПАСНО!)

| Файл | Строка | Проблема | Фикс |
|------|--------|----------|------|
| `/src/elisya/provider_registry.py` | 1139-1154 | **MARKER_93.10_FALLBACK**: XAI API fails → автоматический fallback на OpenRouter | Убрать автоматический fallback, только когда explicitly запрошено |
| `/src/elisya/provider_registry.py` | 1155-1182 | **MARKER_93.10_FALLBACK**: Любой HTTP error → fallback на OpenRouter | Логировать но НЕ auto-rotate без явного запроса |
| `/src/elisya/provider_registry.py` | 1220-1225 | Общий exception handler → fallback на OpenRouter | Пробросить ошибку вверх, не скрывать |
| `/src/elisya/provider_registry.py` | 1088-1154 | **MARKER_93.10**: OpenRouter как fallback для ВСЕХ провайдеров | ПРОБЛЕМА: agents вызываются только когда @упомянули, но fallback может переключить неправильно |

### OpenAI/Anthropic Key Rotation (Phase 93.4)

| Файл | Строка | Проблема | Фикс |
|------|--------|----------|------|
| `/src/elisya/provider_registry.py` | 210-235 | **OpenAI key rotation** на 401/402/403/429 | ✅ Правильно - key rotation с 24h cooldown |
| `/src/elisya/provider_registry.py` | 344-369 | **Anthropic key rotation** на 401/402/403/429 | ✅ Правильно - ротация ключей |
| `/src/elisya/provider_registry.py` | 494-520 | **Google key rotation** на 401/403/429 | ✅ Правильно - ротация ключей |

### Ollama Fallback (Phase 80.5)

| Файл | Строка | Проблема | Фикс |
|------|--------|----------|------|
| `/src/elisya/provider_registry.py` | 691-706 | **Ollama tool error** → retry без tools | ⚠️ ПРАВИЛЬНО для инструментов, но нужна логика когда модель NOT найдена |
| `/src/elisya/provider_registry.py` | 654-657 | Если модель NOT найдена → use default `deepseek-llm:7b` | ⚠️ Может быть не установлена! Нужен fallback на list доступных |

---

## 2. ROUTING ЛОГИКА - ДЕТАЛЬНЫЙ АНАЛИЗ

### 2.1 Точка входа: Group Message Handler

**Файл:** `/src/api/handlers/group_message_handler.py:679-688`

```python
# MARKER_ROUTING_LOGIC: Agent selection entry point
participants_to_respond = await manager.select_responding_agents(
    content=content,
    participants=group.get("participants", {}),
    sender_id=sender_id,
    reply_to_agent=reply_to_agent,
    group=group_object,  # Phase 80.28
)
```

**Правила:**
1. ✅ @mention - явное упоминание агента
2. ✅ reply_to_agent - ответ на сообщение
3. ✅ last_responder_decay - smart reply
4. ✅ /solo, /team, /round команды
5. ✅ Keyword-based selection
6. ✅ Default selection (admin > first worker)

### 2.2 Реализация: select_responding_agents

**Файл:** `/src/services/group_chat_manager.py:179-418`

#### Правило 1: Reply Routing ✅

```python
# Phase 80.7: Reply routing
if reply_to_agent:
    reply_to_normalized = reply_to_agent.lower().lstrip('@')
    for pid, p in participants.items():
        agent_id_normalized = p.get('agent_id', '').lower().lstrip('@')
        if agent_id_normalized == reply_to_normalized:
            if p.get('role') != 'observer':
                return [p]  # ✅ ПРАВИЛЬНО
```

**Статус:** ✅ РАБОТАЕТ - reply корректно маршрутизируется

#### Правило 2: @Mention Parsing ✅

```python
# Line 235-268: @mention detection
all_mentions_raw = re.findall(r'@([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)', content)
# Phase 80.31: Fixed regex to capture full model IDs
```

**Статус:** ✅ ПРАВИЛЬНО - регекс захватывает полные model IDs (gpt-5.2, claude-opus, etc)

#### Правило 3: MCP Agent No-Auto-Reply ✅

```python
# Phase 80.6 + Phase 80.28
is_agent_sender = sender_id.startswith('@')
if is_agent_sender:
    # MCP agents must NOT trigger auto-response
    return []  # ✅ ПРАВИЛЬНО - no auto-cascade
```

**Статус:** ✅ ПРАВИЛЬНО - MCP агенты не вызывают других без явного @mention

#### Правило 4: Smart Reply Decay ⚠️

```python
# Phase 80.28: Line 275-302
if is_agent_sender and group and group.last_responder_id and group.last_responder_decay < 2:
    # Continue conversation
    return [last_responder]  # ⚠️ ДА, но...
```

**Проблема:**
- `last_responder_decay` increments on USER messages (line 609 group_message_handler.py)
- Resets on AGENT response (line 920-927 group_message_handler.py)
- **РАБОТАЕТ ПРАВИЛЬНО**, но сложная логика - нужен комментарий

#### Правило 5: Keyword-Based Selection ✅

```python
# Line 334-356: Smart keyword routing
keywords = {
    'PM': ['plan', 'task', 'scope', ...],
    'Architect': ['architecture', 'design', ...],
    'Dev': ['code', 'implement', ...],
    'QA': ['test', 'bug', 'verify', ...]
}
```

**Статус:** ✅ ПРАВИЛЬНО - хорошая эвристика

---

## 3. АВТОРСТВО СООБЩЕНИЙ

### 3.1 Формат sender_id и attribution

| Компонент | Где формируется | Формат | Проблема |
|-----------|-----------------|--------|----------|
| **User message** | `group_message_handler.py:550-596` | `sender_id="user"` | ✅ Стандартный |
| **Agent message** | `group_message_handler.py:889-896` | `sender_id=agent_id` (e.g. "@architect") | ✅ Правильный формат |
| **Chat history** | `group_message_handler.py:939-949` | `"agent": display_name, "model": model_id, "model_provider": provider_name` | ✅ РЕАЛИЗОВАНО Phase 74.8 |
| **Display name** | Группа participants dict | Может быть `"Claude Opus (Claude CLI)"` | ⚠️ INCONSISTENT - см ниже |

### 3.2 MARKER_AUTHOR_FORMAT - Проблема с форматом

**Файл:** `/src/api/handlers/group_message_handler.py:738-758`

```python
display_name = participant["display_name"]
role = participant.get("role", "worker")

# agent_type_map uses display_name directly
# But display_name может быть:
# - "@architect" (agent_id)
# - "Architect (Llama 405B)"
# - "Claude Opus (Claude CLI)"  <-- INCONSISTENT!
```

**Проблема:**
- Display names иногда включают модель в скобках
- Иногда только роль (Architect, Dev, QA, PM)
- **Нет единого формата**

**Где это видно:**
- `data/groups.json` - participants имеют разные display_name форматы
- Chat history: `"agent": display_name` сохраняет разные форматы

**Рекомендация:**
```python
# ДОЛЖНО БЫТЬ:
sender_id_format = f"{display_name} ({model_id})"  # Claude Opus (claude-3-opus)
# или
sender_id_format = f"{agent_id} ({provider_name})"  # @architect (anthropic)
```

---

## 4. REPLY МЕХАНИЗМ

### 4.1 Reply Detection

**Файл:** `/src/api/handlers/group_message_handler.py:553, 663-677`

```python
reply_to_id = data.get("reply_to")  # Line 553

# Line 663-677: Find original agent
if reply_to_id:
    messages = manager.get_messages(group_id, limit=100)
    for msg in messages:
        if msg.get("id") == reply_to_id:
            original_sender = msg.get("sender_id", "")
            if original_sender.startswith("@"):
                reply_to_agent = original_sender
```

**Статус:** ✅ РАБОТАЕТ - reply корректно находит original sender

### 4.2 Reply Routing

**Файл:** `/src/services/group_chat_manager.py:214-227`

```python
# MARKER_REPLY_HANDLER
if reply_to_agent:
    reply_to_normalized = reply_to_agent.lower().lstrip('@')
    for pid, p in participants.items():
        agent_id_normalized = p.get('agent_id', '').lower().lstrip('@')
        if agent_id_normalized == reply_to_normalized:
            if p.get('role') != 'observer':
                return [p]
```

**Статус:** ✅ РАБОТАЕТ

### 4.3 Reply to MCP Agents - ПРОБЛЕМА!

**Файл:** `/src/api/handlers/group_message_handler.py:80-95`

```python
MCP_AGENTS = {
    "browser_haiku": {...},
    "claude_code": {...}
}
```

**Проблема:**
- MCP агенты НЕ в `group.participants`
- Reply к MCP сообщениям не будет найдена в line 668-677!
- **Нужен special handling для MCP agents**

**Где это может сломаться:**
1. User replies to MCP agent message
2. `reply_to_id` points to MCP message
3. `original_sender` = "claude_code" или "browser_haiku"
4. But `original_sender.startswith("@")` is FALSE
5. Reply игнорируется! ❌

---

## 5. MCP ROUTING (Phase 80.13)

### 5.1 MCP Agent Detection

**Файл:** `/src/api/handlers/group_message_handler.py:614-631`

```python
# MARKER_MCP_ROUTING: Phase 80.13
mentions = re.findall(r"@(\w+)", content)
if mentions:
    await notify_mcp_agents(...)
```

**Проблем:**
- Только простые агент names `@browser_haiku`, не поддерживает aliases
- Regex `r"@(\w+)"` не захватывает полные model names!

### 5.2 MCP Notification

**Файл:** `/src/api/handlers/group_message_handler.py:98-217`

```python
async def notify_mcp_agents(...):
    # Line 125-137: Check direct match + aliases
    for mention in mentions:
        if mention_lower in MCP_AGENTS:
            mentioned_mcp_agents.append(mention_lower)

    # Line 159-172: Emit socket event + store in team_messages
```

**Статус:** ✅ РАБОТАЕТ

---

## 6. TODO ФИКСЫ ДЛЯ PHASE 108

### Критичные (ДОЛЖНЫ БЫТЬ ФИКСЫ)

1. **MARKER_FALLBACK_BUG**: Убрать auto-fallback на OpenRouter в `provider_registry.py:1139-1182`
   - Fallback должен быть ТОЛЬКО когда явно нет ключей, не на каждый error
   - Сейчас: любой HTTP error → switch to OpenRouter → может неправильно маршрутизировать
   - Должно быть: логировать error, пробросить вверх, пусть caller решает

2. **MARKER_MCP_ROUTING Fix**: Reply to MCP agents НЕ работает!
   - Line 668-677 проверяет `original_sender.startswith("@")`
   - Но MCP messages имеют sender_id = "claude_code" (БЕЗ @)
   - Нужна проверка: если MCP agent → маршрутизировать на MCP notification

3. **MARKER_AUTHOR_FORMAT**: Унифицировать формат sender_id
   - Сейчас: смешаны agent_id, display_name, полные модели
   - Должно быть: строгий формат "NAME (PROVIDER)" или "@role (MODEL)"
   - Для всех сообщений в chat_history и group_message_handler

### Важные (УЛУЧШЕНИЯ)

4. **Ollama fallback**: Если модель not found → не use default, check list
   - Line 654-657 → may use non-existent model

5. **MCP regex upgrade**: Поддерживать aliases при @mention
   - Сейчас: только exact names
   - Должно быть: @haiku должен работать как @browser_haiku

6. **Smart reply decay logging**: Добавить DEBUG логи для Phase 80.28
   - Сложная логика - нужны логи как decay increments/resets

### Nice to Have

7. **Model routing в chat_history**: Display model provider отдельно
   - Сейчас: есть `model_provider` field - хорошо
   - Может быть: добавить в UI display "Claude Opus (Anthropic)"

---

## 7. МАРКЕРЫ ДЛЯ КОД REVIEW

```python
# MARKER_FALLBACK_BUG
# Строка: provider_registry.py:1139, 1155, 1220
# Проблема: auto-fallback на OpenRouter/ChatGPT без явного запроса
# Статус: КРИТИЧНО - может вызвать неправильную маршрутизацию

# MARKER_ROUTING_LOGIC
# Строка: group_message_handler.py:679
# Проблема: нет (правильно реализовано в select_responding_agents)
# Статус: ✅ OK

# MARKER_AUTHOR_FORMAT
# Строка: group_message_handler.py:738, 944-946
# Проблема: display_name format inconsistent (may include model, may not)
# Статус: ВАЖНО - может сломать UI attribution

# MARKER_REPLY_HANDLER
# Строка: group_message_handler.py:663-677, group_chat_manager.py:214-227
# Проблема: reply to MCP agents НЕ работает (MCP не в participants)
# Статус: БАГ - MCP replies игнорируются

# MARKER_MCP_ROUTING
# Строка: group_message_handler.py:614-631
# Проблема: @mention regex слишком простой, не поддерживает aliases
# Статус: УЛУЧШЕНИЕ - работает но неполно
```

---

## 8. SUMMARY TABLE

| Компонент | Статус | Фикс | Приоритет |
|-----------|--------|------|-----------|
| Fallback на OpenRouter | ❌ БАГ | Убрать auto-fallback | КРИТИЧНО |
| Reply to MCP agents | ❌ БАГ | Add MCP check в reply detection | БАГ |
| Author format | ⚠️ INCONSISTENT | Унифицировать формат | ВАЖНО |
| Smart reply decay | ✅ OK | Добавить логи | Nice to have |
| @mention routing | ✅ OK | Upgrade regex для aliases | УЛУЧШЕНИЕ |
| Agent selection | ✅ OK | - | - |
| Keyword-based routing | ✅ OK | - | - |

---

## 9. РЕКОМЕНДУЕМЫЙ ПОРЯДОК ФИКСОВ

**Phase 108.1: Критичные баги**
1. Remove auto-fallback в provider_registry.py (MARKER_FALLBACK_BUG)
2. Fix reply to MCP agents в group_message_handler.py (MARKER_REPLY_HANDLER)

**Phase 108.2: Author attribution**
3. Унифицировать sender_id format (MARKER_AUTHOR_FORMAT)
4. Добавить model provider в display_name когда сохраняется

**Phase 108.3: Polish**
5. Улучшить MCP @mention regex (MARKER_MCP_ROUTING)
6. Добавить логи для smart reply decay (Phase 80.28)

---

**Отчет готов для передачи Sonnet на implementation.**
