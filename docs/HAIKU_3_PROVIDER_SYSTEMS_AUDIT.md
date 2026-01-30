# HAIKU 3: Provider Systems Comparison Audit

**Дата:** 2026-01-26
**Objective:** Определить, какая система провайдеров реально используется в production

---

## 1. ProviderRegistry (provider_registry.py)

**Статус:** PRODUCTION SYSTEM ✅

### OpenRouterProvider
- **Location:** Line 684-798
- **Class:** `OpenRouterProvider(BaseProvider)`
- **call() method:** FULLY IMPLEMENTED (Line 695-798)

### Implementation Details
```python
# Line 684-688: Class definition
class OpenRouterProvider(BaseProvider):
    """OpenRouter API provider (aggregator)"""

    @property
    def supports_tools(self) -> bool:
        return False  # OpenRouter has limited tool support
```

### Key Features
- Полная async поддержка (`async def call()`)
- Авторотация ключей с 24h cooldown (MARKER_93.4, Line 748-781)
- Обработка 401/402/403 ошибок (Line 749-760)
- Очистка модельных имён (Line 730-732)
- SSE streaming (Line 1580-1677 через `_stream_openrouter()`)
- Fallback на OpenRouter при XAI 403 (Phase 80.39, Line 887-895)

### Global Singleton
- **Line 1046:** `_registry = ProviderRegistry()`
- **Line 1049-1051:** `get_registry()` function

---

## 2. APIAggregator (api_aggregator_v3.py)

**Статус:** LEGACY FALLBACK SYSTEM ⚠️

### OpenRouterProvider
- **Location:** Line 180-182
- **Class:** `class OpenRouterProvider(APIProvider): pass`
- **generate() method:** NOT IMPLEMENTED (STUB)

### Status
```python
# Line 180-182: EMPTY IMPLEMENTATION
class OpenRouterProvider(APIProvider):
    # ... (Assuming original implementation)
    pass
```

### What's Actually Implemented
- `call_model()` function (Line 278-475) - LEGACY версия
- Ollama поддержка (Line 394-433)
- Direct API calls через api_gateway (Line 363-391)
- Streaming через `call_model_stream()` (Line 481-580)

### Integration Points
- **Line 60:** `HOST_HAS_OLLAMA` - используется для streaming решений
- **Line 100:** `OPENROUTER_API_KEY` - загружается но не используется в OpenRouterProvider
- **Line 438-441:** Fallback на Ollama для OpenRouter моделей

---

## 3. APIGateway (api_gateway.py)

**Статус:** LEGACY INFRASTRUCTURE ⚠️

### Direct API Functions
- **call_openai_direct()** (Line 635-689) - IMPLEMENTED
- **call_anthropic_direct()** (Line 692-775) - IMPLEMENTED
- **call_google_direct()** (Line 778-865) - IMPLEMENTED

### _call_openrouter() method
- **Location:** Line 395-441
- **Status:** IMPLEMENTED (sync version using requests library)
- **Used by:** API Gateway only (не используется в production flow)

### Key Details
- Synchronous API (использует `requests`, не `async/await`)
- Используется только через `APIGateway` class
- Direct функции перехватывают модельные вызовы из api_aggregator_v3

### Who Uses APIGateway
- **Line 243:** `src/initialization/dependency_check.py` - инициализирует
- **Line 192-193:** `src/initialization/components_init.py` - создаёт экземпляр
- **NOT используется** напрямую в основных обработчиках сообщений

---

## 4. Usage Matrix - KTO ISPOLZUET CHE?

### user_message_handler.py (Line 62-68)
```python
from src.elisya.provider_registry import (
    call_model_v2,           ✅ PRODUCTION
    call_model_v2_stream,    ✅ PRODUCTION
    Provider,                ✅ PRODUCTION
    XaiKeysExhausted,       ✅ PRODUCTION
)
```
**Использование:** `call_model_v2()` на Line 363, 537, 559, 789, 871, 882

