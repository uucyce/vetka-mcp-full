# MARKER_90.1.4.1_START: Routing Logic Audit

# PHASE 90.1.4.1: Model Routing Logic - Comprehensive Audit

**Date:** 2026-01-23
**Scope:** All model selection and provider routing paths in VETKA

---

## Executive Summary

VETKA has 4 distinct model routing paths that need unification:

1. **Solo Chat Routing** - Direct user→model via `user_message_handler.py`
2. **Group Chat Routing** - Multi-agent group coordination via `group_message_handler.py`
3. **MCP Routing** - External tools calling models via `llm_call_tool.py`
4. **Orchestrator Routing** - Internal agent execution via `orchestrator_with_elisya.py`

Provider detection happens in **3 separate places** with inconsistent logic. This is the primary unification target.

---

## 1. SOLO CHAT ROUTING

**File:** `/src/api/handlers/user_message_handler.py`
**Entry:** `handle_user_message()` handler (line 142)

### Flow

```
user sends message with optional model selection
    ↓
Line 227: Check if requested_model provided by client
    ↓
Line 231: detect_provider() from chat_handler.py
    ├─ Ollama? → local model direct call (lines 247-359)
    ├─ OpenRouter? → streaming with key rotation (lines 372-590)
    └─ Named model? → parse from @mentions (lines 606-890)
    ↓
Line 1323: If no model specified, route through agent chain
    ↓
Loop through agents ['PM', 'Dev', 'QA']:
    - Line 1387: agent_instance.call_llm() - calls Agent's native LLM call
    - Agent determines model internally
```

### Provider Detection (SOLO)

**Function:** `chat_handler.detect_provider(model)` (lines 96-102 in user_message_handler.py)

```python
def detect_provider(model: str) -> ModelProvider:
    """
    Detects provider by checking model name patterns.

    Returns: ModelProvider enum
    """
    # Pattern matching:
    if model.startswith('gpt-') or model.startswith('openai/')    → OpenAI
    if model.startswith('claude-') or model.startswith('anthropic/')  → Anthropic
    if model.startswith('ollama:')                                → Ollama
    if model.startswith('x-ai/') or 'grok' in model              → x.ai (Grok)
    # ... more patterns
```

### Key Characteristics

- **Client-driven:** User selects model from dropdown
- **Direct LLM calls:** No orchestrator involvement
- **Streaming support:** Via `stream_response()` for Ollama
- **Key rotation:** Lines 384-501, handles 401/402 errors with key cycling
- **Fallback chain:** Direct → Streaming → Non-streaming

---

## 2. GROUP CHAT ROUTING

**File:** `/src/api/handlers/group_message_handler.py`
**Entry:** `handle_group_message()` handler (line 501)

### Flow

```
user sends message to group
    ↓
Line 621: select_responding_agents() from group_chat_manager.py
    ├─ @mention routing? → those agents only
    ├─ Smart keywords? → keyword-based agent selection
    └─ Default? → admin or first worker
    ↓
Line 729: orchestrator.call_agent(agent_type, model_id, prompt)
    ↓
Orchestrator returns response
    ↓
Line 760: Store message, emit response
```

### Provider Detection (GROUP)

**Function:** `group_chat_manager.select_responding_agents()` (line 165)

```python
async def select_responding_agents(
    content: str,
    participants: Dict[str, Any],  # participants have model_id already assigned
    sender_id: str,
    reply_to_agent: str = None,
    group: 'Group' = None
) -> List[Any]:
    """
    Returns list of participant dicts.
    Each participant has model_id already set!
    No provider detection here - model_id passed to orchestrator.
    """
```

**IMPORTANT:** Group routing does NOT detect provider - it delegates to orchestrator with model_id only.

### Model Selection Flow (GROUP)

```
Group participants created with model_id at group creation time
    ↓
select_responding_agents() returns participants
    ↓
Each participant has model_id = "openai/gpt-4o", "ollama/qwen:7b", etc.
    ↓
orchestrator.call_agent(agent_type='Dev', model_id='openai/gpt-4o', prompt)
    ↓
Orchestrator detects provider from model_id (lines 1113-1144)
```

