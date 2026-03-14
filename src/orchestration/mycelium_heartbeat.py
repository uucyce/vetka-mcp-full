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
_CONFIG_FILE = Path(__file__).parent.parent.parent / "data" / "heartbeat_config.json"

# Task trigger patterns
# MARKER_117_3: Added @doctor for diagnostic research
TASK_PATTERNS = [
    re.compile(r"@dragon\s+(.+)", re.IGNORECASE | re.DOTALL),
    re.compile(r"@titan\s+(.+)", re.IGNORECASE | re.DOTALL),  # MARKER_118.10_TITAN
    re.compile(r"@doctor\s+(.+)", re.IGNORECASE | re.DOTALL),
    re.compile(r"@help\s+(.+)", re.IGNORECASE | re.DOTALL),
    re.compile(r"@mycelium\s+(.+)", re.IGNORECASE | re.DOTALL),
    re.compile(r"@pipeline\s+(.+)", re.IGNORECASE | re.DOTALL),  # alias for @mycelium
    re.compile(r"/task\s+(.+)", re.IGNORECASE | re.DOTALL),
    re.compile(r"/fix\s+(.+)", re.IGNORECASE | re.DOTALL),
    re.compile(r"/build\s+(.+)", re.IGNORECASE | re.DOTALL),
    re.compile(r"/research\s+(.+)", re.IGNORECASE | re.DOTALL),
    re.compile(r"@board\s+(.+)", re.IGNORECASE | re.DOTALL),  # MARKER_121_BOARD
]

# Phase type mapping from trigger
PHASE_TYPE_MAP = {
    "dragon": "build",
    "titan": "build",  # MARKER_118.10_TITAN
    "doctor": "research",
    "help": "research",
    "mycelium": "build",
    "pipeline": "build",  # alias for mycelium
    "task": "build",
    "fix": "fix",
    "build": "build",
    "research": "research",
    "board": "board",  # MARKER_121_BOARD: Special — handled by TaskBoard
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
    source_chat_id: str = ""  # MARKER_140: which chat this task came from
    source_chat_type: str = "group"  # "group" or "solo"


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


def _default_heartbeat_config() -> Dict[str, Any]:
    return {
        "enabled": False,
        "interval": 60,
        "monitor_all": True,
        "profile_mode": "global",
        "project_id": "",
        "workflow_family": "",
        "task_id": "",
        "localguys_enabled": True,
        "localguys_idle_sec": 900,
        "localguys_action": "auto",
    }


def _load_heartbeat_config() -> Dict[str, Any]:
    base = dict(_default_heartbeat_config())
    if _CONFIG_FILE.exists():
        try:
            raw = json.loads(_CONFIG_FILE.read_text())
            if isinstance(raw, dict):
                base.update(raw)
        except Exception as e:
            logger.debug(f"[Heartbeat] Failed to load config: {e}")
    return base


def _parse_ts_seconds(value: Any) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        from datetime import datetime

        return float(datetime.fromisoformat(text).timestamp())
    except Exception:
        return 0.0


def _task_matches_heartbeat_profile(task: Dict[str, Any], config: Dict[str, Any]) -> bool:
    profile_mode = str(config.get("profile_mode") or "global").strip().lower()
    project_id = str(config.get("project_id") or "").strip()
    workflow_family = str(config.get("workflow_family") or "").strip()
    task_id = str(config.get("task_id") or "").strip()
    if profile_mode == "task":
        return bool(task_id) and str(task.get("id") or "").strip() == task_id
    if profile_mode == "workflow":
        if project_id and str(task.get("project_id") or task.get("roadmap_id") or "").strip() != project_id:
            return False
        return bool(workflow_family) and str(task.get("workflow_family") or task.get("workflow_id") or "").strip() == workflow_family
    if profile_mode == "project":
        return bool(project_id) and str(task.get("project_id") or task.get("roadmap_id") or "").strip() == project_id
    return True


def _effective_heartbeat_profile(config: Dict[str, Any]) -> Dict[str, str]:
    profile_mode = str(config.get("profile_mode") or "global").strip().lower()
    if profile_mode not in {"global", "project", "workflow", "task"}:
        profile_mode = "global"
    project_id = str(config.get("project_id") or "").strip()
    workflow_family = str(config.get("workflow_family") or "").strip()
    task_id = str(config.get("task_id") or "").strip()

    if profile_mode == "task":
        key = f"task:{task_id or '-'}"
    elif profile_mode == "workflow":
        workflow_key = workflow_family or "-"
        key = f"workflow:{workflow_key}@{project_id}" if project_id else f"workflow:{workflow_key}"
    elif profile_mode == "project":
        key = f"project:{project_id or '-'}"
    else:
        key = "global"

    return {
        "mode": profile_mode,
        "project_id": project_id,
        "workflow_family": workflow_family,
        "task_id": task_id,
        "key": key,
    }


def _is_stalled_localguys_run(run: Dict[str, Any], idle_sec: int) -> bool:
    status = str(run.get("status") or "").strip().lower()
    if status in {"done", "failed", "blocked", "escalated"}:
        return False
    updated_ts = _parse_ts_seconds(run.get("updated_at"))
    if updated_ts <= 0:
        return False
    return (time.time() - updated_ts) >= max(60, int(idle_sec or 900))


def _fetch_localguys_runtime_snapshot(task_id: str) -> Dict[str, Any]:
    import httpx

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"http://localhost:5001/api/mcc/tasks/{task_id}/localguys-run")
            if response.status_code != 200:
                return {}
            data = response.json()
            if not isinstance(data, dict):
                return {}
            return {
                "run": dict(data.get("run") or {}),
                "runtime_guard": dict(data.get("runtime_guard") or {}),
            }
    except Exception as e:
        logger.debug(f"[Heartbeat] localguys runtime snapshot failed for {task_id}: {e}")
        return {}


