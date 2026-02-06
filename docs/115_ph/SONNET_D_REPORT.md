# SONNET-D: Chat Hygiene Bug Analysis Report

## Executive Summary

**Status:** ✅ FIXED - All 7 locations now have `client_chat_id`

**Issue:** Chat auto-creation with parasitic paths and names, cluttering the sidebar.

**Root Cause:** Some `get_or_create_chat()` calls with `'unknown'` path and `context_type='topic'` were missing the `client_chat_id` parameter, causing chat duplication instead of reuse.

**Resolution:** Applied `MARKER_115_BUG1` fix to 3 missing locations (lines 375, 1259, 2048).

---

## Analysis Results

### File Analyzed
`/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py`

### Total `get_or_create_chat()` Calls: 7

#### ✅ FIXED (4 calls) - Have `client_chat_id`
1. **Line 552** - Provider registry path
   - Has: `display_name=chat_display_name, chat_id=client_chat_id`
   - Status: ✅ OK

2. **Line 785** - CAM event emission #2
   - Has: `display_name=chat_display_name, chat_id=client_chat_id`
   - Status: ✅ OK

3. **Line 871** - Streaming path
   - Has: `display_name=chat_display_name, chat_id=client_chat_id`
   - Status: ✅ OK

4. **Line 1198** - Another CAM event emission
   - Has: `display_name=chat_display_name, chat_id=client_chat_id`
   - Status: ✅ OK

#### ❌ BROKEN (3 calls) - Missing `client_chat_id`

1. **Line 375** - Ollama local model path
   ```python
   chat_id = chat_history.get_or_create_chat(
       'unknown',
       context_type='topic',
       display_name=semantic_chat_key
   )
   # MISSING: chat_id=client_chat_id
   ```
   - **Scope Check:** `client_chat_id` IS available (extracted at line 261)
   - **Fix Required:** Add `chat_id=client_chat_id` parameter

2. **Line 1259** - CAM event emission #5
   ```python
   chat_id = chat_history.get_or_create_chat(
       'unknown',
       context_type='topic',
       display_name=chat_display_name
   )
   # MISSING: chat_id=client_chat_id
   ```
   - **Scope Check:** `client_chat_id` IS available (extracted at line 261)
   - **Fix Required:** Add `chat_id=client_chat_id` parameter

3. **Line 2048** - Agent chain CAM event #6
   ```python
   chat_id = chat_history.get_or_create_chat(
       'unknown',
       context_type='topic',
       display_name=chat_display_name
   )
   # MISSING: chat_id=client_chat_id
   ```
   - **Scope Check:** `client_chat_id` IS available (extracted at line 261)
   - **Fix Required:** Add `chat_id=client_chat_id` parameter

---

## Backend Logic Verification

### `chat_history_manager.py` - `get_or_create_chat()` Implementation

**Lines 148-325:** The logic is CORRECT:

1. **Line 193-199:** Priority 1 - Search by `group_id` for group chats (stable key)
2. **Line 222-236:** For null-context (`'unknown'`), search by `display_name` first
3. **Line 285-292:** **FIX_109.4** - Use `client_chat_id` if provided and not yet in history

The backend ALREADY has the infrastructure to reuse chats based on `client_chat_id`. The bug is that some frontend→backend calls are NOT passing it.

---

## Why This Causes Parasitic Chats

