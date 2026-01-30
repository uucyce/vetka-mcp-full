# HAIKU 3: Рекомендации по Унификации Архитектуры

**Date:** 2026-01-25
**Status:** STRATEGIC PLANNING
**Audience:** Architecture team, Phase 93+ planning

---

## 🎯 PROBLEM STATEMENT

VETKA имеет **ДВА несинхронизированных пути** для LLM вызовов:

1. **Solo Chat:** Прямые вызовы + agent.call_llm() (Legacy)
2. **Group Chat:** orchestrator.call_agent() → provider_registry (Modern)

**Последствия:**
- Solo chat НЕ получает XAI fallback
- Solo chat НЕ получает Elisya context fusion
- Solo chat НЕ получает CAM metrics
- Дублирование кода для key rotation
- Разные error handling подходы
- Сложность для maintenance

---

## ✅ CURRENT STATE (Working, but Sub-optimal)

### Solo Chat Architecture
```
User Input
  ↓
user_message_handler.py
  ├─ If model override:
  │  └─ Direct API call (ollama.chat or httpx.post)
  ├─ If @mention:
  │  └─ Direct API call (ollama.chat or requests.post)
  └─ Else agent chain:
     └─ agent.call_llm() (black box)

Problems:
  ❌ 3 different code paths
  ❌ No orchestrator involvement
  ❌ No Elisya context
  ❌ Manual key rotation (if at all)
  ❌ No XAI fallback
  ❌ agent.call_llm() internals hidden
  ❌ Streaming only via httpx (not all paths)
```

### Group Chat Architecture
```
User Input
  ↓
group_message_handler.py
  ↓
select_responding_agents()
  ↓
orchestrator.call_agent()
  ├─ ElisyaState building
  ├─ ElisyaMiddleware reframing
  ├─ provider_registry.call_model_v2()
  │  ├─ Provider detection
  │  ├─ API call
  │  └─ Error handling
  ├─ XAI fallback (if needed)
  ├─ CAM metrics collection
  └─ Return formatted result

Benefits:
  ✅ Single code path
  ✅ Full orchestrator integration
  ✅ Elisya context fusion
  ✅ Automatic key rotation
  ✅ XAI fallback
  ✅ Streaming support
  ✅ 120s timeout protection
  ✅ Chain context via previous_outputs
```

---

## 🚀 PROPOSED SOLUTION: UNIFY ON ORCHESTRATOR

### PHASE 93.1: Refactor Solo Chat Handler

**Goal:** Use orchestrator.call_agent() for ALL solo chat paths

**Changes Required:**

#### Step 1: Remove Direct API Calls

**Current (lines 237-754 in user_message_handler.py):**
```python
if requested_model:
    if is_local_ollama:
        ollama_response = await loop.run_in_executor(
            None,
            lambda: ollama.chat(model=requested_model, ...)
        )
```

**Proposed:**
```python
if requested_model:
    # Route through orchestrator
    result = await orchestrator.call_agent(
        agent_type="Direct",  # or "User" - new type
        model_id=requested_model,
        prompt=model_prompt,
        context={"node_path": node_path, "is_direct_call": True}
    )
    response_text = result.get("output", "")
```

**Benefits:**
- ✅ Uses provider_registry
- ✅ XAI fallback available
- ✅ Consistent with group chat
- ✅ Same streaming support

**Effort:** MEDIUM (need to handle streaming through orchestrator)

---

#### Step 2: Unify Agent Chain

**Current (lines 1685-1829):**
```python
for agent_name in agents_to_call:
    agent_instance = agents[agent_name]["instance"]
    response_text = await loop.run_in_executor(
        None,
        lambda: agent_instance.call_llm(prompt, max_tokens)
    )
```

**Proposed:**
```python
for agent_name in agents_to_call:
    # Use orchestrator instead of agent instance
    result = await orchestrator.call_agent(
        agent_type=agent_name,
        model_id=agents[agent_name]["model_id"],  # Get from config
        prompt=full_prompt,
        context={"node_path": node_path, "is_solo_chat": True}
    )
    response_text = result.get("output", "")
```

**Benefits:**
- ✅ Same CAM metrics as group
- ✅ Same key rotation
- ✅ Same XAI fallback
- ✅ agents[agent_name]["instance"] becomes unnecessary

**Effort:** SMALL (remove executor wrap, change call)

---

#### Step 3: Consolidate Hostess Routing

**Current:** Different implementations in solo vs group

