# UI Handler Bug Analysis - Ollama Path

## Executive Summary

Analysis of `src/api/handlers/user_message_handler.py` reveals **TWO CRITICAL ARCHITECTURAL VIOLATIONS** where the UI handler makes direct model calls without using the `provider_registry`. These direct calls bypass key rotation, error handling, and XAI/Grok support.

---

## 1. Direct Model Calls (Bypass provider_registry)

| Location | Issue | Severity |
|----------|-------|----------|
| Lines 355-360 | `ollama.chat()` - Direct Ollama call in executor | CRITICAL |
| Lines 575-580 | `httpx.stream()` - Direct OpenRouter streaming | HIGH |
| Lines 665-669 | `httpx.post()` - Direct OpenRouter fallback | HIGH |

### Issue 1A: Ollama Direct Call (Lines 355-360)

```python
def ollama_call():
    return ollama.chat(
        model=requested_model,
        messages=[{"role": "user", "content": model_prompt}],
        stream=False,
    )

ollama_response = await loop.run_in_executor(None, ollama_call)
```

**Problems:**
- Uses `import ollama` directly instead of provider registry
- No error handling for model unavailability
- No streaming support (stream=False hardcoded)
- No integration with key manager or API key rotation
- No 403/auth error handling
- Cannot fallback to OpenRouter

**Should Use:** `call_model_v2()` with `Provider.OLLAMA`

---

### Issue 1B: OpenRouter Streaming (Lines 575-580)

```python
async with client.stream(
    "POST",
    "https://openrouter.ai/api/v1/chat/completions",
    headers=headers,
    json=payload,
) as response:
```

**Problems:**
- Direct `httpx.stream()` call bypasses provider registry
- Uses raw API key in headers (though from key_manager)
- Handles 401/402 key rotation manually (code smell)
- **NO 403 ERROR HANDLING** - credentials exhausted not detected
- Cannot retry with fallback provider

**Key Rotation Logic at Lines 601-616:**
- Manual key rotation on 401/402 only
- **Missing:** 403 (Forbidden) handling for XAI keys exhausted

---

### Issue 1C: OpenRouter Fallback (Lines 665-669)

```python
resp = await client.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers=headers,
    json=payload,
)
```

**Problems:**
- Direct HTTP call, no provider abstraction
- Only handles 429 (rate limit), 200 (success), and generic errors
- **NO 403 HANDLING** - cannot detect credential exhaustion
- Cannot switch to alternative provider

---

## 2. Missing Functionality

| Feature | Status | Impact |
|---------|--------|--------|
| XAI/Grok Provider Support | ❌ MISSING | No native XAI calls |
| 403 Error Handling | ❌ MISSING | Keys exhausted = silent fail |
| Provider Auto-Fallback | ❌ MISSING | Must manually retry |
| Key Rotation for 403 | ❌ MISSING | XAI keys can't rotate |

### What's Missing:

1. **No XAI/Grok Support**
   - `provider_registry.py` supports `Provider.XAI` (line 42)
   - UI handler never calls it
   - Should detect Grok models and route to XAI provider

2. **No 403 Handling**
   - OpenRouter returns 403 when API key invalid
   - Current code ignores this status
   - Should trigger `XaiKeysExhausted` exception (provider_registry.py:27-30)
   - Should fallback to alternative provider

3. **Missing Provider.XAI Enum**
   ```python
   # From provider_registry.py (line 42)
   XAI = "xai"  # Phase 80.35: x.ai (Grok models)
   ```
   - Handler never imports or uses this
   - No model name pattern matching for grok-*

---

## 3. Architecture Fix Required

### Current (Broken):
```
user_message_handler.py
  → ollama.chat() [direct]
  → httpx.stream() [direct]
  → httpx.post() [direct]
```

### Correct (Using provider_registry):
```
user_message_handler.py
  → call_model_v2(messages, model, provider) [abstracted]
  → [Router detects provider from model name]
  → OllamaProvider.call() | XaiProvider.call() | OpenRouterProvider.call()
  → [Automatic 403 handling, key rotation, fallback]
```

### Required Import:
```python
from src.elisya.provider_registry import call_model_v2, Provider
```

### Function Signature (provider_registry.py:856-862):
```python
async def call_model_v2(
    messages: List[Dict[str, str]],
    model: str,
    provider: Optional[Provider] = None,
    tools: Optional[List[Dict]] = None,
    **kwargs,
) -> Dict[str, Any]:
```

---

## 4. Recommended Fixes

### Fix 1: Replace Ollama Direct Call (Lines 355-360)
Replace with:
```python
# Auto-detect provider (Ollama) from model name
response = await call_model_v2(
    messages=[{"role": "user", "content": model_prompt}],
    model=requested_model,
    provider=Provider.OLLAMA if is_local_ollama else None
)
full_response = response.get("content", "")
```

### Fix 2: Replace OpenRouter Streaming (Lines 575-580)
Replace with:
```python
response = await call_model_v2(
    messages=[{"role": "user", "content": model_prompt}],
    model=requested_model,
    provider=Provider.OPENROUTER  # Explicit provider
)
full_response = response.get("content", "")
```

### Fix 3: Add XAI/Grok Detection
Replace model detection at line 241:
```python
# Before
is_local_ollama = is_local_ollama_model(requested_model)

# After
is_local_ollama = is_local_ollama_model(requested_model)
is_xai = requested_model.lower().startswith("grok")
provider = (
    Provider.OLLAMA if is_local_ollama
    else Provider.XAI if is_xai
    else None  # Auto-detect for others
)
```

### Fix 4: 403 Error Handling
Import exception:
```python
from src.elisya.provider_registry import XaiKeysExhausted

# In exception handler
except XaiKeysExhausted:
    full_response = "All XAI keys exhausted. Falling back to OpenRouter..."
    # Retry with OpenRouter
    response = await call_model_v2(
        messages=[...],
        model=requested_model,
        provider=Provider.OPENROUTER
    )
```

---

## 5. Impact Assessment

### Current Risk:
- **XAI/Grok models:** Completely unsupported
- **403 errors:** Silent failures, user sees no error
- **Key rotation:** Only for 401/402, not 403
- **Fallback:** Requires manual implementation per handler

### After Fix:
- ✅ Unified provider abstraction
- ✅ Automatic 403 → fallback to OpenRouter
- ✅ XAI/Grok native support
- ✅ Consistent error handling across all handlers
- ✅ Single source of truth for key rotation

---

## 6. Files Involved

**To Fix:**
- `src/api/handlers/user_message_handler.py` (lines 260-755)

**Architecture (Do NOT Modify):**
- `src/elisya/provider_registry.py` - Defines `call_model_v2()`, `Provider.XAI`
- `src/elisya/api_gateway.py` - Uses provider_registry correctly

**Reference:**
- `src/utils/unified_key_manager.py` - Key rotation implementation (already integrated into providers)

---

**Status:** DOCUMENTATION ONLY - No code changes made.
**Phase:** 93 (Haiku C - UI Bug Audit)
