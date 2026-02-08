# H5 Scout: Quick Reference Markers

## Marker Definitions (As Requested)

### H5_ARCHITECT_PROMPT_LINE
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/agent_pipeline.py`
**Lines:** 1144-1158
**Context:** Architect plan LLM call setup
**Status:** No context injection (missing opportunity)

```python
async def _architect_plan(self, task: str, phase_type: str) -> Dict[str, Any]:
    ...
    prompt = self.prompts["architect"]
    model = prompt.get("model", "anthropic/claude-sonnet-4")
    temperature = prompt.get("temperature", 0.3)

    call_args = {  # ← H5_ARCHITECT_PROMPT_LINE (line 1151)
        "model": model,
        "messages": [
            {"role": "system", "content": prompt["system"]},  # ← System prompt here
            {"role": "user", "content": f"Phase type: {phase_type}\n\nTask to break down:\n{task}"}
        ],
        "temperature": temperature,
        "max_tokens": 2000
        # NOTE: No "inject_context" parameter here!
    }
```

---

### H5_INJECT_SOURCES
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/llm_call_tool.py`
**Lines:** 346-454
**Method:** `_gather_inject_context()`
**Status:** 5 sources implemented, chat history NOT included

**Source 1: Files (lines 358-373)**
```python
files = inject_config.get("files", [])
if files:
    # Read up to 10 files, 8000 chars each
    context_parts.append(f"### File: {file_path}\n```\n{content}\n```")
```

**Source 2: Session State (lines 375-386)**
```python
session_id = inject_config.get("session_id")
if session_id:
    # Load from MCPStateManager
    context_parts.append(f"### Session State: {session_id}\n```json\n{json.dumps(state)}\n```")
```

**Source 3: User Preferences/Engram (lines 388-400)**
```python
if inject_config.get("include_prefs"):
    # Get preferences from EngramUserMemory (Qdrant)
    context_parts.append(f"### User Preferences\n```json\n{json.dumps(prefs)}\n```")
```

**Source 4: CAM Active Nodes (lines 402-413)**
```python
if inject_config.get("include_cam"):
    # Get up to 5 active context nodes
    context_parts.append(f"### CAM Active Context\n{nodes_text}")
```

**Source 5: Semantic Search (lines 415-434)**
```python
semantic_query = inject_config.get("semantic_query")
if semantic_query:
    # HybridSearch over codebase, up to N results
    context_parts.append(f"### Semantic Search: '{semantic_query}'\n{search_text}")
```

**Missing Source 6: Chat History**
```python
# NOT YET IMPLEMENTED - needed for H5 goal
chat_id = inject_config.get("chat_id")
if chat_id:
    # Read recent group messages
    # Format as readable context
    context_parts.append(f"### Recent Chat Messages\n...")
```

---

### H5_CHAT_HISTORY_INJECT
**Status:** `partial` - Infrastructure exists but NOT connected to inject_context

**Tools Available (NOT USED BY inject_context):**
1. `vetka_read_group_messages` - MCP tool in vetka_mcp_bridge.py
   - Endpoint: `/api/groups/{group_id}/messages`
   - Returns: recent messages by limit

2. `vetka_get_chat_digest` - MCP tool in vetka_mcp_bridge.py
   - Returns: summary + recent messages
   - Accepts: chat_id + max_messages

3. `ChatHistoryManager` - Python class
   - Module: `src/chat/chat_history_manager`
   - Method: `get_recent_messages(chat_id, limit)`

**Current Usage:**
- Files: `src/mcp/tools/pinned_files_tool.py`
- Files: `src/mcp/tools/session_tools.py`
- NOT used in: `llm_call_tool.py` inject_context

**Answer to Question:** `partial` - The tools exist, but not wired into inject_context parameter

---

### H5_PROMPT_TEMPLATE_FILE
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/templates/pipeline_prompts.json`
**Backup:** In-code defaults in `src/orchestration/agent_pipeline.py` lines 142-192

**Template Structure:**
```json
{
  "_config": {
    "default_router": "openrouter",
    "fallback_enabled": true
  },
  "architect": {
    "system": "You are a task architect...",
    "temperature": 0.1,
    "model": "anthropic/claude-sonnet-4",
    "model_fallback": "meta-llama/llama-3.1-8b-instruct:free"
  },
  "researcher": {...},
  "coder": {...},
  "verifier": {...}
}
```

**Loading Logic (agent_pipeline.py:137-140):**
```python
def _load_prompts(self):
    if PROMPTS_FILE.exists():
        self.prompts = json.loads(PROMPTS_FILE.read_text())
    else:
        self.prompts = {
            "architect": {...},  # Fallback in-code
            "researcher": {...},
            "coder": {...}
        }
```

---

## Quick Lookup Table

| Marker | File | Line(s) | What It Is | Status |
|--------|------|---------|-----------|--------|
| H5_ARCHITECT_PROMPT_LINE | agent_pipeline.py | 1144-1158 | Architect system prompt setup | No inject_context |
| H5_INJECT_SOURCES | llm_call_tool.py | 346-454 | 5 context sources implemented | Missing chat_history |
| H5_CHAT_HISTORY_INJECT | llm_call_tool.py | N/A | Chat history support | **Not implemented** |
| H5_PROMPT_TEMPLATE_FILE | pipeline_prompts.json | N/A | External prompt templates | Exists |

---

## How to Find Each Marker

### Find H5_ARCHITECT_PROMPT_LINE
```bash
grep -n "call_args = {" src/orchestration/agent_pipeline.py | grep -A5 "model"
# Look for the first one around line 1151 (architect)
```

### Find H5_INJECT_SOURCES
```bash
grep -n "_gather_inject_context\|# 1\. Read files\|# 2\. Load session\|# 5\. Semantic" src/mcp/tools/llm_call_tool.py
```

### Find H5_PROMPT_TEMPLATE_FILE
```bash
find . -name "pipeline_prompts.json" -o -name "model_presets.json"
```

---

## Diagram: Context Injection Pipeline

```
inject_config = {
    "files": [...],              ← Source 1
    "session_id": "...",         ← Source 2
    "include_prefs": True,       ← Source 3
    "include_cam": True,         ← Source 4
    "semantic_query": "...",     ← Source 5
    "chat_id": "...",            ← Source 6 (NOT IMPLEMENTED)
    "compress": True
}
    ↓
_gather_inject_context(inject_config)
    ↓
Collects from all 5 sources (6th missing)
    ↓
Joins into single context string
    ↓
Applies ELISION compression if >2000 chars
    ↓
Wraps in <vetka_context>...</vetka_context>
    ↓
Prepends to system message in LLM call
    ↓
Full context available to LLM
```

---

## Implementation Checklist for H5

- [ ] Add chat_id/group_id parameter to inject_config schema (llm_call_tool.py:158-200)
- [ ] Add Source 6 to _gather_inject_context() method (llm_call_tool.py:~435)
- [ ] Call ChatHistoryManager.get_recent_messages()
- [ ] Format messages into context_parts
- [ ] Update architect call to include inject_context with chat_id (agent_pipeline.py:1227)
- [ ] Update coder call to include inject_context with chat_id (agent_pipeline.py:1308)
- [ ] Update prompt templates to mention chat context (pipeline_prompts.json)
- [ ] Test with real chat messages in Lightning group
- [ ] Validate ELISION compression doesn't mangle messages
