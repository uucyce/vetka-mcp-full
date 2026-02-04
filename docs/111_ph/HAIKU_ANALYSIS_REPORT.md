# HAIKU ANALYSIS REPORT - Phase 112 Model Routing
**Date:** 2026-02-03
**Analyzed by:** 6 Parallel Haiku Agents
**Focus:** Multi-source model routing, deduplication bugs, dead code

---

## EXECUTIVE SUMMARY

### CRITICAL BUG FOUND: React Key Collision

**File:** `client/src/components/ModelDirectory.tsx`
**Line:** 756
**Bug:** `key={model.id}` causes React to deduplicate models with same ID but different sources

**Impact:** When gpt-4o exists from both OpenRouter AND Polza:
- Both have `id: "openai/gpt-4o"`
- React sees duplicate keys → renders only ONE
- Polza version silently dropped → shows "via OR" even for Polza models

**FIX REQUIRED:**
```jsx
key={model._compound_key || `${model.id}@${model.source}`}
```

---

## DETAILED FINDINGS BY COMPONENT

### 1. MODEL_FETCHER.PY - Source Assignment ✅

**Status:** CORRECT IMPLEMENTATION

| Source | Assignment Location | Value |
|--------|---------------------|-------|
| OpenRouter | Line 57 | `source = 'openrouter'` |
| Polza | Line 125 | `source = 'polza'` |
| Polza Scraped | Line 200 | `source = 'polza_scraped'` |
| Gemini Direct | Line 248 | `source = 'gemini_direct'` |

**Compound Keys:** Generated correctly at lines 65, 249, 345
- Format: `{model_id}@{source}`
- Example: `openai/gpt-4o@polza`

**NO DEDUPLICATION BUG in model_fetcher:**
- Polza models added via `.extend()` without filtering (line 346)
- Comment explicitly states: "Phase 112: Add ALL Polza models"

---

### 2. MODEL_DUPLICATOR.PY - Logic Issues ⚠️

**MULTI_SOURCE_MODELS Config (Lines 33-185):**
- Correctly defines Polza source for 7/9 models
- GPT-4o, Claude models, Mistral all have Polza routes

**DEAD CODE FOUND (Line 285):**
```python
if model.get('source') == 'polza_direct':  # NEVER TRUE!
    model_copy['source'] = 'polza'
```
- Source `'polza_direct'` doesn't exist anywhere
- model_fetcher.py only sets: 'polza', 'polza_scraped', 'gemini_direct'
- **Action:** Remove dead code

**RECOVERY LOGIC (Lines 307-322):**
- Catches Polza models skipped by main loop
- **Issue:** Doesn't update model name with "(Polza)" suffix
- **Issue:** Doesn't set `source_display` consistently

**SKIP LOGIC (Lines 238-240):**
- Intentional: `if clean_id in processed_ids: continue`
- Recovery loop handles Polza models that match multi-source configs
- NOT A BUG - by design, but inconsistent with main loop behavior

---

### 3. MODEL_DIRECTORY.TSX - CRITICAL BUGS 🔴

**BUG #1: React Key (Line 756)** - CRITICAL
```jsx
<div key={model.id}>  // ❌ Causes dedup of same ID from different sources
```

**BUG #2: No Client-Side Dedup Protection**
- `allModels = [...localModels, ...mcpAgents, ...models]`
- No deduplication by compound key
- Relies entirely on backend

**"via OR" Marker (Lines 946-952):**
```jsx
{model.source_display && !model.isLocal && (
  <span>via {model.source_display}</span>
)}
```
- Works correctly IF `source_display` is set
- Bug is in React key causing wrong model to render

**Source Filter (Lines 286-300):**
- Filters by 5 fields: source, provider, source_display, id prefix, special mappings
- Special mappings correct: xai↔x-ai, mistral↔mistralai

---

### 4. SOLO CHAT MODEL FLOW ✅

**Files:** ChatPanel.tsx → useSocket.ts → user_message_handler.py → provider_registry.py

