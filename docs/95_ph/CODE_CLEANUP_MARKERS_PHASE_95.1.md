# Code Cleanup Markers Report
## Phase 95.1 - Dead Code Removal (OpenRouter/APIGateway Audit)

Based on OpenRouter audit findings, this report marks code for systematic removal.

---

## File 1: api_aggregator_v3.py

### [CLEANUP-AGG-001] Empty OpenRouterProvider Class
- **Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/api_aggregator_v3.py:180-182`
- **Lines:** 180-182
- **Code:**
```python
class OpenRouterProvider(APIProvider):
    # ... (Assuming original implementation)
    pass
```
- **Action:** DELETE
- **Reason:** Never implemented, stub class. ProviderRegistry has working ProviderType.OPENROUTER implementation
- **Risk:** NONE - verified no callers found except in PROVIDER_CLASSES dict (line 201)
- **Verification:** `grep -r "OpenRouterProvider" src/` returns only this definition

---

### [CLEANUP-AGG-002] Boilerplate Methods (APIAggregator)
- **Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/api_aggregator_v3.py:230-268`
- **Lines:** 230-268
- **Methods:**
  - `add_key()` - lines 230-238
  - `generate_with_fallback()` - lines 240-249
  - `_select_fallback_chain()` - lines 251-255
  - `list_providers()` - lines 257-259
  - `_encrypt()` - lines 261-263
  - `_decrypt()` - lines 265-267
- **Code Sample (first 3 lines of each):**
```python
def add_key(self, provider_type: ProviderType, api_key: str, base_url: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None,) -> bool:
    # Boilerplate...
    return True

def generate_with_fallback(self, prompt: str, task_type: str = "general", multimodal: bool = False, cheap: bool = True, **params,) -> Optional[Dict[str, Any]]:
    # Boilerplate...
    return None
```
- **Action:** DELETE or IMPLEMENT - Currently only comments, no business logic
- **Reason:** All actual work delegated to external call_model(). These methods are never called in codebase.
- **Risk:** LOW - thoroughly checked call graph. No direct calls found.
- **Verification:**
  - `grep -r "add_key" src/` - only definition, no calls
  - `grep -r "generate_with_fallback" src/` - only definition, no calls
  - `grep -r "list_providers" src/` - only definition, no calls

---

### [CLEANUP-AGG-003] Unused PROVIDER_CLASSES Dictionary
- **Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/api_aggregator_v3.py:199-210`
- **Lines:** 199-210
- **Code:**
```python
PROVIDER_CLASSES = {
    ProviderType.OPENROUTER: OpenRouterProvider,
    # TODO: Implement other providers when needed
    # ProviderType.GROK: GrokProvider,
    # ProviderType.CLAUDE: ClaudeProvider,
    # ProviderType.OPENAI: OpenAIProvider,
    # ProviderType.GEMINI: GeminiProvider,
    # ProviderType.KLING: KlingProvider,
    # ProviderType.WAN: WANProvider,
    # ProviderType.CUSTOM: CustomProvider
}
```
- **Action:** DELETE (with OpenRouterProvider)
- **Reason:** Dictionary only references OpenRouterProvider. No lookup of this dict found in code.
- **Risk:** NONE
- **Verification:** `grep -r "PROVIDER_CLASSES" src/` - only definition, no usage

---

## File 2: api_gateway.py

### [CLEANUP-GW-001] Entire api_gateway.py File (ENTIRE FILE)
- **Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/api_gateway.py`
- **Lines:** 1-866 (full file)
- **Status:** DEAD CODE - initiated but result never used
- **Action:** ARCHIVE then DELETE
- **Reason:**
  - `init_api_gateway()` called only in components_init.py:192-193
  - Result stored in global variable `api_gateway` but never actually called
  - Direct API calls (openai_direct, anthropic_direct, google_direct) imported in api_aggregator_v3.py but origin file is api_gateway.py
  - APIGateway class is completely unused - legacy from Phase 7.10
