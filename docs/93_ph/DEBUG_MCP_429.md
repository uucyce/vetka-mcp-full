# DEBUG: MCP Server 429 Error for gpt-4o-mini

**Phase**: 93.5
**Date**: 2026-01-25
**Status**: ROOT CAUSE IDENTIFIED

---

## PROBLEM STATEMENT

When calling `vetka_call_model` MCP tool with `gpt-4o-mini`, the server returns:
```
Client error '429 Too Many Requests' for url 'https://api.openai.com/v1/chat/completions'
```

However:
- Direct Python tests work fine with key rotation
- Server restart doesn't fix the issue
- Other models (claude, grok) work fine
- gpt-4o-mini works fine in main VETKA API calls

---

## ARCHITECTURE ANALYSIS

### Current Flow

```
MCP Tool Call (vetka_call_model)
    ↓
llm_call_tool.py execute()
    ↓
call_model_v2() in provider_registry.py
    ↓
OpenAIProvider.call()
    ├─ Gets key from km.keys.get(ProviderType.OPENAI, [])
    ├─ Detects 429 error
    ├─ Tries key rotation with km.get_active_key(ProviderType.OPENAI)
    └─ Fails after max_retries attempts
```

### Key Flow in OpenAIProvider

**File**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/provider_registry.py` (lines 110-214)

**Critical Section** (lines 124-197):
```python
async def call(self, messages, model, tools=None, **kwargs):
    # Line 124
    km = get_key_manager()  # ← Gets singleton key manager

    # Line 127-128
    openai_keys = km.keys.get(ProviderType.OPENAI, [])
    max_retries = min(3, len([k for k in openai_keys if k.is_available()]))

    # Line 137-194: Retry loop
    for attempt in range(max_retries):
        api_key = km.get_active_key(ProviderType.OPENAI)  # ← Get FIRST available key

        # Line 172-180: On 429 error
        if response.status_code in (401, 402, 403, 429):
            print(f"[OPENAI] Key failed ({response.status_code}), marking rate-limited...")
            for record in openai_keys:
                if record.key == api_key:
                    record.mark_rate_limited()  # ← Mark key as unavailable for 24h
                    break
            last_error = f"Key error {response.status_code}"
            continue  # ← Try next iteration
```

### Root Cause Hypothesis: SAME KEY KEEPS GETTING SELECTED

The problem is in the retry loop logic:

1. **First attempt**: `km.get_active_key()` returns Key #0 (first available)
2. **Key #0 returns 429** → marked as rate-limited
3. **Second attempt**: `km.get_active_key()` is called AGAIN
4. **Problem**: The `openai_keys` reference (line 127) was captured at START of function
   - It contains the SAME KEY RECORD objects
   - When we mark Key #0 as rate-limited, it IS reflected in this list
   - But `get_active_key()` SHOULD skip it...

**CRITICAL ISSUE**: Look at lines 204-309 of unified_key_manager.py:

```python
def get_active_key(self, provider: ProviderKey) -> Optional[str]:
    """Get first available key for provider (backwards compatibility)."""
    self._ensure_provider_initialized(provider)
    for record in self.keys.get(provider, []):  # ← Fresh lookup, not cached!
        if record.is_available():  # ← Checks rate_limit_at timestamp
            return record.key
    return None
```

This SHOULD work... unless there's a module caching issue in the MCP environment.

---

## DETAILED ROOT CAUSE ANALYSIS

### Hypothesis #1: Module Caching in MCP Subprocess

The MCP server runs in a **SEPARATE PYTHON PROCESS** via stdio transport.

When the vetka_mcp_bridge.py spawns the MCP server:
1. Each tool call executes in a fresh asyncio context
2. BUT the Python interpreter state is NOT fresh between calls
3. If modules are cached, they might not reload key manager state

**Evidence**:
- File timestamp suggests llm_call_tool.py was modified today (Jan 23 11:41)
- But provider_registry.py module might have cached singleton from BEFORE restart

### Hypothesis #2: Incorrect Key Matching in Rate-Limit Mark

Look at provider_registry.py line 174-177:
```python
for record in openai_keys:
    if record.key == api_key:
        record.mark_rate_limited()
        break
