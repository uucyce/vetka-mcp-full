# MARKER_114.8_SCOPE_VARS
## Complete Variable Scope Analysis for Stream Path (solo chat)

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py`

**Stream Call Location:** Lines 639-645

---

## AVAILABLE_VARS at stream call (line ~639)

### INPUT VARIABLES (from client data)
```python
text: str                   # Line 203, from data.get("text")
                           # Description: Original user query
                           # Status: ALWAYS AVAILABLE

node_path: str            # Line 212-216, normalized from data.get("node_path")
                          # Description: Resolved file/folder path
                          # Status: May be "unknown"

node_id: str              # Line 204, from data.get("node_id", "root")
                          # Description: Unique node identifier
                          # Status: Defaults to "root"

requested_model: str      # Line 219, from data.get("model")
                          # Description: Model name to use
                          # Status: May be None

model_source: str|None    # Line 221, from data.get("model_source")
                          # Description: Provider source (poe, polza, openrouter, etc)
                          # Status: May be None

pinned_files: list        # Line 226, from data.get("pinned_files", [])
                          # Description: List of pinned file paths
                          # Status: May be empty []

viewport_context: dict|None # Line 229, from data.get("viewport_context")
                            # Description: 3D viewport state
                            # Status: May be None
                            # Keys: total_pinned, total_visible, zoom_level

client_chat_id: str|None  # Line 233, from data.get("chat_id")
                          # Description: Chat ID provided by client
                          # Status: May be None

client_display_name: str|None # Line 238, from data.get("display_name")
                              # Description: Display name for chat
                              # Status: May be None
```

### DERIVED VARIABLES (computed before stream call)

#### Context Variables
```python
rich_context: dict        # Line 540, from sync_get_rich_context(node_path)
                         # Description: File/node rich context
                         # Status: ALWAYS SET
                         # Note: May contain "error" key if sync fails

context_for_model: str   # Line 542-548, from format_context_for_agent()
                         # Description: Formatted context string for model
                         # Status: ALWAYS SET
                         # Includes: file content, structure, metadata
```

#### Chat History Variables
```python
chat_id: str             # Line 524, from get_or_create_chat()
                         # Description: Unified chat identifier
                         # Status: ALWAYS SET
                         # Generated from semantic key if not provided

chat_display_name: str   # Line 523, computed
                         # Description: client_display_name OR semantic_key from text
                         # Status: ALWAYS SET
                         # Logic: client_display_name > semantic_key > default

history_messages: list   # Line 530, from get_chat_messages(chat_id)
                         # Description: Previous messages in this chat
                         # Status: ALWAYS SET
                         # Max length: controlled by get_chat_messages()

history_context: str     # Line 531-532, from format_history_for_prompt()
                         # Description: Formatted chat history for prompt
                         # Status: ALWAYS SET
                         # Max messages: 10 (hard-coded in call)
```

#### Pinned Context
```python
pinned_context: str      # Line 551-555, from build_pinned_context()
                         # Description: Formatted pinned files context
                         # Status: CONDITIONAL
                         # Condition: Only if pinned_files is non-empty
                         # Default: "" (empty string)
```

#### Viewport Context
```python
viewport_summary: str    # Line 558-559, from build_viewport_summary()
                         # Description: 3D viewport spatial summary
                         # Status: CONDITIONAL
                         # Condition: Only if viewport_context exists
                         # Default: "" (empty string)
```

#### JSON Context
```python
json_context: str        # Line 565-570, from build_json_context()
                         # Description: Structured JSON dependency context
                         # Status: ALWAYS SET
                         # Parameters passed:
                         #  - pinned_files (list)
                         #  - viewport_context (dict|None)
                         #  - session_id=sid (str)
                         #  - model_name=requested_model (str)
```

#### Model Call Variables
```python
agent_short_name: str    # Line 593, from get_agent_short_name(requested_model)
                         # Description: Short agent name for UI
                         # Status: ALWAYS SET

msg_id: str              # Line 594, from str(uuid.uuid4())
                         # Description: Unique message identifier
                         # Status: ALWAYS SET

detected_provider: enum  # Line 617, from ProviderRegistry.detect_provider()
                         # Description: Detected model provider
                         # Status: ALWAYS SET

stream_system_prompt: str # Line 622-631, hard-coded template
                          # Description: System prompt with tool awareness
                          # Status: ALWAYS SET
                          # Content: Tool list + streaming-mode disclaimer

model_prompt: str        # Line 583-590, from build_model_prompt()
                         # Description: FINAL USER PROMPT for model
                         # Status: ALWAYS SET
                         # This is what gets passed to call_model_v2_stream
```

#### Stream Messages
```python
stream_messages: list    # Line 633-636, constructed
                         # Description: Message list for streamer
                         # Status: ALWAYS SET
                         # Structure: [
                         #   {"role": "system", "content": stream_system_prompt},
                         #   {"role": "user", "content": model_prompt}
                         # ]
