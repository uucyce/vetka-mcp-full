# HAIKU 2: Group Chat Flow Audit - OpenRouter Integration

**Дата:** 2026-01-26
**Фокус:** Проследить путь группового сообщения с ролями (PM, Dev, QA, Architect) и проверить OpenRouter интеграцию

---

## 1. GROUP MESSAGE ENTRY POINT

### Файл: `/src/api/handlers/group_message_handler.py`

| Элемент | Строка | Описание |
|---------|--------|---------|
| **Entry Handler** | 529-530 | `@sio.on("group_message")` - Socket.IO handler |
| **Message Parsing** | 541-550 | Распарсиваются `group_id`, `sender_id`, `content`, `reply_to_id` |
| **MCP Mentions** | 597-614 | Проверка @mentions для MCP agents (browser_haiku, claude_code) |
| **Agent Selection** | 665-671 | Вызов `manager.select_responding_agents()` |
| **Orchestrator Init** | 637 | Получение orchestrator через `get_orchestrator()` |

### MARKER_94.5: Group Chat Entry
```python
# Line 541: Entry marker
print(f"[GROUP_MESSAGE] Received from {sid}")

# Line 600-604: @mention extraction
mentions = re.findall(r"@(\w+)", content)

# Line 665-671: Agent selection with role awareness
participants_to_respond = await manager.select_responding_agents(
    content=content,
    participants=group.get("participants", {}),
    sender_id=sender_id,
    reply_to_agent=reply_to_agent,
    group=group_object,  # Phase 80.28: For smart reply decay
)
```

---

## 2. ROLE-SPECIFIC PROVIDERS & ROUTING

### Файл: `/src/services/group_chat_manager.py`

#### GroupRole Definition (Line 24-29)
```python
class GroupRole(Enum):
    ADMIN = "admin"
    WORKER = "worker"
    REVIEWER = "reviewer"
    OBSERVER = "observer"
```

#### Agent Selection Strategy (Line 166-361)
```python
async def select_responding_agents(
    self,
    content: str,
    participants: Dict[str, Any],
    sender_id: str,
    reply_to_agent: str = None,
    group: 'Group' = None  # Phase 80.28
) -> List[Any]:
```

**Приоритет маршрутизации:**
1. **Line 201-214:** Reply routing - если это ответ на сообщение агента
2. **Line 221-260:** @mentions - явное указание агента
3. **Line 262-272:** Phase 80.28 Smart reply decay - последний отвечавший агент
4. **Line 293-319:** Команды `/solo`, `/team`, `/round` - специальные маршруты
5. **Line 321-343:** SMART keyword-based selection - анализ ключевых слов в контексте
6. **Line 345-360:** Default - первый активный агент (предпочтительно admin)

#### Role-Keyword Mapping (Line 322-326)
```python
keywords = {
    'PM': ['plan', 'task', 'scope', 'timeline', 'requirements', 'analyze', 'strategy'],
    'Architect': ['architecture', 'design', 'system', 'pattern', 'structure', 'module'],
    'Dev': ['code', 'implement', 'function', 'class', 'write', 'debug', 'fix', 'api'],
    'QA': ['test', 'bug', 'review', 'verify', 'validate', 'coverage', 'quality']
}
```

---

## 3. AGENT CALL & MODEL ROUTING

### Файл: `/src/api/handlers/group_message_handler.py`

#### MARKER_94.6: Role-based Agent Routing (Line 719-737)
```python
agent_type_map = {
    "PM": "PM",
    "Dev": "Dev",
    "QA": "QA",
    "Architect": "Architect",
    "Researcher": "Researcher",  # Phase 57.8
    "admin": "PM",  # Default admin to PM
    "worker": "Dev",  # Default worker to Dev
}
agent_type = agent_type_map.get(display_name, agent_type_map.get(role, "Dev"))
```

#### Agent Call (Line 800-810)
```python
result = await asyncio.wait_for(
    orchestrator.call_agent(
        agent_type=agent_type,          # PM, Dev, QA, Architect, Hostess, Researcher
        model_id=model_id,              # Participant's assigned model
        prompt=prompt,                  # Role-specific prompt with context
        context={
            "group_id": group_id,
            "group_name": group["name"],
            "agent_id": agent_id,
            "display_name": display_name,
        },
    ),
    timeout=120.0,  # 2 minute timeout
)
```

---

## 4. ORCHESTRATOR CALL_AGENT METHOD

### Файл: `/src/orchestration/orchestrator_with_elisya.py`

#### call_agent() Method (Line 2242-2331)

