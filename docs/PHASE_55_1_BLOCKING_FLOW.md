# Phase 55.1: Blocking Flow Diagram

## BLOCKING CHAIN

```
USER SENDS MESSAGE
│
└─ Socket.IO: on("group_message")
   │
   └─ handle_group_message(sid, data)
      │
      ├─ Line 545: Print entry
      │
      └─ Line 558-567: ⚠️ BLOCKING SESSION INIT
         │
         └─ await vetka_session_init(
               user_id=sender_id,
               group_id=group_id,
               compress=True
            )  ◄─── NO TIMEOUT, NO ASYNCIO.WAIT_FOR
            │
            └─ session_tools.py: vetka_session_init()
               │
               ├─ Line 114-132: Get user preferences (OK, has try/except)
               │
               ├─ Line 135-142: ⚠️ GET MCP STATES (BLOCKING)
               │  │
               │  └─ await mcp.get_all_states(limit=10)  ◄─── NO TIMEOUT
               │     │
               │     └─ mcp_state_manager.py: get_all_states()
               │        │
               │        ├─ Check cache (O(1), OK)
               │        │
               │        └─ If cache miss & Qdrant available:
               │           │
               │           └─ Line 211: ⚠️ BLOCKING SYNC CALL
               │              │
               │              └─ self._qdrant.scroll(
               │                    collection_name="vetka_mcp_states",
               │                    scroll_filter=scroll_filter,
               │                    limit=limit
               │                 )
               │                 │
               │                 ├─ No timeout parameter
               │                 ├─ No async wrapper
               │                 ├─ No connection pooling
               │                 │
               │                 └─ BLOCKS EVENT LOOP
               │                    If Qdrant slow: ⏳ 5-30+ seconds
               │
               ├─ Line 145-159: ELISION compression (OK)
               │
               └─ Line 162-169: ⚠️ SAVE SESSION STATE (BLOCKING)
                  │
                  └─ await mcp.save_state(session_id, context)
                     │
                     └─ mcp_state_manager.py: save_state()
                        │
                        ├─ Update cache (OK)
                        │
                        └─ Line 109-112: ⚠️ BLOCKING SYNC CALL
                           │
                           └─ self._qdrant.upsert(
                                collection_name="vetka_mcp_states",
                                points=[point]
                              )
                              │
                              ├─ No timeout
                              ├─ No async wrapper
                              │
                              └─ BLOCKS EVENT LOOP (again)

[Session init returns] ◄─── After all Qdrant calls complete

│
└─ handler continues...
   └─ Line 569: if not group_id... (validation - SHOULD BE HERE!)
   │
   └─ Lines 575+: Get group manager, store user message, etc.
      │
      └─ Lines 651+: Get orchestrator and call agents
```

---

## TIMING ANALYSIS

### Best Case (Cache Hits)
```
User sends message
│
├─ Session init starts
│  └─ Cache hit on all calls: ~50ms
│
└─ Handler continues: ✓ Fast response

TOTAL LATENCY: ~100ms (acceptable)
```

### Worst Case (Qdrant Slow)
```
User sends message
│
├─ Session init starts
│  ├─ get_all_states() → Qdrant timeout (30s default)
│  │  └─ EVENT LOOP BLOCKED 30 seconds
│  │
│  └─ save_state() → Qdrant upsert (5s)
│     └─ EVENT LOOP BLOCKED 5 more seconds
│
└─ Handler continues: ✗ Very slow response

TOTAL LATENCY: 35+ seconds (UNACCEPTABLE)
```

---

## THE CORE ISSUE

### Phase 55.1 Code (Line 558-567)

```python
@sio.on("group_message")
async def handle_group_message(sid, data):
    # ... (lines 544-557: print and parse)

    # Phase 55.1: MCP group session init
    try:
        session = await vetka_session_init(  # ◄─── BLOCKING!
            user_id=sender_id,
            group_id=group_id,
            compress=True
        )
        print(f"   [MCP] Group session initialized: {session.get('session_id')}")
    except Exception as e:
        print(f"   ⚠️ MCP group session init failed: {e}")

    # Only AFTER session init completes, validation happens
    if not group_id or not content:  # ◄─── Should be HERE (before session init!)
        await sio.emit(
            "group_error", {"error": "Missing group_id or content"}, to=sid
        )
        return
```

