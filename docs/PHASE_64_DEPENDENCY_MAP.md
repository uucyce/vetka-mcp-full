# Phase 64: God Object Split - Dependency Map

**Date:** 2026-01-17
**Status:** COMPLETE
**Original File:** `src/api/handlers/user_message_handler.py` (~1,700 lines)

---

## Module Overview

```
src/api/handlers/
├── __init__.py              # Re-exports + register_all_handlers()
├── message_utils.py         # Phase 64.1 - Pure functions (~141 lines)
├── streaming_handler.py     # Phase 64.2 - Token streaming (~95 lines)
├── chat_handler.py          # Phase 64.3 - Model calls (~404 lines)
├── workflow_handler.py      # Phase 64.4 - Agent chain (~395 lines)
└── user_message_handler.py  # Phase 64.5 - Main orchestrator (~1,624 lines)
```

---

## Dependency Graph

```
                    ┌──────────────────────┐
                    │  user_message_handler │  (main orchestrator)
                    └──────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌──────────────────┐
│ message_utils │   │ streaming_handler│   │ workflow_handler │
│  (pure funcs) │   │   (streaming)    │   │  (agent chain)   │
└───────────────┘   └─────────────────┘   └──────────────────┘
        │                     │                     │
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   chat_handler   │
                    │ (model detection)│
                    └──────────────────┘
```

---

## Module Details

### 1. message_utils.py (Phase 64.1)

**Purpose:** Pure utility functions with zero side effects.

**Exports:**
```python
format_history_for_prompt(messages, max_messages=10) -> str
load_pinned_file_content(file_path, max_chars=3000) -> Optional[str]
build_pinned_context(pinned_files, max_files=10) -> str
```

**Dependencies:**
- `os` (stdlib)
- `typing` (stdlib)

**Used By:**
- `user_message_handler.py`
- `handlers/__init__.py` (re-export)

---

### 2. streaming_handler.py (Phase 64.2)

**Purpose:** Token streaming from LLM models via Socket.IO.

**Exports:**
```python
async stream_response(sio, sid, prompt, agent_name, model_name, node_id, node_path) -> Tuple[str, int]
```

**Dependencies:**
- `uuid` (stdlib)
- `src.elisya.api_aggregator_v3.call_model_stream`

**Socket.IO Events Emitted:**
- `stream_start`: `{id, agent, model}`
- `stream_token`: `{id, token}`
- `stream_end`: `{id, full_message, metadata}`

**Used By:**
- `user_message_handler.py` (for single agent streaming mode)
- `handlers/__init__.py` (re-export)

---

### 3. chat_handler.py (Phase 64.3)

**Purpose:** Direct model calls and provider detection.

**Exports:**
```python
# Enums
class ModelProvider(Enum):
    OLLAMA, OPENROUTER, GEMINI, XAI, DEEPSEEK, GROQ, ANTHROPIC, OPENAI, UNKNOWN

# Detection
detect_provider(model_name) -> ModelProvider
is_local_ollama_model(model_name) -> bool  # DEPRECATED

# Prompt Building
build_model_prompt(text, context_for_model, pinned_context="", history_context="") -> str

# Model Calls
async call_ollama_model(model_name, prompt, with_tools=False, tools=None) -> Tuple[str, Optional[list]]
async call_openrouter_model(model_name, prompt, api_key, max_tokens=2000, temperature=0.7, stream=True) -> Tuple[str, int, Optional[str]]

# Helpers
get_agent_short_name(model_name) -> str
async emit_model_response(sio, sid, response_text, model_name, node_id, node_path, timestamp, response_type="text")
async emit_stream_wrapper(sio, sid, model_name, full_response, prompt)
```

**Dependencies:**
- `asyncio`, `uuid`, `enum` (stdlib)
- `ollama` (external)
- `httpx` (external)

**Provider Detection Logic:**
```
gemini-*, gemini:*     → GEMINI
grok*, xai:*           → XAI
groq:*                 → GROQ
deepseek:*, deepseek-api → DEEPSEEK
ollama:*, model:tag    → OLLAMA
provider/model         → OPENROUTER
```

**Used By:**
- `user_message_handler.py`
- `handlers/__init__.py` (re-export)

---

### 4. workflow_handler.py (Phase 64.4)

**Purpose:** Agent chain orchestration, summary generation, Hostess routing.

**Exports:**
```python
# Summary
generate_simple_summary(responses) -> str
parse_llm_summary(response_text) -> str
build_summary_prompt(responses) -> str

# Routing
determine_agents_to_call(hostess_decision, parsed_mentions=None) -> Tuple[List[str], bool]
get_max_tokens_for_agent(agent_name, role_prompts_available) -> int

# Response Building
build_agent_response_dict(agent_name, model_name, response_text, node_id, node_path, timestamp) -> Dict

# Socket.IO Helpers
async emit_hostess_response(sio, sid, response_text, node_id, node_path, timestamp, response_type="text")
async emit_agent_response(sio, sid, response, file_available, response_type="text")
async emit_summary_response(sio, sid, summary_text, node_id, node_path, timestamp)
async emit_quick_actions(sio, sid, node_path, agent, is_summary=False)
```

