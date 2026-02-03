# VETKA API Key Management System - Audit Report
## Phase 110: Comprehensive Security & Architecture Audit

**Date:** 2026-02-03
**Methodology:** 9 Haiku scouts (reconnaissance) → 3 Sonnet verifiers (validation)
**Status:** All findings VERIFIED

---

## Executive Summary

The VETKA API Key Management System supports 70+ LLM providers but has **critical bugs** and **security vulnerabilities** that require immediate attention. This audit identified:

- **3 Critical Bugs** (runtime crashes)
- **4 Security Vulnerabilities** (data exposure)
- **4 Integration Gaps** (missing functionality)

---

## Part 1: Critical Bugs (VERIFIED)

### BUG-1: DETECTION_ORDER.insert(20) - CONFIRMED
**File:** `src/elisya/key_learner.py:343`
**Severity:** MEDIUM

```python
# Line 341-343
if pattern.prefix and provider not in APIKeyDetector.DETECTION_ORDER:
    # Insert after unique prefixes (around position 20)
    APIKeyDetector.DETECTION_ORDER.insert(20, provider)  # ← BUG!
```

**Problem:** All new patterns are inserted at fixed position 20, regardless of list length. This causes:
- Detection order corruption when multiple patterns are learned
- Later patterns overwrite earlier ones' priority
- Unpredictable detection behavior

**Fix Required:**
```python
# Option 1: Append to end
APIKeyDetector.DETECTION_ORDER.append(provider)

# Option 2: Calculate proper position based on confidence
position = self._calculate_insertion_position(pattern.confidence)
APIKeyDetector.DETECTION_ORDER.insert(position, provider)
```

---

### BUG-2: report_failure() AttributeError - CONFIRMED
**File:** `src/utils/unified_key_manager.py:335-337`
**Severity:** CRITICAL (runtime crash)

```python
# Lines 335-337
if auto_rotate and provider == ProviderKey.OPENROUTER:
    old_idx = self.current_key_index.get(provider, 0)  # ❌ AttributeError!
    self.rotate_to_next(provider)                       # ❌ TypeError!
    new_idx = self.current_key_index.get(provider, 0)
```

**Problems:**
1. `self.current_key_index` does NOT exist - only `self._current_openrouter_index` (int)
2. `rotate_to_next()` takes no arguments - signature is `def rotate_to_next(self) -> None:`

**Fix Required:**
```python
if auto_rotate and provider == ProviderType.OPENROUTER:
    old_idx = self._current_openrouter_index
    self.rotate_to_next()  # No argument!
    new_idx = self._current_openrouter_index
```

---

### BUG-3: SaveAPIKeyTool Missing - CONFIRMED
**File:** `src/agents/hostess_agent.py:706`
**Severity:** CRITICAL (ImportError)

```python
# Line 706
from src.agents.tools import SaveAPIKeyTool  # ❌ Class does not exist!
```

**Problem:**
- `SaveAPIKeyTool` is referenced in imports and tool permissions but never implemented
- Causes `ImportError` when Hostess agent tries to save API keys
- `save_api_key` tool is broken

**Verified:** Searched entire codebase - `class SaveAPIKeyTool` returns 0 matches.

**Fix Required:** Implement `SaveAPIKeyTool` in `src/agents/tools.py`:
```python
class SaveAPIKeyTool(BaseTool):
    """Tool for saving API keys with auto-detection."""
    name = "save_api_key"

    async def execute(self, key: str, provider: str = "auto") -> ToolResult:
        from src.elisya.api_key_detector import detect_api_key
        from src.elisya.key_learner import get_key_learner
        # Implementation...
```

---

## Part 2: Security Vulnerabilities (VERIFIED)

### SEC-1: Plaintext Key Storage - CRITICAL
**File:** `data/config.json`
**Risk:** HIGH

All API keys stored in plaintext JSON without encryption:
```json
{
  "api_keys": {
    "openrouter": {
      "paid": "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",
      "free": ["sk-or-v1-...", "sk-or-v1-..."]
    },
    "gemini": ["AIzaSyDxID6HnNc5Zn2ww5EUE-U6lQruR8VNErA"],
    "xai": ["xai-...80+ chars..."]
  }
}
```

**Impact:** Any process with read access gets ALL API keys.

**Recommendation:**
1. Use environment variables for sensitive keys
2. Implement AES-256 encryption for stored keys
3. Consider OS keychain integration (macOS Keychain, Windows Credential Manager)

---

### SEC-2: Mask Reveals Key Fragments - HIGH
**File:** `src/utils/unified_key_manager.py:66-70, 648`

