"""
VETKA API Routes - FastAPI Router Aggregator

@file routes/__init__.py
@status ACTIVE
@phase Phase 108.4
@lastAudit 2026-02-02

Aggregates all FastAPI routers for registration with the main app.
ALL REST ROUTES MIGRATED!

Total: 21 routers, 70+ endpoints (Phase 108.4: +1 activity feed router)
"""

from fastapi import APIRouter, FastAPI
from typing import List
import os

from .config_routes import router as config_router
from .metrics_routes import router as metrics_router
from .files_routes import router as files_router
from .tree_routes import router as tree_router
from .eval_routes import router as eval_router
from .semantic_routes import router as semantic_router
from .chat_routes import router as chat_router
from .chat_history_routes import router as chat_history_router
from .knowledge_routes import router as knowledge_router
from .ocr_routes import router as ocr_router
from .file_ops_routes import router as file_ops_router
from .triple_write_routes import router as triple_write_router
from .workflow_routes import router as workflow_router
from .embeddings_routes import router as embeddings_router

# MARKER: PHASE43_HEALTH_ROUTES
from .health_routes import router as health_router

# MARKER: PHASE54_WATCHER_ROUTES
from .watcher_routes import router as watcher_router

# MARKER: PHASE56_MODEL_GROUP_ROUTES
from .model_routes import router as model_router
from .group_routes import router as group_router

# MARKER: PHASE80_DEBUG_ROUTES - Browser Agent Bridge
from .debug_routes import router as debug_router

# MARKER: PHASE98_CAM_ROUTES - CAM-Emoji Link (user reactions -> model weights)
from .cam_routes import router as cam_router

# MARKER_108_5_ACTIVITY_FEED - Phase 108.4 Step 5: Unified Activity Feed
from .activity_routes import router as activity_router

# MARKER_131.C20C: Universal Task API
from .task_routes import router as task_router


def get_all_routers() -> List[APIRouter]:
    """
    Get all API routers for registration.

    Returns:
        List of APIRouter instances to register with the app.
    """
    return [
        config_router,  # /api/config, /api/mentions, /api/models/available, etc.
        metrics_router,  # /api/metrics/dashboard, /api/metrics/agents, etc.
        files_router,  # /api/files/read, /api/files/save, /api/files/raw
        tree_router,  # /api/tree/data, /api/tree/knowledge-graph, etc.
        eval_router,  # /api/eval/score, /api/eval/history, etc.
        semantic_router,  # /api/semantic-tags/*, /api/search/semantic, etc.
        chat_router,  # /api/chat (THE BIG ONE!), /api/chat/history, etc.
        chat_history_router,  # /api/chats/* (Phase 50 - Chat History + Sidebar)
        knowledge_router,  # /api/knowledge-graph/*, /api/arc/*, /api/branch/*, etc.
        ocr_router,  # /api/ocr/status, /api/ocr/process, etc.
        file_ops_router,  # /api/file/show-in-finder
        triple_write_router,  # /api/triple-write/stats, /cleanup, /reindex
        workflow_router,  # /api/workflow/history, /stats, /{id}
        embeddings_router,  # /api/embeddings/project, /project-vetka, /cluster
        health_router,  # /api/health/deep, /ready, /live, /metrics (Phase 43)
        watcher_router,  # /api/watcher/add, /remove, /status, /heat (Phase 54)
        model_router,  # /api/models/* (Phase 56 - Model phonebook)
        group_router,  # /api/groups/* (Phase 56 - Group chats)
        debug_router,  # /api/debug/* (Phase 80 - Browser Agent Bridge)
        cam_router,  # /api/cam/* (Phase 98 - CAM-Emoji Link)
        activity_router,  # /api/activity/* (Phase 108.4 Step 5 - Activity Feed)
        task_router,  # /api/tasks/* (Phase 131.C20C - Universal Task API)
    ]


def register_all_routers(app: FastAPI) -> None:
    """
    Register all routers with FastAPI app.

    Args:
        app: FastAPI application instance
    """
    routers = get_all_routers()

    for router in routers:
        app.include_router(router)

    # === OPENCODE BRIDGE ROUTES (Phase 90.X) ===
    # Optional: only load if explicitly enabled via environment
    opencode_bridge_enabled = (
        os.getenv("OPENCODE_BRIDGE_ENABLED", "false").lower() == "true"
    )

    if opencode_bridge_enabled:
        try:
            from src.opencode_bridge.routes import router as bridge_router

            app.include_router(
                bridge_router, prefix="/api/bridge", tags=["OpenCode Bridge"]
            )
            print("✅ [Phase 90.X] OpenCode Bridge registered on /api/bridge/*")
        except ImportError as e:
            print(f"⚠️  [Phase 90.X] OpenCode Bridge import failed: {e}")
        except Exception as e:
            print(f"❌ [Phase 90.X] OpenCode Bridge registration error: {e}")
    else:
        print(
            "ℹ️  [Phase 90.X] OpenCode Bridge disabled (set OPENCODE_BRIDGE_ENABLED=true to enable)"
        )

    print(
        f"  [API] Registered {len(routers)} FastAPI routers (Phase 108.4: +1 activity feed)"
    )


# Export for convenience
__all__ = [
    "get_all_routers",
    "register_all_routers",
    "config_router",
    "metrics_router",
    "files_router",
    "tree_router",
    "eval_router",
    "semantic_router",
    "chat_router",
    "chat_history_router",
    "knowledge_router",
    "ocr_router",
    "file_ops_router",
    "triple_write_router",
    "workflow_router",
    "embeddings_router",
    "health_router",
    "watcher_router",
    "model_router",
    "group_router",
    "debug_router",
    "cam_router",
    "activity_router",
    "task_router",
]
