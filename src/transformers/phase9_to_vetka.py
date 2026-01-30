"""
VETKA Phase 9 -> Phase 10 Transformer.

Transforms Phase 9 workflow output into VETKA-JSON v1.3 format
for 3D visualization in Phase 10 UI (Three.js).

Specification: VETKA-JSON v1.3 Unified
Principle: "ПРИРАСТАЕТ, НЕ ЛОМАЕТСЯ"

Author: AI Council + Opus 4.5
Date: December 13, 2025

@status: active
@phase: 96
@depends: enum, typing, datetime, uuid, colorsys, math, random, logging
@used_by: src.transformers.__init__, src.orchestration
"""

from enum import Enum
from typing import Optional, Any
from datetime import datetime
from uuid import uuid4
import colorsys
import math
import random
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class AgentType(str, Enum):
    """Agent types for VETKA nodes. ⚠️ NO ELISYA - it's middleware, not an agent!"""
    PM = "PM"
    DEV = "Dev"
    QA = "QA"
    ARC = "ARC"
    HUMAN = "Human"
    SYSTEM = "System"


class BranchType(str, Enum):
    """Branch types for tree structure"""
    MEMORY = "memory"    # Knowledge, rationale, docs (PM plans, Architecture)
    TASK = "task"        # Executable work (Dev code, QA tests)
    DATA = "data"        # Artifacts, files, results (code files, test reports)
    CONTROL = "control"  # Control signals (retry, promote, ARC suggestions)


class EdgeSemantics(str, Enum):
    """Edge semantic types (6 types as per spec)"""
    INFORMS = "informs"         # Information transfer
    INFLUENCES = "influences"   # Design/decision impact
    CREATES = "creates"         # Parent → child artifact
    DEPENDS = "depends"         # Task dependency
    SUPERSEDES = "supersedes"   # Version replacement (DeepSeek)
    REFERENCES = "references"   # Knowledge link / liana (DeepSeek)


class EdgeType(str, Enum):
    """Physical edge types"""
    LIANA = "liana"
    ROOT = "root"
    CONTROL = "control"


class AnimationType(str, Enum):
    """Animation types for Three.js"""
    STATIC = "static"
    PULSE = "pulse"
    GLOW = "glow"
    FLICKER = "flicker"


class ContentType(str, Enum):
    """Content types for node data"""
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    DIAGRAM = "diagram"
    METRICS = "metrics"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# Agent colors (Qwen)
AGENT_COLORS = {
    "PM": "#FFB347",       # warm orange
    "Dev": "#6495ED",      # cold blue
    "QA": "#9370DB",       # purple
    "ARC": "#32CD32",      # green
    "Human": "#FFD700",    # gold
    "System": "#A9A9A9"    # gray
}

# Edge visual styles
EDGE_STYLES = {
    "informs": {
        "color": "#FFB347",      # orange
        "thickness": 1.0,
        "style": "dashed",
        "arrow_type": None
    },
    "influences": {
        "color": "#DC143C",      # red
        "thickness": 2.0,
        "style": "solid",
        "arrow_type": None
    },
    "creates": {
        "color": "#8B4513",      # brown
        "thickness": 3.0,
        "style": "solid",
        "arrow_type": None
    },
    "depends": {
        "color": "#4169E1",      # blue
        "thickness": 1.5,
        "style": "solid",
        "arrow_type": "triangle"
    },
    "supersedes": {
        "color": "#808080",      # gray
        "thickness": 1.0,
        "style": "dotted",
        "arrow_type": None
    },
    "references": {
        "color": "#9370DB",      # purple
        "thickness": 0.5,
        "style": "dashed",
        "arrow_type": None
    }
}

# Icon mapping
BRANCH_TYPE_ICONS = {
    "memory": "document",
    "task": "code",
    "data": "file",
    "control": "suggestion"
}

FILE_EXTENSION_ICONS = {
    ".py": "code",
    ".js": "code",
    ".ts": "code",
    ".tsx": "code",
    ".jsx": "code",
    ".json": "file",
    ".yaml": "file",
    ".yml": "file",
    ".md": "document",
    ".txt": "document",
    ".png": "file",
    ".jpg": "file",
    ".svg": "file"
}

# Animation parameters (Kimi K2)
ANIMATION_PARAMS = {
    "static": {
        "scale": [1.0, 1.0],
        "opacity": [1.0, 1.0],
        "period_ms": 0
    },
    "pulse": {
        "scale": [1.0, 1.1],
        "opacity": [1.0, 1.0],
        "period_ms": 2000
    },
    "glow": {
        "scale": [1.0, 1.0],
        "opacity": [0.7, 1.0],
        "period_ms": 1500
    },
    "flicker": {
        "scale": [1.0, 1.0],
        "opacity": [0.3, 1.0],
        "period_ms": 500
    }
}

# Layout constants (Kimi K2)
LAYOUT_CONSTANTS = {
    "layer_height": 100,        # Y distance between tree levels
    "min_distance": 50,         # Minimum X/Z distance between siblings
    "golden_angle": 137.5,      # Phylotaxis spiral angle
    "max_deviation": 15,        # Maximum random offset in degrees
    "gravity_pull": 0.8,        # How strongly nodes stay near parent axis
    "base_unit": 8              # UI spacing base (8px grid)
}

# LOD distance thresholds (Kimi K2)
LOD_THRESHOLDS = {
    "cluster": 500,   # Very far: show as meta-node cluster
    "dot": 200,       # Far: show as simple colored dot
    "icon": 50,       # Medium: show icon + label
    "full": 0         # Close: show full content with preview
}

# Agent-specific LOD defaults (Kimi K2)
AGENT_LOD_DEFAULTS = {
    "PM": {
        "default_level": "FOREST",
        "max_depth": 3,
        "focus_types": ["memory", "task"]
    },
    "Dev": {
        "default_level": "BRANCH",
        "max_depth": 10,
        "focus_types": ["task", "data"]
    },
    "QA": {
        "default_level": "BRANCH",
        "max_depth": 8,
        "focus_types": ["task", "data"],
        "filter_tags": ["test", "bug", "quality"]
    },
    "ARC": {
        "default_level": "TREE",
        "max_depth": 5,
        "focus_types": ["control", "task"]
    },
    "Human": {
        "default_level": "FOREST",
        "max_depth": 3,
        "focus_types": ["memory"]
    },
    "System": {
        "default_level": "FOREST",
        "max_depth": 2,
        "focus_types": ["memory", "control"]
    }
}

