# FIX MARKERS: Solo vs Group Chat Unification

## CRITICAL FIX LOCATIONS (для унификации)

### FILE 1: user_message_handler.py

#### MARKER-UMH-001: Replace Ollama Direct Call (Line ~355-362)

**CURRENT CODE:**
```python
# Line 355-362
def ollama_call():
    return ollama.chat(
        model=requested_model,
        messages=[{"role": "user", "content": model_prompt}],
        stream=False,
    )

ollama_response = await loop.run_in_executor(None, ollama_call)
```

**ISSUE:**
- Direct provider call bypasses orchestrator
- No system role in messages
- No Elisya integration
- Inconsistent with group chat

**FIX TO:**
```python
# Use orchestrator instead
result = await orchestrator.call_agent(
    agent_type="Assistant",  # Default role for direct chat
    model_id=requested_model,
    prompt=text,
    context={"file": node_path, "is_direct": True}
)

# Extract output
full_response = result.get("output", "")
```

---

#### MARKER-UMH-002: Replace OpenRouter Direct Call (Line ~567-580)

**CURRENT CODE:**
```python
# Line 567-580
payload = {
    "model": requested_model,
    "messages": [{"role": "user", "content": model_prompt}],
    "max_tokens": 999999,
    "temperature": 0.7,
    "stream": True,
}

async with client.stream(
    "POST",
    "https://openrouter.ai/api/v1/chat/completions",
    headers=headers,
    json=payload,
) as response:
```

**ISSUE:**
- Direct HTTP call bypasses provider registry
- Hardcoded URL
- Message format inconsistent
- No system role

**FIX TO:**
```python
# Use orchestrator + provider registry
result = await orchestrator.call_agent(
    agent_type="Assistant",
    model_id=f"openrouter/{requested_model}",  # Ensure provider prefix
    prompt=text,
    context={"file": node_path, "is_streaming": True}
)

full_response = result.get("output", "")
```

---

#### MARKER-UMH-003: Update Provider Detection (Line ~300-420)

**CURRENT CODE:**
```python
# Line 300-320
is_openai_model = ...
is_anthropic_model = ...
is_google_model = ...
is_direct_api_model = ...
is_openrouter_model = ...
is_ollama_model = ...
```

**ISSUE:**
- Duplicate detection logic (exists in provider_registry too)
- Hardcoded checks scattered through code
- Difficult to maintain

**FIX TO:**
```python
# Use chat_handler.py:detect_provider() which delegates to provider_registry
from .chat_handler import detect_provider

detected_provider = detect_provider(requested_model)
# Now use orchestrator - it handles routing
```

---

#### MARKER-UMH-004: Use Unified Message Format (Line ~358, 569)

**CURRENT CODE:**
```python
# Line 358 (Ollama)
messages = [{"role": "user", "content": model_prompt}]

# Line 569 (OpenRouter)
messages = [{"role": "user", "content": model_prompt}]
```

**ISSUE:**
- Only "user" role
- System prompt embedded in content
- Inconsistent with group chat (which uses system role)
- Cannot parse system vs user intent separately

**FIX TO:**
```python
# Split system and user message
system_prompt = get_agent_prompt("Assistant")  # From role_prompts.py
user_message = build_user_message(text, context, pinned, etc.)

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_message}
]

# Pass to orchestrator
result = await orchestrator.call_agent(
    agent_type="Assistant",
    model_id=requested_model,
    prompt=user_message,  # Just user part
    context={"system_prompt_override": system_prompt}
)
```

---

### FILE 2: chat_handler.py

#### MARKER-CH-001: Update build_model_prompt() (Line 110-157)

**CURRENT CODE:**
```python
# Line 110-157
def build_model_prompt(
    text: str,
    context_for_model: str,
    ...
) -> str:
    """Build a standard prompt for direct model calls."""

    return f"""You are a helpful AI assistant. Analyze the following context...

{context_for_model}

{json_section}{pinned_context}{spatial_section}{history_context}## CURRENT USER QUESTION
{text}

---

Provide a helpful, specific answer:"""
```

**ISSUE:**
- Returns single concatenated string
- System prompt hardcoded ("You are a helpful AI assistant")
- Cannot separate system role from user content
- Group chat uses different system prompts (PM, Dev, QA)

**FIX OPTIONS:**

