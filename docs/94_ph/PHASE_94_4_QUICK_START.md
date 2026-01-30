# Phase 94.4: Quick Start Implementation Guide

**Time estimate**: 1-2 hours for MVP

---

## 🎯 Goal
Add model duplication with badges in 3 steps:
1. Create duplicator service (backend)
2. Wire into API route
3. Add badges (frontend)

---

## Step 1: Create Duplicator Service (30 min)

### File: `src/services/model_duplicator.py` (NEW)

```python
"""
Phase 94.4: Model Duplication Service
Generates duplicate entries for models available via multiple sources.
"""

from typing import List, Dict, Optional
from src.utils.unified_key_manager import get_key_manager, ProviderType
import logging

logger = logging.getLogger(__name__)


class ModelDuplicator:
    """
    Creates duplicate model entries for models accessible via:
    - Direct provider API (OpenAI, xAI, Anthropic, Google)
    - OpenRouter proxy

    Shows both versions ONLY if direct API key exists.
    Always shows OpenRouter version (free tier available).
    """

    # Models that can route to BOTH direct API AND OpenRouter
    # Add more models here as needed
    DUAL_SOURCE_MODELS = {
        # xAI (Grok) models
        "grok-2-latest": {
            "display_name": "Grok 2 Latest",
            "direct": {
                "provider": "xai",
                "requires_key": ProviderType.XAI
            },
            "openrouter": {
                "id_format": "x-ai/{model}"
            }
        },
        "grok-vision-beta": {
            "display_name": "Grok Vision Beta",
            "direct": {
                "provider": "xai",
                "requires_key": ProviderType.XAI
            },
            "openrouter": {
                "id_format": "x-ai/{model}"
            }
        },

        # OpenAI models
        "gpt-4o": {
            "display_name": "GPT-4o",
            "direct": {
                "provider": "openai",
                "requires_key": ProviderType.OPENAI
            },
            "openrouter": {
                "id_format": "openai/{model}"
            }
        },
        "gpt-4o-mini": {
            "display_name": "GPT-4o Mini",
            "direct": {
                "provider": "openai",
                "requires_key": ProviderType.OPENAI
            },
            "openrouter": {
                "id_format": "openai/{model}"
            }
        },

        # Anthropic models
        "claude-3-5-sonnet-latest": {
            "display_name": "Claude 3.5 Sonnet",
            "direct": {
                "provider": "anthropic",
                "requires_key": ProviderType.ANTHROPIC
            },
            "openrouter": {
                "id_format": "anthropic/{model}"
            }
        },

        # Google models
        "gemini-2.0-flash-exp": {
            "display_name": "Gemini 2.0 Flash",
            "direct": {
                "provider": "google",
                "requires_key": ProviderType.GEMINI
            },
            "openrouter": {
                "id_format": "google/{model}"
            }
        }
    }

    @staticmethod
    def create_duplicates(base_models: List[Dict]) -> List[Dict]:
        """
        Transform base model list into expanded list with duplicates.

        Logic:
        1. Check which API keys are active (via unified_key_manager)
        2. For each model in DUAL_SOURCE_MODELS:
           - If direct key exists → add direct version
           - Always add OpenRouter version
        3. Mark each with source: "direct" or "openrouter"
        4. Return expanded list

        Args:
            base_models: Original model list from ModelRegistry

        Returns:
            Expanded list with duplicate entries for multi-source models
        """
        km = get_key_manager()
        result = []
        duplicates_added = 0

        for model in base_models:
            model_id = model.get('id', '')

            # Check if this model has dual sources
            if model_id in ModelDuplicator.DUAL_SOURCE_MODELS:
                config = ModelDuplicator.DUAL_SOURCE_MODELS[model_id]
                direct_cfg = config['direct']
                or_cfg = config['openrouter']
                display_name = config.get('display_name', model.get('name', model_id))

                # Add DIRECT version (only if key exists)
                if km.has_active_key(direct_cfg['requires_key']):
                    direct_model = {**model}
                    direct_model['id'] = model_id
                    direct_model['provider'] = direct_cfg['provider']
                    direct_model['source'] = 'direct'
                    direct_model['name'] = f"{display_name} (Direct)"
                    result.append(direct_model)
                    duplicates_added += 1
                    logger.debug(f"[Duplicator] Added direct: {model_id}")

                # Add OPENROUTER version (always)
                or_model = {**model}
                or_model['id'] = or_cfg['id_format'].format(model=model_id)
                or_model['provider'] = 'openrouter'
                or_model['source'] = 'openrouter'
                or_model['name'] = f"{display_name} (OR)"
                result.append(or_model)
                logger.debug(f"[Duplicator] Added OR: {or_model['id']}")

            else:
                # Not a dual-source model, keep as-is
                result.append(model)

        logger.info(f"[Duplicator] Created {duplicates_added} duplicates, total models: {len(result)}")
        return result


# Quick test
if __name__ == '__main__':
    # Test with mock data
    mock_models = [
        {'id': 'grok-2-latest', 'name': 'Grok 2', 'provider': 'xai'},
        {'id': 'gpt-4o', 'name': 'GPT-4o', 'provider': 'openai'},
        {'id': 'qwen2:7b', 'name': 'Qwen 2', 'provider': 'ollama'}
    ]

    duplicated = ModelDuplicator.create_duplicates(mock_models)

    print(f"Input: {len(mock_models)} models")
    print(f"Output: {len(duplicated)} models")
    print("\nExpanded list:")
    for m in duplicated:
        print(f"  - {m['id']} | {m.get('source', 'original')} | {m['name']}")
```

