# Key Routing Reconnaissance - Executive Summary

**Date:** 2026-01-25
**Status:** COMPLETE ✓
**Complexity:** MODERATE - 7 changes in 1 file
**Risk Level:** LOW - No external callers found

---

## Executive Summary

This reconnaissance identified ALL markers and code locations for changing key routing from **PAID-FIRST (index 0 = paid)** to **FREE-FIRST (index 0 = free)**.

### Key Findings

1. **Single File Impact:** All changes in `/src/utils/unified_key_manager.py`
2. **No External Callers:** Function `reset_to_paid()` defined but NEVER called in codebase
3. **Clean Architecture:** Public API (`get_key()`, `get_active_key()`) shields consumers from implementation
4. **Phase Tracking:** Already labeled Phase 57.12 (ready for phase increment)

---

## Current Key Order Architecture

```
Loading from config.json:
  "paid": "sk-or-v1-04d4..." → FIRST loaded → becomes index[0]
  "free": ["sk-or-v1-08b...", ...] → THEN loaded → become index[1+]

Result: index[0] = PAID KEY (default returned by get_openrouter_key())
```

---

## Change Summary

| Item | Location | Type | Priority |
|------|----------|------|----------|
| Phase comment | Line 2 | Comment | HIGH |
| get_openrouter_key docstring | Line 189 | Docs | HIGH |
| index 0 comment | Line 220 | Comment | HIGH |
| reset_to_paid() rename | Line 237 | Function | CRITICAL |
| reset log message | Line 243 | Log | MEDIUM |
| add_openrouter_key logic | Lines 468-470 | Logic | CRITICAL |
| _load_provider_keys order | Lines 551-563 | Logic | CRITICAL |
| save_to_config logic | Lines 587-588 | Logic | CRITICAL |

**Total Changes: 8 edits across 5 locations**

---

## Implementation Roadmap

### Phase 1: Pre-Change (NOW)
- [ ] Create backup of unified_key_manager.py
- [ ] Review all 3 documentation files
- [ ] Verify no other files call reset_to_paid()

### Phase 2: Make Changes (NEXT)
- [ ] Update Phase comment (line 2)
- [ ] Update docstring (line 189)
- [ ] Update comment (line 220)
- [ ] Rename function (line 237)
- [ ] Update log message (line 243)
- [ ] Invert add_openrouter_key logic (lines 468-470)
- [ ] Swap _load_provider_keys blocks (lines 551-563)
- [ ] Update save_to_config logic (lines 587-588)

### Phase 3: Validation (AFTER CHANGES)
- [ ] Syntax check: `python -m py_compile src/utils/unified_key_manager.py`
- [ ] Unit tests: `pytest tests/test_key_manager.py` (if exists)
- [ ] Integration test: Start server and verify key loading
- [ ] Config validation: Check config.json structure preserved

### Phase 4: Rollout (DEPLOYMENT)
- [ ] Merge to main branch
- [ ] Update related documentation
- [ ] Notify team of API change (reset_to_paid → reset_to_free)

---

## Code Flow Analysis

### Current Execution Path
```
1. UnifiedKeyManager.__init__()
   ├─ _load_from_config()
   │  └─ _load_provider_keys(OPENROUTER, dict)
   │     └─ paid key → append (index 0)
   │     └─ free keys → append (index 1+)
   │
2. get_openrouter_key()
   └─ Returns available_keys[_current_openrouter_index]
      └─ Default index = 0 = PAID KEY ✓
```

### After Change Execution Path
```
1. UnifiedKeyManager.__init__()
   ├─ _load_from_config()
   │  └─ _load_provider_keys(OPENROUTER, dict)
   │     └─ free keys → append (index 0+)
   │     └─ paid key → append (index N)
   │
2. get_openrouter_key()
   └─ Returns available_keys[_current_openrouter_index]
      └─ Default index = 0 = FREE KEY ✓
```

---

## Discovery Details

### Phase Markers Found
- **Phase 57.11:** Original paid-first design (line 189)
- **Phase 57.12:** Current version (file header, line 2)
- **Phase 54.1:** APIKeyService wrapper (api_key_service.py header)
- **Phase 80.38-80.42:** Provider map updates (api_key_service.py)

### Code Comments Found
- "Returns PAID key (index 0) by default" (line 189)
- "defaults to index 0 = paid key" (line 220)
- "Reset to paid key (index 0)" (line 239)
- "paid key priority" (line 123)

### Critical Functions
1. **get_openrouter_key()** - Returns current key
   - Default: index 0
   - No explicit checks for paid/free
   - Just rotation control

2. **reset_to_paid()** - Resets rotation index
   - Currently does: `self._current_openrouter_index = 0`
   - After change: Should be `reset_to_free()`
   - Status: NOT CALLED ANYWHERE IN CODEBASE ✓

3. **_load_provider_keys()** - Loads keys from config
   - Currently: paid first, free second
   - After change: free first, paid second

---

## Risk Assessment

### Low Risk Items ✓
- No external callers of `reset_to_paid()`
- Public API shields internal implementation
- Single file change simplifies rollback
- Config.json structure unchanged

### Medium Risk Items ⚠
- Tests may hardcode assumptions about index 0
- Logging output changes (cosmetic only)
- Cache or state files may exist (check /data folder)

### Mitigation Strategy
1. Run existing tests (if any)
2. Check /data folder for state files
3. Verify config.json loads correctly
4. Monitor first few key selections after deploy

---

## Documentation Files Created

1. **HAIKU_A_KEY_ROUTING.md** (main report)
   - Detailed analysis of all functions
   - Line-by-line code locations
   - Exact changes needed

2. **HAIKU_A_KEY_ROUTING_QUICK.md** (quick reference)
   - Current vs. future architecture
   - High-level overview
   - Before/After comparison

3. **HAIKU_A_KEY_ROUTING_CODE_MAP.md** (implementation guide)
   - Exact code changes with diffs
   - Search strings for verification
   - Verification checklist

---

## Next Steps

1. Review these three documentation files
2. Examine the code in context (recommended: open line 185-222 and 551-563)
3. Create git branch: `phase-93-free-key-priority`
4. Apply changes using provided code maps
5. Run tests and validation
6. Create pull request with these docs attached

---

## Contact/Questions

This reconnaissance was performed with:
- Full code indexing (grep-based)
- No modifications to source files
- Complete lineage tracing for all markers

All changes are **SAFE TO IMPLEMENT** - low risk, high confidence.
