# HAIKU-DIAG-3: Phase 55.1 Session Init Blocking Analysis

**Status:** CRITICAL BLOCKING ISSUES FOUND
**Date:** 2026-01-26
**Severity:** High - Potential message handler blocking

---

## MARKER-INIT-001: Synchronous Qdrant Calls in Async Context

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/state/mcp_state_manager.py`
**Lines:** 109-112, 135-138, 211-215, 248-252, 255-258

### Issue Description

The MCPStateManager makes **synchronous Qdrant calls** without timeout protection inside **async methods**. These are blocking operations:

```python
# Line 109-112: upsert - BLOCKING SYNC CALL
self._qdrant.upsert(
    collection_name=self.collection_name,
    points=[point]
)

# Line 135-138: retrieve - BLOCKING SYNC CALL
results = self._qdrant.retrieve(
    collection_name=self.collection_name,
    ids=[point_id]
)

# Line 211-215: scroll - BLOCKING SYNC CALL
points, _ = self._qdrant.scroll(
    collection_name=self.collection_name,
    scroll_filter=scroll_filter,
    limit=limit
)

# Line 248-252: scroll in delete_expired_states - BLOCKING SYNC CALL
points, _ = self._qdrant.scroll(
    collection_name=self.collection_name,
    scroll_filter=expired_filter,
    limit=1000
)

# Line 255-258: delete - BLOCKING SYNC CALL
self._qdrant.delete(
    collection_name=self.collection_name,
    points_selector=ids
)
```

**Problem:** These are marked as `async` methods but execute **synchronous blocking calls**. If Qdrant is slow or unresponsive, the entire event loop freezes.

---

## MARKER-INIT-002: Session Init Called Without Timeout in Message Handler

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`
**Lines:** 558-567

### Issue Description

```python
# Phase 55.1: MCP group session init
try:
    session = await vetka_session_init(
        user_id=sender_id,
        group_id=group_id,
        compress=True
    )
    print(f"   [MCP] Group session initialized: {session.get('session_id')}")
except Exception as e:
    print(f"   ⚠️ MCP group session init failed: {e}")
```

**Problem:**
- `vetka_session_init()` is awaited **WITHOUT timeout**
- If `vetka_session_init()` calls `get_mcp_state_manager().get_all_states()` (line 138 in session_tools.py), it may block indefinitely
- This is called at the **START** of message handler (line 558), BEFORE validating group_id/content
- If this blocks, the user sees NO response while waiting for Qdrant

**Risk Chain:**
1. User sends message → `handle_group_message()` called
2. Line 560: `await vetka_session_init()` (NO TIMEOUT)
3. → calls `mcp.get_all_states()` (line 138 in session_tools.py)
4. → calls `self._qdrant.scroll()` (line 211 in mcp_state_manager.py)
5. → BLOCKS entire event loop if Qdrant is slow/down

---

## MARKER-INIT-003: Missing Error Context in Session Init

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/session_tools.py`
**Lines:** 114-142, 135-142

### Issue Description

```python
# Line 114-142: Get user preferences (has try/except)
try:
    from src.memory.engram_user_memory import get_engram_user_memory
    engram = get_engram_user_memory()
    prefs = engram.get_user_preferences(user_id)
    # ... process prefs
except Exception as e:
    context["user_preferences_error"] = str(e)

# Line 135-142: Get recent MCP states (CRITICAL - no timeout)
try:
    from src.mcp.state import get_mcp_state_manager
    mcp = get_mcp_state_manager()
    recent = await mcp.get_all_states(limit=10)  # <-- NO TIMEOUT HERE
    context["recent_states_count"] = len(recent)
    context["recent_state_ids"] = list(recent.keys())[:5]
except Exception as e:
    context["recent_states_error"] = str(e)
```

**Problem:**
- `get_all_states()` has no timeout parameter
- Exception handler captures error but doesn't prevent blocking

---

## MARKER-INIT-004: Qdrant Client Configuration Without Timeout

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/state/mcp_state_manager.py`
**Lines:** 56-65

### Issue Description

```python
def _init_qdrant(self):
    """Initialize Qdrant client and collection."""
    if not QDRANT_AVAILABLE:
        print("   ⚠️ Qdrant not available - using cache only")
        return
    try:
        from src.memory.qdrant_client import get_qdrant_client
        self._qdrant = get_qdrant_client()
    except Exception as e:
        print(f"   ⚠️ Qdrant init failed: {e}")
```

**Problem:**
- Qdrant client is initialized once without timeout parameters
- No timeout configuration passed to the client
- All subsequent calls inherit no-timeout behavior

