# HAIKU 4: COMPLETE MARKER REFERENCE

**Use this file for exact line numbers and code locations.**

---

## 📍 ALL MARKERS BY FILE

### user_message_handler.py
**Path:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py`

| Marker | Type | Line | Status | Document |
|--------|------|------|--------|----------|
| **MARKER-UMH-001** | FIX | 355-362 | CRITICAL | FIX_MARKERS.md |
| **MARKER-UMH-002** | FIX | 567-580 | CRITICAL | FIX_MARKERS.md |
| **MARKER-UMH-003** | CLEAN | ~300-420 | IMPORTANT | FIX_MARKERS.md |
| **MARKER-UMH-004** | CHANGE | 358, 569 | CRITICAL | FIX_MARKERS.md |

#### Details:

**MARKER-UMH-001: Ollama Direct Call (Line 355-362)**
```
Current: ollama.chat(model=..., messages=[{"role":"user",...}], stream=False)
Issue: Direct provider call, no orchestrator, wrong message format
Fix: Use orchestrator.call_agent(agent_type="Assistant", model_id=..., prompt=...)
Reason: Unify with group chat system
```

**MARKER-UMH-002: OpenRouter HTTP Call (Line 567-580)**
```
Current: httpx.stream("POST", "https://openrouter.ai/api/v1/chat/completions", ...)
Issue: Direct HTTP, hardcoded URL, no provider registry
Fix: Use orchestrator.call_agent(agent_type="Assistant", model_id=f"openrouter/{model}"...)
Reason: Unify with group chat, use provider registry
```

**MARKER-UMH-003: Provider Detection (Line ~300-420)**
```
Current: Multiple if/elif blocks checking model name
Issue: Duplicates logic from provider_registry.py
Fix: Use detect_provider() from chat_handler.py (delegates to ProviderRegistry)
Reason: DRY - Don't Repeat Yourself
```

**MARKER-UMH-004: Message Format (Line 358, 569)**
```
Current: messages = [{"role": "user", "content": full_prompt}]
Issue: Only user role, system prompt embedded in content
Fix: messages = [{"role": "system", ...}, {"role": "user", ...}]
Reason: Standard LLM format, matches group chat
```

---

### chat_handler.py
**Path:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/chat_handler.py`

| Marker | Type | Line | Status | Document |
|--------|------|------|--------|----------|
| **MARKER-CH-001** | REFACTOR | 110-157 | CRITICAL | FIX_MARKERS.md |
| **MARKER-CH-002** | VERIFY | 49-87 | IMPORTANT | FIX_MARKERS.md |

#### Details:

**MARKER-CH-001: build_model_prompt() Refactor (Line 110-157)**
```
Current:
def build_model_prompt(text, context, ...) -> str:
    """Returns single concatenated prompt string"""
    return f"You are a helpful AI...{context}...{text}"

Issues:
1. Single string return
2. System prompt hardcoded ("You are a helpful AI...")
3. Cannot use different roles (PM, Dev, QA)
4. Inconsistent with group chat (which has separate system role)

Fix Option A (Recommended):
def build_model_prompt(text, context, agent_type="Assistant", ...) -> Tuple[str, str]:
    """Returns (system_prompt, user_message) tuple"""
    system_prompt = get_agent_prompt(agent_type)  # From role_prompts.py
    user_message = f"{context}\n\n{text}"
    return (system_prompt, user_message)

Fix Option B:
Create separate functions:
- get_system_prompt(agent_type) -> str
- build_user_message(text, context, ...) -> str

Reason: Support different agent types, match group chat format
```

**MARKER-CH-002: detect_provider() Status (Line 49-87)**
```
Current: ✅ CORRECT!
Code: Delegates to ProviderRegistry.detect_provider()
No action needed - just verify it's being used everywhere
```

---

### orchestrator_with_elisya.py
**Path:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/orchestrator_with_elisya.py`

| Marker | Type | Line | Status | Document |
|--------|------|------|--------|----------|
| **MARKER-ORCH-001** | ADD | 2265-2272 | IMPORTANT | FIX_MARKERS.md |
| **MARKER-ORCH-002** | VERIFY | ~1200-1400 | CRITICAL | FIX_MARKERS.md |

#### Details:

**MARKER-ORCH-001: Add "Assistant" Agent Type (Line 2265-2272)**
```
Current:
valid_agent_types = [
    "PM",
    "Dev",
    "QA",
    "Architect",
    "Hostess",
    "Researcher",
]

Issue: No "Assistant" type for direct solo chat
Fix: Add "Assistant" to list:
valid_agent_types = [
    "PM",
    "Dev",
    "QA",
    "Architect",
    "Hostess",
    "Researcher",
    "Assistant",  # ← NEW
]

Reason: Allow solo chat to use agent type "Assistant"
```

**MARKER-ORCH-002: Verify Message Building (Line ~1200-1400)**
```
NEED TO FIND: _run_agent_with_elisya_async() method

What to verify:
1. It should build messages with explicit roles:
   messages = [
       {"role": "system", "content": system_prompt},
       {"role": "user", "content": prompt}
   ]

