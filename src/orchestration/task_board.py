"""
Mycelium Task Board — Central Task Queue for Multi-Agent Dispatch

Phase 121: Multi-agent task queue system.

Task Board manages a priority queue of tasks that can be dispatched
to the Mycelium Pipeline (Dragon/Titan teams). Tasks are stored in
data/task_board.json with priority, complexity, dependencies, and status.

Flow:
    [Add Tasks] → [Priority Queue] → [Dispatch] → [Pipeline] → [Update Status]
                       ↑                                            │
                       └────────── [Heartbeat @board] ──────────────┘

@status: active
@phase: 121
@depends: src/orchestration/agent_pipeline.py, src/orchestration/mycelium_heartbeat.py
"""

import json
import time
import logging
import os
import re
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("VETKA_TASK_BOARD")

# MARKER_121.1: Task Board storage
TASK_BOARD_FILE = Path(__file__).parent.parent.parent / "data" / "task_board.json"
_TASK_BOARD_FALLBACK = Path(os.environ.get('TMPDIR', '/tmp')) / "vetka_task_board.json"

# Priority levels
PRIORITY_CRITICAL = 1
PRIORITY_HIGH = 2
PRIORITY_MEDIUM = 3
PRIORITY_LOW = 4
PRIORITY_SOMEDAY = 5

# Valid statuses
# MARKER_125.1B: Added "hold" — Doctor triage puts abstract tasks on hold for human approval
# MARKER_130.C16A: Added "claimed" status for multi-agent support
VALID_STATUSES = {"pending", "queued", "claimed", "running", "done", "failed", "cancelled", "hold"}

# Agent types
AGENT_TYPES = {"claude_code", "cursor", "mycelium", "grok", "human", "unknown"}

# Counter for generating IDs
_task_counter = 0


def _generate_task_id() -> str:
    """Generate unique task ID."""
    global _task_counter
    _task_counter += 1
    return f"tb_{int(time.time())}_{_task_counter}"


