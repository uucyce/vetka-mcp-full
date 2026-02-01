# Phase 106: Multi-Agent MCP Architecture
## Research Synthesis Report

**Date:** 2026-02-02
**Methodology:** 9 Haiku Scouts → 3 Sonnet Verifiers → Architect Synthesis
**Status:** Research Complete, Ready for Implementation

---

## Executive Summary

VETKA's current MCP Bridge (`vetka_mcp_bridge.py`) has a **single stdio transport bottleneck** that limits the system to one Claude client at a time. This Phase introduces a **Multi-Agent MCP Hub** architecture enabling 100+ concurrent agents with zero blocking.

### Key Findings

| Problem | Impact | Solution |
|---------|--------|----------|
| Single stdio_server() | 1 client max | WebSocket multi-transport |
| Global httpx.AsyncClient | Race conditions | Per-session client pools |
| No per-provider queuing | Grok blocks Haiku | Model-specific semaphores |
| No session isolation | State collision | workflow_id + session_id namespacing |

---

## 1. Current Architecture Analysis

### 1.1 MCP Bridge Bottleneck (CONFIRMED ✅)

**Location:** `src/mcp/vetka_mcp_bridge.py:1888`

```python
async with stdio_server() as (read_stream, write_stream):
    # ALL clients funnel through single stdio context
```

**Impact:**
- One Claude Desktop/Code instance at a time
- Sequential tool execution (no parallelism)
- 90s timeout blocks entire bridge

### 1.2 HTTP Transport EXISTS (CONFIRMED ✅)

**Location:** `src/mcp/vetka_mcp_server.py:87-254`

```python
async def run_http(host: str = "0.0.0.0", port: int = 5002):
    # Starlette ASGI app with JSON-RPC endpoint
    # Already supports concurrent clients!
```

**Finding:** Phase 65.2 already implemented HTTP transport. Can be activated with `--http --port 5002`.

### 1.3 WebSocket Transport Status (NEEDS_UPDATE ⚠️)

**Haiku claimed:** MCP SDK has `mcp.server.websocket`
**Sonnet verified:** Module does NOT exist in installed SDK

**Correction:** WebSocket transport must be **manually implemented** using the HTTP transport pattern as template.

---

## 2. Connection Pooling Analysis

### 2.1 Current httpx Usage (CONFIRMED ✅)

| Location | Pattern | Issue |
|----------|---------|-------|
| `vetka_mcp_bridge.py:62-76` | Single global client | No limits configured |
| `direct_api_calls.py:52,131,219` | Per-request clients | Connection waste |
| `provider_registry.py:179,315` | Per-call clients | No pooling |

### 2.2 Recommended Configuration

```python
httpx.AsyncClient(
    limits=httpx.Limits(
        max_connections=50,           # Total pool size
        max_keepalive_connections=10,  # Per session
        keepalive_expiry=30.0
    ),
    timeout=httpx.Timeout(90.0, connect=10.0)
)
```

---

## 3. Concurrency Control Analysis

### 3.1 Current Limits (CONFIRMED ✅)

**Location:** `src/orchestration/orchestrator_with_elisya.py:123`

```python
MAX_CONCURRENT_WORKFLOWS = 2  # Global limit for ALL agents
```

**Location:** `src/orchestration/agent_pipeline.py:36-46`

```python
MAX_PARALLEL_PIPELINES = int(os.getenv("VETKA_MAX_PARALLEL", "5"))
_pipeline_semaphore = asyncio.Semaphore(MAX_PARALLEL_PIPELINES)
```

### 3.2 Agent Timeouts

| Agent | Timeout | Notes |
|-------|---------|-------|
| PM | 30s | Planning |
| Architect | 45s | Design |
| Dev | 120s | Complex implementation |
| QA | 40s | Verification |

### 3.3 Missing Infrastructure

- ❌ No per-provider queuing (Grok: 10 slots, Haiku: 50)
- ❌ No aiolimiter/TokenBucket for rate limiting
- ❌ No backpressure signal propagation

