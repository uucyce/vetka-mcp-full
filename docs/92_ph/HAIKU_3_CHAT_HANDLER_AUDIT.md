# HAIKU 3: Chat Handler Audit для VETKA Унификации
**Date:** 2026-01-25
**Status:** COMPLETE
**Focus:** Аудит двух типов чатов (Solo vs Group) и их обработчиков

---

## 📊 EXECUTIVE SUMMARY

VETKA имеет четко разделенную архитектуру для двух типов чатов:

| Аспект | Solo Chat | Group Chat |
|--------|-----------|-----------|
| **Handler File** | `user_message_handler.py` | `group_message_handler.py` |
| **Socket Event** | `user_message` | `group_message` |
| **LLM Call Path** | `agent.call_llm()` (via agent instance) | `orchestrator.call_agent()` (agent type routing) |
| **Key Difference** | Direct agent call / streaming | Orchestrator with Elisya context + agent chain |
| **Роли** | Фиксированные (PM, Dev, QA) | Динамические (в группе) |

**ГЛАВНОЕ ОТКРЫТИЕ:**
- **Solo chat НЕ использует orchestrator** — вызывает agent.call_llm() напрямую
- **Group chat использует orchestrator** — полная Elisya интеграция
- **Обе пути идут в provider_registry** для модели, но на разных уровнях

---

## 🔗 CALL GRAPH: Где вызывается call_model

### 1. SOLO CHAT PATH (user_message_handler.py)

```
User sends "user_message" socket event
    ↓
handle_user_message() in user_message_handler.py (line 150)
    ↓
┌─────────────────────────────────────────────────────────────┐
│ BRANCH 1: Direct Model Call (if model override)             │
│ lines 237-754                                               │
│                                                              │
│ if requested_model:                                         │
│   - Ollama local: call ollama.chat() directly (line 356)    │
│   - OpenRouter: httpx.post() directly (line 666)            │
│                                                              │
│ ❌ NO call_model() or orchestrator involvement               │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ BRANCH 2: @Mention Direct Model (if @model specified)       │
│ lines 757-1133                                              │
│                                                              │
│ if parsed_mentions["mode"] == "single" and models:          │
│   - Ollama: ollama.chat() directly (line 901)               │
│   - OpenRouter: requests.post() directly (line 1008)        │
│                                                              │
│ ❌ NO call_model() or orchestrator involvement               │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ BRANCH 3: Agent Chain (DEFAULT path)                        │
│ lines 1154-2100+                                            │
│                                                              │
│ for agent_name in agents_to_call:                           │
│   agent_instance = agents[agent_name]["instance"]           │
│   response = await executor(                                │
│     agent_instance.call_llm(prompt, max_tokens)  (line 1764)│
│   )                                                          │
│                                                              │
│ ❌ NO call_model() — uses agent.call_llm() internally        │
│ ❌ agent.call_llm() is sync, no orchestrator                │
└─────────────────────────────────────────────────────────────┘

AGENT.CALL_LLM() IMPLEMENTATION:
  - Location: src/agents/base_agent.py
  - Internally calls provider_registry or api_aggregator (NOT direct!)
  - Each agent has its own model selection logic
```

### 2. GROUP CHAT PATH (group_message_handler.py)

```
User sends "group_message" socket event
    ↓
handle_group_message() in group_message_handler.py (line 530)
    ↓
orchestrator = get_orchestrator() (line 635)
    ↓
┌─────────────────────────────────────────────────────────────┐
│ HOSTESS ROUTING (REMOVED in Phase 57.8.2)                   │
│ Previously: route_through_hostess() (lines 222-399)         │
│ Currently: Disabled for performance                         │
└─────────────────────────────────────────────────────────────┘
    ↓
select_responding_agents() (line 663)
    ↓
for participant in participants_to_respond:
    orchestrator.call_agent(
        agent_type="Dev",  # or PM, QA, Architect, Researcher
        model_id="model_name",
        prompt=prompt,
        context={...}
    ) (lines 793-803)
    ↓
┌─────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR.CALL_AGENT() PATH                              │
│ Location: src/orchestration/orchestrator_with_elisya.py     │
│                                                              │
│ Inside orchestrator.call_agent():                           │
│   1. Build Elisya context                                   │
│   2. Call model via provider_registry.call_model_v2()      │
│      (line 45: from src.elisya.provider_registry import...) │
│   3. Handle tools, streaming                                │
│   4. Return formatted response                              │
│                                                              │
│ ✅ Uses provider_registry (MODERN PATH)                     │
│ ✅ Full Elisya integration + context fusion                 │
└─────────────────────────────────────────────────────────────┘
```

