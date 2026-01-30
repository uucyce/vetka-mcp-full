# VETKA Key Rotation Fixes - Grok Analysis
# Based on investigation of Phase 90.* docs and code

## 🐛 Bug 1: Reply Routing Variable Bug
**File:** src/services/group_chat_manager.py
**Lines:** ~198-211 in select_responding_agents()

**Problem:**
```python
# BROKEN - agent_id_normalized not defined
if agent_id_normalized == reply_to_normalized:  # ❌ agent_id_normalized doesn't exist
```

**Fix:**
```python
# FIXED - Define variable before comparison
for pid, p in participants.items():
    agent_id_normalized = p.get('agent_id', '').lower().lstrip('@')  # ✅ Add this line
    if agent_id_normalized == reply_to_normalized:
        if p.get('role') != 'observer':
            participants_to_respond.append(p)
```

## 🐛 Bug 2: Manual Override Bypass
**File:** src/api/handlers/group_message_handler.py
**Lines:** ~729 before orchestrator.call_agent()

**Problem:**
```python
# BROKEN - GPT models go to OpenAI instead of OpenRouter
result = await orchestrator.call_agent(
    model_id=model_id,  # "gpt-5.2-chat" → Detected as Provider.OPENAI ❌
    ...
)
```

**Fix:**
```python
# FIXED - Force OpenRouter prefix for GPT models
if "gpt" in model_id.lower():  # ✅ Add this check
    model_id = f"openrouter/{model_id}"  # "openrouter/gpt-5.2-chat"

result = await orchestrator.call_agent(
    model_id=model_id,  # Now goes to OpenRouter ✅
    ...
)
```

## 🐛 Bug 3: Incomplete Exception Handling
**File:** src/orchestration/orchestrator_with_elisya.py
**Lines:** ~976-995 in _call_llm_with_tools_loop()

**Problem:**
```python
# BROKEN - Only catches XaiKeysExhausted
try:
    response = await call_model_v2(...)
except XaiKeysExhausted:  # ❌ Only XAI handled
    # fallback logic
```

**Fix:**
```python
# FIXED - Catch HTTP errors too
from httpx import HTTPStatusError

try:
    response = await call_model_v2(...)
except XaiKeysExhausted:
    # Existing XAI handling ✅
    pass
except HTTPStatusError as http_err:
    if http_err.response.status_code in [404, 429]:  # ✅ Add this
        # Mark key as rate limited and retry
        from src.utils.unified_key_manager import get_key_manager
        key_manager = get_key_manager()
        # Mark current key rate limited
        key_manager.mark_rate_limited(current_provider, current_key)
        # Fallback to OpenRouter
        return await call_model_v2(..., provider=Provider.OPENROUTER)
    else:
        raise
```

## 🧪 Testing Plan
1. **Reply test:** @mention @Researcher in group chat reply
2. **Model test:** Use GPT model in group (should go to OpenRouter)
3. **Rate limit test:** Simulate 429/404 (should rotate and fallback)

## 📋 Implementation Checklist
- [ ] Fix reply routing variable in group_chat_manager.py
- [ ] Add OpenRouter prefix for GPT models in group_message_handler.py
- [ ] Expand exception handling in orchestrator_with_elisya.py
- [ ] Add tests for all three scenarios
- [ ] Test with existing key rotation system