### Key Characteristics

- **Group-centric:** Model assigned per participant at creation
- **Smart selection:** Keyword-based agent picking
- **Orchestrator delegation:** All LLM calls go through orchestrator
- **MCP mention handling:** Phase 80.13 - lines 92-208 notify external MCP agents

---

## 3. MCP ROUTING (llm_call_tool)

**File:** `/src/mcp/tools/llm_call_tool.py`
**Class:** `LLMCallTool.execute()` (line 136)

### Flow

```
MCP client calls vetka_call_model tool
    ↓
Line 181: _detect_provider(model_name)
    ├─ Check for grok/x-ai patterns → xai
    ├─ Check for gpt- patterns → openai
    ├─ Check for claude- patterns → anthropic
    ├─ Check for gemini patterns → google
    ├─ Check for : or known base names → ollama
    └─ Check for / in model → openrouter (fallback)
    ↓
Line 177: call_model_v2(messages, model, provider, **kwargs)
    ↓
Provider executes via provider_registry
```

### Provider Detection (MCP)

**Function:** `LLMCallTool._detect_provider()` (lines 89-124)

```python
def _detect_provider(self, model: str) -> str:
    """
    Returns provider NAME (string): 'xai', 'openai', 'anthropic', 'google', 'ollama', 'openrouter'

    Pattern matching (similar to Solo):
    - grok/x-ai patterns → xai
    - gpt- patterns → openai
    - claude- patterns → anthropic
    - gemini patterns → google
    - : or known base names → ollama
    - / in model → openrouter
    """
```

### Key Characteristics

- **Tool-centric:** Called via MCP protocol
- **Direct provider mapping:** Strings to Provider enum
- **No orchestrator:** Direct to provider_registry
- **Fallback:** OpenRouter for unknown models

---

## 4. ORCHESTRATOR ROUTING

**File:** `/src/orchestration/orchestrator_with_elisya.py`
**Method:** `_run_agent_with_elisya_async()` (line 1094)

### Flow

```
call_agent(agent_type='Dev', model_id='gpt-4o', prompt)
    ↓
Line 1113-1144: Manual model override routing
    ├─ Check for / in model_id
    │   └─ Extract provider from prefix: "openai/gpt-4o" → "openai"
    ├─ Check for gpt- → openai
    ├─ Check for claude- → anthropic
    ├─ Check for gemini- → google
    ├─ Check for grok- → xai (with fallback to openrouter)
    └─ Default → ollama
    ↓
Line 1147: _get_routing_for_task() for auto-detection
    ├─ Analyzes task type (from context)
    └─ Maps to provider
    ↓
Line 1182-1196: Convert to Provider enum
    ↓
Line 1191: _call_llm_with_tools_loop()
```

### Provider Detection (ORCHESTRATOR)

**Functions:**

1. **Line 1113-1144:** Manual model override detection
   ```python
   if '/' in manual_model:
       real_provider = manual_model.split('/')[0].replace('-', '')  # "x-ai" → "xai"
       if real_provider == 'xai':
           # Check if xai key exists, fallback to openrouter
   elif manual_model.startswith('gpt'):
       real_provider = 'openai'
   # ... more patterns
   ```

2. **Line 1147:** `_get_routing_for_task()` - task-based routing
   ```python
   routing = self._get_routing_for_task(str(state.context or '')[:100], agent_type)
   # Returns: {'provider': 'openai', 'model': 'gpt-4o'}
   ```

### Key Characteristics

- **Agent-centric:** Routes based on agent type
- **Task-aware:** Chooses provider by task complexity
- **Provider enum conversion:** Lines 1182-1187
- **Fallbacks:** xai→openrouter for Grok

---

## PROVIDER DETECTION COMPARISON TABLE

| Path | Location | Method | Patterns Checked | Falls Back To | Supports Tools |
|------|----------|--------|------------------|---------------|----------------|
| **Solo** | `chat_handler.py` | `detect_provider()` | slash format, model prefix | Unclear | Yes (implicit) |
| **Group** | Via Orchestrator | N/A (model_id passed) | Orchestrator handles | Orchestrator | Yes |
| **MCP** | `llm_call_tool.py` | `_detect_provider()` | explicit patterns | openrouter | Via provider enum |
| **Orchestrator** | `orchestrator_with_elisya.py` | Manual + auto | slash format, task-aware | openrouter | Via provider enum |

