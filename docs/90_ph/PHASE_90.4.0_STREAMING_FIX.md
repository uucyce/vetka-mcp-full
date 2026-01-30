# Phase 90.4.0: Add call_model Streaming to VETKA Chat

**Status:** ✅ COMPLETE
**Date:** 2026-01-23
**Implemented by:** Sonnet 4.5

---

## Overview

When `vetka_call_model` MCP tool is invoked, it now streams both the request and response to the VETKA chat "Молния" (Lightning) for visibility and debugging.

**Chat ID:** `5e2198c2-8b1a-45df-807f-5c73c5496aa8`

---

## Implementation

### File Modified

**`src/mcp/tools/llm_call_tool.py`**

### Changes Made

#### 1. Added Chat ID Constant
```python
# MARKER_90.4.0_START: VETKA chat ID for call_model streaming
LIGHTNING_CHAT_ID = "5e2198c2-8b1a-45df-807f-5c73c5496aa8"  # "Молния" group
# MARKER_90.4.0_END
```

#### 2. Added Helper Methods

**`_emit_to_chat(sender_id, content, message_type)`**
- Core method for emitting messages to VETKA chat
- Gets socketio instance via `get_socketio()` from `components_init`
- Handles async event loop gracefully
- Emits to room: `group_{LIGHTNING_CHAT_ID}`
- Socket event: `group_message`

**`_emit_request_to_chat(model, messages, temperature, max_tokens)`**
- Formats and emits the LLM request
- Shows model name, parameters, and message preview (truncated to 200 chars)
- Sender: `@user`
- Message type: `system`

**`_emit_response_to_chat(model, content, usage)`**
- Formats and emits the LLM response
- Includes token usage statistics if available
- Sender: `@{model}` (e.g., `@grok-4`, `@gpt-4o`)
- Message type: `response`

#### 3. Integrated into Execute Flow

```python
# Before calling model
self._emit_request_to_chat(model, messages, temperature, max_tokens)

# After receiving response
self._emit_response_to_chat(model, content, result.get('usage'))
```

---

## Socket Events Used

### Event: `group_message`

**Room:** `group_{group_id}`
**Data format:**
```python
{
    'group_id': '5e2198c2-8b1a-45df-807f-5c73c5496aa8',
    'sender_id': '@grok-4',  # or '@user'
    'content': 'Response text...',
    'message_type': 'response',  # or 'system', 'chat'
    'timestamp': '2026-01-23T10:30:00',
    'metadata': {
        'source': 'vetka_call_model',
        'mcp_tool': True
    }
}
```

---

## Example Output in Chat

### Request Message (from @user)
```
[MCP call_model] grok-4
Temperature: 0.7, Max tokens: 4096
```
Explain the concept of spatial intelligence in AI systems...
```
```

### Response Message (from @grok-4)
```
Spatial intelligence in AI refers to...

*Tokens: 45 → 287 (total: 332)*
```

---

## Architecture Notes

### SocketIO Access
- Uses `get_socketio()` from `src.initialization.components_init`
- SocketIO instance stored globally in `_socketio` after `initialize_all_components()`
- Gracefully handles cases where socketio is not available (e.g., MCP bridge mode)

### Async Handling
- Detects if event loop is running
- Uses `asyncio.create_task()` if loop is running
- Falls back to `asyncio.run()` if no loop
- Silently fails if async operations not possible (logs debug message)

### Message Flow
```
MCP Client (Claude Code)
    ↓ (calls vetka_call_model)
LLMCallTool.execute()
    ↓ (emits request)
SocketIO → group_5e2198c2... → VETKA UI
    ↓ (calls provider)
Provider API (Grok, GPT, etc.)
    ↓ (returns response)
LLMCallTool.execute()
    ↓ (emits response)
SocketIO → group_5e2198c2... → VETKA UI
```

---

## How to Verify in UI

1. **Start VETKA server:**
   ```bash
   python main.py
   ```

2. **Open VETKA UI:**
   ```bash
   cd client && npm run dev
   ```

3. **Navigate to "Молния" group chat**
   - Group ID: `5e2198c2-8b1a-45df-807f-5c73c5496aa8`

4. **Use MCP tool from Claude Code:**
   ```bash
   # In Claude Code, call:
   vetka_call_model(
       model="grok-4",
       messages=[{"role": "user", "content": "Hello!"}]
   )
   ```

5. **Observe in UI:**
   - Request message appears from `@user`
   - Response message appears from `@grok-4`
   - Token usage shown in response

---

## Markers Used

All changes marked with:
```python
# MARKER_90.4.0_START
...
# MARKER_90.4.0_END
```

This allows easy identification and rollback if needed.

---

## Related Files

- **`src/mcp/tools/llm_call_tool.py`** - Main implementation
- **`src/initialization/components_init.py`** - SocketIO singleton access
- **`src/api/routes/debug_routes.py:1142-1232`** - Group message pattern reference
- **`main.py`** - SocketIO instance creation and storage

---

## Future Enhancements

### Option B: Real-time Token Streaming
For future phases, could implement actual token-by-token streaming:
```python
# Emit stream_start
socketio.emit('group_stream_start', {...})

# Emit tokens as they arrive
for token in stream:
    socketio.emit('group_stream_token', {'token': token, ...})

# Emit stream_end
socketio.emit('group_stream_end', {...})
```

This would require modifying `call_model_v2()` to support streaming responses.

---

## Testing

### Manual Test
```python
# From Claude Code MCP console
tool: vetka_call_model
args: {
    "model": "grok-4",
    "messages": [
        {"role": "user", "content": "What is 2+2?"}
    ]
}
```

**Expected:**
1. Message appears in "Молния" chat from `@user` showing request
2. Message appears from `@grok-4` showing "The answer is 4" (or similar)
3. Token usage displayed in response

### Error Cases Handled
- SocketIO not available → logs debug message, continues execution
- No event loop → falls back gracefully
- Async emit fails → logs warning, continues execution

All errors are non-fatal and don't break the tool functionality.

---

## Conclusion

The implementation provides visibility into MCP tool LLM calls directly in the VETKA UI, enabling better debugging and monitoring of agent interactions without requiring separate console logs.