### 3. PROVIDER REGISTRY FLOW (Both Paths Eventually)

```
provider_registry.call_model_v2() [MODERN - Phase 80.10+]
    ↓
  ├─ OpenAI → OpenAIProvider.call()
  ├─ Anthropic → AnthropicProvider.call()
  ├─ Google/Gemini → GoogleProvider.call()
  ├─ Ollama → OllamaProvider.call()
  ├─ OpenRouter → OpenRouterProvider.call()
  └─ XAI (Grok) → XaiProvider.call()
         ↓
     Phase 80.39: If xai_key exhausted (403)
         ↓ (XaiKeysExhausted exception)
         ↓
     Fallback to OpenRouter (Phase 80.37, 80.40)

LOCATION: src/elisya/provider_registry.py
  - Line 28: XaiKeysExhausted exception definition
  - Line 904: "Phase 80.39: All xai keys got 403, fallback to OpenRouter"
```

---

## 📋 РАЗЛИЧИЯ SOLO vs GROUP CHAT

### SOLO CHAT
```python
# Direct Agent Call (line 1764 in user_message_handler.py)
response_text = await loop.run_in_executor(
    None,
    lambda: agent_instance.call_llm(
        prompt=full_prompt,
        max_tokens=max_tokens
    ),
)

# NO Elisya context fusion
# NO streaming support
# NO chain context from orchestrator
# NO proper error handling with fallbacks
```

### GROUP CHAT
```python
# Orchestrator Call (line 793 in group_message_handler.py)
result = await asyncio.wait_for(
    orchestrator.call_agent(
        agent_type=agent_type,
        model_id=model_id,
        prompt=prompt,
        context={
            "group_id": group_id,
            "group_name": group["name"],
            "agent_id": agent_id,
            "display_name": display_name,
        },
    ),
    timeout=120.0,
)

# ✅ Full Elisya context
# ✅ CAM metrics
# ✅ Semantic search integration
# ✅ Proper key rotation (Phase 80.37)
# ✅ XAI fallback (Phase 80.39, 80.40)
```

### KEY DIFFERENCES TABLE

| Feature | Solo | Group |
|---------|------|-------|
| Context Builder | Basic rich_context | Full Elisya middleware |
| Agent Selection | Pre-selected (PM/Dev/QA) | Dynamic via select_responding_agents |
| LLM Path | agent.call_llm() → provider_registry | orchestrator.call_agent() → provider_registry |
| Key Rotation | Manual in user_message_handler | Automatic in orchestrator + APIKeyService |
| XAI Fallback | NOT implemented | Yes (Phase 80.37-80.40) |
| Streaming | Via httpx for OpenRouter only | Full orchestrator support |
| Error Handling | Try/except + manual retry | Orchestrator handles (120s timeout) |
| Response Format | Direct text | Dict with {status, output} |

---

## 🏷️ ПОЛНЫЙ СПИСОК МАРКЕРОВ И ФАЗА

### CHAT_HANDLER.PY (src/api/handlers/chat_handler.py)

| Маркер | Строка | Фаза | Описание |
|--------|--------|------|---------|
| `MARKER_90.1.4.1_START` | 56 | Phase 90.1.4.1 | Use canonical detect_provider from provider_registry |
| `MARKER_90.1.4.1_END` | 87 | Phase 90.1.4.1 | End canonical provider detection |
| Phase comment | 92 | Phase 60.4 | Detect if this is a local Ollama model (DEPRECATED) |
| Phase comment | 165 | Phase 80.5 | Tool support detection to avoid lightweight model errors |
| Phase comment | 182 | Phase 80.5 | Models that don't support tools |
| Phase comment | 228 | Phase 80.5 | If tools error, retry without tools |

### USER_MESSAGE_HANDLER.PY (src/api/handlers/user_message_handler.py)

