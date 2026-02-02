# Phase 108 - Примеры Routing Проблем и Фиксов

---

## ПРОБЛЕМА 1: Auto-Fallback на OpenRouter

### Где проблема

**Файл:** `/src/elisya/provider_registry.py:1089-1226`

```python
async def call_model_v2(...):
    try:
        result = await provider_instance.call(messages, model, tools, **kwargs)
        return result
    except XaiKeysExhausted as e:
        # MARKER_93.10_FALLBACK: fallback to OpenRouter
        print(f"XAI keys exhausted, using OpenRouter fallback...")
        openrouter_provider = registry.get(Provider.OPENROUTER)
        result = await openrouter_provider.call(...)
        return result  # ⚠️ ПРОБЛЕМА: user не просил OpenRouter!
```

### Как проблема проявляется

**Сценарий:**
1. User запросит: "@grok-4" (xAI direct API)
2. xAI API returns 403 (all keys rate-limited)
3. System автоматически переключается на OpenRouter
4. Результат: Claude вместо Grok! 😱

### Почему это проблема

- User явно выбрал модель/провайдера
- System должна СКАЗАТЬ что произошло, не молчать
- Fallback скрывает реальные проблемы (нет ключей, исчерпаны лимиты)
- Может привести к неправильной маршрутизации в групповых чатах

### Правильный фикс

```python
async def call_model_v2(...):
    try:
        result = await provider_instance.call(messages, model, tools, **kwargs)
        return result
    except XaiKeysExhausted as e:
        # MARKER_FALLBACK_BUG: Don't auto-fallback!
        print(f"⚠️ All {provider.value} keys exhausted!")
        print(f"   User requested: {model}")
        print(f"   Available fallbacks: see /api/models/fallbacks")
        # Emit event to frontend - show user what happened
        # raise XaiKeysExhausted(e)  # ← Let caller decide!
        raise  # Propagate error, don't hide
```

---

## ПРОБЛЕМА 2: Reply to MCP Agents НЕ работает

### Где проблема

**Файл 1:** `/src/api/handlers/group_message_handler.py:663-677`

```python
# MARKER_REPLY_HANDLER: Find original agent
if reply_to_id:
    messages = manager.get_messages(group_id, limit=100)
    for msg in messages:
        if msg.get("id") == reply_to_id:
            original_sender = msg.get("sender_id", "")
            # ⚠️ ПРОБЛЕМА: только checking if sender starts with "@"
            if original_sender.startswith("@"):
                reply_to_agent = original_sender
```

**Файл 2:** `/src/api/handlers/group_message_handler.py:80-95`

```python
MCP_AGENTS = {
    "browser_haiku": {...},
    "claude_code": {...}
}
# ⚠️ MCP agents NOT in group.participants!
# ⚠️ sender_id for MCP messages = "claude_code" (NO @)
```

### Как проблема проявляется

**Сценарий:**
1. claude_code агент отправляет сообщение в группу
   - sender_id = "claude_code" (не "@claude_code")
2. User replies to claude_code message
   - reply_to_id = message.id of claude_code message
3. System looks up original_sender = "claude_code"
4. Проверка: `"claude_code".startswith("@")` → FALSE
5. **Результат:** reply игнорируется! ❌
6. System идет дальше по routing logic
7. Вместо claude_code отвечает случайный агент!

### Правильный фикс

```python
# MARKER_REPLY_HANDLER: Fix for MCP agents
if reply_to_id:
    messages = manager.get_messages(group_id, limit=100)
    for msg in messages:
        if msg.get("id") == reply_to_id:
            original_sender = msg.get("sender_id", "")

            # Check if original sender is MCP agent
            if original_sender in ["claude_code", "browser_haiku"]:
                # Route to MCP agent
                await notify_mcp_agents(
                    sio=sio,
                    group_id=group_id,
                    sender_id=user_id,
                    content=content,
                    mentions=[original_sender],
                    message_id=user_message.id,
                    is_reply=True  # ← Important!
                )
                return  # Don't continue to regular routing

            # Original logic for AI agents
            elif original_sender.startswith("@"):
                reply_to_agent = original_sender
```

---

## ПРОБЛЕМА 3: Inconsistent Author Format

### Где проблема

**Файл 1:** `/src/services/group_chat_manager.py:45-52`

```python
@dataclass
class GroupParticipant:
    agent_id: str              # "@architect"
    model_id: str              # "llama-405b"
    role: GroupRole
    display_name: str          # ← INCONSISTENT!
    # display_name может быть:
    # - "@architect"
    # - "Architect"
    # - "Claude Opus (Claude CLI)"
    # - "Dev (Llama 405B)"
```

**Файл 2:** `/src/api/handlers/group_message_handler.py:889-896`

```python
agent_message = await manager.send_message(
    group_id=group_id,
    sender_id=agent_id,  # "@architect" or "@dev"
    content=response_text,
    message_type="response",
    metadata={"in_reply_to": user_message.id},
)

# Потом в chat_history:
chat_history.add_message(chat_id, {
    "role": "assistant",
    "content": response_text,
    "agent": display_name,  # ← МОЖЕТ БЫТЬ РАЗНЫЙ ФОРМАТ!
    "model": model_id,
    "model_provider": provider_name,
    "metadata": {"group_id": group_id},
})
```

### Как проблема проявляется

**Сценарий:**
1. Group participants:
   - Architect: display_name = "Claude Opus (Claude CLI)"
   - Dev: display_name = "Dev (Llama 405B)"
   - PM: display_name = "@pm"

2. Message saved to group: sender_id = "@architect"
3. Message saved to chat_history: agent = "Claude Opus (Claude CLI)"
4. Next UI renders:
   - Group chat: shows "@architect"
   - Chat history panel: shows "Claude Opus (Claude CLI)"
   - Looks like different people! 😱