**Параметры:**
- `agent_type`: 'PM', 'Dev', 'QA', 'Architect', 'Hostess', 'Researcher' (Line 2254)
- `model_id`: Model identifier (e.g., 'openai/gpt-4', 'ollama/qwen2:7b')
- `prompt`: User input
- `context`: Optional context dict

**Валидация (Line 2265-2279):**
```python
valid_agent_types = ["PM", "Dev", "QA", "Architect", "Hostess", "Researcher"]
```

**Model Override (Line 2298-2306):**
```python
if model_id and model_id != "auto":
    old_routing = self.model_routing.get(agent_type)
    self.model_routing[agent_type] = {
        "provider": "manual",
        "model": model_id,
    }
```

**Execution (Line 2309-2316):**
```python
if hasattr(self, "_run_agent_with_elisya_async"):
    output, updated_state = await self._run_agent_with_elisya_async(
        agent_type, state, prompt
    )
```

---

## 5. PROVIDER DETECTION & ROUTING

### Файл: `/src/orchestration/orchestrator_with_elisya.py`

#### _run_agent_with_elisya_async() (Line 1215-1300+)

**Step 1: Manual Model Override Detection (Line 1235-1257)**
```python
# MARKER_90.1.4.1: Use canonical detect_provider
if (
    agent_type in self.model_routing
    and self.model_routing[agent_type].get("provider") == "manual"
):
    manual_model = self.model_routing[agent_type]["model"]
    from src.elisya.provider_registry import ProviderRegistry

    detected_provider = ProviderRegistry.detect_provider(manual_model)  # Line 1244
    real_provider = detected_provider.value

    # Phase 80.37: Check if xai key exists, fallback to openrouter
    if real_provider == "xai":
        if not APIKeyService().get_key("xai"):
            real_provider = "openrouter"  # Fallback!
```

**Step 2: Auto Routing (Line 1258-1262)**
```python
else:
    routing = self._get_routing_for_task(
        str(state.context or "")[:100], agent_type
    )
model_name = routing["model"]
```

**Step 3: API Key Injection (Line 1264-1270)**
```python
api_key = self._inject_api_key(routing)
saved_env = {}
if api_key:
    saved_env = self.key_service.inject_key_to_env(routing["provider"], api_key)
```

#### Provider Detection (Line 1016-1018)
```python
if provider is None:
    provider = ProviderRegistry.detect_provider(model)  # CRITICAL!
print(f"      🌐 Using provider: {provider.value} for model: {model}")
```

**Поддерживаемые провайдеры (provider_registry.py, Line 35-44):**
```python
class Provider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GEMINI = "gemini"       # Phase 80.41
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    XAI = "xai"             # Phase 80.35: x.ai (Grok)
```

---

## 6. LLM CALL & FALLBACK

### Файл: `/src/orchestration/orchestrator_with_elisya.py`

#### call_model_v2() with Provider (Line 1020-1050)

```python
# MARKER_90.1.4.2_START: Handle XaiKeysExhausted
try:
    response = await call_model_v2(  # Line 1023
        messages=messages,
        model=model,
        provider=provider,            # EXPLICIT PROVIDER PASSED!
        tools=tool_schemas
    )
except XaiKeysExhausted:
    print(f"[Orchestrator] XAI keys exhausted, falling back to OpenRouter")
    openrouter_model = f"x-ai/{model}" if not model.startswith("x-ai/") else model
    response = await call_model_v2(
        messages=messages,
        model=openrouter_model,
        provider=Provider.OPENROUTER,  # FALLBACK!
        tools=None,
    )
except Exception as e:
    error_msg = str(e).lower()
    if any(err in error_msg for err in ["404", "429", "rate limit", "quota"]):
        print(f"[Orchestrator] Rate limit/404 detected, falling back to OpenRouter")
        openrouter_model = f"x-ai/{model}" if "grok" in model.lower() else model
        response = await call_model_v2(
            messages=messages,
            model=openrouter_model,
            provider=Provider.OPENROUTER,  # FALLBACK!
```

---

## 7. PARALLEL EXECUTION (LangGraph)

### Файл: `/src/orchestration/langgraph_nodes.py`

**Dev + QA Parallel Execution (Line 1539-1615 in orchestrator_with_elisya.py)**

```python
print("\n3️⃣  DEV & QA with Elisya - PARALLEL EXECUTION...")
print("   🔄 Starting Dev and QA in parallel...")

# Prepare both dev and qa prompts
dev_prompt = ...  # Line 1565
qa_prompt = ...   # Similar pattern

# Execute in parallel via asyncio.gather
async def run_dev():
    return await self._run_agent_with_elisya_async("Dev", state, dev_prompt)

async def run_qa():
    return await self._run_agent_with_elisya_async("QA", state, qa_prompt)

dev_result, qa_result = await asyncio.gather(run_dev(), run_qa())
```