---

## PROVIDER CONSTANTS USED

### Provider Enum
**File:** `/src/elisya/provider_registry.py` (lines 31-39)

```python
class Provider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GEMINI = "gemini"  # Alias for google (Phase 80.41)
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    XAI = "xai"  # x.ai / Grok (Phase 80.35)
```

### Provider Detection (Canonical)
**File:** `/src/elisya/provider_registry.py` (lines 786-804)

```python
@staticmethod
def detect_provider(model_name: str) -> Provider:
    """FALLBACK detection in provider registry"""
    if model_lower.startswith('openai/') or model_lower.startswith('gpt-'):
        return Provider.OPENAI
    elif model_lower.startswith('anthropic/') or model_lower.startswith('claude-'):
        return Provider.ANTHROPIC
    elif model_lower.startswith('google/') or model_lower.startswith('gemini'):
        return Provider.GOOGLE
    elif ':' in model_name or model_lower.startswith('ollama/'):
        return Provider.OLLAMA
    elif '/' in model_name:
        return Provider.OPENROUTER
    else:
        return Provider.OLLAMA  # Default to local
```

---

## ISSUES FOUND

### 1. INCONSISTENT PROVIDER DETECTION

**Problem:** 3 different implementations of provider detection

- `chat_handler.detect_provider()` - returns ModelProvider enum
- `llm_call_tool._detect_provider()` - returns provider string
- `orchestrator._run_agent_with_elisya_async()` - inline slash/prefix matching
- `provider_registry.detect_provider()` - returns Provider enum (canonical)

**Impact:** Risk of mismatch between routing decisions and actual provider calls

### 2. MISSING XAI FALLBACK IN SOLO CHAT

**Problem:** Solo chat `detect_provider()` doesn't handle xai/x.ai patterns

**File:** `user_message_handler.py` lines 96-102

```python
# Current code missing:
if 'grok' in model_lower or model_lower.startswith('x-ai/'):
    return ModelProvider.XAI
```

**Impact:** Grok models routed incorrectly in solo chat

### 3. MODEL_ID AMBIGUITY IN GROUP CHAT

**Problem:** Group participants can have model_id like:
- `"ollama/qwen:7b"` (with provider prefix)
- `"qwen:7b"` (without prefix)
- `"gpt-4o"` (short name)
- `"openai/gpt-4o"` (explicit prefix)

**Impact:** Orchestrator's slice parsing (`split('/')[0]`) assumes slash format

### 4. FALLBACK CHAIN NOT DOCUMENTED

**Location:** `user_message_handler.py` lines 372-590

```python
# Line 478-501: If streaming fails, fallback to non-streaming
# But this logic is deeply nested and easy to miss
use_streaming = True  # Default
try:
    # Try streaming
except:
    use_streaming = False  # Fallback
finally:
    if not use_streaming and not full_response:
        # Try non-streaming
```

**Impact:** Unclear what happens when streaming fails mid-response

### 5. PHASE 80.37-80.40: XAI KEY DETECTION NOT UNIFORM

**Locations:**
- `orchestrator_with_elisya.py` lines 1121-1125: Checks APIKeyService
- `provider_registry.py` lines 677-706: Checks key, falls back to OpenRouter

**Problem:** Two different places check xai key availability

**Impact:** Inconsistent fallback behavior

---

## ROUTING TABLE - WHICH CALLS WHICH