```python
# Line 66-70
def mask(self) -> str:
    return f"{self.key[:4]}****{self.key[-4:]}"  # Reveals prefix AND suffix!

# Line 648 - WORSE!
def mask_key(self, key: str) -> str:
    return f"{key[:10]}***{key[-4:]}"  # Reveals 10 chars + 4 suffix!
```

**Impact:** Log files contain key fragments that can be used for:
- Provider identification (prefix)
- Key correlation attacks (suffix)

**Recommendation:**
```python
def mask(self) -> str:
    return f"{self.key[:4]}****"  # Only prefix, no suffix
```

---

### SEC-3: Insecure File Permissions - MEDIUM
**File:** `data/learned_key_patterns.json`
**Permissions:** `644` (world-readable)

```
-rw-r--r--@ 1 danilagulin staff 1448 Feb 3 17:23 learned_key_patterns.json
```

**Impact:** All users can read key patterns (provider names, prefixes, lengths).

**Recommendation:**
```bash
chmod 600 data/learned_key_patterns.json
chmod 600 data/config.json
```

---

### SEC-4: Thread-Unsafe Singleton - HIGH
**File:** `src/utils/unified_key_manager.py:745-754`

```python
_unified_manager: Optional[UnifiedKeyManager] = None

def get_key_manager() -> UnifiedKeyManager:
    global _unified_manager
    if _unified_manager is None:
        _unified_manager = UnifiedKeyManager()  # ← RACE CONDITION!
    return _unified_manager
```

**Impact:**
- Multiple UnifiedKeyManager instances in memory
- Conflicting writes to config.json
- Broken key rotation

**Recommendation:**
```python
import threading

_lock = threading.Lock()
_unified_manager: Optional[UnifiedKeyManager] = None

def get_key_manager() -> UnifiedKeyManager:
    global _unified_manager
    with _lock:
        if _unified_manager is None:
            _unified_manager = UnifiedKeyManager()
    return _unified_manager
```

---

## Part 3: Integration Gaps (VERIFIED)

### GAP-1: Polza AI Not Integrated - CONFIRMED
**Files:** `src/elisya/model_fetcher.py`, `data/config.json`

**Situation:**
- API key exists: `pza_hU0ySdRapRzLsNhyGFQTCTatPyLb9PUM`
- Pattern learned in `learned_key_patterns.json`
- BUT: No `fetch_polza_models()` function exists!

**Current fetchers:**
- `fetch_openrouter_models()` ✓
- `fetch_gemini_models()` ✓
- `fetch_polza_models()` ❌ MISSING

**Polza AI Integration Info:**
```python
# Base URL: https://api.polza.ai/api/v1
# Auth: Bearer token in Authorization header
# Models list: https://polza.ai/models (scrape) or /v1/models (OpenAI-compatible)
# SDK: Use OpenAI SDK with base_url override
```

---

### GAP-2: No Model Refresh API - CONFIRMED
**File:** `src/api/routes/model_routes.py`

**Missing endpoint:** `POST /api/models/refresh`

**Existing endpoints:**
- GET `/api/models` - list all
- GET `/api/models/available` - online only
- GET `/api/models/status` - health per-model
- POST `/api/models/health/{model_id}` - force health check
- ❌ No way to force cache refresh via API

**Recommendation:** Add refresh endpoint:
```python
@router.post("/refresh")
async def refresh_models(force: bool = True):
    models = await get_all_models(force_refresh=force)
    return {'status': 'refreshed', 'count': len(models)}
```

---

### GAP-3: Missing Provider Patterns - CONFIRMED
**File:** `data/learned_key_patterns.json`

**Covered (5):** polza, tavily, xai, openai, poe

**Missing patterns for providers WITH keys in config:**
| Provider | Keys in config | Pattern | Status |
|----------|---------------|---------|--------|
| openrouter | 13 (1 paid + 12 free) | ❌ | MISSING |
| gemini | 3 | ❌ | MISSING |
| nanogpt | 1 | ❌ | MISSING |
| mistral | 1 | ❌ | MISSING |

**Note:** These providers have keys but no learned patterns. Detection relies on static patterns in `api_key_detector.py`.

---

### GAP-4: Doctor Tool Doesn't Validate Keys - CONFIRMED
**File:** `src/mcp/tools/doctor_tool.py`

**Current health checks:**
- `check_ollama_health()` ✓
- `check_deepseek_health()` ✓
- `check_mcp_bridge_health()` ✓
- `check_api_keys_health()` ❌ MISSING

