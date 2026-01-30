# ФАЗА 90.9.2: МАТРИЦА ЗАВИСИМОСТЕЙ МАРШРУТИЗАЦИИ

**Статус:** СПРАВОЧНАЯ МАТРИЦА
**Дата:** 2026-01-23

---

## МАТРИЦА ЗАВИСИМОСТЕЙ

### Основная иерархия

```
src/elisya/provider_registry.py (CORE)
├── Используется в: chat_handler.py, llm_call_tool.py, orchestrator_with_elisya.py
├── Экспортирует:
│   ├── class Provider (enum)
│   ├── class BaseProvider (ABC)
│   ├── def detect_provider() [CANONICAL]
│   ├── def call_model_v2()
│   ├── get_registry()
│   └── XaiKeysExhausted exception
└── Зависит от:
    ├── src.orchestration.services.api_key_service
    ├── src.utils.unified_key_manager
    ├── httpx (async HTTP)
    └── ollama (local models)
```

### Слой 2: Маршруты маршрутизации

```
1. user_message_handler.py (SOLO CHAT)
   ├── Импортирует: chat_handler.detect_provider()
   ├── Импортирует: call_model_v2() [из provider_registry]
   ├── Использует: APIKeyService для ротации ключей
   └── Фолбэк: OpenRouter при неудаче

2. group_message_handler.py (GROUP CHAT)
   ├── Вызывает: orchestrator.call_agent(model_id, ...)
   ├── Зависит: group_chat_manager.select_responding_agents()
   └── Не вызывает напрямую: provider detection (делегирует оркестратору)

3. llm_call_tool.py (MCP TOOLS)
   ├── Импортирует: ProviderRegistry.detect_provider() [CANONICAL]
   ├── Вызывает: call_model_v2(provider)
   └── Использует: UNIFIED DETECTION ✅

4. orchestrator_with_elisya.py (ORCHESTRATOR)
   ├── Импортирует: call_model_v2(), Provider
   ├── Использует: INLINE detection (строки 1113-1144) ⚠️
   ├── Использует: _get_routing_for_task() для auto-detection
   └── Вызывает: _call_llm_with_tools_loop()
```

### Слой 3: Сервисы и утилиты

```
api_key_service.py (API KEY MANAGEMENT)
├── Используется в: provider_registry.py (каждый провайдер)
├── Используется в: user_message_handler.py (key rotation)
├── Использует: unified_key_manager.py
└── Экспортирует: get_key(provider), add_key(), remove_key()

unified_key_manager.py (KEY STORAGE)
├── Используется в: api_key_service.py
├── Используется в: provider_registry.py (XaiProvider для ротации)
├── Хранилище: data/config.json
└── Интерфейсы: ProviderType enum, KeyRecord класс

model_router_v2.py (TASK-BASED ROUTING)
├── Используется в: orchestrator_with_elisya.py
├── Функция: _get_routing_for_task()
└── Выходная: {'provider': 'openai', 'model': 'gpt-4o'}

group_chat_manager.py (GROUP MANAGEMENT)
├── Функция: select_responding_agents()
├── Параметры: participants (список с model_id)
├── Не делает: provider detection (делегирует)
└── Использует: orchestrator.call_agent()
```

### Слой 4: FastAPI маршруты

```
main.py (APPLICATION ENTRY)
├── Инициализирует: APIKeyService при startup
├── Socket.IO handlers: register_all_handlers()
├── REST routes: register_all_routers()
└── Инициализирует: GroupChatManager

routes/
├── group_routes.py
│   ├── POST /api/groups
│   ├── GET /api/groups/{group_id}
│   ├── PUT /api/groups/{group_id}
│   ├── POST /api/groups/{group_id}/messages
│   └── Использует: group_message_handler
│
└── debug_routes.py, tree_routes.py, etc.

handlers/
├── user_message_handler.py
├── group_message_handler.py
├── chat_handler.py [WRAPPER]
└── Используют: provider_registry + api_key_service
```

---

## ТАБЛИЦА КРОСС-ССЫЛОК

