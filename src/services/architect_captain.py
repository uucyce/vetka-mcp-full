"""
MARKER_153.7A: Architect Captain — strategic recommendation engine.

Analyzes roadmap state + task history to recommend what to work on next.
Static heuristic first; LLM-powered recommendations in future phases.

Flow:
  1. Load roadmap DAG (nodes + edges)
  2. Check task board for completed/failed/pending tasks
  3. Find next actionable module (all dependencies satisfied)
  4. Recommend with reason + workflow + team preset

@phase 153
@wave 7
@status active
"""

import os
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

from src.services.roadmap_generator import RoadmapDAG
import src.services.roadmap_generator as _rg_module
from src.services.architect_prefetch import (
    WorkflowTemplateLibrary,
    ArchitectPrefetch,
)

logger = logging.getLogger(__name__)

# ── Task board path ──
TASK_BOARD_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'task_board.json')


@dataclass
class Recommendation:
    """A single task recommendation from the Architect Captain."""
    module_id: str           # Roadmap node ID
    module_label: str        # Human-readable label
    task_title: str          # Suggested task title
    description: str         # What to do and why
    priority: int            # 1-5 (1=highest)
    workflow_id: str         # Best workflow template key
    preset: str              # Team preset (dragon_bronze/silver/gold)
    reason: str              # Why this module next
    confidence: float = 0.8  # How confident (0-1)
    alternatives: List[str] = field(default_factory=list)  # Other options


@dataclass
class CaptainState:
    """Persistent captain state: what was recommended, accepted, rejected."""
    last_recommendation: Optional[Dict] = None
    accepted_count: int = 0
    rejected_count: int = 0
    completed_modules: List[str] = field(default_factory=list)


