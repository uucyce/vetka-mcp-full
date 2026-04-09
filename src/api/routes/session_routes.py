# file: src/api/routes/session_routes.py
"""
Session Management Routes - Phase 102

API endpoints for managing MCP sessions and session state persistence.

@file session_routes.py
@status ACTIVE
@phase Phase 102
@lastUpdate 2026-02-16

Endpoints:
- GET /api/sessions - List all active sessions
- GET /api/sessions/{session_id} - Get single session details
- POST /api/sessions - Create new session
- DELETE /api/sessions/{session_id} - Delete session
- GET /api/sessions/state - Get current session state
- PUT /api/sessions/state - Update session state
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid

# MARKER_102.2_START
router = APIRouter(prefix="/api", tags=["sessions"])


# ============================================================
# PYDANTIC MODELS
# ============================================================

class SessionCreateRequest(BaseModel):
    """Request model for creating a new session."""
    user_id: str = Field(default="default", description="User identifier")
    group_id: Optional[str] = Field(default=None, description="Group chat ID if in group context")
    chat_id: Optional[str] = Field(default=None, description="Chat ID to link session with existing chat")
    include_viewport: bool = Field(default=True, description="Include 3D viewport context")
    include_pinned: bool = Field(default=True, description="Include pinned files context")
    compress: bool = Field(default=True, description="Apply ELISION compression")
    max_context_tokens: int = Field(default=4000, description="Maximum tokens for context")


class SessionResponse(BaseModel):
    """Response model for session data."""
    session_id: str
    user_id: str
    group_id: Optional[str] = None
    chat_id: Optional[str] = None
    created_at: str
    last_updated: str
    status: str  # "active", "idle", "expired"
    context_summary: Optional[Dict[str, Any]] = None


class SessionStateResponse(BaseModel):
    """Response model for session state."""
    level: str = Field(default="roadmap", description="Navigation level: roadmap | tasks | workflow | running | results")
    roadmap_node_id: str = Field(default="", description="Selected module in roadmap")
    task_id: str = Field(default="", description="Selected task")
    history: List[str] = Field(default_factory=list, description="Navigation history for back button")
    last_updated: str


class SessionStateUpdateRequest(BaseModel):
    """Request model for updating session state."""
    level: Optional[str] = None
    roadmap_node_id: Optional[str] = None
    task_id: Optional[str] = None
    history: Optional[List[str]] = None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _get_all_sessions() -> List[Dict[str, Any]]:
    """
    Get all active sessions from session storage.
    
    Returns:
        List of session dictionaries with metadata
    """
    sessions = []
    
    # Check for MCP state manager sessions
    try:
        from src.mcp.state.mcp_state_manager import MCPStateManager
        state_manager = MCPStateManager()
        
        # Get all session IDs from state manager
        if hasattr(state_manager, 'get_all_sessions'):
            mcp_sessions = state_manager.get_all_sessions()
            for session_data in mcp_sessions:
                sessions.append({
                    "session_id": session_data.get("session_id", ""),
                    "user_id": session_data.get("user_id", "default"),
                    "group_id": session_data.get("group_id"),
                    "chat_id": session_data.get("chat_id"),
                    "created_at": session_data.get("created_at", ""),
                    "last_updated": session_data.get("last_updated", ""),
                    "status": session_data.get("status", "active"),
                    "context_summary": session_data.get("context_summary")
                })
    except (ImportError, AttributeError) as e:
        print(f"[SessionRoutes] MCP state manager not available: {e}")
    
    # Fallback: check session_state.json
    try:
        from src.services.project_config import SessionState, SESSION_STATE_PATH
        if os.path.exists(SESSION_STATE_PATH):
            session_state = SessionState.load()
            # Create a pseudo-session from current state
            sessions.append({
                "session_id": "current",
                "user_id": "default",
                "group_id": None,
                "chat_id": None,
                "created_at": session_state.last_updated or datetime.now(timezone.utc).isoformat(),
                "last_updated": session_state.last_updated or datetime.now(timezone.utc).isoformat(),
                "status": "active",
                "context_summary": {
                    "level": session_state.level,
                    "roadmap_node_id": session_state.roadmap_node_id,
                    "task_id": session_state.task_id
                }
            })
    except Exception as e:
        print(f"[SessionRoutes] Error loading session state: {e}")
    
    return sessions


def _get_session_by_id(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get session by ID.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session dictionary or None if not found
    """
    sessions = _get_all_sessions()
    for session in sessions:
        if session.get("session_id") == session_id:
            return session
    return None


# ============================================================
# API ENDPOINTS
# ============================================================

