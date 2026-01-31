# call_model Quick Reference Guide

**Purpose:** Developer reference for migrating from legacy `call_model()` to canonical `call_model_v2()`

---

## TL;DR - What Should I Use?

```python
# ✅ ALWAYS USE THIS:
from src.elisya.provider_registry import call_model_v2, Provider

response = await call_model_v2(
    messages=[{"role": "user", "content": "Your prompt"}],
    model="grok-4",
    provider=Provider.XAI,  # Optional - auto-detected if omitted
    tools=[...],  # Optional
    temperature=0.7
)

# ❌ DON'T USE THESE (deprecated):
# from src.elisya.api_aggregator_v3 import call_model
# from src.api.handlers.models.model_client import ModelClient
```

---

## Signature Comparison

### OLD: `api_aggregator_v3.call_model()`

```python
async def call_model(
    prompt: str,                                    # ❌ String prompt
    model_name: str = None,
    system_prompt: str = "You are a helpful assistant.",  # ❌ Separate system
    tools: Optional[List[Dict]] = None,
    **kwargs,
) -> Any:                                          # ❌ Untyped return
```

### NEW: `provider_registry.call_model_v2()`

```python
async def call_model_v2(
    messages: List[Dict[str, str]],                # ✅ Messages format
    model: str,
    provider: Optional[Provider] = None,           # ✅ Explicit provider
    tools: Optional[List[Dict]] = None,
    **kwargs,
) -> Dict[str, Any]:                               # ✅ Typed dict return
```

---

## Migration Examples

### Example 1: Simple Prompt

**OLD:**
```python
from src.elisya.api_aggregator_v3 import call_model

response = await call_model(
    prompt="What is the weather?",
    model_name="grok-4",
    system_prompt="You are a weather assistant."
)
```

**NEW:**
```python
from src.elisya.provider_registry import call_model_v2, Provider

response = await call_model_v2(
    messages=[
        {"role": "system", "content": "You are a weather assistant."},
        {"role": "user", "content": "What is the weather?"}
    ],
    model="grok-4",
    provider=Provider.XAI  # Optional - auto-detected
)
```

---

### Example 2: Ollama Local Model

**OLD:**
```python
from src.elisya.api_aggregator_v3 import call_model

response = await call_model(
    prompt="Explain async/await",
    model_name="qwen2.5:7b"
)
```

**NEW:**
```python
from src.elisya.provider_registry import call_model_v2, Provider

response = await call_model_v2(
    messages=[{"role": "user", "content": "Explain async/await"}],
    model="qwen2.5:7b",
    provider=Provider.OLLAMA  # Auto-detected from model name
)
```

---

### Example 3: Tool Calling

**OLD:**
```python
from src.elisya.api_aggregator_v3 import call_model

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather",
            "parameters": {...}
        }
    }
]

response = await call_model(
    prompt="What's the weather in Paris?",
    model_name="gpt-4o",
    tools=tools
)
```

**NEW:**
```python
from src.elisya.provider_registry import call_model_v2, Provider

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather",
            "parameters": {...}
        }
    }
]

response = await call_model_v2(
    messages=[{"role": "user", "content": "What's the weather in Paris?"}],
    model="gpt-4o",
    provider=Provider.OPENAI,
    tools=tools
)

# Check if tool was called
if response.get("message", {}).get("tool_calls"):
    tool_calls = response["message"]["tool_calls"]
    # Handle tool execution...
```

---

### Example 4: Socket.IO Streaming

**OLD:**
```python
from src.api.handlers.models.model_client import ModelClient

model_client = ModelClient(sio, context_builder)

response = await model_client.call_model(
    model_name="anthropic/claude-3-haiku",
    prompt="Write a poem",
    session_id="session-123",
    node_id="node-456",
    node_path="/path/to/file.py",
    streaming=True
)
```

**NEW (with adapter):**
```python
from src.elisya.provider_registry import call_model_v2, Provider

# Emit stream_start event manually
await sio.emit("stream_start", {
    "id": msg_id,
    "agent": "Claude",
    "model": "claude-3-haiku"
}, to=session_id)

# Call canonical implementation
response = await call_model_v2(
    messages=[{"role": "user", "content": "Write a poem"}],
    model="claude-3-haiku",
    provider=Provider.ANTHROPIC
)

# Emit stream_end event
await sio.emit("stream_end", {
    "id": msg_id,
    "full_message": response["message"]["content"],
    "metadata": {...}
}, to=session_id)
```

