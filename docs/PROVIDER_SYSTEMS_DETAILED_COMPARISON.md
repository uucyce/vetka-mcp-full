# Provider Systems - Detailed Technical Comparison

## 1. ProviderRegistry vs APIAggregator vs APIGateway

### Architecture Comparison

#### ProviderRegistry (provider_registry.py)
**Type:** Singleton Registry Pattern
**Status:** PRODUCTION ✅

```
Files affected: user_message_handler, orchestrator, chat_handler, mcp tools, bridges
Lines: 1-1677 (full implementation)
Core functions:
  - get_registry() [Line 1049]
  - call_model_v2() [Line 1054]
  - call_model_v2_stream() [Line 1224]
  - detect_provider() [Line 979]
```

**Architecture:**
```
BaseProvider (ABC, Line 56)
  ├── OpenAIProvider (Line 99)
  ├── AnthropicProvider (Line 226)
  ├── GoogleProvider (Line 377)
  ├── OllamaProvider (Line 532)
  ├── OpenRouterProvider (Line 684) ← PRODUCTION
  └── XaiProvider (Line 801)

ProviderRegistry (Line 918)
  └── Singleton pattern
      ├── register() [Line 958]
      ├── get() [Line 962]
      └── get_by_name() [Line 966]
```

**Key Feature: Standardized Response Format**
```python
{
    "message": {
        "content": "str",
        "tool_calls": [...] or None,
        "role": "assistant"
    },
    "model": "string",
    "provider": "string",
    "usage": {...}
}
```

---

#### APIAggregator (api_aggregator_v3.py)
**Type:** Legacy Wrapper + Streaming
**Status:** LEGACY FALLBACK ⚠️

```
Files affected: streaming_handler only
Lines: 1-588 (mostly boilerplate)
Core functions:
  - call_model() [Line 278] (legacy, rarely used)
  - call_model_stream() [Line 481] (Ollama only)
  - _ollama_chat_sync() [Line 273] (helper)
```

**Architecture:**
```
APIProvider (ABC, Line 146)
  └── OpenRouterProvider (Line 180) ← STUB ONLY
      pass  # Empty!

APIAggregator (Line 190)
  └── Mostly boilerplate
      (add_key, _encrypt, _decrypt methods)
```

**Key Difference: NOT using BaseProvider pattern**
- Each provider would need separate implementation
- No standardization across providers
- OpenRouter stub is never instantiated

---

#### APIGateway (api_gateway.py)
**Type:** Legacy Infrastructure
**Status:** ORPHANED ❌

```
Files affected: None (initialization only, never used)
Lines: 1-865 (full implementations but unreachable)
Core functions:
  - init_api_gateway() [Line 616] (called but never used)
  - get_api_gateway() [Line 623] (never called)
  - _call_openrouter() [Line 395] (sync, unreachable)
```

**Architecture:**
```
ProviderStatus (Enum, Line 20)
APIKey (dataclass, Line 31)
APICallResult (dataclass, Line 64)

APIGateway (Line 96)
  ├── __init__() [Line 109]
  ├── call_model() [Line 182] (unused)
  ├── _call_openrouter() [Line 395] (unreachable)
  ├── _call_gemini() [Line 345] (unreachable)
  └── _call_ollama() [Line 443] (unreachable)
```

---

### OpenRouter Implementation Comparison

#### ProviderRegistry.OpenRouterProvider
**Location:** Lines 684-798 of provider_registry.py
**Status:** PRODUCTION - FULLY IMPLEMENTED ✅

**Key Implementation:**
```python
class OpenRouterProvider(BaseProvider):
    @property
    def supports_tools(self) -> bool:
        return False

    async def call(self, messages, model, tools=None, **kwargs):
        # Line 695-798: Full async implementation

        # Key features implemented:
        1. Async/await throughout [Line 741 async with]
        2. Key manager integration [Line 710-717]
        3. Max retries = key count [Line 711]
        4. Model name cleanup [Line 730-732]
        5. Payload construction [Line 734-738]
        6. Error handling [Line 749-760]
        7. 24h cooldown marking [Line 751-757]
        8. Key rotation [Line 758]
        9. Proper success exit [Line 764]
```

