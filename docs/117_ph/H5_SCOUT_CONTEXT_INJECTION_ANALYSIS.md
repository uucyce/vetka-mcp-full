# H5 SCOUT: Context Injection Architecture Analysis

## Executive Summary

This document analyzes how messages in VETKA chat can be injected as context into Mycelium pipeline prompts. The investigation reveals that **chat history injection is NOT YET implemented** but the infrastructure to support it already exists via the `inject_context` parameter.

---

## Key Findings

### H5_ARCHITECT_PROMPT_LINE
**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/agent_pipeline.py` (lines 1144-1158)

The architect system prompt is defined in two places:

1. **In-Code Default (agent_pipeline.py:144-167):**
```python
"architect": {
    "system": """You are a task architect for VETKA project.
Break down the task into clear subtasks.
For any unclear part, mark it with needs_research=true and add a question.

Respond in STRICT JSON format: {...}"""
}
```

2. **External Template File (data/templates/pipeline_prompts.json:7-12):**
```json
{
  "architect": {
    "system": "You are a task architect. Output ONLY valid JSON, no prose or explanations.\n\nRequired JSON format:\n{...}",
    "temperature": 0.1,
    "model": "anthropic/claude-sonnet-4",
    "model_fallback": "meta-llama/llama-3.1-8b-instruct:free"
  }
}
```

**How It's Used:**
- Loaded in `_load_prompts()` method (line 137-140)
- Applied in `_architect_plan()` method (line 1144)
- Merged into messages without context injection (line 1153-1156)

---

### H5_INJECT_SOURCES
**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/llm_call_tool.py` (lines 346-454)

The `_gather_inject_context()` method supports **5 primary sources**:

1. **Files** (lines 358-373)
   - Accepts file paths via `inject_config["files"]`
   - Reads up to 8,000 chars per file
   - Formats as: `### File: {path}\n```\n{content}\n```

2. **Session State** (lines 375-386)
   - Via `inject_config["session_id"]`
   - Loads from MCPStateManager
   - Formats as JSON: `### Session State: {session_id}\n```json\n{state}\n```

3. **User Preferences (Engram)** (lines 388-400)
   - Triggered by `inject_config["include_prefs"] = True`
   - Reads from EngramUserMemory (Qdrant-backed)
   - Max 1,500 chars

4. **CAM Active Nodes** (lines 402-413)
   - Via `inject_config["include_cam"] = True`
   - Gets up to 5 active context nodes
   - Formats as list of ID + content

5. **Semantic Search** (lines 415-434)
   - Via `inject_config["semantic_query"]` (string)
   - Performs HybridSearch over codebase
   - Returns up to N results (default: 5)
   - Includes relevance scores

**Advanced Features:**
- ELISION Compression (lines 442-451) - compresses context >2000 chars by 40-60%
- All context wrapped in `<vetka_context>` tags for LLM clarity

---

### H5_CHAT_HISTORY_INJECT
**Status:** **PARTIAL - Not Yet Implemented**

**Current State:**
- The `inject_context` parameter does NOT currently support chat history injection
- No `chat_history`, `group_messages`, or `recent_messages` option exists in `_gather_inject_context()`

**Infrastructure Already In Place:**
The codebase HAS the tools to implement this:

1. **Group Message Reading Tool** exists:
   - Tool name: `vetka_read_group_messages`
   - Endpoint: `/api/groups/{group_id}/messages`
   - Available in VETKA MCP bridge
   - Returns recent group messages by limit

2. **Chat Digest Tool** exists:
   - Tool name: `vetka_get_chat_digest`
   - Returns recent messages + summary for a chat
   - Accepts `chat_id` + `max_messages`

3. **Chat History Manager** exists:
   - Module: `src/chat/chat_history_manager`
   - Used by pinned files tool and session tools
   - Provides access to chat-specific message history

**What's Missing:**
To support chat history injection, need to:
1. Add `group_id` or `chat_id` parameter to `inject_config`
2. Call `vetka_get_chat_digest()` or group message API
3. Format recent messages into context
4. Prepend to system prompt (like other sources)