### Правильный фикс

```python
# Унифицировать формат sender_id
# Option A: Use model-based format
sender_id = f"{model_id} ({provider_name})"
# Example: "claude-3-opus (anthropic)"

# Option B: Use role-based format (для compat с @mentions)
sender_id = f"@{role.lower()} ({model_id})"
# Example: "@architect (claude-3-opus)"

# Option C: Use display_name но ВСЕГДА с моделью
sender_id = f"{display_name} ({model_id})"
# Example: "Architect (claude-3-opus)"

# CHOOSE ONE and apply everywhere:
# - group_message_handler.py:656 (sender_id when storing)
# - chat_history.add_message() (agent field)
# - group.json persistence (participants.display_name)
```

**Рекомендация:** Option B - сохраняет @mention compatibility но добавляет model info

---

## ПРОБЛЕМА 4: MCP Agent @mention regex слишком простой

### Где проблема

**Файл:** `/src/api/handlers/group_message_handler.py:617-620`

```python
# MARKER_MCP_ROUTING: MCP @mention detection
all_mentions_raw = re.findall(r"@(\w+)", content)
# ⚠️ Regex r"@(\w+)" НЕ захватывает:
# - Hyphenated names: @some-agent
# - Model names: @gpt-5.2, @claude-opus
# - Slashed names: @openai/gpt-4
```

### Как проблема проявляется

**Сценарий:**
1. User пишет: "@gpt-5.2 help me"
2. Regex `r"@(\w+)"` захватывает: ["gpt"]
3. System ищет MCP agent "gpt" → NOT FOUND
4. Message игнорируется ❌

### Правильный фикс

```python
# Use same robust regex as select_responding_agents!
# Line 235-237 of group_chat_manager.py:
all_mentions_raw = re.findall(
    r'@([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)',
    content
)

# This captures:
# - @grok-4 → "grok-4"
# - @gpt-5.2 → "gpt-5.2"
# - @openai/gpt-4 → "openai/gpt-4"
# - @ollama:qwen2:7b → "ollama:qwen2:7b"
```

---

## ПРАВИЛЬНАЯ FLOW ДЛЯ ФИКСОВ

### Phase 108.1: Critical Bugs (1-2 дня)

**Fix 1: Remove auto-fallback (provider_registry.py)**
```python
# MARKER_FALLBACK_BUG
# Lines: 1088-1226, 1139-1154, 1155-1182, 1220-1225
# Action: Remove auto-fallback logic, propagate errors
# Testing:
#   - Try @grok-4 with exhausted xAI keys
#   - Try @openai/gpt-5.2 with wrong API key
#   - Verify error is shown, not silently switched
```

**Fix 2: Reply to MCP agents (group_message_handler.py)**
```python
# MARKER_REPLY_HANDLER
# Lines: 663-677
# Action: Add MCP agent check before @mention check
# Testing:
#   - Reply to claude_code message
#   - Verify it routes to claude_code, not another agent
#   - Test replies to regular AI agents still work
```

### Phase 108.2: Author Format (1 день)

**Fix 3: Unify sender_id format**
```python
# MARKER_AUTHOR_FORMAT
# Files:
#   - group_message_handler.py:656, 738, 889-896
#   - group_chat_manager.py:627-677
#   - chat_history persistence
# Action: Use ONE consistent format everywhere
# Testing:
#   - Save messages to group
#   - Check chat_history format
#   - Verify UI attribution is correct
```

### Phase 108.3: Improvements (optional)

**Fix 4: Improve MCP regex (group_message_handler.py)**
```python
# MARKER_MCP_ROUTING
# Lines: 617-620
# Action: Use robust regex from group_chat_manager.py:235-237
# Testing:
#   - @grok-4, @gpt-5.2, @openai/gpt-4 mentions work
#   - Aliases work: @haiku → browser_haiku
```

**Fix 5: Smart reply decay logging**
```python
# Phase 80.28 debugging
# Lines: group_message_handler.py:608-612, 920-927
# Action: Add detailed logs showing decay progression
# Testing: Follow user→agent→user→agent conversation, check logs
```

---

## TEST CASES ДЛЯ验证 ФИКСОВ

### Test 1: Fallback Bug

```
Given: xAI keys are all rate-limited
When: User sends "@grok-4 help"
Then:
  - System shows error (not silent fallback)
  - User sees: "⚠️ Grok API rate-limited, try later"
  - Does NOT switch to OpenRouter silently
```

### Test 2: Reply to MCP

```
Given: claude_code agent in group, sent message
When: User replies to that message
Then:
  - Message routes to claude_code
  - claude_code receives notification (not another agent)
  - Reply flag is set (for context)
```

### Test 3: Author Format

```
Given: Multiple agents in group (Claude, Llama, Grok)
When: All respond to same message
Then:
  - Group chat shows: "@architect (claude-3-opus)", "@dev (llama-405b)", etc
  - Chat history shows: same format
  - No ambiguity about who is who
```

### Test 4: MCP @mention Regex

```
Given: User types "@gpt-5.2 analyze this"
When: Message is processed
Then:
  - @mention correctly parsed as "gpt-5.2"
  - System routes correctly (not "gpt")
  - Works with hyphenated and model names
```

---

## ФАЙЛЫ ДЛЯ SONNET ДЛЯ ФИКСОВ

### Критичные
1. `/src/elisya/provider_registry.py` - remove fallback logic
2. `/src/api/handlers/group_message_handler.py` - MCP reply + author format
3. `/src/services/group_chat_manager.py` - check author format consistency

### Второстепенные
4. `/src/api/handlers/group_message_handler.py` - MCP regex improvement
5. Log enhancements для Phase 80.28

---

**Готово для реализации Sonnet в Phase 108!**