```
┌─────────────────────────────────────────────────────────────┐
│ SOLO CHAT: user_message_handler.py                          │
├─────────────────────────────────────────────────────────────┤
│ requested_model provided?                                   │
│   ├─ YES → detect_provider() → direct LLM call               │
│   │         (Ollama or OpenRouter streaming)                │
│   └─ NO  → select agent chain ['PM', 'Dev', 'QA']          │
│            └─ agent.call_llm() [AGENT INTERNAL]             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ GROUP CHAT: group_message_handler.py                        │
├─────────────────────────────────────────────────────────────┤
│ select_responding_agents(content, participants)             │
│   └─ orchestrator.call_agent(agent_type, model_id, prompt)  │
│      └─ _run_agent_with_elisya_async()                      │
│         └─ _call_llm_with_tools_loop()                      │
│            └─ call_model_v2(provider)                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ MCP: llm_call_tool.py                                       │
├─────────────────────────────────────────────────────────────┤
│ execute(model, messages, tools)                             │
│   └─ _detect_provider()                                     │
│      └─ call_model_v2(provider)                             │
│         └─ registry.get(provider).call()                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR: orchestrator_with_elisya.py                  │
├─────────────────────────────────────────────────────────────┤
│ execute_full_workflow_streaming()                           │
│   ├─ _execute_parallel() or _execute_sequential()          │
│   │  └─ _run_agent_with_elisya_async()                     │
│   │     ├─ Manual model override detection                 │
│   │     ├─ or _get_routing_for_task()                      │
│   │     └─ _call_llm_with_tools_loop(provider_enum)        │
│   │        └─ call_model_v2()                              │
│   └─ call_agent() [GROUP CHAT SHORTCUT]                    │
│      └─ Same as _run_agent_with_elisya_async               │
└─────────────────────────────────────────────────────────────┘
```

---

## WHAT NEEDS UNIFICATION

### Priority 1: Consolidate Provider Detection

Create single canonical function in `provider_registry.py`:

```python
def detect_provider_unified(model_name: str) -> Provider:
    """
    CANONICAL provider detection used everywhere.
    - Handles all formats: "gpt-4o", "openai/gpt-4o", "x-ai/grok-4"
    - Handles short names: "claude", "gemini", "qwen"
    - Handles local models: "llama2:7b", "qwen:7b"
    - Special handling for xai: checks key, falls back to openrouter
    - Returns: Provider enum
    """
```

**Usage sites to update:**
1. `/src/api/handlers/chat_handler.py` - `detect_provider()`
2. `/src/mcp/tools/llm_call_tool.py` - `_detect_provider()`
3. `/src/orchestration/orchestrator_with_elisya.py` - lines 1113-1144 inline code
4. `/src/elisya/provider_registry.py` - already exists, use as base

### Priority 2: Unify XAI Fallback Logic

Current state:
- Orchestrator checks and falls back (lines 1121-1125)
- Provider registry checks and falls back (lines 677-706)
- Solo chat doesn't handle xai at all

**Solution:**
- Move xai key check to APIKeyService
- Have provider detection consult APIKeyService
- Centralize fallback logic

### Priority 3: Standardize Model ID Format

**Decision needed:** Which format is canonical?

Option A: `"provider/model"` format
- Pro: Explicit, unambiguous
- Con: Verbose

Option B: Short names with provider registry lookup
- Pro: User-friendly
- Con: Requires registry consultation

**Recommendation:** Use Option A internally, handle Option B in UI layer

---

## FILES INVOLVED

### Core Routing Files
- `/src/api/handlers/user_message_handler.py` - Solo chat (1695 lines)
- `/src/api/handlers/chat_handler.py` - Provider detection for solo
- `/src/api/handlers/group_message_handler.py` - Group chat (893 lines)
- `/src/services/group_chat_manager.py` - Group agent selection (973 lines)
- `/src/mcp/tools/llm_call_tool.py` - MCP routing (259 lines)
- `/src/orchestration/orchestrator_with_elisya.py` - Orchestrator (2500+ lines)
- `/src/elisya/provider_registry.py` - Provider registry (915 lines)

### Related Files
- `/src/orchestration/services/api_key_service.py` - API key management
- `/src/utils/unified_key_manager.py` - Key rotation and storage
- `/src/agents/role_prompts.py` - Agent system prompts
- `/src/chat/chat_history_manager.py` - Chat persistence

---

## MARKER_90.1.4.1_END

**Summary:** VETKA has 4 routing paths with 3+ inconsistent provider detection implementations. Primary unification target is consolidating provider detection into a single canonical function in `provider_registry.py` and updating all 4 routing paths to use it.
