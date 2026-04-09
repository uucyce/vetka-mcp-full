"""
VETKA Activity Feed Routes - Phase 108.4 Step 5
API endpoints for unified activity stream across chat, MCP, artifacts, and git.

@file activity_routes.py
@status ACTIVE
@phase Phase 108.4 Step 5
@created 2026-02-02

MARKER_108_5_ACTIVITY_FEED: Unified activity feed API
- Aggregates chat messages, MCP tool calls, artifact events, git commits
- Real-time updates via Socket.IO activity_update event
- Pagination support for large activity streams
- Type filtering (chat, mcp, artifact, commit)

Endpoints:
- GET /api/activity/feed - Get unified activity stream with pagination
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json
import glob
from pathlib import Path
import logging

from src.chat.chat_history_manager import get_chat_history_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/activity", tags=["activity"])


# ============================================================
# PYDANTIC MODELS
# ============================================================

class ActivityItem(BaseModel):
    """Single activity item in the feed."""
    id: str
    type: str  # 'chat', 'mcp', 'artifact', 'commit'
    timestamp: str  # ISO 8601 format
    title: str
    description: str
    metadata: Dict[str, Any]


class ActivityFeedResponse(BaseModel):
    """Activity feed response with pagination."""
    activities: List[ActivityItem]
    total: int
    has_more: bool


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_chat_activities(limit: int = 50, types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Get recent chat activities from ChatHistoryManager.

    Args:
        limit: Max activities to fetch
        types: Activity types to include (None = all)

    Returns:
        List of activity dictionaries
    """
    if types and 'chat' not in types:
        return []

    try:
        manager = get_chat_history_manager()
        activities = []

        # Get recent chats (limit to prevent loading everything)
        recent_chats = manager.get_all_chats(limit=min(limit, 20), offset=0)

        for chat in recent_chats:
            messages = chat.get("messages", [])
            # Get last 3 messages from each chat
            for msg in messages[-3:]:
                timestamp = msg.get("timestamp", chat.get("updated_at", ""))
                role = msg.get("role", "user")
                content = msg.get("content", msg.get("text", ""))

                # Truncate long messages
                description = content[:100] + "..." if len(content) > 100 else content

                activities.append({
                    "id": f"chat_{msg.get('id', chat['id'])}",
                    "type": "chat",
                    "timestamp": timestamp,
                    "title": f"Message in {chat.get('display_name') or chat.get('file_name', 'Unknown')}",
                    "description": description,
                    "metadata": {
                        "chat_id": chat["id"],
                        "sender": role,
                        "agent": msg.get("agent"),
                        "model": msg.get("model"),
                    }
                })

        return activities
    except Exception as e:
        logger.error(f"[ActivityFeed] Error fetching chat activities: {e}")
        return []