**Proposed:** Single Hostess.call_agent() via orchestrator

```python
# Solo AND Group (identical code)
hostess_result = await orchestrator.call_agent(
    agent_type="Hostess",
    model_id="qwen2:7b",
    prompt=routing_prompt,
    context={"is_routing": True}
)
hostess_decision = parse_routing_decision(hostess_result)
```

---

### PHASE 93.2: Extend Orchestrator

**What orchestrator needs for solo chat:**

1. **"Direct" agent type** for model override calls
   - No special prompt formatting
   - Just pass model_id directly

2. **Solo chat context** handling
   ```python
   context = {
       "node_path": node_path,
       "is_solo_chat": True,
       "is_direct_call": False,
       "conversation_id": sid,
       "pinned_files": pinned_files
   }
   ```

3. **Streaming passthrough** (maybe)
   - orchestrator.call_agent_streaming()
   - Or token-level callback API

4. **Fallback agent mapping**
   ```python
   agent_type_map = {
       "PM": PM_system_prompt,
       "Dev": DEV_system_prompt,
       "QA": QA_system_prompt,
       "Hostess": HOSTESS_system_prompt,
       "Direct": "",  # No special prompt
   }
   ```

**Estimated Effort:** SMALL (mostly just pass through context)

---

## 📊 UNIFIED ARCHITECTURE (After Phases 93.1-93.2)

```
USER INPUT
  ↓
┌─────────────────────────────────────────┐
│  Socket Handler                         │
│  (user_message OR group_message)        │
│                                         │
│  Both call:                             │
│  orchestrator.call_agent(               │
│    agent_type="...",                    │
│    model_id="...",                      │
│    prompt="...",                        │
│    context={...}                        │
│  )                                      │
└─────────────────────────────────────────┘
  ↓
OrchestratorWithElisya
  ├─ Build ElisyaState
  ├─ Apply ElisyaMiddleware
  ├─ provider_registry.call_model_v2()
  ├─ Handle XAI fallback
  ├─ Collect CAM metrics
  └─ Return formatted result
  ↓
RESPONSE (consistent format)
  {status: "done", output: response_text}
```

**Advantages:**
- ✅ Single code path for ALL LLM calls
- ✅ All features available everywhere (XAI fallback, Elisya, CAM, etc.)
- ✅ Easier to test (one flow)
- ✅ Easier to debug (one flow)
- ✅ Consistent error handling
- ✅ Consistent timeout handling (120s)
- ✅ Future features benefit ALL chat types

---

## 🔄 MIGRATION PLAN

### Phase 93.1: Direct Model Calls → Orchestrator
- **Effort:** 2-3 days
- **Risk:** MEDIUM (changes core solo chat path)
- **Test:** All direct model scenarios
- **Rollback:** Keep old code, add feature flag

### Phase 93.2: Agent Chain → Orchestrator
- **Effort:** 1-2 days
- **Risk:** LOW (similar to group chat)
- **Test:** Agent chain scenarios
- **Rollback:** Revert agent call changes

### Phase 93.3: Consolidate Hostess
- **Effort:** 1 day
- **Risk:** LOW (both paths already work)
- **Test:** Hostess routing decisions
- **Rollback:** Revert to per-handler implementations

### Phase 93.4: Remove Legacy Code
- **Effort:** 0.5 day
- **Risk:** LOW (if phases 93.1-93.3 pass)
- **Clean up:**
  - Remove agent.call_llm() calls from user_message_handler.py
  - Remove direct ollama/httpx calls
  - Remove manual key rotation code
  - Mark api_aggregator_v3 as deprecated

### Timeline: 4-5 days total

---

## 🧪 TESTING STRATEGY

### Unit Tests
```python
def test_solo_direct_model_via_orchestrator():
    """Direct model call uses orchestrator"""
    result = orchestrator.call_agent(
        agent_type="Direct",
        model_id="qwen2:7b",
        prompt="test"
    )
    assert result["status"] == "done"
    assert len(result["output"]) > 0

def test_solo_agent_chain_via_orchestrator():
    """Agent chain uses orchestrator"""
    result = orchestrator.call_agent(
        agent_type="PM",
        model_id="qwen2:7b",
        prompt="test"
    )
    assert result["status"] == "done"

def test_xai_fallback_solo_and_group():
    """XAI fallback works in both solo and group"""
    # Mock XAI to exhaust keys
    # Call both paths
    # Verify fallback to OpenRouter
```