### Scenario Without `client_chat_id`:
1. User sends message "fix bug report" → Frontend generates `chat_id = "abc123"`
2. Backend call at line 375 DOESN'T pass `client_chat_id`
3. Backend creates NEW chat with UUID `"xyz789"` (different from frontend's `"abc123"`)
4. Frontend stores `"abc123"`, backend stores `"xyz789"` → **MISMATCH**
5. Next message → Frontend thinks it's still `"abc123"`, but backend creates ANOTHER new chat → **DUPLICATION**

### With `client_chat_id` (Fixed):
1. User sends message "fix bug report" → Frontend generates `chat_id = "abc123"`
2. Backend call passes `chat_id=client_chat_id` (`"abc123"`)
3. Backend uses frontend's ID `"abc123"` (line 286-288 in chat_history_manager.py)
4. Next message → Frontend sends same `"abc123"` → Backend reuses it → **NO DUPLICATION**

---

## Context Type Analysis

All broken calls use `context_type='topic'`, which is correct for file-less chats. The issue is NOT the context type, but the missing `client_chat_id`.

### Related Markers Found:
- **MARKER_109_13:** Thread lock for race condition prevention (lines 59, 175)
- **MARKER_109_14:** Prefer `client_display_name` (used correctly at all 7 locations)
- **FIX_109.4:** Accept `client_chat_id` from frontend (implemented in 4/7 locations)

The system ALREADY has the fix infrastructure. It's just not applied consistently.

---

## Other Files Checked (Read-only)

### Real File Path Calls (No Changes Needed) ✅
- `src/api/handlers/context/context_builders.py:78,140` - Uses `node_path` (real file path), no `client_chat_id` needed
- `src/api/handlers/orchestration/response_manager.py:129` - Uses `node_path`, no `client_chat_id` needed
- `src/api/handlers/mention/mention_handler.py:174,270` - Uses `node_path`, no `client_chat_id` needed

**Why these are OK:** They're creating chats for REAL files, not null-context topic chats. The backend's path-based reuse logic (lines 264-282 in chat_history_manager.py) handles these correctly without needing `client_chat_id`.

### Bug Scope
The bug ONLY affects calls with `file_path='unknown'` and `context_type='topic'`, which are all in `user_message_handler.py`. All such calls have now been fixed.

---

## Fix Applied ✅

### Minimal Changes Strategy

**Applied FIX_109.4 pattern to 3 missing locations:**

1. ✅ **Line 375** (Ollama path) - Added `chat_id=client_chat_id` with `MARKER_115_BUG1`
2. ✅ **Line 1264** (CAM event #5) - Added `chat_id=client_chat_id` with `MARKER_115_BUG1`
3. ✅ **Line 2054** (Agent chain CAM event #6) - Added `chat_id=client_chat_id` with `MARKER_115_BUG1`

**All 7 `get_or_create_chat()` calls in user_message_handler.py now follow the unified pattern:**
```python
chat_id = chat_history.get_or_create_chat(
    'unknown',
    context_type='topic',
    display_name=chat_display_name,
    chat_id=client_chat_id  # FIX_109.4 or MARKER_115_BUG1
)
```

### Verification
- Line 375: ✅ `chat_id=client_chat_id  # MARKER_115_BUG1: Chat hygiene fix`
- Line 557: ✅ `chat_id=client_chat_id  # FIX_109.4: Use client-provided ID if available`
- Line 790: ✅ `chat_id=client_chat_id  # FIX_109.4`
- Line 876: ✅ `chat_id=client_chat_id  # FIX_109.4`
- Line 1203: ✅ `chat_id=client_chat_id  # FIX_109.4`
- Line 1264: ✅ `chat_id=client_chat_id  # MARKER_115_BUG1: Chat hygiene fix`
- Line 2054: ✅ `chat_id=client_chat_id  # MARKER_115_BUG1: Chat hygiene fix`

---

## Additional Findings

### Race Condition Already Fixed
`chat_history_manager.py` lines 59, 175 show `MARKER_109_13` - thread lock is already implemented to prevent parallel requests from creating duplicates. This is GOOD.

### Display Name Stripping
Line 301 in `chat_history_manager.py` strips `display_name` to prevent trailing space mismatches:
```python
clean_display_name = display_name.strip() if display_name else None
```
This is also GOOD and prevents another potential duplication vector.

---

## Conclusion

The parasitic chat creation bug was **NOT due to missing display_name** (all 7 calls already had it). It was due to **missing `client_chat_id` in 3 out of 7 locations**, causing frontend-backend ID mismatch and subsequent duplication.

**Status:** ✅ RESOLVED - Fix applied to all 3 locations (lines 375, 1264, 2054).

### Testing Recommendations
1. Clear existing parasitic chats from `data/chat_history.json`
2. Test solo chat creation with local Ollama models (line 375 path)
3. Test CAM event emission paths (lines 1264, 2054)
4. Verify frontend-backend chat ID consistency across all 7 code paths
5. Monitor for any remaining duplication issues

---

**Report Generated:** 2026-02-06
**Analyzed By:** Claude Sonnet 4.5 (SONNET-D)
**Project:** VETKA Live 03
**Phase:** 115 (Chat Hygiene Fix - BUG-1)
