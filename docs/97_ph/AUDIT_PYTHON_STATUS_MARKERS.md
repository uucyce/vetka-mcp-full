# Python @status Markers Audit

**Date:** 2026-01-28
**Phase:** 96
**Agent:** Haiku

---

## Summary

| Directory | Files | With Marker | Coverage |
|-----------|-------|-------------|----------|
| src/agents/ | 8 | 7 | 87.5% |
| src/api/ | 24 | 19 | 79.2% |
| src/bridge/ | 3 | 3 | 100% |
| src/elisya/ | 4 | 3 | 75% |
| src/initialization/ | 4 | 4 | 100% |
| src/mcp/ | 14 | 5 | 35.7% |
| src/memory/ | 8 | 6 | 75% |
| src/orchestration/ | 12 | 10 | 83.3% |
| src/scanners/ | 6 | 5 | 83.3% |
| src/services/ | 5 | 4 | 80% |
| src/visualizer/ | 3 | 3 | 100% |
| **TOTAL** | **91** | **68** | **74.8%** |

---

## Files Missing @status Marker

### src/mcp/ (Lowest Coverage: 35.7%)
- `src/mcp/__init__.py`
- `src/mcp/mcp_console_standalone.py`
- `src/mcp/vetka_mcp_bridge.py`
- `src/mcp/state/__init__.py`
- `src/mcp/state/mcp_state.py`
- `src/mcp/tools/__init__.py`
- `src/mcp/tools/compound_tools.py`
- `src/mcp/tools/llm_call_tool.py`
- `src/mcp/tools/session_tools.py`

### src/agents/
- `src/agents/hostess_background_prompts.py`

### src/api/handlers/
- `src/api/handlers/di_container.py`
- `src/api/handlers/user_message_handler_legacy.py`
- `src/api/handlers/user_message_handler_v2.py`
- `src/api/handlers/interfaces/__init__.py`
- `src/api/handlers/models/__init__.py`

### src/elisya/
- `src/elisya/__init__.py`

### src/memory/
- `src/memory/elision.py`
- `src/memory/engram_user_memory.py`

### src/orchestration/
- `src/orchestration/services/mcp_state_bridge.py`
- `src/orchestration/services/__init__.py`

### src/scanners/
- `src/scanners/__init__.py`

### src/services/
- `src/services/__init__.py`

---

## Recommended Actions

1. **Priority 1 - MCP Directory**: Add @status markers to all 9 files
2. **Priority 2 - API Handlers**: Add markers to new handler files
3. **Priority 3 - __init__.py files**: Add markers for completeness

---

## Example @status Format

```python
"""
Module description.

@status: active
@phase: 96
@last_audit: 2026-01-28
"""
```
