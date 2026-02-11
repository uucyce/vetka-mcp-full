# MYCELIUM
**Mycelial Yielding Cognitive Execution Layer for Intelligent Unified Mesh**

## The Duality

```
        VETKA (Tree)                    MYCELIUM (Fungal Network)
     What user SEES                   What works UNDERGROUND
  ──────────────────              ──────────────────────────────
  3D visualization                Agent orchestration
  Chat interface (stream)         Task spawning & dispatch
  File browser                    LLM provider management
  Search results                  Heartbeat engine
  Camera controls                 Pipeline execution
  Knowledge Mode (memory view)    DevPanel (Task Board, Activity,
                                    Stats, Results, Pipeline UI)
                                  Tool execution
                                  Inter-agent messaging
                                  Memory routing (STM per-pipeline)
```

**VETKA** renders the tree. **MYCELIUM** feeds it.

### Memory: Shared Data, Separate Routing

Memory is **data** (Qdrant, files), not a service. Both processes access it:

```
                    Qdrant (localhost:6333)
                   ╱                      ╲
        VETKA reads                    MYCELIUM reads
    (Knowledge Mode,               (context injection,
     3D node details,               pipeline STM,
     search results)                 Engram preferences)
```

- **Engram** (user preferences): stored in Qdrant, read by both
- **CAM** (surprise detection): computed by VETKA indexer, read by both
- **STM** (short-term memory): per-pipeline, lives in MYCELIUM process only
- **Knowledge Graph**: rendered by VETKA, data in shared Qdrant

No process locks memory from the other. Like two apps reading one database.

---

## Architecture

### Two MCP Servers

```
Claude Code / Cursor / OpenCode          React DevPanel
          │                                    │
          ├── MCP VETKA (stdio, fast)          │ (SocketIO :5001)
          │     Tools: 25 (search, read,       │
          │       UI, session, memory)          │
          │     Latency: <100ms                │
          │     Process: vetka_mcp_bridge.py   │
          │     State: stateless (REST proxy)  │
          │                                    │
          └── MCP MYCELIUM (stdio, autonomous) ┘ (WebSocket :8082)
                Tools: 17 (pipeline, tasks,
                  heartbeat, LLM, artifacts,
                  DevPanel stream)
                Latency: 1s-300s (LLM calls)
                Process: mycelium_mcp_server.py
                State: task_board.json, pipeline_tasks.json
                DevPanel: direct WebSocket → no VETKA relay
```

**Key:** DevPanel connects to MYCELIUM's WebSocket on port 8082.
Chat stream goes through VETKA's SocketIO on port 5001 (unchanged).
Both share data via filesystem (JSON) and Qdrant (HTTP).

### Why Two, Not Three

Grok proposed 3-4 layers. We go with 2 because:
1. **Shared state via files** — no Redis needed. Both read/write JSON, OS handles filesystem.
2. **Qdrant is already networked** — both servers call `localhost:6333` (HTTP, stateless).
3. **SocketIO relay** — MYCELIUM calls `POST /api/chat/send` on VETKA to emit events. Already works.
4. **No new infrastructure** — no Docker, no Redis, no message queue. Just two Python processes.

A third server (Memory MCP) is a future evolution when Engram/CAM scale beyond single-process.

---

## Tool Distribution

### MCP VETKA (25 tools — fast, stateless, UI-facing)

| Category | Tools | Source |
|----------|-------|--------|
| **Search** | `vetka_search_semantic`, `vetka_search_files`, `vetka_get_tree`, `vetka_get_knowledge_graph`, `vetka_get_metrics` | REST proxy |
| **Files** | `vetka_read_file`, `vetka_list_files`, `vetka_edit_file` | REST + tool |
| **Git** | `vetka_git_status`, `vetka_git_commit` | Tool |
| **Tests** | `vetka_run_tests` | Tool |
| **Session** | `vetka_session_init`, `vetka_session_status` | Tool |
| **Memory** | `vetka_get_conversation_context`, `vetka_get_chat_digest`, `vetka_get_user_preferences`, `vetka_get_memory_summary`, `vetka_get_pinned_files`, `vetka_get_context_dag` | REST + direct |
| **Chat** | `vetka_read_group_messages`, `vetka_send_message` | REST |
| **UI** | `vetka_camera_focus` | Tool |
| **Research** | `vetka_web_search`, `vetka_library_docs` | Tool |

