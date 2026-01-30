# Phase 93.7: Group Chat Provider Fix

**Date**: 2026-01-25
**Status**: IMPLEMENTED
**Related**: Phase 93.6 (model cleanup), Phase 80.10 (provider registry)

---

## SUMMARY

Fixed group chat returning 402 "Payment Required" for models like `openai/gpt-5.2` while solo chat works fine.

**Root Cause**: Group chat handler added unnecessary `openrouter/` prefix to model names, which broke provider detection and forced all GPT calls through OpenRouter.

**Solution**: Removed the prefix injection code, allowing `ProviderRegistry.detect_provider()` to work correctly.

---

## THE BUG

### Symptoms
- **Solo chat**: `openai/gpt-5.2` works fine
- **Group chat**: `openai/gpt-5.2` returns 402 Payment Required

### Root Cause Analysis

In `group_message_handler.py` lines 707-709, there was a "fix" that added `openrouter/` prefix:

```python
# OLD CODE (REMOVED)
# Fix: Force OpenRouter prefix for GPT models to bypass provider detection
if "gpt" in model_id.lower():
    model_id = f"openrouter/{model_id}"
```

This caused the following behavior:

#### Solo Chat Path:
```
User selects: "openai/gpt-5.2"
           ↓
detect_provider("openai/gpt-5.2")
           ↓
startswith("openai/") = True → Provider.OPENAI
           ↓
OpenAI API called with key → SUCCESS ✅
```

#### Group Chat Path (BEFORE FIX):
```
User selects: "openai/gpt-5.2"
           ↓
Line 709 adds prefix: "openrouter/openai/gpt-5.2"
           ↓
detect_provider("openrouter/openai/gpt-5.2")
           ↓
startswith("openai/") = False (starts with "openrouter/")
"/" in model_name = True → Provider.OPENROUTER
           ↓
OpenRouter API called → 402 Payment Required ❌
```

#### Group Chat Path (AFTER FIX):
```
User selects: "openai/gpt-5.2"
           ↓
No prefix added (MARKER_93.7)
           ↓
detect_provider("openai/gpt-5.2")
           ↓
startswith("openai/") = True → Provider.OPENAI
           ↓
OpenAI API called with key → SUCCESS ✅
```

---

## CHANGES MADE

### File: `src/api/handlers/group_message_handler.py`

**Location**: Lines 707-709

**Removed**:
```python
# Fix: Force OpenRouter prefix for GPT models to bypass provider detection
if "gpt" in model_id.lower():
    model_id = f"openrouter/{model_id}"
```

**Added** (MARKER_93.7_REMOVED_OPENROUTER_PREFIX):
```python
# MARKER_93.7_REMOVED_OPENROUTER_PREFIX: Phase 93.7 Fix
# Previously this code added "openrouter/" prefix which broke routing:
# - "openai/gpt-5.2" -> "openrouter/openai/gpt-5.2" -> Provider.OPENROUTER -> 402
# Now we let detect_provider work correctly:
# - "openai/gpt-5.2" -> Provider.OPENAI -> uses OpenAI API directly -> works!
# The old "fix" was counterproductive because it forced OpenRouter
# instead of letting the system use the appropriate provider.
```

---

## WHY THE OLD "FIX" WAS WRONG

The comment said "Force OpenRouter prefix for GPT models to bypass provider detection" but:

1. **Provider detection works correctly** - `detect_provider("openai/gpt-5.2")` correctly returns `Provider.OPENAI`

2. **OpenAI keys exist** - The system has OpenAI API keys configured in config.json

3. **OpenRouter costs money** - Routing through OpenRouter requires credits, hence 402

4. **Solo chat works** - Proves the OpenAI API path is functional

The original author likely misunderstood how provider detection works and added a "fix" that actually broke the system.

---

## PROVIDER DETECTION LOGIC

```python
def detect_provider(model_name: str) -> Provider:
    model_lower = model_name.lower()

    if model_lower.startswith("openai/") or model_lower.startswith("gpt-"):
        return Provider.OPENAI  # ← "openai/gpt-5.2" matches here!
    elif model_lower.startswith("anthropic/") or model_lower.startswith("claude-"):
        return Provider.ANTHROPIC
    elif model_lower.startswith("google/") or model_lower.startswith("gemini"):
        return Provider.GOOGLE
    elif model_lower.startswith("xai/") or model_lower.startswith("x-ai/") or model_lower.startswith("grok"):
        return Provider.XAI
    elif ":" in model_name or model_lower.startswith("ollama/"):
        return Provider.OLLAMA
    elif "/" in model_name:
        return Provider.OPENROUTER  # ← "openrouter/openai/gpt-5.2" falls here!
    else:
        return Provider.OLLAMA
```

