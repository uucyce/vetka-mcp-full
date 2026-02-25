# file: src/api/routes/agent_memory_routes.py

@router.get("/sessions")
async def get_all_sessions(
    status: Optional[str] = Query(None, description="Filter by status (active, completed, failed)"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    marker: Optional[str] = Query(None, description="Filter by task marker"),
    limit: Optional[int] = Query(None, description="Limit number of results")
) -> Dict[str, Any]:
    """
    Get all agent test sessions with optional filtering.
    
    Returns list of sessions sorted by creation time (newest first).
    Supports filtering by status, agent_type, and marker.
    """
    try:
        all_sessions = _get_all_sessions()
        
        # Apply filters
        filtered_sessions = all_sessions
        
        if status:
            filtered_sessions = [s for s in filtered_sessions if s.get("status") == status]
        
        if agent_type:
            filtered_sessions = [s for s in filtered_sessions if s.get("agent_type") == agent_type]
        
        if marker:
            filtered_sessions = [s for s in filtered_sessions if s.get("marker") == marker]
        
        # Sort by created_at descending (newest first)
        filtered_sessions.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        
        # Apply limit
        if limit and limit > 0:
            filtered_sessions = filtered_sessions[:limit]
        
        return {
            "success": True,
            "sessions": filtered_sessions,
            "count": len(filtered_sessions),
            "total_count": len(all_sessions),
            "filters_applied": {
                "status": status,
                "agent_type": agent_type,
                "marker": marker,
                "limit": limit
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve sessions: {str(e)}")