| Файл | Строки | Ключевая функция | Версия Phase | Статус |
|------|--------|------------------|--------------|--------|
| provider_registry.py | 31-39 | class Provider (enum) | 80.10 | ✅ ACTIVE |
| provider_registry.py | 93-171 | class OpenAIProvider | 80.10 | ✅ ACTIVE |
| provider_registry.py | 174-286 | class AnthropicProvider | 80.10 | ✅ ACTIVE |
| provider_registry.py | 289-402 | class GoogleProvider | 80.10 | ✅ ACTIVE |
| provider_registry.py | 405-548 | class OllamaProvider | 80.5+ | ✅ ACTIVE |
| provider_registry.py | 551-620 | class OpenRouterProvider | 80.10 | ✅ ACTIVE |
| provider_registry.py | 623-726 | class XaiProvider | 80.35+ | ✅ ACTIVE |
| provider_registry.py | 729-783 | class ProviderRegistry | 80.10 | ✅ ACTIVE |
| provider_registry.py | 786-810 | detect_provider() | 90.1.4.1 | ✅ CANONICAL |
| provider_registry.py | 821-893 | call_model_v2() | 80.10 | ✅ ACTIVE |
| chat_handler.py | 35-45 | class ModelProvider (enum) | 64.3 | ✅ LEGACY |
| chat_handler.py | 48-86 | detect_provider() [WRAPPER] | 90.1.4.1 | ✅ UNIFIED |
| llm_call_tool.py | 95-111 | _detect_provider() | 90.1.4.1 | ✅ UNIFIED |
| orchestrator_with_elisya.py | 1113-1144 | Manual model override | 80.10 | ⚠️ INLINE |
| orchestrator_with_elisya.py | 1147 | _get_routing_for_task() | 29 | ✅ AUTO-DETECT |
| orchestrator_with_elisya.py | 1182-1196 | Provider enum conversion | 80.10 | ✅ ACTIVE |
| api_key_service.py | 48-84 | get_key() | 54.1 | ✅ ACTIVE |
| api_key_service.py | 58-70 | provider_map | 80.38 | ✅ COMPLETE |
| api_key_service.py | 193-205 | remove_key() provider_map | 80.38 | ✅ COMPLETE |

---

## ИМПОРТЫ И ИСПОЛЬЗОВАНИЕ

### Кто импортирует provider_registry.py?

```
├── src/api/handlers/user_message_handler.py
│   └── from src.elisya.provider_registry import Provider, call_model_v2
│
├── src/api/handlers/chat_handler.py
│   └── from src.elisya.provider_registry import ProviderRegistry, Provider
│
├── src/mcp/tools/llm_call_tool.py
│   └── from src.elisya.provider_registry import ProviderRegistry
│
├── src/orchestration/orchestrator_with_elisya.py
│   └── from src.elisya.provider_registry import (
│       call_model_v2, Provider, ProviderRegistry, get_registry, XaiKeysExhausted
│   )
│
└── src/agents/ (различные агенты)
    └── Используют call_model_v2() через orchestrator
```

### Кто импортирует api_key_service.py?

```
├── src/elisya/provider_registry.py (каждый провайдер)
│   └── from src.orchestration.services.api_key_service import APIKeyService
│
├── src/api/handlers/user_message_handler.py
│   └── Используется для ротации ключей OpenRouter
│
├── main.py
│   └── Инициализируется при startup
│
└── src/api/routes/ (API ключ управление)
    └── APIKeyService().get_key(), add_key(), remove_key()
```

---

## ГЛУБОКИЕ ЗАВИСИМОСТИ

### call_model_v2() DEPENDENCY TREE

```
call_model_v2(messages, model, provider, tools)
│
├─ ProviderRegistry.get_registry()
│  └─ Singleton pattern → Returns ProviderRegistry instance
│
├─ registry.get(provider)
│  └─ Returns BaseProvider instance (OpenAI, Anthropic, etc.)
│
├─ provider.supports_tools (property check)
│
└─ provider.call(messages, model, tools, **kwargs)
   │
   ├─ [For each provider type]
   │  ├─ OpenAIProvider.call()
   │  │  ├─ APIKeyService().get_key('openai')
   │  │  ├─ httpx.AsyncClient().post(https://api.openai.com/...)
   │  │  └─ Parse response + tool_calls
   │  │
   │  ├─ AnthropicProvider.call()
   │  │  ├─ APIKeyService().get_key('anthropic')
   │  │  ├─ httpx.AsyncClient().post(https://api.anthropic.com/...)
   │  │  └─ Parse response + tool_use format
   │  │
   │  ├─ OllamaProvider.call()
   │  │  ├─ Check health: GET http://localhost:11434/api/tags
   │  │  ├─ Check _model_supports_tools(model_name)
   │  │  ├─ ollama.chat() in executor
   │  │  └─ Retry without tools if error
   │  │
   │  ├─ XaiProvider.call()
   │  │  ├─ APIKeyService().get_key('xai')
   │  │  ├─ httpx.AsyncClient().post(https://api.x.ai/v1/chat/completions)
   │  │  ├─ Handle 403 → key_manager.report_failure()
   │  │  ├─ Rotate to next key
   │  │  └─ If all 403 → raise XaiKeysExhausted()
   │  │     └─ [FALLBACK] OpenRouterProvider.call(model="x-ai/...")
   │  │
   │  └─ [Others: GoogleProvider, OpenRouterProvider]
   │
   └─ Standardized response:
      {
          "message": {"content": str, "tool_calls": [...], "role": str},
          "model": str,
          "provider": str,
          "usage": {...}
      }
```