**Character:** Fast. Responds in milliseconds. Never blocks. Pure reads + lightweight writes.
VETKA owns the Chat stream — pipeline agents emit to chat through VETKA's SocketIO.

### MCP MYCELIUM (17 tools — autonomous, stateful, pipeline-facing)

| Category | Tools | Source |
|----------|-------|--------|
| **Pipeline** | `mycelium_pipeline`, `mycelium_heartbeat_tick`, `mycelium_heartbeat_status` | Native |
| **Task Board** | `mycelium_task_board`, `mycelium_task_dispatch`, `mycelium_task_import` | Native |
| **LLM** | `mycelium_call_model` | Native (async) |
| **Compound** | `mycelium_research`, `mycelium_implement`, `mycelium_review` | Native |
| **Workflow** | `mycelium_execute_workflow`, `mycelium_workflow_status` | Native |
| **Artifacts** | `mycelium_list_artifacts`, `mycelium_approve_artifact`, `mycelium_reject_artifact` | Native |
| **DevPanel** | `mycelium_devpanel_stream`, `mycelium_health` | Native (WebSocket) |

**Character:** Autonomous. Runs pipelines for 1-15 minutes. Manages its own state.
MYCELIUM owns the DevPanel — Task Board, Activity Log, Stats, Results.
Direct WebSocket from MYCELIUM → DevPanel React component = zero relay latency.
Chat stream (what user reads) still goes through VETKA (familiar UX, no disruption).

**Namespace change:** `vetka_mycelium_*` / `vetka_task_*` / `vetka_call_model` / `vetka_execute_workflow` → `mycelium_*`. Clean namespace boundary.

### UI Ownership Split

```
     VETKA (React app, port 5173)
     ├── ChatPanel          ← data from VETKA SocketIO (chat_response events)
     ├── Tree3D             ← data from VETKA REST + SocketIO (node_updated)
     ├── FileViewer         ← data from VETKA REST
     └── DevPanel           ← data from MYCELIUM WebSocket (direct connection)
         ├── Task Board     ← mycelium reads task_board.json, streams updates
         ├── Activity Log   ← mycelium streams pipeline_activity
         ├── Stats          ← mycelium streams pipeline_stats
         ├── Results        ← mycelium serves pipeline_tasks.json
         └── Watcher Stats  ← vetka serves (watcher is VETKA's component)
```

**Why DevPanel in MYCELIUM:** During Dragon Silver pipeline, VETKA's event loop was blocked
by pipeline activity floods. With DevPanel connected to MYCELIUM directly, pipeline
activity bypasses VETKA entirely — the DevPanel stays live even if VETKA is busy
with its own agents (search, indexing, camera).

---

## Shared State

### Files (filesystem = shared bus)

| File | Owner | VETKA reads | MYCELIUM reads | MYCELIUM writes |
|------|-------|-------------|----------------|-----------------|
| `data/task_board.json` | MYCELIUM | Yes (GET /task-board) | Yes | Yes |
| `data/pipeline_tasks.json` | MYCELIUM | Yes (GET /results) | Yes | Yes |
| `data/heartbeat_state.json` | MYCELIUM | No | Yes | Yes |
| `data/templates/pipeline_prompts.json` | Shared (read-only) | No | Yes (read) | No |
| `data/templates/model_presets.json` | Shared (read-only) | No | Yes (read) | No |

### Services (network = shared bus)

| Service | Address | VETKA uses | MYCELIUM uses |
|---------|---------|------------|---------------|
| **Qdrant** | `localhost:6333` | Search, index | Search (hybrid) |
| **FastAPI** | `localhost:5001` | Native (runs here) | HTTP client (emit progress, send messages) |
| **Ollama** | `localhost:11434` | Embeddings | Embeddings (for code search) |
| **LLM Providers** | Various APIs | No | Yes (Grok, Qwen, Kimi, GPT via provider_registry) |