| Маркер | Строка | Фаза | Описание |
|--------|--------|------|---------|
| @phase | 6 | Phase 64.5 | God Object Split Complete |
| Phase comment | 43 | Phase 57.9 | Session state for pending API keys |
| Phase comment | 74 | Phase 51.1 | Chat History Integration |
| Phase comment | 77 | Phase 51.4 | Message Surprise - CAM event emission |
| Phase comment | 81 | Phase 64.1 | Extracted pure utility functions |
| Phase comment | 91 | Phase 64.2 | Extracted streaming handler |
| Phase comment | 94 | Phase 64.3 | Extracted chat helpers |
| Phase comment | 104 | Phase 64.4 | Extracted workflow helpers |
| Phase comment | 188 | Phase 48.1 | Model routing from client |
| Phase comment | 233 | Phase 48.2 | Fixed to use SecureKeyManager |
| Phase comment | 234 | Phase 60.4 | Fixed to route local Ollama models correctly |
| Phase comment | 240 | Phase 64.3 | Use extracted helper for model detection |
| Phase comment | 260 | Phase 60.4 | Handle local Ollama models |
| Phase comment | 268 | Phase 51.1 | Load chat history |
| Phase comment | 306-307 | Phase 73.6 | Pass session_id for cold start legend detection |
| Phase comment | 315 | Phase 64.5 | Save user message BEFORE model call |
| Phase comment | 406 | Phase 51.4 | Emit message_sent event for surprise calculation |
| Phase comment | 445 | Phase 48.2 | Use SecureKeyManager for API key |
| Phase comment | 446 | Phase 57.11 | Use paid key by default, retry with rotation |
| Phase comment | 473 | Phase 51.1 | Load chat history |
| Phase comment | 509-510 | Phase 73.6 | Pass session_id for legend detection |
| Phase comment | 518 | Phase 64.5 | Save user message BEFORE model call |
| Phase comment | 526 | Phase 64.3 | Use extracted helper for prompt building |
| Phase comment | 538 | Phase 49.1 | Streaming with fallback |
| Phase comment | 581 | Phase 49.1 | Handle 429 rate limit |
| Phase comment | 602 | Phase 57.11 | Retry with next key on auth/payment errors |
| Phase comment | 654 | Phase 49.1 | Fallback to non-streaming if needed |
| Phase comment | 721 | Phase 51.4 | Emit message_sent event |
| Phase comment | 784 | Phase 44.6 | Frontend expects 'content' field |
| Phase comment | 1179 | Phase 57.9 | Check if user responding to pending key question |
| Phase comment | 1497 | Phase 57.9 | @hostess uses Hostess routing |
| Phase comment | 1502 | Phase 57.9 | If @hostess mentioned, let Hostess process |
| Phase comment | 1555 | Phase 57.9 | API Key handling actions |
| Phase comment | 1644 | Phase 57.9 | Unknown Hostess action - Hostess responds |
| Phase comment | 1719 | Phase 92.4 | Unlimited responses |
| Phase comment | 1833 | Phase 44.6 | Fixed to emit both agent_message and chat_response |
| Phase comment | 1897 | Phase 51.4 | Emit message_sent event |
| Phase comment | 2021 | Phase 44.6 | Emit chat_response for summary |
| Phase comment | 2031 | Phase 44.6 | Emit chat_response for summary |

### GROUP_MESSAGE_HANDLER.PY (src/api/handlers/group_message_handler.py)

