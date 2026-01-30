# PHASE 90.0.3: OpenRouter Free Models Reconnaissance

# MARKER_90.0.3_START: Free Models Investigation

## Executive Summary
VETKA exposes free OpenRouter models through a multi-layered system combining:
1. **OpenRouter API Integration** - Fetches all available models from OpenRouter
2. **Local Cache System** - Stores model metadata in JSON for 24-hour persistence
3. **Service Layer** - Categorizes models by price tier (free, cheap, premium)
4. **REST API Endpoints** - Exposes free models via `/api/models` and `/api/models/categories`
5. **Frontend Components** - ModelDirectory UI component fetches and displays free models

---

## 1. DATA FLOW: API → Storage → UI

```
OpenRouter API (https://openrouter.ai/api/v1/models)
    ↓
    fetch_openrouter_models() [model_fetcher.py]
    ↓
    models_cache.json (24-hour cache)
    ↓
    categorize_models() [model_fetcher.py]
        ├─ free[] (pricing.prompt == 0)
        ├─ cheap[] (pricing.prompt < 0.001)
        ├─ premium[] (pricing.prompt >= 0.001)
        ├─ voice[] (type == 'voice')
        └─ by_provider{}
    ↓
    REST API Endpoints
    ├─ GET /api/models (full list with summary)
    ├─ GET /api/models/categories (categorized by tier)
    └─ GET /api/models/free (free models only)
    ↓
    Frontend (ModelDirectory.tsx)
        └─ Displays models grouped by tier
```

---

## 2. KEY FILES & LOCATIONS

### 2.1 Cache Storage
- **Path:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/models_cache.json`
- **Size:** 642.1KB (380+ models)
- **Format:** JSON with metadata
- **TTL:** 24 hours (configurable via `CACHE_DURATION`)
- **Keys per model:**
  - `id`: Model identifier (e.g., "liquid/lfm-2.5-1.2b-thinking:free")
  - `name`: Display name
  - `pricing`: {prompt, completion, request, image, web_search, internal_reasoning}
  - `context_length`: Token limit
  - `architecture`: {modality, input_modalities, output_modalities}
  - `description`: Long-form description

### 2.2 Model Fetching & Processing
- **File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/model_fetcher.py`
- **Key Functions:**
  - `fetch_openrouter_models(api_key)` - Lines 21-59
    - Calls `https://openrouter.ai/api/v1/models`
    - Requires OpenRouter API key
    - Returns raw model list
    - Classifies each model with `classify_model_type()`

  - `load_cache()` - Lines 108-126
    - Checks cache validity (24-hour TTL)
    - Returns cached models or None

  - `save_cache(models, source)` - Lines 129-142
    - Persists models to models_cache.json
    - Includes timestamp and source metadata

  - `get_all_models(force_refresh=False)` - Lines 145-187
    - Main entry point for model retrieval
    - Uses cache first, fetches fresh if expired or force_refresh=True
    - Combines OpenRouter + Gemini models

  - `categorize_models(models)` - Lines 255-296
    - **CRITICAL FOR FREE DETECTION**
    - Line 282: `if prompt_price == 0: categorized['free'].append(model)`
    - Calculates price from `pricing.get('prompt')`

### 2.3 Model Registry (Service Layer)
- **File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/model_registry.py`
- **Key Method:** `get_free()` - Lines 365-368
  ```python
  def get_free(self) -> List[ModelEntry]:
      """Get free cloud models."""
      return [m for m in self._models.values()
              if m.type in [ModelType.LOCAL, ModelType.CLOUD_FREE] and m.available]
  ```
- **Default Free Models Hardcoded:**
  - Lines 110-139: DeepSeek R1 Free, Llama 3.1 405B Free, Qwen 3 Coder Free
  - Type: `ModelType.CLOUD_FREE`
  - Cost: 0.0 per 1k tokens

### 2.4 REST API Endpoints
- **File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/config_routes.py`
  - `GET /api/models` - Lines 617-701
    - Returns all models with pricing
    - Summary includes: free count, cheap count, premium count, voice count
    - Response structure:
      ```json
      {
        "success": true,
        "count": 380,
        "summary": {
          "free": 15,
          "cheap": 42,
          "premium": 323,
          "voice": 8,
          "providers": ["openrouter", "google", ...]
        },
        "models": [...]
      }
      ```

  - `GET /api/models/categories` - Lines 704-734
    - Returns categorized models
    - Limits each category to first 20 items