def _build_localguys_resume_payload(task: Dict[str, Any], run: Dict[str, Any], runtime_guard: Dict[str, Any]) -> Dict[str, Any]:
    current_step = str(run.get("current_step") or runtime_guard.get("current_step") or "unknown").strip()
    task_id = str(task.get("id") or "").strip()
    run_id = str(run.get("run_id") or "").strip()
    workflow_family = str(task.get("workflow_family") or run.get("workflow_family") or "").strip()
    allowed_tools = [str(tool).strip() for tool in list(runtime_guard.get("allowed_tools") or []) if str(tool).strip()]
    lines = [
        f"Resume stalled localguys run {run_id} for task {task_id}.",
        f"Current step: {current_step}.",
        f"Verification target: {str(runtime_guard.get('verification_target') or '-').strip() or '-'}",
        f"Allowed tools for this step: {', '.join(allowed_tools) if allowed_tools else 'none'}",
        f"Nudge: {str(runtime_guard.get('idle_nudge_template') or '').strip() or 'Continue within current scope.'}",
    ]
    return {
        "title": f"Resume localguys: {str(task.get('title') or task_id)[:72]}",
        "description": "\n".join(lines),
        "priority": int(task.get("priority") or 2),
        "phase_type": str(task.get("phase_type") or "build"),
        "preset": str(task.get("team_profile") or task.get("preset") or "dragon_silver"),
        "tags": list(task.get("tags") or []) + ["localguys_resume", f"run:{run_id}"],
        "dependencies": [task_id] if task_id else [],
        "source": "heartbeat_localguys_resume",
        "created_by": "heartbeat:localguys",
        "workflow_id": str(task.get("workflow_id") or workflow_family),
        "workflow_family": workflow_family,
        "workflow_selection_origin": "heartbeat_resume",
        "team_profile": str(task.get("team_profile") or task.get("preset") or "dragon_silver"),
        "task_origin": "heartbeat_localguys_resume",
        "project_id": str(task.get("project_id") or task.get("roadmap_id") or ""),
        "project_lane": str(task.get("project_lane") or task.get("roadmap_node_id") or task.get("project_id") or ""),
        "parent_task_id": task_id,
        "roadmap_id": task.get("roadmap_id"),
        "roadmap_node_id": task.get("roadmap_node_id"),
        "roadmap_lane": task.get("roadmap_lane"),
        "roadmap_title": task.get("roadmap_title"),
        "architecture_docs": list(task.get("architecture_docs") or []),
        "closure_files": list(task.get("closure_files") or []),
    }


