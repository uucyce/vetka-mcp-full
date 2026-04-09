"""
VETKA Phase 104.4 - Socket.IO Approval Events

MARKER_104_APPROVAL_SOCKET

Emits approval requests to chat UI for user decision.
Handles real-time approval workflow for VETKA mode artifacts.

@file approval_socket_handler.py
@status ACTIVE
@phase Phase 104.4
@lastAudit 2026-01-31

Flow:
1. Agent generates artifacts -> EvalAgent scores them
2. emit_approval_request() sends preview to chat UI
3. User sees code preview + QA score + feedback
4. User clicks Approve/Reject/Edit
5. handle_approval_response() processes decision
6. Workflow continues or stops based on decision
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


async def emit_approval_request(
    socketio,
    group_id: str,
    request_id: str,
    artifacts: List[Dict[str, Any]],
    eval_score: float,
    eval_feedback: str,
    workflow_id: str
) -> bool:
    """
    Emit approval request to chat UI.

    UI should show:
    - Code preview for each artifact
    - QA score badge (green >= 0.8, yellow >= 0.6, red < 0.6)
    - EvalAgent feedback
    - Approve/Reject/Edit buttons

    Args:
        socketio: Socket.IO server instance
        group_id: Target group/room for the event
        request_id: Unique approval request ID
        artifacts: List of artifact dicts with content
        eval_score: Score from EvalAgent (0.0-1.0)
        eval_feedback: Textual feedback from EvalAgent
        workflow_id: Parent workflow ID

    Returns:
        True if emit succeeded, False otherwise
    """
    event_data = {
        "type": "approval_request",
        "request_id": request_id,
        "workflow_id": workflow_id,
        "group_id": group_id,
        "artifacts": [
            {
                "id": a.get("id", f"artifact_{i}"),
                "filename": a.get("filename", a.get("name", "untitled")),
                "language": a.get("language", _detect_language(a.get("filename", ""))),
                "content_preview": a.get("content", "")[:500],
                "full_content": a.get("content", ""),
                "lines": a.get("lines", _count_lines(a.get("content", ""))),
                "agent": a.get("agent", "Dev"),
                "artifact_type": a.get("type", "code")
            }
            for i, a in enumerate(artifacts)
        ],
        "eval_score": eval_score,
        "eval_feedback": eval_feedback,
        "score_level": _get_score_level(eval_score),
        "actions": ["approve", "reject", "edit"],
        "timeout_seconds": 300  # 5 minute timeout
    }

    try:
        await socketio.emit(
            "approval_request",
            event_data,
            room=group_id
        )
        logger.info(f"[Approval] Emitted request {request_id} to group {group_id} "
                   f"(score: {eval_score:.2f}, artifacts: {len(artifacts)})")
        return True
    except Exception as e:
        logger.error(f"[Approval] Failed to emit request {request_id}: {e}")
        return False


async def handle_approval_response(
    socketio,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Handle user approval/rejection from chat UI.

    Expected data:
    {
        "request_id": str,
        "action": "approve" | "reject" | "edit",
        "reason": str (optional),
        "edited_content": dict (optional, for edit action)
    }

    Args:
        socketio: Socket.IO server instance
        data: Response data from client

    Returns:
        Result dict with status and message
    """
    from src.services.approval_service import get_approval_service

    request_id = data.get("request_id")
    action = data.get("action")
    reason = data.get("reason", "")
    group_id = data.get("group_id", "default")

    if not request_id:
        return {"status": "error", "message": "Missing request_id"}

    if action not in ("approve", "reject", "edit"):
        return {"status": "error", "message": f"Invalid action: {action}"}

    service = get_approval_service()
    result = {"request_id": request_id}

    try:
        if action == "approve":
            success = service.approve(request_id, reason or "User approved via chat")
            result["status"] = "approved" if success else "error"
            result["message"] = "Artifacts approved and will be applied" if success else "Approval failed - request not found"

            await socketio.emit("approval_result", result, room=group_id)
            logger.info(f"[Approval] User approved {request_id}")

        elif action == "reject":
            success = service.reject(request_id, reason or "User rejected via chat")
            result["status"] = "rejected" if success else "error"
            result["message"] = "Artifacts rejected" if success else "Rejection failed - request not found"

            await socketio.emit("approval_result", result, room=group_id)
            logger.info(f"[Approval] User rejected {request_id}: {reason}")

        elif action == "edit":
            # Store edited content for re-review
            edited = data.get("edited_content", {})
            result["status"] = "editing"
            result["message"] = "Edit mode - review changes before approval"
            result["edited_artifacts"] = list(edited.keys()) if edited else []

            await socketio.emit("approval_result", result, room=group_id)
            logger.info(f"[Approval] User editing {request_id}")

    except Exception as e:
        logger.error(f"[Approval] Error handling response for {request_id}: {e}")
        result["status"] = "error"
        result["message"] = str(e)
        await socketio.emit("approval_error", {
            "request_id": request_id,
            "error": str(e)
        }, room=group_id)

    return result


def register_approval_socket_handlers(sio, app=None):
    """
    Register approval Socket.IO event handlers.

    Events registered:
    - approval_response: Handle user approve/reject/edit action
    - get_pending_approvals: Fetch all pending approval requests

    Args:
        sio: Socket.IO AsyncServer instance
        app: FastAPI app (optional)
    """

    @sio.on("approval_response")
    async def on_approval_response(sid, data):
        """
        Handle approval response from chat UI.

        Phase 104.4: Enhanced approval flow with edit support.
        """
        logger.debug(f"[Approval] Received response from {sid}: {data.get('action')}")
        return await handle_approval_response(sio, data)

    @sio.on("get_approval_details")
    async def on_get_approval_details(sid, data):
        """
        Get full details of an approval request.

        Returns full artifact content for preview/editing.
        """
        from src.services.approval_service import get_approval_service

        request_id = data.get("request_id") if data else None
        if not request_id:
            return {"status": "error", "message": "Missing request_id"}

        service = get_approval_service()
        request = service.get_request(request_id)

        if request:
            await sio.emit("approval_details", request, to=sid)
            return {"status": "ok", "request_id": request_id}
        else:
            return {"status": "error", "message": "Request not found"}

    logger.info("[Approval] Socket handlers registered (Phase 104.4)")


# === Utility Functions ===

def _detect_language(filename: str) -> str:
    """Detect programming language from filename extension."""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".json": "json",
        ".md": "markdown",
        ".html": "html",
        ".css": "css",
        ".sql": "sql",
        ".sh": "bash",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
    }

    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
    return ext_map.get(ext, "text")


def _count_lines(content: str) -> int:
    """Count lines in content string."""
    if not content:
        return 0
    return content.count("\n") + 1


def _get_score_level(score: float) -> str:
    """
    Get score level for UI badge coloring.

    Returns:
        'high' (green): score >= 0.8
        'medium' (yellow): score >= 0.6
        'low' (red): score < 0.6
    """
    if score >= 0.8:
        return "high"
    elif score >= 0.6:
        return "medium"
    else:
        return "low"
