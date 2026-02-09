# Grok Research: MCP Architecture Bottleneck Analysis

## Date: 2026-02-09
## Source: Grok via VETKA chat (user relay)
## Status: Key insight — validates user intuition

## Core Finding
Single `vetka_mcp_bridge.py` process serves ALL MCP requests.
When pipeline runs heavy tasks (self-editing, fractal decomposition),
Socket.IO events block → frontend freezes → "Ветка висит".

## Bottleneck Map

| Bottleneck | Location | Impact |
|---|---|---|
| Single MCP Bridge | `.mcp.json` → one process | Blocks UI during pipeline |
| STM Drift & Compression | agent_pipeline.py (ELISION) | Sync compress hangs on 1000+ tokens |
| Socket.IO Blocking | stream_handler.py | Frontend freezes on `pipeline_progress` |
| Parallel Limit | MAX_PARALLEL_PIPELINES=5 | MCP + self-edit = queue buildup |
| Self-Editing Loop | Fractal subtasks cascade | One MCP call → cascade → full hang |

## Proposed Architecture: Fractal MCP Layers

```
Layer 1: MCP-Frontend (UI/3D)     <- Socket.IO rooms
             ↓ (Redis Pub/Sub or async queue)
Layer 2: MCP-Pipeline             <- agent_pipeline.py (semaphore → queues)
             ↓ (gRPC/HTTP)
Layer 3: MCP-Tools/STM            <- vetka_mcp_bridge.py → multiple instances
             ↓ (Qdrant vectors)
Layer 4: MCP-SelfEdit (sandbox)   <- Separate process for file editing
```

## Quick Wins (Low Effort)

1. **Multiple MCP servers** in `.mcp.json` — split UI tools from pipeline tools
2. **Async queues** between layers — asyncio.Queue in agent_pipeline.py
3. **Priority routing** — UI events first, edit events last
4. **Prometheus metrics** in progress_tracker.py — measure hang duration

## Phase Allocation
- Quick wins → Phase 128-129 (now)
- Full fractal layers → Phase 130+ (architecture)
- Kubernetes scaling → Phase 135+ (future)

## Action Items for Current Phase
1. Separate `pipeline_activity` broadcast from `chat_response` emit (done in 127.2)
2. Make STM compression async (not blocking emit)
3. Add timeout to MCP bridge tool calls
