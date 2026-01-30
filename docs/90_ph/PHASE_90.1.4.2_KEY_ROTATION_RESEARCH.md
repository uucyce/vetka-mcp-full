# MARKER_90.1.4.2_START: Key Rotation Research

## Executive Summary

VETKA has a sophisticated smart key rotation system with 24h cooldown markers, but it has **subtle gaps in group chat scenarios**. The system works correctly in solo chat but fails to apply rotation logic consistently in multi-agent group scenarios.

---

## 1. WHERE IS 24H MARKER LOGIC?

### Location: `/src/utils/unified_key_manager.py`

The 24-hour cooldown logic is centralized in the `APIKeyRecord` dataclass:

```python
@dataclass
class APIKeyRecord:
    # Rate limit tracking
    rate_limited_at: Optional[datetime] = None
    failure_count: int = 0
    success_count: int = 0
    last_used: Optional[datetime] = None

    def is_available(self) -> bool:
        """Check if key is available (not in cooldown)."""
        if not self.active:
            return False
        if self.rate_limited_at:
            cooldown_end = self.rate_limited_at + RATE_LIMIT_COOLDOWN
            if datetime.now() < cooldown_end:
                return False
            # Cooldown expired, reset
            self.rate_limited_at = None
        return True

    def mark_rate_limited(self):
        """Mark key as rate-limited (starts 24h cooldown)."""
        self.rate_limited_at = datetime.now()
        self.failure_count += 1
```

**Key Definition:**
```python
# Cooldown duration for rate-limited keys (24 hours)
RATE_LIMIT_COOLDOWN = timedelta(hours=24)
```

### How It Works:

1. When a key fails (403 Forbidden, rate limit), `mark_rate_limited()` is called
2. Sets `rate_limited_at = datetime.now()`
3. `is_available()` checks if current time < `rate_limited_at + 24h`
4. If true, key is skipped; moves to next available key
5. After 24h, the marker is automatically reset

---

## 2. WHERE IS IT APPLIED?

### A. Provider Registry (provider_registry.py)

**XAI Provider - Explicit 24h Logic:**
```python
# Lines 677-706 in XaiProvider.call()
if response.status_code == 403:
    print(f"[XAI] ⚠️ 403 Forbidden - 24h timestamp limit, trying rotation...")
    from src.utils.unified_key_manager import get_key_manager, ProviderType
    key_manager = get_key_manager()  # Use singleton

    # Mark current key as rate-limited (24h cooldown)
    for record in key_manager.keys.get(ProviderType.XAI, []):
        if record.key == api_key:
            record.mark_rate_limited()
            print(f"[XAI] Key {record.mask()} marked as rate-limited (24h)")
            break

    # Try next key
    next_key = key_manager.get_active_key(ProviderType.XAI)
    if next_key and next_key != api_key:
        print(f"[XAI] 🔄 Retrying with next key...")
```

**Other Providers - Generic Fallback:**
```python
# Lines 856-883 in call_model_v2()
except ValueError as e:
    # API key not found - try OpenRouter as fallback
    if provider in (Provider.OPENAI, Provider.ANTHROPIC, Provider.GOOGLE, Provider.XAI):
        print(f"[REGISTRY] {provider.value} API key not found, trying OpenRouter fallback...")
```

### B. Orchestrator (orchestrator_with_elisya.py)

**Where Keys Are Injected:**
```python
# Line 1156 in _run_agent_with_elisya_async()
saved_env = self.key_service.inject_key_to_env(routing['provider'], api_key)
```

**Routing Decision:**
```python
# Lines 1113-1147
routing = self._get_routing_for_task(...)  # Returns provider + model
```

**Issue: No explicit error handling for 403 after injection!**

---

## 3. PROVIDER PRIORITY ORDER

### Current Priority (Enforced)

**Defined in `call_model_v2()` provider selection:**

```
1. Direct Provider (specified provider_enum)
   - OpenAI (GPT models)
   - Anthropic (Claude)
   - Google/Gemini
   - XAI (Grok)

2. Fallback Chain:
   a) If all keys rate-limited (24h cooldown) → return None
   b) If key not found (ValueError) → Try OpenRouter
   c) If XaiKeysExhausted (403 from x.ai) → Use OpenRouter with x-ai/model prefix

3. Last Resort: Ollama (local)
```

**Code Evidence:**
```python
# Lines 860-869 in provider_registry.py
except XaiKeysExhausted as e:
    print(f"[REGISTRY] XAI keys exhausted (403), using OpenRouter fallback...")
    openrouter_provider = registry.get(Provider.OPENROUTER)
    if openrouter_provider:
        openrouter_model = f"x-ai/{model}" if not model.startswith('x-ai/') else model
        result = await openrouter_provider.call(messages, openrouter_model, tools, **kwargs)
```

