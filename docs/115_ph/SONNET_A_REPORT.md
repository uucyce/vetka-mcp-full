# SONNET-A REPORT: BUG-3 model_source Persistence Fix

**Date:** 2026-02-06  
**Agent:** Claude Sonnet-4.5  
**Task:** Fix model_source persistence bug across server restarts

## EXECUTIVE SUMMARY

Successfully identified all locations requiring `model_source` field addition. The bug is confirmed as described:
- `model_source` is received from frontend at line 249
- It is NOT being passed to save_chat_message() calls
- Total locations found: **8 save_chat_message calls** requiring updates

## FILE 1: handler_utils.py

**Location:** Line 244-252  
**Status:** ✓ Ready to fix

**Current code (line 244-252):**
```python
msg_to_save = {
    "role": message.get("role", "user"),
    "content": message.get("content") or message.get("text"),
    "agent": message.get("agent"),
    "model": message.get("model"),
    "model_provider": message.get("model_provider"),  # Provider attribution for model disambiguation
    "node_id": message.get("node_id"),
    "metadata": message.get("metadata", {}),
}
```

**Fixed code:**
```python
msg_to_save = {
    "role": message.get("role", "user"),
    "content": message.get("content") or message.get("text"),
    "agent": message.get("agent"),
    "model": message.get("model"),
    "model_provider": message.get("model_provider"),  # Provider attribution for model disambiguation
    "model_source": message.get("model_source"),  # MARKER_115_BUG3: model_source persistence
    "node_id": message.get("node_id"),
    "metadata": message.get("metadata", {}),
}
```

## FILE 2: user_message_handler.py

### model_source variable scope
- **Line 249:** `model_source = data.get("model_source")` ✓ Available in function scope

### Locations to fix:

#### 1. USER message - Ollama path (Line 422-426)
**Current:**
```python
save_chat_message(
    node_path,
    {"role": "user", "text": text, "node_id": node_id},
    pinned_files=pinned_files,
)
```

**Fixed:**
```python
save_chat_message(
    node_path,
    {"role": "user", "text": text, "node_id": node_id, "model_source": model_source},  # MARKER_115_BUG3: model_source persistence
    pinned_files=pinned_files,
)
```

#### 2. ASSISTANT message - Ollama path (Line 494-505)
**Current:**
```python
save_chat_message(
    node_path,
    {
        "role": "assistant",
        "agent": requested_model,
        "model": requested_model,
        "model_provider": "ollama",  # Provider for Ollama local models
        "text": full_response,
        "node_id": node_id,
    },
    pinned_files=pinned_files,
)
```

**Fixed:**
```python
save_chat_message(
    node_path,
    {
        "role": "assistant",
        "agent": requested_model,
        "model": requested_model,
        "model_provider": "ollama",  # Provider for Ollama local models
        "model_source": model_source,  # MARKER_115_BUG3: model_source persistence
        "text": full_response,
        "node_id": node_id,
    },
    pinned_files=pinned_files,
)
```

#### 3. USER message - Streaming path (Line 602-606)
**Current:**
```python
save_chat_message(
    node_path,
    {"role": "user", "text": text, "node_id": node_id},
    pinned_files=pinned_files,
)
```

**Fixed:**
```python
save_chat_message(
    node_path,
    {"role": "user", "text": text, "node_id": node_id, "model_source": model_source},  # MARKER_115_BUG3: model_source persistence
    pinned_files=pinned_files,
)
```

#### 4. ASSISTANT message - Streaming path (Line 765-776)
**Current:**
```python
save_chat_message(
    node_path,
    {
        "role": "assistant",
        "agent": requested_model,
        "model": requested_model,
        "model_provider": detected_provider.value if detected_provider else "unknown",  # Provider from detection
        "text": full_response,
        "node_id": node_id,
    },
    pinned_files=pinned_files,
)
```

**Fixed:**
```python
save_chat_message(
    node_path,
    {
        "role": "assistant",
        "agent": requested_model,
        "model": requested_model,
        "model_provider": detected_provider.value if detected_provider else "unknown",  # Provider from detection
        "model_source": model_source,  # MARKER_115_BUG3: model_source persistence
        "text": full_response,
        "node_id": node_id,
    },
    pinned_files=pinned_files,
)
```

#### 5. USER message - @mention path (Line 923-931)
**Current:**
```python
save_chat_message(
    node_path,
    {
        "role": "user",
        "text": text,  # Original text (with @mention)
        "node_id": node_id,
    },
    pinned_files=pinned_files,
)
```

