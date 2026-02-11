# Cursor Brief: Phase 131 — Mycelium Autonomy Infrastructure

**Priority:** HIGH — Foundation for Dragon autonomy
**Dependencies:** Phase 130.6 (pipeline safety) ✅ DONE

## Overview

You are building the infrastructure that lets Dragon wake up by itself, heal bugs, and let ANY client (Cursor, Opencode, VSCode) submit tasks.

Read the full recon report: `docs/131_ph/RECON_REPORT_131_MYCELIUM_AUTONOMY.md`

---

## Tasks (ordered by priority)

### C20A: Heartbeat Background Daemon (CRITICAL, 2h)
**Marker:** MARKER_C20A

**Problem:** Heartbeat only runs when MCP tool is manually called. Dragon sleeps.

**Solution:** Create background asyncio task that polls heartbeat every 60 seconds.

**Files to create/modify:**
- `src/orchestration/heartbeat_daemon.py` (NEW — ~50 lines)
- `main.py` (ADD startup event to launch daemon)

**Implementation:**
```python
# src/orchestration/heartbeat_daemon.py
# MARKER_C20A: Background heartbeat daemon for autonomous task detection

import asyncio
import logging
from typing import Optional

logger = logging.getLogger("VETKA.heartbeat_daemon")

_daemon_task: Optional[asyncio.Task] = None
_daemon_running = False

HEARTBEAT_GROUP_ID = "5e2198c2-8b1a-45df-807f-5c73c5496aa8"
DEFAULT_INTERVAL = 60  # seconds

async def _heartbeat_loop(interval: int = DEFAULT_INTERVAL):
    """Continuous heartbeat polling loop."""
    global _daemon_running
    _daemon_running = True

    from src.orchestration.mycelium_heartbeat import heartbeat_tick

    logger.info(f"[Daemon] Heartbeat daemon started (interval={interval}s)")

    while _daemon_running:
        try:
            result = await heartbeat_tick(
                group_id=HEARTBEAT_GROUP_ID,
                dry_run=False
            )
            tasks_found = result.get("tasks_found", 0)
            if tasks_found > 0:
                logger.info(f"[Daemon] Found {tasks_found} tasks, dispatched")
        except Exception as e:
            logger.warning(f"[Daemon] Tick failed (will retry): {e}")

        await asyncio.sleep(interval)

async def start_daemon(interval: int = DEFAULT_INTERVAL):
    """Start daemon as background task."""
    global _daemon_task
    if _daemon_task and not _daemon_task.done():
        logger.warning("[Daemon] Already running")
        return
    _daemon_task = asyncio.create_task(_heartbeat_loop(interval))
    logger.info("[Daemon] Background task created")

async def stop_daemon():
    """Stop daemon gracefully."""
    global _daemon_running, _daemon_task
    _daemon_running = False
    if _daemon_task:
        _daemon_task.cancel()
        _daemon_task = None
    logger.info("[Daemon] Stopped")

def get_daemon_status() -> dict:
    """Get daemon status for health check."""
    return {
        "running": _daemon_running,
        "task_alive": _daemon_task is not None and not _daemon_task.done() if _daemon_task else False,
        "interval": DEFAULT_INTERVAL,
        "group_id": HEARTBEAT_GROUP_ID
    }
```

**In main.py — add startup event:**
```python
# MARKER_C20A: Auto-start heartbeat daemon
@app.on_event("startup")
async def start_heartbeat():
    from src.orchestration.heartbeat_daemon import start_daemon
    await start_daemon()
```

**Test:** After server restart, send `@dragon echo hello` to group chat → should auto-dispatch within 60s.

---

### C20B: Heartbeat Auto-Resume (MEDIUM, 30min)
**Marker:** MARKER_C20B

**Problem:** After server restart, heartbeat loses context.

**Solution:** Load persisted state on startup, run catch-up tick immediately.

**Modify:** `src/orchestration/heartbeat_daemon.py` → in `_heartbeat_loop`, first iteration runs immediately (no sleep).

Already handled by C20A design (first tick runs without delay).

---

