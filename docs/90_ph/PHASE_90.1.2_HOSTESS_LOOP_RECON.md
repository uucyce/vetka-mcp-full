# PHASE 90.1.2: Hostess Infinite Thinking Bug - Investigation Report

# MARKER_90.1.2_START: Hostess Loop Investigation

## Problem Statement
Hostess agent triggered, shows "thinking" spinner indefinitely with no response. Disk spinning. Never completes or timeouts.

## Investigation Findings

### 1. HOSTESS TRIGGER CONDITIONS

**Entry Points (Where Hostess gets invoked):**
- `src/api/handlers/user_message_handler_v2.py` (MAIN): Lines 290-331
  - Only triggered if `HOSTESS_AVAILABLE` is True
  - Called synchronously in async context: `hostess = get_hostess()` → `hostess_decision = hostess.process(text, context=rich_context)`
  - Process method is SYNCHRONOUS, not async

- `src/api/routes/chat_routes.py`: Direct call to hostess.process()
- `src/api/handlers/user_message_handler_legacy.py`: Legacy handler with same pattern

**Trigger Flow:**
```
user_message (Socket.IO)
  → handle_user_message() [async]
    → Line 291: if HOSTESS_AVAILABLE
      → Line 293: get_hostess() [gets singleton instance]
      → Line 308: hostess.process(text, context=rich_context) [SYNC CALL IN ASYNC CONTEXT]
        → Blocks async event loop
```

### 2. CRITICAL BUG: SYNC CODE IN ASYNC CONTEXT

**File:** `src/agents/hostess_agent.py`

**Issue:** The `process()` method is SYNCHRONOUS but called from an ASYNC handler without any thread wrapping.

```python
# Line 251: def process() - NO async keyword
def process(self, user_message: str, context: Dict = None) -> Dict[str, Any]:
    # Line 275: _call_ollama_with_tools is SYNC
    response_text = self._call_ollama_with_tools(system_prompt, user_message, context)

    # Line 427-430: Blocking HTTP call with 20s timeout
    resp = requests.post(
        f"{self.ollama_url}/api/generate",
        json=payload,
        timeout=20  # BLOCKING for 20 seconds
    )
```

**Why It Hangs:**
1. Async handler calls sync `hostess.process()` directly on event loop thread
2. Hostess makes blocking HTTP request to Ollama (timeout=20)
3. Event loop is BLOCKED for up to 20 seconds
4. If Ollama is slow or not responding, spinner shows indefinitely
5. No timeout at wrapper level - only internal 20s timeout

### 3. MISSING EXIT CONDITIONS

**In `hostess_agent.py`:**

1. **`_call_ollama_with_tools()` (line 385-445):**
   - 20s timeout on Ollama request ✓
   - BUT: If timeout occurs, returns empty string ""
   - No retry logic - immediate fallback
   - NO outer timeout wrapping the whole process() call

2. **`_parse_tool_call()` (line 447-539):**
   - Complex regex parsing with 3 fallback patterns
   - If regex fails, returns None
   - Then defaults to chain_call (line 281-289)
   - This IS a safety exit condition ✓

3. **`_execute_tool()` (line 541-895):**
   - Has try/except blocks for most tools ✓
   - BUT: No timeout on individual tool execution
   - API key learning (lines 679-720) uses sync KeyLearner - no timeout
   - File read operations not bounded

4. **`_find_available_model()` (line 211-249):**
   - 5s timeout on model list call ✓
   - Fallback chain with defaults ✓

**Missing:**
- NO outer timeout on `process()` call itself
- When called from async handler, blocks entire event loop
- No timeout wrapper in user_message_handler_v2.py around hostess.process()

### 4. EVENT LOOP DEADLOCK SCENARIOS

**Scenario A: Ollama Unresponsive**
```
1. user_message handler (async) calls hostess.process() [BLOCKS]
2. hostess.process() calls requests.post() [BLOCKS for 20s]
3. Ollama is slow/unresponsive
4. No response in 20s, timeout triggered
5. Empty string returned, parsing fails
6. Falls back to chain_call
7. BUT: Meanwhile, Socket.IO event loop is blocked for 20 seconds
8. Spinner shows thinking... thinking... thinking...
```

**Scenario B: Context Builder Hangs**
```
1. Line 298-303: hostess_context_builder.build_context() called
2. This is SYNC but calls history manager which might block
3. Event loop blocked again while building context
4. Then hostess.process() blocks again
5. Double blocking = infinite spinner
```

**Scenario C: Response Parsing Loop**
```
1. Ollama returns malformed JSON
2. _parse_tool_call() tries multiple regex patterns
3. All patterns fail
4. Returns None
5. Falls back to chain_call (safe exit)
6. BUT: If parsing itself hangs (complex regex on large text)?
   - No timeout on regex matching
```

### 5. ASYNCIO EVENT LOOP ISSUES (Lines 642-653)

**In `_execute_tool()` for save_api_key:**
```python
# Line 642-653: Creates or gets event loop
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

result = loop.run_until_complete(tool.execute(key=key, provider=provider))
```

**Problem:**
- Called from sync context (hostess.process())
- If called from existing async context, may conflict with running loop
- Could cause: "RuntimeError: This event loop is already running"
- No error handling for this specific case

### 6. TIMEOUT CHAIN ANALYSIS

| Component | Timeout | Status |
|-----------|---------|--------|
| Model check | 5s | ✓ Has timeout |
| Ollama generate | 20s | ✓ Has timeout |
| Context build | None | ❌ NO timeout |
| Parse tool call | None | ❌ NO timeout |
| Execute tool | None | ❌ NO timeout (except internal) |
| Process() wrapper | None | ❌ NO timeout (CRITICAL) |
| Async handler wrap | None | ❌ NO timeout |

### 7. SYMPTOM CORRELATION

**"Disk spinning" observation:**
- Likely Ollama GPU trying to load model (slow)
- Or Qdrant vector search in context builder (disk I/O)
- Spinner shows because response manager waiting for hostess decision
- No timeout fires at Socket.IO handler level

### 8. ROOT CAUSE SUMMARY

**Primary Issue:**
Synchronous blocking code (`hostess.process()`) called from async handler without timeout wrapper or thread pooling.

**Contributing Factors:**
1. No outer timeout on `process()` method
2. Rich context builder (line 298) also sync but potentially slow (Qdrant queries?)
3. Ollama HTTP call can block for 20s with no socket-level timeout
4. Event loop completely blocked while waiting
5. UI spinner keeps spinning indefinitely because no "timed out" message sent

**Why It Looks Like "Infinite Thinking":**
- UI spinner activated when agent_message with "Thinking..." sent
- No follow-up timeout message or error sent
- Socket.IO waits forever for function to complete
- Disk spinning = Ollama or Qdrant doing work

## CONCLUSION

The Hostess infinite thinking bug is caused by **synchronous blocking I/O in an async context without timeout protection**. When Ollama is slow or unresponsive, the entire async event loop freezes, and the UI spinner never gets the "done" signal.

**Exit Condition Missing:**
There is NO timeout wrapping the entire `hostess.process()` call at the handler level. The individual components have 20s timeouts, but if context building takes 10s + parsing takes 5s + execution takes 5s, total could exceed handler expectations.

# MARKER_90.1.2_END