---

## Step 2: Wire into API Route (10 min)

### File: `src/api/routes/model_routes.py` (MODIFY)

```python
# At the top, add import
from src.services.model_duplicator import ModelDuplicator

# Find the list_models() function (around line 22)
# Replace it with this:

@router.get("")
async def list_models():
    """
    Get all models in phonebook.
    Phase 94.4: Returns duplicates for multi-source models.
    """
    registry = get_model_registry()
    base_models = registry.get_all()

    # Phase 94.4: Generate duplicates for models with multiple sources
    expanded_models = ModelDuplicator.create_duplicates(base_models)

    return {
        'models': expanded_models,
        'count': len(expanded_models),
        'base_count': len(base_models),
        'duplicates': len(expanded_models) - len(base_models)
    }
```

---

## Step 3: Add Frontend Badges (20 min)

### File: `client/src/components/ModelDirectory.tsx` (MODIFY)

#### 3.1: Update Model Interface (line ~12-25)

```typescript
interface Model {
  id: string;
  name: string;
  provider: string;
  context_length: number;
  pricing: {
    prompt: string;
    completion: string;
  };
  description?: string;
  isLocal?: boolean;
  type?: string;
  capabilities?: string[];
  source?: string;  // Phase 94.4: NEW - "direct" | "openrouter" | undefined
}
```

#### 3.2: Add Badge Rendering (after line 809)

Find the section where OpenRouter badge is rendered (around line 799-809), and add this RIGHT AFTER:

```typescript
{/* Phase 94.4: Source badge - Direct API vs OpenRouter */}
{model.source === 'direct' && (
  <span style={{
    fontSize: 9,
    padding: '1px 5px',
    background: '#1a1a1a',
    color: '#aaa',
    borderRadius: 3,
    marginLeft: 4
  }}>
    Direct API
  </span>
)}
{model.source === 'openrouter' && !modelStatus[model.id]?.via_openrouter && (
  <span style={{
    fontSize: 9,
    padding: '1px 5px',
    background: '#1a1a1a',
    color: '#888',
    borderRadius: 3,
    marginLeft: 4
  }}>
    OpenRouter
  </span>
)}
```

---

## Step 4: Test It (10 min)

### Backend Test (Python)

```bash
# In project root
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

# Test the duplicator
python -m src.services.model_duplicator

# Should output:
# Input: 3 models
# Output: 5-6 models (depending on keys)
# Expanded list:
#   - grok-2-latest | direct | Grok 2 (Direct)
#   - x-ai/grok-2-latest | openrouter | Grok 2 (OR)
#   - gpt-4o | direct | GPT-4o (Direct)
#   - openai/gpt-4o | openrouter | GPT-4o (OR)
#   - qwen2:7b | original | Qwen 2
```

