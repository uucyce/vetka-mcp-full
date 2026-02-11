# MARKER_136.ARTIFACT_API_ROUTE
"""REST routes for artifacts panel (list + approve/reject)."""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from src.api.handlers.artifact_routes import (
    list_artifacts_for_panel,
    approve_artifact_for_panel,
    reject_artifact_for_panel,
    save_webpage_artifact,
)


router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


class ArtifactDecisionRequest(BaseModel):
    reason: Optional[str] = None


class SaveWebpageRequest(BaseModel):
    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None


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
    )
