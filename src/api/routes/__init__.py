"""
VETKA API Routes - FastAPI Router Aggregator

@file routes/__init__.py
@status ACTIVE
@phase Phase 108.4
@lastAudit 2026-02-02

Aggregates all FastAPI routers for registration with the main app.
ALL REST ROUTES MIGRATED!

Total: 25+ routers, 75+ endpoints (Phase 136: unified search + artifacts API)
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

# MARKER_133.TRACKER: Task lifecycle tracking
from .task_tracker_routes import router as tracker_router

# MARKER_134.FEEDBACK: Pipeline feedback and self-improvement
from .feedback_routes import router as feedback_router

# MARKER_135.2B: DAG visualization routes
from .dag_routes import router as dag_router

# MARKER_136.UNIFIED_SEARCH_ROUTE
from .unified_search_routes import router as unified_search_router

# MARKER_136.ARTIFACT_API_ROUTE
from .artifact_routes import router as artifact_router

# MARKER_141.PIPELINE_CONFIG: Pipeline presets + prompts API
from .pipeline_config_routes import router as pipeline_config_router
from .connectors_routes import router as connectors_router

# MARKER_144.1B: Workflow template CRUD (distinct from /api/workflow orchestrator history)
from .workflow_template_routes import router as workflow_template_router

# MARKER_144.12: Architect Chat — conversational interface in MCC
from .architect_chat_routes import router as architect_chat_router

# MARKER_152.2: Pipeline Analytics — stats dashboard, drill-down, trends, cost
from .analytics_routes import router as analytics_router

# MARKER_153.1B: MCC — Mycelium Command Center init, state, project setup
from .mcc_routes import router as mcc_router
from .voice_storage_routes import router as voice_storage_router
from .cut_routes import router as cut_router


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
        tracker_router,  # /api/tracker/* (Phase 133 - Task lifecycle tracking)
        feedback_router,  # /api/feedback/* (Phase 134 - Pipeline self-improvement)
        dag_router,  # /api/dag/* (Phase 135 - DAG visualization)
        unified_search_router,  # /api/search/unified (Phase 136 - unified federated search)
        artifact_router,  # /api/artifacts/* (Phase 136 - artifacts panel API)
        pipeline_config_router,  # /api/pipeline/* (Phase 141 - presets + prompts config)
        connectors_router,  # /api/connectors/* (Phase 147.2 - cloud/social connectors)
        workflow_template_router,  # /api/workflows/* (Phase 144 - workflow template CRUD)
        architect_chat_router,  # /api/architect/* (Phase 144.12 - Architect Chat)
        analytics_router,  # /api/analytics/* (Phase 152 - Pipeline analytics dashboard)
        mcc_router,  # /api/mcc/* (Phase 153 - MCC init, state, project setup)
        voice_storage_router,  # /api/voice/storage/* (solo voice persistence + replay)
        cut_router,  # /api/cut/* (Phase 170 - standalone CUT bootstrap)
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
    "tracker_router",
    "feedback_router",
    "dag_router",
    "unified_search_router",
    "artifact_router",
    "pipeline_config_router",
    "connectors_router",
    "workflow_template_router",
    "architect_chat_router",
    "analytics_router",
    "mcc_router",
    "voice_storage_router",
    "cut_router",
]
