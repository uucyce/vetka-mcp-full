"""
MARKER_155B.CANON.SCHEMA_LOCK.V1
MARKER_155B.CANON.SCHEMA_VERSIONING.V1
MARKER_155B.CANON.EVENT_SCHEMA.V1

Canonical DAG schema contract + lightweight validator/migration helpers.
Phase 155B (Canonization roadmap P0).
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


CURRENT_SCHEMA_VERSION = "1.0.0"
SUPPORTED_SCHEMA_VERSIONS = ("0.9.0", "1.0.0")

VALID_NODE_TYPES = {
    "phase",
    "agent",
    "task",
    "subtask",
    "condition",
    "parallel",
    "loop",
    "transform",
    "group",
}

VALID_EDGE_KINDS = {
    "flow",
    "conditional",
    "dataflow",
    "temporal",
    "feedback",
}

VALID_EDGE_CHANNELS = {"explicit", "temporal", "referential", "semantic"}


@dataclass
class CanonicalValidationResult:
    valid: bool
    errors: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def get_schema_versions_payload() -> Dict[str, Any]:
    return {
        "marker": "MARKER_155B.CANON.SCHEMA_VERSIONING.V1",
        "current_schema_version": CURRENT_SCHEMA_VERSION,
        "supported_schema_versions": list(SUPPORTED_SCHEMA_VERSIONS),
        "semver_policy": {
            "major": "breaking structural changes",
            "minor": "additive non-breaking fields",
            "patch": "non-structural fixes",
        },
        "storage_contract": {
            "G_design": "persisted + versioned workflow registry",
            "G_runtime": "persisted immutable run snapshots + latest pointer",
            "G_predict": "ephemeral by default, optional persisted approved snapshots",
        },
    }


def get_event_schema_payload() -> Dict[str, Any]:
    return {
        "marker": "MARKER_155B.CANON.EVENT_SCHEMA.V1",
        "schema_version": "1.0.0",
        "required_fields": [
            "event_id",
            "ts",
            "run_id",
            "task_id",
            "role",
            "phase",
            "action",
            "status",
            "payload",
        ],
        "optional_fields": [
            "duration_s",
            "subtask_idx",
            "detail",
            "sequence",
        ],
        "ordering_rules": {
            "primary_order": ["ts", "sequence"],
            "duplicates": "same event_id is idempotent and ignored after first apply",
            "late_events": "accepted and reconciled deterministically by ts/sequence",
            "missing_terminal_event": "runtime graph kept open with warning",
        },
    }


def get_canonical_schema_template(version: str = CURRENT_SCHEMA_VERSION) -> Dict[str, Any]:
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(f"Unsupported schema version: {version}")
    return {
        "schema_version": version,
        "graph": {
            "id": "",
            "version": "",
            "source_format": "json",
            "execution_mode": "design",
        },
        "nodes": [],
        "edges": [],
        "layout_hints": {
            "orientation": "bottom_up",
            "layer_spacing": 120,
            "node_spacing": 80,
        },
    }


def migrate_canonical_graph(
    payload: Dict[str, Any],
    to_version: str = CURRENT_SCHEMA_VERSION,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if to_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(f"Unsupported target schema version: {to_version}")

    migrated = deepcopy(payload)
    source_version = str(migrated.get("schema_version") or "0.9.0")
    notes: List[str] = []

    if source_version == to_version:
        return migrated, {
            "source_version": source_version,
            "target_version": to_version,
            "changed": False,
            "notes": ["no-op migration"],
        }

    if source_version == "0.9.0" and to_version == "1.0.0":
        migrated.setdefault("graph", {})
        migrated.setdefault("nodes", [])
        migrated.setdefault("edges", [])
        migrated.setdefault(
            "layout_hints",
            {"orientation": "bottom_up", "layer_spacing": 120, "node_spacing": 80},
        )
        migrated["schema_version"] = "1.0.0"
        notes.append("set default graph/nodes/edges/layout_hints and bumped schema_version")
    else:
        raise ValueError(f"Unsupported migration path: {source_version} -> {to_version}")

    return migrated, {
        "source_version": source_version,
        "target_version": to_version,
        "changed": True,
        "notes": notes,
    }


def validate_canonical_graph(payload: Dict[str, Any]) -> CanonicalValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    schema_version = str(payload.get("schema_version") or "")
    if not schema_version:
        errors.append("schema_version is required")
    elif schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(f"unsupported schema_version: {schema_version}")

    graph = payload.get("graph")
    if not isinstance(graph, dict):
        errors.append("graph must be an object")
    else:
        for field in ("id", "version", "source_format", "execution_mode"):
            if field not in graph:
                warnings.append(f"graph.{field} missing")

    nodes = payload.get("nodes")
    edges = payload.get("edges")
    if not isinstance(nodes, list):
        errors.append("nodes must be an array")
        nodes = []
    if not isinstance(edges, list):
        errors.append("edges must be an array")
        edges = []

    node_ids = set()
    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"nodes[{idx}] must be an object")
            continue
        node_id = node.get("id")
        if not node_id:
            errors.append(f"nodes[{idx}] missing id")
            continue
        if node_id in node_ids:
            errors.append(f"duplicate node id: {node_id}")
        node_ids.add(node_id)
        node_type = node.get("type")
        if node_type and node_type not in VALID_NODE_TYPES:
            warnings.append(f"nodes[{idx}] unknown type: {node_type}")
        meta = node.get("meta")
        if isinstance(meta, dict) and "level" in meta:
            level = meta.get("level")
            if not isinstance(level, (int, float)):
                warnings.append(f"nodes[{idx}].meta.level should be numeric")

    for idx, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"edges[{idx}] must be an object")
            continue
        source = edge.get("source")
        target = edge.get("target")
        if not source or not target:
            errors.append(f"edges[{idx}] must include source and target")
            continue
        if source not in node_ids:
            warnings.append(f"edges[{idx}] source not found in nodes: {source}")
        if target not in node_ids:
            warnings.append(f"edges[{idx}] target not found in nodes: {target}")

        kind = edge.get("kind")
        if kind and kind not in VALID_EDGE_KINDS:
            warnings.append(f"edges[{idx}] unknown kind: {kind}")

        meta = edge.get("meta")
        if isinstance(meta, dict):
            channel = meta.get("channel")
            if channel and channel not in VALID_EDGE_CHANNELS:
                warnings.append(f"edges[{idx}] unknown channel: {channel}")
            score = meta.get("score")
            if score is not None and not isinstance(score, (int, float)):
                warnings.append(f"edges[{idx}].meta.score should be numeric")

    layout_hints = payload.get("layout_hints")
    if layout_hints is not None and not isinstance(layout_hints, dict):
        errors.append("layout_hints must be an object if provided")

    return CanonicalValidationResult(valid=not errors, errors=errors, warnings=warnings)
