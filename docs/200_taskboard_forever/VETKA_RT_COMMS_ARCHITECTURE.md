# VETKA Task Board: Real-Time Multi-Agent Communication
## Architecture Document (Research + Implementation Design)

**Date:** March 28, 2026
**Authors:** Grok-4.1-fast (research, 50+ sources), Zeta (architecture corrections)
**Status:** Approved direction — ready for implementation
**Phase:** 201+
**Supersedes:** VETKA_RT_Comms_Unified_Research.md (deleted — contained SQLite trigger myth)

---

## Design Principle: ZERO INTERVALS

No heartbeat polling. No `sleep()` loops. No timer-based checks.
Every notification is triggered by an **event** — a task write, an agent action,
or an explicit notify call. If nothing happens, 0 CPU is consumed.

---

## 1. Executive Summary

### The Problem
5–50+ local AI agents (Claude Code, Codex, Ollama) share a SQLite task board.
Current approach: agents see notifications only on `session_init` — i.e. next session start.
Commander sends a directive, agent doesn't see it until human restarts the session.

### The Solution: Event Bus + UDS Pub-Sub + Piggyback Delivery

```
TaskBoard write
    → Python Event Bus emit(AgentEvent)     ← trigger point (not SQLite, not timer)
        → UDS Daemon fan-out to MCP servers ← push to idle agents (0 CPU)
        → Piggyback in task_board response  ← instant for active agents (0 overhead)
        → Audit log table                   ← observability
```

Three delivery paths, one trigger, zero intervals.

---

## 2. Research Findings (Grok-4.1-fast, 50+ sources)

### Framework Landscape

| Framework | Push Model | Wake-Up | Scale | VETKA Fit |
|-----------|-----------|---------|-------|-----------|
| **OpenHands** | SSE/WebSocket | Poll `/api/events` | ~50 agents | Over-engineered for local |
| **CrewAI** | asyncio.Queue | Sequential delegation | ~50 agents | Sequential bottleneck |
| **AutoGen** | Direct A2A push | `register_reply()` | ~50 agents | Best push, but conversational |
| **LangGraph** | Callbacks | Manual/cron trigger | ~100 agents | Good SQLite fit, needs trigger |

**Key insight:** No framework solves "wake idle agent" without either polling or
external trigger. All eventually fall back to some form of event source + listener.

### Transport Comparison

| Transport | Type | CPU Idle | 10 agents | 100 agents | Interval? | Verdict |
|-----------|------|----------|-----------|------------|-----------|---------|
| Pull polling | Pull | Wastes CPU | OK | Lock contention | **YES** | Rejected |
| inotify/fswatch | File-watch | 0 | OK | FD limits | Hidden | Fallback only |
| Named pipes | Push (uni) | 0 | OK | 1 pipe/agent | No | Doesn't scale |
| **UDS Pub-Sub** | **Push (bi)** | **0** | **Trivial** | **epoll OK** | **No** | **Primary** |
| SSE/WebSocket | Push (HTTP) | Medium | OK | Conn limits | No | MCC UI only |

**Winner: Unix Domain Sockets (UDS)**
- Zero-copy IPC, single socket for N connections
- Bidirectional (agent can ack/respond)
- `recv()` blocks with 0 CPU — kernel manages wake-up
- epoll (Linux) / kqueue (macOS) scales to 1000+ connections

### Scale-Out Path

| Scale | Approach | Status |
|-------|----------|--------|
| 10 agents | UDS daemon (single) | Trivial |
| 50 agents | UDS + asyncio | Stable |
| 100 agents | UDS + async pool | Memory-bound (~1GB) |
| 500+ agents | Multi-machine | Redis pub-sub federation |

### Claude Code Integration Reality

Claude Code agents are subprocesses (stdin/stdout JSON-RPC). They **cannot**:
- Listen on sockets
- Watch files with inotify
- Handle Unix signals
- Run background threads

**Who CAN listen:** The **MCP server process** (`vetka_mcp_bridge.py`).
It's a long-lived Python process with full asyncio control.
This is the relay point for all push notifications.

### MCP Transport

MCP is primarily request-response (JSON-RPC). No native server-push to client.
Solution: MCP server maintains a UDS side-channel for receiving push events,
then delivers via piggyback in the next MCP response.

### References
- OpenHands: https://github.com/All-Hands-AI/OpenHands
- CrewAI: https://docs.crewai.com/
- AutoGen: https://microsoft.github.io/autogen/
- LangGraph: https://langchain-ai.github.io/langgraph/
- MCP Spec: https://modelcontextprotocol.io/

