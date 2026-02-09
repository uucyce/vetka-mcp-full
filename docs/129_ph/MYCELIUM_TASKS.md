# MYCELIUM Implementation Tasks

## Overview
Extract pipeline infrastructure from VETKA MCP bridge into autonomous MYCELIUM MCP server.

---

## Phase 1: Extract (Core)

### O1: mycelium_mcp_server.py — Entry Point
**Agent:** Opus
**Effort:** 3-4 hours
**Files:** `src/mcp/mycelium_mcp_server.py` (NEW)

Create new MCP server with stdio transport:
- MCP protocol handler (same pattern as vetka_mcp_bridge.py but smaller)
- 14 tool registrations (mycelium_* namespace)
- Async tool dispatch (no sync BaseMCPTool limitation)
- Lazy imports for heavy deps (agent_pipeline, provider_registry)
- VETKA_API_URL from env for HTTP callbacks

**Dependencies:** None (greenfield)
**Tests:** `tests/test_mycelium_mcp_server.py` — tool listing, dispatch routing

### O2: BaseAsyncMCPTool — Async Tool Interface
**Agent:** Opus
**Effort:** 30 min
**Files:** `src/mcp/tools/base_async_tool.py` (NEW)

```python
class BaseAsyncMCPTool(ABC):
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pass
```

MYCELIUM tools inherit from this. VETKA tools stay on sync BaseMCPTool.
No cross-contamination. Clean boundary.

### O3: Async LLMCallTool for MYCELIUM
**Agent:** Opus
**Effort:** 2 hours
**Files:** `src/mcp/tools/llm_call_tool_async.py` (NEW)

Fork of `llm_call_tool.py` with:
- `async def execute()` — native async
- Direct `await call_model_v2()` — no ThreadPoolExecutor
- Direct `await self._gather_inject_context()` — no asyncio.run() hack
- Same security filters (SAFE_FUNCTION_CALLING_TOOLS allowlist)
- Same usage tracking (_track_usage_for_balance)

**Why fork, not modify:** Original `llm_call_tool.py` stays untouched for VETKA bridge.
MYCELIUM gets clean async version. No breaking changes.

### O4: mycelium_http_client.py — VETKA Callbacks
**Agent:** Opus
**Effort:** 1 hour
**Files:** `src/mcp/mycelium_http_client.py` (NEW)

Async HTTP client for MYCELIUM → VETKA communication:
```python
class MyceliumClient:
    async def emit_progress(self, role, message, task_id, model):
        await httpx.post(f"{VETKA_URL}/api/chat/send", json={...})

    async def notify_board_update(self, action, task_id):
        await httpx.post(f"{VETKA_URL}/api/debug/task-board/notify", json={...})

    async def send_chat_message(self, chat_id, message, sender="mycelium"):
        await httpx.post(f"{VETKA_URL}/api/chat/send", json={...})
```

### O5: Wire agent_pipeline.py to use async LLM
**Agent:** Opus
**Effort:** 2 hours
**Files:** `src/orchestration/agent_pipeline.py` (MODIFY)

Add `async_mode` flag to AgentPipeline:
- When `async_mode=True` (MYCELIUM): uses `await tool.execute()` at all 5 call sites
- When `async_mode=False` (VETKA legacy): uses `tool.execute()` sync (unchanged)
- `_get_llm_tool()` returns async version when async_mode=True

**Lines to change:** 362, 708, 2271, 2375, 2576

### O6: Update .mcp.json
**Agent:** Opus
**Effort:** 5 min
**Files:** `.mcp.json` (MODIFY)

Add `mycelium` server entry alongside `vetka`.

---

## Phase 2: Clean (Remove from VETKA)

### C13: Remove pipeline tools from vetka_mcp_bridge.py
**Agent:** Cursor
**Effort:** 1 hour
**Files:** `src/mcp/vetka_mcp_bridge.py` (MODIFY)

Remove these tool handlers:
- `vetka_mycelium_pipeline` → now `mycelium_pipeline`
- `vetka_heartbeat_tick` → now `mycelium_heartbeat_tick`
- `vetka_heartbeat_status` → now `mycelium_heartbeat_status`
- `vetka_task_board` → now `mycelium_task_board`
- `vetka_task_dispatch` → now `mycelium_task_dispatch`
- `vetka_task_import` → now `mycelium_task_import`
- `vetka_call_model` → now `mycelium_call_model`
- `vetka_execute_workflow` → now `mycelium_execute_workflow`
- `vetka_workflow_status` → now `mycelium_workflow_status`
- `vetka_edit_artifact` → now `mycelium_edit_artifact` (or keep in VETKA)
- `vetka_approve_artifact` → now `mycelium_approve_artifact`
- `vetka_reject_artifact` → now `mycelium_reject_artifact`
- `vetka_list_artifacts` → now `mycelium_list_artifacts`