### orchestrator_with_elisya.py (Line 44-50)
```python
from src.elisya.provider_registry import (
    call_model_v2,           ✅ PRODUCTION
    Provider,                ✅ PRODUCTION
    ProviderRegistry,        ✅ PRODUCTION
    get_registry,           ✅ PRODUCTION
)
```
**Использование:** `call_model_v2()` на Line 1023, 1032 (основной flow)

### streaming_handler.py (Line 59)
```python
from src.elisya.api_aggregator_v3 import call_model_stream  ⚠️ LEGACY
```
**Использование:** `call_model_stream()` на Line 74

### chat_handler.py (Line 62)
```python
from src.elisya.provider_registry import ProviderRegistry, Provider  ✅ PRODUCTION
```

### mcp/tools/llm_call_tool.py (Line 271)
```python
from src.elisya.provider_registry import call_model_v2, Provider  ✅ PRODUCTION
```

### di_container.py (Line 34)
```python
from src.elisya.api_aggregator_v3 import HOST_HAS_OLLAMA  ⚠️ LEGACY (info only)
```

### opencode_bridge/open_router_bridge.py (Line 15)
```python
from src.elisya.provider_registry import ProviderRegistry, Provider, call_model_v2
```
**Использование:** `call_model_v2()` для OpenRouter

### agents/arc_solver_agent.py (Line 1115)
```python
from src.elisya.api_aggregator_v3 import APIAggregator  ⚠️ LEGACY (but NOT USED)
```
Только импорт, фактического использования нет

---

## 5. Data Flow Analysis

### Production Flow (call_model_v2)
```
user_message_handler.py → call_model_v2()
    ↓
provider_registry.py:1054 (call_model_v2 function)
    ↓
ProviderRegistry.get() → Gets BaseProvider instance
    ↓
provider_instance.call()
    - OpenRouterProvider.call() (Line 695-798)
    - OpenAIProvider.call() (Line 110-223)
    - AnthropicProvider.call() (Line 237-374)
    - GoogleProvider.call() (Line 388-529)
    - OllamaProvider.call() (Line 608-681)
    - XaiProvider.call() (Line 812-915)
    ↓
Standardized response format
```

### Legacy Flow (api_aggregator_v3.call_model)
```
streaming_handler.py → call_model_stream()
    ↓
api_aggregator_v3.py:481 (call_model_stream function)
    ↓
Ollama API call directly via httpx
    ↓
Anti-loop detection + timeout handling
```

### Direct API Flow (for tools)
```
call_model_v2() → Direct API needed
    ↓
api_gateway.py: call_openai_direct()
    (Only via api_aggregator_v3.call_model fallback)
```

---

## 6. OpenRouter Usage Breakdown

### In ProviderRegistry
- **OpenRouterProvider class:** Full implementation with async/await
- **detect_provider():** Handles "x-ai/", "xai/", "provider/" prefixes (Line 1031-1034)
- **Fallback:** Auto-routes failed XAI keys to OpenRouter (Line 1104-1118)
- **Streaming:** Native SSE support via `_stream_openrouter()` (Line 1580-1677)

### In APIAggregator (call_model_legacy)
- **Line 436-441:** Tries OpenRouter if `call_openrouter` function available
- **Line 449-454:** Falls back to Ollama if OpenRouter model fails
- **Note:** This is completely bypassed - nobody calls `call_model()` from api_aggregator_v3

### In APIGateway
- **_call_openrouter():** Sync version using `requests` library (Line 395-441)
- **Status:** Orphaned code - not integrated into main flow

---

## 7. Key Differences: ProviderRegistry vs APIAggregator

| Feature | ProviderRegistry | APIAggregator | APIGateway |
|---------|-----------------|---------------|-----------|
| OpenRouter impl | ✅ Full async | ❌ Stub (empty) | ✅ Sync only |
| Used in production | ✅ YES | ❌ NO* | ❌ NO |
| Provider rotation | ✅ Auto 24h cooldown | ⚠️ Basic | ⚠️ Basic |
| Streaming | ✅ SSE + Anti-loop | ✅ Ollama only | ❌ No |
| Tool support | ✅ Async providers | ❌ Limited | ❌ No |
| Model detection | ✅ Regex-based | ⚠️ Hardcoded | ⚠️ Hardcoded |
| XAI fallback | ✅ 403→OpenRouter | ❌ No | ❌ No |

