# КРИТИЧЕСКИЙ АУДИТ: Solo vs Group Chat Model Calls

## EXECUTIVE SUMMARY

**ФУНДАМЕНТАЛЬНОЕ РАЗЛИЧИЕ:** Solo и Group используют **СОВЕРШЕННО РАЗНЫЕ СИСТЕМЫ ВЫЗОВОВ МОДЕЛЕЙ**:

- **SOLO Chat**: Прямые вызовы ollama/openrouter через user_message_handler (lines ~350-600)
- **GROUP Chat**: Через orchestrator.call_agent() → _run_agent_with_elisya_async() → call_model_v2()

Это приводит к НЕСОВМЕСТИМОСТИ в:
1. Как форматируются сообщения (messages[])
2. Как выбираются провайдеры
3. Как обрабатываются system_prompt
4. Как работает streaming

---

## 1. CALL SITES (ГДЕ ВЫЗЫВАЕТСЯ МОДЕЛЬ)

### 1.1 SOLO CHAT - Прямые вызовы Ollama/OpenRouter

**Файл:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py`

#### Ollama Direct Call (Строки ~355-362)
```python
# Line 355-362: Direct Ollama call
def ollama_call():
    return ollama.chat(
        model=requested_model,
        messages=[{"role": "user", "content": model_prompt}],  # ← ТОЛЬКО USER, БЕЗ SYSTEM
        stream=False,
    )

ollama_response = await loop.run_in_executor(None, ollama_call)
```

**КЛЮЧЕВОЕ РАЗЛИЧИЕ:**
- Сообщения: `[{"role": "user", "content": model_prompt}]`
- **БЕЗ system_prompt** в сообщениях
- System prompt встроен в model_prompt строкой (через build_model_prompt)
- Провайдер: Прямой вызов ollama.chat()

#### OpenRouter Streaming (Строки ~567-580)
```python
# Line 567-580: OpenRouter with streaming
payload = {
    "model": requested_model,
    "messages": [{"role": "user", "content": model_prompt}],  # ← ТОЛЬКО USER
    "max_tokens": 999999,
    "temperature": 0.7,
    "stream": True,
}

async with client.stream(
    "POST",
    "https://openrouter.ai/api/v1/chat/completions",
    headers=headers,
    json=payload,
) as response:
```

**КЛЮЧЕВОЕ РАЗЛИЧИЕ:**
- Сообщения: `[{"role": "user", "content": model_prompt}]`
- **БЕЗ system role** в payload
- Direct HTTP POST к openrouter.ai
- Streaming по умолчанию включен

### 1.2 GROUP CHAT - Через Orchestrator

**Файл:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`

#### call_agent() Вызов (Строки ~785-804)
```python
# Line 785-804: Group chat calls orchestrator
result = await asyncio.wait_for(
    orchestrator.call_agent(
        agent_type=agent_type,          # "Dev", "QA", "Architect", "Hostess"
        model_id=model_id,              # e.g., "openrouter/gpt-4"
        prompt=prompt,                  # ← ПОЛНЫЙ КОНТЕКСТ + REQUEST
        context={
            "group_id": group_id,
            "group_name": group["name"],
            "agent_id": agent_id,
            "display_name": display_name,
        },
    ),
    timeout=120.0,
)
```

**КЛЮЧЕВОЕ РАЗЛИЧИЕ:**
- Вызывает `orchestrator.call_agent()` (НЕ прямой провайдер)
- Передает `agent_type` (для роли)
- Передает `model_id` (может быть с префиксом провайдера)
- Передает `prompt` как строку (включает весь контекст)

#### orchestrator.call_agent() Реализация (Строки ~2242-2331)

