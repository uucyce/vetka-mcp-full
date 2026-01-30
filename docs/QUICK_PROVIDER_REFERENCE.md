# Quick Provider Systems Reference

## TL;DR - Which System to Use?

### For New Features → Use ProviderRegistry ✅
```python
from src.elisya.provider_registry import call_model_v2, Provider

# Simple call
result = await call_model_v2(
    messages=[{"role": "user", "content": "Hello"}],
    model="gpt-4",
    provider=Provider.OPENAI
)

# Or auto-detect provider from model name
result = await call_model_v2(
    messages=[...],
    model="x-ai/grok-4"  # Auto-routes to OpenRouter
)

# With tools
result = await call_model_v2(
    messages=[...],
    model="claude-3",
    provider=Provider.ANTHROPIC,
    tools=[{"name": "my_tool", ...}]
)

# Streaming
async for token in call_model_v2_stream(
    messages=[...],
    model="grok-4"
):
    print(token, end="", flush=True)
```

### For Streaming Legacy Code → Use api_aggregator_v3 ⚠️
```python
from src.elisya.api_aggregator_v3 import call_model_stream

async for token in call_model_stream(
    prompt="Tell me a story",
    model_name="ollama/deepseek-llm:7b"
):
    print(token, end="", flush=True)
```

### AVOID → api_gateway.py ❌
```python
# Don't use these - they're orphaned/legacy
from src.elisya.api_gateway import APIGateway  # ❌ NOT used
from src.elisya.api_gateway import _call_openrouter  # ❌ Sync stub
```

---

## Provider Routing

### Model Name → Provider Mapping

```python
# Auto-detection in ProviderRegistry.detect_provider()

# OpenAI
"gpt-4"              → Provider.OPENAI
"openai/gpt-4"       → Provider.OPENAI
"o1-preview"         → Provider.OPENAI

# Anthropic
"claude-3"           → Provider.ANTHROPIC
"anthropic/claude-3" → Provider.ANTHROPIC

# Google
"gemini-pro"         → Provider.GOOGLE
"google/gemini-pro"  → Provider.GOOGLE

# x.ai (IMPORTANT!)
"grok-4"             → Provider.XAI (direct API)
"x-ai/grok-4"        → Provider.OPENROUTER (via OpenRouter!)
"xai/grok-4"         → Provider.OPENROUTER (via OpenRouter!)

# OpenRouter
"deepseek/chat"      → Provider.OPENROUTER
"anthropic/claude-3" → Provider.ANTHROPIC (not OpenRouter)
(provider/model format with known provider → direct provider)
(provider/model with unknown provider → OPENROUTER)

# Ollama
"llama2"             → Provider.OLLAMA
"ollama/llama2"      → Provider.OLLAMA
"model:tag"          → Provider.OLLAMA (colon = Ollama)
```

---

## OpenRouter Integration

### Direct Usage
```python
from src.elisya.provider_registry import call_model_v2, Provider

# Explicit OpenRouter
result = await call_model_v2(
    messages=[...],
    model="deepseek/deepseek-chat",
    provider=Provider.OPENROUTER
)

# Or auto-detect
result = await call_model_v2(
    messages=[...],
    model="deepseek/deepseek-chat"  # Auto → OPENROUTER
)
```

### Key Features
- **Auto-rotation:** 24h cooldown on 401/402/403
- **Fallback:** XAI 403 → OpenRouter automatic
- **Streaming:** SSE support via `_stream_openrouter()`
- **Tools:** Limited (OpenRouter has limited tool support)

### Fallback Chain for Models

If direct provider fails:
```
Direct API call fails
    ↓
Automatic fallback to OpenRouter
    ↓
OpenRouter call with model format conversion
    (xai/grok-4 → x-ai/grok-4)
```

---

## Key Implementation Details

### ProviderRegistry Singleton
```python
from src.elisya.provider_registry import get_registry, ProviderRegistry

registry = get_registry()  # Get singleton
provider = registry.get(Provider.OPENAI)  # Get provider instance
result = await provider.call(...)  # Call provider
```

### Response Format (Standardized)
```python
{
    "message": {
        "content": "str response",
        "tool_calls": [...],  # or None
        "role": "assistant"
    },
    "model": "gpt-4",
    "provider": "openai",
    "usage": {"prompt_tokens": 10, "completion_tokens": 20}
}
```

