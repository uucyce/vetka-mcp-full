"""
VETKA Embeddings Routes - FastAPI Version

@file embeddings_routes.py
@status ACTIVE
@phase Phase 39.6
@lastAudit 2026-01-05

Embeddings projection API routes.
Migrated from src/server/routes/embeddings_routes.py (Flask Blueprint)

Endpoints:
- POST /api/embeddings/project - Project embeddings to 3D
- POST /api/embeddings/project-vetka - Project embeddings to VETKA 3D format
- POST /api/embeddings/cluster - Compute clusters from embeddings

Changes from Flask version:
- Blueprint -> APIRouter
- request.json -> Pydantic BaseModel
- current_app.config -> request.app.state
- return jsonify({}) -> return {}
- def -> async def
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List


router = APIRouter(prefix="/api/embeddings", tags=["embeddings"])


# ============================================================
# PYDANTIC MODELS
# ============================================================

class ProjectRequest(BaseModel):
    """Request to project embeddings."""
    embeddings: List[List[float]]
    labels: Optional[List[str]] = None
    method: Optional[str] = "PCA"


class ProjectVetkaRequest(BaseModel):
    """Request to project embeddings to VETKA format."""
    embeddings: List[List[float]]
    labels: Optional[List[str]] = None
    node_ids: Optional[List[str]] = None
    colors: Optional[List[str]] = None
    method: Optional[str] = "PCA"


class ClusterRequest(BaseModel):
    """Request to cluster embeddings."""
    embeddings: List[List[float]]
    n_clusters: Optional[int] = 5
    method: Optional[str] = "PCA"


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _get_embeddings_components(request: Request) -> dict:
    """Get embeddings components from app state."""
    flask_config = getattr(request.app.state, 'flask_config', {})
    return {
        'available': flask_config.get('EMBEDDINGS_PROJECTOR_AVAILABLE', False),
        'factory': flask_config.get('embeddings_projector_factory'),
    }


# ============================================================
# ROUTES
# ============================================================

@router.post("/project")
async def embeddings_project(req: ProjectRequest, request: Request):
    """
    Project embeddings to 3D for visualization.

    Supports PCA, UMAP, and TSNE projection methods.
    """
    components = _get_embeddings_components(request)

    if not components['available']:
        raise HTTPException(status_code=503, detail="EmbeddingsProjector not available")

    try:
        if not req.embeddings or len(req.embeddings) < 2:
            raise HTTPException(status_code=400, detail="At least 2 embeddings required")

        # Create projector with requested method
        factory = components['factory']
        projector = factory(method=req.method, n_components=3)
        result = projector.project(req.embeddings, req.labels)

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/project-vetka")
async def embeddings_project_vetka(req: ProjectVetkaRequest, request: Request):
    """
    Project embeddings to VETKA 3D format.

    Returns projected coordinates with node IDs and colors for 3D tree visualization.
    """
    components = _get_embeddings_components(request)

    if not components['available']:
        raise HTTPException(status_code=503, detail="EmbeddingsProjector not available")

    try:
        if not req.embeddings or len(req.embeddings) < 2:
            raise HTTPException(status_code=400, detail="At least 2 embeddings required")

        factory = components['factory']
        projector = factory(method=req.method, n_components=3)
        result = projector.project_for_vetka(
            embeddings=req.embeddings,
            labels=req.labels,
            node_ids=req.node_ids,
            colors=req.colors
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cluster")
async def embeddings_cluster(req: ClusterRequest, request: Request):
    """
    Compute clusters from embeddings.

    Uses K-Means clustering on projected embeddings.
    """
    components = _get_embeddings_components(request)

    if not components['available']:
        raise HTTPException(status_code=503, detail="EmbeddingsProjector not available")

    try:
        if not req.embeddings or len(req.embeddings) < 2:
            raise HTTPException(status_code=400, detail="At least 2 embeddings required")

        factory = components['factory']
        projector = factory(method=req.method, n_components=3)
        result = projector.compute_clusters(
            embeddings=req.embeddings,
            n_clusters=req.n_clusters
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