---

## 3. Architecture

### 3.1 Event Bus (Python-level trigger)

The Event Bus replaces `_notify_board_update()` as the single trigger point.
Every state change in TaskBoard emits an `AgentEvent`. Subscribers decide what to do.

```python
@dataclass
class AgentEvent:
    event_id: str           # unique, monotonic (uuid4 or counter)
    event_type: str         # "task_created", "task_claimed", "notification", ...
    source_agent: str       # "Alpha", "Commander", "system"
    source_tool: str        # "claude_code", "local_ollama", "system"
    timestamp: str          # ISO 8601
    payload: Dict[str, Any] # type-specific data
    tags: List[str]         # routing hints: ["persist", "notify_commander"]

class EventSubscriber:
    def accepts(self, event: AgentEvent) -> bool: ...
    def handle(self, event: AgentEvent) -> None: ...

class EventBus:
    def __init__(self):
        self._subscribers: List[EventSubscriber] = []

    def subscribe(self, sub: EventSubscriber):
        self._subscribers.append(sub)

    def emit(self, event: AgentEvent):
        """Synchronous fan-out. <1ms overhead."""
        for sub in self._subscribers:
            try:
                if sub.accepts(event):
                    sub.handle(event)
            except Exception:
                pass  # subscriber failure MUST NOT block emitter
```

### 3.2 Built-in Subscribers

| Subscriber | Accepts | Action |
|-----------|---------|--------|
| `TaskBoardSubscriber` | task_* events | `_append_history()`, audit |
| `NotificationSubscriber` | events tagged "notify_*" | Write to notifications table |
| `AuditSubscriber` | all events | Append to `event_log` table |
| `UDSPublisher` | all events | Push to UDS daemon for fan-out |
| `MCCSubscriber` (future) | all events | WebSocket push to MCC UI |

### 3.3 Three Delivery Paths

#### Path A: Piggyback (active agents, 0 overhead)
Agent calls `task_board action=list/get/claim/complete` →
TaskBoard checks pending notifications for this role →
Injects into response: `{"notifications": [...], ...normal_response...}`

**Cost:** One SQL SELECT per task_board call. <0.1ms on SQLite.
**Latency:** Instant — agent sees messages on next task_board interaction.

#### Path B: UDS Push (idle agents, 0 CPU)
Event Bus `emit()` → `UDSPublisher` → UDS Daemon → fan-out to MCP servers →
MCP server stores pending → delivers on next MCP call from agent.

**Cost:** 0 CPU when idle. Kernel wakes process on event.
**Latency:** <10ms from emit to MCP server receipt.

#### Path C: REST (external agents — Ollama, Codex)
External agent polls: `GET /api/taskboard/notifications?role=qwen-7b`
OR registers a webhook callback URL at claim time.

**Cost:** One HTTP request per check.
**Latency:** Depends on agent's work cycle. For Ollama orchestrator using
`/loop 5m`, messages arrive within the work cycle interval.

### 3.4 Complete Flow Diagram

```
┌───────────────────────────────────────────────────────┐
│         TaskBoard Python Code                         │
│                                                       │
│  def complete_task(self, task_id, ...):               │
│      self._save_task(task)                            │
│      self.event_bus.emit(AgentEvent(                  │
│          type="task_completed",                       │
│          source_agent="Alpha",                        │
│          payload={task_id, commit_hash, q1, q2, q3},  │
│          tags=["persist", "notify_commander"]         │
│      ))                                               │
└──────────────────────┬────────────────────────────────┘
                       │ emit()
                       ▼
          ┌──────────────────────────┐
          │       Event Bus          │
          │   (in-process, sync)     │
          │                          │
          │  ┌─ TaskBoardSub ────── _append_history()
          │  ├─ NotificationSub ─── SQLite notifications table
          │  ├─ AuditSub ────────── event_log table (append-only)
          │  └─ UDSPublisher ────── push to daemon ──┐
          └──────────────────────────┘                │
                                                      │
                    ┌─────────────────────────────────┘
                    ▼
   ┌────────────────────────────────┐
   │  UDS Daemon (/tmp/vetka.uds)  │
   │  asyncio event loop            │
   │  0 CPU when no events          │
   │                                │
   │  Connected MCP servers:        │
   │  ├─ Alpha (claude/cut-engine)  │
   │  ├─ Beta  (claude/cut-media)   │
   │  ├─ Gamma (claude/cut-ux)      │
   │  └─ ...                        │
   └──┬─────────┬─────────┬────────┘
      │         │         │
      ▼         ▼         ▼
   MCP srv   MCP srv   MCP srv
   stores    stores    stores
   pending   pending   pending
      │         │         │
   Agent      Agent     Agent
   calls      calls     calls
   task_board task_board task_board
      │         │         │
   piggyback piggyback piggyback
   delivery  delivery  delivery
```

