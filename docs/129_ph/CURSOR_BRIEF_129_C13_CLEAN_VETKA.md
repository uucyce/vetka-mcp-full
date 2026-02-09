# CURSOR BRIEF Phase 129.C13: Clean Pipeline Tools from VETKA Bridge

## Context
Phase 129 created MYCELIUM MCP server (`mycelium_mcp_server.py`) with 17 tools.
The old `vetka_mcp_bridge.py` still has deprecated stubs and handlers for these tools.
They need to be removed — VETKA bridge should only have fast, stateless tools (25 tools).

**Commit reference:** f83cdfeb (Phase 129 MYCELIUM MCP Server)

## What to Remove

### 1. Tool Definition Stubs (in `list_tools()`, lines ~875-910)

These are deprecated stubs added during Phase 129. Remove ALL 6:

```
Line 881-883: vetka_mycelium_pipeline (deprecated stub)
Line 886-889: vetka_heartbeat_tick (deprecated stub)
Line 891-894: vetka_heartbeat_status (deprecated stub)
Line 896-899: vetka_task_board (deprecated stub)
Line 901-904: vetka_task_dispatch (deprecated stub)
Line 906-909: vetka_task_import (deprecated stub)
```

### 2. Tool Handlers (in `call_tool()` dispatch)

Remove these handler blocks. **Replace each with a 3-line deprecation stub:**

```python
elif name == "vetka_mycelium_pipeline":
    return [TextContent(type="text", text=json.dumps({
        "error": "Moved to MYCELIUM MCP server. Use mycelium_pipeline instead.",
        "migration": "Add 'mycelium' MCP server to .mcp.json"
    }))]
```

**Handlers to replace with stubs:**

| Tool | Handler Lines | Lines to Remove |
|------|--------------|-----------------|
| vetka_mycelium_pipeline | 1688-1788 | ~101 lines |
| vetka_heartbeat_tick | 1791-1831 | ~41 lines |
| vetka_heartbeat_status | 1833-1871 | ~39 lines |
| vetka_task_board | 1875-1885 | ~11 lines |
| vetka_task_dispatch | 1887-1897 | ~11 lines |
| vetka_task_import | 1899-1909 | ~11 lines |
| vetka_execute_workflow | 1675-1679 | ~4 lines |
| vetka_workflow_status | 1681-1685 | ~4 lines |
| vetka_research | 1631-1640 | ~9 lines |
| vetka_implement | 1642-1658 | ~16 lines |
| vetka_review | 1660-1669 | ~9 lines |
| vetka_call_model | 1297-1308 | ~11 lines |

**Total: ~267 lines removed, replaced with ~36 lines of deprecation stubs (12 tools x 3 lines)**

### 3. Also Remove: vetka_call_model Tool Definition

```
Lines 598-676: vetka_call_model Tool definition (~78 lines)
```

Replace with deprecation stub.

### 4. Keep These (they stay in VETKA for now):

- `vetka_edit_artifact` (lines 913-935 def, 1913-1946 handler) — **KEEP**
- `vetka_approve_artifact` (lines 937-955 def, 1948-1963 handler) — **KEEP**
- `vetka_reject_artifact` (lines 957-974 def, 1965-1980 handler) — **KEEP**
- `vetka_list_artifacts` (lines 976-997 def, 1982-2029 handler) — **KEEP**
- `vetka_arc_suggest` (lines 825-873 def, 1559-1608 handler) — **KEEP**

### 5. Remove Unused Imports

After removing handlers, check if these imports are still needed:
- `from src.mcp.tools.task_board_tools import handle_task_board, handle_task_dispatch, handle_task_import`
- `from src.orchestration.mycelium_heartbeat import heartbeat_tick, get_heartbeat_status`
- `from src.mcp.tools.compound_tools import register_compound_tools` (keep if other compound tools remain)
- `from src.mcp.tools.workflow_tools import register_workflow_tools` (remove if no workflow tools remain)

If they're only used by removed handlers, delete the imports.

## Deprecation Stub Pattern

Every removed tool should still respond if called, with a helpful migration message:

```python
elif name == "vetka_heartbeat_tick":
    return [TextContent(type="text", text=json.dumps({
        "error": "Moved to MYCELIUM MCP server. Use mycelium_heartbeat_tick instead.",
        "migration": "Add 'mycelium' server entry to .mcp.json"
    }))]
```

## Expected Result

- `vetka_mcp_bridge.py`: 2874 lines -> ~2500 lines (~370 lines removed)
- VETKA serves 25 fast tools (search, files, git, session, memory, UI, chat)
- Old tool names return deprecation message pointing to MYCELIUM
- No functional changes to remaining tools

## Testing

1. Verify bridge still starts: `python src/mcp/vetka_mcp_bridge.py` (no import errors)
2. Verify remaining tools work: `vetka_search_semantic`, `vetka_read_file`, `vetka_session_init`
3. Verify deprecation stubs: call `vetka_mycelium_pipeline` -> returns migration message

## Markers
- MARKER_129.C13A: Removed tool definitions
- MARKER_129.C13B: Deprecation stubs in call_tool

## Files
- `src/mcp/vetka_mcp_bridge.py` (MODIFY, -370 lines)

## Style
- Keep all remaining tool logic unchanged
- Deprecation messages: JSON with "error" + "migration" keys
- No console warnings/logs for deprecated calls (silent redirect)

## Estimated Effort
- 1-2 hours