@router.get("/sessions", response_model=Dict[str, Any])
async def list_sessions(request: Request):
    """
    List all active sessions.
    
    Returns:
        Dictionary with sessions list and metadata
    """
    try:
        sessions = _get_all_sessions()
        
        session_responses = [
            SessionResponse(
                session_id=s["session_id"],
                user_id=s["user_id"],
                group_id=s.get("group_id"),
                chat_id=s.get("chat_id"),
                created_at=s["created_at"],
                last_updated=s["last_updated"],
                status=s.get("status", "active"),
                context_summary=s.get("context_summary")
            )
            for s in sessions
        ]
        
        return {
            "sessions": session_responses,
            "total": len(session_responses),
            "active_count": sum(1 for s in sessions if s.get("status") == "active")
        }
    except Exception as e:
        print(f"[SessionRoutes] Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, request: Request):
    """
    Get single session details.
    
    Args:
        session_id: Session UUID or identifier
        
    Returns:
        Session details with full context
    """
    try:
        session = _get_session_by_id(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        return SessionResponse(
            session_id=session["session_id"],
            user_id=session["user_id"],
            group_id=session.get("group_id"),
            chat_id=session.get("chat_id"),
            created_at=session["created_at"],
            last_updated=session["last_updated"],
            status=session.get("status", "active"),
            context_summary=session.get("context_summary")
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SessionRoutes] Error getting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions", response_model=SessionResponse)
async def create_session(session_request: SessionCreateRequest, request: Request):
    """
    Create new session.
    
    Args:
        session_request: Session creation parameters
        
    Returns:
        Created session details
    """
    try:
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        session_data = {
            "session_id": session_id,
            "user_id": session_request.user_id,
            "group_id": session_request.group_id,
            "chat_id": session_request.chat_id,
            "created_at": now,
            "last_updated": now,
            "status": "active",
            "context_summary": {
                "include_viewport": session_request.include_viewport,
                "include_pinned": session_request.include_pinned,
                "compress": session_request.compress,
                "max_context_tokens": session_request.max_context_tokens
            }
        }
        
        # Try to save to MCP state manager
        try:
            from src.mcp.state.mcp_state_manager import MCPStateManager
            state_manager = MCPStateManager()
            import asyncio
            asyncio.create_task(state_manager.save_state(
                agent_id=session_id,
                data=session_data,
                ttl_seconds=3600,
                workflow_id=session_request.user_id
            ))
        except Exception as e:
            print(f"[SessionRoutes] Could not save to MCP state manager: {e}")
        
        return SessionResponse(
            session_id=session_data["session_id"],
            user_id=session_data["user_id"],
            group_id=session_data.get("group_id"),
            chat_id=session_data.get("chat_id"),
            created_at=session_data["created_at"],
            last_updated=session_data["last_updated"],
            status=session_data["status"],
            context_summary=session_data.get("context_summary")
        )
    except Exception as e:
        print(f"[SessionRoutes] Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, request: Request):
    """
    Delete session.
    
    Args:
        session_id: Session UUID to delete
        
    Returns:
        Success status
    """
    try:
        session = _get_session_by_id(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Try to delete from MCP state manager
        try:
            from src.mcp.state.mcp_state_manager import MCPStateManager
            state_manager = MCPStateManager()
            import asyncio
            asyncio.create_task(state_manager.delete_state(session_id))
        except Exception as e:
            print(f"[SessionRoutes] Could not delete from MCP state manager: {e}")
        
        return {
            "success": True,
            "session_id": session_id,
            "message": f"Session {session_id} deleted"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SessionRoutes] Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/state", response_model=SessionStateResponse)
async def get_session_state(request: Request):
    """
    Get current session state.
    
    Returns:
        Current session navigation state
    """
    try:
        from src.services.project_config import SessionState, SESSION_STATE_PATH
        
        if not os.path.exists(SESSION_STATE_PATH):
            # Return default state
            return SessionStateResponse(
                level="roadmap",
                roadmap_node_id="",
                task_id="",
                history=[],
                last_updated=datetime.now(timezone.utc).isoformat()
            )
        
        session_state = SessionState.load()
        
        return SessionStateResponse(
            level=session_state.level,
            roadmap_node_id=session_state.roadmap_node_id,
            task_id=session_state.task_id,
            history=session_state.history,
            last_updated=session_state.last_updated or datetime.now(timezone.utc).isoformat()
        )
    except Exception as e:
        print(f"[SessionRoutes] Error getting session state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sessions/state")
async def update_session_state(state_update: SessionStateUpdateRequest, request: Request):
    """
    Update session state.
    
    Args:
        state_update: State fields to update
        
    Returns:
        Updated session state
    """
    try:
        from src.services.project_config import SessionState, SESSION_STATE_PATH
        
        # Load existing state or create new
        if os.path.exists(SESSION_STATE_PATH):
            session_state = SessionState.load()
        else:
            session_state = SessionState()
        
        # Update fields
        if state_update.level is not None:
            session_state.level = state_update.level
        if state_update.roadmap_node_id is not None:
            session_state.roadmap_node_id = state_update.roadmap_node_id
        if state_update.task_id is not None:
            session_state.task_id = state_update.task_id
        if state_update.history is not None:
            session_state.history = state_update.history
        
        session_state.last_updated = datetime.now(timezone.utc).isoformat()
        
        # Save state
        session_state.save()
        
        return {
            "success": True,
            "state": SessionStateResponse(
                level=session_state.level,
                roadmap_node_id=session_state.roadmap_node_id,
                task_id=session_state.task_id,
                history=session_state.history,
                last_updated=session_state.last_updated
            )
        }
    except Exception as e:
        print(f"[SessionRoutes] Error updating session state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# MARKER_102.2_END