2. It should call call_model_v2() with these messages:
   result = await call_model_v2(
       messages=messages,
       model=model_id,
       provider=provider,  # Can be None for auto-detect
       **kwargs
   )

3. System prompt should NOT be duplicated in prompt string

If any of these are wrong, need to fix!

Reason: Ensure consistent message format for both solo and group
```

---

### provider_registry.py
**Path:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/provider_registry.py`

| Marker | Type | Line | Status | Document |
|--------|------|------|--------|----------|
| **MARKER-PR-001** | DOCUMENT | 856-903 | IMPORTANT | FIX_MARKERS.md |
| **MARKER-PR-002** | VERIFY | 884-885 | IMPORTANT | FIX_MARKERS.md |

#### Details:

**MARKER-PR-001: Document call_model_v2() (Line 856-903)**
```
Location: async def call_model_v2(...)

Current docstring: Has basic description

Add to docstring:

"""
...existing description...

EXPECTED MESSAGE FORMAT:
messages: List[Dict[str, str]] with format:
    [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "What is 2+2?"}
    ]

DO NOT send:
    [{"role": "user", "content": "full prompt including system..."}]

This is critical for proper routing to providers.
Providers expect separate system and user roles.

Args:
    messages: List with role and content dicts
    model: Model identifier (e.g., "gpt-4", "qwen2:7b", "openrouter/claude-3")
    provider: Optional Provider enum (auto-detects if None)
    tools: Optional list of tool schemas
    **kwargs: temperature, max_tokens, etc.

Returns:
    Dict with:
    {
        "message": {"content": str, "tool_calls": Optional[List]},
        "model": str,
        "provider": str,
        "usage": Optional[Dict]
    }
"""

Reason: Prevent incorrect usage, document requirements
```

**MARKER-PR-002: Verify Provider Detection (Line 884-885)**
```
Current:
if provider is None:
    provider = ProviderRegistry.detect_provider(model)

Verify these cases work:
- "qwen2:7b" → OLLAMA ✓
- "ollama/qwen2:7b" → OLLAMA ✓
- "gpt-4" → OPENAI ✓
- "openai/gpt-4" → OPENAI ✓
- "openrouter/gpt-4" → OPENROUTER ✓
- "claude-3" → ANTHROPIC ✓
- "anthropic/claude-3" → ANTHROPIC ✓
- "gemini-pro" → GOOGLE ✓
- "google/gemini-pro" → GOOGLE ✓
- "grok-4" → XAI ✓
- "xai/grok-4" → XAI ✓

If any missing, add to ProviderRegistry.detect_provider()

Reason: Ensure all model formats are recognized
```

---

### group_message_handler.py
**Path:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`

| Marker | Type | Line | Status | Document |
|--------|------|------|--------|----------|
| **MARKER-GMH-001** | VERIFY | 758 | MEDIUM | FIX_MARKERS.md |

#### Details:

**MARKER-GMH-001: System Prompt Handling (Line 758, 762-772)**
```
Current code:
system_prompt = get_agent_prompt(agent_type)  # Line 758

context_parts = [
    f"## ROLE\n{system_prompt}\n",  # ← INCLUDES SYSTEM PROMPT
    f"## GROUP: {group.get('name', 'Team Chat')}\n",
    ...
]

prompt = "\n".join(context_parts)

Issue: system_prompt is included in BOTH places:
1. As system_prompt variable (for what?)
2. IN the prompt string (context_parts)

This is REDUNDANT if call_model_v2 builds:
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": prompt_with_system_in_it}  # DUPLICATION!
]

Future optimization (NOT CRITICAL NOW):
Option 1: Don't include system in context_parts
context_parts = [
    f"## GROUP: ...",
    f"## PREVIOUS OUTPUTS: ...",
    ...  # NO system_prompt
]

Option 2: Create wrapper that handles both
This is a FUTURE optimization, not required for unification

Status: OK for now, but document for future refactoring
```

---

## 🎯 MARKER EXECUTION ORDER

### TIER 1: CRITICAL (Do in this order)
```
1. MARKER-CH-001    [chat_handler.py:110]      Refactor build_model_prompt()
2. MARKER-UMH-001   [user_message_handler.py:355]  Replace Ollama call
3. MARKER-UMH-002   [user_message_handler.py:567]  Replace OpenRouter call
4. MARKER-UMH-004   [user_message_handler.py:358]  Update message format
5. MARKER-ORCH-002  [orchestrator_with_elisya.py:~1200]  Verify message building
```

### TIER 2: IMPORTANT (Do after tier 1)
```
6. MARKER-ORCH-001  [orchestrator_with_elisya.py:2265]  Add "Assistant" type
7. MARKER-PR-001    [provider_registry.py:856]          Document message format
8. MARKER-UMH-003   [user_message_handler.py:~300]      Remove duplicate detection
```

### TIER 3: OPTIONAL (Do for completeness)
```
9. MARKER-CH-002    [chat_handler.py:49]                Verify detect_provider()
10. MARKER-PR-002   [provider_registry.py:884]          Verify provider detection
11. MARKER-GMH-001  [group_message_handler.py:758]      Verify system_prompt
```

---

## 🔄 DEPENDENCIES

```
MARKER-CH-001 (build_model_prompt)
    ↓ Depends on
    ↓
    MARKER-UMH-001, UMH-002, UMH-004 (use new return format)
    ↓
    MARKER-ORCH-002 (receives correct format)
    ↓
    MARKER-ORCH-001 (handles "Assistant" type)
    ↓
    MARKER-PR-001 (documents expected format)

