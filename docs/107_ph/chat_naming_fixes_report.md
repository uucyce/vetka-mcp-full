# CHAT_NAMING Fix Report

**Date:** 2026-02-02
**Phase:** 107.3
**Status:** COMPLETED

---

## Problem

`MARKER_CHAT_NAMING` in `user_message_handler.py:297` identified a critical issue:

- **Current behavior:** Chat name = file path (e.g., `unknown`)
- **Expected behavior:** Chat name = semantic key from message content (e.g., `fix_bug_report`)

In one location (Ollama handler), the fix was already implemented using `generate_semantic_key()`. However, **6 other locations** still used the old `get_or_create_chat(node_path)` pattern.

---

## Solution

### 1. Created Global Function

Added `extract_semantic_key()` at the module level (line 39-56):

```python
def extract_semantic_key(message_text: str, fallback: str = "chat") -> str:
    """
    Extract semantic key from message for chat naming.

    Args:
        message_text: User message text
        fallback: Fallback key if extraction fails

    Returns:
        Semantic key like 'fix_bug_report' (max 30 chars)
    """
    words = message_text.strip().split()[:5]
    noise_words = {'the', 'a', 'an', 'is', 'are', 'what', 'how', 'can', 'do',
                   'does', 'in', 'on', 'at', 'как', 'что', 'в'}
    key_words = [w.lower() for w in words if w.lower() not in noise_words]
    semantic_key = '_'.join(key_words[:3])[:30] or fallback
    return semantic_key if semantic_key else fallback
```

**Features:**
- Extracts first 3-5 meaningful words from message
- Filters out noise words (articles, prepositions)
- Supports English and Russian noise words
- Limits to 30 characters
- Provides fallback to 'chat' if extraction fails

---

### 2. Fixed 6 Locations

All locations now use the same pattern:

```python
chat_history = get_chat_history_manager()
semantic_key = extract_semantic_key(text)
chat_id = chat_history.get_or_create_chat(
    'unknown',
    context_type='topic',
    display_name=semantic_key
)
```

#### Fix 1/6: Line 503 (Provider Registry Handler)
**Location:** Direct model call via provider_registry
**Context:** Loading chat history for model response

**Before:**
```python
chat_history = get_chat_history_manager()
chat_id = chat_history.get_or_create_chat(node_path)
```

**After:**
```python
# MARKER_CHAT_NAMING: Fix 1/6 - Use semantic key for chat naming
chat_history = get_chat_history_manager()
semantic_key = extract_semantic_key(text)
chat_id = chat_history.get_or_create_chat(
    'unknown',
    context_type='topic',
    display_name=semantic_key
)
```

---

#### Fix 2/6: Line 683 (After Workflow Handler)
**Location:** CAM event emission after direct model call
**Context:** Surprise calculation for assistant message

**Before:**
```python
chat_history = get_chat_history_manager()
chat_id = chat_history.get_or_create_chat(node_path)
await emit_cam_event(...)
```

**After:**
```python
# MARKER_CHAT_NAMING: Fix 2/6 - Use semantic key for chat naming
chat_history = get_chat_history_manager()
semantic_key = extract_semantic_key(text)
chat_id = chat_history.get_or_create_chat(
    'unknown',
    context_type='topic',
    display_name=semantic_key
)
await emit_cam_event(...)
```

---

#### Fix 3/6: Line 767 (@mention Direct Model)
**Location:** @mention direct model call
**Context:** Loading chat history for @mention response

**Before:**
```python
chat_history = get_chat_history_manager()
chat_id = chat_history.get_or_create_chat(node_path)
```

**After:**
```python
# MARKER_CHAT_NAMING: Fix 3/6 - Use semantic key for chat naming
chat_history = get_chat_history_manager()
semantic_key = extract_semantic_key(text)
chat_id = chat_history.get_or_create_chat(
    'unknown',
    context_type='topic',
    display_name=semantic_key
)
```

---

#### Fix 4/6: Line 1032 (Another Location)
**Location:** CAM event emission after @mention call
**Context:** Surprise calculation for @mention response

**Before:**
```python
chat_history = get_chat_history_manager()
chat_id = chat_history.get_or_create_chat(node_path)
await emit_cam_event(...)
```

