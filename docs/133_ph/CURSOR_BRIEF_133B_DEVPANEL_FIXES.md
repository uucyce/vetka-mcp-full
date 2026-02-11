# Phase 133B: DevPanel Fixes + Floating Window — Cursor Brief
**Date:** 2026-02-10
**Priority:** CRITICAL — user losing tokens, settings not persisting
**Effort:** ~60 min total

---

## BUGS FOUND (User-reported + Recon-confirmed)

| Bug | Root Cause | File | Severity |
|-----|-----------|------|----------|
| Heartbeat interval resets to 1min | Backend stores in os.environ only, not disk | debug_routes.py:2491 | CRITICAL |
| Save Positions doesn't persist | No POST /api/layout/positions endpoint | useStore.ts:520, backend missing | HIGH |
| Old tasks stuck as active | No cleanup of stale running/claimed tasks | task_board.py | HIGH |
| ON/OFF buttons counterintuitive | Buttons on left, should be right | DevPanel.tsx:720-752 | MEDIUM |
| Activity panel empty | Events stream but may not connect properly | ActivityLog.tsx | MEDIUM |

---

## C33E: Persist Heartbeat Settings to Disk (15 min) — P0 CRITICAL

**File:** `src/api/routes/debug_routes.py` (line ~2491)

**Problem:** `os.environ["VETKA_HEARTBEAT_INTERVAL"]` only lives in RAM. Server restart = back to 60s. User sets 30min but it resets.

**Fix:**
1. Create config file `data/heartbeat_config.json`:
```json
{
  "enabled": true,
  "interval": 1800,
  "updated_at": "2026-02-10T16:00:00Z"
}
```

2. In `debug_routes.py` POST handler (line ~2491), after setting os.environ, also write to disk:
```python
# MARKER_133.C33E: Persist heartbeat settings
import json
from pathlib import Path

HEARTBEAT_CONFIG = Path("data/heartbeat_config.json")

def save_heartbeat_config(enabled: bool, interval: int):
    config = {"enabled": enabled, "interval": interval, "updated_at": datetime.utcnow().isoformat()}
    HEARTBEAT_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_CONFIG.write_text(json.dumps(config, indent=2))

def load_heartbeat_config() -> dict:
    if HEARTBEAT_CONFIG.exists():
        return json.loads(HEARTBEAT_CONFIG.read_text())
    return {"enabled": True, "interval": 60}
```

3. In GET handler, read from file first:
```python
config = load_heartbeat_config()
interval = config.get("interval", int(os.getenv("VETKA_HEARTBEAT_INTERVAL", "60")))
```

4. In POST handler, save to file:
```python
save_heartbeat_config(enabled=body.get("enabled", True), interval=interval)
```

5. In `main.py` startup, load config on boot:
```python
config = load_heartbeat_config()
os.environ["VETKA_HEARTBEAT_INTERVAL"] = str(config.get("interval", 60))
```

**Test:** Set interval to 30min via DevPanel → restart server → interval should still be 30min.

**MARKER:** `MARKER_133.C33E`

---

## C33F: Stale Task Cleanup (15 min) — P1

**File:** `src/orchestration/task_board.py`

**Problem:** Old tasks stuck in "running" or "claimed" forever. Board shows garbage.

**Fix:**
1. Add method to TaskBoard class:
```python
# MARKER_133.C33F: Auto-cleanup stale tasks
def cleanup_stale(self, running_timeout_min=10, claimed_timeout_min=5):
    """Mark stale running tasks as failed, release stale claimed tasks."""
    now = datetime.utcnow()
    cleaned = 0
    for task in self.tasks:
        if task["status"] == "running":
            started = datetime.fromisoformat(task.get("started_at", now.isoformat()))
            if (now - started).total_seconds() > running_timeout_min * 60:
                task["status"] = "failed"
                task["error"] = f"Timeout: running > {running_timeout_min}min"
                cleaned += 1
        elif task["status"] == "claimed":
            claimed = datetime.fromisoformat(task.get("assigned_at", now.isoformat()))
            if (now - claimed).total_seconds() > claimed_timeout_min * 60:
                task["status"] = "pending"
                task["assigned_to"] = None
                task["assigned_at"] = None
                cleaned += 1
    if cleaned:
        self._save()
    return cleaned
```

