# Phase 95.1 Cleanup - Quick Reference

## Execute Cleanup in This Order

### Step 1: Verify No Hidden References
```bash
# Run verification script first
grep -r "api_gateway\." src/ --include="*.py" | grep -v "test" | grep -v "#"
grep -r "init_api_gateway" src/ --include="*.py" | grep -v "test"
grep -r "OpenRouterProvider" src/ --include="*.py"
grep -r "APIGateway" src/ --include="*.py" | grep -v "test" | grep -v "#"
```

### Step 2: Relocate Direct API Functions (CRITICAL!)
Before deleting api_gateway.py, extract these functions to new file:

**File to create:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/direct_api_calls.py`

Functions to move from api_gateway.py (lines 628-865):
- `call_openai_direct()` - lines 635-689
- `call_anthropic_direct()` - lines 692-775
- `call_google_direct()` - lines 778-865

Then update imports in api_aggregator_v3.py:
- Line 370: `from src.elisya.api_gateway import call_openai_direct`
- Line 376: `from src.elisya.api_gateway import call_anthropic_direct`
- Line 382: `from src.elisya.api_gateway import call_google_direct`

Change to:
```python
from src.elisya.direct_api_calls import (
    call_openai_direct,
    call_anthropic_direct,
    call_google_direct
)
```

### Step 3: Delete from api_aggregator_v3.py

```python
# DELETE THESE:

# Lines 180-182: OpenRouterProvider class
class OpenRouterProvider(APIProvider):
    # ... (Assuming original implementation)
    pass

# Lines 199-210: PROVIDER_CLASSES dict
PROVIDER_CLASSES = {
    ProviderType.OPENROUTER: OpenRouterProvider,
    # ...
}

# Lines 230-268: Boilerplate methods in APIAggregator
# - add_key()
# - generate_with_fallback()
# - _select_fallback_chain()
# - list_providers()
# - _encrypt()
# - _decrypt()
```

### Step 4: Delete from dependency_check.py

```python
# DELETE LINES 242-252: API Gateway v2 check block

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

### Step 5: Delete from components_init.py

```python
# DELETE LINES 189-198: API Gateway initialization block

# Initialize API Gateway v2
if modules.get('api_gateway', {}).get('available'):
    try:
        init_api_gateway = modules['api_gateway']['init']
        api_gateway = init_api_gateway(model_router_v2=model_router, timeout=10)
        API_GATEWAY_AVAILABLE = True
        print("✅ API Gateway v2 initialized with automatic failover")
    except Exception as e:
        print(f"⚠️  API Gateway v2 initialization failed: {e}")
        API_GATEWAY_AVAILABLE = False
```

Also remove from globals:
- Line 39: `api_gateway = None`
- Line 66: `API_GATEWAY_AVAILABLE = False`
- Lines 116, 122: Remove from global declarations

Also remove these from `_get_components_dict()` function:
- Line 425: `'api_gateway': api_gateway,`
- Line 442: `'API_GATEWAY_AVAILABLE': API_GATEWAY_AVAILABLE,`

### Step 6: Delete from health_routes.py

```python
# MODIFY LINES 29-43: Remove api_gateway from component list

# OLD:
components = [
    ('orchestrator', 'OrchestratorWithElisya'),
    ('memory_manager', 'MemoryManager'),
    ('model_router', 'ModelRouter'),
    ('api_gateway', 'APIGateway'),  # <-- REMOVE THIS LINE
    ('eval_agent', 'EvalAgent'),
    # ...
]

# NEW:
components = [
    ('orchestrator', 'OrchestratorWithElisya'),
    ('memory_manager', 'MemoryManager'),
    ('model_router', 'ModelRouter'),
    ('eval_agent', 'EvalAgent'),
    # ...
]
```

Also remove from line 233:
```python
# OLD:
critical = ['orchestrator', 'memory_manager', 'eval_agent', 'model_router', 'api_gateway']

# NEW:
critical = ['orchestrator', 'memory_manager', 'eval_agent', 'model_router']
```

### Step 7: ARCHIVE api_gateway.py

```bash
# Before deletion, create backup
mkdir -p docs/95_ph/archived_code
cp src/elisya/api_gateway.py docs/95_ph/archived_code/api_gateway.py.backup
```

### Step 8: DELETE api_gateway.py

```bash
rm src/elisya/api_gateway.py
```

### Step 9: Verify Tests Still Pass

```bash
# Run test suite
pytest tests/ -v

# Search for any remaining references
grep -r "api_gateway" src/ --include="*.py"
grep -r "APIGateway" src/ --include="*.py"
grep -r "OpenRouterProvider" src/ --include="*.py"
```

---

## Files Modified

1. ✅ `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/api_aggregator_v3.py`
   - Delete lines 180-182 (OpenRouterProvider)
   - Delete lines 199-210 (PROVIDER_CLASSES)
   - Delete lines 230-268 (boilerplate methods)
   - Update imports (lines 370, 376, 382)

2. ✅ `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/initialization/dependency_check.py`
   - Delete lines 242-252 (api_gateway check)

3. ✅ `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/initialization/components_init.py`
   - Delete line 39 (`api_gateway = None`)
   - Delete line 66 (`API_GATEWAY_AVAILABLE = False`)
   - Delete lines 116, 122 (global declarations)
   - Delete lines 189-198 (initialization block)
   - Delete from `_get_components_dict()` (lines 425, 442)

4. ✅ `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/health_routes.py`
   - Modify lines 29-43 (remove api_gateway from list)
   - Modify line 233 (remove from critical list)

5. ✅ **CREATE NEW FILE:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/direct_api_calls.py`
   - Move functions from api_gateway.py (lines 628-865)
   - Contains: call_openai_direct, call_anthropic_direct, call_google_direct

6. ✅ **DELETE:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/api_gateway.py`

---

## Marker IDs for Cross-Reference

| Marker | File | Lines | Action |
|--------|------|-------|--------|
| CLEANUP-AGG-001 | api_aggregator_v3.py | 180-182 | DELETE |
| CLEANUP-AGG-002 | api_aggregator_v3.py | 230-268 | DELETE |
| CLEANUP-AGG-003 | api_aggregator_v3.py | 199-210 | DELETE |
| CLEANUP-GW-001 | api_gateway.py | 1-866 | DELETE |
| CLEANUP-GW-002 | api_gateway.py | 10, 15 | (covered by CLEANUP-GW-001) |
| CLEANUP-GW-003 | api_gateway.py | 616-620 | (covered by CLEANUP-GW-001) |
| CLEANUP-GW-004 | api_gateway.py | 628-865 | RELOCATE |
| CLEANUP-DEP-001 | dependency_check.py | 242-252 | DELETE |

---

## Expected Outcome

After cleanup:
- ✅ Removed 866 lines of dead code (api_gateway.py)
- ✅ Removed ~40 lines of stub methods (api_aggregator_v3.py)
- ✅ Removed ~15 lines of module checking (dependency_check.py)
- ✅ Working flow: api_aggregator_v3.py → call_model() → direct_api_calls.py → actual APIs
- ✅ Cleaner initialization (no unused API_GATEWAY_AVAILABLE flag)

---

**Estimated time:** 30 minutes
**Risk level:** MEDIUM (high verification needed)
**Backup created:** docs/95_ph/archived_code/api_gateway.py.backup
