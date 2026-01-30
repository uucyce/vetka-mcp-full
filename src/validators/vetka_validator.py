"""
VETKA JSON Validator.

Validates VETKA-JSON v1.3 format against schema and business rules.

Features:
- JSON Schema validation
- Node ID uniqueness validation
- Edge reference validation
- Visual hints range validation
- Promote consistency validation
- Elisya agent check (CRITICAL: Elisya is middleware, NOT an agent!)

Author: AI Council + Opus 4.5
Date: December 13, 2025

@status: active
@phase: 96
@depends: json, logging, pathlib, typing, jsonschema
@used_by: src.validators.__init__, src.orchestration
"""

import json
import logging
from pathlib import Path
from typing import Optional

try:
    import jsonschema
    from jsonschema import validate, Draft7Validator, ValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

logger = logging.getLogger(__name__)


class VetkaValidator:
    """
    Validates VETKA-JSON v1.3 format.

    Usage:
        validator = VetkaValidator("config/vetka_schema_v1.3.json")
        is_valid, errors = validator.validate(vetka_json)
    """

    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize validator with optional schema path.

        Args:
            schema_path: Path to JSON schema file. If None, uses default location.
        """
        self.schema: Optional[dict] = None
        self.schema_path = schema_path

        if schema_path:
            self._load_schema(schema_path)

    def _load_schema(self, schema_path: str) -> None:
        """Load JSON schema from file"""
        try:
            path = Path(schema_path)
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    self.schema = json.load(f)
                logger.info(f"Loaded VETKA schema from {schema_path}")
            else:
                logger.warning(f"Schema file not found: {schema_path}")
        except Exception as e:
            logger.error(f"Failed to load schema: {e}")

    def validate(self, vetka_json: dict) -> tuple[bool, list[str]]:
        """
        Validate VETKA-JSON against schema and business rules.

        Args:
            vetka_json: VETKA-JSON dictionary to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Schema validation
        schema_errors = self._validate_schema(vetka_json)
        errors.extend(schema_errors)

        # Business rule validations
        errors.extend(self._validate_node_ids(vetka_json))
        errors.extend(self._validate_edge_references(vetka_json))
        errors.extend(self._validate_visual_hints(vetka_json))
        errors.extend(self._validate_promote_consistency(vetka_json))
        errors.extend(self._validate_no_elisya_agent(vetka_json))
        errors.extend(self._validate_tree_structure(vetka_json))

        is_valid = len(errors) == 0
        return is_valid, errors

    def _validate_schema(self, data: dict) -> list[str]:
        """Validate against JSON schema"""
        errors = []

        if not HAS_JSONSCHEMA:
            logger.warning("jsonschema not installed, skipping schema validation")
            return errors

        if not self.schema:
            # Perform basic structure validation without full schema
            return self._validate_basic_structure(data)

        try:
            validate(instance=data, schema=self.schema)
        except ValidationError as e:
            errors.append(f"Schema validation error: {e.message} at {list(e.path)}")
        except Exception as e:
            errors.append(f"Schema validation failed: {str(e)}")

        return errors

    def _validate_basic_structure(self, data: dict) -> list[str]:
        """Basic structure validation when full schema not available"""
        errors = []

        # Required top-level fields
        required_fields = ["$schema", "format", "version", "origin", "created_at", "tree"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Check tree structure
        tree = data.get("tree", {})
        tree_required = ["id", "name", "root_node_id", "nodes", "edges"]
        for field in tree_required:
            if field not in tree:
                errors.append(f"Missing required tree field: {field}")

        # Check nodes have required fields
        for i, node in enumerate(tree.get("nodes", [])):
            node_required = ["id", "type", "branch_type", "name", "content", "metadata", "visual_hints"]
            for field in node_required:
                if field not in node:
                    errors.append(f"Node {i} missing required field: {field}")

        # Check edges have required fields
        for i, edge in enumerate(tree.get("edges", [])):
            edge_required = ["id", "from", "to", "type", "semantics", "flow_weight"]
            for field in edge_required:
                if field not in edge:
                    errors.append(f"Edge {i} missing required field: {field}")

        return errors

    def _validate_node_ids(self, data: dict) -> list[str]:
        """Validate node ID uniqueness and references"""
        errors = []
        tree = data.get("tree", {})
        nodes = tree.get("nodes", [])

        # Check for duplicate IDs
        node_ids = [node.get("id") for node in nodes]
        seen = set()
        duplicates = set()

        for node_id in node_ids:
            if node_id in seen:
                duplicates.add(node_id)
            seen.add(node_id)

        for dup in duplicates:
            errors.append(f"Duplicate node ID: {dup}")

        # Validate root_node_id exists
        root_id = tree.get("root_node_id")
        if root_id and root_id not in seen:
            errors.append(f"Root node ID not found in nodes: {root_id}")

        # Validate parent_id references
        for node in nodes:
            parent_id = node.get("parent_id")
            if parent_id is not None and parent_id not in seen:
                errors.append(f"Node {node.get('id')} has invalid parent_id: {parent_id}")

        # Validate children_ids references
        for node in nodes:
            for child_id in node.get("children_ids", []):
                if child_id not in seen:
                    errors.append(f"Node {node.get('id')} references non-existent child: {child_id}")

        return errors

    def _validate_edge_references(self, data: dict) -> list[str]:
        """Validate edge from/to references exist in nodes"""
        errors = []
        tree = data.get("tree", {})
        nodes = tree.get("nodes", [])
        edges = tree.get("edges", [])

        node_ids = {node.get("id") for node in nodes}

        # Check for duplicate edge IDs
        edge_ids = [edge.get("id") for edge in edges]
        seen = set()
        duplicates = set()

        for edge_id in edge_ids:
            if edge_id in seen:
                duplicates.add(edge_id)
            seen.add(edge_id)

        for dup in duplicates:
            errors.append(f"Duplicate edge ID: {dup}")

        # Validate from/to references
        for edge in edges:
            edge_id = edge.get("id", "unknown")
            from_id = edge.get("from")
            to_id = edge.get("to")

            if from_id not in node_ids:
                errors.append(f"Edge {edge_id} 'from' references non-existent node: {from_id}")
            if to_id not in node_ids:
                errors.append(f"Edge {edge_id} 'to' references non-existent node: {to_id}")

        return errors

    def _validate_visual_hints(self, data: dict) -> list[str]:
        """Validate visual hints are within valid ranges"""
        errors = []
        tree = data.get("tree", {})
        nodes = tree.get("nodes", [])

        for node in nodes:
            node_id = node.get("id", "unknown")
            visual_hints = node.get("visual_hints", {})

            # Validate size_multiplier (0.5 - 3.0)
            size = visual_hints.get("size_multiplier", 1.0)
            if not (0.5 <= size <= 3.0):
                errors.append(f"Node {node_id}: size_multiplier {size} out of range [0.5, 3.0]")

            # Validate opacity (0 - 1)
            opacity = visual_hints.get("opacity", 1.0)
            if not (0 <= opacity <= 1):
                errors.append(f"Node {node_id}: opacity {opacity} out of range [0, 1]")

            # Validate color format (#RRGGBB)
            color = visual_hints.get("color", "")
            if color and not (
                len(color) == 7 and
                color.startswith("#") and
                all(c in "0123456789abcdefABCDEF" for c in color[1:])
            ):
                errors.append(f"Node {node_id}: invalid color format: {color}")

            # Validate animation type
            animation = visual_hints.get("animation", "static")
            valid_animations = ["static", "pulse", "glow", "flicker"]
            if animation not in valid_animations:
                errors.append(f"Node {node_id}: invalid animation type: {animation}")

        # Validate edge visual hints
        for edge in tree.get("edges", []):
            edge_id = edge.get("id", "unknown")
            visual_hints = edge.get("visual_hints", {})

            # Validate thickness
            thickness = visual_hints.get("thickness", 1.0)
            if thickness < 0:
                errors.append(f"Edge {edge_id}: negative thickness: {thickness}")

            # Validate curvature
            curvature = visual_hints.get("curvature", 0.3)
            if not (0 <= curvature <= 1):
                errors.append(f"Edge {edge_id}: curvature {curvature} out of range [0, 1]")

        return errors

    def _validate_promote_consistency(self, data: dict) -> list[str]:
        """Validate promote triggers and history consistency"""
        errors = []
        tree = data.get("tree", {})
        nodes = tree.get("nodes", [])
        promote_history = tree.get("promote_history", [])

        # Build set of nodes with promote_triggers
        nodes_with_triggers = {
            node.get("id")
            for node in nodes
            if node.get("promote_triggers") is not None
        }

        # Validate promote_history entries reference valid nodes
        for event in promote_history:
            source_id = event.get("source_node_id")
            if source_id not in {n.get("id") for n in nodes}:
                errors.append(f"Promote event {event.get('id')} references non-existent node: {source_id}")

            # Check that event has required fields
            required = ["id", "source_node_id", "event", "timestamp"]
            for field in required:
                if field not in event:
                    errors.append(f"Promote event missing required field: {field}")

        # Check consistency: nodes with promote_triggers should have corresponding history
        # (This is a soft check - not always required)
        for node_id in nodes_with_triggers:
            has_history = any(
                e.get("source_node_id") == node_id
                for e in promote_history
            )
            if not has_history:
                logger.debug(f"Node {node_id} has promote_triggers but no history entry")

        return errors

    def _validate_no_elisya_agent(self, data: dict) -> list[str]:
        """
        CRITICAL: Validate that Elisya is NEVER used as an agent.
        Elisya is middleware, not an agent!
        """
        errors = []
        tree = data.get("tree", {})
        nodes = tree.get("nodes", [])

        for node in nodes:
            node_id = node.get("id", "unknown")
            metadata = node.get("metadata", {})
            agent = metadata.get("agent", "")

            # Check for any variation of "Elisya" as agent
            if agent.lower() == "elisya":
                errors.append(
                    f"CRITICAL: Node {node_id} has 'Elisya' as agent. "
                    f"Elisya is MIDDLEWARE, NOT an agent! "
                    f"Valid agents: PM, Dev, QA, ARC, Human, System"
                )

        return errors

    def _validate_tree_structure(self, data: dict) -> list[str]:
        """Validate tree structure integrity"""
        errors = []
        tree = data.get("tree", {})
        nodes = tree.get("nodes", [])

        if not nodes:
            errors.append("Tree has no nodes")
            return errors

        # Build node lookup
        node_map = {node.get("id"): node for node in nodes}
        root_id = tree.get("root_node_id")

        # Check root exists and has no parent
        if root_id not in node_map:
            errors.append(f"Root node {root_id} not found")
        else:
            root_node = node_map[root_id]
            if root_node.get("parent_id") is not None:
                errors.append(f"Root node {root_id} should have null parent_id")
            if root_node.get("type") != "root":
                errors.append(f"Root node {root_id} should have type 'root'")

        # Check for orphan nodes (no parent and not root)
        for node in nodes:
            node_id = node.get("id")
            parent_id = node.get("parent_id")

            if parent_id is None and node_id != root_id:
                errors.append(f"Orphan node found: {node_id} (no parent, not root)")

        # Check for cycles (simple check)
        for node in nodes:
            visited = set()
            current = node
            while current:
                current_id = current.get("id")
                if current_id in visited:
                    errors.append(f"Cycle detected involving node: {current_id}")
                    break
                visited.add(current_id)
                parent_id = current.get("parent_id")
                current = node_map.get(parent_id) if parent_id else None

        # Validate node types
        valid_types = ["root", "branch", "leaf"]
        valid_branch_types = ["memory", "task", "data", "control"]

        for node in nodes:
            node_id = node.get("id", "unknown")
            node_type = node.get("type")
            branch_type = node.get("branch_type")

            if node_type not in valid_types:
                errors.append(f"Node {node_id}: invalid type '{node_type}'")
            if branch_type not in valid_branch_types:
                errors.append(f"Node {node_id}: invalid branch_type '{branch_type}'")

        # Validate metadata scores
        for node in nodes:
            node_id = node.get("id", "unknown")
            metadata = node.get("metadata", {})

            eval_score = metadata.get("eval_score", 0.5)
            if not (0 <= eval_score <= 1):
                errors.append(f"Node {node_id}: eval_score {eval_score} out of range [0, 1]")

            entropy = metadata.get("entropy", 0.3)
            if not (0 <= entropy <= 1):
                errors.append(f"Node {node_id}: entropy {entropy} out of range [0, 1]")

            completion_rate = metadata.get("completion_rate", 0)
            if not (0 <= completion_rate <= 1):
                errors.append(f"Node {node_id}: completion_rate {completion_rate} out of range [0, 1]")

        return errors

    def validate_quick(self, vetka_json: dict) -> bool:
        """
        Quick validation - returns True/False only.
        Use validate() for detailed errors.
        """
        is_valid, _ = self.validate(vetka_json)
        return is_valid

    def format_errors(self, errors: list[str]) -> str:
        """Format errors for display"""
        if not errors:
            return "No validation errors"

        lines = [f"Found {len(errors)} validation error(s):"]
        for i, error in enumerate(errors, 1):
            lines.append(f"  {i}. {error}")

        return "\n".join(lines)