**Error Handling:**
```python
# Lines 749-760: 401/402/403 handling
if response.status_code in (401, 402, 403):
    print(f"[OPENROUTER] Key failed ({response.status_code})")
    # Mark rate-limited
    for record in km.keys.get(ProviderType.OPENROUTER, []):
        if record.key == api_key:
            record.mark_rate_limited()
            break
    # Rotate to next
    km.rotate_to_next()
    continue  # Retry with next key
```

**Streaming Implementation:**
```python
# Lines 1580-1677: _stream_openrouter()
async def _stream_openrouter(
    messages, model, registry, **kwargs
) -> AsyncGenerator[str, None]:
    # Key rotation in loop [Line 1597]
    # SSE parsing [Line 1649-1665]
    # Rate limit detection [Line 1632-1641]
```

---

#### APIAggregator.OpenRouterProvider
**Location:** Lines 180-182 of api_aggregator_v3.py
**Status:** EMPTY STUB ❌

```python
class OpenRouterProvider(APIProvider):
    # ... (Assuming original implementation)
    pass  # ← COMPLETELY EMPTY
```

**Why it's not used:**
- Class is defined but never instantiated
- APIAggregator.PROVIDER_CLASSES at Line 200 only references it
- But APIAggregator is never instantiated anywhere
- Dead code

---

#### APIGateway._call_openrouter()
**Location:** Lines 395-441 of api_gateway.py
**Status:** ORPHANED SYNC CODE ❌

```python
def _call_openrouter(self, model: str, prompt: str, timeout: int) -> str:
    # Line 395-441: Sync implementation

    # Issues:
    1. Synchronous (uses requests library, not async)
    2. No key rotation beyond simple index
    3. No 24h cooldown
    4. No streaming support
    5. No standardized error handling
    6. Unreachable code path
```

**Comparison:**
```python
# ProviderRegistry: ASYNC
async def call(self, messages, model, tools=None, **kwargs):
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(...)

# APIGateway: SYNC
def _call_openrouter(self, model, prompt, timeout):
    response = requests.post(...)  # Blocking call
```

---

## 2. OpenRouter-Specific Features

### Feature: Key Rotation with 24h Cooldown (MARKER_93.4)

**ProviderRegistry Implementation:**
```python
# Lines 710-760
km = get_key_manager()
max_retries = km.get_openrouter_keys_count()

for attempt in range(max_retries):
    api_key = km.get_openrouter_key()

    # Try call...
    if response.status_code in (401, 402, 403):
        # Mark key as rate-limited
        for record in km.keys.get(ProviderType.OPENROUTER, []):
            if record.key == api_key:
                record.mark_rate_limited()  # 24h cooldown
                break
        km.rotate_to_next()
        continue
```

**APIAggregator Implementation:**
- Not implemented (stub)

**APIGateway Implementation:**
```python
# Line 464-491: Basic rotation
self.current_key_index[provider] = (
    self.current_key_index[provider] + 1
) % len(keys)

# But this is never reached in production
```

---

### Feature: SSE Streaming

**ProviderRegistry Implementation:**
```python
# Lines 1580-1677: Full SSE parsing
async with client.stream(
    "POST",
    "https://openrouter.ai/api/v1/chat/completions",
    json=payload,
    headers=headers,
) as response:
    async for line in response.aiter_lines():
        if not line or not line.startswith("data: "):
            continue

        data_str = line[6:]
        if data_str == "[DONE]":
            break

        data = json.loads(data_str)
        delta = data.get("choices", [{}])[0].get("delta", {})
        content = delta.get("content", "")
        if content:
            yield content
```

**APIAggregator Implementation:**
- Stream is via Ollama only, not OpenRouter
- Line 481-580 implements Ollama HTTP streaming

**APIGateway Implementation:**
- Not supported

---

### Feature: Model Name Cleanup (MARKER_93.6)

**ProviderRegistry Implementation:**
```python
# Line 730-732
clean_model = model.replace("openrouter/", "")

# Why needed:
# OpenRouter doesn't accept "openrouter/gpt-4-turbo" format
# It expects just "gpt-4-turbo" or "provider/model" (x-ai/grok-4)
```

**Used in:**
- OpenRouterProvider.call() [Line 732]
- _stream_openrouter() [Line 1614]

---

### Feature: Provider Detection (MARKER_94.8 BUG FIX)

