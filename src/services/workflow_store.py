"""
MARKER_144.1: Workflow Store — persistent storage for user-created workflow templates.

Workflows are DAG templates saved as JSON in data/workflows/.
Separate from task_board.json — different concern (template vs execution).

@phase 144
@status active
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class ValidationError:
    """Single validation issue."""
    severity: str  # "error" | "warning"
    message: str
    node_id: Optional[str] = None
    edge_id: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of workflow validation."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [asdict(e) for e in self.errors],
            "warnings": [asdict(w) for w in self.warnings],
        }


# Valid node/edge types for validation
VALID_NODE_TYPES = {"task", "agent", "subtask", "proposal", "condition", "parallel", "loop", "transform", "group"}
VALID_EDGE_TYPES = {"structural", "dataflow", "temporal", "conditional", "parallel_fork", "parallel_join", "feedback"}


class WorkflowStore:
    """
    MARKER_144.1: Persistent workflow template storage.

    Stores workflows as individual JSON files in data/workflows/.
    Each workflow is a complete DAG template with nodes, edges, and metadata.
    """

    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        self.project_root = project_root
        self.workflows_dir = project_root / "data" / "workflows"
        self.workflows_dir.mkdir(parents=True, exist_ok=True)

    def _workflow_path(self, workflow_id: str) -> Path:
        """Get file path for a workflow by ID."""
        # Sanitize ID to prevent directory traversal
        safe_id = workflow_id.replace("/", "_").replace("..", "_")
        return self.workflows_dir / f"{safe_id}.json"

    def save(self, workflow: Dict[str, Any]) -> str:
        """
        Save a workflow template. Creates new ID if not provided.

        Args:
            workflow: Workflow dict with nodes, edges, metadata.

        Returns:
            Workflow ID string.
        """
        # Generate ID if not provided
        if "id" not in workflow or not workflow["id"]:
            workflow["id"] = f"wf_{uuid.uuid4().hex[:8]}"

        wf_id = workflow["id"]
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Ensure metadata
        if "metadata" not in workflow:
            workflow["metadata"] = {}

        meta = workflow["metadata"]
        if "created_at" not in meta:
            meta["created_at"] = now
        meta["updated_at"] = now
        meta["version"] = meta.get("version", 0) + 1

        # Ensure required fields
        workflow.setdefault("name", "Untitled Workflow")
        workflow.setdefault("nodes", [])
        workflow.setdefault("edges", [])

        # Write to disk
        path = self._workflow_path(wf_id)
        path.write_text(json.dumps(workflow, indent=2, ensure_ascii=False), encoding="utf-8")

        return wf_id

    def load(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a workflow by ID.

        Returns:
            Workflow dict or None if not found.
        """
        path = self._workflow_path(workflow_id)
        if not path.exists():
            return None

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List all workflows (summary only — no nodes/edges).

        Returns:
            List of workflow summaries sorted by updated_at (newest first).
        """
        summaries = []

        for path in self.workflows_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                summaries.append({
                    "id": data.get("id", path.stem),
                    "name": data.get("name", "Untitled"),
                    "description": data.get("description", ""),
                    "node_count": len(data.get("nodes", [])),
                    "edge_count": len(data.get("edges", [])),
                    "metadata": data.get("metadata", {}),
                })
            except (json.JSONDecodeError, OSError):
                continue

        # Sort by updated_at descending
        summaries.sort(
            key=lambda w: w.get("metadata", {}).get("updated_at", ""),
            reverse=True,
        )

        return summaries

    def delete(self, workflow_id: str) -> bool:
        """
        Delete a workflow by ID.

        Returns:
            True if deleted, False if not found.
        """
        path = self._workflow_path(workflow_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def validate(self, workflow: Dict[str, Any]) -> ValidationResult:
        """
        Validate a workflow template.

        Checks:
        - Required fields present
        - Valid node/edge types
        - Edge references valid node IDs
        - No cycles (topological sort)
        - No orphan nodes (disconnected from any edge)

        Returns:
            ValidationResult with errors and warnings.
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        nodes = workflow.get("nodes", [])
        edges = workflow.get("edges", [])

        # --- Check required fields ---
        if not workflow.get("name"):
            warnings.append(ValidationError("warning", "Workflow has no name"))

        if not nodes:
            errors.append(ValidationError("error", "Workflow has no nodes"))
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        # --- Collect node IDs ---
        node_ids = set()
        for node in nodes:
            nid = node.get("id")
            if not nid:
                errors.append(ValidationError("error", "Node missing 'id' field"))
                continue
            if nid in node_ids:
                errors.append(ValidationError("error", f"Duplicate node ID: {nid}", node_id=nid))
            node_ids.add(nid)

            # Check node type
            ntype = node.get("type", "")
            if ntype not in VALID_NODE_TYPES:
                errors.append(ValidationError(
                    "error",
                    f"Invalid node type '{ntype}' (valid: {VALID_NODE_TYPES})",
                    node_id=nid,
                ))

            # Check required node fields
            if not node.get("label"):
                warnings.append(ValidationError("warning", "Node missing label", node_id=nid))

        # --- Check edges ---
        edge_ids = set()
        adjacency: Dict[str, List[str]] = {nid: [] for nid in node_ids}
        connected_nodes = set()

        for edge in edges:
            eid = edge.get("id")
            if not eid:
                errors.append(ValidationError("error", "Edge missing 'id' field"))
                continue
            if eid in edge_ids:
                errors.append(ValidationError("error", f"Duplicate edge ID: {eid}", edge_id=eid))
            edge_ids.add(eid)

            source = edge.get("source", "")
            target = edge.get("target", "")

            if source not in node_ids:
                errors.append(ValidationError(
                    "error",
                    f"Edge source '{source}' not found in nodes",
                    edge_id=eid,
                ))
            if target not in node_ids:
                errors.append(ValidationError(
                    "error",
                    f"Edge target '{target}' not found in nodes",
                    edge_id=eid,
                ))

            etype = edge.get("type", "")
            if etype and etype not in VALID_EDGE_TYPES:
                warnings.append(ValidationError(
                    "warning",
                    f"Unknown edge type '{etype}'",
                    edge_id=eid,
                ))

            # Build adjacency for cycle detection
            if source in adjacency:
                adjacency[source].append(target)

            connected_nodes.add(source)
            connected_nodes.add(target)

        # --- Cycle detection (topological sort) ---
        # Skip feedback edges (they are intentionally cyclic)
        non_feedback_adj: Dict[str, List[str]] = {nid: [] for nid in node_ids}
        for edge in edges:
            if edge.get("type") != "feedback":
                src = edge.get("source", "")
                tgt = edge.get("target", "")
                if src in non_feedback_adj:
                    non_feedback_adj[src].append(tgt)

        if node_ids and self._has_cycle(non_feedback_adj, node_ids):
            errors.append(ValidationError(
                "error",
                "Workflow contains a cycle (excluding feedback edges). "
                "Use 'feedback' edge type for intentional loops.",
            ))

        # --- Orphan nodes ---
        if edges:  # Only check if there are edges
            orphans = node_ids - connected_nodes
            for orphan in orphans:
                warnings.append(ValidationError(
                    "warning",
                    f"Orphan node '{orphan}' — not connected to any edge",
                    node_id=orphan,
                ))

        valid = len(errors) == 0
        return ValidationResult(valid=valid, errors=errors, warnings=warnings)

    def workflow_to_tasks(
        self,
        workflow: Dict[str, Any],
        preset: str = "dragon_silver",
    ) -> List[Dict[str, Any]]:
        """
        MARKER_144.10: Convert workflow nodes → TaskBoard-compatible task dicts.

        Maps node types to task properties:
        - task/subtask → build phase, priority from node data or edge position
        - agent → build phase, tagged with agent role
        - condition/proposal → research phase (needs investigation)
        - parallel → creates group marker, forks handled by dependencies
        - loop/transform/group → build phase with special tags

        Structural edges become task dependencies (parent must complete first).

        Returns:
            List of task dicts ready for TaskBoard.add_task().
        """
        nodes = workflow.get("nodes", [])
        edges = workflow.get("edges", [])

        if not nodes:
            return []

        # Build adjacency and reverse-adjacency for dependency tracking
        # node_id -> list of parent node_ids (structural edges only)
        parents: Dict[str, List[str]] = {n["id"]: [] for n in nodes}
        for edge in edges:
            if edge.get("type", "structural") in ("structural", "temporal"):
                target = edge.get("target", "")
                source = edge.get("source", "")
                if target in parents:
                    parents[target].append(source)

        # Compute topological order for priority assignment
        # Roots (no parents) get highest priority, deeper nodes get lower
        depth: Dict[str, int] = {}
        def compute_depth(nid: str, visited: set) -> int:
            if nid in depth:
                return depth[nid]
            if nid in visited:
                return 0  # Cycle guard
            visited.add(nid)
            if not parents.get(nid):
                depth[nid] = 0
                return 0
            max_parent = max(compute_depth(p, visited) for p in parents[nid])
            depth[nid] = max_parent + 1
            return depth[nid]

        for node in nodes:
            compute_depth(node["id"], set())

        # Map node types to phase_type
        PHASE_MAP = {
            "task": "build",
            "subtask": "build",
            "agent": "build",
            "condition": "research",
            "proposal": "research",
            "parallel": "build",
            "loop": "build",
            "transform": "build",
            "group": "build",
        }

        # Map depth to priority (0=P1 highest, 1=P2, 2+=P3)
        def depth_to_priority(d: int) -> int:
            if d == 0:
                return 1
            elif d == 1:
                return 2
            else:
                return 3

        # Node ID → task ID mapping (for dependency resolution later)
        node_to_task: Dict[str, str] = {}
        task_list: List[Dict[str, Any]] = []

        for node in nodes:
            nid = node.get("id", "")
            ntype = node.get("type", "task")
            label = node.get("label", "Untitled")
            data = node.get("data", {})

            # Build task description from node data
            desc_parts = []
            if data.get("description"):
                desc_parts.append(data["description"])
            if data.get("role"):
                desc_parts.append(f"Role: {data['role']}")
            if data.get("model"):
                desc_parts.append(f"Model: {data['model']}")
            desc_parts.append(f"[from workflow node {nid}, type={ntype}]")
            description = "\n".join(desc_parts)

            # Tags
            tags = [preset.split("_")[0] if "_" in preset else "dragon"]
            if ntype == "agent" and data.get("role"):
                tags.append(data["role"])
            if ntype in ("condition", "proposal"):
                tags.append("research")
            tags.append(f"wf:{workflow.get('id', 'unknown')}")

            phase_type = PHASE_MAP.get(ntype, "build")
            priority = data.get("priority", depth_to_priority(depth.get(nid, 0)))

            # Parent node IDs → will be resolved to task IDs after all tasks created
            parent_node_ids = parents.get(nid, [])

            task_dict = {
                "title": label,
                "description": description,
                "priority": priority,
                "tags": tags,
                "phase_type": phase_type,
                "preset": preset,
                "parent_node_ids": parent_node_ids,  # Temporary, resolved below
                "node_id": nid,  # For reference
                "complexity": data.get("complexity", 1),
            }
            node_to_task[nid] = nid  # Will be replaced with actual task IDs
            task_list.append(task_dict)

        # Resolve parent_node_ids → dependency list (uses node_ids for now,
        # actual task_id mapping happens at execution time when tasks are added)
        for task in task_list:
            parent_nids = task.pop("parent_node_ids", [])
            task["dependency_node_ids"] = parent_nids  # Kept for task creation order

        return task_list

    @staticmethod
    def _has_cycle(adjacency: Dict[str, List[str]], node_ids: set) -> bool:
        """
        Detect cycles using DFS coloring.
        WHITE=0 (unvisited), GRAY=1 (in progress), BLACK=2 (done).
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {nid: WHITE for nid in node_ids}

        def dfs(node: str) -> bool:
            color[node] = GRAY
            for neighbor in adjacency.get(node, []):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    return True  # Back edge = cycle
                if color[neighbor] == WHITE and dfs(neighbor):
                    return True
            color[node] = BLACK
            return False

        for nid in node_ids:
            if color[nid] == WHITE:
                if dfs(nid):
                    return True
        return False