| Маркер | Строка | Фаза | Описание |
|--------|--------|------|---------|
| @phase | 6 | Phase 80.13 | MCP @mention Routing |
| Phase comment | 14 | Phase 57.8 | Hostess as intelligent router for groups |
| Phase comment | 15 | Phase 80.13 | MCP agent @mention routing |
| Phase comment | 17 | Phase 57.4 | Uses orchestrator.call_agent() instead of direct HTTP |
| Phase comment | 20 | Phase 57.8 | Hostess as group router |
| Phase comment | 25 | Phase 80.13 | MCP Agent @mention routing |
| Phase comment | 105 | Phase 80.13 | Notify MCP agents when @mentioned |
| Phase comment | 140 | Phase 80.13 | Detected MCP agent mentions |
| Phase comment | 227 | Phase 57.8 | Hostess as the group orchestrator |
| Phase comment | 413 | Phase 57.8 | Hostess closes the loop with summary |
| Phase comment | 505 | Phase 57.4 | Uses orchestrator for LLM calls |
| Phase comment | 506 | Phase 57.8 | Hostess as intelligent router + summary |
| Phase comment | 548 | Phase 80.7 | Message ID being replied to |
| Phase comment | 551 | Phase 80.11 | Pinned files for context |
| Phase comment | 561 | Phase 80.28 | Get Group object for smart reply decay |
| Phase comment | 570 | Phase 80.11 | Include pinned_files in metadata |
| Phase comment | 588 | Phase 80.28 | Increment decay counter on user messages |
| Phase comment | 592 | Phase 80.28 | User message, decay now X |
| Phase comment | 595 | Phase 80.13 | Check for MCP agent @mentions |
| Phase comment | 604 | Phase 80.13 | Notify MCP agents |
| Phase comment | 614 | Phase 74.8 | Save user message to chat_history |
| Phase comment | 618 | Phase 74.10 | Strip handles trailing spaces |
| Phase comment | 634 | Phase 57.4 | Get orchestrator for proper LLM routing |
| Phase comment | 644 | Phase 80.7 | Find original agent if this is a reply |
| Phase comment | 656 | Phase 80.7 | Reply to message from agent |
| Phase comment | 660 | Phase 57.7 | Use smart agent selection |
| Phase comment | 667 | Phase 80.7 | Pass reply_to_agent for proper routing |
| Phase comment | 668 | Phase 80.28 | Pass group_object for smart reply decay |
| Phase comment | 671 | Phase 57.8.2 | REMOVED Hostess routing - слишком медленная |
| Phase comment | 672 | Phase 57.8.2 | Полагаемся на select_responding_agents + @mentions |
| Phase comment | 732 | Phase 57.7 | Track previous outputs for chain context |
| Phase comment | 758 | Phase 57.7 | Build role-specific prompt with chain context |
| Phase comment | 785 | Phase 57.4 | Use orchestrator.call_agent() for proper Elisya |
| Phase comment | 787 | Phase 57.4 | Calling orchestrator.call_agent() |
| Phase comment | 855 | Phase 80.28 | Track last responder for smart reply decay |
| Phase comment | 856 | Phase 80.28 | last_responder_id, decay reset |
| Phase comment | 865 | Phase 74.8 | Save agent response to chat_history |
| Phase comment | 891 | Phase 57.8 | Check for @mentions in agent response |
| Phase comment | 975 | Phase 57.8.2 | REMOVED Hostess summary - слишком медленная |
| Phase comment | 976 | Phase 57.8.2 | Hostess получает весь контекст пассивно |

### ORCHESTRATOR_WITH_ELISYA.PY (src/orchestration/orchestrator_with_elisya.py)

| Маркер | Строка | Фаза | Описание |
|--------|--------|------|---------|
| @phase | 6 | Phase 35 | EvalAgent + CAM integrated |
| Phase comment | 35 | Phase 17-L | AGENT TOOLS IMPORTS |
| Phase comment | 43 | Phase 80.10 | Use Provider Registry for clean provider routing |
| Phase comment | 44-50 | Phase 90.1.4.2 | Handle XAI key exhaustion (XaiKeysExhausted) |
| Phase comment | 52 | Phase 80.10 | Keep old call_model as fallback |
| Phase comment | 1247 | Phase 80.37 | Check if xai key exists, fallback to openrouter |
| Phase comment | 1251 | Phase 80.37 | xai key not found, using OpenRouter fallback |

---

## 🌊 XAI FALLBACK LOGIC (Phase 80.37, 80.39, 80.40)

### LOCATION CHAIN:
1. **provider_registry.py** (src/elisya/provider_registry.py)
   - Line 28: `XaiKeysExhausted` exception definition
   - Line 904: "Phase 80.39: All xai keys got 403, fallback to OpenRouter"

2. **orchestrator_with_elisya.py** (src/orchestration/orchestrator_with_elisya.py)
   - Line 44-50: Import XaiKeysExhausted from provider_registry
   - Line 1247: "Phase 80.37: Check if xai key exists, fallback to openrouter"
   - Line 1251: "xai key not found, using OpenRouter fallback"

