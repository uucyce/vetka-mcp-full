# Recon Report: Pipeline Architecture for External Clients (Phase 128)

## Date: 2026-02-09
## Author: Opus + 3 Haiku Scouts
## Status: Verified

## Key Finding
Mycelium pipeline is already accessible to external clients via REST API and MCP tools.
No major architectural changes needed — just documentation and minor wiring.

## Entry Points Ready for External Clients

| Entry Point | Protocol | URL/Tool | Ready |
|---|---|---|---|
| Task Board Dispatch | REST | `POST /api/debug/task-board/dispatch` | YES |
| Pipeline Results | REST | `GET /api/debug/pipeline-results/{task_id}` | YES |
| Task Board CRUD | REST | `GET/POST/PATCH/DELETE /api/debug/task-board/*` | YES |
| Test League | REST | `POST /api/debug/task-board/test-league` | YES |
| Cancel Task | REST | `POST /api/debug/task-board/cancel` | YES |
| Mycelium Pipeline | MCP | `vetka_mycelium_pipeline` | YES |
| Task Board | MCP | `vetka_task_board` | YES |
| Heartbeat | MCP | `vetka_heartbeat_tick` | YES |

## Pipeline Output Channels

1. **SocketIO `pipeline_activity`** — broadcast to ALL clients (progress bars, logs)
2. **SocketIO `chat_response`** — targeted to specific chat (solo mode)
3. **HTTP POST** — to group chat `/api/debug/mcp/groups/{chat_id}/send`
4. **JSON file** — `data/pipeline_tasks.json` (persistent results)
5. **Disk files** — `src/vetka_out/` and `artifacts/` (when auto_write=True)
6. **SocketIO `task_board_updated`** — real-time board state changes

## Chat Coupling Points (agent_pipeline.py)

| Line | Type | What |
|------|------|------|
| 178 | Init | `self.chat_id = chat_id` |
| 181-182 | Init | `self.sio = sio`, `self.sid = sid` |
| 989 | Broadcast | `pipeline_activity` to ALL clients |
| 1005 | Targeted | `chat_response` to specific sid |
| 1018 | HTTP | POST to group chat |
| 1516 | File | Write code to disk |
| 1791 | Hook | `on_pipeline_complete(chat_id)` |

## For Cursor Integration
Cursor can trigger pipeline via:
```bash
# 1. Add task
curl -X POST localhost:5001/api/debug/task-board/add \
  -H 'Content-Type: application/json' \
  -d '{"title":"...", "description":"...", "priority":2, "phase_type":"build"}'

# 2. Dispatch
curl -X POST localhost:5001/api/debug/task-board/dispatch \
  -d '{"task_id":"tb_xxx"}'

# 3. Get results
curl localhost:5001/api/debug/pipeline-results/tb_xxx
```

## For MCP Clients (OpenCode, Claude Code)
```
vetka_mycelium_pipeline(task="...", phase_type="build", preset="dragon_silver")
vetka_task_board(action="list")
```
