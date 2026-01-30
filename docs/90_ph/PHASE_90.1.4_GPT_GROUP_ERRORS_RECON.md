# MARKER_90.1.4_START: GPT Group Chat Errors - Rate Limiting & Routing Reconnaissance

## Executive Summary
Investigation reveals critical difference between GROUP and SOLO chat model routing that causes 429 (rate limit) and 404 (not found) errors:
- **SOLO**: Direct OpenRouter calls with proper model naming
- **GROUP**: Goes through orchestrator with model_id ONLY (missing provider prefix)

## The Root Cause: Model Name Normalization Difference

### SOLO Chat Flow (Working)
File: `/src/api/handlers/user_message_handler.py` lines 372-540

```python
# Line 463-476: Model payload sent directly to OpenRouter
payload = {
    'model': requested_model,  # e.g., "gpt-5.2-chat" from dropdown
    'messages': [{'role': 'user', 'content': model_prompt}],
    'max_tokens': 2000,
    'temperature': 0.7,
    'stream': True
}

async with client.stream(
    "POST",
    "https://openrouter.ai/api/v1/chat/completions",  # Direct call
    headers=headers,
    json=payload
) as response:
```

**Key Point**: Model is sent AS-IS to OpenRouter. If client selects `gpt-5.2-chat`, it's sent exactly as `gpt-5.2-chat`.

### GROUP Chat Flow (Broken)
File: `/src/api/handlers/group_message_handler.py` lines 656-740

```python
# Line 656: model_id comes from participant data
model_id = participant['model_id']  # e.g., "gpt-5.2-chat"

# Line 729-732: Model passed through orchestrator.call_agent()
result = await asyncio.wait_for(
    orchestrator.call_agent(
        agent_type=agent_type,
        model_id=model_id,           # "gpt-5.2-chat"
        prompt=prompt,
        context={...}
    ),
    timeout=120.0
)
```

## Routing Differences

### In Orchestrator `_run_agent_with_elisya_async()` (lines 1094-1234)

**Line 1113-1144**: Manual model override detection
```python
if agent_type in self.model_routing and self.model_routing[agent_type].get('provider') == 'manual':
    manual_model = self.model_routing[agent_type]['model']

    # Line 1126-1127: Provider detection from model_id
    if manual_model.startswith('gpt'):
        real_provider = 'openai'
    elif manual_model.startswith('claude'):
        real_provider = 'anthropic'
    # ...
    else:
        real_provider = 'ollama'  # FALLBACK: Defaults to local!
```

**THE PROBLEM**:
- `"gpt-5.2-chat"` matches `startswith('gpt')` ✓
- Provider correctly detected as `'openai'` ✓
- But then routing is set to: `{'provider': 'openai', 'model': 'gpt-5.2-chat'}`

### In `_call_llm_with_tools_loop()` (lines 945-1091)

**Line 976-981**: Model sent to OpenAI endpoint
```python
# Line 972: Provider detection by model name
if provider is None:
    provider = ProviderRegistry.detect_provider(model)  # model = "gpt-5.2-chat"

# Line 975-981: Call with provider
response = await call_model_v2(
    messages=messages,
    model=model,          # "gpt-5.2-chat" (NO PROVIDER PREFIX!)
    provider=provider,     # Provider.OPENAI
    tools=tool_schemas
)
```

## Why 429/404 Occur

### Path 1: OpenAI Provider (429 Too Many Requests)
File: `/src/elisya/provider_registry.py` lines 93-171

```python
class OpenAIProvider(BaseProvider):
    async def call(self, messages, model, tools=None, **kwargs):
        # Line 122-123: Clean model name
        clean_model = model.replace('openai/', '')  # "gpt-5.2-chat" → "gpt-5.2-chat"

        # Line 147-152: Send to OpenAI
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json={"model": clean_model, ...}
        )
```

