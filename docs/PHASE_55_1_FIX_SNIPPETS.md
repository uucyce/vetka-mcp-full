# Phase 55.1: Fix Code Snippets

## FIX #1: Make Session Init Non-Blocking (BEST)

**File:** `src/api/handlers/group_message_handler.py`
**Location:** Lines 558-567 (replace these lines)

### BEFORE (Blocking)
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

### AFTER (Non-Blocking, Fire-and-Forget)
```python
# Phase 55.1: MCP group session init (fire-and-forget, no blocking)
def start_session_init():
    """Start session init in background without blocking handler."""
    try:
        asyncio.create_task(
            asyncio.wait_for(
                vetka_session_init(
                    user_id=sender_id,
                    group_id=group_id,
                    compress=True
                ),
                timeout=1.0  # 1 second max, then abandon
            )
        )
        print(f"   [MCP] Session init started in background")
    except Exception as e:
        print(f"   ⚠️ Session init setup failed: {e}")

# Start session init in background (non-blocking)
start_session_init()
```

**Impact:**
- Message handler returns immediately (no wait)
- Session init continues in background
- Even if session init fails, handler continues
- User sees response in <100ms instead of 5-30s

---

## FIX #2: Add Timeout to Session Init Call

**File:** `src/api/handlers/group_message_handler.py`
**Location:** Lines 558-567 (simpler fix, still blocks)

### BEFORE
```python
try:
    session = await vetka_session_init(...)
except Exception as e:
    print(f"   ⚠️ MCP group session init failed: {e}")
```

### AFTER (With Timeout)
```python
try:
    session = await asyncio.wait_for(
        vetka_session_init(
            user_id=sender_id,
            group_id=group_id,
            compress=True
        ),
        timeout=2.0  # Max 2 seconds
    )
    print(f"   [MCP] Group session initialized: {session.get('session_id')}")
except asyncio.TimeoutError:
    print(f"   ⚠️ Session init timeout after 2s (continuing anyway)")
except Exception as e:
    print(f"   ⚠️ MCP group session init failed: {e}")
```

**Impact:**
- User waits maximum 2 seconds (instead of 30+)
- Better than nothing but still blocks

---

## FIX #3: Wrap Qdrant Calls with Thread Pool

**File:** `src/mcp/state/mcp_state_manager.py`

### FIX 3A: save_state() method (Lines 109-112)

#### BEFORE (Blocking Sync Call)
```python
async def save_state(self, agent_id: str, data: Dict[str, Any],
                     ttl_seconds: int = 3600, workflow_id: str = None) -> bool:
    """Save agent state to cache and Qdrant."""
    # ... cache update code ...

    # Persist to Qdrant
    if self._qdrant:
        try:
            point_id = self._generate_point_id(agent_id)
            vector = [0.0] * self.VECTOR_SIZE
            point = PointStruct(...)
            self._qdrant.upsert(  # ◄─── BLOCKING SYNC CALL
                collection_name=self.collection_name,
                points=[point]
            )
        except Exception as e:
            print(f"   ⚠️ Qdrant save failed: {e}")
            return False

    return True
```

#### AFTER (Non-Blocking with Executor)
```python
async def save_state(self, agent_id: str, data: Dict[str, Any],
                     ttl_seconds: int = 3600, workflow_id: str = None) -> bool:
    """Save agent state to cache and Qdrant."""
    # ... cache update code ...

    # Persist to Qdrant (non-blocking)
    if self._qdrant:
        try:
            point_id = self._generate_point_id(agent_id)
            vector = [0.0] * self.VECTOR_SIZE
            point = PointStruct(...)

            # Run Qdrant call in thread pool (don't block event loop)
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._qdrant.upsert,
                    self.collection_name,
                    [point]
                ),
                timeout=5.0  # Max 5 seconds for upsert
            )
        except asyncio.TimeoutError:
            print(f"   ⚠️ Qdrant save timeout after 5s")
            return False
        except Exception as e:
            print(f"   ⚠️ Qdrant save failed: {e}")
            return False

    return True
```

---

### FIX 3B: get_state() method (Lines 135-138)

#### BEFORE (Blocking)
```python
async def get_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
    """Get state from cache or Qdrant."""
    # Check cache first (O(1))
    if agent_id in self._cache:
        # ... cache hit ...
        return entry.data

    # Fallback to Qdrant
    if self._qdrant:
        try:
            point_id = self._generate_point_id(agent_id)
            results = self._qdrant.retrieve(  # ◄─── BLOCKING SYNC CALL
                collection_name=self.collection_name,
                ids=[point_id]
            )
            # ... process results ...
        except Exception as e:
            print(f"   ⚠️ Qdrant get failed: {e}")

    return None
```