async def _process_localguys_heartbeat(group_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    effective_profile = _effective_heartbeat_profile(config)
    if not bool(config.get("localguys_enabled", True)):
        return {
            "checked": 0,
            "stalled": 0,
            "nudged": 0,
            "resumed": 0,
            "results": [],
            "effective_profile": effective_profile,
        }

    from src.orchestration.task_board import get_task_board
    from src.services.mcc_local_run_registry import get_localguys_run_registry

    board = get_task_board()
    registry = get_localguys_run_registry()
    idle_sec = max(60, int(config.get("localguys_idle_sec") or 900))
    action = str(config.get("localguys_action") or "auto").strip().lower() or "auto"
    tasks = [
        task for task in board.get_queue()
        if str(task.get("workflow_family") or task.get("workflow_id") or "").strip().endswith("_localguys")
        and _task_matches_heartbeat_profile(task, config)
    ]
    results: List[Dict[str, Any]] = []
    stalled = 0
    nudged = 0
    resumed = 0
    for task in tasks:
        task_id = str(task.get("id") or "").strip()
        if not task_id:
            continue
        run = registry.get_latest_for_task(task_id)
        if not isinstance(run, dict) or not _is_stalled_localguys_run(run, idle_sec):
            continue
        stalled += 1
        snapshot = _fetch_localguys_runtime_snapshot(task_id)
        runtime_guard = dict(snapshot.get("runtime_guard") or {})
        run_id = str(run.get("run_id") or "").strip()
        idle_turns = int(((run.get("telemetry") or {}).get("idle_turn_count") or 0))
        next_tools = [str(tool).strip() for tool in list(runtime_guard.get("allowed_tools") or []) if str(tool).strip()]
        registry.update_run(
            run_id,
            metadata={
                "idle_turn_count": idle_turns + 1,
                "recommended_tools": next_tools,
                "verification_target": str(runtime_guard.get("verification_target") or ""),
            },
        )

        effective_action = action
        if action == "auto":
            effective_action = "resume_task" if idle_turns >= 1 else "nudge"

        if effective_action == "resume_task":
            active_resume_exists = any(
                str(row.get("status") or "") in {"pending", "queued", "running", "claimed"}
                and str(row.get("task_origin") or "") == "heartbeat_localguys_resume"
                and str(row.get("parent_task_id") or "") == task_id
                and f"run:{run_id}" in list(row.get("tags") or [])
                for row in board.get_queue()
            )
            if not active_resume_exists:
                payload = _build_localguys_resume_payload(task, run, runtime_guard)
                board.add_task(**payload)
                resumed += 1
                _emit_heartbeat_status(
                    group_id,
                    f"@pipeline: localguys resume queued for {task_id} · run:{run_id} · step:{runtime_guard.get('current_step') or run.get('current_step') or '-'}",
                )
                results.append({
                    "task_id": task_id,
                    "run_id": run_id,
                    "action": "resume_task",
                    "effective_profile_key": effective_profile["key"],
                })
                continue

        nudged += 1
        _emit_heartbeat_status(
            group_id,
            f"@pipeline: localguys nudge for {task_id} · run:{run_id} · step:{runtime_guard.get('current_step') or run.get('current_step') or '-'} · tools:{', '.join(next_tools) if next_tools else '-'}",
        )
        results.append({
            "task_id": task_id,
            "run_id": run_id,
            "action": "nudge",
            "effective_profile_key": effective_profile["key"],
        })

    return {
        "checked": len(tasks),
        "stalled": stalled,
        "nudged": nudged,
        "resumed": resumed,
        "results": results,
        "effective_profile": effective_profile,
    }


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


# MARKER_140.SOLO_CHAT: Fetch messages from solo chats for @mention processing
def _fetch_solo_chat_messages(
    chat_id: str,
    since_id: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Fetch new messages from a solo chat via REST API.

    Solo chats use role/content format. We normalize to match group chat format
    (sender_id, content, id) so _parse_tasks works uniformly.
    """
    import httpx

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"http://localhost:5001/api/chats/{chat_id}")
            if response.status_code != 200:
                return []
            data = response.json()
            raw_messages = data.get("messages", [])

            # Normalize solo chat messages to group chat format
            normalized = []
            for msg in raw_messages:
                msg_id = msg.get("id", "")
                # Skip messages we've already seen
                if since_id and msg_id <= since_id:
                    continue
                normalized.append({
                    "id": msg_id,
                    "content": msg.get("content", ""),
                    "sender_id": msg.get("agent") or msg.get("role", "user"),
                    "message_type": msg.get("role", "user"),
                    "timestamp": msg.get("timestamp", ""),
                })

            # Only return last N messages
            return normalized[-limit:]
    except Exception as e:
        logger.error(f"[Heartbeat] Fetch solo chat {chat_id[:8]} error: {e}")
        return []


def _fetch_all_active_group_ids() -> List[str]:
    """Fetch all active group IDs from VETKA server."""
    import httpx
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get("http://localhost:5001/api/debug/mcp/groups")
            if response.status_code == 200:
                data = response.json()
                groups = data.get("groups", [])
                return [g.get("id") for g in groups if g.get("id")]
            return []
    except Exception:
        return []


def _fetch_recent_solo_chat_ids(limit: int = 10) -> List[str]:
    """Fetch IDs of recently active solo chats."""
    import httpx
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                "http://localhost:5001/api/chats",
                params={"limit": limit, "offset": 0}
            )
            if response.status_code == 200:
                data = response.json()
                chats = data.get("chats", [])
                return [c.get("id") for c in chats if c.get("id")]
            return []
    except Exception:
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
                    trigger=trigger_word,
                    source_chat_id=msg.get("_source_chat_id", ""),
                    source_chat_type=msg.get("_source_chat_type", "group"),
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
    logger.info(f"[Heartbeat] Dispatching: {task.task[:60]}... (phase={task.phase_type})")

    _emit_heartbeat_status(
        group_id,
        f"@pipeline: \u2764\ufe0f Heartbeat detected task from {task.sender_id}:\n"
        f"Trigger: `{task.trigger}` | Phase: `{task.phase_type}`\n"
        f"Task: {task.task[:200]}"
    )

    # MARKER_121_BOARD: Handle @board commands via TaskBoard
    if task.trigger == "board":
        return await _handle_board_command(task, group_id)

    from src.orchestration.agent_pipeline import AgentPipeline

    # MARKER_118.10_TITAN_DISPATCH: Use titan_core preset for @titan trigger
    preset = "titan_core" if task.trigger == "titan" else None
    pipeline = AgentPipeline(chat_id=group_id, preset=preset)

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


# MARKER_121_BOARD: Handle @board commands
async def _handle_board_command(task: ParsedTask, group_id: str) -> Dict[str, Any]:
    """Handle @board <command> from chat.

    Supported commands:
        @board dispatch — dispatch highest-priority task
        @board list — show pending tasks
        @board summary — show board summary
    """
    try:
        from src.orchestration.task_board import get_task_board

        board = get_task_board()
        command = task.task.strip().lower()

        if command.startswith("dispatch"):
            result = await board.dispatch_next(chat_id=group_id)
            _emit_heartbeat_status(
                group_id,
                f"@board: {'✅' if result.get('success') else '❌'} Dispatch: {json.dumps(result, default=str)[:300]}"
            )
            return result

        elif command.startswith("list"):
            tasks = board.get_queue(status="pending")
            task_lines = [f"  P{t['priority']} [{t['phase_type']}] {t['title'][:60]}" for t in tasks[:10]]
            _emit_heartbeat_status(
                group_id,
                f"@board: 📋 {len(tasks)} pending tasks:\n" + "\n".join(task_lines)
            )
            return {"success": True, "count": len(tasks)}

        elif command.startswith("summary"):
            summary = board.get_board_summary()
            _emit_heartbeat_status(
                group_id,
                f"@board: 📊 Task Board: {summary['total']} total, "
                f"{json.dumps(summary.get('by_status', {}), default=str)}"
            )
            return {"success": True, **summary}

        else:
            _emit_heartbeat_status(
                group_id,
                f"@board: ❓ Unknown command '{command}'. Use: dispatch, list, summary"
            )
            return {"success": False, "error": f"Unknown board command: {command}"}

    except Exception as e:
        logger.error(f"[Heartbeat] Board command failed: {e}")
        return {"success": False, "error": str(e)}
# MARKER_121_BOARD_END


async def heartbeat_tick(
    group_id: str = HEARTBEAT_GROUP_ID,
    dry_run: bool = False,
    monitor_all: bool = False,
) -> Dict[str, Any]:
    """
    Execute one heartbeat tick.

    1. Load state (last_message_id per chat)
    2. Fetch new messages since last tick
    3. Parse tasks from messages (@dragon, @doctor, @titan, etc.)
    4. Dispatch tasks to pipeline (unless dry_run)
    5. Update state
    6. Report back to chat

    Args:
        group_id: Primary group chat to monitor (legacy, always included)
        dry_run: If True, parse but don't execute tasks
        monitor_all: If True, monitor ALL active group + solo chats (MARKER_140)

    Returns:
        Tick result with new messages count, tasks found, tasks dispatched
    """
    tick_start = time.time()
    state = _load_state()
    config = _load_heartbeat_config()
    effective_profile = _effective_heartbeat_profile(config)

    logger.info(f"[Heartbeat] Tick #{state.total_ticks + 1} "
                f"(last_msg: {state.last_message_id or 'none'}, monitor_all={monitor_all})")

    # MARKER_140.MULTI_CHAT: Collect messages from all monitored chats
    # Per-chat last_message_id tracking (stored in state file under "chat_cursors")
    _cursors_file = Path(__file__).parent.parent.parent / "data" / "heartbeat_cursors.json"
    chat_cursors = {}
    try:
        if _cursors_file.exists():
            chat_cursors = json.loads(_cursors_file.read_text())
    except Exception:
        chat_cursors = {}

    all_messages = []

    if monitor_all:
        # Fetch from ALL active groups
        group_ids = _fetch_all_active_group_ids()
        if group_id not in group_ids:
            group_ids.append(group_id)

        for gid in group_ids:
            cursor = chat_cursors.get(f"group:{gid}")
            msgs = _fetch_new_messages(gid, since_id=cursor)
            if msgs:
                # Tag messages with source chat for dispatch routing
                for m in msgs:
                    m["_source_chat_id"] = gid
                    m["_source_chat_type"] = "group"
                all_messages.extend(msgs)
                # Update cursor to latest message
                chat_cursors[f"group:{gid}"] = msgs[-1].get("id", cursor)

        # Fetch from recent solo chats
        solo_ids = _fetch_recent_solo_chat_ids(limit=10)
        for cid in solo_ids:
            cursor = chat_cursors.get(f"solo:{cid}")
            msgs = _fetch_solo_chat_messages(cid, since_id=cursor)
            if msgs:
                for m in msgs:
                    m["_source_chat_id"] = cid
                    m["_source_chat_type"] = "solo"
                all_messages.extend(msgs)
                chat_cursors[f"solo:{cid}"] = msgs[-1].get("id", cursor)

        # Persist cursors
        try:
            _cursors_file.parent.mkdir(parents=True, exist_ok=True)
            _cursors_file.write_text(json.dumps(chat_cursors, indent=2))
        except Exception:
            pass

        messages = all_messages
    else:
        # Legacy single-group mode
        messages = _fetch_new_messages(group_id, since_id=state.last_message_id)

    new_count = len(messages)

    if new_count == 0:
        logger.info("[Heartbeat] No new messages, sleeping...")
        localguys_result = {
            "checked": 0,
            "stalled": 0,
            "nudged": 0,
            "resumed": 0,
            "results": [],
            "effective_profile": effective_profile,
        }
        if not dry_run:
            localguys_result = await _process_localguys_heartbeat(group_id, config)
        state.total_ticks += 1
        state.last_tick_time = tick_start
        run_record = {
            "tick": state.total_ticks,
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "new_messages": 0,
            "tasks_found": 0,
            "tasks_dispatched": 0,
            "localguys_checked": int(localguys_result.get("checked") or 0),
            "localguys_stalled": int(localguys_result.get("stalled") or 0),
            "localguys_nudged": int(localguys_result.get("nudged") or 0),
            "localguys_resumed": int(localguys_result.get("resumed") or 0),
            "dry_run": dry_run,
        }
        state.recent_runs.append(run_record)
        state.recent_runs = state.recent_runs[-20:]
        _save_state(state)
        return {
            "tick": state.total_ticks,
            "new_messages": 0,
            "tasks_found": 0,
            "tasks_dispatched": 0,
            "localguys": localguys_result,
            "effective_profile": effective_profile,
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
    # MARKER_124.2B: Route through TaskBoard for priority ordering
    results = []
    if tasks and not dry_run:
        _emit_heartbeat_status(
            group_id,
            f"@pipeline: \u2764\ufe0f\u200d\ud83d\udd25 Heartbeat tick #{state.total_ticks + 1}: "
            f"{new_count} new messages, {len(tasks)} tasks detected!"
        )

        # Phase 124.2B: Add all tasks to TaskBoard first, then dispatch by priority
        from src.orchestration.task_board import get_task_board
        board = get_task_board()

        for task in tasks:
            # @board commands handled directly (not queued)
            if task.trigger == "board":
                result = await _handle_board_command(task, group_id)
                results.append({
                    "task": task.task[:100],
                    "phase_type": task.phase_type,
                    "trigger": task.trigger,
                    "sender": task.sender_id,
                    **result
                })
                continue

            # MARKER_136.GUARD: Skip tasks with too-short descriptions (junk prevention)
            if len(task.task.strip()) < 15:
                logger.warning(f"[Heartbeat] Skipping too-short task: '{task.task[:50]}' ({len(task.task)} chars)")
                continue

            # MARKER_130.C19A: Deduplication — skip if task with same title exists or was recently processed
            task_title = task.task[:100]
            existing_tasks = board.get_queue()

            # Check active tasks (pending, queued, running, claimed)
            is_active_duplicate = any(
                t.get("title") == task_title and t.get("status") in ("pending", "queued", "running", "claimed")
                for t in existing_tasks
            )

            # Check recently completed tasks (done/failed within 1 hour)
            from datetime import datetime, timedelta
            one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
            is_recent_duplicate = any(
                t.get("title") == task_title
                and t.get("status") in ("done", "failed")
                and (t.get("completed_at") or "") > one_hour_ago
                for t in existing_tasks
            )

            if is_active_duplicate or is_recent_duplicate:
                logger.debug(f"[Heartbeat] Skipping duplicate task: {task_title[:50]}...")
                continue

            # Add to board for priority-ordered dispatch
            task_id = board.add_task(
                title=task_title,
                description=task.task,
                priority=2 if task.trigger in ("dragon", "titan") else 3,
                phase_type=task.phase_type,
                preset="titan_core" if task.trigger == "titan" else None,
                source=f"heartbeat_{task.trigger}",
                tags=[task.trigger],
                created_by=f"heartbeat:{task.trigger}",  # MARKER_133.C33D
            )
            logger.info(f"[Heartbeat] Task queued in board: {task_id}")

        # Dispatch from board in priority order (max_concurrent tasks)
        max_dispatch = board.settings.get("max_concurrent", 2)
        dispatched = 0
        while dispatched < max_dispatch:
            result = await board.dispatch_next(chat_id=group_id)
            if not result or not result.get("success"):
                break
            dispatched += 1
            results.append({
                "task": result.get("task_title", "")[:100],
                "phase_type": result.get("phase_type", "build"),
                "trigger": "board_dispatch",
                "sender": "heartbeat",
                **result
            })

            if result.get("success"):
                state.tasks_completed += 1
            else:
                state.tasks_failed += 1

            state.tasks_dispatched += 1
        # MARKER_124.2B_END

    elif tasks and dry_run:
        _emit_heartbeat_status(
            group_id,
            f"@pipeline: \ud83d\udc40 Heartbeat DRY RUN: {len(tasks)} tasks found but NOT executed\n"
            + "\n".join([f"  - [{t.trigger}] {t.task[:80]}" for t in tasks])
        )
        results = [{"task": t.task[:100], "phase_type": t.phase_type, "dry_run": True} for t in tasks]

    localguys_result = {
        "checked": 0,
        "stalled": 0,
        "nudged": 0,
        "resumed": 0,
        "results": [],
        "effective_profile": effective_profile,
    }
    if not dry_run:
        localguys_result = await _process_localguys_heartbeat(group_id, config)

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
        "localguys_checked": int(localguys_result.get("checked") or 0),
        "localguys_stalled": int(localguys_result.get("stalled") or 0),
        "localguys_nudged": int(localguys_result.get("nudged") or 0),
        "localguys_resumed": int(localguys_result.get("resumed") or 0),
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
        "localguys": localguys_result,
        "effective_profile": effective_profile,
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


# MARKER_117.5A: Event-driven wakeup after pipeline completion
# Cursor insight: "Planners should wake when tasks complete"
# Instead of only polling, heartbeat auto-checks for follow-up tasks
# when a pipeline finishes execution.
async def on_pipeline_complete(chat_id: str) -> Dict[str, Any]:
    """Event-driven wakeup — check for follow-up tasks after pipeline completes.

    Called by AgentPipeline.execute() after successful completion.
    Triggers a quick heartbeat tick on the same chat to detect chained tasks.

    Args:
        chat_id: Group chat ID where pipeline completed

    Returns:
        Heartbeat tick result (or empty dict if wakeup skipped)
    """
    logger.info(f"[Heartbeat] ⚡ Wakeup triggered by pipeline completion in {chat_id}")

    try:
        result = await heartbeat_tick(group_id=chat_id, dry_run=False)
        logger.info(f"[Heartbeat] Wakeup tick: {result.get('tasks_found', 0)} follow-up tasks found")
        return result
    except Exception as e:
        logger.warning(f"[Heartbeat] Wakeup tick failed (non-fatal): {e}")
        return {"wakeup": "skipped", "error": str(e)}
# MARKER_117.5A_END