MARKER-UMH-003 (cleanup) - Can be done independently
MARKER-PR-002 (verify) - Can be done independently
MARKER-GMH-001 (verify) - Can be done independently
```

---

## 📝 MARKER TEMPLATE

When you reach each marker, follow this template:

```
MARKER: [Name]
File: [full path]
Line: [numbers]
Type: [FIX/VERIFY/CLEAN/DOCUMENT/ADD]

1. CURRENT CODE
   [Show exact current code from file]

2. ISSUE
   [What's wrong with current code]

3. VERIFICATION (Before making changes)
   [How to verify the issue exists]

4. FIX
   [Exact code to use instead]

5. TESTING (After making changes)
   [How to verify fix works]

6. STATUS
   [ ] TODO
   [ ] IN PROGRESS
   [ ] DONE - Verified working
   [ ] DONE - Merged to main
```

---

## 🧪 VALIDATION FOR EACH MARKER

### After MARKER-CH-001
```
Test:
- Call build_model_prompt("What is 2+2?", "<context>")
- Verify returns: (system_prompt_str, user_message_str)
- NOT: single string
```

### After MARKER-UMH-001
```
Test:
- Send message to solo chat with Ollama model
- Verify: No direct ollama.chat() calls in logs
- Verify: Uses orchestrator.call_agent() instead
- Verify: Response received correctly
```

### After MARKER-UMH-002
```
Test:
- Send message to solo chat with OpenRouter/gpt-4
- Verify: No direct httpx.post() to openrouter.ai
- Verify: Uses orchestrator instead
- Verify: Streaming still works
```

### After MARKER-UMH-004
```
Test:
- Check message format in provider logs
- Verify: messages = [{"role":"system",...}, {"role":"user",...}]
- NOT: messages = [{"role":"user","content":"full_prompt..."}]
```

### After MARKER-ORCH-002
```
Test:
- Find _run_agent_with_elisya_async() code
- Verify: Builds messages correctly
- Verify: No duplication of system prompt
- Verify: Passes to call_model_v2()
```

### After MARKER-ORCH-001
```
Test:
- Try: orchestrator.call_agent(agent_type="Assistant", ...)
- Verify: Does NOT error "Invalid agent type"
- Verify: Works like "Dev" or "PM"
```

---

## 🚨 COMMON MISTAKES

| Mistake | How to Avoid | Check |
|---------|------------|-------|
| Forget to import orchestrator | Import at top of file | `from src.initialization.components_init import get_orchestrator` |
| Wrong message format | Keep reference card handy | Must have both role and content |
| Miss a marker | Use checklist | ✓ All 11 markers done |
| Test only solo | Test both paths | Test solo AND group after changes |
| Forget to handle "Assistant" type | Add to valid_agent_types | List includes "Assistant" |
| Break streaming | Test explicitly | Check tokens appear incrementally |
| Duplicate system prompt | Check orchestrator code | System only in one place |

---

## 📊 TRACKING PROGRESS

Copy this and track your progress:

```
[ ] MARKER-CH-001: build_model_prompt() refactor
[ ] MARKER-UMH-001: Replace Ollama direct call
[ ] MARKER-UMH-002: Replace OpenRouter direct call
[ ] MARKER-UMH-004: Update message format
[ ] MARKER-ORCH-002: Verify message building in orchestrator

[ ] MARKER-ORCH-001: Add "Assistant" agent type
[ ] MARKER-PR-001: Document call_model_v2() format
[ ] MARKER-UMH-003: Remove duplicate provider detection

[ ] MARKER-CH-002: Verify detect_provider()
[ ] MARKER-PR-002: Verify provider detection
[ ] MARKER-GMH-001: Verify system_prompt handling

[ ] Test solo chat with Ollama
[ ] Test solo chat with OpenRouter
[ ] Test solo chat with GPT-4
[ ] Test group chat (regression)
[ ] Test streaming
[ ] Test error handling
[ ] Performance check

[ ] All tests pass
[ ] Code review done
[ ] Ready to merge
[ ] Deployed to production
```

---

## 🎓 LEARNING OUTCOMES

After implementing all markers, you will understand:

- ✅ How solo chat works (current broken state)
- ✅ How group chat works (correct state)
- ✅ Why they're different
- ✅ How to unify them
- ✅ Where providers are detected
- ✅ How message format affects routing
- ✅ Why system prompts are important
- ✅ How orchestrator coordinates calls
- ✅ How provider_registry handles routing
- ✅ How to maintain code consistency

**You'll be the expert on VETKA's LLM calling system!**

---

**Created:** Phase 92 (2026-01-25)
**Status:** Ready for Development
**Total Markers:** 11
**Estimated Time:** 6-9 hours implementation + testing
