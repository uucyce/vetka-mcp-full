# src/transformers/phase11_transformer.py
"""
Phase 11 Transformer: Phase 9 -> VETKA-JSON v1.3.

ALL BUGS FIXED v3.1:
- BFS bottom-up for completion (Haiku #1)
- Local RNG instead of global (Haiku #3)
- Completion by branch type (Haiku #4)
- Skip entropy for leaves (Haiku #9)
- Logarithmic phylotaxis radius (Haiku #7)
- isinstance validation (Haiku #8)
- hidden_in_visualization mapping (Qwen #2)
+ Debug logging (Haiku Section 7)
+ Graceful degradation (Haiku Section 4)

@status: active
@phase: 96
@depends: math, random, logging, datetime, typing, uuid, pathlib, config.design_system
@used_by: src.transformers.__init__, src.orchestration
"""

import math
import random
import sys
import logging
import time
from datetime import datetime
from typing import Optional, List, Dict, Set
from uuid import uuid4
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.design_system import (
    AGENT_COLORS, EDGE_STYLES,
    GOLDEN_ANGLE, LAYER_HEIGHT, GRAVITY_PULL, MAX_DEVIATION,
    PROMOTE_THRESHOLDS, TEMPORAL_DECAY_TAU_DAYS
)


class Phase11Transformer:
    """Transforms Phase 9 data to VETKA-JSON v1.3."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.logger = self._setup_logger()
        self.nodes: List[Dict] = []
        self.edges: List[Dict] = []
        self._node_index = 0
        self._depth_map: Dict[str, int] = {}
        self._created_at = datetime.now()

    def _setup_logger(self) -> logging.Logger:
        """Setup logger with appropriate level."""
        logger = logging.getLogger("Phase11Transformer")
        logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '[%(levelname)s] %(message)s'
            ))
            logger.addHandler(handler)
        return logger

    def transform(self, phase9_data: dict) -> dict:
        """Main entry point with graceful degradation."""
        start_time = time.time()

        # Validate input
        if not isinstance(phase9_data, dict):
            self.logger.error("phase9_data must be a dict, creating minimal tree")
            phase9_data = {}

        # Get or generate workflow_id
        workflow_id = phase9_data.get("workflow_id")
        if not workflow_id:
            workflow_id = uuid4().hex[:8]
            self.logger.warning(f"Missing workflow_id, generated: {workflow_id}")

        self.logger.info(f"Transform started: {workflow_id}")

        # Reset state
        self.nodes = []
        self.edges = []
        self._node_index = 0
        self._depth_map = {}

        # GRACEFUL DEGRADATION: Create placeholders for missing data
        phase9_data = self._ensure_data(phase9_data)

        # Create nodes
        root_id = self._create_root_node(workflow_id)
        pm_id = self._process_pm(phase9_data.get("pm_result"), root_id)
        arch_id = self._process_architect(phase9_data.get("architect_result"), root_id)
        dev_id = self._process_dev(phase9_data.get("dev_result"), root_id)
        qa_id = self._process_qa(phase9_data.get("qa_result"), root_id)
        arc_ids = self._process_arc(phase9_data.get("arc_suggestions", []), root_id)

        # Create edges
        self._create_edges(root_id, pm_id, arch_id, dev_id, qa_id, arc_ids)

        # Post-process (ORDER CRITICAL - DO NOT CHANGE)
        self._update_children_ids()              # 1. Build tree structure
        self._calculate_completion_rates_bfs()   # 2. BFS bottom-up (FIXED)
        self._calculate_entropy_and_visuals()    # 3. Use completion rates
        self._check_promote_triggers()           # 4. Final checks

        elapsed = time.time() - start_time
        self.logger.info(f"Completed: {len(self.nodes)} nodes, {len(self.edges)} edges in {elapsed:.3f}s")

        # Build output
        return {
            "$schema": "https://vetka.io/schema/v1.3.json",
            "format": "vetka-v1.3",
            "version": "1.3",
            "origin": {
                "source": phase9_data.get("source", "phase9"),
                "workflow_id": workflow_id
            },
            "created_at": self._created_at.isoformat(),
            "tree": {
                "id": f"tree_{workflow_id}",
                "name": f"Workflow {workflow_id}",
                "root_node_id": root_id,
                "nodes": self.nodes,
                "edges": self.edges,
                "promote_events": [],
                "metadata": self._calc_tree_metadata()
            }
        }

    def _ensure_data(self, data: dict) -> dict:
        """GRACEFUL DEGRADATION: Create placeholders for missing data."""
        if not data.get("pm_result"):
            self.logger.warning("Missing pm_result, creating placeholder")
            data["pm_result"] = {"plan": "No PM plan available", "eval_score": 0.5}

        if not data.get("architect_result"):
            self.logger.warning("Missing architect_result, creating placeholder")
            data["architect_result"] = {"description": "No architecture", "eval_score": 0.5}

        if not data.get("dev_result"):
            self.logger.warning("Missing dev_result, creating placeholder")
            data["dev_result"] = {"files": [], "eval_score": 0.5}

        if not data.get("qa_result"):
            self.logger.warning("Missing qa_result, creating placeholder")
            data["qa_result"] = {"tests": [], "passed": 0, "failed": 0, "eval_score": 0.5}

        return data

    def _clamp_eval_score(self, score) -> float:
        """Clamp eval_score to [0, 1] range with validation."""
        try:
            score = float(score)
        except (TypeError, ValueError):
            self.logger.warning(f"Invalid eval_score '{score}', using 0.5")
            return 0.5

        if score < 0 or score > 1:
            self.logger.warning(f"eval_score {score} out of range, clamping to [0,1]")
            return max(0.0, min(1.0, score))
        return score

    # ═══════════════════════════════════════════════════════════════
    # NODE CREATION (with validation)
    # ═══════════════════════════════════════════════════════════════

    def _create_root_node(self, workflow_id: str) -> str:
        node_id = f"root_{workflow_id}"
        self._depth_map[node_id] = 0

        self.nodes.append(self._build_node(
            node_id=node_id,
            parent_id=None,
            name=f"Workflow {workflow_id}",
            node_type="root",
            branch_type="memory",
            agent="System",
            content={"type": "workflow", "data": {"workflow_id": workflow_id}},
            eval_score=1.0,
            depth=0
        ))
        self.logger.debug(f"Created root: {node_id}")
        return node_id

    def _process_pm(self, result: Optional[dict], parent_id: str) -> Optional[str]:
        # FIXED: isinstance validation (Haiku #8)
        if not result or not isinstance(result, dict):
            return None

        eval_score = self._clamp_eval_score(result.get("eval_score", 0.8))
        node_id = self._create_branch(
            parent_id, "PM Plan", "memory", "PM",
            {"type": "text", "data": result, "preview": str(result.get("plan", ""))[:100]},
            eval_score
        )
        self.logger.debug(f"Created PM: {node_id} (eval_score={eval_score})")
        return node_id

    def _process_architect(self, result: Optional[dict], parent_id: str) -> Optional[str]:
        if not result or not isinstance(result, dict):
            return None

        eval_score = self._clamp_eval_score(result.get("eval_score", result.get("score", 0.8)))
        node_id = self._create_branch(
            parent_id, "Architecture", "memory", "PM",
            {"type": "diagram", "data": result, "preview": str(result.get("description", ""))[:100]},
            eval_score
        )
        self.logger.debug(f"Created Architect: {node_id} (eval_score={eval_score})")
        return node_id

    def _process_dev(self, result: Optional[dict], parent_id: str) -> Optional[str]:
        if not result or not isinstance(result, dict):
            return None

        files = result.get("files", [])
        if not isinstance(files, list):
            files = []

        eval_score = self._clamp_eval_score(result.get("eval_score", 0.8))
        dev_id = self._create_branch(
            parent_id, "Development", "task", "Dev",
            {"type": "code", "data": {"files_count": len(files)}, "preview": f"{len(files)} files"},
            eval_score
        )
        self.logger.debug(f"Created Dev: {dev_id} with {len(files)} files")

        # Create file leaves (with validation)
        for f in files:
            if not isinstance(f, dict):
                continue  # FIXED: skip invalid entries
            self._create_leaf(
                dev_id, f.get("name", "file"),
                {"type": "code", "data": f, "preview": f"{f.get('language', 'unknown')} file"},
                "Dev"
            )
        return dev_id

    def _process_qa(self, result: Optional[dict], parent_id: str) -> Optional[str]:
        if not result or not isinstance(result, dict):
            return None

        tests = result.get("tests", [])
        if not isinstance(tests, list):
            tests = []

        qa_id = self._create_branch(
            parent_id, "Quality Assurance", "task", "QA",
            {
                "type": "metrics",
                "data": {"passed": result.get("passed", 0), "failed": result.get("failed", 0)},
                "preview": f"Tests: {result.get('passed', 0)}/{result.get('passed', 0) + result.get('failed', 0)}"
            },
            result.get("eval_score", 0.8)
        )

        for test in tests:
            if not isinstance(test, str):
                continue
            self._create_leaf(
                qa_id, test,
                {"type": "code", "data": {"test_name": test}, "preview": "Test file"},
                "QA"
            )
        return qa_id

    def _process_arc(self, suggestions: list, parent_id: str) -> List[str]:
        arc_ids = []
        if not isinstance(suggestions, list):
            return arc_ids

        for s in suggestions:
            if not isinstance(s, dict):
                continue
            node_id = self._create_branch(
                parent_id, s.get("transformation", "Suggestion"), "control", "ARC",
                {"type": "text", "data": s, "preview": str(s.get("transformation", ""))[:50]},
                s.get("success", 0.8),
                hidden=True
            )
            arc_ids.append(node_id)
        return arc_ids

    def _create_branch(
        self, parent_id: str, name: str, branch_type: str, agent: str,
        content: dict, eval_score: float, hidden: bool = False
    ) -> str:
        node_id = f"{branch_type}_{uuid4().hex[:8]}"
        depth = self._depth_map.get(parent_id, 0) + 1
        self._depth_map[node_id] = depth

        self.nodes.append(self._build_node(
            node_id, parent_id, name, "branch", branch_type, agent,
            content, eval_score, depth, hidden
        ))
        self._node_index += 1
        return node_id

    def _create_leaf(self, parent_id: str, name: str, content: dict, agent: str) -> str:
        node_id = f"leaf_{uuid4().hex[:8]}"
        depth = self._depth_map.get(parent_id, 0) + 1
        self._depth_map[node_id] = depth

        self.nodes.append(self._build_node(
            node_id, parent_id, name, "leaf", "data", agent,
            content, 1.0, depth  # Leaves always "complete"
        ))
        self._node_index += 1
        return node_id

    def _build_node(
        self, node_id: str, parent_id: Optional[str], name: str,
        node_type: str, branch_type: str, agent: str, content: dict,
        eval_score: float, depth: int, hidden: bool = False
    ) -> dict:
        """Build node structure."""
        return {
            "id": node_id,
            "parent_id": parent_id,
            "type": node_type,
            "branch_type": branch_type,
            "name": name,
            "content": content,
            "metadata": {
                "agent": agent,
                "eval_score": eval_score,
                "entropy": 0.0,
                "completion_rate": 0.0,
                "timestamp": self._created_at.isoformat(),
                "version": 1,
                "supersedes": None,
                "version_intent": "create",
                # FIXED: correct field name for JS (Qwen #2)
                "hidden_in_visualization": hidden,
                "provenance": {"field": branch_type, "confidence": 0.95}
            },
            "visual_hints": {
                "size_multiplier": 1.0,
                "color": AGENT_COLORS.get(agent, "#6B7280"),
                "opacity": 0.2,
                "animation": "static",
                "icon": self._get_icon(branch_type),
                "layout_hint": self._calc_layout(depth, self._node_index)
            },
            "lod_hints": {
                "forest": {"visible": not hidden, "show_label": False},
                "tree": {"visible": not hidden, "show_label": True},
                "branch": {"visible": True, "show_content": True}
            },
            "promote_triggers": {
                "node_count": {"threshold": PROMOTE_THRESHOLDS["node_count"], "current": 0},
                "entropy": {"threshold": PROMOTE_THRESHOLDS["entropy"], "current": 0.0},
                "depth": {"threshold": PROMOTE_THRESHOLDS["depth"], "current": depth},
                "ready_to_promote": False
            },
            "children_ids": []
        }

    # ═══════════════════════════════════════════════════════════════
    # EDGE CREATION
    # ═══════════════════════════════════════════════════════════════

    def _create_edges(self, root_id, pm_id, arch_id, dev_id, qa_id, arc_ids):
        # Root → branches: "creates" (FINAL DECISION)
        for branch_id in [pm_id, arch_id, dev_id, qa_id]:
            if branch_id:
                self.edges.append(self._make_edge(root_id, branch_id, "root", "creates", 1.0))

        for arc_id in arc_ids:
            self.edges.append(self._make_edge(root_id, arc_id, "control", "creates", 0.5))

        if pm_id and dev_id:
            self.edges.append(self._make_edge(pm_id, dev_id, "liana", "informs", 0.6))
        if pm_id and qa_id:
            self.edges.append(self._make_edge(pm_id, qa_id, "liana", "informs", 0.5))
        if arch_id and dev_id:
            self.edges.append(self._make_edge(arch_id, dev_id, "liana", "influences", 0.8))
        if dev_id and qa_id:
            self.edges.append(self._make_edge(qa_id, dev_id, "liana", "depends", 0.8))

        for arc_id in arc_ids:
            if dev_id:
                self.edges.append(self._make_edge(arc_id, dev_id, "control", "controls", 0.7))

    def _make_edge(self, from_id: str, to_id: str, edge_type: str, semantics: str, weight: float) -> dict:
        style = EDGE_STYLES.get(semantics, EDGE_STYLES["informs"])
        return {
            "id": f"edge_{from_id}_{to_id}",
            "from": from_id,
            "to": to_id,
            "type": edge_type,
            "semantics": semantics,
            "direction": "forward",
            "flow_weight": weight,
            "created_at": self._created_at.isoformat(),
            "visual_hints": {
                "thickness": style["thickness"],
                "color": style["color"],
                "style": style["style"],
                "curvature": 0.3,
                "arrow_type": style.get("arrow")
            }
        }

    # ═══════════════════════════════════════════════════════════════
    # FORMULAS (ALL FIXED)
    # ═══════════════════════════════════════════════════════════════

    def _calc_entropy_shannon(self, children: list) -> float:
        """Pure Shannon entropy (Theory 6.1, no normalization)."""
        if not children:
            return 0.0
        scores = [c["metadata"]["eval_score"] for c in children]
        total = sum(scores)
        if total == 0:
            return 0.0
        probs = [s / total for s in scores]
        return round(-sum(p * math.log2(p) for p in probs if p > 0), 3)

    def _entropy_to_visual(self, entropy: float) -> float:
        """Convert entropy to 0-1 range."""
        return min(1.0, entropy / 4.0)

    def _calc_completion_by_type(self, node: dict, children: list) -> float:
        """
        FIXED: Completion based on branch type (Haiku #4, Theory 4.2).
        - Leaves: 1.0 (they exist)
        - With children: average of children
        - Without children: depends on branch_type
        """
        # Accept both "leaf" and "file" types
        if node["type"] in ["leaf", "file"]:
            return 1.0

        if children:
            child_completions = [c["metadata"]["completion_rate"] for c in children]
            return round(sum(child_completions) / len(child_completions), 2)

        # No children - depends on branch type
        branch_type = node["branch_type"]
        eval_score = node["metadata"]["eval_score"]

        if branch_type == "memory":
            # Memory = plans, complete if eval_score > 0.7
            return 1.0 if eval_score > 0.7 else 0.5
        elif branch_type == "task":
            # Task without children = not started
            return 0.0
        elif branch_type == "data":
            # Data = artifacts, always complete
            return 1.0
        else:  # control
            # Control = never "complete"
            return 0.0

    def _calc_opacity(self, completion_rate: float) -> float:
        """Theory 4.2: opacity = 0.2 + completion × 0.8"""
        return round(0.2 + completion_rate * 0.8, 2)

    def _calc_animation(self, entropy: float, completion: float, branch_type: str) -> str:
        if branch_type == "task" and completion < 1.0:
            return "pulse"
        elif entropy > 0.7:
            return "glow"
        elif completion < 0.3:
            return "flicker"
        return "static"

    def _calc_layout(self, depth: int, index: int) -> dict:
        """
        Phylotaxis 3D layout (Theory 3.2).
        FIXED: Logarithmic radius growth (Haiku #7)
        FIXED: Local RNG (Haiku #3)
        """
        theta = index * GOLDEN_ANGLE
        theta_rad = math.radians(theta)

        # FIXED: Logarithmic radius (more natural)
        radius = LAYER_HEIGHT * (1 + math.log(depth + 2))

        # 3D coordinates
        expected_x = math.cos(theta_rad) * radius
        expected_z = math.sin(theta_rad) * radius
        expected_y = depth * LAYER_HEIGHT

        # FIXED: Local RNG (not global)
        rng = random.Random(index * 1000 + depth)
        deviation_x = rng.gauss(0, MAX_DEVIATION * (1 - GRAVITY_PULL))
        deviation_z = rng.gauss(0, MAX_DEVIATION * (1 - GRAVITY_PULL))

        return {
            "depth": depth,
            "index": index,
            "theta": round(theta % 360, 2),
            "expected_x": round(expected_x + deviation_x, 2),
            "expected_y": expected_y,
            "expected_z": round(expected_z + deviation_z, 2),
            "radius": round(radius, 2)
        }

    def _get_icon(self, branch_type: str) -> str:
        return {"memory": "document", "task": "code", "data": "file", "control": "suggestion"}.get(branch_type, "circle")

    # ═══════════════════════════════════════════════════════════════
    # POST-PROCESSING (ORDER CRITICAL)
    # ═══════════════════════════════════════════════════════════════

    def _update_children_ids(self):
        """Compute children_ids from parent_id."""
        for node in self.nodes:
            node["children_ids"] = [
                n["id"] for n in self.nodes
                if n.get("parent_id") == node["id"]
            ]

    def _calculate_completion_rates_bfs(self):
        """
        FIXED: BFS bottom-up traversal (Haiku #1).
        Process from leaves up to root.
        """
        visited: Set[str] = set()

        def calc_bottom_up(node_id: str):
            if node_id in visited:
                return

            node = next((n for n in self.nodes if n["id"] == node_id), None)
            if not node:
                return

            # First: process all children (recursively)
            children = [n for n in self.nodes if n.get("parent_id") == node_id]
            for child in children:
                calc_bottom_up(child["id"])

            # Then: calculate completion for this node
            completion = self._calc_completion_by_type(node, children)
            node["metadata"]["completion_rate"] = completion
            node["visual_hints"]["opacity"] = self._calc_opacity(completion)

            visited.add(node_id)

        # Start from root
        root = next((n for n in self.nodes if n["type"] == "root"), None)
        if root:
            calc_bottom_up(root["id"])

    def _calculate_entropy_and_visuals(self):
        """Calculate entropy and update visual hints."""
        for node in self.nodes:
            # FIXED: Skip leaves (Haiku #9) - accept both "leaf" and "file"
            if node["type"] in ["leaf", "file"]:
                node["metadata"]["entropy"] = 0.0
                continue

            children = [n for n in self.nodes if n.get("parent_id") == node["id"]]
            entropy = self._calc_entropy_shannon(children)

            node["metadata"]["entropy"] = entropy
            node["visual_hints"]["size_multiplier"] = 1.0 + self._entropy_to_visual(entropy) * 0.5
            node["visual_hints"]["animation"] = self._calc_animation(
                entropy, node["metadata"]["completion_rate"], node["branch_type"]
            )
            node["promote_triggers"]["entropy"]["current"] = entropy

    def _check_promote_triggers(self):
        """Check if nodes are ready to promote."""
        for node in self.nodes:
            triggers = node["promote_triggers"]
            triggers["node_count"]["current"] = len(node["children_ids"])

            ready = (
                triggers["node_count"]["current"] > triggers["node_count"]["threshold"] or
                triggers["entropy"]["current"] > triggers["entropy"]["threshold"] or
                triggers["depth"]["current"] > triggers["depth"]["threshold"]
            )
            triggers["ready_to_promote"] = ready

    def _calc_tree_metadata(self) -> dict:
        """Calculate tree-level metadata."""
        depths = list(self._depth_map.values())
        completions = [n["metadata"]["completion_rate"] for n in self.nodes]

        root = next((n for n in self.nodes if n["type"] == "root"), None)
        root_children = [n for n in self.nodes if n.get("parent_id") == root["id"]] if root else []

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "max_depth": max(depths) if depths else 0,
            "completion_rate": round(sum(completions) / len(completions), 2) if completions else 0,
            "tree_entropy": self._calc_entropy_shannon(root_children),
            "agent_views": {
                "PM": {"view_level": "FOREST", "max_depth": 3},
                "Dev": {"view_level": "BRANCH", "max_depth": 10},
                "QA": {"view_level": "BRANCH", "max_depth": 5},
                "ARC": {"view_level": "TREE", "max_depth": 7}
            }
        }
