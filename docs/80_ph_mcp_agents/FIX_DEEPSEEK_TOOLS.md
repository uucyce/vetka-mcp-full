# Phase 80.5: Fix Deepseek Tool Support Error

## Problem
```
Error in Dev LLM/Tool execution: registry.ollama.ai/library/deepseek-llm:7b does not support tools (status code: 400)
```

### Root Cause
Deepseek 7B is a lightweight model without native tool calling support. The code was attempting to pass `tools=tools` parameter to Ollama for all models, causing the API to reject the request.

## Solution
Implemented a **model capability detection system** with graceful fallback:

### 1. Model Blacklist (`provider_registry.py`)
Created list of models without tool support:
```python
MODELS_WITHOUT_TOOLS = {
    'deepseek-llm',      # Deepseek 7B lightweight
    'llama2',            # Legacy Llama 2
    'codellama',         # CodeLlama base
    'mistral',           # Mistral 7B base
    'phi',               # Microsoft Phi models
    'gemma',             # Google Gemma base
    'orca-mini',         # Orca lightweight
    'vicuna',            # Vicuna base
}
```

### 2. Pre-call Detection
Added `_model_supports_tools()` method:
```python
def _model_supports_tools(self, model_name: str) -> bool:
    base_name = model_name.split(':')[0].lower()
    for unsupported in self.MODELS_WITHOUT_TOOLS:
        if unsupported in base_name:
            return False
    return True
```

### 3. Conditional Tool Parameter
Modified `OllamaProvider.call()`:
```python
model_has_tools = self._model_supports_tools(clean_model)
effective_tools = tools if (tools and model_has_tools) else None

if tools and not model_has_tools:
    print(f"[OLLAMA] ⚠️  {clean_model} does not support tools - calling without tools")
```

### 4. Fallback Error Handling
Added try/catch for edge cases:
```python
try:
    response = await loop.run_in_executor(None, lambda: ollama.chat(**params))
except Exception as e:
    if 'does not support tools' in str(e) and 'tools' in params:
        print(f"[OLLAMA] Tool error detected, retrying {clean_model} without tools")
        del params['tools']
        response = await loop.run_in_executor(None, lambda: ollama.chat(**params))
    else:
        raise
```

## Files Modified

### 1. `/src/elisya/provider_registry.py`
- Added `MODELS_WITHOUT_TOOLS` class constant
- Added `_model_supports_tools()` method
- Modified `call()` to check tool support before adding tools parameter
- Added try/catch fallback for unexpected tool errors

### 2. `/src/api/handlers/chat_handler.py`
- Added same blacklist to `call_ollama_model()` function
- Added pre-call detection with warning message
- Added try/catch fallback for tool errors

## Behavior

### Before Fix
```
User: "Show me main.py"
→ Ollama call with tools=[ camera_focus, search_semantic, get_tree_context ]
→ ERROR: registry.ollama.ai/library/deepseek-llm:7b does not support tools (status code: 400)
→ Workflow fails
```

### After Fix
```
User: "Show me main.py"
→ Detect: deepseek-llm is in MODELS_WITHOUT_TOOLS
→ Log: "[OLLAMA] ⚠️  deepseek-llm:7b does not support tools - calling without tools"
→ Ollama call WITHOUT tools parameter
→ Response: "Here's main.py content..." (text-based response, no tool calls)
→ Workflow succeeds
```

## Trade-offs

### Advantages
- No workflow failures for lightweight models
- Automatic detection - no manual configuration needed
- Graceful degradation - still gets LLM response
- Fallback error handling for unknown cases

### Disadvantages
- Tool-dependent features won't work with these models
- No camera_focus, search_semantic calls from lightweight models
- Users might not know why tools aren't working

## Future Improvements

### Option A: Dynamic Detection
Query Ollama API for model capabilities:
```python
async def _get_model_info(model: str) -> Dict:
    """Fetch model metadata from Ollama"""
    resp = await ollama.show(model)
    return resp.get('capabilities', {})
```

### Option B: User Warning
Emit warning to frontend when tool-less model is selected:
```python
await sio.emit('model_limitation_warning', {
    'model': model_name,
    'message': 'This model does not support tool calling. Camera navigation and search tools will be unavailable.'
})
```

### Option C: Auto-routing
Automatically route tool-requiring queries to tool-capable models:
```python
if tools_required and not model_supports_tools:
    print(f"Routing to tool-capable model: qwen2.5:14b")
    model_name = 'qwen2.5:14b'
```

## Testing

### Manual Test
1. Start VETKA with deepseek-llm:7b as Dev agent
2. Send: "Show me the main.py file"
3. Verify: No error, text response instead of tool call
4. Check logs: Should see "does not support tools - calling without tools"

### Regression Test
1. Use qwen2.5:14b (supports tools)
2. Send: "Show me the main.py file"
3. Verify: Tool call executed, camera focuses on file

## Status
✅ **FIXED** - Both provider_registry.py and chat_handler.py updated
✅ **TESTED** - Deepseek no longer throws 400 errors
✅ **DOCUMENTED** - This file

## Related Issues
- Phase 80.11: Pinned Files Audit (original bug report)
- Phase 22: Tool execution system
- Phase 60: LangGraph orchestration

<!-- MARKER: SONNET_FIX_TASK_5_COMPLETE -->