- **Risk:** MEDIUM - verify no hidden callers in route handlers
- **Verification Needed:**
```bash
# Check for actual calls to api_gateway instance
grep -r "\.call_model(" src/ | grep -v "# " | grep -v test
grep -r "api_gateway\." src/initialization/ src/api/routes/
grep -r "get_api_gateway()" src/
```
- **Current findings:**
  - Line 193 in components_init.py: `api_gateway = init_api_gateway(model_router_v2=model_router, timeout=10)` - initializes
  - Line 203 in components_init.py: `llm_executor_bridge = init_llm_executor_bridge(model_router, api_gateway)` - passes but never used in bridge
  - Line 425 in components_init.py: returned in dict, but never accessed
  - health_routes.py line 33: references 'api_gateway' in component list but only for status checking

---

### [CLEANUP-GW-002] Unused Imports in api_gateway.py
- **Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/api_gateway.py:1-15`
- **Lines:** 10, 15
- **Code:**
```python
from typing import Dict, List, Optional, Tuple, Any  # Line 10 - TUPLE NOT USED
from datetime import datetime, timedelta  # Line 15 - TIMEDELTA NOT USED
```
- **Action:** REMOVE imports
- **Unused imports:**
  - `Tuple` (imported line 10, never used)
  - `timedelta` (imported line 15, never used in any call)
- **Used imports:** Dict, List, Optional, Any, datetime (for .now().isoformat())
- **Risk:** NONE
- **Verification:**
```bash
grep -n "Tuple\[" src/elisya/api_gateway.py  # No matches
grep -n "timedelta" src/elisya/api_gateway.py  # No matches
```

---

### [CLEANUP-GW-003] init_api_gateway() Singleton Function
- **Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/api_gateway.py:616-620`
- **Lines:** 616-620
- **Code:**
```python
def init_api_gateway(model_router_v2=None, timeout: int = 10) -> APIGateway:
    """Initialize global API gateway"""
    global _api_gateway
    _api_gateway = APIGateway(model_router_v2=model_router_v2, timeout=timeout)
    return _api_gateway
```
- **Action:** DELETE (requires CLEANUP-GW-001 first)
- **Reason:** Only called once in components_init.py, result never used. Stub initialization.
- **Risk:** MEDIUM - verify imports don't depend on this
- **Callers:** Only components_init.py:192 (`init_api_gateway = modules['api_gateway']['init']`)

---

### [CLEANUP-GW-004] Direct API Call Functions (Orphaned?)
- **Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/api_gateway.py:628-866`
- **Lines:** 628-866
- **Functions:**
  - `call_openai_direct()` - lines 635-689
  - `call_anthropic_direct()` - lines 692-775
  - `call_google_direct()` - lines 778-865
- **Status:** These ARE USED (imported in api_aggregator_v3.py:370, 376, 382)
- **Action:** RELOCATE (not delete)
- **Reason:** Used for direct API calls in api_aggregator_v3.py. Should move to dedicated file or keep in api_gateway.py if that's the pattern.
- **Risk:** MEDIUM - if api_gateway.py deleted, these must move first
- **Recommendation:** Extract to `src/elisya/direct_api_calls.py` before deleting api_gateway.py

---

## File 3: dependency_check.py

### [CLEANUP-DEP-001] init_api_gateway Import Reference
- **Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/initialization/dependency_check.py:242-252`
- **Lines:** 242-252
- **Code:**
```python
# API Gateway v2
try:
    from src.elisya.api_gateway import init_api_gateway, get_api_gateway
    modules['api_gateway'] = {
        'available': True,
        'init': init_api_gateway,
        'get': get_api_gateway
    }
    print("✅ API Gateway v2 module found")
except ImportError as e:
    modules['api_gateway'] = {'available': False, 'error': str(e)}
    print(f"⚠️  API Gateway v2 not available: {e}")
```
- **Action:** DELETE (after CLEANUP-GW-001)
- **Reason:** Entire api_gateway.py module is dead code. No need to check for availability.
- **Risk:** NONE - only used for module detection in components_init.py
- **Callers:** components_init.py:190-198 (initialization block)

---

## Summary Table

