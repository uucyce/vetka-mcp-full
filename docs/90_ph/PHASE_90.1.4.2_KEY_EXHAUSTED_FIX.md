# Phase 90.1.4.2: XaiKeysExhausted Exception Handling for Group Chat

**Date:** 2026-01-23
**Status:** ✅ COMPLETED
**Type:** Bug Fix - Exception Handling

## Problem

Group chat was not catching the `XaiKeysExhausted` exception when XAI keys hit the 403 rate limit. This caused crashes or errors in group chat, while solo chat handled the exception properly with OpenRouter fallback.

**Symptoms:**
- Group chat fails when XAI key gets 403 Forbidden
- Solo chat works fine (has exception handling)
- Error: `XaiKeysExhausted` propagates to frontend

## Root Cause

The `XaiKeysExhausted` exception is raised in `provider_registry.py` (line 706) when all XAI keys return 403. However:

1. **Solo chat:** Already has fallback handling in `call_model_v2()` (lines 860-869)
2. **Group chat:** Calls orchestrator → `_call_llm_with_tools_loop()` → `call_model_v2()`
3. **Orchestrator:** Did NOT catch `XaiKeysExhausted`, so exception bubbled up to group handler

## Solution

Added `XaiKeysExhausted` exception handling at the orchestrator level, where all group chat requests flow through.

### Files Modified

#### 1. `src/orchestration/orchestrator_with_elisya.py`

**Import Added (Line 49):**
```python
from src.elisya.provider_registry import (
    call_model_v2,
    Provider,
    ProviderRegistry,
    get_registry,
    XaiKeysExhausted  # Phase 90.1.4.2: Handle XAI key exhaustion
)
```

**Exception Handling Added (Line 976-995):**
```python
# MARKER_90.1.4.2_START: Handle XaiKeysExhausted
try:
    response = await call_model_v2(
        messages=messages,
        model=model,
        provider=provider,
        tools=tool_schemas
    )
except XaiKeysExhausted:
    print(f"[Orchestrator] XAI keys exhausted, falling back to OpenRouter")
    # Retry with OpenRouter - convert model to x-ai/model format
    openrouter_model = f"x-ai/{model}" if not model.startswith('x-ai/') else model
    response = await call_model_v2(
        messages=messages,
        model=openrouter_model,
        provider=Provider.OPENROUTER,
        tools=None  # OpenRouter doesn't support tools well
    )
# MARKER_90.1.4.2_END
```

**Tool Loop Exception Handling Added (Line 1092-1110):**
Same exception handling added in the tool execution loop where `call_model_v2()` is called again with tool results.

### Fallback Logic

When `XaiKeysExhausted` is caught:

1. **Log the fallback:** Print message to console for debugging
2. **Convert model name:** `grok-4` → `x-ai/grok-4` (OpenRouter format)
3. **Retry with OpenRouter:** Use `Provider.OPENROUTER` explicitly
4. **Disable tools:** OpenRouter doesn't support tools well, so set `tools=None`

This matches the fallback behavior already implemented in `provider_registry.py` for solo chat.

## Testing Plan

### Manual Test Scenarios

1. **Normal Operation (XAI key works):**
   - Create group chat with Grok agent
   - Send message
   - ✅ Should respond normally using XAI

2. **XAI Rate Limit Hit:**
   - Trigger 403 on all XAI keys (24h rate limit)
   - Send message to Grok in group chat
   - ✅ Should see log: `[Orchestrator] XAI keys exhausted, falling back to OpenRouter`
   - ✅ Should get response from OpenRouter (x-ai/grok-4)
   - ✅ No crash or error shown to user

3. **Tool Loop Fallback:**
   - Send message that triggers tool calls
   - XAI key hits 403 during tool execution
   - ✅ Should fallback to OpenRouter mid-conversation
   - ✅ Tool results should still be processed (tools disabled for OpenRouter call)

### Log Markers

Look for these logs to verify correct behavior:

```
[XAI] ⚠️ 403 Forbidden - 24h timestamp limit, trying rotation...
[XAI] ❌ All xai keys exhausted (403), falling back to OpenRouter...
[Orchestrator] XAI keys exhausted, falling back to OpenRouter
[OPENROUTER] Calling x-ai/grok-4
```

## Code Architecture

```
Group Chat Flow:
┌─────────────────────────────────────────────┐
│ group_message_handler.py                    │
│   handle_group_message()                    │
│   ↓                                          │
│   orchestrator.call_agent()                 │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│ orchestrator_with_elisya.py                 │
│   _call_llm_with_tools_loop()               │
│   ↓                                          │
│   try:                                       │
│     call_model_v2(Provider.XAI)             │
│   except XaiKeysExhausted:  ← NEW!          │
│     call_model_v2(Provider.OPENROUTER)      │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│ provider_registry.py                        │
│   call_model_v2()                           │
│   ↓                                          │
│   xai_provider.call()                       │
│   ↓ (403 detected)                          │
│   raise XaiKeysExhausted()  ← Caught above  │
└─────────────────────────────────────────────┘
```

## Related Code

- **Exception Definition:** `src/elisya/provider_registry.py` (lines 26-28)
- **XAI Provider Logic:** `src/elisya/provider_registry.py` (lines 623-727)
- **Solo Chat Fallback:** `src/elisya/provider_registry.py` (lines 860-869) - Already works
- **Group Chat Handler:** `src/api/handlers/group_message_handler.py` (line 729) - Calls orchestrator
- **Unified Key Manager:** `src/utils/unified_key_manager.py` - Tracks 24h cooldowns

## Follow-up Tasks

- [ ] Add unit tests for `XaiKeysExhausted` handling in orchestrator
- [ ] Add integration test for group chat with XAI rate limit
- [ ] Consider adding retry count limit to prevent infinite OpenRouter fallbacks
- [ ] Add telemetry/metrics for XAI rate limit events

## References

- **Phase 80.39:** Added XAI key rotation + OpenRouter fallback in provider
- **Phase 80.40:** Fixed key rotation bugs (singleton, attribute names)
- **Phase 90.1.4.1:** Haiku research identifying the group chat bug
- **Phase 90.1.4.2:** This fix - orchestrator exception handling