**Flow:**
1. ModelDirectory → `onSelect(modelId)`
2. ChatPanel stores `selectedModel` state
3. Socket.IO emit: `{model: selectedModel}`
4. Backend: `ProviderRegistry.detect_provider(model_id)`
5. Routes to correct provider API

**Source Field:** NOT used in backend routing
- Routing based purely on model ID prefix
- `xai/grok-4` → OpenRouter
- `grok-4` → XAI Direct

---

### 5. GROUP CHAT MODEL FLOW ✅

**Files:** group_chat_manager.py → group_message_handler.py → orchestrator_with_elisya.py

**Key Architecture:**
- Each `GroupParticipant` has explicit `model_id`
- Provider detected from model_id format
- Source field NOT used in backend

**Hardcoded Elements:**
- Hostess Router uses `qwen2:7b` (line 290)
- MCP agent names hardcoded in list (lines 80-95)

---

### 6. MCP MODEL CALLS (vetka_call_model) ✅

**File:** llm_call_tool.py

**Source Field:** NOT USED IN MCP ROUTING
- MCP schema has no `source` parameter
- Routing based purely on model name pattern matching
- Model name encodes routing decision

**Provider Detection:**
- `grok-4` → XAI
- `x-ai/grok-4` → OpenRouter
- `claude-3` → Anthropic
- `openai/gpt-4o` → OpenRouter

---

## ROOT CAUSE ANALYSIS

### Why Polza Models Show "via OR"

```
1. Backend correctly returns models from both sources:
   - {id: "openai/gpt-4o", source: "openrouter", source_display: "OR"}
   - {id: "openai/gpt-4o", source: "polza", source_display: "Polza"}

2. Frontend receives both in `models` array

3. React renders list with key={model.id}:
   - First model: key="openai/gpt-4o" → renders with "via OR"
   - Second model: key="openai/gpt-4o" → SKIPPED (duplicate key!)

4. Result: Only OpenRouter version visible, Polza silently dropped
```

---

## PRIORITY FIXES

### P0 - CRITICAL (Do First)

**ModelDirectory.tsx Line 756:**
```jsx
// BEFORE (BUG):
key={model.id}

// AFTER (FIX):
key={model._compound_key || `${model.id}@${model.source || 'unknown'}`}
```

### P1 - HIGH (After P0)

**model_duplicator.py Line 285-287:**
```python
# REMOVE THIS DEAD CODE:
if model.get('source') == 'polza_direct':
    model_copy['source'] = 'polza'
    model_copy['source_display'] = 'Polza'
```

### P2 - MEDIUM

**model_duplicator.py Lines 316-320:**
```python
# ADD NAME UPDATE to recovery logic:
polza_copy = {**pm}
polza_copy['source_display'] = pm.get('source_display', 'Polza')
polza_copy['name'] = f"{pm.get('name', pm_id)} ({polza_copy['source_display']})"
polza_copy['routes'] = [...]
```

### P3 - LOW

**Consider:** Remove recovery logic entirely
- MULTI_SOURCE_MODELS already handles Polza duplication
- Recovery may create redundant entries

---

## FILES TO MODIFY

| File | Change | Priority |
|------|--------|----------|
| `client/src/components/ModelDirectory.tsx` | Fix React key at line 756 | P0 |
| `src/services/model_duplicator.py` | Remove dead code lines 285-287 | P1 |
| `src/services/model_duplicator.py` | Add name/source_display to recovery | P2 |

---

## VERIFICATION STEPS

After fixes:
1. Run `curl -X POST localhost:5001/api/models/refresh`
2. Check API response: both OpenRouter AND Polza versions of gpt-4o
3. In UI: Search "gpt-4o" → should see multiple entries
4. Click each → verify different `source_display` values
5. Filter by Polza key → should show only Polza models

---

## GROK RESEARCH REQUEST

See separate file: `GROK_RESEARCH_REQUEST.md`