**Problems:**
1. ❌ `vetka_session_init()` has NO timeout
2. ❌ Session init called BEFORE input validation
3. ❌ No asyncio.wait_for wrapper
4. ❌ Exception handling doesn't prevent blocking (just logs)

---

## QDRANT OPERATIONS IN MCPStateManager

All these are **sync calls in async methods** (NO timeout):

### save_state() - Line 109-112
```python
async def save_state(...):
    # ...
    if self._qdrant:
        self._qdrant.upsert(  # ◄─── BLOCKING SYNC
            collection_name=self.collection_name,
            points=[point]
        )
```

### get_state() - Line 135-138
```python
async def get_state(...):
    # ...
    if self._qdrant:
        results = self._qdrant.retrieve(  # ◄─── BLOCKING SYNC
            collection_name=self.collection_name,
            ids=[point_id]
        )
```

### get_all_states() - Line 211-215
```python
async def get_all_states(...):
    # ...
    if self._qdrant and len(result) < limit:
        points, _ = self._qdrant.scroll(  # ◄─── BLOCKING SYNC
            collection_name=self.collection_name,
            scroll_filter=scroll_filter,
            limit=limit
        )
```

**All lack:**
- Timeout parameters
- Async wrappers (`run_in_executor`)
- Connection timeouts on client

---

## FIX PRIORITY

### PRIORITY 1 (Immediate Impact)

**File:** `src/api/handlers/group_message_handler.py:560`

Change from **blocking await** to **fire-and-forget task**:

```python
# BEFORE (blocks)
session = await vetka_session_init(...)

# AFTER (non-blocking)
asyncio.create_task(
    asyncio.wait_for(
        vetka_session_init(...),
        timeout=1.0
    )
)
# Continue immediately
```

**Result:** Message handler never blocks on session init

---

### PRIORITY 2 (Add Resilience)

**File:** `src/mcp/state/mcp_state_manager.py` (all Qdrant ops)

Wrap with `run_in_executor`:

```python
# BEFORE (blocks event loop)
self._qdrant.upsert(...)

# AFTER (thread pool)
loop = asyncio.get_event_loop()
await loop.run_in_executor(
    None,
    self._qdrant.upsert,
    self.collection_name,
    [point]
)
```

**Result:** Qdrant ops don't block event loop

---

### PRIORITY 3 (Add Timeout)

**File:** `src/mcp/tools/session_tools.py:138`

Add timeout to get_all_states:

```python
# BEFORE
recent = await mcp.get_all_states(limit=10)

# AFTER
try:
    recent = await asyncio.wait_for(
        mcp.get_all_states(limit=10),
        timeout=0.5
    )
except asyncio.TimeoutError:
    recent = {}
```

**Result:** Session init never waits >0.5s

---

## VALIDATION ORDER (Current: WRONG)

```
[BLOCKING] Session init
    ↓
[VALIDATION] Check group_id/content ◄─── Should be FIRST!

SHOULD BE:
[VALIDATION] Check group_id/content ◄─── First
    ↓
[OPTIONAL] Session init (with timeout or fire-and-forget)
```

---

## MARKERS REFERENCE

| Marker | File | Line | Type | Severity |
|--------|------|------|------|----------|
| INIT-001 | mcp_state_manager.py | 109-258 | Sync calls in async | CRITICAL |
| INIT-002 | group_message_handler.py | 560 | No timeout | CRITICAL |
| INIT-003 | session_tools.py | 138 | No timeout | HIGH |
| INIT-004 | mcp_state_manager.py | 56-65 | No timeout config | HIGH |
| INIT-005 | mcp_state_manager.py | 72-265 | No pooling | HIGH |

---

Generated by HAIKU diagnostic system