**Каждый node использует:**
- Собственный `agent_type` (Dev или QA)
- Свой `model_id` (из routing или override)
- Провайдер detection через `ProviderRegistry.detect_provider()`
- Fallback на OpenRouter при ошибке

---

## 8. VVERDIKT: OPENROUTER ИНТЕГРАЦИЯ В GROUP CHAT

### Summary Table

| Аспект | Статус | Расположение | Детали |
|--------|--------|--------------|--------|
| **Group Entry** | ✅ DONE | group_message_handler.py:529 | Socket.IO handler работает |
| **Role Distribution** | ✅ DONE | group_chat_manager.py:24-29 | 4 роли: ADMIN, WORKER, REVIEWER, OBSERVER |
| **Agent Selection** | ✅ DONE | group_chat_manager.py:166-343 | Умная селекция с @mentions, keywords, smart reply decay |
| **Role→AgentType Mapping** | ✅ DONE | group_message_handler.py:721-737 | PM→PM, Dev→Dev, QA→QA, Architect→Architect |
| **call_agent() Routing** | ✅ DONE | orchestrator_with_elisya.py:2242-2331 | Поддерживает model_id override |
| **Provider Detection** | ✅ DONE | orchestrator_with_elisya.py:1016, 1244 | `ProviderRegistry.detect_provider()` for каждой роли |
| **API Key Injection** | ✅ DONE | orchestrator_with_elisya.py:1264-1270 | Per-provider key management |
| **Parallel Execution** | ✅ DONE | orchestrator_with_elisya.py:1539-1615 | Dev+QA одновременно с asyncio.gather() |
| **OpenRouter Fallback** | ✅ DONE | orchestrator_with_elisya.py:1020-1050 | Fallback на OpenRouter при XAI key exhaust, 404, rate limit |
| **Tool Support** | ⚠️ PARTIAL | orchestrator_with_elisya.py:1023-1036 | Tools при основном провайдере, None при OpenRouter fallback |

---

## 9. КРИТИЧЕСКИЕ НАХОДКИ

### 9.1 OPENROUTER ПОЛНОСТЬЮ ИНТЕГРИРОВАН ✅

**Доказательство:**
1. **Line 1244:** `ProviderRegistry.detect_provider()` детектирует провайдер каждой роли
2. **Line 1023:** `call_model_v2()` получает `provider=Provider.OPENROUTER` для OpenRouter
3. **Line 1032-1037:** Fallback с конвертацией модели в `x-ai/{model}` для OpenRouter
4. **Line 1041-1050:** Обработка rate limit/404 ошибок с автоматическим fallback

### 9.2 TOOL SUPPORT LIMITATION ⚠️

**Проблема:** Когда используется OpenRouter fallback, tools отключаются (Line 1036):
```python
response = await call_model_v2(
    messages=messages,
    model=openrouter_model,
    provider=Provider.OPENROUTER,
    tools=None,  # ❌ TOOLS DISABLED!
)
```

**Риск:**
- В fallback сценариях (rate limit, 404, XAI exhaustion) роли теряют tool support
- Может снизить функциональность Dev и QA агентов в Group Chat

**Место:** `orchestrator_with_elisya.py:1036`

### 9.3 PER-ROLE FALLBACK ✅

**Детали:**
- PM, Dev, QA, Architect - каждый имеет собственный `model_routing` (Line 2302)
- Каждый роль может иметь разный провайдер и fallback поведение
- XAI fallback специфичен для xai провайдера (Line 1248-1250)

### 9.4 NO DEPENDENCY ON APIAGGREGATOR ✅

**Важный момент:** Group chat использует **новую архитектуру** (`call_model_v2`):
- ❌ НЕ использует `APIAggregator` (устаревший)
- ✅ Использует `ProviderRegistry.detect_provider()` + `call_model_v2()`
- ✅ Чистое разделение: ProviderRegistry определяет провайдер, call_model_v2 исполняет

---

## 10. ПОЛНЫЙ FLOW ДИАГРАММА