---

## 4. WHY DOES IT FAIL IN GROUP CHAT?

### The Problem: Orchestrator → Group Chat Handler Chain

```
orchestrator.call_agent()
  ↓
_run_agent_with_elisya_async()
  ↓
_call_llm_with_tools_loop()
  ↓
call_model_v2() [Provider Registry]
  ↓ (on 403 or key error)
OpenRouter fallback
```

**Issue 1: No 403 Handling in Orchestrator**

The orchestrator **never catches** the 403 response from XAI. It only happens inside `XaiProvider.call()`:

```python
# In orchestrator_with_elisya.py line 1191
llm_response = await self._call_llm_with_tools_loop(
    prompt=prompt,
    agent_type=agent_type,
    model=model_name,
    system_prompt=system_prompt,
    provider=provider_enum
)
# NO error handling here! If XAI returns 403, we don't retry rotation
```

**Issue 2: Group Chat Uses Manual Model Override**

In `group_message_handler.py` line 729:
```python
result = await orchestrator.call_agent(
    agent_type=agent_type,
    model_id=model_id,  # ← MANUAL OVERRIDE
    prompt=prompt,
    context={...}
)
```

When model_id is manually specified (e.g., "x-ai/grok-4"), the orchestrator sets:
```python
# Lines 2101-2106 in call_agent()
if model_id and model_id != 'auto':
    old_routing = self.model_routing.get(agent_type)
    self.model_routing[agent_type] = {
        'provider': 'manual',
        'model': model_id
    }
```

**This bypasses the intelligent routing!** The orchestrator can't fallback because it's forced to use the manual provider.

**Issue 3: No Retry Loop in Group Handler**

In `group_message_handler.py`, if an agent call fails, there's no retry logic:
```python
# Lines 728-741
try:
    result = await asyncio.wait_for(
        orchestrator.call_agent(...),
        timeout=120.0
    )
except asyncio.TimeoutError:
    print(f"[GROUP_ERROR] Timeout after 120s calling {agent_type}")
    result = {'status': 'error', 'error': 'Timeout after 120 seconds'}
# ← Only catches timeout, not 403 or key errors!
```

---

## 5. KEY ROTATION FLOW (ACTUAL vs INTENDED)

### What SHOULD Happen (Intended)

```
Group Chat Message
  ↓
Orchestrator.call_agent(model_id="x-ai/grok-4")
  ↓
_run_agent_with_elisya_async()
  ↓
XaiProvider.call()
  ↓
[First xai key] → 403 Forbidden
  ↓
mark_rate_limited() [24h marker set]
  ↓
get_active_key() → [Next xai key]
  ↓
[Second xai key] → Success! ✅
```

### What ACTUALLY Happens (Current Bug)

```
Group Chat Message
  ↓
Orchestrator.call_agent(model_id="x-ai/grok-4")
  ↓
_run_agent_with_elisya_async()
  ↓
XaiProvider.call()
  ↓
[First xai key] → 403 Forbidden
  ↓
mark_rate_limited() [24h marker set]
  ↓
get_active_key(XAI) → None (all keys in cooldown!)
  ↓
raise ValueError("x.ai API key not found")
  ↓
Caught in call_model_v2() fallback
  ↓
Try OpenRouter ✅ (works, but not ideal)
```

**The Real Problem:**
- In group chat, only 1 xai key might be configured
- First failure marks it as rate-limited
- No other xai keys available
- Falls back to OpenRouter
- **No retry loop to test rotation later**

---

## 6. WHAT'S MISSING

### Gap 1: Error Handling in Orchestrator

**File:** `src/orchestration/orchestrator_with_elisya.py`
**Line:** ~1191

**Missing:**
```python
try:
    llm_response = await self._call_llm_with_tools_loop(...)
except XaiKeysExhausted:  # ← NOT CAUGHT HERE!
    # Should retry with next provider or log rotation
    raise
```

### Gap 2: Intelligent Fallback in Group Chat

**File:** `src/api/handlers/group_message_handler.py`
**Line:** ~728-741

**Missing:**
```python
# No retry logic if key is rate-limited
# Should:
# 1. Detect 403 or key exhaustion
# 2. Automatically switch to OpenRouter
# 3. Retry the same request
```

### Gap 3: Multi-Key Configuration for Group Chat

**Current:** Group chats often have only 1 xai key
**Better:** Pre-populate multiple keys per provider

**File:** `data/config.json` structure
```json
{
  "api_keys": {
    "xai": [
      "xai-key-1",
      "xai-key-2",    // ← Multiple keys needed
      "xai-key-3"
    ]
  }
}
```

### Gap 4: Rotation Logging/Metrics