**Recommendation:** Add key validation to Doctor Tool:
```python
async def check_api_keys_health(self) -> HealthCheckResult:
    """Validate all configured API keys via provider endpoints."""
    from src.elisya.api_key_detector import APIKeyDetector

    results = []
    for provider, keys in config['api_keys'].items():
        for key in keys:
            # Try HEAD request to validation_endpoint
            valid = await self._validate_key(provider, key)
            results.append({'provider': provider, 'valid': valid})

    return HealthCheckResult(
        component="api_keys",
        status=HealthStatus.HEALTHY if all(r['valid'] for r in results) else HealthStatus.DEGRADED,
        details={'keys': results}
    )
```

---

## Part 4: Architecture Overview

### Current API Key Flow
```
User pastes key → hostess_agent.py (save_api_key tool)
                         ↓
                  api_key_detector.py (70+ static patterns)
                         ↓
              ┌──────────┴──────────┐
              ↓                     ↓
         DETECTED              NOT DETECTED
              ↓                     ↓
    unified_key_manager      key_learner.py
    (save to config.json)    (analyze + learn)
                                    ↓
                             User confirms provider
                                    ↓
                             Save pattern + key
```

### Key Files Summary
| File | Purpose | Lines | Issues |
|------|---------|-------|--------|
| `api_key_detector.py` | Static pattern detection (70+ providers) | 730 | Overlapping patterns |
| `key_learner.py` | Dynamic pattern learning | 499 | insert(20) bug |
| `unified_key_manager.py` | Key storage & rotation | 754 | 2 critical bugs |
| `hostess_agent.py` | User interface tools | 1009 | Missing SaveAPIKeyTool |
| `doctor_tool.py` | Health diagnostics | 293 | No key validation |
| `model_fetcher.py` | Model list fetching | 318 | No Polza support |
| `config_routes.py` | REST API endpoints | ~400 | No refresh endpoint |

---

## Part 5: Recommended Fix Priority

### Immediate (P0) - Within 24h
1. **BUG-2:** Fix `report_failure()` AttributeError
2. **BUG-3:** Implement `SaveAPIKeyTool`
3. **SEC-4:** Add thread lock to singleton

### High Priority (P1) - Within 1 week
4. **BUG-1:** Fix DETECTION_ORDER insertion
5. **SEC-2:** Fix mask to hide suffix
6. **SEC-3:** Set file permissions to 600
7. **GAP-1:** Implement Polza AI fetcher

### Medium Priority (P2) - Within 2 weeks
8. **SEC-1:** Implement key encryption (AES-256)
9. **GAP-2:** Add `/api/models/refresh` endpoint
10. **GAP-4:** Add key validation to Doctor Tool

### Low Priority (P3) - Backlog
11. **GAP-3:** Add patterns for missing providers
12. TruffleHog integration for pattern base
13. Sparse SLM sanitizer for unknown keys
14. Federated pattern sharing system

---

## Appendix A: Test Commands

```bash
# Verify BUG-2
grep -n "current_key_index" src/utils/unified_key_manager.py
# Expected: No matches for attribute definition

# Verify BUG-3
grep -rn "class SaveAPIKeyTool" src/
# Expected: 0 matches

# Verify SEC-3
ls -la data/learned_key_patterns.json
# Should show 644, needs 600

# Verify GAP-1
grep -n "polza" src/elisya/model_fetcher.py
# Expected: 0 matches
```

---

## Appendix B: Haiku Scout → Sonnet Verifier Matrix

| Scout | Target | Findings | Verifier | Status |
|-------|--------|----------|----------|--------|
| Haiku 1 | api_key_detector.py | 70+ patterns, conflicts | - | Validated |
| Haiku 2 | key_learner.py | insert(20) bug | Sonnet 1 | ✅ CONFIRMED |
| Haiku 3 | unified_key_manager.py | 2 bugs, 4 sec issues | Sonnet 1, 2 | ✅ CONFIRMED |
| Haiku 4 | hostess_agent.py | Missing SaveAPIKeyTool | Sonnet 1 | ✅ CONFIRMED |
| Haiku 5 | doctor_tool.py | No key validation | Sonnet 3 | ✅ CONFIRMED |
| Haiku 6 | model_fetcher.py | No Polza fetcher | Sonnet 3 | ✅ CONFIRMED |
| Haiku 7 | config_routes.py | No refresh endpoint | Sonnet 3 | ✅ CONFIRMED |
| Haiku 8 | learned_key_patterns.json | 5 patterns, 4 missing | Sonnet 3 | ✅ CONFIRMED |
| Haiku 9 | key_handlers.py | Socket handlers OK | - | Validated |

---

**Report prepared by:** Claude Opus (Architect)
**Methodology:** Haiku reconnaissance + Sonnet verification
**Next Phase:** Implementation of P0 fixes
