# Phase 94: Jarvis Prompt Enricher Status

**Agent:** Haiku 2
**Date:** 2026-01-26
**Status:** PARTIAL - Working code but NOT connected to production

---

## 1. COMPONENT OVERVIEW

**Path:** `src/memory/jarvis_prompt_enricher.py`
**Lines:** 657
**Purpose:** Model-agnostic prompt enrichment with ELISION compression

---

## 2. ARCHITECTURE

### Enrichment Pipeline:
```
Raw Prompt
    ↓
┌─────────────────────────┐
│ 1. Context Injection    │
│    - User memory        │
│    - Session history    │
│    - Project context    │
└──────────┬──────────────┘
           ↓
┌─────────────────────────┐
│ 2. ELISION Compression  │
│    - 40-60% token save  │
│    - Semantic preserve  │
└──────────┬──────────────┘
           ↓
┌─────────────────────────┐
│ 3. Model Adaptation     │
│    - Format for target  │
│    - Token limit check  │
└─────────────────────────┘
           ↓
Enriched Prompt
```

---

## 3. KEY METHODS

| Method | Purpose | Status |
|--------|---------|--------|
| `enrich(prompt, model_id)` | Main entry point | EXISTS |
| `inject_context(prompt)` | Add user/session context | EXISTS |
| `compress_with_elision(text)` | Apply ELISION | EXISTS |
| `adapt_for_model(prompt, model)` | Model-specific format | EXISTS |

---

## 4. ELISION COMPRESSION

**Path:** `src/memory/elision.py`
**Purpose:** Lossy context compression (like JPEG for text)

### Compression Strategy:
| Level | Savings | Quality |
|-------|---------|---------|
| Light | 20-30% | Near-lossless |
| Medium | 40-50% | Good semantic |
| Heavy | 60-70% | Key points only |

### Algorithm:
1. Semantic chunking (by meaning, not chars)
2. Importance scoring (TF-IDF + position)
3. Selective pruning (keep high-score chunks)
4. Reference compression (dedupe repeated info)

---

## 5. INTEGRATION STATUS

### Current State: NOT WIRED INTO PRODUCTION

**Evidence:**
1. No imports in `src/elisya/api_gateway.py`
2. No imports in `src/elisya/provider_registry.py`
3. No calls from orchestrator
4. Module complete but orphaned

### Where It SHOULD Be Called:

| Location | Integration Point |
|----------|-------------------|
| `api_gateway.py` | Before `call_model()` |
| `orchestrator.py` | Before sending to Elisya |
| `provider_registry.py` | In `call_model_v2()` |

---

## 6. EXPECTED BENEFITS

When integrated:
| Benefit | Impact |
|---------|--------|
| Token savings | 40-60% fewer tokens |
| Cost reduction | Proportional to savings |
| Context fit | More history in window |
| Personalization | User memory injection |

---

## 7. REQUIRED CHANGES

### Option A: In api_gateway.py (recommended)

```python
from src.memory.jarvis_prompt_enricher import JarvisPromptEnricher

enricher = JarvisPromptEnricher()

async def call_model(model_id: str, messages: List[Dict], **kwargs):
    # Enrich before calling
    enriched_messages = await enricher.enrich(messages, model_id)
    return await _actual_call(model_id, enriched_messages, **kwargs)
```

### Option B: In provider_registry.py

```python
# In call_model_v2(), before API call:
from src.memory.jarvis_prompt_enricher import JarvisPromptEnricher
enricher = JarvisPromptEnricher()
messages = await enricher.enrich(messages, model)
```

---

## 8. DEPENDENCIES

| Dependency | Status | Notes |
|------------|--------|-------|
| ELISION module | EXISTS | `src/memory/elision.py` |
| Engram memory | PARTIAL | Needs integration |
| tiktoken | INSTALLED | Token counting |
| numpy | INSTALLED | Scoring |

---

## 9. ESTIMATED EFFORT

| Task | Lines | Time |
|------|-------|------|
| Import in api_gateway | +5 | 10 min |
| Add enrich() call | +10 | 15 min |
| Config for compression level | +15 | 20 min |
| Test with various models | - | 1 hour |

**Total:** ~30 lines, ~1.5 hours

---

## SUMMARY

Jarvis Prompt Enricher is COMPLETE but NOT CONNECTED. The 657-line module with ELISION compression is ready, just needs ~30 lines to wire into the request pipeline. Once active, expect 40-60% token savings.

**Priority:** HIGH - Direct cost savings + better context management.
