# UI Handler Bug Analysis - OpenRouter Direct Calls

## Critical Issue: Hardcoded OpenRouter Calls in user_message_handler.py

### Executive Summary
The `user_message_handler.py` contains **TWO HARDCODED direct HTTP calls to OpenRouter API** (lines 577 and 666) that completely bypass the `provider_registry.py` abstraction layer. This creates:
- **API Key management bypassing** - doesn't use APIKeyService
- **Inconsistent error handling** - doesn't follow provider_registry patterns
- **Duplicate streaming logic** - reimplements what provider_registry already does
- **Missing fallback chains** - local retry logic instead of unified retry strategy

---

## 1. Hardcoded OpenRouter Calls (Direct httpx Violations)

| Line | Type | URL | Issue |
|------|------|-----|-------|
| **577** | Streaming | `https://openrouter.ai/api/v1/chat/completions` | Direct POST with `httpx.AsyncClient.stream()` |
| **666** | Fallback | `https://openrouter.ai/api/v1/chat/completions` | Direct POST with `httpx.AsyncClient.post()` |

### Details of Each Call:

#### Call 1: Streaming (Line 575-680)
```python
# Lines 575-580: Direct stream call
async with client.stream(
    "POST",
    "https://openrouter.ai/api/v1/chat/completions",  # ← HARDCODED
    headers=headers,
    json=payload,
) as response:
```

**Problems:**
- `client` is raw `httpx.AsyncClient(timeout=120.0)` - no retry logic
- No use of APIKeyService via provider_registry
- Gets key via `km.get_openrouter_key()` (lines 454-456) instead of `APIKeyService().get_key("openrouter")`

#### Call 2: Non-Streaming Fallback (Line 665-686)
```python
# Lines 665-669: Direct POST fallback
resp = await client.post(
    "https://openrouter.ai/api/v1/chat/completions",  # ← HARDCODED
    headers=headers,
    json=payload,
)
```

**Problems:**
- Same isolation from provider_registry
- Repeats streaming call error handling instead of using unified logic

---

## 2. Error Handling & Recovery Strategy

### Current Implementation (Scattered Logic)

| Status | Streaming | Fallback | Issue |
|--------|-----------|----------|-------|
| **401 Unauthorized** | ✓ Rotates key (607) | ✗ Ignored | Inconsistent |
| **402 Payment** | ✓ Rotates key (607) | ✗ No retry | Incomplete |
| **429 Rate Limit** | ✓ User message (586) | ✓ User message (672) | OK, but generic |
| **400 Bad Request** | ✓ Fallback trigger (595) | ✗ Returns error (685) | One-way fallback |
| **Generic Error** | ✓ Returns error (621) | ✓ Returns error (685) | Simple message |

### Key Retry Logic (Lines 601-616)
```python
elif response.status_code in [401, 402]:
    key_retry_count += 1
    if key_retry_count < max_key_retries:
        km.rotate_to_next()  # ← Custom rotation
        api_key = km.get_openrouter_key()
        headers["Authorization"] = f"Bearer {api_key}"
        use_streaming = False  # Falls through to fallback
```

**Issues with this approach:**
1. **Custom rotation** - Reimplements what APIKeyService should handle
2. **Limited scope** - Only retries within same function call
3. **Fallback coupling** - Uses `use_streaming = False` flag to trigger retry
4. **Max 3 retries** - Hardcoded based on `km.get_openrouter_keys_count()`

### Missing Fallback Chain
- Streaming fails → Falls to non-streaming ✓
- Both fail → Returns error message ✗
- **Should be:** Try provider_registry → Try rotation → Use fallback models

---

## 3. API Key Management Chaos

### Current (Broken) Pattern
```python
# Line 454-456: Manual key fetch
api_key = km.get_openrouter_key()  # Custom key manager
```

### Should Be (provider_registry pattern)
```python
# From src/elisya/provider_registry.py line 592
api_key = APIKeyService().get_key("openrouter")
# Automatically handles rotation, caching, etc.
```

### Key Manager Details
- **Current:** `km = KeyManager()` with `rotate_to_next()` method (line 608)
- **Problem:** Works locally but doesn't sync with APIKeyService
- **Risk:** If APIKeyService rotates keys elsewhere, this handler uses stale key

---

## 4. Recommended Fixes (Priority Order)

### MUST FIX (Critical)
1. **Replace hardcoded URLs with provider_registry call**
   - Use existing `openrouter_provider.call()` from provider_registry (line 914)
   - Eliminates duplicate streaming logic
   - Inherits all error handling & retry logic

2. **Use APIKeyService for key management**
   - Replace `km.get_openrouter_key()` with `APIKeyService().get_key("openrouter")`
   - Removes local rotation logic
   - Syncs with global key rotation

### SHOULD FIX (High)
3. **Move to unified streaming via provider_registry**
   - If streaming needed, use provider_registry's built-in streaming
   - Or use `streaming_handler.py` helper (line 92)

4. **Implement proper fallback chain**
   - Try primary model via provider_registry
   - On 429/402: Rotate and retry once via APIKeyService
   - On failure: Fall back to fallback_model list from provider_registry

### NICE TO HAVE (Medium)
5. **Remove local AsyncClient context**
   - Let provider_registry manage HTTP client lifecycle
   - Consistent timeout & retry config

---

## 5. Evidence from Code Structure

### Where provider_registry Should Be Used
From `src/elisya/provider_registry.py`:

```python
# Line 908-915: Existing OpenRouter provider pattern
openrouter_provider = registry.get(Provider.OPENROUTER)
if openrouter_provider:
    openrouter_model = f"x-ai/{clean_model}"
    result = await openrouter_provider.call(
        messages, openrouter_model, tools, **kwargs
    )
```

### What provider_registry Provides
- ✓ APIKeyService integration (line 592)
- ✓ Unified streaming support
- ✓ Built-in error handling
- ✓ Automatic retry logic
- ✓ Fallback model chains
- ✓ Request/response logging

### Current Gap
- **Lines 450-720** in user_message_handler.py: Reimplements everything locally
- **Lines 575-686** especially: Hardcoded URLs, custom error handling, isolated key management

---

## 6. Risk Assessment

| Risk | Severity | Impact | Likelihood |
|------|----------|--------|------------|
| Stale API keys due to local rotation | **CRITICAL** | Auth failures, rate limiting | HIGH |
| Duplicate streaming logic | **HIGH** | Inconsistent behavior, hard to debug | HIGH |
| Bypassed APIKeyService | **HIGH** | Lost audit trail, inconsistent rotation | HIGH |
| Limited retry (max 3 keys) | **MEDIUM** | Fails early if only 1-2 keys available | MEDIUM |
| No provider fallback | **MEDIUM** | Can't fall back to Ollama/other on failure | MEDIUM |

---

## Summary

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py`

**Violations:** 2 hardcoded OpenRouter API calls (lines 577, 666)

**Root Cause:** Handler tries to implement its own OpenRouter logic instead of delegating to provider_registry

**Fix Effort:** ~30 lines of code changes to use provider_registry properly

**Benefit:** Eliminates duplicate code, fixes API key sync issues, enables proper fallback chains
