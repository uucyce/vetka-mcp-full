# H5 Implementation: Code Examples & Integration Points

## Current State: Where Context Injection Happens

### Current Researcher Call (USES inject_context)
**File:** `src/orchestration/agent_pipeline.py` lines 1195-1236

```python
async def _research(self, question: str) -> Dict[str, Any]:
    """Grok researcher with context injection."""
    tool = self._get_llm_tool()

    prompt = self.prompts["researcher"]
    model = prompt.get("model", "x-ai/grok-4")
    temperature = prompt.get("temperature", 0.3)

    call_args = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": f"Research this for VETKA project:\n\n{question}"}
        ],
        "temperature": temperature,
        "max_tokens": 1500,
        "inject_context": {  # ← CONTEXT INJECTION ENABLED
            "semantic_query": question,      # Source 5: Search codebase
            "semantic_limit": 5,
            "include_prefs": True,           # Source 3: User preferences
            "compress": True                 # Enable ELISION compression
        }
    }
    if self.provider_override:
        call_args["model_source"] = self.provider_override
    result = tool.execute(call_args)
    # ... rest of method
```

**Result:** Researcher gets injected context about:
1. User preferences from Engram
2. Semantic matches from codebase search
3. All compressed with ELISION

---

### Current Architect Call (NO inject_context)
**File:** `src/orchestration/agent_pipeline.py` lines 1129-1162

```python
async def _architect_plan(self, task: str, phase_type: str) -> Dict[str, Any]:
    """Task architect - NO context injection."""
    tool = self._get_llm_tool()

    prompt = self.prompts["architect"]
    model = prompt.get("model", "anthropic/claude-sonnet-4")
    temperature = prompt.get("temperature", 0.3)

    call_args = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": f"Phase type: {phase_type}\n\nTask to break down:\n{task}"}
        ],
        "temperature": temperature,
        "max_tokens": 2000
        # ← NO "inject_context" parameter!
    }
    if self.provider_override:
        call_args["model_source"] = self.provider_override
    result = tool.execute(call_args)
    # ... rest of method
```

**Issue:** Architect gets no context about:
- Recent chat discussions
- User preferences
- Relevant code files
- Related semantic matches

---

## Implementation: How to Add Chat History

### Step 1: Update LLMCallTool Schema
**File:** `src/mcp/tools/llm_call_tool.py` lines 158-200

Add chat_id parameter to inject_context schema:

```python
"inject_context": {
    "type": "object",
    "description": (
        "Phase 55.2: Auto-inject VETKA context into system prompt. "
        "VETKA will gather context from specified sources and prepend to messages. "
        "This saves tokens - you don't need to pass file contents in messages."
    ),
    "properties": {
        "files": {
            "type": "array",
            "items": {"type": "string"},
            "description": "File paths to read and inject (e.g., ['src/main.py', 'README.md'])"
        },
        "session_id": {
            "type": "string",
            "description": "MCPStateManager session ID to load state from"
        },
        "include_prefs": {
            "type": "boolean",
            "description": "Include user preferences from Engram memory",
            "default": False
        },
        "include_cam": {
            "type": "boolean",
            "description": "Include CAM (Context-Aware Memory) active nodes",
            "default": False
        },
        "semantic_query": {
            "type": "string",
            "description": "Semantic search query to find relevant context"
        },
        "semantic_limit": {
            "type": "integer",
            "description": "Max results for semantic search (default: 5)",
            "default": 5
        },
        "chat_id": {  # ← ADD THIS
            "type": "string",
            "description": "Chat/Group ID to include recent messages"
        },
        "message_limit": {  # ← ADD THIS
            "type": "integer",
            "description": "Max chat messages to include (default: 10)",
            "default": 10
        },
        "compress": {
            "type": "boolean",
            "description": "Apply ELISION compression to injected context",
            "default": True
        }
    }
}
```

---

### Step 2: Add Chat History Source to _gather_inject_context()
**File:** `src/mcp/tools/llm_call_tool.py` lines 346-454

Add AFTER semantic search (before compression):

