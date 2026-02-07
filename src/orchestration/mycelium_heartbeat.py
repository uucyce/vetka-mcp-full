"""
Mycelium Heartbeat Engine — The Dragon's Heart

Phase 117.2c: Autonomous task execution from group chat messages.

Flow:
    [Heartbeat Tick] → [Read New Messages] → [Parse Tasks] → [Dragon Dispatch] → [Report Back]

The heartbeat monitors the MCP Dev group chat for new task messages
from architects (Claude Code, User). When it finds actionable tasks,
it dispatches Mycelium pipeline to execute them.

Message format for tasks:
    @dragon <task description>
    @pipeline <task description>
    /task <task description>
    /fix <task description>
    /build <task description>

@status: active
@phase: 117.2c
@depends: src/orchestration/agent_pipeline.py, src/api/routes/debug_routes.py
"""

import json
import time
import logging
import re
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict, field

logger = logging.getLogger("VETKA_HEARTBEAT")

# Default group chat for heartbeat monitoring
HEARTBEAT_GROUP_ID = "5e2198c2-8b1a-45df-807f-5c73c5496aa8"

# State file — stores last_message_id and run history
_STATE_FILE = Path(__file__).parent.parent.parent / "data" / "heartbeat_state.json"
_STATE_FILE_FALLBACK = Path(os.environ.get('TMPDIR', '/tmp')) / "vetka_heartbeat_state.json"

# Task trigger patterns
# MARKER_117_3: Added @doctor for diagnostic research
TASK_PATTERNS = [
    re.compile(r"@dragon\s+(.+)", re.IGNORECASE | re.DOTALL),
    re.compile(r"@doctor\s+(.+)", re.IGNORECASE | re.DOTALL),
    re.compile(r"@help\s+(.+)", re.IGNORECASE | re.DOTALL),
    re.compile(r"@pipeline\s+(.+)", re.IGNORECASE | re.DOTALL),
    re.compile(r"/task\s+(.+)", re.IGNORECASE | re.DOTALL),
    re.compile(r"/fix\s+(.+)", re.IGNORECASE | re.DOTALL),
    re.compile(r"/build\s+(.+)", re.IGNORECASE | re.DOTALL),
    re.compile(r"/research\s+(.+)", re.IGNORECASE | re.DOTALL),
]

# Phase type mapping from trigger
PHASE_TYPE_MAP = {
    "dragon": "build",
    "doctor": "research",
    "help": "research",
    "pipeline": "build",
    "task": "build",
    "fix": "fix",
    "build": "build",
    "research": "research",
}


@dataclass
class HeartbeatState:
    """Persistent state for heartbeat engine."""
    last_message_id: Optional[str] = None
    last_tick_time: float = 0.0
    total_ticks: int = 0
    tasks_dispatched: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    recent_runs: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ParsedTask:
    """A task parsed from a chat message."""
    task: str
    phase_type: str
    source_message_id: str
    sender_id: str
    trigger: str  # "dragon", "fix", "build", etc.


def _load_state() -> HeartbeatState:
    """Load heartbeat state from disk."""
    for path in [_STATE_FILE, _STATE_FILE_FALLBACK]:
        if path.exists():
            try:
                data = json.loads(path.read_text())
                return HeartbeatState(**{
                    k: v for k, v in data.items()
                    if k in HeartbeatState.__dataclass_fields__
                })
            except Exception as e:
                logger.warning(f"[Heartbeat] Failed to load state from {path}: {e}")
    return HeartbeatState()


def _save_state(state: HeartbeatState):
    """Save heartbeat state to disk with sandbox fallback."""
    data = json.dumps(asdict(state), indent=2, default=str)
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(data)
    except (PermissionError, OSError):
        try:
            _STATE_FILE_FALLBACK.write_text(data)
            logger.info(f"[Heartbeat] State saved to fallback: {_STATE_FILE_FALLBACK}")
        except Exception as e:
            logger.error(f"[Heartbeat] Failed to save state: {e}")


