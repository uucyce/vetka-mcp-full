# HAIKU SCOUT: Multi-Source Model Display + Key Filter Feature
## Markers Report

**Date:** 2026-02-03
**Scout:** Haiku Agent ad2c66f
**Status:** RECONNAISSANCE COMPLETE

---

## EXECUTIVE SUMMARY

The codebase has a **robust foundation** for multi-source model display with provider tracking. Key systems are:
- **Model Duplicator** (Phase 94.4) - creates dual-source model entries
- **API Key Management** (Phase 57.12+) - unified key system with provider typing
- **Model Fetcher** (Phase 48+110) - merges models from multiple providers
- **UI Components** (Phase 80+111) - displays sources and filters by provider

---

## 1. MODEL DUPLICATOR SYSTEM

**File:** `src/services/model_duplicator.py`

| Line Range | Component | Purpose | Status |
|-----------|-----------|---------|--------|
| 1-11 | Header + Marker | PHASE 94.4 declaration | Active |
| 20-261 | `DUAL_SOURCE_MODELS` dict | Config mapping base model IDs to direct + OR versions | **NEEDS EXTENSION** |
| 264-272 | `has_active_key()` | Check if provider has non-rate-limited key | Active |
| 275-353 | `create_duplicates()` | **MARKER_94.4_CREATE_DUPLICATES** - Main duplication logic | Core |
| 313-324 | Direct API creation | Creates `source='direct'` + `source_display` field | Active |
| 325-334 | OpenRouter creation | Creates `source='openrouter'` + `source_display` field | Active |
| 336-351 | Non-dual handling | Preserves single-source models, adds default source field | Active |
| 356-380 | `get_duplication_stats()` | Returns statistics about duplication capacity | Utility |

### Current DUAL_SOURCE_MODELS Coverage:
- **XAI/Grok:** 12 models (grok-4, grok-4-fast, grok-4.1-fast, grok-3, etc.)
- **OpenAI/GPT:** 3 models (gpt-4o, gpt-4o-mini, gpt-4-turbo)
- **Anthropic/Claude:** 3 models (claude-3-5-sonnet, claude-3-5-haiku, claude-3-opus)
- **Google/Gemini:** 3 models (gemini-2.0-flash-exp, gemini-exp-1206, gemini-pro)

### What Needs to Change:
- ⚠️ Extend to `MULTI_SOURCE_MODELS` with array of sources
- ⚠️ Add Polza, NanoGPT, Poe as source options
- ⚠️ Change structure from `{direct, openrouter}` to `sources: []`

---

## 2. MODEL FETCHER INTEGRATION

**File:** `src/elisya/model_fetcher.py`

| Line Range | Component | Purpose | Status |
|-----------|-----------|---------|--------|
| 26-73 | `fetch_openrouter_models()` | Fetch from OR, adds `source='openrouter'` | Active |
| 50-62 | Source/provider fields | Sets `source` + extracts `provider` from ID | Active |
| 76-140 | `fetch_polza_models()` | Fetch Polza AI, sets `source='polza_direct'` | Active |
| 120-121 | Polza source | Sets `provider='Polza'` + `source='polza_direct'` | Active |
| 208-251 | `fetch_gemini_models()` | Fetch Gemini, sets `source='gemini_direct'` | Active |
| 240-241 | Gemini source | Sets `source='gemini_direct'` for all Gemini models | Active |
| 291-347 | `get_all_models()` | Main aggregation - merges from multiple providers | Core |
| 329-341 | **DEDUPLICATION BUG** | Checks `existing_ids` — filters out Polza chat models! | **NEEDS FIX** |

### Current Deduplication Logic (PROBLEM):
```python
# Line 334-337
existing_ids = {m['id'] for m in all_models}
for pm in polza_models:
    if pm['id'] not in existing_ids:  # Always false for GPT/Claude!
        all_models.append(pm)
```

### What Needs to Change:
- ⚠️ Remove deduplication OR add source prefix to IDs
- ⚠️ Option: `polza/openai/gpt-4o` instead of `openai/gpt-4o`
- ⚠️ Or: Store models with compound key `{id}@{source}`

---

## 3. API KEY MANAGEMENT

**File:** `src/utils/unified_key_manager.py`

| Line Range | Component | Purpose | Status |
|-----------|-----------|---------|--------|
| 33-45 | `ProviderType` enum | **CORE** - 8 defined providers | **INCOMPLETE** |
| 52-117 | `APIKeyRecord` class | Individual key storage + status tracking | Active |
| 120-174 | `UnifiedKeyManager.__init__()` | Initialize all provider key lists | Active |
| 263-311 | `get_key()` + `get_active_key()` | Retrieve keys by provider | Active |
| 516-590 | Config persistence | Load/save keys from config.json | Active |
| 652-660 | `validate_keys()` | Check which providers have keys | Active |