---

## 4. State Management Analysis

### 4.1 MCPStateManager (CONFIRMED ✅)

**Location:** `src/mcp/state/mcp_state_manager.py`

| Feature | Value | Notes |
|---------|-------|-------|
| Collection | `vetka_mcp_states` | Single Qdrant collection |
| Cache | LRU max 100 | OrderedDict |
| TTL | 3600s (1 hour) | Configurable |
| Isolation | workflow_id | Payload filtering |

### 4.2 MCPStateBridge Pattern (CONFIRMED ✅)

**Location:** `src/orchestration/services/mcp_state_bridge.py`

```python
agent_id = f"{workflow_id}_{agent_type}"  # Composite key for isolation
```

**Triple-Write:**
1. LRU Cache (instant)
2. ChangeLog JSONL (critical, never fails)
3. Qdrant vectors (best-effort)

### 4.3 Session Isolation Gap

- ✅ workflow_id isolation EXISTS
- ❌ user_id isolation MISSING
- ❌ ContextVars only used for logging

---

## 5. Socket.IO Infrastructure

### 5.1 Current Setup (CONFIRMED ✅)

**Location:** `main.py:355-368`

```python
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    ping_interval=25,
    ping_timeout=60,
)
app.state.socketio = sio
```

### 5.2 Existing Namespaces

| Namespace | Handler | Events |
|-----------|---------|--------|
| `/` (default) | connection_handlers | connect, disconnect |
| `/workflow` | workflow_socket_handler | join_workflow, leave_workflow |
| N/A | voice_socket_handler | voice_start, voice_audio |

### 5.3 StreamManager (Phase 104.7)

**Location:** `src/api/handlers/stream_handler.py:190-252`

- StreamLevel: FULL, SUMMARY, SILENT
- ELISION compression integration
- Room management for workflow isolation
- Ready for MCP event emission

---

## 6. Actor Pattern Analysis

### 6.1 Best Existing Pattern: VoiceSession

**Location:** `src/api/handlers/voice_router.py:37-77`

```python
@dataclass
class VoiceSession:
    session_id: str
    state: VoiceState = VoiceState.IDLE
    current_task: Optional[asyncio.Task]  # Task-per-session
    conversation_history: List[dict]      # Local message buffer
```

### 6.2 Parallel Execution Pattern

**Location:** `src/orchestration/agent_pipeline.py:938-986`

```python
async def run_subtask_with_limit(idx: int, subtask: Subtask):
    async with semaphore:
        result = await self._execute_subtask(subtask, phase_type)
```

---

## 7. Integration Points Summary

### 7.1 Files to Modify

| File | Changes | Priority |
|------|---------|----------|
| `vetka_mcp_bridge.py` | Add session_id, WebSocket mode | HIGH |
| `vetka_mcp_server.py` | Add /mcp/ws endpoint | HIGH |
| `direct_api_calls.py` | Shared client pool | MEDIUM |
| `provider_registry.py` | Per-model semaphores | MEDIUM |
| `mcp_state_manager.py` | Add user_id field | LOW |

### 7.2 New Files to Create

| File | Purpose |
|------|---------|
| `src/mcp/mcp_actor.py` | MCPActor class with mailbox |
| `src/mcp/client_pool.py` | Per-tenant httpx pool manager |
| `src/api/handlers/mcp_socket_handler.py` | /mcp namespace handler |

---