```python
# 6. Chat history (NEW - Phase H5)
chat_id = inject_config.get("chat_id")
if chat_id:
    try:
        from src.chat.chat_history_manager import get_chat_history_manager
        chat_mgr = get_chat_history_manager()

        msg_limit = inject_config.get("message_limit", 10)

        # Get recent messages from chat
        recent_messages = chat_mgr.get_recent_messages(chat_id, limit=msg_limit)

        if recent_messages:
            # Format messages with sender and content
            msgs_formatted = []
            for msg in recent_messages:
                sender = msg.get('sender', msg.get('agent_id', 'unknown'))
                content = msg.get('content', '')[:300]  # Truncate long messages
                timestamp = msg.get('timestamp', '')

                # Format: "2026-02-07 10:30 @user: This is a message"
                if timestamp:
                    msgs_formatted.append(f"[{timestamp}] @{sender}: {content}")
                else:
                    msgs_formatted.append(f"@{sender}: {content}")

            msgs_text = "\n".join(msgs_formatted)
            context_parts.append(f"### Recent Chat Messages (last {msg_limit})\n{msgs_text}")

            logger.info(f"[INJECT_CONTEXT] Injected {len(recent_messages)} chat messages from {chat_id}")
    except Exception as e:
        logger.warning(f"[INJECT_CONTEXT] Chat history error: {e}")
```

---

### Step 3: Enable Context in Architect Call
**File:** `src/orchestration/agent_pipeline.py` lines 1151-1162

**BEFORE:**
```python
call_args = {
    "model": model,
    "messages": [
        {"role": "system", "content": prompt["system"]},
        {"role": "user", "content": f"Phase type: {phase_type}\n\nTask to break down:\n{task}"}
    ],
    "temperature": temperature,
    "max_tokens": 2000
}
```

**AFTER:**
```python
call_args = {
    "model": model,
    "messages": [
        {"role": "system", "content": prompt["system"]},
        {"role": "user", "content": f"Phase type: {phase_type}\n\nTask to break down:\n{task}"}
    ],
    "temperature": temperature,
    "max_tokens": 2000,
    "inject_context": {  # ← ADD THIS BLOCK
        "chat_id": self.chat_id,          # Use pipeline's chat_id
        "message_limit": 5,               # Last 5 chat messages
        "include_prefs": False,           # Optional: user preferences
        "compress": True                  # Enable ELISION if >2000 chars
    }
}
```

---

### Step 4: Enable Context in Coder Call
**File:** `src/orchestration/agent_pipeline.py` lines 1308-1323

**BEFORE:**
```python
call_args = {
    "model": model,
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"""
Phase type: {phase_type}
Subtask: {subtask.description}
Marker: {subtask.marker or 'MARKER_102.X'}

{context_str}

Execute this subtask. Provide clear, actionable output."""}
    ],
    "temperature": temperature,
    "max_tokens": 2000
}
```

**AFTER:**
```python
call_args = {
    "model": model,
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"""
Phase type: {phase_type}
Subtask: {subtask.description}
Marker: {subtask.marker or 'MARKER_102.X'}

{context_str}

Execute this subtask. Provide clear, actionable output."""}
    ],
    "temperature": temperature,
    "max_tokens": 2000,
    "inject_context": {  # ← ADD THIS BLOCK
        "chat_id": self.chat_id,
        "message_limit": 3,               # Last 3 chat messages (less is more for coder)
        "compress": True
    }
}
```

---

### Step 5: Update Prompts to Reference Chat Context
**File:** `data/templates/pipeline_prompts.json`

**BEFORE:**
```json
{
  "architect": {
    "system": "You are a task architect. Output ONLY valid JSON, no prose or explanations.\n\nRequired JSON format: {...}"
  }
}
```

**AFTER:**
```json
{
  "architect": {
    "system": "You are a task architect. Consider the recent chat context to understand user intent and any reported issues.\nOutput ONLY valid JSON, no prose or explanations.\n\nRequired JSON format: {...}"
  }
}
```

---

## Example: What Gets Injected

### Before (Architect Without Chat Context)
```
User Input:
"Implement authentication flow for VETKA dashboard"

System Prompt (Only):
"You are a task architect. Output ONLY valid JSON..."

LLM Output:
{
  "subtasks": [
    {"description": "Create login page", ...},
    {"description": "Add password hashing", ...},
    {"description": "Implement session tokens", ...}
  ]
}
```

### After (Architect With Chat Context)
```
User Input:
"Implement authentication flow for VETKA dashboard"

System Prompt + Injected Context:
"You are a task architect. Consider the recent chat context...

<vetka_context>
### Recent Chat Messages (last 5)
[2026-02-07 14:30] @danila: Found a bug in session timeout - expires after 5 mins
[2026-02-07 14:28] @architect: Should we use JWT or session cookies?
[2026-02-07 14:20] @danila: Need to fix the auth flow - users getting logged out
[2026-02-07 14:15] @researcher: OAuth2 standard says... (truncated)
[2026-02-07 14:10] @user: Let's use OAuth2 for better security
</vetka_context>

Output ONLY valid JSON..."

LLM Output:
{
  "subtasks": [
    {"description": "Fix session timeout issue (reported: 5 min expiration)", ...},
    {"description": "Implement OAuth2 flow", ...},
    {"description": "Add proper session management (session cookies vs JWT)", ...},
    {"description": "Test logout scenarios", ...}
  ]
}
```

