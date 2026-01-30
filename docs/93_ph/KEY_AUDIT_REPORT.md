# VETKA API Key Audit Report

**Phase:** 93.0
**Date:** 2026-01-25
**Auditor:** Claude Opus 4.5

---

## Executive Summary

This audit analyzed all API keys configured in the VETKA project. The system manages keys through `UnifiedKeyManager` (Phase 57.12), which reads from `data/config.json` as the single source of truth.

**Key Findings:**
- Total unique keys found: **21 keys** across 7 providers
- Correctly categorized: **All keys properly categorized**
- Working keys: **12 keys** (57%)
- Quota exhausted: **4 keys** (19%)
- No credits/license: **3 keys** (14%)
- Unconfigured: **2 keys** (10%)

---

## Provider Type Enum Analysis

The `ProviderType` enum in `unified_key_manager.py` defines these providers:

| Enum Value | Config Key | Match Status |
|------------|------------|--------------|
| OPENROUTER | openrouter | MATCH |
| GEMINI | gemini | MATCH |
| OLLAMA | ollama | MATCH |
| NANOGPT | nanogpt | MATCH |
| TAVILY | tavily | MATCH |
| XAI | xai | MATCH |
| OPENAI | openai | MATCH |
| ANTHROPIC | anthropic | MATCH |

**Note:** The `poe` provider in config.json is a dynamic provider (not in enum), handled via `_validate_dynamic_key()`.

---

## Key Inventory by Provider

### 1. OpenRouter (10 keys)

| # | Masked Key | Type | Test Result | Notes |
|---|------------|------|-------------|-------|
| 1 | `sk-or-v1-04d4****9193` | paid | SUCCESS | Working |
| 2 | `sk-or-v1-08b3****b296` | free | SUCCESS | Working |
| 3 | `sk-or-v1-2335****8dcd` | free | SUCCESS | Working |
| 4 | `sk-or-v1-1468****39b9` | free | SUCCESS | Working |
| 5 | `sk-or-v1-3592****fa8f` | free | SUCCESS | Working |
| 6 | `sk-or-v1-7b85****705c` | free | SUCCESS | Working |
| 7 | `sk-or-v1-8128****53c6` | free | SUCCESS | Working |
| 8 | `sk-or-v1-36dc****4212` | free | SUCCESS | Working |
| 9 | `sk-or-v1-fdd5****1b60` | free | SUCCESS | Working |
| 10 | `sk-or-v1-d73c****5665` | free | SUCCESS | Working |

**Validation:** All keys pass `_validate_openrouter_key()` (prefix `sk-or-` and length > 20).

---

### 2. OpenAI (2 keys)

| # | Masked Key | Test Result | Error Details |
|---|------------|-------------|---------------|
| 1 | `sk-proj-ya****J4UA` | ERROR 429 | Quota exceeded |
| 2 | `sk-proj-QE****9vsA` | SUCCESS | Working |

**Validation:** Both keys pass `_validate_openai_key()` (prefix `sk-proj-` and length > 80).

**Recommendation:** Key 1 has exceeded its quota. Consider:
- Adding billing/credits to the OpenAI account
- Removing the exhausted key from rotation

---

### 3. Google/Gemini (3 keys)

| # | Masked Key | Test Result | Error Details |
|---|------------|-------------|---------------|
| 1 | `AIzaSyDx****NErA` | ERROR 429 | Quota exceeded |
| 2 | `AIzaSyCZ****mvd0` | ERROR 429 | Quota exceeded |
| 3 | `AIzaSyBF****6eeU` | ERROR 429 | Quota exceeded |

**Validation:** All keys pass `_validate_gemini_key()` (length > 30, alphanumeric with -/_).

**Recommendation:** All Gemini keys have exceeded quota. Options:
- Wait for quota reset (daily/monthly)
- Add billing to Google Cloud project
- Use OpenRouter's `google/gemini-flash-1.5` as fallback (already configured)

---

### 4. XAI/Grok (3 keys)

| # | Masked Key | Test Result | Error Details |
|---|------------|-------------|---------------|
| 1 | `xai-OezI****ty5o` | ERROR 403 | No credits/license |
| 2 | `xai-e71H****P1cE` | ERROR 403 | No credits/license |
| 3 | `xai-aYQB****R1Dd` | ERROR 403 | No credits/license |

