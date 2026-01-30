# PHASE 90.4.0: call_model Streaming to VETKA Chat - Reconnaissance

Date: 2026-01-23
Status: Investigation Complete
Complexity Estimate: MEDIUM (3-4 hours implementation)

# MARKER_90.4.0_START: call_model Stream Investigation

## Executive Summary

The `vetka_call_model` MCP tool currently returns **complete responses only** after the entire LLM call completes. No streaming to chat is implemented. The infrastructure exists to add streaming via Socket.IO events to the "Молния" group chat (ID: `5e2198c2-8b1a-45df-807f-5c73c5496aa8`), but `call_model_v2()` itself doesn't support streaming output.

### Current State
- **LLM Call Flow**: Synchronous blocking call to `call_model_v2()` → waits for complete response → returns dict → formats result
- **Chat Integration**: Result is only logged **after completion** via `log_to_group_chat()`
- **No Streaming**: Token-by-token output is NOT available from the tool

### What Exists
- ✅ Socket.IO emit infrastructure (used extensively in debug_routes.py, group_message_handler.py)
- ✅ Group chat message sending pattern: `POST /api/debug/mcp/groups/{group_id}/send`
- ✅ Socket events: `group_stream_start`, `group_stream_token` (not used), `group_stream_end`
- ✅ Request/response logging to group chat already works

### What's Missing
- ❌ Streaming support in `call_model_v2()`
- ❌ Token-level chunking in `LLMCallTool.execute()`
- ❌ Real-time emit of chunks to group chat during call
- ❌ Async wrapper around blocking call

---

## Current call_model Flow

### File: `/src/mcp/tools/llm_call_tool.py`

```python
def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Line 136-258"""

    # Flow:
    1. Validate inputs (lines 145-173)
    2. Detect provider from model name (line 181)
    3. Call call_model_v2() SYNCHRONOUSLY (lines 193-221)
       - If event loop running: use ThreadPoolExecutor
       - Else: use asyncio.run()
    4. Extract response (line 224)
    5. Build result dict (lines 229-237)
    6. Return COMPLETE response
```

**Key Issue**: Lines 193-221 block until the ENTIRE response is complete. No streaming.

### File: `/src/mcp/vetka_mcp_bridge.py`

**Tool Handler** (lines 754-765):
```python
elif name == "vetka_call_model":
    from src.mcp.tools.llm_call_tool import LLMCallTool
    tool = LLMCallTool()

    result = tool.execute(arguments)  # Blocking call
    return [TextContent(type="text", text=format_llm_result(result))]
```

**Request Logging** (lines 100-105):
```python
async def log_mcp_request(tool_name: str, arguments: dict, request_id: str):
    """Logs to group chat when tool starts"""
    await log_to_group_chat(f"🔧 **{tool_name}** ...", "chat")
```

**Response Logging** (lines 108-113):
```python
async def log_mcp_response(tool_name: str, result: dict, request_id: str, duration_ms: float, error: str = None):
    """Logs to group chat when tool finishes"""
    await log_to_group_chat(f"✅ **{tool_name}** done ({int(duration_ms)}ms)", "response")
```

**Key Issue**: Response is only logged AFTER completion (line 789). No streaming during the call.

---

## How Group Chat Streaming Already Works

### File: `/src/api/routes/debug_routes.py` (MCP Agents in Group Chat)

**Pattern for streaming to group** (lines 1142-1232, 1307-1396):

```python
@router.post("/mcp/groups/{group_id}/send")
async def send_group_message_from_mcp(...):
    """Send message to group as MCP agent"""

    # 1. Send initial message
    message = await manager.send_message(group_id, sender_id, content)

    # 2. Emit start event
    await socketio.emit('group_stream_start', {
        'id': msg_id,
        'group_id': group_id,
        'agent_id': agent_id,
        'model': model_id
    }, room=f'group_{group_id}')

    # 3. Get agent response
    result = await orchestrator.call_agent(...)
    response_text = result.get('output', '')

    # 4. Emit end event with full response
    await socketio.emit('group_stream_end', {
        'id': msg_id,
        'group_id': group_id,
        'agent_id': agent_id,
        'full_message': response_text,
        'metadata': {...}
    }, room=f'group_{group_id}')

    # 5. Store final message
    agent_message = await manager.send_message(group_id, agent_id, response_text)
    await socketio.emit('group_message', agent_message.to_dict(), room=room)
```

**Key Pattern**:
1. Emit `group_stream_start` (indicates streaming beginning)
2. Optionally emit `group_stream_token` for each chunk (not currently used)
3. Emit `group_stream_end` with full response text
4. Emit `group_message` with final stored message

**Socket.IO Access**:
```python
socketio = getattr(request.app.state, 'socketio', None)
if socketio:
    await socketio.emit('event_name', data, room=f'group_{group_id}')
```

---

## How to Add Streaming to call_model

### Approach: Two Phases

#### Phase 1: Chunk-Level Streaming (Without Token Streaming)
Start with what's available now - emit full response on completion.

**Changes Needed**:
1. **In `llm_call_tool.py`**: Modify `execute()` to:
   - Detect if we have SocketIO access
   - After getting response, emit chunks via Socket.IO

2. **Problem**: `LLMCallTool` is a standalone tool - it doesn't have Socket.IO reference

3. **Solution**: Pass SocketIO reference through context or use a callback pattern