def get_mcp_activities(limit: int = 50, types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Get recent MCP tool call activities from audit logs.

    Args:
        limit: Max activities to fetch
        types: Activity types to include (None = all)

    Returns:
        List of activity dictionaries
    """
    if types and 'mcp' not in types:
        return []

    try:
        activities = []
        audit_dir = Path("data/mcp_audit")

        if not audit_dir.exists():
            return []

        # Get all audit files sorted by modification time (newest first)
        audit_files = sorted(
            audit_dir.glob("mcp_audit_*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        # Read recent entries from files
        entries_collected = 0
        for audit_file in audit_files[:5]:  # Check last 5 files
            if entries_collected >= limit:
                break

            try:
                with open(audit_file, 'r') as f:
                    lines = f.readlines()
                    # Read lines in reverse (newest first)
                    for line in reversed(lines):
                        if entries_collected >= limit:
                            break

                        try:
                            entry = json.loads(line.strip())
                            timestamp = entry.get("timestamp", "")
                            tool = entry.get("tool", "unknown")
                            client_id = entry.get("client_id", "unknown")
                            success = entry.get("success", False)

                            # Create activity
                            status_emoji = "✅" if success else "❌"
                            activities.append({
                                "id": f"mcp_{timestamp}_{tool}",
                                "type": "mcp",
                                "timestamp": timestamp,
                                "title": f"{status_emoji} MCP: {tool}",
                                "description": f"Client: {client_id}",
                                "metadata": {
                                    "tool": tool,
                                    "client_id": client_id,
                                    "success": success,
                                    "duration_ms": entry.get("duration_ms"),
                                }
                            })
                            entries_collected += 1
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.warning(f"[ActivityFeed] Error reading audit file {audit_file}: {e}")
                continue

        return activities
    except Exception as e:
        logger.error(f"[ActivityFeed] Error fetching MCP activities: {e}")
        return []


def get_artifact_activities(limit: int = 50, types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Get recent artifact activities from staging.json and disk artifacts.

    Args:
        limit: Max activities to fetch
        types: Activity types to include (None = all)

    Returns:
        List of activity dictionaries
    """
    if types and 'artifact' not in types:
        return []

    try:
        activities = []

        # Read staging.json
        staging_file = Path("data/staging.json")
        if staging_file.exists():
            try:
                staging_data = json.loads(staging_file.read_text())
                artifacts = staging_data.get("artifacts", {})

                for artifact_id, artifact in artifacts.items():
                    status = artifact.get("status", "unknown")

                    activities.append({
                        "id": f"artifact_{artifact_id}",
                        "type": "artifact",
                        "timestamp": datetime.now(timezone.utc).isoformat(),  # Staging doesn't have timestamps
                        "title": f"Artifact: {artifact_id}",
                        "description": f"Status: {status}",
                        "metadata": {
                            "artifact_id": artifact_id,
                            "status": status,
                        }
                    })
            except Exception as e:
                logger.warning(f"[ActivityFeed] Error reading staging.json: {e}")

        # Read disk artifacts
        artifacts_dir = Path("artifacts")
        if artifacts_dir.exists():
            artifact_files = sorted(
                artifacts_dir.glob("*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )[:limit]

            for artifact_file in artifact_files:
                if artifact_file.is_file():
                    mtime = datetime.fromtimestamp(artifact_file.stat().st_mtime, tz=timezone.utc)

                    activities.append({
                        "id": f"artifact_disk_{artifact_file.name}",
                        "type": "artifact",
                        "timestamp": mtime.isoformat(),
                        "title": f"Artifact saved: {artifact_file.name}",
                        "description": f"Size: {artifact_file.stat().st_size} bytes",
                        "metadata": {
                            "file_name": artifact_file.name,
                            "file_path": str(artifact_file),
                            "size_bytes": artifact_file.stat().st_size,
                        }
                    })

        return activities[:limit]
    except Exception as e:
        logger.error(f"[ActivityFeed] Error fetching artifact activities: {e}")
        return []


def get_git_activities(limit: int = 50, types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Get recent git commit activities from git log.

    Args:
        limit: Max activities to fetch
        types: Activity types to include (None = all)

    Returns:
        List of activity dictionaries
    """
    if types and 'commit' not in types:
        return []

    try:
        import subprocess

        activities = []

        # Run git log to get recent commits
        # Format: hash|timestamp|author|subject
        result = subprocess.run(
            ["git", "log", f"-{limit}", "--format=%H|%aI|%an|%s"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if not line:
                    continue

                parts = line.split('|', 3)
                if len(parts) == 4:
                    commit_hash, timestamp, author, subject = parts

                    activities.append({
                        "id": f"commit_{commit_hash[:8]}",
                        "type": "commit",
                        "timestamp": timestamp,
                        "title": subject[:100],
                        "description": f"By {author}",
                        "metadata": {
                            "commit_hash": commit_hash,
                            "short_hash": commit_hash[:8],
                            "author": author,
                            "subject": subject,
                        }
                    })

        return activities
    except Exception as e:
        logger.error(f"[ActivityFeed] Error fetching git activities: {e}")
        return []


def merge_and_sort_activities(
    activities: List[Dict[str, Any]],
    limit: int,
    offset: int
) -> tuple[List[Dict[str, Any]], int]:
    """
    Merge activities from all sources, sort by timestamp, and paginate.

    Args:
        activities: Combined list of activities from all sources
        limit: Max activities to return
        offset: Skip first N activities

    Returns:
        Tuple of (paginated activities, total count)
    """
    # Sort by timestamp (most recent first)
    try:
        sorted_activities = sorted(
            activities,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
    except Exception as e:
        logger.error(f"[ActivityFeed] Error sorting activities: {e}")
        sorted_activities = activities

    total = len(sorted_activities)

    # Paginate
    paginated = sorted_activities[offset:offset + limit]

    return paginated, total


# ============================================================
# API ENDPOINTS
# ============================================================

@router.get("/feed", response_model=ActivityFeedResponse)
async def get_activity_feed(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    types: Optional[str] = None  # Comma-separated: "chat,mcp,artifact,commit"
):
    """
    Get unified activity stream with pagination.

    MARKER_108_5_ACTIVITY_FEED: Main activity feed endpoint

    Query params:
    - limit: Max activities to return (default 50, max 200)
    - offset: Skip first N activities (default 0)
    - types: Comma-separated activity types (chat,mcp,artifact,commit)

    Returns:
        ActivityFeedResponse with activities, total count, and has_more flag

    Example:
        GET /api/activity/feed?limit=20&offset=0&types=chat,mcp
    """
    try:
        # Validate and limit params
        limit = min(max(1, limit), 200)
        offset = max(0, offset)

        # Parse types filter
        type_filter = None
        if types:
            type_filter = [t.strip() for t in types.split(',') if t.strip()]

        # Fetch activities from all sources
        all_activities = []

        # Fetch from each source
        chat_activities = get_chat_activities(limit=limit * 2, types=type_filter)
        mcp_activities = get_mcp_activities(limit=limit * 2, types=type_filter)
        artifact_activities = get_artifact_activities(limit=limit * 2, types=type_filter)
        git_activities = get_git_activities(limit=limit * 2, types=type_filter)

        # Combine all activities
        all_activities.extend(chat_activities)
        all_activities.extend(mcp_activities)
        all_activities.extend(artifact_activities)
        all_activities.extend(git_activities)

        # Merge, sort, and paginate
        paginated_activities, total = merge_and_sort_activities(
            all_activities,
            limit,
            offset
        )

        # Convert to Pydantic models
        activity_items = [
            ActivityItem(**activity)
            for activity in paginated_activities
        ]

        return ActivityFeedResponse(
            activities=activity_items,
            total=total,
            has_more=(offset + limit) < total
        )

    except Exception as e:
        logger.error(f"[ActivityFeed] Error in get_activity_feed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emit")
async def emit_activity_update(
    request: Request,
    activity: ActivityItem
):
    """
    Emit activity_update Socket.IO event for real-time feed updates.

    MARKER_108_5_ACTIVITY_FEED: Real-time activity updates

    This endpoint is called by internal services to broadcast new activities
    to all connected clients via Socket.IO.

    Args:
        activity: Activity item to broadcast

    Returns:
        Success status
    """
    try:
        # Get Socket.IO instance from app state
        socketio = request.app.state.socketio

        if not socketio:
            logger.warning("[ActivityFeed] Socket.IO not available")
            return {"success": False, "message": "Socket.IO not available"}

        # Emit activity_update event
        await socketio.emit('activity_update', activity.dict())

        logger.info(f"[ActivityFeed] Emitted activity_update: {activity.type} - {activity.title}")

        return {
            "success": True,
            "message": "Activity update emitted",
            "activity_id": activity.id
        }

    except Exception as e:
        logger.error(f"[ActivityFeed] Error emitting activity update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_activity_stats(request: Request):
    """
    Get activity statistics (counts by type, recent activity rate).

    Returns:
        Activity statistics
    """
    try:
        # Fetch all activities (no limit)
        chat_activities = get_chat_activities(limit=1000)
        mcp_activities = get_mcp_activities(limit=1000)
        artifact_activities = get_artifact_activities(limit=1000)
        git_activities = get_git_activities(limit=1000)

        return {
            "total": (
                len(chat_activities) +
                len(mcp_activities) +
                len(artifact_activities) +
                len(git_activities)
            ),
            "by_type": {
                "chat": len(chat_activities),
                "mcp": len(mcp_activities),
                "artifact": len(artifact_activities),
                "commit": len(git_activities),
            },
            "sources": {
                "chat_history_manager": len(chat_activities),
                "mcp_audit_logs": len(mcp_activities),
                "disk_artifacts": len(artifact_activities),
                "git_log": len(git_activities),
            }
        }

    except Exception as e:
        logger.error(f"[ActivityFeed] Error in get_activity_stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