## 8. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    VETKA MCP HUB                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                     │
│  │ Claude  │  │ Claude  │  │  API    │    N clients        │
│  │ Desktop │  │  Code   │  │ Client  │                     │
│  └────┬────┘  └────┬────┘  └────┬────┘                     │
│       │            │            │                           │
│       └────────────┼────────────┘                           │
│                    ▼                                        │
│  ┌─────────────────────────────────────────┐               │
│  │         Transport Layer                  │               │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │               │
│  │  │stdio │ │ HTTP │ │  WS  │ │ SSE  │   │               │
│  │  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘   │               │
│  └─────┼────────┼────────┼────────┼───────┘               │
│        └────────┴────────┴────────┘                        │
│                    ▼                                        │
│  ┌─────────────────────────────────────────┐               │
│  │           Session Dispatcher             │               │
│  │  ┌─────────────────────────────────┐    │               │
│  │  │ session_id → MCPActor mapping   │    │               │
│  │  └─────────────────────────────────┘    │               │
│  └─────────────────────────────────────────┘               │
│                    ▼                                        │
│  ┌─────────────────────────────────────────┐               │
│  │         MCPActor Pool (100+)            │               │
│  │  ┌────────┐ ┌────────┐ ┌────────┐      │               │
│  │  │Actor 1 │ │Actor 2 │ │Actor N │      │               │
│  │  │mailbox │ │mailbox │ │mailbox │      │               │
│  │  │  state │ │  state │ │  state │      │               │
│  │  └────┬───┘ └────┬───┘ └────┬───┘      │               │
│  └───────┼──────────┼──────────┼───────────┘               │
│          └──────────┼──────────┘                           │
│                     ▼                                       │
│  ┌─────────────────────────────────────────┐               │
│  │         Resource Layer                   │               │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────┐ │               │
│  │  │  httpx   │ │ Provider │ │  Qdrant │ │               │
│  │  │   Pool   │ │Semaphores│ │Namespace│ │               │
│  │  └──────────┘ └──────────┘ └─────────┘ │               │
│  └─────────────────────────────────────────┘               │
│                     ▼                                       │
│  ┌─────────────────────────────────────────┐               │
│  │         VETKA FastAPI (:5001)           │               │
│  └─────────────────────────────────────────┘               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Expected Metrics

| Metric | Current | Phase 106 |
|--------|---------|-----------|
| Max Concurrent Agents | 1 | 100+ |
| Subagent Latency | 90s blocking | <5s parallel |
| Throughput | 1 req/s | 50 req/s |
| State Isolation | Shared | Per-session |
| Autonomy | Wait for Claude | Self-loop |

---

## 10. Implementation Plan

### Phase 106a: HTTP Multi-Transport (1-2 hours)
1. Activate `vetka_mcp_server.py --http` mode
2. Add session_id header support
3. Test with multiple Claude instances

### Phase 106b: MCPActor Class (2-3 hours)
1. Create `src/mcp/mcp_actor.py` with mailbox pattern
2. Implement session dispatcher
3. Add asyncio.Queue per actor

### Phase 106c: Client Pool Manager (1-2 hours)
1. Create `src/mcp/client_pool.py`
2. Replace per-request clients in direct_api_calls.py
3. Add connection limits

### Phase 106d: Provider Semaphores (1-2 hours)
1. Add per-model semaphores to provider_registry.py
2. Configure: Grok=10, Haiku=50, Claude=20
3. Implement backpressure signals

### Phase 106e: Socket.IO Integration (1 hour)
1. Create `src/api/handlers/mcp_socket_handler.py`
2. Add `/mcp` namespace
3. Integrate with StreamManager

---

## Appendix: Research Sources

### Haiku Scouts (9 total)
1. MCP stdio bottleneck analysis
2. httpx client pooling patterns
3. Provider registry concurrency
4. Session isolation patterns
5. Backpressure implementations
6. Actor model patterns
7. WebSocket/Socket.IO infrastructure
8. MCPStateBridge usage
9. Workflow tools structure

### Sonnet Verifiers (3 total)
1. MCP transport + httpx pooling → 4 CONFIRMED, 1 NEEDS_UPDATE
2. Concurrency + actor patterns → All CONFIRMED
3. State + Socket.IO → 95% CONFIRMED

### Corrections Applied
- MCP SDK does NOT have native WebSocket (manual implementation required)
- Triple-write is Cache + ChangeLog + Qdrant (not Cache + Qdrant + Qdrant)
- ContextVars used only for logging, not session propagation

---

**Document Version:** 1.0
**Next Step:** Phase 4 - Super-prompt creation for implementation