### Integration Tests
```python
# Replay actual conversation flows
def test_solo_chat_full_flow():
    # User sends model override
    # Receive response
    # Check socket events

def test_group_chat_full_flow():
    # Group sends message
    # Select agents
    # Receive all responses

def test_mixed_solo_group():
    # Both happening simultaneously
    # Different models
    # All work correctly
```

### Performance Tests
```python
# Ensure no regression
# Latency should be same or better
# Throughput should be same or better
# Memory usage should be same or better
```

---

## ⚠️ RISKS & MITIGATION

### Risk 1: Breaking Solo Chat During Migration
**Mitigation:**
- Feature flag: `UNIFIED_HANDLER` (default False)
- Parallel implementations for 1 release
- Gradual rollout (10% → 50% → 100%)

### Risk 2: Agent System Depends on agent.call_llm()
**Mitigation:**
- Check agent.py for external API surface
- If agent.call_llm() used elsewhere, must keep it
- Or refactor agents to work with orchestrator context

### Risk 3: Orchestrator Doesn't Handle All Edge Cases
**Mitigation:**
- Test all solo chat edge cases before migration
- Extend orchestrator if needed
- Keep api_aggregator_v3 as ultimate fallback

### Risk 4: Performance Impact
**Mitigation:**
- Profile before/after
- Orchestrator adds minimal overhead
- Provider registry is efficient

---

## 📈 BENEFITS AFTER UNIFICATION

### For Users
- ✅ More reliable solo chat (XAI fallback)
- ✅ Better error messages
- ✅ Consistent behavior solo vs group
- ✅ More features available in all chat types

### For Developers
- ✅ One code path to maintain
- ✅ Easier to add new features
- ✅ Easier to debug issues
- ✅ Better test coverage
- ✅ Less code duplication

### For Operations
- ✅ Easier to monitor (all calls same path)
- ✅ Easier to rate limit
- ✅ Easier to track usage
- ✅ Simpler key rotation logic

---

## 🎬 NEXT STEPS

1. **Review this proposal** with team
2. **Estimate effort** for each phase
3. **Plan Phase 93 sprint**
4. **Create detailed issue breakdown**
5. **Implement Phase 93.1** (direct model calls)
6. **Test thoroughly**
7. **Iterate on feedback**

---

## APPENDIX: Code Examples

### Example 1: Migrating Direct Model Call

**Before:**
```python
# user_message_handler.py:356
ollama_response = await loop.run_in_executor(
    None,
    lambda: ollama.chat(
        model=requested_model,
        messages=[{"role": "user", "content": model_prompt}],
        stream=False,
    ),
)
```

**After:**
```python
# user_message_handler.py:356
result = await orchestrator.call_agent(
    agent_type="Direct",
    model_id=requested_model,
    prompt=model_prompt,
    context={
        "node_path": node_path,
        "is_direct_call": True,
        "request_node_id": request_node_id,
    }
)
response_text = result.get("output", "")
```

---

### Example 2: Migrating Agent Chain

**Before:**
```python
# user_message_handler.py:1762-1767
response_text = await loop.run_in_executor(
    None,
    lambda: agent_instance.call_llm(
        prompt=full_prompt, max_tokens=max_tokens
    ),
)
```

**After:**
```python
# user_message_handler.py:1762-1767
result = await orchestrator.call_agent(
    agent_type=agent_name,
    model_id=agent_config.get("model_id", "qwen2:7b"),
    prompt=full_prompt,
    context={
        "node_path": node_path,
        "is_solo_chat": True,
        "is_chain": True,
        "previous_outputs": previous_outputs,
    }
)
response_text = result.get("output", "")
```

---

### Example 3: Consolidated Hostess Routing

**Before (Solo):**
```python
# user_message_handler.py:1161
hostess = get_hostess()
hostess_response = hostess.call_llm(routing_prompt)
```

**Before (Group):**
```python
# group_message_handler.py:285
result = await orchestrator.call_agent(
    agent_type="Hostess",
    model_id="qwen2:7b",
    prompt=routing_prompt,
    context={"group_id": group_id, "is_routing": True}
)
```

**After (Both):**
```python
# unified code (same for both)
result = await orchestrator.call_agent(
    agent_type="Hostess",
    model_id="qwen2:7b",
    prompt=routing_prompt,
    context={"is_routing": True}
)
```

---

**Document Version:** 1.0
**Last Updated:** 2026-01-25
**Status:** READY FOR REVIEW