**One event → five outcomes:**
1. TaskBoardSubscriber → status_history updated
2. NotificationSubscriber → Commander inbox entry
3. AuditSubscriber → event_log row (queryable)
4. UDSPublisher → push to all MCP servers
5. (future) MCCSubscriber → WebSocket to UI

---

## 4. Why NOT SQLite Triggers

Grok's original research proposed:
```sql
CREATE TRIGGER task_notify AFTER INSERT ON tasks
BEGIN
    SELECT notify_daemon(NEW.id);  -- ← DOES NOT WORK
END;
```

**This is impossible without a custom C extension.** SQLite triggers can only
execute SQL statements. They cannot call external functions, write to sockets,
or signal other processes. `sqlite3_create_function()` requires compiling a
shared library — fragile, non-portable, and unnecessary.

**The correct trigger is Python-level:** `self.event_bus.emit()` inside
`_save_task()`, `claim_task()`, `complete_task()`, etc. We already have
`_notify_board_update()` at these exact call sites — it becomes the emit point.

---

## 5. Migration Path (incremental, each phase standalone useful)

### Phase 1: Piggyback + Event Bus skeleton
- Formalize `AgentEvent` dataclass
- Create `EventBus` class with subscriber registry
- Wire `_notify_board_update()` → `emit()`
- Piggyback notifications in every `task_board` MCP response
- Subscribers = `AuditSubscriber` (event_log table)
- **Result:** Active agents see inbox instantly. Audit trail works.

### Phase 2: UDS Daemon
- Create `UDSPublisher` subscriber
- Create standalone `uds_daemon.py` process
- MCP servers connect on startup
- **Result:** Idle agents get push notifications via MCP relay.

### Phase 3: Memory + Debrief routing
- `MemorySubscriber` → routes Q1-Q3 debrief to CORTEX
- `EngramSubscriber` → routes bugs to ENGRAM L1 danger cache
- **Result:** One event, automatic memory + experience capture.

### Phase 4: MCC + External
- `MCCSubscriber` → WebSocket push to MCC UI
- REST webhook for external agents
- **Result:** Full observability in browser, Codex/Ollama integration.

---

## 6. Constraints (from TaskBoard Bible)

- Event emission MUST NOT block the write path (<1ms overhead)
- Subscriber failures MUST NOT propagate to emitter (try/except, fire-and-forget)
- SQLite remains authoritative store — Event Bus is routing layer, not storage
- No bulk writes in `__init__` (Bible Section 12.1)
- Subscribers run synchronously in same process (no distributed bus needed)
- UDS Daemon is a separate process (communicates via socket, not shared memory)

---

## 7. Implementation Code

### 7.1 Event Bus + AgentEvent

See Section 3.1 above. Lives in `src/orchestration/event_bus.py`.

### 7.2 UDS Daemon (event-driven, zero intervals)

```python
import asyncio, json, struct, os

class UDSDaemon:
    """Single daemon process. N agent connections. 0 CPU when idle."""
    def __init__(self, path="/tmp/vetka-events.uds"):
        self.path = path
        self.agents: dict[str, asyncio.StreamWriter] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()

    async def run(self):
        if os.path.exists(self.path):
            os.unlink(self.path)
        agent_srv = await asyncio.start_unix_server(
            self._handle_agent_connect, self.path
        )
        asyncio.create_task(self._fanout_loop())
        async with agent_srv:
            await agent_srv.serve_forever()

    async def _handle_agent_connect(self, reader, writer):
        """MCP server connects, sends {"role": "Alpha"}. Stays connected."""
        data = await reader.read(1024)
        reg = json.loads(data)
        role = reg["role"]
        self.agents[role] = writer
        # Connection stays open. Writer blocks on recv(). 0 CPU.
        try:
            while True:
                check = await reader.read(1)  # detect disconnect
                if not check:
                    break
        except Exception:
            pass
        finally:
            self.agents.pop(role, None)

    async def _fanout_loop(self):
        """Blocks on queue.get() — wakes ONLY when event arrives. No interval."""
        while True:
            event = await self._event_queue.get()  # ← blocking, 0 CPU
            msg = json.dumps(event).encode()
            frame = struct.pack('>I', len(msg)) + msg
            dead = []
            for role, writer in self.agents.items():
                try:
                    writer.write(frame)
                    await writer.drain()
                except Exception:
                    dead.append(role)
            for r in dead:
                self.agents.pop(r, None)

    async def push_event(self, event: dict):
        """Called by Event Bus UDSPublisher (via local socket or direct)."""
        await self._event_queue.put(event)

if __name__ == "__main__":
    daemon = UDSDaemon()
    asyncio.run(daemon.run())
```

