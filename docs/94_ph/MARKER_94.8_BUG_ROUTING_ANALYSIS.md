# CRITICAL BUG: Model Routing Confusion - MARKER_94.8

## Problem Statement

When user calls `x-ai/grok-4` (OpenRouter version), the system was routing it to the direct xAI API (`api.x.ai`) instead of OpenRouter, resulting in:

```
User called: @x-ai/grok-4 (OR version)
But log shows: POST https://api.x.ai/v1/chat/completions "HTTP/1.1 403 Forbidden"
```

## Root Cause Analysis

### The Confusion

The bug stems from misunderstanding what model ID prefixes mean:

1. **Direct xAI API Models** (call `api.x.ai/v1/chat/completions`):
   - Format: `grok-4`, `grok-beta`, etc. (NO prefix)
   - These use direct xAI API key
   - Examples: `grok-4`, `grok-2`, `grok-beta`

2. **OpenRouter xAI Models** (call `openrouter.ai/api/v1/chat/completions`):
   - Format: `x-ai/grok-4`, `xai/grok-4` (WITH provider prefix)
   - These use OpenRouter API key
   - OpenRouter wraps xAI models with provider prefix
   - Examples: `x-ai/grok-4`, `xai/grok-beta`

### The Bug Code (BEFORE FIX)

**File**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/provider_registry.py`
**Lines**: 1005-1011

```python
elif (
    model_lower.startswith("xai/")
    or model_lower.startswith("x-ai/")
    or model_lower.startswith("grok")
):
    # Phase 90.1.4.1: xai/Grok detection (x-ai/grok-4, xai/grok-4, grok-4)
    return Provider.XAI
```

**The Problem:**
- Line 1007: Treats `x-ai/` prefix as "direct xAI API"
- This is **WRONG** - `x-ai/` is OpenRouter's format for xAI models
- When this function returns `Provider.XAI`, the call goes to `XaiProvider`
- `XaiProvider.call()` at line 832 strips the prefix: `grok-4`
- Then sends to `api.x.ai/v1/chat/completions` with model `grok-4`
- Gets 403 Forbidden (xAI rate limit or auth issue)

## The Routing Flow (BROKEN)

```
User Input: x-ai/grok-4
    ↓
detect_provider() returns Provider.XAI [WRONG!]
    ↓
XaiProvider.call(model="x-ai/grok-4")
    ↓
Clean model: clean_model = "x-ai/grok-4".replace("x-ai/", "") → "grok-4"
    ↓
POST https://api.x.ai/v1/chat/completions with model="grok-4"
    ↓
403 Forbidden (because this is the direct API, not OpenRouter)
```

## The Fix (AFTER)

**File**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/provider_registry.py`
**Lines**: 978-1043 (updated detect_provider method)

**Strategy:**
1. Check for direct API format FIRST (no slash at all)
2. Then check for provider-prefixed models (OpenRouter format)
3. Direct xAI API: `grok-*` or `grok` (no prefix)
4. OpenRouter xAI: `x-ai/*` or `xai/*` (with prefix)

**Fixed Code:**
```python
# Check if this is a direct xAI API call (no prefix, starts with grok)
if model_lower.startswith("grok-") or model_lower == "grok":
    # MARKER_94.8_FIX: Direct xAI API (grok-4, grok-beta, etc. without x-ai/ prefix)
    return Provider.XAI

# ... other providers ...

# MARKER_94.8_FIX: OpenRouter models with x-ai/ prefix (x-ai/grok-4)
# These are OpenRouter's representation of xAI models, NOT direct xAI API calls
elif model_lower.startswith("xai/") or model_lower.startswith("x-ai/"):
    # MARKER_94.8_OPENROUTER_XAI: Models like "x-ai/grok-4" or "xai/grok-4"
    # are OpenRouter models, not direct xAI API
    return Provider.OPENROUTER

# ... rest of logic ...
```

## The Routing Flow (FIXED)

```
User Input: x-ai/grok-4
    ↓
detect_provider() returns Provider.OPENROUTER [CORRECT!]
    ↓
OpenRouterProvider.call(model="x-ai/grok-4")
    ↓
Clean model: clean_model = "x-ai/grok-4".replace("openrouter/", "") → "x-ai/grok-4"
    (Note: no "openrouter/" prefix, so model stays as "x-ai/grok-4")
    ↓
POST https://openrouter.ai/api/v1/chat/completions with model="x-ai/grok-4"
    ↓
200 OK (OpenRouter understands "x-ai/grok-4" as xAI's grok-4)
```

## Alternative: Direct xAI API

If user specifies direct xAI model:
```
User Input: grok-4
    ↓
detect_provider() returns Provider.XAI [CORRECT!]
    ↓
XaiProvider.call(model="grok-4")
    ↓
Clean model: "grok-4" (no prefix to strip)
    ↓
POST https://api.x.ai/v1/chat/completions with model="grok-4"
    ↓
200 OK (direct xAI API)
```

## Test Cases

### Case 1: OpenRouter xAI (FIXED)
- Input: `x-ai/grok-4`
- Expected provider: `OPENROUTER`
- Expected endpoint: `openrouter.ai/api/v1/chat/completions`
- Expected model name sent: `x-ai/grok-4`

### Case 2: Direct xAI API (FIXED)
- Input: `grok-4`
- Expected provider: `XAI`
- Expected endpoint: `api.x.ai/v1/chat/completions`
- Expected model name sent: `grok-4`

### Case 3: Direct xAI API variant
- Input: `grok-beta`
- Expected provider: `XAI`
- Expected endpoint: `api.x.ai/v1/chat/completions`
- Expected model name sent: `grok-beta`

## Code Locations

### Where detect_provider is called:

1. **user_message_handler.py:534**
   ```python
   detected_provider = ProviderRegistry.detect_provider(requested_model)
   ```
   Then at line 540: `provider=detected_provider`

2. **user_message_handler.py:869**
   ```python
   detected_provider = ProviderRegistry.detect_provider(model_to_use)
   ```

3. **chat_handler.py:64**
   ```python
   canonical_provider = ProviderRegistry.detect_provider(model_name)
   ```

### Where XAI provider checks happen:

1. **provider_registry.py:801-915** - XaiProvider.call() implementation
2. **provider_registry.py:1073-1095** - Fallback logic when XAI fails
3. **provider_registry.py:1282-1302** - Streaming XAI support
4. **provider_registry.py:1441-1553** - Direct xAI streaming

## Impact

- **Broken flow**: `x-ai/grok-4` → 403 error when trying direct xAI API
- **Fixed flow**: `x-ai/grok-4` → Success via OpenRouter
- **Direct API still works**: `grok-4` → Success via direct xAI API
- **No breaking changes**: This is a pure BUG FIX, not a behavior change

## MARKER_94.8 Summary

- **Bug location**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/provider_registry.py:978-1043`
- **Bug type**: Router confusion - wrong provider selected for model ID format
- **Cause**: `x-ai/` prefix mistakenly treated as direct API indicator instead of OpenRouter format indicator
- **Fix**: Check for direct API format FIRST (grok-* with no slash), then handle OpenRouter prefixed models
- **Status**: FIXED with detailed comments and markers
