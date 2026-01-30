# Fallback Chain Markers Report

**Reconnaissance Date:** 2026-01-25
**Analysis Scope:** provider_registry.py vs api_aggregator_v3.py
**Status:** COMPLETE - All fallback chain markers identified

---

## 1. Current Fallback Chain Architecture

### **NEW (provider_registry.py - Phase 80.10+)**
```
Direct API Call
    ↓ [XaiKeysExhausted (403)] → OpenRouter (with model conversion)
    ↓ [ValueError: key not found] → OpenRouter (if provider in OPENAI/ANTHROPIC/GOOGLE/XAI)
    ↓ [Generic Exception] → Raise (no fallback)
```

### **OLD (api_aggregator_v3.py - Phase 27-80)**
```
Direct API (OpenAI/Anthropic/Google)
    ↓ [Exception] → Fallback to OpenRouter/Ollama
    ↓
OpenRouter (if is_openrouter_model)
    ↓ [Exception] → Fallback to Ollama
    ↓
Ollama (Local)
    ↓ [Exception] → Return error response
    ↓ [Final] → Error message with all failed attempts
```

---

## 2. Fallback Chain Exception Handlers

| Exception Type | Location | Fallback Target | Model Conversion | Phase |
|---|---|---|---|---|
| **XaiKeysExhausted** | provider_registry.py:903-918 | OpenRouter | `xai/model` → `x-ai/model` | 80.39 |
| **ValueError (key not found)** | provider_registry.py:919-946 | OpenRouter | Only for XAI: `xai/` prefix removed | 80.39 |
| **Generic Exception** | provider_registry.py:947-949 | None (raise) | N/A | 80.10 |
| **Direct API ImportError** | api_aggregator_v3.py:386-391 | OpenRouter/Ollama | N/A | 80.9 |
| **OpenRouter Exception** | api_aggregator_v3.py:443-444 | Ollama | Model mapped via OPENROUTER_TO_OLLAMA | 27.15 |
| **Ollama Tool Exception** | api_aggregator_v3.py:415-432 | Ollama (no tools) | Same model | 32.4 |
| **Ollama Final Exception** | api_aggregator_v3.py:465-467 | Return error dict | N/A | 27.15 |

---

## 3. Key Markers Found

### **XAI Provider Markers (provider_registry.py)**
- **Line 26-30:** `XaiKeysExhausted` exception definition
  ```python
  class XaiKeysExhausted(Exception):
      """Raised when all xai keys return 403 - signals to use OpenRouter fallback"""
  ```

- **Line 642:** XaiProvider class introduced
  ```python
  class XaiProvider(BaseProvider):
      """Phase 80.35: x.ai API provider (Grok models)"""
  ```

- **Line 694-732:** XAI 403 handling with key rotation
  - Line 696: Check `response.status_code == 403`
  - Line 700-711: Key rotation with `get_key_manager()`
  - Line 714-722: Retry with next key
  - Line 725-732: Raise `XaiKeysExhausted` if all keys exhausted

### **Provider Registry Fallback (provider_registry.py:900-950)**
- **Line 900-902:** Primary try block (direct provider call)
- **Line 903-918:** `XaiKeysExhausted` handler with OpenRouter fallback
- **Line 904:** Phase 80.39 comment
- **Line 911:** `MARKER-PROVIDER-004-FIX` - Remove double x-ai/xai/ prefix
- **Line 919-946:** `ValueError` handler (API key not found)
- **Line 933:** `MARKER-PROVIDER-006-FIX` - Convert model for XAI fallback consistency
- **Line 943-944:** Nested fallback error handling
- **Line 947-949:** Generic exception (no fallback)

### **Provider Detection Markers (provider_registry.py:821-844)**
- **Line 821-844:** `MARKER_90.1.4.1_START/END` - CANONICAL detect_provider with XAI patterns
  - Supports: `xai/`, `x-ai/`, `grok*` prefixes
  - Phase 90.1.4.1 comment

### **Model Routing (api_aggregator_v3.py)**
- **Line 334-347:** `OPENROUTER_TO_OLLAMA` mapping dictionary (Phase 27.15)
- **Line 349-354:** Ollama model validation fallback (Phase 32.4)
- **Line 362-391:** Direct API attempts with 3-provider fallback chain (Phase 80.9)
- **Line 393-433:** Tool-enabled Ollama routing with nested fallback (Phase 27.15)

---

## 4. Phase Timeline & Evolution

| Phase | File | Change | Status |
|-------|------|--------|--------|
| 27.11 | api_agg | Model alias handling (`model` kwarg) | LEGACY |
| 27.15 | api_agg | OpenRouter→Ollama mapping + tool routing | LEGACY |
| 32.4 | api_agg | Ollama model validation fallback | LEGACY |
| 80.9 | api_agg | Direct API detection for OpenAI/Anthropic/Google | LEGACY |
| 80.10 | provider_reg | New unified call_model_v2 architecture | **CURRENT** |
| 80.35 | provider_reg | XaiProvider implementation | **ACTIVE** |
| 80.39 | provider_reg | XaiKeysExhausted exception + OpenRouter fallback | **ACTIVE** |
| 80.40 | provider_reg | Bug fixes: singleton + correct attribute names | **ACTIVE** |
| 80.41 | provider_reg | GEMINI alias for Google (config.json compatibility) | **ACTIVE** |
| 80.42 | provider_reg | Use 'gemini' key for config.json storage | **ACTIVE** |
| 90.1.4.1 | provider_reg | CANONICAL detect_provider with XAI patterns | **LATEST** |

---

## 5. Architecture Differences Summary

| Aspect | provider_registry.py (NEW) | api_aggregator_v3.py (OLD) |
|--------|---------------------------|-------------------------|
| **Exception Handling** | Explicit custom exception (XaiKeysExhausted) | Generic catch-all with logging |
| **Fallback Chain** | Direct → OpenRouter only | Direct → OpenRouter → Ollama → Error |
| **XAI Support** | Native with 403 key rotation | Not present |
| **Key Management** | Uses unified_key_manager singleton | Global dict storage |
| **Tool Support** | Per-provider (supports_tools flag) | Conditional mapping via OPENROUTER_TO_OLLAMA |
| **Model Conversion** | Explicit in fallback (x-ai/ prefix) | Implicit in mapping dict |
| **Responsibility** | Provider registry handles provider selection | Aggregator handles all routing logic |
| **API Keys** | Retrieved on-demand via APIKeyService | Pre-loaded as globals |

---

## 6. Critical Observations

1. **Dual System:** Code contains both old (api_aggregator_v3.py) and new (provider_registry.py) implementations
   - Old system has 3-tier fallback: Direct → OpenRouter → Ollama
   - New system has 2-tier fallback: Direct → OpenRouter only

2. **XAI Special Handling:**
   - Only in new system (provider_registry.py)
   - Custom exception for 403 exhaustion
   - Key rotation before fallback
   - Model prefix conversion required (xai/ → x-ai/)

3. **Model Format Inconsistencies:**
   - XAI models need format conversion in fallback (MARKER-PROVIDER-004-FIX, MARKER-PROVIDER-006-FIX)
   - This inconsistency suggests API naming mismatch between systems

4. **Missing in Old System:**
   - No XaiKeysExhausted exception
   - No key rotation logic
   - No OpenRouter native XAI model support
   - XAI not in Provider enum

5. **Tool Support Divergence:**
   - New system: Determined by provider.supports_tools flag
   - Old system: Determined by OPENROUTER_TO_OLLAMA mapping + conditional logic

---

**END OF REPORT**