### FLOW:
```
user/group requests xAI model
    ↓
orchestrator.call_agent() → provider_registry.call_model_v2()
    ↓
XaiProvider.call()
    ↓
Try xAI API with key
    ↓
┌─────────────────────────────────────────────────┐
│ Success: Return response                        │
│ 403 Forbidden: Raise XaiKeysExhausted (80.39)   │
│ Other Error: Raise exception                    │
└─────────────────────────────────────────────────┘
    ↓
catch XaiKeysExhausted:
    Phase 80.40: Fallback to OpenRouter
    - Mark all xai keys as exhausted
    - Retry call with OpenRouter provider
    - User gets response via OpenRouter
```

---

## 🎯 CURRENT UI PATH (Which Provider?)

### WHERE THE UI CALLS (Based on Code Analysis)

**For Solo Chat:**
```
client → user_message socket event
→ user_message_handler.py (line 150)
→ BRANCH 1: requested_model (lines 237-754)
  → Direct API call (ollama.chat or httpx.post)
  → NO orchestrator, NO provider_registry

→ BRANCH 2: @mention model (lines 757-1133)
  → Direct API call (ollama.chat or requests.post)
  → NO orchestrator, NO provider_registry

→ BRANCH 3: Agent chain (default) (lines 1154+)
  → agent.call_llm() (line 1764)
  → agent internally uses provider (varies by agent)
  → May use provider_registry or api_aggregator_v3
```

**For Group Chat:**
```
client → group_message socket event
→ group_message_handler.py (line 530)
→ orchestrator.call_agent() (line 793)
→ orchestrator → provider_registry.call_model_v2() (line 45)
→ Uses clean provider interface (MODERN PATH)
```

### CURRENT STATUS:
- **Solo chat: MIXED** (not unified, some paths use direct API, some use provider)
- **Group chat: UNIFIED** (uses provider_registry via orchestrator)
- **UI doesn't directly call** provider_registry or api_aggregator
- **All paths eventually use providers** (directly or indirectly)

---

## 📊 ROLE FORMATTING

### SOLO CHAT (user_message_handler.py)
```python
# Fixed roles
agents_to_call = ["PM", "Dev", "QA"]  # Default

# Agent instance from registry
agent_instance = agents[agent_name]["instance"]
system_prompt = agents[agent_name]["system_prompt"]

# Call directly
response = agent_instance.call_llm(prompt, max_tokens)
```

### GROUP CHAT (group_message_handler.py)
```python
# Dynamic role from participant
agent_type_map = {
    "PM": "PM",
    "Dev": "Dev",
    "QA": "QA",
    "Architect": "Architect",
    "Researcher": "Researcher",  # Phase 57.8
}
agent_type = agent_type_map.get(display_name, "Dev")

# Get system prompt from role_prompts
system_prompt = get_agent_prompt(agent_type)

# Call via orchestrator
result = orchestrator.call_agent(
    agent_type=agent_type,
    model_id=model_id,
    prompt=full_prompt,
    context={...}
)
```

---

## 🔍 MCP TOOLS INTEGRATION

### MCP AGENT ROUTING (Phase 80.13)

**Location:** group_message_handler.py, lines 71-215

**Supported MCP Agents:**
```python
MCP_AGENTS = {
    "browser_haiku": {
        "name": "Browser Haiku",
        "endpoint": "mcp/browser_haiku",
        "role": "Tester",
        "aliases": ["browserhaiku", "browser", "haiku"],
    },
    "claude_code": {
        "name": "Claude Code",
        "endpoint": "mcp/claude_code",
        "role": "Executor",
        "aliases": ["claudecode", "claude", "code"],
    },
}
```

**Detection & Notification Flow:**
1. Parse user message for @mentions (line 598-602)
2. Find MCP agent matches (lines 119-134)
3. Emit `mcp_mention` socket event (line 160)
4. Store in team_messages buffer for API access (line 205)
5. MCP agents listen to socket events and respond

---

## 📈 ELISYA INTEGRATION DIFFERENCES

### SOLO CHAT
```python
# Basic rich context (no Elisya middleware)
rich_context = sync_get_rich_context(node_path)
context_for_llm = format_context_for_agent(rich_context, "generic")

# No Elisya state, no middleware, no CAM
```