### C20C: Universal Task API (HIGH, 3h)
**Marker:** MARKER_C20C

**Problem:** Task endpoints live in `/api/debug/task-board/*` — not suitable for production clients.

**Solution:** Create proper `/api/tasks/*` namespace with agent identity.

**Files to create/modify:**
- `src/api/routes/task_routes.py` (NEW — ~200 lines)
- `src/api/routes/__init__.py` (ADD router)
- `main.py` (REGISTER router)

**Endpoints:**

```
GET    /api/tasks                    # List tasks (filter by status, agent)
GET    /api/tasks/{task_id}          # Get task details
POST   /api/tasks                    # Create task
POST   /api/tasks/{task_id}/claim    # Claim task (X-Agent-ID header)
POST   /api/tasks/{task_id}/complete # Complete task with results
POST   /api/tasks/{task_id}/cancel   # Cancel task
GET    /api/tasks/agents             # Active agents
GET    /api/tasks/next               # Get next task for agent to claim
```

**Agent Identity:** All endpoints require `X-Agent-ID` header:
- `cursor` — Cursor IDE
- `opencode` — Opencode CLI
- `dragon` — Mycelium pipeline
- `opus` — Claude Opus
- `mistral` — Mistral in Opencode
- `human` — Manual task

**Key: Claim Locking:**
```python
# MARKER_C20C: Optimistic locking for task claims
async def claim_task(task_id: str, agent_id: str):
    task = board.get_task(task_id)
    if task["status"] != "pending":
        raise HTTPException(409, "Task already claimed")
    # Atomic claim
    board.claim_task(task_id, agent_name=agent_id, agent_type=agent_id)
```

**Response Format (for all clients):**
```json
{
  "task_id": "tb_1770577538_1",
  "title": "Fix button styling",
  "description": "...",
  "status": "pending",
  "priority": 2,
  "phase_type": "fix",
  "assigned_to": null,
  "created_at": "2026-02-10T12:00:00",
  "files_hint": ["src/components/Button.tsx"]
}
```

---

### C20D: Cursor Task Workflow Integration (MEDIUM, 2h)
**Marker:** MARKER_C20D

**Problem:** Cursor has no standard way to check tasks, claim, and report done.

**Solution:** Add MCP tool or REST client that Cursor uses at session start.

**Cursor should:**
1. On session start → `GET /api/tasks?status=pending&assigned_to=cursor`
2. Pick highest priority → `POST /api/tasks/{id}/claim` with `X-Agent-ID: cursor`
3. Work on task
4. `POST /api/tasks/{id}/complete` with commit hash

**Integration point:** Add to Cursor's `.cursorrules` or MCP config.

---

### C20E: Camera Fly-To on Approve (MEDIUM, 2h)
**Marker:** MARKER_C20E

**Problem:** Camera system works but doesn't trigger on artifact approval.

**Solution:** In approval_service.py, after approve → emit Socket.IO event that CameraController listens for.

**Modify:**
- `src/services/approval_service.py` — add camera_focus emit after approve
- `client/src/components/canvas/CameraController.tsx` — listen for approval event

---

## Testing Checklist

- [ ] C20A: Server restart → heartbeat auto-starts within 60s
- [ ] C20A: `@dragon echo test` in group chat → pipeline dispatches within 60s
- [ ] C20C: `curl /api/tasks` returns task list
- [ ] C20C: Two agents can't claim same task (409 conflict)
- [ ] C20D: Cursor session reads pending tasks on start
- [ ] C20E: Approve artifact → camera flies to file

## Files Index

| File | Status | Marker |
|------|--------|--------|
| src/orchestration/heartbeat_daemon.py | NEW | MARKER_C20A |
| src/api/routes/task_routes.py | NEW | MARKER_C20C |
| main.py | MODIFY | MARKER_C20A, C20C |
| src/api/routes/__init__.py | MODIFY | MARKER_C20C |
| src/services/approval_service.py | MODIFY | MARKER_C20E |
| client/src/components/canvas/CameraController.tsx | MODIFY | MARKER_C20E |
