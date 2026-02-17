# MARKER_136.ARTIFACT_API_ROUTE
# MARKER_141.ARTIFACT_CONTENT: Added content reading endpoint
"""REST routes for artifacts panel (list + approve/reject + content)."""

from pathlib import Path
import base64
import mimetypes
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.api.handlers.artifact_routes import (
    list_artifacts_for_panel,
    approve_artifact_for_panel,
    reject_artifact_for_panel,
    save_search_result_artifact,
    save_webpage_artifact,
)
from src.scanners.qdrant_updater import get_qdrant_updater
from src.services.artifact_scanner import set_artifact_favorite


router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


def _try_index_saved_artifact(result: dict, request: Request) -> dict:
    """
    Best-effort index bridge for saved artifacts.
    Keeps API response stable and only augments with index status fields.
    """
    try:
        if not result.get("success") or not result.get("file_path"):
            return result
        qdrant_manager = getattr(request.app.state, "qdrant_manager", None)
        qdrant_client = getattr(qdrant_manager, "client", None) if qdrant_manager else None
        if not qdrant_client:
            result["indexed"] = False
            result["index_error"] = "qdrant_client_not_available"
            return result
        updater = get_qdrant_updater(qdrant_client=qdrant_client, enable_triple_write=True)
        indexed = updater.update_file(Path(str(result["file_path"])))
        result["indexed"] = bool(indexed)
    except Exception as idx_err:
        result["indexed"] = False
        result["index_error"] = str(idx_err)[:200]
    return result


class ArtifactDecisionRequest(BaseModel):
    reason: Optional[str] = None

class ArtifactFavoriteRequest(BaseModel):
    is_favorite: bool


class SaveWebpageRequest(BaseModel):
    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None
    raw_html: Optional[str] = None
    raw_text: Optional[str] = None
    output_format: Optional[str] = None
    file_name: Optional[str] = None
    target_node_path: Optional[str] = None


class SaveSearchResultRequest(BaseModel):
    source: str
    path: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    snippet: Optional[str] = None
    output_format: Optional[str] = None
    file_name: Optional[str] = None
    target_node_path: Optional[str] = None


@router.get("")
async def get_artifacts():
    return list_artifacts_for_panel()


@router.post("/{artifact_id}/approve")
async def approve_artifact_endpoint(artifact_id: str, body: ArtifactDecisionRequest):
    return approve_artifact_for_panel(
        artifact_id=artifact_id,
        reason=body.reason or "Approved via API",
    )


@router.post("/{artifact_id}/reject")
async def reject_artifact_endpoint(artifact_id: str, body: ArtifactDecisionRequest):
    return reject_artifact_for_panel(
        artifact_id=artifact_id,
        reason=body.reason or "Rejected via API",
    )


@router.put("/{artifact_id}/favorite")
async def favorite_artifact_endpoint(artifact_id: str, body: ArtifactFavoriteRequest, request: Request):
    result = set_artifact_favorite(
        artifact_id=artifact_id,
        is_favorite=body.is_favorite,
    )
    if not result.get("success"):
        return result

    # MARKER_137.6F: Optional CAM memory sync for favorited artifacts.
    try:
        flask_config = getattr(request.app.state, "flask_config", {}) if request and request.app else {}
        if bool(flask_config.get("ELISYA_ENABLED", False)) and body.is_favorite:
            from src.orchestration.cam_event_handler import emit_cam_event
            await emit_cam_event(
                "artifact_created",
                {
                    "path": f"artifact_favorites/{artifact_id}",
                    "content": f"Favorite artifact: {artifact_id}",
                    "source_agent": "artifact_routes",
                },
                source="artifact_routes",
            )
    except Exception:
        pass

    # MARKER_137.6F: ENGRAM user preference sync (non-critical).
    try:
        from src.memory.engram_user_memory import get_engram_user_memory

        engram = get_engram_user_memory()
        user_id = (
            request.headers.get("x-user-id")
            or request.headers.get("x-session-user")
            or request.headers.get("x-session-id")
            or "danila"
        ).strip() or "danila"

        highlights = engram.get_preference(user_id, "project_highlights", "highlights")
        if not isinstance(highlights, dict):
            highlights = {}

        favorites = highlights.get("favorite_artifacts", [])
        if not isinstance(favorites, list):
            favorites = []

        if body.is_favorite:
            if artifact_id not in favorites:
                favorites.append(artifact_id)
        else:
            favorites = [aid for aid in favorites if aid != artifact_id]

        highlights["favorite_artifacts"] = favorites[-500:]
        engram.set_preference(
            user_id,
            "project_highlights",
            "highlights",
            highlights,
            confidence=0.85 if body.is_favorite else 0.72,
        )
    except Exception:
        pass

    return result


