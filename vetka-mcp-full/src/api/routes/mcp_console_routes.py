"""
MCP Console Routes - FastAPI Version

@file mcp_console_routes.py
@status ACTIVE
@phase Phase 80.41
@created 2026-01-22

MCP Debug Console API routes for tracking AI agent communications.

Endpoints:
- POST /api/mcp-console/log - Log MCP request/response
- GET /api/mcp-console/history - Get recent MCP logs
- POST /api/mcp-console/save - Save logs to /docs/mcp_chat/
- DELETE /api/mcp-console/clear - Clear log history
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel


router = APIRouter(prefix="/api/mcp-console", tags=["mcp-console"])


# In-memory log storage
_mcp_logs: List[Dict[str, Any]] = []
_max_logs = 1000  # Maximum logs to keep in memory


# ============================================================
# PYDANTIC MODELS
# ============================================================

class MCPLogEntry(BaseModel):
    """Single MCP request or response entry"""
    id: str
    type: str  # 'request' or 'response'
    timestamp: float
    agent: Optional[str] = None
    tool: Optional[str] = None
    model: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    tokens: Optional[int] = None


class SaveRequest(BaseModel):
    """Request to save logs to file"""
    session_id: Optional[str] = "default"
    filename: Optional[str] = None


# ============================================================
# ENDPOINTS
# ============================================================

@router.post("/log")
async def log_mcp_event(entry: MCPLogEntry):
    """
    Log an MCP request or response event.

    Called by:
    - MCP bridge when sending requests
    - MCP bridge when receiving responses
    - Socket.IO handlers for real-time updates
    """
    global _mcp_logs

    # Add to log storage
    log_dict = entry.model_dump()
    _mcp_logs.append(log_dict)

    # Trim if exceeds max size
    if len(_mcp_logs) > _max_logs:
        _mcp_logs = _mcp_logs[-_max_logs:]

    # Emit via Socket.IO if available
    try:
        from main import app
        if hasattr(app.state, 'sio'):
            await app.state.sio.emit('mcp_log', log_dict)
    except Exception as e:
        print(f"[MCP Console] Could not emit Socket.IO event: {e}")

    return {
        'success': True,
        'log_count': len(_mcp_logs),
        'entry_id': entry.id
    }


@router.get("/history")
async def get_history(
    limit: int = 50,
    type_filter: Optional[str] = None,
    agent: Optional[str] = None
):
    """
    Get recent MCP log history.

    Query params:
    - limit: Maximum number of entries to return (default: 50)
    - type_filter: Filter by 'request' or 'response'
    - agent: Filter by agent name
    """
    global _mcp_logs

    # Apply filters
    filtered_logs = _mcp_logs

    if type_filter:
        filtered_logs = [log for log in filtered_logs if log.get('type') == type_filter]

    if agent:
        filtered_logs = [log for log in filtered_logs if log.get('agent') == agent]

    # Get most recent entries
    recent_logs = filtered_logs[-limit:] if len(filtered_logs) > limit else filtered_logs

    return {
        'success': True,
        'logs': recent_logs,
        'total_count': len(_mcp_logs),
        'filtered_count': len(filtered_logs),
        'returned_count': len(recent_logs)
    }


@router.post("/save")
async def save_logs(request: SaveRequest):
    """
    Save current MCP logs to /docs/mcp_chat/ as JSON file.

    Request body:
    - session_id: Optional session identifier (default: "default")
    - filename: Optional custom filename
    """
    global _mcp_logs

    if not _mcp_logs:
        raise HTTPException(status_code=400, detail="No logs to save")

    # Prepare filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = request.session_id or "default"

    if request.filename:
        filename = request.filename
    else:
        filename = f"mcp_console_{session_id}_{timestamp}.json"

    # Ensure directory exists
    docs_dir = Path("docs/mcp_chat")
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Save to file
    filepath = docs_dir / filename

    save_data = {
        'session_id': session_id,
        'saved_at': datetime.now().isoformat(),
        'log_count': len(_mcp_logs),
        'logs': _mcp_logs
    }

    filepath.write_text(json.dumps(save_data, indent=2))

    return {
        'success': True,
        'path': str(filepath.absolute()),
        'filename': filename,
        'log_count': len(_mcp_logs),
        'size_bytes': filepath.stat().st_size
    }


@router.delete("/clear")
async def clear_logs():
    """
    Clear all MCP logs from memory.
    """
    global _mcp_logs

    count = len(_mcp_logs)
    _mcp_logs = []

    return {
        'success': True,
        'cleared_count': count,
        'message': f'Cleared {count} log entries'
    }


@router.get("/stats")
async def get_stats():
    """
    Get statistics about MCP logs.
    """
    global _mcp_logs

    if not _mcp_logs:
        return {
            'success': True,
            'total_logs': 0,
            'requests': 0,
            'responses': 0,
            'agents': [],
            'tools': [],
            'models': []
        }

    # Collect statistics
    requests = [log for log in _mcp_logs if log.get('type') == 'request']
    responses = [log for log in _mcp_logs if log.get('type') == 'response']

    agents = list(set(log.get('agent') for log in _mcp_logs if log.get('agent')))
    tools = list(set(log.get('tool') for log in _mcp_logs if log.get('tool')))
    models = list(set(log.get('model') for log in _mcp_logs if log.get('model')))

    # Calculate average duration
    durations = [log.get('duration_ms') for log in responses if log.get('duration_ms')]
    avg_duration = sum(durations) / len(durations) if durations else 0

    # Calculate total tokens
    tokens = [log.get('tokens') for log in responses if log.get('tokens')]
    total_tokens = sum(tokens) if tokens else 0

    return {
        'success': True,
        'total_logs': len(_mcp_logs),
        'requests': len(requests),
        'responses': len(responses),
        'agents': agents,
        'tools': tools,
        'models': models,
        'avg_duration_ms': round(avg_duration, 2),
        'total_tokens': total_tokens
    }
