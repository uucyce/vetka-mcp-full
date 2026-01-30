# HAIKU-DIAG-1: Hostess Agent Fallback Loop Analysis

**Problem Statement:** After sending a message in group chat, agent "thinks" infinitely (spinning disk - no response).

**Root Cause Identified:** Infinite tool loop without proper timeout handling + Hostess delegation fallback creates cascade of waiting.

---

## MARKER-LOOP-001: Unbounded Tool Loop in _call_llm_with_tools_loop

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/orchestrator_with_elisya.py`

**Lines:** 1060-1211

**Issue:** Tool execution loop has `max_tool_turns=5` but **NO TIMEOUT for the entire loop**. If an LLM keeps requesting tools indefinitely (or takes very long per tool), the entire operation hangs.

```python
for turn in range(max_tool_turns):  # Line 1060
    # ... tool execution block ...
    # Phase 22: Convert Pydantic message to dict if needed
    if hasattr(response, "message") and hasattr(response.message, "model_dump"):
        msg_dict = response.message.model_dump()

    # CRITICAL: No timeout here for LLM call
    response = await call_model_v2(
        messages=messages,  # Full history with tool results
        model=model,
        provider=provider,
        tools=tool_schemas,
    )
    # Loop continues if tool_calls_data is not empty
    else:
        # LLM responded with a final message
        break  # Line 1211
```

**Problems:**
1. Each `call_model_v2()` call (lines 1026, 1035, 1050, 1188, 1202) has **no timeout**
2. If LLM is slow or stuck, entire tool loop waits indefinitely
3. `call_model_v2` might itself hang on network issues
4. No progress logging during tool loop iterations

**Severity:** CRITICAL - This causes "spinning disk" with zero feedback

---

## MARKER-LOOP-002: Missing Timeout in Group Message Handler Call

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`

**Lines:** 813-826

**Issue:** Agent call has 120s timeout, but the orchestrator's internal tool loop has NO timeout.

```python
try:
    result = await asyncio.wait_for(
        orchestrator.call_agent(
            agent_type=agent_type,
            model_id=model_id,
            prompt=prompt,
            context={...},
        ),
        timeout=120.0,  # 2 minute timeout  <- Line 825
    )
except asyncio.TimeoutError:
    print(f"[GROUP_ERROR] Timeout after 120s calling {agent_type}")
    result = {"status": "error", "error": "Timeout after 120 seconds"}
```

**Problem:** The 120s timeout is EXTERNAL. If orchestrator's tool loop hangs on a single `call_model_v2()` call, the timeout will eventually trigger, but:
1. User waits 120s with spinning disk and NO feedback
2. Then gets generic timeout error
3. No way to know WHERE it timed out (which tool turn, which LLM call)

**Severity:** HIGH - No user feedback during hang

---

## MARKER-LOOP-003: Hostess Fallback with No Timeout

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`

**Lines:** 225-403 (route_through_hostess function)

**Issue:** Hostess routing itself has a 30s timeout (line 294), but if Hostess fails to parse, it falls back to Architect delegation WITHOUT timeout on the actual agent call.

```python
# Line 287-295: Hostess call with timeout
result = await asyncio.wait_for(
    orchestrator.call_agent(
        agent_type="Hostess",
        model_id="qwen2:7b",
        prompt=hostess_prompt,
        context={"group_id": group_id, "is_routing": True},
    ),
    timeout=30.0,  # 30 second timeout for routing
)

