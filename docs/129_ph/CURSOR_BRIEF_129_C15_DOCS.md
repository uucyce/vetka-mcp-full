# CURSOR BRIEF Phase 129.C15: CLAUDE.md Docs Polish

## Context
CLAUDE.md was already updated with dual MCP architecture in Phase 129.
This brief is for **polish only** — verify everything is accurate after C13 cleanup.

## Status: MOSTLY DONE
CLAUDE.md already contains:
- Dual MCP Architecture table (VETKA vs MYCELIUM)
- MCP VETKA tools section (fast, stateless)
- MCP MYCELIUM tools section (async, pipelines)
- Deprecation note for old vetka_* tool names
- Current Phase: 129
- .mcp.json reference

## What to Verify/Update After C13

### 1. Tool Count
After C13 removes pipeline tools from VETKA bridge:
- VETKA: verify "25 tools" is accurate (count after removal)
- MYCELIUM: verify "17 tools" matches mycelium_mcp_server.py

### 2. Add Missing MYCELIUM Tools to Docs
Currently listed: pipeline, call_model, task_board, task_dispatch, heartbeat_tick, heartbeat_status

Missing from CLAUDE.md (add to MCP MYCELIUM section):
- `mycelium_task_import` — Import tasks from todo file
- `mycelium_execute_workflow` — Full PM→QA workflow
- `mycelium_workflow_status` — Check workflow execution
- `mycelium_research` — Semantic search + summarize
- `mycelium_implement` — Plan implementation
- `mycelium_review` — Review file
- `mycelium_list_artifacts` / `mycelium_approve_artifact` / `mycelium_reject_artifact`
- `mycelium_health` — Health check
- `mycelium_devpanel_stream` — WebSocket broadcaster info

### 3. Add WebSocket Port Reference
Under Architecture, add:
```
- **MYCELIUM WebSocket:** Port 8082 (DevPanel direct connection)
```

## Files
- `CLAUDE.md` (MODIFY, +10-15 lines)

## Estimated Effort
- 15-30 min (polish only, not rewrite)