```

---

## build_model_prompt INCLUDES

**Function:** `src/api/handlers/chat_handler.py`, lines 110-156

**Parameters Received:**
```python
text                  # User query
context_for_model     # File/node context
pinned_context        # Optional pinned files
history_context       # Optional chat history
viewport_summary      # Optional spatial awareness
json_context          # Optional JSON dependencies
```

**Final Prompt Assembly (line 147-156):**

The prompt is structured as:

```
1. Base instruction line:
   "You are a helpful AI assistant. Analyze the following context and answer the user's question."

2. context_for_model (ALWAYS PRESENT)
   - File content
   - Structure analysis
   - Metadata

3. json_section (conditional)
   - Only if json_context is non-empty
   - Already formatted with header

4. pinned_context (conditional)
   - Only if pinned_files exists
   - Formatted file snippets + references

5. spatial_section (conditional)
   - Only if viewport_summary is non-empty
   - Prefixed with "## 3D VIEWPORT CONTEXT"

6. history_context (conditional)
   - Previous messages formatted
   - Max 10 messages

7. Query section (ALWAYS PRESENT)
   - "## CURRENT USER QUESTION"
   - User's actual text

8. Closing instruction:
   "Provide a helpful, specific answer:"
```

**Assembly Order (lines 147-156):**
```python
return f"""You are a helpful AI assistant. Analyze the following context and answer the user's question.

{context_for_model}

{json_section}{pinned_context}{spatial_section}{history_context}## CURRENT USER QUESTION
{text}

---

Provide a helpful, specific answer:"""
```

---

## MISSING from stream prompt

**Not in model_prompt that COULD be pre-fetched:**

1. **Agent/Role Context**
   - No agent system message in user_prompt
   - System prompt added separately (MARKER_114.7)
   - Could pre-compute: role-specific instructions

2. **Tool Instructions Detail**
   - Basic tool list in stream_system_prompt (hard-coded)
   - Could enhance: tool parameters, examples, expected outputs
   - Current: Generic mention-ability + reference suggestion

3. **Client Session Context**
   - `sid` (session ID) used in json_context build only
   - Could enhance: session-specific settings, user preferences

4. **Chat Metadata**
   - `chat_id` computed but NOT in model_prompt
   - `request_timestamp` computed but NOT in model_prompt
   - `request_node_id` saved but NOT in model_prompt

5. **Model Provider Hints**
   - `detected_provider` computed AFTER prompt building
   - Could pre-compute provider-specific instructions

6. **Response Preferences**
   - No format/length specifications
   - Could include: response format hints, length targets

---

## SCOPE PURITY CHECK

**Variables SAFE to use before stream call:**
- ✅ `text` - input
- ✅ `node_path` - input
- ✅ `context_for_model` - computed (line 542-548)
- ✅ `pinned_files` - input
- ✅ `pinned_context` - computed (line 551-555)
- ✅ `viewport_context` - input
- ✅ `viewport_summary` - computed (line 558-559)
- ✅ `json_context` - computed (line 565-570)
- ✅ `history_context` - computed (line 531-532)
- ✅ `model_prompt` - computed (line 583-590)
- ✅ `stream_messages` - constructed (line 633-636)

**Variables that AFFECT stream call:**
- `requested_model` → affects `detected_provider`
- `model_source` → affects `detected_provider`
- `stream_system_prompt` → in `stream_messages[0]`
- `model_prompt` → in `stream_messages[1]`

---

## CRITICAL NOTES

1. **model_prompt is FULLY COMPOSED** before stream call
   - All context variables are resolved
   - No lazy loading during streaming
   - Final prompt is static from line 590 onward

2. **System prompt is SEPARATE** (line 622-631)
   - Not generated by `build_model_prompt()`
   - Hard-coded with tool awareness (MARKER_114.7)
   - Injected as `stream_messages[0]`

3. **Stream call is LEAN** (line 639-645)
   - Only passes: messages, model, provider, source, temperature
   - No context variables passed directly
   - All context pre-baked into `model_prompt`

4. **Scope cleanliness achieved**
   - No "clean_text" variable (uses `text` directly)
   - No separate content variable (uses `model_prompt`)
   - `build_model_prompt` is PURE FUNCTION (no side effects)

---

## USAGE PATTERNS FOR MCP INTEGRATION

**For MCP tools that need to understand context:**
```python
# Available at tool invocation time:
available_in_stream_scope = {
    "user_text": text,
    "node_path": node_path,
    "pinned_files": pinned_files,
    "viewport_context": viewport_context,
    "chat_id": chat_id,
    "session_id": sid,
    "model_used": requested_model,
    "provider": detected_provider,
}

# For smart tool suggestions:
context_for_tools = {
    "rich_context": rich_context,
    "context_for_model": context_for_model,
    "pinned_context": pinned_context,
    "history_context": history_context,
    "json_context": json_context,
}
```