### GROUP CHAT
```python
# Full Elisya integration via orchestrator
orchestrator.call_agent(
    agent_type="Dev",
    model_id="model",
    prompt=prompt,
    context={"group_id": group_id, "display_name": display_name}
)

# Inside orchestrator:
# 1. Build ElisyaState from context
# 2. Apply ElisyaMiddleware for context fusion
# 3. Use ModelRouter for intelligent selection
# 4. CAM metrics collected
# 5. Semantic search integration available
```

---

## ⚠️ KEY FINDINGS

### ISSUE 1: Solo Chat NOT Using Orchestrator
- **Impact:** Solo chat misses XAI fallback (80.37, 80.39, 80.40)
- **Impact:** Solo chat misses Elisya context fusion
- **Impact:** Solo chat doesn't have CAM metrics
- **Location:** user_message_handler.py, lines 1764 (agent.call_llm())
- **Status:** KNOWN - Phase 64 split intentionally separated solo from orchestrator

### ISSUE 2: Direct API Calls in Solo Chat
- **Impact:** Lines 237-754 and 757-1133 bypass all abstraction
- **Impact:** Manual retry logic duplicated from orchestrator
- **Impact:** Key rotation NOT integrated with APIKeyService
- **Location:** user_message_handler.py, lines 356, 666, 901, 1008
- **Status:** DESIGN CHOICE - for simplicity/speed

### ISSUE 3: Hostess Routing REMOVED in Phase 57.8.2
- **Note:** Was too slow, affecting group chat performance
- **Note:** Hostess still available for camera focus and context (passive)
- **Note:** Delegation now via @mentions instead of automatic routing
- **Location:** group_message_handler.py, lines 671-673

### FINDING 4: api_aggregator_v3 as LEGACY Fallback
- **Status:** Kept for backwards compatibility (line 52-53, orchestrator_with_elisya.py)
- **Status:** `call_model as call_model_legacy` imported but rarely used
- **Status:** provider_registry.call_model_v2() is PREFERRED modern path

---

## 🎬 RECOMMENDATIONS FOR UNIFICATION

1. **Bring Solo Chat to Orchestrator**
   - Replace agent.call_llm() with orchestrator.call_agent()
   - Would inherit: XAI fallback, Elisya context, CAM metrics
   - Estimated effort: MEDIUM (requires refactoring agent instance handling)

2. **Unify Key Rotation**
   - Both solo/group should use APIKeyService (with cached KeyManager)
   - Remove manual key rotation from user_message_handler.py
   - Estimated effort: SMALL

3. **Use provider_registry for ALL calls**
   - Remove direct ollama.chat() and httpx.post() calls
   - Keep api_aggregator_v3 only as legacy fallback
   - Estimated effort: MEDIUM

4. **Standardize Response Format**
   - Both solo/group should return {status, output} from orchestrator
   - Remove string-based response checking
   - Estimated effort: SMALL

---

## 📝 FILES AUDIT SUMMARY

| File | Lines | Key Paths | Status |
|------|-------|-----------|--------|
| `chat_handler.py` | 467 | Model detection, prompt building, Ollama/OpenRouter calls | Extracted helper module |
| `user_message_handler.py` | 2120+ | Main solo chat handler, agent chain, direct model calls | God object, needs refactor |
| `group_message_handler.py` | 994 | Group routing, orchestrator calls, MCP mentions | Modern architecture |
| `orchestrator_with_elisya.py` | 2000+ | Elisya integration, agent orchestration, provider routing | Production-ready |
| `provider_registry.py` | 1000+ | Provider interface, XAI fallback, clean API | Modern architecture |

---

## 🔚 CONCLUSION

VETKA's chat handlers show clear architectural evolution:
- **Phase 64:** Split god object into specialized handlers
- **Phase 80.13:** Added MCP agent support for groups
- **Phase 80.37-80.40:** Added XAI with OpenRouter fallback
- **Phase 90.1.4.1:** Unified provider detection

**Current state:** Dual-path system working correctly, but not fully unified.
**Next step:** Bring solo chat into orchestrator for full Elisya integration.

---

**Generated by:** Haiku 3 Agent
**Confidence:** HIGH (code analysis + execution paths verified)
**Review recommended:** YES - for unification strategy before Phase 93