**Option A: Return tuple (recommended for group compatibility)**
```python
def build_model_prompt(
    text: str,
    context_for_model: str,
    agent_type: str = "Assistant",  # NEW PARAMETER
    ...
) -> Tuple[str, str]:
    """Build system prompt and user message separately."""

    from src.agents.role_prompts import get_agent_prompt

    system_prompt = get_agent_prompt(agent_type)

    user_message = f"""## CONTEXT
{context_for_model}

{json_section}{pinned_context}{spatial_section}{history_context}## CURRENT QUESTION
{text}"""

    return (system_prompt, user_message)
```

**Option B: Create new separate functions**
```python
def get_system_prompt(agent_type: str = "Assistant") -> str:
    """Get system prompt for agent type."""
    from src.agents.role_prompts import get_agent_prompt
    return get_agent_prompt(agent_type)

def build_user_message(
    text: str,
    context_for_model: str,
    ...
) -> str:
    """Build only the user message part."""
    # Current logic without system prompt
```

---

#### MARKER-CH-002: Align detect_provider() (Line 49-87)

**CURRENT CODE:**
```python
# Line 49-87
def detect_provider(model_name: str) -> ModelProvider:
    """Detect which provider a model belongs to."""

    if not model_name:
        return ModelProvider.UNKNOWN

    from src.elisya.provider_registry import ProviderRegistry, Provider

    canonical_provider = ProviderRegistry.detect_provider(model_name)

    # Map Provider enum to ModelProvider enum
    provider_map = {...}

    result = provider_map.get(canonical_provider, ModelProvider.UNKNOWN)

    # Legacy check for deepseek/groq
    model_lower = model_name.lower()
    if model_lower.startswith("deepseek:") or "deepseek-api" in model_lower:
        return ModelProvider.DEEPSEEK
    if model_lower.startswith("groq:"):
        return ModelProvider.GROQ

    return result
```

**STATUS:** ✅ Already correct! Uses ProviderRegistry.detect_provider()

**VERIFY:**
- Confirm this is used everywhere in user_message_handler
- Ensure solo chat calls this instead of inline if/elif checks

---

### FILE 3: orchestrator_with_elisya.py

#### MARKER-ORCH-001: Ensure call_agent() Handles Solo Requests (Line 2242-2331)

**CURRENT CODE:**
```python
# Line 2265-2272: Valid agent types
valid_agent_types = [
    "PM",
    "Dev",
    "QA",
    "Architect",
    "Hostess",
    "Researcher",
]
```

**ISSUE:**
- No "Assistant" type for direct solo chat
- Solo chat will fail if agent_type="Assistant"

**FIX TO:**
```python
# Line 2265-2272: Add Assistant type
valid_agent_types = [
    "PM",
    "Dev",
    "QA",
    "Architect",
    "Hostess",
    "Researcher",
    "Assistant",  # ← NEW: For solo chat
]

# And in agent type mapping (line ~713-730 in group_message_handler):
agent_type_map = {
    "PM": "PM",
    "Dev": "Dev",
    "QA": "QA",
    "Architect": "Architect",
    "Researcher": "Researcher",
    "assistant": "Assistant",  # ← NEW
    "admin": "PM",
    "worker": "Dev",
}
```

---

#### MARKER-ORCH-002: Verify Message Format in _run_agent_with_elisya_async()

**LOCATION:** Lines ~1200-1400 (FIND THIS!)

**CURRENT ISSUE:**
- Need to verify that `_run_agent_with_elisya_async()` builds messages correctly
- Should separate system and user roles

**TO FIX:**
```python
# Should do something like:
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": prompt}
]

# Then call:
result = await call_model_v2(
    messages=messages,
    model=model_id,
    provider=provider,  # Can be None for auto-detect
    **kwargs
)
```

**ACTION:** Find and verify this code!

---

### FILE 4: provider_registry.py

#### MARKER-PR-001: Document call_model_v2 Message Format (Line 856-903)

**CURRENT CODE:**
```python
# Line 856-903
async def call_model_v2(
    messages: List[Dict[str, str]],
    model: str,
    provider: Optional[Provider] = None,
    tools: Optional[List[Dict]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Phase 80.10: New unified call_model with explicit provider.
    ...
    """
```

**ACTION:**
Add to docstring clarification about expected message format:

```python
"""
Phase 80.10: New unified call_model with explicit provider.

Key difference from old call_model:
- Provider is a FIRST-CLASS parameter
- No routing logic here - orchestrator decides provider
- If provider not specified, auto-detect as fallback

Args:
    messages: List of message dicts with 'role' and 'content' keys.
              EXPECTED FORMAT:
              [
                  {"role": "system", "content": "You are a helpful assistant"},
                  {"role": "user", "content": "What is 2+2?"}
              ]
    model: Model identifier
    provider: Provider enum (OPENAI, ANTHROPIC, etc.)
    tools: Optional list of tool schemas
    **kwargs: Additional params (temperature, max_tokens, etc.)

Returns:
    Standardized response dict with 'message' and 'usage' keys
"""
```

---

#### MARKER-PR-002: Verify Provider Detection Logic (Line 884-885)

**CURRENT CODE:**
```python
# Line 884-885
if provider is None:
    provider = ProviderRegistry.detect_provider(model)
```

**VERIFY:** This should handle all cases:
- ✅ `ollama/qwen2:7b` → Provider.OLLAMA
- ✅ `openrouter/gpt-4` → Provider.OPENROUTER
- ✅ `openai/gpt-4` → Provider.OPENAI
- ✅ `qwen2:7b` → Provider.OLLAMA (no prefix)

**IF NOT:** Add patterns to ProviderRegistry.detect_provider()

---

### FILE 5: group_message_handler.py

#### MARKER-GMH-001: Verify system_prompt Handling (Line 758)

**CURRENT CODE:**
```python
# Line 758: Get agent-specific system prompt
system_prompt = get_agent_prompt(agent_type)

# Line 762-772: Build context with role
context_parts = [
    f"## ROLE\n{system_prompt}\n",
    f"## GROUP: {group.get('name', 'Team Chat')}\n",
]
```

**ISSUE:**
- system_prompt is included IN prompt string (line 763)
- This is REDUNDANT if we also pass it as system role
- Need to either:
  1. Keep as-is (current group behavior)
  2. Or remove from prompt and let call_model_v2 handle it

**VERIFY:**
- If call_model_v2 builds: `[{"role": "system", ...}, {"role": "user", ...}]`
- Then we should NOT include system prompt in prompt string again

**FUTURE FIX:**
```python
# Option 1: Don't include system_prompt in context_parts
context_parts = [
    f"## GROUP: {group.get('name', 'Team Chat')}\n",
    # NOT including system_prompt - let orchestrator handle it
]

# Option 2: Pass system_prompt separately to orchestrator
result = await orchestrator.call_agent(
    agent_type=agent_type,
    model_id=model_id,
    prompt="\n".join(context_parts),  # User message only
    system_prompt_override=system_prompt,  # Pass explicitly
    context={...}
)
```

---

## IMPLEMENTATION ROADMAP

### Phase 1: Message Format Unification (CRITICAL)
```
Priority: HIGH
Effort: MEDIUM
Risk: MEDIUM

Steps:
1. MARKER-CH-001: Update build_model_prompt() to return (system, user) tuple
2. MARKER-UMH-003/004: Update user_message_handler to use new format
3. MARKER-PR-001: Document expected message format
4. MARKER-ORCH-002: Verify orchestrator builds messages correctly

Files to change:
- chat_handler.py (primary)
- user_message_handler.py (secondary)
- orchestrator_with_elisya.py (verify)
- provider_registry.py (document)
```

### Phase 2: Provider Routing Unification (IMPORTANT)
```
Priority: HIGH
Effort: SMALL
Risk: LOW

Steps:
1. MARKER-UMH-002: Replace OpenRouter direct HTTP with orchestrator
2. MARKER-UMH-001: Replace Ollama direct call with orchestrator
3. MARKER-UMH-003: Ensure detect_provider() is used everywhere
4. MARKER-PR-002: Verify provider detection covers all cases

Files to change:
- user_message_handler.py (primary)
- provider_registry.py (verify)
```

### Phase 3: Agent Type Unification (FEATURE)
```
Priority: MEDIUM
Effort: SMALL
Risk: LOW

Steps:
1. MARKER-ORCH-001: Add "Assistant" to valid_agent_types
2. Create Agent system prompt for solo chat (or use existing)
3. Allow users to select agent type in solo chat UI
4. Pass agent_type from frontend

Files to change:
- orchestrator_with_elisya.py (add type)
- role_prompts.py (optional: create ASSISTANT_SYSTEM_PROMPT)
- client/src/components/chat/ChatPanel.tsx (add UI selector)
```