**NEW (using SocketIOModelClient wrapper - Phase 2):**
```python
from src.api.handlers.models.socketio_model_client import SocketIOModelClient

client = SocketIOModelClient(sio)
response = await client.call_model(
    messages=[{"role": "user", "content": "Write a poem"}],
    model="claude-3-haiku",
    session_id="session-123"
)
# Wrapper handles stream events automatically
```

---

## Response Format Comparison

### OLD: `api_aggregator_v3.call_model()`

```python
# Ollama response
{
    "message": {
        "content": "Response text here",
        "tool_calls": [...]  # If tools were used
    },
    "model": "qwen2.5:7b",
    "done": True
}

# OpenRouter response
{
    "message": {
        "content": "Response text here"
    }
}
```

### NEW: `call_model_v2()`

```python
# Standardized response for ALL providers
{
    "message": {
        "content": "Response text here",
        "tool_calls": [...]  # If tools were used
    },
    "model": "grok-4",
    "provider": "xai",
    "usage": {
        "prompt_tokens": 123,
        "completion_tokens": 456,
        "total_tokens": 579
    }
}
```

---

## Provider Auto-Detection

You don't need to specify `provider` - it's auto-detected from model name:

```python
# Model name patterns that auto-detect provider:

# XAI/Grok
"grok-4"           → Provider.XAI
"grok-beta"        → Provider.XAI
"xai/grok-4"       → Provider.XAI

# OpenAI
"gpt-4o"           → Provider.OPENAI
"gpt-4-turbo"      → Provider.OPENAI
"openai/gpt-4o"    → Provider.OPENAI

# Anthropic
"claude-opus-4-5"  → Provider.ANTHROPIC
"claude-sonnet-4"  → Provider.ANTHROPIC
"anthropic/claude" → Provider.ANTHROPIC

# Google
"gemini-2.0-flash" → Provider.GOOGLE
"gemini-1.5-pro"   → Provider.GOOGLE
"google/gemini"    → Provider.GOOGLE

# Ollama (local)
"qwen2.5:7b"       → Provider.OLLAMA
"deepseek-llm:7b"  → Provider.OLLAMA
"llama3.1:8b"      → Provider.OLLAMA

# OpenRouter (fallback)
"mistralai/..."    → Provider.OPENROUTER
"meta-llama/..."   → Provider.OPENROUTER
```

---

## Error Handling

### OLD: Inconsistent errors

```python
try:
    response = await call_model(prompt="...", model_name="grok-4")
except Exception as e:
    # Different error types from different providers
    # No consistent error handling
    pass
```

### NEW: Consistent error handling + automatic fallbacks

```python
from src.elisya.provider_registry import call_model_v2, Provider, XaiKeysExhausted

try:
    response = await call_model_v2(
        messages=[{"role": "user", "content": "..."}],
        model="grok-4",
        provider=Provider.XAI
    )
except XaiKeysExhausted:
    # All XAI keys got 403 - already fell back to OpenRouter
    # Response is from OpenRouter fallback
    pass
except httpx.HTTPStatusError as e:
    if e.response.status_code == 429:
        # Rate limited - already tried fallback
        pass
    elif e.response.status_code in [401, 402]:
        # Auth/payment error - already tried fallback
        pass
except ValueError as e:
    # API key not found - already tried fallback
    pass
```

**Automatic Fallbacks:**

1. XAI 403 → OpenRouter (with model name conversion: `grok-4` → `x-ai/grok-4`)
2. Direct API 401/402 → OpenRouter
3. Direct API 404 → OpenRouter (model not found)
4. Direct API 429 → OpenRouter (rate limit)

---

## Tool Support Matrix

| Provider    | Tools Supported | Notes |
|-------------|----------------|-------|
| OPENAI      | ✅ Yes         | Native tool calling |
| ANTHROPIC   | ✅ Yes         | Native tool calling |
| GOOGLE      | ✅ Yes         | Native tool calling |
| XAI         | ✅ Yes         | Native tool calling |
| OLLAMA      | ✅ Yes         | Local tool calling |
| OPENROUTER  | ❌ No          | Tools ignored |

**call_model_v2() automatically:**
- Validates tool support per provider
- Ignores tools if provider doesn't support them
- Logs warning when tools are ignored

---

## Streaming Support

### Non-streaming (default)

```python
response = await call_model_v2(
    messages=[{"role": "user", "content": "..."}],
    model="grok-4"
)
# Returns complete response after generation
```

### Streaming