### 7.3 MCP Server Notification Receiver

```python
import asyncio, json, struct

class MCPNotificationReceiver:
    """Runs inside MCP server process. Connects to UDS daemon."""
    def __init__(self, role: str, daemon_path="/tmp/vetka-events.uds"):
        self.role = role
        self._daemon_path = daemon_path
        self.pending: list[dict] = []

    async def connect_and_listen(self):
        """Connect to daemon, register role, listen for events forever."""
        reader, writer = await asyncio.open_unix_connection(self._daemon_path)
        writer.write(json.dumps({"role": self.role}).encode())
        await writer.drain()
        while True:
            header = await reader.readexactly(4)
            length = struct.unpack('>I', header)[0]
            data = await reader.readexactly(length)
            event = json.loads(data)
            self.pending.append(event)

    def drain_pending(self) -> list[dict]:
        """Called during any task_board MCP response — piggyback delivery."""
        result = self.pending[:]
        self.pending.clear()
        return result
```

### 7.4 Append-Only Event Log Table

```sql
CREATE TABLE IF NOT EXISTS event_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    source_agent TEXT,
    source_tool TEXT,
    timestamp TEXT NOT NULL,
    payload JSON,
    tags JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_event_log_type ON event_log(event_type);
CREATE INDEX IF NOT EXISTS idx_event_log_ts ON event_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_event_log_agent ON event_log(source_agent);
```

---

## 8. Gotchas & Pitfalls

### From Research (Grok-4.1-fast)
1. Don't use Redis before 100 agents — UDS is simpler
2. Don't embed LLM context in SQLite — use JSON column + async loading
3. Don't use Kafka/RabbitMQ locally — over-engineered
4. Do use append-only event table — replayable, auditable
5. Do measure p99 latency, not just p50

### From Implementation (Zeta)
1. SQLite triggers CANNOT call external functions — use Python emit
2. Claude Code agents CANNOT listen on sockets — MCP server is the relay
3. `_notify_board_update()` already exists at all trigger points — reuse it
4. UDS daemon must handle agent reconnection gracefully (MCP server restart)
5. Event Bus emit must be <1ms — no network I/O in subscribers (UDSPublisher uses async queue)

### Anti-Patterns to Avoid
- `while True: sleep(N); check_inbox()` — interval polling, wastes CPU, doesn't scale
- `postToolUse` hook checking inbox — fires on EVERY tool call, polling in disguise
- `heartbeat_tick` inbox check — interval-based, same problem
- SQLite trigger + inotify — fragile chain, hidden polling

---

## 9. Decision Tree

```
START: Agent needs to receive a notification

├─ Agent is ACTIVE (currently calling task_board)?
│  └─ Piggyback in response (0 overhead, instant)
│
├─ Agent is IDLE (session open, not calling tools)?
│  └─ UDS push → MCP server → stored → piggyback on next call
│
├─ Agent is SLEEPING (no active session)?
│  └─ Notification stored in SQLite
│  └─ Delivered on next session_init
│  └─ (Future: UDS daemon could wake agent via /loop or process signal)
│
└─ Agent is EXTERNAL (Ollama/Codex, no MCP)?
   └─ REST GET /api/taskboard/notifications (part of work cycle)
   └─ OR webhook callback (registered at claim time)
```

---

**Document Version:** 2.0
**Last Updated:** March 28, 2026
**Changelog:**
- v2.0: Zeta corrections — removed SQLite trigger myth, removed all interval patterns,
  added Event Bus as Python-level trigger, clarified MCP server as relay point,
  added piggyback as primary delivery for active agents
- v1.0: Grok-4.1-fast original research (deleted — contained architectural inaccuracies)