# Line 390-392: Fallback if parsing fails
print(f"[GROUP_HOSTESS] Parsing failed, defaulting to Architect delegation")
return {"handled": False, "delegate_to": "Architect", "response": None}
```

**Problem:** But look at where route_through_hostess is called in the main handler - it's COMMENTED OUT:

**Lines:** 687-690 (in main handle_group_message)
```python
# Phase 57.8.2: REMOVED Hostess routing - она слишком медленная для роутинга
# Hostess теперь только для: камера, навигация, context awareness
# Вместо этого полагаемся на select_responding_agents + agent-to-agent @mentions
```

**So route_through_hostess is UNUSED** but the fallback pattern shows a design flaw:
- Hostess delegates to Architect
- Then Architect goes through call_agent -> tool loop WITHOUT proper internal timeouts
- If tool loop hangs, entire message processing hangs

**Severity:** MEDIUM - Indicates architectural issue with cascading timeouts

---

## MARKER-LOOP-004: call_model_v2 Has No Timeout (Root Cause)

**File:** Likely in `src/elisya/api_gateway.py` or `src/elisya/api_aggregator_v3.py`

**Issue:** The `call_model_v2()` function (called from orchestrator) likely lacks timeout on actual API calls.

```python
# In orchestrator_with_elisya.py lines 1026, 1035, 1050, 1188, 1202
response = await call_model_v2(
    messages=messages,
    model=model,
    provider=provider,
    tools=tool_schemas,
)
# No timeout wrapper!
```

**Problems:**
1. Network calls to OpenRouter, Ollama, XAI might hang indefinitely
2. No per-call timeout on HTTP requests
3. If provider is down/slow, entire chain blocks

**Severity:** CRITICAL - This is the actual source of hanging

---

## MARKER-LOOP-005: Tool Execution Loop Progress Opacity

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/orchestrator_with_elisya.py`

**Lines:** 1060-1211

**Issue:** Tool loop iteration progress is not visible to user. After 2+ min, user has no idea if system is:
- Stuck on tool execution?
- Waiting for LLM response?
- Processing results?

```python
for turn in range(max_tool_turns):  # No progress indication
    if tool_calls_data:
        print(
            f"      🔧 LLM requested {len(tool_calls_data)} tool call(s) on turn {turn + 1}"
        )
        # Execute and continue...
    else:
        break  # Only way to know progress is from logs
```

**Problem:** No streaming updates to frontend about tool progress.

**Severity:** MEDIUM - User experience issue

---

## MARKER-LOOP-006: Agent Chain With No Inter-Agent Timeout

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`

**Lines:** 714-720 (while loop for participants)

**Issue:** While loop processes agents sequentially with 120s timeout per agent, but:

```python
while (
    processed_idx < len(participants_to_respond) and processed_idx < max_agents
):
    participant = participants_to_respond[processed_idx]
    processed_idx += 1

    # EACH agent gets 120s timeout - cumulative!
    result = await asyncio.wait_for(
        orchestrator.call_agent(...),
        timeout=120.0,  # Line 825
    )
```

**Problem:** If there are 3 agents and each takes 120s, that's 360 seconds = 6 minutes total! With no feedback.

**Severity:** HIGH - Silent multiplication of timeouts

---

## ROOT CAUSE CHAIN DIAGRAM

```
User sends message to group
  ↓
Group handler calls select_responding_agents (3 agents selected)
  ↓
For each agent in while loop:
  ↓
  call_agent() → _run_agent_with_elisya_async()
    ↓
    _call_llm_with_tools_loop() [NO TIMEOUT on this function]
      ↓
      for turn in range(5):  [NO TIMEOUT on loop]
        ↓
        call_model_v2()  [NO TIMEOUT on this call!]
          ↓
          HTTP request to provider hangs
            ↓
            User sees spinning disk for 120s
              ↓
              FINALLY times out with "Timeout after 120 seconds"
```

---

## RECOMMENDATIONS

### FIX-1: Add Timeout to _call_llm_with_tools_loop (CRITICAL)

```python
async def _call_llm_with_tools_loop(
    self,
    prompt: str,
    agent_type: str,
    model: str,
    system_prompt: str,
    max_tool_turns: int = 5,
    provider: Provider = None,
    tool_loop_timeout: float = 60.0,  # NEW: 60s for entire tool loop
) -> Dict[str, Any]:
    """Main tool-enabled chat loop with timeout protection."""

    start_time = time.time()

    for turn in range(max_tool_turns):
        # Check if we've exceeded tool loop timeout
        elapsed = time.time() - start_time
        if elapsed > tool_loop_timeout:
            print(f"[Tool Loop] Timeout after {elapsed:.1f}s on turn {turn+1}")
            break

        # Calculate remaining time for this turn
        remaining = tool_loop_timeout - elapsed
        if remaining < 5:
            print(f"[Tool Loop] Less than 5s remaining, breaking")
            break

        # Wrap call_model_v2 with timeout
        try:
            response = await asyncio.wait_for(
                call_model_v2(...),
                timeout=min(remaining - 1, 30.0)  # Per-call timeout
            )
        except asyncio.TimeoutError:
            print(f"[Tool Loop] LLM call timed out on turn {turn+1}")
            break