**Файл:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/orchestrator_with_elisya.py`

```python
# Line 2242-2331: call_agent implementation
async def call_agent(
    self,
    agent_type: str,
    model_id: str,
    prompt: str,
    context: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Single-agent execution for GroupChat integration."""

    # Line 2281-2296: Create state for single agent
    workflow_id = str(uuid.uuid4())
    state = self._get_or_create_state(workflow_id, prompt)

    if context:
        # Convert dict to readable string
        context_parts = [f"{k}: {v}" for k, v in context.items()]
        state.raw_context = "\n".join(context_parts)

    # Line 2298-2305: Inject model override
    old_routing = None
    if model_id and model_id != "auto":
        old_routing = self.model_routing.get(agent_type)
        self.model_routing[agent_type] = {
            "provider": "manual",
            "model": model_id,
        }

    try:
        # Line 2309-2316: Run with Elisya integration
        if hasattr(self, "_run_agent_with_elisya_async"):
            output, updated_state = await self._run_agent_with_elisya_async(
                agent_type, state, prompt
            )
        else:
            output = f"[{agent_type}] {prompt}"
            updated_state = state

        return {"output": output, "state": updated_state, "status": "done"}
```

---

## 2. РОЛИ И SYSTEM PROMPTS

### 2.1 SOLO CHAT - Система ролей

**Нет явных ролей!** System prompt встроен в model_prompt через `build_model_prompt()`:

**Файл:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/chat_handler.py`

```python
# Line 110-157: build_model_prompt
def build_model_prompt(
    text: str,
    context_for_model: str,
    pinned_context: str = "",
    history_context: str = "",
    viewport_summary: str = "",
    json_context: str = "",
) -> str:
    """Build a standard prompt for direct model calls."""

    spatial_section = ""
    if viewport_summary:
        spatial_section = f"""## 3D VIEWPORT CONTEXT
The user is viewing this codebase in a 3D visualization. Here's what they can see:

{viewport_summary}
"""

    json_section = json_context if json_context else ""

    return f"""You are a helpful AI assistant. Analyze the following context and answer the user's question.

{context_for_model}

{json_section}{pinned_context}{spatial_section}{history_context}## CURRENT USER QUESTION
{text}

---

Provide a helpful, specific answer:"""
```

**СИСТЕМА РОЛЕЙ:**
- **НЕТУ!** Все solo модели получают одинаковый system prompt: "You are a helpful AI assistant..."
- Нет разделения между PM, Dev, QA, Architect
- Контекст встроен в user_message (часть одного большого prompt)

### 2.2 GROUP CHAT - Система ролей через agents/role_prompts.py

**Файл:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/agents/role_prompts.py`

```python
# Line 15-74: PM_SYSTEM_PROMPT (пример)
PM_SYSTEM_PROMPT = """You are PM (Project Manager) in the VETKA AI team.

## YOUR ROLE
- Analyze user requests and break them into CONCRETE tasks
- Create clear specifications for Dev agent
- Identify risks and dependencies
- You do NOT write code - that's Dev's job

## YOUR TEAM (use @mentions to delegate)
- @Dev — Implementation, coding, file creation
- @QA — Testing, code review, quality checks
- @Researcher — Deep investigation if needed
...
"""

# Line 79-149: DEV_SYSTEM_PROMPT
DEV_SYSTEM_PROMPT = """You are Dev (Developer) in the VETKA AI team.

## YOUR ROLE
- Write WORKING, COMPLETE code
- Create artifacts (files, functions, classes)
...
"""
```

**КЛЮЧЕВЫЕ РОЛЕВЫЕ СИСТЕМНЫЕ PROMPTS:**
1. **PM_SYSTEM_PROMPT** (lines 15-74) - Project Manager
2. **DEV_SYSTEM_PROMPT** (lines 79-149) - Developer
3. **QA_SYSTEM_PROMPT** - Quality Assurance
4. **ARCHITECT_SYSTEM_PROMPT** - Architecture
5. **RESEARCHER_SYSTEM_PROMPT** - Research

**Как используются:**

**Файл:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`

```python
# Line 758: Get agent-specific system prompt
system_prompt = get_agent_prompt(agent_type)

# Line 762-772: Build context with role
context_parts = [
    f"## ROLE\n{system_prompt}\n",
    f"## GROUP: {group.get('name', 'Team Chat')}\n",
]

# Add chain context if other agents have responded
if previous_outputs:
    context_parts.append("## PREVIOUS AGENT OUTPUTS")
    for agent_name, output in previous_outputs.items():
        context_parts.append(f"[{agent_name}]: {output[:400]}...")
    context_parts.append("")

# Add recent conversation
context_parts.append("## RECENT CONVERSATION")
for msg in recent_messages:
    msg_content = msg.get("content", "")[:200]
    context_parts.append(f"[{msg.get('sender_id')}]: {msg_content}")

# Current request
context_parts.append(f"\n## CURRENT REQUEST\n{content}")

prompt = "\n".join(context_parts)
```

---

## 3. MESSAGE FORMAT РАЗЛИЧИЯ

### 3.1 SOLO CHAT MESSAGE FORMAT

**Ollama:** (Line 358)
```python
messages = [{"role": "user", "content": model_prompt}]
```

**OpenRouter:** (Line 569)
```python
messages = [{"role": "user", "content": model_prompt}]
```

**СТРУКТУРА:**
- Массив из 1 сообщения
- role: ВСЕГДА "user"
- content: весь контекст + вопрос (встроены в model_prompt)
- **БЕЗ system role**

### 3.2 GROUP CHAT MESSAGE FORMAT

**Файл:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/orchestrator_with_elisya.py`

Система использует ElisyaState для построения сообщений. Когда `_run_agent_with_elisya_async` вызывает модель, она:

1. Берет `system_prompt` из role_prompts
2. Берет `prompt` (контекст + запрос)
3. Строит сообщения через ConversationMessage objects
4. Передает в `call_model_v2()` с явным role разделением

---

## 4. PROVIDER SELECTION LOGIC

### 4.1 SOLO CHAT PROVIDER SELECTION

**Файл:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py`

Provider выбирается на основе `requested_model`:

```python
# Line ~300-310 (приблизительно):
# Detect provider from requested_model name
if requested_model.startswith("ollama"):
    # Use Ollama (Line 355-362)
    ollama.chat(model=requested_model, ...)
elif requested_model.startswith("openrouter") or "/" in requested_model:
    # Use OpenRouter (Line 567-580)
    httpx.post("https://openrouter.ai/api/v1/chat/completions", ...)
```

**ЛОГИКА:**
- `ollama/*` или `model:version` → Ollama
- `provider/*` или содержит `/` → OpenRouter
- **HARDCODED провайдеры в разных блоках кода**

### 4.2 GROUP CHAT PROVIDER SELECTION

**Файл:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`

```python
# Line 707-709: Force OpenRouter prefix for GPT models
if "gpt" in model_id.lower():
    model_id = f"openrouter/{model_id}"

# Line 793: Pass to orchestrator with model override
orchestrator.call_agent(
    agent_type=agent_type,
    model_id=model_id,        # ← Может быть с префиксом провайдера
    ...
)
```

**Затем в orchestrator:**

**Файл:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/orchestrator_with_elisya.py`

```python
# Line 2300-2305: Store model override
self.model_routing[agent_type] = {
    "provider": "manual",
    "model": model_id,
}

# Line ~1200-1400 (в _run_agent_with_elisya_async):
# ModelRouter выбирает провайдер на основе model_routing
```

**Провайдер выбирается через ModelRouter (new система):**

**Файл:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/provider_registry.py`

```python
# Line 856-903: call_model_v2 с явным provider parameter
async def call_model_v2(
    messages: List[Dict[str, str]],
    model: str,
    provider: Optional[Provider] = None,  # ← ЯВНЫЙ PARAMETER!
    tools: Optional[List[Dict]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Phase 80.10: New unified call_model with explicit provider."""

    registry = get_registry()

    # If provider not specified, auto-detect (fallback)
    if provider is None:
        provider = ProviderRegistry.detect_provider(model)  # ← AUTO-DETECTION

    # Get provider instance
    provider_instance = registry.get(provider)

    # Call provider
    result = await provider_instance.call(messages, model, tools, **kwargs)
    return result
```

---

## 5. ТАБЛИЦА РАЗЛИЧИЙ

| Аспект | Solo Chat | Group Chat | Файл:Строка |
|--------|-----------|------------|-------------|
| **call_site** | Прямой ollama.chat() или httpx.post() | orchestrator.call_agent() | solo: UMH:355,567 / group: GMH:793 |
| **system_prompt** | Встроен в model_prompt строкой | Отдельный role_prompts (PM/Dev/QA) | solo: CH:110 / group: RP:15-149 |
| **message format** | [{"role": "user", "content": full_prompt}] | Построено ElisyaState с явным role разделением | solo: UMH:358,569 / group: orch:~1300 |
| **provider detection** | if/elif blocks по prefix | ProviderRegistry.detect_provider() | solo: UMH:~300 / group: PR:885 |
| **provider parameter** | Hardcoded в коде (ollama vs openrouter) | call_model_v2(provider=...) явный | solo: none / group: PR:859 |
| **model override** | N/A | self.model_routing[agent_type] | group: GMH:707,orch:2300 |
| **streaming** | Встроен в логике (try streaming, fallback) | Через ElisyaState streaming flag | solo: UMH:551 / group: orch:~ |
| **fallback strategy** | 429 → message, 400 → non-streaming | XAI → OpenRouter fallback | solo: UMH:582 / group: PR:903 |
| **tool support** | Частично (Ollama only if model supports) | call_model_v2 проверяет provider.supports_tools | solo: CH:183-198 / group: PR:895 |
| **context building** | build_model_prompt() - встроена в prompt | get_agent_prompt() + context_parts[] | solo: CH:110 / group: GMH:758 |

---

## 6. КОНКРЕТНЫЕ СТРОКИ КОДА

### 6.1 SOLO CHAT CALL SITES

| Что | Файл | Строка | Код |
|-----|------|--------|-----|
| **Ollama Detection** | user_message_handler.py | ~300 | `if is_ollama_model:` |
| **Ollama Direct Call** | user_message_handler.py | 355-362 | `ollama.chat(model=requested_model, messages=[{"role": "user", ...}])` |
| **OpenRouter Detection** | user_message_handler.py | ~420 | `if is_openrouter_model:` |
| **OpenRouter HTTP Call** | user_message_handler.py | 567-580 | `httpx.stream("POST", "https://openrouter.ai/api/v1/chat/completions")` |
| **Message Format** | user_message_handler.py | 358, 569 | `messages=[{"role": "user", "content": model_prompt}]` |
| **Prompt Builder** | chat_handler.py | 110-157 | `def build_model_prompt(text, context_for_model, ...)` |
| **System Prompt** | chat_handler.py | 147 | `f"""You are a helpful AI assistant...` |

### 6.2 GROUP CHAT CALL SITES

| Что | Файл | Строка | Код |
|-----|------|--------|-----|
| **GPT Model Prefix** | group_message_handler.py | 707-709 | `if "gpt" in model_id.lower(): model_id = f"openrouter/{model_id}"` |
| **call_agent() Call** | group_message_handler.py | 793-804 | `orchestrator.call_agent(agent_type=..., model_id=..., prompt=...)` |
| **System Prompt Select** | group_message_handler.py | 758 | `system_prompt = get_agent_prompt(agent_type)` |
| **Message Format Building** | group_message_handler.py | 762-783 | `context_parts = [f"## ROLE\n{system_prompt}...", ...]` |
| **call_agent() Definition** | orchestrator_with_elisya.py | 2242-2331 | `async def call_agent(self, agent_type, model_id, prompt, context):` |
| **Model Override** | orchestrator_with_elisya.py | 2300-2305 | `self.model_routing[agent_type] = {"provider": "manual", "model": model_id}` |
| **Elisya Async Call** | orchestrator_with_elisya.py | 2310 | `await self._run_agent_with_elisya_async(agent_type, state, prompt)` |
| **call_model_v2() Definition** | provider_registry.py | 856-903 | `async def call_model_v2(messages, model, provider=None, tools=None):` |
| **Provider Detection** | provider_registry.py | 884-885 | `if provider is None: provider = ProviderRegistry.detect_provider(model)` |

---

## 7. РЕКОМЕНДАЦИИ ПО УНИФИКАЦИИ

### ПРОБЛЕМА 1: Два разных вызова модели
- **Solo:** Ollama и OpenRouter вызываются напрямую в user_message_handler
- **Group:** Через orchestrator.call_agent()

### РЕШЕНИЕ:
```python
# Сделать solo chat ТОЖЕ использовать orchestrator.call_agent()
# Это даст:
# 1. Единую точку входа для всех LLM calls
# 2. Использование ElisyaState для всех
# 3. Единый provider routing (call_model_v2)
# 4. Поддержку агентских ролей в solo chat
```

### ПРОБЛЕМА 2: Разные message formats
- **Solo:** `[{"role": "user", "content": full_prompt}]`
- **Group:** Построено с явным role разделением

### РЕШЕНИЕ:
```python
# Использовать call_model_v2 везде
# Это ожидает messages с role и content
# Всегда передавать system_prompt отдельно от user message

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_message},
]
```

### ПРОБЛЕМА 3: Система ролей только в group
- **Solo:** Нет ролей, все одинаково
- **Group:** PM/Dev/QA/Architect с разными system_prompts

### РЕШЕНИЕ:
```python
# Расширить solo chat для поддержки ролей
# Использовать role_prompts.py для обоих solo и group
# При прямом запросе: использовать default role (помощник)
```

### ПРОБЛЕМА 4: Provider detection logic дублируется
- **Solo:** if/elif blocks в user_message_handler.py
- **Group:** ProviderRegistry.detect_provider()

### РЕШЕНИЕ:
```python
# Удалить дублирование в solo chat
# Использовать ТОЛЬКО ProviderRegistry.detect_provider()
# Это уже реализовано в chat_handler.py detect_provider()
```

### ПРОБЛЕМА 5: System prompt обработка
- **Solo:** Встроен в user message (часть prompt string)
- **Group:** Отдельный role в messages[]

### РЕШЕНИЕ:
```python
# ВСЕГДА передавать system_prompt отдельно:
messages = [
    {"role": "system", "content": get_agent_prompt(agent_type)},
    {"role": "user", "content": user_message},
]
# Не встраивать system в user message!
```

---

## 8. МИГРАЦИОННЫЙ ПУТЬ

### Фаза 1: Унификация call sites (КРИТИЧНО)
1. Обновить user_message_handler.py для использования orchestrator.call_agent()
2. Удалить прямые ollama.chat() и httpx.post() из solo handler
3. Все solo requests → orchestrator.call_agent(agent_type="Assistant", ...)

### Фаза 2: Message format унификация
1. Обновить build_model_prompt() для возврата двух значений: (system, user)
2. Все модели получают явный system role
3. Проверить backward compatibility в call_model_v2()

### Фаза 3: Role system в solo chat
1. Добавить параметр `agent_type` в solo chat socket.IO события
2. Использовать role_prompts для всех agent_types
3. Дать пользователям возможность выбирать роль (PM, Dev, QA, etc.)

### Фаза 4: Provider registry everywhere
1. Убедиться что detect_provider() используется везде
2. Удалить hardcoded provider detection из solo handler
3. Всегда использовать call_model_v2() с явным provider

---

## 9. ФАЙЛЫ, ТРЕБУЮЩИЕ ОБНОВЛЕНИЯ

```
КРИТИЧНЫЕ:
- src/api/handlers/user_message_handler.py (линии ~300-600)
  └─ Заменить прямые ollama.chat/httpx.post на orchestrator.call_agent()

- src/api/handlers/chat_handler.py (build_model_prompt)
  └─ Вернуть (system_prompt, user_message) вместо объединенного prompt

- src/orchestration/orchestrator_with_elisya.py (call_agent)
  └─ Убедиться что system_prompt правильно передается

ВАЖНЫЕ:
- src/elisya/provider_registry.py (call_model_v2)
  └─ Документировать ожидаемый message format

- src/api/handlers/group_message_handler.py
  └─ Может остаться как есть (уже использует правильный паттерн)

- src/agents/role_prompts.py
  └─ Может быть использован из solo chat
```

---

## ЗАКЛЮЧЕНИЕ

**ГЛАВНАЯ ПРОБЛЕМА:** Два полностью разных пути вызова моделей создают несогласованность.

**ГЛАВНОЕ РЕШЕНИЕ:** Унифицировать на `orchestrator.call_agent()` + `call_model_v2()` + `ProviderRegistry`

**ВЫИГРЫШ:**
- ✅ Одна система для всех LLM calls
- ✅ Поддержка агентских ролей везде
- ✅ Единый provider routing
- ✅ Лучше error handling и fallbacks
- ✅ Легче в поддержке