```python
from src.elisya.provider_registry import call_model_v2_stream

async for token in call_model_v2_stream(
    messages=[{"role": "user", "content": "..."}],
    model="grok-4"
):
    print(token, end="", flush=True)
    # Emit to Socket.IO, etc.
```

---

## Common Mistakes

### ❌ Mistake 1: Using old import

```python
from src.elisya.api_aggregator_v3 import call_model  # Wrong!
```

**Fix:**
```python
from src.elisya.provider_registry import call_model_v2  # Correct!
```

---

### ❌ Mistake 2: Passing string prompt instead of messages

```python
response = await call_model_v2(
    prompt="What is 2+2?",  # Wrong! This parameter doesn't exist
    model="grok-4"
)
```

**Fix:**
```python
response = await call_model_v2(
    messages=[{"role": "user", "content": "What is 2+2?"}],  # Correct!
    model="grok-4"
)
```

---

### ❌ Mistake 3: Not handling message format in response

```python
response = await call_model_v2(...)
text = response["content"]  # Wrong! No direct "content" key
```

**Fix:**
```python
response = await call_model_v2(...)
text = response["message"]["content"]  # Correct!
# Or use helper:
text = response.get("message", {}).get("content", "")
```

---

### ❌ Mistake 4: Hardcoding provider when not needed

```python
response = await call_model_v2(
    messages=[...],
    model="qwen2.5:7b",
    provider=Provider.OLLAMA  # Unnecessary - auto-detected
)
```

**Fix:**
```python
response = await call_model_v2(
    messages=[...],
    model="qwen2.5:7b"  # Provider auto-detected from ":7b" pattern
)
```

---

## Checklist for Migration

- [ ] Replace `from src.elisya.api_aggregator_v3 import call_model`
- [ ] Replace `from src.api.handlers.models.model_client import ModelClient`
- [ ] Convert `prompt` string to `messages` list format
- [ ] Merge `system_prompt` into messages with `role: "system"`
- [ ] Update response access from `response["content"]` to `response["message"]["content"]`
- [ ] Add provider enum (optional but recommended)
- [ ] Update error handling to catch new exceptions
- [ ] Test with actual LLM calls (Ollama, OpenRouter, direct APIs)
- [ ] Update unit tests
- [ ] Remove deprecated imports

---

## Testing

```python
import pytest
from src.elisya.provider_registry import call_model_v2, Provider

@pytest.mark.asyncio
async def test_grok_call():
    """Test XAI Grok call with auto-fallback"""
    response = await call_model_v2(
        messages=[{"role": "user", "content": "Say 'test' and nothing else"}],
        model="grok-4"
    )

    assert response["success"] is True  # If XAI fails, falls back to OpenRouter
    assert "test" in response["message"]["content"].lower()
    assert response["model"] in ["grok-4", "x-ai/grok-4"]  # Depends on provider used

@pytest.mark.asyncio
async def test_ollama_call():
    """Test Ollama local model"""
    response = await call_model_v2(
        messages=[{"role": "user", "content": "Reply with 'hello'"}],
        model="qwen2.5:7b",
        provider=Provider.OLLAMA
    )

    assert response["provider"] == "ollama"
    assert "hello" in response["message"]["content"].lower()
```

---

## FAQ

**Q: Do I need to update all my code at once?**
A: No. Phase 1 creates adapters, so old code continues working with deprecation warnings.

**Q: What if I need Socket.IO streaming events?**
A: Use `SocketIOModelClient` wrapper (Phase 2) or emit events manually around `call_model_v2()`.

**Q: Can I still use Ollama directly?**
A: Yes, but go through `call_model_v2()` with `provider=Provider.OLLAMA` for consistency.

**Q: What about tool calling?**
A: Fully supported in `call_model_v2()` with automatic provider validation.

**Q: What if a provider is down?**
A: `call_model_v2()` automatically falls back to OpenRouter on errors (401/402/403/404/429).

**Q: How do I know which provider was actually used?**
A: Check `response["provider"]` in the response dict.

---

## Support

- **Migration issues:** Check `/docs/103_ph/call_model_consolidation_plan.md`
- **Flow diagrams:** Check `/docs/103_ph/call_model_flow_diagram.txt`
- **Provider docs:** Check `/docs/QUICK_PROVIDER_REFERENCE.md`
- **MCP tools:** Check `/docs/95_ph/MCP_TOOLS_MARKERS.md`

---

**Last Updated:** 2026-01-31
**Author:** Haiku 1 (Audit Agent)
**Phase:** 103