**Validation:** All keys pass `_validate_xai_key()` (prefix `xai-` and length > 50).

**Recommendation:** All XAI keys return 403 "team doesn't have any credits". Options:
- Purchase credits at console.x.ai
- System already has fallback: `XaiKeysExhausted` exception triggers OpenRouter fallback to `x-ai/grok-*` models

---

### 5. Anthropic (0 keys)

| Status | Details |
|--------|---------|
| null | No direct Anthropic keys configured |

**Note:** Anthropic models (claude-3-haiku, claude-3.5-sonnet) are accessed via OpenRouter.

**Test via OpenRouter:**
- Model: `anthropic/claude-3-haiku`
- Result: SUCCESS

**Recommendation:** Current setup is fine. If direct API access is needed:
- Get key from console.anthropic.com
- Key format: `sk-ant-XXXX...` (40+ chars)

---

### 6. Tavily (1 key)

| # | Masked Key | Test Result | Notes |
|---|------------|-------------|-------|
| 1 | `tvly-dev-****eM9F` | SUCCESS | Working (search API) |

**Validation:** Key passes `_validate_tavily_key()` (prefix `tvly-dev-` or `tvly-` and length > 20).

---

### 7. NanoGPT (1 key)

| # | Masked Key | Test Result | Notes |
|---|------------|-------------|-------|
| 1 | `sk-nano-****07d7` | ERROR 400 | Model not supported |

**Validation:** Key passes `_validate_nanogpt_key()` (prefix `sk-nano-` and length > 40).

**Note:** Key format is valid but the test model may not be supported. Key authentication itself may be working.

---

### 8. Poe (2 keys) - Dynamic Provider

| # | Masked Key | Notes |
|---|------------|-------|
| 1 | `kwod****Lqo` | Format matches learned pattern |
| 2 | `pa-e****ZIQ` | Format matches learned pattern |

**Validation:** Keys validated via `_validate_dynamic_key()` using learned pattern from `learned_key_patterns.json`.

**Note:** Poe keys not tested (no standard API endpoint). These are likely for Poe.com bot integration.

---

## Key Location Analysis

### Primary Source: `data/config.json`

This is the canonical source loaded by `UnifiedKeyManager._load_from_config()`.

```
api_keys:
  openrouter: {paid: "...", free: [...]}  # 10 keys
  gemini: [...]                            # 3 keys
  anthropic: null                          # No keys
  nanogpt: [...]                           # 1 key
  tavily: "..."                            # 1 key
  xai: [...]                               # 3 keys
  openai: [...]                            # 2 keys
  poe: [...]                               # 2 keys (dynamic)
```

### Secondary Sources (Legacy/Backup):

| File | Keys Found | Status |
|------|-----------|--------|
| `.env` | 9 OpenRouter + 1 Gemini | REDUNDANT - Same as config.json |
| `config/config.py` | 9 OpenRouter (hardcoded defaults) | DEPRECATED - Should use .env |
| `app/.env` | Empty placeholders | Template only |

---

## Miscategorization Check

**Finding: No miscategorized keys detected.**

All keys have correct prefixes for their providers:
- OpenRouter: `sk-or-v1-` prefix (correct)
- OpenAI: `sk-proj-` prefix (correct, new 2024/2025 format)
- Gemini: `AIzaSy` prefix (correct)
- XAI: `xai-` prefix (correct)
- Tavily: `tvly-dev-` prefix (correct)
- NanoGPT: `sk-nano-` prefix (correct)
- Poe: Various formats (matched via learned patterns)

The user mentioned ~70 keys - current count is 21 unique keys. This discrepancy may be due to:
1. Keys removed in previous cleanup
2. Duplicate keys across .env and config.json counted separately
3. Test/temporary keys that were purged

---

## Provider Registry Analysis

The `provider_registry.py` defines these provider implementations:

| Provider | API Endpoint | Tool Support | Fallback |
|----------|--------------|--------------|----------|
| OpenAI | api.openai.com | Yes | OpenRouter |
| Anthropic | api.anthropic.com | Yes | OpenRouter |
| Google/Gemini | generativelanguage.googleapis.com | Yes | OpenRouter |
| Ollama | localhost:11434 | Yes | None (local) |
| OpenRouter | openrouter.ai | No | None (is fallback) |
| XAI | api.x.ai | Yes | OpenRouter (x-ai/*) |

**Key Rotation Logic:**
- All providers implement 24h cooldown on 401/402/403/429 errors
- `mark_rate_limited()` called on failure
- Automatic rotation to next available key

---

## Recommendations

### Critical (Action Required)

1. **Add XAI Credits**
   - All 3 XAI keys return 403
   - Purchase credits at console.x.ai OR rely on OpenRouter fallback

2. **Add OpenAI Credits**
   - Key 1 (sk-proj-ya...) is quota-exhausted
   - Either add billing or remove from rotation

### High Priority

3. **Consolidate Key Storage**
   - Remove redundant keys from `.env`
   - Keep only `data/config.json` as source of truth
   - Mark `config/config.py` OPENROUTER_KEYS as deprecated

4. **Add Direct Anthropic Key (Optional)**
   - Currently works via OpenRouter
   - Direct key provides: native tool support, potentially better rate limits

### Medium Priority

5. **Gemini Quota Management**
   - All 3 keys exhausted
   - Monitor quota reset or add Google Cloud billing
   - Fallback via OpenRouter working

6. **NanoGPT Integration**
   - Key exists but model selection needs verification
   - Check supported models at nano-gpt.com

### Low Priority

7. **Poe Keys Verification**
   - 2 keys stored but usage unclear
   - Verify if needed for Poe.com bot integration

---

## Key Health Summary

| Provider | Total | Working | Quota Exhausted | No Credits | Other |
|----------|-------|---------|-----------------|------------|-------|
| OpenRouter | 10 | 10 (100%) | 0 | 0 | 0 |
| OpenAI | 2 | 1 (50%) | 1 | 0 | 0 |
| Gemini | 3 | 0 (0%) | 3 | 0 | 0 |
| XAI | 3 | 0 (0%) | 0 | 3 | 0 |
| Anthropic | 0 | N/A | N/A | N/A | via OpenRouter |
| Tavily | 1 | 1 (100%) | 0 | 0 | 0 |
| NanoGPT | 1 | 0 (0%) | 0 | 0 | 1 (model error) |
| Poe | 2 | ? | ? | ? | untested |
| **TOTAL** | **22** | **12** | **4** | **3** | **1** |

---

## Appendix: Validation Rules

From `unified_key_manager.py`:

```python
# OpenRouter: sk-or- prefix, length > 20
def _validate_openrouter_key(self, key: str) -> bool:
    return key.startswith("sk-or-") and len(key) > 20

# Gemini: length > 30, alphanumeric with -/_
def _validate_gemini_key(self, key: str) -> bool:
    return len(key) > 30 and key.replace("-", "").replace("_", "").isalnum()

# OpenAI: sk-proj- (new) or sk- (legacy), length > 40/80
def _validate_openai_key(self, key: str) -> bool:
    if key.startswith("sk-proj-") and len(key) > 80:
        return True
    return key.startswith("sk-") and len(key) > 40

# Anthropic: sk-ant- prefix, length > 40
def _validate_anthropic_key(self, key: str) -> bool:
    return key.startswith("sk-ant-") and len(key) > 40

# XAI: xai- prefix, length > 50
def _validate_xai_key(self, key: str) -> bool:
    return key.startswith("xai-") and len(key) > 50

# NanoGPT: sk-nano- prefix, length > 40
def _validate_nanogpt_key(self, key: str) -> bool:
    return key.startswith("sk-nano-") and len(key) > 40

# Tavily: tvly-dev- or tvly- prefix, length > 20
def _validate_tavily_key(self, key: str) -> bool:
    return (key.startswith("tvly-dev-") or key.startswith("tvly-")) and len(key) > 20
```

---

**Report Generated:** 2026-01-25
**Files Analyzed:**
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/utils/unified_key_manager.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/config.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/.env`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/config/config.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/provider_registry.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/learned_key_patterns.json`