#### Phase 2: Full Token Streaming (With Provider Support)
If `call_model_v2()` can return streaming response.

**Check**: Does `call_model_v2()` support async generators or streaming?
- If YES: Modify execute() to iterate and emit each token
- If NO: Add streaming wrapper around provider calls

---

## Socket Event to Use

### For call_model Streaming to Chat "Молния"

**Group ID**: `5e2198c2-8b1a-45df-807f-5c73c5496aa8`
**Events**: Already standardized in group handlers

```python
# When call_model starts
await socketio.emit('group_stream_start', {
    'id': '<unique_msg_id>',
    'group_id': '5e2198c2-8b1a-45df-807f-5c73c5496aa8',
    'agent_id': 'claude_mcp',  # or similar
    'model': arguments['model']  # e.g., 'grok-4'
}, room='group_5e2198c2-8b1a-45df-807f-5c73c5496aa8')

# When tokens/chunks arrive (optional, advanced)
await socketio.emit('group_stream_token', {
    'id': msg_id,
    'group_id': '5e2198c2-8b1a-45df-807f-5c73c5496aa8',
    'token': '<chunk_text>',
    'delta': token_count
}, room=room)

# When response completes
await socketio.emit('group_stream_end', {
    'id': msg_id,
    'group_id': '5e2198c2-8b1a-45df-807f-5c73c5496aa8',
    'agent_id': 'claude_mcp',
    'full_message': response_content,
    'metadata': {
        'model': model_id,
        'provider': provider_name,
        'tokens': usage_stats
    }
}, room=room)
```

---

## Implementation Roadmap

### Step 1: Modify llm_call_tool.py
- Accept optional `socketio` parameter in `execute()`
- Emit `group_stream_start` before calling `call_model_v2()`
- Collect response
- Emit `group_stream_end` after response completes
- Total: ~20 lines added

### Step 2: Modify vetka_mcp_bridge.py
- Pass SocketIO reference from `request.app.state` to tool
- Wrap tool execution with streaming context
- Total: ~15 lines added

### Step 3: Test Integration
- Call `vetka_call_model` from MCP
- Verify events appear in Socket.IO logs
- Verify messages appear in Молния group chat

### Step 4: (Optional) Add Token Streaming
- Only if `call_model_v2()` supports streaming
- Emit `group_stream_token` for each chunk
- Frontend accumulates tokens into single message

---

## Key Files to Modify

| File | Lines | Changes |
|------|-------|---------|
| `src/mcp/tools/llm_call_tool.py` | 136-258 | Add socketio param, emit start/end |
| `src/mcp/vetka_mcp_bridge.py` | 754-765, 100-113 | Pass socketio to tool, enhance logging |
| `src/services/group_chat_manager.py` | 562-620 | NO CHANGE (already supports sends) |

---

## Complexity Assessment

### Estimated Effort

| Component | Hours | Risk | Notes |
|-----------|-------|------|-------|
| **Modify LLMCallTool** | 1.0 | LOW | Straightforward parameter passing |
| **Get SocketIO Reference** | 0.5 | LOW | Pattern exists in debug_routes.py |
| **Emit Start/End Events** | 0.5 | LOW | Events standardized across codebase |
| **Testing** | 1.0 | MEDIUM | Need to verify Socket.IO delivery |
| **Optional: Token Streaming** | 2.0 | HIGH | Depends on provider_registry capability |

**Total (Basic)**: 3.0 hours
**Total (With Token Streaming)**: 5.0 hours

### Risk Factors

1. **SocketIO Availability**: May not be available if called from CLI-only context
   - Mitigation: Make socketio optional, graceful fallback to logging

2. **Event Loop Issues**: `call_model_v2()` handling mixed event loops
   - Already handled in current code (ThreadPoolExecutor logic)
   - Should not break with streaming

3. **Provider Support**: Some LLM providers may not stream
   - Mitigation: Start with completion-based emit, add streaming later

---

## References

**Existing Streaming Patterns**:
- Group chat streaming: `src/api/routes/debug_routes.py` lines 1307-1396
- Token streaming infrastructure: `src/api/handlers/streaming_handler.py`
- Socket events: Search for `group_stream_start` in codebase

**MCP Logging Currently**:
- Request: `src/mcp/vetka_mcp_bridge.py` lines 100-105
- Response: `src/mcp/vetka_mcp_bridge.py` lines 108-113

**Socket.IO Access Pattern**:
```python
socketio = getattr(request.app.state, 'socketio', None)
# OR (from MCP context)
socketio = getattr(app.state, 'socketio', None)  # May be None in MCP
```

---

# MARKER_90.4.0_END

## Summary for Implementation

**What exists**: ✅ Socket.IO infrastructure, ✅ group chat patterns, ✅ message storage
**What's missing**: ❌ Streaming calls from llm_call_tool.py, ❌ Socket.IO reference passing
**How to add**: Pass socketio from bridge → emit start/end events from tool execute()
**Complexity**: MEDIUM - 3 hours basic, 5 hours with token streaming
**Risk**: LOW if we make socketio optional (graceful fallback to logging)

**Next Steps**:
1. Create async wrapper in llm_call_tool to emit events
2. Pass socketio from vetka_mcp_bridge to tool
3. Add event emission around call_model_v2() call
4. Test with MCP tool invocation
