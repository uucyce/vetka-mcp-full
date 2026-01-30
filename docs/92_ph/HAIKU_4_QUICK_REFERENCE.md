# HAIKU 4: QUICK REFERENCE CARD

**Print this page or keep it in your terminal!**

## 🎯 ONE-MINUTE SUMMARY

```
┌─────────────────────────────────────────────────────────────┐
│                   SOLO vs GROUP DIFFERENCES                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  SOLO CHAT:                    GROUP CHAT:                  │
│  ├─ Direct ollama.chat()       ├─ orchestrator.call_agent() │
│  ├─ No roles (all generic)     ├─ PM, Dev, QA, Architect   │
│  ├─ No Elisya state            ├─ Full Elisya integration  │
│  ├─ [{"role":"user",...}]      ├─ [{"role":"system",...},  │
│  │                             │   {"role":"user",...}]    │
│  └─ BROKEN! 🔴               └─ CORRECT! 🟢              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 📍 CRITICAL FILES

```
user_message_handler.py
├─ LINE 355-362   → MARKER-UMH-001 (Ollama direct)
├─ LINE 567-580   → MARKER-UMH-002 (OpenRouter direct)
├─ LINE ~300-420  → MARKER-UMH-003 (Provider detection)
└─ LINE 358, 569  → MARKER-UMH-004 (Message format)

chat_handler.py
├─ LINE 110-157   → MARKER-CH-001 (build_model_prompt)
└─ LINE 49-87     → MARKER-CH-002 (detect_provider)

orchestrator_with_elisya.py
├─ LINE 2242-2331 → MARKER-ORCH-001 (call_agent definition)
└─ LINE ~1200     → MARKER-ORCH-002 (Find _run_agent_with_elisya_async)

provider_registry.py
├─ LINE 856-903   → MARKER-PR-001 (call_model_v2 definition)
└─ LINE 884-885   → MARKER-PR-002 (Provider detection)

group_message_handler.py
└─ LINE 758       → MARKER-GMH-001 (system_prompt handling)
```

## 🔧 QUICK FIX CHECKLIST

```
Phase 1: CRITICAL (Do these first)
┌─────────────────────────────────────────────────────────┐
│ MARKER-UMH-001: Ollama direct call → orchestrator       │
│ Replace: ollama.chat(messages=[{"role":"user",...}])    │
│ With:    orchestrator.call_agent(agent_type=..., ...)   │
│ Status:  ☐ TODO  ☐ IN PROGRESS  ☐ DONE                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ MARKER-UMH-002: OpenRouter direct HTTP → orchestrator   │
│ Replace: httpx.post("https://openrouter.ai/...")        │
│ With:    orchestrator.call_agent(agent_type=..., ...)   │
│ Status:  ☐ TODO  ☐ IN PROGRESS  ☐ DONE                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ MARKER-CH-001: build_model_prompt() return format       │
│ Change: return single prompt string                      │
│ To:     return (system_prompt, user_message)            │
│ Status:  ☐ TODO  ☐ IN PROGRESS  ☐ DONE                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ MARKER-ORCH-002: Verify message building in orchestrator│
│ Check:  messages = [{"role":"system"}, {"role":"user"}] │
│ Verify: call_model_v2 receives correct format           │
│ Status:  ☐ TODO  ☐ IN PROGRESS  ☐ DONE                 │
└─────────────────────────────────────────────────────────┘