### Current ProviderType Enum:
```python
class ProviderType(Enum):
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    NANOGPT = "nanogpt"    # EXISTS but unused in fetcher!
    TAVILY = "tavily"
    XAI = "xai"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    # MISSING: POLZA, POE, MISTRAL
```

### What Needs to Change:
- ⚠️ Add `POLZA = "polza"`
- ⚠️ Add `POE = "poe"`
- ⚠️ Add `MISTRAL = "mistral"`
- ⚠️ Update `validate_keys()` to include new providers

---

## 4. UI COMPONENTS - MODEL DIRECTORY

**File:** `client/src/components/ModelDirectory.tsx`

| Line Range | Component | Purpose | Status |
|-----------|-----------|---------|--------|
| 15-35 | `Model` interface | Includes `source?` + `source_display?` fields | ✅ Ready |
| 29-30 | Source field markers | `source: 'direct' \| 'openrouter' \| 'local'` | ✅ Ready |
| 37-50 | `ProviderKeys` + `APIKeyInfo` | Key storage interface | ✅ Ready |
| 75 | `FilterType` | Filter categories ('all', 'local', 'free', etc.) | **NEEDS EXTENSION** |
| 151-153 | `isRefreshing` state | Phase 111 refresh state | ✅ Active |
| 229-256 | `handleRefresh()` | Phase 111 refresh function | ✅ Active |
| 258-264 | `isNewModel()` | Phase 111 NEW marker helper | ✅ Active |
| 271-303 | `filteredModels` | **NEEDS SOURCE FILTER** | ⚠️ Missing |
| 803-817 | NEW marker display | Phase 111 NEW badge | ✅ Active |
| 924-930 | **MARKER_94.4_SOURCE_BADGE** | Shows "via xAI", "via OR" | ✅ Ready |
| 981-1162 | Key drawer | Shows saved keys | **NEEDS CLICK FILTER** |

### Current Source Display (Lines 924-930):
```tsx
{model.source_display && !model.isLocal && model.type !== 'mcp_agent' && (
  <span style={{
    color: model.source === 'direct' ? '#888' : '#555',
    fontWeight: model.source === 'direct' ? 500 : 400
  }}>
    via {model.source_display}
  </span>
)}
```

### What Needs to Change:
- ⚠️ Add `sourceFilter` state (null | string)
- ⚠️ Add filter logic in `filteredModels` useMemo
- ⚠️ Add click handler on keys in drawer to set filter
- ⚠️ Visual indicator when filter is active

---

## 5. PROVIDER REGISTRY

**File:** `src/elisya/provider_registry.py`

| Line Range | Component | Purpose | Status |
|-----------|-----------|---------|--------|
| 64-73 | `Provider` enum | 7 providers defined | Active |
| 1014-1077 | `detect_provider()` | Route model ID to provider | Core |
| 1048-1069 | **MARKER_94.8_OPENROUTER_XAI** | x-ai/ prefix → OpenRouter | Bug fix |
| 1089-1165 | `call_model_v2()` | Execute call with explicit provider | Active |

### Detection Logic:
```
1. grok-* (no prefix) → XAI direct
2. openai/ or gpt-* → OPENAI
3. anthropic/ or claude-* → ANTHROPIC
4. google/ or gemini → GOOGLE
5. x-ai/ or xai/ → OPENROUTER (NOT direct XAI!)
6. : or ollama/ → OLLAMA
7. Default → OLLAMA
```

---

## 6. SUMMARY: READY vs. MISSING

| Feature | Status | Location | Action |
|---------|--------|----------|--------|
| Source field tracking | ✅ Ready | model_duplicator, model_fetcher | - |
| Dual-source duplicates | ✅ Ready | model_duplicator lines 275-353 | Extend to multi |
| API key enum | ⚠️ Partial | unified_key_manager line 33 | Add Polza/Poe/Mistral |
| Source display in UI | ✅ Ready | ModelDirectory lines 924-930 | - |
| Model deduplication | ❌ Bug | model_fetcher line 334 | Fix or prefix IDs |
| Source filter in UI | ❌ Missing | ModelDirectory filteredModels | Implement |
| Key click → filter | ❌ Missing | ModelDirectory key drawer | Implement |

---

## 7. IMPLEMENTATION PRIORITY

### Phase 112.1: Fix Deduplication
1. `model_fetcher.py` - Add source prefix to Polza model IDs
2. Or: Change dedup key to `{id}@{source}`

### Phase 112.2: Extend ProviderType
1. `unified_key_manager.py` - Add POLZA, POE, MISTRAL
2. `validate_keys()` - Include new providers

### Phase 112.3: Multi-Source Config
1. `model_duplicator.py` - Refactor to MULTI_SOURCE_MODELS
2. Support N sources per model (not just 2)

### Phase 112.4: UI Filter
1. `ModelDirectory.tsx` - Add sourceFilter state
2. Add filter logic in filteredModels
3. Add click handler on keys

---

**Report by:** Haiku Scout Agent
**Agent ID:** ad2c66f