class TaskBoard:
    """Central task queue for Mycelium pipeline dispatch.

    Manages a JSON-backed priority queue of tasks. Tasks are dispatched
    to AgentPipeline with appropriate presets based on complexity and tags.

    Usage:
        board = TaskBoard()
        task_id = board.add_task("Fix bug", "Fix file positioning", priority=2)
        await board.dispatch_next(chat_id="some-chat-id")
    """

    # MARKER_133.C33C: Class-level semaphore for concurrent dispatch limiting
    _dispatch_semaphore: Optional[asyncio.Semaphore] = None
    _dispatch_semaphore_size: int = 2  # Default max concurrent

    @classmethod
    def _get_dispatch_semaphore(cls, max_concurrent: int = 2) -> asyncio.Semaphore:
        """Get or create the dispatch semaphore.

        MARKER_133.C33C: Enforces max_concurrent pipelines running.
        """
        # Create new semaphore if size changed or doesn't exist
        if cls._dispatch_semaphore is None or cls._dispatch_semaphore_size != max_concurrent:
            cls._dispatch_semaphore = asyncio.Semaphore(max_concurrent)
            cls._dispatch_semaphore_size = max_concurrent
            logger.info(f"[TaskBoard] Created dispatch semaphore with max_concurrent={max_concurrent}")
        return cls._dispatch_semaphore

    @classmethod
    def get_concurrent_info(cls, board: 'TaskBoard') -> Dict[str, Any]:
        """Get current concurrency info for monitoring.

        MARKER_133.C33C: Returns max, available slots, and running count.
        """
        max_c = board.settings.get("max_concurrent", 2)
        sem = cls._get_dispatch_semaphore(max_c)
        running = len([t for t in board.tasks.values() if t.get("status") == "running"])
        return {
            "max": max_c,
            "available": sem._value if hasattr(sem, '_value') else max_c,
            "running": running,
        }
    # MARKER_133.C33C_END

    def __init__(self, board_file: Optional[Path] = None):
        """Initialize TaskBoard with storage file.

        Args:
            board_file: Path to JSON storage. Defaults to data/task_board.json.
        """
        self.board_file = board_file or TASK_BOARD_FILE
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.settings: Dict[str, Any] = {
            "max_concurrent": 2,
            "auto_dispatch": False,
            "default_preset": "dragon_silver"
        }
        self._load()

    # ==========================================
    # PERSISTENCE
    # ==========================================

    def _load(self):
        """Load task board from disk."""
        for path in [self.board_file, _TASK_BOARD_FALLBACK]:
            if path.exists():
                try:
                    data = json.loads(path.read_text())
                    self.tasks = data.get("tasks", {})
                    self.settings = data.get("settings", self.settings)
                    logger.info(f"[TaskBoard] Loaded {len(self.tasks)} tasks from {path}")
                    return
                except Exception as e:
                    logger.warning(f"[TaskBoard] Failed to load from {path}: {e}")
        logger.info("[TaskBoard] No existing board found, starting fresh")

    def _save(self, action: str = "update"):
        """Save task board to disk with sandbox fallback."""
        data = {
            "_meta": {
                "version": "1.0",
                "phase": "121",
                "updated": datetime.now().isoformat()
            },
            "tasks": self.tasks,
            "settings": self.settings
        }
        content = json.dumps(data, indent=2, default=str, ensure_ascii=False)

        for path in [self.board_file, _TASK_BOARD_FALLBACK]:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
                logger.debug(f"[TaskBoard] Saved {len(self.tasks)} tasks to {path}")
                # MARKER_124.3D: Emit SocketIO event for live UI updates
                self._notify_board_update(action)
                return
            except (PermissionError, OSError) as e:
                logger.warning(f"[TaskBoard] Cannot write to {path}: {e}")

        logger.error("[TaskBoard] Failed to save task board to any location")

    def _notify_board_update(self, action: str = "update", event_data: Optional[Dict[str, Any]] = None):
        """MARKER_124.3D: Emit SocketIO event for live Task Board UI updates.
        MARKER_130.C18C: Enhanced with event_data for claim/complete actions.

        Uses fire-and-forget HTTP POST to our own REST endpoint which has sio access.
        Falls back silently if server isn't running.

        Args:
            action: Event action type (update, task_claimed, task_completed, etc.)
            event_data: Optional extra data to include in event (task_id, assigned_to, etc.)
        """
        try:
            import asyncio
            summary = self.get_board_summary()

            # MARKER_130.C18C: Build payload with optional event_data
            payload = {"action": action, "summary": summary}
            if event_data:
                payload.update(event_data)

            async def _emit():
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=2.0) as client:
                        await client.post(
                            "http://localhost:5001/api/debug/task-board/notify",
                            json=payload
                        )
                except Exception:
                    pass

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_emit())
            except RuntimeError:
                pass  # No event loop (sync context)
        except Exception:
            pass  # Never block save on notification failure

    # ==========================================
    # CRUD OPERATIONS
    # ==========================================

    def add_task(
        self,
        title: str,
        description: str = "",
        priority: int = PRIORITY_MEDIUM,
        phase_type: str = "build",
        complexity: str = "medium",
        preset: Optional[str] = None,
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        source: str = "manual",
        assigned_to: Optional[str] = None,  # MARKER_130.C16A
        agent_type: Optional[str] = None,   # MARKER_130.C16A
        created_by: str = "unknown",        # MARKER_133.C33D: Client attribution
    ) -> str:
        """Add a new task to the board.

        Args:
            title: Short task title
            description: Detailed description for pipeline
            priority: 1 (critical) to 5 (someday)
            phase_type: "build" | "fix" | "research"
            complexity: "low" | "medium" | "high"
            preset: Optional pipeline preset override
            tags: Optional tags for categorization
            dependencies: Optional list of task IDs that must complete first
            source: Origin of task ("manual", "dragon_todo", "titan_todo", etc.)
            assigned_to: Agent name who should work on this ("opus", "cursor", "dragon")
            agent_type: Agent type ("claude_code", "cursor", "mycelium", "grok", "human")
            created_by: Client that created task ("claude-code", "cursor", "opencode", "heartbeat")

        Returns:
            Generated task ID
        """
        task_id = _generate_task_id()
        priority = max(1, min(5, priority))  # Clamp 1-5

        self.tasks[task_id] = {
            "id": task_id,
            "title": title,
            "description": description or title,
            "priority": priority,
            "complexity": complexity,
            "phase_type": phase_type,
            "preset": preset,
            "assigned_tier": None,
            "status": "pending",
            "source": source,
            "tags": tags or [],
            "dependencies": dependencies or [],
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "pipeline_task_id": None,
            "result_summary": None,
            "stats": None,
            # MARKER_135.DAG_BRIDGE: Result data for DAG visualization
            "result": None,  # {agents: {...}, subtasks: [...]} for DAGAggregator
            # MARKER_130.C16A: Multi-agent coordination fields
            "assigned_to": assigned_to,       # Agent name: "opus", "cursor", "dragon", "grok"
            "assigned_at": None,              # ISO timestamp when claimed
            "agent_type": agent_type,         # "claude_code", "cursor", "mycelium", "grok", "human"
            "commit_hash": None,              # Git commit that completed this task
            "commit_message": None,           # First line of commit message
            # MARKER_133.C33D: Client attribution
            "created_by": created_by,         # "claude-code", "cursor", "opencode", "heartbeat"
        }

        self._save(action="added")
        logger.info(f"[TaskBoard] Added task {task_id}: {title} (P{priority}, {phase_type})")
        return task_id

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task dict or None if not found
        """
        return self.tasks.get(task_id)

    def update_task(self, task_id: str, **updates) -> bool:
        """Update task fields.

        Args:
            task_id: Task identifier
            **updates: Field=value pairs to update

        Returns:
            True if task was found and updated
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"[TaskBoard] Task {task_id} not found for update")
            return False

        # Validate status if being updated
        if "status" in updates:
            if updates["status"] not in VALID_STATUSES:
                logger.warning(f"[TaskBoard] Invalid status: {updates['status']}")
                return False

        for key, value in updates.items():
            if key in task:
                task[key] = value

        self._save(action="updated")
        logger.debug(f"[TaskBoard] Updated {task_id}: {list(updates.keys())}")
        return True

    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the board.

        Args:
            task_id: Task identifier

        Returns:
            True if task was found and removed
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save(action="removed")
            logger.info(f"[TaskBoard] Removed task {task_id}")
            return True
        return False

    # ==========================================
    # MARKER_133.C33F: STALE TASK CLEANUP
    # ==========================================

    def cleanup_stale(
        self,
        running_timeout_min: int = 10,
        claimed_timeout_min: int = 5,
    ) -> int:
        """Mark stale running tasks as failed, release stale claimed tasks.

        Args:
            running_timeout_min: Max minutes a task can be "running" before marked failed
            claimed_timeout_min: Max minutes a task can be "claimed" before reset to pending

        Returns:
            Number of tasks cleaned up
        """
        now = datetime.now()
        cleaned = 0

        for task in self.tasks.values():
            status = task.get("status")

            if status == "running":
                started_at = task.get("started_at")
                if started_at:
                    try:
                        started = datetime.fromisoformat(started_at.replace("Z", "+00:00").replace("+00:00", ""))
                        if (now - started).total_seconds() > running_timeout_min * 60:
                            task["status"] = "failed"
                            task["result_summary"] = f"Timeout: running > {running_timeout_min}min"
                            cleaned += 1
                            logger.info(f"[TaskBoard] Cleaned stale running task {task.get('id')}")
                    except Exception:
                        pass

            elif status == "claimed":
                assigned_at = task.get("assigned_at")
                if assigned_at:
                    try:
                        claimed = datetime.fromisoformat(assigned_at.replace("Z", "+00:00").replace("+00:00", ""))
                        if (now - claimed).total_seconds() > claimed_timeout_min * 60:
                            task["status"] = "pending"
                            task["assigned_to"] = None
                            task["assigned_at"] = None
                            cleaned += 1
                            logger.info(f"[TaskBoard] Released stale claimed task {task.get('id')}")
                    except Exception:
                        pass

        if cleaned:
            self._save(action="cleanup")
            logger.info(f"[TaskBoard] Cleaned {cleaned} stale tasks")

        return cleaned

    # ==========================================
    # MARKER_130.C16A: AGENT COORDINATION
    # ==========================================

    def claim_task(self, task_id: str, agent_name: str, agent_type: str = "unknown") -> Dict[str, Any]:
        """Claim a task for an agent.

        Args:
            task_id: Task identifier
            agent_name: Name of agent claiming ("opus", "cursor", "dragon", "grok")
            agent_type: Type of agent ("claude_code", "cursor", "mycelium", "grok", "human")

        Returns:
            Result dict with success/error
        """
        task = self.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        if task["status"] not in ("pending", "queued"):
            return {"success": False, "error": f"Task {task_id} is {task['status']}, can't claim"}

        self.update_task(task_id,
            status="claimed",
            assigned_to=agent_name,
            agent_type=agent_type,
            assigned_at=datetime.now().isoformat(),
        )

        # MARKER_130.C18C: Emit enhanced event for claim
        self._notify_board_update("task_claimed", {
            "task_id": task_id,
            "title": task.get("title", ""),
            "assigned_to": agent_name,
            "agent_type": agent_type,
        })

        logger.info(f"[TaskBoard] Task {task_id} claimed by {agent_name} ({agent_type})")
        return {"success": True, "task_id": task_id, "assigned_to": agent_name}

    def complete_task(self, task_id: str, commit_hash: Optional[str] = None,
                      commit_message: Optional[str] = None) -> Dict[str, Any]:
        """Mark a task as complete with optional commit info.

        Args:
            task_id: Task identifier
            commit_hash: Git commit hash that completed this task
            commit_message: First line of commit message

        Returns:
            Result dict with success/error
        """
        task = self.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        update = {
            "status": "done",
            "completed_at": datetime.now().isoformat(),
        }
        if commit_hash:
            update["commit_hash"] = commit_hash
        if commit_message:
            update["commit_message"] = commit_message[:200]  # Truncate

        self.update_task(task_id, **update)

        # MARKER_130.C18C: Emit enhanced event for completion
        self._notify_board_update("task_completed", {
            "task_id": task_id,
            "title": task.get("title", ""),
            "assigned_to": task.get("assigned_to"),
            "commit_hash": commit_hash,
            "commit_message": commit_message[:50] if commit_message else None,
        })

        logger.info(f"[TaskBoard] Task {task_id} completed" +
                    (f" (commit: {commit_hash[:8]})" if commit_hash else ""))
        return {"success": True, "task_id": task_id, "commit_hash": commit_hash}

    def get_active_agents(self) -> List[Dict[str, Any]]:
        """Get list of agents with active (claimed/running) tasks.

        Returns:
            List of dicts with agent_name, agent_type, task_id, task_title, elapsed_time
        """
        active = []
        now = datetime.now()

        for task in self.tasks.values():
            if task["status"] in ("claimed", "running"):
                agent = task.get("assigned_to")
                if agent:
                    assigned_at = task.get("assigned_at") or task.get("started_at")
                    elapsed = 0
                    if assigned_at:
                        try:
                            start = datetime.fromisoformat(assigned_at)
                            elapsed = int((now - start).total_seconds())
                        except (ValueError, TypeError):
                            pass

                    active.append({
                        "agent_name": agent,
                        "agent_type": task.get("agent_type", "unknown"),
                        "task_id": task["id"],
                        "task_title": task["title"],
                        "status": task["status"],
                        "elapsed_seconds": elapsed,
                    })

        return active

    # ==========================================
    # MARKER_130.C17A: GIT COMMIT AUTO-DETECTION
    # ==========================================

    def auto_complete_by_commit(self, commit_hash: str, commit_message: str) -> List[str]:
        """Auto-complete tasks mentioned in commit message.

        Looks for patterns in commit message:
        - "Phase 129.C13" → find task with tag "C13" or title containing "C13"
        - "tb_xxxx" → direct task ID reference
        - "MARKER_130.6" → find task with matching marker

        Args:
            commit_hash: Git commit hash
            commit_message: Full commit message

        Returns:
            List of task IDs that were auto-completed
        """
        completed = []
        # Normalize commit message for matching
        msg_lower = commit_message.lower()

        # Get tasks that could be auto-completed (claimed or running)
        eligible = [t for t in self.tasks.values() if t["status"] in ("claimed", "running")]

        for task in eligible:
            if self._commit_matches_task(task, commit_message, msg_lower):
                self.complete_task(task["id"], commit_hash, commit_message.split('\n')[0])
                completed.append(task["id"])
                logger.info(f"[TaskBoard] Auto-completed {task['id']} from commit {commit_hash[:8]}")

        return completed

    def _commit_matches_task(self, task: Dict[str, Any], commit_msg: str, msg_lower: str) -> bool:
        """Check if commit message matches a task.

        Matches:
        - Direct task ID mention (tb_xxx)
        - Task title keywords in commit message
        - Tag matches (C13, C16A, etc.)
        - Phase/MARKER patterns

        Args:
            task: Task dict
            commit_msg: Original commit message
            msg_lower: Lowercased commit message for case-insensitive matching

        Returns:
            True if commit appears to complete this task
        """
        task_id = task["id"]
        title = task.get("title", "")
        tags = task.get("tags", [])

        # Direct ID mention
        if task_id in commit_msg:
            return True

        # Tag mentions (e.g., "C13", "C16A" in commit matches task with that tag)
        for tag in tags:
            if tag and tag in commit_msg:
                return True

        # Title keyword matching (at least 3 significant words match)
        title_words = [w for w in re.findall(r'\w+', title.lower()) if len(w) > 3]
        if title_words:
            matches = sum(1 for w in title_words if w in msg_lower)
            if matches >= min(3, len(title_words)):
                return True

        # Phase/MARKER pattern (e.g., "Phase 130.C16" matches task tagged "C16")
        phase_match = re.search(r'Phase\s*(\d+)[\.\s]*([A-Z]\d+[A-Z]?)', commit_msg, re.IGNORECASE)
        if phase_match:
            phase_tag = phase_match.group(2).upper()
            if phase_tag in [t.upper() for t in tags]:
                return True

        return False

    # ==========================================
    # QUEUE OPERATIONS
    # ==========================================

    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """Get the highest-priority pending task with satisfied dependencies.

        Returns tasks sorted by: priority (ascending), then created_at (oldest first).
        Skips tasks whose dependencies haven't completed.

        Returns:
            Next task dict or None if queue is empty
        """
        pending = [
            t for t in self.tasks.values()
            if t["status"] == "pending"
        ]

        if not pending:
            return None

        # Filter by satisfied dependencies (Sugiyama-style: all deps must be done)
        ready = []
        for task in pending:
            deps = task.get("dependencies", [])
            if not deps:
                ready.append(task)
            else:
                all_done = all(
                    self.tasks.get(dep_id, {}).get("status") == "done"
                    for dep_id in deps
                )
                if all_done:
                    ready.append(task)

        if not ready:
            return None

        # Sort by priority (1=highest), then by creation time (oldest first)
        ready.sort(key=lambda t: (t["priority"], t["created_at"]))
        return ready[0]

    def get_queue(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get tasks filtered by status, sorted by priority.

        Args:
            status: Filter by status. None = all tasks.

        Returns:
            List of task dicts sorted by priority
        """
        if status:
            tasks = [t for t in self.tasks.values() if t["status"] == status]
        else:
            tasks = list(self.tasks.values())

        tasks.sort(key=lambda t: (t["priority"], t["created_at"]))
        return tasks

    def get_board_summary(self) -> Dict[str, Any]:
        """Get summary counts of tasks by status.

        Returns:
            Dict with counts per status, total, and next task preview
        """
        counts = {}
        for task in self.tasks.values():
            status = task["status"]
            counts[status] = counts.get(status, 0) + 1

        next_task = self.get_next_task()
        return {
            "total": len(self.tasks),
            "by_status": counts,
            "next_task": {
                "id": next_task["id"],
                "title": next_task["title"],
                "priority": next_task["priority"],
                "phase_type": next_task["phase_type"]
            } if next_task else None
        }

    # ==========================================
    # TODO MARKER_126.11B: MULTI-AGENT CLAIM SUPPORT
    # ==========================================
    # def claim_task(self, task_id: str, agent_id: str, agent_type: str = "mcp") -> bool:
    #     """External agent claims a task. Sets status='claimed', records agent info."""
    #     pass
    #
    # def release_task(self, task_id: str, agent_id: str, new_status: str = "done") -> bool:
    #     """Agent releases task after completion."""
    #     pass
    #
    # def get_claimable_tasks(self, limit: int = 5) -> List[Dict]:
    #     """Returns pending tasks ready for claiming. For session_init."""
    #     pass

    # ==========================================
    # STATISTICS (MARKER_126.0B)
    # ==========================================

    def record_pipeline_stats(self, task_id: str, stats: dict) -> bool:
        """Record pipeline execution statistics for a task.

        MARKER_126.0B: Called by AgentPipeline at end of execute().
        Stats include: preset, league, llm_calls, tokens, duration, success.
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        task["stats"] = stats
        self._save(action="stats_recorded")
        logger.info(f"[TaskBoard] Stats recorded for {task_id}: {stats.get('preset', '?')}")
        return True

    # ==========================================
    # CANCEL (MARKER_126.5D)
    # ==========================================

    # MARKER_126.5D: Global registry of running pipelines for cancellation
    _running_pipelines: dict = {}  # task_id -> AgentPipeline instance

    @classmethod
    def register_pipeline(cls, task_id: str, pipeline) -> None:
        """Register a running pipeline for future cancellation."""
        cls._running_pipelines[task_id] = pipeline
        logger.debug(f"[TaskBoard] Pipeline registered: {task_id}")

    @classmethod
    def unregister_pipeline(cls, task_id: str) -> None:
        """Unregister pipeline after completion."""
        cls._running_pipelines.pop(task_id, None)

    def cancel_task(self, task_id: str, reason: str = "Cancelled by user") -> bool:
        """Cancel a running or pending task.

        MARKER_126.5D: If task is running and pipeline is registered,
        signals cancellation via asyncio.Event.

        Returns:
            True if task was found and cancel was initiated
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"[TaskBoard] Task {task_id} not found for cancel")
            return False

        old_status = task["status"]

        if old_status in ("done", "cancelled", "failed"):
            logger.info(f"[TaskBoard] Task {task_id} already {old_status}, skip cancel")
            return False

        # If running — signal pipeline to stop
        if old_status == "running" and task_id in self._running_pipelines:
            pipeline = self._running_pipelines[task_id]
            pipeline.cancel(reason)
            logger.info(f"[TaskBoard] Pipeline {task_id} cancel signal sent")
            # Status will be set to "cancelled" by pipeline's except handler
            return True

        # For pending/queued/hold — just set status directly
        task["status"] = "cancelled"
        self._save(action="cancelled")
        logger.info(f"[TaskBoard] Task {task_id} cancelled (was {old_status})")
        return True

    # ==========================================
    # DISPATCH
    # ==========================================

    async def dispatch_next(
        self,
        chat_id: Optional[str] = None,
        selected_key: Optional[Dict[str, str]] = None  # MARKER_126.9E
    ) -> Dict[str, Any]:
        """Pick highest-priority task and dispatch to pipeline.

        Args:
            chat_id: Optional chat ID for progress streaming
            selected_key: Optional {provider, key_masked} for specific API key

        Returns:
            Dispatch result dict
        """
        task = self.get_next_task()
        if not task:
            return {"success": False, "error": "No pending tasks with satisfied dependencies"}

        return await self.dispatch_task(task["id"], chat_id=chat_id, selected_key=selected_key)

    async def dispatch_task(
        self,
        task_id: str,
        chat_id: Optional[str] = None,
        selected_key: Optional[Dict[str, str]] = None  # MARKER_126.9E
    ) -> Dict[str, Any]:
        """Dispatch a specific task to the Mycelium pipeline.

        Creates an AgentPipeline with appropriate preset based on task
        complexity and phase_type. Updates task status through lifecycle.

        MARKER_133.C33C: Enforces max_concurrent via semaphore.

        Args:
            task_id: Task to dispatch
            chat_id: Optional chat ID for progress streaming
            selected_key: Optional {provider, key_masked} for specific API key

        Returns:
            Dict with success status, pipeline_task_id, and result
        """
        task = self.tasks.get(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        if task["status"] not in ("pending", "queued"):
            return {"success": False, "error": f"Task {task_id} is {task['status']}, not dispatchable"}

        # MARKER_133.C33C: Check concurrent limit before dispatching
        max_concurrent = self.settings.get("max_concurrent", 2)
        sem = TaskBoard._get_dispatch_semaphore(max_concurrent)

        # Non-blocking check: if semaphore locked, return queued status
        if sem.locked():
            running_count = len([t for t in self.tasks.values() if t.get("status") == "running"])
            logger.warning(f"[TaskBoard] Max concurrent ({max_concurrent}) reached, queuing {task_id}. Running: {running_count}")
            self.update_task(task_id, status="queued")
            return {"success": False, "error": f"max_concurrent ({max_concurrent}) reached", "queued": True, "task_id": task_id}

        # Acquire semaphore and dispatch
        # MARKER_133.C33C: Pipeline execution inside semaphore context
        async with sem:
            # Mark as running (inside semaphore to ensure accurate count)
            self.update_task(task_id, status="running", started_at=datetime.now().isoformat())

            try:
                from src.orchestration.agent_pipeline import AgentPipeline

                # Determine preset: task-specific > phase-based > default
                preset = task.get("preset") or self.settings.get("default_preset")

                # MARKER_133.FIX1: auto_write=True — Dragon writes real code to disk
                pipeline = AgentPipeline(
                    chat_id=chat_id,
                    auto_write=True,
                    preset=preset
                )
                # MARKER_121.2: Tag pipeline with board task ID for callback
                pipeline._board_task_id = task_id

                # MARKER_126.9E: Pass selected key to pipeline for preferred key routing
                if selected_key:
                    pipeline.selected_key = selected_key

                # MARKER_126.5E: Register pipeline for cancellation support
                TaskBoard.register_pipeline(task_id, pipeline)

                # Build task description from title + description
                task_text = task["title"]
                if task.get("description") and task["description"] != task["title"]:
                    task_text += f"\n\n{task['description']}"

                try:
                    # Execute pipeline
                    result = await pipeline.execute(task_text, task["phase_type"])
                finally:
                    # Always unregister after completion
                    TaskBoard.unregister_pipeline(task_id)

                # Update task with results
                pipeline_status = result.get("status", "unknown")
                completed = pipeline_status == "done"

                # MARKER_C21A: Expanded result storage (2KB limit)
                pipeline_results = {
                    "subtasks_completed": result.get("results", {}).get("subtasks_completed", 0),
                    "subtasks_total": result.get("results", {}).get("subtasks_total", 0),
                    "files_created": result.get("results", {}).get("files_created", [])[:20],  # Limit to 20 files
                    "stats": result.get("results", {}).get("stats", {}),
                    "approval_status": result.get("results", {}).get("approval_status", "unknown"),
                    "success": result.get("results", {}).get("success", completed),
                }
                result_summary = json.dumps(pipeline_results)[:2000]  # 2KB limit

                self.update_task(
                    task_id,
                    status="done" if completed else "failed",
                    completed_at=datetime.now().isoformat(),
                    pipeline_task_id=result.get("task_id"),
                    assigned_tier=pipeline.preset_name,
                    result_summary=result_summary
                )

                logger.info(f"[TaskBoard] Task {task_id} dispatched → {'done' if completed else 'failed'}")

                return {
                    "success": completed,
                    "task_id": task_id,
                    "pipeline_task_id": result.get("task_id"),
                    "status": "done" if completed else "failed",
                    "tier_used": pipeline.preset_name,
                    "subtasks_completed": result.get("results", {}).get("subtasks_completed", 0),
                    "subtasks_total": result.get("results", {}).get("subtasks_total", 0)
                }

            except Exception as e:
                logger.error(f"[TaskBoard] Dispatch failed for {task_id}: {e}")
                self.update_task(
                    task_id,
                    status="failed",
                    completed_at=datetime.now().isoformat(),
                    result_summary=f"Dispatch error: {str(e)[:200]}"
                )
                return {"success": False, "task_id": task_id, "error": str(e)}

    # ==========================================
    # BULK IMPORT
    # ==========================================

    def import_from_todo(self, file_path: str, source_tag: str = "imported") -> int:
        """Import tasks from a plain-text todo file.

        Parses lines looking for task descriptions. Each non-empty line
        that doesn't look like a header becomes a task.

        Format heuristics:
        - Lines with "баг" / "fix" / "исправ" → phase_type="fix", priority=2
        - Lines with "research" / "исследов" / "выяснить" → phase_type="research", priority=3
        - Other lines → phase_type="build", priority=3

        Args:
            file_path: Path to todo file
            source_tag: Tag for task source tracking

        Returns:
            Number of tasks imported
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"[TaskBoard] Todo file not found: {file_path}")
            return 0

        content = path.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        imported = 0
        for line in lines:
            line = line.strip()
            # Skip empty lines, very short lines, headers
            if not line or len(line) < 10:
                continue
            # Skip lines that look like section headers
            if line.startswith("#") or line.startswith("="):
                continue

            # Determine phase_type and priority from content
            line_lower = line.lower()

            if any(w in line_lower for w in ["баг", "fix", "исправ", "broken", "не работает", "кривой"]):
                phase_type = "fix"
                priority = PRIORITY_HIGH
            elif any(w in line_lower for w in ["research", "исследов", "выяснить", "diagnose", "узнать"]):
                phase_type = "research"
                priority = PRIORITY_MEDIUM
            elif any(w in line_lower for w in ["нужно сделать", "добавить", "add", "create", "implement"]):
                phase_type = "build"
                priority = PRIORITY_MEDIUM
            else:
                phase_type = "build"
                priority = PRIORITY_LOW

            # Determine complexity
            if len(line) > 200:
                complexity = "high"
            elif len(line) > 80:
                complexity = "medium"
            else:
                complexity = "low"

            # Truncate title to first 100 chars
            title = line[:100]
            if len(line) > 100:
                title += "..."

            self.add_task(
                title=title,
                description=line,
                priority=priority,
                phase_type=phase_type,
                complexity=complexity,
                source=source_tag
            )
            imported += 1

        logger.info(f"[TaskBoard] Imported {imported} tasks from {file_path}")
        return imported


# ==========================================
# SINGLETON ACCESS
# ==========================================

_board_instance: Optional[TaskBoard] = None


def get_task_board() -> TaskBoard:
    """Get or create the singleton TaskBoard instance."""
    global _board_instance
    if _board_instance is None:
        _board_instance = TaskBoard()
    return _board_instance
