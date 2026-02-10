# MARKER_133.C33E: Heartbeat health and config persistence
"""
Heartbeat health endpoint + config persistence to disk.
Solves: interval resets to 60s on restart (was only in os.environ).
"""
import json
import time
import os
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, Body

router = APIRouter(prefix="/api/heartbeat", tags=["heartbeat"])

CONFIG_FILE = Path("data/heartbeat_config.json")
STATE_FILE = Path("data/heartbeat_state.json")
START_TIME = time.time()


def load_config() -> dict:
    """Load heartbeat config from disk. Falls back to env vars then defaults."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    # Fallback to env vars
    return {
        "enabled": os.getenv("VETKA_HEARTBEAT_ENABLED", "false").lower() == "true",
        "interval": int(os.getenv("VETKA_HEARTBEAT_INTERVAL", "1800")),
        "updated_at": None
    }


def save_config(config: dict):
    """Persist heartbeat config to disk."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    config["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
    # Also sync to env vars for backward compat
    os.environ["VETKA_HEARTBEAT_ENABLED"] = str(config.get("enabled", False)).lower()
    os.environ["VETKA_HEARTBEAT_INTERVAL"] = str(config.get("interval", 1800))


def load_state() -> dict:
    """Load heartbeat runtime state."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


@router.get("/health")
async def heartbeat_health():
    """Health check — is heartbeat alive and ticking?"""
    config = load_config()
    state = load_state()
    last_tick = state.get("last_tick_time", 0)
    interval = config.get("interval", 1800)
    # "alive" if last tick was within 5x interval
    is_alive = (time.time() - last_tick) < interval * 5 if last_tick else False
    return {
        "status": "alive" if is_alive else "dead",
        "enabled": config.get("enabled", False),
        "interval": interval,
        "interval_human": f"{interval // 60}m" if interval >= 60 else f"{interval}s",
        "last_tick": last_tick,
        "last_tick_human": time.strftime("%H:%M:%S", time.localtime(last_tick)) if last_tick else "never",
        "total_ticks": state.get("total_ticks", 0),
        "tasks_dispatched": state.get("tasks_dispatched", 0),
        "tasks_completed": state.get("tasks_completed", 0),
        "tasks_failed": state.get("tasks_failed", 0),
        "uptime_seconds": round(time.time() - START_TIME, 1)
    }


@router.post("/config")
async def update_heartbeat_config(body: Dict[str, Any] = Body(...)):
    """Update heartbeat config and persist to disk."""
    config = load_config()
    if "enabled" in body:
        config["enabled"] = bool(body["enabled"])
    if "interval" in body:
        # Clamp: 30 seconds to 1 week
        config["interval"] = max(30, min(int(body["interval"]), 604800))
    save_config(config)
    return {"success": True, "config": config}


@router.get("/config")
async def get_heartbeat_config():
    """Get current heartbeat config (from disk)."""
    return {"success": True, "config": load_config()}


@router.post("/cleanup")
async def cleanup_stale_tasks():
    """Cleanup stale running/claimed tasks in TaskBoard."""
    from src.orchestration.task_board import TaskBoard
    board = TaskBoard()
    cleaned = board.cleanup_stale()
    return {"success": True, "cleaned": cleaned}


@router.get("/board/summary")
async def board_summary():
    """Quick TaskBoard status — pending, running, done counts."""
    from src.orchestration.task_board import TaskBoard
    board = TaskBoard()
    summary = board.get_summary()
    return {"success": True, **summary}