### Communication Protocol

```
MYCELIUM → VETKA (chat stream, for user to read):
  POST http://localhost:5001/api/chat/send
    { "message": "@coder writing toggle...", "chat_id": "xxx" }
  This shows up in ChatPanel — familiar UX, no disruption.

MYCELIUM → DevPanel (direct WebSocket, bypasses VETKA):
  ws://localhost:8082/ws/devpanel
    { "type": "pipeline_activity", "role": "@coder", "message": "...", "task_id": "..." }
    { "type": "task_board_updated", "action": "task_completed", "task_id": "tb_xxx" }
    { "type": "pipeline_stats", "stats": {...} }
  DevPanel React component connects directly. No VETKA relay.

VETKA → MYCELIUM (no direct calls needed):
  User calls mycelium_* tools via MCP protocol (stdio)
  MYCELIUM processes autonomously
```

**Two streams, two purposes:**
- Chat stream (VETKA SocketIO) = what the user reads, conversational
- DevPanel stream (MYCELIUM WebSocket) = pipeline control panel, technical

---

## Process Lifecycle

### Startup

```bash
# VETKA (current, unchanged)
python3 main.py
# Starts: FastAPI + SocketIO + Watcher + Qdrant indexer
# Listens: port 5001

# MYCELIUM (new, separate process)
# Started by Claude Code/Cursor via .mcp.json
# OR manually: python3 src/mcp/mycelium_mcp_server.py
# No port needed — communicates via stdio (MCP protocol) + HTTP to VETKA
```

### .mcp.json (updated)

```json
{
  "mcpServers": {
    "vetka": {
      "command": "python3",
      "args": ["src/mcp/vetka_mcp_bridge.py"],
      "env": {
        "VETKA_API_URL": "http://localhost:5001",
        "PYTHONPATH": "/path/to/vetka_live_03"
      }
    },
    "mycelium": {
      "command": "python3",
      "args": ["src/mcp/mycelium_mcp_server.py"],
      "env": {
        "VETKA_API_URL": "http://localhost:5001",
        "PYTHONPATH": "/path/to/vetka_live_03"
      }
    }
  }
}
```

### Shutdown

- VETKA stops → MYCELIUM can still finish current pipeline (graceful), emits will fail silently
- MYCELIUM stops → VETKA continues normally, pipeline status shows "cancelled" in task_board
- Both processes are independent. No parent-child relationship.

---

## MYCELIUM Internal Architecture

### Core Components

```
mycelium_mcp_server.py (entry point)
│
├── MCP Handler (stdio protocol — for Claude Code/Cursor)
│   └── 17 tool handlers (mycelium_* namespace)
│
├── WebSocket Server (port 8082 — for DevPanel)
│   ├── pipeline_activity stream
│   ├── task_board_updated events
│   ├── pipeline_stats stream
│   └── pipeline_results serve
│
├── AgentPipeline (agent_pipeline.py, async_mode=True)
│   ├── Scout → Architect → Researcher → Coder → Verifier
│   ├── FC Loop (coder function calling)
│   ├── Verify-Retry loop
│   └── Tier upgrade (bronze → silver → gold)
│
├── TaskBoard (task_board.py)
│   ├── Priority queue (1-5)
│   ├── Status lifecycle (pending → queued → running → done/failed)
│   ├── Dependency resolution (Sugiyama)
│   └── Pipeline stats recording
│
├── Heartbeat (mycelium_heartbeat.py)
│   ├── Chat scanner (@dragon/@doctor triggers)
│   ├── Task dispatch
│   └── Event-driven wakeup
│
├── LLM Router (async, no ThreadPoolExecutor)
│   ├── call_model_v2 (native async)
│   ├── Provider registry (Polza, OpenRouter, xAI, etc.)
│   └── Key rotation (UnifiedKeyManager)
│
└── HTTP Client (to VETKA)
    ├── Chat message relay (pipeline → ChatPanel)
    └── Search/memory queries (when pipeline needs Qdrant via VETKA API)
```