**Why 429**: OpenAI receives MULTIPLE rapid calls for same model in group (one per agent response):
1. Dev agent calls with `"gpt-5.2-chat"` → Rate limited
2. QA agent calls with `"gpt-5.2-chat"` → 429 (quota exceeded)
3. Retry mechanism lacks backoff

**Why SOLO works**: Single sequential call, no parallel rate limiting.

### Path 2: Provider Prefix Missing (404 Not Found)
File: `/src/elisya/provider_registry.py` lines 785-804 (ProviderRegistry.detect_provider)

When model name lacks proper detection:
- `"gpt-5.2-codex"` detected as OpenAI ✓
- `"gpt-5.2-chat"` → May trigger secondary detection (line 801):

```python
@staticmethod
def detect_provider(model_name: str) -> Provider:
    model_lower = model_name.lower()

    if model_lower.startswith('openai/') or model_lower.startswith('gpt-'):
        return Provider.OPENAI
    elif model_lower.startswith('anthropic/') or model_lower.startswith('claude-'):
        return Provider.ANTHROPIC
    # ...
    elif '/' in model_name:
        return Provider.OPENROUTER  # LINE 801: If '/' exists → OpenRouter!
    else:
        return Provider.OLLAMA      # LINE 804: Default fallback
```

**Why 404**: If model somehow triggers line 801 (`'/' in model_name`), it goes to OpenRouter:
- OpenRouter receives `"gpt-5.2-chat"` (expects `"openai/gpt-5.2-chat"`)
- 404: Model not found in OpenRouter's index

## Key Differences: GROUP vs SOLO

| Aspect | SOLO | GROUP |
|--------|------|-------|
| **Model Source** | Client dropdown (e.g., `"gpt-5.2-chat"`) | Participant config (e.g., `"gpt-5.2-chat"`) |
| **Routing Path** | Direct to OpenRouter API | → Orchestrator → Provider Registry |
| **Provider Detection** | None (direct model send) | ProviderRegistry.detect_provider() |
| **Rate Limit Exposure** | Single sequential call | Parallel calls (Dev+QA simultaneously) |
| **API Endpoint** | openrouter.ai/api/v1/ | api.openai.com/v1/ (if provider=OPENAI) |
| **Fallback Behavior** | Uses manual key rotation | Defaults to ollama if detection fails |

## Discovery: The Missing Prefix

**CRITICAL INSIGHT**:
- SOLO accepts: `"gpt-5.2-chat"` → Works with OpenRouter
- GROUP sends: `"gpt-5.2-chat"` → Detected as OpenAI → Fails with 429

OpenRouter implicitly handles model routing, but OpenAI API requires exact model names:
- OpenRouter: `"gpt-5.2-chat"` ✓ (aggregator finds it)
- OpenAI: `"gpt-5.2-chat"` ✗ (expects `"gpt-4o"`, `"gpt-4-turbo"`, etc.)

## Why Both 429 AND 404 Occur

1. **429 Case**: Group chat calls OpenAI endpoint directly (provider correctly detected)
   - Multiple agents → Multiple rapid calls
   - OpenAI rate limits → 429

2. **404 Case**: Fallback routing creates `"gpt-5.2-chat"` on wrong endpoint
   - Possible secondary detection error
   - Routed to OpenRouter without provider prefix
   - Model not found → 404

## Code Markers

- **Group Handler**: `/src/api/handlers/group_message_handler.py:656-740`
- **Orchestrator Routing**: `/src/orchestration/orchestrator_with_elisya.py:1113-1144`
- **LLM Call**: `/src/orchestration/orchestrator_with_elisya.py:1191-1196`
- **Provider Detection**: `/src/elisya/provider_registry.py:972, 785-804`
- **OpenAI Provider**: `/src/elisya/provider_registry.py:93-171`
- **Solo Handler**: `/src/api/handlers/user_message_handler.py:372-540`

# MARKER_90.1.4_END
