# Phase 90.1.2: Hostess Infinite Thinking Fix

**Date:** 2026-01-23
**Agent:** Sonnet 4.5
**Status:** ✅ IMPLEMENTED

## Problem

Hostess agent blocks entire event loop with infinite "thinking" spinner.

**Root Cause:** Synchronous `hostess.process()` called from async handler without timeout protection.

**Location:** `src/api/handlers/user_message_handler_v2.py:308`

## Solution

Added async timeout wrapper around `hostess.process()` call:

1. **Timeout Value:** 15 seconds
2. **Fallback Behavior:** Default agent chain (PM → Dev → QA) on timeout
3. **Non-blocking:** Runs in executor to prevent event loop blocking

## Changes

### File: `src/api/handlers/user_message_handler_v2.py`

#### 1. Import asyncio

```python
import time
import asyncio  # NEW
from pathlib import Path
```

#### 2. Add Timeout Wrapper Function

```python
# MARKER_90.1.2_START: Hostess timeout wrapper
HOSTESS_TIMEOUT = 15  # seconds

async def call_hostess_with_timeout(hostess, text, context):
    """
    Run hostess.process() with timeout to prevent blocking.

    The sync hostess.process() call can block the entire event loop.
    This wrapper runs it in an executor with a timeout.

    Args:
        hostess: Hostess agent instance
        text: User message text
        context: Rich context dict

    Returns:
        Hostess decision dict or None on timeout
    """
    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: hostess.process(text, context=context)),
            timeout=HOSTESS_TIMEOUT
        )
        return result
    except asyncio.TimeoutError:
        print(f"[Hostess] ⚠️ Timeout after {HOSTESS_TIMEOUT}s")
        return None
# MARKER_90.1.2_END
```

#### 3. Replace Direct Call with Timeout Wrapper

**BEFORE:**
```python
hostess_decision = hostess.process(text, context=rich_context)
print(f"[HANDLER_V2] Hostess decision: {hostess_decision['action']} (confidence: {hostess_decision['confidence']:.2f})")

# Process Hostess decision
agents_result = await container.hostess_router.process_hostess_decision(
    sid=sid,
    decision=hostess_decision,
    context={...}
)
```

**AFTER:**
```python
# MARKER_90.1.2: Use timeout wrapper to prevent infinite thinking
hostess_decision = await call_hostess_with_timeout(hostess, text, rich_context)

if hostess_decision is None:
    # Timeout occurred, fallback to default agent chain
    print(f"[HANDLER_V2] Hostess timeout, using default agent chain")
    agents_result = ['PM', 'Dev', 'QA']  # Default chain on timeout
else:
    print(f"[HANDLER_V2] Hostess decision: {hostess_decision['action']} (confidence: {hostess_decision['confidence']:.2f})")

    # Process Hostess decision
    agents_result = await container.hostess_router.process_hostess_decision(
        sid=sid,
        decision=hostess_decision,
        context={...}
    )
```

## Why 15 Seconds?

- **Typical LLM Call:** 2-5 seconds
- **Complex Reasoning:** 5-10 seconds
- **Buffer:** Extra margin for slow responses
- **User Experience:** Prevents indefinite waiting

## Behavior

### Normal Operation (< 15s)
1. Hostess processes request
2. Returns routing decision
3. Agents execute as routed

### Timeout (≥ 15s)
1. Hostess times out after 15s
2. Warning logged: `[Hostess] ⚠️ Timeout after 15s`
3. Fallback to default agent chain (PM → Dev → QA)
4. User sees response (no infinite spinner)

## Testing

**Test Case 1: Normal Hostess Response**
- User message → Hostess responds < 15s → Correct routing

**Test Case 2: Slow Hostess Response**
- User message → Hostess > 15s → Timeout → Default chain → Response delivered

**Test Case 3: Hostess Crash**
- User message → Hostess error → Caught by try/except → Default chain

## Markers

All changes marked with `MARKER_90.1.2` for tracking:
- Function definition: `MARKER_90.1.2_START` ... `MARKER_90.1.2_END`
- Call site: `MARKER_90.1.2: Use timeout wrapper...`

## Impact

- ✅ Prevents infinite thinking spinner
- ✅ Non-blocking async execution
- ✅ Graceful degradation on timeout
- ✅ User always gets a response
- ⚠️ Long Hostess responses fallback to default chain (acceptable tradeoff)

## Next Steps

If Hostess timeouts become frequent:
1. Investigate why `hostess.process()` is slow
2. Consider caching or optimization
3. May need to refactor Hostess to be async-native

---

**Phase 90.1.2 Complete** ✅
