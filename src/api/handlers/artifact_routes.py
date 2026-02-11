# MARKER_136.ARTIFACT_API_HANDLER
"""Artifact API business logic for MCC panel."""

from __future__ import annotations

from typing import Any, Dict, List

from src.services.artifact_scanner import (
    scan_artifacts,
    approve_artifact,
    reject_artifact,
)


def _normalize_artifact_list(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for node in nodes:
        meta = node.get("metadata", {})
        out.append(
            {
                "id": node.get("id"),
                "name": node.get("name"),
                "status": meta.get("status", "done"),
                "artifact_type": meta.get("artifact_type", "document"),
                "language": meta.get("language", "text"),
                "file_path": meta.get("file_path", ""),
                "size_bytes": meta.get("size_bytes", 0),
                "modified_at": meta.get("modified_at"),
            }
        )
    return out


def list_artifacts_for_panel() -> Dict[str, Any]:
    nodes = scan_artifacts()
    return {
        "success": True,
        "artifacts": _normalize_artifact_list(nodes),
        "count": len(nodes),
    }


def approve_artifact_for_panel(artifact_id: str, reason: str = "Approved via API") -> Dict[str, Any]:
    return approve_artifact(artifact_id=artifact_id, reason=reason)


def reject_artifact_for_panel(artifact_id: str, reason: str = "Rejected via API") -> Dict[str, Any]:
    return reject_artifact(artifact_id=artifact_id, reason=reason)