**Critical Fix for x-ai/ prefix:**

```python
# Lines 991-1041
# The bug: x-ai/grok-4 was routed to XAI direct API (wrong!)
# The fix: x-ai/grok-4 routes to OpenRouter (correct!)

# MARKER_94.8_FIX: Direct xAI API detection
if model_lower.startswith("grok-") or model_lower == "grok":
    return Provider.XAI  # Direct x.ai API (no prefix)

# MARKER_94.8_FIX: OpenRouter's xAI models
elif model_lower.startswith("xai/") or model_lower.startswith("x-ai/"):
    # Models like "x-ai/grok-4" are OpenRouter models
    return Provider.OPENROUTER
```

**Routing Rules:**
```
grok-4           → XAI (direct API)
x-ai/grok-4      → OPENROUTER (via OpenRouter)
xai/grok-4       → OPENROUTER (via OpenRouter)
openai/gpt-4     → OPENAI (direct API)
anthropic/claude → ANTHROPIC (direct API)
deepseek/chat    → OPENROUTER (format = provider/model)
```

---

## 3. Fallback Chains

### ProviderRegistry Fallback Logic

**Implemented at Lines 1098-1190 in call_model_v2():**

```
XAI Call Fails
    ↓
if XaiKeysExhausted (403):
    └→ Convert: grok-4 → x-ai/grok-4
    └→ Call: openrouter_provider.call()
    └→ Return result

ValueErrors (API key missing):
    ↓
if provider in (OPENAI, ANTHROPIC, GOOGLE, XAI):
    └→ Try OpenRouter fallback
    └→ Convert model name appropriately
    └→ Call: openrouter_provider.call()
    └→ Return result

HTTPStatusError (401/402/403/404/429):
    ↓
if provider in (OPENAI, ANTHROPIC, GOOGLE, XAI):
    └→ Update model status [update_model_status()]
    └→ Try OpenRouter fallback
    └→ Call: openrouter_provider.call()
    └→ Return result
```

**Error Handling Priority:**
```python
try:
    result = await provider_instance.call(...)
except XaiKeysExhausted:
    # Line 1104: XAI 403 exhaustion
except ValueError:
    # Line 1120: Missing API key
except httpx.HTTPStatusError:
    # Line 1148: HTTP errors
except Exception:
    # Line 1185: Generic catch-all
```

---

### APIAggregator Fallback Logic

**Lines 363-433:**
- Try direct API call (openai_direct, etc.)
- Fall through to Ollama

**No fallback to OpenRouter** (not implemented)

---

### APIGateway Fallback Logic

**Lines 212-278:**
- Unused fallback logic
- Would try multiple models in chain
- Never reached in production

---

## 4. Tool Support Analysis

### Which Providers Support Tools?

**ProviderRegistry:**
```python
# Line 67-69: Provider interface
@property
@abstractmethod
def supports_tools(self) -> bool:
    pass

# Implementations:
OpenAIProvider:       True   [Line 103]
AnthropicProvider:    True   [Line 230]
GoogleProvider:       True   [Line 381]
OllamaProvider:       True   [Line 558]
OpenRouterProvider:   False  [Line 688] ← By design
XaiProvider:          True   [Line 805]
```

**Why OpenRouter is False:**
- OpenRouter has limited tool/function calling support
- Most models via OpenRouter don't support tools well
- If tools needed, direct API providers are preferred

---

### Tool Support in call_model_v2()

**Lines 1092-1095:**
```python
if tools and not provider_instance.supports_tools:
    print(f"[REGISTRY] Warning: {provider.value} doesn't support tools")
    tools = None  # Silently ignore tools
```

**In user_message_handler.py:**
```python
# Line 789: Tool calling with Ollama as fallback
ollama_response = await call_model_v2(
    messages, model, Provider.OLLAMA, tools=tools
)

# Line 871: Try tool calling with selected provider
result = await call_model_v2(
    messages, model, provider, tools=tools
)
```

---

## 5. Integration Points

### Where ProviderRegistry Gets Called

**Main entry points:**

1. **user_message_handler.py** (Line 63)
   - Imports: call_model_v2, call_model_v2_stream, Provider
   - Usage: Lines 363, 537, 559, 789, 871, 882
   - Purpose: Main message handling

