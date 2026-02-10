"""
MARKER_135.2A: DAG Aggregator — Build DAG from MCC data sources.
Aggregates Task Board, Pipeline results, and Feedback into unified DAG.

@phase 135.2
@status active
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Literal
from pathlib import Path
from datetime import datetime, timedelta
import json


# Type aliases
NodeType = Literal["task", "agent", "subtask", "proposal"]
NodeStatus = Literal["pending", "running", "done", "failed"]
EdgeType = Literal["structural", "dataflow", "temporal"]
AgentRole = Literal["scout", "architect", "researcher", "coder", "verifier"]


@dataclass
class DAGNode:
    """Node in the DAG graph."""

    id: str
    type: NodeType
    label: str
    status: NodeStatus
    layer: int  # 0=task, 1=agents, 2-3=subtasks, 4=proposals
    task_id: str  # Root task reference

    # Optional metadata
    parent_id: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_s: Optional[float] = None
    tokens: Optional[int] = None
    model: Optional[str] = None
    confidence: Optional[float] = None
    role: Optional[AgentRole] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class DAGEdge:
    """Edge connecting two nodes."""

    id: str
    source: str
    target: str
    type: EdgeType
    strength: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DAGStats:
    """Aggregate statistics."""

    total_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    success_rate: float = 0.0
    total_agents: int = 0
    total_subtasks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DAGResponse:
    """Full DAG response for API."""

    nodes: List[DAGNode] = field(default_factory=list)
    edges: List[DAGEdge] = field(default_factory=list)
    root_ids: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "root_ids": self.root_ids,
            "stats": self.stats,
        }


class TaskBoard:
    """Minimal TaskBoard interface for DAG aggregator."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.task_board_path = data_dir / "task_board.json"

    def list_tasks(self) -> List[Dict[str, Any]]:
        """Load tasks from task_board.json."""
        if not self.task_board_path.exists():
            return []

        try:
            with open(self.task_board_path, "r") as f:
                data = json.load(f)
                return data.get("tasks", [])
        except (json.JSONDecodeError, IOError):
            return []


