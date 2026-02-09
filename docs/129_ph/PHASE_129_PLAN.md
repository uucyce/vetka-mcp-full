# Phase 129: MCP Scaling — Async Pipeline Fix

## Date: 2026-02-09
## Commander: Opus

## Problem Statement
Single-threaded FastAPI event loop blocks entirely during pipeline execution.
LLMCallTool.execute() is SYNC, calls asyncio.run() inside running loop via ThreadPoolExecutor hack.
Result: server unresponsive for 60-300s during any pipeline run.

## Root Cause
```
Pipeline (async) → LLMCallTool.execute() (SYNC!) → ThreadPoolExecutor → asyncio.run()
                                                   ↑ BLOCKS EVENT LOOP
```

### Critical files:
- `src/mcp/tools/llm_call_tool.py:720` — `def execute()` must become `async def execute()`
- `src/mcp/tools/llm_call_tool.py:750-760` — ThreadPoolExecutor hack (remove)
- `src/mcp/tools/llm_call_tool.py:686-700` — Another ThreadPoolExecutor hack (remove)
- `src/orchestration/agent_pipeline.py:2375` — `tool.execute()` → `await tool.execute()`

## Fix Strategy

### 129.1: Async LLMCallTool (Opus — Priority 0)
1. Convert `LLMCallTool.execute()` to `async def execute()`
2. Replace `asyncio.run()` wrappers with direct `await`
3. Replace ThreadPoolExecutor hacks with `asyncio.to_thread()` where needed
4. Update pipeline calls: `tool.execute()` → `await tool.execute()`
5. Update MCP bridge tool dispatch for async tools
6. Tests: verify server responds during pipeline execution

### 129.2: Pipeline Process Isolation (Opus — if 129.1 insufficient)
1. Run pipeline in separate subprocess via `multiprocessing`
2. Pipeline communicates with FastAPI via IPC (Unix socket or Redis)
3. FastAPI stays responsive, pipeline runs independently
4. Progress events relayed via SocketIO

### 129.3: MCP Server Split (Grok Research → Implementation)
Based on Grok's research in `docs/128_ph/GROK_RESEARCH_128_MCP_BOTTLENECK.md`:
1. Split `vetka_mcp_bridge.py` (35+ tools) into 2-3 MCP servers:
   - **MCP-UI**: camera, viewport, tree, search (fast, stateless)
   - **MCP-Pipeline**: mycelium, task_board, heartbeat (async, long-running)
   - **MCP-Files**: read, edit, search, list (I/O bound)
2. Shared state via Qdrant + Redis/file-based STM
3. `.mcp.json` supports multiple server entries

## Assignment Table

| ID | Task | Agent | Priority | Est. |
|----|------|-------|----------|------|
| O1 | 129.1 Async LLMCallTool | Opus | P0 | 3h |
| G1 | 129.3 MCP Split Research (deep) | Grok | P1 | relay |
| C1 | Toast notifications (128.7) | Cursor | P2 | 30min |
| C2 | Apply All button (128.8) | Cursor | P2 | 45min |
| C3 | Keyboard shortcuts (128.9) | Cursor | P3 | 30min |
| M1 | Marker placement for 129.1 | Mistral | P1 | 15min |

## Success Criteria
- [ ] `/api/health` responds in <1s during pipeline execution
- [ ] SocketIO stays connected during 60s Grok call
- [ ] Multiple concurrent pipelines work
- [ ] verifier_avg_confidence ≥ 0.8 on E2E test
- [ ] Zustand imports (not MobX) in all generated code
- [ ] Server CPU <50% during idle between pipeline subtasks

## Dependencies
- Phase 128 complete (all committed)
- Server must be restarted after changes