**Dependencies:**
- `json`, `re` (stdlib)
- No external dependencies

**Agent Routing Logic:**
```python
hostess_decision.action:
  'quick_answer' → []
  'show_file'    → ['Dev']
  'agent_call'   → [specified_agent]
  'chain_call'   → ['PM', 'Dev', 'QA']
  'clarify'      → []
  'search'       → []
  'ask_provider' → []
  api_key_*      → []
```

**Used By:**
- `user_message_handler.py`
- `handlers/__init__.py` (re-export)

---

### 5. user_message_handler.py (Phase 64.5)

**Purpose:** Main Socket.IO handler that orchestrates all message processing.

**Exports:**
```python
register_user_message_handler(sio, app=None)
```

**Internal Flow:**
```
1. Parse incoming message data
2. Check for direct model call (requested_model)
   └── If Ollama/OpenRouter → call directly, return
3. Parse @mentions
   └── If model mention → call directly, return
4. Save user message to chat history
5. Get Hostess routing decision
   └── Handle: quick_answer, clarify, search, camera_focus, api_key actions
6. Determine agents to call
7. Run agent chain (PM → Dev → QA)
8. Extract artifacts, emit responses
9. Generate summary (if multi-agent)
10. Emit quick actions
```

**Dependencies:**
- `.message_utils`: format_history_for_prompt, build_pinned_context
- `.streaming_handler`: stream_response
- `.chat_handler`: detect_provider, build_model_prompt, get_agent_short_name
- `.workflow_handler`: generate_simple_summary, parse_llm_summary, ...
- `src.api.handlers.handler_utils`: sync_get_rich_context, save_chat_message, ...
- `src.agents.*`: parse_mentions, get_hostess, role_prompts
- `src.chat.*`: ChatRegistry, chat_history_manager
- `src.elisya.*`: api_aggregator_v3
- `src.orchestration.*`: cam_event_handler

---

## Import Patterns

### From Package Level
```python
from src.api.handlers import (
    format_history_for_prompt,
    stream_response,
    detect_provider,
    ModelProvider,
    generate_simple_summary,
)
```

### Direct Module Import
```python
from src.api.handlers.chat_handler import detect_provider, ModelProvider
from src.api.handlers.streaming_handler import stream_response
```

---

## Testing Commands

```bash
# Test all modules
python -c "from src.api.handlers import *; print('OK')"

# Test specific module
python -c "from src.api.handlers.chat_handler import detect_provider; print(detect_provider('qwen2:7b'))"

# Test provider detection
python -c "
from src.api.handlers.chat_handler import detect_provider, ModelProvider
tests = [
    ('qwen2:7b', ModelProvider.OLLAMA),
    ('anthropic/claude-3', ModelProvider.OPENROUTER),
    ('gemini-pro', ModelProvider.GEMINI),
    ('grok-1', ModelProvider.XAI),
]
for model, expected in tests:
    result = detect_provider(model)
    print(f'{model} -> {result.value} (expected: {expected.value})')
"

# Test full handler registration
python -c "from src.api.handlers import register_all_handlers; print('OK')"
```

---

## Migration Notes

### Backwards Compatibility
All original imports still work:
```python
# Old (still works)
from src.api.handlers.user_message_handler import register_user_message_handler

# New (preferred)
from src.api.handlers import register_user_message_handler
```

### Breaking Changes
None - all existing APIs preserved.

### Deprecations
- `is_local_ollama_model()` - Use `detect_provider()` instead

---

## Future Improvements

1. **Extract more from user_message_handler.py:**
   - Direct model call blocks (~350 lines) → `direct_model_handler.py`
   - @mention routing (~200 lines) → merge into `chat_handler.py`
   - Hostess response handling (~150 lines) → `hostess_handler.py`

2. **Add typing:**
   - Add TypedDict for socket message payloads
   - Add Protocol for agent interfaces

3. **Add tests:**
   - Unit tests for pure functions in `message_utils.py`
   - Integration tests for `chat_handler.py` provider detection

---

## Git History

```
edb418a Phase 64.5: Complete facade pattern for user_message_handler
2bd3690 Phase 64.4: Extract workflow_handler.py + improve provider detection
3219eac Phase 64.3: Extract chat_handler.py helpers
558b63b Phase 64.2: Extract streaming_handler.py from user_message_handler
d00cf73 Phase 64.1: Extract message_utils.py from user_message_handler
```