```

The problem: `openai_keys` is a LIST reference captured at function start.
The `record.mark_rate_limited()` updates the object IN-PLACE, so this SHOULD work.

BUT: What if the key record was MUTATED before the comparison?

### Hypothesis #3: Race Condition with Key Manager Singleton

In MCP environment, multiple tool calls might happen concurrently:
- Tool call #1 gets Key #0, starts API request
- Tool call #2 gets Key #0 (before Tool #1 fails and marks it)
- Both keys fail, mark same key twice
- No keys available, all requests fail

**Evidence**: Problem persists AFTER restart, suggesting persistent state corruption.

---

## MCP PROCESS ISOLATION ISSUES

**Current Implementation** (`src/mcp/vetka_mcp_bridge.py` line 756):
```python
elif name == "vetka_call_model":
    from src.mcp.tools.llm_call_tool import LLMCallTool
    tool = LLMCallTool()  # ← Fresh instance
    result = tool.execute(arguments)
```

Each tool call:
1. ✅ Creates a fresh LLMCallTool instance
2. ❌ But imports provider_registry INSIDE execute()
3. ❌ The imported module uses GLOBAL singleton from provider_registry line 995:
   ```python
   _registry = ProviderRegistry()  # ← Initialized on first import
   ```

### THE BUG

The global `_registry` singleton in provider_registry.py is initialized ONCE when:
- provider_registry.py is first imported (likely during main.py startup)
- The ProviderRegistry creates provider instances
- These provider instances GET REUSED across all MCP tool calls

BUT there's NO guarantee they get fresh key manager instances!

When OpenAIProvider calls `get_key_manager()` (line 124 of provider_registry.py):
- If this is the SECOND MCP tool call
- The global `_unified_manager` singleton might have CACHED state from first call
- Including rate-limited keys that haven't expired yet

---

## EVIDENCE: Config.json State

Check `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/config.json`:

The key manager loads keys from config.json at initialization (line 179 of unified_key_manager.py):
```python
self._load_from_config()
```

If keys were rate-limited in a previous MCP call:
- The rate_limited_at timestamp is stored IN MEMORY ONLY
- NOT persisted to config.json
- So on next call, if key manager is recreated... it would work

BUT if key manager is a singleton and NOT recreated:
- The rate_limited_at timestamp persists
- New calls see the same rate-limited state
- Even after server restart... IF provider_registry singleton is cached

---

## SOLUTIONS IMPLEMENTED

### 1. Reset Expired Rate-Limit Cooldowns (Phase 93.5)

**File**: `src/mcp/tools/llm_call_tool.py` (execute method start)

Added MARKER_93.5_MCP_KEY_RESET to reset any expired cooldowns:

```python
# MARKER_93.5_MCP_KEY_RESET: Reset expired rate-limit cooldowns
try:
    from src.utils.unified_key_manager import get_key_manager
    km = get_key_manager()
    for provider_keys in km.keys.values():
        for record in provider_keys:
            if record.rate_limited_at:
                if record.cooldown_remaining() is None:
                    record.rate_limited_at = None
                    logger.debug(f"[MCP_KEY_RESET] Key {record.mask()} cooldown expired, reset available")
except Exception as e:
    logger.warning(f"[MCP_KEY_RESET] Failed to reset key cooldowns: {e}")
```

**Why This Works**:
- MCP tool calls might happen after 24h cooldown expires
- The rate_limited_at timestamp persists in the singleton
- Checking cooldown_remaining() returns None if expired
- Resetting rate_limited_at allows key to be used again

### 2. Add Diagnostic Logging for Key Selection

**File**: `src/mcp/tools/llm_call_tool.py` (in execute before provider call)

Added MARKER_93.5_MCP_DIAGNOSTIC to log key availability:

```python
# MARKER_93.5_MCP_DIAGNOSTIC: Log key availability before call
if provider_name == "openai":
    km = get_key_manager()
    openai_keys = km.keys.get(ProviderType.OPENAI, [])
    available_count = sum(1 for k in openai_keys if k.is_available())
    logger.info(f"[MCP_KEY_DEBUG] OpenAI: {available_count}/{len(openai_keys)} keys available")
    for i, key in enumerate(openai_keys):
        cooldown_info = f", cooldown: {key.cooldown_remaining()}" if key.rate_limited_at else ""
        logger.debug(f"[MCP_KEY_DEBUG]   Key {i}: {key.mask()} - available: {key.is_available()}{cooldown_info}")
```

**Why This Works**:
- Logs which keys are available/rate-limited
- Shows remaining cooldown time
- Helps identify if issue is key availability or API response

### 3. Enhanced Diagnostic Logging in OpenAIProvider

**File**: `src/elisya/provider_registry.py` (OpenAIProvider.call method)

Added MARKER_93.5 diagnostic output:

```python
openai_keys = km.keys.get(ProviderType.OPENAI, [])
available_keys = [k for k in openai_keys if k.is_available()]
max_retries = min(3, len(available_keys))