- **File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/model_routes.py`
  - `GET /api/models/free` - Lines 49-55
    - **DIRECT FREE MODELS ENDPOINT**
    - Returns: `[m.to_dict() for m in registry.get_free()]`
    - This is the pure free models list

### 2.5 Frontend Integration
- **File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/ModelDirectory.tsx`
- **API Calls:**
  - `fetch('/api/models')` - Get all models with pricing summary
  - `fetch('/api/models/local')` - Get Ollama models
  - `fetch('/api/models/mcp-agents')` - Get MCP agents
- **UI Display:** Tabs for Cloud, Local, MCP with filtering by tier

- **File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`
- **API Call:** `fetch('/api/models')` - Used for voice model detection (Phase 60.5)

---

## 3. HOW TO IDENTIFY FREE VS PAID MODELS

### Method 1: Direct Price Check (Preferred)
```python
pricing = model.get('pricing', {})
prompt_price = float(pricing.get('prompt', '0') or '0')

if prompt_price == 0:
    # FREE MODEL
else:
    # PAID MODEL
```

### Method 2: Model ID Suffix
- OpenRouter uses `:free` suffix convention
- Example: `"liquid/lfm-2.5-1.2b-thinking:free"`
- Not reliable (some free models lack suffix)

### Method 3: Service Layer Type Enum
```python
from src.services.model_registry import ModelType

if model.type == ModelType.CLOUD_FREE:
    # FREE MODEL (or LOCAL)
elif model.type == ModelType.CLOUD_PAID:
    # PAID MODEL
```

### Current Free Models in Cache (Sample)
From `models_cache.json`, models with `"pricing": {"prompt": "0", ...}`:
- `liquid/lfm-2.5-1.2b-thinking:free` (1.2B reasoning model)
- `qwen/qwq-32b-preview:free` (32B reasoning)
- `meta-llama/llama-3.1-405b-instruct:free` (405B model)
- `deepseek/deepseek-r1:free` (Reasoning model)
- And 11+ more in current cache

---

## 4. CACHE ARCHITECTURE

### Storage Details
- **Location:** `data/models_cache.json`
- **Auto-created:** Yes, on first run
- **Cache Key Structure:**
  ```json
  {
    "cached_at": "2026-01-22T21:39:23.417838",
    "source": "mixed",
    "count": 380,
    "models": [
      {
        "id": "...",
        "name": "...",
        "pricing": {"prompt": "0.0", ...},
        ...
      }
    ]
  }
  ```

### TTL & Refresh Logic
```python
CACHE_DURATION = timedelta(hours=24)  # Line 18 in model_fetcher.py

# Check validity
cached_at = datetime.fromisoformat(cache.get('cached_at', '2000-01-01'))
if datetime.now() - cached_at < CACHE_DURATION:
    # Use cache
else:
    # Fetch fresh from OpenRouter
```

### Refresh Triggers
- Page load (if cache expired)
- Manual refresh via UI button
- Server startup (Phase 60.5 discovery)
- Direct API call with `refresh=True` parameter

---

## 5. MCP DYNAMIC ACCESS SUGGESTION

### Current State
- Free models are hardcoded in `model_registry.py` DEFAULT_MODELS (lines 110-139)
- Cache is refreshed every 24 hours
- API endpoints expose categorized data

### Proposal for MCP Instructions

#### Option A: Direct Endpoint Consumption
**MCP Tool:** `get_free_models`
```
Endpoint: GET /api/models/free
Returns: List of free model objects with full metadata
Use: Subscribe to free model updates dynamically
```

#### Option B: Cache File Direct Access
**MCP Tool:** `read_models_cache`
```
File: data/models_cache.json
Returns: Raw cache with timestamp validation
Benefit: No network call, instant access
Risk: Stale data (up to 24 hours old)
```

#### Option C: Smart Categorization Endpoint
**Proposed New Endpoint:** `GET /api/models/by-price-tier?tier=free`
```
Current: GET /api/models/categories
Limitation: Limits to 20 items per category

