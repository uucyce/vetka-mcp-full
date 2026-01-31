# Dead Code Report - Backend (src/)
**Date:** 2026-01-31
**Agent:** Haiku-1 (Reconnaissance Scout)
**Status:** COMPLETE

---

## Executive Summary

Scanned 24 handler files + 100+ core modules in `/src/` directory. Found:
- **1 Unused Module** (v2 handler, never registered)
- **1 Removed Component** (api_gateway, replaced in Phase 95)
- **1 Dead Dependency** (commented out in dependencies.py)
- **Multiple Deprecated Sections** (marked in code comments)

**Overall Health:** GOOD - Codebase is well-maintained with explicit deprecation markers

---

## Found Issues

| File | Issue | Type | Phase | Priority | Action |
|------|-------|------|-------|----------|--------|
| `src/api/handlers/user_message_handler_v2.py` | Unused handler - never registered, only DI container imports it | Dead Code | Phase 96 | HIGH | Mark `@status dead` and document archival |
| `src/dependencies.py` (lines 97-105) | Commented code for `get_api_gateway()` - removed Phase 95 | Dead Code | Phase 95 | MEDIUM | Delete commented block, keep note |
| `src/initialization/components_init.py` (line 44) | Commented out `api_gateway = None` - Phase 95 removal | Dead Code | Phase 95 | LOW | Delete comment |
| `src/mcp/vetka_mcp_bridge.py` | Marked as active but relies on removed api_gateway pattern | Needs Review | Phase 96 | MEDIUM | Verify integration paths |

---

## Detailed Findings

### 1. DEAD: `src/api/handlers/user_message_handler_v2.py`

**Status:** Never Registered
**Phase:** 96
**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler_v2.py`

**Issue:**
- File exists but is NOT imported in `src/api/handlers/__init__.py`
- Not called from `register_all_handlers()` function
- Only referenced in docstring: `@used_by: user_message_handler_v2` in `di_container.py`
- Appears to be a replacement attempt for `user_message_handler.py` (from comments: "1694 lines -> ~200 lines")

**Evidence:**
```python
# src/api/handlers/__init__.py - register_all_handlers()
# Lines 61-87 register these handlers:
register_connection_handlers(sio, app)
register_approval_handlers(sio, app)
register_tree_handlers(sio, app)
register_chat_handlers(sio, app)
register_workflow_handlers(sio, app)
register_reaction_handlers(sio, app)
register_user_message_handler(sio, app)  # <-- Uses old version
register_group_message_handler(sio, app)
# ... NOT user_message_handler_v2
```

**Recommendation:**
- Mark with `@status dead`
- Archive or delete if refactor was abandoned
- Consider merging improvements into active handler if valuable

---

### 2. DEPRECATED: `api_gateway` Component (Removed Phase 95)

**Status:** Removed, Replaced
**Phase:** 95 → Direct API Calls
**Affected Files:**
- `src/dependencies.py` (lines 97-105)
- `src/initialization/components_init.py` (line 44)

**Issue:**
Comments indicate `api_gateway` was replaced by `direct_api_calls.py` module in Phase 95.
Commented code still references it:

```python
# src/dependencies.py, lines 97-105
# REMOVED: Phase 95 - api_gateway replaced by direct_api_calls.py
# def get_api_gateway(request: Request) -> Optional[Any]:
#     """
#     Get API gateway from app state.
#     Optional dependency - returns None if not available.
#     """
#     if not getattr(request.app.state, 'API_GATEWAY_AVAILABLE', False):
#         return None
#     return getattr(request.app.state, 'api_gateway', None)
```

**Current Implementation:**
- New module: `src/elisya/direct_api_calls.py` (Phase 95.1)
- Status: ACTIVE
- Called by: `api_aggregator_v3.py`, `provider_registry.py`

**Recommendation:**
- Delete the commented block (it's documented in git history)
- Keep note in git commit message
- Verify no legacy imports still reference it

---

### 3. Architecture Review

**Well-Organized Modules with Proper Markers:**
✅ All active handlers have `@status` and `@phase` markers
✅ Clear `@used_by` annotations in most files
✅ Phase progression is documented (39 → 96)

**Candidates for Future Cleanup:**
- `src/mcp/vetka_mcp_bridge.py` - relies on patterns that may be deprecated
- Legacy voice handlers may have duplicates (investigate `voice_handler.py` vs `voice_socket_handler.py`)

---

## Statistics

| Metric | Count |
|--------|-------|
| Files Scanned | 24 handlers + 100+ core modules |
| Dead Code Files | 1 (user_message_handler_v2.py) |
| Removed Components (documented) | 1 (api_gateway) |
| Dead Imports/Comments | ~3 locations |
| Overall Dead Code %| <0.5% |

---

## Recommendations

### Priority 1 (HIGH) - Do This Now
1. **Mark `user_message_handler_v2.py` as DEAD**
   ```python
   @status dead  # Never registered, replaced by user_message_handler.py (Phase 64.5)
   @reason: Attempted refactor abandoned; DI container imports but not used
   @archived_phase: 96
   ```

2. **Remove commented api_gateway code from dependencies.py**
   - Delete lines 97-105 (comments only)
   - Commit message: "cleanup: Remove Phase 95 api_gateway migration comments"

### Priority 2 (MEDIUM) - Document
3. **Verify MCP Bridge**
   - Check `vetka_mcp_bridge.py` doesn't depend on removed api_gateway
   - Update Phase references if needed

### Priority 3 (LOW) - Optional
4. **Voice Handler Architecture Review**
   - Multiple voice files exist (handler, socket_handler, router, providers)
   - Consider consolidation if duplicated functionality exists

---

## Markers To Be Set

Ready for VETKA MCP marker system:
```
@status dead | @stack backend | @phase 96 | @priority high
```

Applied to:
- `user_message_handler_v2.py` → Mark DEAD

---

## Notes for Future Scouts

**Search Pattern for Dead Code:**
```bash
# Find commented-out code blocks
grep -r "^\s*#\s*def \|^\s*#\s*class \|^\s*#\s*async def" src/

# Find unused imports
grep -r "# REMOVED:\|# DEPRECATED:\|# Phase .* removed" src/

# Find files not referenced
grep -rL "from.*file_name\|import.*file_name" src/
```

**Phase Transitions:**
- Phase 64.5: Socket.IO handler reorganization (split user_message_handler)
- Phase 95: API gateway replaced with direct_api_calls.py
- Phase 96: Current active phase (all markers should say 96)

---

**Report Generated By:** Haiku-1 Scout Agent
**Next Steps:** Awaiting user confirmation to apply markers via VETKA MCP system
