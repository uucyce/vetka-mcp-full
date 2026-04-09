"""
MARKER_135.2B: DAG API Routes.
REST endpoints for DAG data retrieval and node actions.

@phase 135.2
@status active
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from src.services.dag_aggregator import DAGAggregator


router = APIRouter(prefix="/api/dag", tags=["DAG"])

# Singleton aggregator instance
_aggregator: Optional[DAGAggregator] = None


def get_aggregator() -> DAGAggregator:
    """Get or create DAG aggregator singleton."""
    global _aggregator
    if _aggregator is None:
        _aggregator = DAGAggregator()
    return _aggregator


class NodeActionRequest(BaseModel):
    """Request body for node actions."""
    action: str  # "retry" | "approve" | "reject" | "cancel"
    params: Optional[dict] = None


class NodeActionResponse(BaseModel):
    """Response for node actions."""
    success: bool
    message: str
    node_id: str


@router.get("")
async def get_dag(
    status: Optional[str] = Query(None, description="Filter by status: pending|running|done|failed|all"),
    time_range: Optional[str] = Query("1h", description="Time range: 1h|6h|24h|all"),
    task_id: Optional[str] = Query(None, description="Get tree for specific task"),
):
    """
    Get unified DAG data for visualization.

    Returns nodes, edges, root_ids, and aggregate stats.
    """
    aggregator = get_aggregator()

    filters = {}
    if status and status != "all":
        filters["status"] = status
    if time_range:
        filters["time_range"] = time_range
    if task_id:
        filters["task_id"] = task_id

    try:
        dag = aggregator.build_dag(filters=filters)
        return dag.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build DAG: {str(e)}")


@router.get("/node/{node_id}")
async def get_node_detail(node_id: str):
    """
    Get detailed info for a specific node.

    Returns full node metadata including code preview for subtasks.
    """
    aggregator = get_aggregator()

    node = aggregator.get_node_detail(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    return node.to_dict()


@router.post("/node/{node_id}/action")
async def node_action(node_id: str, request: NodeActionRequest):
    """
    Execute action on a node.

    Actions:
    - retry: Re-run failed task
    - approve: Approve proposal
    - reject: Reject proposal
    - cancel: Cancel running task
    """
    aggregator = get_aggregator()

    # Verify node exists
    node = aggregator.get_node_detail(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    valid_actions = ["retry", "approve", "reject", "cancel"]
    if request.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action: {request.action}. Valid: {valid_actions}"
        )

    # TODO: Implement actual actions
    # For now, return success placeholder
    return NodeActionResponse(
        success=True,
        message=f"Action '{request.action}' queued for node {node_id}",
        node_id=node_id,
    )


@router.get("/stats")
async def get_dag_stats():
    """
    Get aggregate DAG statistics without full node data.

    Lightweight endpoint for dashboard widgets.
    """
    aggregator = get_aggregator()

    try:
        dag = aggregator.build_dag()
        return {
            "success": True,
            "stats": dag.stats,
            "node_count": len(dag.nodes),
            "edge_count": len(dag.edges),
            "root_count": len(dag.root_ids),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