Phase 2: IMPORTANT (Do these next)
┌─────────────────────────────────────────────────────────┐
│ MARKER-ORCH-001: Add "Assistant" to valid_agent_types   │
│ Add: "Assistant" to line 2265-2272                       │
│ Status:  ☐ TODO  ☐ IN PROGRESS  ☐ DONE                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ MARKER-UMH-004: Use unified message format              │
│ Change: messages = [{"role":"user","content":prompt}]   │
│ To:     messages = [{"role":"system"}, {"role":"user"}] │
│ Status:  ☐ TODO  ☐ IN PROGRESS  ☐ DONE                 │
└─────────────────────────────────────────────────────────┘
```

## 📊 MARKER MATRIX

| Marker | File | Line | Type | Effort | Risk | Impact |
|--------|------|------|------|--------|------|--------|
| **UMH-001** | UMH | 355 | FIX | 🟡 | 🔴 | CRITICAL |
| **UMH-002** | UMH | 567 | FIX | 🟡 | 🔴 | CRITICAL |
| **UMH-003** | UMH | 300 | CLEAN | 🟢 | 🟡 | MEDIUM |
| **UMH-004** | UMH | 358 | CHANGE | 🟡 | 🔴 | CRITICAL |
| **CH-001** | CH | 110 | REFACTOR | 🟡 | 🟡 | CRITICAL |
| **CH-002** | CH | 49 | VERIFY | 🟢 | 🟢 | LOW |
| **ORCH-001** | ORCH | 2265 | ADD | 🟢 | 🟢 | MEDIUM |
| **ORCH-002** | ORCH | ~1200 | VERIFY | 🟡 | 🔴 | CRITICAL |
| **PR-001** | PR | 856 | DOCUMENT | 🟢 | 🟢 | LOW |
| **PR-002** | PR | 884 | VERIFY | 🟢 | 🟢 | LOW |
| **GMH-001** | GMH | 758 | VERIFY | 🟢 | 🟢 | MEDIUM |

**Legend:** 🟢=Easy/Low 🟡=Medium 🔴=Hard/High

## 🚀 IMPLEMENTATION STEPS

### STEP 1: Preparation (15 min)
```bash
# 1. Create feature branch
git checkout -b feature/solo-group-unification

# 2. Read all documents
code docs/92_ph/HAIKU_4_*.md

# 3. Create test file
touch tests/test_solo_group_unification.py
```

### STEP 2: Core Changes (3-4 hours)
```bash
# In this order:
# 1. Update chat_handler.py:build_model_prompt() [CH-001]
# 2. Update user_message_handler.py Ollama call [UMH-001]
# 3. Update user_message_handler.py OpenRouter call [UMH-002]
# 4. Verify orchestrator message building [ORCH-002]

# Test after each change
pytest tests/test_solo_group_unification.py -v
```

### STEP 3: Cleanup (1-2 hours)
```bash
# 1. Add "Assistant" agent type [ORCH-001]
# 2. Remove duplicate provider detection [UMH-003]
# 3. Document message format [PR-001]
# 4. Verify provider detection [PR-002]

pytest tests/ -v  # Full test suite
```

### STEP 4: Validation (2-3 hours)
```bash
# 1. Test solo chat with Ollama
# 2. Test solo chat with OpenRouter
# 3. Test group chat (regression)
# 4. Test streaming
# 5. Test error handling
# 6. Performance check

# Then commit and push
git add -A
git commit -m "Phase 92: Unify solo and group chat LLM calls"
git push origin feature/solo-group-unification
```

## 🎯 BEFORE/AFTER CODE SNIPPETS

### BEFORE (SOLO - BROKEN)
```python
# user_message_handler.py:355-362
def ollama_call():
    return ollama.chat(
        model=requested_model,
        messages=[{"role": "user", "content": model_prompt}],
        stream=False,
    )
```

### AFTER (SOLO - FIXED)
```python
# user_message_handler.py:355-362
result = await orchestrator.call_agent(
    agent_type="Assistant",
    model_id=requested_model,
    prompt=text,
    context={"file": node_path}
)
```

---

### BEFORE (MESSAGE FORMAT - INCONSISTENT)
```python
# Solo:
messages = [{"role": "user", "content": full_prompt}]