@router.post("/save-webpage")
async def save_webpage_endpoint(body: SaveWebpageRequest, request: Request):
    result = await save_webpage_artifact(
        url=body.url,
        title=body.title or "",
        snippet=body.snippet or "",
        raw_html=body.raw_html or "",
        raw_text=body.raw_text or "",
        output_format=body.output_format or "md",
        file_name=body.file_name or "",
        target_node_path=body.target_node_path or "",
    )
    # MARKER_153.IMPL.G16_WEB_SAVE_INDEX_BRIDGE
    return _try_index_saved_artifact(result, request)


@router.post("/save-search-result")
async def save_search_result_endpoint(body: SaveSearchResultRequest, request: Request):
    result = await save_search_result_artifact(
        source=body.source,
        path=body.path or "",
        url=body.url or "",
        title=body.title or "",
        snippet=body.snippet or "",
        output_format=body.output_format or "md",
        file_name=body.file_name or "",
        target_node_path=body.target_node_path or "",
    )
    # MARKER_153.IMPL.G16_SEARCH_SAVE_INDEX_BRIDGE
    return _try_index_saved_artifact(result, request)


# MARKER_141.ARTIFACT_CONTENT: Read artifact content by ID
# The artifact_id is URL-encoded, may contain slashes from file paths
@router.get("/{artifact_id:path}/content")
async def get_artifact_content(artifact_id: str):
    """
    Read the content of a panel artifact by its ID.

    The artifact scanner stores file_path in metadata. We look up
    the artifact to find its path, then read the file content.
    """
    # First find the artifact in the panel list
    result = list_artifacts_for_panel()
    artifacts = result.get("artifacts", [])

    target = None
    for art in artifacts:
        if art.get("id") == artifact_id or art.get("name") == artifact_id:
            target = art
            break

    if not target:
        raise HTTPException(status_code=404, detail=f"Artifact '{artifact_id}' not found")

    file_path = target.get("file_path", "")
    if not file_path:
        return {
            "success": True,
            "artifact_id": artifact_id,
            "content": "(no file path associated with this artifact)",
            "truncated": False,
        }

    # Resolve the file path
    p = Path(file_path)
    if not p.is_absolute():
        # Relative to project root
        project_root = Path(__file__).parent.parent.parent.parent
        p = project_root / file_path

    if not p.exists():
        return {
            "success": True,
            "artifact_id": artifact_id,
            "content": f"(file not found: {file_path})",
            "truncated": False,
        }

    try:
        max_size = 10000  # 10KB limit for UI display
        mime_type, _ = mimetypes.guess_type(str(p))
        mime_type = mime_type or "application/octet-stream"

        if mime_type.startswith("text/") or p.suffix.lower() in {".md", ".txt", ".json", ".yaml", ".yml", ".py", ".js", ".ts", ".tsx"}:
            content = p.read_text(encoding="utf-8", errors="replace")
            truncated = len(content) > max_size
            if truncated:
                content = content[:max_size]
            return {
                "success": True,
                "artifact_id": artifact_id,
                "file_path": str(p),
                "content": content,
                "encoding": "utf-8",
                "mimeType": mime_type,
                "size": p.stat().st_size,
                "truncated": truncated,
            }

        raw = p.read_bytes()
        truncated = len(raw) > max_size
        if truncated:
            raw = raw[:max_size]
        return {
            "success": True,
            "artifact_id": artifact_id,
            "file_path": str(p),
            "content": base64.b64encode(raw).decode("ascii"),
            "encoding": "base64",
            "mimeType": mime_type,
            "size": p.stat().st_size,
            "truncated": truncated,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "artifact_id": artifact_id,
        }