### Async Pipeline (the key fix)

In MYCELIUM, LLM calls are **natively async**:

```python
# OLD (in vetka_mcp_bridge.py):
def execute(self, arguments):  # SYNC — blocks everything
    with ThreadPoolExecutor() as executor:
        future = executor.submit(asyncio.run, self._async_call())
        result = future.result(timeout=120)  # BLOCKS 120s

# NEW (in mycelium_mcp_server.py):
async def execute(self, arguments):  # ASYNC — event loop stays free
    result = await call_model_v2(
        messages=messages, model=model, provider=provider
    )
    return result
```

No ThreadPoolExecutor hack. No asyncio.run() inside running loop. Native async all the way.

---

## Dragon Teams (unchanged, now in MYCELIUM)

| Tier | Preset | Architect | Researcher | Coder | Verifier |
|------|--------|-----------|------------|-------|----------|
| Bronze | `dragon_bronze` | Qwen3-30b | Grok Fast 4.1 | Qwen3-coder-flash | Mimo-v2-flash |
| Silver | `dragon_silver` | Kimi K2.5 | Grok Fast 4.1 | Qwen3-coder | GLM-4.7-flash |
| Gold | `dragon_gold` | Kimi K2.5 | Grok Fast 4.1 | Qwen3-coder | Qwen3-235b |

Auto-tier based on architect's `estimated_complexity`. Configurable in `data/templates/model_presets.json`.

---

## Contracts

### spawn(task) → task_id

```python
# Tool: mycelium_pipeline
mycelium_pipeline(
    task="Add chat favorites with star icon",
    phase_type="build",        # build | fix | research
    preset="dragon_silver",    # dragon_bronze | dragon_silver | dragon_gold
    chat_id="group_mcp_dev",   # where to emit progress
    auto_write=False           # staging mode (safe)
) → { "task_id": "task_1770665725", "status": "executing" }
```

### heartbeat(state)

```python
# Tool: mycelium_heartbeat_tick
mycelium_heartbeat_tick(
    group_id="group_mcp_dev",  # chat to scan for @dragon/@doctor
    dry_run=True               # preview without executing
) → { "tasks_found": 2, "dispatched": 0 }
```

### task.manage()

```python
# Tool: mycelium_task_board
mycelium_task_board(
    action="list",             # add | list | get | update | remove | summary
    filter_status="pending"
) → { "tasks": [...], "summary": {...} }
```

### model.call()

```python
# Tool: mycelium_call_model
mycelium_call_model(
    model="qwen3-coder",
    messages=[{"role": "user", "content": "..."}],
    model_source="polza",
    temperature=0.7,
    max_tokens=4096
) → { "content": "...", "model": "qwen3-coder", "usage": {...} }
```

---

## Non-Goals

- **Rendering** — VETKA handles all 3D, React, Three.js
- **Chat stream** — VETKA owns the chat UX (agent messages flow through VETKA SocketIO)
- **File indexing** — VETKA's Watcher + TripleWrite handles Qdrant indexing
- **User session** — VETKA's session_init stays in VETKA (fast, lightweight)
- **Git operations** — stay in VETKA (fast, no LLM needed)
- **Search** — stays in VETKA (Qdrant queries are fast, no blocking)
- **Long-term memory storage** — Qdrant/Engram are shared data, not owned by either process
- **Knowledge Mode rendering** — VETKA reads memory data, renders 3D graph

---

## Migration Path

### Phase 1: Extract (create mycelium_mcp_server.py)
1. Create `src/mcp/mycelium_mcp_server.py` — new MCP server entry point (stdio)
2. Create `src/mcp/mycelium_ws_server.py` — WebSocket server for DevPanel (port 8082)
3. Move pipeline-related tool handlers from `vetka_mcp_bridge.py`
4. Create `llm_call_tool_async.py` — native async LLM (no ThreadPoolExecutor)
5. Wire HTTP client for chat message relay to VETKA
6. Update `.mcp.json` with second server entry
7. Update DevPanel to connect to MYCELIUM WebSocket (port 8082)