---

## MARKER-INIT-005: No Connection Pool or Retry Logic

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/state/mcp_state_manager.py`
**All Qdrant operations (lines 109-258)**

### Issue Description

All Qdrant operations:
- Have no connection pool timeout
- Have no retry logic
- Have no circuit breaker
- Have no connection pooling
- If Qdrant is slow: operations block the event loop

---

## RECOMMENDED FIXES

### Priority 1: Add Timeout to Session Init in Message Handler

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`
**Line 560**

```python
# BEFORE
try:
    session = await vetka_session_init(
        user_id=sender_id,
        group_id=group_id,
        compress=True
    )
except Exception as e:
    print(f"   ⚠️ MCP group session init failed: {e}")

# AFTER - Add timeout, make it fire-and-forget
try:
    # Non-blocking session init with 1s timeout
    asyncio.create_task(
        asyncio.wait_for(
            vetka_session_init(
                user_id=sender_id,
                group_id=group_id,
                compress=True
            ),
            timeout=1.0  # 1 second max
        )
    )
    # Continue without waiting
except asyncio.TimeoutError:
    print(f"   ⚠️ Session init timeout (continuing anyway)")
except Exception as e:
    print(f"   ⚠️ Session init error: {e}")
```

**Why:** Converts from blocking await to fire-and-forget task. Message handler continues immediately, session init happens in background.

---

### Priority 2: Add Timeout to get_all_states()

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/session_tools.py`
**Line 138**

```python
# BEFORE
recent = await mcp.get_all_states(limit=10)

# AFTER
try:
    recent = await asyncio.wait_for(
        mcp.get_all_states(limit=10),
        timeout=0.5  # 500ms max
    )
except asyncio.TimeoutError:
    print(f"   ⚠️ MCP states timeout - using empty")
    recent = {}
```

---

### Priority 3: Make Qdrant Calls Non-Blocking

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/state/mcp_state_manager.py`

Option A (Quick Fix): Wrap sync Qdrant calls with run_in_executor:

```python
# In save_state() method, line 109-112
if self._qdrant:
    try:
        # ... prepare point ...
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._qdrant.upsert,
            self.collection_name,
            [point]
        )
    except Exception as e:
        print(f"   ⚠️ Qdrant save failed: {e}")
```

This moves Qdrant calls to thread pool, prevents event loop blocking.

---

## DIAGNOSIS SUMMARY

| Marker | Severity | Issue | Impact |
|--------|----------|-------|--------|
| INIT-001 | **CRITICAL** | Sync Qdrant calls in async code | Event loop blocking |
| INIT-002 | **CRITICAL** | No timeout on session_init | Message handler hangs |
| INIT-003 | **HIGH** | No timeout on get_all_states | Can block 5+ seconds |
| INIT-004 | **HIGH** | Qdrant client no timeout config | All ops inherit no timeout |
| INIT-005 | **HIGH** | No connection pooling | Single request blocks all |

---

## FLOW ANALYSIS: What Blocks

```
User sends message
    ↓
handle_group_message() starts
    ↓
[BLOCKING] await vetka_session_init() - Line 560
    ↓
    → calls mcp.get_all_states() - session_tools.py:138
        ↓
        [BLOCKING] await mcp.get_all_states(limit=10)
        ↓
        → calls self._qdrant.scroll() - mcp_state_manager.py:211
        ↓
        [BLOCKING] sync scroll() with no timeout
        ↓
        If Qdrant is slow/down: BLOCKS HERE

    ← returns only after Qdrant responds OR error caught

    ← returns to handler

Message handler continues (after session init done)
```

**If Qdrant timeout is 30s, user waits 30s before seeing response.**

---

## IMMEDIATE ACTION PLAN

1. **Change session init to fire-and-forget** (Priority 1)
   - Allows message handler to continue immediately
   - Session initialization happens in background

2. **Add 1s timeout to session init** (Priority 2)
   - Prevents blocking if session init takes too long

3. **Wrap Qdrant calls with run_in_executor** (Priority 3)
   - Thread pool handles slow Qdrant operations
   - Event loop stays responsive

---

## EXPECTED IMPACT AFTER FIXES

- **Before:** Message handler can block 5-30+ seconds on Qdrant
- **After:** Message handler continues in <100ms, session init in background

This is **essential for multi-user responsiveness** in group chat.

---

*Report generated by HAIKU diagnostic system*
*Markers: INIT-001, INIT-002, INIT-003, INIT-004, INIT-005*