# Default values for missing data
DEFAULTS = {
    "eval_score": 0.5,
    "entropy": 0.3,
    "completion_rate": 0.0,
    "student_level": 0,
    "flow_weight": 0.5
}

# Promote thresholds
PROMOTE_THRESHOLDS = {
    "node_count": 50,
    "entropy": 0.8,
    "user_actions": ["dive"]
}


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: VISUAL HINTS CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════

class VisualHintsCalculator:
    """Static methods for calculating visual properties (Qwen + DeepSeek formulas)"""

    @staticmethod
    def calculate_size_multiplier(entropy: float) -> float:
        """
        Higher entropy = larger node (more complexity)
        Range: 1.0 - 1.5
        """
        return round(1.0 + (entropy * 0.5), 3)

    @staticmethod
    def calculate_opacity(completion_rate: float) -> float:
        """
        Higher completion = more opaque (solid)
        Range: 0.2 - 1.0
        """
        return round(0.2 + (completion_rate * 0.8), 2)

    @staticmethod
    def calculate_animation(
        completion_rate: float,
        branch_type: str,
        eval_score: float,
        entropy: float
    ) -> str:
        """
        Animation based on node state:
        - pulse: task in progress
        - flicker: needs attention (low quality)
        - glow: high entropy (complex)
        - static: completed
        """
        if completion_rate < 1.0 and branch_type == "task":
            return "pulse"
        elif eval_score < 0.5:
            return "flicker"
        elif entropy > 0.7:
            return "glow"
        else:
            return "static"

    @staticmethod
    def get_animation_params(animation_type: str) -> dict:
        """Get animation parameters for Three.js"""
        return ANIMATION_PARAMS.get(animation_type, ANIMATION_PARAMS["static"])

    @staticmethod
    def desaturate(hex_color: str, factor: float) -> str:
        """Reduce saturation by converting to HSL, multiply S, convert back"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16) / 255
        g = int(hex_color[2:4], 16) / 255
        b = int(hex_color[4:6], 16) / 255
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        s *= factor
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    @staticmethod
    def calculate_color(agent: str, eval_score: float) -> str:
        """Base color from agent, saturation from quality"""
        base_color = AGENT_COLORS.get(agent, "#A9A9A9")

        if eval_score > 0.8:
            return base_color              # full saturation
        elif eval_score > 0.5:
            return VisualHintsCalculator.desaturate(base_color, 0.7)
        else:
            return VisualHintsCalculator.desaturate(base_color, 0.4)

    @staticmethod
    def calculate_position_hint(
        node_index: int,
        depth: int,
        parent_position: Optional[dict] = None
    ) -> dict:
        """
        Phylotaxis-based positioning with organic deviation.
        Uses Golden Angle (137.5°) for natural spiral distribution.
        """
        LAYER_HEIGHT = LAYOUT_CONSTANTS["layer_height"]
        GOLDEN_ANGLE = LAYOUT_CONSTANTS["golden_angle"]
        MAX_DEVIATION = LAYOUT_CONSTANTS["max_deviation"]
        GRAVITY_PULL = LAYOUT_CONSTANTS["gravity_pull"]

        # Base Y from depth
        base_y = depth * LAYER_HEIGHT

        # Golden angle spiral for X/Z
        theta = node_index * GOLDEN_ANGLE
        radius = depth * 50  # Spread increases with depth
        organic_x = math.sin(math.radians(theta)) * radius
        organic_z = math.cos(math.radians(theta)) * radius

        # Controlled randomness (seeded for reproducibility)
        random.seed(node_index * 1000 + depth)
        deviation_x = random.gauss(0, MAX_DEVIATION * (1 - GRAVITY_PULL))
        deviation_z = random.gauss(0, MAX_DEVIATION * (1 - GRAVITY_PULL))

        # Apply gravity pull toward parent axis
        if parent_position:
            organic_x = organic_x * (1 - GRAVITY_PULL) + parent_position.get("x", 0) * GRAVITY_PULL
            organic_z = organic_z * (1 - GRAVITY_PULL) + parent_position.get("z", 0) * GRAVITY_PULL

        return {
            "x": round(organic_x + deviation_x, 2),
            "y": round(base_y, 2),
            "z": round(organic_z + deviation_z, 2),
            "calculation": "phylotaxis"
        }

    @staticmethod
    def get_icon_for_branch_type(branch_type: str) -> str:
        """Get icon based on branch type"""
        return BRANCH_TYPE_ICONS.get(branch_type, "document")

    @staticmethod
    def get_icon_for_file(filename: str) -> str:
        """Get icon based on file extension"""
        for ext, icon in FILE_EXTENSION_ICONS.items():
            if filename.endswith(ext):
                return icon
        return "file"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: PHASE 10 TRANSFORMER
# ═══════════════════════════════════════════════════════════════════════════════

class Phase10Transformer:
    """
    Transforms Phase 9 workflow output into VETKA-JSON v1.3 format.

    Usage:
        transformer = Phase10Transformer()
        vetka_json = transformer.transform(phase9_output)
    """

    def __init__(self):
        self.nodes: list[dict] = []
        self.edges: list[dict] = []
        self.promote_history: list[dict] = []
        self.node_counter = 0
        self.edge_counter = 0
        self.workflow_id: str = ""

    def transform(self, phase9_data: dict) -> dict:
        """
        Main transformation method.

        Args:
            phase9_data: Phase 9 workflow output dictionary

        Returns:
            VETKA-JSON v1.3 formatted dictionary
        """
        # Reset state for new transformation
        self.nodes = []
        self.edges = []
        self.promote_history = []
        self.node_counter = 0
        self.edge_counter = 0

        # Extract workflow ID
        self.workflow_id = phase9_data.get("workflow_id") or uuid4().hex[:12]

        # Create root node
        root_id = self._create_root_node()

        # Process all Phase 9 results
        pm_id = self._process_pm_result(
            phase9_data.get("pm_result"),
            root_id,
            phase9_data
        )

        arch_id = self._process_architect_result(
            phase9_data.get("architect_result"),
            root_id,
            phase9_data
        )

        dev_id = self._process_dev_result(
            phase9_data.get("dev_result"),
            root_id,
            phase9_data
        )

        qa_id = self._process_qa_result(
            phase9_data.get("qa_result"),
            root_id,
            phase9_data
        )

        arc_ids = self._process_arc_suggestions(
            phase9_data.get("arc_suggestions", []),
            root_id,
            phase9_data
        )

        # Create edges based on mapping rules
        self._create_edges(root_id, pm_id, arch_id, dev_id, qa_id, arc_ids, phase9_data)

        # Calculate entropy for all nodes (requires all nodes to exist first)
        self._calculate_all_entropies()

        # Check promote triggers
        self._check_all_promote_triggers()

        # Capture cost optimization if available
        cost_optimization = self._calculate_cost_optimization(phase9_data)

        # Build final VETKA-JSON structure
        return {
            "$schema": "https://vetka.io/schema/v1.3.json",
            "format": "vetka-v1.3",
            "version": "1.3",
            "compatibility": {
                "reads": ["1.0", "1.1", "1.2"],
                "writes": ["1.2"]
            },
            "origin": {
                "source": "phase9",
                "workflow_id": self.workflow_id
            },
            "created_at": datetime.now().isoformat() + "Z",
            "tree": {
                "id": f"tree_{self.workflow_id}",
                "name": f"Workflow {self.workflow_id}",
                "root_node_id": root_id,
                "nodes": self.nodes,
                "edges": self.edges,
                "promote_history": self.promote_history,
                "metadata": self._calculate_tree_metadata(cost_optimization)
            }
        }

    def _generate_node_id(self, prefix: str) -> str:
        """Generate unique node ID"""
        self.node_counter += 1
        return f"{prefix}_{self.workflow_id}_{self.node_counter:03d}"

    def _generate_edge_id(self) -> str:
        """Generate unique edge ID"""
        self.edge_counter += 1
        return f"edge_{self.workflow_id}_{self.edge_counter:03d}"

    def _create_root_node(self) -> str:
        """Create the root node of the tree"""
        node_id = f"root_{self.workflow_id}"

        root_node = {
            "id": node_id,
            "parent_id": None,
            "type": "root",
            "branch_type": BranchType.MEMORY.value,
            "name": f"Workflow {self.workflow_id}",
            "content": {
                "type": ContentType.TEXT.value,
                "data": {
                    "description": f"Root node for workflow {self.workflow_id}",
                    "created": datetime.now().isoformat()
                },
                "preview": f"Workflow {self.workflow_id}",
                "download_url": None
            },
            "metadata": {
                "agent": AgentType.SYSTEM.value,
                "eval_score": 1.0,
                "entropy": 0.0,  # Will be recalculated
                "completion_rate": 0.0,
                "timestamp": datetime.now().isoformat() + "Z",
                "student_level": 0,
                "version": "1",
                "tags": ["root", "workflow"],
                "phase9_source": {
                    "field": "workflow_id",
                    "index": None,
                    "confidence": 1.0
                },
                "context_source": {
                    "type": "direct",
                    "reframe_applied": False,
                    "query_sources": []
                }
            },
            "visual_hints": {
                "size_multiplier": 1.5,
                "color": AGENT_COLORS["System"],
                "opacity": 1.0,
                "animation": AnimationType.STATIC.value,
                "animation_params": ANIMATION_PARAMS["static"],
                "icon": "document",
                "position_hint": {
                    "x": 0,
                    "y": 0,
                    "z": 0,
                    "calculation": "manual"
                }
            },
            "lod_hints": {
                "forest": {"visible": True},
                "tree": {"show_label": True},
                "branch": {"show_content": True}
            },
            "version_history": [],
            "children_ids": [],
            "promote_triggers": None,
            "promoted_to": None
        }

        self.nodes.append(root_node)
        return node_id

    def _process_pm_result(
        self,
        pm_result: Optional[dict],
        parent_id: str,
        phase9_data: dict
    ) -> Optional[str]:
        """Process PM result and create PM branch node"""
        if pm_result is None:
            # Create placeholder node for missing PM
            return self._create_placeholder_node(parent_id, "PM", "pm_result")

        node_id = self._generate_node_id("pm_plan")
        eval_score = pm_result.get("eval_score", DEFAULTS["eval_score"])

        # Build content data
        content_data = {
            "plan": pm_result.get("plan", "No plan provided"),
            "risks": pm_result.get("risks", [])
        }

        # Generate preview (first 100 chars)
        preview = pm_result.get("plan", "No plan")[:100]
        if len(pm_result.get("plan", "")) > 100:
            preview += "..."

        pm_node = {
            "id": node_id,
            "parent_id": parent_id,
            "type": "branch",
            "branch_type": BranchType.MEMORY.value,
            "name": "PM Plan",
            "content": {
                "type": ContentType.TEXT.value,
                "data": content_data,
                "preview": preview,
                "download_url": None
            },
            "metadata": {
                "agent": AgentType.PM.value,
                "eval_score": eval_score,
                "entropy": 0.0,  # Will be recalculated
                "completion_rate": 1.0 if eval_score > 0.7 else 0.8,
                "timestamp": datetime.now().isoformat() + "Z",
                "student_level": self._get_student_level(phase9_data),
                "version": "1",
                "tags": ["planning", "risk-assessment"],
                "phase9_source": {
                    "field": "pm_result",
                    "index": None,
                    "confidence": 0.95
                },
                "context_source": self._build_context_source(phase9_data, "pm")
            },
            "visual_hints": self._build_visual_hints(
                agent=AgentType.PM.value,
                eval_score=eval_score,
                completion_rate=1.0,
                branch_type=BranchType.MEMORY.value,
                entropy=0.3,
                node_index=1,
                depth=1
            ),
            "lod_hints": {
                "forest": {"visible": True},
                "tree": {"show_label": True},
                "branch": {"show_content": True}
            },
            "version_history": [],
            "children_ids": [],
            "promote_triggers": None,
            "promoted_to": None
        }

        # Add infrastructure tracking if available
        self._capture_infrastructure(pm_node, phase9_data, "pm")

        self.nodes.append(pm_node)

        # Update root's children
        self._add_child_to_parent(parent_id, node_id)

        return node_id

    def _process_architect_result(
        self,
        arch_result: Optional[dict],
        parent_id: str,
        phase9_data: dict
    ) -> Optional[str]:
        """Process architect result and create architecture branch node"""
        if arch_result is None:
            return None  # Architecture is optional

        node_id = self._generate_node_id("arch")
        eval_score = arch_result.get("score", DEFAULTS["eval_score"])

        content_data = {
            "diagram": arch_result.get("diagram", ""),
            "description": arch_result.get("description", "")
        }

        preview = arch_result.get("description", "Architecture")[:100]

        arch_node = {
            "id": node_id,
            "parent_id": parent_id,
            "type": "branch",
            "branch_type": BranchType.MEMORY.value,
            "name": "Architecture",
            "content": {
                "type": ContentType.DIAGRAM.value,
                "data": content_data,
                "preview": preview,
                "download_url": None
            },
            "metadata": {
                "agent": AgentType.PM.value,  # Or Dev depending on your setup
                "eval_score": eval_score,
                "entropy": 0.0,
                "completion_rate": 1.0 if eval_score > 0.7 else 0.8,
                "timestamp": datetime.now().isoformat() + "Z",
                "student_level": self._get_student_level(phase9_data),
                "version": "1",
                "tags": ["architecture", "design"],
                "phase9_source": {
                    "field": "architect_result",
                    "index": None,
                    "confidence": 0.95
                },
                "context_source": self._build_context_source(phase9_data, "architect")
            },
            "visual_hints": self._build_visual_hints(
                agent=AgentType.PM.value,
                eval_score=eval_score,
                completion_rate=1.0,
                branch_type=BranchType.MEMORY.value,
                entropy=0.3,
                node_index=2,
                depth=1
            ),
            "lod_hints": {
                "forest": {"visible": True},
                "tree": {"show_label": True},
                "branch": {"show_content": True}
            },
            "version_history": [],
            "children_ids": [],
            "promote_triggers": None,
            "promoted_to": None
        }

        self._capture_infrastructure(arch_node, phase9_data, "architect")
        self.nodes.append(arch_node)
        self._add_child_to_parent(parent_id, node_id)

        return node_id

    def _process_dev_result(
        self,
        dev_result: Optional[dict],
        parent_id: str,
        phase9_data: dict
    ) -> Optional[str]:
        """Process dev result and create dev branch node with file leaves"""
        if dev_result is None:
            return self._create_placeholder_node(parent_id, "Dev", "dev_result")

        node_id = self._generate_node_id("dev")
        eval_score = dev_result.get("eval_score", DEFAULTS["eval_score"])
        files = dev_result.get("files", [])

        # Calculate completion based on file count
        completion_rate = 1.0 if files else 0.0

        dev_node = {
            "id": node_id,
            "parent_id": parent_id,
            "type": "branch",
            "branch_type": BranchType.TASK.value,
            "name": "Development",
            "content": {
                "type": ContentType.CODE.value,
                "data": {
                    "file_count": len(files),
                    "total_tokens": sum(f.get("tokens", 0) for f in files),
                    "languages": list(set(f.get("language", "unknown") for f in files))
                },
                "preview": f"{len(files)} files generated",
                "download_url": None
            },
            "metadata": {
                "agent": AgentType.DEV.value,
                "eval_score": eval_score,
                "entropy": 0.0,
                "completion_rate": completion_rate,
                "timestamp": datetime.now().isoformat() + "Z",
                "student_level": self._get_student_level(phase9_data),
                "version": "1",
                "tags": ["development", "code-generation"],
                "phase9_source": {
                    "field": "dev_result",
                    "index": None,
                    "confidence": 0.95
                },
                "context_source": self._build_context_source(phase9_data, "dev")
            },
            "visual_hints": self._build_visual_hints(
                agent=AgentType.DEV.value,
                eval_score=eval_score,
                completion_rate=completion_rate,
                branch_type=BranchType.TASK.value,
                entropy=0.4,
                node_index=3,
                depth=1
            ),
            "lod_hints": {
                "forest": {"visible": True},
                "tree": {"show_label": True},
                "branch": {"show_content": True}
            },
            "version_history": [],
            "children_ids": [],
            "promote_triggers": None,
            "promoted_to": None
        }

        self._capture_infrastructure(dev_node, phase9_data, "dev")
        self.nodes.append(dev_node)
        self._add_child_to_parent(parent_id, node_id)

        # Create leaf nodes for each file
        for i, file_info in enumerate(files):
            self._create_file_leaf(node_id, file_info, i, phase9_data)

        return node_id

    def _create_file_leaf(
        self,
        parent_id: str,
        file_info: dict,
        index: int,
        phase9_data: dict
    ) -> str:
        """Create a leaf node for a file"""
        filename = file_info.get("name", f"file_{index}")
        node_id = self._generate_node_id(f"file_{filename.replace('.', '_')}")

        leaf_node = {
            "id": node_id,
            "parent_id": parent_id,
            "type": "leaf",
            "branch_type": BranchType.DATA.value,
            "name": filename,
            "content": {
                "type": ContentType.CODE.value,
                "data": {
                    "name": filename,
                    "path": file_info.get("path", ""),
                    "tokens": file_info.get("tokens", 0),
                    "language": file_info.get("language", "unknown")
                },
                "preview": file_info.get("path", filename),
                "download_url": f"/api/files/{self.workflow_id}/{filename}"
            },
            "metadata": {
                "agent": AgentType.DEV.value,
                "eval_score": 0.85,  # Default for files
                "entropy": 0.1,  # Leaves have low entropy
                "completion_rate": 1.0,
                "timestamp": datetime.now().isoformat() + "Z",
                "student_level": self._get_student_level(phase9_data),
                "version": "1",
                "tags": ["file", file_info.get("language", "code")],
                "phase9_source": {
                    "field": "dev_result.files",
                    "index": index,
                    "confidence": 1.0
                },
                "context_source": {
                    "type": "direct",
                    "reframe_applied": False,
                    "query_sources": []
                }
            },
            "visual_hints": self._build_visual_hints(
                agent=AgentType.DEV.value,
                eval_score=0.85,
                completion_rate=1.0,
                branch_type=BranchType.DATA.value,
                entropy=0.1,
                node_index=index + 10,
                depth=2
            ),
            "lod_hints": {
                "forest": {"visible": False},
                "tree": {"show_label": True},
                "branch": {"show_content": True}
            },
            "version_history": [],
            "children_ids": [],
            "promote_triggers": None,
            "promoted_to": None
        }

        # Override icon based on file extension
        leaf_node["visual_hints"]["icon"] = VisualHintsCalculator.get_icon_for_file(filename)

        self.nodes.append(leaf_node)
        self._add_child_to_parent(parent_id, node_id)

        return node_id

    def _process_qa_result(
        self,
        qa_result: Optional[dict],
        parent_id: str,
        phase9_data: dict
    ) -> Optional[str]:
        """Process QA result and create QA branch node with test leaves"""
        if qa_result is None:
            return self._create_placeholder_node(parent_id, "QA", "qa_result")

        node_id = self._generate_node_id("qa")
        eval_score = qa_result.get("eval_score", DEFAULTS["eval_score"])

        passed = qa_result.get("passed", 0)
        failed = qa_result.get("failed", 0)
        total_tests = passed + failed
        completion_rate = passed / total_tests if total_tests > 0 else 0.0

        qa_node = {
            "id": node_id,
            "parent_id": parent_id,
            "type": "branch",
            "branch_type": BranchType.TASK.value,
            "name": "QA Testing",
            "content": {
                "type": ContentType.METRICS.value,
                "data": {
                    "coverage": qa_result.get("coverage", 0),
                    "passed": passed,
                    "failed": failed,
                    "total_tests": total_tests
                },
                "preview": f"{passed}/{total_tests} tests passed ({qa_result.get('coverage', 0)}% coverage)",
                "download_url": None
            },
            "metadata": {
                "agent": AgentType.QA.value,
                "eval_score": eval_score,
                "entropy": 0.0,
                "completion_rate": completion_rate,
                "timestamp": datetime.now().isoformat() + "Z",
                "student_level": self._get_student_level(phase9_data),
                "version": "1",
                "tags": ["testing", "qa", "quality"],
                "phase9_source": {
                    "field": "qa_result",
                    "index": None,
                    "confidence": 0.95
                },
                "context_source": self._build_context_source(phase9_data, "qa")
            },
            "visual_hints": self._build_visual_hints(
                agent=AgentType.QA.value,
                eval_score=eval_score,
                completion_rate=completion_rate,
                branch_type=BranchType.TASK.value,
                entropy=0.4,
                node_index=4,
                depth=1
            ),
            "lod_hints": {
                "forest": {"visible": True},
                "tree": {"show_label": True},
                "branch": {"show_content": True}
            },
            "version_history": [],
            "children_ids": [],
            "promote_triggers": None,
            "promoted_to": None
        }

        self._capture_infrastructure(qa_node, phase9_data, "qa")
        self.nodes.append(qa_node)
        self._add_child_to_parent(parent_id, node_id)

        # Create leaf nodes for each test file
        tests = qa_result.get("tests", [])
        for i, test_name in enumerate(tests):
            self._create_test_leaf(node_id, test_name, i, phase9_data)

        return node_id

    def _create_test_leaf(
        self,
        parent_id: str,
        test_name: str,
        index: int,
        phase9_data: dict
    ) -> str:
        """Create a leaf node for a test file"""
        node_id = self._generate_node_id(f"test_{test_name.replace('.', '_')}")

        leaf_node = {
            "id": node_id,
            "parent_id": parent_id,
            "type": "leaf",
            "branch_type": BranchType.DATA.value,
            "name": test_name,
            "content": {
                "type": ContentType.CODE.value,
                "data": {
                    "test_name": test_name,
                    "test_type": "unit"
                },
                "preview": test_name,
                "download_url": f"/api/tests/{self.workflow_id}/{test_name}"
            },
            "metadata": {
                "agent": AgentType.QA.value,
                "eval_score": 0.85,
                "entropy": 0.1,
                "completion_rate": 1.0,
                "timestamp": datetime.now().isoformat() + "Z",
                "student_level": self._get_student_level(phase9_data),
                "version": "1",
                "tags": ["test", "qa"],
                "phase9_source": {
                    "field": "qa_result.tests",
                    "index": index,
                    "confidence": 1.0
                },
                "context_source": {
                    "type": "direct",
                    "reframe_applied": False,
                    "query_sources": []
                }
            },
            "visual_hints": self._build_visual_hints(
                agent=AgentType.QA.value,
                eval_score=0.85,
                completion_rate=1.0,
                branch_type=BranchType.DATA.value,
                entropy=0.1,
                node_index=index + 20,
                depth=2
            ),
            "lod_hints": {
                "forest": {"visible": False},
                "tree": {"show_label": True},
                "branch": {"show_content": True}
            },
            "version_history": [],
            "children_ids": [],
            "promote_triggers": None,
            "promoted_to": None
        }

        leaf_node["visual_hints"]["icon"] = "test"

        self.nodes.append(leaf_node)
        self._add_child_to_parent(parent_id, node_id)

        return node_id

    def _process_arc_suggestions(
        self,
        arc_suggestions: list,
        parent_id: str,
        phase9_data: dict
    ) -> list[str]:
        """Process ARC suggestions and create control branch nodes"""
        arc_ids = []

        for i, suggestion in enumerate(arc_suggestions):
            node_id = self._generate_node_id(f"arc_{i}")
            success_score = suggestion.get("success", DEFAULTS["eval_score"])

            arc_node = {
                "id": node_id,
                "parent_id": parent_id,
                "type": "branch",
                "branch_type": BranchType.CONTROL.value,
                "name": f"ARC Suggestion {i + 1}",
                "content": {
                    "type": ContentType.TEXT.value,
                    "data": {
                        "transformation": suggestion.get("transformation", ""),
                        "success_probability": success_score
                    },
                    "preview": suggestion.get("transformation", "")[:100],
                    "download_url": None
                },
                "metadata": {
                    "agent": AgentType.ARC.value,
                    "eval_score": success_score,
                    "entropy": 0.0,
                    "completion_rate": 1.0,
                    "timestamp": datetime.now().isoformat() + "Z",
                    "student_level": self._get_student_level(phase9_data),
                    "version": "1",
                    "tags": ["arc", "suggestion", "optimization"],
                    "phase9_source": {
                        "field": "arc_suggestions",
                        "index": i,
                        "confidence": 0.9
                    },
                    "context_source": self._build_context_source(phase9_data, "arc")
                },
                "visual_hints": self._build_visual_hints(
                    agent=AgentType.ARC.value,
                    eval_score=success_score,
                    completion_rate=1.0,
                    branch_type=BranchType.CONTROL.value,
                    entropy=0.5,
                    node_index=5 + i,
                    depth=1
                ),
                "lod_hints": {
                    "forest": {"visible": True},
                    "tree": {"show_label": True},
                    "branch": {"show_content": True}
                },
                "version_history": [],
                "children_ids": [],
                "promote_triggers": None,
                "promoted_to": None
            }

            # Add ARC-specific execution tracking if available
            self._capture_arc_execution(arc_node, phase9_data, i)
            self._capture_infrastructure(arc_node, phase9_data, "arc")

            self.nodes.append(arc_node)
            self._add_child_to_parent(parent_id, node_id)
            arc_ids.append(node_id)

        return arc_ids

    def _create_placeholder_node(
        self,
        parent_id: str,
        agent: str,
        field: str
    ) -> str:
        """Create a placeholder node for missing data"""
        node_id = self._generate_node_id(f"{agent.lower()}_placeholder")

        placeholder_node = {
            "id": node_id,
            "parent_id": parent_id,
            "type": "branch",
            "branch_type": BranchType.MEMORY.value,
            "name": f"{agent} (Missing)",
            "content": {
                "type": ContentType.TEXT.value,
                "data": {"message": f"No {agent} data provided"},
                "preview": f"No {agent} data provided",
                "download_url": None
            },
            "metadata": {
                "agent": AgentType.SYSTEM.value,
                "eval_score": 0.5,
                "entropy": 0.1,
                "completion_rate": 0.0,
                "timestamp": datetime.now().isoformat() + "Z",
                "student_level": 0,
                "version": "1",
                "tags": ["placeholder", "missing"],
                "phase9_source": {
                    "field": field,
                    "index": None,
                    "confidence": 0.0
                },
                "context_source": {
                    "type": "direct",
                    "reframe_applied": False,
                    "query_sources": []
                }
            },
            "visual_hints": {
                "size_multiplier": 1.05,
                "color": "#A9A9A9",
                "opacity": 0.2,
                "animation": AnimationType.FLICKER.value,
                "animation_params": ANIMATION_PARAMS["flicker"],
                "icon": "document",
                "position_hint": VisualHintsCalculator.calculate_position_hint(
                    self.node_counter, 1
                )
            },
            "lod_hints": {
                "forest": {"visible": True},
                "tree": {"show_label": True},
                "branch": {"show_content": True}
            },
            "version_history": [],
            "children_ids": [],
            "promote_triggers": None,
            "promoted_to": None
        }

        self.nodes.append(placeholder_node)
        self._add_child_to_parent(parent_id, node_id)

        return node_id

    def _create_edges(
        self,
        root_id: str,
        pm_id: Optional[str],
        arch_id: Optional[str],
        dev_id: Optional[str],
        qa_id: Optional[str],
        arc_ids: list[str],
        phase9_data: dict
    ) -> None:
        """Create all edges based on mapping rules (Section 7.3)"""

        # Root → all top-level branches (creates)
        for branch_id in [pm_id, arch_id, dev_id, qa_id] + arc_ids:
            if branch_id:
                self._create_edge(
                    root_id, branch_id,
                    EdgeType.ROOT.value,
                    EdgeSemantics.CREATES.value,
                    1.0
                )

        # PM → Dev (informs)
        if pm_id and dev_id:
            self._create_edge(
                pm_id, dev_id,
                EdgeType.LIANA.value,
                EdgeSemantics.INFORMS.value,
                0.6
            )

        # PM → QA (informs)
        if pm_id and qa_id:
            self._create_edge(
                pm_id, qa_id,
                EdgeType.LIANA.value,
                EdgeSemantics.INFORMS.value,
                0.5
            )

        # Architecture → Dev (influences)
        if arch_id and dev_id:
            self._create_edge(
                arch_id, dev_id,
                EdgeType.LIANA.value,
                EdgeSemantics.INFLUENCES.value,
                0.8
            )

        # Dev → QA (depends) — QA depends on Dev
        # Note: Edge goes from QA to Dev to show dependency direction
        if dev_id and qa_id:
            edge = self._create_edge(
                qa_id, dev_id,
                EdgeType.LIANA.value,
                EdgeSemantics.DEPENDS.value,
                0.8
            )
            # Add parallel execution info if available
            self._add_parallel_execution_info(edge, phase9_data)

        # ARC → Dev (influences)
        for arc_id in arc_ids:
            if dev_id:
                self._create_edge(
                    arc_id, dev_id,
                    EdgeType.CONTROL.value,
                    EdgeSemantics.INFLUENCES.value,
                    0.7
                )

    def _create_edge(
        self,
        from_id: str,
        to_id: str,
        edge_type: str,
        semantics: str,
        flow_weight: float
    ) -> dict:
        """Create a single edge"""
        edge_id = self._generate_edge_id()
        style = EDGE_STYLES.get(semantics, EDGE_STYLES["informs"])

        edge = {
            "id": edge_id,
            "from": from_id,
            "to": to_id,
            "type": edge_type,
            "semantics": semantics,
            "flow_weight": flow_weight,
            "age": "0s",
            "direction": "forward",
            "visual_hints": {
                "thickness": style["thickness"],
                "color": style["color"],
                "style": style["style"],
                "curvature": 0.3,
                "arrow_type": style["arrow_type"]
            },
            "metadata": {
                "created_at": datetime.now().isoformat() + "Z",
                "description": f"{semantics} relationship"
            }
        }

        self.edges.append(edge)
        return edge

    def _add_parallel_execution_info(self, edge: dict, phase9_data: dict) -> None:
        """Add parallel execution info for Dev↔QA edge if available"""
        infra = phase9_data.get("infrastructure", {})
        parallel_info = infra.get("parallel", {})

        if parallel_info:
            edge["parallel_execution"] = {
                "executed_concurrently": True,
                "dev_start_time": parallel_info.get("dev_start_time"),
                "dev_end_time": parallel_info.get("dev_end_time"),
                "qa_start_time": parallel_info.get("qa_start_time"),
                "qa_end_time": parallel_info.get("qa_end_time"),
                "overlap_ms": parallel_info.get("overlap_ms", 0),
                "elisya_reframe_occurred": parallel_info.get("elisya_reframe_occurred", False),
                "reframe_timestamp": parallel_info.get("reframe_timestamp"),
                "reframe_trigger": parallel_info.get("reframe_trigger"),
                "reframe_impact": parallel_info.get("reframe_impact"),
                "shared_context_tokens": parallel_info.get("shared_context_tokens", 0),
                "context_updates_during_execution": parallel_info.get("context_updates", 0),
                "elisya_recommendations": parallel_info.get("elisya_recommendations", [])
            }

    def _build_visual_hints(
        self,
        agent: str,
        eval_score: float,
        completion_rate: float,
        branch_type: str,
        entropy: float,
        node_index: int,
        depth: int
    ) -> dict:
        """Build visual hints for a node"""
        animation = VisualHintsCalculator.calculate_animation(
            completion_rate, branch_type, eval_score, entropy
        )

        return {
            "size_multiplier": VisualHintsCalculator.calculate_size_multiplier(entropy),
            "color": VisualHintsCalculator.calculate_color(agent, eval_score),
            "opacity": VisualHintsCalculator.calculate_opacity(completion_rate),
            "animation": animation,
            "animation_params": VisualHintsCalculator.get_animation_params(animation),
            "icon": VisualHintsCalculator.get_icon_for_branch_type(branch_type),
            "position_hint": VisualHintsCalculator.calculate_position_hint(node_index, depth)
        }

    def _build_context_source(self, phase9_data: dict, agent_type: str) -> dict:
        """Build context_source metadata"""
        infra = phase9_data.get("infrastructure", {})
        elisya_info = infra.get("elisya", {})

        context_source = {
            "type": "elisya" if elisya_info else "direct",
            "reframe_applied": bool(elisya_info.get("reframes_applied")),
            "query_sources": elisya_info.get("query_sources", ["changelog"])
        }

        # Add detailed Elisya tracking if available
        if elisya_info:
            context_source["elisya_details"] = {
                "elisya_version": elisya_info.get("version", "1.0.0"),
                "lod_level_requested": elisya_info.get("lod_requested", "BRANCH"),
                "lod_level_applied": elisya_info.get("lod_applied", "BRANCH"),
                "weaviate_queries": elisya_info.get("weaviate_stats", {}),
                "qdrant_queries": elisya_info.get("qdrant_stats", {}),
                "total_assembly_time_ms": elisya_info.get("assembly_time_ms", 0),
                "reframe_operations": elisya_info.get("reframe_operations", []),
                "degradation_occurred": elisya_info.get("degradation", False)
            }

        return context_source

    def _capture_infrastructure(
        self,
        node: dict,
        phase9_data: dict,
        agent_key: str
    ) -> None:
        """Add infrastructure tracking to node if Phase 9 provides it"""
        infra = phase9_data.get("infrastructure", {})

        # Learning context
        if "learning" in infra:
            learning = infra["learning"]
            node["metadata"]["learning_context"] = {
                "created_by_learner": learning.get("learner_model"),
                "learner_model_version": learning.get("model_version"),
                "is_training_exemplar": node["metadata"].get("eval_score", 0) > 0.8,
                "learner_confidence": learning.get("confidence", 0.0),
                "exemplar_portfolio_id": learning.get("portfolio_id"),
                "models_improved_by_this": learning.get("improvements", [])
            }

        # Model provenance
        if "routing" in infra:
            routing = infra["routing"]
            decisions = routing.get("decisions", [])
            agent_decision = next(
                (d for d in decisions if d.get("agent", "").lower() == agent_key),
                {}
            )

            if agent_decision:
                node["metadata"]["model_provenance"] = {
                    "primary_model": agent_decision.get("model"),
                    "model_version": agent_decision.get("version"),
                    "api_provider": agent_decision.get("provider"),
                    "api_key_index": agent_decision.get("key_index"),
                    "fallback_used": agent_decision.get("fallback_used", False),
                    "local_model_fallback": agent_decision.get("local_fallback"),
                    "tokens_input": agent_decision.get("tokens_input", 0),
                    "tokens_output": agent_decision.get("tokens_output", 0),
                    "tokens_total": agent_decision.get("tokens_total", 0),
                    "estimated_cost_usd": agent_decision.get("cost_usd", 0.0),
                    "execution_time_ms": agent_decision.get("time_ms", 0),
                    "routing_decision": {
                        "task_complexity": agent_decision.get("complexity"),
                        "routing_reason": agent_decision.get("reason"),
                        "alternative_considered": agent_decision.get("alternative"),
                        "cost_savings_vs_alternative": agent_decision.get("savings", 0.0)
                    }
                }

        # Storage status
        if "storage" in infra:
            storage = infra["storage"]
            triple_write = storage.get("triple_write_results", {})

            node["metadata"]["storage_status"] = {
                "changelog": triple_write.get("changelog", {"status": "unknown"}),
                "weaviate": triple_write.get("weaviate", {"status": "unknown"}),
                "qdrant": triple_write.get("qdrant", {"status": "unknown"}),
                "overall_status": storage.get("overall_status", "unknown"),
                "degradation_mode": storage.get("degradation_mode", False)
            }

        # Feedback tracking
        if "feedback" in infra:
            feedback = infra["feedback"]
            evaluations = feedback.get("evaluations", [])
            agent_eval = next(
                (e for e in evaluations if e.get("agent", "").lower() == agent_key),
                {}
            )

            if agent_eval:
                node["metadata"]["learning_feedback"] = {
                    "eval_score": node["metadata"].get("eval_score"),
                    "eval_agent_model": agent_eval.get("eval_model"),
                    "eval_timestamp": agent_eval.get("timestamp"),
                    "qualifies_for_training": node["metadata"].get("eval_score", 0) > 0.8,
                    "training_decision": agent_eval.get("decision"),
                    "retry_info": {
                        "retry_occurred": agent_eval.get("retried", False),
                        "retry_count": agent_eval.get("retry_count", 0),
                        "original_score": agent_eval.get("original_score"),
                        "improvement_delta": agent_eval.get("improvement"),
                        "prompt_adjustments": agent_eval.get("adjustments", [])
                    },
                    "saved_examples": agent_eval.get("saved_examples", []),
                    "feedback_source": "auto_eval"
                }

    def _capture_arc_execution(
        self,
        node: dict,
        phase9_data: dict,
        index: int
    ) -> None:
        """Add ARC-specific execution tracking"""
        infra = phase9_data.get("infrastructure", {})
        arc_info = infra.get("arc", {})

        if arc_info:
            executions = arc_info.get("execution_details", [])
            exec_detail = executions[index] if index < len(executions) else {}

            if exec_detail:
                node["metadata"]["arc_execution"] = {
                    "solver_model": exec_detail.get("solver_model"),
                    "solver_model_version": exec_detail.get("model_version"),
                    "prompt_template_version": exec_detail.get("template_version"),
                    "candidates": exec_detail.get("candidates", {}),
                    "best_candidate": exec_detail.get("best_candidate", {}),
                    "code_fixes_applied": exec_detail.get("fixes", []),
                    "training_examples_saved": exec_detail.get("saved_examples", {}),
                    "timing": exec_detail.get("timing", {})
                }

    def _add_child_to_parent(self, parent_id: str, child_id: str) -> None:
        """Add child ID to parent's children_ids list"""
        for node in self.nodes:
            if node["id"] == parent_id:
                if "children_ids" not in node:
                    node["children_ids"] = []
                node["children_ids"].append(child_id)
                break

    def _get_student_level(self, phase9_data: dict) -> int:
        """Get student level from infrastructure data"""
        infra = phase9_data.get("infrastructure", {})
        learning = infra.get("learning", {})
        return learning.get("student_level", DEFAULTS["student_level"])

    def _calculate_all_entropies(self) -> None:
        """Calculate entropy for all nodes after tree is built"""
        for node in self.nodes:
            entropy = self._calculate_entropy(node)
            node["metadata"]["entropy"] = entropy
            # Update visual hints based on new entropy
            node["visual_hints"]["size_multiplier"] = (
                VisualHintsCalculator.calculate_size_multiplier(entropy)
            )

    def _calculate_entropy(self, node: dict) -> float:
        """
        Calculate entropy for a node (DeepSeek formula).

        Entropy = measure of uncertainty/branching complexity
        Formula:
        entropy = min(1.0, (
            child_count / 20 * 0.4 +         # many children = high
            unique_agents / 5 * 0.3 +        # diverse agents = high
            (1 - avg_eval_score) * 0.3       # low quality = high uncertainty
        ))
        """
        children = [n for n in self.nodes if n.get("parent_id") == node["id"]]
        child_count = len(children)

        if child_count == 0:
            return 0.1  # leaf node = low entropy

        unique_agents = len(set(
            c.get("metadata", {}).get("agent", "System")
            for c in children
        ))

        scores = [
            c.get("metadata", {}).get("eval_score", 0.5)
            for c in children
        ]
        avg_score = sum(scores) / len(scores) if scores else 0.5

        entropy = min(1.0, (
            child_count / 20 * 0.4 +
            unique_agents / 5 * 0.3 +
            (1 - avg_score) * 0.3
        ))

        return round(entropy, 2)

    def _check_all_promote_triggers(self) -> None:
        """Check promote triggers for all branch nodes"""
        total_nodes = len(self.nodes)

        for node in self.nodes:
            if node["type"] in ["branch", "root"]:
                triggers = self._check_promote_triggers(node, total_nodes)
                if triggers and triggers.get("threshold_reached"):
                    node["promote_triggers"] = triggers

                    # Create promote event
                    promote_event = self._create_promote_event(node, triggers)
                    self.promote_history.append(promote_event)

    def _check_promote_triggers(self, node: dict, total_nodes: int) -> Optional[dict]:
        """Check if a node meets promote thresholds"""
        entropy = node["metadata"].get("entropy", 0)
        child_count = len(node.get("children_ids", []))

        # Check thresholds
        node_count_trigger = total_nodes > PROMOTE_THRESHOLDS["node_count"]
        entropy_trigger = entropy > PROMOTE_THRESHOLDS["entropy"]

        if node_count_trigger or entropy_trigger:
            return {
                "node_count": total_nodes,
                "entropy": entropy,
                "user_action": None,
                "threshold_reached": True
            }

        return None

    def _create_promote_event(self, node: dict, triggers: dict) -> dict:
        """Create a promote event for history"""
        event_id = f"promote_{uuid4().hex[:8]}"
        new_tree_id = f"tree_{node['id']}_{uuid4().hex[:8]}"

        return {
            "id": event_id,
            "source_node_id": node["id"],
            "event": "seed_detached",
            "timestamp": datetime.now().isoformat() + "Z",
            "new_tree_id": new_tree_id,
            "root_edge_id": f"edge_root_{uuid4().hex[:8]}",
            "triggers": triggers,
            "animation_duration_ms": 1800
        }

    def _calculate_cost_optimization(self, phase9_data: dict) -> Optional[dict]:
        """Calculate cost optimization metrics if routing data available"""
        infra = phase9_data.get("infrastructure", {})
        routing = infra.get("routing", {})

        if not routing:
            return None

        decisions = routing.get("decisions", [])
        cost_summary = routing.get("cost_summary", {})

        if not decisions:
            return None

        # Calculate totals
        total_tokens = sum(d.get("tokens_total", 0) for d in decisions)
        total_cost = sum(d.get("cost_usd", 0) for d in decisions)

        # Estimate baseline cost (if all used GPT-4)
        # Rough estimate: GPT-4 is about 3x more expensive
        baseline_cost = total_cost * 2.5 if total_cost > 0 else 0
        savings = baseline_cost - total_cost
        savings_percent = (savings / baseline_cost * 100) if baseline_cost > 0 else 0

        # Build cost by agent
        cost_by_agent = {}
        for decision in decisions:
            agent = decision.get("agent", "Unknown")
            cost_by_agent[agent] = {
                "tokens": decision.get("tokens_total", 0),
                "cost": decision.get("cost_usd", 0),
                "model": decision.get("model", "unknown")
            }

        # Count local vs API usage
        local_count = sum(1 for d in decisions if d.get("provider") == "ollama")
        api_count = len(decisions) - local_count
        fallback_count = sum(1 for d in decisions if d.get("fallback_used"))

        return {
            "total_tokens_used": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "baseline_cost_if_gpt4": round(baseline_cost, 4),
            "savings_usd": round(savings, 4),
            "savings_percent": round(savings_percent, 1),
            "cost_by_agent": cost_by_agent,
            "routing_summary": {
                "local_model_used": local_count,
                "api_model_used": api_count,
                "fallback_triggered": fallback_count
            }
        }

    def _calculate_tree_metadata(self, cost_optimization: Optional[dict]) -> dict:
        """Calculate tree-level metadata"""
        # Calculate max depth
        max_depth = 0
        for node in self.nodes:
            depth = self._get_node_depth(node["id"])
            max_depth = max(max_depth, depth)

        # Calculate completion rate
        scores = [
            n["metadata"].get("eval_score", 0.5)
            for n in self.nodes
            if n["type"] != "root"
        ]
        avg_completion = sum(scores) / len(scores) if scores else 0.0

        metadata = {
            "phase": "phase9",
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "max_depth": max_depth,
            "completion_rate": round(avg_completion, 2)
        }

        if cost_optimization:
            metadata["cost_optimization"] = cost_optimization

        return metadata

    def _get_node_depth(self, node_id: str, depth: int = 0) -> int:
        """Get depth of a node in the tree"""
        for node in self.nodes:
            if node["id"] == node_id:
                if node["parent_id"] is None:
                    return depth
                return self._get_node_depth(node["parent_id"], depth + 1)
        return depth
