"""
VETKA Workflow Routes - FastAPI Version

@file workflow_routes.py
@status ACTIVE
@phase Phase 39.6
@lastAudit 2026-01-05

Workflow history and stats API routes.
Migrated from src/server/routes/workflow_routes.py (Flask Blueprint)

Endpoints:
- GET /api/workflow/history - Get workflow history
- GET /api/workflow/stats - Get workflow statistics
- GET /api/workflow/{workflow_id} - Get specific workflow details

Changes from Flask version:
- Blueprint -> APIRouter
- request.args.get() -> Query()
- return jsonify({}) -> return {}
- def -> async def
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query


router = APIRouter(prefix="/api/workflow", tags=["workflow"])


# ============================================================
# DAG VERSION HELPERS (Phase 155B)
# ============================================================

_DEFAULT_PROJECT = "default_project"


def _get_version_or_404(version_id: str, project_id: str = _DEFAULT_PROJECT):
    from src.services.mcc_dag_versions import get_dag_version
    v = get_dag_version(project_id, version_id)
    if not v:
        raise HTTPException(status_code=404, detail=f"DAG version not found: {version_id}")
    return v


def _get_primary_version(project_id: str = _DEFAULT_PROJECT):
    from src.services.mcc_dag_versions import list_dag_versions, get_dag_version
    listing = list_dag_versions(project_id)
    primary_id = listing.get("primary_version_id", "")
    if not primary_id:
        raise HTTPException(status_code=404, detail="No primary DAG version set")
    v = get_dag_version(project_id, primary_id)
    if not v:
        raise HTTPException(status_code=404, detail=f"Primary version not found: {primary_id}")
    return v


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _get_orchestrator(request: Request):
    """Get orchestrator from app state."""
    flask_config = getattr(request.app.state, 'flask_config', {})
    get_orchestrator = flask_config.get('get_orchestrator')

    if not get_orchestrator:
        # Fallback to singleton
        try:
            from src.initialization.singletons import get_orchestrator as _get_orch
            return _get_orch()
        except Exception:
            return None

    return get_orchestrator()


# ============================================================
# ROUTES
# ============================================================

@router.get("/history")
async def get_workflow_history(
    limit: int = Query(10, description="Max history items"),
    request: Request = None
):
    """
    Get workflow history.

    Returns recent workflow executions with their results.
    """
    orchestrator = _get_orchestrator(request)

    if not orchestrator:
        return {'local_history': [], 'weaviate_history': [], 'note': 'Orchestrator not available'}

    try:
        history = orchestrator.get_workflow_history(limit)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_workflow_stats(request: Request):
    """
    Get workflow statistics.

    Returns aggregated agent statistics.
    """
    orchestrator = _get_orchestrator(request)

    if not orchestrator:
        return {'agents': {}, 'total_workflows': 0, 'note': 'Orchestrator not available'}

    try:
        stats = orchestrator.get_agent_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# GRAPH SOURCE ROUTES (Phase 155B)
# MARKER_155B.CANON.GRAPH_SOURCE_ROUTES.V1
# ============================================================

@router.get("/runtime-graph/{version_id}")
async def get_runtime_graph(version_id: str, project_id: str = Query(_DEFAULT_PROJECT)):
    """
    MARKER_155B.CANON.RUNTIME_GRAPH_API.V1:
    Return runtime graph from a stored DAG version.
    """
    v = _get_version_or_404(version_id, project_id)
    payload = v.get("dag_payload") or {}
    runtime = payload.get("runtime_graph") or {}
    overview = runtime.get("l2_overview") or {}
    nodes = overview.get("nodes") or []
    edges = overview.get("edges") or []
    return {
        "marker": "MARKER_155B.CANON.RUNTIME_GRAPH_API.V1",
        "graph_source": "version",
        "task_id": version_id,
        "runtime_graph": overview,
        "stats": {"node_count": len(nodes), "edge_count": len(edges)},
    }


@router.get("/design-graph/latest")
async def get_design_graph_latest(project_id: str = Query(_DEFAULT_PROJECT)):
    """
    MARKER_155B.CANON.DESIGN_GRAPH_API.V1:
    Return design graph from the primary (latest) DAG version.
    """
    v = _get_primary_version(project_id)
    payload = v.get("dag_payload") or {}
    design = payload.get("design_graph") or {}
    nodes = design.get("nodes") or []
    edges = design.get("edges") or []
    return {
        "marker": "MARKER_155B.CANON.DESIGN_GRAPH_API.V1",
        "graph_source": "version",
        "stats": {"node_count": len(nodes), "edge_count": len(edges)},
        "design_graph": design,
        "canonical_markers": [
            "MARKER_155B.CANON.DRIFT_REPORT_API.V1",
            "MARKER_155B.CANON.RUNTIME_GRAPH_API.V1",
            "MARKER_155B.CANON.PREDICT_GRAPH_API.V1",
        ],
    }


@router.get("/predict-graph/{version_id}")
async def get_predict_graph(version_id: str, project_id: str = Query(_DEFAULT_PROJECT)):
    """
    MARKER_155B.CANON.PREDICT_GRAPH_API.V1:
    Return predictive overlay from a stored DAG version.
    """
    v = _get_version_or_404(version_id, project_id)
    payload = v.get("dag_payload") or {}
    overlay = payload.get("predictive_overlay") or {}
    predicted_edges = overlay.get("predicted_edges") or []
    # Collect unique nodes from predicted edges
    node_ids = set()
    for e in predicted_edges:
        node_ids.add(e.get("source", ""))
        node_ids.add(e.get("target", ""))
    node_ids.discard("")
    return {
        "marker": "MARKER_155B.CANON.PREDICT_GRAPH_API.V1",
        "graph_source": "version",
        "task_id": version_id,
        "predict_graph": {
            "edges": predicted_edges,
            "nodes": [{"id": nid} for nid in sorted(node_ids)],
        },
        "stats": overlay.get("stats") or {},
    }


@router.get("/drift-report/{version_id}")
async def get_drift_report(version_id: str, project_id: str = Query(_DEFAULT_PROJECT)):
    """
    MARKER_155B.CANON.DRIFT_REPORT_API.V1:
    Compare design vs runtime graph and return drift metrics.
    """
    v = _get_version_or_404(version_id, project_id)
    payload = v.get("dag_payload") or {}
    design = payload.get("design_graph") or {}
    runtime = payload.get("runtime_graph") or {}
    overview = runtime.get("l2_overview") or {}
    verifier = payload.get("verifier") or {}

    design_nodes = {n["id"] for n in (design.get("nodes") or []) if isinstance(n, dict)}
    runtime_nodes = {n["id"] for n in (overview.get("nodes") or []) if isinstance(n, dict)}
    design_edges = {(e["source"], e["target"]) for e in (design.get("edges") or []) if isinstance(e, dict)}
    runtime_edges = {(e["source"], e["target"]) for e in (overview.get("edges") or []) if isinstance(e, dict)}

    missing_runtime_edges = [
        {"source": s, "target": t} for s, t in sorted(design_edges - runtime_edges)
    ]

    return {
        "marker": "MARKER_155B.CANON.DRIFT_REPORT_API.V1",
        "graph_source": "version",
        "task_id": version_id,
        "drift_report": {
            "status": verifier.get("decision", "unknown"),
            "counts": {
                "design_nodes": len(design_nodes),
                "runtime_nodes": len(runtime_nodes),
                "shared_nodes": len(design_nodes & runtime_nodes),
                "design_edges": len(design_edges),
                "runtime_edges": len(runtime_edges),
            },
            "delta": {
                "missing_runtime_edges": missing_runtime_edges,
                "extra_runtime_edges": [
                    {"source": s, "target": t} for s, t in sorted(runtime_edges - design_edges)
                ],
            },
        },
    }


@router.get("/{workflow_id}")
async def get_workflow_details(workflow_id: str, request: Request):
    """
    Get specific workflow details.

    Returns full workflow data including agent results.
    """
    orchestrator = _get_orchestrator(request)

    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")

    try:
        history = orchestrator.get_workflow_history(100)

        # Search in local history
        for item in history.get('local_history', []):
            if item.get('workflow_id') == workflow_id:
                return item

        # Search in Weaviate history
        for item in history.get('weaviate_history', []):
            if item.get('workflow_id') == workflow_id:
                return item

        raise HTTPException(status_code=404, detail="Workflow not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