**Example Implementation Pattern:**
```python
# 6. Chat history (NEW - not yet implemented)
chat_id = inject_config.get("chat_id")
if chat_id:
    try:
        from src.chat.chat_history_manager import get_chat_history_manager
        chat_mgr = get_chat_history_manager()
        messages = chat_mgr.get_recent_messages(chat_id, limit=inject_config.get("message_limit", 10))
        if messages:
            # Format as readable context
            context_parts.append(f"### Recent Chat Context\n" + "\n".join(...))
    except Exception as e:
        logger.warning(f"[INJECT_CONTEXT] Chat history error: {e}")
```

---

### H5_PROMPT_TEMPLATE_FILE
**Primary Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/templates/pipeline_prompts.json`

**Structure:**
```json
{
  "_config": {
    "default_router": "openrouter",
    "comment": "Pipeline agent prompts...",
    "fallback_enabled": true
  },
  "architect": { "system": "...", "temperature": 0.1, "model": "..." },
  "researcher": { "system": "...", "temperature": 0.3, "model": "..." },
  "coder": { "system": "...", "temperature": 0.4, "model": "..." },
  "verifier": { "system": "...", "temperature": 0.1, "model": "..." }
}
```

**Backup Location:** In-code defaults in `agent_pipeline.py` lines 142-192 (fallback if JSON not found)

**Roles Defined:**
| Role | Model | Temperature | Purpose |
|------|-------|-------------|---------|
| architect | claude-sonnet-4 | 0.1 | Task decomposition |
| researcher | grok-4 | 0.3 | Deep research |
| coder | claude-sonnet-4 | 0.4 | Implementation |
| verifier | claude-sonnet-4 | 0.1 | Verification |

---

## Architecture: How Context Injection Works Today

### Flow Diagram

```
User Request
    ↓
AgentPipeline._architect_plan()
    ↓
LLMCallTool.execute({
    "model": "anthropic/claude-sonnet-4",
    "messages": [
        {"role": "system", "content": architect_prompt},
        {"role": "user", "content": task_description}
    ],
    "inject_context": {  // ← CONTEXT INJECTION CONFIG
        "semantic_query": question,
        "semantic_limit": 5,
        "include_prefs": True,
        "compress": True
    }
})
    ↓
LLMCallTool._gather_inject_context()  // Gathers from 5 sources
    ↓
Context prepended to system prompt as:
    <vetka_context>
    ### File: src/main.py
    ...
    ### User Preferences
    ...
    ### Semantic Search: 'question'
    ...
    </vetka_context>
    ↓
Full messages sent to LLM provider (OpenRouter/Polza/etc)
    ↓
Response returned + streamed to chat
```

### Current Inject Sources (Researcher Uses This)

In `agent_pipeline.py` lines 1227-1232, the researcher call includes:
```python
"inject_context": {
    "semantic_query": question,  # ← Source 5: Semantic search
    "semantic_limit": 5,
    "include_prefs": True,      # ← Source 3: User preferences
    "compress": True            # ← Enable ELISION compression
}
```

But architect does NOT use inject_context (lines 1151-1158):
```python
call_args = {
    "model": model,
    "messages": [...],  # No inject_context!
    "temperature": temperature,
    "max_tokens": 2000
}
```

---

## Discovery: Missing Chat History Support

### Why It Matters

If user writes in chat:
> "I found a bug in the authentication flow that causes session timeouts after 5 minutes"

**Current Behavior:**
- Architect plans without seeing this bug report
- Researcher researches the generic question
- Coder implements without context of the chat discussion

**Desired Behavior (H5 Goal):**
- Pipeline reads recent chat messages
- Injects bug report and chat context into architect/researcher/coder prompts
- All agents have full conversation history for better decisions

### Implementation Path

**Phase 1: Add chat_history source to `_gather_inject_context()`**
```python
# 6. Chat history from group chat
chat_id = inject_config.get("chat_id") or inject_config.get("group_id")
if chat_id:
    try:
        from src.chat.chat_history_manager import get_chat_history_manager
        chat_mgr = get_chat_history_manager()
        msg_limit = inject_config.get("message_limit", 10)
        recent_msgs = chat_mgr.get_recent_messages(chat_id, limit=msg_limit)
        if recent_msgs:
            msgs_text = "\n".join([f"- {m.get('sender', 'unknown')}: {m.get('content', '')[:300]}"
                                   for m in recent_msgs])
            context_parts.append(f"### Recent Chat Messages\n{msgs_text}")
    except Exception as e:
        logger.warning(f"[INJECT_CONTEXT] Chat history error: {e}")