**Fixed:**
```python
save_chat_message(
    node_path,
    {
        "role": "user",
        "text": text,  # Original text (with @mention)
        "model_source": model_source,  # MARKER_115_BUG3: model_source persistence
        "node_id": node_id,
    },
    pinned_files=pinned_files,
)
```

#### 6. ASSISTANT message - @mention path (Line 1178-1189)
**Current:**
```python
save_chat_message(
    node_path,
    {
        "role": "assistant",
        "agent": model_to_use,
        "model": model_to_use,
        "model_provider": detected_provider.value if 'detected_provider' in locals() and detected_provider else "ollama",  # Provider from detection or default to ollama
        "text": response_text,
        "node_id": node_id,
    },
    pinned_files=pinned_files,
)
```

**Fixed:**
```python
save_chat_message(
    node_path,
    {
        "role": "assistant",
        "agent": model_to_use,
        "model": model_to_use,
        "model_provider": detected_provider.value if 'detected_provider' in locals() and detected_provider else "ollama",  # Provider from detection or default to ollama
        "model_source": model_source,  # MARKER_115_BUG3: model_source persistence
        "text": response_text,
        "node_id": node_id,
    },
    pinned_files=pinned_files,
)
```

#### 7. USER message - Hostess path (Line 1247-1251)
**Current:**
```python
save_chat_message(
    node_path,
    {"role": "user", "text": text, "node_id": node_id},
    pinned_files=pinned_files,
)
```

**Fixed:**
```python
save_chat_message(
    node_path,
    {"role": "user", "text": text, "node_id": node_id, "model_source": model_source},  # MARKER_115_BUG3: model_source persistence
    pinned_files=pinned_files,
)
```

#### 8. AGENT message - Workflow path (Line 2030-2040)
**SPECIAL CASE:** This is an agent workflow response where model_source comes from `resp` dict, not from outer scope.

**Current:**
```python
save_chat_message(
    node_path,
    {
        "role": "agent",
        "agent": resp["agent"],
        "model": resp["model"],
        "text": resp["text"],
        "node_id": resp["node_id"],
    },
    pinned_files=pinned_files,
)
```

**Fixed:**
```python
save_chat_message(
    node_path,
    {
        "role": "agent",
        "agent": resp["agent"],
        "model": resp["model"],
        "model_source": resp.get("model_source", model_source),  # MARKER_115_BUG3: model_source persistence (fallback to outer scope)
        "text": resp["text"],
        "node_id": resp["node_id"],
    },
    pinned_files=pinned_files,
)
```

## VERIFICATION CHECKLIST

- [x] model_source variable is in scope for all USER/ASSISTANT messages (line 249)
- [x] All 7 direct save calls identified
- [x] 1 agent workflow call identified (needs resp.get fallback)
- [x] No unexpected patterns found
- [x] All locations use consistent marker comment

## IMPLEMENTATION COMMANDS

```bash
# Step 1: Backup files
cp src/api/handlers/handler_utils.py src/api/handlers/handler_utils.py.bak
cp src/api/handlers/user_message_handler.py src/api/handlers/user_message_handler.py.bak

# Step 2: Apply fixes (manual or via sed/python script)
# See exact changes above

# Step 3: Verify
git diff src/api/handlers/handler_utils.py
git diff src/api/handlers/user_message_handler.py

# Step 4: Test
# - Restart server
# - Send message with model_source="polza_ai"
# - Check data/chat_history.json for model_source field
# - Restart server again
# - Verify model_source is preserved
```

## RISK ASSESSMENT

**Risk Level:** LOW
- Only adding a single field to existing dicts
- Field is optional (`.get()` pattern used in handler_utils)
- No refactoring of other code
- Backwards compatible (old messages without model_source will still work)

## EXPECTED OUTCOME

After fix:
1. User selects "Grok@POLZA" in UI
2. Frontend sends `model_source: "polza_ai"`
3. Backend saves to chat_history.json with `"model_source": "polza_ai"`
4. After server restart, model card shows "Grok@POLZA" (not "Grok@OpenRouter")

## CONCLUSION

✓ All locations identified  
✓ model_source variable accessible in all scopes  
✓ Consistent pattern for all changes  
✓ Ready for implementation  

**Recommendation:** Proceed with fixes as outlined above.

---
**Report Status:** COMPLETE  
**Next Action:** Apply fixes to both files
