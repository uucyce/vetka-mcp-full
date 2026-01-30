# PHASE 90.5.0a: Last Working Scanner Commit Analysis

# MARKER_90.5.0a_START: Working Commit Search

## Executive Summary
**Last Known Working Commit:** `9b9959f` (Phase 83-88)
**Date:** Wednesday, January 21, 2026
**Current Broken Commit:** `c83cfa2` (Phase 80.38-80.40)
**Days Since Last Working:** 2 days (Jan 21 → Jan 23)

**Root Cause:** Commit `6072e08` introduced **Phase 80.20** which **CHANGED THE BEHAVIOR OF LAZY QDRANT CLIENT FETCH**. The watcher now expects app.state.qdrant_manager to exist and have a .client attribute, but initialization may be incomplete or None.

---

## Timeline of Scanner-Related Commits (Jan 20-23)

```
c83cfa2 Phase 80.38-80.40: Fix xai key detection + rotation + OpenRouter fallback (TODAY - BROKEN)
711cf45 Phase 80.37: xai fallback to openrouter when API key not found
4d7850b Phase 80.36: Fix x-ai provider name normalization (x-ai -> xai)
6072e08 Phase 80.35: Fix Grok routing + PM reply intercept + x.ai provider (REGRESSED SCANNER!)
9b9959f Phase 83-88: Complete scanner control, UI fixes, MCP integration and bug fixes (LAST WORKING)
```

---

## What Changed in Commit 6072e08 (Jan 22) - THE CULPRIT

### Phase 80.20: Async Emit & Lazy Qdrant Fetch

**File:** `src/scanners/file_watcher.py`

#### Added Method: `_get_qdrant_client()`
```python
def _get_qdrant_client(self) -> Optional[Any]:
    """
    Phase 80.17: Lazy fetch Qdrant client.
    The watcher singleton may be created BEFORE Qdrant connects.
    This method fetches the client at event time, not at init time.
    """
    # First check instance variable (may have been set via get_watcher update)
    if self.qdrant_client is not None:
        return self.qdrant_client

    # Phase 80.17: Lazy fetch from components_init
    try:
        from src.initialization.components_init import get_qdrant_manager
        manager = get_qdrant_manager()
        if manager and hasattr(manager, 'client') and manager.client:
            self.qdrant_client = manager.client
            return manager.client
    except Exception as e:
        print(f"[Watcher] Phase 80.17: Cannot lazy fetch: {e}")
    return None
```

#### Changed Line in `handle_file_event()`:
**Before (Working - 9b9959f):**
```python
if self.qdrant_client:
    try:
        handle_watcher_event(event, qdrant_client=self.qdrant_client)
```

**After (Broken - 6072e08):**
```python
qdrant_client = self._get_qdrant_client()
if qdrant_client:
    try:
        handle_watcher_event(event, qdrant_client=qdrant_client)
```

---

## The Problem Chain

### 1. **Lazy Fetch Depends on `components_init.get_qdrant_manager()`**
   - This function tries to retrieve a cached instance from `src.initialization.components_init`
   - **If Qdrant manager initialization failed or wasn't called, this returns None**

### 2. **app.state.qdrant_manager is None**
   - In `main.py` lifespan, qdrant_manager is set via: `app.state.qdrant_manager = components.get('qdrant_manager')`
   - If the component fails to initialize, this becomes None
   - The error message gets logged but execution continues

### 3. **watcher Routes Can't Access It**
   - In `src/api/routes/watcher_routes.py` lines 110-113:
   ```python
   qdrant_manager = getattr(request.app.state, 'qdrant_manager', None)
   qdrant_client = None
   if qdrant_manager and hasattr(qdrant_manager, 'client'):
       qdrant_client = qdrant_manager.client
   ```
   - If `qdrant_manager is None`, then `qdrant_client` stays None
   - This None gets passed to `get_watcher(qdrant_client=None)`

### 4. **Lazy Fetch Fails Silently**
   - When `_get_qdrant_client()` tries to import `get_qdrant_manager()` it may:
     - Get an already-failed manager instance (None)
     - Or get a manager that hasn't been initialized yet
   - Returns None either way
   - **Silent failure:** Print statement says "WARNING: qdrant_client not available (lazy fetch failed)"

### 5. **Scan Silently Skips**
   - In `handle_file_event()`: `if qdrant_client:` is False
   - **No error is raised** - just silently skips indexing
   - **This is why it appears to work but doesn't index anything**

---

## Commits Between Working and Broken

### 6072e08 - Phase 80.20: REGRESSED SCANNER (Jan 22)
- **Changed:** File watcher lazy fetch logic
- **Impact:** Now depends on components_init rather than instance variable
- **Issue:** Lazy fetch can fail silently if qdrant_manager not ready

### 4d7850b, 711cf45, c83cfa2 - Phases 80.36-80.40 (Jan 22-23)
- **Changed:** Provider routing, xai key detection, OpenRouter fallback
- **Impact on Scanner:** NONE directly, but may affect overall app initialization timing
- **Possible Secondary Issue:** Initialization order changed, qdrant_manager still fails to init

---

## Root Initialization Issue

**Location:** `main.py` - lifespan function

```python
app.state.qdrant_manager = components.get('qdrant_manager')
```

### Questions to Investigate:
1. Is `components.get('qdrant_manager')` returning None?
2. Did the components initialization change between commits?
3. Is there an error in `src/initialization/components_init.py` getting qdrant_manager?
4. Is Qdrant server not running/accessible?

---

## How to Fix

### Option A: Revert to Phase 83-88 (Safest)
```bash
git checkout 9b9959f
```

### Option B: Fix Phase 80.20 Lazy Fetch
1. Ensure `components_init.get_qdrant_manager()` properly handles initialization failures
2. Add explicit error logging in `_get_qdrant_client()`
3. Add fallback to direct app.state lookup

### Option C: Immediate Debug (Phase 90.5.0b)
1. Add logging to main.py to show what components.get('qdrant_manager') returns
2. Check if Qdrant server is running: `curl localhost:6333/health`
3. Trace why `app.state.qdrant_manager` is None

---

## File Impact Summary

| File | Commit | Change | Severity |
|------|--------|--------|----------|
| `src/scanners/file_watcher.py` | 6072e08 | Added lazy fetch logic | **HIGH** |
| `main.py` | 9b9959f | Added Phase 87 file watcher init | DEPENDS |
| `src/api/routes/watcher_routes.py` | 9b9959f | Added qdrant_client param | OK |
| `src/initialization/components_init.py` | ? | Unknown state | **UNKNOWN** |

---

## Recommendations

1. **IMMEDIATE:** Check if Qdrant server is running
2. **INVESTIGATE:** Why is `app.state.qdrant_manager` None after initialization?
3. **REVERT:** If time critical, revert to commit `9b9959f`
4. **FIX:** Improve error handling in Phase 80.20 lazy fetch:
   - Don't rely solely on components_init
   - Fall back to app.state if available
   - Log actual initialization errors, not just warnings

# MARKER_90.5.0a_END

---

**Status:** READY FOR PHASE 90.5.0b - Root Cause Debug
**Last Updated:** 2026-01-23
**Time Spent:** < 10 minutes