**Missing:** No visibility into when rotation happens
- When did key get marked rate-limited?
- How many rotations occurred?
- Which key is currently active?

---

## 7. ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│                    GROUP MESSAGE FLOW                       │
└─────────────────────────────────────────────────────────────┘

1. User sends message to group
   ↓
2. group_message_handler.handle_group_message()
   │
   ├─→ select_responding_agents() [Choose which agents]
   │
   └─→ For each agent:
       ├─→ orchestrator.call_agent(
       │   agent_type="Dev",
       │   model_id="x-ai/grok-4"  ← Manual override!
       │ )
       │
       ├─→ _run_agent_with_elisya_async()
       │   ├─→ Inject API key into env
       │   ├─→ _call_llm_with_tools_loop()
       │   │   ├─→ call_model_v2()  [Provider Registry]
       │   │   │   ├─→ XaiProvider.call()
       │   │   │   │   ├─→ First xai key → 403
       │   │   │   │   ├─→ mark_rate_limited()  [24h marker]
       │   │   │   │   ├─→ Try next key
       │   │   │   │   ├─→ All keys in cooldown
       │   │   │   │   └─→ raise XaiKeysExhausted()
       │   │   │   │
       │   │   │   └─→ Catch XaiKeysExhausted
       │   │   │       └─→ Try OpenRouter fallback ✅
       │   │   │
       │   │   └─→ Return response
       │   │
       │   └─→ Restore env variables
       │
       └─→ Broadcast response to group

┌─────────────────────────────────────────────────────────────┐
│         KEY ROTATION STATE MACHINE (Internal)               │
└─────────────────────────────────────────────────────────────┘

KEY STATE:
  ├─ active: true/false
  ├─ rate_limited_at: Optional[datetime]
  │   └─ Cooldown expires at: rate_limited_at + 24h
  ├─ failure_count: int
  ├─ success_count: int
  └─ last_used: datetime

TRANSITIONS:
  ├─ Success → success_count++, failure_count=0
  ├─ 403 Error → mark_rate_limited() [rate_limited_at=now()]
  ├─ Other Error → failure_count++
  └─ Cooldown Expired → rate_limited_at=None, available again

AVAILABILITY CHECK:
  if not active:
    return False
  if rate_limited_at:
    if now < rate_limited_at + 24h:
      return False  ← Still in cooldown
    else:
      rate_limited_at = None  ← Cooldown expired
      return True
  return True
```

---

## 8. RECOMMENDATIONS

### Priority 1: Add Error Handling in Orchestrator
```python
# orchestrator_with_elisya.py line ~1189-1198
try:
    llm_response = await self._call_llm_with_tools_loop(...)
except XaiKeysExhausted as e:
    print(f"[Orchestrator] XAI keys exhausted, logged for monitoring")
    # Optionally emit warning to UI
    raise
```

### Priority 2: Implement Fallback in Group Handler
```python
# group_message_handler.py line ~728
try:
    result = await orchestrator.call_agent(...)
except XaiKeysExhausted:
    # Log rotation event
    # Optionally retry with OpenRouter
    print(f"[GROUP] Key rotated to OpenRouter for {agent_id}")
```

### Priority 3: Populate Multiple Keys
- Add 2-3 xai/openai/anthropic keys to `config.json`
- Ensures rotation has alternative keys to try

### Priority 4: Add Monitoring
```python
def get_key_rotation_stats():
    """Return: {
        'xai': {'total_keys': 3, 'available': 2, 'rate_limited': 1},
        'openai': {...}
    }"""
```

---

## 9. FILES INVOLVED

| File | Purpose | Status |
|------|---------|--------|
| `src/utils/unified_key_manager.py` | Core 24h logic (APIKeyRecord) | ✅ Complete |
| `src/elisya/provider_registry.py` | XAI 403 → rotation logic | ✅ Complete |
| `src/orchestration/orchestrator_with_elisya.py` | Calls LLM, injects keys | ⚠️ Missing error handling |
| `src/api/handlers/group_message_handler.py` | Routes group messages | ⚠️ No retry on rotation |
| `src/orchestration/services/api_key_service.py` | Key injection wrapper | ✅ Works |
| `data/config.json` | Stores keys | ⚠️ Usually single keys |

---

## 10. CONCLUSION

**The 24h marker system is well-designed but has execution gaps in group chat:**

1. **What works:** XAI provider detects 403 and marks key as rate-limited (24h)
2. **What fails:** Group chat doesn't handle rotation gracefully
3. **Root cause:** Manual model override in group chat bypasses fallback logic
4. **Solution:** Add error handling + retry logic in group handler + multiple keys per provider

The system is **90% there** – it just needs better error propagation and fallback handling in the group chat layer.

# MARKER_90.1.4.2_END