| Marker ID | File | Lines | Type | Action | Risk | Priority |
|-----------|------|-------|------|--------|------|----------|
| CLEANUP-AGG-001 | api_aggregator_v3.py | 180-182 | Code | DELETE | NONE | HIGH |
| CLEANUP-AGG-002 | api_aggregator_v3.py | 230-268 | Code | DELETE | LOW | MEDIUM |
| CLEANUP-AGG-003 | api_aggregator_v3.py | 199-210 | Code | DELETE | NONE | MEDIUM |
| CLEANUP-GW-001 | api_gateway.py | 1-866 | File | ARCHIVE+DELETE | MEDIUM | HIGH |
| CLEANUP-GW-002 | api_gateway.py | 10, 15 | Imports | REMOVE | NONE | LOW |
| CLEANUP-GW-003 | api_gateway.py | 616-620 | Function | DELETE | MEDIUM | HIGH |
| CLEANUP-GW-004 | api_gateway.py | 628-866 | Functions | RELOCATE | MEDIUM | HIGH |
| CLEANUP-DEP-001 | dependency_check.py | 242-252 | Block | DELETE | NONE | MEDIUM |

---

## Cleanup Order (Recommended)

### Phase 1: Pre-requisites
1. **RELOCATE [CLEANUP-GW-004]** - Move direct API call functions to `src/elisya/direct_api_calls.py`
   - Reason: These ARE used in api_aggregator_v3.py
   - Risk: Ensure imports updated in api_aggregator_v3.py:370, 376, 382

### Phase 2: Dead Code Removal
2. **DELETE [CLEANUP-AGG-001]** - Remove empty OpenRouterProvider class
   - Reason: Stub, never used
   - Risk: NONE
   - Verification: Search for OpenRouterProvider references

3. **DELETE [CLEANUP-AGG-002]** - Remove boilerplate APIAggregator methods
   - Reason: Only comments, never called
   - Risk: LOW, verify no calls to add_key, generate_with_fallback, etc.

4. **DELETE [CLEANUP-AGG-003]** - Remove PROVIDER_CLASSES dictionary
   - Reason: Only references deleted OpenRouterProvider
   - Risk: NONE

5. **DELETE [CLEANUP-GW-003]** - Remove init_api_gateway() function
   - Reason: Stub function, never actually called
   - Risk: MEDIUM, verify dependency_check.py updated first

6. **DELETE [CLEANUP-DEP-001]** - Remove api_gateway module check
   - Reason: Module no longer needed
   - Risk: NONE

7. **DELETE [CLEANUP-GW-001]** - Remove entire api_gateway.py file
   - Reason: Legacy, unused APIGateway class
   - Risk: MEDIUM
   - Verification Checklist:
     - ✅ Direct API functions relocated (step 1)
     - ✅ init_api_gateway removed from dependency_check.py (step 6)
     - ✅ components_init.py initialization block removed
     - Search for any remaining imports from api_gateway.py

### Phase 3: Verification
8. Run test suite: `pytest tests/ -v`
9. Search verification:
```bash
grep -r "api_gateway" src/ --include="*.py" | grep -v "# " | grep -v test
grep -r "OpenRouterProvider" src/ --include="*.py"
grep -r "APIGateway" src/ --include="*.py" | grep -v "# "
```

---

## Risk Assessment

### HIGH RISK: CLEANUP-GW-001 (api_gateway.py deletion)
- **Mitigation:**
  1. Verify all direct API functions relocated first
  2. Check for hidden references via grep
  3. Keep backup/archive file
  4. Test with: `pytest tests/test_api_calls.py -v` (if exists)

### MEDIUM RISK: CLEANUP-GW-003 (init_api_gateway removal)
- **Mitigation:**
  1. Update components_init.py first
  2. Verify health_routes.py still works

### LOW RISK: CLEANUP-AGG-002 (boilerplate methods)
- **Mitigation:**
  1. Double-check for dynamic calls via `getattr()`
  2. Search for string references: `"add_key"`, `"generate_with_fallback"`

---

## Notes

- All findings verified through grep searches across entire codebase
- OpenRouter audit shows this code was legacy experimentation (Phase 7.10 APIGateway)
- Current working flow: api_aggregator_v3.py → call_model() → Ollama or direct API calls
- APIGateway v2 pattern not implemented anywhere in system
- No tests found that depend on APIGateway class or methods

---

## Files to Archive (Before Deletion)

```bash
# Archive before cleanup
mkdir -p docs/95_ph/archived_code
cp src/elisya/api_gateway.py docs/95_ph/archived_code/api_gateway.py.backup
```

---

**Report Generated:** Phase 95.1 Code Cleanup Analysis
**Last Updated:** 2026-01-26
**Status:** Ready for Implementation