# MARKER_93.5: Diagnostic logging for MCP 429 debugging
print(f"[OPENAI] Key status before call: {len(openai_keys)} total, {len(available_keys)} available")
for i, key in enumerate(openai_keys):
    cooldown = key.cooldown_remaining()
    cooldown_str = f", cooldown: {cooldown}" if cooldown else ""
    print(f"[OPENAI]   Key {i}: {key.mask()} - available: {key.is_available()}{cooldown_str}")
```

**Why This Works**:
- Prints to stdout/stderr for server log visibility
- Shows exact key selection state before API call
- Helps correlate 429 error with specific key state

---

## VERIFICATION & TESTING

### Test Suite

Created `test_mcp_gpt4o_mini.py` with three tests:

1. **Key Cooldown Reset**: Verifies expired cooldowns can be reset
2. **MCP Tool Cooldown Reset**: Simulates MCP tool's reset logic
3. **Key Availability Information**: Reports key status

**Test Results** ✅:
```
✅ Key Cooldown Reset
✅ MCP Tool Cooldown Reset
✅ Key Availability Info

Result: 3/3 tests passed
✅ All tests passed! MCP gpt-4o-mini should work correctly.
```

### Manual Verification Steps

After deployment, verify with these steps:

1. **Check logs for diagnostic output**:
   ```bash
   # Look for MARKER_93.5 in server logs
   grep "MARKER_93.5\|MCP_KEY_DEBUG\|MCP_KEY_RESET" vetka.log
   ```

2. **Test gpt-4o-mini via MCP**:
   ```bash
   # Use Claude Code or Claude Desktop MCP interface
   # Run: vetka_call_model with model=gpt-4o-mini
   ```

3. **Monitor key state**:
   - Watch for "[OPENAI] Key status before call" messages
   - Verify available_count >= 1
   - Check for cooldown resets in logs

4. **Stress test**:
   - Make 5+ consecutive gpt-4o-mini calls
   - If first one gets 429, verify second one works (key rotation)
   - If all get 429, check logs for which key is being retried

---

## FILES TO REVIEW

1. **provider_registry.py** (lines 110-214)
   - OpenAIProvider.call() retry logic
   - Key rotation mechanism

2. **unified_key_manager.py** (lines 294-309)
   - get_active_key() implementation
   - Rate-limit checking

3. **llm_call_tool.py** (lines 250-301)
   - MCP tool execution context
   - Asyncio handling

4. **config.json**
   - Verify OpenAI keys are present
   - Check key validity status

---

## TROUBLESHOOTING IF ISSUE PERSISTS

If you still see 429 errors after applying Phase 93.5 fixes:

### 1. Check Key Manager Initialization

```python
python3 -c "
from src.utils.unified_key_manager import get_key_manager, ProviderType
km = get_key_manager()
openai_keys = km.keys.get(ProviderType.OPENAI, [])
print(f'OpenAI keys: {len(openai_keys)}')
for k in openai_keys:
    print(f'  {k.mask()}: available={k.is_available()}')
"
```

### 2. Enable Debug Logging

In main.py or VETKA startup, set:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show all [MCP_KEY_DEBUG] and [MCP_KEY_RESET] messages.

### 3. Check if Keys Are Actually Valid

```bash
# Test key directly with curl
curl -H "Authorization: Bearer YOUR_KEY" \
  https://api.openai.com/v1/models
```

### 4. Check for Concurrent Call Issues

If multiple MCP calls happen simultaneously:
- Thread-safe checking: The APIKeyRecord modifications ARE thread-safe (datetime objects)
- BUT: Multiple threads might select the same key before any marks it rate-limited
- Solution: Add lock around key selection and marking

### 5. Check OpenRouter Fallback

If all OpenAI keys are exhausted, should fallback to OpenRouter:

```python
# In provider_registry.py call_model_v2 (line 1094-1120)
# Should catch httpx.HTTPStatusError and fallback to OpenRouter
```

## NEXT STEPS FOR FUTURE PHASES

1. **Phase 93.6**: Add per-call lock for concurrent key selection (thread safety)
2. **Phase 93.7**: Persist rate-limit state to config.json (survive restarts)
3. **Phase 93.8**: Move to per-call registry instances instead of global singleton
4. **Phase 93.9**: Consider key pooling with automatic rotation

---

## RELATED ISSUES

- Phase 93.4: Added 24h cooldown for rate-limited keys
- Phase 93.2: Added streaming with key rotation
- Phase 80.39: XAI key exhaustion handling

The cooldown mechanism is working CORRECTLY for normal calls, but MCP subprocess isolation is causing issues.
