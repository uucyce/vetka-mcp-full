"""
MARKER_108_4_ARTIFACT_TOOLS: Phase 108.4 - MCP Artifact Tools for Dev/QA Mode

MCP tools for managing artifacts in Dev/QA approval workflow.

Tools:
- EditArtifactTool: Edit artifact content and submit for approval
- ApproveArtifactTool: Approve pending artifact
- RejectArtifactTool: Reject artifact with feedback
- ListArtifactsTool: List artifacts by status

Integration:
- Uses disk_artifact_service for disk operations
- Uses staging_utils for status management
- Emits Socket.IO events for UI notifications

@status: active
@phase: 108.4
@depends: base_tool, disk_artifact_service, staging_utils, singletons
@used_by: mcp_server, stdio_server
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_tool import BaseMCPTool
from src.services.disk_artifact_service import (
    ARTIFACTS_DIR,
    sanitize_artifact_name,
    list_artifacts as list_disk_artifacts,
)
from src.utils.staging_utils import (
    get_staged_artifacts,
    update_artifact_status,
    _load_staging,
    _save_staging,
)
from src.initialization.singletons import get_socketio

logger = logging.getLogger(__name__)


class EditArtifactTool(BaseMCPTool):
    """
    Edit artifact content and submit for approval.

    MARKER_108_4_ARTIFACT_TOOLS

    Updates artifact content, sets status to "pending_approval",
    and emits artifact_approval Socket.IO event for UI notification.
    """

    @property
    def name(self) -> str:
        return "vetka_edit_artifact"

    @property
    def description(self) -> str:
        return "Edit artifact content and submit for approval"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "artifact_id": {
                    "type": "string",
                    "description": "Artifact ID from staging.json (e.g., 'art_1735891234_abc123')"
                },
                "path": {
                    "type": "string",
                    "description": "Alternative: artifact filepath (e.g., 'artifacts/hello_world.py')"
                },
                "new_content": {
                    "type": "string",
                    "description": "New content for the artifact"
                }
            },
            "required": ["new_content"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Edit artifact content and update status."""
        artifact_id = arguments.get("artifact_id")
        path = arguments.get("path")
        new_content = arguments.get("new_content")

        if not new_content:
            return {
                "success": False,
                "error": "new_content is required",
                "result": None
            }

        if not artifact_id and not path:
            return {
                "success": False,
                "error": "Either artifact_id or path must be provided",
                "result": None
            }

        try:
            # Load staging data
            data = _load_staging()

            # Find artifact by ID or path
            target_artifact = None
            target_id = None

            if artifact_id:
                target_artifact = data.get("artifacts", {}).get(artifact_id)
                target_id = artifact_id
            elif path:
                # Search for artifact with matching filepath
                for aid, artifact in data.get("artifacts", {}).items():
                    if artifact.get("filepath") == path or artifact.get("filename") == Path(path).name:
                        target_artifact = artifact
                        target_id = aid
                        break

            if not target_artifact:
                return {
                    "success": False,
                    "error": f"Artifact not found: {artifact_id or path}",
                    "result": None
                }

            # Update content and status
            target_artifact["content"] = new_content
            target_artifact["status"] = "pending_approval"
            target_artifact["updated_at"] = datetime.now().isoformat()
            target_artifact["content_length"] = len(new_content)

            # Save to staging
            data["artifacts"][target_id] = target_artifact
            if not _save_staging(data):
                return {
                    "success": False,
                    "error": "Failed to save staging data",
                    "result": None
                }

            # Emit artifact_approval event if socketio available
            socketio = get_socketio()
            if socketio:
                try:
                    # Use asyncio to emit if available
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(socketio.emit('artifact_approval', {
                            "artifact_id": target_id,
                            "name": target_artifact.get("filename", "unknown"),
                            "status": "pending_approval",
                            "content_length": len(new_content),
                            "content_preview": new_content[:200] + "..." if len(new_content) > 200 else new_content,
                            "updated_at": target_artifact["updated_at"]
                        }))
                    else:
                        # Fallback for synchronous context
                        loop.run_until_complete(socketio.emit('artifact_approval', {
                            "artifact_id": target_id,
                            "name": target_artifact.get("filename", "unknown"),
                            "status": "pending_approval",
                            "content_length": len(new_content),
                            "updated_at": target_artifact["updated_at"]
                        }))
                    logger.info(f"[EditArtifact] Emitted artifact_approval for: {target_id}")
                except Exception as e:
                    logger.warning(f"[EditArtifact] Failed to emit artifact_approval: {e}")

            return {
                "success": True,
                "result": {
                    "artifact_id": target_id,
                    "status": "pending_approval",
                    "content_length": len(new_content),
                    "updated_at": target_artifact["updated_at"]
                },
                "error": None
            }

        except Exception as e:
            logger.error(f"[EditArtifact] Error editing artifact: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": None
            }