**After:**
```python
# MARKER_CHAT_NAMING: Fix 4/6 - Use semantic key for chat naming
chat_history = get_chat_history_manager()
semantic_key = extract_semantic_key(text)
chat_id = chat_history.get_or_create_chat(
    'unknown',
    context_type='topic',
    display_name=semantic_key
)
await emit_cam_event(...)
```

---

#### Fix 5/6: Line 1091 (User Input Event)
**Location:** User message input processing
**Context:** Surprise calculation for user message

**Before:**
```python
chat_history = get_chat_history_manager()
chat_id = chat_history.get_or_create_chat(node_path)
await emit_cam_event(...)
```

**After:**
```python
# MARKER_CHAT_NAMING: Fix 5/6 - Use semantic key for chat naming
chat_history = get_chat_history_manager()
semantic_key = extract_semantic_key(text)
chat_id = chat_history.get_or_create_chat(
    'unknown',
    context_type='topic',
    display_name=semantic_key
)
await emit_cam_event(...)
```

---

#### Fix 6/6: Line 1879 (Agent Chain)
**Location:** Agent chain response (PM → Dev → QA)
**Context:** Surprise calculation for agent chain response

**Before:**
```python
chat_history = get_chat_history_manager()
chat_id = chat_history.get_or_create_chat(node_path)
await emit_cam_event(...)
```

**After:**
```python
# MARKER_CHAT_NAMING: Fix 6/6 - Use semantic key for chat naming
chat_history = get_chat_history_manager()
semantic_key = extract_semantic_key(text)
chat_id = chat_history.get_or_create_chat(
    'unknown',
    context_type='topic',
    display_name=semantic_key
)
await emit_cam_event(...)
```

---

## Verification

### Code Search Results

**Old pattern (`get_or_create_chat(node_path)`):**
```bash
$ grep -n "get_or_create_chat(node_path)" user_message_handler.py
# No matches found ✓
```

**New markers:**
```bash
$ grep -n "MARKER_CHAT_NAMING: Fix" user_message_handler.py
503:    # MARKER_CHAT_NAMING: Fix 1/6 - Use semantic key for chat naming
683:    # MARKER_CHAT_NAMING: Fix 2/6 - Use semantic key for chat naming
767:    # MARKER_CHAT_NAMING: Fix 3/6 - Use semantic key for chat naming
1032:   # MARKER_CHAT_NAMING: Fix 4/6 - Use semantic key for chat naming
1091:   # MARKER_CHAT_NAMING: Fix 5/6 - Use semantic key for chat naming
1879:   # MARKER_CHAT_NAMING: Fix 6/6 - Use semantic key for chat naming
```

---

## Impact

### Before
- Chat names were generic: `unknown`, `root`, file paths
- No semantic connection between chat and conversation topic
- Hard to find relevant chats in history

### After
- Chat names are semantic: `fix_bug_report`, `add_feature_x`, `explain_code`
- Clear topic identification from message content
- Better chat organization and searchability
- Consistent behavior across all handler locations

---

## Testing Checklist

- [ ] Test direct model call (provider_registry) chat naming
- [ ] Test @mention call chat naming
- [ ] Test agent chain (PM → Dev → QA) chat naming
- [ ] Verify CAM event emission with correct chat_id
- [ ] Check chat history persistence with semantic keys
- [ ] Verify fallback to 'chat' when extraction fails
- [ ] Test with Russian and English messages
- [ ] Verify 30-character limit enforcement

---

## Technical Details

**File Modified:**
```
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/user_message_handler.py
```

**Changes:**
- Added `extract_semantic_key()` function (lines 39-56)
- Fixed 6 locations (lines 503, 683, 767, 1032, 1091, 1879)
- Total additions: ~45 lines
- Pattern consistency: 100%

**Dependencies:**
- `ChatHistoryManager.get_or_create_chat()` (already supported `display_name` parameter)
- No breaking changes to existing API

---

## Notes

1. **Ollama handler** (line 312) already had the fix implemented - used as reference pattern
2. **All 6 locations** now use identical semantic key extraction logic
3. **Noise word filtering** supports both English and Russian
4. **Fallback mechanism** ensures chat is always created even if extraction fails
5. **Context type** set to `'topic'` for all semantic chats (vs. `'file'` for file-based chats)

---

## Next Steps

1. Test in development environment
2. Monitor chat naming in production logs
3. Consider adding telemetry for semantic key quality
4. Potential future enhancement: ML-based topic extraction

---

**Status:** READY FOR TESTING
**Reviewer:** @danilagulin
**Approved:** Pending