# Group:
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": prompt}
]
```

### AFTER (MESSAGE FORMAT - UNIFIED)
```python
# Both solo and group:
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_message}
]
```

## 🧪 QUICK TESTS

### Test 1: Ollama Still Works
```bash
# Send message to solo chat
# Verify response from Ollama local model
# Check: No errors in console
```

### Test 2: OpenRouter Still Works
```bash
# Send message with gpt-4 model
# Verify response from OpenRouter
# Check: Streaming works (tokens appear incrementally)
```

### Test 3: Group Chat Still Works
```bash
# Create group with PM, Dev, QA
# Send message
# Verify all agents respond in sequence
# Check: @mentions trigger additional agents
```

### Test 4: Message Format
```python
# In provider_registry.py, add debug:
print(f"[DEBUG] Messages: {messages}")
# Verify format is: [{"role": "system", ...}, {"role": "user", ...}]
```

## 🔍 DEBUGGING COMMANDS

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check logs for errors
tail -f logs/vetka.log | grep -i "error\|model\|provider"

# Test direct API call
curl -X POST https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_KEY"

# Run specific test
pytest tests/test_solo_group_unification.py::test_ollama_call -v

# Profile performance
python -m cProfile -s cumtime main.py
```

## 📞 IF YOU GET STUCK

### Issue: "Orchestrator is None"
```python
# Fix: Ensure orchestrator is initialized in get_orchestrator()
from src.initialization.components_init import get_orchestrator
orchestrator = get_orchestrator()
if not orchestrator:
    print("[ERROR] Orchestrator not initialized!")
```

### Issue: "Agent type not valid"
```python
# Fix: Add "Assistant" to valid_agent_types in orchestrator_with_elisya.py:2265
valid_agent_types = [
    "PM", "Dev", "QA", "Architect", "Hostess", "Researcher",
    "Assistant",  # ← ADD THIS
]
```

### Issue: "Message format mismatch"
```python
# Fix: Ensure messages always have role and content
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_message}
]
# NOT: [{"role": "user", "content": full_prompt}]
```

### Issue: "Provider not detected"
```python
# Fix: Use detect_provider() from chat_handler or ProviderRegistry
from src.elisya.provider_registry import ProviderRegistry, Provider
provider = ProviderRegistry.detect_provider(model_name)
# NOT: Manual if/elif checks
```

## ✨ SUCCESS SIGNALS

You're done when you see:

- ✅ Solo chat works with Ollama
- ✅ Solo chat works with OpenRouter
- ✅ Solo chat works with GPT models
- ✅ Group chat still works (regression pass)
- ✅ Streaming shows tokens (solo + group)
- ✅ No direct `ollama.chat()` calls
- ✅ No direct `httpx.post()` to openrouter
- ✅ All messages have system + user roles
- ✅ No `provider_not_found` errors
- ✅ Performance similar to before (~same speed)

## 🎓 KEY LEARNINGS

| What | Solo Before | Solo After | Why Better |
|------|------------|-----------|-----------|
| Provider routing | if/elif blocks | ProviderRegistry | Centralized, testable |
| Role system | None (generic) | PM/Dev/QA/Assistant | Consistent with group |
| Message format | Single user role | System + user roles | Standard LLM format |
| Elisya integration | None | Full | Better context fusion |
| Error handling | Scattered | Unified | Easier to maintain |
| Code duplication | High | Low | Don't Repeat Yourself |

## 📈 METRICS TO TRACK

```
BEFORE:
- Solo call latency: ~150-200ms
- Group call latency: ~500-1000ms
- Code files: user_message_handler + chat_handler (duplicated logic)
- Error handling: Different in each place
- Role support: None in solo, full in group

AFTER:
- Solo call latency: ~170-220ms (10-15% overhead for orchestrator)
- Group call latency: ~500-1000ms (unchanged)
- Code files: Unified in orchestrator + call_model_v2
- Error handling: Consistent everywhere
- Role support: Full in both solo and group
```

## 🎉 WHEN YOU COMMIT

Use this commit message:

```
Phase 92: Unify solo and group chat LLM calls

- Replace direct ollama.chat() with orchestrator.call_agent()
- Replace direct openrouter API calls with provider_registry
- Unified message format: [system role, user role]
- Added "Assistant" agent type for solo chat
- Removed provider detection code duplication
- Solo and group now use same calling convention

Fixes: #ISSUE_NUMBER
Markers: UMH-001, UMH-002, CH-001, ORCH-002, etc.
```

---

**Status:** ✅ Ready to use
**Time:** Created in Phase 92 (2026-01-25)
**For:** VETKA Live v0.3