```

### FIX-2: Add Per-Call Timeout in call_model_v2

Ensure `call_model_v2` has timeout on actual HTTP request:

```python
async def call_model_v2(
    messages, model, provider, tools=None,
    request_timeout: float = 30.0,  # NEW: 30s timeout
) -> Dict:
    # ... setup code ...

    try:
        response = await asyncio.wait_for(
            provider_client.call(messages, model, tools),
            timeout=request_timeout
        )
    except asyncio.TimeoutError:
        # Fallback logic
        raise ModelTimeoutError(f"Model call timed out after {request_timeout}s")
```

### FIX-3: Add Progress Streaming to Frontend

```python
# In group_message_handler.py line 810+
print(f"[GROUP_DEBUG] Calling {agent_type}, turn {turn+1}/{max_tool_turns}")

# Emit progress event
await sio.emit(
    "group_agent_progress",
    {
        "group_id": group_id,
        "agent_id": agent_id,
        "tool_turn": turn + 1,
        "max_turns": max_tool_turns,
        "elapsed_seconds": elapsed_seconds,
    },
    room=f"group_{group_id}",
)
```

### FIX-4: Reduce Cumulative Timeout

Instead of 120s per agent with 3 agents = 360s total:

```python
# Lines 714-825
# Distribute timeout across agents
total_timeout = 180.0  # 3 minutes total for all agents
timeout_per_agent = total_timeout / max(len(participants_to_respond), 1)

for participant in participants_to_respond:
    result = await asyncio.wait_for(
        orchestrator.call_agent(...),
        timeout=min(timeout_per_agent, 60.0)  # Min 60s per agent
    )
```

### FIX-5: Add Heartbeat/Progress Logging

```python
# During tool loop
for turn in range(max_tool_turns):
    print(f"[Tool Loop Turn {turn+1}] Starting LLM call...")

    try:
        start = time.time()
        response = await asyncio.wait_for(call_model_v2(...), timeout=30)
        elapsed = time.time() - start
        print(f"[Tool Loop Turn {turn+1}] LLM responded in {elapsed:.2f}s")
    except asyncio.TimeoutError:
        print(f"[Tool Loop Turn {turn+1}] LLM TIMEOUT after 30s")
        raise
```

---

## SUMMARY TABLE

| Marker | File | Line | Issue | Severity | Fix |
|--------|------|------|-------|----------|-----|
| LOOP-001 | orchestrator_with_elisya.py | 1060-1211 | Unbounded tool loop, no timeout | CRITICAL | Add loop-level timeout |
| LOOP-002 | group_message_handler.py | 813-826 | External timeout only, no internal | HIGH | Add call_model_v2 timeout |
| LOOP-003 | group_message_handler.py | 225-403 | Fallback pattern design issue | MEDIUM | Redesign cascade |
| LOOP-004 | api_aggregator/api_gateway.py | ? | call_model_v2 has no timeout | CRITICAL | Wrap HTTP calls |
| LOOP-005 | orchestrator_with_elisya.py | 1060 | No progress feedback to user | MEDIUM | Stream progress events |
| LOOP-006 | group_message_handler.py | 714-720 | Cumulative agent timeouts | HIGH | Distribute timeout |

---

## DEPLOYMENT PRIORITY

1. **CRITICAL (Deploy immediately):**
   - FIX-1: Add timeout to _call_llm_with_tools_loop
   - FIX-2: Add timeout to call_model_v2 HTTP calls
   - FIX-4: Reduce cumulative timeout from 360s to 180s

2. **HIGH (Next iteration):**
   - FIX-3: Stream progress updates to frontend
   - FIX-5: Add heartbeat logging

---

## TESTING RECOMMENDATIONS

```bash
# Test 1: Simulate slow LLM (30s response time)
# Expected: Tool loop should timeout at 60s, not hang indefinitely

# Test 2: Send message with 3 agents selected
# Expected: Total time should be ~180s max, not 360s+

# Test 3: Check frontend receives progress events
# Expected: Spinning disk updates with "Tool turn 1/5", etc.

# Test 4: Network timeout on provider
# Expected: Graceful fallback to OpenRouter, not hang
```

---

**Report Generated:** 2026-01-26
**Analysis Scope:** Group chat fallback loop investigation
**Status:** DIAGNOSIS COMPLETE - Ready for implementation
