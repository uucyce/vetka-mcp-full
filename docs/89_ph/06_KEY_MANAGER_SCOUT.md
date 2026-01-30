# KEY MANAGER SCOUT REPORT - Phase 89
**Mission: Map VETKA's API Key Management & Model Routing for Claude Code Integration**

---

## 1. KEY MANAGEMENT ARCHITECTURE

### [CONFIG:/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/config.json]
```json
"api_keys": {
  "openrouter": {"paid": "sk-or-v1-...", "free": [...]},
  "gemini": [AIzaSy...],
  "xai": ["xai-...", "xai-...", "xai-..."],  // Grok keys!
  "anthropic": null,
  "openai": [sk-proj-...]
}
```

### [CONFIG:/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/utils/unified_key_manager.py]
**Unified Key Manager (Phase 57.12)** - Single source of truth
- **Location**: `/src/utils/unified_key_manager.py`
- **Singleton**: `get_key_manager()` returns UnifiedKeyManager instance
- **Config Load**: Reads from `/data/config.json` → section `api_keys`
- **Key Formats Detected**:
  - `xai`: Starts with `xai-` and ~70 chars (Grok keys)
  - `openrouter`: Starts with `sk-or-v1-`
  - `anthropic`: Starts with `sk-ant-`
  - `openai`: Starts with `sk-proj-` (new format)

**Key Operations**:
```python
from src.utils.unified_key_manager import get_key_manager, ProviderType

manager = get_key_manager()
xai_key = manager.get_key('xai')  # Returns first available key
xai_key = manager.get_active_key(ProviderType.XAI)  # Same thing
all_keys = manager.keys[ProviderType.XAI]  # List of APIKeyRecord
```

---

## 2. MODEL ROUTING & PROVIDER REGISTRY

### [REGISTRY:/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/provider_registry.py]
**ProviderRegistry (Phase 80.10)** - Adapter pattern for all providers

**Supported Providers**:
```python
class Provider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    XAI = "xai"  # Phase 80.35: x.ai (Grok)
```

**Registry Usage**:
```python
from src.elisya.provider_registry import ProviderRegistry, Provider

registry = ProviderRegistry()  # Singleton
xai_provider = registry.get(Provider.XAI)
response = await xai_provider.call(messages, model="grok-4")
```

---

## 3. XAI/GROK PROVIDER IMPLEMENTATION

### [ENDPOINT:POST https://api.x.ai/v1/chat/completions]
**XaiProvider** (lines 621-724 in provider_registry.py)

```python
class XaiProvider(BaseProvider):
    """Phase 80.35: x.ai API provider (Grok models)"""

    async def call(messages, model, tools=None, **kwargs):
        api_key = APIKeyService().get_key('xai')

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "tools": tools  # If provided (Phase 80.35: supports function calling)
        }

        response = await client.post(
            "https://api.x.ai/v1/chat/completions",
            headers=headers,
            json=payload
        )

        # Phase 80.39: 403 handling with key rotation
        if response.status_code == 403:
            manager = get_key_manager()
            record.mark_rate_limited()  # 24h cooldown
            next_key = manager.get_active_key(ProviderType.XAI)
            # Retry with next key or fallback to OpenRouter
```

### [PARAMS:json]
```json
{
  "model": "grok-4",
  "messages": [
    {"role": "user", "content": "query"},
    {"role": "system", "content": "system prompt"}
  ],
  "temperature": 0.7,
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "tool_name",
        "description": "Tool description",
        "parameters": {"type": "object", "properties": {}}
      }
    }
  ]
}
```

### [RESPONSE:json]
```json
{
  "message": {
    "content": "Assistant response",
    "tool_calls": null,
    "role": "assistant"
  },
  "model": "grok-4",
  "provider": "xai",
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150
  }
}
```

---

## 4. API KEY DETECTION & VALIDATION

### [CONFIG:/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/api_key_detector.py]
**APIKeyDetector** - Auto-detects provider from key format

```python
class APIKeyDetector:
    PATTERNS = {
        "xai": ProviderConfig(
            prefix="xai-",
            regex=r"^xai-[a-zA-Z0-9]{60,90}$",
            base_url="https://api.x.ai/v1",
            category=ProviderCategory.LLM,
            display_name="xAI (Grok)"
        ),
        "openrouter": ProviderConfig(
            prefix="sk-or-v1-",
            regex=r"^sk-or-v1-[a-zA-Z0-9]{32,64}$",
            base_url="https://openrouter.ai/api/v1",
            display_name="OpenRouter"
        )
    }

    @staticmethod
    def detect(key):
        # Returns {"provider": "xai", "display_name": "xAI (Grok)", ...}
```

---

## 5. EXACT CALL COORDINATES FOR CLAUDE CODE

### How to Call Grok from Claude Code:

#### Option A: Direct Provider Call (Recommended)
```python
from src.elisya.provider_registry import ProviderRegistry, Provider

async def call_grok(messages: List[Dict], model: str = "grok-4"):
    registry = ProviderRegistry()  # Get singleton
    xai_provider = registry.get(Provider.XAI)

    response = await xai_provider.call(
        messages=messages,
        model=model,
        temperature=0.7
    )

    return response["message"]["content"]
```

#### Option B: Via APIKeyService (Lower Level)
```python
from src.orchestration.services.api_key_service import APIKeyService
import httpx

api_key = APIKeyService().get_key('xai')

payload = {
    "model": "grok-4",
    "messages": [{"role": "user", "content": "query"}],
    "temperature": 0.7
}

async with httpx.AsyncClient() as client:
    resp = await client.post(
        "https://api.x.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload
    )
    result = resp.json()
```

#### Option C: Via Unified Key Manager (Full Control)
```python
from src.utils.unified_key_manager import get_key_manager, ProviderType

manager = get_key_manager()
xai_key = manager.get_active_key(ProviderType.XAI)

# Call x.ai API with xai_key
# On failure: manager.report_failure(xai_key, mark_cooldown=True)
# Or: manager.rotate_to_next()
```

---

## 6. SUPPORTED MODELS

### Grok Models (via x.ai):
- `grok-4` - Latest Grok model
- `grok-3` - Previous version
- `grok-2` - Stable version
- `grok-1.5` - Lightweight

### Via OpenRouter (Fallback):
- `x-ai/grok-4` - Routes through OpenRouter's x.ai mirror

---

## 7. AVAILABLE KEYS IN PRODUCTION

### [CONFIG:Keys Currently Loaded]
```
XAI (Grok):
  - 3 active keys in config.json (lines 29-32)
  - Validation: Must start with "xai-" and be 60-90 chars
  - Cooldown: 24 hours on 403 Forbidden (timestamp limit)

OpenRouter:
  - 1 paid key (sk-or-v1-...)
  - 8 free keys for fallback

OpenAI:
  - 2 keys (sk-proj-... format)

Gemini:
  - 3 keys (AIzaSy... format)
```

---

## 8. MISSING FEATURES FOR PRODUCTION DEPLOYMENT

### [MISSING:Error Handling & Resilience]
- Rate limit detection for OpenRouter needs refresh logic
- Circuit breaker pattern for cascading failures
- Metrics collection for cost tracking

### [MISSING:Key Rotation UI]
- Frontend dashboard for viewing available keys
- Manual key rotation endpoint
- Key health status display

### [MISSING:Streaming Support]
- XaiProvider doesn't implement streaming (currently sync only)
- Need: `async_stream()` method for real-time responses

### [MISSING:Tool Use Validation]
- XaiProvider passes tools as-is, no format validation
- Should validate OpenAI tool format compatibility

---

## 9. SERVICE LAYER ARCHITECTURE

```
Claude Code
    ↓
APIKeyService (get_key)  OR  UnifiedKeyManager
    ↓                              ↓
/data/config.json ←────────────────┘
    ↓
ProviderRegistry
    ├─ XaiProvider (grok-4)
    ├─ OpenRouterProvider (fallback)
    ├─ OpenAIProvider
    ├─ AnthropicProvider
    ├─ GoogleProvider
    └─ OllamaProvider (local)
    ↓
https://api.x.ai/v1/chat/completions
```

---

## 10. QUICK START TEMPLATE

```python
# 1. Import the registry
from src.elisya.provider_registry import ProviderRegistry, Provider

# 2. Get Grok provider
registry = ProviderRegistry()
grok = registry.get(Provider.XAI)

# 3. Prepare messages
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Explain quantum computing"}
]

# 4. Call Grok
response = await grok.call(
    messages=messages,
    model="grok-4",
    temperature=0.7
)

# 5. Get response
print(response["message"]["content"])
```

---

## 11. PROVIDER ENDPOINTS SUMMARY

| Provider | Endpoint | Auth | Status |
|----------|----------|------|--------|
| XAI/Grok | https://api.x.ai/v1/chat/completions | Bearer Token | ✅ Active |
| OpenRouter | https://openrouter.ai/api/v1/chat/completions | Bearer Token | ✅ Active |
| OpenAI | https://api.openai.com/v1/chat/completions | Bearer Token | ✅ Active |
| Anthropic | https://api.anthropic.com/v1/messages | x-api-key | ✅ Active |
| Google | https://generativelanguage.googleapis.com/v1beta | Query param | ✅ Active |
| Ollama | http://localhost:11434/api/chat | None | ✅ Local |

---

**Report Generated**: 2026-01-22
**Phase**: 89 - Key Manager Scout
**Status**: READY FOR CLAUDE CODE INTEGRATION
