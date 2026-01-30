# Phase 80.10: Provider Registry Architecture

## Problem Statement

In group chats, models were not being called by their correct providers. When a user assigned `openai/gpt-4o` to the Architect role, Ollama was responding instead because:

1. `call_model()` in `api_aggregator_v3.py` had complex routing logic
2. Provider detection was scattered and inconsistent
3. `orchestrator.call_agent()` didn't pass explicit provider
4. When tools were involved, everything defaulted to Ollama

## Solution: Provider Registry Pattern

Based on ChatGPT's architectural recommendation:

> "Orchestrator выбирает provider. call_model только вызывает provider."

### Key Principle

**Separation of Concerns:**
- Orchestrator decides WHICH provider to use
- Provider Registry only EXECUTES the call
- No routing logic in `call_model_v2()`

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Orchestrator                         │
│  - Extracts provider from model_id                      │
│  - Passes Provider enum to call_model_v2()              │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  ProviderRegistry                       │
│  - Singleton with registered providers                  │
│  - get(Provider.OPENAI) → OpenAIProvider               │
│  - No routing logic, just lookup                        │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    OpenAIProvider  AnthropicProvider  OllamaProvider
    - supports_tools: True
    - Native API call
    - Standardized response
```

## New Files

### `src/elisya/provider_registry.py`

```python
class Provider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"

class BaseProvider(ABC):
    @property
    def supports_tools(self) -> bool: ...
    async def call(self, messages, model, tools=None) -> Dict: ...

class ProviderRegistry:
    def register(provider_type: Provider, provider: BaseProvider): ...
    def get(provider_type: Provider) -> BaseProvider: ...
    @staticmethod
    def detect_provider(model_name: str) -> Provider: ...

async def call_model_v2(
    messages: List[Dict],
    model: str,
    provider: Provider = None,  # Explicit provider!
    tools: List[Dict] = None
) -> Dict[str, Any]: ...
```

## Changes to Orchestrator

### `src/orchestration/orchestrator_with_elisya.py`

```python
# New imports
from src.elisya.provider_registry import (
    call_model_v2,
    Provider,
    ProviderRegistry,
    get_registry
)

# In _run_agent_with_elisya():
provider_str = routing.get('provider', 'ollama')
provider_enum = Provider(provider_str.lower())

llm_response = await self._call_llm_with_tools_loop(
    prompt=prompt,
    agent_type=agent_type,
    model=model_name,
    system_prompt=system_prompt,
    provider=provider_enum  # NEW: Explicit provider
)

# In _call_llm_with_tools_loop():
response = await call_model_v2(
    messages=messages,
    model=model,
    provider=provider,  # Passed from orchestrator
    tools=tool_schemas
)
```

## Provider Detection Rules

| Model Format | Provider |
|-------------|----------|
| `openai/gpt-4o`, `gpt-4` | OPENAI |
| `anthropic/claude-3`, `claude-3` | ANTHROPIC |
| `google/gemini-pro`, `gemini` | GOOGLE |
| `qwen2:7b`, `llama3:8b` (with `:`) | OLLAMA |
| `meta-llama/llama-3.1` (with `/`) | OPENROUTER |

## Tool Support by Provider

| Provider | Native Tools |
|----------|--------------|
| OpenAI | ✅ Yes |
| Anthropic | ✅ Yes |
| Google | ✅ Yes |
| Ollama | ✅ Yes |
| OpenRouter | ❌ No (limited) |

## Message Flow

1. User creates group with `openai/gpt-4o` as Architect
2. Frontend sends `model_id: "openai/gpt-4o"` in participant data
3. `group_message_handler.py` calls `orchestrator.call_agent(model_id="openai/gpt-4o")`
4. Orchestrator extracts provider: `openai` from model_id
5. Orchestrator calls `_call_llm_with_tools_loop(provider=Provider.OPENAI)`
6. `call_model_v2()` gets OpenAIProvider from registry
7. OpenAIProvider makes native API call with tools
8. Response returned to group chat

## Response Format

All providers return standardized format:

```python
{
    "message": {
        "content": "Response text",
        "tool_calls": [...] or None,
        "role": "assistant"
    },
    "model": "gpt-4o",
    "provider": "openai",
    "usage": {"prompt_tokens": N, "completion_tokens": M}
}
```

## Testing

```bash
# 1. Create group with GPT model
curl -X POST http://localhost:3000/api/groups \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","admin_agent_id":"@Architect","admin_model_id":"openai/gpt-4o","admin_display_name":"Architect (GPT 4o)"}'

# 2. Send message - should use OpenAI, not Ollama
curl -X POST http://localhost:3000/api/groups/{id}/messages \
  -H "Content-Type: application/json" \
  -d '{"sender_id":"user","content":"Hello"}'

# Expected log:
# [GROUP] Calling agent @Architect (openai/gpt-4o) via orchestrator as Architect...
# 🌐 Using provider: openai for model: openai/gpt-4o
# [OPENAI] Calling gpt-4o (tools: 3)
# [OPENAI] ✅ Completed in 2.1s
```

## Benefits

1. **Clean separation** - Orchestrator selects, Registry executes
2. **Explicit provider** - No guessing, provider passed as parameter
3. **Native tools** - OpenAI/Anthropic/Google use their native tool APIs
4. **Standardized responses** - All providers return same format
5. **Extensible** - Easy to add new providers (Groq, xAI, etc.)

## Migration Path

- Old `call_model()` kept as `call_model_legacy` for backwards compatibility
- New code uses `call_model_v2()` with explicit provider
- Gradual migration: update callers one by one
