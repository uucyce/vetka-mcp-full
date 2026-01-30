# Phase 94.4: Model Duplication Investigation
**Research on showing models from multiple sources separately**

## 🎯 Task
Models accessible via TWO sources (e.g., Grok via xAI direct AND OpenRouter) should appear TWICE with different labels.

---

## 📊 Current Data Flow

### 1. Backend Sources (API Endpoints)

#### `/api/models` → Cloud Models
- **Source**: `src/api/routes/model_routes.py:list_models()`
- **Data from**: `model_registry.get_all()` → `ModelRegistry.DEFAULT_MODELS`
- **Static list**: Hardcoded models in `src/services/model_registry.py`
- **Contains**:
  - Local Ollama models (qwen2:7b, llama3:8b, deepseek-coder:6.7b)
  - OpenRouter free models (deepseek/deepseek-r1:free, meta-llama/llama-3.1-405b-instruct:free)
  - Voice models (elevenlabs/*, google/wavenet, deepgram/nova-2)
  - MCP agents (mcp/claude_code, mcp/browser_haiku)

#### `/api/models/local` → Ollama Models
- **Source**: `model_routes.py:list_local()`
- **Data from**: `model_registry.get_local()` - filters `type == ModelType.LOCAL`

#### `/api/models/mcp-agents` → MCP Agents
- **Source**: `model_routes.py:list_mcp_agents()`
- **Data from**: `model_registry.get_mcp_agents()` - filters `type == ModelType.MCP_AGENT`

#### Dynamic Model Discovery (NOT USED BY FRONTEND YET)
- **OpenRouter models**: `src/elisya/model_fetcher.py:fetch_openrouter_models()`
  - Fetches ALL models from OpenRouter API
  - Caches to `data/models_cache.json` (24h cache)
  - Returns ~500+ models from all providers
- **Gemini direct**: `model_fetcher.py:fetch_gemini_models()`
  - Fetches from Google Generative AI API
  - Adds `source: 'gemini_direct'` marker

### 2. Frontend Aggregation

**File**: `client/src/components/ModelDirectory.tsx`

```typescript
// Line 234-236: Combined model list
const allModels = useMemo(() => {
  return [...localModels, ...mcpAgents, ...models];
}, [localModels, mcpAgents, models]);
```

**Flow**:
1. Frontend fetches 3 separate arrays in parallel (line 167-171)
2. Merges them into `allModels` (local → mcp → cloud)
3. Filters/searches happen on merged list (line 239-323)

### 3. Provider Detection Logic

**File**: `src/elisya/provider_registry.py`

```python
@staticmethod
def detect_provider(model_name: str) -> Provider:
    # Line 979-1015: Simple prefix-based routing
    # openai/* or gpt-* → OPENAI
    # anthropic/* or claude-* → ANTHROPIC
    # google/* or gemini* → GOOGLE
    # xai/* or x-ai/* or grok* → XAI
    # else → OPENROUTER
```

**Key insight**: Models WITHOUT prefixes default to OpenRouter!

---

## 🔍 Models That Exist in Multiple Sources

### Example: Grok Models

**xAI Direct** (if API key exists):
- `grok-2-latest` → routes to xAI API
- `grok-vision-beta` → routes to xAI API

**OpenRouter** (always available):
- `x-ai/grok-2-latest` → routes to OpenRouter
- `x-ai/grok-vision-beta` → routes to OpenRouter

### Problem
Currently: Frontend shows models from `ModelRegistry.DEFAULT_MODELS` which is STATIC.
- No duplication exists
- No dynamic discovery from OpenRouter

### Other Duplicate Cases
1. **OpenAI models**: `gpt-4o` (direct) vs `openai/gpt-4o` (OpenRouter)
2. **Anthropic models**: `claude-3-5-sonnet-latest` (direct) vs `anthropic/claude-3-5-sonnet-latest` (OpenRouter)
3. **Google models**: `gemini-2.0-flash-exp` (direct) vs `google/gemini-2.0-flash-exp` (OpenRouter)

---

## 💡 Where to Implement Duplication

### Option A: Backend (Recommended ⭐)
**Location**: `src/api/routes/model_routes.py:list_models()`

**Pros**:
- ✅ Clean separation: backend owns data logic
- ✅ Easy to cache/optimize
- ✅ Single source of truth
- ✅ Can check which API keys are active before showing duplicates

**Cons**:
- ❌ Requires backend restart to test
- ❌ More complex caching logic

**Why best**: Backend already knows which providers have keys (`unified_key_manager`), can intelligently show only relevant duplicates.

---

### Option B: Frontend
**Location**: `client/src/components/ModelDirectory.tsx:allModels` computation

**Pros**:
- ✅ Fast iteration (no backend restart)
- ✅ Easy to A/B test visually

**Cons**:
- ❌ Duplicates data logic
- ❌ Harder to check key availability
- ❌ More complex filtering logic

---

## 📝 Pseudocode Solution (Backend)

### Step 1: Create Duplication Service

```python
# File: src/services/model_duplicator.py

from typing import List, Dict
from src.utils.unified_key_manager import get_key_manager, ProviderType

class ModelDuplicator:
    """
    Phase 94.4: Generate duplicate entries for multi-source models.
    Shows same model via different providers IF keys exist.
    """

    # Models that can route to BOTH direct API AND OpenRouter
    DUAL_SOURCE_MODELS = {
        # Grok (xAI direct + OpenRouter)
        "grok-2-latest": {
            "direct": {"provider": "xai", "requires_key": ProviderType.XAI},
            "openrouter": {"provider": "openrouter", "id_format": "x-ai/{model}"}
        },
        "grok-vision-beta": {
            "direct": {"provider": "xai", "requires_key": ProviderType.XAI},
            "openrouter": {"provider": "openrouter", "id_format": "x-ai/{model}"}
        },

        # OpenAI models
        "gpt-4o": {
            "direct": {"provider": "openai", "requires_key": ProviderType.OPENAI},
            "openrouter": {"provider": "openrouter", "id_format": "openai/{model}"}
        },

        # Anthropic models
        "claude-3-5-sonnet-latest": {
            "direct": {"provider": "anthropic", "requires_key": ProviderType.ANTHROPIC},
            "openrouter": {"provider": "openrouter", "id_format": "anthropic/{model}"}
        },

        # Google models
        "gemini-2.0-flash-exp": {
            "direct": {"provider": "google", "requires_key": ProviderType.GEMINI},
            "openrouter": {"provider": "openrouter", "id_format": "google/{model}"}
        }
    }

    @staticmethod
    def create_duplicates(base_models: List[Dict]) -> List[Dict]:
        """
        Take base model list, return expanded list with duplicates.

        Logic:
        1. Check which API keys are active
        2. For each model in DUAL_SOURCE_MODELS:
           - If direct key exists → add direct version
           - Always add OpenRouter version (free tier available)
        3. Mark duplicates with badges: "Direct" vs "OR"
        """
        km = get_key_manager()
        result = []

        for model in base_models:
            model_id = model['id']

            # Check if this model has dual sources
            if model_id in DUAL_SOURCE_MODELS:
                config = DUAL_SOURCE_MODELS[model_id]

                # Add direct version IF key exists
                direct_cfg = config['direct']
                if km.has_active_key(direct_cfg['requires_key']):
                    direct_model = {**model}
                    direct_model['id'] = model_id  # Keep original ID
                    direct_model['provider'] = direct_cfg['provider']
                    direct_model['source'] = 'direct'
                    direct_model['name'] = f"{model['name']} (Direct)"
                    result.append(direct_model)

                # Always add OpenRouter version
                or_cfg = config['openrouter']
                or_model = {**model}
                or_model['id'] = or_cfg['id_format'].format(model=model_id)
                or_model['provider'] = 'openrouter'
                or_model['source'] = 'openrouter'
                or_model['name'] = f"{model['name']} (OR)"
                result.append(or_model)
            else:
                # Not a dual-source model, keep as-is
                result.append(model)

        return result
```

### Step 2: Integrate into API Route

```python
# File: src/api/routes/model_routes.py

@router.get("")
async def list_models():
    """
    Get all models in phonebook.
    Phase 94.4: Returns duplicates for multi-source models.
    """
    from src.services.model_duplicator import ModelDuplicator

    registry = get_model_registry()
    base_models = registry.get_all()

    # Generate duplicates for models with multiple sources
    expanded_models = ModelDuplicator.create_duplicates(base_models)

    return {
        'models': expanded_models,
        'count': len(expanded_models),
        'duplicates': len(expanded_models) - len(base_models)  # Info for debugging
    }
```

### Step 3: Frontend Badge Display

```typescript
// File: client/src/components/ModelDirectory.tsx (line 799-809)

{/* Phase 94.4: Source badge - Direct vs OpenRouter */}
{model.source === 'direct' && (
  <span style={{
    fontSize: 9, padding: '1px 5px',
    background: '#1a1a1a', color: '#aaa',
    borderRadius: 3, marginLeft: 4
  }}>Direct API</span>
)}
{model.source === 'openrouter' && (
  <span style={{
    fontSize: 9, padding: '1px 5px',
    background: '#1a1a1a', color: '#888',
    borderRadius: 3, marginLeft: 4
  }}>OpenRouter</span>
)}
```

---

## 🗂️ Files to Modify

### Backend (Python)
1. **CREATE**: `src/services/model_duplicator.py`
   - New service for duplication logic
   - ~150 lines

2. **MODIFY**: `src/api/routes/model_routes.py`
   - Line ~25: Add `ModelDuplicator.create_duplicates()` call
   - +5 lines

3. **MODIFY**: `src/services/model_registry.py`
   - Optional: Add `source` field to `ModelEntry` dataclass
   - +1 line in `to_dict()` method

### Frontend (TypeScript)
4. **MODIFY**: `client/src/components/ModelDirectory.tsx`
   - Line ~12-25: Add `source?: string` to `Model` interface
   - Line ~799-809: Add source badge rendering (after OpenRouter badge)
   - +15 lines

### Tests (Optional)
5. **CREATE**: `tests/test_model_duplicator.py`
   - Test duplication logic
   - Test key availability checks
   - ~100 lines

---

## 🚀 Implementation Plan

### Phase 1: Minimal Viable Product (1-2 hours)
1. Create `model_duplicator.py` with 5-10 most popular models
2. Integrate into `/api/models` endpoint
3. Add source badges to frontend
4. Test with xAI key present/absent

### Phase 2: Full Coverage (2-3 hours)
1. Expand `DUAL_SOURCE_MODELS` to cover all major providers
2. Add tests
3. Add caching layer (avoid recalculating on every request)
4. Document in API docs

### Phase 3: Dynamic Discovery (4-6 hours)
1. Use `model_fetcher.py` to discover models dynamically
2. Auto-detect which models exist on both OpenRouter AND direct APIs
3. Remove hardcoded `DUAL_SOURCE_MODELS` list
4. Use OpenRouter cache to compare IDs

---

## ⚠️ Edge Cases to Handle

1. **Model doesn't exist on OpenRouter**
   - Only show direct version
   - Example: OpenAI's unreleased models

2. **Direct API key expired/invalid**
   - Hide direct version
   - Only show OpenRouter version

3. **Free vs Paid tiers**
   - OpenRouter free tier: `deepseek/deepseek-r1:free`
   - Direct API: `deepseek-r1` (paid)
   - Show BOTH, mark pricing clearly

4. **Model name conflicts**
   - `grok-2-latest` (direct xAI)
   - `x-ai/grok-2-latest` (OpenRouter)
   - Use badges to disambiguate

---

## 📋 Testing Checklist

- [ ] With xAI key: shows `grok-2-latest` (Direct) + `x-ai/grok-2-latest` (OR)
- [ ] Without xAI key: shows only `x-ai/grok-2-latest` (OR)
- [ ] With OpenAI key: shows `gpt-4o` (Direct) + `openai/gpt-4o` (OR)
- [ ] Badges render correctly
- [ ] Clicking each version calls correct API (verify in console logs)
- [ ] Search works for both versions
- [ ] Filters work correctly (direct models show in `xai_direct` filter)

---

## 🎓 Key Learnings

1. **Current state**: No real duplication exists - `ModelRegistry` is static
2. **Root cause**: Frontend uses hardcoded `DEFAULT_MODELS`, not dynamic OpenRouter data
3. **Best approach**: Backend duplication with key-aware logic
4. **Side benefit**: Forces migration to dynamic model discovery (Phase 60.5 goal)

---

## 📌 Related Issues

- Phase 60.5: Dynamic model discovery (partially implemented, not used by frontend)
- Phase 93.11: Model status for online/offline detection
- Phase 94: Provider filters in ModelDirectory

---

**Status**: ✅ Investigation Complete - Ready for Implementation
**Recommended**: Start with Phase 1 (MVP) using backend approach
