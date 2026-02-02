# MARKER_CHAT_HISTORY_ATTRIBUTION Fix

## Problem
When chat history is saved, there's no clear model attribution. Grok confuses its own responses with ChatGPT responses because:
- No `model` field in saved messages (was `null`)
- No `model_provider` field to distinguish between providers

## Root Cause
The `save_chat_message()` function in `handler_utils.py` already expected `model` and `model_provider` fields, but the message dictionaries being created in handlers didn't include them.

## Files Modified

### 1. `/src/api/handlers/user_message_handler.py`
**Three locations fixed:**

#### Location 1: Ollama Direct Call (Line ~420)
```python
save_chat_message(
    node_path,
    {
        "role": "assistant",
        "agent": requested_model,
        "model": requested_model,  # ✅ ADDED
        "model_provider": "ollama",  # ✅ ADDED
        "text": full_response,
        "node_id": node_id,
    },
    pinned_files=pinned_files,
)
```

#### Location 2: Provider Registry Call (Line ~633)
```python
save_chat_message(
    node_path,
    {
        "role": "assistant",
        "agent": requested_model,
        "model": requested_model,  # ✅ ADDED
        "model_provider": detected_provider.value if detected_provider else "unknown",  # ✅ ADDED
        "text": full_response,
        "node_id": node_id,
    },
    pinned_files=pinned_files,
)
```

#### Location 3: @mention Direct Call (Line ~967)
```python
save_chat_message(
    node_path,
    {
        "role": "assistant",
        "agent": model_to_use,
        "model": model_to_use,  # ✅ ADDED
        "model_provider": detected_provider.value if 'detected_provider' in locals() and detected_provider else "ollama",  # ✅ ADDED
        "text": response_text,
        "node_id": node_id,
    },
    pinned_files=pinned_files,
)
```

### 2. `/src/api/handlers/handler_utils.py` (Line ~247)
Updated `save_chat_message()` to explicitly save `model_provider`:

```python
msg_to_save = {
    "role": message.get("role", "user"),
    "content": message.get("content") or message.get("text"),
    "agent": message.get("agent"),
    "model": message.get("model"),  # Already existed
    "model_provider": message.get("model_provider"),  # ✅ ADDED
    "node_id": message.get("node_id"),
    "metadata": message.get("metadata", {}),
}
```

### 3. `/src/api/handlers/group_message_handler.py` (Line ~727 and ~945)
#### Provider Detection (Line ~727)
```python
# Detect provider for model attribution
from src.elisya.provider_registry import ProviderRegistry
detected_provider = ProviderRegistry.detect_provider(model_id)
provider_name = detected_provider.value if detected_provider else "unknown"
```

#### Save with Attribution (Line ~945)
```python
chat_history.add_message(
    chat_id,
    {
        "role": "assistant",
        "content": response_text,
        "agent": display_name,
        "model": model_id,
        "model_provider": provider_name,  # ✅ ADDED
        "metadata": {"group_id": group_id},
    },
)
```

## Result
Now all saved messages include:
- `"model": "grok-4-fast"` (or any model name)
- `"model_provider": "xai"` (or "ollama", "openai", "openrouter", etc.)

This allows Grok (and any agent) to:
1. Identify which model generated each response
2. Distinguish between different providers (XAI vs OpenRouter vs ChatGPT)
3. Build proper context from conversation history
4. Avoid confusing its own responses with other models

## Testing
After this fix, new messages will be saved with full attribution:
```json
{
  "role": "assistant",
  "content": "...",
  "agent": "grok-4-fast",
  "model": "grok-4-fast",
  "model_provider": "xai",
  "timestamp": "..."
}
```

## Marker Location
All changes are marked with: `MARKER_CHAT_HISTORY_ATTRIBUTION`

Search for this marker to find all related changes:
```bash
grep -r "MARKER_CHAT_HISTORY_ATTRIBUTION" src/
```