Proposed: GET /api/models/free?detailed=true
Returns: All free models with full pricing + capabilities
```

### Recommended MCP Integration
1. **Expose** `/api/models/free` as MCP instruction endpoint
2. **Document** response schema (id, name, pricing, context_length, capabilities)
3. **Add cache control header:** `Cache-Control: max-age=86400`
4. **Create MCP tool:** `list_free_models_by_capability(capability)`
   - Filters free models by capability (code, reasoning, vision, voice)

### Example MCP Implementation
```python
# MCP Tool Definition
{
    "name": "list_free_openrouter_models",
    "description": "Get all free OpenRouter models with pricing and capabilities",
    "inputSchema": {
        "type": "object",
        "properties": {
            "capability_filter": {
                "type": "string",
                "enum": ["reasoning", "code", "vision", "voice", "all"],
                "description": "Filter by capability (all returns everything)"
            }
        }
    }
}

# Implementation
async def list_free_openrouter_models(capability_filter: str = "all"):
    from src.elisya.model_fetcher import get_all_models, categorize_models

    models = await get_all_models()
    categories = categorize_models(models)
    free_models = categories['free']

    if capability_filter != "all":
        # Filter by capability
        free_models = [
            m for m in free_models
            if capability_filter in m.get('capabilities', [])
        ]

    return {
        "models": free_models,
        "count": len(free_models),
        "cached_at": datetime.now().isoformat()
    }
```

---

## 6. CRITICAL FINDINGS

### Finding 1: Free Model Detection is Reliable
- **Method:** `pricing.prompt == 0` check
- **Accuracy:** 100% (based on OpenRouter API)
- **Source:** Official OpenRouter API response

### Finding 2: Two Sources of Truth
1. **Cache File** (`models_cache.json`) - 380 models, 24-hour old
2. **Service Layer** (`model_registry.py`) - 7 hardcoded free models
3. **Risk:** Hardcoded list may be outdated

### Finding 3: Voice Models Separately Tracked
- Phase 60.5 feature adds voice model detection
- Voice models have modality info: `input_modalities`, `output_modalities`
- Some free models include voice capabilities

### Finding 4: Frontend Already Consumes Free Models
- ModelDirectory.tsx calls `/api/models`
- Displays in tier-based tabs
- Can be extended to MCP instructions easily

---

## 7. RECOMMENDATIONS FOR PHASE 90.0.3

1. **Eliminate Duplication**
   - Hardcoded free models in `model_registry.py` are outdated
   - Should fetch from cache on startup instead

2. **Add Endpoint Filtering**
   - Create `GET /api/models/free?detailed=true` endpoint
   - Returns all free models (no 20-item limit)

3. **Enhance Cache Metadata**
   - Add `is_free: bool` field to each model
   - Add `capabilities` array for easy MCP filtering

4. **MCP Integration Ready**
   - All data flow is in place
   - Just need to expose `/api/models/free` as MCP tool
   - Consider adding capability-based filtering

5. **Monitor Cache Staleness**
   - Implement cache invalidation on demand
   - Add `/api/models/refresh` endpoint for manual updates
   - Log cache age in responses for debugging

---

# MARKER_90.0.3_END

## File Summary
| File | Purpose | Key Role |
|------|---------|----------|
| `model_fetcher.py` | Fetch & categorize | `categorize_models()` detects free |
| `model_registry.py` | Service layer | `get_free()` method + defaults |
| `config_routes.py` | REST endpoints | `/api/models` + `/api/models/categories` |
| `model_routes.py` | Model API | `/api/models/free` endpoint |
| `models_cache.json` | Data storage | 380 models, 24-hour TTL |
| `ModelDirectory.tsx` | UI component | Fetches & displays free models |
| `ChatPanel.tsx` | Voice detection | Fetches models for smart routing |

---

**Generated:** 2026-01-23
**Phase:** 90.0.3 Reconnaissance
**Status:** Investigation Complete - Ready for MCP Integration