class ApproveArtifactTool(BaseMCPTool):
    """
    Approve pending artifact.

    MARKER_108_4_ARTIFACT_TOOLS

    Sets status to "approved", saves to disk if not already saved,
    and emits artifact_applied Socket.IO event.
    """

    @property
    def name(self) -> str:
        return "vetka_approve_artifact"

    @property
    def description(self) -> str:
        return "Approve pending artifact and save to disk"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "artifact_id": {
                    "type": "string",
                    "description": "Artifact ID from staging.json"
                }
            },
            "required": ["artifact_id"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Approve artifact and save to disk."""
        artifact_id = arguments.get("artifact_id")

        if not artifact_id:
            return {
                "success": False,
                "error": "artifact_id is required",
                "result": None
            }

        try:
            # Load staging data
            data = _load_staging()
            artifact = data.get("artifacts", {}).get(artifact_id)

            if not artifact:
                return {
                    "success": False,
                    "error": f"Artifact not found: {artifact_id}",
                    "result": None
                }

            # Get artifact details
            content = artifact.get("content", "")
            filename = artifact.get("filename", f"artifact_{artifact_id}.txt")

            # Ensure artifacts directory exists
            ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

            # Determine filepath
            filepath = ARTIFACTS_DIR / filename

            # Handle duplicate filenames
            if filepath.exists():
                timestamp = int(datetime.now().timestamp())
                base_name = Path(filename).stem
                ext = Path(filename).suffix
                filename = f"{base_name}_{timestamp}{ext}"
                filepath = ARTIFACTS_DIR / filename

            # Write to disk
            filepath.write_text(content, encoding='utf-8')
            logger.info(f"[ApproveArtifact] Saved to disk: {filepath}")

            # Update status
            artifact["status"] = "approved"
            artifact["approved_at"] = datetime.now().isoformat()
            artifact["filepath"] = str(filepath.relative_to(filepath.parent.parent))

            data["artifacts"][artifact_id] = artifact
            if not _save_staging(data):
                logger.warning(f"[ApproveArtifact] Failed to save staging data")

            # Emit artifact_applied event
            socketio = get_socketio()
            if socketio:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(socketio.emit('artifact_applied', {
                            "artifact_id": artifact_id,
                            "filepath": str(filepath.relative_to(filepath.parent.parent)),
                            "status": "approved",
                            "approved_at": artifact["approved_at"]
                        }))
                    else:
                        loop.run_until_complete(socketio.emit('artifact_applied', {
                            "artifact_id": artifact_id,
                            "filepath": str(filepath.relative_to(filepath.parent.parent)),
                            "status": "approved",
                            "approved_at": artifact["approved_at"]
                        }))
                    logger.info(f"[ApproveArtifact] Emitted artifact_applied for: {artifact_id}")
                except Exception as e:
                    logger.warning(f"[ApproveArtifact] Failed to emit artifact_applied: {e}")

            return {
                "success": True,
                "result": {
                    "artifact_id": artifact_id,
                    "filepath": str(filepath.relative_to(filepath.parent.parent)),
                    "status": "approved",
                    "approved_at": artifact["approved_at"]
                },
                "error": None
            }

        except Exception as e:
            logger.error(f"[ApproveArtifact] Error approving artifact: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": None
            }


class RejectArtifactTool(BaseMCPTool):
    """
    Reject artifact with optional feedback.

    MARKER_108_4_ARTIFACT_TOOLS

    Sets status to "rejected", logs feedback,
    and emits artifact_rejected Socket.IO event.
    """

    @property
    def name(self) -> str:
        return "vetka_reject_artifact"

    @property
    def description(self) -> str:
        return "Reject artifact with optional feedback"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "artifact_id": {
                    "type": "string",
                    "description": "Artifact ID from staging.json"
                },
                "feedback": {
                    "type": "string",
                    "description": "Optional feedback/reason for rejection"
                }
            },
            "required": ["artifact_id"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Reject artifact with feedback."""
        artifact_id = arguments.get("artifact_id")
        feedback = arguments.get("feedback", "No feedback provided")

        if not artifact_id:
            return {
                "success": False,
                "error": "artifact_id is required",
                "result": None
            }

        try:
            # Update status
            success = update_artifact_status(artifact_id, "rejected")

            if not success:
                return {
                    "success": False,
                    "error": f"Artifact not found or failed to update: {artifact_id}",
                    "result": None
                }

            # Load updated data to add feedback
            data = _load_staging()
            artifact = data.get("artifacts", {}).get(artifact_id)

            if artifact:
                artifact["feedback"] = feedback
                artifact["rejected_at"] = datetime.now().isoformat()
                data["artifacts"][artifact_id] = artifact
                _save_staging(data)

            # Emit artifact_rejected event
            socketio = get_socketio()
            if socketio:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(socketio.emit('artifact_rejected', {
                            "artifact_id": artifact_id,
                            "feedback": feedback,
                            "status": "rejected",
                            "rejected_at": artifact.get("rejected_at")
                        }))
                    else:
                        loop.run_until_complete(socketio.emit('artifact_rejected', {
                            "artifact_id": artifact_id,
                            "feedback": feedback,
                            "status": "rejected",
                            "rejected_at": artifact.get("rejected_at")
                        }))
                    logger.info(f"[RejectArtifact] Emitted artifact_rejected for: {artifact_id}")
                except Exception as e:
                    logger.warning(f"[RejectArtifact] Failed to emit artifact_rejected: {e}")

            return {
                "success": True,
                "result": {
                    "artifact_id": artifact_id,
                    "status": "rejected",
                    "feedback": feedback,
                    "rejected_at": artifact.get("rejected_at")
                },
                "error": None
            }

        except Exception as e:
            logger.error(f"[RejectArtifact] Error rejecting artifact: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": None
            }


class ListArtifactsTool(BaseMCPTool):
    """
    List artifacts from staging.json and disk.

    MARKER_108_4_ARTIFACT_TOOLS

    Combines artifacts from staging.json (pending/approved/rejected)
    with artifacts on disk, optionally filtered by status.
    """

    @property
    def name(self) -> str:
        return "vetka_list_artifacts"

    @property
    def description(self) -> str:
        return "List artifacts by status from staging.json and disk"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status_filter": {
                    "type": "string",
                    "enum": ["pending", "approved", "rejected", "all"],
                    "default": "all",
                    "description": "Filter artifacts by status (default: all)"
                }
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List artifacts with optional status filter."""
        status_filter = arguments.get("status_filter", "all")

        try:
            result_artifacts = []

            # 1. Get staged artifacts from staging.json
            staged = get_staged_artifacts()
            for artifact in staged:
                if status_filter == "all" or artifact.get("status") == status_filter:
                    result_artifacts.append({
                        "id": artifact.get("task_id", artifact.get("id", "unknown")),
                        "name": artifact.get("filename", artifact.get("name", "unknown")),
                        "status": artifact.get("status", "unknown"),
                        "path": artifact.get("filepath", artifact.get("path", "")),
                        "last_modified": artifact.get("updated_at", artifact.get("staged_at", "")),
                        "content_length": artifact.get("content_length", len(artifact.get("content", ""))),
                        "qa_score": artifact.get("qa_score"),
                        "agent": artifact.get("agent")
                    })

            # 2. Get artifacts from disk (if not already in staging)
            try:
                # Run async function in sync context
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If event loop is running, we need to use a different approach
                    # For now, skip disk artifacts in async context
                    logger.debug("[ListArtifacts] Skipping disk artifacts in async context")
                    disk_artifacts = []
                else:
                    disk_artifacts = loop.run_until_complete(list_disk_artifacts())
            except Exception as e:
                logger.warning(f"[ListArtifacts] Failed to list disk artifacts: {e}")
                disk_artifacts = []

            # Add disk artifacts that aren't in staging
            staged_names = {a.get("name") for a in result_artifacts}
            for disk_artifact in disk_artifacts:
                if disk_artifact["filename"] not in staged_names:
                    if status_filter == "all" or status_filter == "approved":
                        result_artifacts.append({
                            "id": disk_artifact["filename"],
                            "name": disk_artifact["filename"],
                            "status": "approved",  # Assume disk artifacts are approved
                            "path": disk_artifact["path"],
                            "last_modified": disk_artifact["modified"],
                            "content_length": disk_artifact["size"],
                            "qa_score": None,
                            "agent": None
                        })

            # Sort by last_modified (newest first)
            result_artifacts.sort(key=lambda x: x.get("last_modified", ""), reverse=True)

            return {
                "success": True,
                "result": {
                    "total": len(result_artifacts),
                    "filter": status_filter,
                    "artifacts": result_artifacts
                },
                "error": None
            }

        except Exception as e:
            logger.error(f"[ListArtifacts] Error listing artifacts: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": None
            }


# Export all tools
__all__ = [
    'EditArtifactTool',
    'ApproveArtifactTool',
    'RejectArtifactTool',
    'ListArtifactsTool',
]