class DAGAggregator:
    """
    MARKER_135.2A: Build DAG from existing MCC data sources.

    Sources:
    - Task Board (task_board.json) → Layer 0 (root tasks)
    - Pipeline results (task["result"]) → Layers 1-3 (agents, subtasks)
    - Proposals/Artifacts → Layer 4
    """

    def __init__(self, project_root: Path = None):
        if project_root is None:
            # Phase 134 CWD fix: always use absolute paths
            project_root = Path(__file__).resolve().parent.parent.parent

        self.project_root = project_root
        self.data_dir = project_root / "data"
        self.task_board = TaskBoard(self.data_dir)

    def build_dag(self, filters: Dict[str, Any] = None) -> DAGResponse:
        """
        Build unified DAG from all data sources.

        Args:
            filters: Optional filters
                - status: "running" | "done" | "failed" | "pending" | None
                - time_range: "1h" | "6h" | "24h" | "all" | None
                - task_id: Specific task ID to get tree for

        Returns:
            DAGResponse with nodes, edges, root_ids, and stats
        """
        filters = filters or {}
        nodes: List[DAGNode] = []
        edges: List[DAGEdge] = []
        edge_counter = 0

        # Load all tasks
        all_tasks = self.task_board.list_tasks()

        # Apply filters
        tasks = self._apply_filters(all_tasks, filters)

        # Stats counters
        stats = DAGStats()

        for task in tasks:
            task_id = task.get("id", "unknown")
            node_id = f"task_{task_id}"

            # Layer 0: Task node
            task_node = DAGNode(
                id=node_id,
                type="task",
                label=task.get("title", "Untitled")[:50],
                status=self._normalize_status(task.get("status", "pending")),
                layer=0,
                task_id=task_id,
                started_at=task.get("started_at"),
                completed_at=task.get("completed_at"),
                description=task.get("description"),
            )
            nodes.append(task_node)

            # Update stats
            stats.total_tasks += 1
            if task_node.status == "running":
                stats.running_tasks += 1
            elif task_node.status == "done":
                stats.completed_tasks += 1
            elif task_node.status == "failed":
                stats.failed_tasks += 1

            # Process pipeline result if present
            result = task.get("result")
            if result and isinstance(result, dict):
                # Layer 1: Agent nodes
                agents_data = result.get("agents", {})
                for role, agent_info in agents_data.items():
                    if not isinstance(agent_info, dict):
                        continue

                    agent_node_id = f"agent_{task_id}_{role}"
                    agent_node = DAGNode(
                        id=agent_node_id,
                        type="agent",
                        label=f"@{role}",
                        status=self._normalize_status(agent_info.get("status", "pending")),
                        layer=1,
                        task_id=task_id,
                        parent_id=node_id,
                        role=role,
                        model=agent_info.get("model"),
                        duration_s=agent_info.get("duration_s"),
                        confidence=agent_info.get("confidence"),
                    )
                    nodes.append(agent_node)
                    stats.total_agents += 1

                    # Edge: task → agent
                    edge_counter += 1
                    edges.append(
                        DAGEdge(
                            id=f"e_{edge_counter}",
                            source=node_id,
                            target=agent_node_id,
                            type="structural",
                            strength=0.8,
                        )
                    )

                # Layer 2: Subtask nodes
                subtasks = result.get("subtasks", [])
                coder_id = f"agent_{task_id}_coder"

                for idx, subtask in enumerate(subtasks):
                    if not isinstance(subtask, dict):
                        continue

                    subtask_node_id = f"sub_{task_id}_{idx}"
                    subtask_node = DAGNode(
                        id=subtask_node_id,
                        type="subtask",
                        label=subtask.get("description", f"Subtask {idx}")[:40],
                        status=self._normalize_status(subtask.get("status", "pending")),
                        layer=2,
                        task_id=task_id,
                        parent_id=coder_id,
                        tokens=subtask.get("tokens_used"),
                    )
                    nodes.append(subtask_node)
                    stats.total_subtasks += 1

                    # Edge: coder → subtask
                    edge_counter += 1
                    edges.append(
                        DAGEdge(
                            id=f"e_{edge_counter}",
                            source=coder_id,
                            target=subtask_node_id,
                            type="dataflow",
                            strength=0.7,
                        )
                    )

                    # Edge: subtask → verifier (temporal)
                    verifier_id = f"agent_{task_id}_verifier"
                    if any(n.id == verifier_id for n in nodes):
                        edge_counter += 1
                        edges.append(
                            DAGEdge(
                                id=f"e_{edge_counter}",
                                source=subtask_node_id,
                                target=verifier_id,
                                type="temporal",
                                strength=0.6,
                            )
                        )

        # Calculate success rate
        if stats.total_tasks > 0:
            stats.success_rate = round(
                (stats.completed_tasks / stats.total_tasks) * 100, 1
            )

        # Root IDs = all task nodes
        root_ids = [n.id for n in nodes if n.type == "task"]

        return DAGResponse(
            nodes=nodes,
            edges=edges,
            root_ids=root_ids,
            stats=stats.to_dict(),
        )

    def _apply_filters(
        self, tasks: List[Dict], filters: Dict[str, Any]
    ) -> List[Dict]:
        """Apply filters to task list."""
        result = tasks

        # Filter by status
        status_filter = filters.get("status")
        if status_filter and status_filter != "all":
            result = [t for t in result if t.get("status") == status_filter]

        # Filter by task_id
        task_id_filter = filters.get("task_id")
        if task_id_filter:
            result = [t for t in result if t.get("id") == task_id_filter]

        # Filter by time range
        time_range = filters.get("time_range")
        if time_range and time_range != "all":
            now = datetime.now()
            hours_map = {"1h": 1, "6h": 6, "24h": 24}
            hours = hours_map.get(time_range, 24)
            cutoff = now - timedelta(hours=hours)

            filtered = []
            for t in result:
                created_at = t.get("created_at")
                if created_at:
                    try:
                        task_time = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00")
                        )
                        # Make naive for comparison
                        if task_time.tzinfo:
                            task_time = task_time.replace(tzinfo=None)
                        if task_time >= cutoff:
                            filtered.append(t)
                    except (ValueError, TypeError):
                        filtered.append(t)  # Include if can't parse
                else:
                    filtered.append(t)  # Include if no timestamp
            result = filtered

        return result

    def _normalize_status(self, status: str) -> NodeStatus:
        """Normalize status string to valid NodeStatus."""
        status_map = {
            "pending": "pending",
            "running": "running",
            "in_progress": "running",
            "done": "done",
            "completed": "done",
            "success": "done",
            "failed": "failed",
            "error": "failed",
        }
        return status_map.get(status.lower(), "pending")

    def get_node_detail(self, node_id: str) -> Optional[DAGNode]:
        """Get detailed info for a specific node."""
        dag = self.build_dag()
        for node in dag.nodes:
            if node.id == node_id:
                return node
        return None
