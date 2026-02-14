# MARKER_136.ARTIFACT_API_ROUTE
# MARKER_141.ARTIFACT_CONTENT: Added content reading endpoint
"""REST routes for artifacts panel (list + approve/reject + content)."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.handlers.artifact_routes import (
    list_artifacts_for_panel,
    approve_artifact_for_panel,
    reject_artifact_for_panel,
    save_search_result_artifact,
    save_webpage_artifact,
)


router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


class ArtifactDecisionRequest(BaseModel):
    reason: Optional[str] = None


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


@router.post("/save-webpage")
async def save_webpage_endpoint(body: SaveWebpageRequest):
    return await save_webpage_artifact(
        url=body.url,
        title=body.title or "",
        snippet=body.snippet or "",
        raw_html=body.raw_html or "",
        raw_text=body.raw_text or "",
        output_format=body.output_format or "md",
        file_name=body.file_name or "",
        target_node_path=body.target_node_path or "",
    )


@router.post("/save-search-result")
async def save_search_result_endpoint(body: SaveSearchResultRequest):
    return await save_search_result_artifact(
        source=body.source,
        path=body.path or "",
        url=body.url or "",
        title=body.title or "",
        snippet=body.snippet or "",
        output_format=body.output_format or "md",
        file_name=body.file_name or "",
        target_node_path=body.target_node_path or "",
    )


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
        content = p.read_text(encoding="utf-8", errors="replace")
        max_size = 10000  # 10KB limit for UI display
        truncated = len(content) > max_size
        if truncated:
            content = content[:max_size]

        return {
            "success": True,
            "artifact_id": artifact_id,
            "file_path": str(p),
            "content": content,
            "size": p.stat().st_size,
            "truncated": truncated,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "artifact_id": artifact_id,
        }