Keep backward compat: add deprecation warning if old tool names called.

### O10: mycelium_ws_server.py — WebSocket for DevPanel
**Agent:** Opus
**Effort:** 2 hours
**Files:** `src/mcp/mycelium_ws_server.py` (NEW)

WebSocket server on port 8082 for DevPanel direct connection:
- `pipeline_activity` events (role, message, task_id, model)
- `task_board_updated` events (action, task data)
- `pipeline_stats` events (per-pipeline metrics)
- `pipeline_results` serve (subtask results on demand)
- Connection management (multiple DevPanel tabs)

Uses `websockets` library (lightweight, no FastAPI needed).

### C14: DevPanel → MYCELIUM WebSocket
**Agent:** Cursor
**Effort:** 2 hours
**Files:**
- `client/src/hooks/useMyceliumSocket.ts` (NEW)
- `client/src/components/panels/DevPanel.tsx` (MODIFY)

Changes:
- New hook `useMyceliumSocket()` — connects to `ws://localhost:8082/ws/devpanel`
- DevPanel data source: MYCELIUM WebSocket instead of VETKA SocketIO
- Show connection indicator: green dot = MYCELIUM connected, red = disconnected
- Task Board, Activity Log, Stats, Results — all from MYCELIUM stream
- Fallback: if MYCELIUM WebSocket down, try VETKA SocketIO (backward compat)

### C15: Update CLAUDE.md tool documentation
**Agent:** Cursor
**Effort:** 30 min
**Files:** `CLAUDE.md` (MODIFY)

Document new mycelium_* tool names and usage.
Document dual MCP architecture (VETKA + MYCELIUM).

---

## Phase 3: Harden

### O7: Health check + graceful shutdown
**Agent:** Opus
**Effort:** 1 hour

- `mycelium_health` tool — returns process uptime, current pipeline status, queue depth
- Signal handler (SIGTERM/SIGINT) — finish current subtask, save state, exit

### O8: Crash recovery
**Agent:** Opus
**Effort:** 2 hours

- On startup, check `pipeline_tasks.json` for `status=executing` tasks
- Resume or mark as failed with last known subtask
- Heartbeat state recovery from `heartbeat_state.json`

### O9: MYCELIUM → VETKA SocketIO relay
**Agent:** Opus
**Effort:** 1 hour

Current: `agent_pipeline._emit_progress()` uses direct SocketIO access.
After: MYCELIUM has no SocketIO server. Relay via HTTP:
- `POST /api/pipeline/progress` → VETKA broadcasts via SocketIO
- New endpoint in `debug_routes.py` or `main.py`

---

## Phase 4: Scale (Future)

### F1: Remote MYCELIUM deployment
- Docker container with MYCELIUM + dependencies
- `VETKA_API_URL=https://remote-server.com`
- Auth: API key in .env

### F2: Multiple MYCELIUM workers
- Worker pool: N instances of mycelium_mcp_server.py
- Task board becomes central dispatcher (Redis or shared DB)
- Each worker pulls next pending task

### F3: Memory MCP (third server)
- Extract Engram, CAM, STM to dedicated MCP
- Heavy vector operations isolated
- Shared by both VETKA and MYCELIUM

---

## Task Order (Critical Path)

```
O2 (BaseAsyncTool) ─────┐
                         ├──→ O3 (Async LLMCall) ──→ O5 (Wire pipeline) ──→ O1 (Server) ──→ O6 (.mcp.json)
O4 (HTTP Client) ────────┤                                                      │
O10 (WS Server) ─────────┘                                                      │
                                                                                 ↓
                                                                          E2E TEST
                                                                                 │
                                                              ┌──────────────────┤
                                                              ↓                  ↓
                                                   C14 (DevPanel WS)    C13 (Clean VETKA)
                                                              │                  │
                                                              ↓                  ↓
                                                        C15 (Docs)    O7 (Health) → O8 (Recovery)
```

**Parallel work:**
- Opus: O1-O6, O10 (core server + async pipeline + WebSocket)
- Cursor: C13-C15 (cleanup + DevPanel WebSocket + docs) — AFTER E2E test passes

---

## Estimated Timeline

| Day | Opus | Cursor |
|-----|------|--------|
| 1 | O2 + O3 + O4 (async tools + HTTP client) | Wave 3 polish (finishing) |
| 1 | O5 (wire pipeline async_mode) + O10 (WS server) | |
| 2 | O1 (server entry point) + O6 (.mcp.json) | |
| 2 | E2E test: Dragon Silver via MYCELIUM | C14 (DevPanel → MYCELIUM WS) |
| 3 | O7 (health) | C13 (remove from VETKA bridge) |
| 3 | O8 (crash recovery) | C15 (docs) |
| 4 | Buffer + fixes | Buffer + fixes |

**Total: 3-4 days, parallelizable between Opus and Cursor.**