### Error Handling
```python
from src.elisya.provider_registry import XaiKeysExhausted

try:
    result = await call_model_v2(...)
except XaiKeysExhausted:
    # All xai keys got 403, automatic fallback to OpenRouter
    print("Using OpenRouter fallback")
except ValueError as e:
    if "not found" in str(e):
        print("API key missing")
except httpx.HTTPStatusError as e:
    print(f"HTTP error: {e.response.status_code}")
```

---

## Current Usage in Handlers

### user_message_handler.py
```python
from src.elisya.provider_registry import call_model_v2, call_model_v2_stream

# Line 363: Direct model call
response = await call_model_v2(messages, model, provider)

# Line 537: Streaming
async for token in call_model_v2_stream(messages, model):
    yield token
```

### orchestrator_with_elisya.py
```python
from src.elisya.provider_registry import call_model_v2, ProviderRegistry

# Line 1023: Orchestrator uses call_model_v2
response = await call_model_v2(messages, model, provider)
```

### chat_handler.py
```python
from src.elisya.provider_registry import ProviderRegistry, Provider

# Direct registry access
registry = ProviderRegistry()
provider = registry.get(Provider.OPENAI)
```

---

## Migration Path

If you find code using old systems:

### From api_aggregator_v3.call_model → call_model_v2
```python
# OLD
result = await call_model(
    prompt="...",
    model_name="gpt-4",
    system_prompt="..."
)

# NEW
result = await call_model_v2(
    messages=[
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
    ],
    model="gpt-4",
    provider=Provider.OPENAI
)
```

### From api_gateway.APIGateway → ProviderRegistry
```python
# OLD
gateway = APIGateway()
result = gateway.call_model("task", "prompt")

# NEW
result = await call_model_v2(messages, model, provider)
```

---

## Provider Capabilities

| Provider | Tools | Streaming | Auto-rotate | Fallback |
|----------|-------|-----------|-------------|----------|
| ProviderRegistry | Varies* | ✅ SSE | ✅ 24h | ✅ OpenRouter |
| api_aggregator_v3 | Ollama only | ✅ Ollama | ⚠️ Basic | ⚠️ Ollama |
| api_gateway | Limited | ❌ | ⚠️ Basic | ❌ |

*Varies per provider: OpenAI/Anthropic/Google=✅, Others=❌

---

## File Structure

```
src/elisya/
├── provider_registry.py          ✅ PRODUCTION (use this)
│   ├── BaseProvider (ABC)
│   ├── OpenRouterProvider (impl)
│   ├── OpenAIProvider (impl)
│   ├── AnthropicProvider (impl)
│   ├── GoogleProvider (impl)
│   ├── OllamaProvider (impl)
│   ├── XaiProvider (impl)
│   ├── ProviderRegistry (singleton)
│   ├── call_model_v2() ← USE THIS
│   └── call_model_v2_stream()
│
├── api_aggregator_v3.py          ⚠️ LEGACY (streaming only)
│   ├── OpenRouterProvider (stub)
│   ├── APIAggregator (unused)
│   ├── call_model() (legacy)
│   └── call_model_stream()
│
└── api_gateway.py                ❌ ORPHANED
    ├── APIGateway (unused)
    ├── init_api_gateway() (stub)
    └── call_openai_direct() (only in api_aggregator_v3)
```

---

## Debug Helpers

### Check Provider Registry
```python
from src.elisya.provider_registry import get_registry

registry = get_registry()
providers = registry.list_providers()  # ['openai', 'anthropic', ...]

# Check specific provider
openai = registry.get(Provider.OPENAI)
print(f"OpenAI supports tools: {openai.supports_tools}")
```

### Check Model Detection
```python
from src.elisya.provider_registry import ProviderRegistry

model = "x-ai/grok-4"
provider = ProviderRegistry.detect_provider(model)
print(f"Model {model} → {provider.value}")  # Should be 'openrouter'
```

### Check Available Models (Ollama)
```python
from src.elisya.api_aggregator_v3 import OLLAMA_AVAILABLE_MODELS, HOST_HAS_OLLAMA

if HOST_HAS_OLLAMA:
    print(f"Available: {OLLAMA_AVAILABLE_MODELS}")
```

---

**Last Updated:** 2026-01-26
**Status:** ProviderRegistry is the canonical production system