2. **orchestrator_with_elisya.py** (Line 44)
   - Imports: call_model_v2, Provider, ProviderRegistry
   - Usage: Lines 1023, 1032
   - Purpose: Orchestration decisions

3. **chat_handler.py** (Line 62)
   - Imports: ProviderRegistry, Provider
   - Purpose: Group chat handling

4. **mcp/tools/llm_call_tool.py** (Line 271)
   - Imports: call_model_v2, Provider
   - Usage: Lines 310, 323
   - Purpose: MCP tool execution

5. **opencode_bridge** (Line 15)
   - Imports: ProviderRegistry, call_model_v2
   - Purpose: Code execution via OpenRouter

---

### Where APIAggregator Gets Called

**Limited entry points:**

1. **streaming_handler.py** (Line 59)
   - Imports: call_model_stream
   - Usage: Line 74
   - Purpose: Ollama streaming only

2. **user_message_handler.py** (Line 60)
   - Imports: HOST_HAS_OLLAMA
   - Usage: Line 1591
   - Purpose: Streaming decision flag

3. **di_container.py** (Line 34)
   - Imports: HOST_HAS_OLLAMA
   - Purpose: DI parameter

---

### Where APIGateway Gets Used

**Zero production usage:**

1. **initialization/components_init.py** (Line 192)
   - Creates instance but never used
   - Result stored in variables not accessed

2. **initialization/singletons.py** (Line 19)
   - Listed as singleton but never accessed

3. **dependencies.py** (Line 97)
   - Exposed as FastAPI dependency but never injected

---

## 6. Performance Implications

### ProviderRegistry (PRODUCTION)
- **Async/await:** Full async throughout, non-blocking
- **Key rotation:** Happens inline, no extra calls
- **Streaming:** SSE with generators, memory efficient
- **Overhead:** Minimal (singleton pattern)

### APIAggregator (LEGACY)
- **Blocking calls:** Uses sync ollama library
- **Thread pool:** Uses executor for sync calls
- **Streaming:** Direct HTTP streaming (optimized)
- **Overhead:** Thread pool overhead, but only for Ollama

### APIGateway (ORPHANED)
- **Blocking calls:** All requests are sync, blocking
- **No async:** Would block entire event loop if used
- **Threading:** Would need threading for non-blocking
- **Overhead:** High if actually used (but it's not)

---

## 7. Maintenance Burden

### ProviderRegistry
- **7 provider implementations** to maintain
- **Shared BaseProvider interface** ensures consistency
- **Fallback logic** handles 3 error types
- **Burden:** HIGH (but justified by production use)

### APIAggregator
- **1 empty stub** for OpenRouter (dead code)
- **Legacy call_model()** function
- **Streaming implementation** for Ollama
- **Burden:** LOW (but dying code)

### APIGateway
- **Full implementations** of 3 providers
- **Key management** logic
- **Health tracking** logic
- **Burden:** MEDIUM (completely unreachable)

---

## 8. Recommendations

### Keep
✅ ProviderRegistry (provider_registry.py)
- Production system
- Modern architecture
- Active maintenance needed

### Deprecate
⚠️ APIAggregator (api_aggregator_v3.py)
- Mark as deprecated
- Keep for streaming only
- Plan migration to call_model_v2_stream()

### Remove
❌ APIGateway (api_gateway.py)
- Completely unused
- Orphaned infrastructure
- Dead code

---

## Summary Table

| Aspect | ProviderRegistry | APIAggregator | APIGateway |
|--------|-----------------|---------------|-----------|
| **Status** | Production ✅ | Legacy ⚠️ | Orphaned ❌ |
| **OpenRouter impl** | Full async | Empty stub | Sync orphaned |
| **Files using it** | 10+ | 1 | 0 |
| **Async/await** | Yes | No | No |
| **Key rotation** | 24h cooldown | N/A | Basic |
| **Streaming** | SSE | Ollama | None |
| **Tool support** | Yes (conditional) | No | No |
| **Maintenance burden** | High | Low | High (unused) |
| **Reachability** | 100% | ~1% (streaming) | 0% |
| **Recommendation** | Keep | Deprecate | Remove |

---

**Generated:** 2026-01-26
**Status:** Complete ✅
**Canonical System:** ProviderRegistry
