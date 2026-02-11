# Research Request: Multi-Source Model Aggregator System for VETKA
**Updated:** 2026-02-03 (Post-Haiku Analysis)

## CRITICAL BUG FOUND

**React Key Collision in ModelDirectory.tsx Line 756:**
```jsx
key={model.id}  // BUG: Causes dedup of same model from different sources
```

**Root Cause:** When `gpt-4o` exists from both OpenRouter AND Polza:
- Both have `id: "openai/gpt-4o"`
- React sees duplicate keys → renders only OpenRouter version
- Polza version silently dropped

**Proposed Fix:**
```jsx
key={model._compound_key || `${model.id}@${model.source || 'unknown'}`}
```

---

## Context

VETKA is an AI orchestration platform that supports multiple LLM providers. Currently we have:

**Configured API Keys (from config.json):**
- openrouter: 13 keys
- gemini: 3 keys
- xai: 6 keys
- openai: 2 keys
- polza: 1 key
- nanogpt: 1 key
- poe: 2 keys
- mistral: 1 key
- anthropic: 1 key
- tavily: 1 key

**Current Behavior:**
- Models fetched from OpenRouter (347), Gemini Direct (31), Polza (20 embedding only)
- `model_duplicator.py` creates dual entries for xAI models: `grok-4 (xAI)` + `grok-4 (OR)`
- Polza/Nano/Poe models are DEDUPLICATED because they have same IDs as OpenRouter (e.g., `openai/gpt-4o`)
- User sees only 2 sources: "via xAI" (direct) and "via OR" (openrouter)

**Problem:**
User has keys for Polza, NanoGPT, Poe but cannot see/select these aggregators in UI. All 333 Polza chat models are filtered out because their IDs match OpenRouter.

## Requirements

### 1. Multi-Source Model Display
Same model should appear multiple times if available from different sources:
```
GPT-4o (Direct) — via OpenAI API
GPT-4o (OR) — via OpenRouter
GPT-4o (Polza) — via Polza AI
GPT-4o (Nano) — via NanoGPT
```

### 2. Key-Based Filtering
When user clicks on API key in "API Keys" drawer:
- Filter model list to show only models available through that provider
- Highlight which source will be used for each model
- Show quota/limits if available

### 3. Provider Priority System
User should be able to set preference order:
1. Direct API (cheapest, fastest)
2. Polza (has different limits)
3. OpenRouter (fallback)

## Current Architecture

### model_duplicator.py (Phase 94.4)
```python
DUAL_SOURCE_MODELS = {
    "grok-4": {
        "direct": {"provider": "xai", "requires_key": ProviderType.XAI, "display_suffix": "xAI"},
        "openrouter": {"id_format": "x-ai/grok-4", "display_suffix": "OR"}
    },
    # ... only xAI, OpenAI, Anthropic, Gemini
}
```
**Limitation:** Only supports 2 sources (direct + openrouter), hardcoded for 4 providers.

### model_fetcher.py (Phase 110)
```python
# Deduplication prevents Polza models from being added
existing_ids = {m['id'] for m in all_models}
for pm in polza_models:
    if pm['id'] not in existing_ids:  # Always false for chat models!
        all_models.append(pm)
```

### unified_key_manager.py
```python
class ProviderType(Enum):
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    XAI = "xai"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    NANOGPT = "nanogpt"  # Exists but unused!
    # Missing: POLZA, POE, MISTRAL
```

## Questions for Research

1. **Architecture Pattern:** What's the best way to handle N sources for the same model?
   - Option A: Extend DUAL_SOURCE_MODELS to MULTI_SOURCE_MODELS with array of sources
   - Option B: Store models with compound keys (e.g., `openai/gpt-4o@polza`)
   - Option C: Separate "model" from "route" — model is unique, routes are many

2. **Aggregator APIs:**
   - NanoGPT: What's their API format? OpenAI-compatible?
   - Poe: Do they have public API for model listing?
   - How to detect which models each aggregator supports?

3. **UI/UX Pattern:**
   - How should multi-source models appear in list? Grouped? Separate?
   - Best practice for "click key to filter" interaction?
   - Should we show price comparison between sources?

4. **Routing Logic:**
   - When user selects `gpt-4o`, how to decide which source to use?
   - Should it auto-fallback if primary source fails?
   - How to track usage per-source for cost analysis?

## Deliverable Expected

1. Recommended architecture for MULTI_SOURCE_MODELS
2. Code snippets for:
   - Extended ProviderType enum
   - New model_fetcher logic (no deduplication, add source prefix)
   - UI filter component
3. API research for NanoGPT/Poe model listing
4. Priority queue implementation for source selection

## Haiku Scout Markers Report

### Files to Modify:

| File | Lines | What to Change |
|------|-------|----------------|
| `src/services/model_duplicator.py` | 21-261 | Extend DUAL_SOURCE_MODELS → MULTI_SOURCE_MODELS |
| `src/elisya/model_fetcher.py` | 329-341 | Remove deduplication, add source prefix to IDs |
| `src/utils/unified_key_manager.py` | 33-45 | Add POLZA, POE, MISTRAL to ProviderType |
| `client/src/components/ModelDirectory.tsx` | 271-303 | Add source filter in filteredModels |
| `client/src/components/ModelDirectory.tsx` | 981-1162 | Add click-to-filter on key drawer |

### Current Source Display (ModelDirectory.tsx:924-930):
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

### Provider Detection (provider_registry.py:1041-1076):
```
1. grok-* (no prefix) → XAI direct
2. openai/ or gpt-* → OPENAI
3. anthropic/ or claude-* → ANTHROPIC
4. google/ or gemini → GOOGLE
5. x-ai/ → OPENROUTER (not direct!)
6. Default → OLLAMA
```

## Attached Documents
- PHASE_111_STATUS_REPORT.md
- PHASE_111_FINAL_PLAN.md
- HAIKU_ANALYSIS_REPORT.md (NEW - detailed 6-agent analysis)

---

## HAIKU ANALYSIS SUMMARY (6 Parallel Agents)

### Agent 1: model_fetcher.py ✅
- Source fields assigned correctly
- NO deduplication bug in fetcher
- Compound keys generated properly

### Agent 2: model_duplicator.py ⚠️
- Dead code at lines 285-287 (checks 'polza_direct' which doesn't exist)
- Recovery logic (307-322) doesn't set name/source_display consistently

### Agent 3: ModelDirectory.tsx 🔴
- **P0 BUG:** Line 756 `key={model.id}` causes React dedup
- No client-side compound key dedup

### Agent 4: Solo Chat Flow ✅
- Source field NOT used in routing
- Routing based on model ID prefix only

### Agent 5: Group Chat Flow ✅
- Each participant has explicit model_id
- Source field NOT used in backend

### Agent 6: MCP Model Calls ✅
- vetka_call_model has no `source` parameter
- Routing via model name pattern matching

---

## QUESTIONS FOR GROK

### Primary Question
Is React key collision the root cause of "Polza models showing via OR"?

### Architecture Validation
1. Should `source` field be used in backend routing, or keep model-ID-based routing?
2. Is compound key pattern `{id}@{source}` the right solution?
3. Should we unify MULTI_SOURCE_MODELS with recovery logic, or remove recovery?

### Code Review Requests
1. Validate proposed fix for ModelDirectory.tsx line 756
2. Confirm dead code removal safe (lines 285-287)
3. Review recovery logic necessity (lines 307-322)