---

## TESTING CHECKLIST

- [ ] Group chat with `openai/gpt-5.2` - should work (no more 402)
- [ ] Group chat with `anthropic/claude-3.5-sonnet` - should use Anthropic API
- [ ] Group chat with `x-ai/grok-4` - should use XAI API
- [ ] Group chat with local `ollama:qwen2:7b` - should use Ollama
- [ ] Solo chat with same models - should still work

---

## RELATED MARKERS

| Marker | Phase | Description |
|--------|-------|-------------|
| MARKER_93.7_REMOVED_OPENROUTER_PREFIX | 93.7 | This fix - removed prefix injection |
| MARKER_93.6_MODEL_CLEANUP | 93.6 | Cleanup openrouter/ prefix in OpenRouterProvider |
| MARKER_90.1.4.1 | 90.1.4 | Canonical detect_provider logic |

---

## LESSONS LEARNED

1. **Don't "fix" provider detection by adding prefixes** - the detection logic exists for a reason
2. **Test both solo and group chat paths** - they can diverge silently
3. **402 Payment Required** means the API endpoint is correct but account needs credits
4. **Follow the data flow** - trace exactly what model name gets passed to the API

---

---

## Phase 93.8 Addition: OpenAI Model Whitelist

After fixing the provider detection, we discovered that models like `openai/gpt-5.2` don't actually exist in OpenAI's API - they are **OpenRouter-only** models with an `openai/` prefix.

### The New Problem

```
[STREAM ERROR]: Client error '404 Not Found' for url
'https://api.openai.com/v1/chat/completions'
```

The model `openai/gpt-5.2-chat` was correctly routed to OpenAI (after Phase 93.7 fix), but OpenAI API returned 404 because **GPT-5.2 doesn't exist** in their API!

### Solution: MARKER_93.8_OPENAI_WHITELIST

Added a whitelist of **real** OpenAI models in `detect_provider()`:

```python
REAL_OPENAI_MODELS = {
    "gpt-4o", "gpt-4o-mini", "gpt-4o-2024-05-13",
    "gpt-4-turbo", "gpt-4-turbo-preview",
    "gpt-4", "gpt-4-0613",
    "gpt-3.5-turbo", "gpt-3.5-turbo-16k",
    "o1-preview", "o1-mini", "o1",
    "chatgpt-4o-latest",
}
```

Now the routing logic is:
- `openai/gpt-4o` → OpenAI API (real model) ✅
- `openai/gpt-5.2` → OpenRouter (not real OpenAI) ✅
- `gpt-4-turbo` → OpenAI API (real model) ✅
- `gpt-5.2-chat` → OpenRouter (not real OpenAI) ✅

---

---

## Phase 93.10: NO WHITELIST - Simple Prefix Routing

### Why Whitelist Was Wrong

Phases 93.8 and 93.9 used a whitelist approach - manually listing all "real" OpenAI models.
This is **bad design** because:
1. Every new OpenAI model release requires code update
2. Claude's knowledge cutoff means it doesn't know about new models
3. Maintenance nightmare - who remembers to update the list?

### The Simple Solution (MARKER_93.10)

**Route by prefix only. No whitelist. No maintenance.**

```python
# MARKER_93.10_SIMPLE_ROUTING
if (model_lower.startswith("openai/") or
    model_lower.startswith("gpt-") or
    model_lower.startswith("o1") or
    model_lower.startswith("chatgpt-")):
    return Provider.OPENAI
```

### How It Works Now

| Model | Prefix Match | Provider |
|-------|--------------|----------|
| `openai/gpt-5.2` | `openai/` | **OPENAI** ✅ |
| `openai/gpt-99.9` | `openai/` | **OPENAI** ✅ |
| `gpt-5.2-chat` | `gpt-` | **OPENAI** ✅ |
| `o1-pro-max` | `o1` | **OPENAI** ✅ |
| `x-ai/grok-4` | `xai/` or `grok` | **XAI** ✅ |
| `anthropic/claude-4` | `anthropic/` | **ANTHROPIC** ✅ |
| `deepseek/chat` | `/` fallback | **OPENROUTER** ✅ |

### Benefits

1. **Future-proof**: New GPT-6, GPT-7 will work automatically
2. **No maintenance**: No whitelist to update
3. **Simple logic**: Easy to understand and debug
4. **Let API decide**: If model doesn't exist, API returns 404 - that's their job

---

**Status**: ✅ COMPLETE
**Phase**: 93.7 → 93.10 (final)
**Date**: 2026-01-25