2. Call from heartbeat every 10 ticks (in `mycelium_heartbeat.py`):
```python
# After tick processing:
if self.tick_count % 10 == 0:
    cleaned = board.cleanup_stale()
    if cleaned:
        logger.info(f"[Heartbeat] Cleaned {cleaned} stale tasks")
```

3. Add button in DevPanel Board tab to manually trigger cleanup:
```tsx
<button onClick={() => fetch('/api/tasks/cleanup', { method: 'POST' })}>🧹 Cleanup</button>
```

4. Add endpoint:
```python
@router.post("/cleanup")
async def cleanup_stale_tasks():
    cleaned = board.cleanup_stale()
    return {"cleaned": cleaned}
```

**MARKER:** `MARKER_133.C33F`

---

## C33G: DevPanel UX Fixes (10 min) — P1

**File:** `client/src/components/panels/DevPanel.tsx`

**Fixes:**

1. **Move ON/OFF toggles to RIGHT side** (lines 720-752, 804-835):
```tsx
{/* MARKER_133.C33G: Move controls to right */}
<div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
  <span>Heartbeat {heartbeat.enabled ? '●' : '○'}</span>
  <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
    <select value={heartbeat.interval} onChange={...}>...</select>
    <button onClick={...}>ON</button>
    <button onClick={...}>OFF</button>
  </div>
</div>
```

2. **Show task status more clearly** — add colored badges:
- `running` → pulsing yellow dot
- `done` → green check ✓
- `failed` → red X
- `pending` → gray circle

3. **Show "who created" each task** (uses C33D's created_by field):
```tsx
<span className="text-xs text-gray-500">{task.created_by || 'unknown'}</span>
```

**MARKER:** `MARKER_133.C33G`

---

## C33H: Save Positions Backend Endpoint (10 min) — P2

**File:** `src/api/routes/` (new or existing route file)

**Problem:** Frontend tries POST `/api/layout/positions` but endpoint doesn't exist. Silent fail.

**Fix:**
```python
# MARKER_133.C33H: Position persistence endpoint
POSITIONS_FILE = Path("data/layout_positions.json")

@router.post("/api/layout/positions")
async def save_positions(body: Dict[str, Any]):
    POSITIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    POSITIONS_FILE.write_text(json.dumps(body, indent=2))
    return {"success": True}

@router.get("/api/layout/positions")
async def get_positions():
    if POSITIONS_FILE.exists():
        return json.loads(POSITIONS_FILE.read_text())
    return {"positions": {}}
```

**MARKER:** `MARKER_133.C33H`

---

## C34A-D: Floating DevPanel Window (45 min) — P2

See separate brief: `docs/133_ph/CURSOR_BRIEF_134_DEVPANEL_WINDOW.md`

Summary: Add second Tauri window (always-on-top, 420x650px) that renders DevPanel standalone.

---

## Execution Order
```
C33E (heartbeat persist) ← CRITICAL, tokens burning
  ↓
C33F (stale cleanup)     ← HIGH, board is garbage
  ↓
C33G (UX fixes)          ← toggle layout + badges
  ↓
C33H (positions endpoint) ← missing backend
  ↓
C34A-D (floating window)  ← separate Tauri window
```

## DO NOT TOUCH
- Backend pipeline logic (agent_pipeline.py)
- approval_service.py
- eval_agent.py
- docs/ directory

## Files to Edit
1. `src/api/routes/debug_routes.py` (C33E — heartbeat persist)
2. `src/orchestration/task_board.py` (C33F — cleanup)
3. `src/orchestration/mycelium_heartbeat.py` (C33F — auto-trigger)
4. `client/src/components/panels/DevPanel.tsx` (C33G — UX)
5. `src/api/routes/` new or existing (C33H — positions)
6. `data/heartbeat_config.json` (C33E — new file)
7. Tauri files (C34A-D — see separate brief)