class ArchitectCaptain:
    """
    Strategic recommendation engine for Mycelium Matryoshka.

    Analyzes project roadmap + task history to recommend next actions.
    Static heuristic-based (no LLM calls needed — fast, deterministic).
    """

    # ── Status → priority mapping ──
    STATUS_PRIORITY = {
        'active': 1,      # Currently active — highest priority to continue
        'pending': 2,     # Not started — next in line
        'completed': 99,  # Done — skip
    }

    # ── Layer → complexity estimate ──
    LAYER_COMPLEXITY = {
        'core': 7,
        'feature': 5,
        'enhancement': 3,
        'test': 4,
        'docs': 2,
    }

    # ── Layer → task type mapping ──
    LAYER_TASK_TYPE = {
        'core': 'build',
        'feature': 'build',
        'enhancement': 'build',
        'test': 'test',
        'docs': 'docs',
    }

    @staticmethod
    def load_roadmap() -> Optional[RoadmapDAG]:
        """Load current roadmap from disk."""
        return RoadmapDAG.load(_rg_module.ROADMAP_PATH)

    @staticmethod
    def load_task_board() -> Dict[str, Any]:
        """Load task board state."""
        try:
            if os.path.exists(TASK_BOARD_PATH):
                with open(TASK_BOARD_PATH, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"[Captain] Failed to load task board: {e}")
        return {"tasks": [], "settings": {}}

    @classmethod
    def get_completed_modules(cls, roadmap: RoadmapDAG, board: Dict) -> set:
        """Find which roadmap modules have completed tasks."""
        completed = set()
        raw_tasks = board.get("tasks", [])
        tasks: List[Dict[str, Any]] = []

        # Support both board formats:
        # - {"tasks": [ {...}, {...} ]}
        # - {"tasks": {"id1": {...}, "id2": {...}}}
        if isinstance(raw_tasks, dict):
            tasks = [t for t in raw_tasks.values() if isinstance(t, dict)]
        elif isinstance(raw_tasks, list):
            tasks = [t for t in raw_tasks if isinstance(t, dict)]

        for task in tasks:
            status = task.get("status", "")
            if status in ("done", "completed"):
                # Try to match task to roadmap module
                title = (task.get("title", "") + " " + task.get("description", "")).lower()
                for node in roadmap.nodes:
                    node_label = node.get("label", "").lower()
                    node_id = node.get("id", "").lower()
                    if node_id in title or node_label in title:
                        completed.add(node.get("id"))

        # Also mark nodes with status=completed in the roadmap itself
        for node in roadmap.nodes:
            if node.get("data", {}).get("status") == "completed" or node.get("status") == "completed":
                completed.add(node.get("id"))

        return completed

    @classmethod
    def get_dependencies_satisfied(cls, node_id: str, roadmap: RoadmapDAG, completed: set) -> bool:
        """Check if all dependencies of a node are satisfied."""
        for edge in roadmap.edges:
            # Edge: source → target means target depends on source
            if edge.get("target") == node_id:
                source = edge.get("source")
                if source not in completed:
                    return False
        return True

    @classmethod
    def rank_candidates(
        cls,
        roadmap: RoadmapDAG,
        completed: set,
    ) -> List[Dict]:
        """
        Rank roadmap nodes by actionability.

        Scoring:
        - Active nodes get highest priority (continue what's started)
        - Pending nodes with all deps satisfied are next
        - Lower layer complexity = earlier (quick wins)
        """
        candidates = []

        for node in roadmap.nodes:
            node_id = node.get("id", "")
            if node_id in completed:
                continue

            status = node.get("data", {}).get("status", node.get("status", "pending"))
            if status == "completed":
                continue

            # Check dependencies
            deps_ok = cls.get_dependencies_satisfied(node_id, roadmap, completed)
            if not deps_ok:
                continue

            layer = node.get("data", {}).get("layer", node.get("layer", "feature"))
            complexity = cls.LAYER_COMPLEXITY.get(layer, 5)
            status_priority = cls.STATUS_PRIORITY.get(status, 3)

            score = status_priority * 10 + complexity
            candidates.append({
                "node": node,
                "score": score,
                "layer": layer,
                "complexity": complexity,
                "status": status,
                "deps_satisfied": True,
            })

        # Sort: lower score = higher priority
        candidates.sort(key=lambda c: c["score"])
        return candidates

    @classmethod
    def recommend_next(
        cls,
        roadmap: Optional[RoadmapDAG] = None,
        board: Optional[Dict] = None,
    ) -> Optional[Recommendation]:
        """
        Main entry point: recommend next task based on project state.

        1. Load roadmap + task board
        2. Find completed modules
        3. Rank remaining candidates
        4. Return top recommendation with reason
        """
        if roadmap is None:
            roadmap = cls.load_roadmap()
        if roadmap is None or len(roadmap.nodes) == 0:
            return None

        if board is None:
            board = cls.load_task_board()

        completed = cls.get_completed_modules(roadmap, board)
        candidates = cls.rank_candidates(roadmap, completed)

        if not candidates:
            # All modules completed or no candidates
            return None

        top = candidates[0]
        node = top["node"]
        layer = top["layer"]
        complexity = top["complexity"]

        # Select workflow and team
        task_type = cls.LAYER_TASK_TYPE.get(layer, "build")
        WorkflowTemplateLibrary.load_all()
        workflow_id = WorkflowTemplateLibrary.select_workflow(task_type, complexity)

        # Select team preset based on complexity
        if complexity <= 3:
            preset = "dragon_bronze"
        elif complexity <= 6:
            preset = "dragon_silver"
        else:
            preset = "dragon_gold"

        # Build reason
        reason_parts = []
        if top["status"] == "active":
            reason_parts.append(f"Module '{node.get('label')}' is already active — continue work")
        else:
            reason_parts.append(f"Module '{node.get('label')}' has all dependencies satisfied")

        if len(completed) > 0:
            reason_parts.append(f"{len(completed)} module(s) already completed")

        if len(candidates) > 1:
            alt_names = [c["node"].get("label", c["node"].get("id")) for c in candidates[1:3]]
            reason_parts.append(f"alternatives: {', '.join(alt_names)}")

        # Build recommendation
        alternatives = [c["node"].get("id") for c in candidates[1:4]]

        return Recommendation(
            module_id=node.get("id", ""),
            module_label=node.get("label", node.get("id", "")),
            task_title=f"Implement {node.get('label', node.get('id', ''))} module",
            description=node.get("data", {}).get("description", node.get("description", "")),
            priority=min(top["score"] // 10, 5),
            workflow_id=workflow_id,
            preset=preset,
            reason=". ".join(reason_parts),
            confidence=0.85 if top["status"] == "active" else 0.7,
            alternatives=alternatives,
        )

    @classmethod
    def accept_recommendation(cls, recommendation: Recommendation) -> Dict:
        """
        Accept a recommendation: prepare prefetch context for execution.

        Returns dict ready for pipeline dispatch.
        """
        return {
            "ok": True,
            "task_title": recommendation.task_title,
            "module_id": recommendation.module_id,
            "workflow_id": recommendation.workflow_id,
            "preset": recommendation.preset,
            "description": recommendation.description,
            "priority": recommendation.priority,
        }

    @classmethod
    def reject_recommendation(cls, recommendation: Recommendation) -> Dict:
        """
        Reject a recommendation: return alternatives.
        """
        return {
            "ok": True,
            "rejected": recommendation.module_id,
            "alternatives": recommendation.alternatives,
            "message": f"Rejected '{recommendation.module_label}'. "
                       f"Try: {', '.join(recommendation.alternatives) if recommendation.alternatives else 'no alternatives'}",
        }

    @classmethod
    def get_progress(cls, roadmap: Optional[RoadmapDAG] = None, board: Optional[Dict] = None) -> Dict:
        """
        Return overall project progress based on roadmap.
        """
        if roadmap is None:
            roadmap = cls.load_roadmap()
        if roadmap is None:
            return {"total": 0, "completed": 0, "active": 0, "pending": 0, "percent": 0}

        if board is None:
            board = cls.load_task_board()

        completed = cls.get_completed_modules(roadmap, board)
        total = len(roadmap.nodes)
        active_count = sum(
            1 for n in roadmap.nodes
            if n.get("data", {}).get("status") == "active" or n.get("status") == "active"
        )

        return {
            "total": total,
            "completed": len(completed),
            "active": active_count,
            "pending": total - len(completed) - active_count,
            "percent": round(len(completed) / total * 100, 1) if total > 0 else 0,
            "completed_ids": list(completed),
        }