---

## Testing Checklist

### Unit Test: Chat Context Gathering
```python
# Test in: tests/test_llm_call_tool.py

async def test_inject_context_with_chat_history():
    """Test that chat history is properly gathered and formatted."""
    tool = LLMCallTool()

    inject_config = {
        "chat_id": "test-chat-123",
        "message_limit": 5,
        "compress": False
    }

    context = await tool._gather_inject_context(inject_config)

    assert "<vetka_context>" in context
    assert "Recent Chat Messages" in context
    assert "@" in context  # Should have sender markers
```

### Integration Test: Architect with Chat
```python
# Test in: tests/test_agent_pipeline.py

async def test_architect_with_chat_context():
    """Test that architect receives and uses chat context."""
    pipeline = AgentPipeline(chat_id="test-chat-123")

    plan = await pipeline._architect_plan(
        "Fix session timeout bug",
        phase_type="fix"
    )

    # Verify plan mentions the bug or session management
    assert any("session" in st["description"].lower()
               for st in plan["subtasks"])
```

### Manual Test: Live Chat Injection
```python
# Steps:
1. Write a bug report in Lightning chat:
   "BUG: Authentication endpoint returns 500 on concurrent requests"

2. Launch pipeline with same chat_id as Lightning

3. Watch architect plan - should reference the bug report

4. Watch progress emit to Lightning - should show context was used

5. Check logs for: "[INJECT_CONTEXT] Injected N chat messages from {chat_id}"
```

---

## Backward Compatibility

The implementation is **fully backward compatible**:

1. **Existing code without chat_id:** Works as before (no chat context)
2. **New code with chat_id:** Automatically includes chat context
3. **ELISION compression:** Already handles both compressed and uncompressed
4. **Error handling:** Falls back gracefully if chat history unavailable

**Zero Breaking Changes:**
- No existing inject_context calls need updating
- New optional parameters only
- Researcher call unaffected
- All 5 existing sources still work

---

## Performance Considerations

**Token Usage:**
- Chat messages: ~50-200 tokens (5-10 recent messages)
- ELISION compression: 40-60% reduction if >2000 chars
- Total context budget: Usually <500 tokens after compression

**Latency:**
- Chat history fetch: ~50ms (via ChatHistoryManager)
- Formatting: ~10ms
- Compression: ~20ms
- Total overhead: ~80ms (negligible vs LLM call latency)

**Storage:**
- No additional storage needed
- Uses existing ChatHistoryManager
- Messages already indexed

---

## Monitoring & Debugging

**Log What Gets Injected:**
```python
logger.debug(f"[INJECT_CONTEXT] Chat history added: {len(recent_messages)} messages, {len(msgs_text)} chars")
```

**Track in VETKA Chat:**
```
@pipeline: [INJECT_CONTEXT] Injected 5 chat messages (324 chars)
Compressed: 324 → 196 chars (60% savings)
```

**Validate in LLM Response:**
Check if LLM response:
1. References recent chat messages
2. Acknowledges reported bugs/issues
3. Builds on previous architect decisions

---

## Future Enhancements

### Phase H6: Multi-Source Chat
```python
"inject_context": {
    "chat_id": "main-chat",          # Primary chat
    "secondary_chat": "bug-reports",  # Also include this
    "message_limit": 5,
    "filter_by_type": "user"          # Only user messages, not system
}
```

### Phase H7: Smart Message Selection
```python
# Don't just take last N messages, take N MOST RELEVANT
# Use semantic search to find relevant messages
semantic_query = question
relevant_messages = search_messages(chat_id, semantic_query, limit=5)
```

### Phase H8: Context Summarization
```python
# If >10 messages, use Claude to summarize them first
# "Summarize the key points from these 50 chat messages"
# Then inject summary instead of raw messages
```

---

## Questions & Answers

**Q: Will this slow down pipeline execution?**
A: No, chat history fetch (~50ms) is negligible vs LLM call (~5-30s)

**Q: What if chat has no recent messages?**
A: Graceful fallback - inject_context just won't include chat section

**Q: Can this leak sensitive information?**
A: No - only includes messages user already sees in chat UI

**Q: What about very large chats with 1000+ messages?**
A: `message_limit` parameter caps it (default: 10). ELISION compression handles excess.

**Q: Will this work with private/group chats?**
A: Yes, ChatHistoryManager supports any chat_id with proper access controls