---

## CIRCULAR DEPENDENCIES - ПРОВЕРКА

### Есть ли циклические зависимости?

```
✅ NO - Архитектура ЧИСТАЯ

Почему:
1. provider_registry.py не импортирует orchestrator_with_elisya.py
2. orchestrator_with_elisya.py импортирует provider_registry.py (однонаправленно)
3. api_key_service.py не импортирует provider_registry.py
4. provider_registry.py импортирует api_key_service.py (однонаправленно)
5. Все маршруты маршрутизации (Solo, Group, MCP) → provider_registry.py (star pattern)

Граф зависимостей:
    provider_registry.py ← orchestrator_with_elisya.py
         ↑
         └─ user_message_handler.py
         └─ chat_handler.py
         └─ llm_call_tool.py
         └─ group_message_handler.py

    api_key_service.py ← provider_registry.py
         ↑
         └─ main.py
         └─ API routes

    model_router_v2.py ← orchestrator_with_elisya.py
    group_chat_manager.py ← group_message_handler.py
```

**Заключение:** Архитектура ACYCLIC, хорошая для тестирования и поддержки.

---

## ВРЕМЕННАЯ СЛОЖНОСТЬ МАРШРУТИЗАЦИИ

### Для Solo Chat

```
user sends message
  └─ detect_provider(model_name)        O(n) where n = length of model_name
     ├─ ProviderRegistry.detect_provider()  O(1) - pattern matching
     └─ return ModelProvider enum         O(1)
  └─ call_model_v2()                      O(1) - registry lookup
     └─ provider.call()                   O(HTTP request time) ≈ 2-30s
```

**Итого:** O(1) для обнаружения, O(HTTP) для вызова

### Для Group Chat

```
user sends to group
  └─ select_responding_agents()           O(p) where p = number of participants
     └─ orchestrator.call_agent()         O(a) × [O(detect) + O(call)]
        where a = number of responding agents
     └─ Parallel execution               O(a) concurrent
```

**Итого:** O(p × a × HTTP time) sequential, O(a × HTTP time) parallel

### Для MCP

```
MCP tool calls
  └─ _detect_provider(model)              O(1) - pattern matching
  └─ call_model_v2()                      O(1) - registry lookup
     └─ provider.call()                   O(HTTP request time)
```

**Итого:** O(HTTP) dominant

---

## КОНФЛИКТЫ И РАЗРЕШЕНИЕ

### Конфликт 1: Dual XAI detection

**Место:**
- orchestrator_with_elisya.py (line 1121)
- provider_registry.py/XaiProvider (line 677)

**Проблема:** Две проверки ключа xai
**Разрешение:** Удалить из orchestrator, оставить в XaiProvider

### Конфликт 2: Model format ambiguity

**Место:** group chat participants

**Проблема:** model_id может быть "gpt-4o" или "openai/gpt-4o" или даже "claude-opus"
**Разрешение:** Стандартизировать на "provider/model" или auto-prefix

### Конфликт 3: GEMINI vs GOOGLE

**Место:** provider_registry.py, api_key_service.py

**Проблема:**
- config.json хранит ключ как "gemini"
- Provider enum имеет оба GOOGLE и GEMINI
- Alias создан: `self.register(Provider.GEMINI, google_provider)`

**Разрешение:** ✅ DONE - alias in ProviderRegistry (line 759)

---

## ВЕРСИОНИРОВАНИЕ И ФАЗЫ

### Phase-by-phase evolution

```
Phase 29: Task-based routing (_get_routing_for_task)
Phase 54.1: API Key Service refactor
Phase 55: Approval + Tool support
Phase 56: Model Registry + Discovery
Phase 57: API Key UI + Detection
Phase 60: LangGraph + Streaming
Phase 64.3: Chat Handler extraction
Phase 80.5: Ollama tool support checking
Phase 80.10: Provider Registry architecture ← MAJOR
Phase 80.35: xAI/Grok integration
Phase 80.37: xAI fallback to OpenRouter
Phase 80.38: xAI key detection fix
Phase 80.39: XaiKeysExhausted exception
Phase 80.40: Fixed singleton + attributes
Phase 80.41: GEMINI alias for config.json
Phase 80.42: Google key lookup for gemini
Phase 90.1.4.1: UNIFIED detect_provider ← CURRENT
Phase 90.1.4.2: xAI key rotation + retry
Phase 90.4.0: VETKA chat streaming for call_model
Phase 90.5.0: Qdrant connection wait in lifespan
```

---

**Статус матрицы:** ПОЛНАЯ И АКТУАЛЬНАЯ
**Дата создания:** 2026-01-23
**Версия:** 1.0
