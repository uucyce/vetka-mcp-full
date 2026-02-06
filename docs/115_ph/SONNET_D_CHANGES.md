# SONNET-D: Chat Hygiene Fix - Changes Summary

## Phase 115 - BUG-1: Chat Hygiene Fix
**Date:** 2026-02-06
**Agent:** Claude Sonnet 4.5 (SONNET-D)
**Status:** ✅ COMPLETE

---

## Changes Made

### File: `src/api/handlers/user_message_handler.py`

#### Change 1: Line 375 (Ollama Local Model Path)
**Location:** Ollama direct model call path
**Marker:** `MARKER_115_BUG1`

```python
# BEFORE:
chat_id = chat_history.get_or_create_chat('unknown', context_type='topic', display_name=semantic_chat_key)

# AFTER:
chat_id = chat_history.get_or_create_chat(
    'unknown',
    context_type='topic',
    display_name=semantic_chat_key,
    chat_id=client_chat_id  # MARKER_115_BUG1: Chat hygiene fix
)
```

**Impact:** Prevents duplicate chat creation when using local Ollama models in solo chat mode.

---

#### Change 2: Line 1264 (CAM Event Emission #5)
**Location:** Hostess routing CAM event emission
**Marker:** `MARKER_115_BUG1`

```python
# BEFORE:
chat_id = chat_history.get_or_create_chat(
    'unknown',
    context_type='topic',
    display_name=chat_display_name
)

# AFTER:
chat_id = chat_history.get_or_create_chat(
    'unknown',
    context_type='topic',
    display_name=chat_display_name,
    chat_id=client_chat_id  # MARKER_115_BUG1: Chat hygiene fix
)
```

**Impact:** Prevents duplicate chat creation during CAM event emission in Hostess routing path.

---

#### Change 3: Line 2054 (Agent Chain CAM Event #6)
**Location:** Agent chain response CAM event emission
**Marker:** `MARKER_115_BUG1`

```python
# BEFORE:
chat_id = chat_history.get_or_create_chat(
    'unknown',
    context_type='topic',
    display_name=chat_display_name
)

# AFTER:
chat_id = chat_history.get_or_create_chat(
    'unknown',
    context_type='topic',
    display_name=chat_display_name,
    chat_id=client_chat_id  # MARKER_115_BUG1: Chat hygiene fix
)
```

**Impact:** Prevents duplicate chat creation during agent chain response emission.

---

## No Changes Required

### Files Verified (No Issues Found):
- ✅ `src/api/handlers/context/context_builders.py` - Uses real file paths, not `'unknown'`
- ✅ `src/api/handlers/orchestration/response_manager.py` - Uses real file paths
- ✅ `src/api/handlers/mention/mention_handler.py` - Uses real file paths
- ✅ `src/chat/chat_history_manager.py` - Backend logic already correct (FIX_109.4 infrastructure exists)

---

## Technical Details

### Root Cause
Frontend-backend chat ID mismatch caused by missing `client_chat_id` parameter in 3 out of 7 `get_or_create_chat()` calls with null-context (`'unknown'` path).

### Solution
Apply existing FIX_109.4 pattern consistently across all 7 call sites in `user_message_handler.py`.

### Backend Support
The backend (`chat_history_manager.py` lines 285-292) already had the infrastructure to accept `client_chat_id`:
```python
# FIX_109.4: Use client-provided chat_id if available (unified ID system like groups)
if chat_id and chat_id not in self.history["chats"]:
    # Use provided ID
    print(f"[ChatHistory] Using client-provided chat_id: {chat_id}")
else:
    # Generate new ID
    chat_id = str(uuid.uuid4())
```

This was implemented in Phase 109.4 but not applied to all call sites until now.

---

## Verification

### All 7 Call Sites Now Consistent:
1. ✅ Line 375 - `MARKER_115_BUG1` (NEW)
2. ✅ Line 557 - `FIX_109.4` (existing)
3. ✅ Line 790 - `FIX_109.4` (existing)
4. ✅ Line 876 - `FIX_109.4` (existing)
5. ✅ Line 1203 - `FIX_109.4` (existing)
6. ✅ Line 1264 - `MARKER_115_BUG1` (NEW)
7. ✅ Line 2054 - `MARKER_115_BUG1` (NEW)

### Grep Verification Command:
```bash
grep -n "MARKER_115_BUG1" src/api/handlers/user_message_handler.py
# Returns: 379, 1268, 2058
```

---

## Testing Checklist

Before deploying to production:
- [ ] Clear existing parasitic chats from `data/chat_history.json`
- [ ] Test solo chat with Ollama models (line 375 path)
- [ ] Test Hostess routing with CAM events (line 1264 path)
- [ ] Test agent chain responses (line 2054 path)
- [ ] Verify no duplicate chats appear in sidebar after reload
- [ ] Check frontend console for `[FIX_109.4] Using client-provided chat_id` logs
- [ ] Monitor `data/chat_history.json` growth over 24h

---

## Related Issues

### Fixed:
- ✅ Parasitic chat creation in solo mode
- ✅ Frontend-backend chat ID mismatch
- ✅ Sidebar clutter from duplicate chats

### Remains (Out of Scope):
- Race conditions → Already fixed by `MARKER_109_13` (thread lock in chat_history_manager.py)
- Display name trailing spaces → Already fixed by `.strip()` (line 301 in chat_history_manager.py)

---

## Code Markers Reference

| Marker | Description | Location |
|--------|-------------|----------|
| `MARKER_115_BUG1` | Chat hygiene fix - add `client_chat_id` | user_message_handler.py:379, 1268, 2058 |
| `FIX_109.4` | Accept client-provided chat_id (Phase 109.4) | user_message_handler.py:261, 557, 790, 876, 1203 + chat_history_manager.py:155, 286 |
| `MARKER_109_13` | Thread lock for race prevention (Phase 109) | chat_history_manager.py:46, 59, 175 |
| `MARKER_109_14` | Prefer client_display_name (Phase 109) | user_message_handler.py:265, 374, 551, 784, 870, 1197, 1258, 2047 |

---

**Fix Completed:** 2026-02-06
**Lines Changed:** 3
**Files Modified:** 1
**Total Impact:** 7 call sites now consistent