### Phase 2: Clean (remove pipeline from VETKA bridge)
1. Remove `vetka_mycelium_pipeline`, `vetka_task_board`, `vetka_task_dispatch` from `vetka_mcp_bridge.py`
2. Remove `vetka_call_model`, `vetka_heartbeat_tick` from `vetka_mcp_bridge.py`
3. Remove `vetka_execute_workflow` from `vetka_mcp_bridge.py`
4. VETKA bridge becomes pure UI/search/files proxy (25 tools, all fast)

### Phase 3: Harden
1. Add health check: `mycelium_health` tool
2. Add graceful shutdown (finish current subtask, save state)
3. Add crash recovery (resume from last saved subtask)
4. Pipeline stats exposed via `mycelium_stats` tool

### Phase 4: Scale (future)
1. Move MYCELIUM to remote server (cloud GPU for local Ollama models)
2. VETKA stays local (desktop app, Tauri)
3. Communication: VETKA ← HTTPS → MYCELIUM (replace localhost with remote URL)
4. Remote tech support: customer runs VETKA, MYCELIUM runs on your server
5. Multiple MYCELIUM workers for parallel pipeline execution

---

## File Structure

```
src/mcp/
├── vetka_mcp_bridge.py          # VETKA MCP server (25 tools, fast, stateless)
├── mycelium_mcp_server.py       # MYCELIUM MCP server (17 tools, autonomous) [NEW]
├── mycelium_http_client.py      # HTTP client for VETKA callbacks [NEW]
├── mycelium_ws_server.py        # WebSocket server for DevPanel (port 8082) [NEW]
├── tools/
│   ├── base_tool.py             # BaseMCPTool (sync, for VETKA tools)
│   ├── base_async_tool.py       # BaseAsyncMCPTool (async, for MYCELIUM) [NEW]
│   ├── llm_call_tool.py         # LLMCallTool (sync, stays for VETKA legacy)
│   ├── llm_call_tool_async.py   # LLMCallToolAsync (async, for MYCELIUM) [NEW]
│   ├── camera_tool.py           # → stays in VETKA
│   ├── edit_file_tool.py        # → stays in VETKA
│   ├── git_tool.py              # → stays in VETKA
│   ├── run_tests_tool.py        # → stays in VETKA
│   └── ...
src/orchestration/
├── agent_pipeline.py            # → used by MYCELIUM (async_mode=True)
├── task_board.py                 # → used by MYCELIUM (native, not imported by VETKA)
├── mycelium_heartbeat.py        # → used by MYCELIUM
client/src/
├── hooks/
│   └── useMyceliumSocket.ts     # WebSocket hook for MYCELIUM port 8082 [NEW]
├── components/panels/
│   └── DevPanel.tsx             # → connects to MYCELIUM WebSocket (not VETKA SocketIO)
```

---

## Success Metrics

| Metric | Before (monolith) | After (dual MCP) |
|--------|-------------------|-------------------|
| `/api/health` during pipeline | ❌ Timeout (60-300s) | ✅ <100ms always |
| `vetka_search_semantic` during pipeline | ❌ Blocked | ✅ <200ms always |
| Chat stream during Dragon Silver | ❌ Frozen | ✅ Always responsive |
| DevPanel during Dragon Silver | ❌ Frozen (VETKA relay) | ✅ Direct MYCELIUM WebSocket |
| Concurrent pipelines | ❌ 1 (blocks) | ✅ 1 per MYCELIUM process |
| Remote deployment | ❌ Impossible | ✅ Change URL in .mcp.json |
| Crash isolation | ❌ Pipeline crash = server crash | ✅ MYCELIUM crash, VETKA survives |
| Memory access during pipeline | ❌ Contended (shared event loop) | ✅ Both read Qdrant independently |

---

*VETKA shows the tree. MYCELIUM grows it.*