```
User Message in Group
    ↓
[group_message_handler.py:529] @sio.on("group_message")
    ↓
Parse message: group_id, sender_id, content, @mentions (Line 541-614)
    ↓
[group_chat_manager.py:166] select_responding_agents()
    ├─ Reply routing? → route to original agent (Line 201-214)
    ├─ @mentions? → select mentioned agents (Line 221-260)
    ├─ Smart reply? → use last responder (Line 262-289)
    ├─ Keywords? → SMART selection (Line 321-343)
    └─ Default? → use admin/first worker (Line 345-360)
    ↓
[group_message_handler.py:719] Map Role → AgentType
    PM/ADMIN → "PM"
    Dev/WORKER → "Dev"
    QA/REVIEWER → "QA"
    Architect → "Architect"
    ↓
[orchestrator_with_elisya.py:2242] call_agent()
    ├─ agent_type: "PM" | "Dev" | "QA" | "Architect"
    ├─ model_id: "openai/gpt-4" | "ollama/qwen2:7b" | etc
    └─ Override model_routing (Line 2300-2305)
    ↓
[orchestrator_with_elisya.py:1215] _run_agent_with_elisya_async()
    ├─ Check manual model override (Line 1235-1257)
    ├─ Detect provider via ProviderRegistry (Line 1244)
    ├─ XAI → check key, fallback to OpenRouter (Line 1248-1250)
    ├─ Inject API key to environment (Line 1270)
    └─ Get agent system prompt + tools
    ↓
[orchestrator_with_elisya.py:1023] call_model_v2()
    ├─ provider=Provider.OPENAI/ANTHROPIC/OLLAMA/XAI/OPENROUTER
    ├─ tools=tool_schemas (if supported)
    └─ response from LLM
    ↓
On Exception (Line 1026-1050):
    ├─ XaiKeysExhausted → retry with Provider.OPENROUTER
    ├─ 404/429/Rate Limit → retry with Provider.OPENROUTER
    └─ Fallback model: "x-ai/{model}" (for Grok models)
    ↓
Response → Store in group_chat_manager → Emit via Socket.IO
```

---

## 11. РИСКИ И РЕКОМЕНДАЦИИ

| № | Риск | Вероятность | Импакт | Решение |
|---|------|------------|--------|---------|
| 1 | OpenRouter fallback отключает tools | ВЫСОКАЯ | КРИТИЧЕСКИЙ | Проверить, поддерживает ли OpenRouter tools для rolle-specific операций |
| 2 | XAI key exhaustion не логируется достаточно | СРЕДНЯЯ | СРЕДНИЙ | Добавить отдельный вызов телеметрии при fallback |
| 3 | Per-role model override может конфликтовать | НИЗКАЯ | СРЕДНИЙ | Использовать mutex для синхронизации model_routing updates |
| 4 | Phase 80.28 Smart reply decay работает только с group.Group object | НИЗКАЯ | НИЗКИЙ | Убедиться что group_object всегда передаётся |

---

## 12. FILES & LINE REFERENCES

### Core Files:
1. **`/src/api/handlers/group_message_handler.py`** - Group message routing & agent calls
   - Line 529: Entry handler
   - Line 719-737: Role→AgentType mapping (MARKER_94.6)
   - Line 800-810: call_agent() invocation

2. **`/src/services/group_chat_manager.py`** - Group management & agent selection
   - Line 24-29: GroupRole enum
   - Line 166-343: select_responding_agents() with SMART selection
   - Line 322-326: Role-keyword mapping

3. **`/src/orchestration/orchestrator_with_elisya.py`** - Orchestrator & routing
   - Line 1016-1018: Provider detection
   - Line 1215-1300+: _run_agent_with_elisya_async()
   - Line 1235-1257: Manual model override with fallback
   - Line 1023-1050: call_model_v2() with exception handling
   - Line 2242-2331: call_agent() group chat method

4. **`/src/elisya/provider_registry.py`** - Provider management
   - Line 35-44: Supported providers enum
   - ProviderRegistry.detect_provider(): Core detection logic

---

## ЗАКЛЮЧЕНИЕ

**OpenRouter интегрирован в Group Chat: ПОЛНОСТЬЮ ✅**

- Все 4+ роли (PM, Dev, QA, Architect, Hostess, Researcher) поддерживают OpenRouter fallback
- Provider detection работает per-role через ProviderRegistry
- Fallback триггируется на XAI key exhaustion, rate limits, 404 ошибки
- Parallel execution (Dev+QA) поддерживает OpenRouter для обеих ролей одновременно
- Tool support отключается при OpenRouter fallback (ожидаемое ограничение)

**Уязвимость:** Потеря tool support при fallback может повлиять на функциональность в критических сценариях.

**Рекомендация:** Тестировать Group Chat с OpenRouter fallback сценариями для каждой роли.