def _fetch_new_messages(
    group_id: str,
    since_id: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Fetch new messages from group chat via REST API."""
    import httpx

    params = {"limit": limit}
    if since_id:
        params["since_id"] = since_id

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"http://localhost:5001/api/debug/mcp/groups/{group_id}/messages",
                params=params
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("messages", [])
            else:
                logger.warning(f"[Heartbeat] Fetch messages failed: {response.status_code}")
                return []
    except Exception as e:
        logger.error(f"[Heartbeat] Fetch messages error: {e}")
        return []


def _parse_tasks(messages: List[Dict[str, Any]]) -> List[ParsedTask]:
    """Parse task triggers from chat messages."""
    tasks = []

    for msg in messages:
        content = msg.get("content", "")
        sender_id = msg.get("sender_id", "")
        message_id = msg.get("id", "")

        # Skip messages from pipeline itself (avoid loops)
        if sender_id in ("@Mycelium Pipeline", "@pipeline", "pipeline"):
            continue

        # Skip system messages that are pipeline progress
        if msg.get("message_type") == "system" and "@pipeline:" in content:
            continue

        # Try each pattern
        for pattern in TASK_PATTERNS:
            match = pattern.search(content)
            if match:
                task_text = match.group(1).strip()
                # Determine trigger type from pattern
                trigger_word = pattern.pattern.split(r"\s+")[0].replace("@", "").replace("/", "").lower()
                # Clean up regex artifacts
                trigger_word = re.sub(r'[^a-z]', '', trigger_word)

                phase_type = PHASE_TYPE_MAP.get(trigger_word, "build")

                tasks.append(ParsedTask(
                    task=task_text,
                    phase_type=phase_type,
                    source_message_id=message_id,
                    sender_id=sender_id,
                    trigger=trigger_word
                ))
                break  # One task per message

    return tasks


def _emit_heartbeat_status(group_id: str, message: str):
    """Send heartbeat status message to group chat."""
    import httpx

    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(
                f"http://localhost:5001/api/debug/mcp/groups/{group_id}/send",
                json={
                    "agent_id": "pipeline",
                    "content": message,
                    "message_type": "system"
                }
            )
    except Exception as e:
        logger.warning(f"[Heartbeat] Emit status failed: {e}")


async def _dispatch_task(task: ParsedTask, group_id: str) -> Dict[str, Any]:
    """Dispatch a parsed task to Mycelium pipeline."""
    from src.orchestration.agent_pipeline import AgentPipeline

    logger.info(f"[Heartbeat] Dispatching: {task.task[:60]}... (phase={task.phase_type})")

    _emit_heartbeat_status(
        group_id,
        f"@pipeline: \u2764\ufe0f Heartbeat detected task from {task.sender_id}:\n"
        f"Trigger: `{task.trigger}` | Phase: `{task.phase_type}`\n"
        f"Task: {task.task[:200]}"
    )

    pipeline = AgentPipeline(chat_id=group_id)

    try:
        result = await pipeline.execute(task.task, task.phase_type)
        return {
            "success": True,
            "task_id": result.get("task_id", "unknown"),
            "status": result.get("status", "unknown"),
            "completed": result.get("results", {}).get("subtasks_completed", 0),
            "total": result.get("results", {}).get("subtasks_total", 0)
        }
    except Exception as e:
        logger.error(f"[Heartbeat] Pipeline failed: {e}")
        return {"success": False, "error": str(e)}


async def heartbeat_tick(
    group_id: str = HEARTBEAT_GROUP_ID,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Execute one heartbeat tick.

    1. Load state (last_message_id)
    2. Fetch new messages since last tick
    3. Parse tasks from messages
    4. Dispatch tasks to pipeline (unless dry_run)
    5. Update state
    6. Report back to chat

    Args:
        group_id: Group chat to monitor
        dry_run: If True, parse but don't execute tasks

    Returns:
        Tick result with new messages count, tasks found, tasks dispatched
    """
    tick_start = time.time()
    state = _load_state()

    logger.info(f"[Heartbeat] Tick #{state.total_ticks + 1} "
                f"(last_msg: {state.last_message_id or 'none'})")

    # 1. Fetch new messages
    messages = _fetch_new_messages(group_id, since_id=state.last_message_id)
    new_count = len(messages)

    if new_count == 0:
        logger.info("[Heartbeat] No new messages, sleeping...")
        state.total_ticks += 1
        state.last_tick_time = tick_start
        _save_state(state)
        return {
            "tick": state.total_ticks,
            "new_messages": 0,
            "tasks_found": 0,
            "tasks_dispatched": 0,
            "dry_run": dry_run
        }

    logger.info(f"[Heartbeat] Found {new_count} new messages")

    # 2. Update last_message_id to latest
    if messages:
        state.last_message_id = messages[-1].get("id", state.last_message_id)

    # 3. Parse tasks
    tasks = _parse_tasks(messages)
    logger.info(f"[Heartbeat] Parsed {len(tasks)} tasks from {new_count} messages")

    # 4. Dispatch tasks
    results = []
    if tasks and not dry_run:
        _emit_heartbeat_status(
            group_id,
            f"@pipeline: \u2764\ufe0f\u200d\ud83d\udd25 Heartbeat tick #{state.total_ticks + 1}: "
            f"{new_count} new messages, {len(tasks)} tasks detected!"
        )

        for task in tasks:
            result = await _dispatch_task(task, group_id)
            results.append({
                "task": task.task[:100],
                "phase_type": task.phase_type,
                "trigger": task.trigger,
                "sender": task.sender_id,
                **result
            })

            if result.get("success"):
                state.tasks_completed += 1
            else:
                state.tasks_failed += 1

            state.tasks_dispatched += 1

    elif tasks and dry_run:
        _emit_heartbeat_status(
            group_id,
            f"@pipeline: \ud83d\udc40 Heartbeat DRY RUN: {len(tasks)} tasks found but NOT executed\n"
            + "\n".join([f"  - [{t.trigger}] {t.task[:80]}" for t in tasks])
        )
        results = [{"task": t.task[:100], "phase_type": t.phase_type, "dry_run": True} for t in tasks]

    # 5. Update state
    state.total_ticks += 1
    state.last_tick_time = tick_start

    # Keep last 20 runs
    run_record = {
        "tick": state.total_ticks,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "new_messages": new_count,
        "tasks_found": len(tasks),
        "tasks_dispatched": len(results),
        "dry_run": dry_run
    }
    state.recent_runs.append(run_record)
    state.recent_runs = state.recent_runs[-20:]

    _save_state(state)

    tick_result = {
        "tick": state.total_ticks,
        "new_messages": new_count,
        "tasks_found": len(tasks),
        "tasks_dispatched": len(results),
        "results": results,
        "dry_run": dry_run,
        "duration_ms": int((time.time() - tick_start) * 1000)
    }

    logger.info(f"[Heartbeat] Tick complete: {json.dumps(tick_result, default=str)[:200]}")
    return tick_result


def get_heartbeat_status() -> Dict[str, Any]:
    """Get current heartbeat state (for MCP tool)."""
    state = _load_state()
    return {
        "last_message_id": state.last_message_id,
        "last_tick_time": state.last_tick_time,
        "total_ticks": state.total_ticks,
        "tasks_dispatched": state.tasks_dispatched,
        "tasks_completed": state.tasks_completed,
        "tasks_failed": state.tasks_failed,
        "recent_runs": state.recent_runs[-5:]
    }
