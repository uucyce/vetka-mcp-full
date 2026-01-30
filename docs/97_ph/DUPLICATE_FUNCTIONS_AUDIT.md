# Duplicate Functions Audit

**Date:** 2026-01-28
**Phase:** 96
**Agent:** Haiku

---

## Summary

| Category | Count | Risk |
|----------|-------|------|
| Exact Duplicates | 15 | 🔴 High |
| Similar Names | 8 | 🟡 Medium |
| Format Utilities | 3 suites | 🟢 Low (intentional) |

---

## Exact Duplicate Functions

### `format_timestamp()` - 4 instances
```
src/api/handlers/message_utils.py:45
src/api/handlers/handler_utils.py:128
src/orchestration/response_formatter.py:67
src/services/group_chat_manager.py:234
```
**Recommendation:** Consolidate to `src/utils/formatters.py`

### `get_api_key()` - 3 instances
```
src/elisya/provider_registry.py:89
src/orchestration/services/api_key_service.py:45
src/bridge/shared_tools.py:156
```
**Recommendation:** Use only `api_key_service.py`

### `sanitize_filename()` - 2 instances
```
src/scanners/file_watcher.py:67
src/visualizer/tree_renderer.py:34
```
**Recommendation:** Move to `src/utils/file_utils.py`

### `truncate_text()` - 2 instances
```
src/memory/compression.py:89
src/orchestration/context_fusion.py:156
```
**Recommendation:** Keep in `compression.py`, import elsewhere

### `parse_json_safe()` - 2 instances
```
src/api/handlers/chat_handler.py:234
src/mcp/tools/llm_call_tool.py:78
```
**Recommendation:** Move to `src/utils/json_utils.py`

### `emit_socket_event()` - 2 instances
```
src/api/handlers/user_message_handler.py:312
src/api/handlers/group_message_handler.py:287
```
**Recommendation:** Move to `handler_utils.py`

---

## Similar Names (Potential Confusion)

### Search-related
```
do_search()           - search_handlers.py
perform_search()      - semantic_routes.py (legacy)
execute_search()      - qdrant_client.py
```
**Status:** `do_search` is current, others may be legacy

### Message handling
```
handle_message()      - chat_handler.py
process_message()     - user_message_handler.py
handle_user_message() - chat_routes.py (route wrapper)
```
**Status:** Different layers, acceptable

### File operations
```
read_file()           - multiple locations (intentional)
load_file()           - tree_renderer.py
get_file_content()    - file_watcher.py
```
**Status:** Different purposes, acceptable

---

## Format Utility Suites (Intentional)

### `format_*` family in response_formatter.py
```
format_response()
format_error()
format_stream_chunk()
format_model_info()
```
**Status:** ✅ Related functions, keep together

### `convert_*` family in apiConverter.ts
```
convertToApiFormat()
convertFromApiFormat()
convertSearchResult()
```
**Status:** ✅ API conversion utilities, keep together

### `validate_*` family in handlers
```
validate_request()
validate_message()
validate_group_id()
```
**Status:** ✅ Validation utilities, keep in handlers

---

## Consolidation Recommendations

### Priority 1: Create src/utils/formatters.py
```python
"""
Centralized formatting utilities.
@status: active
@phase: 96
"""

def format_timestamp(dt: datetime) -> str:
    ...

def truncate_text(text: str, max_len: int) -> str:
    ...

def sanitize_filename(name: str) -> str:
    ...
```

### Priority 2: Consolidate API key access
```python
# Use ONLY:
from src.orchestration.services.api_key_service import get_api_key

# Remove duplicates from:
# - provider_registry.py
# - shared_tools.py
```

### Priority 3: Create src/utils/json_utils.py
```python
"""
Safe JSON utilities.
@status: active
@phase: 96
"""

def parse_json_safe(text: str, default=None):
    ...

def serialize_json_safe(obj, indent=None):
    ...
```

---

## Files Requiring Updates After Consolidation

1. `src/api/handlers/message_utils.py` - remove format_timestamp
2. `src/api/handlers/handler_utils.py` - remove format_timestamp
3. `src/orchestration/response_formatter.py` - import from utils
4. `src/services/group_chat_manager.py` - import from utils
5. `src/elisya/provider_registry.py` - import from api_key_service
6. `src/bridge/shared_tools.py` - import from api_key_service
7. `src/scanners/file_watcher.py` - import sanitize_filename
8. `src/visualizer/tree_renderer.py` - import sanitize_filename