### API Test (curl)

```bash
# Test the API endpoint
curl http://localhost:5002/api/models | jq '.count, .duplicates'

# Should output:
# 25  (total count - will vary)
# 8   (duplicates added)
```

### Frontend Test (Browser)

1. Start backend: `python main.py`
2. Start frontend: `cd client && npm run dev`
3. Open http://localhost:5173
4. Click phone icon (Model Directory)
5. Look for models with badges:
   - `Grok 2 Latest (Direct)` with `[Direct API]` badge
   - `Grok 2 Latest (OR)` with `[OpenRouter]` badge

### Visual Verification

**With xAI key**:
```
🟢 Grok 2 Latest (Direct)    [Direct API]
   grok-2-latest
   Free · 32K ctx · xai

🟢 Grok 2 Latest (OR)        [OpenRouter]
   x-ai/grok-2-latest
   Free · 32K ctx · openrouter
```

**Without xAI key**:
```
🟢 Grok 2 Latest (OR)        [OpenRouter]
   x-ai/grok-2-latest
   Free · 32K ctx · openrouter
```

---

## Step 5: Verify Routing (10 min)

### Test Direct API Call

1. Click "Grok 2 Latest (Direct)" in phone book
2. Send message: "Hello"
3. Check backend logs for:
   ```
   [XAI] Calling grok-2-latest (key: ****xxxx)
   POST https://api.x.ai/v1/chat/completions
   ```

### Test OpenRouter Call

1. Click "Grok 2 Latest (OR)" in phone book
2. Send message: "Hello"
3. Check backend logs for:
   ```
   [OPENROUTER] Calling x-ai/grok-2-latest
   POST https://openrouter.ai/api/v1/chat/completions
   ```

---

## 🐛 Troubleshooting

### Issue: No duplicates showing

**Check 1**: Backend logs
```python
# In model_duplicator.py, add debug logging
logger.setLevel(logging.DEBUG)
```

**Check 2**: API response
```bash
curl http://localhost:5002/api/models | jq '.duplicates'
# Should be > 0
```

**Check 3**: Key manager
```bash
# In Python console
from src.utils.unified_key_manager import get_key_manager, ProviderType
km = get_key_manager()
print(km.has_active_key(ProviderType.XAI))
# Should be True if xAI key exists
```

---

### Issue: Badges not showing

**Check 1**: Model object structure
```typescript
// In ModelDirectory.tsx, add console.log
console.log('[ModelDirectory] Model:', model);
// Check if 'source' field exists
```

**Check 2**: Badge CSS
```typescript
// Temporarily change badge background to bright color
background: '#ff0000',  // Red - easy to spot
```

---

### Issue: Wrong API being called

**Check 1**: Provider detection
```python
# In provider_registry.py, add logging
print(f"[DETECT] model={model}, detected={provider.value}")
```

**Check 2**: Model ID format
```
Direct should be: "grok-2-latest"
OpenRouter should be: "x-ai/grok-2-latest" (with slash!)
```

---

## 📊 Success Metrics

After implementation, you should see:

✅ Backend: `duplicates` count > 0 in `/api/models` response
✅ Frontend: Models with "(Direct)" and "(OR)" suffixes
✅ Frontend: Badges showing "Direct API" and "OpenRouter"
✅ Routing: Console logs show correct API being called
✅ Filters: `xai_direct` filter shows only Direct versions

---

## 🚀 Next Steps (Phase 2)

After MVP works:

1. **Add more models** to `DUAL_SOURCE_MODELS` dict
2. **Add tests** in `tests/test_model_duplicator.py`
3. **Add caching** to avoid recalculating on every request
4. **Dynamic discovery** - auto-detect from OpenRouter cache

---

## 📚 References

- Full investigation: `PHASE_94_4_MODEL_DUPLICATION.md`
- Architecture diagrams: `PHASE_94_4_DATA_FLOW_DIAGRAM.md`
- Provider registry: `src/elisya/provider_registry.py`
- Key manager: `src/utils/unified_key_manager.py`

---

**Estimated Time**: 1-2 hours total
**Difficulty**: Medium (backend + frontend changes)
**Status**: Ready to implement