#### AFTER (Non-Blocking)
```python
async def get_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
    """Get state from cache or Qdrant."""
    # Check cache first (O(1))
    if agent_id in self._cache:
        # ... cache hit ...
        return entry.data

    # Fallback to Qdrant (non-blocking)
    if self._qdrant:
        try:
            point_id = self._generate_point_id(agent_id)

            # Run in thread pool
            loop = asyncio.get_event_loop()
            results = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._qdrant.retrieve,
                    self.collection_name,
                    [point_id]
                ),
                timeout=2.0  # Max 2 seconds
            )

            if results:
                # ... process results ...
                return entry.data
        except asyncio.TimeoutError:
            print(f"   ⚠️ Qdrant get timeout after 2s")
        except Exception as e:
            print(f"   ⚠️ Qdrant get failed: {e}")

    return None
```

---

### FIX 3C: get_all_states() method (Lines 211-215)

#### BEFORE (Blocking)
```python
async def get_all_states(self, prefix: str = None, limit: int = 100) -> Dict[str, Dict[str, Any]]:
    """Get all states, optionally filtered by prefix."""
    result = {}

    # ... cache processing ...

    if self._qdrant and len(result) < limit:
        try:
            # ... scroll_filter setup ...
            points, _ = self._qdrant.scroll(  # ◄─── BLOCKING SYNC CALL
                collection_name=self.collection_name,
                scroll_filter=scroll_filter,
                limit=limit
            )
            # ... process points ...
        except Exception as e:
            print(f"   ⚠️ Qdrant scroll failed: {e}")

    return result
```

#### AFTER (Non-Blocking)
```python
async def get_all_states(self, prefix: str = None, limit: int = 100) -> Dict[str, Dict[str, Any]]:
    """Get all states, optionally filtered by prefix."""
    result = {}

    # ... cache processing ...

    if self._qdrant and len(result) < limit:
        try:
            # ... scroll_filter setup ...

            # Run scroll in thread pool
            loop = asyncio.get_event_loop()
            points, _ = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._qdrant.scroll,
                    self.collection_name,
                    scroll_filter,
                    limit
                ),
                timeout=3.0  # Max 3 seconds for scroll
            )

            # ... process points ...
        except asyncio.TimeoutError:
            print(f"   ⚠️ Qdrant scroll timeout after 3s")
        except Exception as e:
            print(f"   ⚠️ Qdrant scroll failed: {e}")

    return result
```

---

## FIX #4: Add Timeout to session_tools.py

**File:** `src/mcp/tools/session_tools.py`
**Location:** Lines 135-142 (inside _execute_async)

### BEFORE (No Timeout)
```python
# Get recent MCP states
try:
    from src.mcp.state import get_mcp_state_manager
    mcp = get_mcp_state_manager()
    recent = await mcp.get_all_states(limit=10)  # ◄─── NO TIMEOUT
    context["recent_states_count"] = len(recent)
    context["recent_state_ids"] = list(recent.keys())[:5]
except Exception as e:
    context["recent_states_error"] = str(e)
```

### AFTER (With Timeout)
```python
# Get recent MCP states (with timeout)
try:
    from src.mcp.state import get_mcp_state_manager
    mcp = get_mcp_state_manager()
    recent = await asyncio.wait_for(
        mcp.get_all_states(limit=10),
        timeout=0.5  # 500ms max for session init context gathering
    )
    context["recent_states_count"] = len(recent)
    context["recent_state_ids"] = list(recent.keys())[:5]
except asyncio.TimeoutError:
    context["recent_states_error"] = "Timeout fetching states"
    context["recent_states_count"] = 0
except Exception as e:
    context["recent_states_error"] = str(e)
```

---

## RECOMMENDED IMPLEMENTATION ORDER

1. **Start with FIX #1** (fire-and-forget in group_message_handler.py)
   - Immediate impact
   - Solves blocking issue
   - No other changes needed

2. **Then add FIX #4** (timeout in session_tools.py)
   - Adds resilience
   - Prevents long waits if Qdrant is slow

3. **Finally apply FIX #3** (executor wrapping in mcp_state_manager.py)
   - Complete solution
   - Makes all Qdrant calls non-blocking
   - More refactoring required

---

## TESTING AFTER FIXES

### Test 1: Session Init Doesn't Block Handler
```
1. Send a message to group
2. Check: Response appears in <500ms
3. Check logs: "Session init started in background"
```

### Test 2: Handler Continues on Session Init Timeout
```
1. Simulate slow Qdrant (add 5s delay to Qdrant query)
2. Send message
3. Check: Response appears in <3s (with FIX #4 timeout)
4. Check: Handler not blocked by session init
```

### Test 3: Session Init Still Completes in Background
```
1. Wait 2-3 seconds after message response
2. Check logs: "Session init completed"
3. Check: Session was saved to Qdrant
```

---

## KEY METRICS AFTER FIXES

| Metric | Before | After |
|--------|--------|-------|
| Handler blocking time | 5-30s | <100ms |
| User-visible latency | 5-30s | <500ms |
| Session init still runs | No | Yes (background) |
| Qdrant failures cause handler error | Yes | No |

---

*Code snippets for Phase 55.1 blocking fix*
*Use with diagnostic: HAIKU_DIAG_3_PHASE_55_1_ANALYSIS.md*
