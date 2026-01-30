# src/validators/theory_validator.py
"""
Validate VETKA-JSON against Unified Theory v1.2.

Ensures nodes and edges comply with the theoretical model
including branch types, edge semantics, and structural rules.

@status: active
@phase: 96
@depends: pathlib, typing, config.design_system
@used_by: src.validators.__init__, src.orchestration
"""

import sys
from pathlib import Path
from typing import Tuple, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.design_system import BRANCH_TYPES, EDGE_SEMANTICS


class TheoryValidator:
    """Validates VETKA-JSON against Theory."""

    def validate(self, data: dict) -> Tuple[bool, List[str]]:
        errors = []

        if "tree" not in data:
            return False, ["Missing 'tree' field"]

        tree = data["tree"]
        nodes = tree.get("nodes", [])
        edges = tree.get("edges", [])

        # Check nodes
        for node in nodes:
            # Required fields
            for f in ["id", "type", "branch_type", "metadata", "visual_hints"]:
                if f not in node:
                    errors.append(f"Node {node.get('id', '?')}: missing '{f}'")

            # Branch type valid
            if node.get("branch_type") not in BRANCH_TYPES:
                errors.append(f"Node {node['id']}: invalid branch_type '{node.get('branch_type')}'")

            # Opacity formula: 0.2 + completion × 0.8
            completion = node.get("metadata", {}).get("completion_rate", 0)
            expected = round(0.2 + completion * 0.8, 2)
            actual = node.get("visual_hints", {}).get("opacity", 0)
            if abs(expected - actual) > 0.03:
                errors.append(f"Node {node['id']}: opacity {actual} != expected {expected}")

            # Entropy should be 0 for leaves (accept both "leaf" and "file")
            if node.get("type") in ["leaf", "file"]:
                if node.get("metadata", {}).get("entropy", 0) != 0:
                    errors.append(f"Leaf {node['id']}: entropy should be 0")

        # Check edges
        for edge in edges:
            if edge.get("semantics") not in EDGE_SEMANTICS:
                errors.append(f"Edge {edge.get('id', '?')}: invalid semantics '{edge.get('semantics')}'")

            # Root edges must use "creates"
            if edge.get("type") == "root" and edge.get("semantics") != "creates":
                errors.append(f"Edge {edge['id']}: root edge must use 'creates'")

        # Check structure
        roots = [n for n in nodes if n.get("type") == "root"]
        if len(roots) != 1:
            errors.append(f"Must have exactly 1 root, found {len(roots)}")

        return len(errors) == 0, errors