```

**Phase 2: Update architect and coder to use chat context**
```python
# In _architect_plan()
call_args = {
    "model": model,
    "messages": [...],
    "inject_context": {
        "chat_id": self.chat_id,      # ← ADD THIS
        "message_limit": 5,
        "include_prefs": False,
        "compress": True
    }
}

# Same for _execute_subtask()
```

**Phase 3: Update prompt templates to reference chat context**
```json
{
  "architect": {
    "system": "You are a task architect. Consider recent chat messages when breaking down tasks.\n\nOutput ONLY valid JSON..."
  }
}
```

---

## Code Markers Found

| Marker | File | Lines | Purpose |
|--------|------|-------|---------|
| H5_ARCHITECT_PROMPT_LINE | agent_pipeline.py | 1144-1158 | Architect call (no inject_context) |
| H5_INJECT_SOURCES | llm_call_tool.py | 346-454 | 5 context sources defined |
| MARKER_55.2_START | llm_call_tool.py | 345-454 | Context injection implementation |
| MARKER_102.6_START | agent_pipeline.py | 1195-1269 | Researcher (uses inject_context) |
| MARKER_102.5_START | agent_pipeline.py | 1129-1193 | Architect planning |
| MARKER_102.13 | agent_pipeline.py | 1145, 1211 | Model selection from config |
| H5_PROMPT_TEMPLATE_FILE | pipeline_prompts.json | - | External prompt storage |

---

## Recommendations for H5 Implementation

### Short Term (Add Chat History Injection)
1. Extend `_gather_inject_context()` to support `chat_id` parameter
2. Call `get_chat_history_manager().get_recent_messages()` when `chat_id` provided
3. Format messages as readable context with sender + content
4. Update architect and coder calls to pass `self.chat_id` in inject_context

### Medium Term (Improve Context Formatting)
1. Create structured format for chat messages (timestamp, sender, content)
2. Add filtering for system messages vs user messages
3. Truncate/summarize old messages for efficiency
4. Test with different message volumes

### Long Term (Multi-Chat Context)
1. Support multiple chat sources (e.g., bug-report channel + general channel)
2. Weight recent messages higher than older ones
3. Extract entities/topics from chat and use for semantic search
4. Store processed chat context in CAM for faster access

---

## Files Modified Summary

**Read-Only Analysis (H5):**
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/agent_pipeline.py` — Prompt building, STM context
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/llm_call_tool.py` — inject_context implementation
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/templates/pipeline_prompts.json` — Prompt templates

**Implementation Targets (For Future H5 Work):**
- `src/mcp/tools/llm_call_tool.py` — Add chat_history source to `_gather_inject_context()`
- `src/orchestration/agent_pipeline.py` — Pass chat_id in inject_context configs
- `data/templates/pipeline_prompts.json` — Update system prompts to reference chat context

---

## Conclusion

The VETKA pipeline architecture **already has the building blocks for chat history injection**:
- `inject_context` parameter exists and works
- 5 context sources implemented
- Chat history access tools available
- ELISION compression ready

What's missing is the **6th source: chat history**. Implementation is straightforward and requires minimal changes to 2 files.

The architect/researcher/coder can all benefit from recent chat context, improving decision-making quality and preventing duplicate work.
