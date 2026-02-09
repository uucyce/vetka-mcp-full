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
VALID_STATUSES = {"pending", "queued", "running", "done", "failed", "cancelled", "hold"}

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

    def _notify_board_update(self, action: str = "update"):
        """MARKER_124.3D: Emit SocketIO event for live Task Board UI updates.

        Uses fire-and-forget HTTP POST to our own REST endpoint which has sio access.
        Falls back silently if server isn't running.
        """
        try:
            import asyncio
            summary = self.get_board_summary()

            async def _emit():
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=2.0) as client:
                        await client.post(
                            "http://localhost:5001/api/debug/task-board/notify",
                            json={"action": action, "summary": summary}
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
        source: str = "manual"
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
            "stats": None
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
    # DISPATCH
    # ==========================================

    async def dispatch_next(self, chat_id: Optional[str] = None) -> Dict[str, Any]:
        """Pick highest-priority task and dispatch to pipeline.

        Args:
            chat_id: Optional chat ID for progress streaming

        Returns:
            Dispatch result dict
        """
        task = self.get_next_task()
        if not task:
            return {"success": False, "error": "No pending tasks with satisfied dependencies"}

        return await self.dispatch_task(task["id"], chat_id=chat_id)

    async def dispatch_task(
        self,
        task_id: str,
        chat_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Dispatch a specific task to the Mycelium pipeline.

        Creates an AgentPipeline with appropriate preset based on task
        complexity and phase_type. Updates task status through lifecycle.

        Args:
            task_id: Task to dispatch
            chat_id: Optional chat ID for progress streaming

        Returns:
            Dict with success status, pipeline_task_id, and result
        """
        task = self.tasks.get(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        if task["status"] not in ("pending", "queued"):
            return {"success": False, "error": f"Task {task_id} is {task['status']}, not dispatchable"}

        # Mark as running
        self.update_task(task_id, status="running", started_at=datetime.now().isoformat())

        try:
            from src.orchestration.agent_pipeline import AgentPipeline

            # Determine preset: task-specific > phase-based > default
            preset = task.get("preset") or self.settings.get("default_preset")

            pipeline = AgentPipeline(
                chat_id=chat_id,
                auto_write=False,  # Staging mode for safety
                preset=preset
            )
            # MARKER_121.2: Tag pipeline with board task ID for callback
            pipeline._board_task_id = task_id

            # Build task description from title + description
            task_text = task["title"]
            if task.get("description") and task["description"] != task["title"]:
                task_text += f"\n\n{task['description']}"

            # Execute pipeline
            result = await pipeline.execute(task_text, task["phase_type"])

            # Update task with results
            pipeline_status = result.get("status", "unknown")
            completed = pipeline_status == "done"

            self.update_task(
                task_id,
                status="done" if completed else "failed",
                completed_at=datetime.now().isoformat(),
                pipeline_task_id=result.get("task_id"),
                assigned_tier=pipeline.preset_name,
                result_summary=str(result.get("results", {}))[:500]
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