*APIAggregator.call_model_stream() используется только для streaming, но это наследие

---

## 8. OpenRouter Model Routing (MARKER_94.8_BUG_ROUTING)

### Critical Fix in ProviderRegistry.detect_provider()
**Lines 992-1041:**

Problem: x-ai/ prefix был направляется на прямой XAI API вместо OpenRouter
Solution: Распознавание format "provider/model" как OpenRouter (Line 1031-1034)

```python
# MARKER_94.8_FIX: OpenRouter models with x-ai/ prefix
# These are OpenRouter's representation of xAI models, NOT direct xAI API calls
elif model_lower.startswith("xai/") or model_lower.startswith("x-ai/"):
    # MARKER_94.8_OPENROUTER_XAI: Models like "x-ai/grok-4"
    # are OpenRouter models, not direct xAI API
    return Provider.OPENROUTER
```

**Direct xAI API detection:**
- Models без префикса: "grok-4", "grok-beta" → Provider.XAI (Line 1014-1016)
- Модели с префиксом: "x-ai/grok-4", "xai/grok-4" → Provider.OPENROUTER (Line 1031-1034)

---

## 9. ВЕРДИКТ

### Production System
**ProviderRegistry (provider_registry.py)** ✅
- Полностью implemented и used в production
- All handlers используют `call_model_v2()`
- Modern async/await architecture
- Поддержка инструментов через tool-aware providers
- Fallback chain для XAI→OpenRouter

### Legacy Systems
**APIAggregator (api_aggregator_v3.py)** ⚠️
- OpenRouterProvider - stub (не реализован)
- call_model() - используется только как fallback
- call_model_stream() - используется для streaming Ollama
- HOST_HAS_OLLAMA - используется для решения streaming decisions

**APIGateway (api_gateway.py)** ⚠️
- _call_openrouter() - orphaned sync code
- init_api_gateway() - инициализируется но не используется
- call_openai_direct() - перехватываются ProviderRegistry

### OpenRouter Provider Status
| Location | Status | Notes |
|----------|--------|-------|
| ProviderRegistry | ✅ PRODUCTION | Full async, 24h cooldown, auto-rotate |
| APIAggregator | ❌ EMPTY | Stub class, never instantiated |
| APIGateway | ⚠️ LEGACY | Sync version, not integrated |

### Recommendations

1. **KEEP:** ProviderRegistry system - это основная production система
2. **REMOVE:** APIAggregator.OpenRouterProvider (stub class) - мёртвый код
3. **REMOVE:** APIGateway._call_openrouter() - orphaned sync code
4. **UPDATE:** Удалить unused import `from src.elisya.api_aggregator_v3 import APIAggregator`
5. **DEPRECATE:** Migrate call_model_stream() to use call_model_v2_stream() from ProviderRegistry

### Konkretno dlja OpenRouter
- **Direct использование:** ProviderRegistry.OpenRouterProvider (Production)
- **Model detection:** ProviderRegistry.detect_provider() с x-ai/ support
- **Streaming:** call_model_v2_stream() → _stream_openrouter()
- **Fallback:** XAI 403 → OpenRouter (automatic)

---

## 10. File-by-File Summary

| File | OpenRouter impl | Status | Used |
|------|-----------------|--------|------|
| provider_registry.py | ✅ Line 684-798 | PRODUCTION | ✅ |
| api_aggregator_v3.py | ❌ Line 180-182 | STUB | ⚠️ Streaming only |
| api_gateway.py | ⚠️ Line 395-441 | LEGACY | ❌ |
| user_message_handler.py | - | Uses call_model_v2 | ✅ |
| orchestrator_with_elisya.py | - | Uses call_model_v2 | ✅ |
| streaming_handler.py | - | Uses call_model_stream | ⚠️ |
| chat_handler.py | - | Uses ProviderRegistry | ✅ |

---

**Report Generated:** 2026-01-26
**System Status:** ProviderRegistry is the canonical production system