### Phase 4: Testing & Verification (CRITICAL)
```
Priority: HIGH
Effort: LARGE
Risk: HIGH

Steps:
1. Test solo chat with all providers after changes
2. Test group chat still works (regression)
3. Verify streaming still works
4. Test error handling and fallbacks
5. Check performance (should be same or better)

Test files:
- tests/test_solo_chat.py (create or update)
- tests/test_group_chat.py (verify not broken)
- tests/test_provider_registry.py (verify routing)
- tests/test_orchestrator.py (verify call_agent)
```

---

## SUCCESS CRITERIA

When unification is COMPLETE:

- ✅ Solo chat uses `orchestrator.call_agent()`
- ✅ Group chat uses `orchestrator.call_agent()` (already does)
- ✅ Both use `call_model_v2()` under the hood
- ✅ Message format is consistent: `[{"role": "system"}, {"role": "user"}]`
- ✅ Provider detection is centralized in `ProviderRegistry.detect_provider()`
- ✅ System prompts come from `role_prompts.py` (or new place)
- ✅ No direct `ollama.chat()` or `httpx.post()` in handlers
- ✅ Solo chat can use agent types (PM, Dev, QA, or Assistant)
- ✅ Streaming works for both solo and group
- ✅ Error handling is consistent

---

## POTENTIAL ISSUES & MITIGATIONS

### Issue 1: Performance Regression
**Problem:** Orchestrator adds overhead
**Mitigation:**
- Measure before/after performance
- Consider lightweight path for simple solo requests
- Cache system prompts

### Issue 2: Breaking Changes
**Problem:** Existing solo chat API might break
**Mitigation:**
- Keep backward compatibility layer for old API
- Gradual migration with feature flag
- Update client code alongside

### Issue 3: Streaming Performance
**Problem:** Group chat buffers whole response (no incremental tokens)
**Mitigation:**
- Verify streaming works through orchestrator
- Consider async generator for token streaming
- May need updates to Socket.IO emit logic

### Issue 4: Message Format in Different Providers
**Problem:** Some providers might not support separate system role
**Mitigation:**
- Verify in provider implementations (OpenAI, Anthropic, Ollama, etc.)
- Fall back to merged format if needed
- Document provider-specific behavior

---

## MARKER QUICK REFERENCE

```
UMH = user_message_handler.py
CH = chat_handler.py
ORCH = orchestrator_with_elisya.py
PR = provider_registry.py
GMH = group_message_handler.py

CRITICAL FIXES (Do First):
1. MARKER-UMH-001: Ollama direct call → orchestrator
2. MARKER-UMH-002: OpenRouter direct call → orchestrator
3. MARKER-CH-001: build_model_prompt() return format
4. MARKER-ORCH-002: Verify message building

IMPORTANT FIXES (Do Second):
5. MARKER-PR-001: Document message format
6. MARKER-PR-002: Verify provider detection
7. MARKER-ORCH-001: Add "Assistant" agent type

OPTIONAL IMPROVEMENTS (Do Later):
8. MARKER-UMH-003: Remove duplicate detection
9. MARKER-GMH-001: Remove system_prompt duplication
```

---

## IMPLEMENTATION CHECKLIST

```
[ ] Read all markers and understand issues
[ ] Create feature branch: feature/solo-group-unification
[ ] Implement MARKER-CH-001 (build_model_prompt)
[ ] Implement MARKER-UMH-001 (Ollama)
[ ] Implement MARKER-UMH-002 (OpenRouter)
[ ] Implement MARKER-UMH-003 (Provider detection)
[ ] Implement MARKER-UMH-004 (Message format)
[ ] Implement MARKER-ORCH-001 (Assistant agent type)
[ ] Implement MARKER-ORCH-002 (Verify message building)
[ ] Test solo chat basic functionality
[ ] Test solo chat with different models
[ ] Test solo chat streaming
[ ] Test solo chat error handling
[ ] Test group chat (regression)
[ ] Update documentation
[ ] Create PR with all changes
[ ] Code review
[ ] Deploy
```

