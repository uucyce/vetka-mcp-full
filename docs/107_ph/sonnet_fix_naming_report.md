# Phase 107.3: MARKER_CHAT_NAMING Fix Report

**Date:** 2026-02-02
**Agent:** Claude Sonnet
**Status:** Analysis Complete - Ready for Implementation

---

## Problem

Chat names use file paths (`node_path`) instead of semantic keys from user messages.

**Current:** `/Users/dan/project/src/auth.py`
**Expected:** `авторизация_api`

---

## Root Cause

**Inconsistent implementation:**
- ✅ Ollama handler (line 312) - has `generate_semantic_key()`
- ❌ 6 other locations - use `node_path` directly

---

## Locations to Fix

| Line | Handler | Current |
|------|---------|---------|
| 485 | provider_registry | `get_or_create_chat(node_path)` |
| 660 | after workflow | `get_or_create_chat(node_path)` |
| 737 | @mention direct model | `get_or_create_chat(node_path)` |
| 997 | another location | `get_or_create_chat(node_path)` |
| 1050 | user input event | `get_or_create_chat(node_path)` |
| 1832 | agent chain | `get_or_create_chat(node_path)` |

---

## Solution

### 1. Add Module-Level Function (after line 35)

```python
def extract_semantic_key(message_text: str, fallback: str = "chat") -> str:
    """
    Extract semantic key from message content for chat naming.
    Phase 107.3: MARKER_CHAT_NAMING fix

    Examples:
        "Как добавить авторизацию в API?" -> "добавить_авторизацию_api"
        "Fix bug in chat history" -> "fix_bug_chat"
    """
    words = message_text.strip().split()[:5]
    noise_words = {'the', 'a', 'an', 'is', 'are', 'what', 'how', 'can', 'do',
                   'does', 'in', 'on', 'at', 'как', 'что', 'в'}
    key_words = [w.lower() for w in words if w.lower() not in noise_words]
    semantic_key = '_'.join(key_words[:3])[:30] or fallback
    return semantic_key if semantic_key else fallback
```

### 2. Remove Duplicate (lines 301-311)

**OLD:**
```python
def generate_semantic_key(message_text: str, node_path: str) -> str:
    # ... duplicate code
semantic_chat_key = generate_semantic_key(text, node_path)
```

**NEW:**
```python
semantic_chat_key = extract_semantic_key(text)
```

### 3. Replace 6 Instances

**OLD:**
```python
chat_id = chat_history.get_or_create_chat(node_path)
```

**NEW:**
```python
semantic_chat_key = extract_semantic_key(text)
chat_id = chat_history.get_or_create_chat(
    'unknown',
    context_type='topic',
    display_name=semantic_chat_key
)
```

---

## Testing

| Test | Input | Expected |
|------|-------|----------|
| Russian | "Как добавить авторизацию в API?" | `добавить_авторизацию_api` |
| English | "Fix bug in chat history" | `fix_bug_chat` |
| Short | "What is VETKA?" | `vetka` |

**Data check:** `chat_history.json` should have:
```json
{
  "file_path": "unknown",
  "context_type": "topic",
  "display_name": "semantic_key_here"
}
```

---

## Implementation Steps

1. Add `extract_semantic_key()` after imports
2. Replace duplicate function at lines 301-311
3. Find & replace 6 instances of `get_or_create_chat(node_path)`
4. Restart server
5. Test with messages above

---

## Impact

- Human-readable chat names
- Consistent behavior across all handlers
- Supports Russian and English
- Backward compatible (existing chats not affected)
